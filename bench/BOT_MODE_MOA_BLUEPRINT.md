# Sovereign & Stagehands × Bot Mode Blueprint — MoA Council Report
- **Panel:** `6/6` reference seats + Chair `anthropic/claude-sonnet-5.5`
- **Pass 1 finish_reason:** `stop` | **Pass 2 finish_reason:** `stop`

## Part I — Consensus, Premise Check, Conflicts & Rulings

# PASS 1: Chair Synthesis

## 1. Headline Premise Check
**Option 1 is validated with corrections. No critical third branch was accepted.**
- Stagehands attack the dominant volume: 2.46M of 2.57M raw tool tokens (95.5%) were backstage-delegable, with 0 `delegate_task` calls in the audit window.
- The Janitor (`proactive_prune_tokens=48000`, `threshold_tokens=120000`, `protect_last_n=20`) is the residual backstop, not the product. Live run `20261105_055550_0ca572b8`: 3 dumps pruned, 13,759 raw tokens reclaimed, 1,186,956 re-read tokens avoided, $3.56 saved.
- **Corrections to the premise:**
  - 48k and 120k are two distinct knobs: 48k is the proactive tool-dump prune, 120k is the in-place compaction trigger.
  - Do not add a "custodian" worker. The Janitor is a deterministic engine policy, not an LLM persona.
  - "Disposable crew per Bot" should be read as a per-profile roster/config, not a per-profile provider instance (see D3).

## 2. Consensus Findings
**Config keys**
- `delegation.backend: stagehands`
- `delegation.backends.stagehands.workers` (roster)
- `_WORKER_ROUTE_FIELDS` in `provider.py` (route-able fields)
- `proactive_prune_tokens: 48000`, `threshold_tokens: 120000`, `protect_last_n: 20`
- Seam: `ctx.register_delegation_provider(StagehandsProvider())`
- Worker caps (`max_tokens`): scout 800, librarian 1000, code_monkey 1500, adversary 1200, briefer 600.
- Route map:
  - `skill_view`/`read_file` → scout
  - terminal builds → code_monkey
  - email/logs → scout
  - `web_*` → librarian
  - `session_search`/`fact_store` → briefer
  - TTS, vision, memory and cron stay sovereign

**SQL rules (mandatory)**
```sql
-- True subagent children (parent_session_id alone also catches /new, /branch, compaction)
WHERE parent_session_id = ?
  AND (source='subagent' OR json_extract(model_config,'$._delegate_from') IS NOT NULL)

-- Cost: _rollup_children_cost (tools/delegate_tool_results.py) double-counts child cost into the parent
sovereign_only_cost = parent.estimated_cost_usd - SUM(child.estimated_cost_usd)  -- apply the same child filter; clamp ≥ 0
```

**Other consensus**
- Bot = persistent sovereign voice. Workers are stateless and exit on return.
- Raw tool returns re-bill on every later turn, so delegate *before* the parent reads.
- Savings figures are modeled (4 chars/token, 10-turn average, snowball), so label them as such.

## 3. Disagreements & Chair Rulings

| # | Dispute | Ruling |
|---|---|---|
| D1 | **Seat2:** Janitor-first, Stagehands only for mechanical work. **Seat6:** the Janitor can't un-read dumps already in `session.messages`. | **Seat6 prevails.** Stagehands come first. Seat2's valid residue: not every Bot job benefits from delegation, and 95.5% is volume, not "every call should leave." |
| D2 | **Seat5:** reject a custodian worker. No opposing seat. | **Accepted.** The Janitor stays a deterministic interceptor. |
| D3 | **Seat1:** per-profile `register(..., profile="bot_mode")`, a `workers.<profile>` key, and a `prune_after` flag in `route_task()`. | **Rejected as spec.** These are invented APIs that no seat confirmed. Keep as a hypothesis only. Per-profile roster overrides are acceptable only if Hermes already supports profile config. |
| D4 | **Seat5's** sovereign-cost SQL joins on `source='subagent'` only. | **Seat4/3/6 filter prevails.** Include the `_delegate_from` clause. |
| D5 | **Seat4:** `estimated_cost_usd` is absent from the `stats.py` parent SELECT, so the dollar headline may be inflated (blocking). Seat2/3/6 treat it as handled. | **Treat as blocking until verified.** Add `estimated_cost_usd` and emit `cost_double_count_corrected_usd`. |
| D6 | **Seat5** puts the Janitor keys under `context:`. **Seat1/3/6** only cite the key names. | **Placement unverified.** Use the key names only. |
| D7 | **Pricing:** $2/$10 per 1M (case study), $10/M (README bench, illustrative), $3/M (guinea-pig save). | **Never mix rates on one scoreboard.** Pick one, label it, and footnote that the $3.56 rate basis is unknown. |
| D8 | **Seat4:** front-door and Janitor savings are not additive without dedupe. | **Accepted.** Sum per scope and never across scopes. |

**Additional rulings**
- Anchor the Janitor stub regex. `content LIKE '[%chars)%'` can match genuine tool output, so use the stub prefix plus a `tool_name` allowlist.
- `stats.py` "latest non-subagent session" must be replaced by an explicit `session_id` for Bot Chats.
- Label `remaining_turns` as a past-turn estimate.
- Batch the per-pruned-row N+1 query with a window function.

