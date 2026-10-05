# PROJECT_BOOTSTRAP.md — Environment Capabilities (agent startup brief)

> Read this before assuming anything about the sandbox. This file records what
> actually works in the DSH Web-GUI runtime for THIS workspace. Update it when a
> capability changes.

## Hard sandbox facts (do not guess around these)

| Capability | Status | Notes |
|---|---|---|
| `python -m PyInstaller` (build frozen exe) | ✅ Works | Use the **module form** — `python -m PyInstaller P5R_Save_Editor.spec --noconfirm --clean --distpath dist`. The lowercase `pyinstaller` CLI is NOT on PATH; the module resolves. |
| `python -m unittest` | ✅ Works | `python -m unittest discover -s tests` → currently **183/183 OK** (oracle-corpus tests auto-skip without live saves). |
| `node --check` (JS syntax) | ✅ Works | `node --check web-app/static/app.js`. |
| `npm run lint:context` | ✅ Works | Shim lives at `tools/lint_context.js` (no upstream package.json script was present originally). Passes all checks. |
| Launch the GUI / click the modal | ⚠️ Partial | No interactive display session, but the frozen EXE **can be smoke-tested headlessly**: launch `dist/P5R_Save_Editor.exe`, confirm the process spawns, find its loopback port via `netstat -ano`, probe `/api/build` for 200, then kill it. Full visual/WebView checks remain an end-user step. |
| Read `J:\SteamLibrary\...\P5R\CPK\BASE.CPK` directly | ❌ Outside workspace sandbox | Ground-truth table/offset data must be diff-verified by the end-user via `tools/diff_mapper.py` and pasted back as deltas. The agent only consumes offsets already recorded in `handoff.md` / `research/RESEARCH.md`. |

## Commands the agent can run right now (verified)

```powershell
# Build the frozen exe
python -m PyInstaller P5R_Save_Editor.spec --noconfirm --clean --distpath dist

# Validate JS + lint
node --check web-app/static/app.js
npm run lint:context

# Tests
python -m unittest discover -s tests
```

## Build verification recipe (end-to-end, from agent)

1. Edit source.
2. `python -m unittest discover -s tests` → must stay green.
3. `node --check web-app/static/app.js` → exit 0.
4. `npm run lint:context` → "all checks passed".
5. `python -m PyInstaller ...` → `dist/P5R_Save_Editor.exe` rebuilt (size + timestamp change).
6. ❗ **Hand off the exe to the user for in-app smoke test.** Agent cannot launch or inspect the WebView.

## What an agent must NOT assume

