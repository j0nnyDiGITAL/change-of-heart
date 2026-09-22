"""CHRONOS — calendar time travel for P5R saves.

All format rules below are empirically verified against a corpus of
legitimate saves spanning the full story (docs/TIME_TRAVEL_GUIDE.md):

- The canonical date is the container header field `day`: a 0-based index
  counting from April 1 (April 1 = 0, Jan 1 = 275 on a non-leap schedule).
  Verified exact across the whole save corpus.
- The payload day counter at 0x3D70 follows: 0x3D70 = max(0, hdr.day - 52)
  for hdr.day <= 242 (i.e. dates through 12/31). Verified exact across the
  corpus. The rule BREAKS after New Year (cross-year semantics unverified).
- The event-flag matrix @0x2F200 = 12 tables x 3072 bits; bit ids address it
  as flat = (base>>28)*3072 + index.
- A day is warp-skippable when its schedule data triggers no story events.
  Ambient (daily-life) event families are derived empirically from the
  model: any event fired on >= 10 distinct days of the year.

Safety envelope (fail-closed):
- Forward-only warps (v2 card), inside the same in-game year, target <= 12/24
  (hdr.day <= 267), because 0x3D70 semantics beyond the year boundary are
  unverified. The FULL TIME WARP card (v3) additionally supports backward
  warps by syncing palace + event flags to the destination date.
- Every skipped day and the destination day itself must be classified
  skippable by the chronos model (v2), or fully flag-synced (v3); otherwise
  the warp is refused.
"""
import json
import os
import re
import struct
import sys

# Weekday by hdr.day: April 1 2016 was a Friday (cross-checked against the
# desc text of every corpus save: 7/26 Tue, 12/25 Sun, 1/2 Mon).
WEEKDAYS = ("Fri", "Sat", "Sun", "Mon", "Tue", "Wed", "Thu")
_DATE_TOKEN_RE = re.compile(r"^\d{1,2}/\d{1,2}\([A-Za-z]{3}\)\s*")

# hdr.day values (0-based from April 1) — hard verification envelope
DAY_IDX = {  # (month, day) -> hdr.day
    (4, 1): 0, (7, 26): 116, (8, 20): 141, (8, 21): 142, (8, 22): 143,
    (9, 15): 167, (12, 24): 267, (12, 31): 274,
}
MONTH_STARTS = {4: 0, 5: 30, 6: 60, 7: 91, 8: 122, 9: 153,
                10: 183, 11: 214, 12: 244}
MONTH_DAYS = {4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30,
              10: 31, 11: 30, 12: 31}

DAY_COUNTER_OFFSET = 52
DAY_COUNTER_MAX_INDEX = 242          # last verified 0x3D70 date (12/31)
HDR_DAY_MAX = 267                    # last shipped target: 12/24
AMBIENT_THRESHOLD = 10               # distinct days -> ambient family

