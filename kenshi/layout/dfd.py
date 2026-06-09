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
        e.label = ""        # the floating node IS the label; avoid draw.io doubling it
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


def _spread_column(nodes, min_gap):
    """1-D overlap removal: keep desired order, push apart to keep min vertical gap."""
    nodes.sort(key=lambda n: n.style.get("_wy", n.cy))
    for i in range(1, len(nodes)):
        prev = nodes[i - 1]
        cur = nodes[i]
        need = prev.y + prev.h + min_gap
        if cur.y < need:
            cur.y = need


def _route_ortho(diagram, procs, exts, stores, EXT_X, STORE_X):
    """Explicit orthogonal router for the single-node DFD.

    Every process<->peripheral (external/data-store) edge picks the *most
    efficient ENTRY SIDE* on the peripheral node instead of cramming the whole
    bus onto one face:
        * peripheral roughly level with the process -> facing side (external
          RIGHT / store LEFT), routed through a unique vertical channel in the
          corridor between the two columns;
        * process well ABOVE the peripheral -> the peripheral's TOP edge;
        * process well BELOW -> the peripheral's BOTTOM edge.
    Top/bottom entries drop straight down/up a channel that sits inside the
    peripheral's own x-span, so flows fan across three faces (like a hand-drawn
    DFD) rather than stacking into one comb. Ports are written as
    exitX/exitY/entryX/entryY and the path as two waypoints.
    """
    node_by = {n.id: n for n in diagram.nodes}

    pp = []
    info: dict = {}          # eid -> {proc, periph, on_right, is_store, side}
    VS = 24.0                # small slack: a store fans to top/bottom as soon as
    #                          its process isn't roughly level with it
    for e in diagram.edges:
        a, b = node_by.get(e.source), node_by.get(e.target)
        if not a or not b:
            continue
        if a.kind == PROCESS and b.kind == PROCESS:
            pp.append(e)
            continue
        if a.kind in (EXTERNAL, DATASTORE):
            periph, proc = a, b
        elif b.kind in (EXTERNAL, DATASTORE):
            periph, proc = b, a
        else:
            continue
        if proc.kind != PROCESS:
            continue
        on_right = periph.cx >= proc.cx          # which column the peripheral sits in
        is_store = periph.kind == DATASTORE
        dy = proc.cy - periph.cy
        # Data stores (short, well-spaced) fan to top/bottom; externals (tall,
        # may be stacked) stay facing-side so a vertical channel never pierces a
        # neighbouring box.
        if is_store and dy < -(periph.h / 2 + VS):
            side = "T"
        elif is_store and dy > (periph.h / 2 + VS):
            side = "B"
        else:
            side = "F"
        info[e.id] = {"proc": proc, "periph": periph, "on_right": on_right,
                      "is_store": is_store, "edge": e, "side": side}

    # --- spread ports: process facing side, and each used peripheral face ---
    pgroups: dict = {}       # (proc.id, 'L'|'R') -> [eid]
    sgroups: dict = {}       # (periph.id, side)  -> [eid]
    for eid, d in info.items():
        pgroups.setdefault((d["proc"].id, "R" if d["on_right"] else "L"), []).append(eid)
        sgroups.setdefault((d["periph"].id, d["side"]), []).append(eid)

    port: dict = {}          # eid -> {'proc': (rx, ry), 'periph': (rx, ry)}
    for (pid, lr), eids in pgroups.items():
        eids.sort(key=lambda eid: info[eid]["periph"].cy)
        rx = 1.0 if lr == "R" else 0.0
        n = len(eids)
        for i, eid in enumerate(eids):
            port.setdefault(eid, {})["proc"] = (rx, (i + 1) / (n + 1))
    for (sid, side), eids in sgroups.items():
        on_right = info[eids[0]]["on_right"]
        if side == "F":
            rx = 0.0 if on_right else 1.0    # right peripheral faces left, & vv
            eids.sort(key=lambda eid: info[eid]["proc"].cy)
            n = len(eids)
            for i, eid in enumerate(eids):
                port.setdefault(eid, {})["periph"] = (rx, (i + 1) / (n + 1))
        else:
            ry = 0.0 if side == "T" else 1.0
            eids.sort(key=lambda eid: info[eid]["proc"].cx)
            n = len(eids)
            for i, eid in enumerate(eids):
                port.setdefault(eid, {})["periph"] = ((i + 1) / (n + 1), ry)

    def anchor(node, frac):
        return node.x + frac[0] * node.w, node.y + frac[1] * node.h

    def commit(e, chx):
        d = info[e.id]
        pa = anchor(d["proc"], port[e.id]["proc"])
        ca = anchor(d["periph"], port[e.id]["periph"])
        a = node_by[e.source]
        if a.kind == PROCESS:                       # process -> peripheral
            (sx, sy), (tx, ty) = port[e.id]["proc"], port[e.id]["periph"]
            e.waypoints = [(chx, pa[1]), (chx, ca[1])]
        else:                                       # peripheral -> process
            (sx, sy), (tx, ty) = port[e.id]["periph"], port[e.id]["proc"]
            e.waypoints = [(chx, ca[1]), (chx, pa[1])]
        e.style["exitX"], e.style["exitY"] = f"{sx:.3f}", f"{sy:.3f}"
        e.style["entryX"], e.style["entryY"] = f"{tx:.3f}", f"{ty:.3f}"

    # facing edges: unique channel in their column corridor (left vs right);
    # top/bottom edges: channel sits at the peripheral port's own x
    def lay_corridor(eids, lo, hi):
        eids.sort(key=lambda eid: (anchor(info[eid]["proc"], port[eid]["proc"])[1]
                                   + anchor(info[eid]["periph"], port[eid]["periph"])[1]) / 2)
        n = len(eids)
        for i, eid in enumerate(eids):
            commit(info[eid]["edge"], lo + (hi - lo) * (i + 1) / (n + 1))

    left_F = [eid for eid, d in info.items() if d["side"] == "F" and not d["on_right"]]
    right_F = [eid for eid, d in info.items() if d["side"] == "F" and d["on_right"]]
    if left_F:
        lp = [info[eid]["periph"] for eid in left_F]
        lay_corridor(left_F, max(p.x + p.w for p in lp) + 26.0,
                     min(p.x for p in procs) - 26.0)
    if right_F:
        rp = [info[eid]["periph"] for eid in right_F]
        lay_corridor(right_F, max(p.x + p.w for p in procs) + 26.0,
                     min(p.x for p in rp) - 26.0)
    for eid, d in info.items():
        if d["side"] in ("T", "B"):
            commit(d["edge"], anchor(d["periph"], port[eid]["periph"])[0])

    # process -> process: straight down the centre column
    for e in pp:
        e.style["exitX"], e.style["exitY"] = "0.5", "1"
        e.style["entryX"], e.style["entryY"] = "0.5", "0"
        e.waypoints = []