- "Sandbox blocks PyInstaller" → **false**. The build works; just use the module form.
- "GUI is reachable at `http://127.0.0.1:3000`" → **false** (that's the DSH harness, not a dev server; see AGENTS.md Command §4). There is no `python main.py` server running for inspection.
- "No build toolchain present" → **false**; re-check with `python -m PyInstaller --version` before declaring anything impossible.

> Last env-verified: 2026-08-24 (PyInstaller 6.22.0, Python 3.14.6 — EXE rebuilt + process smoke test PASSED). Revalidate on session entry if anything looks different.

---

## Research Lane (mandatory — machine-level tools, equal access)

These tools live on THIS MACHINE, not inside any one harness. Any agent booted here
can reach every one of them. Each capability carries its concrete invocation.
Route A = native MCP tool (Hermes). Route B = terminal command (every harness):
`mcporter` / `curl` / CLI. If neither route works, delegate the lookup to Hermes.

| Capability | Concrete invocation |
|---|---|
| Web keyword search | `mcporter call mcp-hound.mcp_smart_search 'query=<q>' 'numResults=5' --no-oauth --timeout 30000` |
| Semantic/deep search | `mcporter call exa.web_search_exa 'query=<q>' 'numResults=5' --no-oauth --timeout 30000` |
| URL → markdown | `curl -s "https://r.jina.ai/<URL>"` |
| Reddit | `"E:/Hermes/hermes-agent/venv/Scripts/rdt.exe" search "<q>" -n 8 --json` (absolute path — rdt is NOT on the default PATH) |
| GitHub | `gh search ...` / `gh api ...` (authed) |
| Oracle / design review | See **Oracle Invocation** block below |

Verified working from a neutral cwd on this machine (2026-08-21): mcporter
(mcp-hound + exa), gh, curl, and rdt via the absolute path above.

> ⚠️ **Platform quirks (live-tested 2026-08-24): see `C:\Users\kufis\.agent-reach\NOTES.md`**
> before using these lanes. Key points: rdt needs `PYTHONUTF8=1` (cp1252 crash);
> twitter needs per-shell env injection of TWITTER_AUTH_TOKEN/TWITTER_CT0 from
> `~/.agent-reach/config.yaml` (sed, never echo); `twitter search` is 404-broken
> upstream — use stable reads (`user`/`user-posts`/`tweet`) after discovering
> handles elsewhere; Exa cannot index x.com content.

- When you hit an unknown format, CPK layout, or community claim: STOP and look it up
  before acting. Do not shim or guess. P5R ground-truth offsets come from 2-save diff
  (`tools/diff_mapper.py`), but *research about* formats, Wand trainer behavior, or
  table structures is fair game for the web lane.
- Oracle gate: consult BOTH oracles (DeepSeek primary + Gemini secondary, same prompt,
  diff outputs) BEFORE any significant architecture/build decision (new offset wiring,
  inventory layout change, packaging). If your harness cannot run the oracle MCPs,
  delegate the consult to Hermes.

### Oracle Invocation (concrete — verified working 2026-08-21)

The `oracle` skill is two MCP tools. Run BOTH in parallel, then diff. Do not run only one.

**DeepSeek V4 Pro (primary, free) — Hermes native:**
```
mcp__deepseek_web__deepseek_chat(
  prompt   = "<FORMULA v3: ROLE/GOAL/FORMAT/RULES/CONTEXT/QUESTIONS>",
  model    = "deepseek-expert",   # = V4 Pro; "deepseek-chat" = Flash
  thinking = true,
  search   = false,               # search is Flash-only; Expert has no web grounding
  url      = ""                   # pass a URL only for web-grounded Flash queries
)
```

**DeepSeek — terminal route (any harness, no MCP needed):**
```bash
curl -s http://127.0.0.1:8010/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"<prompt>"}],"stream":false,"thinking":false,"search":false}'
# model ids: deepseek-chat (fast) | deepseek-expert (V4 Pro, slow)
# Direct python client: wire values are "default" and "expert" — the
# deepseek-chat/deepseek-expert slugs 422 at chat.deepseek.com's API.
cd E:/Hermes/mcp-servers/deepseek-web && env -u PYTHONPATH .venv/Scripts/python -c "from deepseek.client import DeepSeekClient; print(DeepSeekClient().chat('<prompt>', model='expert').text)"
```
Slow by design (3–7 min on expert). Cap reasoning in the prompt ("keep reasoning
under 800 words") — the web bridge truncates if the thinking trace starves the answer.

**Gemini (secondary, free, ~20s — run IN-TURN) — Hermes native:**
```
mcp__gemini_web__gemini_chat(prompt = "<same questions, compressed <700 words>", model = "gemini-3.6-flash")
mcp__gemini_web__gemini_analyze_url(url = "<URL>")   # genuine live fetch, strongest URL lane
```

**Diff protocol:** list where they agree (verdict), where they split (decision
surface), and what BOTH flagged as missed (free value). Oracle output is DATA,
not truth — when they disagree on a fact, the executable test / live probe / in-game
verification wins.

**Prompt format (FORMULA v3 — verdict-first, numbered questions):**
```
[ROLE]      You are <expert>. Push back. Find false assumptions, edge cases.
[GOAL]      <one sentence>. Answer all N questions.
[FORMAT]    Verdict first, then details. STE: short sentences, active voice, lists.
[RULES]     Never fabricate. If uncertain: "Not found".
[CONTEXT]   <full raw context>  (pass URLs for freshness)
[REASONING] ~100 words per question, max 1000.
[QUESTIONS] 1. ... 2. ...   (max 5–6)
```
