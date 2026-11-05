"""Hermes plugin entry point for Stagehands delegation."""

from __future__ import annotations

from typing import Any

try:
    from .provider import DEFAULT_WORKERS, StagehandsProvider
except ImportError:
    from provider import DEFAULT_WORKERS, StagehandsProvider


def _make_slash_handler(ctx: Any, provider: StagehandsProvider):
    """Build the `/stagehands` slash command handler for CLI, TUI, Desktop, and messaging."""

    def handle_stagehands(raw_args: str = "", session_key: str = "", **_: Any) -> str:
        words = [w.strip().lower() for w in (raw_args or "").split() if w.strip()]
        now = "--now" in words or "now" in words
        action_words = [w for w in words if w not in ("--now", "now")]
        action = action_words[0] if action_words else "status"
        api = getattr(ctx, "delegation_backends", None)

        if action in ("on", "enable", "use", "activate") or (action == "status" and now):
            if api is None:
                return "Stagehands: ctx.delegation_backends is unavailable on this Hermes build."
            try:
                if now and session_key:
                    api.set_global_backend("stagehands", session_key=session_key, apply_now=True)
                    return (
                        "Stagehands activated (`delegation.backend = stagehands`) and applied to this chat "
                        "(tools will rebuild on your next message)."
                    )
                api.set_global_backend("stagehands", session_key=session_key)
                return (
                    "Stagehands saved (`delegation.backend = stagehands`). "
                    "Start a `/new` session or run `/stagehands --now` to rebuild this chat's tools immediately."
                )
            except Exception as exc:
                return f"Could not activate Stagehands: {exc}"

        if action in ("off", "default", "disable"):
            if api is None:
                return "Stagehands: ctx.delegation_backends is unavailable on this Hermes build."
            try:
                if now and session_key:
                    api.set_global_backend("default", session_key=session_key, apply_now=True)
                    return "Switched back to `default` delegation backend for this chat (rebuilds on next message)."
                api.set_global_backend("default", session_key=session_key)
                return "Switched `delegation.backend` back to `default` (applies on `/new` or with `--now`)."
            except Exception as exc:
                return f"Could not switch backend: {exc}"

        lines = ["🎭 Sovereign & Stagehands — Backstage Worker Roster:"]
        for name, spec in DEFAULT_WORKERS.items():
            model = spec.get("model", "default")
            effort = spec.get("reasoning_effort", "low")
            cap = (spec.get("request_overrides") or {}).get("max_tokens", "-")
            desc = spec.get("desc", "")
            lines.append(f"  • {name:<12} {model} (effort={effort}, max_tokens={cap}) — {desc}")
        lines.append(
            "\nCommands: `/stagehands --now` (activate in this chat) · "
            "`/stagehands on` (save for `/new`) · `/stagehands off [--now]`"
        )
        return "\n".join(lines)

    return handle_stagehands


def register(ctx: Any) -> None:
    """Register the Stagehands delegation provider and `/stagehands` slash command with Hermes."""
    provider = StagehandsProvider()
    ctx.register_delegation_provider(provider)
    if hasattr(ctx, "register_command"):
        ctx.register_command(
            "stagehands",
            _make_slash_handler(ctx, provider),
            description="Inspect the 5 Stagehands workers or activate Stagehands delegation (--now for this chat)",
            args_hint="[status | on | off] [--now]",
        )
