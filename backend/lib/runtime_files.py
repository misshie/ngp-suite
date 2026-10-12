"""Pre-flight check for the GMDB files that are bind-mounted into the container.

The image ships no GMDB data. ``data/`` and ``saved_models/`` are mounted read-only from
the host directory given by ``NGPSUITE_GMDB_DIR``. Run this before starting the API so that
a missing or unreadable file stops the container immediately with a complete list, instead of
surfacing as a worker crash after the health-check start period.

Usage (from the application root, e.g. /app):

    python -m lib.runtime_files
"""
import os
import sys

# Paths are relative to the application root (the container WORKDIR), exactly as the
# runtime code opens them. Keep in sync with:
#   lib/face_alignment.py, lib/encode.py, lib/evaluation.py, main.py
REQUIRED_FILES = (
    "saved_models/Resnet50_Final.pth",
    "saved_models/s1_glint360k_r50_512d_gmdb__v1.1.4_bs64_size112_channels3_last_model.pth",
    "saved_models/s2_glint360k_r100_512d_gmdb__v1.1.4_bs128_size112_channels3_last_model.pth",
    "saved_models/glint360k_r100.onnx",
    "data/patient_metadata_2026-05-23_mondo.p",
    "data/gallery_encodings/GMDB_gallery_encodings_23052026_v1.1.4_service.pkl",
    "data/transformation_probabilities_07052025.csv",
)


def find_problems(root=".", files=REQUIRED_FILES):
    """Return a list of (relative_path, reason) for every file that cannot be used."""
    problems = []
    for rel in files:
        path = os.path.join(root, rel)
        if not os.path.exists(path):
            problems.append((rel, "missing"))
        elif not os.path.isfile(path):
            problems.append((rel, "not a regular file"))
        elif not os.access(path, os.R_OK):
            problems.append((rel, "not readable"))
    return problems


def main(root="."):
    problems = find_problems(root)
    if not problems:
        print(f"GMDB files OK: {len(REQUIRED_FILES)} required files found.")
        return 0

    print(
        f"ERROR: {len(problems)} of {len(REQUIRED_FILES)} required GMDB files are unusable "
        f"(looked under {os.path.abspath(root)}):",
        file=sys.stderr,
    )
    for rel, reason in problems:
        print(f"  - {rel}: {reason}", file=sys.stderr)
    print(
        "Check that NGPSUITE_GMDB_DIR (backend/.env) points to a directory containing data/ and "
        "saved_models/ with these files. See README.md for the expected layout.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
