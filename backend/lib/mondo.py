"""Minimal MONDO OBO reader used to label and place gallery disorders in the ontology.

The gallery metadata only stores MONDO IDs, so names and the surrounding hierarchy
are resolved here at startup from the OBO release shipped in ``mondo/``.
"""

import gzip
import io
import re
from collections import Counter
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


def _ancestors(index: MondoIndex, mondo_id: str) -> Set[str]:
    """All is_a ancestors of ``mondo_id``, including the term itself."""
    seen = {mondo_id}
    stack = [mondo_id]
    while stack:
        for parent in index.get(stack.pop(), {}).get("parents", []):
            if parent not in seen:
                seen.add(parent)
                stack.append(parent)
    return seen


def _lowest_common_ancestors(index: MondoIndex, a: str, b: str) -> List[str]:
    """Common ancestors that are not an ancestor of another common ancestor."""
    common = _ancestors(index, a) & _ancestors(index, b)
    above = set()
    for term in common:
        above.update(_ancestors(index, term) - {term})
    return sorted(common - above)


def _path_lengths_up(index: MondoIndex, start: str, ancestor: str,
                     memo: Dict[str, Counter]) -> Counter:
    """Count the is_a paths from ``start`` up to ``ancestor`` by edge count.

    Paths are counted rather than listed, so heavy multiple inheritance cannot
    blow up memory. ``memo`` is keyed by term and is only valid for one ancestor.
    """
    if start in memo:
        return memo[start]
    lengths: Counter = Counter()
    if start == ancestor:
        lengths[0] = 1
    else:
        for parent in index.get(start, {}).get("parents", []):
            for length, count in _path_lengths_up(index, parent, ancestor, memo).items():
                lengths[length + 1] += count
    memo[start] = lengths
    return lengths


def mondo_distance(index: MondoIndex, a: str, b: str) -> Dict[str, Any]:
    """Edge counts of every is_a path joining ``a`` and ``b`` through their lowest common ancestors.

    Each path climbs from ``a`` to a lowest common ancestor and descends to ``b``;
    distinct paths of equal length are listed separately. When one term is an
    ancestor of the other, that ancestor is the only lowest common ancestor.
    ``distance`` is empty and ``minimum`` is ``None`` when the terms share no ancestor.
    """
    total: Counter = Counter()
    common_ancestors = []
    for ancestor in _lowest_common_ancestors(index, a, b):
        from_a = _path_lengths_up(index, a, ancestor, {})
        from_b = _path_lengths_up(index, b, ancestor, {})
        lengths: Counter = Counter()
        for length_a, count_a in from_a.items():
            for length_b, count_b in from_b.items():
                lengths[length_a + length_b] += count_a * count_b
        total.update(lengths)
        common_ancestors.append(dict(_term(index, ancestor), distance=sorted(lengths.elements())))

    distance = sorted(total.elements())
    return {
        "distance": distance,
        "minimum": distance[0] if distance else None,
        "common_ancestors": common_ancestors,
    }


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
