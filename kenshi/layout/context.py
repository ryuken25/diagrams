"""DFD Context Diagram (Diagram 0 / Konteks) — orthogonal, non-overlapping.

One central process (the whole system) in the middle; external entities pinned
to the sides (top / right / left / bottom). Every data flow gets its own
perimeter PORT on both the external and the central process plus its own parallel
LANE, so flows run as straight axis-parallel lines that never sit on top of one
another. Each flow carries an opaque, de-collided ``data_/info_`` label.
"""
from __future__ import annotations

from ..model import Node, PROCESS, EXTERNAL
from ..geometry import measure_label, normalize
from .shared import make_label, de_collide_labels

PITCH = 70.0        # spacing between parallel lanes of one external
GAP = 250.0         # clear space between an external and the central process
BAND = 0.46         # fraction of the central side that lanes may occupy


def _band_positions(k, half):
    """k symmetric lane offsets in [-half, half] (single 0 when k == 1)."""
    if k <= 1:
        return [0.0]
    return [-half + 2 * half * i / (k - 1) for i in range(k)]


def layout_context(diagram, ring: float = 0.0):
    central = next((n for n in diagram.nodes if n.kind == PROCESS), None)
    externals = [n for n in diagram.nodes if n.kind == EXTERNAL]
    if central is None:
        return diagram

    node_by = {n.id: n for n in diagram.nodes}

    # --- group flows by the external they touch, preserve authored order ------
    flows_by_ext: dict[str, list] = {ex.id: [] for ex in externals}
    for e in diagram.edges:
        a, b = node_by.get(e.source), node_by.get(e.target)
        if not a or not b:
            continue
        ext = a if a.kind == EXTERNAL else b
        flows_by_ext.setdefault(ext.id, []).append(e)

    # --- assign each external a side ------------------------------------------
    sides = ["top", "right", "left", "bottom"]
    ext_side = {ex.id: sides[i % 4] for i, ex in enumerate(externals)}
    vert = [ex for ex in externals if ext_side[ex.id] in ("top", "bottom")]
    horiz = [ex for ex in externals if ext_side[ex.id] in ("left", "right")]

    def kflows(ex):
        return max(1, len(flows_by_ext[ex.id]))

    # --- size the central process so every side's lanes fit in its mid-band ---
    cw, ch = measure_label(central.label, font=15, min_w=300, min_h=180)
    need_w = max((kflows(ex) - 1) * PITCH for ex in vert) if vert else 0
    need_h = max((kflows(ex) - 1) * PITCH for ex in horiz) if horiz else 0
    central.w = max(cw, need_w / BAND + 150, 320)
    central.h = max(ch, need_h / BAND + 120, 200)
    central.x = -central.w / 2
    central.y = -central.h / 2

    # --- size + place externals on their side ---------------------------------
    for ex in externals:
        k = kflows(ex)
        ew, eh = measure_label(ex.label, font=14, min_w=160, min_h=70)
        side = ext_side[ex.id]
        if side in ("top", "bottom"):
            ex.w = max(ew, (k - 1) * PITCH + 130)
            ex.h = max(eh, 70)
        else:
            ex.w = max(ew, 170)
            ex.h = max(eh, (k - 1) * PITCH + 110)
    for ex in externals:
        side = ext_side[ex.id]
        if side == "top":
            ex.x, ex.y = -ex.w / 2, central.y - GAP - ex.h
        elif side == "bottom":
            ex.x, ex.y = -ex.w / 2, central.y + central.h + GAP
        elif side == "right":
            ex.x, ex.y = central.x + central.w + GAP, -ex.h / 2
        else:  # left
            ex.x, ex.y = central.x - GAP - ex.w, -ex.h / 2

    # --- route each flow as a straight axis-parallel lane via fixed ports ------
    def set_ports(e, sx, sy, tx, ty):
        e.style["exitX"], e.style["exitY"] = f"{sx:.3f}", f"{sy:.3f}"
        e.style["entryX"], e.style["entryY"] = f"{tx:.3f}", f"{ty:.3f}"
        e.waypoints = []

    labels: list[Node] = []
    li = 0
    for ex in externals:
        side = ext_side[ex.id]
        flows = flows_by_ext[ex.id]
        k = len(flows)
        if side in ("top", "bottom"):
            offs = _band_positions(k, BAND / 2 * central.w)
            c_edge_y = 0.0 if side == "top" else 1.0
            e_edge_y = 1.0 if side == "top" else 0.0
        else:
            offs = _band_positions(k, BAND / 2 * central.h)
            c_edge_x = 1.0 if side == "right" else 0.0
            e_edge_x = 0.0 if side == "right" else 1.0
        for j, e in enumerate(flows):
            a, b = node_by[e.source], node_by[e.target]
            ext_is_src = (a.kind == EXTERNAL)
            if side in ("top", "bottom"):
                lane_x = offs[j]                       # absolute (both centred 0)
                c_fx = 0.5 + lane_x / central.w
                e_fx = 0.5 + lane_x / ex.w
                ep = (e_fx, e_edge_y)                  # external port (frac)
                cp = (c_fx, c_edge_y)                  # central port (frac)
                # label on the lane, just outside the central process edge
                lx = lane_x
                ly = central.y - 48 if side == "top" else \
                    central.y + central.h + 48
            else:
                lane_y = offs[j]
                c_fy = 0.5 + lane_y / central.h
                e_fy = 0.5 + lane_y / ex.h
                ep = (e_edge_x, e_fy)
                cp = (c_edge_x, c_fy)
                ly = lane_y
                lx = central.x + central.w + 64 if side == "right" else \
                    central.x - 64
            if ext_is_src:
                set_ports(e, ep[0], ep[1], cp[0], cp[1])
            else:
                set_ports(e, cp[0], cp[1], ep[0], ep[1])
            if e.label:
                labels.append(make_label(f"_fl{li}", e.label, lx, ly, font=11))
                labels[-1].style["flow"] = "1"
                e.label = ""    # floating node IS the label; avoid draw.io doubling
                li += 1

    obstacles = [x for x in diagram.nodes if x.kind != "label"]
    de_collide_labels(labels, obstacles, passes=200, step=5.0, gap=7.0)
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
