"""Minimal MONDO OBO reader used to label and place gallery disorders in the ontology.

The gallery metadata only stores MONDO IDs, so names and the surrounding hierarchy
are resolved here at startup from the OBO release shipped in ``mondo/``.
"""

import gzip
import io
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple

MondoIndex = Dict[str, Dict[str, Any]]

SYN_RE = re.compile(r'^synonym: "([^"]+)"(.*)$')
LANG_RE = re.compile(r'language="([a-zA-Z-]+)"')
# MONDO international stores translations as: property_value: skos:altLabel "ウィリアムズ症候群@ja" xsd:string
ALT_LABEL_RE = re.compile(r'^property_value: skos:altLabel "(.+)@([a-zA-Z-]+)"')
VERSION_INFO_RE = re.compile(r'^property_value: owl:versionInfo "([^"]+)"')
NANDO_XREF_RE = re.compile(r'^xref: (NANDO:\d+)')
OMIM_XREF_RE = re.compile(r'^xref: OMIM:(\d+)(.*)$')


def _open_text(path: str) -> io.TextIOBase:
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return open(path, "r", encoding="utf-8")


def _pick_label(candidates: List[Tuple[bool, str]]) -> str:
    """Prefer the first EXACT synonym, otherwise the first synonym of that language."""
    for exact, text in candidates:
        if exact:
            return text
    return candidates[0][1]


def load_mondo_index(path: str) -> Tuple[MondoIndex, Optional[str]]:
    """Parse an OBO file into ``{mondo_id: {"name", "labels", "parents"}}``.

    Obsolete terms are dropped so that retired IDs cannot shadow their replacements.
    ``labels`` maps ISO 639 language codes (``en``, ``ja``, …) onto display names.

    Returns:
        ``(index, version)`` where ``version`` is the OBO header
        ``owl:versionInfo`` value (e.g. ``2026-07-06``), or ``None`` if absent.
    """
    index: MondoIndex = {}
    version: Optional[str] = None

    term_id: Optional[str] = None
    name = ""
    parents: List[str] = []
    nando_ids: List[str] = []
    omim_ids: List[str] = []
    # language -> [(is_exact, text), ...]
    synonyms: Dict[str, List[Tuple[bool, str]]] = {}
    obsolete = False
    in_term = False

    def flush() -> None:
        if not in_term or not term_id or obsolete:
            return
        labels: Dict[str, str] = {}
        if name:
            labels["en"] = name
        for lang, candidates in synonyms.items():
            if lang == "en" and "en" in labels:
                continue
            labels[lang] = _pick_label(candidates)
        index[term_id] = {
            "name": name,
            "labels": labels,
            "parents": sorted(set(parents)),
            "nando_ids": sorted(set(nando_ids)),
            "omim_ids": sorted(set(omim_ids)),
        }

    with _open_text(path) as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            if line.startswith("["):
                flush()
                in_term = line == "[Term]"
                term_id = None
                name = ""
                parents = []
                nando_ids = []
                omim_ids = []
                synonyms = {}
                obsolete = False
            elif not in_term:
                match = VERSION_INFO_RE.match(line)
                if match and version is None:
                    version = match.group(1)
            elif line.startswith("id: "):
                if term_id is None:
                    term_id = line[4:].strip()
            elif line.startswith("name: "):
                name = line[6:].strip()
            elif line.startswith("synonym: "):
                match = SYN_RE.match(line)
                if not match:
                    continue
                text, rest = match.group(1), match.group(2)
                lang_match = LANG_RE.search(rest)
                if not lang_match:
                    continue
                lang = lang_match.group(1).lower()
                synonyms.setdefault(lang, []).append(("EXACT" in rest, text))
            elif line.startswith("property_value: skos:altLabel "):
                match = ALT_LABEL_RE.match(line)
                if not match:
                    continue
                text, lang = match.group(1), match.group(2).lower()
                synonyms.setdefault(lang, []).append((False, text))
            elif line.startswith("xref: NANDO:"):
                match = NANDO_XREF_RE.match(line)
                if match:
                    nando_ids.append(match.group(1))
            elif line.startswith("xref: OMIM:"):
                match = OMIM_XREF_RE.match(line)
                if match and "MONDO:equivalentTo" in match.group(2):
                    omim_ids.append(match.group(1))
            elif line.startswith("is_a: "):
                # 'is_a: MONDO:0002254 {source="DOID:1928"} ! syndromic disease'
                fields = line[6:].split()
                if fields and fields[0].startswith("MONDO:"):
                    parents.append(fields[0])
            elif line.startswith("is_obsolete: true"):
                obsolete = True
        flush()

    return index, version