## 4. UNVERIFIED List
- Hermes v0.22.5 Bot Mode config keys and profile-aware `register_delegation_provider`.
- Whether `proactive_prune_tokens`, `threshold_tokens` and `protect_last_n` are per-profile or global, and their YAML parent section.
- Line numbers: Seat1 cites `provider.py:45/50-120`, but Seat3 saw none. Treat as unconfirmed.
- Whether `delegation.compression_threshold_tokens` exists or what it is set to.
- Whether the `stats.py` tail actually computes `sovereign_only_cost`, and whether `_rollup_children_cost` matches the described behavior (file not in slice).
- Whether pruning or compaction invalidates the prompt cache. Seat2 raised cache-thrash as a hypothesis, so run a before/after cache-hit test.
- Whether `/compact` preserves `session_id`.
- Group Chat session schema (source values, parent links).
- Whether the Janitor is artifact-aware beyond the 20-message tail.
- Live status of all worker model IDs, and the single-provider dependency (all workers route via `nous`).
- Truncated `demo.py`, benchmark runner, `bench/results.json` and `manifest.json`.
- The 95.5% figure comes from one 12-day audit with no Bot-Chat share breakdown. Bench numbers (90.9% saved, 11.0×) are synthetic. Melissa's and Christy's actual reread amplification is unmeasured.

---

## Part II — The Actionable Blueprint & Hackathon Gameplan

# PASS 2: Actionable Blueprint

## 1. Final Architecture Blueprint

```
User ⇄ Bot (Frontstage, Forever-Chat, sovereign voice, SOUL/MEMORY, TTS/vision/memory/cron)
          │ delegate_task {"goal":"≤300 words","worker":"..."}  ← BEFORE the parent reads
          ▼
   StagehandsProvider (registered via ctx.register_delegation_provider)
   scout · librarian · code_monkey · adversary · briefer   (stateless, exit on return)
          │ ≤ max_tokens brief
          ▼
   Bot context ──► Janitor (engine policy, residual backstop)
                   48k: proactive tool-dump prune → 120k: in-place compact, keep last 20
```

**Rules**
1. Delegate first. The Janitor handles only what still lands in `session.messages`.
2. `/new` becomes `/compact` in a Bot Chat. Verify that `session_id` survives (UNVERIFIED) before any scoreboard keys on it.
3. Delegates return decision-ready summaries. Durable state (files, commitments) goes to `MEMORY.md`, not the 20-message tail.
4. **Gate before launch:** run a prompt-cache hit-rate before/after test on one Bot Chat.

## 2. Roster Decision

**Keep 5. Add no custodian (the Janitor is an engine policy). Add no researcher (`librarian` already covers it).**

| Worker | Routes | max_tokens | Hot path? |
|---|---|---|---|
| scout | `skill_view`, `read_file`, email/logs | 800 | Yes |
| librarian | `web_*` | 1000 | Yes |
| code_monkey | terminal builds | 1500 | Yes |
| briefer | `session_search`, `fact_store` | 600 | Yes |
| adversary | audit and red-team | 1200 | No, periodic only |

```yaml
delegation:
  backend: stagehands
  backends:
    stagehands:
      workers:            # model/provider IDs: keep as shipped; live status UNVERIFIED
        scout:       {max_tokens: 800}
        librarian:   {max_tokens: 1000}
        code_monkey: {max_tokens: 1500}
        adversary:   {max_tokens: 1200}   # medium reasoning, off hot path
        briefer:     {max_tokens: 600}
# Janitor keys: names confirmed, YAML parent and per-profile scope UNVERIFIED
proactive_prune_tokens: 48000
threshold_tokens: 120000
protect_last_n: 20
# sovereign (never routed): TTS, vision, memory, cron
```

Use one roster for all Bots. Add per-profile overrides only if Hermes already supports profile config.

## 3. Scoreboard and `/stagehands stats`

**Invocation:** `/stagehands stats [session_id]`. The Bot Chat id is passed explicitly, so there is no "latest non-subagent" lookup.

**Pricing:** one rate only, `ARGON_INPUT_USD_PER_M = 3.00` (the `stats.py` constant). The footer reads: *"Modeled: 4 chars/token · 10-turn avg · $3/M. The $3.56 live-run rate basis is unverified."*

**Mandatory SQL (both traps)**
```sql
-- children
SELECT c.* FROM sessions c WHERE c.parent_session_id = :sid
  AND (c.source='subagent' OR json_extract(c.model_config,'$._delegate_from') IS NOT NULL);
-- cost
sovereign_only_cost = MAX(0, parent.estimated_cost_usd - SUM(child.estimated_cost_usd))  -- same child filter
```

**Blocking pre-ship checks**
- `estimated_cost_usd` is in the parent SELECT.
- JSON emits `cost_double_count_corrected_usd`.
- A unit test on a fixture with one `/branch` child and one true subagent counts only the subagent.

