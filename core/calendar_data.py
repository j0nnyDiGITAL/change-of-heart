"""
Fixed Persona 5 Royal calendar — READ-ONLY Time Travel Planner (ADR 0003, Tier 0).

The game's year is a hard-coded schedule (Apr 1 → Mar 31, spanning two game
years, "20XX"). Every story beat, exam, Palace deadline and confidant gate is
pinned to specific dates; the save merely records WHERE in that schedule the
player stands. This module encodes that schedule so the editor can render an
honest, read-only planner. It performs NO save writes and never touches the
event-flag matrix (D008/D009).

Sources:
- Megami Tensei wiki, "Calendar/Persona 5" (Royal section) — deadlines, exam
  blocks, confidant gates, weekday anchors.
- Weekday math verified against three wiki rows: 4/1=Fri, 6/21=Tue, 1/1=Sun
  (the game uses a real, non-leap 2016→2017-style year).

Conservatism rules (safe direction for a planner):
- Only days marked ×× (no free time) or auto-run story days are classed
  "story". Partial-slot (△) days are NOT asserted.
- Palace deadlines use the player-facing final date; where the wiki gives a
  treasure-room deadline a day before the game-over day, the EARLIER date is
  used (one day conservative can never mislead into missing a deadline).
"""

import re
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Calendar scaffolding
# ---------------------------------------------------------------------------

MONTH_ORDER = (4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3)  # Apr..Dec, Jan..Mar
MONTH_LENGTHS = {4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31,
                 11: 30, 12: 31, 1: 31, 2: 28, 3: 31}
MONTH_NAMES = {4: "April", 5: "May", 6: "June", 7: "July", 8: "August",
               9: "September", 10: "October", 11: "November", 12: "December",
               1: "January", 2: "February", 3: "March"}
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_FIRST_WEEKDAY_INDEX = 4  # 4/1 = Friday (wiki-verified)

assert sum(MONTH_LENGTHS[m] for m in MONTH_ORDER) == 365


def abs_day(month: int, day: int) -> int:
    """1-based absolute day index across the Apr..Mar game year (4/1 = 1)."""
    if month not in MONTH_LENGTHS:
        raise ValueError(f"Invalid month: {month!r}")
    if not 1 <= day <= MONTH_LENGTHS[month]:
        raise ValueError(f"Invalid day {day} for month {month}")
    idx = 0
    for m in MONTH_ORDER:
        if m == month:
            break
        idx += MONTH_LENGTHS[m]
    return idx + day


def weekday(month: int, day: int) -> str:
    """Weekday name for a game date (4/1 = Fri, verified vs wiki)."""
    return WEEKDAYS[(_FIRST_WEEKDAY_INDEX + abs_day(month, day) - 1) % 7]


# ---------------------------------------------------------------------------
# Palace deadlines (kind="palace") and confidant gates (kind="gate")
# ---------------------------------------------------------------------------

DEADLINES: List[Dict[str, Any]] = [
    # --- Palace deadlines ---
    {"key": "kamoshida", "kind": "palace", "month": 4, "day": 29,
     "label": "Kamoshida — treasure room / calling card deadline",
     "note": "Earliest of the two hard dates; game-over follows if unsecured."},
    {"key": "madarame", "kind": "palace", "month": 6, "day": 4,
     "label": "Madarame — Palace deadline",
     "note": "Day-3 deadline 6/2, calling-card deadline 6/3, final 6/4."},
    {"key": "kaneshiro", "kind": "palace", "month": 7, "day": 9,
     "label": "Kaneshiro — Palace deadline",
     "note": "Community consensus; verify against the in-game calendar."},
    {"key": "futaba", "kind": "palace", "month": 8, "day": 30,
     "label": "Futaba — Palace deadline",
     "note": "Community consensus (heist runs 8/26); summer ends 8/31."},
    {"key": "okumura", "kind": "palace", "month": 10, "day": 10,
     "label": "Okumura — Palace deadline",
     "note": "Miss it and 10/11 is 'the day Haru is sold'."},
    {"key": "sae", "kind": "palace", "month": 11, "day": 17,
     "label": "Sae — secure the treasure route",
     "note": "Calling card auto-sends 11/18; search-warrant game over 11/20."},
    {"key": "shido", "kind": "palace", "month": 12, "day": 17,
     "label": "Shido — calling card deadline",
     "note": "Party locked in the Palace same day; game over 12/24 if failed."},
    {"key": "maruki_palace", "kind": "palace", "month": 2, "day": 2,
     "label": "Maruki's Palace — final deadline",
     "note": "Calling card sent 2/2 evening; 'Day of Fates' 2/3."},
    # --- Confidant gates (calendar-pinned rank checks) ---
    {"key": "councillor_gate", "kind": "gate", "month": 11, "day": 18,
     "confidant": "Councillor", "required_rank": 9,
     "label": "Maruki (Councillor) Rank 9 — 3rd semester gate",
     "note": "Evaluated by the game on this date; auto-maxes to Rank 10."},
    {"key": "justice_gate", "kind": "gate", "month": 11, "day": 17,
     "confidant": "Justice", "required_rank": 8,
     "label": "Akechi (Justice) Rank 8 — third-tier persona gate",
     "note": "Required for Hereward and the Royal true ending route."},
    {"key": "faith_gate", "kind": "gate", "month": 1, "day": 12,
     "confidant": "Faith", "required_rank": 5,
     "label": "Kasumi (Faith) Rank 5 — 3rd semester progression gate",
     "note": "Rank 6+ unlocks after 1/13 only if Rank 5 was reached."},
]

