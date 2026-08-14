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
5. Never exceed 0..9,999,999 money; both fields (0x35C0 and 0x3C) are always written together. (Enforced.)
6. Never set HP/SP above the real derived max (max is NOT stored in the save — derived from level + persona in-game; proven 2026-08-13). Set to 1 if unsure.
7. Never rank a confidant before they appear in the confidant block.
8. Pre-ranking confidants accepts missing rank-up scenes. The 3rd-semester unlock is best-effort: it writes ranks only; story flags in 0x2F200 are not mapped and may block the semester. Test on a backup copy. (Warning added 2026-08-13.)
9. Never touch day counter or calendar fields.
10. Names are fixed-length UTF-8 (truncated at 64/25 chars) — no control characters.
11. Never touch unsupported zones (compendium, SteamID, romance flags on PC) — the editor returns `unsupported` for these since 2026-08-13, not silent success.

## Editor safety guarantees (as of 2026-08-13)

- All writes bounds-checked; PC payload passed through verbatim except verified offsets.
- Every repack re-signs CRC + AES correctly (40/40 + 13 regression tests).
- Unsupported operations return `{"status": "unsupported"}` — never fake success.
- Persona stock writes validate ids against `data/Personas.txt` and `data/Skill ID.txt`.
- `equip_persona` refuses to equip an empty slot.
- Backup zip is created automatically before every CLI edit unless `--no-backup`.
