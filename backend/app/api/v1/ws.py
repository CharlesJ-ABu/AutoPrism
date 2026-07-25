"""Backward-compatible import for older callers."""

from app.core.websocket import ConnectionManager, manager

__all__ = ["ConnectionManager", "manager"]
