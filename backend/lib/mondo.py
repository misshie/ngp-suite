"""Minimal MONDO OBO reader used to label and place gallery disorders in the ontology.

The gallery metadata only stores MONDO IDs, so names and the surrounding hierarchy
are resolved here at startup from the OBO release shipped in ``data/``.
"""

import gzip
import io
from typing import Any, Dict, List, Optional

MondoIndex = Dict[str, Dict[str, Any]]


def _open_text(path: str) -> io.TextIOBase:
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return open(path, "r", encoding="utf-8")


def load_mondo_index(path: str) -> MondoIndex:
    """Parse an OBO file into ``{mondo_id: {"name": str, "parents": [mondo_id]}}``.

    Obsolete terms are dropped so that retired IDs cannot shadow their replacements.
    """
    index: MondoIndex = {}

    term_id: Optional[str] = None
    name = ""
    parents: List[str] = []
    obsolete = False
    in_term = False

    def flush() -> None:
        if in_term and term_id and not obsolete:
            index[term_id] = {"name": name, "parents": sorted(set(parents))}

    with _open_text(path) as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            if line.startswith("["):
                flush()
                in_term = line == "[Term]"
                term_id = None
                name = ""
                parents = []
                obsolete = False
            elif not in_term:
                continue
            elif line.startswith("id: "):
                if term_id is None:
                    term_id = line[4:].strip()
            elif line.startswith("name: "):
                name = line[6:].strip()
            elif line.startswith("is_a: "):
                # 'is_a: MONDO:0002254 {source="DOID:1928"} ! syndromic disease'
                fields = line[6:].split()
                if fields and fields[0].startswith("MONDO:"):
                    parents.append(fields[0])
            elif line.startswith("is_obsolete: true"):
                obsolete = True
        flush()

    return index


def _terms(index: MondoIndex, mondo_ids) -> List[Dict[str, str]]:
    return [
        {"id": mondo_id, "name": index[mondo_id]["name"] if mondo_id in index else ""}
        for mondo_id in sorted(mondo_ids)
    ]


def resolve(index: MondoIndex, mondo_id: str) -> Dict[str, Any]:
    """Return the label plus the two ancestor levels above ``mondo_id``.

    Grandparents exclude the term itself and its direct parents, which multiple
    inheritance would otherwise let reappear one level up.
    """
    entry = index.get(mondo_id)
    if entry is None:
        return {"name": "", "parents": [], "grandparents": []}

    parents = set(entry["parents"])
    grandparents = set()
    for parent in parents:
        grandparents.update(index.get(parent, {}).get("parents", []))
    grandparents.discard(mondo_id)
    grandparents -= parents

    return {
        "name": entry["name"],
        "parents": _terms(index, parents),
        "grandparents": _terms(index, grandparents),
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
                metadata_by_key[key] = {
                    "syndrome_name": (resolved["name"] if resolved else "") or row["disorder_name"],
                    "mondo_id": key if mondo_ids else None,
                    "mondo_parents": resolved["parents"] if resolved else [],
                    "mondo_grandparents": resolved["grandparents"] if resolved else [],
                    "omim_id": row["omim_id"],
                    "mondo_source": row.get("mondo_source") or None,
                }

        entries_by_image[image_id] = keys

    return entries_by_image, metadata_by_key