def layout_dfd_ortho(diagram, title=None):
    """Chelisnet-style: single externals (left), processes (centre column),
    single data stores (right); orthogonal edges. Overlap-free by column."""
    procs = [n for n in diagram.nodes if n.kind == PROCESS]
    procs.sort(key=lambda p: p.style.get("order", 0))
    exts = [n for n in diagram.nodes if n.kind == EXTERNAL]
    stores = [n for n in diagram.nodes if n.kind == DATASTORE]

    for p in procs:
        w, h = measure_label(p.label, font=13, min_w=PROC_W, min_h=PROC_H)
        p.w, p.h = max(PROC_W, w), max(PROC_H, h)
    for e in exts:
        w, h = measure_label(e.label, font=13, min_w=EXT_W, min_h=EXT_H)
        e.w, e.h = max(EXT_W, w), max(EXT_H, h)
    for s in stores:
        w, _ = measure_label(s.label, font=12, min_w=STORE_W, min_h=STORE_H)
        s.w, s.h = max(STORE_W, w), STORE_H

    EXT_X, STORE_X, VGAP = -780.0, 780.0, 132.0
    # process column
    y = 0.0
    for p in procs:
        p.x = -p.w / 2
        p.y = y
        y += p.h + VGAP

    node_by = {n.id: n for n in diagram.nodes}

    def connected_procs(node):
        ys = []
        for e in diagram.edges:
            other = None
            if e.source == node.id:
                other = node_by.get(e.target)
            elif e.target == node.id:
                other = node_by.get(e.source)
            if other is not None and other.kind == PROCESS:
                ys.append(other.cy)
        return ys

    # Split externals across BOTH side columns. With stores fanning to their
    # top/bottom the right corridor runs nearly empty, so the heavier externals
    # are load-balanced onto whichever side currently carries fewer facing flows
    # — this relieves the single congested "comb" on the left.
    def edge_count(n):
        return sum(1 for e in diagram.edges if n.id in (e.source, e.target))

    left_ext, right_ext = [], []
    ll, rl = 0, len(stores)            # seed right with the store facing baseline
    for ex in sorted(exts, key=lambda x: -edge_count(x)):
        if ll <= rl:
            left_ext.append(ex)
            ll += edge_count(ex)
        else:
            right_ext.append(ex)
            rl += edge_count(ex)

    for col, cx in ((left_ext, EXT_X), (right_ext + stores, STORE_X)):
        for n in col:
            ys = connected_procs(n)
            wy = sum(ys) / len(ys) if ys else 0.0
            n.style["_wy"] = wy
            n.x = cx - n.w / 2
            n.y = wy - n.h / 2
        _spread_column(col, min_gap=46.0)
        for n in col:
            n.x = cx - n.w / 2

    # explicit orthogonal routing: per-edge ports + unique vertical channels
    _route_ortho(diagram, procs, exts, stores, EXT_X, STORE_X)

    # one INLINE data_/info_ label per edge — sat on the edge's longest
    # horizontal run (its opaque box hides the line) so the text reads along the
    # flow like a hand-drawn DFD, then lightly de-collided to break ties.
    labels: list[Node] = []
    li = 0
    for e in diagram.edges:
        if not e.label:
            continue
        a, b = node_by.get(e.source), node_by.get(e.target)
        if not a or not b:
            continue
        if "exitX" in e.style and "entryX" in e.style:
            pts = ([(a.x + float(e.style["exitX"]) * a.w,
                     a.y + float(e.style["exitY"]) * a.h)]
                   + list(e.waypoints)
                   + [(b.x + float(e.style["entryX"]) * b.w,
                       b.y + float(e.style["entryY"]) * b.h)])
        else:
            pts = [(a.cx, a.cy), (b.cx, b.cy)]
        lx = ly = None
        best = -1.0
        for (p, q) in zip(pts, pts[1:]):            # longest horizontal segment
            if abs(p[1] - q[1]) < 1.5 and abs(q[0] - p[0]) > best:
                best = abs(q[0] - p[0])
                lx, ly = (p[0] + q[0]) / 2, p[1]
        if lx is None:                               # purely vertical (pp) edge
            lx = (pts[0][0] + pts[-1][0]) / 2
            ly = (pts[0][1] + pts[-1][1]) / 2
        labels.append(make_label(f"_fl{li}", e.label, lx, ly, font=10))
        e.label = ""        # the floating node IS the label; avoid draw.io doubling it
        li += 1
    de_collide_labels(labels, [n for n in diagram.nodes if n.kind != "label"],
                      passes=160, step=5.0, gap=6.0)
    diagram.nodes.extend(labels)

    t = Node(id="_title", kind="title",
             label=title or diagram.meta.get("title", diagram.name),
             w=760, h=40)
    minx = min(x.x for x in diagram.nodes)
    maxx = max(x.x + x.w for x in diagram.nodes)
    miny = min(x.y for x in diagram.nodes)
    t.x = (minx + maxx) / 2 - t.w / 2
    t.y = miny - 76
    diagram.nodes.append(t)
    normalize(diagram, margin=60)
    return diagram


def layout_dfd0(diagram, title=None):
    return _layout_clusters(diagram, title=title)


def layout_dfd1(diagram, title=None):
    return _layout_clusters(diagram, title=title)
