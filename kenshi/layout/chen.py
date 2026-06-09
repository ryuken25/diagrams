"""ERD Chen — radial "sunburst" layout.

Entities sit on a ring (cyclic order optimised to minimise chord crossings),
each entity's attributes fan outward in its own angular sector (two staggered
arcs so dense entities never clip), relationship diamonds sit on the straight
chord between their two entities, and cardinality labels sit at the entity end.
"""
from __future__ import annotations

import math

from ..model import Node, ENTITY, ATTRIBUTE, RELATIONSHIP
from ..geometry import measure_label, segments_cross, normalize
from .shared import make_label, de_collide_labels


def _neighbors(diagram, node_id):
    out = []
    for e in diagram.edges:
        if e.source == node_id:
            out.append((e.target, e))
        elif e.target == node_id:
            out.append((e.source, e))
    return out


def ring_crossings(order, pairs):
    """Chord crossings when nodes are placed on a ring in ``order``.

    ``order`` is a list of node ids/indices; ``pairs`` is a list of (a, b)
    relationship endpoints (same id space as ``order``).
    """
    pos = {v: i for i, v in enumerate(order)}
    n = len(order)
    pts = [(math.cos(2 * math.pi * i / n), math.sin(2 * math.pi * i / n))
           for i in range(n)]
    chords = [(pts[pos[a]], pts[pos[b]]) for a, b in pairs
              if a in pos and b in pos]
    c = 0
    for i in range(len(chords)):
        for j in range(i + 1, len(chords)):
            if segments_cross(*chords[i], *chords[j]):
                c += 1
    return c


def crossing_order(node_ids, pairs, max_passes=None):
    """2-opt over the cyclic order to minimise chord crossings.

    Seeded by the given ``node_ids`` order (so the offline model can pass its
    predicted order for a cheap, capped polish). ``max_passes=None`` runs to a
    local optimum (the deterministic teacher / engine default).
    Returns (best_order, best_crossings).
    """
    best = list(node_ids)
    best_c = ring_crossings(best, pairs)
    passes = 0
    improved = True
    while improved and (max_passes is None or passes < max_passes):
        improved = False
        passes += 1
        for i in range(1, len(best) - 1):
            for j in range(i + 1, len(best)):
                cand = best[:i] + best[i:j + 1][::-1] + best[j + 1:]
                c = ring_crossings(cand, pairs)
                if c < best_c:
                    best, best_c = cand, c
                    improved = True
    return best, best_c


def _order_entities(entities, rel_pairs):
    ids = [e.id for e in entities]
    return crossing_order(ids, rel_pairs)


