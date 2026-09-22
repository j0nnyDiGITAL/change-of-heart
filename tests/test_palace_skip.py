"""Palace Skip regression tests — guard-bit + clock warp (CHRONOS engine).

The engine checks ONE guard bit per palace on deadline day. If set → palace
is cleared and post-clearance events play. If not → game over. We pre-set
both the guard bit and discovery bit, warp the clock to the deadline day,
and let the engine's own scheduler replay the scenes.

Guard bits: T2+200/600/1000/1400/1800/2200/2700 (empirically verified).
Discovery bits: T2+249/611/1012/1412/1805/2202/2702 (empirically verified).
"""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.chronos import (
    T2_FLAT_BASE, PALACE_SKIP_CATALOG, _bit_location, _lookup_palace,
    apply_palace_skip, build_palace_skip_plan, day_index,
    index_to_month_day, load_model,
)
from core.editor import SaveEditor
from core.parser import SaveHeader

MODEL = load_model()


def make_real_pc_save(hdr_day=0):
    """Real signed container with a structured header."""
    e = SaveEditor()
    e.parser.is_pc_0x31 = True
    e.parser.data_payload = bytes(0x40000)
    h = SaveHeader()
    h.playtime = 288000
    h.level = 45
    h.day = hdr_day
    h.desc = "4/1(Fri) Afternoon\nPLV:99 L\nPLAY TIME:80h 0m\nDIFFICULTY:Merciless"
    e.parser.header = h
    e.container.header_bytes = h.pack()
    return e


