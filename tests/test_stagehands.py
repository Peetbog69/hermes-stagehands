#!/usr/bin/env python3
"""Provider contract tests against the real Hermes v0.22.5 core.

Run with:
    python3 -m unittest discover -s tests -v
or:
    /usr/local/lib/hermes-agent/venv/bin/python -m unittest discover -s tests -v
"""

from copy import deepcopy
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
    ("scout", "deepseek/deepseek-v4-flash", "low", 800),
    ("librarian", "qwen/qwen3.7-flash", "low", 1000),
    ("code_monkey", "deepseek/deepseek-v4.1-flash", "low", 1500),
    ("adversary", "anthropic/claude-haiku-5.5", "medium", 1200),
    ("briefer", "deepseek/deepseek-v4-flash", "low", 600),
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
                        "provider": "nous",
                        "reasoning_effort": effort,
                        "request_overrides": {"max_tokens": budget},
                        "label": worker,
                    },
                )
                self.assertTrue(set(route) <= set(ROUTE_KEYS))
                self.assertNotIn("service_tier", route)
                self.assertNotIn("desc", route)

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
        self.assertEqual(route["request_overrides"], {"max_tokens": 800})
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
            DEFAULT_WORKERS["scout"]["request_overrides"]["max_tokens"], 800
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
