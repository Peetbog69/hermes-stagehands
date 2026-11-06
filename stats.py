#!/usr/bin/env python3
"""Live telemetry & savings calculator for Sovereign & Stagehands + Context Janitor.

Reads Hermes `state.db` (read-only) to compute:
1. Front-Door Bouncer (Stagehands subagents): raw tool tokens absorbed backstage vs.
   compact brief tokens returned to the Sovereign, multiplied by remaining parent turns.
2. Back-Door Janitor (`proactive_prune_tokens` / `ContextCompressor`): bulky parent tool
   results deterministically pruned (`[tool] ... (N chars)` stubs), plus snowball tokens
   avoided across subsequent assistant turns in the same session.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sqlite3
from typing import Any

_PRUNED_CHARS_RE = re.compile(
    r"(?:\(([\d,]+)\s+chars(?:\s+result)?\)|demoted at compaction\s+[—-]\s+([\d,]+)\s+chars\s+preserved)"
)
_PRUNED_TERMINAL_RE = re.compile(
    r"^\[terminal\] ran `.*` -> exit [^,]+,\s*([\d,]+)\s+lines output",
    re.DOTALL,
)
_PRUNED_EXEC_CODE_RE = re.compile(
    r"^\[execute_code\] `.*` \(([\d,]+)\s+lines output\)",
    re.DOTALL,
)
_PRUNED_WRITE_FILE_RE = re.compile(
    r"^\[write_file\] wrote to .* \(([\d,]+|\?)\s+lines\)"
)
_PRUNED_SEARCH_FILES_RE = re.compile(
    r"^\[search_files\] .* search for .* -> ([\d,]+|\?)\s+matches"
)
_PRUNED_DUPLICATE_PREFIX = "[Duplicate tool output"

ARGON_INPUT_USD_PER_M = 3.00
ARGON_UNCACHED_INPUT_USD_PER_M = 2.00
ARGON_CACHED_INPUT_USD_PER_M = 0.10
WORKER_INPUT_USD_PER_M = 0.15


def _estimate_pruned_stub_orig_chars(content: str) -> int | None:
    """Return original char count (exact or conservative estimate) if `content` is a Janitor stub."""
    if not content or not content.startswith("["):
        return None
    if len(content) >= 600 and "[SKILL_PRUNED:" not in content:
        return None
    m = _PRUNED_CHARS_RE.search(content)
    if m:
        raw_num = m.group(1) or m.group(2)
        if raw_num:
            try:
                return int(raw_num.replace(",", ""))
            except ValueError:
                return None
    m_term = _PRUNED_TERMINAL_RE.match(content) or _PRUNED_EXEC_CODE_RE.match(content)
    if m_term:
        try:
            lines = int(m_term.group(1).replace(",", ""))
            return max(400, lines * 80)
        except ValueError:
            return 400
    m_wf = _PRUNED_WRITE_FILE_RE.match(content)
    if m_wf:
        val = m_wf.group(1)
        if val and val != "?":
            try:
                return max(400, int(val.replace(",", "")) * 60)
            except ValueError:
                pass
        return 400
    m_sf = _PRUNED_SEARCH_FILES_RE.match(content)
    if m_sf:
        val = m_sf.group(1)
        if val and val != "?":
            try:
                return max(400, min(20000, int(val.replace(",", "")) * 120))
            except ValueError:
                pass
        return 400
    if content.startswith(_PRUNED_DUPLICATE_PREFIX):
        return 400
    return None


def resolve_state_db(explicit_path: str | Path | None = None) -> Path | None:
    """Locate the active Hermes profile's state.db."""
    if explicit_path:
        p = Path(explicit_path).expanduser()
        return p if p.is_file() else None

    candidates: list[Path] = []
    env_db = os.environ.get("HERMES_STATE_DB")
    if env_db:
        candidates.append(Path(env_db).expanduser())

    profile = os.environ.get("HERMES_PROFILE") or "nimbo"
    hermes_home = Path(os.environ.get("HERMES_HOME", "~/.hermes")).expanduser()
    candidates.append(hermes_home / "profiles" / profile / "state.db")
    candidates.append(hermes_home / "state.db")

    for c in candidates:
        if c.is_file():
            return c
    return None


