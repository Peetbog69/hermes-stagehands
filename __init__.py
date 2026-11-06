"""Hermes plugin entry point for Stagehands delegation + Two-Door Context Janitor."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

try:
    from .provider import DEFAULT_WORKERS, StagehandsProvider
    from .stats import compute_stats, format_stats_report, resolve_state_db
except ImportError:
    from provider import DEFAULT_WORKERS, StagehandsProvider
    from stats import compute_stats, format_stats_report, resolve_state_db

JANITOR_RECOMMENDED: dict[str, Any] = {
    "proactive_prune_tokens": 48000,
    "threshold_tokens": 120000,
    "protect_last_n": 20,
    "in_place": True,
    "hygiene_hard_message_limit": 2000,
}


def _read_raw_config(config_path: Path | None = None) -> tuple[Path, dict[str, Any]]:
    """Read raw user config.yaml via Hermes config helpers (with explicit-path fallback for tests)."""
    if config_path is not None:
        p = Path(config_path)
        if not p.is_file():
            return p, {}
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        return p, (data if isinstance(data, dict) else {})
    from hermes_cli.config import get_config_path, read_user_config_raw

    path = Path(get_config_path())
    raw = read_user_config_raw(path)
    return path, (raw if isinstance(raw, dict) else {})


def _write_raw_config(path: Path, data: dict[str, Any], *, explicit_path: bool = False) -> None:
    """Atomically write user config.yaml via Hermes's atomic_config_write."""
    if not explicit_path:
        from hermes_cli.config import atomic_config_write, format_managed_message, is_managed

        if is_managed():
            raise PermissionError(format_managed_message("update compression settings"))
        atomic_config_write(path, data)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".yaml.tmp")
    tmp.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    tmp.replace(path)


def apply_janitor_config(config_path: Path | None = None) -> str:
    """Apply the recommended 48k/120k Back-Door Context Janitor settings to config.yaml."""
    explicit = config_path is not None
    path, user_config = _read_raw_config(config_path)
    comp = user_config.get("compression")
    if not isinstance(comp, dict):
        comp = {}
        user_config["compression"] = comp
    for key, val in JANITOR_RECOMMENDED.items():
        comp[key] = val
    _write_raw_config(path, user_config, explicit_path=explicit)
    summary = ", ".join(f"{k}={v}" for k, v in JANITOR_RECOMMENDED.items())
    return (
        f"🧹 Back-Door Janitor tuned in `{path}`:\n"
        f"  • {summary}\n"
        " Bulky parent tool outputs will now proactively prune at 48k tokens and compact in-place at 120k."
    )


def run_doctor(config_path: Path | None = None, db_path: Path | None = None) -> str:
    """Audit both doors of the Sovereign & Stagehands architecture (read-only)."""
    path, user_config = _read_raw_config(config_path)
    delegation = user_config.get("delegation") if isinstance(user_config.get("delegation"), dict) else {}
    backend = str(delegation.get("backend") or "default").strip()
    comp = user_config.get("compression") if isinstance(user_config.get("compression"), dict) else {}

    door1_ok = backend == "stagehands"
    prune_tok = comp.get("proactive_prune_tokens")
    thresh_tok = comp.get("threshold_tokens")
    protect_n = comp.get("protect_last_n")
    in_place = comp.get("in_place")
    hyg_msg_limit = comp.get("hygiene_hard_message_limit")

    prune_ok = isinstance(prune_tok, int) and 0 < prune_tok <= 64000
    thresh_ok = isinstance(thresh_tok, int) and 0 < thresh_tok <= 160000
    protect_ok = isinstance(protect_n, int) and 10 <= protect_n <= 40
    inplace_ok = in_place is True
    hyg_ok = hyg_msg_limit is None or (isinstance(hyg_msg_limit, int) and hyg_msg_limit >= 1000)
    door2_ok = prune_ok and thresh_ok and protect_ok and inplace_ok and hyg_ok

    resolved_db = resolve_state_db(db_path)
    db_ok = resolved_db is not None

    lines = [
        "🩺 Sovereign & Stagehands — Two-Door Doctor Audit",
        f"  Config: `{path}`",
        (
            f"  [{'PASS' if door1_ok else 'WARN'}] Door #1 · Front-Door Bouncer: "
            f"`delegation.backend = {backend}`"
            + ("" if door1_ok else " (run `/stagehands on --now` to enable)")
        ),
        (
            f"  [{'PASS' if prune_ok else 'WARN'}] Door #2a · Proactive Tool Pruner: "
            f"`compression.proactive_prune_tokens = {prune_tok!r}` (recommended: `48000`)"
        ),
        (
            f"  [{'PASS' if thresh_ok else 'WARN'}] Door #2b · Compaction Ceiling: "
            f"`compression.threshold_tokens = {thresh_tok!r}` (recommended: `120000`)"
        ),
        (
            f"  [{'PASS' if (protect_ok and inplace_ok) else 'WARN'}] Door #2c · Forever-Chat Tail & In-Place: "
            f"`protect_last_n = {protect_n!r}`, `in_place = {in_place!r}` (recommended: `20`, `True`)"
        ),
        (
            f"  [{'PASS' if hyg_ok else 'WARN'}] Door #2d · KV Prompt-Cache Guard: "
            f"`compression.hygiene_hard_message_limit = {hyg_msg_limit!r}` "
            "(recommended: `>=1000` / `2000`; low limits like `140` slice message #1 and bust KV prompt cache)"
        ),
        (
            f"  [{'PASS' if db_ok else 'WARN'}] Telemetry Ledger (`state.db`): "
            + (f"`{resolved_db}`" if db_ok else "not found")
        ),
    ]
    if door1_ok and door2_ok:
        lines.append("  Verdict: ✅ BOTH DOORS ARMED AND HEALTHY.")
    else:
        fixes = []
        if not door1_ok:
            fixes.append("`/stagehands on --now`")
        if not door2_ok:
            fixes.append("`/stagehands janitor`")
        lines.append(f"  Verdict: ⚠️ Action needed — run {' and '.join(fixes)} (or `/stagehands on --janitor --now`).")
    return "\n".join(lines)


