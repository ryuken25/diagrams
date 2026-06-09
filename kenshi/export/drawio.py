"""draw.io (mxGraphModel) exporter.

Emits a multi-page ``mxfile`` (one page per diagram) that opens fully editable in
app.diagrams.net or the desktop app. Key choices:

* Edges are written **first** (so they render *under* the opaque shapes — a line
  crossing an unrelated shape is hidden and reads clean), then shapes, then the
  floating labels **last** (on top, each with an opaque white box).
* Edges connect to their source/target **cells without fixed exit/entry ports**,
  so draw.io anchors them on whichever side faces the other shape — flows can
  arrive from the top, bottom, left or right (not only left<->right).
* Data stores use ``shape=partialRectangle`` (top+bottom only) for the open-box
  look; duplicated instances get the extra "double left edge" / corner-diagonal
  marks as separate line cells.
"""
from __future__ import annotations

import html
from xml.sax.saxutils import quoteattr

from ..model import (PROCESS, EXTERNAL, DATASTORE, ENTITY, ATTRIBUTE,
                     RELATIONSHIP)

EDGE_NAVY = "#1F3A5F"

_CROW = {
    "crowsfoot-one": "ERone",
    "crowsfoot-many": "ERmany",
    "crowsfoot-one-many": "ERoneToMany",
    "crowsfoot-zero-many": "ERzeroToMany",
    "crowsfoot-zero-one": "ERzeroToOne",
    "block": "block",
    "none": "none",
}


def _esc(s: str) -> str:
    return html.escape(s or "", quote=True).replace("\n", "&#10;")


def _node_style(n) -> str:
    k = n.kind
    if k == PROCESS:
        return ("ellipse;whiteSpace=wrap;html=1;fillColor=#FFFFFF;"
                "strokeColor=#1F3A5F;fontSize=13;fontStyle=1;verticalAlign=middle;")
    if k == EXTERNAL:
        return ("rounded=0;whiteSpace=wrap;html=1;fillColor=#EEF2F7;"
                "strokeColor=#1F3A5F;fontSize=13;")
    if k == DATASTORE:
        return ("shape=partialRectangle;top=1;bottom=1;left=0;right=0;"
                "whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#1F3A5F;"
                "fontSize=12;align=center;")
    if k == ENTITY:
        align = "left" if "\n" in n.label else "center"
        valign = "top" if "\n" in n.label else "middle"
        return (f"rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;"
                f"strokeColor=#1F3A5F;fontSize=12;align={align};"
                f"verticalAlign={valign};spacingLeft=6;spacingTop=4;")
    if k == ATTRIBUTE:
        fs = "4" if n.is_key else "0"   # 4 = underline
        return ("ellipse;whiteSpace=wrap;html=1;fillColor=#FFFFFF;"
                f"strokeColor=#1F3A5F;fontSize=12;fontStyle={fs};")
    if k == RELATIONSHIP:
        return ("rhombus;whiteSpace=wrap;html=1;fillColor=#FFFFFF;"
                "strokeColor=#1F3A5F;fontSize=12;")
    if k == "title":
        return ("text;html=1;align=center;verticalAlign=middle;fontSize=18;"
                "fontStyle=1;strokeColor=none;fillColor=none;")
    if k == "label":
        fs = n.style.get("font", "11")
        return ("text;html=1;align=center;verticalAlign=middle;"
                f"fontSize={fs};rounded=0;fillColor=#FFFFFF;strokeColor=none;"
                "whiteSpace=wrap;spacing=2;")
    return "whiteSpace=wrap;html=1;"


def _edge_style(e) -> str:
    end = _CROW.get(e.end_arrow, e.end_arrow or "block")
    start = _CROW.get(e.start_arrow, e.start_arrow or "none")
    base = ("html=1;rounded=0;strokeColor=#1F3A5F;strokeWidth=1.4;"
            f"endArrow={end};startArrow={start};")
    if e.routing == "orthogonal":
        base += "edgeStyle=orthogonalEdgeStyle;"
    else:
        base += "edgeStyle=none;"
    return base


HEADER_H = 28.0
ROW_H = 22.0


