#!/usr/bin/env python3
"""Build an NGPsuite-compatible metadata pickle from a MONDO-annotated TSV.

Reads patient_metadata_*_mondo.tsv (or similar), keeps Frontal face images that
have at least one of gene / disorder / MONDO, and writes a four-block pickle:

  gene_level_metadata, disorder_level_metadata, gene_metadata, disorder_metadata

PP4 threshold keys are intentionally omitted (NGPsuite treats missing keys as
"Not available yet"). Only mondo_id and mondo_source are stored from the MONDO
columns; parents and names are left for runtime OBO lookup.
"""

from __future__ import annotations

import argparse
import csv
import pickle
import sys
from collections import Counter
from pathlib import Path
from typing import Any, TextIO

from map_GMDBomim_to_mondo import OboIndex, parse_obo, primary_omim_value
from mondo_gene_resolution import (
    build_children,
    classify,
    sorted_symbols,
)

PP4_KEYS = ("very_strong", "strong", "moderate", "supporting")
MONDO_SOURCES = ("omim", "gene", "")
GENE_STATUSES = ("gmdb", "mondo", "gene_unresolved")
GENE_SOURCES = ("gmdb", "mondo")
REQUIRED_TOP = (
    "gene_level_metadata",
    "disorder_level_metadata",
    "gene_metadata",
    "disorder_metadata",
)
EMPTY_MARKERS = {"", '""', "[]"}
DEFAULT_OBO = Path("mondo-international.obo.gz")


def clean_cell(raw: str | None) -> str:
    if raw is None:
        return ""
    value = raw.strip()
    if value in EMPTY_MARKERS:
        return ""
    return value


def tokenize(raw: str) -> list[str]:
    cleaned = clean_cell(raw)
    if not cleaned:
        return []
    return [part.strip() for part in cleaned.replace(";", ",").split(",") if part.strip()]


def parse_mondo_ids(raw: str) -> list[str]:
    """Split a mondo_id cell into a sorted-unique-preserving list of IDs."""
    seen: set[str] = set()
    out: list[str] = []
    for part in tokenize(raw):
        if part not in seen:
            seen.add(part)
            out.append(part)
    return out


def mondo_group_key(mondo_ids: list[str]) -> tuple[str, ...]:
    return tuple(sorted(mondo_ids))


def resolve_omim_value(raw: str) -> int | str:
    """Return the representative bare OMIM integer for a cell, else ''."""
    return primary_omim_value(raw)


def load_rows(
    path: Path,
    image_type: str | None,
) -> tuple[list[dict[str, str]], Counter[str]]:
    stats: Counter[str] = Counter()
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise SystemExit(f"No header in {path}")
        required = {
            "image_id",
            "patient_id",
            "image_type",
            "gene_names",
            "gene_entrez_ids",
            "disorder_names",
            "omim_ids",
            "mondo_id",
        }
        missing = required - set(reader.fieldnames)
        if missing:
            raise SystemExit(f"Missing columns in {path}: {sorted(missing)}")

        for raw in reader:
            stats["tsv_rows"] += 1
            if image_type is not None and raw.get("image_type", "") != image_type:
                stats["excluded_image_type"] += 1
                continue

            gene_names = clean_cell(raw.get("gene_names"))
            disorder_names = clean_cell(raw.get("disorder_names"))
            mondo_ids = parse_mondo_ids(raw.get("mondo_id", ""))
            if not gene_names and not disorder_names and not mondo_ids:
                stats["excluded_no_diagnostic"] += 1
                continue

            genes = tokenize(gene_names)
            entrez = tokenize(clean_cell(raw.get("gene_entrez_ids")))
            if len(genes) != len(entrez):
                raise SystemExit(
                    f"gene_names/gene_entrez_ids length mismatch "
                    f"at image_id={raw.get('image_id')}: "
                    f"{len(genes)} vs {len(entrez)}"
                )

            rows.append(
                {
                    "image_id": raw["image_id"].strip(),
                    "patient_id": raw["patient_id"].strip(),
                    "gene_names": gene_names,
                    "gene_entrez_ids": clean_cell(raw.get("gene_entrez_ids")),
                    "disorder_names": disorder_names,
                    "omim_ids": clean_cell(raw.get("omim_ids")),
                    "mondo_id": raw.get("mondo_id", ""),
                    "mondo_disease": clean_cell(raw.get("mondo_disease")),
                    "mondo_source": clean_cell(raw.get("mondo_source")),
                }
            )
            stats["adopted"] += 1
            if mondo_ids:
                stats["with_mondo"] += 1
                stats[f"source_{clean_cell(raw.get('mondo_source')) or 'unset'}"] += 1
                if len(mondo_ids) > 1:
                    stats["multi_mondo"] += 1
            else:
                stats["without_mondo"] += 1
    return rows, stats


