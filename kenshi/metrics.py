"""Quality metrics — the acceptance criterion is *zero overlapping labels*."""
from __future__ import annotations

from .geometry import _aabb_overlap, segments_cross


def _boxes(diagram, kinds=None):
    out = []
    for n in diagram.nodes:
        if kinds and n.kind not in kinds:
            continue
        out.append((n.id, n.kind, (n.x, n.y, n.w, n.h)))
    return out


def label_overlaps(diagram) -> int:
    """Count overlapping pairs among labels and labels-vs-shapes."""
    labels = _boxes(diagram, kinds={"label"})
    shapes = _boxes(diagram, kinds={"process", "external", "datastore",
                                    "entity", "attribute", "relationship"})
    count = 0
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            if _aabb_overlap(labels[i][2], labels[j][2], gap=0):
                count += 1
    for (lid, lk, lb) in labels:
        for (sid, sk, sb) in shapes:
            if _aabb_overlap(lb, sb, gap=0):
                count += 1
    return count


def shape_overlaps(diagram) -> int:
    shapes = _boxes(diagram, kinds={"process", "external", "datastore",
                                    "entity", "attribute", "relationship"})
    count = 0
    for i in range(len(shapes)):
        for j in range(i + 1, len(shapes)):
            if _aabb_overlap(shapes[i][2], shapes[j][2], gap=0):
                count += 1
    return count


def edge_crossings(diagram) -> int:
    node = {n.id: n for n in diagram.nodes}
    segs = []
    for e in diagram.edges:
        a, b = node.get(e.source), node.get(e.target)
        if a and b:
            segs.append((a.center, b.center))
    c = 0
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            if segments_cross(segs[i][0], segs[i][1], segs[j][0], segs[j][1]):
                c += 1
    return c


def report(diagrams: dict) -> dict:
    print(f"{'diagram':28} {'labelOverlap':>12} {'shapeOverlap':>12} "
          f"{'edgeCross':>10}")
    print("-" * 66)
    totals = {"label": 0, "shape": 0}
    out = {}
    for name, d in diagrams.items():
        lo = label_overlaps(d)
        so = shape_overlaps(d)
        ec = edge_crossings(d)
        totals["label"] += lo
        totals["shape"] += so
        out[name] = (lo, so, ec)
        flag = "" if (lo == 0 and so == 0) else "  <-- CHECK"
        print(f"{name:28} {lo:>12} {so:>12} {ec:>10}{flag}")
    print("-" * 66)
    print(f"{'TOTAL label/shape overlaps':28} {totals['label']:>12} "
          f"{totals['shape']:>12}")
    return out
