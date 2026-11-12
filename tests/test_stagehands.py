#!/usr/bin/env python3
"""Provider contract tests against the real Hermes v0.22.5 core.

Run with:
    python3 -m unittest discover -s tests -v
or:
    /usr/local/lib/hermes-agent/venv/bin/python -m unittest discover -s tests -v
"""

from copy import deepcopy
import tempfile
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
HERMES_ROOT = Path("/usr/local/lib/hermes-agent")
for candidate in (ROOT, HERMES_ROOT):
    if candidate.is_dir() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from agent.delegation_provider import (  # noqa: E402
    ROUTE_KEYS,
    DelegationProvider,
    DelegationRouteError,
)
from plugins.delegation.default import DefaultDelegationProvider  # noqa: E402
from provider import DEFAULT_WORKERS, StagehandsProvider  # noqa: E402

WORKERS = ["scout", "librarian", "code_monkey", "adversary", "briefer"]
EXPECTED_ROUTES = [
    ("scout", "deepseek/deepseek-v4-flash", "low", 8192),
    ("librarian", "qwen/qwen3.7-flash", "low", 8192),
    ("code_monkey", "deepseek/deepseek-v4.1-flash", "low", 16384),
    ("adversary", "anthropic/claude-haiku-5.5", "medium", 8192),
    ("briefer", "deepseek/deepseek-v4-flash", "low", 8192),
]


def worker_config(workers):
    """Provider methods receive the delegation section, not the entire config."""
    return {"backends": {"stagehands": {"workers": workers}}}