def assign_disorder_ids(
    rows: list[dict[str, str]],
) -> tuple[dict[int, int], dict[int, dict[str, Any]], Counter[str]]:
    """Return image_id -> disorder_internal_id and disorder_metadata."""
    key_to_id: dict[tuple[str, Any], int] = {}
    # Accumulator for representative fields per disorder id.
    accum: dict[int, dict[str, Any]] = {}
    image_to_did: dict[int, int] = {}
    kind_stats: Counter[str] = Counter()

    def get_or_create(kind: str, key: Any) -> int:
        full = (kind, key)
        if full not in key_to_id:
            did = len(key_to_id)
            key_to_id[full] = did
            accum[did] = {
                "kind": kind,
                "key": key,
                "disorder_names": Counter(),
                "mondo_disease": Counter(),
                "omim_values": Counter(),
                "mondo_source": Counter(),
                "mondo_ids": list(key) if kind == "mondo" else [],
            }
            kind_stats[kind] += 1
        return key_to_id[full]

    for row in rows:
        image_id = int(row["image_id"])
        mondo_ids = parse_mondo_ids(row["mondo_id"])
        disorder_names = row["disorder_names"]
        gene_names = row["gene_names"]

        if mondo_ids:
            did = get_or_create("mondo", mondo_group_key(mondo_ids))
        elif disorder_names:
            did = get_or_create("disorder_names", disorder_names)
        elif gene_names:
            did = get_or_create("gene_names", gene_names)
        else:
            # Should have been filtered earlier.
            raise RuntimeError(f"row without diagnostic info: image_id={image_id}")

        image_to_did[image_id] = did
        bucket = accum[did]
        if disorder_names:
            bucket["disorder_names"][disorder_names] += 1
        if row["mondo_disease"]:
            bucket["mondo_disease"][row["mondo_disease"]] += 1
        if row["mondo_source"]:
            bucket["mondo_source"][row["mondo_source"]] += 1
        omim_val = resolve_omim_value(row["omim_ids"])
        if omim_val != "":
            bucket["omim_values"][omim_val] += 1

    disorder_metadata: dict[int, dict[str, Any]] = {}
    for did, bucket in accum.items():
        kind = bucket["kind"]
        if kind == "mondo":
            if bucket["mondo_disease"]:
                name = bucket["mondo_disease"].most_common(1)[0][0]
                # Prefer the first label when multiple diseases were joined.
                name = name.split(",")[0].strip() if name else ""
            elif bucket["disorder_names"]:
                name = bucket["disorder_names"].most_common(1)[0][0]
            else:
                name = ", ".join(bucket["mondo_ids"] or [])
            mondo_ids = list(bucket["mondo_ids"] or [])
        elif kind == "disorder_names":
            name = str(bucket["key"])
            mondo_ids = []
        else:  # gene_names
            name = str(bucket["key"])
            mondo_ids = []

        if bucket["omim_values"]:
            omim_id: int | str = bucket["omim_values"].most_common(1)[0][0]
        else:
            omim_id = ""

        if bucket["mondo_source"]:
            mondo_source = bucket["mondo_source"].most_common(1)[0][0]
        else:
            mondo_source = ""

        disorder_metadata[did] = {
            "disorder_name": name,
            "omim_id": omim_id,
            "mondo_id": mondo_ids,
            "mondo_source": mondo_source,
            # PP4 keys intentionally absent.
        }

    return image_to_did, disorder_metadata, kind_stats


