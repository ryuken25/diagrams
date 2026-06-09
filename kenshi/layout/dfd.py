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

    Each edge gets (1) distinct exit/entry PORTS on the perimeter of its two
    nodes (so parallel flows don't collapse onto one anchor), and (2) a UNIQUE
    vertical CHANNEL in the corridor between the process column and the
    external/store column — written as two waypoints ``[(ch_x, y_exit),
    (ch_x, y_entry)]``. The exporter reads ``exitX/exitY/entryX/entryY`` from
    ``edge.style`` and emits ``waypoints`` as an ``<Array as="points">``.

    The path of every routed edge is therefore: leave the source perimeter on a
    spread-out Y, run horizontally to its own channel, drop/climb vertically in
    that channel, then run horizontally into the target perimeter — two bends,
    no shared channels ("lika-liku sedikit, garis tidak menyatu").
    """
    node_by = {n.id: n for n in diagram.nodes}

    left, right, pp = [], [], []
    for e in diagram.edges:
        a, b = node_by.get(e.source), node_by.get(e.target)
        if not a or not b:
            continue
        if a.kind == PROCESS and b.kind == PROCESS:
            pp.append(e)
        elif a.kind == EXTERNAL or b.kind == EXTERNAL:
            left.append(e)
        elif a.kind == DATASTORE or b.kind == DATASTORE:
            right.append(e)

    # --- spread Y anchors along each used side of each node ---------------
    # groups: (node_id, side) -> list of [edge, end('source'|'target'), other_cy]
    # side codes: PL=process-left, PR=process-right, ER=external-right, SL=store-left
    groups: dict = {}

    def reg(node, side, e, end, other):
        groups.setdefault((node.id, side), []).append([e, end, other.cy])

    for e in left:
        a, b = node_by[e.source], node_by[e.target]
        proc = a if a.kind == PROCESS else b
        ext = b if proc is a else a
        reg(proc, "PL", e, "source" if a is proc else "target", ext)
        reg(ext, "ER", e, "source" if a is ext else "target", proc)
    for e in right:
        a, b = node_by[e.source], node_by[e.target]
        proc = a if a.kind == PROCESS else b
        st = b if proc is a else a
        reg(proc, "PR", e, "source" if a is proc else "target", st)
        reg(st, "SL", e, "source" if a is st else "target", proc)

    SIDE_X = {"PL": 0.0, "ER": 1.0, "PR": 1.0, "SL": 0.0}
    port: dict = {}   # edge_id -> {'source': (rx, ry), 'target': (rx, ry)}
    for (nid, side), items in groups.items():
        items.sort(key=lambda it: it[2])     # order by the other end's y
        n = len(items)
        rx = SIDE_X[side]
        for i, (e, end, _oy) in enumerate(items):
            ry = (i + 1) / (n + 1)            # even spread, never touching a corner
            port.setdefault(e.id, {})[end] = (rx, ry)

    def anchor(e, end):
        rx, ry = port[e.id][end]
        node = node_by[e.source if end == "source" else e.target]
        return node.x + rx * node.w, node.y + ry * node.h

    def write_ports(e):
        sx, sy = port[e.id]["source"]
        tx, ty = port[e.id]["target"]
        e.style["exitX"], e.style["exitY"] = f"{sx:.3f}", f"{sy:.3f}"
        e.style["entryX"], e.style["entryY"] = f"{tx:.3f}", f"{ty:.3f}"

    def proc_anchor_y(e):
        a = node_by[e.source]
        end = "source" if a.kind == PROCESS else "target"
        return anchor(e, end)[1]

    # --- assign a unique vertical channel per edge in each corridor -------
    def lay_channels(edges, lo, hi):
        # order channels by the edge midpoint y so adjacent rows use adjacent
        # channels -> fewer crossings; every edge still gets its own x.
        edges.sort(key=lambda e: (anchor(e, "source")[1] + anchor(e, "target")[1]) / 2)
        n = len(edges)
        for i, e in enumerate(edges):
            chx = lo + (hi - lo) * (i + 1) / (n + 1)
            s, t = anchor(e, "source"), anchor(e, "target")
            e.waypoints = [(chx, s[1]), (chx, t[1])]
            write_ports(e)

    if left:
        ext_right = max(x.x + x.w for x in exts) if exts else EXT_X
        proc_left = min(p.x for p in procs)
        lay_channels(left, ext_right + 26.0, proc_left - 26.0)
    if right:
        proc_right = max(p.x + p.w for p in procs)
        store_left = min(s.x for s in stores) if stores else STORE_X
        lay_channels(right, proc_right + 26.0, store_left - 26.0)

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

    # externals (left) & stores (right): align to the mean y of their processes
    for col, cx in ((exts, EXT_X), (stores, STORE_X)):
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

    # one floating data_/info_ label per edge, near the process end, de-collided
    labels: list[Node] = []
    li = 0
    for e in diagram.edges:
        if not e.label:
            continue
        a, b = node_by.get(e.source), node_by.get(e.target)
        if not a or not b:
            continue
        proc = a if a.kind == PROCESS else b
        other = b if proc is a else a
        if e.waypoints:
            # sit the label on the edge's own vertical channel (its opaque box
            # hides the line behind it); de_collide spreads parallels apart
            (chx, y0), (_chx2, y1) = e.waypoints[0], e.waypoints[1]
            lx, ly = chx, (y0 + y1) / 2
        else:
            lx = proc.cx + (other.cx - proc.cx) * 0.40
            ly = proc.cy + (other.cy - proc.cy) * 0.40
        labels.append(make_label(f"_fl{li}", e.label, lx, ly, font=10))
        li += 1
    de_collide_labels(labels, [n for n in diagram.nodes if n.kind != "label"],
                      passes=260, step=5.0, gap=7.0)
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
