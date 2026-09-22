"""CHRONOS regression tests — script-derived time travel.

Ground truth is the bundled calendar model (web-app/static/chronos_model.json)
plus the empirically verified save-corpus rules:
  hdr.day          = canonical date (0-based index from April 1)
  payload 0x3D70   = max(0, hdr.day - 52)   (verified Apr..Dec)
"""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.chronos import (DAY_COUNTER_OFFSET, HDR_DAY_MAX, apply_time_travel,
                          apply_full_time_warp, build_time_travel_plan, day_index,
                          derive_ambient_events, index_to_month_day, load_model,
                          _palace_state_for_day, _event_flags_for_day,
                          _set_payload_bit, _bit_location, PALACE_SKIP_CATALOG)
from core.editor import SaveEditor
from core.parser import SaveHeader

MODEL = load_model()


def make_real_pc_save(hdr_day=116):
    """Real signed container with a structured header (same recipe as
    tests/test_deadline_escape.py — the fixture that survived roundtrips)."""
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


class TestDayIndexRules(unittest.TestCase):
    def test_known_corpus_indices(self):
        # Empirically pinned by the multi-slot save corpus
        self.assertEqual(day_index(7, 26), 116)
        self.assertEqual(day_index(8, 20), 141)
        self.assertEqual(day_index(8, 21), 142)
        self.assertEqual(day_index(9, 15), 167)
        self.assertEqual(day_index(12, 24), 267)

    def test_roundtrip(self):
        for m, d in [(4, 1), (6, 20), (7, 26), (9, 15), (12, 24)]:
            self.assertEqual(index_to_month_day(day_index(m, d)), (m, d))

    def test_day_counter_rule_matches_corpus(self):
        # Ladder (hdr.day, counter) pairs — empirically exact, all 16 slots
        for hdr_day, ctr in [(80, 28), (83, 31), (116, 64), (167, 115),
                             (173, 121), (211, 159), (267, 215)]:
            self.assertEqual(max(0, hdr_day - DAY_COUNTER_OFFSET), ctr)

    def test_envelope_cap(self):
        self.assertLessEqual(HDR_DAY_MAX, 267)  # 12/24 — last verified day-counter date


class TestAmbientClassification(unittest.TestCase):
    def test_ambient_families_found(self):
        amb = derive_ambient_events(MODEL)
        # 880/881 (household ambience) must classify ambient; 309 must not
        self.assertIn(880, amb)
        self.assertIn(881, amb)
        self.assertNotIn(309, amb)

    def test_story_event_309_blocks(self):
        plan = build_time_travel_plan(MODEL, 116, 8, 22)
        self.assertEqual(plan["status"], "blocked")
        dates = {b["date"] for b in plan["blocked_days"]}
        self.assertIn("8/21", dates)

    def test_clean_runway_7_26_to_8_20(self):
        plan = build_time_travel_plan(MODEL, 116, 8, 20)
        self.assertEqual(plan["status"], "ok")
        self.assertEqual(plan["days_skipped"], 25)

    def test_forward_only(self):
        plan = build_time_travel_plan(MODEL, 116, 7, 26)
        self.assertEqual(plan["status"], "invalid")
        plan = build_time_travel_plan(MODEL, 116, 7, 25)
        self.assertEqual(plan["status"], "invalid")

    def test_beyond_verified_envelope_refused(self):
        plan = build_time_travel_plan(MODEL, 116, 12, 25)
        self.assertEqual(plan["status"], "invalid")

    def test_unknown_date_refused(self):
        plan = build_time_travel_plan(MODEL, 116, 2, 30)
        self.assertEqual(plan["status"], "invalid")


