"""Neutral diagram model shared by every layout engine and exporter.

A single set of dataclasses that all builders produce and all exporters
consume. Coordinates use a screen frame (y grows downward); every layout
function only sets ``x, y, w, h`` (and optional edge ``waypoints``).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# Node kinds understood by the exporters / layouts.
PROCESS = "process"        # DFD process (circle / ellipse)
EXTERNAL = "external"      # DFD external entity / terminator (rectangle)
DATASTORE = "datastore"    # DFD data store (open rectangle: top+bottom borders)
ENTITY = "entity"          # ERD entity (rectangle)
ATTRIBUTE = "attribute"    # ERD attribute (ellipse); is_key -> underlined label
RELATIONSHIP = "relationship"  # ERD relationship (diamond)
TITLE = "title"            # free-floating title text


@dataclass
class Borders:
    top: bool = True
    right: bool = True
    bottom: bool = True
    left: bool = True

    @staticmethod
    def open_store() -> "Borders":
        # data store look: only top + bottom lines, left/right open
        return Borders(top=True, right=False, bottom=True, left=False)


@dataclass
class Node:
    id: str
    kind: str
    label: str = ""
    x: float = 0.0
    y: float = 0.0
    w: float = 120.0
    h: float = 60.0
    borders: Borders = field(default_factory=Borders)
    is_key: bool = False              # ERD attribute PK -> underline
    duplicate_of: Optional[str] = None  # duplicated DFD store/external instance
    store_id: Optional[str] = None    # e.g. "D1" rendered in the left compartment
    style: dict = field(default_factory=dict)

    # ---- geometry helpers (screen frame) ----
    @property
    def cx(self) -> float:
        return self.x + self.w / 2.0

    @property
    def cy(self) -> float:
        return self.y + self.h / 2.0

    @property
    def center(self) -> tuple[float, float]:
        return (self.cx, self.cy)


@dataclass
class Edge:
    id: str
    source: str
    target: str
    label: str = ""
    card_source: str = ""             # ERD cardinality at source end (1 / N / M)
    card_target: str = ""             # ERD cardinality at target end
    end_arrow: str = "block"          # block | none | crowsfoot-*
    start_arrow: str = "none"
    routing: str = "straight"         # straight | orthogonal
    waypoints: list[tuple[float, float]] = field(default_factory=list)
    style: dict = field(default_factory=dict)


@dataclass
class Diagram:
    id: str
    name: str
    type: str                          # erd-chen | erd-crowsfoot | dfd-context | dfd-level0 | dfd-level1
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    def node(self, nid: str) -> Node:
        for n in self.nodes:
            if n.id == nid:
                return n
        raise KeyError(nid)

    def add(self, node: Node) -> Node:
        self.nodes.append(node)
        return node

    def connect(self, edge: Edge) -> Edge:
        self.edges.append(edge)
        return edge