def _table_cells(n, parent="1") -> str:
    """Render a crow's-foot entity as a real table: dark header + marked rows."""
    rows = n.style.get("rows", [])
    cells = [
        f'<mxCell id={quoteattr(n.id)} value="{_esc(n.label)}" '
        f'style="rounded=0;whiteSpace=wrap;html=1;fillColor=#1F3A5F;'
        f'fontColor=#FFFFFF;fontStyle=1;strokeColor=#1F3A5F;fontSize=13;'
        f'verticalAlign=middle;" vertex="1" parent="{parent}">'
        f'<mxGeometry x="{n.x:.1f}" y="{n.y:.1f}" width="{n.w:.1f}" '
        f'height="{HEADER_H:.1f}" as="geometry"/></mxCell>'
    ]
    for i, (text, kind) in enumerate(rows):
        y = n.y + HEADER_H + i * ROW_H
        if kind == "pk":
            mark, fs = "PK  ", 5      # bold+underline
        elif kind == "fk":
            mark, fs = "FK  ", 2      # italic
        else:
            mark, fs = "      ", 0
        cells.append(
            f'<mxCell id={quoteattr(n.id + f".r{i}")} '
            f'value="{_esc(mark + text)}" '
            f'style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;'
            f'strokeColor=#1F3A5F;align=left;verticalAlign=middle;spacingLeft=8;'
            f'fontSize=12;fontStyle={fs};" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{n.x:.1f}" y="{y:.1f}" width="{n.w:.1f}" '
            f'height="{ROW_H:.1f}" as="geometry"/></mxCell>'
        )
    return "".join(cells)


def _cell_node(n, parent="1") -> str:
    if n.kind == ENTITY and n.style.get("table"):
        return _table_cells(n, parent)
    cells = []
    cells.append(
        f'<mxCell id={quoteattr(n.id)} value="{_esc(n.label)}" '
        f'style="{_node_style(n)}" vertex="1" parent="{parent}">'
        f'<mxGeometry x="{n.x:.1f}" y="{n.y:.1f}" width="{n.w:.1f}" '
        f'height="{n.h:.1f}" as="geometry"/></mxCell>'
    )
    # duplication marks
    if n.duplicate_of and n.kind == DATASTORE:
        lx = n.x + 7
        cells.append(
            f'<mxCell id={quoteattr(n.id + "_dup")} value="" '
            f'style="endArrow=none;html=1;strokeColor=#1F3A5F;" edge="1" '
            f'parent="{parent}"><mxGeometry relative="1" as="geometry">'
            f'<mxPoint x="{lx:.1f}" y="{n.y:.1f}" as="sourcePoint"/>'
            f'<mxPoint x="{lx:.1f}" y="{n.y + n.h:.1f}" as="targetPoint"/>'
            f'</mxGeometry></mxCell>'
        )
    if n.duplicate_of and n.kind == EXTERNAL:
        cells.append(
            f'<mxCell id={quoteattr(n.id + "_dup")} value="" '
            f'style="endArrow=none;html=1;strokeColor=#1F3A5F;" edge="1" '
            f'parent="{parent}"><mxGeometry relative="1" as="geometry">'
            f'<mxPoint x="{n.x:.1f}" y="{n.y + 16:.1f}" as="sourcePoint"/>'
            f'<mxPoint x="{n.x + 16:.1f}" y="{n.y:.1f}" as="targetPoint"/>'
            f'</mxGeometry></mxCell>'
        )
    return "".join(cells)


def _cell_edge(e, parent="1") -> str:
    label = _esc(e.label)
    return (
        f'<mxCell id={quoteattr(e.id)} value="{label}" '
        f'style="{_edge_style(e)}" edge="1" parent="{parent}" '
        f'source={quoteattr(e.source)} target={quoteattr(e.target)}>'
        f'<mxGeometry relative="1" as="geometry"/></mxCell>'
    )


def _page(diagram) -> str:
    by_kind = {n.id: n for n in diagram.nodes}
    edges = "".join(_cell_edge(e) for e in diagram.edges)
    shapes = "".join(_cell_node(n) for n in diagram.nodes
                     if n.kind not in ("label", "title"))
    labels = "".join(_cell_node(n) for n in diagram.nodes
                     if n.kind in ("label", "title"))
    body = (
        '<mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" '
        'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
        'pageWidth="1654" pageHeight="1169" math="0" shadow="0">'
        '<root><mxCell id="0"/><mxCell id="1" parent="0"/>'
        + edges + shapes + labels +
        '</root></mxGraphModel>'
    )
    return (f'<diagram id={quoteattr(diagram.id)} '
            f'name={quoteattr(diagram.name)}>{body}</diagram>')


def to_drawio(diagrams) -> str:
    """Return a full multi-page ``mxfile`` string for a list of diagrams."""
    if not isinstance(diagrams, (list, tuple)):
        diagrams = [diagrams]
    pages = "".join(_page(d) for d in diagrams)
    return ('<mxfile host="Kenshi Diagrams" type="device" '
            'agent="kenshi-engine">' + pages + '</mxfile>')