def _format_roster() -> str:
    lines = ["🎭 Sovereign & Stagehands — Backstage Worker Roster:"]
    for name, spec in DEFAULT_WORKERS.items():
        model = spec.get("model", "default")
        effort = spec.get("reasoning_effort", "low")
        cap = (spec.get("request_overrides") or {}).get("max_tokens", "-")
        desc = spec.get("desc", "")
        lines.append(f"  • {name:<12} {model} (effort={effort}, max_tokens={cap}) — {desc}")
    lines.append(
        "\nCommands: `/stagehands stats` · `/stagehands doctor` · `/stagehands janitor` · "
        "`/stagehands on [--janitor] [--now]` · `/stagehands off [--now]`"
    )
    return "\n".join(lines)


def _make_slash_handler(ctx: Any, provider: StagehandsProvider):
    """Build the `/stagehands` slash command handler for CLI, TUI, Desktop, and messaging."""

    def handle_stagehands(
        raw_args: str = "",
        session_key: str = "",
        *,
        config_path: Path | None = None,
        db_path: Path | None = None,
        **_: Any,
    ) -> str:
        words = [w.strip().lower() for w in (raw_args or "").split() if w.strip()]
        now = "--now" in words or "now" in words
        with_janitor = "--janitor" in words or "--tune" in words
        action_words = [w for w in words if w not in ("--now", "now", "--janitor", "--tune")]
        action = action_words[0] if action_words else "status"
        api = getattr(ctx, "delegation_backends", None)

        if action in ("stats", "savings", "scoreboard"):
            return format_stats_report(compute_stats(db_path, session_id=session_key or None))

        if action in ("doctor", "check", "audit"):
            return run_doctor(config_path=config_path, db_path=db_path)

        if action in ("janitor", "tune", "install-janitor"):
            try:
                return apply_janitor_config(config_path=config_path)
            except Exception as exc:
                return f"Could not apply Janitor settings: {exc}"

        if action in ("on", "enable", "use", "activate") or (action == "status" and now):
            if api is None:
                return "Stagehands: ctx.delegation_backends is unavailable on this Hermes build."
            try:
                if now and session_key:
                    api.set_global_backend("stagehands", session_key=session_key, apply_now=True)
                    msg = (
                        "Stagehands activated (`delegation.backend = stagehands`) and applied to this chat "
                        "(tools will rebuild on your next message)."
                    )
                else:
                    api.set_global_backend("stagehands", session_key=session_key)
                    msg = (
                        "Stagehands saved (`delegation.backend = stagehands`). "
                        "Start a `/new` session or run `/stagehands --now` to rebuild this chat's tools immediately."
                    )
                if with_janitor:
                    msg = f"{msg}\n\n{apply_janitor_config(config_path=config_path)}"
                return msg
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

        return _format_roster()

    return handle_stagehands


