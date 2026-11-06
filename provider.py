"""Route delegated tasks to specialized, token-budgeted backstage workers."""

from __future__ import annotations

from typing import Any, Mapping

from agent.delegation_provider import (
    ROUTE_KEYS,
    DelegationProvider,
    DelegationRouteError,
)

DEFAULT_WORKERS: dict[str, dict[str, Any]] = {
    "scout": {
        "model": "deepseek/deepseek-v4-flash",
        "reasoning_effort": "low",
        "request_overrides": {"max_tokens": 4096},
        "desc": "Fast log/file/URL reader; extracts signal and drops raw noise (<=300 words)",
    },
    "librarian": {
        "model": "qwen/qwen3.7-flash",
        "reasoning_effort": "low",
        "request_overrides": {"max_tokens": 4096},
        "desc": "Multi-source doc and codebase searcher returning cited excerpts only (<=350 words)",
    },
    "code_monkey": {
        "model": "deepseek/deepseek-v4.1-flash",
        "reasoning_effort": "low",
        "request_overrides": {"max_tokens": 4096},
        "desc": "Backstage mechanic for repo greps, test runs, and root-cause diffs (<=400 words)",
    },
    "adversary": {
        "model": "anthropic/claude-haiku-5.5",
        "reasoning_effort": "medium",
        "request_overrides": {"max_tokens": 4096},
        "desc": "Red-team auditor finding edge cases, race conditions, and security holes (<=350 words)",
    },
    "briefer": {
        "model": "deepseek/deepseek-v4-flash",
        "reasoning_effort": "low",
        "request_overrides": {"max_tokens": 4096},
        "desc": "Executive synthesizer pre-digesting heavy JSON/payload dumps into compact briefs (<=250 words)",
    },
}

_WORKER_ROUTE_FIELDS = (
    "model",
    "provider",
    "base_url",
    "api_key",
    "api_mode",
    "reasoning_effort",
    "service_tier",
    "request_overrides",
    "fallback_providers",
    "profile",
)


class StagehandsProvider(DelegationProvider):
    """Delegate by typed worker role while retaining the sovereign route when omitted."""

    @property
    def name(self) -> str:
        return "stagehands"

    @property
    def display_name(self) -> str:
        return "Stagehands"

    @property
    def summary(self) -> str:
        return "Route delegated tasks to typed, budgeted backstage workers (scout, librarian, code_monkey, adversary, briefer)."

    def _workers(self, config: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        """Resolve the active worker roster from settings, merging overrides onto DEFAULT_WORKERS.

        Accepts either a dict mapping ``{name: spec}`` or a list of dicts ``[{name: ..., ...}]``
        under ``delegation.backends.stagehands.workers``. When unset or empty, returns DEFAULT_WORKERS
        so the plugin works zero-config out of the box.
        """
        raw = self.settings(config).get("workers")
        if not raw:
            return {k: dict(v) for k, v in DEFAULT_WORKERS.items()}

        merged: dict[str, dict[str, Any]] = {
            k: dict(v) for k, v in DEFAULT_WORKERS.items()
        }
        if isinstance(raw, Mapping):
            for name, spec in raw.items():
                if isinstance(name, str) and isinstance(spec, Mapping):
                    base = dict(merged.get(name, {}))
                    base.update(spec)
                    merged[name] = base
            return merged

        if isinstance(raw, list):
            custom: dict[str, dict[str, Any]] = {}
            for item in raw:
                if isinstance(item, Mapping) and isinstance(item.get("name"), str):
                    wname = item["name"].strip()
                    if wname:
                        base = dict(DEFAULT_WORKERS.get(wname, {}))
                        base.update({k: v for k, v in item.items() if k != "name"})
                        custom[wname] = base
            if custom:
                return custom

        return merged

    def description(self, config: Mapping[str, Any]) -> str:
        workers = self._workers(config)
        roster = "; ".join(
            f"`{name}` ({w.get('model', 'default')}): {w.get('desc', w.get('description', name))}"
            for name, w in workers.items()
        )
        return (
            "Sovereign & Stagehands routing — keep raw logs, grep dumps, and bulky payloads out of "
            "your primary context by picking a typed `worker` per task: "
            f"{roster}. "
            "SOVEREIGN RULE (overrides default 'DO NOT USE FOR' above): your parent turn runs on "
            "expensive frontier compute — whenever work needs 3+ shell/file/DB probes, log scraping, "
            "codebase greps/tests, or multi-doc/skill reading, delegate it to `scout`, `librarian`, "
            "`code_monkey`, `adversary`, or `briefer` instead of chaining `terminal`, `execute_code`, "
            "or `read_file` loops directly in the parent. "
            "Ask backstage workers for concise, structured briefs or use `output_schema` to bound "
            "their response. Omit `worker` only when a subagent genuinely needs the parent route."
        )

    def is_available(self) -> bool:
        return True

    def task_parameters(self, config: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        workers = self._workers(config)
        names = list(workers.keys())
        details = "; ".join(
            f"{name}: {w.get('desc', w.get('description', name))}"
            for name, w in workers.items()
        )
        return {
            "worker": {
                "type": "string",
                "enum": names,
                "description": f"Backstage worker role for this task ({details}).",
            }
        }

    def route_task(
        self, task: Mapping[str, Any], config: Mapping[str, Any]
    ) -> dict[str, Any]:
        worker_name = task.get("worker")
        workers = self._workers(config)

        if worker_name is not None and worker_name != "":
            if not isinstance(worker_name, str) or worker_name not in workers:
                available = ", ".join(workers.keys())
                raise DelegationRouteError(
                    f"Unknown stagehand worker {worker_name!r}. "
                    f"Choose one of: {available}."
                )
            worker = workers[worker_name]
            route: dict[str, Any] = {"label": worker_name}
            for field in _WORKER_ROUTE_FIELDS:
                val = worker.get(field)
                # Inherit delegation.provider when worker doesn't pin one; when both are
                # unset, omitting 'provider' lets Hermes inherit the parent session's
                # active provider (Nous Portal, OpenRouter, etc.) and auto-derive api_mode.
                if field == "provider" and (val is None or val == ""):
                    val = config.get("provider")
                # Only emit service_tier or other optional fields when explicitly set;
                # an unsupported default service_tier='fast' fails spawn in task_service_tier().
                if val is not None and val != "":
                    if field == "request_overrides" and isinstance(val, Mapping):
                        route[field] = dict(val)
                    else:
                        route[field] = val
            return {k: v for k, v in route.items() if k in ROUTE_KEYS}

        # No worker specified: fall back cleanly to the delegation config section
        # (without any stray service_tier key, matching DefaultDelegationProvider).
        return {k: v for k, v in config.items() if k != "service_tier"}
