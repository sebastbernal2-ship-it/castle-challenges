"""Shared allocation primitives; game-specific rules live in separate packages."""

from .allocation import Allocation, SOLDIERS, VALUES, allocations, validate

__all__ = ["Allocation", "SOLDIERS", "VALUES", "allocations", "validate"]
