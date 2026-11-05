# Spec: Government Paperwork Brutalist Scoreboard + SQL Trap Unit Tests

## 1. Surface Archetype (Claude Design)
- **Primary Surface:** **Monitor / Audit Ledger** (NOT a marketing landing page — no centered SaaS hero, no 3-card icon feature grid, no purple/indigo tech gradients, no glassmorphism).
- **Aesthetic:** **Government Paperwork / County Surveyor & Federal Token Auditor Brutalism (`FORM SH-022.5 // DEPT. OF CONTEXT SANITATION & BACKSTAGE LABOR`)**.
  - Default theme (`data-theme="manila"`): Aged archival manila/newsprint bond (`#F3EFE6`), stark carbon-black ink (`#111111`), secondary ruled cell fill (`#EAE4D6`), crisp `2px solid #111111` outer frames and `1px solid #111111` internal accounting table rules, zero border-radius (`0px`), hard offset drop shadows (`4px 4px 0 #111111`), punched binder-hole markers or perforation ticks along the top edge, and angled (`-2.5deg`) **Crimson Audit Rubber Stamps** (`#B81D13`, double border, uppercase tracked monospace).
  - Secondary toggleable theme (`data-theme="microfiche"` via an unobtrusive top-right `[MODE: MANILA BOND ⇄ CARBON MICROFICHE]` button): High-contrast phosphor/blueprint terminal (`#0D1117` background, `#E6EDF3` ink, `#FFB000` amber stamps) for dark-room video recording.
- **Self-Contained Requirement (CRITICAL):**
  - `grep -oE 'https?://' /root/stagehands/bench/scoreboard.html | wc -l` MUST BE **0** (no external Google Fonts, no CDN scripts, no external links with `http://` or `https://` — display repo/doc paths as plain monospace strings like `github.com/Peetbog69/hermes-stagehands`).
  - Use clean system monospace/grotesque stacks (`'IBM Plex Mono', 'JetBrains Mono', 'SFMono-Regular', Consolas, monospace` and `'Arial Narrow', 'Helvetica Neue', Impact, sans-serif`).

## 2. Deliverable 1: `/root/stagehands/bench/scoreboard.html`
Write a complete, self-contained HTML file at `/root/stagehands/bench/scoreboard.html` containing 5 `<section>` blocks formatted as official numbered sections of **FORM SH-022.5 (REV. 2026-11-05)**:

1. **`<section id="sec-header">` — FORM HEADER & OFFICIAL FILING METADATA:**
   - Form Box `FORM SH-022.5`, Agency Header `AMPERSAND FLEET OPERATIONS // DEPT. OF CONTEXT SANITATION & BACKSTAGE LABOR`, Document Title `PUBLIC TOKEN AUDIT & CONTINUITY LEDGER — SOVEREIGN & STAGEHANDS (HERMES v0.22.5)`, Filing Date `2026-11-05`, Inspector `R. FLEET / NIMBO-01`, Status Stamp `[APPROVED FOR FRONTSTAGE DEPLOYMENT]`.
   - Interactive top bar with:
     - `[PAPER STOCK: MANILA BOND ⇄ CARBON MICROFICHE]` theme switch
     - `[LOAD LIVE_STATS.JSON]` file picker / paste modal + live recalculator so any exported `live_stats.json` updates Exhibit D dynamically.

2. **`<section id="sec-exhibit-a">` — EXHIBIT A: CITIZEN CONTINUITY RECORD (CASE NO. ROB-2026-0527):**
   - Subject: **Melissa M. & Companion Profile `robert` (`vultr-1`, Active Since `2026-05-27 09:45:56`)**.
   - Verified SQLite Ledger Boxes:
     - `302` Real Customer Sessions (`WHERE source != 'subagent'`)
     - `10,354` Real Messages Exchanged
     - `3,302` Tool Invocations Executed
     - `0` Personality Downgrades Permitted (*"Keep the frontstage soul on Gemini-4-Argon. Move the gravel backstage."*)

3. **`<section id="sec-exhibit-b">` — EXHIBIT B: THE "AUDI HAULING GRAVEL" INDICTMENT (12-DAY PRODUCTION AUDIT):**
   - Accounting ledger table + ruled horizontal bar chart comparing **Raw Tool Output vs. Compounded Frontier Re-Reads** across `13` sessions (`2,303` API calls):
     - Raw Tool Tokens Ingested: `2,571,941` tokens (~1 turn cost)
     - Compounded Argon Input Billed: `230,842,110` tokens (~90x turn-over-turn snowball multiplier!)
     - Share of Tool Payload Backstage-Delegable: **`95.5%`** (Stamp: `[INDICTMENT: 95.5% MECHANICAL GRAVEL]`)
   - Itemized breakdown rows with CSS bar gauges:
     - `terminal` (SSH/CLI/build logs): `38.2%` of raw payload → Routed to `code_monkey` / `scout`
     - `web_extract` / `web_search`: `24.6%` of raw payload → Routed to `librarian`
     - `read_file` / `search_files`: `19.4%` of raw payload → Routed to `scout` / `code_monkey`
     - `skill_view` / `session_search`: `13.3%` of raw payload → Routed to `briefer` + `48k Janitor`
     - Direct User-Facing Action (`tts`, `vision`, `memory`): `4.5%` → Kept on Sovereign (`gemini-4-argon`)