class TestApplyTimeTravel(unittest.TestCase):
    def test_apply_writes_both_clock_fields(self):
        ed = make_real_pc_save(hdr_day=116)
        res = apply_time_travel(ed, MODEL, 8, 20)
        self.assertEqual(res["status"], "success")
        self.assertEqual(ed.parser.header.day, 141)
        ctr = int.from_bytes(ed.parser.data_payload[0x3D70:0x3D72], "little")
        self.assertEqual(ctr, 141 - DAY_COUNTER_OFFSET)

    def test_blocked_apply_does_not_mutate(self):
        ed = make_real_pc_save(hdr_day=116)
        before = (ed.parser.header.day, ed.parser.data_payload[:0x4000])
        res = apply_time_travel(ed, MODEL, 8, 22)
        self.assertEqual(res["status"], "blocked")
        self.assertEqual((ed.parser.header.day, ed.parser.data_payload[:0x4000]), before)

    def test_full_roundtrip_real_signed_container(self):
        """Load -> warp -> save_to_bytes -> fresh SaveEditor sees new date."""
        ed = make_real_pc_save(hdr_day=116)
        res = apply_time_travel(ed, MODEL, 8, 20)
        self.assertEqual(res["status"], "success")
        raw = ed.save_to_bytes()
        ed2 = SaveEditor(raw)
        self.assertEqual(ed2.parser.header.day, 141)
        self.assertEqual(ed2.get_quick_info()["day"], "8/20(Sat) Afternoon,Futaba's Palace")

    def test_counter_clamps_at_zero_pre_june(self):
        # Synthetic empty-lattice model: every day skippable — isolates the
        # write mechanics. Destinations below hdr.day 52 must clamp to 0.
        ed = make_real_pc_save(hdr_day=9)  # 4/10
        res = apply_time_travel(ed, {"lattice": {}}, 4, 15)
        self.assertEqual(res["status"], "success")
        ctr = int.from_bytes(ed.parser.data_payload[0x3D70:0x3D72], "little")
        self.assertEqual(ctr, 0)

    def test_desc_date_token_rewritten(self):
        ed = make_real_pc_save(hdr_day=116)
        res = apply_time_travel(ed, MODEL, 8, 20)
        self.assertEqual(res["status"], "success")
        raw = ed.save_to_bytes()
        ed2 = SaveEditor(raw)
        self.assertTrue(ed2.get_quick_info()["day"].startswith("8/20"))


class TestPalaceStateForDay(unittest.TestCase):
    """Test _palace_state_for_day() — which palaces are cleared/discovered."""

    def test_early_game_nothing_cleared(self):
        # Day 4/5 (day_idx=4): before any palace entry
        state = _palace_state_for_day(day_index(4, 5))
        for pid, ps in state.items():
            self.assertFalse(ps["guard"], f"{pid} guard should be False before entry")
            self.assertFalse(ps["discovery"], f"{pid} discovery should be False before entry")

    def test_kamoshida_discovered_at_entry(self):
        # 4/15 = day 14: Kamoshida's earliest_entry
        state = _palace_state_for_day(day_index(4, 15))
        self.assertTrue(state["kamoshida"]["discovery"])
        self.assertFalse(state["kamoshida"]["guard"])  # not yet cleared

    def test_kamoshida_cleared_at_deadline(self):
        # 5/2 = day 31: Kamoshida's deadline
        state = _palace_state_for_day(day_index(5, 2))
        self.assertTrue(state["kamoshida"]["guard"])
        self.assertTrue(state["kamoshida"]["discovery"])

    def test_madarame_cleared_by_day_85(self):
        # Day 85 = 6/25: past Madarame deadline (6/5)
        state = _palace_state_for_day(85)
        self.assertTrue(state["madarame"]["guard"])
        # Kaneshiro not yet cleared (deadline 7/9)
        self.assertFalse(state["kaneshiro"]["guard"])

    def test_all_seven_palaces_cycle(self):
        """Each palace transitions: undiscovered -> discovered -> cleared."""
        deadlines = [(p["palace_id"], p["earliest_entry"], p["deadline"])
                     for p in PALACE_SKIP_CATALOG]
        for pid, entry, deadline in deadlines:
            entry_idx = day_index(*entry)
            deadline_idx = day_index(*deadline)

            # Before entry: neither
            state_before = _palace_state_for_day(entry_idx - 1)
            self.assertFalse(state_before[pid]["discovery"])
            self.assertFalse(state_before[pid]["guard"])

            # At entry: discovered, not cleared
            state_at_entry = _palace_state_for_day(entry_idx)
            self.assertTrue(state_at_entry[pid]["discovery"])
            self.assertFalse(state_at_entry[pid]["guard"])

            # Between entry and deadline: discovered, not cleared
            mid = (entry_idx + deadline_idx) // 2
            state_mid = _palace_state_for_day(mid)
            self.assertTrue(state_mid[pid]["discovery"])
            self.assertFalse(state_mid[pid]["guard"])

            # At deadline: both set
            state_deadline = _palace_state_for_day(deadline_idx)
            self.assertTrue(state_deadline[pid]["guard"])
            self.assertTrue(state_deadline[pid]["discovery"])


