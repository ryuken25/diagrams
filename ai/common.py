"""Shared helpers for the training subproject.

Distillation task: imitate the deterministic engine's ERD-Chen *ordering
decision* — the cyclic order of entities on the ring that minimises chord
crossings (``kenshi.layout.chen.crossing_order``). The model predicts a 2-D ring
configuration; decoding = sort by angle. Procrustes alignment in the loss makes
the target invariant to rotation/reflection (a ring has no canonical start).
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kenshi.layout.chen import crossing_order, ring_crossings  # noqa: E402

N_MIN, N_MAX = 3, 12
PAD = 12        # max nodes incl. padding
N_EIG = 4       # Laplacian eigenvectors used as positional features
FEAT_DIM = 2 + N_EIG


def random_graph(rng: np.random.Generator):
    """A random relationship graph among n entities (varied FK density)."""
    n = int(rng.integers(N_MIN, N_MAX + 1))
    density = rng.uniform(0.15, 0.6)
    pairs = set()
    # a light spanning chain so graphs aren't trivially disconnected
    perm = rng.permutation(n)
    for i in range(n - 1):
        if rng.random() < 0.7:
            a, b = int(perm[i]), int(perm[i + 1])
            pairs.add((min(a, b), max(a, b)))
    max_e = n * (n - 1) // 2
    target = int(density * max_e)
    guard = 0
    while len(pairs) < target and guard < 200:
        a, b = int(rng.integers(n)), int(rng.integers(n))
        guard += 1
        if a != b:
            pairs.add((min(a, b), max(a, b)))
    return n, sorted(pairs)


def fast_crossings(order, pairs):
    """Chord-crossing count via the combinatorial arc test (fast, integer-only).

    Two chords on a circle cross iff exactly one endpoint of one lies strictly
    inside the arc spanned by the other: i<k<j<l or k<i<l<j (positions sorted).
    Vectorised with numpy — ~100x faster than the geometric segment test, which
    matters because the 2-opt teacher evaluates this thousands of times.
    """
    pos = np.empty(len(order), dtype=np.int64)
    for p, node in enumerate(order):
        pos[node] = p
    if not pairs:
        return 0
    e = np.array([(pos[a], pos[b]) for a, b in pairs])
    lo = np.minimum(e[:, 0], e[:, 1])
    hi = np.maximum(e[:, 0], e[:, 1])
    i, j = lo[:, None], hi[:, None]
    k, l = lo[None, :], hi[None, :]
    cross = ((i < k) & (k < j) & (j < l)) | ((k < i) & (i < l) & (l < j))
    return int(np.triu(cross, 1).sum())


def fast_order(n, pairs, max_passes=3):
    """Near-optimal crossing-minimising cyclic order (2-opt, capped passes)."""
    best = list(range(n))
    best_c = fast_crossings(best, pairs)
    for _ in range(max_passes):
        improved = False
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                cand = best[:i] + best[i:j + 1][::-1] + best[j + 1:]
                c = fast_crossings(cand, pairs)
                if c < best_c:
                    best, best_c = cand, c
                    improved = True
        if not improved:
            break
    return best, best_c


def teacher(n, pairs):
    """Near-optimal cyclic order + its crossing count (the distillation target)."""
    return fast_order(n, pairs)


def _laplacian_eigenvectors(n, A):
    """Smallest non-trivial Laplacian eigenvectors — the spectral ordering cue.

    Sorting nodes by the Fiedler vector is a classic low-crossing circular layout
    heuristic, so these features give the GNN a strong, learnable signal. Sign of
    each eigenvector is arbitrary, so we canonicalise it (sum >= 0).
    """
    sub = A[:n, :n]
    deg = sub.sum(1)
    L = np.diag(deg) - sub
    vals, vecs = np.linalg.eigh(L)        # ascending; index 0 is ~constant
    out = np.zeros((n, N_EIG), dtype=np.float32)
    for k in range(N_EIG):
        col = k + 1                        # skip the trivial constant eigenvector
        if col < n:
            v = vecs[:, col]
            if v.sum() < 0:
                v = -v
            out[:, k] = v
    return out


def features(n, pairs):
    """Per-node features [deg/n, 1.0, eig1..eigK] and the (padded) adjacency."""
    A = np.zeros((PAD, PAD), dtype=np.float32)
    deg = np.zeros(PAD, dtype=np.float32)
    for a, b in pairs:
        A[a, b] = A[b, a] = 1.0
        deg[a] += 1
        deg[b] += 1
    feat = np.zeros((PAD, FEAT_DIM), dtype=np.float32)
    feat[:n, 0] = deg[:n] / max(1, n)
    feat[:n, 1] = 1.0
    feat[:n, 2:] = _laplacian_eigenvectors(n, A)
    mask = np.zeros(PAD, dtype=np.float32)
    mask[:n] = 1.0
    return feat, A, mask


def target_ring(n, order):
    """Target ring coordinates Q[PAD,2] from the teacher order (rank -> angle)."""
    Q = np.zeros((PAD, 2), dtype=np.float32)
    rank = {node: i for i, node in enumerate(order)}
    for node in range(n):
        theta = 2 * np.pi * rank[node] / n
        Q[node] = (np.cos(theta), np.sin(theta))
    return Q


def decode_order(P, mask):
    """Decode a predicted [PAD,2] config into a cyclic order (angle sort)."""
    n = int(mask.sum())
    ang = np.arctan2(P[:n, 1], P[:n, 0])
    return list(np.argsort(ang))