def build_nando_map(index: MondoIndex) -> Dict[str, str]:
    """MONDO ID -> smallest NANDO xref (lexicographic min of NANDO:…)."""
    return {
        mondo_id: min(entry["nando_ids"])
        for mondo_id, entry in index.items()
        if entry.get("nando_ids")
    }


def build_omim_map(index: MondoIndex) -> Dict[str, str]:
    """MONDO ID -> smallest equivalent OMIM entry number."""
    return {
        mondo_id: min(entry["omim_ids"])
        for mondo_id, entry in index.items()
        if entry.get("omim_ids")
    }


def _term(index: MondoIndex, mondo_id: str) -> Dict[str, Any]:
    entry = index.get(mondo_id)
    name = entry["name"] if entry else ""
    labels = dict(entry["labels"]) if entry else {}
    if name and "en" not in labels:
        labels["en"] = name
    return {"id": mondo_id, "name": name, "labels": labels}


def _terms(index: MondoIndex, mondo_ids) -> List[Dict[str, Any]]:
    return [_term(index, mondo_id) for mondo_id in sorted(mondo_ids)]


def resolve(index: MondoIndex, mondo_id: str) -> Dict[str, Any]:
    """Return the label plus the two ancestor levels above ``mondo_id``.

    Grandparents exclude the term itself and its direct parents, which multiple
    inheritance would otherwise let reappear one level up.
    """
    entry = index.get(mondo_id)
    if entry is None:
        return {"name": "", "labels": {}, "parents": [], "grandparents": []}

    parents = set(entry["parents"])
    grandparents = set()
    for parent in parents:
        grandparents.update(index.get(parent, {}).get("parents", []))
    grandparents.discard(mondo_id)
    grandparents -= parents

    return {
        "name": entry["name"],
        "labels": dict(entry.get("labels") or {}),
        "parents": _terms(index, parents),
        "grandparents": _terms(index, grandparents),
    }


def _hops_up(index: MondoIndex, mondo_id: str) -> Dict[str, int]:
    """Shortest is_a edge count from ``mondo_id`` to each ancestor, the term itself at 0."""
    hops = {mondo_id: 0}
    frontier = [mondo_id]
    while frontier:
        next_frontier = []
        for term in frontier:
            for parent in index.get(term, {}).get("parents", []):
                if parent not in hops:
                    hops[parent] = hops[term] + 1
                    next_frontier.append(parent)
        frontier = next_frontier
    return hops


def _lowest_common_ancestors(index: MondoIndex, common: Set[str]) -> List[str]:
    """Common ancestors that are not an ancestor of another common ancestor."""
    above = set()
    for term in common:
        above.update(set(_hops_up(index, term)) - {term})
    return sorted(common - above)


DEFAULT_IC_ROOT = "MONDO:0700096"  # human disease
IC_METHODS = ("seco", "descendants")

IcTable = Dict[str, Any]


def build_ic_table(index: MondoIndex, root: str = DEFAULT_IC_ROOT) -> IcTable:
    """Count the is_a descendants of every term under ``root`` (the root included).

    Only terms under ``root`` and the is_a edges between them are used, so the
    counts do not depend on the rest of MONDO. Descendant sets are int bitsets
    so that shared subtrees under multiple inheritance are counted once.

    Returns:
        ``{"root", "n_terms", "descendants": {mondo_id: count}}`` where a count
        excludes the term itself.
    """
    children: Dict[str, List[str]] = {}
    for mondo_id, entry in index.items():
        for parent in entry["parents"]:
            children.setdefault(parent, []).append(mondo_id)

    scope = {root}
    stack = [root]
    while stack:
        for child in children.get(stack.pop(), []):
            if child not in scope:
                scope.add(child)
                stack.append(child)

    bit = {mondo_id: 1 << i for i, mondo_id in enumerate(sorted(scope))}
    below: Dict[str, int] = {}
    # Iterative post-order: a term's set is the union of its children and their sets.
    for start in scope:
        stack = [(start, False)]
        while stack:
            term, expanded = stack.pop()
            if term in below:
                continue
            if expanded:
                bits = 0
                for child in children.get(term, []):
                    bits |= bit[child] | below[child]
                below[term] = bits
            else:
                stack.append((term, True))
                stack.extend((child, False) for child in children.get(term, []) if child not in below)

    return {
        "root": root,
        "n_terms": len(scope),
        "descendants": {mondo_id: bin(bits).count("1") for mondo_id, bits in below.items()},
    }


