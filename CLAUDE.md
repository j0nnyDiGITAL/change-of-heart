# CLAUDE.md
> Master agent instructions and architectural invariants live at [AGENTS.md](./AGENTS.md). Read AGENTS.md first.

## Agent skills

### Issue tracker

Issues live in this repo's GitHub Issues; skills use the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Five default labels, each equal to its role name (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one root `GLOSSARY.md` + `docs/adr/`. See `docs/agents/domain.md`.