class TestEventFlagsForDay(unittest.TestCase):
    """Test _event_flags_for_day() — daily event flag collection."""

    def test_no_flags_before_game(self):
        # Day 0 (4/1): no events yet
        flags = _event_flags_for_day(MODEL, 0)
        self.assertEqual(len(flags["bits_on"]), 0)
        self.assertEqual(len(flags["bits_off"]), 0)

    def test_flags_accumulate_forward(self):
        """Event flags should accumulate as day increases."""
        f4 = _event_flags_for_day(MODEL, day_index(4, 9))   # 4/9
        f8 = _event_flags_for_day(MODEL, day_index(4, 15))  # 4/15
        # 4/15 should have >= as many bits_on as 4/9
        self.assertGreaterEqual(len(f8["bits_on"]), len(f4["bits_on"]))

    def test_day_116_has_bits(self):
        """Day 116 (7/26) should have collected many event flags."""
        flags = _event_flags_for_day(MODEL, 116)
        self.assertGreater(len(flags["bits_on"]), 10)

    def test_off_wins_over_on(self):
        """When a bit is both on and off for different days, the net effect
        at the latest day should reflect the off (since off is applied after on)."""
        # Day 10 (4/11): bit 143 is ON in AMA
        flags_10 = _event_flags_for_day(MODEL, day_index(4, 11))
        self.assertIn(143, flags_10["bits_on"])
        # Day 15 (4/16): bit 143 is ON in PMC but no OFF yet
        # Day 23 (4/24): bit 143 is OFF in PME
        flags_23 = _event_flags_for_day(MODEL, day_index(4, 24))
        self.assertIn(143, flags_23["bits_off"])