# ---------------------------------------------------------------------------
# Story-pinned / locked days (×× in the Royal tables) — conservative subset.
# Partial-slot (△) days are deliberately NOT asserted here.
# ---------------------------------------------------------------------------

STORY_DAYS: Dict[int, List[int]] = {
    4: [9, 10, 11, 12, 13, 14, 15],                      # arrival + Kamoshida intro week
    5: [2, 3, 4, 5, 11, 12, 13, 14, 15, 16, 17],         # holidays, midterms, Madarame opener
    6: [9, 10, 11, 14, 15, 16, 19, 20],                  # TV trip, Akechi, Makoto, Kaneshiro op
    7: [13, 14, 15, 16, 18, 20, 21, 22, 23, 24, 25],     # finals, fireworks, Alibaba, Futaba visit
    8: [25, 26],                                         # Futaba card + auto-heist day
    9: [1, 7, 8, 9, 10, 11, 12, 14, 15, 16, 17, 18],     # school, Hawaii, Morgana rift, Okumura op
    10: [3, 11, 12, 17, 18, 19, 25, 26, 27, 29],         # Kasumi event, Haru sold, midterms, fest
    11: [18, 19, 20, 21, 22, 23, 24],                    # Sae card, locked Palace, warrant week
    12: [18, 20, 21, 22, 23, 24, 25],                    # election, finals, rearrest, Christmas
    1: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],          # New Year + illusion week + Palace breach
    2: [2, 3, 6, 7, 8, 9, 14],                           # Day of Fates, finals, Valentine's
    3: [19, 20],                                         # farewell / going home
}


def _parse_today_label(label: Optional[str]) -> Optional[Dict[str, int]]:
    """Parse a save header date label like '6/14(Tue)' into (month, day)."""
    if not label:
        return None
    m = re.match(r"(\d+)/(\d+)", str(label).strip())
    if not m:
        return None
    month, day = int(m.group(1)), int(m.group(2))
    if month not in MONTH_LENGTHS or not 1 <= day <= MONTH_LENGTHS[month]:
        return None
    return {"month": month, "day": day}


def _deadline_rows(today: Optional[Dict[str, int]],
                   confidant_ranks: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    today_abs = abs_day(today["month"], today["day"]) if today else None
    rows: List[Dict[str, Any]] = []
    for entry in DEADLINES:
        d_abs = abs_day(entry["month"], entry["day"])
        days_left = (d_abs - today_abs) if today_abs is not None else None
        if today_abs is not None and days_left < 0:
            continue  # past deadlines are not upcoming
        row: Dict[str, Any] = {
            "key": entry["key"],
            "kind": entry["kind"],
            "label": entry["label"],
            "note": entry.get("note", ""),
            "month": entry["month"],
            "day": entry["day"],
            "weekday": weekday(entry["month"], entry["day"]),
            "abs_day": d_abs,
            "days_left": days_left,
        }
        if entry["kind"] == "gate":
            row["confidant"] = entry["confidant"]
            row["required_rank"] = entry["required_rank"]
            rank = None
            if confidant_ranks:
                info = confidant_ranks.get(entry["confidant"]) or {}
                rank = info.get("rank")
            if rank is None:
                row["status"] = "unknown"
            else:
                row["status"] = "met" if rank >= entry["required_rank"] else "at_risk"
                row["current_rank"] = rank
        else:
            row["status"] = "today" if days_left == 0 else "upcoming"
        rows.append(row)
    rows.sort(key=lambda r: (r["abs_day"], r["kind"]))
    return rows


def build_calendar_plan(today_label: Optional[str] = None,
                        confidant_ranks: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build the full read-only planner payload.

    today_label: the save header's quick-info date string ("6/14(Tue)") or None
                 when no save is loaded (planner then shows the whole year).
    confidant_ranks: get_confidant_ranks()-shaped dict, or None.
    """
    today = _parse_today_label(today_label)
    months: List[Dict[str, Any]] = []
    for m in MONTH_ORDER:
        story = set(STORY_DAYS.get(m, []))
        deadline_days = {e["day"] for e in DEADLINES if e["month"] == m}
        days = []
        for d in range(1, MONTH_LENGTHS[m] + 1):
            cls = "open"
            if d in story:
                cls = "story"
            if d in deadline_days:
                cls = "deadline"
            days.append({"day": d, "weekday": weekday(m, d), "class": cls})
        months.append({"month": m, "name": MONTH_NAMES[m], "days": days})

    today_abs = abs_day(today["month"], today["day"]) if today else None
    return {
        "today": {
            "label": today_label,
            "month": today["month"],
            "day": today["day"],
            "weekday": weekday(today["month"], today["day"]) if today else None,
            "abs_day": today_abs,
        } if today else None,
        "total_days": 365,
        "months": months,
        "deadlines": _deadline_rows(today, confidant_ranks),
        "disclaimer": ("Read-only planner (ADR 0003). The in-game date cannot be "
                       "edited by this tool; day-counter writes are gated on diff "
                       "verification. Story days shown are a conservative "
                       "××-only subset; partial-slot days are not marked."),
    }