def layout_chen(diagram, r_e: float = 560.0, order_fn=None):
    """Lay out an ERD-Chen diagram.

    ``order_fn(node_ids, pairs) -> order`` overrides the entity ring order (e.g.
    the offline ONNX model). When ``None`` the deterministic crossing-minimising
    engine is used. Either way the placer is identical, so output is always
    overlap-free; only the ordering decision differs.
    """
    entities = [n for n in diagram.nodes if n.kind == ENTITY]
    rels = [n for n in diagram.nodes if n.kind == RELATIONSHIP]
    n = len(entities)
    if n == 0:
        return diagram

    # --- relationship chord pairs (entity-entity) ---
    rel_entity = {}
    for r in rels:
        ents = [nid for nid, _ in _neighbors(diagram, r.id)
                if any(x.id == nid and x.kind == ENTITY for x in diagram.nodes)]
        rel_entity[r.id] = ents[:2]
    rel_pairs = [tuple(v) for v in rel_entity.values() if len(v) == 2]

    if order_fn is not None:
        order = order_fn([e.id for e in entities], rel_pairs)
    else:
        order, _cross = _order_entities(entities, rel_pairs)
    ent_by_id = {e.id: e for e in entities}

    # --- size entities to their label ---
    for e in entities:
        w, h = measure_label(e.label, font=14, min_w=120, min_h=52)
        e.w, e.h = max(120, w), 52

    # --- pre-measure attribute fans to pick a radius that never clips ---
    attrs_of = {}
    for e in entities:
        a = [ent_by_id_get(diagram, nid) for nid, _ in _neighbors(diagram, e.id)]
        attrs_of[e.id] = [x for x in a if x and x.kind == ATTRIBUTE]
    sector = 0.82 * (2 * math.pi / n)
    # adaptive #rows per entity so dense entities spread radially (more rows),
    # keeping each arc's column count small -> compact, no clipping, balanced.
    COL_CAP = 6
    rows_of = {e.id: max(2, math.ceil(len(attrs_of[e.id]) / COL_CAP))
               for e in entities}
    max_cols = max((math.ceil(len(attrs_of[e.id]) / rows_of[e.id])
                    for e in entities), default=1)
    needed_arc = max(1, (max_cols - 1)) * 132.0
    # radius wide enough that the densest sector's arc fits without clipping
    r_a = max(r_e + 190.0, needed_arc / max(sector, 0.1))

    cx, cy = 0.0, 0.0
    # --- place entities on the ring ---
    for i, eid in enumerate(order):
        ang = 2 * math.pi * i / n - math.pi / 2
        e = ent_by_id[eid]
        e.x = cx + r_e * math.cos(ang) - e.w / 2
        e.y = cy + r_e * math.sin(ang) - e.h / 2
        e.style["_angle"] = ang

    # --- fan attributes in each entity's sector, two staggered arcs ---
    for eid in order:
        e = ent_by_id[eid]
        ang = e.style["_angle"]
        alist = attrs_of[eid]
        k = len(alist)
        if k == 0:
            continue
        n_rows = rows_of[eid]
        cols = math.ceil(k / n_rows)
        for idx, attr in enumerate(alist):
            w, h = measure_label(attr.label, font=12, min_w=96, min_h=42)
            attr.w, attr.h = max(96, w), 42
            row = idx % n_rows
            col = idx // n_rows
            # spread columns across the sector, centred on the entity angle
            frac = (col / (cols - 1) - 0.5) if cols > 1 else 0.0
            a_ang = ang + frac * sector
            rad = r_a + row * 110.0           # wider radial pitch -> no kissing
            attr.x = cx + rad * math.cos(a_ang) - attr.w / 2
            attr.y = cy + rad * math.sin(a_ang) - attr.h / 2

    # --- relationship diamonds on the chord between their two entities ---
    placed_centers = []
    for r in rels:
        ents = rel_entity.get(r.id, [])
        w, h = measure_label(r.label, font=12, min_w=120, min_h=74)
        r.w, r.h = max(120, w), 74
        if len(ents) < 2:
            r.x = cx - r.w / 2
            r.y = cy - r.h / 2
            continue
        e1, e2 = ent_by_id[ents[0]], ent_by_id[ents[1]]
        mx = (e1.cx + e2.cx) / 2
        my = (e1.cy + e2.cy) / 2
        # perpendicular nudge to avoid stacking diamonds on near-parallel chords
        dx, dy = e2.cx - e1.cx, e2.cy - e1.cy
        length = math.hypot(dx, dy) or 1.0
        px, py = -dy / length, dx / length
        nudge = 0.0
        for (ox, oy) in placed_centers:
            if math.hypot(mx - ox, my - oy) < 150:
                nudge += 95.0
        mx += px * nudge
        my += py * nudge
        placed_centers.append((mx, my))
        r.x = mx - r.w / 2
        r.y = my - r.h / 2

    # --- spread attributes & diamonds so nothing clips (entities stay on ring) ---
    movable = [n for n in diagram.nodes if n.kind in (ATTRIBUTE, RELATIONSHIP)]
    fixed = [n for n in diagram.nodes if n.kind == ENTITY]
    de_collide_labels(movable, fixed, passes=300, step=7.0, gap=18.0)

    # --- cardinality labels at the entity end of each connector ---
    labels: list[Node] = []
    li = 0
    for e in diagram.edges:
        if not e.card_target and not e.card_source:
            continue
        a = ent_by_id_get(diagram, e.source)
        b = ent_by_id_get(diagram, e.target)
        if not a or not b:
            continue
        # cardinality sits near whichever endpoint is the entity
        for node, other, card in ((a, b, e.card_source), (b, a, e.card_target)):
            if not card or node.kind != ENTITY:
                continue
            t = 0.22
            lx = node.cx + (other.cx - node.cx) * t
            ly = node.cy + (other.cy - node.cy) * t
            lab = make_label(f"_card{li}", card, lx, ly, font=13)
            lab.style["card"] = "1"
            labels.append(lab)
            li += 1

    obstacles = [x for x in diagram.nodes if x.kind != "label"]
    de_collide_labels(labels, obstacles)
    diagram.nodes.extend(labels)

    # --- title ---
    title = Node(id="_title", kind="title",
                 label=diagram.meta.get("title", diagram.name),
                 w=620, h=40)
    minx = min(x.x for x in diagram.nodes)
    maxx = max(x.x + x.w for x in diagram.nodes)
    miny = min(x.y for x in diagram.nodes)
    title.x = (minx + maxx) / 2 - title.w / 2
    title.y = miny - 80
    diagram.nodes.append(title)

    normalize(diagram, margin=60)
    return diagram


def ent_by_id_get(diagram, nid):
    for x in diagram.nodes:
        if x.id == nid:
            return x
    return None
