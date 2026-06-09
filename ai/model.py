"""Compact GNN that predicts an ERD ring configuration (layout DECISION).

Message passing over the (self-looped, row-normalised) adjacency; a per-node
2-D head outputs ring coordinates. Decoding to a cyclic order = sort by angle.
~50k params — trains fast on CPU or GPU.
"""
from __future__ import annotations

import torch
import torch.nn as nn


def normalize_adj(adj: torch.Tensor) -> torch.Tensor:
    """Â = D^-1 (A + I), row-normalised, batched [B,N,N]."""
    eye = torch.eye(adj.shape[-1], device=adj.device).unsqueeze(0)
    a = adj + eye
    deg = a.sum(-1, keepdim=True).clamp(min=1.0)
    return a / deg


class GNNLayer(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.lin = nn.Linear(dim, dim)
        self.self_lin = nn.Linear(dim, dim)

    def forward(self, h, a_norm):
        agg = torch.bmm(a_norm, h)
        return torch.relu(self.self_lin(h) + self.lin(agg))


class RingGNN(nn.Module):
    def __init__(self, in_dim=2, hidden=64, layers=3):
        super().__init__()
        self.embed = nn.Linear(in_dim, hidden)
        self.layers = nn.ModuleList([GNNLayer(hidden) for _ in range(layers)])
        self.head = nn.Linear(hidden, 2)

    def forward(self, feats, adj):
        a_norm = normalize_adj(adj)
        h = torch.relu(self.embed(feats))
        for layer in self.layers:
            h = layer(h, a_norm)
        out = self.head(h)
        # unit-normalise so outputs live on the ring (stable angle decode)
        return out / (out.norm(dim=-1, keepdim=True) + 1e-6)


def procrustes_loss(pred, target, mask):
    """Rotation/reflection-invariant ring loss via pairwise Gram matrices.

    Points on the unit circle: P_i·P_j = cos(Δangle), which is invariant to any
    global rotation/reflection (a ring has no canonical start/orientation). So we
    match the pairwise dot-product matrix of the prediction to the target's. This
    is smooth and SVD-free (the orthogonal-Procrustes route NaNs on tied singular
    values), and directly supervises the *relative* angular order = the decision.
    """
    pair_mask = mask.unsqueeze(2) * mask.unsqueeze(1)        # [B,N,N]
    gp = torch.bmm(pred, pred.transpose(1, 2))
    gq = torch.bmm(target, target.transpose(1, 2))
    diff = (gp - gq) ** 2 * pair_mask
    return diff.sum() / pair_mask.sum().clamp(min=1.0)
