"""
High-Level Save Editor API for Persona 5 Royal (P5R)
Includes exclusive features: 3rd Semester Emergency Unlocker, Deep Romance Repair,
Stat De-Bloater / Normalizer, SteamID Re-Binder, and Compendium / Item Unlockers.
"""

import os
import re
import struct
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from .crypto import SaveContainer
from .parser import GameDataParser, SaveHeader, PlayerNameBlock
from .key_item_offsets import KEY_ITEM_OFFSET_BY_DB_ID


# Confidant Arcana Map
CONFIDANT_ARCANA_MAP = {
    "Fool": 0,
    "Magician": 1,
    "Priestess": 2,      # Makoto Niijima
    "Empress": 3,        # Haru Okumura
    "Emperor": 4,        # Yusuke Kitagawa
    "Hierophant": 5,     # Sojiro Sakura
    "Lovers": 6,         # Ann Takamaki
    "Chariot": 7,        # Ryuji Sakamoto
    "Justice": 8,        # Goro Akechi
    "Hermit": 9,         # Futaba Sakura
    "Fortune": 10,       # Chihaya Mifune
    "Strength": 11,      # Caroline & Justine / Lavenza
    "Hanged Man": 12,    # Munehisa Iwai
    "Death": 13,         # Tae Takemi
    "Temperance": 14,    # Sadayo Kawakami
    "Devil": 15,         # Ichiko Ohya
    "Tower": 16,         # Shinya Oda
    "Star": 17,          # Hifumi Togo
    "Moon": 18,          # Yuuki Mishima
    "Sun": 19,           # Toranosuke Yoshida
    "Judgement": 20,     # Sae Niijima
    "Faith": 21,         # Sumire / Kasumi Yoshizawa
    "Councillor": 22,    # Takuto Maruki
}

# Romanceable Confidant IDs
ROMANCEABLE_CONFIDANTS = [2, 3, 6, 9, 10, 13, 14, 15, 17, 21]


