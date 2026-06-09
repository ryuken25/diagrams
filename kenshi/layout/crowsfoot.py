"""ERD Crow's Foot — layered orthogonal tables.

Entities are rendered as tables (title bar + attribute rows; PK marked 🔑, FK
marked FK — the content builder bakes this into the node label). Entities are
ordered into layers by the FK graph (longest-path layering + barycenter sweeps),
placed in columns, and FK edges are routed orthogonally with crow's-foot ends.
"""
from __future__ import annotations

from ..model import ENTITY
from ..geometry import normalize, resolve_node_overlaps

COL_GAP = 150.0
ROW_GAP = 70.0


def _layers_from_fk(entities, edges):
    """Longest-path layering: parents (1-side) left, children (N-side) right."""
    ids = [e.id for e in entities]
    children = {i: [] for i in ids}     # parent -> [children]
    indeg = {i: 0 for i in ids}
    for e in edges:
        # edge encodes parent(source, card '1') -> child(target, card 'N')
        if e.source in children and e.target in indeg:
            children[e.source].append(e.target)
            indeg[e.target] += 1
    layer = {i: 0 for i in ids}
    # Kahn-style longest path
    from collections import deque
    q = deque([i for i in ids if indeg[i] == 0])
    seen_indeg = dict(indeg)
    while q:
        u = q.popleft()
        for v in children[u]:
            layer[v] = max(layer[v], layer[u] + 1)
            seen_indeg[v] -= 1
            if seen_indeg[v] == 0:
                q.append(v)
    return layer


def layout_crowsfoot(diagram):
    entities = [n for n in diagram.nodes if n.kind == ENTITY]
    if not entities:
        return diagram
    layer = _layers_from_fk(entities, diagram.edges)

    cols: dict[int, list] = {}
    for e in entities:
        cols.setdefault(layer[e.id], []).append(e)

    x = 0.0
    for li in sorted(cols):
        col = cols[li]
        col_w = max(e.w for e in col)
        y = 0.0
        for e in col:
            e.x = x + (col_w - e.w) / 2
            e.y = y
            y += e.h + ROW_GAP
        x += col_w + COL_GAP

    # vertically centre each column around the tallest column's mid
    heights = {}
    for li, col in cols.items():
        top = min(e.y for e in col)
        bot = max(e.y + e.h for e in col)
        heights[li] = (top, bot)
    mid = max((b - t) for t, b in heights.values()) / 2
    for li, col in cols.items():
        top, bot = heights[li]
        shift = mid - (top + bot) / 2
        for e in col:
            e.y += shift

    for e in diagram.edges:
        e.routing = "orthogonal"

    resolve_node_overlaps(entities, gap=40)
    normalize(diagram, margin=60)
    return diagram
