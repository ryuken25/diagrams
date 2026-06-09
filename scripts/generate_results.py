"""Generate every diagram twice — WITHOUT the model (pure deterministic engine)
and WITH the offline ONNX model deciding the ERD ring order — into result/.

    result/without/   engine-only layouts (no ML)
    result/with/      ERD ring order chosen by the distilled model

Both are overlap-free by construction; the comparison shows the offline model
reproduces (and is graded against) the engine's ordering decision. The DFD/Context
layouts are deterministic in both folders (the model only covers ERD ordering).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kenshi.content import mellogang, beauty_salon
from kenshi.export import to_drawio, to_graphml
from kenshi.metrics import label_overlaps, shape_overlaps, edge_crossings
from kenshi.ai import model_order_fn

ONNX = os.path.join("ai", "artifacts", "kenshi-layout.onnx")
ROOT = "result"


def _write(folder, name, d):
    os.makedirs(folder, exist_ok=True)
    open(os.path.join(folder, f"{name}.drawio"), "w", encoding="utf-8").write(
        to_drawio(d))
    open(os.path.join(folder, f"{name}.graphml"), "w", encoding="utf-8").write(
        to_graphml(d))


def build_set(order_fn):
    out = {}
    out["mellogang_erd_chen"] = mellogang.build_erd_chen(order_fn=order_fn)
    out["mellogang_erd_crowsfoot"] = mellogang.build_erd_crowsfoot()
    out["mellogang_diagram_konteks"] = mellogang.build_context()
    out["mellogang_dfd_level0"] = mellogang.build_dfd0()
    for p in ["P1", "P2", "P3", "P4", "P5", "P6"]:
        out[f"mellogang_dfd_level1_{p}"] = mellogang.build_dfd1(p)
    out["beautysalon_erd_chen"] = beauty_salon.build_erd_chen(order_fn=order_fn)
    out["beautysalon_erd_crowsfoot"] = beauty_salon.build_erd_crowsfoot()
    out["beautysalon_diagram_konteks"] = beauty_salon.build_context()
    out["beautysalon_dfd_level0"] = beauty_salon.build_dfd0()
    return out


def main():
    order_fn = model_order_fn(ONNX)
    if order_fn is None:
        print(f"NOTE: {ONNX} not found / onnxruntime missing — 'with' folder "
              "falls back to the engine ordering.")

    variants = {"without": None, "with": order_fn}
    print(f"{'diagram':32} {'folder':8} {'labelOv':>7} {'shapeOv':>7} "
          f"{'edgeCross':>9}")
    print("-" * 70)
    for folder, ofn in variants.items():
        ds = build_set(ofn)
        for name, d in ds.items():
            _write(os.path.join(ROOT, folder), name, d)
            if "erd_chen" in name:
                print(f"{name:32} {folder:8} {label_overlaps(d):>7} "
                      f"{shape_overlaps(d):>7} {edge_crossings(d):>9}")
        # one combined multi-page file per folder
        open(os.path.join(ROOT, folder, "ALL.drawio"), "w",
             encoding="utf-8").write(to_drawio(list(ds.values())))
    print("-" * 70)
    print(f"wrote result/with/ and result/without/  "
          f"({'model' if order_fn else 'engine-fallback'} for ERD order)")


if __name__ == "__main__":
    main()