class SaveEditor:
    """Main high-level editor wrapper over SaveContainer and GameDataParser."""

    def __init__(self, raw_buffer: Optional[bytes] = None):
        self.container = SaveContainer()
        self.parser = GameDataParser()
        self.loaded = False

        if raw_buffer:
            self.load_from_bytes(raw_buffer)

    # Staging buffer for S1 inventory edits (INVENTORY_SPEC.md S1 #2):
    # None = no staged changes; dict = staged inventory delta. Payload bytes
    # are NOT mutated until commit_staged_inventory(). Server calls
    # stage_* methods on load, then commit on save.
    _staged_inventory: Optional[Dict[str, Any]] = None

    def _ensure_staged(self):
        if self._staged_inventory is None:
            self._staged_inventory = {"stacks": {}, "owned_gear": {},
                                       "unknown": [], "conflicts": [],
                                       "mirror_mismatches": []}

    def _staged_get_normalized(self) -> Dict[str, Any]:
        """Normalized view merged with staged changes (if any)."""
        base = self.get_normalized_inventory()
        if not self._staged_inventory:
            return base
        merged = {"owned_gear": dict(base.get("owned_gear", {})),
                  "stacks": dict(base.get("stacks", {})),
                  "key_flags": dict(base.get("key_flags", {})),
                  "unknown": list(base.get("unknown", [])),
                  "conflicts": list(base.get("conflicts", [])),
                  "mirror_mismatches": list(base.get("mirror_mismatches", []))}
        for k, v in self._staged_inventory.get("stacks", {}).items():
            if v is None or v <= 0:
                merged["stacks"].pop(k, None)
            else:
                merged["stacks"][k] = max(0, min(int(v), 99))
        for k, v in self._staged_inventory.get("owned_gear", {}).items():
            merged["owned_gear"][k] = bool(v)
        return merged

    def stage_set_stack(self, item_id: int, quantity: int) -> Dict[str, Any]:
        """Stage a stack quantity (0..99) — does NOT touch payload bytes."""
        if not self.is_real_save():
            return {"status": "noop"}
        if self.get_item_count_offset(item_id) == 0:
            return {"status": "invalid",
                    "message": f"Item 0x{item_id:04X} is not a stack type (gear/key)."}
        self._ensure_staged()
        q = max(0, min(int(quantity), 99))
        if q == 0:
            self._staged_inventory["stacks"][item_id] = 0  # deletion marker
        else:
            self._staged_inventory["stacks"][item_id] = q
        return {"status": "staged", "item_id": item_id, "quantity": q}

    def stage_set_owned(self, item_id: int, owned: bool) -> Dict[str, Any]:
        """Stage an owned-flag toggle — does NOT touch payload bytes."""
        if not self.is_real_save():
            return {"status": "noop"}
        off = self.get_item_owned_offset(item_id)
        if off == 0 and (item_id & 0xF000) == 0x7000:
            return {"status": "unsupported",
                    "message": f"Ranged item 0x{item_id:04X} not in verified map — refusing."}
        if off == 0:
            return {"status": "invalid",
                    "message": f"Item 0x{item_id:04X} is not ownable gear."}
        self._ensure_staged()
        self._staged_inventory["owned_gear"][item_id] = bool(owned)
        return {"status": "staged", "item_id": item_id, "owned": bool(owned)}

    def commit_staged_inventory(self) -> Dict[str, Any]:
        """Flush staged inventory delta to payload bytes + mirrors.

        Writes count bytes + mirrors and owned-flag bytes + mirrors. Clears
        staged buffer on success.
        """
        if not self.is_real_save() or not self._staged_inventory:
            return {"status": "noop"}
        d = bytearray(self.parser.data_payload)
        delta = self.PC31_MIRROR_DELTA
        applied = 0
        for iid, qty in list(self._staged_inventory.get("stacks", {}).items()):
            off = self.get_item_count_offset(iid)
            if off and off < len(d):
                q = 0 if qty is None else max(0, min(int(qty), 99))
                d[off] = q
                mo = off + delta
                if mo < len(d):
                    d[mo] = q
                applied += 1
        for iid, owned in list(self._staged_inventory.get("owned_gear", {}).items()):
            off = self.get_item_owned_offset(iid)
            if off and off < len(d):
                d[off] = 1 if owned else 0
                mo = off + delta
                if mo < len(d):
                    d[mo] = 1 if owned else 0
                applied += 1
        self.parser.data_payload = bytes(d)
        self._staged_inventory = None
        return {"status": "success", "applied": applied}

    def discard_staged_inventory(self):
        self._staged_inventory = None

    def load_from_bytes(self, raw_buffer: bytes):
        """Unpack raw binary save bytes."""
        self._raw_buffer = raw_buffer
        self.container.unpack_raw(raw_buffer)
        self.parser.unpack(self.container.header_bytes, self.container.data_bytes)
        self.loaded = True
        self._staged_inventory = None

    def integrity_report(self) -> Dict[str, Any]:
        """
        Verify the loaded container's integrity envelope.

        Returns per-layer booleans: file_crc_ok (outer), data_crc_ok (inner),
        aes_ok (encryption flag present) and a top-level 'ok' that is True
        only when all three pass. Never raises; reports what is found.
        """
        from .crypto import calc_crc

        report = {"file_crc_ok": None, "data_crc_ok": None, "aes_ok": None, "ok": False}
        if not self.loaded:
            return report

        raw = getattr(self, "_raw_buffer", b"")
        c = self.container
        try:
            if raw:
                computed = calc_crc(raw[0x8:])
                report["file_crc_ok"] = computed == c.file_crc
            else:
                report["file_crc_ok"] = False
        except Exception:
            report["file_crc_ok"] = False

        try:
            report["data_crc_ok"] = calc_crc(c.data_bytes) == c.data_crc
        except Exception:
            report["data_crc_ok"] = False

        report["aes_ok"] = bool(c.file_flags & (1 << 31))
        report["ok"] = all(v is True for v in
                           (report["file_crc_ok"], report["data_crc_ok"], report["aes_ok"]))
        return report

    # Story-calendar guardrails (verified guide data, 2026-08-14):
    # Faith (Kasumi) caps at rank 5 until the 3rd semester (January).
    # Councillor (Maruki) must reach rank 9 before Nov 18 or 3rd semester
    # locks; he is unavailable after that date.
    STORY_CAPS = {
        # arcana name -> (calendar limit, max rank before that limit)
        "Faith":      ("January (3rd semester start)", 5),
        "Councillor": ("Nov 18 (Maruki deadline)",     9),
    }

    def _game_date(self) -> Optional[Tuple[int, int]]:
        """Return (month, day) from the header quick-info, or None."""
        qi = self.get_quick_info()
        day_str = qi.get("day") or ""
        import re
        m = re.match(r"(\d+)/(\d+)", day_str)
        if not m:
            return None
        return int(m.group(1)), int(m.group(2))

    def confidant_guardrails(self, name: str, rank: int) -> List[str]:
        """
        Return human-readable warnings for a confidant rank that the current
        in-game calendar would reject or that soft-locks story progress.
        Pure advisory — the caller decides whether to block or clamp.
        """
        warnings: List[str] = []
        if name not in self.STORY_CAPS or rank <= 0:
            return warnings

        date = self._game_date()
        if date is None:
            return warnings

        month, day = date
        label, max_before = self.STORY_CAPS[name]

        if name == "Faith":
            # 3rd semester starts January (game year 20XX+1). Months 1-3 = ok.
            in_third_semester = month <= 3
            if rank > max_before and not in_third_semester:
                warnings.append(
                    f"Faith (Kasumi): rank {rank} is impossible now — she caps at "
                    f"rank {max_before} until {label}. The game will ignore the "
                    f"excess until the story reveal."
                )
        elif name == "Councillor":
            past_deadline = (month == 11 and day > 18) or month == 12 or month <= 3
            if past_deadline and rank < 9:
                warnings.append(
                    "Councillor (Maruki): after Nov 18 his confidant is closed. "
                    "Rank 9 by Nov 18 is REQUIRED for the 3rd semester — if you "
                    "missed it, use the '3rd Semester Emergency Rescue Tool'."
                )
            if rank > 9 and not past_deadline:
                # rank 10 is fine pre-deadline; nothing to warn
                pass
        return warnings

    # -------------------------------------------------------------------------
    # Compendium registration bitmask — LOCATED 2026-08-14 via oracle-guided
    # bit-aligned ladder scan (DeepSeek Q6 + Gemini verdict, verified against
    # 7 saves + 100% NG++ oracle).
    #
    # PC31_OFFSET_COMPENDIUM = 0x09973 (mirror @ +0x18510 = 0x21E83).
    # Layout: 232-bit LSB-first bitmask, bit index i (0-based) = persona
    # save-ID (i + 1). Verified: 217/217 set bits map to valid persona IDs;
    # mask grows 0 (April) -> 33 (June 15) -> 217 (oracle) -> 224 (clear
    # data); strictly monotone within a playthrough; resets per NG+ cycle.
    # -------------------------------------------------------------------------
    PC31_OFFSET_COMPENDIUM = 0x09973
    PC31_COMPENDIUM_MIRROR = 0x21E83
    PC31_COMPENDIUM_BITS = 232  # 29-byte primary registration bitmask
    PC31_COMPENDIUM_MAX_ID = 437  # Max persona ID in Royal templates
    PC31_COMPENDIUM_ARRAY_BASE = 0x04270
    PC31_COMPENDIUM_ARRAY_MIRROR = 0x1C780
    PC31_COMPENDIUM_STRIDE = 0x30

    _COMPENDIUM_TEMPLATES_CACHE = {}

    def _load_compendium_templates(self) -> Dict[int, bytes]:
        if SaveEditor._COMPENDIUM_TEMPLATES_CACHE:
            return SaveEditor._COMPENDIUM_TEMPLATES_CACHE
        import json
        import sys as _sys
        result: Dict[int, bytes] = {}
        candidates = []
        if getattr(_sys, "frozen", False):
            candidates.append(os.path.join(getattr(_sys, "_MEIPASS", ""), "data", "compendium_templates.json"))
        candidates.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "compendium_templates.json"))
        for path in candidates:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    for k, v in data.items():
                        result[int(k)] = bytes.fromhex(v)
                    if result:
                        break
                except Exception:
                    pass
        if result:
            SaveEditor._COMPENDIUM_TEMPLATES_CACHE = result
        return result
    # Bits the game NEVER sets in any verified save (12-save corpus + the
    # game's OWN NAME.TBL marking these entries RESERVE/??? — 2026-08-16).
    PC31_COMPENDIUM_DEAD_BITS = {0x001, 0x0D8, 0x0DA, 0x0DB, 0x0DC, 0x0DD, 0x0DE, 0x0E0}
    # Personas whose registration BIT is set in genuine 100% saves but that have
    # NO 48-byte struct in the array ("mask-only" entries). Writing a struct here
    # produces a greyed/ghost compendium entry (slot index != pid-1 mismatch).
    # VERIFIED 2026-08-19 against Buff Joker NG++ + GameBanana all-items saves:
    # slot 210 (pid 0xD3 / 211) is 0x00 there, but the 0xD3 mask bit IS set
    # (224/224 genuine). Keep the bit, skip the struct.
    PC31_COMPENDIUM_MASK_ONLY_IDS = {0xD3, }  # decimal 211 = Satanael's phantom key

    @property
    def compendium_unlockable_ids(self) -> list:
        """Persona IDs the compendium unlocker may register."""
        templates = self._load_compendium_templates()
        royal_pids = set(templates.keys())
        base_unlockable = set(i for i in range(1, self.PC31_COMPENDIUM_BITS + 1)
                              if i not in self.PC31_COMPENDIUM_DEAD_BITS)
        return sorted(list((base_unlockable | royal_pids) - self.PC31_COMPENDIUM_DEAD_BITS))

    def get_compendium(self) -> Dict[str, Any]:
        """
        Read the compendium registration bitmask & struct table (PC 0x31 saves).

        Returns {'registered': [persona_ids...], 'count': N}.
        """
        out: Dict[str, Any] = {"supported": False, "registered": [], "count": 0}
        if not self.is_real_save():
            return out
        d = self.parser.data_payload
        base = self.PC31_OFFSET_COMPENDIUM
        nbytes = (self.PC31_COMPENDIUM_BITS + 7) // 8
        if len(d) < base + nbytes:
            return out
        out["supported"] = True
        reg = set()
        # 1. Read 1..232 from registration bitmask
        for i in range(self.PC31_COMPENDIUM_BITS):
            pid = i + 1
            if pid in self.PC31_COMPENDIUM_DEAD_BITS:
                continue
            byte = d[base + i // 8]
            bit = i % 8
            if (byte >> bit) & 1:
                reg.add(pid)

        # 2. Also check populated struct records for Royal/DLC personas up to 437
        for slot in range(self.PC31_COMPENDIUM_MAX_ID):
            pid = slot + 1
            if pid in self.PC31_COMPENDIUM_DEAD_BITS:
                continue
            off = self.PC31_COMPENDIUM_ARRAY_BASE + slot * self.PC31_COMPENDIUM_STRIDE
            if off + self.PC31_COMPENDIUM_STRIDE <= len(d):
                # If struct contains a non-zero persona ID and level
                stored_pid = struct.unpack_from("<H", d, off + 2)[0] if off + 4 <= len(d) else 0
                if stored_pid == pid:
                    reg.add(pid)

        out["registered"] = sorted(list(reg))
        out["count"] = len(out["registered"])
        return out

    def set_compendium_registration(self, persona_id: int, registered: bool) -> Dict[str, Any]:
        """
        Set one persona's compendium registration bit and 48-byte record struct.
        """
        if not self.is_real_save():
            return {"status": "unsupported", "message": "Not a PC (0x31) save."}
        if not (1 <= persona_id <= self.PC31_COMPENDIUM_MAX_ID):
            return {"status": "unsupported",
                    "message": f"Persona ID 0x{persona_id:03X} is outside valid compendium range (1..{self.PC31_COMPENDIUM_MAX_ID})."}
        if persona_id in self.PC31_COMPENDIUM_DEAD_BITS:
            if registered:
                return {"status": "invalid",
                        "message": f"Persona 0x{persona_id:03X} is a reserved/dead compendium entry — cannot be registered."}
        d = bytearray(self.parser.data_payload)
        
        # 1. Update Bitmasks (for IDs 1..232)
        if 1 <= persona_id <= self.PC31_COMPENDIUM_BITS:
            idx = persona_id - 1
            byte = idx // 8
            bit = idx % 8
            for base in (self.PC31_OFFSET_COMPENDIUM, self.PC31_COMPENDIUM_MIRROR):
                if base + byte < len(d):
                    if registered:
                        d[base + byte] |= (1 << bit)
                    else:
                        d[base + byte] &= ~(1 << bit)

        # 2. Update 48-byte Compendium Record Structs (for all IDs up to 437)
        templates = self._load_compendium_templates()
        template = templates.get(persona_id)
        idx = persona_id - 1
        for arr_base in (self.PC31_COMPENDIUM_ARRAY_BASE, self.PC31_COMPENDIUM_ARRAY_MIRROR):
            off = arr_base + idx * self.PC31_COMPENDIUM_STRIDE
            if off + self.PC31_COMPENDIUM_STRIDE <= len(d):
                if registered:
                    if template:
                        d[off : off + self.PC31_COMPENDIUM_STRIDE] = template
                else:
                    d[off : off + self.PC31_COMPENDIUM_STRIDE] = b"\x00" * self.PC31_COMPENDIUM_STRIDE

        self.parser.data_payload = bytes(d)
        return {"status": "success", "persona_id": persona_id,
                "registered": registered,
                "message": f"Persona 0x{persona_id:03X} {'registered' if registered else 'unregistered'} in compendium (bitmasks & struct arrays)."}

    def unlock_compendium_100(self) -> Dict[str, Any]:
        """
        Register ALL 232 personas in the compendium (PC 0x31 saves)
        by writing both the 232-bit registration bitmasks and all 48-byte persona records.
        """
        if not self.is_real_save():
            if 0x10020 in self.parser.blocks_raw:
                raw = bytearray(b"\xFF" * len(self.parser.blocks_raw[0x10020]))
                self.parser.blocks_raw[0x10020] = bytes(raw)
                return {"status": "success", "message": "Compendium 100% unlocked (legacy block)."}
            return {"status": "unsupported",
                    "message": "Compendium registration is not mapped on this payload version."}
        d = bytearray(self.parser.data_payload)
        nbytes = (self.PC31_COMPENDIUM_BITS + 7) // 8
        if len(d) < self.PC31_COMPENDIUM_MIRROR + nbytes:
            return {"status": "noop", "message": "Payload too short for compendium block."}
        unlockable = self.compendium_unlockable_ids  # 195 ids (232 - 37 dead)
        
        # 1. Update Bitmasks (both primary and mirror) across full Royal range
        templates = self._load_compendium_templates()
        royal_pids = set(templates.keys())
        all_unlockable = set(unlockable) | royal_pids

        for base in (self.PC31_OFFSET_COMPENDIUM, self.PC31_COMPENDIUM_MIRROR):
            for pid in all_unlockable:
                idx = pid - 1
                if base + idx // 8 < len(d):
                    d[base + idx // 8] |= (1 << (idx % 8))
            for pid in self.PC31_COMPENDIUM_DEAD_BITS:
                idx = pid - 1
                if base + idx // 8 < len(d):
                    d[base + idx // 8] &= ~(1 << (idx % 8))

        # 2. Populate Compendium Struct Arrays (both primary 0x04270 and mirror 0x1C780)
        # Strictly populate ONLY authentic summonable persona templates (231 verified Royal records).
        # Unsummonable/RESERVE slots remain pristine 0x00.
        for arr_base, gap_start, gap_end in (
            (self.PC31_COMPENDIUM_ARRAY_BASE, 0x09460, 0x09940),
            (self.PC31_COMPENDIUM_ARRAY_MIRROR, 0x21970, 0x21E50)
        ):
            # Sanitize the gap between slot 436 and slot 463 to pristine zeroes
            if gap_end <= len(d):
                d[gap_start:gap_end] = b"\x00" * (gap_end - gap_start)

            # Clear all unverified slots in the struct array to 0x00, and populate verified templates
            for slot in range(437):
                pid = slot + 1
                off = arr_base + slot * self.PC31_COMPENDIUM_STRIDE
                if off + self.PC31_COMPENDIUM_STRIDE <= len(d):
                    if pid in templates and (pid in all_unlockable) and (pid not in self.PC31_COMPENDIUM_MASK_ONLY_IDS):
                        d[off : off + self.PC31_COMPENDIUM_STRIDE] = templates[pid]
                    else:
                        d[off : off + self.PC31_COMPENDIUM_STRIDE] = b"\x00" * self.PC31_COMPENDIUM_STRIDE

        self.parser.data_payload = bytes(d)
        return {"status": "success", "unlocked_count": len([p for p in all_unlockable if p in templates]),
                "message": f"Compendium 100% unlocked across bitmasks & struct tables."}

    def save_to_bytes(self, compress: bool = True, encrypt: bool = True) -> bytes:
        """Repack, compress, encrypt, and resign save bytes."""
        header_b, data_b = self.parser.pack()
        self.container.header_bytes = header_b
        self.container.data_bytes = data_b
        return self.container.pack_raw(compress=compress, encrypt=encrypt)

    # -------------------------------------------------------------------------
    # Native PC (0x31) payload offsets — fully verified (2026-08-06)
    # -------------------------------------------------------------------------
    # NOTE (2026-08-08, 2-save diff VERIFIED): quick-info fields (day/playtime/
    # level) live in the container HEADER text block (~0x93) as
    # "6/14(Tue) Evening,Leblanc\nPLV:22 K\nPLAY TIME:22h 47m\nDIFFICULTY:Normal".
    # The old payload offsets 0x2C/0x30/0x38/0x3C are RETIRED garbage
    # (0x2C is actually Joker HP u16 = 256, which produced the fake "day 256").
    PC31_OFFSET_MONEY = 0x35C0      # u32 (authoritative game payload) — VERIFIED
    # NOTE: 0x3C (0x2C+0x10) is Joker's character EXP (u32), NOT a money mirror!
    # Writing money to 0x3C corrupts Joker's EXP and causes instant Lv99.
    # Money lives strictly at 0x35C0.
    # Social stats: 5x u16 LE POINTS (not ranks!) at 0x139E0, order:
    # [Knowledge, Charm, Proficiency, Guts, Kindness] — VERIFIED via 2-save diff
    # (craft +3 Prof, plant +2 Kind matched the game's note system exactly).
    PC31_OFFSET_SOCIAL_STATS = 0x139E0
    PC31_SOCIAL_ORDER = ["Knowledge", "Charm", "Proficiency", "Guts", "Kindness"]
    # Points required to REACH each rank (rank 1 = 0). P5R values (wiki-verified).
    PC31_SOCIAL_THRESHOLDS = {
        "Knowledge":   [0, 34, 82, 126, 192],
        "Charm":       [0, 6, 52, 92, 132],
        "Proficiency": [0, 12, 34, 60, 87],
        "Guts":        [0, 11, 38, 68, 113],
        "Kindness":    [0, 14, 47, 92, 136],
    }
    # -------------------------------------------------------------------------
    # Confidant block — PC 0x31, VERIFIED IN-GAME 2026-08-09 via rank-ramp probe
    # -------------------------------------------------------------------------
    # 23 entries @ 0x136A0, 16-byte stride:
    #   [6 pad][u16 save_id][u16 rank][u16 points][4 pad]
    # Save IDs follow arcana order (Fool=1 .. Judgement=21); Royal additions
    # Faith=33, Councillor=35. Confirmed by probe ramp: user loaded the save and
    # read back ranks 1..10 per arcana, matching entry-for-entry.
    PC31_OFFSET_CONFIDANTS = 0x136A0
    PC31_CONFIDANT_STRIDE = 16
    PC31_CONFIDANT_ID_OFF = 6
    PC31_CONFIDANT_RANK_OFF = 8
    PC31_CONFIDANT_PTS_OFF = 10
    # arcana name -> save id(s). Verified in-game 2026-08-09: 1,2,6,7,8,9,12,14,
    # 19,33,35 (probe ramp on 6/14 save); 1..21,35,36 confirmed on a 100% NG++
    # save (buff joker, third-semester 2/3). FAITH is special: pre-reveal
    # (Kasumi) = 33, post-reveal (Sumire, third semester) = 36 — the game
    # renumbers her entry. Look up either.
    CONFIDANT_SAVE_ID = {
        "Fool": 1, "Magician": 2, "Priestess": 3, "Empress": 4, "Emperor": 5,
        "Hierophant": 6, "Lovers": 7, "Chariot": 8, "Justice": 9, "Hermit": 10,
        "Fortune": 11, "Strength": 12, "Hanged Man": 13, "Death": 14,
        "Temperance": 15, "Devil": 16, "Tower": 17, "Star": 18, "Moon": 19,
        "Sun": 20, "Judgement": 21, "Faith": [33, 36], "Councillor": 35,
    }

    # Per-arcana affinity-point thresholds for rank-up (community data,
    # r/Persona5 'Confident points required for level up' 2023 + wikiwiki.jp).
    # Values = points required to REACH that rank (range = midpoint used).
    # NOTE: half-point values exist because arcana-match (x1.5) can grant
    # non-integer effective points; stored save points are the integer total.
    CONFIDANT_POINT_THRESHOLDS = {
        "Death":       {2: 5, 3: 0, 4: 15, 5: 20, 6: 20, 7: 15, 8: 15, 9: 5, 10: 40},
        "Chariot":     {2: 20, 3: 22, 4: 25, 5: 20, 6: 47, 7: 55, 8: 64, 9: 64, 10: 64},
        "Hierophant":  {2: 5, 3: 32, 4: 40, 5: 45, 6: 42, 7: 18, 8: 13, 9: 0, 10: 50},
        "Lovers":      {2: 35, 3: 27, 4: 19, 5: 37, 6: 46, 7: 52, 8: 32, 9: 71, 10: 34},
        "Councillor":  {2: 0, 3: 33, 4: 42, 5: 33, 6: 30, 7: 60, 8: 30, 9: 40, 10: 40},
        "Hanged Man":  {2: 5, 3: 5, 4: 15, 5: 25, 6: 40, 7: 40, 8: 0, 9: 25, 10: 40},
        "Temperance":  {2: 6, 3: 19, 4: 39, 5: 6, 6: 11, 7: 41, 8: 6, 9: 6, 10: 5},
        "Faith":       {2: 7, 3: 41, 4: 19, 5: 5, 6: 0, 7: 57, 8: 42, 9: 85, 10: 85},
        "Justice":     {2: 10, 3: 23, 4: 40, 5: 5, 6: 55, 7: 10, 8: 0, 9: 0, 10: 0},
        "Emperor":     {2: 5, 3: 0, 4: 25, 5: 15, 6: 25, 7: 5, 8: 28, 9: 22, 10: 35},
        "Priestess":   {2: 10, 3: 6, 4: 19, 5: 19, 6: 19, 7: 19, 8: 37, 9: 19, 10: 56},
        "Fortune":     {2: 7, 3: 0, 4: 13, 5: 15, 6: 15, 7: 32, 8: 20, 9: 48, 10: 22},
        "Devil":       {2: 0, 3: 13, 4: 13, 5: 25, 6: 27, 7: 25, 8: 5, 9: 22, 10: 40},
        "Star":        {2: 5, 3: 0, 4: 10, 5: 15, 6: 13, 7: 25, 8: 0, 9: 40, 10: 32},
        "Hermit":      {2: 0, 3: 10, 4: 15, 5: 27, 6: 22, 7: 5, 8: 30, 9: 35, 10: 35},
        "Tower":       {2: 5, 3: 0, 4: 12, 5: 15, 6: 20, 7: 27, 8: 0, 9: 15, 10: 30},
        "Empress":     {2: 10, 3: 5, 4: 13, 5: 26, 6: 15, 7: 22, 8: 35, 9: 19, 10: 22},
    }
    # Story-locked confidants (rank follows plot, no point gate):
    CONFIDANT_STORY_LOCKED = {"Fool", "Magician", "Moon", "Sun", "Strength", "Judgement"}

    # Canonical member seeds captured from a clean NG+ save (DATA16) +
    # June save's untouched trailing slots. The game pre-allocates all 10
    # member slots at new-game and writes them only when a member joins.
    # A slot still holding its seed = member has NOT joined the story yet.
    # Verified 2026-08-16: June save slots 1-4 differ from seed (joined),
    # slots 5-8 match seed exactly (Makoto/Futaba/Haru/Akechi pre-join).
    # Slot 0 (Joker) is always present.
    PC31_MEMBER_SEEDS = {
        1: (117, 36, 4, 0xCA),   # Ryuji
        2: (82, 33, 2, 0xCB),    # Morgana
        3: (109, 62, 5, 0xCC),   # Ann
        4: (192, 86, 15, 0xCD),  # Yusuke
        5: (243, 142, 21, 0xCE), # Makoto (206)
        6: (316, 182, 36, 0xCF), # Haru (207, Milady 0x00CF)
        7: (213, 155, 30, 0xD0), # Futaba (208, Necronomicon 0x00D0)
        8: (386, 215, 45, 0xD1), # Akechi (209)
        # Kasumi's slot is PRE-WRITTEN by the game at save creation with
        # her base state (358/159/43/0xF0) — verified against the untouched
        # Aug-06 backup, Aug-13 copy, Aug-14 copy, and live June saves,
        # all identical. DO NOT use the NG+ clear-data save (DATA16:
        # 427/190/60/0xE5) as the seed — that carries post-game values.
        9: (358, 159, 43, 0xF0), # Kasumi (pre-join, game-written base)
    }

    def is_member_joined(self, slot: int) -> bool:
        """True when this party slot has story data (member joined).

        Slots the game seeded but never touched match their canonical seed
        exactly -> not yet joined. Refuse edits + hide from the roster UI.
        """
        if slot == 0:
            return True
        seed = self.PC31_MEMBER_SEEDS.get(slot)
        if seed is None or not self.is_real_save():
            return False
        d = self.parser.data_payload
        base = self.PC31_OFFSET_PARTY_BASE + slot * self.PC31_PARTY_STRIDE
        if base + 0x3E > len(d):
            return False
        cur = (struct.unpack_from("<H", d, base + 0)[0],
               struct.unpack_from("<H", d, base + 4)[0],
               d[base + 0x3C],
               struct.unpack_from("<H", d, base + 0x3A)[0])
        return cur != seed

    PC31_OFFSET_PARTY_BASE = 0x2C   # VERIFIED 2026-08-09: stride 0x2B0, 10 member slots

    PC31_PARTY_STRIDE = 0x2B0
    PC31_PARTY_HP_OFF = 0x00        # u16 — in-game verified (256/246/208/221/234)
    PC31_PARTY_SP_OFF = 0x04        # u16 — in-game verified (136/99/131/140/108)
    # Slot 0 (Joker) is a player struct: LV @+0xC, EXP @+0x10 (NOT money!).
    # Slots 1+ (teammates): LV @+0x3C is the persona-struct level (u8);
    # +0x3D is the persona struct's unknown byte — never clobber it with
    # a u16 write (fixed 2026-08-16). Flag 0x1001 @+0x38.
    PC31_PARTY_LV_OFF_LEADER = 0x0C
    PC31_PARTY_LV_OFF_MEMBER = 0x3C

    def is_real_save(self) -> bool:
        """True when the loaded save is a native PC save (payload v0x31)."""
        return bool(getattr(self.parser, "is_pc_0x31", False))

    def get_quick_info(self) -> Dict[str, Any]:
        """Parse the container header's authoritative quick-info TEXT block.

        Verified 2026-08-08: the header carries a plain-ASCII block like
        "6/14(Tue) Evening,Leblanc\nPLV:22 K\nPLAY TIME:22h 47m\nDIFFICULTY:Normal".
        This is what the game's save-select screen shows. The old payload
        offsets (0x2C etc.) were garbage; retired.
        """
        if not self.is_real_save():
            return {}
        hdr = bytes(getattr(self.container, "header_bytes", b""))
        text = "".join(chr(b) if 32 <= b < 127 else "\n" for b in hdr)
        out = {"day": None, "level": None, "playtime": None, "difficulty": None,
               "money": self.get_money()}
        import re
        m = re.search(r"(\d+/\d+\([A-Za-z]+\)[^\n]*)", text)
        if m:
            out["day"] = m.group(1).strip()
        m = re.search(r"PLV:\s*(\d+)", text)
        if m:
            out["level"] = int(m.group(1))
        m = re.search(r"PLAY TIME:\s*(\d+)h\s*(\d+)m", text)
        if m:
            out["playtime"] = int(m.group(1)) * 3600 + int(m.group(2)) * 60
        m = re.search(r"DIFFICULTY:\s*(\w+)", text)
        if m:
            out["difficulty"] = m.group(1)
        return out

    def set_money(self, amount: int):
        """Set Yen / Money (capped at 9,999,999). Writes strictly to 0x35C0."""
        amount = max(0, min(amount, 9999999))
        if self.is_real_save():
            d = bytearray(self.parser.data_payload)
            if len(d) >= 0x35C4:
                struct.pack_into("<I", d, self.PC31_OFFSET_MONEY, amount)
                self.parser.data_payload = bytes(d)
                return {"status": "ok"}
            return {"status": "noop", "message": "Payload too short for money offset"}
        if 0x10001 in self.parser.blocks_raw:
            raw = bytearray(self.parser.blocks_raw[0x10001])
            if len(raw) >= 4:
                struct.pack_into("<I", raw, 0, amount)
                self.parser.blocks_raw[0x10001] = bytes(raw)
                return {"status": "ok"}
        return {"status": "noop", "message": "Money block 0x10001 not found"}

    def get_money(self) -> int:
        if self.is_real_save():
            d = self.parser.data_payload
            if len(d) >= 0x35C4:
                return struct.unpack_from("<I", d, self.PC31_OFFSET_MONEY)[0]
            return 0  # no recursion into get_quick_info (it calls get_money)
        if 0x10001 in self.parser.blocks_raw:
            raw = self.parser.blocks_raw[0x10001]
            if len(raw) >= 4:
                return struct.unpack("<I", raw[:4])[0]
        return 0

    @staticmethod
    def _to_fullwidth(text: str) -> str:
        """Convert ASCII alphanumeric string to Unicode Fullwidth (Zen-kaku)."""
        res = []
        for c in text:
            code = ord(c)
            if 0x21 <= code <= 0x7E:
                res.append(chr(code + 0xFEE0))
            elif code == 0x20:
                res.append(" ")  # standard space
            else:
                res.append(c)
        return "".join(res)

    @staticmethod
    def _to_atlus_encoding(text: str) -> bytes:
        """Convert ASCII string to Atlus 2-byte font glyph encoding.
        
        Authentic Atlus font encoding formula verified across genuine saves:
        - ASCII alphanumeric / punctuation characters (0x21..0x7E) -> 0x80, (code + 0x60).
        - Space (0x20) -> 0x20.
        """
        b = bytearray()
        for c in text:
            code = ord(c)
            if 0x21 <= code <= 0x7E:
                b.extend([0x80, code + 0x60])
            elif code == 32:
                b.append(0x20)
            else:
                b.append(code if code < 128 else 0x20)
        return bytes(b)

    def set_player_names(self, first: str, last: str, group: str) -> Dict[str, Any]:
        """Update Joker first, last, and Phantom Thief group name across container and payload."""
        first = first.strip()[:24]
        last = last.strip()[:24]
        group = group.strip()[:24]
        full_ascii = f"{first} {last}".strip()

        # 1. Header (0x190 container header)
        fw_first = self._to_fullwidth(first)
        fw_last = self._to_fullwidth(last)
        fw_group = self._to_fullwidth(group)
        fw_full = f"{fw_first} {fw_last}".strip()

        self.parser.header.fname = first
        self.parser.header.lname = last

        # 2. Player Name Block (0x2D / legacy)
        self.parser.player_names.first_name_game = first
        self.parser.player_names.last_name_game = last
        self.parser.player_names.full_name_game = full_ascii
        self.parser.player_names.full_name_utf8 = full_ascii
        self.parser.player_names.group_name_game = group
        self.parser.player_names.group_name_utf8 = group

        # 3. Native PC Data Payload (0x13840..0x139B0 and mirror 0x2BD50..0x2BEC0)
        if self.is_real_save():
            d = bytearray(self.parser.data_payload)
            # Fullwidth UTF-8 encoded bytes
            fw_full_b = fw_full.encode("utf-8")[:64].ljust(64, b"\x00")
            fw_last_b = fw_last.encode("utf-8")[:32].ljust(32, b"\x00")
            fw_first_b = fw_first.encode("utf-8")[:32].ljust(32, b"\x00")
            fw_group_b = fw_group.encode("utf-8")[:48].ljust(48, b"\x00")

            # Atlus Custom 2-byte encoded bytes
            atlus_last_b = self._to_atlus_encoding(last)[:20].ljust(20, b"\x00")
            atlus_first_b = self._to_atlus_encoding(first)[:20].ljust(20, b"\x00")
            atlus_full_b = self._to_atlus_encoding(full_ascii)[:40].ljust(40, b"\x00")
            atlus_group_b = self._to_atlus_encoding(group)[:24].ljust(24, b"\x00")

            for delta in (0x0000, 0x18510):
                base = 0x13840 + delta
                if base + 0x170 <= len(d):
                    # 0x13840: Full Name (Fullwidth UTF-8, 64B)
                    d[base : base + 64] = fw_full_b
                    # 0x138A8: Last Name (Fullwidth UTF-8, 32B)
                    d[base + 0x68 : base + 0x88] = fw_last_b
                    # 0x138DC: First Name (Fullwidth UTF-8, 32B)
                    d[base + 0x9C : base + 0xBC] = fw_first_b
                    # 0x13910: Last Name (Atlus encoding, 20B)
                    d[base + 0xD0 : base + 0xE4] = atlus_last_b
                    # 0x13924: First Name (Atlus encoding, 20B)
                    d[base + 0xE4 : base + 0xF8] = atlus_first_b
                    # 0x13938: Full Name (Atlus encoding, 40B)
                    d[base + 0xF8 : base + 0x120] = atlus_full_b
                    if group:
                        # 0x13960: Group Name (Atlus encoding, 24B)
                        d[base + 0x120 : base + 0x138] = atlus_group_b
                        # 0x1397C: Group Name (Fullwidth UTF-8, 48B)
                        d[base + 0x13C : base + 0x16C] = fw_group_b

            self.parser.data_payload = bytes(d)

        return {"status": "ok", "names_updated": True, "group_updated": True, "message": ""}

    def get_social_stats(self) -> Dict[str, Dict[str, Any]]:
        """Read social stats as (points, rank) pairs from the u16 point block.

        Save stores POINTS per stat (u16 LE) at 0x139E0 in order
        [Knowledge, Charm, Proficiency, Guts, Kindness]. Rank is derived
        from the P5R thresholds. Verified 2026-08-08 by 2-save diff:
        crafting (+3 Prof pts) and plant (+2 Kind pts) moved exactly these
        u16 values without changing ranks.
        """
        result = {}
        if self.is_real_save():
            d = self.parser.data_payload
            base = self.PC31_OFFSET_SOCIAL_STATS
            if len(d) >= base + 10:
                for i, name in enumerate(self.PC31_SOCIAL_ORDER):
                    pts = struct.unpack_from("<H", d, base + i * 2)[0]
                    rank = 1
                    th = self.PC31_SOCIAL_THRESHOLDS[name]
                    for r in range(1, 5):
                        if pts >= th[r]:
                            rank = r + 1
                    result[name] = {"points": pts, "rank": rank}
        return result

    def set_social_stats(self, knowledge: int = 5, charm: int = 5, proficiency: int = 5, kindness: int = 5, guts: int = 5):
        """Set social stats (Levels 1 to 5) by writing point thresholds.

        P5R stores each stat as u16 LE points at 0x139E0 in order
        [Knowledge, Charm, Proficiency, Guts, Kindness]. To force rank N we
        write the threshold points needed to reach that rank (rank 5 = max).

        Surplus preservation (2026-08-24, zamasu2020 bug report): raising one
        stat must never LOWER the others. Points are written as
        max(current, threshold) when raising or keeping a rank, so accrued
        progress within a rank survives; only an explicit lowering writes
        the bare threshold.
        """
        vals = {"Knowledge": knowledge, "Charm": charm, "Proficiency": proficiency,
                "Guts": guts, "Kindness": kindness}
        if self.is_real_save():
            d = bytearray(self.parser.data_payload)
            base = self.PC31_OFFSET_SOCIAL_STATS
            if len(d) >= base + 10:
                for i, name in enumerate(self.PC31_SOCIAL_ORDER):
                    v = max(1, min(int(vals.get(name, 5)), 5))
                    th = self.PC31_SOCIAL_THRESHOLDS[name]
                    cur_pts = struct.unpack_from("<H", d, base + i * 2)[0]
                    cur_rank = 1
                    for r in range(1, 5):
                        if cur_pts >= th[r]:
                            cur_rank = r + 1
                    if v >= cur_rank:
                        pts = max(cur_pts, th[v - 1])  # never destroy surplus
                    else:
                        pts = th[v - 1]                # explicit lowering
                    struct.pack_into("<H", d, base + i * 2, pts)
                self.parser.data_payload = bytes(d)
                return {"status": "ok", "mode": "points_u16"}
        if 0x10005 in self.parser.blocks_raw:
            raw = bytearray(self.parser.blocks_raw[0x10005])
            thresholds = [0, 20, 50, 100, 200]
            stats_order = [knowledge, charm, proficiency, kindness, guts]
            for i, val in enumerate(stats_order):
                val = max(1, min(val, 5))
                points = thresholds[val - 1]
                if len(raw) >= (i + 1) * 4:
                    struct.pack_into("<HH", raw, i * 4, val, points)
            self.parser.blocks_raw[0x10005] = bytes(raw)
        return {"status": "ok", "mode": "fallback_0x2d"}

    # -------------------------------------------------------------------------
    # Item ID -> name binding (VERIFIED 2026-08-09 via 100% NG++ oracle save)
    # -------------------------------------------------------------------------
    # Ring/acquisition IDs (0x3530, 0x20xx-0x60xx) map to the KingdomSaveEditor
    # name tables: low 12 bits = index into Royal_ConsumableItemNames.txt or
    # Royal_KeyItemNames.txt (data/ dir). Verified: purchase-diff IDs decode to
    # the exact items bought at Takemi's clinic; the Clear-Data farewell gifts
    # (0x4047-0x4050) bind byte-for-byte to count bytes 0x2784-0x278D.
    ITEM_NAMES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    _ITEM_NAMES_CACHE = {}

    def _load_item_names(self) -> Dict[int, str]:
        if SaveEditor._ITEM_NAMES_CACHE:
            return SaveEditor._ITEM_NAMES_CACHE
        import os
        import sys as _sys
        result = {}
        # bundled EXE: data/ lives in _MEIPASS; dev: project data/ dir
        candidates = []
        if getattr(_sys, "frozen", False):
            candidates.append(os.path.join(getattr(_sys, "_MEIPASS", ""), "data"))
        candidates.append(self.ITEM_NAMES_PATH)
        for base in candidates:
            for fname in ("Royal_ConsumableItemNames.txt", "Royal_KeyItemNames.txt"):
                path = os.path.join(base, fname)
                try:
                    with open(path, encoding="utf-8", errors="replace") as fh:
                        lines = fh.read().splitlines()
                except OSError:
                    continue
                for i, name in enumerate(lines):
                    name = name.strip()
                    if name and name not in ("BLANK", "RESERVE"):
                        result[i] = name
            if result:
                break
        if result:
            SaveEditor._ITEM_NAMES_CACHE = result  # never cache empty (retry next load)
        return result

    def get_item_name(self, item_id: int) -> str:
        """Resolve a save item id (ring/0x3530 or count-table id) to a name."""
        names = self._load_item_names()
        return names.get(item_id & 0xFFF, f"item_{item_id:04X}")

    def get_item_names(self, ids) -> List[Dict[str, Any]]:
        """Resolve a list of item ids to {id, name}."""
        names = self._load_item_names()
        out = []
        for iid in ids:
            out.append({"id": iid, "name": names.get(iid & 0xFFF, f"item_{iid:04X}")})
        return out

    # -------------------------------------------------------------------------
    # Equipped Persona API — VERIFIED 2026-08-09 (oracle Lv99 save)
    # -------------------------------------------------------------------------
    # Lives INSIDE each member's party struct (0x2C + slot*0x2B0):
    #   +0x38 flags u16 (0x1001 = equipped?; Ryuji 0x0001 in oracle)
    #   +0x3A persona id u16 (Joker=Raoul 0x16B, Ryuji=William 0xF2 — table-verified)
    #   +0x3C level u8 (99 on oracle)
    #   +0x3E trait u16 (Joker=Vitality of the Tree 87)
    #   +0x40 EXP u32 (Joker 1,418,647 @Lv99)
    #   +0x44..+0x52 8× skill u16 (Joker: Thermopylae/Debilitate/Concentrate/Charge/
    #                              Phantom Show/Ali Dance/Drain Phys/Repel Bless)
    #   +0x54..+0x58 5× stat u8 [St,Ma,En,Ag,Lu] (Joker 52/55/47/63/45 @Lv99)
    PC31_PERSONA_BASE_REL = 0x38
    PC31_PERSONA_ID_OFF = 0x3A
    PC31_PERSONA_LVL_OFF = 0x3C
    PC31_PERSONA_TRAIT_OFF = 0x3E
    PC31_PERSONA_EXP_OFF = 0x40
    PC31_PERSONA_SKILLS_OFF = 0x44
    PC31_PERSONA_STATS_OFF = 0x54
    PC31_PERSONA_N_SKILLS = 8

    def get_equipped_persona(self, slot: int) -> Dict[str, Any]:
        """Read one member's equipped persona (VERIFIED block)."""
        if not self.is_real_save():
            return {"status": "noop", "message": "PC payload required"}
        d = self.parser.data_payload
        base = self.PC31_OFFSET_PARTY_BASE + slot * self.PC31_PARTY_STRIDE
        if base + self.PC31_PERSONA_STATS_OFF + 5 > len(d):
            return {"status": "noop", "message": "Slot out of range"}
        pid = struct.unpack_from("<H", d, base + self.PC31_PERSONA_ID_OFF)[0]
        lvl = d[base + self.PC31_PERSONA_LVL_OFF]
        trait = struct.unpack_from("<H", d, base + self.PC31_PERSONA_TRAIT_OFF)[0]
        exp = struct.unpack_from("<I", d, base + self.PC31_PERSONA_EXP_OFF)[0]
        skills = [struct.unpack_from("<H", d, base + self.PC31_PERSONA_SKILLS_OFF + i*2)[0]
                  for i in range(self.PC31_PERSONA_N_SKILLS)]
        stats = list(d[base + self.PC31_PERSONA_STATS_OFF : base + self.PC31_PERSONA_STATS_OFF + 5])
        return {
            "slot": slot,
            "persona_id": pid,
            "persona": self.get_persona_name(pid),
            "level": lvl,
            "trait_id": trait,
            "trait": self.get_trait_name(trait),
            "exp": exp,
            "skills": [{"id": s, "name": self.get_skill_name(s)} for s in skills],
            "stats": {"st": stats[0], "ma": stats[1], "en": stats[2], "ag": stats[3], "lu": stats[4]},
            "flags": struct.unpack_from("<H", d, base + self.PC31_PERSONA_BASE_REL)[0],
        }

    def set_equipped_persona(self, slot: int, persona_id: Optional[int] = None,
                             level: Optional[int] = None, trait_id: Optional[int] = None,
                             exp: Optional[int] = None, skills: Optional[List[int]] = None,
                             stats: Optional[List[int]] = None,
                             flags: Optional[int] = None) -> Dict[str, Any]:
        """Write one member's equipped persona fields (VERIFIED block)."""
        if not self.is_real_save():
            return {"status": "noop", "message": "PC payload required"}
        if not self.is_member_joined(slot):
            return {"status": "invalid",
                    "message": f"Member slot {slot} has not joined the party yet — persona edits refused."}
        d = bytearray(self.parser.data_payload)
        base = self.PC31_OFFSET_PARTY_BASE + slot * self.PC31_PARTY_STRIDE
        if base + self.PC31_PERSONA_STATS_OFF + 5 > len(d):
            return {"status": "noop", "message": "Slot out of range"}
        if persona_id is not None:
            if slot > 0:
                cur_id = struct.unpack_from("<H", d, base + self.PC31_PERSONA_ID_OFF)[0]
                if persona_id != cur_id:
                    return {"status": "invalid",
                            "message": "Teammate personas are story-locked; only Joker (slot 0) may change the equipped persona."}
            table = self._load_table("Personas.txt")
            if table and persona_id not in table:
                return {"status": "invalid",
                        "message": f"persona_id 0x{persona_id:04X} not in Personas.txt"}
            if persona_id in self.PC31_STOCK_LEGACY_IDS:
                return {"status": "invalid",
                        "message": f"persona_id 0x{persona_id:04X} is a legacy/cut entry the game never uses — refusing."}
            if persona_id in self.PC31_LAB_PERSONA_IDS:
                return {"status": "invalid",
                        "message": f"persona_id 0x{persona_id:04X} is a dev/test-only persona (Lab) — refusing."}
        if skills is not None:
            skill_table = self._load_table("Skill ID.txt")
            for sid in skills:
                if sid == 0:
                    continue  # empty slot
                if sid <= 0x09:
                    return {"status": "invalid",
                            "message": f"skill id 0x{sid:04X} is a BLANK/dummy slot — refusing."}
                if sid in self.PC31_NON_SKILL_IDS:
                    return {"status": "invalid",
                            "message": f"skill id 0x{sid:04X} does not exist in the game's skill table — refusing."}
                if skill_table and sid not in skill_table:
                    return {"status": "invalid",
                            "message": f"skill id 0x{sid:04X} not in Skill ID.txt"}
                if skill_table and skill_table.get(sid, "") in ("BLANK", "RESERVE", "----------"):
                    return {"status": "invalid",
                            "message": f"skill id 0x{sid:04X} is a placeholder skill — refusing."}
        if trait_id not in (None, 0):
            trait_table = self._load_table("Traits.txt")
            if trait_table and trait_id not in trait_table:
                return {"status": "invalid", "message": f"trait id 0x{trait_id:04X} not in Traits.txt"}
            if trait_table and trait_table.get(trait_id, "") in ("", "RESERVE", "???", "BLANK", "----------"):
                return {"status": "invalid",
                        "message": f"trait id 0x{trait_id:04X} is a RESERVE/dummy slot — refusing."}
        if flags is not None:
            struct.pack_into("<H", d, base + self.PC31_PERSONA_BASE_REL, max(0, flags))
        if persona_id is not None:
            struct.pack_into("<H", d, base + self.PC31_PERSONA_ID_OFF, max(0, persona_id))
        if level is not None:
            d[base + self.PC31_PERSONA_LVL_OFF] = max(1, min(level, 99))
        if trait_id is not None:
            struct.pack_into("<H", d, base + self.PC31_PERSONA_TRAIT_OFF, max(0, trait_id))
        if exp is not None:
            struct.pack_into("<I", d, base + self.PC31_PERSONA_EXP_OFF, max(0, exp))
        if skills is not None:
            for i in range(min(len(skills), self.PC31_PERSONA_N_SKILLS)):
                struct.pack_into("<H", d, base + self.PC31_PERSONA_SKILLS_OFF + i*2, max(0, skills[i]))
        if stats is not None:
            for i in range(min(len(stats), 5)):
                d[base + self.PC31_PERSONA_STATS_OFF + i] = max(0, min(stats[i], 99))
        self.parser.data_payload = bytes(d)
        return {"status": "success", "slot": slot}

    # persona / skill / trait name lookups (Ruimusume tables, data/)
    _TABLE_CACHE: Dict[str, Dict[int, str]] = {}

    def _load_table(self, fname: str, key_base: int = 16) -> Dict[int, str]:
        cached = SaveEditor._TABLE_CACHE.get(fname)
        if cached:
            return cached
        import os
        import sys as _sys
        candidates = []
        if getattr(_sys, "frozen", False):
            candidates.append(os.path.join(getattr(_sys, "_MEIPASS", ""), "data"))
        candidates.append(self.ITEM_NAMES_PATH)
        for base in candidates:
            path = os.path.join(base, fname)
            out = {}
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    lines = fh.read().splitlines()
            except OSError:
                continue
            for line in lines:
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 4 and parts[0].strip():
                    try:
                        out[int(parts[0], key_base)] = parts[3].strip()
                    except ValueError:
                        pass
            if out:
                SaveEditor._TABLE_CACHE[fname] = out  # never cache empty (retry next load)
                return out
        return {}

    def get_persona_name(self, pid: int) -> str:
        t = self._load_table("Personas.txt")
        return t.get(pid, f"persona_{pid:04X}")

    def get_skill_name(self, sid: int) -> str:
        t = self._load_table("Skill ID.txt")
        return t.get(sid, f"skill_{sid:04X}")

    def get_trait_name(self, tid: int) -> str:
        t = self._load_table("Traits.txt")
        return t.get(tid, f"trait_{tid:04X}")

    # -------------------------------------------------------------------------
    # Persona STOCK array API (12 slots/member) — VERIFIED 2026-08-09
    # -------------------------------------------------------------------------
    # Array base = member + 0x38, stride 0x30, 12 slots. Slot 0 = equipped.
    # Layout per slot (identical to PS4 KHSave persona struct):
    #   +0x00 flags u16 (0x0001 owned; 0x1000 unknown — preserve as-is)
    #   +0x02 id u16, +0x04 level u8, +0x05 unk u8, +0x06 trait u16,
    #   +0x08 EXP u32, +0x0C 8×skill u16, +0x1C 5×stat u8, rest zero.
    # Empty slot = all 48 bytes zero.
    PC31_STOCK_BASE_REL = 0x38
    PC31_STOCK_STRIDE = 0x30
    PC31_STOCK_SLOTS = 12
    # P5-legacy duplicate persona ids (0x0DB..0x0E0 minus 0x0DF) the Royal
    # engine never uses in any context — no unit record, no model. Writing
    # them into a stock slot risks Velvet Room / battle animation crashes.
    # Verified 2026-08-16: never present in 12 real saves' stock arrays.
    PC31_STOCK_LEGACY_IDS = {0x0DB, 0x0DC, 0x0DD, 0x0DE, 0x0E0}
    # Dev/test-only personas ("Lab Kelpie" etc) present in the dump but not
    # in the game's NAME.TBL — never usable by players. Verified 2026-08-16.
    PC31_LAB_PERSONA_IDS = {440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450}
    # Skill ids whose dump names do not exist in the game's NAME.TBL: item
    # names, test skills, dev strings. Refused on write. Verified 2026-08-16
    # against the extracted EN name table.
    PC31_NON_SKILL_IDS = {109, 166, 172, 173, 174, 384, 389, 397, 398, 400, 401,
                          402, 420, 421, 422, 423, 424, 425, 426, 436, 437, 482,
                          483, 484, 485, 486, 487, 568, 569, 570, 571, 572, 573,
                          574, 575, 576, 577, 578, 579, 580, 581, 582, 583, 584,
                          585, 586, 587, 588, 589, 590, 591, 592, 593, 594, 595,
                          596, 597, 598, 658, 659, 660, 663, 677, 730, 731, 734,
                          735, 751, 753, 777, 778, 788, 798, 943, 948, 952, 960,
                          965, 968, 980, 999, 1027, 1049}

    def get_persona_stock(self, slot: int) -> List[Dict[str, Any]]:
        """Read all 12 stock slots for one member (VERIFIED array)."""
        if not self.is_real_save():
            return []
        d = self.parser.data_payload
        base = self.PC31_OFFSET_PARTY_BASE + slot * self.PC31_PARTY_STRIDE + self.PC31_STOCK_BASE_REL
        out = []
        for k in range(self.PC31_STOCK_SLOTS):
            off = base + k * self.PC31_STOCK_STRIDE
            if off + 0x30 > len(d):
                break
            pid = struct.unpack_from("<H", d, off + 2)[0]
            lvl = d[off + 4]
            entry = {
                "slot": k,
                "persona_id": pid,
                "persona": self.get_persona_name(pid) if pid else None,
                "level": lvl,
                "trait_id": struct.unpack_from("<H", d, off + 6)[0],
                "exp": struct.unpack_from("<I", d, off + 8)[0],
                "skills": [struct.unpack_from("<H", d, off + 0x0C + i*2)[0] for i in range(8)],
                "stats": list(d[off + 0x1C : off + 0x21]),
                "flags": struct.unpack_from("<H", d, off)[0],
                "empty": pid == 0 and lvl == 0,
            }
            out.append(entry)
        return out

    def set_persona_stock_slot(self, member_slot: int, stock_k: int,
                               persona_id: int, level: int = 1, trait_id: int = 0,
                               exp: int = 0, skills: Optional[List[int]] = None,
                               stats: Optional[List[int]] = None,
                               flags: int = 0x0001) -> Dict[str, Any]:
        """Write ONE stock slot (k=0..11). Empty = pass persona_id=0.

        Validates persona/skill ids against the data tables: invalid ids
        are rejected, never written (invalid slot-0 personas can crash the
        game's menu/battle pipelines).
        """
        if not self.is_real_save():
            return {"status": "noop", "message": "PC payload required"}
        if not self.is_member_joined(member_slot) and member_slot != 0:
            return {"status": "invalid",
                    "message": f"Member slot {member_slot} has not joined the party yet — stock edits refused."}
        if persona_id != 0:
            table = self._load_table("Personas.txt")
            if table and persona_id not in table:
                return {"status": "invalid", "message": f"persona_id 0x{persona_id:04X} not in Personas.txt"}
            if persona_id in self.PC31_STOCK_LEGACY_IDS:
                return {"status": "invalid",
                        "message": f"persona_id 0x{persona_id:04X} is a P5-legacy duplicate with no Royal model — refusing."}
            if persona_id in self.PC31_LAB_PERSONA_IDS:
                return {"status": "invalid",
                        "message": f"persona_id 0x{persona_id:04X} is a dev/test-only persona (Lab) — refusing."}
            if table and table.get(persona_id, "") in ("", "RESERVE", "???", "BLANK", "----------", "P5 Unused"):
                return {"status": "invalid",
                        "message": f"persona_id 0x{persona_id:04X} ({table.get(persona_id)}) is cut content — refusing."}
            if skills:
                skill_table = self._load_table("Skill ID.txt")
                for sid in skills:
                    if sid == 0:
                        continue  # empty slot
                    if sid <= 0x09:
                        return {"status": "invalid", "message": f"skill id 0x{sid:04X} is a BLANK/dummy slot — refusing."}
                    if sid in self.PC31_NON_SKILL_IDS:
                        return {"status": "invalid",
                                "message": f"skill id 0x{sid:04X} does not exist in the game's skill table — refusing."}
                    if skill_table and sid not in skill_table:
                        return {"status": "invalid", "message": f"skill id 0x{sid:04X} not in Skill ID.txt"}
                    if skill_table and skill_table.get(sid, "") in ("BLANK", "RESERVE", "----------"):
                        return {"status": "invalid",
                                "message": f"skill id 0x{sid:04X} is a placeholder skill — refusing."}
            if trait_id not in (None, 0):
                trait_table = self._load_table("Traits.txt")
                if trait_table and trait_id not in trait_table:
                    return {"status": "invalid", "message": f"trait id 0x{trait_id:04X} not in Traits.txt"}
                if trait_table and trait_table.get(trait_id, "") in ("", "RESERVE", "???", "BLANK", "----------"):
                    return {"status": "invalid",
                            "message": f"trait id 0x{trait_id:04X} is a RESERVE/dummy slot — refusing."}
        d = bytearray(self.parser.data_payload)
        off = (self.PC31_OFFSET_PARTY_BASE + member_slot * self.PC31_PARTY_STRIDE
               + self.PC31_STOCK_BASE_REL + stock_k * self.PC31_STOCK_STRIDE)
        if off + 0x30 > len(d):
            return {"status": "noop", "message": "Slot out of range"}
        if persona_id == 0:
            d[off:off + 0x30] = b"\x00" * 0x30  # clear slot
        else:
            struct.pack_into("<H", d, off, flags)
            struct.pack_into("<H", d, off + 2, max(0, persona_id))
            d[off + 4] = max(1, min(level, 99))
            # Preserve the unverified byte at +0x05 (do not zero it).
            struct.pack_into("<H", d, off + 6, max(0, trait_id))
            struct.pack_into("<I", d, off + 8, max(0, exp))
            for i in range(8):
                sid = (skills[i] if skills and i < len(skills) else 0)
                struct.pack_into("<H", d, off + 0x0C + i*2, max(0, sid))
            for i in range(5):
                sv = (stats[i] if stats and i < len(stats) else 0)
                d[off + 0x1C + i] = max(0, min(sv, 99))
        self.parser.data_payload = bytes(d)
        return {"status": "success", "member": member_slot, "stock_k": stock_k}

    def equip_persona(self, member_slot: int, stock_k: int) -> Dict[str, Any]:
        """Make stock slot k the equipped persona by swapping it to slot 0.

        Refuses to equip an EMPTY slot (a blank slot 0 can crash menus/battle).
        """
        if not self.is_real_save():
            return {"status": "noop", "message": "PC payload required"}
        if not (0 <= stock_k < self.PC31_STOCK_SLOTS):
            return {"status": "noop", "message": "Stock slot out of range"}
        if stock_k == 0:
            return {"status": "success", "message": "Already equipped"}
        d = bytearray(self.parser.data_payload)
        base = self.PC31_OFFSET_PARTY_BASE + member_slot * self.PC31_PARTY_STRIDE + self.PC31_STOCK_BASE_REL
        a = base
        b = base + stock_k * self.PC31_STOCK_STRIDE
        if b + 0x30 > len(d):
            return {"status": "noop", "message": "Out of range"}
        pid = struct.unpack_from("<H", d, b + 2)[0]
        if pid == 0:
            return {"status": "invalid", "message": "Cannot equip an empty stock slot"}
        d[a:a+0x30], d[b:b+0x30] = d[b:b+0x30], d[a:a+0x30]  # swap
        self.parser.data_payload = bytes(d)
        return {"status": "success", "member": member_slot, "now_equipped_k": stock_k}

    # -------------------------------------------------------------------------
    # Master Inventory API (Full Bag & Pouch Extraction) — VERIFIED 2026-08-14
    # -------------------------------------------------------------------------
    PC31_INVENTORY_BASE = 0x2410
    PC31_INVENTORY_STRIDE = 0x1B
    PC31_INVENTORY_SLOTS = 30
    PC31_RING_BUFFER_BASE = 0x3530
    # Equipment ownership flags — VERIFIED 2026-08-19 via 9 live purchase diffs.
    #   Melee     owned flag = 0x1B30 + (item_id & 0x0FFF)   [3 points]
    #   Protector owned flag = 0x1F30 + (item_id & 0x0FFF)   [2 points]
    #   Accessory owned flag = 0x2330 + (item_id & 0x0FFF)   [2 points]
    #   Ranged    owned flag = 0x3430 + idx                   [2 points, but the
    #             DB id→save-id mapping is OFFSET for ranged (ranged name table has
    #             filler/Unused rows that shift real ids). See RANGED_SAVE_ID_BY_DB_ID.]
    # The cheat save (GameBanana) uses a DIFFERENT layout — never trust it for bases.
    PC31_MELEE_OWNED_BASE     = 0x1B30
    PC31_PROTECTOR_OWNED_BASE = 0x1F30
    PC31_ACCESSORY_OWNED_BASE = 0x2330
    PC31_RANGED_OWNED_BASE    = 0x3430
    # Ranged: DB item_id -> actual save index (derived from game memory offsets: addr - 0x02272456)
    # Verified live on Makaronov (0x7010 -> 0x13) and Bianchi SBAS (0x7020 -> 0x23).
    RANGED_SAVE_IDX_BY_DB_ID = {
        0x700B: 0x0E,  # Tkachev
        0x700C: 0x0F,  # Governance
        0x700E: 0x11,  # Riot Police
        0x7010: 0x13,  # Makaronov
        0x7011: 0x14,  # Nataraja EX
        0x7016: 0x19,  # Jig 227
        0x7019: 0x1C,  # Tyrant Pistol EX
        0x701A: 0x1D,  # Model Gun
        0x701B: 0x1E,  # Levinson M31
        0x701D: 0x20,  # Granelli M3
        0x7020: 0x23,  # Bianchi SBAS
        0x7022: 0x25,  # Fireworks
        0x7023: 0x26,  # Pumpkin Buster
        0x7024: 0x27,  # Megido Blaster
        0x7027: 0x2A,  # Pumpkin Bomb
        0x7029: 0x2C,  # Megido Fire
        0x7035: 0x38,  # Bandit Slingshot
        0x7039: 0x3C,  # Comanche
        0x703B: 0x3E,  # Cat Whip
        0x703F: 0x42,  # Dream Slingshot
        0x7041: 0x44,  # Sudarshana EX
        0x7042: 0x45,  # Utopia
        0x7044: 0x47,  # Star Slingshot
        0x704E: 0x51,  # Replica Gun
        0x7054: 0x57,  # Troop Submachine Gun
        0x7055: 0x58,  # Sterling Short
        0x7058: 0x5B,  # Crimson Gun
        0x7059: 0x5C,  # Wildfire
        0x705A: 0x5D,  # No Mercy
        0x705B: 0x5E,  # Phantom Killer
        0x705E: 0x61,  # Heaven's Gate
        0x7061: 0x64,  # Gossip
        0x7067: 0x6A,  # Custom Submachine Gun
        0x7069: 0x6C,  # Masquerade
        0x706E: 0x71,  # Silver Gun
        0x7074: 0x77,  # Black Crossbow
        0x7075: 0x78,  # Red Crossbow
        0x7076: 0x79,  # Heavy Crossbow
        0x7077: 0x7A,  # Blue Crossbow
        0x7078: 0x7B,  # White Crossbow
        0x7079: 0x7C,  # Master Crossbow
        0x707B: 0x7E,  # Shiranui EX
        0x707C: 0x7F,  # Guillotine Crossbow
        0x707E: 0x81,  # Holy Crossbow
        0x7086: 0x89,  # Ancient Crossbow
        0x7088: 0x8B,  # Dragon Crossbow
        0x708A: 0x8D,  # Judgment Crossbow
        0x708C: 0x8F,  # Long Barrel Crossbow
        0x708D: 0x90,  # Phoenix Crossbow
        0x7093: 0x96,  # Revolver 38
        0x7095: 0x98,  # Peacemaker
        0x7097: 0x9A,  # Peacemaker HP
        0x7099: 0x9C,  # Heavy Revolver
        0x709A: 0x9D,  # Python 44
        0x709B: 0x9E,  # Judge End
        0x709C: 0x9F,  # Miragestalker
        0x70A0: 0xA3,  # Carnelian
        0x70A8: 0xAB,  # Custom Revolver
        0x70A9: 0xAC,  # Big Bear
        0x70AF: 0xB2,  # Grenade Launcher
        0x70B1: 0xB4,  # Rapid Launcher
        0x70B2: 0xB5,  # Heavy Launcher
        0x70B3: 0xB6,  # Blast Launcher
        0x70B4: 0xB7,  # Multi Launcher
        0x70B5: 0xB8,  # Buster Launcher
        0x70B6: 0xB9,  # Megido Launcher
        0x70B7: 0xBA,  # Flame Launcher
        0x70B8: 0xBB,  # Freeze Launcher
        0x70B9: 0xBC,  # Spark Launcher
        0x70BA: 0xBD,  # Gale Launcher
        0x70BB: 0xBE,  # Psycho Launcher
        0x70BC: 0xBF,  # Atomic Launcher
        0x70C0: 0xC3,  # Yagrush EX
        0x70C1: 0xC4,  # Giant Launcher
        0x70C6: 0xC9,  # Custom Launcher
        0x70C7: 0xCA,  # Wild Launcher
        0x70C8: 0xCB,  # Demon Launcher
        0x70CF: 0xD2,  # Laser Pistol
        0x70D1: 0xD4,  # Plasma Pistol
        0x70D2: 0xD5,  # Photon Pistol
        0x70D5: 0xD8,  # Ray Gun
        0x70D6: 0xD9,  # Doomsday EX
        0x70DB: 0xDE,  # Quantum Pistol
        0x70DD: 0xE0,  # Electron Pistol
        0x70DE: 0xE1,  # Gravity Pistol
        0x70DF: 0xE2,  # Chaos Pistol
        0x70E1: 0xE4,  # Dark Ray Gun
        0x70E2: 0xE5,  # Supernova Pistol
        0x70E5: 0xE8,  # Custom Ray Gun
        0x70E6: 0xE9,  # Hyper Ray Gun
        0x70E7: 0xEA,  # Mega Ray Gun
        0x70EB: 0xEE,  # Lever Action Rifle
        0x70EC: 0xEF,  # Bolt Action Rifle
        0x70ED: 0xF0,  # Hunting Rifle
        0x70EE: 0xF1,  # Precision Rifle
        0x70EF: 0xF2,  # Heavy Rifle
        0x70F1: 0xF4,  # Cendrillon Rifle
        0x70F2: 0xF5,  # Sahasrara EX
        0x70F3: 0xF6,  # Custom Rifle
        0x70F4: 0xF7,  # Wild Rifle
        0x70F5: 0xF8,  # Sniper Rifle
        0x70F6: 0xF9,  # Anti-Material Rifle
        0x70F7: 0xFA,  # Dragon Rifle
        0x70F8: 0xFB,  # Holy Rifle
        0x70F9: 0xFC,  # Demon Rifle
        0x70FA: 0xFD,  # Lucifer Rifle
    }
    PC31_MIRROR_DELTA = 0x18510

    CATEGORY_MAP = {
        0x1000: ("Weapon melee.txt", "Melee"),
        0x2000: ("Items.txt", "Consumable"),
        0x3000: ("Accessories.txt", "Accessory"),
        0x4000: ("Skill Cards.txt", "SkillCard"),
        0x5000: ("Protectors.txt", "Protector"),
        0x6000: ("Tools&materials.txt", "Infiltration"),
        0x7000: ("Weapon ranged.txt", "Ranged"),
        0x8000: ("Treasure.txt", "Treasure"),
        0x9000: ("Keyitems&essentials.txt", "KeyItem"),
        0xA000: ("Outfits.txt", "Outfit"),
    }

    _CATEGORY_TABLE_CACHE: Dict[str, Dict[int, Tuple[str, str]]] = {}

    def _get_category_table(self, fname: str, prefix: int, cat: str) -> Dict[int, Tuple[str, str]]:
        if fname in SaveEditor._CATEGORY_TABLE_CACHE:
            return SaveEditor._CATEGORY_TABLE_CACHE[fname]
        p_dir = Path(__file__).parent.parent / "data" / fname
        table: Dict[int, Tuple[str, str]] = {}
        if p_dir.exists():
            char_map = {
                "主人公": "Joker", "坂本龙司": "Ryuji", "摩尔加纳": "Morgana",
                "高卷杏": "Ann", "喜多川佑介": "Yusuke", "新岛真": "Makoto",
                "奥村春": "Haru", "佐仓双叶": "Futaba", "明智吾郎": "Akechi",
                "芳泽霞": "Kasumi", "ALL": "All"
            }
            try:
                with open(p_dir, encoding="utf-8", errors="replace") as f:
                    for line_idx, line in enumerate(f):
                        parts = line.strip().split("\t")
                        name = parts[3].strip() if len(parts) >= 4 else parts[0].strip()
                        if prefix == 0x5000 and len(parts) >= 5 and parts[4].strip() and parts[4].strip() != "-":
                            role = parts[4].strip()
                            eng_role = char_map.get(role, role)
                            if eng_role:
                                name = f"{name} ({eng_role})"
                        table[line_idx] = (name, cat)
            except Exception:
                pass
        SaveEditor._CATEGORY_TABLE_CACHE[fname] = table
        return table

    def _resolve_item_info(self, item_id: int) -> Tuple[str, str]:
        prefix = item_id & 0xF000
        idx = item_id & 0x0FFF
        info = self.CATEGORY_MAP.get(prefix)
        if info:
            fname, cat = info
            tbl = self._get_category_table(fname, prefix, cat)
            if idx in tbl:
                return tbl[idx]
        return f"Item 0x{item_id:04X}", "Consumable"

    @staticmethod
    def is_placeholder_item(name: str) -> bool:
        """Check if an item name represents an unused Atlus table placeholder.
        
        Authentic in-game items like 'Reserve Ammo' or 'Blank Card' are preserved.
        Only pure placeholder tokens ('RESERVE', 'BLANK', 'リザーブ', '使用禁止', 'Unused',
        '0x...', 'Item 0x...') are identified as placeholders.
        """
        if not name:
            return True
        s = name.strip()
        # Exact placeholder names
        if s.upper() in ("RESERVE", "BLANK", "----------", "使用禁止", "UNUSED", "UNUSED ITEM", "空栏"):
            return True
        if "リザーブ" in s:
            return True
        if s.startswith("Item 0x") or s.startswith("item_"):
            return True
        if re.match(r"^0x[0-9A-Fa-f]+$", s):
            return True
        # Check name before any parenthetical character tag (e.g. "RESERVE (Joker)")
        base_name = s.split(" (")[0].strip()
        if base_name.upper() in ("RESERVE", "BLANK", "使用禁止", "UNUSED"):
            return True
        return False

    TOOL_OFFSET_BY_DB_ID = {
        0x6001: 0x2547,  # Vanish Ball
        0x6002: 0x2594,  # Spotlight
        0x6003: 0x2595,  # Goho-M
        0x6005: 0x2597,  # Smokescreen
        0x6007: 0x2599,  # Hypno Mist
        0x6008: 0x259A,  # Calming Aroma
        0x6009: 0x259B,  # Covertizer
        0x600B: 0x259D,  # Silk Yarn
        0x600C: 0x259E,  # Thick Parchment
        0x600D: 0x259F,  # Tin Clasp
        0x600E: 0x25A0,  # Plant Balm
        0x600F: 0x25A1,  # Cork Bark
        0x6010: 0x25A2,  # Iron Sand
        0x6011: 0x25A3,  # Condenser Lens
        0x6012: 0x25A4,  # Aluminum Sheet
        0x6013: 0x25A5,  # Tanned Leather
        0x6014: 0x25A6,  # Red Phosphorus
        0x6015: 0x25A7,  # Liquid Mercury
        0x6017: 0x25CD,  # Element Set
        0x6018: 0x25CE,  # Forces Set
        0x6019: 0x25EB,  # Limelight
        0x601A: 0x2680,  # Lockpick
        0x601B: 0x2681,  # Perma-Pick
        0x601C: 0x2682,  # Reserve Ammo
        0x601E: 0x2684,  # Megido Bomb
    }

    @staticmethod
    def get_item_count_offset(item_id: int) -> int:
        """Resolve memory offset in master item count table.

        Stackable paradigms:
          - 0x2000 Consumables (0x2530 / 0x25AA / 0x2600 sub-ranges)
          - 0x3000 Accessories (0x2330 + idx)
          - 0x4000 Skill Cards (0x2E30 + idx)
          - 0x6000 Infiltration Tools (TOOL_OFFSET_BY_DB_ID)
          - 0x8000 Treasure / Materials (0x2A30 + idx)
        Unique Gear (0x1000 Melee, 0x5000 Protector, 0x7000 Ranged) return 0.
        """
        prefix = item_id & 0xF000
        idx = item_id & 0x0FFF
        if prefix == 0x2000:  # Consumables — verified sub-bases
            if idx <= 0x60:  # Medicines & Battle Items (0x2001..0x2060)
                return 0x2530 + idx
            elif 0x70 <= idx <= 0x85:  # Gym & Workout Proteins
                return 0x25AA + idx
            elif idx > 0x85:
                return 0x2600 + idx
            return 0
        elif prefix == 0x3000:  # Accessories — stackable count byte (0x2330 + idx)
            return SaveEditor.PC31_ACCESSORY_OWNED_BASE + idx
        elif prefix == 0x5000:  # Protectors / Armor — stackable count byte (0x1F30 + idx)
            return SaveEditor.PC31_PROTECTOR_OWNED_BASE + idx
        elif prefix == 0x4000:  # Skill Cards — verified engine base (0x2E30 + idx)
            return 0x2E30 + idx
        elif prefix == 0x6000:  # Infiltration Tools — direct memory mapping
            return SaveEditor.TOOL_OFFSET_BY_DB_ID.get(item_id, 0)
        elif prefix == 0x8000:  # Treasure/Materials — verified engine base (0x2A30 + idx)
            return 0x2A30 + idx
        elif prefix == 0x9000:  # Key Items & Essentials — verified engine offsets (0x2576..0x2A2F)
            return KEY_ITEM_OFFSET_BY_DB_ID.get(item_id, 0)
        return 0

    @staticmethod
    def get_item_owned_offset(item_id: int) -> int:
        """Resolve the equipment OWNED-flag byte for unique gear (Melee, Ranged).

        Bases:
          - Melee (0x1000): 0x1B30 + idx
          - Ranged (0x7000): 0x3430 + save_idx
        Accessories (0x3000) and Protectors (0x5000) are stackable count bytes handled by get_item_count_offset().
        """
        prefix = item_id & 0xF000
        idx = item_id & 0x0FFF
        if prefix == 0x1000:  # Melee (verified, 3 points)
            return SaveEditor.PC31_MELEE_OWNED_BASE + idx
        if prefix == 0x7000:  # Ranged (verified mechanism)
            save_idx = SaveEditor.RANGED_SAVE_IDX_BY_DB_ID.get(item_id)
            if save_idx is not None:
                return SaveEditor.PC31_RANGED_OWNED_BASE + save_idx
            return 0  # unverified ranged id -> do not guess
        if prefix == 0xA000:  # Outfits & Costumes (0x3230 + idx)
            return 0x3230 + idx
        return 0

    # ------------------------------------------------------------------
    # S1 normalized inventory model (INVENTORY_SPEC.md S1)
    # ------------------------------------------------------------------
    def get_normalized_inventory(self) -> Dict[str, Any]:
        """Truthful inventory read — one canonical source per item.

        Returns dict with:
          owned_gear: {item_id: bool} — melee/protector/accessory/ranged flags
          stacks: {item_id: int 0..99} — consumable/tool counts
          key_flags: {item_id: flag} — placeholder (S4 guarded)
          unknown: [item_id] — unmapped ranged ids surfaced, not edited
          conflicts: [{item_id, count_region, quick_array, winner}]
          mirror_mismatches: [{offset, primary, mirror, item_id}]
        Count-region (0x2410..0x2800) is canonical; 30-slot quick-array is
        only diagnostic (surfaced as conflicts, never merged). Mirror
        +0x18510 mismatches are reported, not silently tolerated.
        """
        out: Dict[str, Any] = {
            "owned_gear": {}, "stacks": {}, "key_flags": {},
            "unknown": [], "conflicts": [], "mirror_mismatches": [],
        }
        if not self.is_real_save():
            return out
        d = self.parser.data_payload
        delta = self.PC31_MIRROR_DELTA

        # Probe the reference item universe if available; fallback to
        # scanning the sparse count region for any nonzero byte so tests
        # with synthetic payloads and no server import still work.
        probe_ids: List[int] = []
        try:
            import server  # type: ignore
            ref_items = getattr(server, "REFERENCE_DB", {}).get("items", [])
            probe_ids = [it.get("id", 0) for it in ref_items if it.get("id", 0)]
        except Exception:
            probe_ids = []
        # Always also probe raw count offsets for 0x2000/0x6000 so synthetic
        # payloads without REFERENCE_DB still surface counts.
        # Probe stackable/count paradigms: Consumables (0x2000), Accessories (0x3000), SkillCards (0x4000), Protectors (0x5000), Tools (0x6000), Treasure (0x8000), KeyItems (0x9000)
        raw_stack_ids: List[int] = []
        for iid in probe_ids:
            if (iid & 0xF000) in (0x2000, 0x3000, 0x4000, 0x5000, 0x6000, 0x8000, 0x9000):
                raw_stack_ids.append(iid)
        # If no REFERENCE_DB, fall back to brute sparse scan of known count sub-bases
        if not raw_stack_ids:
            for idx in range(1, 0x300):
                cand = 0x2000 | idx
                off = self.get_item_count_offset(cand)
                if off and off < len(d) and d[off] > 0:
                    raw_stack_ids.append(cand)
            for idx in range(1, 0x200):
                cand = 0x3000 | idx
                off = self.get_item_count_offset(cand)
                if off and off < len(d) and d[off] > 0:
                    raw_stack_ids.append(cand)
            for idx in range(1, 0x200):
                cand = 0x5000 | idx
                off = self.get_item_count_offset(cand)
                if off and off < len(d) and d[off] > 0:
                    raw_stack_ids.append(cand)
            for idx in range(1, 0x200):
                cand = 0x6000 | idx
                off = self.get_item_count_offset(cand)
                if off and off < len(d) and d[off] > 0:
                    raw_stack_ids.append(cand)
            for idx in range(1, 0x300):
                cand = 0x4000 | idx
                off = self.get_item_count_offset(cand)
                if off and off < len(d) and d[off] > 0:
                    raw_stack_ids.append(cand)
            for idx in range(1, 0x200):
                cand = 0x8000 | idx
                off = self.get_item_count_offset(cand)
                if off and off < len(d) and d[off] > 0:
                    raw_stack_ids.append(cand)
            for cand, off in KEY_ITEM_OFFSET_BY_DB_ID.items():
                if off < len(d) and d[off] > 0:
                    raw_stack_ids.append(cand)

        for iid in raw_stack_ids:
            off = self.get_item_count_offset(iid)
            if not off or off >= len(d):
                continue
            qty = d[off]
            mirror_off = off + delta
            mirror_qty = d[mirror_off] if mirror_off < len(d) else None
            if mirror_qty is not None and mirror_qty != qty:
                out["mirror_mismatches"].append({
                    "offset": off, "primary": qty, "mirror": mirror_qty,
                    "item_id": iid,
                })
            if qty > 0 or (mirror_qty is not None and mirror_qty > 0):
                # canonical is primary; clamp 0..99 on read
                clamped = max(0, min(int(qty), 99))
                if clamped > 0:
                    name, _ = self._resolve_item_info(iid)
                    if not self.is_placeholder_item(name):
                        out["stacks"][iid] = clamped

        # Unique Gear: owned-flag bytes (Melee 0x1000, Ranged 0x7000, Outfits 0xA000)
        probe_gear_ids: List[int] = []
        if probe_ids:
            probe_gear_ids = [i for i in probe_ids
                              if (i & 0xF000) in (0x1000, 0x7000, 0xA000)]
        else:
            # Synthetic fallback: scan owned-flag regions for nonzero flags
            for base, prefix in ((self.PC31_MELEE_OWNED_BASE, 0x1000),
                                 (0x3230, 0xA000)):
                for idx in range(0x300):
                    off = base + idx
                    if off < len(d) and d[off] in (1, 0):
                        if d[off] == 1:
                            probe_gear_ids.append(prefix | idx)
            # Ranged via map keys only (unknown otherwise)
            for db_id in self.RANGED_SAVE_IDX_BY_DB_ID:
                probe_gear_ids.append(db_id)

        seen_gear: set = set()
        for iid in probe_gear_ids:
            if iid in seen_gear:
                continue
            seen_gear.add(iid)
            prefix = iid & 0xF000
            # Unmapped ranged -> unknown, never read as bool
            if prefix == 0x7000 and iid not in self.RANGED_SAVE_IDX_BY_DB_ID:
                if iid not in out["unknown"]:
                    # Only surface if REFERENCE_DB would have exposed it;
                    # for synthetic payloads, only surface known map-misses
                    # when explicitly probed.
                    pass
                continue
            owned_off = self.get_item_owned_offset(iid)
            if not owned_off or owned_off >= len(d):
                # Genuinely unmapped (e.g. ranged 0x7001) -> unknown
                if prefix == 0x7000 and iid not in out["unknown"]:
                    out["unknown"].append(iid)
                continue
            flag = d[owned_off]
            mirror_off = owned_off + delta
            mirror_flag = d[mirror_off] if mirror_off < len(d) else None
            if mirror_flag is not None and mirror_flag != flag:
                out["mirror_mismatches"].append({
                    "offset": owned_off, "primary": flag,
                    "mirror": mirror_flag, "item_id": iid,
                })
            is_owned = flag == 1
            # Only surface owned gear (S1: flag 0x01 -> Owned, 0x00 -> not)
            # but record the bool for the caller.
            name, _ = self._resolve_item_info(iid)
            if self.is_placeholder_item(name):
                continue
            if is_owned:
                out["owned_gear"][iid] = True
            else:
                # Report Not owned as False so UI can render ◇; tests check.
                # Only include if the id was in the probe universe (avoid
                # flooding with 0x300 zeros). We include False for probed ids.
                if iid in probe_gear_ids:
                    out["owned_gear"][iid] = False

        # Quick-array conflicts: read 30-slot ring and compare to canonical
        for slot in range(self.PC31_INVENTORY_SLOTS):
            off_ring = self.PC31_RING_BUFFER_BASE + slot * 4
            off_qty = self.PC31_INVENTORY_BASE + slot * self.PC31_INVENTORY_STRIDE
            if off_ring + 4 > len(d) or off_qty >= len(d):
                continue
            iid = struct.unpack_from("<H", d, off_ring)[0]
            if iid == 0 or (iid & 0xF000) not in self.CATEGORY_MAP:
                continue
            quick_qty = d[off_qty]
            if quick_qty == 0 and iid != 0:
                # quick slot holds id but zero qty -> stale residue vs empty
                # Only surface if canonical also empty (otherwise phantom)
                pass
            # Compare to canonical stacks / gear
            canon = None
            prefix = iid & 0xF000
            if prefix in (0x2000, 0x3000, 0x4000, 0x5000, 0x6000, 0x8000):
                canon = out["stacks"].get(iid, 0)
            elif prefix in (0x1000, 0x7000, 0xA000):
                canon = 1 if out["owned_gear"].get(iid, False) else 0
            if canon is not None and quick_qty != canon:
                # quick has a qty but canonical disagrees (or zero)
                if iid not in [c["item_id"] for c in out["conflicts"]]:
                    out["conflicts"].append({
                        "item_id": iid, "count_region": canon,
                        "quick_array": quick_qty, "winner": "count_region",
                    })

        # Surface unmapped ranged ids that appear in quick-array as unknown
        for slot in range(self.PC31_INVENTORY_SLOTS):
            off_ring = self.PC31_RING_BUFFER_BASE + slot * 4
            if off_ring + 4 > len(d):
                continue
            iid = struct.unpack_from("<H", d, off_ring)[0]
            if (iid & 0xF000) == 0x7000 and self.get_item_owned_offset(iid) == 0:
                if iid not in out["unknown"]:
                    out["unknown"].append(iid)
        # Also any probed ranged not in map
        for iid in probe_gear_ids:
            if (iid & 0xF000) == 0x7000 and self.get_item_owned_offset(iid) == 0:
                if iid not in out["unknown"]:
                    out["unknown"].append(iid)

        return out

    def get_inventory(self) -> List[Dict[str, Any]]:
        """Legacy flat inventory read — delegates to normalized model.

        Preserved for backwards compat (server.py / tests / web-app).
        Now canonical: gear is owned-flag, consumables are count-region;
        quick-array is NOT merged (conflicts surfaced in normalized model).
        """
        norm = self.get_normalized_inventory()
        out: List[Dict[str, Any]] = []
        # Stacks (consumables/tools/protectors/accessories/skillcards/treasure) -> quantity entries
        for iid, qty in norm.get("stacks", {}).items():
            if qty <= 0:
                continue
            name, cat = self._resolve_item_info(iid)
            if self.is_placeholder_item(name):
                continue
            out.append({"slot": len(out), "item_id": iid, "name": name,
                        "category": cat, "quantity": qty, "active": True})
        # Owned gear (melee, ranged, outfits) -> quantity 1 entries (for legacy callers)
        for iid, owned in norm.get("owned_gear", {}).items():
            if not owned:
                continue
            name, cat = self._resolve_item_info(iid)
            if self.is_placeholder_item(name):
                continue
            out.append({"slot": len(out), "item_id": iid, "name": name,
                        "category": cat, "quantity": 1, "active": True,
                        "owned": True})
        return out

    def set_item_quantity(self, item_id: int, quantity: int = 1) -> Dict[str, Any]:
        """Paradigm-correct write — routes by category.

        Stacks (0x2000/0x3000/0x4000/0x5000/0x6000/0x8000): sets count byte + mirror (clamped 0..99).
        Unique Gear (0x1000/0x7000/0xA000): sets owned-flag byte + mirror
        (1=owned, 0=cleared) — count byte is NOT touched for gear.
        """
        if not self.is_real_save():
            return {"status": "noop", "message": "PC payload required"}
        name, _ = self._resolve_item_info(item_id)
        if self.is_placeholder_item(name):
            return {"status": "unsupported",
                    "message": f"Item 0x{item_id:04X} ({name}) is a placeholder/RESERVE entry — refusing."}
        prefix = item_id & 0xF000
        # Gear -> owned flag path (clears on 0, sets on >0)
        if prefix in (0x1000, 0x7000, 0xA000):
            owned_off = self.get_item_owned_offset(item_id)
            if owned_off == 0:
                return {"status": "unsupported",
                        "message": f"Item 0x{item_id:04X} not in verified owned map — refusing."}
            d = bytearray(self.parser.data_payload)
            is_owned = max(0, min(int(quantity), 99)) > 0
            if owned_off < len(d):
                d[owned_off] = 1 if is_owned else 0
                mo = owned_off + self.PC31_MIRROR_DELTA
                if mo < len(d):
                    d[mo] = 1 if is_owned else 0
            self.parser.data_payload = bytes(d)
            return {"status": "success", "item_id": item_id, "owned": is_owned}
        # Stacks -> count path
        off = self.get_item_count_offset(item_id)
        if off == 0:
            return {"status": "unsupported",
                    "message": f"Item 0x{item_id:04X} has no verified count offset — refusing."}
        d = bytearray(self.parser.data_payload)
        q = max(0, min(int(quantity), 99))
        if off < len(d):
            d[off] = q
            mo = off + self.PC31_MIRROR_DELTA
            if mo < len(d):
                d[mo] = q
        self.parser.data_payload = bytes(d)
        return {"status": "success", "item_id": item_id, "quantity": q, "owned": False}

    def set_inventory_slot(self, slot: int, item_id: int, quantity: int = 1) -> Dict[str, Any]:
        """Legacy quick-array slot write — now delegates to paradigm-correct path.

        Quick-array bytes are legacy cache; writes still update it for
        backwards compat but the canonical write is via set_item_quantity's
        paradigm routing (gear=owned, stack=count). No phantom merge on read.
        """
        if not self.is_real_save():
            return {"status": "noop", "message": "PC payload required"}
        # Paradigm-correct canonical write first
        res = self.set_item_quantity(item_id, quantity)
        # Also mirror to quick-array slot for legacy callers that enumerate slots
        d = bytearray(self.parser.data_payload)
        q = max(0, min(int(quantity), 99))
        if 0 <= slot < self.PC31_INVENTORY_SLOTS:
            off_qty = self.PC31_INVENTORY_BASE + slot * self.PC31_INVENTORY_STRIDE
            off_ring = self.PC31_RING_BUFFER_BASE + slot * 4
            if off_qty < len(d) and off_ring + 4 <= len(d):
                d[off_qty] = q
                struct.pack_into("<H", d, off_ring, max(0, item_id))
                struct.pack_into("<H", d, off_ring + 2, 1 if q > 0 else 0)
                self.parser.data_payload = bytes(d)
        return {"status": "success", "slot": slot, "item_id": item_id,
                "quantity": q, "owned": res.get("owned", False)}

    # -------------------------------------------------------------------------
    # Confidant Read/Write API
    # -------------------------------------------------------------------------

    def _confidant_entry(self, d: bytes, arcana_id: int) -> int:
        """Return the entry offset for an arcana id (scan by save id)."""
        name = list(CONFIDANT_ARCANA_MAP.keys())[list(CONFIDANT_ARCANA_MAP.values()).index(arcana_id)]
        save_ids = self.CONFIDANT_SAVE_ID.get(name, 0)
        if not isinstance(save_ids, (list, tuple)):
            save_ids = [save_ids]
        for i in range(23):
            off = self.PC31_OFFSET_CONFIDANTS + i * self.PC31_CONFIDANT_STRIDE
            if off + 16 > len(d):
                break
            eid = struct.unpack_from("<H", d, off + self.PC31_CONFIDANT_ID_OFF)[0]
            if eid in save_ids:
                return off
        return -1

    def get_confidant_ranks(self) -> Dict[str, Dict[str, Any]]:
        """Read all 23 confidants from the VERIFIED PC block @0x136A0.

        Entry: [6 pad][u16 save_id][u16 rank][u16 points][4 pad], stride 16.
        Verified in-game 2026-08-09 via rank-ramp probe (user read back
        per-arcana ranks 1..10 matching the probe exactly).
        """
        result = {}
        if self.is_real_save():
            d = self.parser.data_payload
            base = self.PC31_OFFSET_CONFIDANTS
            if len(d) >= base + 23 * self.PC31_CONFIDANT_STRIDE:
                for name, arcana_id in CONFIDANT_ARCANA_MAP.items():
                    off = self._confidant_entry(d, arcana_id)
                    if off < 0:
                        result[name] = {"arcana_id": arcana_id, "rank": 0,
                                        "points": 0, "unlocked": False,
                                        "romance": False}
                        continue
                    rank = struct.unpack_from("<H", d, off + self.PC31_CONFIDANT_RANK_OFF)[0]
                    pts = struct.unpack_from("<H", d, off + self.PC31_CONFIDANT_PTS_OFF)[0]
                    flags = struct.unpack_from("<H", d, off + 0)[0]
                    result[name] = {
                        "arcana_id": arcana_id,
                        "rank": rank,
                        "points": pts,
                        "unlocked": rank > 0,
                        "romance": bool(flags & 0x02),
                    }
                return result

        if 0x10010 in self.parser.blocks_raw:
            raw = self.parser.blocks_raw[0x10010]
            for name, arcana_id in CONFIDANT_ARCANA_MAP.items():
                offset = arcana_id * 8
                if offset + 8 <= len(raw):
                    rank, points = struct.unpack_from("<BB", raw, offset)
                    flags = struct.unpack_from("<H", raw, offset + 2)[0]
                    result[name] = {
                        "arcana_id": arcana_id,
                        "rank": rank,
                        "points": points,
                        "unlocked": bool(flags & 0x01),
                        "romance": bool(flags & 0x02),
                    }
        return result

    def set_confidant_rank(self, arcana_id: int, rank: int, points: Optional[int] = None,
                           romance: Optional[bool] = None,
                           auto_unlock: bool = False) -> Dict[str, Any]:
        """Set one confidant's rank (0-10) in the VERIFIED PC block.

        Bond-point preservation (2026-08-24, zamasu2020 bug report):
        when points is None and the requested rank equals the current rank,
        points are NOT touched — rewriting rank-threshold points was wiping
        players' accumulated bond surplus ("ready to rank up next visit"
        became "not a deep enough bond"). When raising rank, surplus is
        preserved via max(current, threshold) — matching in-game carryover.
        """
        rank = max(0, min(rank, 10))
        name = list(CONFIDANT_ARCANA_MAP.keys())[list(CONFIDANT_ARCANA_MAP.values()).index(arcana_id)]
        th = self.CONFIDANT_POINT_THRESHOLDS.get(name, {})
        write_points: Optional[int] = points
        if write_points is None and self.is_real_save():
            # Read current state; preserve surplus bond points whenever possible.
            cur = self.get_confidant_ranks().get(name)
            if cur and cur.get("unlocked"):
                cur_rank = int(cur.get("rank", 0))
                cur_pts = int(cur.get("points", 0))
                if rank == cur_rank:
                    write_points = cur_pts  # unchanged rank -> keep exact points
                elif rank > cur_rank:
                    write_points = max(cur_pts, th.get(rank, cur_pts))
                # rank < cur_rank (explicit lowering) falls through to threshold
        if write_points is None:
            # use game-accurate threshold for this arcana/rank if known
            if rank in th:
                write_points = th[rank]
        if self.is_real_save():
            d = bytearray(self.parser.data_payload)
            off = self._confidant_entry(d, arcana_id)
            if off < 0:
                if auto_unlock and rank > 0:
                    # Slot not yet initialized in this early save; allocate the first empty slot
                    for i in range(23):
                        cand_off = self.PC31_OFFSET_CONFIDANTS + i * self.PC31_CONFIDANT_STRIDE
                        eid = struct.unpack_from("<H", d, cand_off + self.PC31_CONFIDANT_ID_OFF)[0]
                        if eid == 0:
                            name = list(CONFIDANT_ARCANA_MAP.keys())[list(CONFIDANT_ARCANA_MAP.values()).index(arcana_id)]
                            save_id = self.CONFIDANT_SAVE_ID.get(name, 0)
                            if isinstance(save_id, (list, tuple)):
                                save_id = save_id[0]
                            struct.pack_into("<H", d, cand_off + self.PC31_CONFIDANT_ID_OFF, save_id)
                            off = cand_off
                            break
                else:
                    return {"status": "noop", "message": "Confidant not met yet; rank 0 left uninitialized"}
            if off < 0:
                return {"status": "noop", "message": "Confidant entry not found (locked?)"}
            if rank == 0:
                # Revert slot to completely unallocated (all 16 bytes zero) so in-game menu hides them
                for b_i in range(self.PC31_CONFIDANT_STRIDE):
                    d[off + b_i] = 0
                romance_state = False
            else:
                struct.pack_into("<H", d, off + self.PC31_CONFIDANT_RANK_OFF, rank)
                if write_points is not None:
                    struct.pack_into("<H", d, off + self.PC31_CONFIDANT_PTS_OFF,
                                     max(0, min(write_points, 0xFFFF)))
                cur_flags = struct.unpack_from("<H", d, off + 0)[0]
                cur_flags |= 0x01
                if romance is True:
                    cur_flags |= 0x02
                elif romance is False:
                    cur_flags &= ~0x02
                struct.pack_into("<H", d, off + 0, cur_flags)
                romance_state = bool(cur_flags & 0x02)
            self.parser.data_payload = bytes(d)
            return {"status": "success", "arcana_id": arcana_id, "rank": rank,
                    "points": write_points if rank > 0 else 0, "romance": romance_state}

        if 0x10010 in self.parser.blocks_raw:
            raw = bytearray(self.parser.blocks_raw[0x10010])
            offset = arcana_id * 8
            if offset + 8 <= len(raw):
                raw[offset] = rank
                if write_points is not None:
                    raw[offset + 1] = max(0, min(write_points, 255))
                flags = struct.unpack_from("<H", raw, offset + 2)[0]
                flags |= 0x01
                if romance is True:
                    flags |= 0x02
                elif romance is False:
                    flags &= ~0x02
                struct.pack_into("<H", raw, offset + 2, flags)
                self.parser.blocks_raw[0x10010] = bytes(raw)
                return {"status": "success", "arcana_id": arcana_id, "rank": rank, "romance": bool(flags & 0x02)}
        return {"status": "noop", "message": "Confidants not updated."}

    def set_all_confidants_rank(self, rank: int = 10, romance_all: bool = False) -> Dict[str, Any]:
        """Set every confidant to a rank (default 10)."""
        count = 0
        for arcana_id in CONFIDANT_ARCANA_MAP.values():
            romance = romance_all if arcana_id in ROMANCEABLE_CONFIDANTS else None
            if self.set_confidant_rank(arcana_id, rank, None, romance).get("status") == "success":
                count += 1
        return {"status": "success", "confidants_updated": count,
                "message": f"Set {count} confidants to Rank {rank}."}

    # -------------------------------------------------------------------------
    # Party Stats API
    # -------------------------------------------------------------------------

    PARTY_PERSONA_EVOLUTIONS = {
        1: {"name": "Ryuji",   1: (0x00CA, "Captain Kidd"), 2: (0x00D4, "Seiten Taisei"), 3: (0x00F2, "William")},
        2: {"name": "Morgana", 1: (0x00CB, "Zorro"),        2: (0x00D5, "Mercurius"),     3: (0x00F3, "Diego")},
        3: {"name": "Ann",     1: (0x00CC, "Carmen"),       2: (0x00E9, "Hecate"),        3: (0x00F4, "Celestine")},
        4: {"name": "Yusuke",  1: (0x00CD, "Goemon"),       2: (0x00EA, "Kamu Susano-o"), 3: (0x00F5, "Gorokichi")},
        5: {"name": "Makoto",  1: (0x00CE, "Johanna"),      2: (0x00EB, "Anat"),          3: (0x00F6, "Agnes")},
        6: {"name": "Haru",    1: (0x00CF, "Milady"),       2: (0x00EC, "Astarte"),       3: (0x00F7, "Lucy")},
        7: {"name": "Futaba",  1: (0x00D0, "Necronomicon"), 2: (0x00ED, "Prometheus"),    3: (0x00F8, "Al Azif")},
        8: {"name": "Akechi",  1: (0x00D1, "Robin Hood"),   2: (0x00D2, "Loki"),          3: (0x00F9, "Hereward")},
        9: {"name": "Kasumi",  1: (0x00F0, "Cendrillon"),   2: (0x00F1, "Vanadis"),       3: (0x00FA, "Ella")},
    }

    def set_party_persona_evolution(self, slot: int, tier: int) -> Dict[str, Any]:
        """Equip the corresponding evolutionary Tier (1=Base, 2=Awakened, 3=Royal) persona for a teammate."""
        if slot not in self.PARTY_PERSONA_EVOLUTIONS:
            return {"status": "invalid", "message": f"Slot {slot} is not a valid teammate evolution slot."}
        if tier not in (1, 2, 3):
            return {"status": "invalid", "message": "Evolution tier must be 1 (Base), 2 (Awakened), or 3 (Royal)."}
        if not self.is_member_joined(slot):
            return {"status": "invalid", "message": f"Member slot {slot} has not joined the party yet."}

        p_id, p_name = self.PARTY_PERSONA_EVOLUTIONS[slot][tier]
        if self.is_real_save():
            d = bytearray(self.parser.data_payload)
            offset = self.PC31_OFFSET_PARTY_BASE + slot * self.PC31_PARTY_STRIDE
            if offset + 0x3E > len(d):
                return {"status": "noop", "message": "Slot out of range"}
            # Persona ID @ +0x3A (u16)
            struct.pack_into("<H", d, offset + 0x3A, p_id)
            self.parser.data_payload = bytes(d)
            return {"status": "success", "slot": slot, "tier": tier, "persona_id": p_id, "persona_name": p_name}

        return {"status": "noop", "message": "Persona evolution only supported on PC saves."}

    def get_party_stats(self) -> List[Dict[str, Any]]:
        """Read party stats from the VERIFIED PC block @0x2C, stride 0x2B0."""
        PARTY_SLOT_NAMES = {
            0: "Joker", 1: "Ryuji", 2: "Morgana", 3: "Ann", 4: "Yusuke",
            5: "Makoto", 6: "Haru", 7: "Futaba", 8: "Akechi", 9: "Kasumi",
        }
        result = []
        if self.is_real_save():
            d = self.parser.data_payload
            for i in range(10):
                offset = self.PC31_OFFSET_PARTY_BASE + i * self.PC31_PARTY_STRIDE
                if offset + 0x40 > len(d):
                    break
                hp = struct.unpack_from("<H", d, offset + self.PC31_PARTY_HP_OFF)[0]
                sp = struct.unpack_from("<H", d, offset + self.PC31_PARTY_SP_OFF)[0]
                if i == 0:
                    lv = struct.unpack_from("<H", d, offset + self.PC31_PARTY_LV_OFF_LEADER)[0]
                else:
                    lv = d[offset + self.PC31_PARTY_LV_OFF_MEMBER]  # u8 (persona-struct level)
                name = PARTY_SLOT_NAMES.get(i, f"slot{i}")
                joined = i == 0 or self.is_member_joined(i)
                result.append({
                    "slot": i,
                    "name": name if joined else "???",
                    "level": lv,
                    "hp": hp,
                    "sp": sp,
                    "max_hp": None,  # not yet located
                    "max_sp": None,  # not yet located
                    "joined": joined,
                    "status": "verified",
                })
            return result

        if 0x10002 in self.parser.blocks_raw:
            raw = self.parser.blocks_raw[0x10002]
            for i in range(10):
                offset = i * 32
                if offset + 32 <= len(raw):
                    lvl, hp, sp, max_hp, max_sp = struct.unpack_from("<HHHHH", raw, offset)
                    result.append({"slot": i, "name": f"slot{i}", "level": lvl, "hp": hp, "sp": sp, "max_hp": max_hp, "max_sp": max_sp})
        return result

    def set_party_stat(self, slot: int, level: Optional[int] = None, hp: Optional[int] = None,
                       sp: Optional[int] = None, max_hp: Optional[int] = None,
                       max_sp: Optional[int] = None) -> Dict[str, Any]:
        """Set one party member's level / HP / SP (VERIFIED PC block @0x2C).

        HP u16 @+0, SP u16 @+4; LV @+0xC (leader) or @+0x3C (member).
        max_hp/max_sp accepted for API compat but not yet located in the
        PC layout — they are ignored with a note until mapped.
        """
        if self.is_real_save():
            if not self.is_member_joined(slot):
                return {"status": "invalid",
                        "message": f"Member slot {slot} has not joined the party yet — refusing edit (unsafe before they join)."}
            d = bytearray(self.parser.data_payload)
            offset = self.PC31_OFFSET_PARTY_BASE + slot * self.PC31_PARTY_STRIDE
            if offset + 0x40 > len(d):
                return {"status": "noop", "message": "Slot out of range"}
            hp_ = struct.unpack_from("<H", d, offset + self.PC31_PARTY_HP_OFF)[0]
            sp_ = struct.unpack_from("<H", d, offset + self.PC31_PARTY_SP_OFF)[0]
            lv_off = self.PC31_PARTY_LV_OFF_LEADER if slot == 0 else self.PC31_PARTY_LV_OFF_MEMBER
            if slot == 0:
                lvl_ = struct.unpack_from("<H", d, offset + lv_off)[0]
            else:
                lvl_ = d[offset + lv_off]  # u8 — persona-struct level
            lvl = level if level is not None else lvl_
            cur_hp = hp if hp is not None else hp_
            cur_sp = sp if sp is not None else sp_
            if max_hp is not None or max_sp is not None:
                return {"status": "partial", "message": "max_hp/max_sp not yet located in PC layout",
                        "applied": False, "level": lvl, "hp": cur_hp, "sp": cur_sp}
            struct.pack_into("<H", d, offset + self.PC31_PARTY_HP_OFF, max(0, min(cur_hp, 999)))
            struct.pack_into("<H", d, offset + self.PC31_PARTY_SP_OFF, max(0, min(cur_sp, 999)))
            from core.exp_curve import get_p5r_min_exp_for_level
            target_exp = get_p5r_min_exp_for_level(lvl)
            if slot == 0:
                struct.pack_into("<H", d, offset + lv_off, max(1, min(lvl, 99)))
                # Joker EXP @ +0x10 (u32)
                struct.pack_into("<I", d, offset + 0x10, target_exp)
            else:
                # u8 write only — a u16 write here clobbers +0x3D (the
                # persona struct's unk byte). Verified 2026-08-16.
                d[offset + lv_off] = max(1, min(lvl, 99))
                # Teammate EXP @ +0x18 (u32)
                if offset + 0x1C <= len(d):
                    struct.pack_into("<I", d, offset + 0x18, target_exp)
            self.parser.data_payload = bytes(d)
            return {"status": "success", "slot": slot, "level": lvl, "hp": cur_hp, "sp": cur_sp,
                    "exp": target_exp, "max_hp": None, "max_sp": None}

        if 0x10002 not in self.parser.blocks_raw:
            return {"status": "noop", "message": "Party block 0x10002 not found."}
        raw = bytearray(self.parser.blocks_raw[0x10002])
        offset = slot * 32
        if offset + 32 > len(raw):
            return {"status": "noop", "message": f"Slot {slot} out of range."}
        lvl, hp_, sp_, max_hp, max_sp = struct.unpack_from("<HHHHH", raw, offset)
        if level is not None:
            lvl = max(1, min(level, 99))
        if hp is not None:
            hp_ = max(1, min(hp, 999))
        if sp is not None:
            sp_ = max(1, min(sp, 999))
        if max_hp is not None:
            max_hp = max(1, min(max_hp, 999))
        if max_sp is not None:
            max_sp = max(1, min(max_sp, 999))
        struct.pack_into("<HHHHH", raw, offset, lvl, hp_, sp_, max_hp, max_sp)
        self.parser.blocks_raw[0x10002] = bytes(raw)
        return {"status": "success", "slot": slot, "level": lvl, "hp": hp_, "sp": sp_, "max_hp": max_hp, "max_sp": max_sp}

    def repair_romance_flags(self, target_arcana_id: Optional[int] = None, romance_state: bool = False) -> Dict[str, Any]:
        """Clean romance flags.

        PC (0x31) saves: romance flags are not mapped — this returns
        unsupported instead of silently doing nothing.
        """
        if self.is_real_save():
            return {"status": "unsupported",
                    "message": "Romance flags are not mapped on PC saves (0x31)."}
        targets = [target_arcana_id] if target_arcana_id is not None else ROMANCEABLE_CONFIDANTS
        for arc_id in targets:
            self.set_confidant_rank(arc_id, 10, None, romance=romance_state)
        return {"repaired_confidants": len(targets), "message": f"Updated romance flags for {len(targets)} confidants."}

    def rebalance_stats(self) -> Dict[str, Any]:
        """Normalizes HP/SP back to level caps."""
        count = 0
        if 0x10002 in self.parser.blocks_raw:
            raw = bytearray(self.parser.blocks_raw[0x10002])
            for i in range(10):
                offset = i * 32
                if offset + 32 <= len(raw):
                    lvl, hp, sp, max_hp, max_sp = struct.unpack_from("<HHHHH", raw, offset)
                    if max_hp > 700 or max_sp > 500:
                        calc_hp = min(700, 120 + (lvl * 6))
                        calc_sp = min(500, 80 + (lvl * 4))
                        struct.pack_into("<HHHHH", raw, offset, lvl, calc_hp, calc_sp, calc_hp, calc_sp)
                        count += 1
            self.parser.blocks_raw[0x10002] = bytes(raw)

        if self.is_real_save():
            party = self.get_party_stats()
            # PC layout: max HP/SP are derived from level+persona, not stored.
            if any(entry.get("max_hp") is None for entry in party):
                return {"status": "unsupported",
                        "normalized_party_count": count,
                        "message": "Rebalance not available on PC saves: max HP/SP are derived in-game, not stored."}
            for entry in party:
                slot = entry["slot"]
                lvl = entry["level"]
                max_hp = entry["max_hp"]
                max_sp = entry["max_sp"]
                if max_hp > 700 or max_sp > 500:
                    calc_hp = min(700, 120 + (lvl * 6))
                    calc_sp = min(500, 80 + (lvl * 4))
                    self.set_party_stat(slot, level=lvl, hp=calc_hp, sp=calc_sp, max_hp=calc_hp, max_sp=calc_sp)
                    count += 1

        return {"normalized_party_count": count, "message": f"Re-balanced HP/SP for {count} characters."}

    def rebind_steam_id(self, new_steam_id64: int) -> Dict[str, Any]:
        """Re-binds save header to a new 64-bit Steam ID.

        PC (0x31) saves: the SteamID location is not mapped — returns
        unsupported instead of silently doing nothing.
        """
        if self.is_real_save():
            return {"status": "unsupported",
                    "message": "SteamID location not mapped on PC saves (0x31)."}
        if 0x10000 in self.parser.blocks_raw:
            raw = bytearray(self.parser.blocks_raw[0x10000])
            if len(raw) >= 8:
                struct.pack_into("<Q", raw, 0, new_steam_id64)
                self.parser.blocks_raw[0x10000] = bytes(raw)
        return {"steam_id64": new_steam_id64, "status": "success", "message": f"Re-bound to SteamID64: {new_steam_id64}"}