def _register_context_ref(ctx: Any) -> None:
    """Register `@stagehands:<target>` inline context references when supported by Hermes."""
    if not hasattr(ctx, "register_context_reference"):
        return
    try:
        from agent.context_references import ContextCompletionItem, ContextReferenceProvider
    except ImportError:
        class ContextCompletionItem:  # type: ignore[no-redef]
            def __init__(self, label: str, text: str, detail: str = "") -> None:
                self.label = label
                self.text = text
                self.detail = detail

        class ContextReferenceProvider:  # type: ignore[no-redef]
            pass

    class StagehandsContextReference(ContextReferenceProvider):
        prefix = "stagehands"
        description = "Inline Stagehands telemetry, doctor check, or worker roster (@stagehands:stats, @stagehands:doctor, @stagehands:roster)"

        async def autocomplete(self, query: str, *, limit: int = 10) -> list[ContextCompletionItem]:
            items = [
                ContextCompletionItem("stats", "@stagehands:stats", "Live Front-Door + Back-Door token & USD savings"),
                ContextCompletionItem("doctor", "@stagehands:doctor", "Two-Door health audit (backend + 48k/120k Janitor)"),
                ContextCompletionItem("roster", "@stagehands:roster", "5-worker backstage roster & model routes"),
            ]
            q = (query or "").strip().lower()
            matched = [it for it in items if not q or q in it.text]
            return matched[:limit]

        async def expand(self, target: str) -> str | None:
            t = (target or "").strip().lower().strip("`'\"")
            if t in ("stats", "savings", "scoreboard", "ledger"):
                return format_stats_report(compute_stats())
            if t in ("doctor", "check", "audit"):
                return run_doctor()
            if t in ("roster", "workers", "status"):
                return _format_roster()
            return None

    try:
        ctx.register_context_reference(StagehandsContextReference())
    except Exception:
        pass


def _render_sovereign_prompt_section(session_info: Any = None) -> str:
    """Frozen Sovereign routing & anti-churn discipline injected once after memory."""
    if isinstance(session_info, dict) and session_info.get("source") == "subagent":
        return ""
    try:
        cfg_path = _resolve_config_path()
        if cfg_path and cfg_path.is_file():
            raw = cfg_path.read_text(encoding="utf-8")
            if "stagehands" not in raw:
                return ""
    except Exception:
        pass
    return (
        "## Sovereign & Stagehands Discipline\n"
        "- **Backstage First (`delegate_task`):** Your parent loop runs on frontier Sovereign compute. "
        "Whenever a task needs 3+ `terminal`, `execute_code`, `read_file`, or `search_files` calls, log/DB "
        "scraping, codebase diffs, or bulky payload synthesis, dispatch `delegate_task` with a typed `worker` "
        "(`scout`, `librarian`, `code_monkey`, `adversary`, `briefer`) instead of running tool loops directly in the parent.\n"
        "- **No Reflexive Skill Reload Churn:** If an earlier `skill_view` result shows `[SKILL_PRUNED: ...]`, "
        "do NOT reload that skill unless your *current* active user request directly needs its exact commands or "
        "templates and no newer load is already in context. When a subtask needs a skill, let `code_monkey` or "
        "`librarian` load and execute it backstage so 40KB skill bodies stay out of Sovereign context."
    )


def register(ctx: Any) -> None:
    """Register the Stagehands delegation provider, `/stagehands` command, `@stagehands:` context ref, and Sovereign prompt section."""
    provider = StagehandsProvider()
    ctx.register_delegation_provider(provider)
    if hasattr(ctx, "register_command"):
        ctx.register_command(
            "stagehands",
            _make_slash_handler(ctx, provider),
            description="Inspect Stagehands workers, live savings (`stats`), audit health (`doctor`), or tune (`janitor`)",
            args_hint="[status | stats | doctor | janitor | on | off] [--janitor] [--now]",
        )
    if hasattr(ctx, "register_system_prompt_section"):
        try:
            ctx.register_system_prompt_section(
                "stagehands.sovereign_routing",
                _render_sovereign_prompt_section,
                position="after_memory",
            )
        except Exception:
            pass
    _register_context_ref(ctx)
