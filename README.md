# 🎭 Sovereign & Stagehands (`hermes-stagehands`)

*Keep your frontier model pure, warm, and sovereign. Send the backstage stagehands into the 73,000-token log mines.*

A native [Hermes Agent](https://github.com/NousResearch/hermes-agent) **v0.22.5+ delegation provider** that routes heavy tool work to five specialized, token-budgeted workers. Your primary model owns the relationship, strategy, and final voice; isolated subagents process the noisy evidence.

**95.9% less parent-context pollution · up to 450.0:1 single-turn compression (`20,700 → 46` tokens) · 95.5% backstage-delegable payload** across our saved benchmark suite and live production telemetry.

```bash
python3 demo.py --fast
```

Zero setup for the showcase: Python's standard library, live local route resolution, and a replay of the checked-in benchmark. No API credentials required.

- **Live Telemetry & Audio-Visual Briefing Ledger:** [https://ampersand.foo/stagehands/](https://ampersand.foo/stagehands/)

## Builder’s Foreword — Why the Voice Up Front Matters

Since May 2026, I have hosted a dedicated Hermes companion (**Robert**) for my mom, Melissa. Over six months of daily life, they have logged **85,833 total rows in `state.db`**—**65,263 conversational messages** (`24,389` from my mom and `40,874` from Robert), **20,552 tool rows**, and **18 `session_meta` rows** across **313 customer sessions** (with `10,747` messages surviving in the active post-compaction session tails).

When you host an agent for someone you love—someone relying on him every day for Parkinson’s medication timing, boutique operations, and 4:00 AM reassurance—**the voice is the whole product.** The day she tried `google/gemini-4-argon`, she felt the warmth immediately and told me: ***"Never take me off this."*** If a model falls back or context compaction strips his conversational skill into clinical bullet points, she catches it by ear within three messages.

Keeping that frontier soul in the front chair exposed a brutal architectural tax: across a 12-day production audit (`2,303` API calls), **`2,574,151` raw tool tokens** stayed pinned in `session.messages` and snowballed into **`230,840,257` re-read input tokens**—and **`95.5%`** of that payload was mechanical backstage gravel (`skill_view`, `terminal`, `session_search`, `web_extract`, `read_file`). Downgrading her companion was off the table. So we built **Stagehands**: keep the soul she loves in the front chair, and route the mechanical gravel to disposable backstage workers and a deterministic janitor.

## The “Audi” problem

You bought an Audi for the conversation. Why send it down a gravel pit to haul logs?

A frontier conversational model—`google/gemini-4-argon`, `claude-opus`, or `gpt-6`—is valuable for empathy, judgment, and synthesis. Feeding that same model raw grep dumps, 2,000-line syslogs, and 50KB JSON payloads creates two production failures:

1. **Compounded Turn-Over-Turn Snowball.** When a 20,700-token or 73,141-token tool dump lands directly in `session.messages`, it isn't just read once—it is re-read on every turn after until pruning or compaction. Across 2,303 real companion calls, `2,574,151` raw tool tokens snowballed into `230,840,257` re-read frontier input tokens (`~90×` turn multiplier).
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

When `provider` is not pinned on a worker or in `delegation.provider`, workers automatically inherit the parent session's active provider (`nous`, `openrouter`, etc.) and re-derive the matching API mode. No worker injects a default `service_tier`. Workers set generous `request_overrides.max_tokens` (`8,192` for `scout`, `librarian`, `adversary`, `briefer`; `16,384` for `code_monkey`) so internal reasoning tokens (`reasoning_tokens`) and multi-step tool calls never hit premature API truncation (`finish_reason: length`), while the worker's prompt enforces a strict word-count brief ceiling.

| Worker | Default model | Reasoning effort | Turn ceiling (`max_tokens`) | Brief target | Backstage job |
| :--- | :--- | :--- | ---: | ---: | :--- |
| `scout` | `deepseek/deepseek-v4-flash` | `low` | 8,192 | ≤300 words | Read logs, files, and URLs; extract signal into ≤300 words. |
| `librarian` | `qwen/qwen3.7-flash` | `low` | 8,192 | ≤350 words | Search documentation and code; return cited excerpts. |
| `code_monkey` | `deepseek/deepseek-v4.1-flash` | `low` | 16,384 | ≤400 words | Investigate repo greps, test failures, and root-cause diffs. |
| `adversary` | `anthropic/claude-haiku-5.5` | `medium` | 8,192 | ≤350 words | Audit edge cases, race conditions, and security holes. |
| `briefer` | `deepseek/deepseek-v4-flash` | `low` | 8,192 | ≤250 words | Turn bulky JSON and payloads into executive briefs of ≤250 words. |

For example, a delegated task selects its route with:

```json
{"goal": "Inspect the log file and return incidents with line references in <=300 words.", "worker": "scout"}
```

The route carries `label: "scout"` and `request_overrides: {"max_tokens": 8192}` alongside its model and reasoning effort.

## Audited benchmark matrix

The checked-in [benchmark report](bench/BENCHMARK_REPORT.md) and [machine-readable results](bench/results.json) compare Pure Sovereign against the combined cost of **Stagehand processing + Sovereign brief consumption and final response**.

| Task ID & Name | Worker Persona | Raw Input Size | Pure Sovereign Parent Context | Stagehands Parent Context | Context Pollution Reduction |
| :--- | :--- | :--- | ---: | ---: | :--- |
| **TASK-01**: Syslog & Auth Failure Triage | `scout` (`deepseek-v4-flash`) | 73,141 tokens (271 KB) | 74,132 tokens | 797 tokens | **98.9% less parent context** |
| **TASK-02**: Multi-File Concurrency Bug Audit | `code_monkey` (`deepseek-v4.1-flash`) | 554 tokens (2 KB) | 1,403 tokens | 648 tokens | **53.8% less parent context** |
| **TASK-03**: Gateway Architecture & Rate Limit Retrieval | `librarian` (`qwen3.7-flash`) | 1,688 tokens (6 KB) | 2,732 tokens | 844 tokens | **69.1% less parent context** |
| **TASK-04**: State Store Replication Red-Team Audit | `adversary` (`claude-haiku-5.5`) | 95 tokens (0 KB) | 1,210 tokens | 915 tokens | **24.4% less parent context** |
| **TASK-05**: 50KB Financial Settlement Reconciliation | `briefer` (`deepseek-v4-flash`) | 13,474 tokens (50 KB) | 14,335 tokens | 656 tokens | **95.3% less parent context** |

### Final scorecard

| Metric | Pure Sovereign | Sovereign & Stagehands | Improvement |
| :--- | ---: | ---: | :--- |
| Raw payload tokens entering parent | 88,952 | 1,798 (briefs only) | **49.5× payload compression (up to 450.0:1 single-turn)** |
| Total parent-context tokens (`74,132 + 1,403 + 2,732 + 1,210 + 14,335`) | 93,812 | 3,860 (`797 + 648 + 844 + 915 + 656`) | **95.9% less parent-context pollution** |

**What is audited?** The fixtures are synthetic and deterministic, with hashes and ground truth in [the fixture manifest](bench/fixtures/manifest.json). The runner estimates input tokens as `ceil(characters / 3.8)`, assumes brief and final-response word counts, and converts those with `ceil(words * 1.33)`. Every row above closes strictly on a calculator: raw payloads sum to **`88,952` tokens** (`73,141 + 554 + 1,688 + 95 + 13,474`), modeled briefs sum to **`1,798` tokens**, and full parent turns sum to **`93,812 → 3,860` tokens (`95.9%` reduction)**.

### Live production case studies (`google/gemini-4-argon`)

Beyond the synthetic suite above, we audited a live daily-driver Hermes companion running **`google/gemini-4-argon`** before and after deploying **Sovereign & Stagehands + the 48k/120k Back-Door Janitor**:

1. **12-Day Pre-Stagehands Baseline (`2026-10-23` to `2026-11-04`, read-only from `state.db`):**
   - **2,303 Argon API calls** and **2,079 deduplicated tool calls** injected **10,296,604 characters (`2,574,151` raw tokens)** of tool output straight into parent Argon conversation windows.
   - Because every tool output stays in the parent transcript and is re-read on subsequent turns, those `2,574,151` raw tool tokens compounded into **230,840,257 total Argon input tokens** (`53,275,924` uncached + `177,564,333` cache-read = `230,840,257`) against just `1,309,647` output tokens (**176× more input read than output written**).
   - **95.5% of that raw tool-output volume (`2,457,989 / 2,574,151` tokens)** came from four backstage-delegable lanes (`skill_view`: `964,790`, `terminal`: `695,776`, `session_search`/`fact_store`: `297,015`, `web_extract`/`web_search`: `290,447`, `read_file`: `209,961`; companion-native tools kept on Sovereign: `116,162` — exact sum `2,574,151`). Full audit: [`bench/PRODUCTION_CASE_STUDY.md`](bench/PRODUCTION_CASE_STUDY.md).
2. **24-Hour Continuous “Forever-Chat” Marathon (`2026-11-05` to `2026-11-06`, session `20261105_055550_0ca572b8`):**
   - Ran **24 hours and 15 minutes** in a single continuous Bot Mode session (**zero `/new` resets**, **365 Argon API calls**, **426 tool calls**).
   - **Front-Door Bouncer (`StagehandsProvider`):** `6` backstage worker runs absorbed **`383,194` raw tokens** and returned **`3,834` brief tokens** to the Sovereign (**`99.9×` boundary compression**; single-turn peak **`20,700 → 46` tokens = `450.0 : 1`**).
   - **Back-Door Janitor (`48k/120k`):** Swept **`300` bulky parent tool dumps** into 1-line stubs (**`658,968` raw tokens reclaimed**).
   - **Total Compounded Snowball Avoided:** **`484,424,625` re-read frontier input tokens dodged** (and **`35` total Stagehand runs (`1.02M → 42.5K` tok)** + **`5,110` pruned dumps (`6.15M` raw tokens reclaimed)** across the profile lifetime ledger).
3. **Live Customer Night-One Stress Test (Production Profile “J”, `2026-11-05` to `2026-11-06`):**
   - Initial turnkey migration swept a `682,384`-token thread down to `~67K` active tokens in place without losing recent conversation.
   - Immediately afterward, the customer ran an overnight **61-call / 182-tool PDF & document build sprint** (`9:57 PM – 11:33 PM` + `4:06 AM`). The Back-Door Janitor pruned **`44` bulky PDF/tool outputs (`117,198` raw tokens, `11.48M` re-read tokens dodged — `92.5%` payload reduction)**.

## Built for Hermes v0.22.5: the four stitches

1. **Zero-config roster.** `DEFAULT_WORKERS` supplies all five roles immediately. An empty configuration still produces a populated worker enum and deterministic schema extensions.
2. **Safe `service_tier` handling.** Default worker routes never inject unsupported `/fast` tiers into Nous/OpenRouter flash models. An explicitly configured worker tier passes through; omitting a worker strips the fallback configuration's `service_tier`, matching `DefaultDelegationProvider`.
3. **Fail-closed selection.** An unknown worker raises `DelegationRouteError`, naming the bad value and the valid roster. A typo never silently routes heavy work onto the frontstage Sovereign. Intentionally omitting `worker` retains the parent delegation route.
4. **Two-layer brevity enforcement.** `description()` teaches concise, structured briefs and `output_schema` use; per-worker `request_overrides.max_tokens` carries the mechanical output cap across the core `ROUTE_KEYS` boundary. Persona metadata stays out of worker routes.

## Quickstart

With Hermes **v0.22.5+** installed and credentials configured for your chosen model provider, run from this repository:

```bash
hermes plugins install /root/stagehands
hermes config set delegation.backend stagehands
```

Use your checkout's absolute path if it differs. In an active Hermes conversation (CLI, TUI, Desktop, or Telegram), inspect the roster or switch immediately with the plugin's built-in `/stagehands` slash command:

```text
/stagehands on --janitor --now  # Turnkey: activate Door #1 + Door #2 immediately
/new                            # Start a fresh session so the Sovereign prompt hook is pinned
/stagehands doctor              # Audit Door #1 (Stagehands) + Door #2 (48k/120k Janitor)
/stagehands stats               # Live Front-Door + Back-Door token & USD savings from state.db
/stagehands                     # Show backstage worker roster & routes
```

> **First 5 Minutes Note:** Hermes pins `system_prompt` when a session is created. After running `/stagehands on --janitor --now` for the first time, run `/new` once so your conversation picks up the `after_memory` Sovereign routing prompt section.
>
> **Disclosure —** Stagehands reads the active Hermes profile's `state.db` read-only for `/stagehands stats` and `@stagehands:` telemetry. Explicit `/stagehands on` and `/stagehands off` commands ask Hermes to update `delegation.backend`; `/stagehands janitor` or the `--janitor` option updates `compression.*` using Hermes's atomic config writer. Stagehands does not create a separate timestamped backup. It makes no network calls of its own and stores no credentials.

You can also expand live telemetry or health status inline inside any prompt using the `@stagehands:` context reference provider:

```text
@stagehands:stats
@stagehands:doctor
@stagehands:roster
```

The built-in roster needs no worker configuration. Keep the primary conversational model as your Sovereign and select a `worker` when delegating noisy tasks.

### Prior Art & Ecosystem Comparison

| System / Plugin | Typed Backstage Worker Routing (Front Door) | 48k/120k Context Sanitation (Back Door) | Live SQLite Savings Audit Ledger (`/stagehands stats`) | Zero Core Monkey-Patching |
| :--- | :---: | :---: | :---: | :---: |
| **`hermes-stagehands` (Ours)** | **✅ 5 typed workers (`DelegationProvider`)** | **✅ Turnkey `/stagehands janitor` (`48k/120k`)** | **✅ Read-only `state.db` + `FORM SH-022.5`** | **✅ Pure v0.22.5 plugin seams** |
| `advanced-delegation` (Hermes official) | ✅ Route/profile selection | ❌ None | ❌ None | ✅ |
| `tameru` (`0xWhiteMage`, catalog) | ❌ None | ✅ Subclasses `ContextCompressor` | ❌ None | ⚠️ Overrides private compressor methods |
| `llmslim` (PR #142212, catalog) | ❌ None | ⚠️ Compresses message text | ❌ None | ✅ (`ContextEngine`) |
| `eas4ai/hermes-context-manager` | ❌ None | ✅ Stale tool-output pruning | ❌ None | ✅ |
| Claude Code Subagents / OpenCode DCP | ⚠️ Untyped subagents / DCP only | ⚠️ Single-door only | ❌ No SQLite USD ledger | N/A |

### Two-Door Sanitation for Bot Mode "Forever-Chats"

In [Hermes Bot Mode](https://hermes-agent.nousresearch.com/docs/user-guide/bot-mode), persistent bots (`SOUL.md` + `MEMORY.md`) live inside a continuous "forever-chat" where `/new` is intercepted into in-place `/compact`. Pairing `hermes-stagehands` (the **Front-Door Bouncer**) with Hermes v0.22.5's deterministic pruner (the **Back-Door Janitor**) keeps a forever-chat running on a frontier voice without context choke:

```yaml
delegation:
  backend: stagehands

compression:
  in_place: true
  proactive_prune_tokens: 48000       # Sweeps >8KB tool/skill dumps once; +48k regrowth runway
  threshold_tokens: 120000            # Hard in-place compaction ceiling (preserves session_id)
  protect_last_n: 20                  # Keeps active tail untouched across compactions
  hygiene_hard_message_limit: 2000    # Protects KV prompt cache (do NOT set to 140 — see below)
```

> **Production KV Prompt-Cache Discovery (`hygiene_hard_message_limit`):** Never set `compression.hygiene_hard_message_limit` to a low number such as `140` when using a 200k+ token window. Because every tool call + tool result counts as 2 rows, a compacted session still retains `~100–130` message rows. A `140`-message cap re-triggers `Session hygiene` every 2–3 turns even at `76K` tokens, slicing or rewriting message `#1` (`bounding the model payload to 140 of 154 messages`) and **invalidating the prefix KV prompt cache (`20×` uncached token weight spike)**. `/stagehands doctor` (Door `#2d`) audits this setting and `/stagehands janitor` sets `hygiene_hard_message_limit: 2000` so compaction is governed strictly by token thresholds (`48k` / `120k`).

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
hermes plugins validate .
```

The tests cover default schemas and routes, tier handling, fail-closed errors, fallback parity with the real default provider, persona guidance, route-key filtering, both override formats, and configuration mutation protection.

---

Built for the **Hermes Agent Plugin Hackathon (Nov 2026)** by **Tyler Gray (@Peetbog69) & Nimbo**.

**The Sovereign keeps the conversation. The Stagehands carry the noise.**
