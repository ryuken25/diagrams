"""Kenshi Diagrams CLI — generate clean, editable DFD & ERD files.

Usage:
    python -m kenshi.cli            # build MellogangVisuals -> out/
    python -m kenshi.cli --out DIR  # choose output directory
    python -m kenshi.cli --check    # build + report overlap metrics, no write
"""
from __future__ import annotations

import argparse
import os

from .content import build_all
from .export import to_drawio, to_graphml
from .metrics import report


def main(argv=None):
    ap = argparse.ArgumentParser(prog="kenshi", description=__doc__)
    ap.add_argument("--out", default="out", help="output directory")
    ap.add_argument("--check", action="store_true",
                    help="print overlap metrics instead of writing files")
    args = ap.parse_args(argv)

    diagrams = build_all()

    if args.check:
        report(diagrams)
        return 0

    os.makedirs(args.out, exist_ok=True)
    # one combined multi-page .drawio (tabs) + per-diagram .graphml
    combined = to_drawio(list(diagrams.values()))
    path = os.path.join(args.out, "MellogangVisuals_all.drawio")
    with open(path, "w", encoding="utf-8") as f:
        f.write(combined)
    print(f"wrote {path}  ({len(diagrams)} pages)")

    for name, d in diagrams.items():
        dp = os.path.join(args.out, f"{name}.drawio")
        with open(dp, "w", encoding="utf-8") as f:
            f.write(to_drawio(d))
        gp = os.path.join(args.out, f"{name}.graphml")
        with open(gp, "w", encoding="utf-8") as f:
            f.write(to_graphml(d))
        print(f"wrote {dp} + {gp}")

    print("\nOverlap check:")
    report(diagrams)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