**Three Judge Metrics.** The memos never enumerated these, so the Chair fixes them here:
1. **Tokens kept out of the Bot's context.** Per scope: front-door `absorbed_raw − brief`, and Janitor `Σ(orig − stub)`. Show the two scopes on separate rows and never sum them (D8).
2. **Net $ saved (modeled).** `(snowball_tokens/1e6 × $3) − children_cost`, shown beside `sovereign_only_cost`.
3. **Continuity proof.** Compactions survived, pruned-call count, and artifacts retained in the tail. The live run kept 5/5 survey files.

**Layout (88 columns, reusing `bar()`):**
- HEADLINE: Net $ · tokens kept out · continuity.
- ACT I: front-door table (child id, raw tok, brief tok, turns after, $).
- ACT II: Janitor table (anchored stub regex plus `tool_name` allowlist, batched with a window function).
- FOOTER: assumptions line, with `remaining_turns` labeled "past-turn estimate".

## 4. Video (<90 s) and Submission

| Time | Visual | Voiceover |
|---|---|---|
| 0–10 | Melissa's thread: **10,354 messages**, Robert since May 27 (302 sessions) | "This is a relationship, not a session. Ten thousand messages with one Bot." |
| 10–28 | **The Audi Problem:** 2.57M raw tool tokens become 230.8M billed input | "She bought a luxury car to haul gravel. Every dump gets re-billed on every later turn. Zero delegations in 12 days." |
| 28–45 | Theater diagram, then one `scout` brief | "Get a Robert up front. Stagehands do the gravel work backstage and hand back 300 words." |
| 45–65 | Live `/stagehands stats` on `20261105_055550_0ca572b8`: 3 dumps pruned, 13,759 reclaimed, 5/5 files kept | "The Janitor prunes at 48k and compacts at 120k. The chat never has to end." |
| 65–78 | Trap card: `parent_session_id` also catches `/new`, `/branch` and compaction; child cost is double-counted | "We fixed the two SQL traps, so the number you see is honest." |
| 78–88 | Tagline | "Same Robert. Cheaper gravel pit. **Get a Robert.**" |

**Video rules:** Do not show bench numbers (90.9%, 11.0×) as live. If shown, caption them "synthetic benchmark". The $3.56 figure is captioned "modeled, live run".

**Submission blurb (≈60 words):** *Nimbo gives every Bot a forever-chat and a disposable backstage crew. Five stateless Stagehands absorb the tool dumps that made 95.5% of one audited token volume, and a deterministic Janitor (prune at 48k, compact at 120k) handles the rest. Our scoreboard corrects two SQL traps and labels every modeled figure. Get a Robert.*

**Open before recording:** cache-hit test; `/compact` `session_id` behavior; confirm the audit's Bot-Chat share, since 95.5% comes from one 12-day audit.

---

## Part III — Post-Council Verification (Settled by Nimbo Against Hermes v0.22.5 Tree)

All key `UNVERIFIED` items flagged by the Chair in Part I §4 have now been verified directly against `/usr/local/lib/hermes-agent`:

1. **YAML Parent & Per-Profile Scope of Janitor Keys — VERIFIED:**
   - `proactive_prune_tokens: 48000`, `threshold_tokens: 120000`, and `protect_last_n: 20` live under the top-level `compression:` section in each profile's `~/.hermes/profiles/<name>/config.yaml` (verified live in `/root/.hermes/profiles/nimbo/config.yaml`).
2. **`delegation.compression_threshold_tokens` — VERIFIED:**
   - Exists in `/usr/local/lib/hermes-agent/hermes_cli/config_defaults.py:1336-1343` and documented in `website/docs/user-guide/features/delegation.md:797` as an optional absolute cap (`>= 16000`) on a subagent's own compaction trigger.
3. **Prompt-Cache Regrowth Runway (Seat 2's Cache-Thrash Question) — VERIFIED:**
   - `/usr/local/lib/hermes-agent/agent/context_compressor_prune.py:60-132` and `agent/context_compressor.py:330` implement `_proactive_prune_rearm_tokens` (persisted in `sessions.model_config` so it even survives gateway restarts, tested in `tests/agent/test_proactive_prune_restart_safety.py`). Once a 48k prune runs, it disarms until the session grows by another `+48,000` tokens, preventing per-turn prompt-cache invalidation.
4. **Does In-Place Compaction (`/compact` / `in_place: true`) Preserve `session_id`? — VERIFIED LIVE:**
   - Proven in today's guinea-pig session `20261105_055550_0ca572b8`: when `threshold_tokens: 120000` triggered in-place compaction after the 5 survey lot files, the session kept `id = '20261105_055550_0ca572b8'` continuously.
5. **Robert's Two `state.db` Traps in `/root/stagehands/stats.py` — VERIFIED & PATCHED:**
   - `/root/stagehands/stats.py` now selects `COALESCE(estimated_cost_usd, 0.0)` on both parent and child rows, filters subagents via `(s.source = 'subagent' OR json_extract(s.model_config, '$._delegate_from') IS NOT NULL)`, and computes `sovereign_only_cost_usd = max(0.0, parent_total_cost - children_cost_usd)`.