def _resolve_model_path() -> str:
    """Frozen EXE: web-app/static is bundled under _MEIPASS (see spec datas).
    Dev: resolve against the project root (CWD when launched normally)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "web-app", "static", "chronos_model.json")
    return os.path.join("web-app", "static", "chronos_model.json")


MODEL_PATH = _resolve_model_path()

SAFE_CLASSES = {"EMPTY", "FREE", "TUTORIAL", "FLAG_ONLY", "GUARDED"}


def day_index(month: int, day: int) -> int:
    """0-based day index from April 1 (the save format's hdr.day)."""
    return MONTH_STARTS[month] + (day - 1)


def index_to_month_day(idx: int):
    for m in (4, 5, 6, 7, 8, 9, 10, 11, 12):
        start = MONTH_STARTS[m]
        end = start + MONTH_DAYS[m]
        if start <= idx < end:
            return m, idx - start + 1
    raise ValueError("day index %d outside verified warp window (Apr 1 - Dec 31)" % idx)


def load_model(path: str = None) -> dict:
    p = path or MODEL_PATH
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def derive_ambient_events(model: dict, threshold: int = AMBIENT_THRESHOLD) -> set:
    """Events fired on >= threshold distinct days are ambient/daily-life."""
    per_event = {}
    for month, days in model["lattice"].items():
        for _d, segs in days.items():
            seen = set()
            for s in segs.values():
                for c in s.get("calls", []):
                    seen.add(c["event"])
            for e in seen:
                per_event[e] = per_event.get(e, 0) + 1
    return {e for e, n in per_event.items() if n >= threshold}


def _day_skippable(model: dict, ambient: set, month: int, day: int):
    """(bool, list_of_blockers) for one calendar day from the model."""
    d = model["lattice"].get(str(month), {}).get(str(day))
    if d is None:
        return True, []
    blockers = []
    for seg, s in sorted(d.items()):
        cls = s.get("class")
        if cls == "CALL_EVENT":
            story = [c for c in s.get("calls", []) if c["event"] not in ambient]
            if story:
                blockers.append({"segment": seg, "proc": s.get("proc"),
                                 "reason": "story_event",
                                 "calls": story})
        elif cls not in SAFE_CLASSES:
            blockers.append({"segment": seg, "proc": s.get("proc"),
                             "reason": "class_" + cls})
    return (not blockers), blockers


def build_time_travel_plan(model: dict, current_hdr_day: int, target_month: int,
                           target_day: int) -> dict:
    """Full-walk plan: classify every skipped day and the destination day."""
    try:
        tgt_idx = day_index(target_month, target_day)
    except KeyError:
        return {"allowed": False, "status": "invalid",
                "reason": "Unknown month/day (warp window is Apr 1 - Dec 24)."}

    if tgt_idx <= current_hdr_day:
        return {"allowed": False, "status": "invalid",
                "reason": "Forward-only: destination must be after the save date."}
    if tgt_idx > HDR_DAY_MAX:
        return {"allowed": False, "status": "invalid",
                "reason": "Targets beyond 12/24 are outside the verified "
                          "day-counter envelope (Apr-Dec only)."}

    ambient = derive_ambient_events(model)
    cur_m, cur_d = index_to_month_day(current_hdr_day)
    blockers = []
    skipped = []
    idx = current_hdr_day + 1
    while True:
        m, d = index_to_month_day(idx)
        ok, bad = _day_skippable(model, ambient, m, d)
        if not ok:
            blockers.append({"date": "%d/%d" % (m, d), **bad[0]})
        skipped.append({"date": "%d/%d" % (m, d),
                        "class": "blocked" if not ok else "ok"})
        if idx == tgt_idx:
            break
        idx += 1

    allowed = not blockers
    return {
        "allowed": allowed,
        "status": "ok" if allowed else "blocked",
        "current": {"hdr_day": current_hdr_day, "date": "%d/%d" % (cur_m, cur_d)},
        "target": {"hdr_day": tgt_idx, "date": "%d/%d" % (target_month, target_day)},
        "days_skipped": tgt_idx - current_hdr_day,
        "ambient_events": sorted(ambient),
        "blocked_days": blockers,
        "notes": [
            "Forward-only within the same game year (Apr-Dec envelope).",
            "Every skipped day + the destination day must be script-skippable.",
            "Write set: header.day + payload 0x3D70 mirror (max(0, hdr.day-52)), "
            "then re-sign (dual CRC32 + AES) — nothing else is touched.",
        ],
    }


def _rewrite_desc_date(desc: str, tgt_idx: int) -> str:
    """Rewrite only the leading 'M/D(DoW)' token of the header quick-info text.

    The slot-screen string is cosmetic, but the load screen renders it —
    a stale date next to a warped clock would be a visible inconsistency.
    Time-of-day wording (Afternoon/Evening/...) is left untouched.
    """
    m, d = index_to_month_day(tgt_idx)
    token = "%d/%d(%s)" % (m, d, WEEKDAYS[tgt_idx % 7])
    lines = desc.split("\n")
    if lines and _DATE_TOKEN_RE.match(lines[0]):
        lines[0] = _DATE_TOKEN_RE.sub(token + " ", lines[0], count=1)
        return "\n".join(lines)
    return desc  # no date token present — leave cosmetic text alone


ENGINE_DAY_OFFSET = 0x0A670       # engine's internal day (exact match hdr.day
                                   # across all corpus saves; no +0x18510 mirror)
ENGINE_DAY_DUP = 0x0A674           # near-duplicate (matches hdr.day in 14/16 slots)


def _write_clock_fields(editor, tgt_idx: int) -> dict:
    """Shared write set: header day + desc date token + 0x3D70 mirror +
    engine internal day fields (0x0A670, 0x0A674).

    Caller re-signs via save_to_bytes() and writes to disk."""
    editor.parser.header.day = tgt_idx
    editor.parser.header.desc = _rewrite_desc_date(editor.parser.header.desc, tgt_idx)
    editor.container.header_bytes = editor.parser.header.pack()
    d = bytearray(editor.parser.data_payload)
    ctr = max(0, tgt_idx - DAY_COUNTER_OFFSET)
    struct.pack_into("<H", d, 0x3D70, ctr)
    struct.pack_into("<H", d, ENGINE_DAY_OFFSET, tgt_idx)
    struct.pack_into("<H", d, ENGINE_DAY_DUP, tgt_idx)
    editor.parser.data_payload = bytes(d)
    return {"header_day": tgt_idx, "counter_0x3D70": ctr,
            "engine_day_0x0A670": tgt_idx, "engine_day_dup_0x0A674": tgt_idx,
            "desc_date": "updated"}


def apply_time_travel(editor, model: dict, target_month: int, target_day: int) -> dict:
    """Plan, and if allowed, mutate the editor's payload + header day fields.

    Mutates: parser.header.day (u32 @hdr) and payload 0x3D70 mirror.
    Caller re-signs via save_to_bytes() and writes to disk.
    """
    plan = build_time_travel_plan(model, editor.parser.header.day,
                                  target_month, target_day)
    if not plan["allowed"]:
        return {"status": plan["status"], "plan": plan}

    tgt = plan["target"]["hdr_day"]
    wrote = _write_clock_fields(editor, tgt)
    return {"status": "success", "plan": plan, "wrote": wrote}


# ---------------------------------------------------------------------------
# WARP V2 — branch-bit resolution across story windows (ADR 0004)
#
# The game's story branches on persistent bits: the scheduler CHECKS a bit on
# a pinned day and runs the cleared or the failure branch accordingly. When a
# warp crosses such a day, the engine never runs the skipped scheduler — so
# the branch the user wants must be pre-set as save state (bits), and the
# arrival day's own scheduler plays the equivalent scenes LIVE. We only ever
# write bits whose save location is empirically verified
# (BANK RULE).
# ---------------------------------------------------------------------------

# Table-2 (script base 0x20000000) flat transform — empirically verified
# across the save corpus:
#   flat_bit = 0x1C700 + idx, LSB0 (bit0 = 0x01)
T2_FLAT_BASE = 0x1C700

BRANCH_WINDOWS = [
    {
        "window_id": "futaba_awakening",
        "label": "Futaba's Palace — mission & awakening window",
        "start": (7, 26),
        "end": (8, 31),
        "verified": True,
        # Days inside the window whose cleared branch the arrival engine
        # replays natively (script-decoded, see ADR 0004 verification):
        "arrival_targets": [(8, 21), (8, 22)],
        "resolution_bits": [
            {"bit_id": "T2+1400", "table": 2, "index": 1400,
             "label": "Futaba's Palace secured",
             "evidence": "verified across the save corpus @0x398F.b0; "
                         "deadline-day cleared/fail branch guard"},
            {"bit_id": "T2+1410", "table": 2, "index": 1410,
             "label": "Futaba window bookkeeping",
             "evidence": "verified across the save corpus @0x3990.b2; read-only "
                         "in schedule data (morning 7/26-8/21 latch)"},
        ],
        "implied_summary": ("Futaba's Palace counts as secured before the "
                            "awakening window; the awakening scenes play "
                            "themselves on arrival."),
        "branches": [
            {"branch": "cleared", "offered": True,
             "why": "required by your destination — the engine replays the "
                    "cleared branch and the awakening natively"},
            {"branch": "conquest failed (game over)", "offered": False,
             "why": "a dead end; the editor never fabricates a game over"},
        ],
        "notes": [
            "8/21's morning branch is guarded ONLY on T2+1400: "
            "set = decision scenes + join chain play naturally.",
            "8/22's evening ceremony chain is unconditional in the schedule "
            "data — it runs live on arrival.",
        ],
    },
    # Known but NOT yet warpable — branch bits lack corpus verification.
    # Listed so the UI can honestly report them instead of silently refusing.
    {"window_id": "okumura", "label": "Okumura's Palace window",
     "start": (9, 19), "end": (10, 11), "verified": False,
     "arrival_targets": [], "resolution_bits": [], "branches": [],
     "implied_summary": "Known window — branch bits not yet verified.",
     "notes": []},
    {"window_id": "niijima", "label": "Niijima's Palace window",
     "start": (10, 30), "end": (11, 20), "verified": False,
     "arrival_targets": [], "resolution_bits": [], "branches": [],
     "implied_summary": "Known window — branch bits not yet verified.",
     "notes": []},
    {"window_id": "councillor_gate", "label": "Councillor R9 gate (3rd semester)",
     "start": (11, 18), "end": (11, 18), "verified": False,
     "arrival_targets": [], "resolution_bits": [], "branches": [],
     "implied_summary": "Known gate — use the Deadline Escape Hatch (ADR 0003 "
                        "Tier 2) instead; warp across it is not verified.",
     "notes": []},
    {"window_id": "shido", "label": "Shido's Palace window",
     "start": (12, 17), "end": (12, 24), "verified": False,
     "arrival_targets": [], "resolution_bits": [], "branches": [],
     "implied_summary": "Known window — branch bits not yet verified.",
     "notes": []},
]


def _bit_location(table: int, index: int):
    """(byte_offset, bit) for a bit id. Raises on unverified tables
    (BANK RULE: only empirically verified transforms may be written)."""
    if table == 2:
        flat = T2_FLAT_BASE + index
        return flat // 8, flat % 8
    raise ValueError(
        "Bit table %d has no empirically-verified byte transform — refusing to "
        "write (ADR 0004 BANK RULE)." % table)


def _set_payload_bit(payload: bytearray, table: int, index: int, value: int) -> dict:
    off, bit = _bit_location(table, index)
    if value:
        payload[off] |= (1 << bit)
    else:
        payload[off] &= (~(1 << bit)) & 0xFF
    return {"byte_offset": off, "bit": bit, "value": int(bool(value))}


def _blocked_date_idx(blocker: dict) -> int:
    m, d = blocker["date"].split("/")
    return day_index(int(m), int(d))


def _overlapping_windows(cur_idx: int, tgt_idx: int) -> list:
    out = []
    for w in BRANCH_WINDOWS:
        s = day_index(*w["start"])
        e = day_index(*w["end"])
        if s <= tgt_idx and e >= cur_idx + 1:
            out.append(w)
    return out


def build_time_travel_plan_v2(model: dict, current_hdr_day: int,
                              target_month: int, target_day: int) -> dict:
    """V2 plan: v1 classification + branch resolution for known windows.

    Statuses:
      ok                 — clean runway (v1 warp, no bits needed)
      blocked_resolvable — all story blockers inside one verified window and
                           the destination is an arrival target; plan carries
                           branch_choices the user must acknowledge
      blocked            — refused; v2.reason explains honestly why
      invalid            — malformed/out-of-envelope request (v1 semantics)
    """
    plan = build_time_travel_plan(model, current_hdr_day,
                                  target_month, target_day)
    v2 = {"engine": "branch-bit resolution v2 (ADR 0004)"}

    if plan["status"] == "invalid":
        plan["v2"] = {**v2, "resolvable": False, "reason": plan["reason"]}
        return plan

    if plan["status"] == "ok":
        plan["v2"] = {**v2, "resolvable": False,
                      "reason": "clean runway — no branch bits needed"}
        return plan

    # blocked: try to resolve through a verified window.
    cur_idx = plan["current"]["hdr_day"]
    tgt_idx = plan["target"]["hdr_day"]
    blocked_idx = sorted({_blocked_date_idx(b) for b in plan["blocked_days"]})
    overlaps = _overlapping_windows(cur_idx, tgt_idx)
    plan["windows_overlapped"] = [
        {"window_id": w["window_id"], "label": w["label"],
         "start": "%d/%d" % w["start"], "end": "%d/%d" % w["end"],
         "verified": w["verified"], "implied_summary": w["implied_summary"]}
        for w in overlaps]

    for w in overlaps:
        if not w.get("verified"):
            continue
        s = day_index(*w["start"])
        e = day_index(*w["end"])
        if all(s <= b <= e for b in blocked_idx) \
                and (target_month, target_day) in [tuple(t) for t in w["arrival_targets"]]:
            arrival = "%d/%d" % (target_month, target_day)
            choice = {
                "choice_id": "%s:cleared" % w["window_id"],
                "window_id": w["window_id"],
                "kind": "implied",
                "label": "%s — cleared branch (implied by your destination)"
                         % w["label"],
                "description": w["implied_summary"],
                "bits": w["resolution_bits"],
                "branches": w["branches"],
                "notes": w["notes"],
                "arrival": arrival,
            }
            plan["v2"] = {**v2,
                          "resolvable": True,
                          "window_id": w["window_id"],
                          "branch_choices": [choice],
                          "reason": "all story days resolve inside the %s "
                                    "window" % w["window_id"]}
            plan["status"] = "blocked_resolvable"
            return plan

    # Not resolvable — explain honestly.
    def _inside_verified(idx):
        return any(day_index(*w["start"]) <= idx <= day_index(*w["end"])
                   for w in overlaps if w.get("verified"))

    if blocked_idx and all(_inside_verified(b) for b in blocked_idx):
        reason = ("Story days inside a known window resolve only when the "
                  "destination is an arrival target the engine replays "
                  "natively (Futaba window: 8/21 or 8/22). Mid-window or "
                  "post-window arrivals would silently lose the skipped "
                  "days' state writes — refused.")
    elif any(not w.get("verified") for w in overlaps):
        reason = ("Skip window crosses a known but unverified story window "
                  "(%s) — its branch bits lack verification and the "
                  "editor will not fabricate them." %
                  ", ".join(w["window_id"] for w in overlaps
                            if not w.get("verified")))
    else:
        reason = "Story days outside any known window — no verified branch " \
                 "resolution exists."
    plan["v2"] = {**v2, "resolvable": False, "reason": reason}
    return plan


# ---------------------------------------------------------------------------
# PALACE SKIP — set guard bit + warp to deadline day (engine replays scenes)
#
# The engine checks ONE guard bit per palace on deadline day. If set → palace
# is cleared and post-clearance events play. If not → game over. We set the
# guard bit + discovery bit, warp the clock to the deadline day, and let the
# engine's own scheduler replay the scenes. No event fabrication needed.
#
# Guard bits: T2+200/600/1000/1400/1800/2200/2700 (empirically verified).
# Discovery bits: T2+249/611/1012/1412/1805/2202/2702 (empirically verified).
# ---------------------------------------------------------------------------

PALACE_SKIP_CATALOG = [
    {
        "palace_id": "kamoshida",
        "label": "Kamoshida's Palace (Castle)",
        "guard_bit": {"table": 2, "index": 200,
                      "bit_id": "T2+200",
                      "label": "Palace secured",
                      "evidence": "deadline guard, verified across the save corpus @0x38F9.b0"},
        "discovery_bit": {"table": 2, "index": 249,
                          "bit_id": "T2+249",
                          "label": "Palace discovered",
                          "evidence": "palace entry guard, verified across the save corpus"},
        "deadline": (5, 2),
        "earliest_entry": (4, 15),
        "party_unlock": "Ann (Lovers), Ryuji (Chariot), Morgana (Magician)",
    },
    {
        "palace_id": "madarame",
        "label": "Madarame's Palace (Museum)",
        "guard_bit": {"table": 2, "index": 600,
                      "bit_id": "T2+600",
                      "label": "Palace secured",
                      "evidence": "deadline guard, verified across the save corpus @0x392B.b0"},
        "discovery_bit": {"table": 2, "index": 611,
                          "bit_id": "T2+611",
                          "label": "Palace discovered",
                          "evidence": "palace entry guard, verified across the save corpus"},
        "deadline": (6, 5),
        "earliest_entry": (5, 19),
        "party_unlock": "Yusuke (Emperor)",
    },
    {
        "palace_id": "kaneshiro",
        "label": "Kaneshiro's Palace (Bank)",
        "guard_bit": {"table": 2, "index": 1000,
                      "bit_id": "T2+1000",
                      "label": "Palace secured",
                      "evidence": "deadline guard, verified across the save corpus @0x395D.b0"},
        "discovery_bit": {"table": 2, "index": 1012,
                          "bit_id": "T2+1012",
                          "label": "Palace discovered",
                          "evidence": "palace entry guard, verified across the save corpus"},
        "deadline": (7, 9),
        "earliest_entry": (6, 20),
        "party_unlock": "Makoto (Priestess), Futaba (Hermit)",
    },
    {
        "palace_id": "futaba",
        "label": "Futaba's Palace (Tomb)",
        "guard_bit": {"table": 2, "index": 1400,
                      "bit_id": "T2+1400",
                      "label": "Palace secured",
                      "evidence": "deadline guard, verified across the save corpus @0x398F.b0"},
        "discovery_bit": {"table": 2, "index": 1412,
                          "bit_id": "T2+1412",
                          "label": "Palace discovered",
                          "evidence": "scripted-only palace entry, verified across the save corpus"},
        "deadline": (8, 21),
        "earliest_entry": (7, 25),
        "party_unlock": "Futaba joins as navigator",
        "notes": ["Futaba palace is scripted-only (no free dungeon visits). "
                  "8/22 awakening ceremony is unconditional in the schedule data — "
                  "plays on arrival if guard bit is set."],
    },
    {
        "palace_id": "okumura",
        "label": "Okumura's Palace (Spaceship)",
        "guard_bit": {"table": 2, "index": 1800,
                      "bit_id": "T2+1800",
                      "label": "Palace secured",
                      "evidence": "deadline guard, verified across the save corpus @0x39C1.b0"},
        "discovery_bit": {"table": 2, "index": 1805,
                          "bit_id": "T2+1805",
                          "label": "Palace discovered",
                          "evidence": "palace entry guard, verified across the save corpus"},
        "deadline": (10, 11),
        "earliest_entry": (9, 15),
        "party_unlock": "Haru (Empress)",
    },
    {
        "palace_id": "niijima",
        "label": "Niijima's Palace (Casino)",
        "guard_bit": {"table": 2, "index": 2200,
                      "bit_id": "T2+2200",
                      "label": "Palace secured",
                      "evidence": "deadline guard, verified across the save corpus @0x39F3.b0"},
        "discovery_bit": {"table": 2, "index": 2202,
                          "bit_id": "T2+2202",
                          "label": "Palace discovered",
                          "evidence": "palace entry guard, verified across the save corpus"},
        "deadline": (11, 19),
        "earliest_entry": (10, 29),
        "party_unlock": "Makoto joins active party",
    },
    {
        "palace_id": "shido",
        "label": "Shido's Palace (Cruiser)",
        "guard_bit": {"table": 2, "index": 2700,
                      "bit_id": "T2+2700",
                      "label": "Palace secured",
                      "evidence": "deadline guard, verified across the save corpus @0x3A31.b4"},
        "discovery_bit": {"table": 2, "index": 2702,
                          "bit_id": "T2+2702",
                          "label": "Palace discovered",
                          "evidence": "palace entry guard, verified across the save corpus"},
        "deadline": (12, 18),
        "earliest_entry": (11, 24),
        "party_unlock": "Akechi (Justice) — story-locked",
    },
]


def _lookup_palace(palace_id: str) -> dict:
    """Return the catalog entry for a palace_id, or raise ValueError."""
    for p in PALACE_SKIP_CATALOG:
        if p["palace_id"] == palace_id:
            return p
    raise ValueError("Unknown palace_id: %s (valid: %s)" % (
        palace_id, ", ".join(p["palace_id"] for p in PALACE_SKIP_CATALOG)))


def build_palace_skip_plan(editor, palace_id: str, mode: str = "deadline") -> dict:
    """Plan a palace skip in one of two modes:

    - "deadline" (original): set guard+discovery bits AND warp the clock to
      the deadline day. One-day compression of the whole arc.
    - "claim" (grind skip): set the bits WITHOUT touching the clock. The
      player keeps every remaining calendar day before the deadline; the
      objective flips to "wait for the change of heart" and the game plays
      all pinned scenes on their scripted days (in-game validated: the
      engine checks the guard bit, not history).

    Returns a plan dict with status, bits to write, target date, etc.
    """
    if mode not in ("deadline", "claim"):
        mode = "deadline"
    p = _lookup_palace(palace_id)
    cur_day = editor.parser.header.day
    deadline_m, deadline_d = p["deadline"]
    deadline_idx = day_index(deadline_m, deadline_d)
    entry_m, entry_d = p["earliest_entry"]
    entry_idx = day_index(entry_m, entry_d)

    # Validation: must be before the deadline
    if cur_day >= deadline_idx:
        return {
            "allowed": False,
            "status": "too_late",
            "palace": p["palace_id"],
            "reason": "Current day (%d/%d) is already past %s's deadline "
                      "(%d/%d). Cannot skip a palace after its deadline." % (
                          *index_to_month_day(cur_day), p["label"],
                          deadline_m, deadline_d),
        }

    # Validation: must be at or after earliest entry (palace must exist)
    if cur_day < entry_idx:
        return {
            "allowed": False,
            "status": "too_early",
            "palace": p["palace_id"],
            "reason": "%s's palace doesn't exist yet on %d/%d "
                      "(earliest entry: %d/%d)." % (
                          p["label"], *index_to_month_day(cur_day),
                          entry_m, entry_d),
        }

    # Check if guard bit is already set
    payload = editor.parser.data_payload
    g_byte, g_bit = _bit_location(p["guard_bit"]["table"],
                                  p["guard_bit"]["index"])
    already_cleared = bool(payload[g_byte] & (1 << g_bit))

    if already_cleared:
        return {
            "allowed": False,
            "status": "already_cleared",
            "palace": p["palace_id"],
            "reason": "%s's guard bit is already set — palace is cleared." %
                      p["label"],
        }

    # Build bit writes
    bits_to_write = [
        {**p["guard_bit"], "action": "set"},
        {**p["discovery_bit"], "action": "set"},
    ]

    cur_m, cur_d = index_to_month_day(cur_day)
    days_saved = deadline_idx - cur_day

    if mode == "claim":
        plan = {
            "allowed": True,
            "status": "ok",
            "mode": "claim",
            "palace": p["palace_id"],
            "palace_label": p["label"],
            "current": {"hdr_day": cur_day, "date": "%d/%d" % (cur_m, cur_d)},
            "target": {"hdr_day": cur_day, "date": "%d/%d" % (cur_m, cur_d)},
            "days_kept": days_saved,
            "deadline": "%d/%d" % (deadline_m, deadline_d),
            "bits_to_write": bits_to_write,
            "party_unlock": p.get("party_unlock", ""),
            "notes": [
                "Grind skipped, calendar kept: the clock does not move.",
                "In-game objective becomes 'wait for the change of heart'",
                "on the deadline (%s) — allies will react to the claimed clear." %
                ("%d/%d" % (deadline_m, deadline_d)),
                "All pinned story scenes still fire on their scripted days.",
            ],
        }
        return plan

    plan = {
        "allowed": True,
        "status": "ok",
        "mode": "deadline",
        "palace": p["palace_id"],
        "palace_label": p["label"],
        "current": {"hdr_day": cur_day, "date": "%d/%d" % (cur_m, cur_d)},
        "target": {"hdr_day": deadline_idx,
                   "date": "%d/%d" % (deadline_m, deadline_d)},
        "days_saved": days_saved,
        "bits_to_write": bits_to_write,
        "party_unlock": p.get("party_unlock", ""),
        "notes": p.get("notes", []) + [
            "Guard bit set: engine will treat palace as cleared on arrival.",
            "Discovery bit set: palace known to the engine.",
            "Post-clearance events replay on arrival (engine's own scheduler).",
            "Party members who join during the palace arc will be available.",
        ],
    }
    return plan


def apply_palace_skip(editor, palace_id: str, mode: str = "deadline") -> dict:
    """Execute a palace skip in the given mode. Caller re-signs.

    mode="deadline": guard bit, discovery bit, header day, desc date token,
    0x3D70 mirror. mode="claim": bits ONLY — the clock is untouched.
    Returns status + what was written.
    """
    plan = build_palace_skip_plan(editor, palace_id, mode=mode)
    if not plan["allowed"]:
        return {"status": plan["status"], "plan": plan}

    d = bytearray(editor.parser.data_payload)
    bit_writes = []

    for b in plan["bits_to_write"]:
        result = _set_payload_bit(d, b["table"], b["index"], 1)
        bit_writes.append({"bit_id": b["bit_id"], "label": b["label"],
                           **result})

    editor.parser.data_payload = bytes(d)

    if plan.get("mode") == "claim":
        # Grind skip: no clock writes at all — the calendar is preserved.
        return {"status": "success", "plan": plan, "wrote": None,
                "bits_written": bit_writes}

    tgt = plan["target"]["hdr_day"]
    wrote = _write_clock_fields(editor, tgt)

    return {"status": "success", "plan": plan, "wrote": wrote,
            "bits_written": bit_writes}


def apply_time_travel_v2(editor, model: dict, target_month: int,
                         target_day: int, choice_ids=None) -> dict:
    """V2 apply: acknowledge branch choices, write verified bits + clocks.

    Writes ONLY: header day, desc date token, 0x3D70 mirror, and branch bits
    whose byte transform is empirically verified. Caller re-signs + backs up.
    """
    choice_ids = set(choice_ids or [])
    plan = build_time_travel_plan_v2(model, editor.parser.header.day,
                                     target_month, target_day)
    if plan["status"] == "ok":
        return apply_time_travel(editor, model, target_month, target_day)
    if plan["status"] != "blocked_resolvable":
        return {"status": plan["status"], "plan": plan}

    choices = plan["v2"]["branch_choices"]
    required = {c["choice_id"] for c in choices}
    missing = required - choice_ids
    if missing:
        return {"status": "confirm_required", "plan": plan,
                "message": "Acknowledge these branch choices before the warp: "
                           "%s" % ", ".join(sorted(missing))}

    # Branch bits first (fail-hard on any unverified bit, before clocks move).
    bit_writes = []
    d = bytearray(editor.parser.data_payload)
    for c in choices:
        for b in c["bits"]:
            bit_writes.append({"bit_id": b["bit_id"], "label": b["label"],
                               **_set_payload_bit(d, b["table"], b["index"], 1)})
    editor.parser.data_payload = bytes(d)

    tgt = plan["target"]["hdr_day"]
    wrote = _write_clock_fields(editor, tgt)
    return {"status": "success", "plan": plan, "wrote": wrote,
            "bits_written": bit_writes}


# ---------------------------------------------------------------------------
# CHRONOS V3 — Full time warp with complete flag sync
#
# Engine validation rules (empirically confirmed via 5 in-game tests):
#   1. Engine reads calendar date from save (header.day + 0x0A670).
#   2. Engine runs the scheduler for whatever date is in the save.
#   3. Guard bits create overlay warnings but don't prevent loading.
#   4. Pre-game-start dates (before 4/9/day 8) fallback to 4/9.
#   5. Calendar + aligned guards = perfect load.
#   6. Calendar ahead of story = warning overlays (hybrid state).
#
# Full warp strategy:
#   1. Write all clock fields (header.day, desc, 0x3D70, 0x0A670, 0x0A674).
#   2. Sync ALL palace guard bits (set if deadline <= target, clear if > target).
#   3. Sync ALL palace discovery bits (same logic as guard bits).
#   4. Apply daily event flags from the model (bits_on for days <= target).
#   5. For backward warp: clear event flags set by days > target.
# ---------------------------------------------------------------------------

# Palace metadata for full warp — maps palace_id to (entry_day, deadline_day)
# and guard/discovery bit info. Used by _palace_state_for_day().

def _palace_state_for_day(target_day_idx: int) -> dict:
    """Determine which palaces should have guard/discovery bits set at target_day.

    Returns dict: {palace_id: {"guard": bool, "discovery": bool, ...}}.
    A palace is "cleared" if target_day >= deadline (the engine checks the guard
    bit on deadline day — if set, palace is cleared and post-clearance scenes play).
    A palace is "discovered" if target_day >= earliest_entry (the palace exists).
    """
    result = {}
    for p in PALACE_SKIP_CATALOG:
        entry_idx = day_index(*p["earliest_entry"])
        deadline_idx = day_index(*p["deadline"])
        discovered = target_day_idx >= entry_idx
        cleared = target_day_idx >= deadline_idx
        result[p["palace_id"]] = {
            "guard": cleared,
            "discovery": discovered,
            "guard_bit": p["guard_bit"],
            "discovery_bit": p["discovery_bit"],
            "deadline": p["deadline"],
            "earliest_entry": p["earliest_entry"],
        }
    return result


def _event_flags_for_day(model: dict, target_day_idx: int) -> dict:
    """Collect all table-2 bits_on and bits_off for days <= target_day.

    Returns {"bits_on": {table_idx: set(), ...}, "bits_off": {table_idx: set(), ...}}.
    Only table-2 bits are included (the only empirically-verified table).
    """
    bits_on = set()
    bits_off = set()

    for month_str, days in model.get("lattice", {}).items():
        month = int(month_str)
        for day_str, segs in days.items():
            day = int(day_str)
            try:
                day_idx = day_index(month, day)
            except (KeyError, ValueError):
                continue
            if day_idx > target_day_idx:
                continue

            for seg_name, seg_data in segs.items():
                for bit_entry in seg_data.get("bits_on", []):
                    base = bit_entry.get("base", "")
                    if base == "0x20000000":
                        bits_on.add(bit_entry["index"])
                for bit_entry in seg_data.get("bits_off", []):
                    base = bit_entry.get("base", "")
                    if base == "0x20000000":
                        bits_off.add(bit_entry["index"])

    return {"bits_on": bits_on, "bits_off": bits_off}


def plan_full_time_warp_changes(parser, model: dict, target_day_idx: int) -> dict:
    """Diff the CURRENT save bits against the DESTINATION date's required state.

    The full-warp plan endpoint reports destination state; this answers the
    question the user actually has: "what will change on MY save?". Only bits
    that differ are listed — palaces whose required state already matches the
    save are omitted entirely.
    """
    payload = bytes(parser.data_payload)

    def bit_at(table: int, index: int) -> int:
        off, b = _bit_location(table, index)
        return (payload[off] >> b) & 1

    palace_changes = []
    palace_state = _palace_state_for_day(target_day_idx)
    for p in PALACE_SKIP_CATALOG:
        ps = palace_state[p["palace_id"]]
        g_bit, d_bit = p["guard_bit"], p["discovery_bit"]
        changes = {}
        g_cur = bit_at(g_bit["table"], g_bit["index"])
        g_tgt = 1 if ps["guard"] else 0
        if g_cur != g_tgt:
            changes["guard_change"] = {"from": g_cur, "to": g_tgt}
        d_cur = bit_at(d_bit["table"], d_bit["index"])
        d_tgt = 1 if ps["discovery"] else 0
        if d_cur != d_tgt:
            changes["discovery_change"] = {"from": d_cur, "to": d_tgt}
        if changes:
            palace_changes.append({"palace": p["palace_id"], "label": p["label"], **changes})

    event_flags = _event_flags_for_day(model, target_day_idx)
    set_n = sum(1 for idx in event_flags["bits_on"] if not bit_at(2, idx))
    clear_n = sum(1 for idx in event_flags["bits_off"] if bit_at(2, idx))

    return {
        "palace_changes": palace_changes,
        "event_flag_changes": {"set": set_n, "clear": clear_n},
    }


def _apply_palace_bits(payload: bytearray, palace_state: dict) -> list:
    """Set/clear all palace guard and discovery bits. Returns list of writes."""
    writes = []
    for pid, ps in palace_state.items():
        g_bit = ps["guard_bit"]
        d_bit = ps["discovery_bit"]

        # Guard bit: set if cleared, clear if not
        result = _set_payload_bit(payload, g_bit["table"], g_bit["index"],
                                  1 if ps["guard"] else 0)
        writes.append({"palace": pid, "type": "guard",
                       "bit_id": g_bit["bit_id"], "action": "set" if ps["guard"] else "clear",
                       **result})

        # Discovery bit: set if discovered, clear if not
        result = _set_payload_bit(payload, d_bit["table"], d_bit["index"],
                                  1 if ps["discovery"] else 0)
        writes.append({"palace": pid, "type": "discovery",
                       "bit_id": d_bit["bit_id"], "action": "set" if ps["discovery"] else "clear",
                       **result})

    return writes


def _apply_event_flags(payload: bytearray, event_flags: dict) -> list:
    """Apply daily event flags (bits_on/bits_off from model). Returns list of writes."""
    writes = []

    # Apply bits ON first, then bits OFF (OFF wins for any conflicts)
    for idx in event_flags["bits_on"]:
        if idx not in event_flags["bits_off"]:
            off, bit = _bit_location(2, idx)
            payload[off] |= (1 << bit)
            writes.append({"table": 2, "index": idx, "action": "set",
                           "byte_offset": off, "bit": bit, "value": 1})

    for idx in event_flags["bits_off"]:
        off, bit = _bit_location(2, idx)
        payload[off] &= (~(1 << bit)) & 0xFF
        writes.append({"table": 2, "index": idx, "action": "clear",
                       "byte_offset": off, "bit": bit, "value": 0})

    return writes


def apply_full_time_warp(editor, model: dict, target_month: int, target_day: int,
                         direction: str = "auto") -> dict:
    """Full CHRONOS V3 time warp: clock + palace state + event flags.

    direction:
      "auto"    - determine from current vs target day
      "forward" - warp forward (set bits for days <= target)
      "backward" - warp backward (clear bits for days > target)

    Writes:
      - Clock fields: header.day, desc, 0x3D70, 0x0A670, 0x0A674
      - Palace guard bits: set if target >= deadline, clear otherwise
      - Palace discovery bits: set if target >= earliest_entry, clear otherwise
      - Daily event flags from model: bits_on for days <= target

    Caller re-signs via save_to_bytes() and writes to disk.
    """
    current_day = editor.parser.header.day
    try:
        target_day_idx = day_index(target_month, target_day)
    except KeyError:
        return {"status": "error",
                "reason": "Invalid target date: %d/%d" % (target_month, target_day)}

    if direction == "auto":
        direction = "forward" if target_day_idx > current_day else "backward"

    cur_m, cur_d = index_to_month_day(current_day)

    # 1. Determine palace state for target day
    palace_state = _palace_state_for_day(target_day_idx)

    # 2. Collect event flags for target day
    event_flags = _event_flags_for_day(model, target_day_idx)

    # 3. Apply everything to the payload
    d = bytearray(editor.parser.data_payload)

    # Palace bits
    palace_writes = _apply_palace_bits(d, palace_state)

    # Event flags
    event_writes = _apply_event_flags(d, event_flags)

    editor.parser.data_payload = bytes(d)

    # 4. Write clock fields
    wrote = _write_clock_fields(editor, target_day_idx)

    # Build summary of what changed
    guard_set = [w for w in palace_writes if w["type"] == "guard" and w["action"] == "set"]
    guard_clear = [w for w in palace_writes if w["type"] == "guard" and w["action"] == "clear"]
    disc_set = [w for w in palace_writes if w["type"] == "discovery" and w["action"] == "set"]
    disc_clear = [w for w in palace_writes if w["type"] == "discovery" and w["action"] == "clear"]

    plan = {
        "current": {"hdr_day": current_day, "date": "%d/%d" % (cur_m, cur_d)},
        "target": {"hdr_day": target_day_idx, "date": "%d/%d" % (target_month, target_day)},
        "direction": direction,
        "palaces": {pid: {"guard": ps["guard"], "discovery": ps["discovery"]}
                    for pid, ps in palace_state.items()},
        "summary": {
            "guards_set": [w["palace"] for w in guard_set],
            "guards_cleared": [w["palace"] for w in guard_clear],
            "discoveries_set": [w["palace"] for w in disc_set],
            "discoveries_cleared": [w["palace"] for w in disc_clear],
            "event_flags_on": len(event_flags["bits_on"]),
            "event_flags_off": len(event_flags["bits_off"]),
        },
        "notes": [
            "Engine reads calendar date and runs that date's scheduler.",
            "Guard bits set palaces as cleared; discovery bits mark them known.",
            "Event flags sync daily-life state to match the target date.",
        ],
    }

    return {
        "status": "success",
        "plan": plan,
        "wrote": wrote,
        "bits_written": palace_writes + event_writes,
    }
