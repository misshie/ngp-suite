#!/usr/bin/env python3
"""Map OMIM IDs (and optionally gene names) in image metadata TSV to MONDO terms."""

from __future__ import annotations

import argparse
import csv
import gzip
import re
import sys
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, TextIO

MONDO_COLUMNS = [
    "mondo_id",
    "mondo_disease",
    "mondo_parent_id",
    "mondo_parent_disease",
    "mondo_grandparent_id",
    "mondo_grandparent_disease",
    "mondo_source",
]

PS_RE = re.compile(r"^PS(\d+)$", re.IGNORECASE)
NUM_RE = re.compile(r"^\d+$")
SYN_RE = re.compile(r'^synonym: "([^"]+)"(.*)$')
CAUSED_BY_RE = re.compile(r"caused by mutation in ([A-Za-z][A-Za-z0-9-]+)$")
GENE_RELATED_RE = re.compile(r"^([A-Za-z][A-Za-z0-9-]+)-related\b")
SERIES_GENE_RE = re.compile(r"^([A-Z][A-Z0-9-]+) ")
# MONDO's curated gene association; the trailing OBO comment carries the symbol:
#   relationship: has_material_basis_in_germline_mutation_in <IRI> {source="..."} ! BICRA
GENE_REL_RE = re.compile(
    r"^relationship: has_material_basis_in_germline_mutation_in "
    r"(\S+)(?: \{[^}]*\})? ! (.+)$"
)
HGNC_IRI_RE = re.compile(r"(?:hgnc[:/]|HGNC:)(\d+)\s*$", re.IGNORECASE)
JOIN = ", "
NON_HUMAN_ROOT = "MONDO:0005583"


@dataclass
class OboIndex:
    omim_to_mondo: dict[str, str] = field(default_factory=dict)
    gene_to_mondo: dict[str, list[str]] = field(default_factory=dict)
    mondo_name: dict[str, str] = field(default_factory=dict)
    mondo_parents: dict[str, list[str]] = field(default_factory=dict)
    # Forward index: MONDO ID -> curated causal gene symbols (relationship: only).
    mondo_causal_genes: dict[str, list[str]] = field(default_factory=dict)
    # Gene symbol (upper) -> HGNC:nnn from the relationship IRI.
    gene_hgnc: dict[str, str] = field(default_factory=dict)
    # Non-human animal disease terms dropped from the gene indexes.
    non_human_excluded: int = 0


def normalize_hgnc_iri(iri: str) -> str | None:
    """Convert ``http://identifiers.org/hgnc/7133`` (etc.) to ``HGNC:7133``."""
    match = HGNC_IRI_RE.search(iri.strip())
    if not match:
        return None
    return f"HGNC:{match.group(1)}"


def _strip_trailing_comment(value: str) -> str:
    """Drop OBO trailing comments / axioms after '!' or '{'."""
    value = value.split("{", 1)[0]
    value = value.split("!", 1)[0]
    return value.strip()


