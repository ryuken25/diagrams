"""Evaluate the trained model on the held-out test split + the real ERD graphs.

Reports the distillation quality (how often the model reproduces the engine's
optimal crossing count) and confirms the rendered layout is overlap-free.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from model import RingGNN
from common import decode_order, features, teacher, fast_order, fast_crossings
from real_erds import REAL_ERDS
from kenshi.layout.chen import ring_crossings
from kenshi.content import mellogang
from kenshi.metrics import label_overlaps, shape_overlaps


def load(path, device):
    ck = torch.load(path, map_location=device)
    m = RingGNN(ck.get("in_dim", 2), ck["hidden"], ck["layers"]).to(device)
    m.load_state_dict(ck["state"])
    m.eval()
    return m


def eval_split(model, data, device):
    d = np.load(data)
    te = np.load(os.path.join(os.path.dirname(data), "test_idx.npy"))
    feats, adjs, masks, tcross = d["feats"], d["adjs"], d["masks"], d["tcross"]
    with torch.no_grad():
        P = model(torch.tensor(feats[te], device=device),
                  torch.tensor(adjs[te], device=device)).cpu().numpy()
    gap = opt = excess0 = 0
    for k, i in enumerate(te):
        n = int(masks[i].sum())
        pairs = [(a, b) for a in range(n) for b in range(a + 1, n)
                 if adjs[i, a, b] > 0]
        c = ring_crossings(decode_order(P[k], masks[i]), pairs)
        g = c - int(tcross[i])
        gap += g
        opt += int(g == 0)
        excess0 += int(g <= 1)
    n = len(te)
    return {"test_samples": n, "mean_crossing_gap": gap / n,
            "optimal_rate": opt / n, "within_1_rate": excess0 / n}


def eval_real(model, device):
    """The actual ERDs the engine ships (MellogangVisuals) — overlap must be 0."""
    chen = mellogang.build_erd_chen()
    lo, so = label_overlaps(chen), shape_overlaps(chen)
    # ordering quality on the Mellogang entity graph
    ents = list(mellogang.ENTITIES)
    idx = {e: i for i, e in enumerate(ents)}
    pairs = []
    for (_v, p, _c1, c, _c2) in mellogang.RELATIONSHIPS:
        pairs.append((min(idx[p], idx[c]), max(idx[p], idx[c])))
    n = len(ents)
    f, A, m = features(n, pairs)
    with torch.no_grad():
        P = model(torch.tensor(f[None], device=device),
                  torch.tensor(A[None], device=device)).cpu().numpy()[0]
    model_c = ring_crossings(decode_order(P, m), pairs)
    _order, teacher_c = teacher(n, pairs)
    return {"mellogang_label_overlap": lo, "mellogang_shape_overlap": so,
            "mellogang_model_crossings": model_c,
            "mellogang_teacher_crossings": teacher_c}


def eval_real_erds(model, device, refine=1):
    """Eval on real-world ERDs ('ERD orang'). Returns per-ERD + aggregate.

    Reports the offline path = model proposes the order, then a light ``refine``-
    pass 2-opt polish (seeded by the model) renders it. 'good' = matches the
    deterministic engine's optimum crossing count.
    """
    rows = {}
    good_pure = good_off = 0
    for name, (ents, pairs) in REAL_ERDS.items():
        n = len(ents)
        f, A, m = features(n, pairs)
        with torch.no_grad():
            P = model(torch.tensor(f[None], device=device),
                      torch.tensor(A[None], device=device)).cpu().numpy()[0]
        model_order = decode_order(P, m)
        pure_c = fast_crossings(model_order, pairs)
        off_order, off_c = fast_order(n, pairs, max_passes=refine,
                                      start=model_order)
        _opt, teacher_c = teacher(n, pairs)
        rows[name] = {"n": n, "teacher": teacher_c, "model": pure_c,
                      "offline": off_c}
        good_pure += int(pure_c == teacher_c)
        good_off += int(off_c == teacher_c)
    k = len(REAL_ERDS)
    return rows, good_pure / k, good_off / k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="ai/artifacts/ringgnn.pt")
    ap.add_argument("--data", default="ai/artifacts/dataset.npz")
    ap.add_argument("--out", default="ai/artifacts/metrics.json")
    a = ap.parse_args()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = load(a.model, device)
    rows, good_pure, good_off = eval_real_erds(model, device, refine=1)
    metrics = {**eval_split(model, a.data, device), **eval_real(model, device),
               "real_erds": rows,
               "real_erd_pure_optimal_rate": round(good_pure, 3),
               "real_erd_offline_optimal_rate": round(good_off, 3)}
    print("Real-world ERDs (ERD orang) — crossings model / offline / engine:")
    for name, r in rows.items():
        tag = "OK" if r["offline"] == r["teacher"] else "  "
        print(f"  {name:12} n={r['n']}  model={r['model']:>2}  "
              f"offline={r['offline']:>2}  engine={r['teacher']:>2}  {tag}")
    print(f"  -> pure-model optimal: {good_pure*100:.0f}%   "
          f"offline (model+1-pass polish) optimal: {good_off*100:.0f}%\n")
    print(json.dumps({k: v for k, v in metrics.items() if k != "real_erds"},
                     indent=2))
    if metrics["mellogang_label_overlap"] or metrics["mellogang_shape_overlap"]:
        print("WARNING: overlap detected on the real ERD!")
    with open(a.out, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
