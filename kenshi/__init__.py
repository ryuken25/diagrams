"""Kenshi Diagrams — deterministic, overlap-free DFD & ERD layout engine.

Public surface:
    from kenshi import build_all       # build every MellogangVisuals diagram
    from kenshi.export import to_drawio, to_graphml
"""
from .model import Diagram, Node, Edge, Borders  # noqa: F401

__all__ = ["Diagram", "Node", "Edge", "Borders"]
__version__ = "1.0.0"