def pseudo_gene_label(row: dict[str, str]) -> str:
    """Disease-name fallback used when gene_names is empty (legacy / unresolved)."""
    if row["disorder_names"]:
        return row["disorder_names"]
    label = row["mondo_disease"] or (
        parse_mondo_ids(row["mondo_id"])[0]
        if parse_mondo_ids(row["mondo_id"])
        else "unknown"
    )
    return label.split(",")[0].strip()


def assign_gene_ids(
    rows: list[dict[str, str]],
    index: OboIndex | None = None,
) -> tuple[dict[str, int], dict[int, dict[str, Any]], list[dict[str, Any]], Counter[str]]:
    """Map gene_name -> gene_internal_id and build gene_metadata.

    When ``index`` is provided, empty-gene_names rows are classified via MONDO.
    Single-gene diseases and subtype_expanded candidates merge into real gene
    internal ids (one gene_level entry per candidate later).
    """
    name_to_id: dict[str, int] = {}
    gene_metadata: dict[int, dict[str, Any]] = {}
    report_rows: list[dict[str, Any]] = []
    class_stats: Counter[str] = Counter()
    children = build_children(index) if index is not None else {}

    def ensure(
        gene_name: str,
        *,
        entrez: str | None,
        status: str,
        hgnc_id: str | None = None,
    ) -> int:
        if gene_name not in name_to_id:
            gid = len(name_to_id)
            name_to_id[gene_name] = gid
            gene_metadata[gid] = {
                "gene_name": gene_name,
                "gene_entrez_id": entrez,
                "hgnc_id": hgnc_id,
                "gene_status": status,
            }
        else:
            gid = name_to_id[gene_name]
            meta = gene_metadata[gid]
            if meta["gene_entrez_id"] is None and entrez is not None:
                meta["gene_entrez_id"] = entrez
            if meta.get("hgnc_id") is None and hgnc_id is not None:
                meta["hgnc_id"] = hgnc_id
            # Prefer gmdb over mondo if both paths register the same symbol.
            if meta.get("gene_status") == "mondo" and status == "gmdb":
                meta["gene_status"] = "gmdb"
        return gid

    # Pass 1: real GMDB genes (so MONDO fill can merge into existing IDs).
    for row in rows:
        genes = tokenize(row["gene_names"])
        entrez_list = tokenize(row["gene_entrez_ids"])
        if genes:
            for gene, entrez in zip(genes, entrez_list):
                hgnc = None
                if index is not None:
                    hgnc = index.gene_hgnc.get(gene.upper())
                ensure(gene, entrez=entrez or None, status="gmdb", hgnc_id=hgnc)

    # Pass 2: empty gene_names → classify or legacy pseudo-gene.
    for row in rows:
        if tokenize(row["gene_names"]):
            continue
        label = pseudo_gene_label(row)
        mondo_ids = parse_mondo_ids(row["mondo_id"])

        if index is None:
            ensure(label, entrez=None, status="gene_unresolved")
            class_stats["legacy_unresolved"] += 1
            continue

        status, symbols = classify(index, children, mondo_ids)
        class_stats[status] += 1
        resolved_gene = ""
        candidate_list: list[str] = []

        if status == "mondo":
            symbol = next(iter(symbols))
            resolved_gene = symbol
            ensure(
                symbol,
                entrez=None,
                status="mondo",
                hgnc_id=index.gene_hgnc.get(symbol.upper()),
            )
        elif status == "subtype_expanded":
            candidate_list = sorted_symbols(symbols)
            for symbol in candidate_list:
                ensure(
                    symbol,
                    entrez=None,
                    status="mondo",
                    hgnc_id=index.gene_hgnc.get(symbol.upper()),
                )
        else:
            ensure(label, entrez=None, status="gene_unresolved")

        report_rows.append(
            {
                "image_id": row["image_id"],
                "patient_id": row["patient_id"],
                "disorder_names": row["disorder_names"],
                "omim_ids": row["omim_ids"],
                "mondo_id": row["mondo_id"],
                "mondo_disease": row["mondo_disease"],
                "classification": status,
                "resolved_gene": resolved_gene,
                "hgnc_id": (
                    index.gene_hgnc.get(resolved_gene.upper()) if resolved_gene else ""
                ),
                "subtype_candidates": ";".join(candidate_list),
            }
        )

    return name_to_id, gene_metadata, report_rows, class_stats