4. **`<section id="sec-exhibit-c">` — EXHIBIT C: TWO-DOOR SANITATION SCHEMATIC (BOT MODE × STAGEHANDS × 48K JANITOR):**
   - Clean technical-manual SVG/CSS wiring diagram + specification table showing:
     - **FRONT DOOR (`delegation.backend: stagehands`):** 5 stateless, fail-closed workers (`scout` @ 800 tok, `librarian` @ 1000 tok, `code_monkey` @ 1500 tok, `briefer` @ 600 tok, `adversary` @ 1200 tok) on `$0.15/M` flash models — raw tool dumps die with the ephemeral subagent; only the bounded brief enters the Bot Mode forever-chat.
     - **BACK DOOR (Deterministic Engine Policy under `compression:`):** `proactive_prune_tokens: 48000` (with `_proactive_prune_rearm_tokens` `+48k` prompt-cache runway), `threshold_tokens: 120000` (`in_place: true`, preserves `session_id`), and `protect_last_n: 20`.

5. **`<section id="sec-exhibit-d">` — EXHIBIT D: LIVE GUINEA-PIG TELEMETRY RECEIPT (`SESSION 20261105_055550_0ca572b8`):**
   - Pre-populated with today's verified numbers from `/root/stagehands/bench/live_stats.json` AND separarated into two distinct accounting rows (per MoA Council Ruling `D5` — no double-counting):
     - **Row 1 — Front-Door Interceptor (`Stagehands` Subagents):** Subagent runs, Backstage raw tokens absorbed, Returned brief tokens, Compression Ratio (`38.4x` reference / live session ratio), Children Cost USD vs. Sovereign-Only Cost USD.
     - **Row 2 — Back-Door Context Janitor (`48k Pruner + 120k In-Place Compactor`):** `3` bulky tool dumps pruned (`13,759` raw tokens reclaimed), `69` older messages compacted in-place at `120k`, **`1,186,956` re-read tokens dodged**, **`$3.56` saved in this single session** at `$3.00/M` Argon input!
   - **Field Continuity Certification Box (`CASE NO. JOCO-SURVEY-168`):**
     - Stamp: `[CONTINUITY PASSED: 5/5 SURVEY LOTS RETAINED]`
     - Notes: `168` PNEZD stakeout points across Lots `13, 22, 23, 34, 35` remained 100% intact inside `protect_last_n: 20` while `69` older turns were compacted in-place without changing `session_id`.
   - **SQLite Audit Integrity Certifications (Robert's Two Traps):**
     - `[TRAP A CLEARED]` Subagent filter enforces `source = 'subagent' OR json_extract(model_config, '$._delegate_from') IS NOT NULL` (excludes `/new` and `/branch` lineage rows).
     - `[TRAP B CLEARED]` Sovereign cost subtracts `SUM(child.estimated_cost_usd)` rolled up by `delegate_tool_results.py`.

## 3. Deliverable 2: Add SQL Trap Regression Test to `/root/stagehands/tests/test_stagehands.py`
- Add a test method `test_stats_excludes_branch_sessions_and_subtracts_child_cost` that constructs a temporary SQLite `state.db` containing:
  1. A parent session (`id='sess_parent'`, `source='telegram'`, `estimated_cost_usd=1.25`, `api_call_count=20`)
  2. A `/branch` child session (`id='sess_branch'`, `parent_session_id='sess_parent'`, `source='telegram'`, `model_config='{}'`, `input_tokens=999999`, `estimated_cost_usd=0.50`) — MUST NOT be counted as a Stagehands subagent!
  3. A real Stagehands subagent session (`id='sess_sub1'`, `parent_session_id='sess_parent'`, `source='subagent'`, `model_config='{"_delegate_from": "sess_parent"}'`, `input_tokens=20000`, `output_tokens=400`, `estimated_cost_usd=0.25`)
- Assert that `compute_savings('sess_parent', db_path=...)` returns:
  - `front_door["subagent_runs"] == 1` (excluded `sess_branch`!)
  - `front_door["children_cost_usd"] == 0.25`
  - `front_door["sovereign_only_cost_usd"] == 1.0` (`1.25 - 0.25`)
- Run `/usr/local/lib/hermes-agent/venv/bin/python -m unittest discover -s /root/stagehands/tests -v` and confirm all tests pass.
- Do NOT run `git push`, `scp`, or touch `/var/www/ampersand.foo`.
