"""CHRONOS warp v2 regression tests — branch-bit resolution (ADR 0004).

V2 resolves v1-blocked story windows through verified branch bits:
the engine replays skipped-window scenes on arrival; the save only pre-sets
the bits the scheduler checks. Bank rule: a bit is writable ONLY when its
byte transform is verified against the multi-slot save corpus
(T2 flat = 0x1C700 + idx, LSB0). Verified on the real pack 2026-09-21:
T2+1400 @0x398F.b0 and T2+1410 @0x3990.b2 — both era-perfect.
"""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.chronos import (BRANCH_WINDOWS, T2_FLAT_BASE, apply_time_travel,
                          apply_time_travel_v2, build_time_travel_plan,
                          build_time_travel_plan_v2, day_index, load_model)
from core.editor import SaveEditor
from core.parser import SaveHeader

MODEL = load_model()
FUTABA = next(w for w in BRANCH_WINDOWS if w["window_id"] == "futaba_awakening")


def make_real_pc_save(hdr_day=116):
    """Real signed container with a structured header (same recipe as
    tests/test_chronos.py / test_deadline_escape.py)."""
    e = SaveEditor()
    e.parser.is_pc_0x31 = True
    e.parser.data_payload = bytes(0x40000)
    h = SaveHeader()
    h.playtime = 288000
    h.level = 45
    h.day = hdr_day
    h.desc = "7/26(Tue) Afternoon,Futaba's Palace\nPLV:99 L\nPLAY TIME:80h 0m\nDIFFICULTY:Merciless"
    e.parser.header = h
    e.container.header_bytes = h.pack()
    return e