def build_gene_level(
    rows: list[dict[str, str]],
    name_to_gid: dict[str, int],
    gene_metadata: dict[int, dict[str, Any]],
    index: OboIndex | None = None,
) -> dict[int, list[dict[str, Any]]]:
    out: dict[int, list[dict[str, Any]]] = {}
    children = build_children(index) if index is not None else {}

    for row in rows:
        image_id = int(row["image_id"])
        patient_id = int(row["patient_id"])
        genes = tokenize(row["gene_names"])
        entrez_list = tokenize(row["gene_entrez_ids"])
        entries: list[dict[str, Any]] = []

        if genes:
            seen_genes: set[str] = set()
            for gene, entrez in zip(genes, entrez_list):
                if gene in seen_genes:
                    continue
                seen_genes.add(gene)
                entries.append(
                    {
                        "image_id": image_id,
                        "patient_id": patient_id,
                        "gene_internal_id": name_to_gid[gene],
                        "gene_name": gene,
                        "gene_entrez_id": entrez or None,
                        "disorder_names": row["disorder_names"],
                        "omim_ids": row["omim_ids"],
                        "gene_source": "gmdb",
                    }
                )
        else:
            label = pseudo_gene_label(row)
            symbols_to_emit: list[tuple[str, str]] = []  # (gene_name, gene_source)
            if index is not None:
                status, symbols = classify(
                    index, children, parse_mondo_ids(row["mondo_id"])
                )
                if status == "mondo":
                    symbols_to_emit = [(next(iter(symbols)), "mondo")]
                elif status == "subtype_expanded":
                    symbols_to_emit = [
                        (symbol, "mondo") for symbol in sorted_symbols(symbols)
                    ]
                else:
                    symbols_to_emit = [(label, "gmdb")]
            else:
                symbols_to_emit = [(label, "gmdb")]

            for gene_name, gene_source in symbols_to_emit:
                gid = name_to_gid[gene_name]
                meta = gene_metadata[gid]
                entries.append(
                    {
                        "image_id": image_id,
                        "patient_id": patient_id,
                        "gene_internal_id": gid,
                        "gene_name": meta["gene_name"],
                        "gene_entrez_id": meta.get("gene_entrez_id"),
                        "disorder_names": row["disorder_names"],
                        "omim_ids": row["omim_ids"],
                        "gene_source": gene_source,
                    }
                )

        if not entries:
            raise RuntimeError(f"empty gene_level list for image_id={image_id}")
        out[image_id] = entries
    return out


