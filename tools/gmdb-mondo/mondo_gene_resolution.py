"""Classify empty-gene_names gallery rows using MONDO causal-gene relations.

Used by Stage 3 (030_build_metadata_pickle.py). Evidence is limited to
``relationship: has_material_basis_in_germline_mutation_in`` edges stored in
``OboIndex.mondo_causal_genes`` — synonym-derived gene hints are ignored.

``subtype_expanded`` rows are split in the pickle into one gene_level entry per
candidate gene (same image, same GM distance later), mirroring the legacy
OMIM Phenotypic Series expansion in upstream GestaltMatcher pickles.
"""

from __future__ import annotations

from typing import Iterable

from map_GMDBomim_to_mondo import OboIndex

# Chromosomal / aneuploidy roots. Checked before subtype descent so that
# Prader-Willi (child Schaaf-Yang / MAGEL2) is not mislabeled subtype_expanded.
CHROMOSOMAL_ROOTS = ("MONDO:0019040", "MONDO:0700064")
DESCENDANT_DEPTH = 4

GeneStatus = str  # gmdb | mondo | subtype_expanded | gene_unresolved


def build_children(index: OboIndex) -> dict[str, list[str]]:
    """Invert ``mondo_parents`` into a child index."""
    children: dict[str, list[str]] = {}
    for child, parents in index.mondo_parents.items():
        for parent in parents:
            children.setdefault(parent, []).append(child)
    return children


def is_under_roots(
    index: OboIndex,
    mondo_id: str,
    roots: Iterable[str],
) -> bool:
    """True if ``mondo_id`` is any of ``roots`` or a descendant via is_a."""
    root_set = set(roots)
    if mondo_id in root_set:
        return True
    stack = list(index.mondo_parents.get(mondo_id, []))
    seen = {mondo_id}
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        if current in root_set:
            return True
        stack.extend(index.mondo_parents.get(current, []))
    return False


def is_chromosomal(index: OboIndex, mondo_id: str) -> bool:
    return is_under_roots(index, mondo_id, CHROMOSOMAL_ROOTS)


def own_genes(index: OboIndex, mondo_id: str) -> list[str]:
    return list(index.mondo_causal_genes.get(mondo_id, []))


def descendant_genes(
    index: OboIndex,
    children: dict[str, list[str]],
    mondo_id: str,
    depth: int = DESCENDANT_DEPTH,
) -> set[str]:
    """Causal genes on descendants of ``mondo_id`` (not including itself)."""
    found: set[str] = set()
    # (node, remaining_depth)
    stack = [(child, depth - 1) for child in children.get(mondo_id, [])]
    seen = {mondo_id}
    while stack:
        node, remaining = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        for gene in index.mondo_causal_genes.get(node, []):
            found.add(gene)
        if remaining <= 0:
            continue
        for child in children.get(node, []):
            stack.append((child, remaining - 1))
    return found


def classify(
    index: OboIndex,
    children: dict[str, list[str]],
    mondo_ids: list[str],
) -> tuple[GeneStatus, set[str]]:
    """Classify empty-gene_names images by MONDO ID(s).

    Order (must not change):
      1. chromosomal / aneuploidy with no own gene → gene_unresolved
      2. exactly one own causal gene (union across IDs) → mondo
      3. multiple own genes, or descendants have genes → subtype_expanded
      4. otherwise → gene_unresolved
    """
    if not mondo_ids:
        return "gene_unresolved", set()

    own: set[str] = set()
    for mid in mondo_ids:
        own.update(own_genes(index, mid))

    chromosomal = any(is_chromosomal(index, mid) for mid in mondo_ids)
    if chromosomal and not own:
        return "gene_unresolved", set()

    if len(own) == 1:
        return "mondo", own

    if len(own) > 1:
        return "subtype_expanded", own

    # No own genes: look at descendants.
    descendants: set[str] = set()
    for mid in mondo_ids:
        descendants.update(descendant_genes(index, children, mid))
    if descendants:
        return "subtype_expanded", descendants

    return "gene_unresolved", set()


def sorted_symbols(symbols: set[str]) -> list[str]:
    """Deterministic candidate order for gene_level expansion."""
    return sorted(symbols, key=str.upper)
