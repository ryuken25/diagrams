"""Offline ordering predictor backed by the exported ONNX model.

``model_order_fn(onnx_path)`` returns a callable ``(node_ids, pairs) -> order``
suitable as ``layout_chen(order_fn=...)``. If onnxruntime or the model file is
missing it returns ``None`` so the caller uses the deterministic engine — the
identical code path with the engine's own ordering (graceful degradation).

Featurisation here MUST mirror ``ai/common.features`` (degree + constant + the
first ``N_EIG`` non-trivial Laplacian eigenvectors).
"""
from __future__ import annotations

import math

import numpy as np

N_EIG = 4
FEAT_DIM = 2 + N_EIG


def _features(n, idx_pairs):
    A = np.zeros((n, n), dtype=np.float32)
    deg = np.zeros(n, dtype=np.float32)
    for a, b in idx_pairs:
        A[a, b] = A[b, a] = 1.0
        deg[a] += 1
        deg[b] += 1
    feat = np.zeros((n, FEAT_DIM), dtype=np.float32)
    feat[:, 0] = deg / max(1, n)
    feat[:, 1] = 1.0
    L = np.diag(deg) - A
    vals, vecs = np.linalg.eigh(L)
    for k in range(N_EIG):
        col = k + 1
        if col < n:
            v = vecs[:, col]
            if v.sum() < 0:
                v = -v
            feat[:, 2 + k] = v
    return feat, A


def model_order_fn(onnx_path):
    try:
        import onnxruntime as ort
        import os
        if not os.path.exists(onnx_path):
            return None
        sess = ort.InferenceSession(onnx_path,
                                    providers=["CPUExecutionProvider"])
    except Exception:
        return None

    def order_fn(node_ids, pairs):
        n = len(node_ids)
        if n <= 2:
            return list(node_ids)
        index = {nid: i for i, nid in enumerate(node_ids)}
        idx_pairs = [(index[a], index[b]) for (a, b) in pairs
                     if a in index and b in index]
        feat, A = _features(n, idx_pairs)
        coords = sess.run(None, {"feats": feat[None], "adj": A[None]})[0][0]
        ang = np.arctan2(coords[:, 1], coords[:, 0])
        order_idx = list(np.argsort(ang))
        return [node_ids[i] for i in order_idx]

    return order_fn