def build_disorder_level(
    rows: list[dict[str, str]],
    image_to_did: dict[int, int],
    disorder_metadata: dict[int, dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for row in rows:
        image_id = int(row["image_id"])
        patient_id = int(row["patient_id"])
        did = image_to_did[image_id]
        meta = disorder_metadata[did]
        mondo_ids = parse_mondo_ids(row["mondo_id"])
        # Per-image omim: resolve this row; fall back to group representative.
        omim_id = resolve_omim_value(row["omim_ids"])
        if omim_id == "":
            omim_id = meta["omim_id"]

        out[image_id] = {
            "image_id": image_id,
            "patient_id": patient_id,
            "gene_names": row["gene_names"],
            "gene_entrez_ids": row["gene_entrez_ids"],
            "disorder_name": meta["disorder_name"],
            "omim_id": omim_id,
            "disorder_internal_id": did,
            "mondo_id": mondo_ids,
            "mondo_source": row["mondo_source"],
        }
    return out


def build_pickle(
    rows: list[dict[str, str]],
    index: OboIndex | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    image_to_did, disorder_metadata, kind_stats = assign_disorder_ids(rows)
    name_to_gid, gene_metadata, report_rows, class_stats = assign_gene_ids(rows, index)
    gene_level = build_gene_level(rows, name_to_gid, gene_metadata, index)
    disorder_level = build_disorder_level(rows, image_to_did, disorder_metadata)
    return {
        "gene_level_metadata": gene_level,
        "disorder_level_metadata": disorder_level,
        "gene_metadata": gene_metadata,
        "disorder_metadata": disorder_metadata,
        "_stats": {
            "disorder_id_kinds": dict(kind_stats),
            "n_genes": len(gene_metadata),
            "n_disorders": len(disorder_metadata),
            "gene_resolution": dict(class_stats),
        },
    }, report_rows


def validate_pickle(data: dict[str, Any], file: TextIO = sys.stderr) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED_TOP:
        if key not in data:
            errors.append(f"missing top-level key: {key}")
    if errors:
        return errors

    glm = data["gene_level_metadata"]
    dlm = data["disorder_level_metadata"]
    gm = data["gene_metadata"]
    dm = data["disorder_metadata"]

    if set(glm.keys()) != set(dlm.keys()):
        only_g = set(glm) - set(dlm)
        only_d = set(dlm) - set(glm)
        errors.append(
            f"image_id mismatch gene_level vs disorder_level: "
            f"only_gene={len(only_g)} only_disorder={len(only_d)}"
        )

    for image_id, entries in glm.items():
        if not isinstance(entries, list) or not entries:
            errors.append(f"gene_level[{image_id}] is empty or not a list")
            continue
        seen_gids: set[Any] = set()
        for entry in entries:
            gid = entry.get("gene_internal_id")
            if gid not in gm:
                errors.append(f"gene_internal_id {gid} missing from gene_metadata")
            if gid in seen_gids:
                errors.append(f"gene_level[{image_id}] duplicate gene_internal_id {gid}")
            seen_gids.add(gid)
            if not isinstance(entry.get("patient_id"), int):
                errors.append(f"gene_level[{image_id}] patient_id not int")
            source = entry.get("gene_source")
            if source is not None and source not in GENE_SOURCES:
                errors.append(f"gene_level[{image_id}] bad gene_source {source!r}")
            elif source == "mondo":
                status = gm.get(gid, {}).get("gene_status")
                if status not in ("gmdb", "mondo"):
                    errors.append(
                        f"gene_level[{image_id}] gene_source=mondo but "
                        f"gene_status={status!r}"
                    )

    for image_id, row in dlm.items():
        did = row.get("disorder_internal_id")
        if did not in dm:
            errors.append(f"disorder_internal_id {did} missing from disorder_metadata")
        if not isinstance(row.get("patient_id"), int):
            errors.append(f"disorder_level[{image_id}] patient_id not int")
        mondo = row.get("mondo_id")
        if not isinstance(mondo, list):
            errors.append(
                f"disorder_level[{image_id}] mondo_id is {type(mondo).__name__}, expected list"
            )
        elif any(not isinstance(x, str) for x in mondo):
            errors.append(f"disorder_level[{image_id}] mondo_id has non-str elements")
        source = row.get("mondo_source")
        if source not in MONDO_SOURCES:
            errors.append(f"disorder_level[{image_id}] bad mondo_source {source!r}")
        elif bool(mondo) != bool(source):
            errors.append(
                f"disorder_level[{image_id}] mondo_id/mondo_source disagree: "
                f"{len(mondo or [])} id(s), source {source!r}"
            )

    for did, meta in dm.items():
        for pp4 in PP4_KEYS:
            if pp4 in meta:
                errors.append(f"disorder_metadata[{did}] has forbidden PP4 key {pp4!r}")
        mondo = meta.get("mondo_id")
        if not isinstance(mondo, list):
            errors.append(
                f"disorder_metadata[{did}] mondo_id is {type(mondo).__name__}, expected list"
            )
        if meta.get("mondo_source") not in MONDO_SOURCES:
            errors.append(
                f"disorder_metadata[{did}] bad mondo_source {meta.get('mondo_source')!r}"
            )

    for gid, meta in gm.items():
        status = meta.get("gene_status")
        if status is not None and status not in GENE_STATUSES:
            errors.append(f"gene_metadata[{gid}] bad gene_status {status!r}")
        if "subtype_candidates" in meta:
            errors.append(f"gene_metadata[{gid}] has forbidden subtype_candidates")
        if status == "gmdb" and not meta.get("gene_entrez_id"):
            errors.append(f"gene_metadata[{gid}] gmdb gene missing gene_entrez_id")

    if errors:
        print(f"VALIDATE FAIL: {len(errors)} issue(s)", file=file)
        for err in errors[:30]:
            print(f"  - {err}", file=file)
        if len(errors) > 30:
            print(f"  ... and {len(errors) - 30} more", file=file)
    else:
        print(
            f"VALIDATE OK: images={len(dlm)} genes={len(gm)} disorders={len(dm)}",
            file=file,
        )
    return errors


def compare_pickles(
    new_data: dict[str, Any],
    old_path: Path,
    file: TextIO = sys.stderr,
) -> None:
    with old_path.open("rb") as handle:
        old = pickle.load(handle)
    new_dlm = new_data["disorder_level_metadata"]
    old_dlm = old["disorder_level_metadata"]
    new_dm = new_data["disorder_metadata"]
    old_dm = old["disorder_metadata"]

    new_ids = set(new_dlm)
    old_ids = set(old_dlm)
    print(f"COMPARE vs {old_path}", file=file)
    print(f"  images: new={len(new_ids)} old={len(old_ids)}", file=file)
    print(
        f"  intersection={len(new_ids & old_ids)} "
        f"only_new={len(new_ids - old_ids)} only_old={len(old_ids - new_ids)}",
        file=file,
    )
    print(
        f"  disorders: new={len(new_dm)} old={len(old_dm)}",
        file=file,
    )
    print(
        f"  genes: new={len(new_data['gene_metadata'])} "
        f"old={len(old['gene_metadata'])}",
        file=file,
    )
    new_status = Counter(
        m.get("gene_status") or "unset" for m in new_data["gene_metadata"].values()
    )
    if new_status:
        print(f"  new gene_status counts: {dict(new_status)}", file=file)
    new_mondo_src = sum(
        1
        for entries in new_data["gene_level_metadata"].values()
        for e in entries
        if e.get("gene_source") == "mondo"
    )
    print(f"  new gene_level entries with gene_source=mondo: {new_mondo_src}", file=file)
    new_entry_counts = [len(v) for v in new_data["gene_level_metadata"].values()]
    print(
        f"  new gene_level entries total={sum(new_entry_counts)} "
        f"max_per_image={max(new_entry_counts) if new_entry_counts else 0}",
        file=file,
    )

    shared = new_ids & old_ids
    name_agree = 0
    for iid in shared:
        if new_dlm[iid]["disorder_name"] == old_dlm[iid]["disorder_name"]:
            name_agree += 1
    if shared:
        print(
            f"  disorder_name agree on shared images: "
            f"{name_agree}/{len(shared)} ({100 * name_agree / len(shared):.1f}%)",
            file=file,
        )

    new_with_mondo = sum(1 for r in new_dlm.values() if r["mondo_id"])
    print(
        f"  new images with non-empty mondo_id: "
        f"{new_with_mondo}/{len(new_dlm)} ({100 * new_with_mondo / len(new_dlm):.1f}%)",
        file=file,
    )

    old_pp4 = sum(
        1 for m in old_dm.values() if any(k in m for k in PP4_KEYS)
    )
    new_pp4 = sum(
        1 for m in new_dm.values() if any(k in m for k in PP4_KEYS)
    )
    print(f"  disorder_metadata with any PP4 key: new={new_pp4} old={old_pp4}", file=file)


def print_build_stats(
    load_stats: Counter[str],
    data: dict[str, Any],
    file: TextIO = sys.stderr,
) -> None:
    internal = data.pop("_stats", {})
    print("BUILD STATS", file=file)
    print(f"  tsv_rows: {load_stats.get('tsv_rows', 0)}", file=file)
    print(f"  excluded_image_type: {load_stats.get('excluded_image_type', 0)}", file=file)
    print(
        f"  excluded_no_diagnostic: {load_stats.get('excluded_no_diagnostic', 0)}",
        file=file,
    )
    print(f"  adopted: {load_stats.get('adopted', 0)}", file=file)
    print(
        f"  with_mondo: {load_stats.get('with_mondo', 0)} "
        f"without_mondo: {load_stats.get('without_mondo', 0)}",
        file=file,
    )
    print(
        f"  mondo_source omim: {load_stats.get('source_omim', 0)} "
        f"gene: {load_stats.get('source_gene', 0)}",
        file=file,
    )
    print(f"  images with >1 mondo_id: {load_stats.get('multi_mondo', 0)}", file=file)
    print(f"  genes: {internal.get('n_genes', len(data['gene_metadata']))}", file=file)
    print(
        f"  disorders: {internal.get('n_disorders', len(data['disorder_metadata']))}",
        file=file,
    )
    kinds = internal.get("disorder_id_kinds", {})
    if kinds:
        print(f"  disorder_id_kinds: {kinds}", file=file)
    resolution = internal.get("gene_resolution", {})
    if resolution:
        print(f"  gene_resolution: {resolution}", file=file)


def write_resolution_report(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "image_id",
        "patient_id",
        "disorder_names",
        "omim_ids",
        "mondo_id",
        "mondo_disease",
        "classification",
        "resolved_gene",
        "hgnc_id",
        "subtype_candidates",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def default_output_path(input_path: Path) -> Path:
    name = input_path.name
    if name.endswith(".tsv"):
        return input_path.with_name(name[:-4] + ".p")
    return input_path.with_suffix(".p")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build NGPsuite metadata pickle from MONDO-annotated TSV."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("patient_metadata_2026-05-23_mondo.tsv"),
        help="Input TSV (default: patient_metadata_2026-05-23_mondo.tsv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output pickle path (default: input with .tsv -> .p)",
    )
    parser.add_argument(
        "--obo",
        type=Path,
        default=DEFAULT_OBO,
        help=f"MONDO OBO for gene resolution (default: {DEFAULT_OBO})",
    )
    parser.add_argument(
        "--no-gene-resolution",
        action="store_true",
        help="Skip MONDO gene resolution (legacy pseudo-gene behaviour)",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Write CSV report for empty-gene_names classifications",
    )
    parser.add_argument(
        "--image-type",
        default="Frontal face",
        help="Keep only this image_type; use 'all' to keep every row "
        "(default: 'Frontal face')",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate the written pickle against NGPsuite invariants",
    )
    parser.add_argument(
        "--compare",
        type=Path,
        default=None,
        help="Optional existing pickle to compare against after build",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if not args.input.is_file():
        print(f"Input not found: {args.input}", file=sys.stderr)
        return 1

    image_type = None if args.image_type == "all" else args.image_type
    output = args.output or default_output_path(args.input)

    index: OboIndex | None = None
    if not args.no_gene_resolution:
        if not args.obo.is_file():
            print(f"OBO not found: {args.obo}", file=sys.stderr)
            return 1
        print(f"Loading OBO: {args.obo}", file=sys.stderr)
        index = parse_obo(args.obo)
        print(
            f"  terms={len(index.mondo_name)} "
            f"causal_gene_terms={len(index.mondo_causal_genes)} "
            f"gene_hgnc={len(index.gene_hgnc)} "
            f"non_human_excluded={index.non_human_excluded}",
            file=sys.stderr,
        )
    else:
        print("Gene resolution disabled (--no-gene-resolution)", file=sys.stderr)

    print(f"Reading: {args.input}", file=sys.stderr)
    rows, load_stats = load_rows(args.input, image_type)
    print(f"Building pickle from {len(rows)} images...", file=sys.stderr)
    data, report_rows = build_pickle(rows, index)
    print_build_stats(load_stats, data)

    # Strip internal stats before serializing (already popped in print_build_stats
    # if called; ensure clean payload).
    data.pop("_stats", None)

    print(f"Writing: {output}", file=sys.stderr)
    with output.open("wb") as handle:
        pickle.dump(data, handle, protocol=4)

    if args.report is not None:
        write_resolution_report(args.report, report_rows)
        print(
            f"Wrote gene-resolution report: {args.report} ({len(report_rows)} rows)",
            file=sys.stderr,
        )

    if args.validate:
        errors = validate_pickle(data)
        if errors:
            return 1

    if args.compare is not None:
        if not args.compare.is_file():
            print(f"Compare target not found: {args.compare}", file=sys.stderr)
            return 1
        compare_pickles(data, args.compare)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
