# GMDB-MONDO: Mapping GMDB Image Metadata to MONDO Disease Terms

*Japanese version: [README-ja.md](README-ja.md)*

## About this directory

This directory publishes the scripts that build NGPsuite's gallery metadata pickle (`patient_metadata_*_mondo.p`) from a GMDB metadata export. In practice the intended users are the GMDB maintainers, who have access to the GMDB metadata. NGPsuite users do not need to run these scripts; they receive the finished pickle together with the other GMDB files.

The scripts are maintained in a separate, private repository and copied here as a snapshot. The snapshot is updated manually when the pipeline changes.

**No data is included.** The GMDB metadata and everything derived from it may contain personal information and must be obtained under the GMDB data use conditions. `.gitignore` in this directory excludes `*.p`, `*.tsv`, `*.csv`, `*.err.txt` and ontology files so they are not committed by accident.

### Quick start

Stage 1 mounts the current directory into a Docker container, so run all stages from one working directory that holds the scripts and the data. Keep it outside the repository.

```sh
mkdir -p ~/gmdb-mondo-work
cp tools/gmdb-mondo/*.sh tools/gmdb-mondo/*.py tools/gmdb-mondo/*.ru ~/gmdb-mondo-work/
cp backend/mondo/mondo-international.obo.gz ~/gmdb-mondo-work/   # or run Stage 1 instead
cp /path/to/patient_metadata_2026-05-23.tsv ~/gmdb-mondo-work/    # GMDB export
cd ~/gmdb-mondo-work
python3 020_map_GMDBomim_to_mondo.py 2> patient_metadata_2026-05-23_mondo.err.txt
python3 030_build_metadata_pickle.py --validate
cp patient_metadata_2026-05-23_mondo.p "$NGPSUITE_GMDB_DIR/data/"
```

`$NGPSUITE_GMDB_DIR` is the GMDB data directory that NGPsuite mounts at run time (see [`backend/.env.example`](../../backend/.env.example) and the main [README](../../README.md)). After replacing the pickle, run `docker compose restart api` in `backend/`.

Stage 1 is needed only when updating MONDO. Otherwise use the OBO bundled with NGPsuite (`backend/mondo/mondo-international.obo.gz`), so that the pickle and the runtime ontology come from the same MONDO release.

## Overview