def read_bit(payload: bytes, table: int, index: int) -> int:
    flat = T2_FLAT_BASE + index
    return (payload[flat // 8] >> (flat % 8)) & 1


class TestBranchWindowCatalog(unittest.TestCase):
    def test_futaba_window_is_verified_with_two_bits(self):
        self.assertTrue(FUTABA["verified"])
        self.assertEqual(len(FUTABA["resolution_bits"]), 2)
        idxs = {b["index"] for b in FUTABA["resolution_bits"]}
        self.assertEqual(idxs, {1400, 1410})

    def test_every_window_bit_is_writable_under_bank_rule(self):
        # Any bit listed in a window marked verified must have a verified
        # transform — _bit_location raises for unverified tables.
        from core.chronos import _bit_location
        for w in BRANCH_WINDOWS:
            if not w.get("verified"):
                continue
            for b in w["resolution_bits"]:
                off, bit = _bit_location(b["table"], b["index"])
                self.assertIsInstance(off, int)

    def test_unverified_windows_exist_and_declare_themselves(self):
        for wid in ("okumura", "niijima", "shido", "councillor_gate"):
            w = next(x for x in BRANCH_WINDOWS if x["window_id"] == wid)
            self.assertFalse(w["verified"])
            self.assertEqual(w["resolution_bits"], [])


class TestPlanV2(unittest.TestCase):
    def test_clean_runway_unchanged_v1_semantics(self):
        v1 = build_time_travel_plan(MODEL, 116, 8, 20)
        v2 = build_time_travel_plan_v2(MODEL, 116, 8, 20)
        self.assertEqual(v1["status"], "ok")
        self.assertEqual(v2["status"], "ok")
        self.assertFalse(v2["v2"]["resolvable"])

    def test_v1_wall_day_now_resolvable(self):
        plan = build_time_travel_plan_v2(MODEL, 116, 8, 22)
        self.assertEqual(plan["status"], "blocked_resolvable")
        self.assertTrue(plan["v2"]["resolvable"])
        self.assertEqual(plan["v2"]["window_id"], "futaba_awakening")
        choice = plan["v2"]["branch_choices"][0]
        self.assertEqual(choice["kind"], "implied")
        self.assertEqual({b["index"] for b in choice["bits"]}, {1400, 1410})
        self.assertTrue(choice["label"].startswith("Futaba"))

    def test_arrival_target_8_21_also_resolvable(self):
        plan = build_time_travel_plan_v2(MODEL, 116, 8, 21)
        self.assertEqual(plan["status"], "blocked_resolvable")

    def test_mid_window_arrival_still_refused(self):
        plan = build_time_travel_plan_v2(MODEL, 116, 8, 25)
        self.assertEqual(plan["status"], "blocked")
        self.assertFalse(plan["v2"]["resolvable"])
        self.assertIn("arrival target", plan["v2"]["reason"])

    def test_unverified_window_refused_with_honest_reason(self):
        plan = build_time_travel_plan_v2(MODEL, 167, 10, 20)
        self.assertEqual(plan["status"], "blocked")
        self.assertFalse(plan["v2"]["resolvable"])
        self.assertIn("okumura", plan["v2"]["reason"])

    def test_envelope_and_forward_only_still_enforced(self):
        self.assertEqual(build_time_travel_plan_v2(MODEL, 116, 7, 25)["status"], "invalid")
        self.assertEqual(build_time_travel_plan_v2(MODEL, 116, 12, 25)["status"], "invalid")
        self.assertEqual(build_time_travel_plan_v2(MODEL, 116, 2, 3)["status"], "invalid")


class TestApplyV2(unittest.TestCase):
    def test_apply_v2_requires_choice_acknowledgement(self):
        ed = make_real_pc_save(hdr_day=116)
        res = apply_time_travel_v2(ed, MODEL, 8, 22)
        self.assertEqual(res["status"], "confirm_required")
        # nothing mutated
        self.assertEqual(ed.parser.header.day, 116)
        self.assertEqual(read_bit(ed.parser.data_payload, 2, 1400), 0)

    def test_apply_v2_writes_bits_and_clocks(self):
        ed = make_real_pc_save(hdr_day=116)
        res = apply_time_travel_v2(ed, MODEL, 8, 22,
                                   choice_ids=["futaba_awakening:cleared"])
        self.assertEqual(res["status"], "success")
        self.assertEqual(ed.parser.header.day, 143)  # 8/22
        self.assertEqual(read_bit(ed.parser.data_payload, 2, 1400), 1)
        self.assertEqual(read_bit(ed.parser.data_payload, 2, 1410), 1)
        ctr = int.from_bytes(ed.parser.data_payload[0x3D70:0x3D72], "little")
        self.assertEqual(ctr, 143 - 52)
        self.assertEqual(res["bits_written"][0]["byte_offset"], (T2_FLAT_BASE + 1400) // 8)

    def test_apply_v2_full_roundtrip_real_signed_container(self):
        ed = make_real_pc_save(hdr_day=116)
        res = apply_time_travel_v2(ed, MODEL, 8, 21,
                                   choice_ids=["futaba_awakening:cleared"])
        self.assertEqual(res["status"], "success")
        raw = ed.save_to_bytes()
        ed2 = SaveEditor(raw)
        self.assertEqual(ed2.parser.header.day, 142)  # 8/21
        self.assertTrue(ed2.get_quick_info()["day"].startswith("8/21"))
        self.assertEqual(read_bit(ed2.parser.data_payload, 2, 1400), 1)
        self.assertTrue(ed2.integrity_report()["ok"])

    def test_apply_v2_clean_runway_delegates_no_bits(self):
        ed = make_real_pc_save(hdr_day=116)
        res = apply_time_travel_v2(ed, MODEL, 8, 20)
        self.assertEqual(res["status"], "success")
        self.assertNotIn("bits_written", res)
        self.assertEqual(ed.parser.header.day, 141)

    def test_apply_v2_refused_plan_never_mutates(self):
        ed = make_real_pc_save(hdr_day=116)
        before = (ed.parser.header.day, bytes(ed.parser.data_payload))
        res = apply_time_travel_v2(ed, MODEL, 8, 25)
        self.assertEqual(res["status"], "blocked")
        self.assertEqual((ed.parser.header.day, bytes(ed.parser.data_payload)), before)

    def test_apply_v2_wrongs_choice_id_rejected(self):
        ed = make_real_pc_save(hdr_day=116)
        res = apply_time_travel_v2(ed, MODEL, 8, 22, choice_ids=["nope:whatever"])
        self.assertEqual(res["status"], "confirm_required")

    def test_v1_apply_still_works_for_clean_runway(self):
        # v1 API untouched — regression guard for existing callers/tests.
        ed = make_real_pc_save(hdr_day=116)
        res = apply_time_travel(ed, MODEL, 8, 20)
        self.assertEqual(res["status"], "success")
        self.assertEqual(ed.parser.header.day, 141)


class TestLadderAgreement(unittest.TestCase):
    """The window's bit ids must match the empirically verified locations."""

    def test_t2_transform_matches_corpus_anchors(self):
        # Ladder-verified: T2+1400 -> byte 0x398F bit 0; T2+1410 -> 0x3990 bit 2
        off, bit = (T2_FLAT_BASE + 1400) // 8, (T2_FLAT_BASE + 1400) % 8
        self.assertEqual((hex(off), bit), ("0x398f", 0))
        off, bit = (T2_FLAT_BASE + 1410) // 8, (T2_FLAT_BASE + 1410) % 8
        self.assertEqual((hex(off), bit), ("0x3990", 2))

    def test_window_bounds_are_corpus_era(self):
        # 7/26 (pack DATA08 era start) .. 8/31 (summer end)
        self.assertEqual(day_index(*FUTABA["start"]), 116)
        self.assertEqual(day_index(*FUTABA["end"]), day_index(8, 31))


if __name__ == "__main__":
    unittest.main()
