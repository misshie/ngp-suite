# CLAUDE.md

NGPsuite is a web application for next-generation phenotyping. It ranks candidate syndromes and genes from a facial
image (GestaltMatcher-Arc v1.1.4, MONDO-keyed gallery) and optional HPO terms (PubCaseFinder).

Detailed handoff notes (Japanese): [plans-ja/handoff-claude-code.md](plans-ja/handoff-claude-code.md).

## Layout

- `backend/` — FastAPI API (`main.py`, `lib/`) and nginx, run with Docker compose (`compose.yml`)
- `backend/static/` — built frontend; regenerate with `./build-frontend.sh`
- `backend/mondo/` — bundled MONDO ontology (tracked in git)
- `frontend/` — Vue 3 / TypeScript UI
- `tools/gmdb-mondo/` — scripts that build the MONDO-keyed metadata pickle (for GMDB maintainers)
- `plans-ja/` — design memos and handoff notes, in Japanese

## Conventions

- Reply to the maintainer in Japanese. Write design memos in `plans-ja/` in Japanese.
- `README.md` is the original; keep `README-ja.md` in step with it.
- Commit messages are one English sentence ending with a period.
- Merge PRs into `main` with a merge commit and keep the branch. Bump the minor version for breaking changes.

## Never commit

- GMDB data and models: `backend/data/`, `backend/saved_models/`, `*.p`, `*.pkl`, `*.pth`, `*.onnx`, `*.csv`
- `backend/.env` (credentials and local paths)

These files may contain patient-derived information or are not redistributable.

## Run and check

```bash
cd backend
cp .env.example .env   # set NGPSUITE_GMDB_DIR to the directory holding data/ and saved_models/
docker compose up -d --build
docker compose logs api | grep "Load MONDO index"
```

Open `https://localhost/` (self-signed certificate). The API stops at startup and lists any missing GMDB file.
