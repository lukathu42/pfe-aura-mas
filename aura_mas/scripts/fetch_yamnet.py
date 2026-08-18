"""Fetch the YAMNet TF2 SavedModel to a local directory (one-time, idempotent).

Why not `tensorflow_hub.load("https://tfhub.dev/google/yamnet/1")` (what
AudioAgent used to call): as of 2026-08-18 that URL returns HTTP 404 --
tfhub.dev has been retired in favor of Kaggle Models. `tensorflow_hub` also
pulls in the `tf-keras` compatibility package to bridge Keras 3, an extra
dependency this disk-constrained environment doesn't need. Downloading the
SavedModel once to `models/yamnet/` makes every scenario run offline and
byte-for-byte reproducible -- no network dependency at eval time, and the
exact model bytes are pinned by sha256 in PROVENANCE.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

YAMNET_URL = (
    "https://www.kaggle.com/api/v1/models/google/yamnet/tensorFlow2/yamnet/1/download"
)
EXPECT_BYTES = 14242921
REQUIRED_MEMBERS = (
    "saved_model.pb",
    "variables/variables.index",
    "assets/yamnet_class_map.csv",
)


def fetch(dest: Path, force: bool = False) -> None:
    if (dest / "saved_model.pb").exists() and not force:
        print(f"YAMNet already present at {dest} (use --force to re-fetch)")
        return

    dest.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        print(f"Downloading {YAMNET_URL} ...")
        urllib.request.urlretrieve(YAMNET_URL, tmp_path)

        size = tmp_path.stat().st_size
        if size != EXPECT_BYTES:
            raise RuntimeError(
                f"downloaded {size} bytes, expected {EXPECT_BYTES} -- "
                "download likely truncated or the upstream artifact changed; "
                "not extracting an unverified archive"
            )
        digest = hashlib.sha256(tmp_path.read_bytes()).hexdigest()

        with tarfile.open(tmp_path) as tar:
            members = set(tar.getnames())
            missing = [m for m in REQUIRED_MEMBERS if m not in members]
            if missing:
                raise RuntimeError(f"archive missing expected members: {missing}")
            tar.extractall(dest, filter="data")

        for member in REQUIRED_MEMBERS:
            if not (dest / member).exists():
                raise RuntimeError(f"extraction did not produce {dest / member}")

        provenance = {
            "url": YAMNET_URL,
            "sha256": digest,
            "bytes": size,
            "fetched_utc": datetime.now(timezone.utc).isoformat(),
            "format": "TensorFlow 2 SavedModel",
            "license": "Apache 2.0 (google/yamnet)",
            "note": (
                "tfhub.dev/google/yamnet/1 returns HTTP 404 as of 2026-08-18; "
                "this is the Kaggle Models mirror, fetched directly (no "
                "tensorflow_hub dependency)."
            ),
        }
        (dest / "PROVENANCE.json").write_text(json.dumps(provenance, indent=2))
        print(f"YAMNet extracted to {dest} (sha256={digest[:12]}...)")
    finally:
        tmp_path.unlink(missing_ok=True)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dir", default="models/yamnet", help="destination directory")
    p.add_argument("--force", action="store_true", help="re-fetch even if present")
    args = p.parse_args()
    fetch(Path(args.dir), force=args.force)


if __name__ == "__main__":
    main()
