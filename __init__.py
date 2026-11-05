"""Hermes plugin entry point for Stagehands delegation."""

from typing import Any

from .provider import StagehandsProvider


def register(ctx: Any) -> None:
    """Register the Stagehands delegation provider with Hermes."""
    ctx.register_delegation_provider(StagehandsProvider())
