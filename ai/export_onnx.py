"""Export the trained RingGNN to ONNX (offline 'AI tidy' path) + verify parity."""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from model import RingGNN


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="ai/artifacts/ringgnn.pt")
    ap.add_argument("--out", default="ai/artifacts/kenshi-layout.onnx")
    a = ap.parse_args()
    ck = torch.load(a.model, map_location="cpu")
    in_dim = ck.get("in_dim", 2)
    m = RingGNN(in_dim, ck["hidden"], ck["layers"])
    m.load_state_dict(ck["state"])
    m.eval()

    feats = torch.randn(1, 16, in_dim)
    adj = (torch.rand(1, 16, 16) > 0.7).float()
    adj = ((adj + adj.transpose(1, 2)) > 0).float()
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    torch.onnx.export(
        m, (feats, adj), a.out,
        input_names=["feats", "adj"], output_names=["coords"],
        dynamic_axes={"feats": {0: "B", 1: "N"}, "adj": {0: "B", 1: "N", 2: "N"},
                      "coords": {0: "B", 1: "N"}},
        opset_version=17)

    # parity check vs onnxruntime
    import onnxruntime as ort
    sess = ort.InferenceSession(a.out, providers=["CPUExecutionProvider"])
    onnx_out = sess.run(None, {"feats": feats.numpy(), "adj": adj.numpy()})[0]
    with torch.no_grad():
        torch_out = m(feats, adj).numpy()
    err = float(np.abs(onnx_out - torch_out).max())
    print(f"exported {a.out}  |  onnx-vs-torch max abs diff = {err:.2e}")
    if err > 1e-4:
        print("WARNING: parity error high")


if __name__ == "__main__":
    main()
