# P5R Save Editor — Safety Manual

Compiled 2026-08-13 from dual-oracle review (DeepSeek V4 Pro + Gemini) and
in-game-verified project knowledge. Read this before editing saves.

## How the editor can break the game (ranked)

| # | Misuse | Consequence | Detected? |
|---|---|---|---|
| 1 | Confidant rank writes without event-flag pairing | Rank shows 10 but story-gated content does not fire; rank-up scenes skipped forever | No |
| 2 | Pre-ranking a confidant before they exist in the block | Write ignored/overwritten; NPC never spawns | No |
| 3 | Editing while P5R runs or Steam Cloud is active | Game overwrites edits from RAM; partial writes; cloud revert | Yes (CRC) |
| 4 | Invalid persona/skill IDs in stock slot 0 | Crash on menu/battle load | No |
| 5 | Copying event-flag zones between different saves | Story logic dead-ends; NG+ mismatch | No |
| 6 | HP/SP above the derived max | Weird UI (999/400); engine clamps later | Yes (clamp) |
| 7 | Level writes without HP/SP adjustment | Over-max UI; weak characters | No |
| 8 | Money > 9,999,999 or mirror mismatch | Shop UI breaks; transactions desync | No |
| 9 | Invalid name encoding/length | Header corruption; text crash | Yes (parse) |
| 10 | Day counter / calendar edits | Day transitions freeze | No |
| 11 | Social stats at non-threshold points | Wrong rank display (self-corrects +1pt) | No |

## DO-NOT-DO list

1. Never edit while P5R is running or Steam Cloud is active. `--force` is for emergencies only.
2. Never copy event-flag zones or confidant blocks between different saves/playthroughs.
3. Never write a persona/skill ID that is not in the data tables. Keep stock slot 0 valid. (Enforced by the editor since 2026-08-13.)
4. Never invent flag bit 0x1000 on persona slots — preserve existing bits.
5. Never exceed 0..9,999,999 money; Yen is written to 0x35C0 (Joker EXP at 0x3C is preserved). (Enforced.)
6. Never set HP/SP above the real derived max (max is NOT stored in the save — derived from level + persona in-game; proven 2026-08-13). Set to 1 if unsure.
7. Never rank a confidant before they appear in the confidant block.
8. Pre-ranking confidants accepts missing rank-up scenes. Confidants must be ranked before their in-game story deadlines (e.g. Maruki Rank 9 on/before 11/18 for 3rd semester); rank edits past a deadline cannot retroactively replay story events. (Updated 2026-08-21).
9. Never touch day counter or calendar fields.
10. Names are fixed-length UTF-8 (truncated at 64/25 chars) — no control characters.
11. Level edits automatically sync minimum cumulative EXP curve (cubic Atlus formula) to prevent battle EXP calculation lockups. (Updated 2026-08-23).
12. Romance route toggle on PC is verified at `0x136A0` bit 0x02 for Rank 9+ confidants. (Updated 2026-08-23).

## Editor safety guarantees (as of 2026-08-23)

- All writes bounds-checked; PC payload passed through verbatim except verified offsets.
- Every repack re-signs CRC + AES correctly (182/182 regression unit tests, 2026-09-22).
- Teammate party personas scoped to authentic Tier 1 / 2 / 3 evolution lines; arbitrary cross-character persona assignment blocked to prevent battle animation crashes.
- Unsupported operations return `{"status": "unsupported"}` — never fake success.
- Persona stock writes validate ids against `data/Personas.txt` and `data/Skill ID.txt`.
- Backup zip is created automatically before every save write.