def _dedupe_preserve(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _join_ids(ids: list[str]) -> str:
    return JOIN.join(ids)


def _join_names(ids: list[str], index: OboIndex) -> str:
    return JOIN.join(index.mondo_name.get(i, "") for i in ids)


@contextmanager
def open_text(path: Path) -> Iterator[TextIO]:
    """Open a text file, transparently decompressing *.gz."""
    if path.suffix == ".gz" or path.name.endswith(".obo.gz"):
        with gzip.open(path, mode="rt", encoding="utf-8") as handle:
            yield handle
    else:
        with path.open(encoding="utf-8") as handle:
            yield handle


def parse_obo(path: Path) -> OboIndex:
    """Build OMIM/OMIMPS/gene→MONDO, name, and is_a indexes from an OBO file."""
    index = OboIndex()
    gene_seen: dict[str, set[str]] = {}
    cur_id: str | None = None
    cur_name: str | None = None
    cur_parents: list[str] = []
    cur_xrefs: list[str] = []
    cur_synonyms: list[tuple[str, str]] = []
    # (symbol, optional HGNC id) from relationship: lines only.
    cur_gene_rels: list[tuple[str, str | None]] = []
    cur_obsolete = False

    def add_gene(gene: str, mondo_id: str) -> None:
        key = gene.upper()
        seen = gene_seen.setdefault(key, set())
        if mondo_id in seen:
            return
        seen.add(mondo_id)
        index.gene_to_mondo.setdefault(key, []).append(mondo_id)

    def reset() -> None:
        nonlocal cur_id, cur_name, cur_parents, cur_xrefs, cur_synonyms
        nonlocal cur_gene_rels, cur_obsolete
        cur_id = None
        cur_name = None
        cur_parents = []
        cur_xrefs = []
        cur_synonyms = []
        cur_gene_rels = []
        cur_obsolete = False

    def flush() -> None:
        nonlocal cur_id, cur_name, cur_parents, cur_xrefs, cur_synonyms
        nonlocal cur_gene_rels, cur_obsolete
        if cur_id is None or cur_obsolete:
            # Deprecated terms carry stale xrefs that would otherwise shadow the
            # live term sharing the same OMIM ID.
            reset()
            return
        if cur_name is not None:
            index.mondo_name[cur_id] = cur_name
        index.mondo_parents[cur_id] = list(cur_parents)
        for xref in cur_xrefs:
            if xref.startswith("OMIM:") or xref.startswith("OMIMPS:"):
                index.omim_to_mondo.setdefault(xref, cur_id)
        for syn, rest in cur_synonyms:
            m = CAUSED_BY_RE.search(syn)
            if m:
                add_gene(m.group(1), cur_id)
            m = GENE_RELATED_RE.match(syn)
            if m:
                add_gene(m.group(1), cur_id)
            if "disease_series_by_gene" in rest:
                m = SERIES_GENE_RE.match(syn)
                if m:
                    add_gene(m.group(1), cur_id)
        causal: list[str] = []
        causal_seen: set[str] = set()
        for gene, hgnc_id in cur_gene_rels:
            add_gene(gene, cur_id)
            key = gene.upper()
            if gene not in causal_seen:
                causal_seen.add(gene)
                causal.append(gene)
            if hgnc_id and key not in index.gene_hgnc:
                index.gene_hgnc[key] = hgnc_id
        if causal:
            index.mondo_causal_genes[cur_id] = causal
        reset()

    with open_text(path) as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            if line == "[Term]":
                flush()
                continue
            if line.startswith("[") and line.endswith("]") and line != "[Term]":
                flush()
                continue
            if line.startswith("id: "):
                cur_id = line[4:].strip()
            elif line.startswith("name: "):
                cur_name = line[6:].strip()
            elif line.startswith("is_a: "):
                parent_id = _strip_trailing_comment(line[6:])
                if parent_id:
                    cur_parents.append(parent_id)
            elif line.startswith("xref: "):
                xref = _strip_trailing_comment(line[6:])
                if xref:
                    cur_xrefs.append(xref)
            elif line.startswith("synonym: "):
                m = SYN_RE.match(line)
                if m:
                    cur_synonyms.append((m.group(1), m.group(2)))
            elif line.startswith("relationship: "):
                m = GENE_REL_RE.match(line)
                if m:
                    iri, gene = m.group(1).strip(), m.group(2).strip()
                    if gene:
                        cur_gene_rels.append((gene, normalize_hgnc_iri(iri)))
            elif line.startswith("is_obsolete: true"):
                cur_obsolete = True
        flush()

    exclude_non_human_from_gene_indexes(index)
    return index


def non_human_terms(index: OboIndex) -> set[str]:
    """Return NON_HUMAN_ROOT and every is_a descendant of it."""
    children: dict[str, list[str]] = {}
    for child, parents in index.mondo_parents.items():
        for parent in parents:
            children.setdefault(parent, []).append(child)
    found: set[str] = set()
    stack = [NON_HUMAN_ROOT]
    while stack:
        node = stack.pop()
        if node in found:
            continue
        found.add(node)
        stack.extend(children.get(node, []))
    return found


def exclude_non_human_from_gene_indexes(index: OboIndex) -> None:
    """
    Drop animal disease terms from gene lookups.

    MONDO annotates animal diseases with the orthologous human gene, so gene
    lookups would otherwise attach e.g. cattle or dog diseases to patients.
    Names and is_a edges are kept so hierarchy traversal stays intact.
    """
    excluded = non_human_terms(index)
    index.non_human_excluded = len(excluded)
    for gene in list(index.gene_to_mondo):
        kept = [mid for mid in index.gene_to_mondo[gene] if mid not in excluded]
        if kept:
            index.gene_to_mondo[gene] = kept
        else:
            del index.gene_to_mondo[gene]
    for mid in excluded:
        index.mondo_causal_genes.pop(mid, None)


def tokenize_field(raw: str) -> list[str]:
    if not raw or not raw.strip():
        return []
    return [part.strip() for part in raw.replace(";", ",").split(",") if part.strip()]


def split_omim_tokens(raw: str) -> tuple[list[str], list[str], list[str]]:
    """Split an omim_ids cell into (plain numbers, PS numbers, unrecognised)."""
    nums: list[str] = []
    pss: list[str] = []
    other: list[str] = []
    for part in tokenize_field(raw):
        if NUM_RE.fullmatch(part):
            nums.append(part)
            continue
        m = PS_RE.fullmatch(part)
        if m:
            pss.append(m.group(1))
        else:
            other.append(part)
    return _dedupe_preserve(nums), _dedupe_preserve(pss), other


def resolve_lookup_keys(raw: str) -> tuple[list[str], str]:
    """
    Resolve an omim_ids cell to every OBO xref key worth looking up.

    All plain OMIM numbers are used when present. Phenotypic series are a
    deliberate second choice: GMDB frequently lists a disease together with its
    series (``239300, PS135900, PS239300``), and treating both as equals would
    emit a disease and its own supertype as two independent syndromes. The
    series reappears as a MONDO parent anyway.
    """
    nums, pss, _other = split_omim_tokens(raw)
    if nums:
        return [f"OMIM:{n}" for n in nums], "omim"
    if pss:
        return [f"OMIMPS:{p}" for p in pss], "omimps"
    return [], "none"


def primary_omim_value(raw: str) -> int | str:
    """Return the representative bare OMIM number for a cell, else ''."""
    nums, pss, _other = split_omim_tokens(raw)
    if nums:
        return int(nums[0])
    if pss:
        return int(pss[0])
    return ""


def collect_parents(mondo_ids: list[str], index: OboIndex) -> list[str]:
    parents: list[str] = []
    for mid in mondo_ids:
        parents.extend(index.mondo_parents.get(mid) or [])
    return _dedupe_preserve(parents)


def collect_grandparents(parent_ids: list[str], index: OboIndex) -> list[str]:
    grandparents: list[str] = []
    for pid in parent_ids:
        grandparents.extend(index.mondo_parents.get(pid) or [])
    return _dedupe_preserve(grandparents)


def values_from_mondo_ids(
    mondo_ids: list[str],
    index: OboIndex,
    source: str,
) -> dict[str, str]:
    mondo_ids = _dedupe_preserve(mondo_ids)
    parent_ids = collect_parents(mondo_ids, index)
    grandparent_ids = collect_grandparents(parent_ids, index)
    return {
        "mondo_id": _join_ids(mondo_ids),
        "mondo_disease": _join_names(mondo_ids, index),
        "mondo_parent_id": _join_ids(parent_ids),
        "mondo_parent_disease": _join_names(parent_ids, index),
        "mondo_grandparent_id": _join_ids(grandparent_ids),
        "mondo_grandparent_disease": _join_names(grandparent_ids, index),
        "mondo_source": source,
    }


def empty_mondo_cols() -> dict[str, str]:
    return {col: "" for col in MONDO_COLUMNS}


def enrich_row(
    omim_ids: str,
    gene_names: str,
    index: OboIndex,
) -> tuple[dict[str, str], str, bool]:
    """
    Return (mondo columns, reason, mapped).

    OMIM identifiers win; the gene symbols are consulted whenever OMIM yields
    nothing, including when OMIM IDs were present but absent from the ontology.
    Every resolvable identifier contributes a MONDO term, so ``mondo_id`` may
    hold several IDs.

    mapped=False means conversion failed and should be reported on stderr.
    """
    keys, kind = resolve_lookup_keys(omim_ids)
    mondo_ids = _dedupe_preserve(
        [index.omim_to_mondo[key] for key in keys if key in index.omim_to_mondo]
    )
    if mondo_ids:
        return values_from_mondo_ids(mondo_ids, index, "omim"), f"mapped_{kind}", True

    genes = tokenize_field(gene_names)
    mondo_ids = _dedupe_preserve(
        [mid for gene in genes for mid in index.gene_to_mondo.get(gene.upper(), [])]
    )
    if mondo_ids:
        return values_from_mondo_ids(mondo_ids, index, "gene"), "mapped_gene", True

    if keys and genes:
        return empty_mondo_cols(), "unmapped_omim_gene", False
    if keys:
        return empty_mondo_cols(), "unmapped_omim", False
    if genes:
        return empty_mondo_cols(), "unmapped_gene", False
    return empty_mondo_cols(), "unmapped_no_identifier", False


def process_tsv(
    input_path: Path,
    output_path: Path,
    index: OboIndex,
) -> Counter[str]:
    stats: Counter[str] = Counter()
    with input_path.open(encoding="utf-8", newline="") as in_f:
        reader = csv.DictReader(in_f, delimiter="\t")
        if reader.fieldnames is None:
            raise SystemExit(f"No header found in {input_path}")
        required = {"omim_ids", "gene_names", "image_id", "patient_id"}
        missing = required - set(reader.fieldnames)
        if missing:
            raise SystemExit(f"Missing columns in {input_path}: {sorted(missing)}")

        fieldnames = list(reader.fieldnames) + [
            col for col in MONDO_COLUMNS if col not in reader.fieldnames
        ]

        with output_path.open("w", encoding="utf-8", newline="") as out_f:
            writer = csv.DictWriter(
                out_f,
                fieldnames=fieldnames,
                delimiter="\t",
                lineterminator="\n",
                extrasaction="ignore",
            )
            writer.writeheader()
            for row in reader:
                mondo_cols, reason, mapped = enrich_row(
                    row.get("omim_ids", "") or "",
                    row.get("gene_names", "") or "",
                    index,
                )
                stats[reason] += 1
                stats["total"] += 1
                if mapped:
                    stats["mapped"] += 1
                    n_ids = len(tokenize_field(mondo_cols["mondo_id"]))
                    if n_ids > 1:
                        stats["multi_mondo"] += 1
                else:
                    stats["failed"] += 1
                    print(
                        f"unmapped\t{row.get('image_id', '')}\t{row.get('patient_id', '')}",
                        file=sys.stderr,
                    )
                row.update(mondo_cols)
                writer.writerow(row)
    return stats


def print_stats(stats: Counter[str], file: TextIO | None = None) -> None:
    out = sys.stdout if file is None else file
    print(f"rows: {stats.get('total', 0)}", file=out)
    print(f"mapped: {stats.get('mapped', 0)}", file=out)
    print(f"failed: {stats.get('failed', 0)}", file=out)
    print("breakdown:", file=out)
    for key in sorted(k for k in stats if k not in {"total", "mapped", "failed"}):
        print(f"  {key}: {stats[key]}", file=out)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Append MONDO IDs and parent terms to image metadata TSV."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("patient_metadata_2026-05-23.tsv"),
        help="Input image metadata TSV (default: patient_metadata_2026-05-23.tsv)",
    )
    parser.add_argument(
        "--obo",
        type=Path,
        default=Path("mondo-international.obo.gz"),
        help="MONDO OBO file (.obo or .obo.gz)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("patient_metadata_2026-05-23_mondo.tsv"),
        help="Output TSV path",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if not args.input.is_file():
        print(f"Input not found: {args.input}", file=sys.stderr)
        return 1
    if not args.obo.is_file():
        print(f"OBO not found: {args.obo}", file=sys.stderr)
        return 1

    print(f"Parsing OBO: {args.obo}", file=sys.stderr)
    index = parse_obo(args.obo)
    print(
        f"  terms={len(index.mondo_name)} "
        f"omim_xrefs={sum(1 for k in index.omim_to_mondo if k.startswith('OMIM:'))} "
        f"omimps_xrefs={sum(1 for k in index.omim_to_mondo if k.startswith('OMIMPS:'))} "
        f"genes={len(index.gene_to_mondo)} "
        f"non_human_excluded={index.non_human_excluded}",
        file=sys.stderr,
    )

    print(f"Writing: {args.output}", file=sys.stderr)
    stats = process_tsv(args.input, args.output, index)
    print_stats(stats, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
