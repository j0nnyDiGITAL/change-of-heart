# P5R (Steam) — Progression Systems Findings (baton / technical / stamps)

**Date:** 2026-08-09 · **Source:** subagent cross-save empirical diff (6 saves, 2 playthroughs + fresh baseline) · **Status:** LOCATED, write-probe pending in-game confirmation

## Save timeline (from container headers)

| Save | Date/Location | Lv | Role |
|---|---|---|---|
| DATA14 | 12/24 Sat, Shibuya | 91 | run-1 start |
| DATA12 | 12/24, Shujin | 99 | run-1 |
| DATA11 (oracle) | 2/3 Fri, Late Night | 99 | run-1 end, maxed |
| DATA15 | 12/24, Qliphoth | 75 | run-2 |
| DATA13 | 12/31, in Mementos | 99 | run-2 |
| DATA16 | 3/20, Clear Data | 99 | run-2 end |

## Maxed-progression signature (oracle=3/4, run-2=1, D16=0, fresh=0/1)

All offsets absolute payload. Mirror copies exist at +0x18510 (byte-identical in oracle).

| Block | Oracle | DATA13/15 | DATA16 | Fresh | Confidence |
|---|---|---|---|---|---|
| A `0xA690–0xA780` (240B) | 115 nz, sum 372 (4/3/1) | 114 nz, all=1 | 0 | 23 nz, sum 45 | HIGH: maxed-progression flag matrix |
| B `0xB6C0–0xB720` (96B) | 36 nz, sum 135 (04/03 runs) | 36 nz, all=1 | 0 | 0 | HIGH progression; MEDIUM as baton |
| C `0xC6C0–0xC6EB` (44B) | 22 nz: 10×04 + 12×03 | 22 nz, all=1 | 0 | 6 nz, all=1 | HIGH progression; MEDIUM as stamps |
| D `0xF6A0–0xF700` (96B) | 68 nz | 0 | 0 | 12 nz | TRANSIENT (moved D14→D11; zero in Mementos save) — NOT stamps |

Run-1 saves (D14→D12→D11) byte-identical across A/B/C. Mirrors at `0x22BA8/0x23BC0/0x24BD5/0x27BC4`.

## Technical rank candidates (isolated byte: oracle=3/4, D13=1, D15=1, D16=0, fresh=0)

- `0x3D38` (oracle 3) — inside u32 counter region `0x3D20–0x3DC0`
- `0x3D80` (oracle 3)
- `0x3EC4` (oracle 3)
- `0x4184` (oracle 4) — near Subworx SECONDHANDPOINTS `0x411C` — MEDIUM-HIGH
- `0x13B64` (oracle 4) — item-possession records `0x13B40+`
- `0x1C248`, `0x1C290`, `0x1C694` — same signature

## Baton pass

No clean 10×u8 all-3s array exists. Per-member structs have no consistent rank field (re-verified). **Best candidate: block B** `0xB6C0–0xB720` (+ mirror `0x23BC0`) — 8 rows × 0x20 with 12-byte 04/03 runs (oracle) vs 01 (run-2) vs 0 (fresh/D16). Medium confidence as baton per-character flags.

## Mementos

- **Permanent flowers: `0x17DA8` u16** (Subworx-verified; "crashes at FFFF")
- Permanent stamps NOT a compact 5–9-int array. Block C (`0xC6C0`, 22 values 1–4) best matches per-floor/per-stand flags; count 22 ≠ ~165 total stamps → collapsed representation.
- Block D definitively NOT persistent stamps.

## SYSTEM.DAT

882 nonzero bytes scanned — pure flag-bit noise. Excluded.

## Required next step (game-as-oracle probe)

1. Set `0x3D38/0x3D80/0x3EC4/0x4184/0x13B64` → 3 in a fresh-save COPY → check Technical rank in-game
2. Set block C `0xC6C0–0xC6EB` → 4 → check Mementos stamp display per area
3. Set block B `0xB6C0–0xB720` → 4 → check Baton Pass screen

**Status: candidates located with high confidence; fields NOT confirmed until in-game probe.** Write-probe is the documented next action (user plays a copied save; reads back values).
