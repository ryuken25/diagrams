"""DFD Context Diagram (Diagram 0 / Konteks).

One large central process (the whole system); external entities on a ring at
angles of least crowding; every data flow is its own arrow with an opaque,
de-collided label. Spacing on the ring guarantees no label overlap.
"""
from __future__ import annotations

import math

from ..model import Node, PROCESS, EXTERNAL
from ..geometry import measure_label, normalize
from .shared import make_label, de_collide_labels


def layout_context(diagram, ring: float = 620.0):
    central = next((n for n in diagram.nodes if n.kind == PROCESS), None)
    externals = [n for n in diagram.nodes if n.kind == EXTERNAL]
    if central is None:
        return diagram

    w, h = measure_label(central.label, font=15, min_w=240, min_h=160)
    central.w, central.h = max(260, w), max(160, h)
    central.x = -central.w / 2
    central.y = -central.h / 2

    m = len(externals)
    for i, ext in enumerate(externals):
        ang = 2 * math.pi * i / m - math.pi / 2
        ew, eh = measure_label(ext.label, font=14, min_w=150, min_h=64)
        ext.w, ext.h = max(150, ew), max(64, eh)
        ext.x = ring * math.cos(ang) - ext.w / 2
        ext.y = ring * math.sin(ang) - ext.h / 2
        ext.style["_angle"] = ang

    # one floating label per flow, placed along the flow then de-collided
    labels: list[Node] = []
    # group flows by the external they touch so we can offset parallels
    by_ext: dict[str, list] = {}
    for e in diagram.edges:
        ext_id = e.source if any(x.id == e.source and x.kind == EXTERNAL
                                 for x in diagram.nodes) else e.target
        by_ext.setdefault(ext_id, []).append(e)

    li = 0
    for ext_id, flows in by_ext.items():
        ext = next(x for x in diagram.nodes if x.id == ext_id)
        ang = ext.style.get("_angle", 0.0)
        # spread the labels along the radial direction between system and external
        kf = len(flows)
        for j, e in enumerate(flows):
            # parameter along the radius (closer to system for outputs vs inputs)
            base = 0.34 + 0.5 * (j / max(1, kf - 1)) if kf > 1 else 0.5
            lx = central.cx + (ext.cx - central.cx) * base
            ly = central.cy + (ext.cy - central.cy) * base
            # perpendicular offset so the two directions don't sit on one line
            perp = (j - (kf - 1) / 2) * 30.0
            lx += -math.sin(ang) * perp
            ly += math.cos(ang) * perp
            lab = make_label(f"_fl{li}", e.label, lx, ly, font=11)
            lab.style["flow"] = "1"
            labels.append(lab)
            li += 1

    obstacles = [x for x in diagram.nodes if x.kind != "label"]
    de_collide_labels(labels, obstacles, passes=160)
    diagram.nodes.extend(labels)

    title = Node(id="_title", kind="title",
                 label=diagram.meta.get("title", diagram.name), w=680, h=40)
    minx = min(x.x for x in diagram.nodes)
    maxx = max(x.x + x.w for x in diagram.nodes)
    miny = min(x.y for x in diagram.nodes)
    title.x = (minx + maxx) / 2 - title.w / 2
    title.y = miny - 70
    diagram.nodes.append(title)

    normalize(diagram, margin=60)
    return diagram
