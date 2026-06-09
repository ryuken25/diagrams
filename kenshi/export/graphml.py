"""yEd-compatible GraphML exporter.

Emits yWorks-flavoured GraphML (``y:ShapeNode`` / ``y:PolyLineEdge`` with real
geometry, fills, labels and crow's-foot arrows) so the file opens **editable in
yEd** with shapes and positions intact — not as anonymous boxes. One file per
diagram.
"""
from __future__ import annotations

from xml.sax.saxutils import escape, quoteattr

from ..model import (PROCESS, EXTERNAL, DATASTORE, ENTITY, ATTRIBUTE,
                     RELATIONSHIP)

_SHAPE = {
    PROCESS: "ellipse",
    EXTERNAL: "rectangle",
    DATASTORE: "rectangle",
    ENTITY: "rectangle",
    ATTRIBUTE: "ellipse",
    RELATIONSHIP: "diamond",
    "label": "rectangle",
    "title": "rectangle",
}

_FILL = {
    PROCESS: "#FFFFFF",
    EXTERNAL: "#EEF2F7",
    DATASTORE: "#FFFFFF",
    ENTITY: "#FFFFFF",
    ATTRIBUTE: "#FFFFFF",
    RELATIONSHIP: "#FFFFFF",
    "label": "#FFFFFF",
    "title": "#FFFFFF",
}

_CROW = {
    "crowsfoot-one": "crows_foot_one_mandatory",
    "crowsfoot-many": "crows_foot_many_mandatory",
    "crowsfoot-one-many": "crows_foot_many_mandatory",
    "crowsfoot-zero-many": "crows_foot_many_optional",
    "crowsfoot-zero-one": "crows_foot_one_optional",
    "block": "standard",
    "none": "none",
}


def _arrow(name: str) -> str:
    return _CROW.get(name, "standard" if name == "block" else (name or "none"))


def _node_xml(nid: str, n) -> str:
    shape = _SHAPE.get(n.kind, "rectangle")
    fill = _FILL.get(n.kind, "#FFFFFF")
    transparent = "true" if n.kind == "title" else "false"
    border = "none" if n.kind in ("label", "title") else "line"
    border_w = "0.0" if n.kind in ("label", "title") else "1.0"
    font_style = "bold" if n.kind in ("title", PROCESS) else "plain"
    font_size = n.style.get("font", "12")
    if n.kind == "title":
        font_size = "18"
    underline = ' underlinedText="true"' if n.is_key else ""
    label_text = n.label or ""
    if n.kind == ENTITY and n.style.get("rows"):
        lines = [n.label, "─" * 16]
        for text, kind in n.style["rows"]:
            prefix = {"pk": "PK ", "fk": "FK "}.get(kind, "   ")
            lines.append(prefix + text)
        label_text = "\n".join(lines)
        font_style = "plain"
    label = escape(label_text)
    return (
        f'    <node id={quoteattr(nid)}>\n'
        f'      <data key="d_kind">{escape(n.kind)}</data>\n'
        f'      <data key="d_node">\n'
        f'        <y:ShapeNode>\n'
        f'          <y:Geometry height="{n.h:.1f}" width="{n.w:.1f}" '
        f'x="{n.x:.1f}" y="{n.y:.1f}"/>\n'
        f'          <y:Fill color="{fill}" transparent="{transparent}"/>\n'
        f'          <y:BorderStyle color="#1F3A5F" type="{border}" '
        f'width="{border_w}"/>\n'
        f'          <y:NodeLabel fontSize="{font_size}" fontStyle="{font_style}"'
        f' alignment="center"{underline} '
        f'modelName="internal" modelPosition="c" autoSizePolicy="content">'
        f'{label}</y:NodeLabel>\n'
        f'          <y:Shape type="{shape}"/>\n'
        f'        </y:ShapeNode>\n'
        f'      </data>\n'
        f'    </node>\n'
    )


def _edge_xml(eid: str, e, src: str, tgt: str) -> str:
    tarrow = _arrow(e.end_arrow)
    sarrow = _arrow(e.start_arrow)
    label = ""
    if e.label:
        label = (f'          <y:EdgeLabel fontSize="11" '
                 f'backgroundColor="#FFFFFF">{escape(e.label)}</y:EdgeLabel>\n')
    smoothed = "true" if e.routing == "orthogonal" else "false"
    return (
        f'    <edge id={quoteattr(eid)} source={quoteattr(src)} '
        f'target={quoteattr(tgt)}>\n'
        f'      <data key="d_edge">\n'
        f'        <y:PolyLineEdge>\n'
        f'          <y:LineStyle color="#1F3A5F" type="line" width="1.4"/>\n'
        f'          <y:Arrows source="{sarrow}" target="{tarrow}"/>\n'
        f'{label}'
        f'          <y:BendStyle smoothed="{smoothed}"/>\n'
        f'        </y:PolyLineEdge>\n'
        f'      </data>\n'
        f'    </edge>\n'
    )


def to_graphml(diagram) -> str:
    # safe, stable ids
    id_map = {n.id: f"n{i}" for i, n in enumerate(diagram.nodes)}
    nodes_xml = "".join(_node_xml(id_map[n.id], n) for n in diagram.nodes)
    edges_xml = ""
    for i, e in enumerate(diagram.edges):
        if e.source not in id_map or e.target not in id_map:
            continue
        edges_xml += _edge_xml(f"e{i}", e, id_map[e.source], id_map[e.target])
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
        '<graphml xmlns="http://graphml.graphdrawing.org/xmlns" '
        'xmlns:y="http://www.yworks.com/xml/graphml" '
        'xmlns:yed="http://www.yworks.com/xml/yed/3" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns '
        'http://www.yworks.com/xml/schema/graphml/1.1/ygraphml.xsd">\n'
        '  <key for="node" id="d_node" yfiles.type="nodegraphics"/>\n'
        '  <key for="edge" id="d_edge" yfiles.type="edgegraphics"/>\n'
        '  <key for="node" attr.name="kind" attr.type="string" id="d_kind"/>\n'
        f'  <graph edgedefault="directed" id={quoteattr(diagram.name)}>\n'
        + nodes_xml + edges_xml +
        '  </graph>\n'
        '</graphml>\n'
    )