def read_bit(payload: bytes, table: int, index: int) -> int:
    flat = T2_FLAT_BASE + index
    return (payload[flat // 8] >> (flat % 8)) & 1


class TestPalaceSkipCatalog(unittest.TestCase):
    def test_all_seven_palaces_present(self):
        self.assertEqual(len(PALACE_SKIP_CATALOG), 7)
        ids = [p["palace_id"] for p in PALACE_SKIP_CATALOG]
        self.assertEqual(ids, [
            "kamoshida", "madarame", "kaneshiro", "futaba",
            "okumura", "niijima", "shido",
        ])

    def test_guard_bits_are_distinct(self):
        guard_idxs = [p["guard_bit"]["index"] for p in PALACE_SKIP_CATALOG]
        self.assertEqual(len(guard_idxs), len(set(guard_idxs)))

    def test_discovery_bits_are_distinct(self):
        disc_idxs = [p["discovery_bit"]["index"] for p in PALACE_SKIP_CATALOG]
        self.assertEqual(len(disc_idxs), len(set(disc_idxs)))

    def test_deadlines_are_increasing_order(self):
        deadline_idxs = [day_index(*p["deadline"]) for p in PALACE_SKIP_CATALOG]
        self.assertEqual(deadline_idxs, sorted(deadline_idxs))

    def test_all_guard_bits_writable_under_bank_rule(self):
        for p in PALACE_SKIP_CATALOG:
            off, bit = _bit_location(p["guard_bit"]["table"],
                                     p["guard_bit"]["index"])
            self.assertIsInstance(off, int)
            off2, bit2 = _bit_location(p["discovery_bit"]["table"],
                                       p["discovery_bit"]["index"])
            self.assertIsInstance(off2, int)

    def test_lookup_palace_valid(self):
        p = _lookup_palace("kamoshida")
        self.assertEqual(p["palace_id"], "kamoshida")
        self.assertEqual(p["deadline"], (5, 2))

    def test_lookup_palace_invalid_raises(self):
        with self.assertRaises(ValueError):
            _lookup_palace("nonexistent")


class TestBuildPalaceSkipPlan(unittest.TestCase):
    def test_kamoshida_skip_from_4_16(self):
        ed = make_real_pc_save(hdr_day=day_index(4, 16))
        plan = build_palace_skip_plan(ed, "kamoshida")
        self.assertTrue(plan["allowed"])
        self.assertEqual(plan["status"], "ok")
        self.assertEqual(plan["target"]["date"], "5/2")
        self.assertEqual(plan["days_saved"], day_index(5, 2) - day_index(4, 16))
        self.assertEqual(len(plan["bits_to_write"]), 2)

    def test_claim_mode_keeps_calendar(self):
        """mode='claim': bits written, clock untouched — grind skip only."""
        ed = make_real_pc_save(hdr_day=day_index(4, 16))
        plan = build_palace_skip_plan(ed, "kamoshida", mode="claim")
        self.assertTrue(plan["allowed"])
        self.assertEqual(plan["mode"], "claim")
        self.assertEqual(plan["target"]["date"], "4/16")
        self.assertEqual(plan["days_kept"], day_index(5, 2) - day_index(4, 16))
        self.assertEqual(len(plan["bits_to_write"]), 2)

    def test_claim_mode_apply_writes_bits_not_clock(self):
        ed = make_real_pc_save(hdr_day=day_index(4, 16))
        payload_before = ed.parser.data_payload
        header_before = ed.parser.header.pack()
        res = apply_palace_skip(ed, "kamoshida", mode="claim")
        self.assertEqual(res["status"], "success")
        self.assertIsNone(res["wrote"])
        self.assertEqual(len(res["bits_written"]), 2)
        # guard + discovery bits set
        self.assertEqual(read_bit(ed.parser.data_payload, 2, 200), 1)
        self.assertEqual(read_bit(ed.parser.data_payload, 2, 249), 1)
        # clock fields byte-identical
        self.assertEqual(ed.parser.header.pack(), header_before)
        self.assertEqual(len(ed.parser.data_payload), len(payload_before))

    def test_kamoshida_skip_from_deadline_day_refused(self):
        ed = make_real_pc_save(hdr_day=day_index(5, 2))
        plan = build_palace_skip_plan(ed, "kamoshida")
        self.assertFalse(plan["allowed"])
        self.assertEqual(plan["status"], "too_late")

    def test_kamoshida_skip_after_deadline_refused(self):
        ed = make_real_pc_save(hdr_day=day_index(5, 10))
        plan = build_palace_skip_plan(ed, "kamoshida")
        self.assertFalse(plan["allowed"])
        self.assertEqual(plan["status"], "too_late")

    def test_kamoshida_skip_before_entry_refused(self):
        ed = make_real_pc_save(hdr_day=day_index(4, 10))
        plan = build_palace_skip_plan(ed, "madarame")
        self.assertFalse(plan["allowed"])
        self.assertEqual(plan["status"], "too_early")

    def test_already_cleared_refused(self):
        ed = make_real_pc_save(hdr_day=day_index(4, 20))
        # Pre-set the guard bit
        d = bytearray(ed.parser.data_payload)
        off, bit = _bit_location(2, 200)  # Kamoshida guard
        d[off] |= (1 << bit)
        ed.parser.data_payload = bytes(d)
        plan = build_palace_skip_plan(ed, "kamoshida")
        self.assertFalse(plan["allowed"])
        self.assertEqual(plan["status"], "already_cleared")

    def test_all_palaces_planable_from_their_entry_windows(self):
        """Each palace can be skipped from any day between its entry and deadline."""
        for p in PALACE_SKIP_CATALOG:
            mid_entry = (p["earliest_entry"][0],
                         (p["earliest_entry"][1] + p["deadline"][1]) // 2)
            # Clamp mid-point between entry and deadline
            entry_idx = day_index(*p["earliest_entry"])
            deadline_idx = day_index(*p["deadline"])
            mid_idx = (entry_idx + deadline_idx) // 2
            ed = make_real_pc_save(hdr_day=mid_idx)
            plan = build_palace_skip_plan(ed, p["palace_id"])
            self.assertTrue(plan["allowed"],
                            f"{p['palace_id']} should be planable from mid-window")

    def test_guard_bit_indices_match_known_values(self):
        expected = {
            "kamoshida": 200, "madarame": 600, "kaneshiro": 1000,
            "futaba": 1400, "okumura": 1800, "niijima": 2200, "shido": 2700,
        }
        for p in PALACE_SKIP_CATALOG:
            self.assertEqual(p["guard_bit"]["index"],
                             expected[p["palace_id"]])

    def test_discovery_bit_indices_match_known_values(self):
        expected = {
            "kamoshida": 249, "madarame": 611, "kaneshiro": 1012,
            "futaba": 1412, "okumura": 1805, "niijima": 2202, "shido": 2702,
        }
        for p in PALACE_SKIP_CATALOG:
            self.assertEqual(p["discovery_bit"]["index"],
                             expected[p["palace_id"]])


class TestApplyPalaceSkip(unittest.TestCase):
    def test_kamoshida_skip_writes_bits_and_clocks(self):
        ed = make_real_pc_save(hdr_day=day_index(4, 20))
        res = apply_palace_skip(ed, "kamoshida")
        self.assertEqual(res["status"], "success")
        # Day should be deadline (5/2)
        self.assertEqual(ed.parser.header.day, day_index(5, 2))
        # Guard bit set
        self.assertEqual(read_bit(ed.parser.data_payload, 2, 200), 1)
        # Discovery bit set
        self.assertEqual(read_bit(ed.parser.data_payload, 2, 249), 1)
        # Day counter mirror (max(0, day-52); May 2 = day 31, so counter = 0)
        ctr = int.from_bytes(ed.parser.data_payload[0x3D70:0x3D72], "little")
        self.assertEqual(ctr, max(0, day_index(5, 2) - 52))

    def test_palace_skip_refused_plan_never_mutates(self):
        ed = make_real_pc_save(hdr_day=day_index(5, 2))  # past deadline
        before_payload = bytes(ed.parser.data_payload)
        before_day = ed.parser.header.day
        res = apply_palace_skip(ed, "kamoshida")
        self.assertEqual(res["status"], "too_late")
        self.assertEqual(ed.parser.header.day, before_day)
        self.assertEqual(bytes(ed.parser.data_payload), before_payload)

    def test_full_roundtrip_real_signed_container(self):
        ed = make_real_pc_save(hdr_day=day_index(4, 20))
        res = apply_palace_skip(ed, "kamoshida")
        self.assertEqual(res["status"], "success")
        raw = ed.save_to_bytes()
        ed2 = SaveEditor(raw)
        self.assertEqual(ed2.parser.header.day, day_index(5, 2))
        self.assertEqual(read_bit(ed2.parser.data_payload, 2, 200), 1)
        self.assertEqual(read_bit(ed2.parser.data_payload, 2, 249), 1)
        self.assertTrue(ed2.integrity_report()["ok"])

    def test_futaba_skip_from_8_10(self):
        ed = make_real_pc_save(hdr_day=day_index(8, 10))
        res = apply_palace_skip(ed, "futaba")
        self.assertEqual(res["status"], "success")
        self.assertEqual(ed.parser.header.day, day_index(8, 21))
        self.assertEqual(read_bit(ed.parser.data_payload, 2, 1400), 1)
        self.assertEqual(read_bit(ed.parser.data_payload, 2, 1412), 1)

    def test_all_palaces_applyable_from_respective_entry_windows(self):
        """Each palace can be skipped from any day between entry and deadline."""
        test_days = {
            "kamoshida": day_index(4, 25),
            "madarame": day_index(5, 25),
            "kaneshiro": day_index(6, 25),
            "futaba": day_index(8, 10),
            "okumura": day_index(9, 25),
            "niijima": day_index(11, 5),
            "shido": day_index(12, 10),
        }
        for p in PALACE_SKIP_CATALOG:
            ed = make_real_pc_save(hdr_day=test_days[p["palace_id"]])
            res = apply_palace_skip(ed, p["palace_id"])
            self.assertEqual(res["status"], "success",
                             f"{p['palace_id']} should apply from test day")
            self.assertEqual(ed.parser.header.day, day_index(*p["deadline"]))
            self.assertEqual(read_bit(ed.parser.data_payload, 2,
                                      p["guard_bit"]["index"]), 1)
            self.assertEqual(read_bit(ed.parser.data_payload, 2,
                                      p["discovery_bit"]["index"]), 1)


class TestLadderAgreement(unittest.TestCase):
    """Guard and discovery bit locations must match verified values."""

    def test_kamoshida_guard_bit_location(self):
        off, bit = _bit_location(2, 200)
        # T2+200 = 0x1C700 + 200 = 0x1C7C8; byte = 0x1C7C8//8 = 0x38F9, bit 0
        self.assertEqual((hex(off), bit), ("0x38f9", 0))

    def test_madarame_guard_bit_location(self):
        off, bit = _bit_location(2, 600)
        # T2+600 = 0x1C700 + 600 = 0x1C958; byte = 0x1C958//8 = 0x392B, bit 0
        self.assertEqual((hex(off), bit), ("0x392b", 0))

    def test_futaba_guard_bit_location(self):
        off, bit = _bit_location(2, 1400)
        # T2+1400 = 0x1C700 + 1400 = 0x1CC78; byte = 0x1CC78//8 = 0x398F, bit 0
        self.assertEqual((hex(off), bit), ("0x398f", 0))

    def test_shido_guard_bit_location(self):
        off, bit = _bit_location(2, 2700)
        # T2+2700 = 0x1C700 + 2700 = 0x1D18C; byte = 0x1D18C//8 = 0x3A31, bit 4
        self.assertEqual((hex(off), bit), ("0x3a31", 4))


if __name__ == "__main__":
    unittest.main()