This pipeline annotates GestaltMatcher Database (GMDB) image metadata with [MONDO](https://mondo.monarchinitiative.org/) disease terms. Each GMDB record carries OMIM identifiers and/or gene symbols; the pipeline resolves them to a MONDO term and adds the term's parent and grandparent classes so that records can be grouped at coarser levels of the disease hierarchy.

The pipeline has three stages:

1. Convert the MONDO international edition from OWL to OBO format (`010_run-docker-robot-owl2obo.sh` with `preprocess_labels_for_obo.ru`).
2. Map OMIM IDs and gene symbols in the metadata TSV to MONDO terms (`020_map_GMDBomim_to_mondo.py`, a thin wrapper around `map_GMDBomim_to_mondo.py`).
3. Build an NGPsuite-compatible metadata pickle that includes `mondo_id` (`030_build_metadata_pickle.py`).

Stages 2 and 3 read `mondo-international.obo.gz` produced by Stage 1.

Ontology products are exchanged as gzip (`.owl.gz` / `.obo.gz`). ROBOT cannot reliably read gzipped inputs, so the shell wrapper decompresses to a temporary file under the working directory, then asks ROBOT to write gzipped OBO output directly.

**Note on numbered Python entry points:** Python cannot `import` a module whose name starts with a digit. `020_…` is only a wrapper that calls `map_GMDBomim_to_mondo.main`; keep the unnumbered body file as the importable library (`010` = Stage 1, `020` = Stage 2, `030` = Stage 3).

## Data sources

### MONDO international edition

`mondo-international.owl` / `mondo-international.owl.gz` was obtained from the MONDO download page, <https://mondo.monarchinitiative.org/pages/download/> (retrieved **2026-09-18**; MONDO release **2026-09-01**), via the PURL <https://purl.obolibrary.org/obo/mondo/mondo-international.owl>.

The international edition is equivalent to the main OWL edition but additionally carries community-curated language translations (the Japanese translation is led by Toyofumi Fujiwara and Terue Takatsuki at the Database Center for Life Science, DBCLS). MONDO is distributed under CC BY 4.0.

The OWL is not included here (~15 MB gzipped, ~271 MB uncompressed). Download it from the PURL above and gzip it as `mondo-international.owl.gz` if you run Stage 1.

### GMDB image metadata

`patient_metadata_2026-05-23.tsv` is the GMDB patient/image metadata export used for the current NGPsuite gallery (28,499 records). It is not included; GMDB maintainers obtain it from GMDB. Stage 2 (mapping) writes `patient_metadata_2026-05-23_mondo.tsv`.

## Requirements

- Docker (Stage 1 pulls and runs the `obolibrary/robot` image)
- At least ~16 GB of RAM available to the JVM inside the container (Stage 1 sets `-Xmx16G`)
- Python 3.9 or later (standard library only)
- `gzip` / `gunzip` (used by the shell wrapper)

## Files

| File | Role |
| --- | --- |
| `010_run-docker-robot-owl2obo.sh` | Stage 1 driver: decompress input if needed, ROBOT `query`, write `.obo.gz` |
| `preprocess_labels_for_obo.ru` | Stage 1 SPARQL Update rules for label normalization |
| `020_map_GMDBomim_to_mondo.py` | Stage 2 thin wrapper (`from map_GMDBomim_to_mondo import main`) |
| `map_GMDBomim_to_mondo.py` | Stage 2 mapper body (reads `.obo` or `.obo.gz`; importable) |
| `mondo_gene_resolution.py` | Stage 3 helper: classify empty `gene_names` via MONDO |
| `030_build_metadata_pickle.py` | Stage 3: TSV → NGPsuite metadata pickle |
| `mondo-international.owl.gz` | Stage 1 input (~15 MB; prefer over uncompressed `.owl` when both exist). *Not included; download.* |
| `mondo-international.obo.gz` | Stage 1 output / **ontology for Stages 2 and 3** (58,942 terms, ~8.1 MB). *Bundled with NGPsuite as `backend/mondo/mondo-international.obo.gz`.* |
| `patient_metadata_2026-05-23.tsv` | Stage 2 input. *Not included; GMDB export.* |
| `patient_metadata_2026-05-23_mondo.tsv` | Stage 2 output / Stage 3 input |
| `patient_metadata_2026-05-23_mondo.err.txt` | Stage 2 stderr log |
| `patient_metadata_2026-05-23_mondo.p` | Stage 3 output (NGPsuite-compatible pickle) |

The GMDB metadata and everything derived from it (`*.p`, `*.tsv`, `*.csv`, `*.err.txt`) may contain personal information. Never commit them; share them only under the GMDB data use conditions.

## Stage 1: OWL to OBO conversion with label normalization

```sh
./010_run-docker-robot-owl2obo.sh
```

Chooses `mondo-international.owl.gz` if present, otherwise `mondo-international.owl`. When the input is gzipped it is decompressed to a temporary `.tmp-mondo-international.owl.*` file (removed on exit; made world-readable so the Docker ROBOT process can read it). Then runs `robot query --update preprocess_labels_for_obo.ru --format obo --output mondo-international.obo.gz` inside the `obolibrary/robot` container (`JAVA_TOOL_OPTIONS="-Xmx16G -Dfile.encoding=UTF-8"`).

The SPARQL Update is required because OBO format allows exactly one `name` per term, whereas the international edition attaches one `rdfs:label` per language. Without normalization the OBO writer fails or emits arbitrary labels. The rules are applied in order:

1. **Move non-English labels to alternative labels.** Every `rdfs:label` whose language tag is neither `en` nor empty is deleted and re-inserted as a `skos:altLabel` whose language tag is folded into the string itself, e.g. the Japanese label of MONDO:0000005 becomes `"脱毛症, 孤立性@ja"`. Any OWL annotation axiom (`owl:annotatedSource`/`Property`/`Target`) reifying the deleted label is removed along with it. In the resulting OBO these appear as `property_value: altLabel "…@ja" xsd:string`.

2. **Drop redundant labels on obsolete terms.** For a term with `owl:deprecated true` that carries both an `"obsolete …"` label and the original label, the `"obsolete "`-prefixed label is kept and the others are deleted (again together with their reifying axioms).

3. **Reduce any remaining multi-label terms to one label.** For each subject still holding more than one `rdfs:label`, the lexicographically smallest label string is kept and every other label is converted to `oboInOwl:hasExactSynonym`. This enforces the one-node-one-label invariant the OBO writer needs, without losing label text.

Japanese labels survive the conversion: the OBO contains 26,560 `@ja` strings. The resulting `mondo-international.obo.gz` has **58,942** terms after obsolete stanzas are skipped in Stage 2.

## Stage 2: Map OMIM IDs and gene symbols to MONDO terms

```sh
python3 020_map_GMDBomim_to_mondo.py \
  --input patient_metadata_2026-05-23.tsv \
  --obo mondo-international.obo.gz \
  --output patient_metadata_2026-05-23_mondo.tsv \
  2> patient_metadata_2026-05-23_mondo.err.txt
```

(`python3 map_GMDBomim_to_mondo.py …` is equivalent.) All three options default to the values shown above, so the script can also be run without arguments. The `--obo` path may be `.obo` or `.obo.gz`. The input TSV must contain the columns `omim_ids`, `gene_names`, `image_id` and `patient_id`.

### Building the ontology index

The OBO file is parsed stanza by stanza. From every `[Term]` the script records `id`, `name`, `is_a` parents, `xref` values, `synonym` values and gene `relationship` values; trailing OBO comments (`! …`) and axiom annotations (`{…}`) are stripped from `is_a` and `xref` values.

Terms flagged `is_obsolete: true` are skipped entirely. This matters because deprecated terms keep their old OMIM xrefs, and since the first stanza to claim an xref wins, an obsolete term would otherwise shadow the live term that replaced it. Three lookup tables are built from the remaining **58,942** terms:

- **OMIM index**: every xref with an `OMIM:` or `OMIMPS:` prefix maps to its MONDO term.
- **Gene index**: upper-cased gene symbols, each mapping to one or more MONDO terms. Symbols come from two kinds of source:
  - MONDO's curated association `relationship: has_material_basis_in_germline_mutation_in <HGNC IRI> {source="…"} ! <GENE>`, where the symbol is read from the trailing OBO comment. This is the authoritative source and supplies the bulk of the index (current OBO: 6,197 causal-gene terms / 4,645 HGNC symbols).
  - Three synonym-string heuristics kept from the original implementation: a trailing `"… caused by mutation in <GENE>"`, a leading `"<GENE>-related …"`, and the leading all-caps token of a synonym tagged `disease_series_by_gene`.
  - Non-human animal diseases (`MONDO:0005583` and its 8,318 `is_a` descendants) are removed from the gene index and the causal-gene table (6,197 terms remain). MONDO annotates these with the orthologous human gene, so without this step a `KDM2B` patient would also receive *lethal multi-organ developmental dysplasia, KDM2B-related, cattle*. Names and `is_a` edges are kept.
- **Hierarchy index**: term name and `is_a` parents, used to derive parent and grandparent classes.

### Per-record mapping rules

The `omim_ids` cell is split on commas and semicolons and each token is classified as a plain OMIM number (`^\d+$`), an OMIM phenotypic series (`^PS\d+$`, case-insensitive), or something else. Every resolvable identifier contributes a term, so `mondo_id` may hold several IDs.

| Content of `omim_ids` | Action | `mondo_source` | Reason code |
| --- | --- | --- | --- |
| one or more plain OMIM numbers | look up `OMIM:<n>` for **all** of them | `omim` | `mapped_omim` |
| only PS numbers | look up `OMIMPS:<n>` for all of them | `omim` | `mapped_omimps` |
| nothing resolvable | fall back to `gene_names` | `gene` | `mapped_gene` |

Phenotypic series are a deliberate second choice rather than an equal partner. GMDB routinely lists a disease together with its series (`239300, PS135900, PS239300`), and treating both as equals would emit a disease and its own supertype as two independent syndromes. The series reappears as a MONDO parent anyway, so nothing is lost.

The gene fallback runs whenever OMIM resolution yields no term — including when OMIM IDs were present but absent from the ontology. All gene symbols in the cell are looked up case-insensitively and every MONDO term registered for any of them is kept.

Records that survive neither path are left unmapped and classified by what was available: `unmapped_omim`, `unmapped_gene`, `unmapped_omim_gene`, or `unmapped_no_identifier`.

### Output

The output TSV reproduces every input column and appends seven columns:

| Column | Content |
| --- | --- |
| `mondo_id` | matched MONDO term ID(s) |
| `mondo_disease` | name(s) of the matched term(s) |
| `mondo_parent_id` | `is_a` parents of the matched term(s) |
| `mondo_parent_disease` | names of those parents |
| `mondo_grandparent_id` | `is_a` parents of the parents |
| `mondo_grandparent_disease` | names of those grandparents |
| `mondo_source` | `omim` or `gene`, recording which path produced the IDs |

Parents and grandparents are collected across all matched terms, de-duplicated while preserving the order in which they were found, and multiple values are joined with `", "`. Unmapped records keep all seven columns empty.

`mondo_source` exists because the two paths carry different confidence. A gene-derived record names every disease that gene can cause, and those sets are often clinically heterogeneous — `PDGFRB` yields infantile myofibromatosis, idiopathic basal ganglia calcification 4, and an overgrowth syndrome. Downstream consumers need to be able to tell these apart from OMIM-derived assignments.

Every unmapped record is reported on stderr as `unmapped<TAB><image_id><TAB><patient_id>`, followed by a summary. Summary of the current run:

```
rows: 28499
mapped: 26812
failed: 1687
breakdown:
  mapped_gene: 3142
  mapped_omim: 21810
  mapped_omimps: 1860
  multi_mondo: 1089
  unmapped_gene: 380
  unmapped_no_identifier: 1301
  unmapped_omim: 6
```

That is, 26,812 of 28,499 records (94.1%) received a MONDO annotation, up from 84.5% before curated gene `relationship` edges were indexed. `multi_mondo` counts mapped records that received more than one ID; it overlaps the `mapped_*` rows rather than adding to them. The largest residual group, `unmapped_no_identifier`, is records with neither an OMIM ID nor a gene symbol.

## Stage 3: Build NGPsuite metadata pickle

```sh
python3 030_build_metadata_pickle.py \
  --input patient_metadata_2026-05-23_mondo.tsv \
  --obo mondo-international.obo.gz \
  --validate \
  --report gene-resolution-report.csv \
  --compare image_gene_and_syndrome_metadata_pp4_23052026_v1.1.4.p
```

Defaults write `patient_metadata_2026-05-23_mondo.p`. The pickle is built **only from the TSV**. `--compare` is optional: it takes the legacy GestaltMatcher pickle, which only GMDB maintainers hold, as a structural reference (not a data source). Stage 3 reads the same `mondo-international.obo.gz` as Stage 2. Use `--no-gene-resolution` for the legacy behaviour, in which images without `gene_names` keep the disease name as a stand-in gene symbol (a *disease-name placeholder*, unrelated to biological pseudogenes).

### Selection rules

1. Keep `image_type == 'Frontal face'` (use `--image-type all` to disable).
2. Drop rows with no gene names, no disorder names, and no `mondo_id` (no diagnostic information yet).
3. Current run: 28,499 TSV rows → 18,534 frontal → **17,566 adopted** (968 excluded).

### MONDO resolution for empty `gene_names`

Rows with empty `gene_names` are classified from OBO `has_material_basis_in_germline_mutation_in` edges only (fixed order):

1. **`gene_unresolved` (chromosomal)** — under `MONDO:0019040` / `MONDO:0700064` with no own causal gene (checked first so Prader–Willi is not mislabeled via Schaaf–Yang / MAGEL2).
2. **`mondo` fill** — exactly one own causal gene → merge into that gene’s `gene_internal_id` (e.g. Kabuki syndrome 1 → KMT2D).
3. **`subtype_expanded`** — no own gene but descendants (or multiple own genes) provide candidates → **split into one `gene_level` entry per candidate** (e.g. Kabuki syndrome → KMT2D and KDM6A). At predict time each entry receives the same GM distance. This is the MONDO analogue of the OMIM Phenotypic Series expansion in upstream GestaltMatcher pickles.
4. **`gene_unresolved` (other)** — everything else.

Measured on 2,867 empty-gene images: `mondo` 1,171 / `subtype_expanded` 610 / `gene_unresolved` 1,086. `--report` writes a CSV suitable for GMDB feedback.

### Output layout

Four top-level dicts, compatible with NGPsuite (`backend/main.py`):

| Block | Key | Contents |
| --- | --- | --- |
| `gene_level_metadata` | `image_id` → non-empty list | per-gene (or disease-name placeholder) rows plus `gene_source` (`gmdb` / `mondo`); multiple rows when a subtype is expanded |
| `disorder_level_metadata` | `image_id` → dict | one syndrome-centric row per image, plus `mondo_id: list[str]` |
| `gene_metadata` | `gene_internal_id` → dict | `gene_name`, `gene_entrez_id`, `hgnc_id`, `gene_status` |
| `disorder_metadata` | `disorder_internal_id` → dict | `disorder_name`, `omim_id`, `mondo_id: list[str]`, `mondo_source` |

`gene_status` is `gmdb` | `mondo` | `gene_unresolved`.

Design choices:

- **`mondo_id` and `mondo_source` only** (no parent/grandparent/disease name columns). Downstream resolves names and hierarchy from `mondo-international.obo.gz` at runtime, so the pickle never goes stale against a newer ontology release.
- **`mondo_id` is `list[str]`**, empty list when unmapped.
- **No PP4 keys** (`very_strong` / `strong` / `moderate` / `supporting`). NGPsuite's `get_pp4()` skips missing keys and reports "Not available yet"; storing `None` would raise `TypeError`.
- **No `internal_syndrome_*`**. Disease identity is assigned from `mondo_id` (preferred), else `disorder_names`, else `gene_names`. Manual subtype→supertype labels are replaced by MONDO hierarchy lookup at use time.
- **`disorder_internal_id` / `gene_internal_id` are plain `int`** (not `numpy.int64`).
- **Single-gene MONDO fills and subtype expansions merge into existing gene IDs** so NGPsuite’s gene deduplication does not emit duplicate symbols.

`--validate` checks NGPsuite invariants (non-empty gene lists, referential integrity and no duplicate gene ids per image, `mondo_id` typed as list, `mondo_source` consistent with `mondo_id`, PP4 keys absent, `gene_status` / `gene_source` consistency).

### Current run (2026-10-06 regenerate, non-human terms excluded)

```
adopted: 17566
with_mondo: 17303 without_mondo: 263
mondo_source omim: 15330 gene: 1973
images with >1 mondo_id: 707
genes: 1398
disorders: 1439
gene_resolution: {'gene_unresolved': 1086, 'mondo': 1171, 'subtype_expanded': 610}
```

**98.5%** of adopted images carry at least one MONDO ID (17,303 / 17,566). Gene metadata grows to 1,398 entries after subtype expansion (new candidate genes not already in GMDB).

The 263 remaining images are genes MONDO has no disease entry for at all (`PSMC3`, `SPATA5`, `KCTD3`); they keep an empty `mondo_id` and are grouped by gene symbol instead. Every MONDO ID in use resolves in the ontology, is non-obsolete, and has at least one parent.

## License and attribution

The scripts are part of NGPsuite and are covered by its license ([LICENSE.md](../../LICENSE.md), CC BY-NC 4.0). MONDO is distributed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); OBO files derived from it inherit that license. GMDB metadata and the pickle built from it are subject to the GMDB data use conditions.
