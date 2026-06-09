"""Generate MellogangVisuals diagrams in monochrome (white fill, black lines) with
a transparent background, into generated/.

    generated/*.drawio    black-and-white, editable in draw.io
    generated/*.graphml   black-and-white, editable in yEd
    generated/*.png       black-and-white with a TRANSPARENT background
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kenshi.content import build_all
from kenshi.export import to_drawio, to_graphml
from kenshi.preview import render

OUT = "generated"

# colour -> black/white (navy stroke -> black; light-blue external fill -> white)
_MONO = {"#1F3A5F": "#000000", "#EEF2F7": "#FFFFFF"}


def monochrome(xml: str) -> str:
    for a, b in _MONO.items():
        xml = xml.replace(a, b)
    return xml


def main():
    os.makedirs(OUT, exist_ok=True)
    diagrams = build_all()
    for name, d in diagrams.items():
        open(os.path.join(OUT, f"{name}.drawio"), "w", encoding="utf-8").write(
            monochrome(to_drawio(d)))
        open(os.path.join(OUT, f"{name}.graphml"), "w", encoding="utf-8").write(
            monochrome(to_graphml(d)))
        render(d, os.path.join(OUT, f"{name}.png"), mono=True, transparent=True)
        print("wrote", name, "(.drawio + .graphml + transparent .png)")
    # one combined multi-page mono file
    open(os.path.join(OUT, "MellogangVisuals_all.drawio"), "w",
         encoding="utf-8").write(monochrome(to_drawio(list(diagrams.values()))))
    print(f"\nwrote {len(diagrams)} diagrams to {OUT}/ (mono, transparent PNGs)")


if __name__ == "__main__":
    main()
