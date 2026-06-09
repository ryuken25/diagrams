"""Offline 'AI tidy' runtime — uses the distilled ONNX model to pick the ERD
ring order, falling back silently to the deterministic engine if absent."""
from .runtime import model_order_fn

__all__ = ["model_order_fn"]
