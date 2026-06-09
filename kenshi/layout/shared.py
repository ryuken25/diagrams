"""Shared layout utilities: free-floating flow labels with collision avoidance."""
from __future__ import annotations

import math

from ..model import Node
from ..geometry import measure_label, _aabb_overlap


def make_label(nid: str, text: str, cx: float, cy: float, font: int = 11) -> Node:
    """A free-floating text label (opaque white box) centred on (cx, cy)."""
    w, h = measure_label(text, font=font, pad_x=14, pad_y=8, min_w=30, min_h=20)
    return Node(id=nid, kind="label", label=text, x=cx - w / 2, y=cy - h / 2,
                w=w, h=h, style={"font": str(font)})


def de_collide_labels(labels: list[Node], obstacles: list[Node],
                      passes: int = 120, step: float = 5.0, gap: float = 7.0,
                      vbias: float = 1.0):
    """Push label nodes apart from each other and out of obstacle shapes.

    Labels move; obstacles are fixed. Keeps flow/cardinality text from ever
    stacking on top of another label or a shape (the #1 cleanliness rule).
    ``vbias`` < 1 damps VERTICAL motion between labels so they slide *along* their
    flow line (stay inline) instead of being shoved off it — used for DFD flows.
    """
    obs_boxes = [(o.x, o.y, o.w, o.h) for o in obstacles]
    for _ in range(passes):
        moved = False
        # label vs label
        for i in range(len(labels)):
            for j in range(i + 1, len(labels)):
                a, b = labels[i], labels[j]
                ba = (a.x, a.y, a.w, a.h)
                bb = (b.x, b.y, b.w, b.h)
                if not _aabb_overlap(ba, bb, gap):
                    continue
                dx = a.cx - b.cx
                dy = (a.cy - b.cy) * vbias
                if abs(dx) < 1e-6 and abs(dy) < 1e-6:
                    dx = 1.0
                length = math.hypot(dx, dy) or 1.0
                a.x += dx / length * step / 2; a.y += dy / length * step / 2
                b.x -= dx / length * step / 2; b.y -= dy / length * step / 2
                moved = True
        # label vs obstacle
        for a in labels:
            ba = (a.x, a.y, a.w, a.h)
            for ob in obs_boxes:
                if not _aabb_overlap(ba, ob, gap):
                    continue
                dx = (a.x + a.w / 2) - (ob[0] + ob[2] / 2)
                dy = (a.y + a.h / 2) - (ob[1] + ob[3] / 2)
                if abs(dx) < 1e-6 and abs(dy) < 1e-6:
                    dy = 1.0
                length = math.hypot(dx, dy) or 1.0
                a.x += dx / length * step
                a.y += dy / length * step
                moved = True
                ba = (a.x, a.y, a.w, a.h)
        if not moved:
            break
