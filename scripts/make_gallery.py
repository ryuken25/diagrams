"""Render PNG previews of every generated diagram into docs/img/ (for the README)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kenshi.content import build_all
from kenshi.content import beauty_salon
from kenshi.preview import render

OUT = os.path.join("docs", "img")


def main():
    os.makedirs(OUT, exist_ok=True)
    sets = {"mellogang": build_all(), "beautysalon": beauty_salon.build_all()}
    for proj, ds in sets.items():
        for name, d in ds.items():
            short = name.replace("bs_", "")
            path = os.path.join(OUT, f"{proj}_{short}.png")
            render(d, path)
            print("wrote", path)


if __name__ == "__main__":
    main()
