"""Train the RingGNN by distillation. GPU autodetect, early stopping on val loss."""
from __future__ import annotations

import argparse
import os
import time

import numpy as np
import torch

from model import RingGNN, procrustes_loss
from common import decode_order
from kenshi.layout.chen import ring_crossings


def crossing_gap(model, feats, adjs, masks, tcross, device, sample=1500):
    """Mean (model-order crossings - teacher crossings) on a subset."""
    model.eval()
    idx = np.random.default_rng(0).choice(len(feats), min(sample, len(feats)),
                                          replace=False)
    gap = 0
    optimal = 0
    with torch.no_grad():
        P = model(torch.tensor(feats[idx], device=device),
                  torch.tensor(adjs[idx], device=device)).cpu().numpy()
    for k, i in enumerate(idx):
        n = int(masks[i].sum())
        pairs = [(a, b) for a in range(n) for b in range(a + 1, n)
                 if adjs[i, a, b] > 0]
        order = decode_order(P[k], masks[i])
        c = ring_crossings(order, pairs)
        gap += c - int(tcross[i])
        optimal += int(c == int(tcross[i]))
    return gap / len(idx), optimal / len(idx)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="ai/artifacts/dataset.npz")
    ap.add_argument("--out", default="ai/artifacts/ringgnn.pt")
    ap.add_argument("--epochs", type=int, default=200)
    ap.add_argument("--batch", type=int, default=512)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--patience", type=int, default=15)
    ap.add_argument("--hidden", type=int, default=64)
    ap.add_argument("--layers", type=int, default=3)
    a = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Distillation training on {device.upper()} "
          f"({'CUDA' if device=='cuda' else 'CPU reduced'} run). "
          "Teacher = deterministic engine; 10 user diagrams = gold eval only.")

    d = np.load(a.data)
    feats, adjs, masks = d["feats"], d["adjs"], d["masks"]
    targets, tcross = d["targets"], d["tcross"]
    n = len(feats)
    rng = np.random.default_rng(42)
    perm = rng.permutation(n)
    n_tr, n_va = int(0.8 * n), int(0.1 * n)
    tr, va, te = perm[:n_tr], perm[n_tr:n_tr + n_va], perm[n_tr + n_va:]
    np.save(os.path.join(os.path.dirname(a.out), "test_idx.npy"), te)

    def to(x, i):
        return torch.tensor(x[i], device=device)

    in_dim = feats.shape[-1]
    model = RingGNN(in_dim, a.hidden, a.layers).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"model params: {n_params:,}")
    opt = torch.optim.Adam(model.parameters(), lr=a.lr)
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, factor=0.5,
                                                       patience=5)

    best_val = float("inf")
    best_state = None
    bad = 0
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    for epoch in range(1, a.epochs + 1):
        model.train()
        ep = rng.permutation(tr)
        tot = 0.0
        t0 = time.time()
        for s in range(0, len(ep), a.batch):
            b = ep[s:s + a.batch]
            P = model(to(feats, b), to(adjs, b))
            loss = procrustes_loss(P, to(targets, b), to(masks, b))
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += loss.item() * len(b)
        tr_loss = tot / len(tr)

        model.eval()
        with torch.no_grad():
            P = model(to(feats, va), to(adjs, va))
            val = procrustes_loss(P, to(targets, va), to(masks, va)).item()
        sched.step(val)
        if val < best_val - 1e-5:
            best_val = val
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            bad = 0
        else:
            bad += 1
        if epoch % 5 == 0 or epoch == 1:
            gap, opt_rate = crossing_gap(model, feats, adjs, masks, tcross,
                                         device)
            print(f"epoch {epoch:3d}  train {tr_loss:.4f}  val {val:.4f}  "
                  f"crossGap {gap:+.3f}  optimal {opt_rate*100:.1f}%  "
                  f"{time.time()-t0:.1f}s")
        if bad >= a.patience:
            print(f"early stop at epoch {epoch} (no val improvement "
                  f"for {a.patience})")
            break

    model.load_state_dict(best_state)
    torch.save({"state": best_state, "in_dim": in_dim, "hidden": a.hidden,
                "layers": a.layers}, a.out)
    gap, opt_rate = crossing_gap(model, feats[te], adjs[te], masks[te],
                                 tcross[te], device, sample=len(te))
    print(f"\nBEST val loss {best_val:.4f}  |  TEST crossGap {gap:+.3f}  "
          f"optimal {opt_rate*100:.1f}%")
    print(f"saved -> {a.out}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    main()
