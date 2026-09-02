# AGENTS.md — p5r-save-editor (Change of Heart)

## Domain Playbook
> This project follows the **Binary & Save File Editors (Archetype 2)**.
> Read [guides/binary-and-save-engineering.md](file:///E:/ai-workspace/knowledge-base/guides/binary-and-save-engineering.md) for domain-specific invariants.


> **Agent: read this first.** It is your map. Open deeper docs by line range only when needed.

## Where to look (on-demand)
| Need | File | Description |
|---|---|---|
| Truth & History | `MEMORY.md` | Locked decisions (D001+), verified domain rules |
| Current State | `state.json` / `STATUS.md` | Active phase, gate, blockers, next steps |
| Loop State | `GOALS.md` | The Loop: CURRENT POSITION, milestones, phase plan |
| Safety & Pitfalls | `SAFETY.md` | Ranked failure modes and DO-NOT-DO list |
| Environment | `PROJECT_BOOTSTRAP.md` | Verified working tools and build recipes |

## Startup Protocol (in order)
1. **Loop-First Execution (Mandatory, HARNESS-AGNOSTIC):** Resuming from `handoff.md` or cold, the resume contract is `GOALS.md` → **CURRENT POSITION** → "do this next". This loop works for ANY agent (Pi, Claude Code, Codex, OpenCode, fresh session) — the contract is plain files, no harness mechanism. `handoff.md` is a *stable trigger only* — do not trust its detail to be current. Read `GOALS.md`, act on its CURRENT POSITION, and treat `state.json`/`STATUS.md` as synced FROM `GOALS.md` (never authoritative on their own — they lag the loop). Note: `.pi/` is Pi-specific — non-Pi harnesses IGNORE it and read root `handoff.md` + `GOALS.md`.
2. If cold and `GOALS.md` is missing/empty, read `state.json` and recent decisions in `MEMORY.md`.
3. Run `git status -s` (protect context window from unbounded output).
4. Run invariant check & test gates: `python scripts/check-invariants.py`.

## Exit Protocol (Mandatory on every session end)
1. Verify all test/check commands pass (`python scripts/check-invariants.py`).
2. Record durable decisions in `MEMORY.md` with new `Dxxx` ID.
3. Write session log to `memory/YYYY-MM-DD-topic.md` and update `handoff.md`.
4. Update `state.json` (`phase`, `gate`, `test_count`, `updated_at`, `next_action`).
5. Auto-sync `STATUS.md`: `python scripts/check-invariants.py --sync`.
6. Verify working tree cleanliness (`git status -s` shows no stray scratch files).

## Architectural Invariants
1. **Save/State Integrity:** Write primary + mirror (+0x18510), read must warn on mismatch (`test_mirror_sync.py`).
2. **Ground Truth Verification:** Never guess data structures from web assumptions; verify via real diffs (`tools/diff_mapper.py`).
3. **3-Phase Execution Cadence (Self-Driving & Anti-Analysis Paralysis):**
   - *Phase 1 (Recon, max 2–3 turns):* Prove 90% of raw facts/opcodes, then HALT analysis.
   - *AUTONOMOUS TRANSITION (Mandatory):* Do NOT wait for user prompt/permission. Once facts are verified, announce `[Phase Transition] Ground truth verified. Proceeding to Phase 2 (Code Synthesis)...` and write the code immediately.
   - *Phase 2 (Synthesis, 1–2 turns):* Immediately write working code (`src/` or `core/`). Wire hooks immediately.
   - *Phase 3 (Oracle Gate, 1 turn):* Execute test gates (`scripts/check-invariants.py`). Let test errors drive refinement.
4. **Tool Output Hygiene:** Never run un-bounded terminal dump commands. Always pipe or truncate verbose outputs (`git status -s`, `pytest -q`, `head -n 50`, `tail -n 30`) to protect the context window from token bloat.
5. **Communication Protocol (STE + Caveman):** Output strictly in Simplified Technical English merged with Caveman brevity. Zero politeness fluff, zero conversational padding. Raw facts, bullet points, and code only.
6. **User Preemption & Anti-Looping Directive (Mandatory):** On receiving any new user message or nudge, immediately abort lingering internal scratchpad loops. Address the user's latest prompt in Step 1. Never repeat the same reasoning sentence more than twice; trust trace ground truth and proceed directly to code synthesis.
7. **Discuss First, Confirm Before Mutating:** When the user asks exploratory, diagnostic, or theoretical questions, prioritize analysis and discussion. NEVER execute file modifications, configuration changes, or mutating actions without explicit user confirmation.
8. **Compute Over Context (The Universal Tool-Building & Token Compression Law):** Never use the LLM context window as a dumb data pipe. Whenever an operation involves reading, transforming, validating, or emitting more than ~50 lines of repetitive or structured data: **NEVER hand-type or ingest raw data across chat turns.** ALWAYS write a lightweight, deterministic script in `scripts/` or `tools/` (Python/Node/Bash) to perform the computation natively on the CPU.
9. **Single-Source Empirical Ground Truth:** When an execution trace, production log, database schema, API response, or test artifact exists on disk or over the wire, trust its recorded empirical values directly.
10. **Tool Batching Cap:** Maximum 4 focused tool calls per turn. Maintain output hygiene.
11. **Tooling & Automation Script Safety (Bounded & Self-Guarded):** Monotonically advancing pointers (`assert pos > prev_pos`), explicit max iteration bounds, and test sample dry-runs before production runs.
12. **Test Gate:** All check commands and test suites must pass before declaring work complete.
13. **Mandatory Goal & Task-Scoped To-Do Protocol (Every Run):** At the beginning of any execution run or prompt, the agent MUST establish and maintain an ongoing 1-line Goal and a task-scoped To-Do list with live progress updates.
14. **Epistemic Humility & Boundary Surfacing:** Never guess unknown APIs, database schemas, hardware registers, memory offsets, or file paths. Surface technical blockers immediately.
15. **Multi-Modal & Sensory Verification (The Vision Blindspot Law):** For frontend UI, graphics, or layout changes: verify visual output using headless screenshots or deterministic property-probe scripts.
16. **Clean Core Abstraction (Avoid the Harness Trap):** Never mistake a temporary test harness, mock, or hardcoded test fixture for the production product.
17. **Secret & Credential Firewall (Zero Leakage):** Never commit `.env`, `*secret*`, `*.pem`, `*.key`, or service account tokens to git.
18. **Cross-Platform Path Portability:** All Python tooling, build scripts, CMake targets, and C/C++/Node `#include`/`import` paths must strictly use **POSIX forward slashes (`/`)** and `pathlib.Path`.
19. **Test Runtime Budget (< 3s Fast Gate):** Per-turn invariant check commands registered in `state.json` must execute in **sub-3-seconds**.
20. **Tiered Agent Synergy (Orchestrator + Worker Protocol):** Compact task prompts, zero context bleed, ground-truth code verification.
21. **Loop-First State Contract (Continuous Ledger, Crash-Safe, HARNESS-AGNOSTIC):** The resume contract is `GOALS.md` → CURRENT POSITION → "do this next". Update `GOALS.md` + sync `state.json`/`STATUS.md` IMMEDIATELY after each completed item.
22. **Ground-Truth Before Review:** Read the actual files/diffs the claim rests on.
23. **Human-Gate Triggers:** Human sign-off required before irreversible actions, architecture changes, or money/data-costing actions (`human_gate: required` in `state.json`).

## Circuit Breaker & Git Revert Protocol

If the same test or build fails **3 consecutive times**, HALT immediately:
1. **Preserve Work to Patch:** Save ongoing changes to research scratch:
   ```bash
   git diff > research/failed_attempt.patch
   ```
2. **Reset Working Tree:** Revert working directory to the last known green commit:
   ```bash
   git checkout .
   git clean -fd
   ```
3. **Set Blocked State:** Update `state.json` and `STATUS.md` with `"gate": "blocked"`.
4. **Log Blocker:** Append the root cause and failure trace to `STATUS.md` and `memory/YYYY-MM-DD-topic.md`.
5. **Halt Execution:** Exit turn and request human guidance. Never silently change or bypass an invariant.

## Constraints (violating = corrupt save)

- `J:\SteamLibrary\...\P5R\CPK\BASE.CPK` via `tools/cpk_extract.py` is ground truth. Not web.
- PC ≠ PS4: KHSaveEditor `0x357C`/`0x2252` is PS4 garbage on PC. Verify via 2-save diff (`tools/diff_mapper.py`).
- Save is 4 paradigms + mirror `+0x18510`: Gear `0x1B30/0x2330/0x1F30/0x3430+save-idx` owned-flag `0x00/0x01`; Stacks `0x2410..0x2800` count `0..99`. Write primary+mirror, read must warn on mismatch.
- Quick-array `0x3530` (30×[u16 id][u16 flag]) is never merged — surface as `conflicts` where count-region wins.
- `0xA000+` Outfits (286 rows, `ITEM.TBL` seg6) — DO NOT wire save offset until diff proves.

## Build order

S1 normalized read (backend, FIRST) → S4 key guard → S2+S5 paradigm writes + three-bucket UI (Gear ◆◇ / Items steppers / Key guarded) → S3 done. Vertical slice: melee+consumables end-to-end. No max presets yet.

## Commands

- `python tools/extract_tables_job.py` — decompress `BATTLE/TABLEITEM.TBL` (168416B).
- `python -m PyInstaller P5R_Save_Editor.spec --noconfirm --clean --distpath dist` — rebuild `dist/P5R_Save_Editor.exe`.
- `python tools/capture_ui_state.py` — automated headless capture of all 10 views into `screenshots/current_state/`.
- `npm run lint:context` — token budget + path + ADR check (fails = don't report done).
- `python scripts/check-invariants.py` — run invariant checks.

## Ready/Done gates (block work if not [x])

**Ready (START) before coding:**
`[ ] stakeholders [ ] MRM is now [ ] ≥2 alternatives [ ] ITEM.TBL seg/stride cited [ ] ADR file created`

**Done before stamp:**
`[ ] 178/178 + mirror read-check warns [ ] no phantom merge [ ] STATUS.md stamped [ ] state.json updated [ ] lint:context pasted`

