"""Quick matplotlib preview of a Diagram model (sanity check / docs thumbnails).

Not used by the exporters — purely to eyeball that a layout is clean. Renders
shapes, edges (with boundary clipping + short arrowheads) and labels.
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Rectangle, FancyArrow, Polygon

from .geometry import clip_edge
from .model import (PROCESS, EXTERNAL, DATASTORE, ENTITY, ATTRIBUTE,
                    RELATIONSHIP)


def render(diagram, path, scale=0.01):
    node = {n.id: n for n in diagram.nodes}
    xs = [n.x for n in diagram.nodes] + [n.x + n.w for n in diagram.nodes]
    ys = [n.y for n in diagram.nodes] + [n.y + n.h for n in diagram.nodes]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    w = (maxx - minx) * scale + 2
    h = (maxy - miny) * scale + 2
    fig, ax = plt.subplots(figsize=(max(6, w), max(6, h)))
    ax.set_xlim(minx - 40, maxx + 40)
    ax.set_ylim(maxy + 40, miny - 40)   # invert y (screen frame)
    ax.axis("off")

    # edges first (under shapes)
    for e in diagram.edges:
        a, b = node.get(e.source), node.get(e.target)
        if not a or not b:
            continue
        (sx, sy), (tx, ty) = clip_edge(a, b)
        ax.annotate("", xy=(tx, ty), xytext=(sx, sy),
                    arrowprops=dict(arrowstyle="-|>" if e.end_arrow != "none"
                                    else "-", color="#1F3A5F", lw=1.0))

    for n in diagram.nodes:
        cx, cy = n.center
        if n.kind == PROCESS:
            ax.add_patch(Ellipse((cx, cy), n.w, n.h, fill=True, fc="white",
                                 ec="#1F3A5F"))
        elif n.kind == ENTITY and n.style.get("rows"):
            hh = 28.0
            ax.add_patch(Rectangle((n.x, n.y), n.w, hh, fill=True, fc="#1F3A5F",
                                   ec="#1F3A5F"))
            ax.text(cx, n.y + hh / 2, n.label, ha="center", va="center",
                    fontsize=9, color="white", fontweight="bold")
            for i, (text, kind) in enumerate(n.style["rows"]):
                ry = n.y + hh + i * 22.0
                ax.add_patch(Rectangle((n.x, ry), n.w, 22.0, fill=True,
                                       fc="white", ec="#1F3A5F"))
                pre = {"pk": "PK ", "fk": "FK "}.get(kind, "")
                ax.text(n.x + 8, ry + 11, pre + text, ha="left", va="center",
                        fontsize=7,
                        fontweight="bold" if kind == "pk" else "normal",
                        style="italic" if kind == "fk" else "normal")
            continue
        elif n.kind in (EXTERNAL, ENTITY):
            fc = "#EEF2F7" if n.kind == EXTERNAL else "white"
            ax.add_patch(Rectangle((n.x, n.y), n.w, n.h, fill=True, fc=fc,
                                   ec="#1F3A5F"))
        elif n.kind == DATASTORE:
            ax.plot([n.x, n.x + n.w], [n.y, n.y], color="#1F3A5F")
            ax.plot([n.x, n.x + n.w], [n.y + n.h, n.y + n.h], color="#1F3A5F")
        elif n.kind == ATTRIBUTE:
            ax.add_patch(Ellipse((cx, cy), n.w, n.h, fill=True, fc="white",
                                 ec="#1F3A5F"))
        elif n.kind == RELATIONSHIP:
            ax.add_patch(Polygon([(cx, n.y), (n.x + n.w, cy), (cx, n.y + n.h),
                                  (n.x, cy)], fill=True, fc="white", ec="#1F3A5F"))
        elif n.kind == "label":
            ax.add_patch(Rectangle((n.x, n.y), n.w, n.h, fill=True, fc="white",
                                   ec="none"))
        fs = 7 if n.kind in ("label",) else (12 if n.kind == "title" else 8)
        ax.text(cx, cy, n.label, ha="center", va="center", fontsize=fs,
                wrap=True)

    fig.tight_layout()
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    import sys
    from .content import build_all
    diagrams = build_all()
    which = sys.argv[1:] or list(diagrams)
    for name in which:
        render(diagrams[name], f"preview_{name}.png")
        print("wrote", f"preview_{name}.png")
