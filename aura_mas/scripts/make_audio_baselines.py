"""Build "with_baseline" audio clips: a low-level noise lead-in prepended to
a real ESC-50 event recording.

Why the lead-in exists: AudioAgent's DSP fallback (DspAnomalyScorer) needs
>=10 one-second chunks of rolling history before its z-score baseline is
populated (audio_agent.py) -- a bare 5s ESC-50 clip with no lead-in
structurally can never fire under the DSP path. `glass_breaking_with_baseline.wav`
(pre-existing, no generator script committed anywhere in this repo) already
uses this pattern; this script reproduces it for the two ESC-50 assets that
were on disk but never wired into any scenario (`siren_esc50.wav`,
`clock_alarm_esc50.wav`, see data/clips_real/manifest.json) and documents the
noise characteristics measured from the existing file so the new clips are a
fair comparison.

Measured from glass_breaking_with_baseline.wav's first 15s (not regenerated
from a seed -- no original generator exists, so this is a best-effort match,
not a byte-identical reproduction): 44100 Hz mono, uniform noise (not
Gaussian -- 57.7% of samples fall within 1 std, matching a uniform
distribution's 1/sqrt(3) ~= 57.7%, vs. Gaussian's ~68%), amplitude range
approximately [-0.015, 0.015].
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import soundfile as sf

PREFIX_SECONDS = 15.0
NOISE_AMPLITUDE = 0.015
SEED = 0

SOURCES = {
    "siren_esc50.wav": "siren_with_baseline.wav",
    "clock_alarm_esc50.wav": "clock_alarm_with_baseline.wav",
}


def build_one(src_path: Path, dst_path: Path, force: bool = False) -> None:
    if dst_path.exists() and not force:
        print(f"skip (exists): {dst_path}")
        return
    event, sr = sf.read(src_path)
    if event.ndim > 1:
        event = event.mean(axis=1)  # ESC-50 clips are mono already; defensive

    rng = np.random.default_rng(SEED)
    n_prefix = int(PREFIX_SECONDS * sr)
    prefix = rng.uniform(-NOISE_AMPLITUDE, NOISE_AMPLITUDE, n_prefix)

    combined = np.concatenate([prefix, event]).astype(np.float64)
    sf.write(dst_path, combined, sr, subtype="PCM_16")
    print(f"wrote {dst_path} ({len(combined) / sr:.1f}s @ {sr}Hz)")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dir", default="data/clips_real/audio",
                   help="directory holding the ESC-50 source clips")
    p.add_argument("--force", action="store_true",
                   help="regenerate even if the destination already exists")
    p.add_argument("--source", action="append", default=[], metavar="INPUT=OUTPUT",
                   help="additional relative source/output pair; may be repeated")
    p.add_argument("--only-missing", action="store_true", default=True,
                   help="(default) never touch glass_breaking_with_baseline.wav "
                        "-- it is a cited, pre-existing artifact with no "
                        "generator script; this tool only ever creates the "
                        "siren/clock_alarm variants")
    args = p.parse_args()

    base = Path(args.dir)
    pairs = dict(SOURCES)
    for value in args.source:
        if "=" not in value:
            p.error("--source must use INPUT=OUTPUT")
        src_name, dst_name = value.split("=", 1)
        pairs[src_name] = dst_name
    for src_name, dst_name in pairs.items():
        build_one(base / src_name, base / dst_name, force=args.force)


if __name__ == "__main__":
    main()
