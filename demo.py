#!/usr/bin/env python3
"""A stdlib-only theater: live local routes and a saved, modeled benchmark replay."""

import argparse
import json
import math
from pathlib import Path
import sys
import time
from types import ModuleType


ROOT = Path(__file__).resolve().parent
# Explicit response-length assumptions from bench/runner.py, not measured outputs.
MODELED_BRIEF_WORDS = {
    "TASK-01": 280,
    "TASK-02": 190,
    "TASK-03": 320,
    "TASK-04": 350,
    "TASK-05": 210,
}


class DemoDelegationProvider:
    """Minimal settings lookup for the standalone presentation only."""

    def settings(self, config):
        return config.get("backends", {}).get(self.name, {})


class DemoDelegationRouteError(ValueError):
    """Stable exception identity if the presentation is replayed in one process."""


def load_provider():
    """Use Hermes when installed; otherwise supply only the local demo contract."""
    try:
        from agent.delegation_provider import DelegationRouteError
    except ModuleNotFoundError as error:
        if error.name not in {"agent", "agent.delegation_provider"}:
            raise
    else:
        from provider import StagehandsProvider
        return StagehandsProvider(), DelegationRouteError, "real Hermes core"

    shim = ModuleType("agent.delegation_provider")
    shim.DelegationProvider = DemoDelegationProvider
    shim.DelegationRouteError = DemoDelegationRouteError
    shim.ROUTE_KEYS = frozenset({
        "model", "provider", "base_url", "api_key", "api_mode",
        "reasoning_effort", "service_tier", "request_overrides",
        "fallback_providers", "profile", "label",
    })
    parent_added = "agent" not in sys.modules
    if parent_added:
        parent = ModuleType("agent")
        parent.__path__ = []
        sys.modules["agent"] = parent
    sys.modules["agent.delegation_provider"] = shim
    try:
        from provider import StagehandsProvider
    finally:
        # Keep the shim local to loading the showcase, not future core imports.
        sys.modules.pop("agent.delegation_provider", None)
        if parent_added:
            sys.modules.pop("agent", None)
    return StagehandsProvider(), DemoDelegationRouteError, "standalone demo shim"


