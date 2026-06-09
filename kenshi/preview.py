"""Faithful matplotlib preview of a Diagram model (sanity check / docs thumbnails).

Not used by the exporters, but it now mirrors what draw.io actually draws so the
PNG gallery is trustworthy:
  * edges follow their real perimeter PORTS (exitX/exitY/entryX/entryY) + channel
    waypoints -> clean orthogonal runs, not centre-to-centre slants;
  * horizontal segments hop VERTICAL ones with a small arc (the ``jumpStyle=arc``
    line-jumps from the exporter);
  * crow's-foot cardinality symbols (one / many / zero) are drawn at edge ends;
  * primary-key ERD attributes are underlined.
"""
from __future__ import annotations

import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Rectangle, Polygon, Arc

from .geometry import clip_edge, boundary_point
from .model import (PROCESS, EXTERNAL, DATASTORE, ENTITY, ATTRIBUTE,
                    RELATIONSHIP)

_EPS = 1.5   # px tolerance for "axis-aligned"


def _edge_points(e, node):
    """Full polyline (screen coords) from the source perimeter to the target.

    Honours explicit ports when present (DFD/context), else falls back to a
    boundary-clipped orthogonal/straight route (ERD)."""
    a, b = node.get(e.source), node.get(e.target)
    if not a or not b:
        return None
    if "exitX" in e.style and "entryX" in e.style:
        sx = a.x + float(e.style["exitX"]) * a.w
        sy = a.y + float(e.style["exitY"]) * a.h
        tx = b.x + float(e.style["entryX"]) * b.w
        ty = b.y + float(e.style["entryY"]) * b.h
        return [(sx, sy)] + [tuple(p) for p in e.waypoints] + [(tx, ty)]
    (sx, sy), (tx, ty) = clip_edge(a, b, pullback=0.0)
    if e.waypoints:
        return [(sx, sy)] + [tuple(p) for p in e.waypoints] + [(tx, ty)]
    if e.routing == "orthogonal":
        midx = (sx + tx) / 2.0
        return [(sx, sy), (midx, sy), (midx, ty), (tx, ty)]
    return [(sx, sy), (tx, ty)]


def _marker(ax, tip, away, arrow, stroke):
    """Draw an edge-end decoration. ``away`` is the unit vector pointing back
    along the line (out of the shape). Supports block arrow + crow's-foot."""
    if not arrow or arrow == "none":
        return
    x, y = tip
    ux, uy = away
    px, py = -uy, ux                      # perpendicular (unit)
    if arrow == "block":
        ax.annotate("", xy=(x, y), xytext=(x + ux * 13, y + uy * 13),
                    arrowprops=dict(arrowstyle="-|>", color=stroke, lw=1.0))
        return
    if "crowsfoot" in arrow:
        W, L = 11.0, 16.0
        if "many" in arrow:               # three prongs converging away
            bx, by = x + ux * L, y + uy * L
            for s in (1.0, 0.0, -1.0):
                ax.plot([bx, x + px * W * s], [by, y + py * W * s],
                        color=stroke, lw=1.0)
        if "one" in arrow:                # single bar across the line
            ox, oy = x + ux * 9.0, y + uy * 9.0
            ax.plot([ox + px * W, ox - px * W], [oy + py * W, oy - py * W],
                    color=stroke, lw=1.0)
        if "zero" in arrow:               # open circle further out
            ax.add_patch(Ellipse((x + ux * (L + 7), y + uy * (L + 7)), 11, 11,
                                  fill=True, fc="white", ec=stroke, lw=1.0))


def _h_segment_with_jumps(ax, x0, x1, y, verticals, stroke, r=6.0):
    """Draw a horizontal segment, hopping every vertical segment it crosses."""
    lo, hi = (x0, x1) if x0 <= x1 else (x1, x0)
    cuts = sorted({vx for (vx, ya, yb) in verticals
                   if lo + r < vx < hi - r and min(ya, yb) < y < max(ya, yb)})
    cur = lo
    for cx in cuts:
        ax.plot([cur, cx - r], [y, y], color=stroke, lw=1.0)
        ax.add_patch(Arc((cx, y), 2 * r, 2 * r, angle=0, theta1=0, theta2=180,
                         color=stroke, lw=1.0))
        cur = cx + r
    ax.plot([cur, hi], [y, y], color=stroke, lw=1.0)


