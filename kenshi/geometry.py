"""Geometry helpers — the math that keeps diagrams clean and overlap-free.

The two ideas that remove most "mess":
  1. An edge leaves and enters a shape on whichever *side faces the other
     shape* (computed via ``boundary_point``), so flows can approach from the
     top, bottom, left or right — not only left<->right.
  2. Every edge label carries an opaque background box and is pushed apart from
     its neighbours (``de_collide``) so no two labels ever overlap.
"""
from __future__ import annotations

import math
from typing import Iterable

from .model import Node


def measure_label(label: str, font: int = 12, pad_x: int = 22, pad_y: int = 16,
                  min_w: int = 80, min_h: int = 40) -> tuple[int, int]:
    """Cheap text metric: width from the longest line, height from line count."""
    lines = label.replace("<br>", "\n").split("\n") or [""]
    longest = max((len(ln) for ln in lines), default=0)
    w = max(min_w, int(longest * font * 0.62) + pad_x)
    h = max(min_h, len(lines) * (font + 6) + pad_y)
    return w, h


def boundary_point(node: Node, toward: tuple[float, float]) -> tuple[float, float]:
    """Point where the segment from ``node.center`` toward ``toward`` exits the node.

    Ellipses/circles use the parametric ellipse intersection; rectangles use the
    half-extent clamp. Works for every direction, so edges naturally pick the
    facing side (incl. top / bottom).
    """
    cx, cy = node.center
    ux, uy = toward[0] - cx, toward[1] - cy
    if ux == 0 and uy == 0:
        return cx, cy
    hw, hh = node.w / 2.0, node.h / 2.0
    if node.kind in ("process",):  # ellipse / circle
        denom = math.sqrt((ux / hw) ** 2 + (uy / hh) ** 2)
        t = 1.0 / denom if denom else 0.0
        return cx + ux * t, cy + uy * t
    if node.kind == "relationship":  # diamond: |x/hw| + |y/hh| = 1
        denom = abs(ux) / hw + abs(uy) / hh
        t = 1.0 / denom if denom else 0.0
        return cx + ux * t, cy + uy * t
    # rectangle-ish (entity, external, datastore, attribute treated as box bb)
    if node.kind == "attribute":    # ellipse attribute
        denom = math.sqrt((ux / hw) ** 2 + (uy / hh) ** 2)
        t = 1.0 / denom if denom else 0.0
        return cx + ux * t, cy + uy * t
    tx = hw / abs(ux) if ux else math.inf
    ty = hh / abs(uy) if uy else math.inf
    t = min(tx, ty)
    return cx + ux * t, cy + uy * t


def pull_back(p: tuple[float, float], toward: tuple[float, float], dist: float = 7.0):
    """Pull point ``p`` ``dist`` px back along the line toward its own center side."""
    dx, dy = toward[0] - p[0], toward[1] - p[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return p
    return p[0] + dx / length * dist, p[1] + dy / length * dist


def clip_edge(src: Node, tgt: Node, pullback: float = 7.0):
    """Return (start, end) clipped to each node's boundary, arrowhead pulled short."""
    start = boundary_point(src, tgt.center)
    end = boundary_point(tgt, src.center)
    end = pull_back(end, src.center, pullback)
    return start, end


def offset_parallel(a: tuple[float, float], b: tuple[float, float], k: float):
    """Shift segment a->b by ``k`` along its perpendicular (parallel/bi-dir flows)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy) or 1.0
    px, py = -dy / length, dx / length
    return (a[0] + px * k, a[1] + py * k), (b[0] + px * k, b[1] + py * k)


def _aabb_overlap(a, b, gap=4.0) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw + gap <= bx or bx + bw + gap <= ax or
                ay + ah + gap <= by or by + bh + gap <= ay)


def de_collide(boxes: list[list[float]], passes: int = 60, step: float = 6.0,
               gap: float = 6.0) -> list[list[float]]:
    """Nudge overlapping label boxes apart in place.

    ``boxes`` is a list of mutable ``[x, y, w, h]`` (x,y = top-left). Each box is
    pushed away from any neighbour it intersects until no pair overlaps (or the
    pass budget runs out). Returns the same list for convenience.
    """
    n = len(boxes)
    for _ in range(passes):
        moved = False
        for i in range(n):
            for j in range(i + 1, n):
                bi, bj = boxes[i], boxes[j]
                if not _aabb_overlap(bi, bj, gap):
                    continue
                ci = (bi[0] + bi[2] / 2, bi[1] + bi[3] / 2)
                cj = (bj[0] + bj[2] / 2, bj[1] + bj[3] / 2)
                dx, dy = ci[0] - cj[0], ci[1] - cj[1]
                if abs(dx) < 1e-6 and abs(dy) < 1e-6:
                    dy = 1.0
                length = math.hypot(dx, dy) or 1.0
                push_x, push_y = dx / length * step, dy / length * step
                bi[0] += push_x; bi[1] += push_y
                bj[0] -= push_x; bj[1] -= push_y
                moved = True
        if not moved:
            break
    return boxes


def resolve_node_overlaps(nodes: Iterable[Node], gap: float = 24.0, passes: int = 80):
    """Spread nodes so no two bounding boxes overlap (safety net after layout)."""
    items = list(nodes)
    for _ in range(passes):
        moved = False
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b = items[i], items[j]
                box_a = [a.x, a.y, a.w, a.h]
                box_b = [b.x, b.y, b.w, b.h]
                if not _aabb_overlap(box_a, box_b, gap):
                    continue
                dx = a.cx - b.cx
                dy = a.cy - b.cy
                if abs(dx) < 1e-6 and abs(dy) < 1e-6:
                    dx = 1.0
                length = math.hypot(dx, dy) or 1.0
                shift = gap
                a.x += dx / length * shift / 2
                a.y += dy / length * shift / 2
                b.x -= dx / length * shift / 2
                b.y -= dy / length * shift / 2
                moved = True
        if not moved:
            break


def segments_cross(p1, p2, p3, p4) -> bool:
    """True if segment p1p2 properly crosses p3p4 (for crossing-count metrics)."""
    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])
    d1 = ccw(p3, p4, p1)
    d2 = ccw(p3, p4, p2)
    d3 = ccw(p1, p2, p3)
    d4 = ccw(p1, p2, p4)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def normalize(diagram, margin: float = 60.0):
    """Translate every node so the diagram's top-left sits at (margin, margin)."""
    if not diagram.nodes:
        return diagram
    min_x = min(n.x for n in diagram.nodes)
    min_y = min(n.y for n in diagram.nodes)
    dx, dy = margin - min_x, margin - min_y
    for n in diagram.nodes:
        n.x += dx
        n.y += dy
    for e in diagram.edges:
        e.waypoints = [(x + dx, y + dy) for (x, y) in e.waypoints]
    return diagram
