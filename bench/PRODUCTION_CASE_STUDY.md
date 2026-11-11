# Production Case Study: 12 Days of a Live Frontier Companion (`google/gemini-4-argon`)

Beyond synthetic benchmarks, Stagehands was designed around telemetry from a live, daily-driver Hermes v0.22.5 companion agent running **`google/gemini-4-argon`** over a 12-day production window (**2026-10-23 to 2026-11-04**).

 All figures below were extracted read-only (`mode=ro`, metadata and character lengths only) from the agent's production SQLite `state.db` (`session_model_usage`, `sessions`, and `messages` deduplicated by `tool_call_uid`).

---

## 1. The Production "Context Choke" Signature

Across 12 days on `google/gemini-4-argon` (`task = main_chat`):

- **Conversational API calls (`google/gemini-4-argon`):** `2,303` calls
- **Deduplicated tool calls in Argon sessions:** `2,079` calls (`delegate_task` calls during window: `0`)
- **Raw tool output injected directly into parent Argon context:** `10,296,604` characters (**`~2,574,151` raw tokens**)
- **Cumulative Argon input tokens billed across those turns:** **`230,840,257` tokens**
  - Uncached input tokens: `53,275,924`
  - Cache-read input tokens: `177,564,333`
- **Total Argon output tokens:** `1,309,647` tokens (**176× more input read than output generated**)

Because Hermes appends every raw tool return to the parent transcript, each large tool payload is re-read on every subsequent turn of a long-lived messaging session:
- **Session A (4-day window):** `623` distinct tool calls injected **`3,054,390` chars (`~763,598` tokens)** of raw tool output into a single Argon conversation.
- **Session B (29-hour active window):** `416` distinct tool calls injected **`2,232,621` chars (`~558,155` tokens)** of raw tool output into the active Argon conversation.

---

## 2. Audited Tool-Output Breakdown & Stagehands Routing Map

| Tool / Workload Class | Distinct Calls | Raw Output Chars | Est. Raw Tokens | Avg / Max Chars | Calls ≥ 4 KB / ≥ 10 KB | Stagehands Interception Route |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| **`skill_view`** (procedural docs loaded into parent) | 171 | 3,859,159 | 964,790 | 22,568 / 74,535 | 160 / 105 | Loaded inside disposable subagent (`code_monkey` / `scout`) instead of persistent parent window |
| **`terminal`** (522 doc/PDF builds, 148 `ffmpeg`, 81 `himalaya` email ops) | 918 | 2,783,104 | 695,776 | 3,032 / 56,492 | 179 / 73 | **`code_monkey`** (`max_tokens: 1500`) for build/test loops; **`scout`** (`max_tokens: 800`) for email/log triage |
| **`read_file`** (long local docs, specs, configs) | 103 | 839,843 | 209,961 | 8,154 / 63,927 | 63 / 20 | **`scout`** (`deepseek-v4-flash`, `max_tokens: 800`) |
| **`web_extract`** + **`web_search`** (articles, PDFs, search dumps) | 96 | 1,161,790 | 290,447 | 12,102 / 70,553 | 70 / 35 | **`librarian`** (`qwen3.7-flash`, `max_tokens: 1000`) returns cited excerpts only |
| **`session_search`** + **`fact_store`** (historical transcript & memory recall) | 281 | 1,188,061 | 297,015 | 4,228 / 71,232 | 83 / 36 | **`briefer`** (`deepseek-v4-flash`, `max_tokens: 8192`) condenses 71 KB history windows into `<250`-word briefs |
| **Companion-native tools** (`text_to_speech`: 159, `vision_analyze`: 110, `memory`: 26, `cronjob_manage`: 57, other: 158) | 510 | 464,647 | 116,162 | 911 / 12,725 | 15 / 3 | Stays in **Sovereign (`google/gemini-4-argon`)** — tiny footprint, direct user experience |
| **Total (12-Day Argon Window)** | **2,079** | **10,296,604** | **2,574,151** | — | **570 / 272** | **95.5% of raw tool-output volume (`2.46M / 2.57M` tokens) is backstage-delegable** |

---

## 3. Terminal Workload Drill-Down (`918` Calls in Argon Window)

Inspecting the command prefixes across the `918` `terminal` calls shows why a frontier conversational model should not execute mechanical loops directly in its primary context:

- **Python / PDF / `.docx` / ReportLab build & verification scripts:** `522` calls (`56.9%`) — iterative document generation where intermediate tracebacks and layout checks stay in the parent session forever.
- **`ffmpeg` / `ffprobe` media processing:** `148` calls (`16.1%`) — verbose codec banners and stream probes.
- **`himalaya` CLI email operations:** `81` calls (`8.8%`) — raw JSON envelope listings, search results, and full multi-page MIME thread bodies.
- **Filesystem / DB / shell probes (`date`, `ls`, `curl`, `grep`, `sqlite3`, `find`, `tail`):** `167` calls (`18.2%`).

---

## 4. Key Takeaway

In a real production companion, **95.5% of the tool-output tokens entering the frontier model's context (`2.46M` of `2.57M` tokens)** come from backstage mechanics: reading 70 KB web extractions, iterating on Python/PDF scripts, triaging raw CLI email JSON, hydrating old session transcripts, and loading 20 KB–74 KB procedural skills to run those tasks.

By routing those four lanes through **Stagehands** (`scout`, `librarian`, `code_monkey`, `briefer`) while keeping the main agent on **`google/gemini-4-argon`**, the human never loses the frontier voice — and the Sovereign never chokes on backstage exhaust.