def render(diagram, path, scale=0.01, mono=False, transparent=False):
    """Render a preview PNG.

    ``mono=True`` -> pure black & white; ``transparent=True`` -> no canvas bg."""
    stroke = "#000000" if mono else "#1F3A5F"
    ext_fill = "#FFFFFF" if mono else "#EEF2F7"
    header_fill = "#000000" if mono else "#1F3A5F"
    txt = "#000000"

    node = {n.id: n for n in diagram.nodes}
    xs = [n.x for n in diagram.nodes] + [n.x + n.w for n in diagram.nodes]
    ys = [n.y for n in diagram.nodes] + [n.y + n.h for n in diagram.nodes]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    w = min(20, (maxx - minx) * scale + 2)
    h = min(20, (maxy - miny) * scale + 2)
    fig, ax = plt.subplots(figsize=(max(6, w), max(6, h)))
    ax.set_xlim(minx - 40, maxx + 40)
    ax.set_ylim(maxy + 40, miny - 40)   # invert y (screen frame)
    ax.axis("off")

    # --- pre-compute every edge polyline, collect the vertical segments -------
    paths = []
    verticals = []
    for e in diagram.edges:
        pts = _edge_points(e, node)
        if not pts:
            continue
        paths.append((e, pts))
        for (p, q) in zip(pts, pts[1:]):
            if abs(p[0] - q[0]) <= _EPS and abs(p[1] - q[1]) > _EPS:
                verticals.append((p[0], p[1], q[1]))

    # --- draw edges (under shapes); horizontals hop verticals -----------------
    for e, pts in paths:
        for (p, q) in zip(pts, pts[1:]):
            if abs(p[1] - q[1]) <= _EPS and abs(p[0] - q[0]) > _EPS:
                _h_segment_with_jumps(ax, p[0], q[0], p[1], verticals, stroke)
            else:
                ax.plot([p[0], q[0]], [p[1], q[1]], color=stroke, lw=1.0)
        # end decorations
        def _unit(frm, to):
            dx, dy = frm[0] - to[0], frm[1] - to[1]
            d = math.hypot(dx, dy) or 1.0
            return (dx / d, dy / d)
        _marker(ax, pts[-1], _unit(pts[-2], pts[-1]), e.end_arrow, stroke)
        _marker(ax, pts[0], _unit(pts[1], pts[0]), e.start_arrow, stroke)

    # --- shapes ---------------------------------------------------------------
    for n in diagram.nodes:
        cx, cy = n.center
        if n.kind == PROCESS:
            ax.add_patch(Ellipse((cx, cy), n.w, n.h, fill=True, fc="white",
                                 ec=stroke))
        elif n.kind == ENTITY and n.style.get("rows"):
            hh = 28.0
            ax.add_patch(Rectangle((n.x, n.y), n.w, hh, fill=True,
                                   fc=header_fill, ec=stroke))
            ax.text(cx, n.y + hh / 2, n.label, ha="center", va="center",
                    fontsize=9, color="white", fontweight="bold")
            for i, (text, kind) in enumerate(n.style["rows"]):
                ry = n.y + hh + i * 22.0
                ax.add_patch(Rectangle((n.x, ry), n.w, 22.0, fill=True,
                                       fc="white", ec=stroke))
                pre = {"pk": "PK ", "fk": "FK "}.get(kind, "")
                ax.text(n.x + 8, ry + 11, pre + text, ha="left", va="center",
                        fontsize=7, color=txt,
                        fontweight="bold" if kind == "pk" else "normal",
                        style="italic" if kind == "fk" else "normal")
            continue
        elif n.kind in (EXTERNAL, ENTITY):
            fc = ext_fill if n.kind == EXTERNAL else "white"
            ax.add_patch(Rectangle((n.x, n.y), n.w, n.h, fill=True, fc=fc,
                                   ec=stroke))
        elif n.kind == DATASTORE:
            ax.plot([n.x, n.x + n.w], [n.y, n.y], color=stroke)
            ax.plot([n.x, n.x + n.w], [n.y + n.h, n.y + n.h], color=stroke)
        elif n.kind == ATTRIBUTE:
            ax.add_patch(Ellipse((cx, cy), n.w, n.h, fill=True, fc="white",
                                 ec=stroke))
        elif n.kind == RELATIONSHIP:
            ax.add_patch(Polygon([(cx, n.y), (n.x + n.w, cy), (cx, n.y + n.h),
                                  (n.x, cy)], fill=True, fc="white", ec=stroke))
        elif n.kind == "label":
            ax.add_patch(Rectangle((n.x, n.y), n.w, n.h, fill=True, fc="white",
                                   ec="none"))
        fs = 7 if n.kind in ("label",) else (12 if n.kind == "title" else 8)
        ax.text(cx, cy, n.label, ha="center", va="center", fontsize=fs,
                color=txt, wrap=True)
        # primary-key ERD attribute -> underline the label
        if n.kind == ATTRIBUTE and n.is_key:
            uw = min(n.w * 0.78, len(n.label) * 4.6)
            ax.plot([cx - uw / 2, cx + uw / 2], [cy + 8, cy + 8],
                    color=txt, lw=0.9)

    fig.tight_layout()
    fig.savefig(path, dpi=95, bbox_inches="tight", transparent=transparent)
    plt.close(fig)


if __name__ == "__main__":
    import sys
    from .content import build_all
    diagrams = build_all()
    which = sys.argv[1:] or list(diagrams)
    for name in which:
        render(diagrams[name], f"preview_{name}.png")
        print("wrote", f"preview_{name}.png")