class TestStagehandsProvider(unittest.TestCase):
    def setUp(self):
        self.provider = StagehandsProvider()

    def test_native_provider_identity(self):
        self.assertIsInstance(self.provider, DelegationProvider)
        self.assertEqual(self.provider.name, "stagehands")
        self.assertEqual(self.provider.display_name, "Stagehands")
        self.assertTrue(self.provider.is_available())

    def test_zero_config_roster_and_deterministic_schema(self):
        for config in ({}, worker_config({}), worker_config([])):
            with self.subTest(config=config):
                original = deepcopy(config)
                parameter = self.provider.task_parameters(config)["worker"]
                self.assertEqual(parameter["type"], "string")
                self.assertEqual(parameter["enum"], WORKERS)
                first = (
                    deepcopy(self.provider.task_parameters(config)),
                    self.provider.description(config),
                )
                self.assertEqual(
                    first,
                    (self.provider.task_parameters(config), self.provider.description(config)),
                )
                self.assertEqual(
                    first,
                    (
                        StagehandsProvider().task_parameters(config),
                        StagehandsProvider().description(config),
                    ),
                )
                self.assertEqual(config, original)

    def test_default_routes_cross_real_core_boundary(self):
        for worker, model, effort, budget in EXPECTED_ROUTES:
            with self.subTest(worker=worker):
                route = self.provider.route_task(
                    {"goal": "Return a compact evidence brief", "worker": worker}, {}
                )
                self.assertEqual(
                    route,
                    {
                        "model": model,
                        "reasoning_effort": effort,
                        "request_overrides": {"max_tokens": budget},
                        "label": worker,
                    },
                )
                self.assertTrue(set(route) <= set(ROUTE_KEYS))
                self.assertNotIn("provider", route)
                self.assertNotIn("service_tier", route)
                self.assertNotIn("desc", route)

    def test_worker_inherits_delegation_provider_when_set(self):
        route = self.provider.route_task(
            {"goal": "Read logs", "worker": "scout"},
            {"provider": "openrouter"},
        )
        self.assertEqual(route["provider"], "openrouter")
        self.assertEqual(route["model"], "deepseek/deepseek-v4-flash")

    def test_parent_fast_tier_is_not_inherited_by_workers(self):
        for backend in ("nous", "openrouter"):
            for worker in WORKERS:
                with self.subTest(backend=backend, worker=worker):
                    config = worker_config({worker: {"provider": backend}})
                    config.update(model="parent/model", provider=backend, service_tier="fast")
                    route = self.provider.route_task(
                        {"goal": "Read logs", "worker": worker}, config
                    )
                    self.assertEqual(route["provider"], backend)
                    self.assertNotIn("service_tier", route)

    def test_explicit_worker_fast_tier_is_preserved(self):
        config = worker_config({"scout": {"service_tier": "fast"}})
        self.assertEqual(
            self.provider.route_task({"worker": "scout"}, config)["service_tier"],
            "fast",
        )

    def test_unset_worker_tier_is_not_emitted(self):
        for tier in (None, ""):
            with self.subTest(tier=tier):
                config = worker_config({"scout": {"service_tier": tier}})
                self.assertNotIn(
                    "service_tier",
                    self.provider.route_task({"worker": "scout"}, config),
                )

    def test_unknown_worker_fails_closed_and_lists_roster(self):
        with self.assertRaises(DelegationRouteError) as ctx:
            self.provider.route_task({"goal": "x", "worker": "janitor"}, {})
        message = str(ctx.exception)
        self.assertIn("janitor", message)
        for worker in WORKERS:
            self.assertIn(worker, message)

    def test_invalid_worker_values_raise_route_error(self):
        for worker in (42, True, [], {}, " scout "):
            with self.subTest(worker=worker):
                with self.assertRaises(DelegationRouteError):
                    self.provider.route_task({"goal": "x", "worker": worker}, {})

    def test_omitted_worker_matches_default_provider_without_fast_tier(self):
        for selection in ({}, {"worker": None}, {"worker": ""}):
            with self.subTest(selection=selection):
                task = {"goal": "x", **selection}
                config = {"model": "fallback-m", "provider": "nous", "service_tier": "fast"}
                original = deepcopy(config)
                route = self.provider.route_task(task, config)
                self.assertEqual(route, {"model": "fallback-m", "provider": "nous"})
                self.assertEqual(route, DefaultDelegationProvider().route_task(task, config))
                self.assertEqual(config, original)

    def test_description_teaches_personas_and_brevity(self):
        description = self.provider.description({})
        for worker in WORKERS:
            self.assertIn(f"`{worker}`", description)
        self.assertIn("concise, structured briefs", description)
        self.assertIn("output_schema", description)
        self.assertIn("raw logs", description)
        self.assertIn("Omit `worker` only", description)

    def test_dict_override_merges_with_default_roster(self):
        config = worker_config({"scout": {"model": "custom/m"}})
        original = deepcopy(config)
        defaults = deepcopy(DEFAULT_WORKERS)
        workers = self.provider._workers(config)
        self.assertEqual(list(workers), WORKERS)
        self.assertEqual(workers["scout"], {**defaults["scout"], "model": "custom/m"})
        for worker in WORKERS[1:]:
            self.assertEqual(workers[worker], defaults[worker])
        self.assertEqual(
            self.provider.route_task({"worker": "scout"}, config)["model"], "custom/m"
        )
        self.assertEqual(config, original)
        self.assertEqual(DEFAULT_WORKERS, defaults)

    def test_list_override_selects_roster_and_inherits_worker_defaults(self):
        config = worker_config([{"name": "scout", "model": "custom/m"}])
        original = deepcopy(config)
        self.assertEqual(
            self.provider._workers(config),
            {"scout": {**DEFAULT_WORKERS["scout"], "model": "custom/m"}},
        )
        self.assertEqual(
            self.provider.task_parameters(config)["worker"]["enum"], ["scout"]
        )
        route = self.provider.route_task({"worker": "scout"}, config)
        self.assertEqual(route["model"], "custom/m")
        self.assertEqual(route["request_overrides"], {"max_tokens": 8192})
        self.assertNotIn("name", route)
        with self.assertRaises(DelegationRouteError):
            self.provider.route_task({"worker": "librarian"}, config)
        self.assertEqual(config, original)

    def test_new_custom_worker_and_metadata_filtering(self):
        config = worker_config(
            {
                "reviewer": {
                    "model": "custom/reviewer",
                    "provider": "openrouter",
                    "request_overrides": {"max_tokens": 123},
                    "description": "A short review",
                    "unrecognized": "must not reach the router",
                }
            }
        )
        route = self.provider.route_task({"worker": "reviewer"}, config)
        self.assertEqual(
            route,
            {
                "label": "reviewer",
                "model": "custom/reviewer",
                "provider": "openrouter",
                "request_overrides": {"max_tokens": 123},
            },
        )
        self.assertTrue(set(route) <= set(ROUTE_KEYS))
        self.assertEqual(
            self.provider.task_parameters(config)["worker"]["enum"],
            WORKERS + ["reviewer"],
        )

    def test_malformed_roster_retains_defaults(self):
        for workers in (None, "invalid", [None, {}, {"name": " "}]):
            with self.subTest(workers=workers):
                self.assertEqual(
                    self.provider._workers(worker_config(workers)), DEFAULT_WORKERS
                )

    def test_returned_route_budget_does_not_mutate_configuration(self):
        config = worker_config({"scout": {"request_overrides": {"max_tokens": 321}}})
        original = deepcopy(config)
        route = self.provider.route_task({"worker": "scout"}, config)
        route["request_overrides"]["max_tokens"] = 1
        self.assertEqual(config, original)
        self.assertEqual(
            self.provider.route_task({"worker": "scout"}, config)["request_overrides"],
            {"max_tokens": 321},
        )
        default_route = self.provider.route_task({"worker": "scout"}, {})
        default_route["request_overrides"]["max_tokens"] = 1
        self.assertEqual(
            DEFAULT_WORKERS["scout"]["request_overrides"]["max_tokens"], 8192
        )

    def test_register_wires_provider_and_slash_command(self):
        import asyncio
        import __init__ as stagehands_pkg

        providers = []
        commands = {}
        calls = []
        context_refs = []
        prompt_sections = {}

        class StubBackends:
            def set_global_backend(self, name, *, session_key="", apply_now=False):
                calls.append((name, session_key, apply_now))

        class StubCtx:
            delegation_backends = StubBackends()

            def register_delegation_provider(self, p):
                providers.append(p)

            def register_command(self, name, handler, **kwargs):
                commands[name] = (handler, kwargs)

            def register_context_reference(self, ref):
                context_refs.append(ref)

            def register_system_prompt_section(self, sec_id, content, **kwargs):
                prompt_sections[sec_id] = (content, kwargs)

        stagehands_pkg.register(StubCtx())
        self.assertEqual(len(providers), 1)
        self.assertEqual(providers[0].name, "stagehands")
        self.assertIn("stagehands", commands)
        self.assertEqual(len(context_refs), 1)
        self.assertEqual(context_refs[0].prefix, "stagehands")
        self.assertIn("stagehands.sovereign_routing", prompt_sections)
        sec_fn, sec_kw = prompt_sections["stagehands.sovereign_routing"]
        self.assertEqual(sec_kw.get("position"), "after_memory")
        self.assertEqual(sec_fn({"source": "subagent"}), "")
        self.assertIn("Backstage First", sec_fn({"source": "telegram"}))
        self.assertIn("No Reflexive Skill Reload Churn", sec_fn({"source": "telegram"}))

        handler, _ = commands["stagehands"]
        roster_text = handler("")
        for worker in WORKERS:
            self.assertIn(worker, roster_text)

        now_text = handler("--now", session_key="tg_123")
        self.assertIn("applied to this chat", now_text)
        self.assertEqual(calls[-1], ("stagehands", "tg_123", True))

        stats_text = handler("stats")
        self.assertIn("Stagehands", stats_text)

        # Test turnkey /stagehands doctor and /stagehands janitor against a temp config.yaml
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_file = Path(tmpdir) / "config.yaml"
            cfg_file.write_text(
                "delegation:\n  backend: default\ncompression:\n  hygiene_hard_message_limit: 140\n",
                encoding="utf-8",
            )

            doc_warn = handler("doctor", config_path=cfg_file)
            self.assertIn("[WARN] Door #1", doc_warn)
            self.assertIn("[WARN] Door #2a", doc_warn)
            self.assertIn("[WARN] Door #2d", doc_warn)

            jan_out = handler("janitor", config_path=cfg_file)
            self.assertIn("proactive_prune_tokens=48000", jan_out)
            self.assertIn("threshold_tokens=120000", jan_out)
            self.assertIn("hygiene_hard_message_limit=2000", jan_out)

            # Simulate /stagehands on setting backend: stagehands
            cfg_file.write_text(
                cfg_file.read_text(encoding="utf-8").replace("backend: default", "backend: stagehands"),
                encoding="utf-8",
            )
            doc_pass = handler("doctor", config_path=cfg_file)
            self.assertIn("[PASS] Door #1", doc_pass)
            self.assertIn("[PASS] Door #2a", doc_pass)
            self.assertIn("[PASS] Door #2d", doc_pass)
            self.assertIn("BOTH DOORS ARMED AND HEALTHY", doc_pass)

        # Test @stagehands:roster context reference expansion
        expanded_roster = asyncio.run(context_refs[0].expand("roster"))
        self.assertIn("Backstage Worker Roster", expanded_roster)