def compute_stats(
    db_path: str | Path | None = None,
    *,
    session_id: str | None = None,
    since_ts: float | None = None,
) -> dict[str, Any]:
    """Compute Front-Door (Stagehands) and Back-Door (Janitor) token & dollar savings."""
    resolved = resolve_state_db(db_path)
    if resolved is None:
        return {"error": "state.db not found", "db_path": str(db_path or "")}

    uri = f"file:{resolved}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()

        # Check optional columns on sessions (e.g. cache_read_tokens)
        sess_cols = {
            r["name"] for r in cur.execute("PRAGMA table_info(sessions)").fetchall()
        }
        cache_col_sql = (
            ", COALESCE(cache_read_tokens, 0) AS cache_read_tokens "
            if "cache_read_tokens" in sess_cols
            else ", 0 AS cache_read_tokens "
        )

        # Resolve target parent session (latest non-subagent session if not specified
        # or if session_id is a gateway session_key not matching sessions.id)
        active_session: dict[str, Any] = {}
        row = None
        if session_id:
            row = cur.execute(
                f"SELECT id, source, model, started_at, input_tokens, output_tokens, "
                f"message_count, tool_call_count, api_call_count, "
                f"COALESCE(estimated_cost_usd, 0.0) AS estimated_cost_usd"
                f"{cache_col_sql}"
                f"FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            row = cur.execute(
                f"SELECT id, source, model, started_at, input_tokens, output_tokens, "
                f"message_count, tool_call_count, api_call_count, "
                f"COALESCE(estimated_cost_usd, 0.0) AS estimated_cost_usd"
                f"{cache_col_sql}"
                f"FROM sessions s WHERE s.source != 'subagent' "
                f"AND json_extract(s.model_config, '$._delegate_from') IS NULL "
                f"ORDER BY COALESCE((SELECT MAX(m.timestamp) FROM messages m WHERE m.session_id = s.id), s.started_at) DESC LIMIT 1"
            ).fetchone()
        if row:
            active_session = dict(row)
            in_tok = int(active_session.get("input_tokens") or 0)
            cache_tok = int(active_session.get("cache_read_tokens") or 0)
            total_prompt_tok = in_tok + cache_tok
            active_session["cache_hit_rate"] = (
                round(cache_tok / total_prompt_tok, 4) if total_prompt_tok > 0 else 0.0
            )
        active_sid = active_session.get("id")

        # 1. Front-Door Bouncer: subagent runs (Robert Gotcha A: filter subagent explicitly,
        # never bare parent_session_id which also links /new, /branch, and compactions)
        sub_where = [
            "(s.source = 'subagent' OR json_extract(s.model_config, '$._delegate_from') IS NOT NULL)"
        ]
        sub_params: list[Any] = []
        if since_ts is not None:
            sub_where.append("s.started_at >= ?")
            sub_params.append(since_ts)
        if active_sid:
            sub_where.append("s.parent_session_id = ?")
            sub_params.append(active_sid)

        sub_rows = cur.execute(
            f"SELECT s.id, s.parent_session_id, s.model, s.started_at, "
            f"s.input_tokens, s.output_tokens, s.tool_call_count, "
            f"COALESCE(s.estimated_cost_usd, 0.0) AS estimated_cost_usd "
            f"FROM sessions s WHERE {' AND '.join(sub_where)} "
            f"ORDER BY s.started_at DESC",
            sub_params,
        ).fetchall()

        subagent_count = len(sub_rows)
        backstage_raw_tokens = 0
        returned_brief_tokens = 0
        front_door_snowball_tokens = 0
        children_cost_usd = 0.0

        for srow in sub_rows:
            sid = srow["id"]
            children_cost_usd += float(srow["estimated_cost_usd"] or 0.0)
            tool_chars_row = cur.execute(
                "SELECT COALESCE(SUM(LENGTH(content)), 0) AS c "
                "FROM messages WHERE session_id = ? AND role = 'tool'",
                (sid,),
            ).fetchone()
            raw_tok = int((tool_chars_row["c"] if tool_chars_row else 0) // 4)

            last_asst = cur.execute(
                "SELECT COALESCE(LENGTH(content), 0) AS c "
                "FROM messages WHERE session_id = ? AND role = 'assistant' "
                "ORDER BY id DESC LIMIT 1",
                (sid,),
            ).fetchone()
            brief_tok = int((last_asst["c"] if last_asst else 0) // 4)

            delta_tok = max(0, raw_tok - brief_tok)
            backstage_raw_tokens += raw_tok
            returned_brief_tokens += brief_tok

            parent_id = srow["parent_session_id"]
            remaining_turns = 1
            if parent_id:
                t_row = cur.execute(
                    "SELECT COUNT(*) AS cnt FROM messages "
                    "WHERE session_id = ? AND role = 'assistant' "
                    "AND id > COALESCE((SELECT MAX(id) FROM messages WHERE session_id = ?), 0)",
                    (parent_id, sid),
                ).fetchone()
                remaining_turns = max(1, int(t_row["cnt"] if t_row else 1))

            front_door_snowball_tokens += delta_tok * remaining_turns

        # 2. Back-Door Janitor: pruned tool outputs in active session + overall
        def _janitor_for_scope(target_sid: str | None) -> dict[str, int]:
            q = (
                "SELECT m.id, m.session_id, m.tool_name, m.content, "
                "(SELECT COUNT(*) FROM messages m2 "
                " WHERE m2.session_id = m.session_id AND m2.role = 'assistant' AND m2.id > m.id) AS turns_after "
                "FROM messages m "
                "WHERE m.role = 'tool' AND m.content LIKE '[%'"
            )
            params: tuple[Any, ...] = ()
            if target_sid:
                q += " AND m.session_id = ?"
                params = (target_sid,)
            rows = cur.execute(q, params).fetchall()

            pruned_calls = 0
            reclaimed_tokens = 0
            snowball_avoided = 0

            for r in rows:
                c = r["content"] or ""
                orig_chars = _estimate_pruned_stub_orig_chars(c)
                if orig_chars is None:
                    continue
                stub_chars = len(c)
                if orig_chars <= stub_chars:
                    continue
                reclaimed = (orig_chars - stub_chars) // 4
                pruned_calls += 1
                reclaimed_tokens += reclaimed
                turns_after = max(1, int(r["turns_after"] or 1))
                snowball_avoided += reclaimed * turns_after

            return {
                "pruned_calls": pruned_calls,
                "reclaimed_tokens": reclaimed_tokens,
                "snowball_avoided_tokens": snowball_avoided,
            }

        active_sid = active_session.get("id")
        active_janitor = _janitor_for_scope(active_sid) if active_sid else {
            "pruned_calls": 0,
            "reclaimed_tokens": 0,
            "snowball_avoided_tokens": 0,
        }
        profile_janitor = _janitor_for_scope(None)

        total_snowball_avoided = (
            front_door_snowball_tokens + active_janitor["snowball_avoided_tokens"]
        )
        cache_hit_rate = float(active_session.get("cache_hit_rate") or 0.0)
        effective_rate = (
            round(
                ARGON_UNCACHED_INPUT_USD_PER_M * (1.0 - cache_hit_rate)
                + ARGON_CACHED_INPUT_USD_PER_M * cache_hit_rate,
                4,
            )
            if cache_hit_rate > 0
            else ARGON_INPUT_USD_PER_M
        )
        active_saved_usd = (total_snowball_avoided / 1_000_000.0) * ARGON_INPUT_USD_PER_M
        active_cache_adjusted_saved_usd = (
            total_snowball_avoided / 1_000_000.0
        ) * effective_rate
        profile_saved_usd = (
            (front_door_snowball_tokens + profile_janitor["snowball_avoided_tokens"])
            / 1_000_000.0
        ) * ARGON_INPUT_USD_PER_M

        parent_total_cost = float(active_session.get("estimated_cost_usd") or 0.0)
        # Robert Gotcha B: _rollup_children_cost adds children_cost_usd into parent.estimated_cost_usd
        sovereign_only_cost = max(0.0, parent_total_cost - children_cost_usd)
        comp_ratio = (
            round(backstage_raw_tokens / max(1, returned_brief_tokens), 1)
            if backstage_raw_tokens > 0
            else 0.0
        )

        return {
            "db_path": str(resolved),
            "active_session": active_session,
            "front_door": {
                "subagent_runs": subagent_count,
                "backstage_raw_tokens": backstage_raw_tokens,
                "returned_brief_tokens": returned_brief_tokens,
                "compression_ratio": comp_ratio,
                "children_cost_usd": round(children_cost_usd, 4),
                "sovereign_only_cost_usd": round(sovereign_only_cost, 4),
                "snowball_avoided_tokens": front_door_snowball_tokens,
            },
            "janitor_active_session": active_janitor,
            "janitor_profile_total": profile_janitor,
            "active_snowball_avoided_tokens": total_snowball_avoided,
            "effective_input_usd_per_m": effective_rate,
            "active_estimated_saved_usd": round(active_saved_usd, 4),
            "active_cache_adjusted_saved_usd": round(active_cache_adjusted_saved_usd, 4),
            "profile_estimated_saved_usd": round(profile_saved_usd, 2),
        }
    finally:
        conn.close()


def compute_savings(
    session_id: str | None = None,
    db_path: str | Path | None = None,
    *,
    since_ts: float | None = None,
) -> dict[str, Any]:
    """Spec-compatible alias for `compute_stats()`.

    ``BRUTALIST_SCOREBOARD_SPEC.md`` calls ``compute_savings('sess_parent',
    db_path=...)``. This delegates to the real implementation so callers (and
    regression tests) use one code path.
    """
    return compute_stats(db_path, session_id=session_id, since_ts=since_ts)


def format_stats_report(stats: dict[str, Any]) -> str:
    """Format a compact Telegram/CLI scoreboard from `compute_stats()`."""
    if "error" in stats:
        return f"Stagehands Stats: {stats['error']}"

    sess = stats.get("active_session") or {}
    fd = stats["front_door"]
    jan_s = stats["janitor_active_session"]
    jan_p = stats["janitor_profile_total"]

    sid = sess.get("id", "none")
    s_model = sess.get("model", "unknown")
    s_in = int(sess.get("input_tokens") or 0)
    s_cache = int(sess.get("cache_read_tokens") or 0)
    s_hit = float(sess.get("cache_hit_rate") or 0.0) * 100.0
    s_msgs = int(sess.get("message_count") or 0)
    s_tools = int(sess.get("tool_call_count") or 0)
    eff_rate = float(stats.get("effective_input_usd_per_m") or ARGON_INPUT_USD_PER_M)
    cache_adj_usd = float(stats.get("active_cache_adjusted_saved_usd") or stats["active_estimated_saved_usd"])
    cache_line = (
        f" · {s_cache:,} cache reads ({s_hit:.1f}% KV hit, eff ${eff_rate:.2f}/M)"
        if s_cache > 0
        else ""
    )

    lines = [
        "📊 Sovereign & Stagehands — Live Savings Scoreboard",
        f"  • Active Session: `{sid}` ({s_model})",
        f"    {s_msgs} msgs · {s_tools} tool calls · {s_in:,} cumulative input tokens{cache_line}",
        "  • Front-Door Bouncer (Stagehands Workers):",
        f"    {fd['subagent_runs']} runs · {fd['backstage_raw_tokens']:,} raw tokens absorbed backstage "
        f"→ {fd['returned_brief_tokens']:,} brief tokens returned "
        f"({fd['snowball_avoided_tokens']:,} snowball tokens dodged)",
        "  • Back-Door Janitor (Active Session Pruner):",
        f"    {jan_s['pruned_calls']} bulky tool outputs pruned · "
        f"{jan_s['reclaimed_tokens']:,} raw tokens reclaimed · "
        f"{jan_s['snowball_avoided_tokens']:,} re-read tokens dodged "
        f"(${stats['active_estimated_saved_usd']:.2f} list / ${cache_adj_usd:.2f} cache-adj saved this chat)",
        "  • Profile Lifetime Janitor + Stagehands:",
        f"    {jan_p['pruned_calls']:,} pruned tool dumps · "
        f"{jan_p['reclaimed_tokens']:,} raw tokens reclaimed · "
        f"~${stats['profile_estimated_saved_usd']:.2f} Argon snowball avoided (@ $3/M input)",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Stagehands & Janitor savings stats")
    parser.add_argument("--db", help="Explicit state.db path")
    parser.add_argument("--session", help="Specific parent session_id")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument("--save", help="Write JSON snapshot to path")
    args = parser.parse_args()

    data = compute_stats(args.db, session_id=args.session)
    if args.save:
        out = Path(args.save)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(format_stats_report(data))


if __name__ == "__main__":
    main()
