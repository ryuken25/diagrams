"""DFD Level 0 & Level 1 — per-process clusters with duplicated stores/externals.

The technique that defeats the "shared data store hairball": each process is its
own horizontal row — externals stacked on the LEFT, the process ellipse in the
CENTRE, its data stores in one COLUMN on the RIGHT. A store/external used by
several processes is *duplicated* next to each process that uses it (and marked),
so there are zero inter-row crossings.

Node tagging contract (set by the content builder in ``style``):
    style['proc']  -> id of the owning process
    style['side']  -> 'left' (external) | 'right' (datastore)
Duplicated instances carry ``duplicate_of`` so the exporter can mark them.
"""
from __future__ import annotations

from ..model import Node, PROCESS, EXTERNAL, DATASTORE
from ..geometry import measure_label, normalize
from .shared import make_label, de_collide_labels

PROC_W, PROC_H = 214.0, 170.0
STORE_W, STORE_H = 210.0, 48.0
EXT_W, EXT_H = 158.0, 80.0
SLOT_S = 86.0      # vertical pitch between stores
SLOT_E = 116.0     # vertical pitch between externals
ROWGAP = 92.0      # gap between process rows
STORE_X = 560.0    # store column centre (x) relative to process centre 0
EXT_X = -560.0     # external column centre (x)


def _layout_clusters(diagram, title=None):
    processes = [n for n in diagram.nodes if n.kind == PROCESS]
    # keep author order (P1..Pn) for top->down stacking
    processes.sort(key=lambda p: p.style.get("order", 0))

    members = {p.id: {"left": [], "right": []} for p in processes}
    for n in diagram.nodes:
        pid = n.style.get("proc")
        if pid in members and n.kind in (EXTERNAL, DATASTORE):
            members[pid][n.style.get("side", "right")].append(n)

    # --- size shapes to their text ---
    for p in processes:
        w, h = measure_label(p.label, font=13, min_w=PROC_W, min_h=PROC_H)
        p.w, p.h = max(PROC_W, w), max(PROC_H, h)
    for n in diagram.nodes:
        if n.kind == DATASTORE:
            w, _ = measure_label(n.label, font=12, min_w=STORE_W, min_h=STORE_H)
            n.w, n.h = max(STORE_W, w), STORE_H
        elif n.kind == EXTERNAL:
            w, h = measure_label(n.label, font=13, min_w=EXT_W, min_h=EXT_H)
            n.w, n.h = max(EXT_W, w), max(EXT_H, h)

    # --- stack rows top -> down ---
    y_cursor = 0.0
    prev_half = 0.0
    for i, p in enumerate(processes):
        stores = members[p.id]["right"]
        exts = members[p.id]["left"]
        store_span = max(0, len(stores) - 1) * SLOT_S
        ext_span = max(0, len(exts) - 1) * SLOT_E
        row_half = max(p.h / 2, store_span / 2 + STORE_H / 2,
                       ext_span / 2 + EXT_H / 2)
        if i == 0:
            y_center = 0.0
        else:
            y_center = y_cursor + prev_half + row_half + ROWGAP
        prev_half = row_half
        y_cursor = y_center

        p.x = -p.w / 2
        p.y = y_center - p.h / 2

        # stores: single right column, clean vertical fan
        for j, s in enumerate(stores):
            sy = y_center - store_span / 2 + j * SLOT_S
            s.x = STORE_X - s.w / 2
            s.y = sy - s.h / 2
        # externals: single left column
        for j, ex in enumerate(exts):
            ey = y_center - ext_span / 2 + j * SLOT_E
            ex.x = EXT_X - ex.w / 2
            ex.y = ey - ex.h / 2

    # --- floating flow labels, de-collided per nothing-global (whole diagram) ---
    labels: list[Node] = []
    li = 0
    node_by = {n.id: n for n in diagram.nodes}
    for e in diagram.edges:
        if not e.label:
            continue
        a = node_by.get(e.source)
        b = node_by.get(e.target)
        if not a or not b:
            continue
        mx = (a.cx + b.cx) / 2
        my = (a.cy + b.cy) / 2
        lab = make_label(f"_fl{li}", e.label, mx, my, font=11)
        lab.style["flow"] = "1"
        labels.append(lab)
        li += 1
    obstacles = [n for n in diagram.nodes if n.kind != "label"]
    de_collide_labels(labels, obstacles, passes=200, step=5.0, gap=6.0)
    diagram.nodes.extend(labels)

    t = Node(id="_title", kind="title",
             label=title or diagram.meta.get("title", diagram.name),
             w=760, h=40)
    minx = min(x.x for x in diagram.nodes)
    maxx = max(x.x + x.w for x in diagram.nodes)
    miny = min(x.y for x in diagram.nodes)
    t.x = (minx + maxx) / 2 - t.w / 2
    t.y = miny - 72
    diagram.nodes.append(t)

    normalize(diagram, margin=60)
    return diagram


def layout_dfd0(diagram, title=None):
    return _layout_clusters(diagram, title=title)


def layout_dfd1(diagram, title=None):
    return _layout_clusters(diagram, title=title)