def bar(value, maximum, width=22):
    filled = round(width * value / maximum) if maximum else 0
    filled = max(1 if value > 0 else 0, min(width, filled))
    return "[" + "█" * filled + "░" * (width - filled) + "]"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    pacing = parser.add_mutually_exclusive_group()
    pacing.add_argument("--fast", action="store_true", help="Replay without pauses")
    pacing.add_argument("--step", action="store_true", help="Press Enter between workloads")
    parser.add_argument("--color", choices=("auto", "always", "never"), default="auto")
    args = parser.parse_args(argv)
    color = args.color == "always" or (args.color == "auto" and sys.stdout.isatty())

    def paint(text, code="36"):
        return f"\033[{code}m{text}\033[0m" if color else text

    def section(title):
        print("\n" + paint("─" * 88))
        print(paint(title, "1;36"))

    results = json.loads((ROOT / "bench/results.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "bench/fixtures/manifest.json").read_text(encoding="utf-8"))
    tasks = results["task_breakdown"]
    if [task["task_id"] for task in tasks] != list(MODELED_BRIEF_WORDS):
        raise ValueError("Expected saved benchmark workloads TASK-01 through TASK-05")

    print(paint("═" * 88, "1;35"))
    print(paint("SOVEREIGN & STAGEHANDS — Dual-Engine Delegation for Hermes Agent v0.22.5", "1;35"))
    print("Keep the Sovereign warm. Send the Stagehands into the log mines.")
    print(paint("═" * 88, "1;35"))
    print(f"Saved audit: {results['timestamp']} | {len(manifest['files'])} fixture manifest entries")
    print(f"Synthetic fixtures: {manifest['synthetic']} | Costs and brief lengths are modeled.")

    section("ACT I · LIVE ROUTE RESOLUTION")
    provider, route_error, core_mode = load_provider()
    print(f"Provider: {provider.name} | Contract: {core_mode}")
    for worker in provider.task_parameters({})["worker"]["enum"]:
        route = provider.route_task({"goal": "Return a concise evidence brief", "worker": worker}, {})
        print(paint(f"  ✓ {worker}", "32"))
        print("    " + json.dumps(route, ensure_ascii=False, sort_keys=True))
    try:
        provider.route_task({"goal": "Demonstrate fail-closed routing", "worker": "invalid_worker"}, {})
    except route_error as error:
        print(paint(f"  ✓ Fail-closed · DelegationRouteError: {error}", "33"))
    else:
        raise RuntimeError("Unknown worker unexpectedly accepted")

    section("ACT II · SIDE-BY-SIDE WORKLOAD REPLAY")
    rates = results["rates_card_usd_per_million"]["google/gemini-4-argon"]
    print(f"Pure Sovereign: google/gemini-4-argon @ ${rates['input']:g}/M input and output tokens")
    print("Stagehands cost = child processing + Sovereign reading the brief and replying.")
    print("Bars share a scale within each pair; brief tokens use runner response-length assumptions.")
    print("TASK-02 replay uses v4-flash; the current code_monkey route above uses v4.1-flash.")

    total_brief = 0
    for task in tasks:
        if args.step:
            input("\nPress Enter to raise the next curtain… ")
        elif not args.fast:
            time.sleep(0.05)
        pure = task["pure_sovereign"]
        stage = task["sovereign_and_stagehands"]
        delta = task["deltas"]
        raw = task["raw_context_tokens"]
        brief = math.ceil(MODELED_BRIEF_WORDS[task["task_id"]] * 1.33)
        total_brief += brief
        scale = max(raw, brief)
        print("\n" + paint(f"{task['task_id']} · {task['task_name']}", "1"))
        print(f"  Worker: {task['worker_role']} ({task['worker_model']})")
        print(f"  Fixture: {task['fixture']} · {task['raw_context_bytes']:,} bytes")
        print(f"  RAW   {bar(raw, scale)} {raw:>7,} tokens  │  BRIEF {bar(brief, scale)} {brief:>5,} tokens")
        pure_cost, stage_cost = pure["cost_usd"], stage["total_cost_usd"]
        print(f"  PURE  {bar(pure_cost, pure_cost)} ${pure_cost:.5f}       │  DUAL  {bar(stage_cost, pure_cost)} ${stage_cost:.5f}")
        print(paint(
            f"  Cost saved: {delta['cost_reduction_pct']:.1f}% ({delta['savings_ratio']})"
            f" · Parent context pollution prevented: {delta['memory_pollution_reduction_pct']:.1f}%",
            "32",
        ))
        print(f"  Parent context: {pure['parent_memory_tokens']:,} → {stage['parent_memory_tokens']:,} tokens (includes prompt and reply)")

    truth = manifest["ground_truth"]
    print("\nFixture ground truth: "
          f"{len(truth['log_incidents'])} log incidents, "
          f"{len(truth['code_findings'])} code findings, "
          f"{truth['transactions']['count']} settlement transactions.")

    section("CURTAIN CALL · FINAL SCORECARD")
    summary = results["summary"]
    print(paint(
        f"  {summary['aggregate_cost_savings_pct']:.1f}% cost reduction "
        f"(${summary['pure_sovereign_total_cost_usd']:.4f} → ${summary['stagehands_total_cost_usd']:.4f})"
        f" · {summary['aggregate_cost_ratio'].replace('cost reduction', 'cheaper')}", "1;32",
    ))
    print(paint(
        f"  {summary['aggregate_memory_pollution_reduction_pct']:.1f}% parent context memory savings "
        f"({summary['pure_sovereign_total_memory_tokens']:,} → "
        f"{summary['stagehands_total_memory_tokens']:,} tokens)", "1;32",
    ))
    print(f"  Raw payloads: {sum(task['raw_context_tokens'] for task in tasks):,} tokens; modeled briefs alone: {total_brief:,} tokens.")
    print("  The audited 95.9% compares total parent context (including prompt and reply overhead).")
    print("\n" + paint("The Sovereign keeps the conversation. The Stagehands carry the noise.", "1;35"))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (EOFError, KeyboardInterrupt):
        print("\nCurtain closed.")
        raise SystemExit(0)