class TestSqlTrapsRegression(unittest.TestCase):
    """SQL Trap A & B regression tests (BRUTALIST_SCOREBOARD_SPEC.md).

    Trap A: the Front-Door Bouncer must count ONLY real Stagehands subagents --
        ``source = 'subagent'`` OR ``model_config._delegate_from`` non-null --
        and must NOT be fooled by unrelated lineage rows (``/new``, ``/branch``,
        compactions) that share ``parent_session_id``.

    Trap B: sovereign-only cost must SUBTRACT rolled-up child cost
        (``_rollup_children_cost`` folds children into the parent's
        ``estimated_cost_usd``), never double-count it.
    """

    PARENT = "sess_parent"
    PARENT_COST = 10.00
    SUB = "sess_subagent"
    SUB_COST = 2.50

    def setUp(self):
        import sqlite3

        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "state.db"
        conn = sqlite3.connect(self.db_path)
        conn.executescript(
            """
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY, source TEXT, model TEXT, model_config TEXT,
                parent_session_id TEXT, started_at REAL, input_tokens INTEGER,
                output_tokens INTEGER, message_count INTEGER, tool_call_count INTEGER,
                api_call_count INTEGER, estimated_cost_usd REAL
            );
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY, session_id TEXT, role TEXT, content TEXT,
                tool_name TEXT, timestamp REAL
            );
            """
        )
        cols = "id, source, model, model_config, parent_session_id, started_at, input_tokens, output_tokens, message_count, tool_call_count, api_call_count, estimated_cost_usd"
        vals = "?,?,?,?,?,?,?,?,?,?,?,?"
        # Parent (sovereign). estimated_cost_usd already folds in children cost.
        conn.execute(
            f"INSERT INTO sessions ({cols}) VALUES ({vals})",
            (self.PARENT, "telegram", "google/gemini-4-argon", None, None,
             1000.0, 500000, 2000, 120, 30, 12, self.PARENT_COST),
        )
        # Real subagent child (MUST be counted by Trap A).
        conn.execute(
            f"INSERT INTO sessions ({cols}) VALUES ({vals})",
            (self.SUB, "subagent", "deepseek/deepseek-v4.1-flash",
             '{"_delegate_from": "scout"}', self.PARENT,
             1001.0, 40000, 500, 8, 4, 3, self.SUB_COST),
        )
        # DECOY lineage row: shares parent_session_id but is a /branch, NOT a
        # subagent. Trap A must EXCLUDE it.
        conn.execute(
            f"INSERT INTO sessions ({cols}) VALUES ({vals})",
            ("sess_branch", "telegram", "google/gemini-4-argon",
             '{"branch_of": "sess_parent"}', self.PARENT,
             1002.0, 300000, 1000, 70, 20, 9, 5.00),
        )
        mcols = "session_id, role, content, tool_name, timestamp"
        # Real subagent: bulky raw tool dump -> compact brief.
        raw = "[tool] " + ("x" * 40000) + "\n(40000 chars)"
        conn.execute(
            f"INSERT INTO messages ({mcols}) VALUES (?,?,?,?,?)",
            (self.SUB, "tool", raw, "terminal", 1001.1),
        )
        conn.execute(
            f"INSERT INTO messages ({mcols}) VALUES (?,?,?,?,?)",
            (self.SUB, "assistant", "brief" * 100, None, 1001.2),
        )
        # Decoy tool message under the branch row: must NOT inflate counts.
        conn.execute(
            f"INSERT INTO messages ({mcols}) VALUES (?,?,?,?,?)",
            ("sess_branch", "tool", "[tool] " + ("y" * 30000), "terminal", 1002.1),
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self):
        import stats

        return stats.compute_savings(self.PARENT, db_path=self.db_path)

    def test_report_labels_latest_profile_fallback_not_current_chat(self):
        import stats

        for session_id in (None, "gateway:telegram:chat:1"):
            with self.subTest(session_id=session_id):
                result = stats.compute_stats(self.db_path, session_id=session_id)
                self.assertEqual(result["active_session"]["id"], "sess_branch")
                self.assertEqual(result["session_scope"], "latest_in_profile")
                report = stats.format_stats_report(result).lower()
                self.assertIn("latest session in this profile", report)
                self.assertIn("not necessarily this chat", report)
                self.assertNotIn("saved this chat", report)
                self.assertNotIn("active session", report)

    def test_report_labels_exact_session_selection(self):
        import stats

        result = stats.compute_stats(self.db_path, session_id=self.PARENT)
        self.assertEqual(result["session_scope"], "exact")
        self.assertEqual(result["active_session"]["id"], self.PARENT)
        self.assertNotIn("latest session in this profile", stats.format_stats_report(result).lower())

    def test_no_parent_session_does_not_count_profile_runs_as_session(self):
        import sqlite3
        import stats

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM sessions WHERE source != 'subagent'")
        result = stats.compute_stats(self.db_path)
        self.assertEqual(result["session_scope"], "none")
        self.assertEqual(result["front_door"]["subagent_runs"], 0)
        self.assertEqual(result["front_door_profile_total"]["subagent_runs"], 1)

    def test_trap_a_subagent_filter_excludes_branch_lineage(self):
        fd = self._run()["front_door"]
        # Exactly ONE real subagent; the /branch decoy is excluded.
        self.assertEqual(fd["subagent_runs"], 1)
        # Raw tokens come only from the real subagent's dump -- len("[tool] " +
        # "x"*40000 + "\n(40000 chars)") == 40021, //4 == 10005 -- never the
        # branch's 30000-char dump.
        self.assertEqual(fd["backstage_raw_tokens"], 10005)
        self.assertGreater(fd["returned_brief_tokens"], 0)
        self.assertLess(fd["returned_brief_tokens"], fd["backstage_raw_tokens"])

    def test_trap_b_sovereign_cost_subtracts_children(self):
        fd = self._run()["front_door"]
        # children_cost_usd is the real subagent's cost only (Trap A scope).
        self.assertAlmostEqual(fd["children_cost_usd"], self.SUB_COST, places=4)
        # Sovereign-only cost == parent total minus rolled-in children cost.
        self.assertAlmostEqual(
            fd["sovereign_only_cost_usd"], self.PARENT_COST - self.SUB_COST, places=4
        )
        self.assertNotAlmostEqual(
            fd["sovereign_only_cost_usd"], self.PARENT_COST, places=4
        )

    def test_trap_a_b_parent_session_is_resolved_sovereign(self):
        out = self._run()
        self.assertEqual(out["active_session"]["id"], self.PARENT)
        self.assertEqual(out["active_session"]["source"], "telegram")

    def test_janitor_counts_both_proactive_and_compaction_demoted_stubs(self):
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        mcols = "session_id, role, content, tool_name, timestamp"
        conn.execute(
            f"INSERT INTO messages ({mcols}) VALUES (?,?,?,?,?)",
            (
                self.PARENT,
                "tool",
                "[read_file] read /tmp/big.py from line 1 (20,000 chars)",
                "read_file",
                1003.0,
            ),
        )
        conn.execute(
            f"INSERT INTO messages ({mcols}) VALUES (?,?,?,?,?)",
            (
                self.PARENT,
                "tool",
                "[read_file output demoted at compaction — 16,000 chars preserved in session history.]",
                "read_file",
                1003.1,
            ),
        )
        conn.execute(
            f"INSERT INTO messages ({mcols}) VALUES (?,?,?,?,?)",
            (self.PARENT, "assistant", "Done.", None, 1003.2),
        )
        conn.commit()
        conn.close()

        jan = self._run()["janitor_active_session"]
        self.assertEqual(jan["pruned_calls"], 2)
        self.assertGreater(jan["reclaimed_tokens"], 8000)

    def test_janitor_counts_terminal_exec_search_write_and_duplicate_stubs(self):
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        mcols = "session_id, role, content, tool_name, timestamp"
        stubs = [
            (
                "[terminal] ran `pytest -q` -> exit 0, 120 lines output",
                "terminal",
                1004.0,
            ),
            (
                "[execute_code] `from hermes_tools import terminal...` (80 lines output)",
                "execute_code",
                1004.1,
            ),
            (
                "[search_files] content search for 'foo' in /tmp -> 25 matches",
                "search_files",
                1004.2,
            ),
            (
                "[write_file] wrote to /tmp/out.py (50 lines)",
                "write_file",
                1004.3,
            ),
            (
                "[Duplicate tool output — same content as a more recent call]",
                "skill_view",
                1004.4,
            ),
        ]
        for content, tname, ts in stubs:
            conn.execute(
                f"INSERT INTO messages ({mcols}) VALUES (?,?,?,?,?)",
                (self.PARENT, "tool", content, tname, ts),
            )
        conn.execute(
            f"INSERT INTO messages ({mcols}) VALUES (?,?,?,?,?)",
            (self.PARENT, "assistant", "Done.", None, 1005.0),
        )
        conn.commit()
        conn.close()

        jan = self._run()["janitor_active_session"]
        self.assertEqual(jan["pruned_calls"], 5)
        self.assertGreater(jan["reclaimed_tokens"], 4000)

    def test_resolve_state_db_no_hardcoded_nimbo_when_profile_unset(self):
        import os
        import stats

        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            default_db = home / "state.db"
            default_db.write_text("", encoding="utf-8")
            decoy_nimbo = home / "profiles" / "nimbo" / "state.db"
            decoy_nimbo.parent.mkdir(parents=True, exist_ok=True)
            decoy_nimbo.write_text("", encoding="utf-8")

            old_home = os.environ.get("HERMES_HOME")
            old_prof = os.environ.get("HERMES_PROFILE")
            old_db = os.environ.get("HERMES_STATE_DB")
            try:
                os.environ["HERMES_HOME"] = str(home)
                os.environ.pop("HERMES_PROFILE", None)
                os.environ.pop("HERMES_STATE_DB", None)
                self.assertEqual(stats.resolve_state_db(), default_db)

                # HERMES_PROFILE is not a database selector; Hermes owns home resolution.
                os.environ["HERMES_PROFILE"] = "nimbo"
                self.assertEqual(stats.resolve_state_db(), default_db)
            finally:
                for k, v in (("HERMES_HOME", old_home), ("HERMES_PROFILE", old_prof), ("HERMES_STATE_DB", old_db)):
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v

    def test_sovereign_prompt_gate_respects_delegation_backend(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("stagehands_init", ROOT / "__init__.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "config.yaml"
            cfg.write_text("delegation:\n  backend: default\n", encoding="utf-8")
            self.assertEqual(mod._render_sovereign_prompt_section(config_path=cfg), "")

            cfg.write_text("delegation:\n  backend: stagehands\n", encoding="utf-8")
            rendered = mod._render_sovereign_prompt_section(config_path=cfg)
            self.assertIn("Sovereign & Stagehands Discipline", rendered)
            self.assertEqual(
                mod._render_sovereign_prompt_section({"source": "subagent"}, config_path=cfg),
                "",
            )

    def test_profile_lifetime_front_door_persists_across_new_session_and_doctor_door1b(self):
        import importlib.util
        import sqlite3
        import stats

        conn = sqlite3.connect(self.db_path)
        conn.execute("ALTER TABLE sessions ADD COLUMN system_prompt TEXT")
        cols = "id, source, model, model_config, parent_session_id, started_at, input_tokens, output_tokens, message_count, tool_call_count, api_call_count, estimated_cost_usd, system_prompt"
        vals = "?,?,?,?,?,?,?,?,?,?,?,?,?"
        conn.execute(
            f"INSERT INTO sessions ({cols}) VALUES ({vals})",
            (
                "sess_newer_parent",
                "telegram",
                "google/gemini-4-argon",
                None,
                self.PARENT,
                2000.0,
                10000,
                200,
                4,
                0,
                2,
                0.50,
                "Base prompt without hook",
            ),
        )
        conn.commit()
        conn.close()

        res = stats.compute_stats(self.db_path, session_id="sess_newer_parent")
        self.assertEqual(res["front_door"]["subagent_runs"], 0)
        self.assertEqual(res["front_door_profile_total"]["subagent_runs"], 1)
        report = stats.format_stats_report(res)
        self.assertIn("1 backstage worker runs", report)

        spec = importlib.util.spec_from_file_location("stagehands_init", ROOT / "__init__.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "config.yaml"
            cfg.write_text("delegation:\n  backend: stagehands\n", encoding="utf-8")
            doc_warn = mod.run_doctor(config_path=cfg, db_path=self.db_path)
            self.assertIn("[WARN] Door #1b · Live Prompt Hook Pinned", doc_warn)

            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "UPDATE sessions SET system_prompt = ? WHERE id = ?",
                ("## Sovereign & Stagehands Discipline\n...", "sess_newer_parent"),
            )
            conn.commit()
            conn.close()

            doc_pass = mod.run_doctor(config_path=cfg, db_path=self.db_path)
            self.assertIn("[PASS] Door #1b · Live Prompt Hook Pinned", doc_pass)

    def test_demo_fast_runs_zero_setup_subprocess(self):
        import subprocess, sys
        proc = subprocess.run(
            [sys.executable, str(ROOT / "demo.py"), "--fast", "--color", "never"],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            timeout=15,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("SOVEREIGN & STAGEHANDS", proc.stdout)
        self.assertIn("deepseek/deepseek-v4.1-flash", proc.stdout)
        self.assertIn("95.9%", proc.stdout)



if __name__ == "__main__":
    unittest.main(verbosity=2)
