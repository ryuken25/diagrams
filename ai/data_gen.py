"""Generate the synthetic distillation dataset (teacher = the deterministic engine)."""
from __future__ import annotations

import argparse
import os

import numpy as np

from common import random_graph, teacher, features, target_ring, PAD, FEAT_DIM


def generate(n_samples: int, seed: int, out: str):
    rng = np.random.default_rng(seed)
    feats = np.zeros((n_samples, PAD, FEAT_DIM), dtype=np.float32)
    adjs = np.zeros((n_samples, PAD, PAD), dtype=np.float32)
    masks = np.zeros((n_samples, PAD), dtype=np.float32)
    targets = np.zeros((n_samples, PAD, 2), dtype=np.float32)
    tcross = np.zeros((n_samples,), dtype=np.int32)
    for i in range(n_samples):
        n, pairs = random_graph(rng)
        order, cross = teacher(n, pairs)
        f, A, m = features(n, pairs)
        feats[i], adjs[i], masks[i] = f, A, m
        targets[i] = target_ring(n, order)
        tcross[i] = cross
        if (i + 1) % 2000 == 0:
            print(f"  generated {i + 1}/{n_samples}")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    np.savez_compressed(out, feats=feats, adjs=adjs, masks=masks,
                        targets=targets, tcross=tcross)
    print(f"saved {n_samples} samples -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=24000, help="number of samples")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="ai/artifacts/dataset.npz")
    a = ap.parse_args()
    print("Distillation dataset: synthetic graphs, teacher = deterministic "
          "ERD-Chen ordering engine. The 10 user diagrams are gold eval only.")
    generate(a.n, a.seed, a.out)
