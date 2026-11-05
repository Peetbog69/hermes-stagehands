# 🎭 Sovereign & Stagehands (`hermes-stagehands`)

*Keep your frontier model pure, warm, and sovereign. Send the backstage stagehands into the 73,000-token log mines.*

A native [Hermes Agent](https://github.com/NousResearch/hermes-agent) **v0.22.5+ delegation provider** that routes heavy tool work to five specialized, token-budgeted workers. Your primary model owns the relationship, strategy, and final voice; isolated subagents process the noisy evidence.

**90.9% modeled cost reduction · 11.0x cheaper · 95.9% less parent-context pollution** across the five saved benchmark workloads.

```bash
python3 demo.py --fast
```

Zero setup for the showcase: Python's standard library, live local route resolution, and a replay of the checked-in benchmark. No API credentials required.

## The “Audi” problem

You bought an Audi for the conversation. Why send it down a gravel pit to haul logs?

A frontier conversational model—`google/gemini-4-argon`, `claude-opus`, or `gpt-6`—is valuable for empathy, judgment, and synthesis. Feeding that same model raw grep dumps, 2,000-line syslogs, and 50KB JSON payloads creates two production failures:

1. **$15+/day token burn.** At the benchmark's illustrative **$10/M input and output tokens** for `google/gemini-4-argon`, a 35,000-token input alone costs $0.35. Repeated heavy turns can push a day's spend past $15. The benchmark's 73,141-token syslog task costs $0.7413 on the Pure Sovereign path.
2. **Context Choke.** When 35k+ raw tool tokens are permanently pinned in `session.messages` until pruning or compaction, subsequent turns carry the baggage. Useful conversational context gets crowded out, persona warmth suffers, and latency rises.

The fix: delegate **before** reading the raw payload into the parent. Give the worker a file path or investigation goal, then return a concise evidence brief. A routing plugin cannot retroactively remove logs the parent already ingested.

## The theater architecture

```text
                         Human conversation
                                 ^
                                 |
              +------------------v------------------+
              |      FRONT-OF-HOUSE SOVEREIGN        |
              | Persona / Empathy / Strategy        |
              | Final Voice / Warm conversation     |
              +------------------+------------------+
                                 ^
                  task + worker  |  compact brief
                                 v
              +-------------------------------------+
              | Native Hermes v0.22.5 seam           |
              | DelegationProvider                  |
              | ctx.register_delegation_provider    |
              |   (StagehandsProvider())            |
              +------------------+------------------+
                                 ^
                                 v
       +-----------------------------------------------------+
       |                 BACKSTAGE STAGEHANDS                |
       | scout / librarian / code_monkey / adversary / briefer|
       |                                                     |
       | Isolated child context windows                      |
       | Raw logs / grep / code / documents / JSON            |
       | Mechanical request_overrides.max_tokens caps        |
       +-----------------------------------------------------+
```

Hermes supplies subagent isolation and dispatch. Stagehands supplies the typed `worker` parameter, persona guidance, model routes, and output budgets through the native plugin seam. The Sovereign gets the brief and speaks to the human.

## Meet the five workers

All defaults use provider **`nous`**. No worker injects a default `service_tier`.

| Worker | Default model | Reasoning effort | `max_tokens` cap | Backstage job |
| :--- | :--- | :--- | ---: | :--- |
| `scout` | `deepseek/deepseek-v4-flash` | `low` | 800 | Read logs, files, and URLs; extract signal into ≤300 words. |
| `librarian` | `qwen/qwen3.7-flash` | `low` | 1,000 | Search documentation and code; return cited excerpts. |
| `code_monkey` | `deepseek/deepseek-v4.1-flash` | `low` | 1,500 | Investigate repo greps, test failures, and root-cause diffs. |
| `adversary` | `anthropic/claude-haiku-5.5` | `medium` | 1,200 | Audit edge cases, race conditions, and security holes. |
| `briefer` | `deepseek/deepseek-v4-flash` | `low` | 600 | Turn bulky JSON and payloads into executive briefs of ≤250 words. |

For example, a delegated task selects its route with:

```json
{"goal": "Inspect the log file and return incidents with line references in <=300 words.", "worker": "scout"}
```

The route carries `label: "scout"` and `request_overrides: {"max_tokens": 800}` alongside its model, provider, and reasoning effort.

## Audited benchmark matrix

The checked-in [benchmark report](bench/BENCHMARK_REPORT.md) and [machine-readable results](bench/results.json) compare Pure Sovereign against the combined cost of **Stagehand processing + Sovereign brief consumption and final response**.

| Task ID & Name | Worker Persona | Raw Input Size | Pure Sovereign Cost | Stagehands Cost | Cost Reduction | Memory Savings |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TASK-01**: Syslog & Auth Failure Triage | `scout` (deepseek-v4-flash) | 73,141 tokens (271 KB) | $0.7413 | $0.0448 | **94.0%** (16.5x cheaper) | **98.9%** |
| **TASK-02**: Multi-File Concurrency Bug Audit | `code_monkey` (deepseek-v4-flash) | 554 tokens (2 KB) | $0.0140 | $0.0070 | **49.7%** (2.0x cheaper) | **53.8%** |
| **TASK-03**: Gateway Architecture & Rate Limit Retrieval | `librarian` (qwen3.7-flash) | 1,688 tokens (6 KB) | $0.0273 | $0.0095 | **65.5%** (2.9x cheaper) | **69.1%** |
| **TASK-04**: State Store Replication Red-Team Audit | `adversary` (claude-haiku-5.5) | 95 tokens (0 KB) | $0.0121 | $0.0100 | **16.9%** (1.2x cheaper) | **24.4%** |
| **TASK-05**: 50KB Financial Settlement Reconciliation | `briefer` (deepseek-v4-flash) | 13,474 tokens (50 KB) | $0.1434 | $0.0137 | **90.4%** (10.5x cheaper) | **95.3%** |

### Final scorecard

| Metric | Pure Sovereign | Sovereign & Stagehands | Improvement |
| :--- | ---: | ---: | :--- |
| Total modeled spend | $0.9381 | $0.0851 | **90.9% less · 11.0x cheaper** |
| Total parent-context tokens | 93,812 | 3,860 | **95.9% less context pollution** |

**What is audited?** The fixtures are synthetic and deterministic, with hashes and ground truth in [the fixture manifest](bench/fixtures/manifest.json). The runner estimates input tokens as `ceil(characters / 3.8)`, assumes brief and final-response word counts, converts those with `ceil(words * 1.33)`, and applies its fixed rate card. These are reproducible cost/context calculations, not live model calls, measured invoices, latency measurements, or a scored accuracy evaluation. The headline is workload-weighted: the large syslog dominates the savings.

**Token accounting matters.** Raw payloads sum to **88,952 tokens**. Modeled briefs alone sum to **1,798 tokens**. The audited **93,812 → 3,860** parent-context comparison includes the full parent turn (system/user prompt overhead plus the final synthesized reply).

**Route version matters, too.** TASK-02's saved benchmark uses `deepseek/deepseek-v4-flash`; the current `code_monkey` default is `deepseek/deepseek-v4.1-flash`. The demo shows the current route live and preserves the historical replay's model and costs.

### Live production case study (12 days on `google/gemini-4-argon`)

Beyond the synthetic suite above, we audited a live daily-driver Hermes v0.22.5 companion running **`google/gemini-4-argon`** over a 12-day production window (**2026-10-23 to 2026-11-04**, read-only from `state.db`):

- **2,303 Argon API calls** and **2,079 deduplicated tool calls** injected **10,296,604 characters (`~2,574,151` raw tokens)** of tool output straight into the parent Argon conversation windows.
- Because every tool output stays in the parent transcript and is re-read on subsequent turns, those `2.57M` raw tool tokens compounded into **230,840,257 total Argon input tokens** (`53.28M` uncached + `177.56M` cache-read) against just `1.31M` output tokens (**176× more input read than output written**).
- **95.5% of that raw tool-output volume (`2.46M / 2.57M` tokens)** came from four backstage-delegable lanes (`terminal` doc builds & CLI email, `web_extract`/`web_search`/`read_file`, `session_search`/`fact_store` hydrations, and procedural `skill_view` loads). Full audit: [`bench/PRODUCTION_CASE_STUDY.md`](bench/PRODUCTION_CASE_STUDY.md).

## Built for Hermes v0.22.5: the four stitches

1. **Zero-config roster.** `DEFAULT_WORKERS` supplies all five roles immediately. An empty configuration still produces a populated worker enum and deterministic schema extensions.
2. **Safe `service_tier` handling.** Default worker routes never inject unsupported `/fast` tiers into Nous/OpenRouter flash models. An explicitly configured worker tier passes through; omitting a worker strips the fallback configuration's `service_tier`, matching `DefaultDelegationProvider`.
3. **Fail-closed selection.** An unknown worker raises `DelegationRouteError`, naming the bad value and the valid roster. A typo never silently routes heavy work onto the $10/M Sovereign. Intentionally omitting `worker` retains the parent delegation route.
4. **Two-layer brevity enforcement.** `description()` teaches concise, structured briefs and `output_schema` use; per-worker `request_overrides.max_tokens` carries the mechanical output cap across the core `ROUTE_KEYS` boundary. Persona metadata stays out of worker routes.

## Quickstart

With Hermes **v0.22.5+** installed and credentials configured for your chosen model provider, run from this repository:

```bash
hermes plugins install /root/stagehands
hermes config set delegation.backend stagehands
```

Use your checkout's absolute path if it differs. In an active Hermes conversation (CLI, TUI, Desktop, or Telegram), inspect the roster or switch immediately with the plugin's built-in `/stagehands` slash command:

```text
/stagehands
/stagehands --now
/stagehands stats
```

The built-in roster needs no worker configuration. Keep the primary conversational model as your Sovereign and select a `worker` when delegating noisy tasks.

### Two-Door Sanitation for Bot Mode "Forever-Chats"

In [Hermes Bot Mode](https://hermes-agent.nousresearch.com/docs/user-guide/bot-mode), persistent bots (`SOUL.md` + `MEMORY.md`) live inside a continuous "forever-chat" where `/new` is intercepted into in-place `/compact`. Pairing `hermes-stagehands` (the **Front-Door Bouncer**) with Hermes v0.22.5's deterministic pruner (the **Back-Door Janitor**) keeps a forever-chat running on a frontier voice without context choke:

```yaml
delegation:
  backend: stagehands

compression:
  in_place: true
  proactive_prune_tokens: 48000   # Sweeps >8KB tool/skill dumps once; +48k regrowth runway
  threshold_tokens: 120000        # Hard in-place compaction ceiling (preserves session_id)
  protect_last_n: 20              # Keeps active tail untouched across compactions
```

Use `/stagehands stats` (or `python3 stats.py --save bench/live_stats.json`) to inspect both rows directly from `state.db` and open the Government Paperwork Brutalist audit ledger at `bench/scoreboard.html`.

### Optional `config.yaml` overrides

A **mapping merges** named overrides onto the five-worker roster. Unspecified fields retain their defaults:

```yaml
delegation:
  backend: stagehands
  backends:
    stagehands:
      workers:
        scout:
          model: deepseek/deepseek-v4-flash
          provider: openrouter
          request_overrides:
            max_tokens: 500
```

A **nonempty list selects an explicit roster**, inheriting built-in fields for matching names:

```yaml
delegation:
  backend: stagehands
  backends:
    stagehands:
      workers:
        - name: scout
          model: custom/m
```

That list exposes only `scout`; the mapping form retains the other four workers. Overrides are shallow: supplying `request_overrides` replaces that worker's entire override mapping. Configure `service_tier: fast` only when the selected model/provider supports it.

## Run the theater

```bash
python3 demo.py
python3 demo.py --fast
python3 demo.py --step
python3 demo.py --fast --color always
```

The default replay takes only tiny 0.05-second beats; `--fast` removes pauses and `--step` lets a presenter advance each workload. ANSI colors activate in a terminal, with `--color always` for recordings or `--color never` for plain output.

The demo resolves all five routes through `StagehandsProvider`, catches an invalid-worker error, and replays TASK-01 through TASK-05 with raw/brief and cost comparison bars. If Hermes is unavailable, a narrowly scoped compatibility shim supplies the base class and route-key contract; the screen labels this mode explicitly. Real-core integration is covered separately by the test suite.

### Reproduce and verify

```bash
# Recalculate the modeled benchmark (rewrites results.json and BENCHMARK_REPORT.md).
python3 bench/runner.py

# Run contract tests against the real Hermes v0.22.5 core (stdlib unittest, zero extra deps).
python3 -m unittest discover -s tests -v

# Validate the plugin with Hermes' guard.
hermes plugins validate /root/stagehands
```

The tests cover default schemas and routes, tier handling, fail-closed errors, fallback parity with the real default provider, persona guidance, route-key filtering, both override formats, and configuration mutation protection.

---

Built for the **Hermes Agent Plugin Hackathon (Nov 2026)** by **Tyler Gray (@Peetborg) & Nimbo**.

**The Sovereign keeps the conversation. The Stagehands carry the noise.**
