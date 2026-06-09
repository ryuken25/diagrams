"""Generic, content-agnostic diagram builders.

Any project (MellogangVisuals, beauty-salon, an imported DB schema, …) feeds the
same neutral structures in and gets clean, overlap-free, editable diagrams out.
"""
from __future__ import annotations

from ..model import (Diagram, Node, Edge, Borders, ENTITY, ATTRIBUTE,
                     RELATIONSHIP, PROCESS, EXTERNAL, DATASTORE)
from ..layout import (layout_chen, layout_crowsfoot, layout_context,
                      layout_dfd0, layout_dfd1)


def _safe(s: str) -> str:
    return s.replace(" ", "_").replace("&", "and").replace("/", "_").strip("_")


def build_erd_chen(name, title, entities, relationships, order_fn=None) -> Diagram:
    """entities: {ename: (pk, [attrs])};  relationships: [(verb,parent,c1,child,c2)].

    ``order_fn`` (optional) overrides the ring order — pass the offline model's
    predictor for the 'AI tidy' path; ``None`` uses the deterministic engine.
    """
    d = Diagram(id=_safe(name), name=name, type="erd-chen", meta={"title": title})
    for ename, (pk, attrs) in entities.items():
        d.add(Node(id=ename, kind=ENTITY, label=ename))
        for a in [pk] + list(attrs):
            aid = f"{ename}.{a}"
            d.add(Node(id=aid, kind=ATTRIBUTE, label=a, is_key=(a == pk)))
            d.connect(Edge(id=f"sp.{aid}", source=ename, target=aid,
                           end_arrow="none"))
    for i, (verb, e1, c1, e2, c2) in enumerate(relationships):
        rid = f"R{i}_{_safe(verb)}"
        d.add(Node(id=rid, kind=RELATIONSHIP, label=verb.strip()))
        d.connect(Edge(id=f"rc.{rid}.1", source=e1, target=rid,
                       card_source=c1, end_arrow="none"))
        d.connect(Edge(id=f"rc.{rid}.2", source=e2, target=rid,
                       card_source=c2, end_arrow="none"))
    return layout_chen(d, order_fn=order_fn)


HEADER_H = 28.0
ROW_H = 22.0


def build_erd_crowsfoot(name, title, entities, relationships) -> Diagram:
    d = Diagram(id=_safe(name), name=name, type="erd-crowsfoot",
                meta={"title": title})
    fks: dict[str, list[str]] = {e: [] for e in entities}
    for (_v, parent, _c1, child, _c2) in relationships:
        pk = entities[parent][0]
        if child in fks and pk not in fks[child]:
            fks[child].append(pk)
    for ename, (pk, attrs) in entities.items():
        rows = [(pk, "pk")]
        fk_set = set(fks[ename])
        for a in attrs:
            rows.append((a, "fk" if a in fk_set else "attr"))
        for fk in fks[ename]:
            if fk not in attrs:
                rows.append((fk, "fk"))
        longest = max([len(ename)] + [len(t) + 4 for t, _k in rows])
        w = max(170, int(longest * 7.6) + 28)
        h = HEADER_H + len(rows) * ROW_H
        # rows are carried in style so the exporters/preview can draw a real
        # table (header band + separated, marked rows) instead of flat text.
        d.add(Node(id=ename, kind=ENTITY, label=ename, w=w, h=h,
                   style={"rows": rows, "table": "1"}))
    for (verb, parent, _c1, child, _c2) in relationships:
        d.connect(Edge(id=f"fk.{_safe(verb)}.{child}", source=parent,
                       target=child, label=verb.strip(),
                       start_arrow="crowsfoot-one", end_arrow="crowsfoot-many",
                       routing="orthogonal"))
    return layout_crowsfoot(d)


def build_context(name, title, system_label, actors, flows) -> Diagram:
    """actors: [str];  flows: [(src, dst, label)] using actor names or 'SYS'."""
    d = Diagram(id=_safe(name), name=name, type="dfd-context",
                meta={"title": title})
    d.add(Node(id="SYS", kind=PROCESS, label=system_label))
    for a in actors:
        d.add(Node(id=a, kind=EXTERNAL, label=a))
    for i, (s, t, lab) in enumerate(flows):
        d.connect(Edge(id=f"cf{i}", source=s, target=t, label=lab))
    return layout_context(d)


def build_dfd(data) -> Diagram:
    """Per-process-cluster DFD (Level 0 or Level 1).

    data keys: id, name, type ('dfd-level0'|'dfd-level1'), title,
        procs:[(pid,label)], store_names:{Dn:label},
        ext:{pid:[(actor,[(label,'to'|'from')])]},
        store:{pid:[(Dn,'',[(label,'to'|'from')])]},
        pp:[(src,dst,label)]
    """
    store_names = data.get("store_names", {})
    d = Diagram(id=data["id"], name=data["name"], type=data["type"],
                meta={"title": data["title"]})
    for order, (pid, plabel) in enumerate(data["procs"]):
        d.add(Node(id=pid, kind=PROCESS, label=plabel, style={"order": order}))

    ext_use: dict[str, int] = {}
    store_use: dict[str, int] = {}
    for pid in [p[0] for p in data["procs"]]:
        for (actor, _f) in data.get("ext", {}).get(pid, []):
            ext_use[actor] = ext_use.get(actor, 0) + 1
        for (sid, _nm, _f) in data.get("store", {}).get(pid, []):
            store_use[sid] = store_use.get(sid, 0) + 1

    def eid(pid, side, key):
        return f"{pid}__{side}__{key}"

    def balance(flows, base):
        """Guarantee both directions on a connection (DFD data goes both ways).

        Every external / process / data store must have an input AND an output
        flow; we synthesise the missing direction with the academic data_/info_
        convention ("Data X" in, "Info X" out)."""
        flows = list(flows)
        dirs = {dr for _l, dr in flows}
        if "to" not in dirs:
            flows.append((f"Data {base}", "to"))
        if "from" not in dirs:
            flows.append((f"Info {base}", "from"))
        return flows

    for pid in [p[0] for p in data["procs"]]:
        for (actor, flows) in data.get("ext", {}).get(pid, []):
            nid = eid(pid, "L", _safe(actor))
            dup = actor if ext_use.get(actor, 0) > 1 else None
            d.add(Node(id=nid, kind=EXTERNAL, label=actor, duplicate_of=dup,
                       style={"proc": pid, "side": "left"}))
            for j, (lab, direction) in enumerate(balance(flows, actor)):
                s, t = (nid, pid) if direction == "to" else (pid, nid)
                d.connect(Edge(id=f"e.{nid}.{j}", source=s, target=t, label=lab))
        for (sid, _nm, flows) in data.get("store", {}).get(pid, []):
            nid = eid(pid, "R", sid)
            dup = sid if store_use.get(sid, 0) > 1 else None
            base = store_names.get(sid, sid).split("  ")[-1]
            d.add(Node(id=nid, kind=DATASTORE, label=store_names.get(sid, sid),
                       borders=Borders.open_store(), duplicate_of=dup,
                       store_id=sid, style={"proc": pid, "side": "right"}))
            for j, (lab, direction) in enumerate(balance(flows, base)):
                s, t = (pid, nid) if direction == "to" else (nid, pid)
                d.connect(Edge(id=f"e.{nid}.{j}", source=s, target=t, label=lab))
    for j, (s, t, lab) in enumerate(data.get("pp", [])):
        d.connect(Edge(id=f"pp{j}", source=s, target=t, label=lab))

    if data["type"] == "dfd-level0":
        return layout_dfd0(d, title=data["title"])
    return layout_dfd1(d, title=data["title"])