def information_content(table: IcTable, mondo_id: str, method: str = "seco") -> Optional[float]:
    """Intrinsic IC of ``mondo_id``, or ``None`` outside the table's scope.

    ``seco``: ``1 - ln(desc + 1) / ln(N)``, 0 at the root and 1 at a leaf.
    ``descendants``: ``-ln((desc + 1) / N)``, 0 at the root and ``ln N`` at a leaf.
    """
    desc = table["descendants"].get(mondo_id)
    if desc is None:
        return None
    n = table["n_terms"]
    if method == "seco":
        return 1.0 - math.log(desc + 1) / math.log(n) if n > 1 else 0.0
    if method == "descendants":
        # max() keeps the root at 0.0 rather than -0.0.
        return max(0.0, -math.log((desc + 1) / n))
    raise ValueError("Unknown IC method: {}".format(method))


def mondo_similarity(index: MondoIndex, table: IcTable, a: str, b: str,
                     method: str = "seco") -> Dict[str, Any]:
    """Compare ``a`` and ``b`` by intrinsic IC and by is_a hops to their MICA.

    Common ancestors are the intersection of the two ancestor sets, each including
    the term itself, so when one term is an ancestor of the other it is the MICA.
    ``hops`` is ``[from a, from b]``, the shortest is_a edge counts to that ancestor.
    ``common_ancestors`` lists the lowest common ancestors (ID order) with their IC
    and hops; the MICA is always one of them because IC falls towards the root.
    ``mica_ties`` lists every common ancestor sharing the highest IC (ID order) and
    ``mica`` is its first item. Lin is 1 for the same term and ``None`` when
    ``IC(a) + IC(b)`` is 0. ``mica``, ``resnik`` and ``lin`` are ``None`` when
    either term is outside the table's scope.
    """
    hops_a = _hops_up(index, a)
    hops_b = _hops_up(index, b)
    common = set(hops_a) & set(hops_b)

    def describe(term: str) -> Dict[str, Any]:
        return dict(_term(index, term), ic=information_content(table, term, method),
                    hops=[hops_a[term], hops_b[term]])

    result: Dict[str, Any] = {
        "common_ancestors": [describe(term) for term in _lowest_common_ancestors(index, common)],
        "mica": None,
        "mica_ties": [],
        "resnik": None,
        "lin": None,
    }
    ic_a = information_content(table, a, method)
    ic_b = information_content(table, b, method)
    if ic_a is None or ic_b is None:
        return result

    scored = [describe(term) for term in sorted(common) if term in table["descendants"]]
    resnik = max(item["ic"] for item in scored)
    ties = [item for item in scored if item["ic"] == resnik]

    if a == b:
        lin: Optional[float] = 1.0
    elif ic_a + ic_b > 0:
        lin = 2 * resnik / (ic_a + ic_b)
    else:
        lin = None
    result.update(mica=ties[0], mica_ties=ties, resnik=resnik, lin=lin)
    return result


def build_syndrome_index(metadata, mondo_index: MondoIndex):
    """Expand the gallery into MONDO-keyed syndrome candidates.

    Returns ``(entries_by_image, metadata_by_key)``. An image with several MONDO
    IDs — which happens when the disorder was resolved through a gene symbol —
    contributes one candidate per ID, so the same face can support more than one
    syndrome at the same gestalt distance. Images MONDO could not place keep a
    ``GMDB:<disorder_internal_id>`` key so they stay in the ranking under their
    GMDB name.
    """
    entries_by_image: Dict[int, List[str]] = {}
    metadata_by_key: Dict[str, Dict[str, Any]] = {}

    for image_id, row in metadata["disorder_level_metadata"].items():
        mondo_ids = sorted(row.get("mondo_id") or [])
        keys = mondo_ids if mondo_ids else ["GMDB:{}".format(row["disorder_internal_id"])]

        for key in keys:
            if key not in metadata_by_key:
                resolved = resolve(mondo_index, key) if mondo_ids else None
                english = (resolved["name"] if resolved else "") or row["disorder_name"]
                labels = dict(resolved["labels"]) if resolved else {}
                if english:
                    labels.setdefault("en", english)
                metadata_by_key[key] = {
                    "syndrome_name": english,
                    "syndrome_labels": labels,
                    "mondo_id": key if mondo_ids else None,
                    "mondo_parents": resolved["parents"] if resolved else [],
                    "mondo_grandparents": resolved["grandparents"] if resolved else [],
                    "omim_id": row["omim_id"],
                    "mondo_source": row.get("mondo_source") or None,
                }

        entries_by_image[image_id] = keys

    return entries_by_image, metadata_by_key