class TestApplyFullTimeWarp(unittest.TestCase):
    """Test apply_full_time_warp() — the complete CHRONOS V3 warp."""

    def test_forward_warp_sets_palace_bits(self):
        """Forward warp to 6/25 should set Kamoshida + Madarame guard bits."""
        ed = make_real_pc_save(hdr_day=15)  # 4/16
        res = apply_full_time_warp(ed, MODEL, 6, 25)
        self.assertEqual(res["status"], "success")
        self.assertEqual(ed.parser.header.day, 84)  # 6/25

        # Check palace bits in payload
        payload = ed.parser.data_payload
        # Kamoshida guard (T2+200)
        g_off, g_bit = _bit_location(2, 200)
        self.assertTrue(payload[g_off] & (1 << g_bit), "Kamoshida guard should be SET")
        # Madarame guard (T2+600)
        g_off, g_bit = _bit_location(2, 600)
        self.assertTrue(payload[g_off] & (1 << g_bit), "Madarame guard should be SET")
        # Kaneshiro guard (T2+1000) — should NOT be set (deadline 7/9 > 6/25)
        g_off, g_bit = _bit_location(2, 1000)
        self.assertFalse(payload[g_off] & (1 << g_bit), "Kaneshiro guard should be CLEAR")

    def test_backward_warp_clears_palace_bits(self):
        """Backward warp to 5/1 should clear Kamoshida guard (deadline 5/2)."""
        ed = make_real_pc_save(hdr_day=31)  # 5/2 (Kamoshida cleared)
        # First, SET the Kamoshida guard bit
        d = bytearray(ed.parser.data_payload)
        _set_payload_bit(d, 2, 200, 1)  # set Kamoshida guard
        ed.parser.data_payload = bytes(d)

        # Now warp backward to 4/20 (before Kamoshida deadline)
        res = apply_full_time_warp(ed, MODEL, 4, 20)
        self.assertEqual(res["status"], "success")
        self.assertEqual(ed.parser.header.day, 19)  # 4/20

        # Check Kamoshida guard is cleared
        payload = ed.parser.data_payload
        g_off, g_bit = _bit_location(2, 200)
        self.assertFalse(payload[g_off] & (1 << g_bit), "Kamoshida guard should be CLEAR after backward warp")

    def test_writes_clock_fields(self):
        """Full warp should write all clock fields."""
        ed = make_real_pc_save(hdr_day=15)  # 4/16
        res = apply_full_time_warp(ed, MODEL, 8, 20)
        self.assertEqual(res["status"], "success")
        self.assertEqual(ed.parser.header.day, 141)
        ctr = int.from_bytes(ed.parser.data_payload[0x3D70:0x3D72], "little")
        self.assertEqual(ctr, 141 - DAY_COUNTER_OFFSET)
        eng = int.from_bytes(ed.parser.data_payload[0x0A670:0x0A672], "little")
        self.assertEqual(eng, 141)
        dup = int.from_bytes(ed.parser.data_payload[0x0A674:0x0A676], "little")
        self.assertEqual(dup, 141)

    def test_roundtrip_real_signed_container(self):
        """Load -> full warp -> save_to_bytes -> fresh editor sees new date + bits."""
        ed = make_real_pc_save(hdr_day=15)
        res = apply_full_time_warp(ed, MODEL, 6, 25)
        self.assertEqual(res["status"], "success")
        raw = ed.save_to_bytes()
        ed2 = SaveEditor(raw)
        self.assertEqual(ed2.parser.header.day, 84)
        self.assertTrue(ed2.get_quick_info()["day"].startswith("6/25"))

    def test_plan_contains_palace_summary(self):
        """Plan should include which palaces are set/cleared."""
        ed = make_real_pc_save(hdr_day=15)
        res = apply_full_time_warp(ed, MODEL, 9, 15)
        self.assertEqual(res["status"], "success")
        plan = res["plan"]
        self.assertIn("guards_set", plan["summary"])
        self.assertIn("guards_cleared", plan["summary"])
        self.assertIn("kamoshida", plan["summary"]["guards_set"])
        self.assertIn("madarame", plan["summary"]["guards_set"])
        self.assertIn("kaneshiro", plan["summary"]["guards_set"])
        # Futaba not yet cleared (deadline 8/21 > 9/15... wait, 9/15 > 8/21)
        # Actually 9/15 is day 167, Futaba deadline is 8/21 = day 142, so Futaba IS cleared
        self.assertIn("futaba", plan["summary"]["guards_set"])
        # Okumura not yet cleared (deadline 10/11 > 9/15)
        self.assertIn("okumura", plan["summary"]["guards_cleared"])

    def test_invalid_date_returns_error(self):
        ed = make_real_pc_save(hdr_day=15)
        res = apply_full_time_warp(ed, MODEL, 2, 30)  # invalid month
        self.assertEqual(res["status"], "error")

    def test_event_flags_applied(self):
        """Event flags from model should be applied to payload."""
        ed = make_real_pc_save(hdr_day=0)  # 4/1
        res = apply_full_time_warp(ed, MODEL, 4, 11)
        self.assertEqual(res["status"], "success")
        # Day 4/11 (day_idx=10) should have some event flags set
        payload = ed.parser.data_payload
        # Bit 8 should be ON (from 4/11 AMB bits_on)
        off, bit = _bit_location(2, 8)
        self.assertTrue(payload[off] & (1 << bit), "Bit 8 should be set for 4/11")

    def test_day_counter_pre_june_clamps_zero(self):
        """Counter at 0x3D70 should clamp to 0 for days before 6/1."""
        ed = make_real_pc_save(hdr_day=5)  # 4/6
        res = apply_full_time_warp(ed, MODEL, 4, 15)
        self.assertEqual(res["status"], "success")
        ctr = int.from_bytes(ed.parser.data_payload[0x3D70:0x3D72], "little")
        self.assertEqual(ctr, 0)

    def test_direction_backward_explicit(self):
        """Explicit direction='backward' should work."""
        ed = make_real_pc_save(hdr_day=31)  # 5/2
        res = apply_full_time_warp(ed, MODEL, 4, 15, direction="backward")
        self.assertEqual(res["status"], "success")
        self.assertEqual(ed.parser.header.day, 14)
        self.assertEqual(res["plan"]["direction"], "backward")


if __name__ == "__main__":
    unittest.main()
