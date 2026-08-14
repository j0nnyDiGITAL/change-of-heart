"""Regression tests for the 2026-08-13 audit fixes (dual-oracle review).

Covers: silent no-ops -> explicit unsupported on PC (0x31) saves, the
points=99 sentinel removal, unk-byte preservation, HP/SP cap consistency,
and the get_money recursion guard.
"""

import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.editor import SaveEditor, CONFIDANT_ARCANA_MAP


def make_pc_editor() -> SaveEditor:
    """Synthetic 0x31 PC save: is_pc_0x31 flag + a payload big enough for
    all verified offset regions."""
    e = SaveEditor()
    e.parser.is_pc_0x31 = True
    e.parser.data_payload = bytes(0x40000)  # 256 KiB, covers all regions
    return e


def add_confidant_entry(e: SaveEditor, arcana_name: str, save_id: int,
                        rank: int = 1, points: int = 0):
    """Write one confidant entry into the synthetic payload."""
    arcana_id = CONFIDANT_ARCANA_MAP[arcana_name]
    off = e.PC31_OFFSET_CONFIDANTS + arcana_id * e.PC31_CONFIDANT_STRIDE
    d = bytearray(e.parser.data_payload)
    struct.pack_into("<H", d, off + e.PC31_CONFIDANT_ID_OFF, save_id)
    struct.pack_into("<H", d, off + e.PC31_CONFIDANT_RANK_OFF, rank)
    struct.pack_into("<H", d, off + e.PC31_CONFIDANT_PTS_OFF, points)
    e.parser.data_payload = bytes(d)


class TestUnsupportedOnPC(unittest.TestCase):
    def test_compendium_unsupported_on_pc(self):
        # SUPERSEDED 2026-08-14: compendium bitmask located at 0x09973
        # (mirror 0x21E83), verified against 7 saves + 100% oracle. The old
        # honest-unsupported stub is now a REAL implementation. This test now
        # asserts the real behavior: full unlock writes all 232 bits.
        e = make_pc_editor()
        r = e.unlock_compendium_100()
        self.assertEqual(r["status"], "success")
        self.assertEqual(r.get("unlocked_count"), 232)
        c = e.get_compendium()
        self.assertTrue(c["supported"])
        self.assertEqual(c["count"], 232)

    def test_steamid_unsupported_on_pc(self):
        e = make_pc_editor()
        r = e.rebind_steam_id(76561198000000000)
        self.assertEqual(r["status"], "unsupported")

    def test_romance_repair_unsupported_on_pc(self):
        e = make_pc_editor()
        r = e.repair_romance_flags()
        self.assertEqual(r["status"], "unsupported")

    def test_confidant_romance_param_unsupported_on_pc(self):
        e = make_pc_editor()
        add_confidant_entry(e, "Death", 14)
        r = e.set_confidant_rank(13, 5, romance=True)
        self.assertEqual(r["status"], "unsupported")

    def test_all_confidants_romance_all_unsupported_on_pc(self):
        e = make_pc_editor()
        r = e.set_all_confidants_rank(10, romance_all=True)
        self.assertEqual(r["status"], "unsupported")

    def test_rebalance_unsupported_on_pc(self):
        e = make_pc_editor()
        r = e.rebalance_stats()
        self.assertEqual(r["status"], "unsupported")


class TestSentinelRemoved(unittest.TestCase):
    def test_points_none_uses_threshold(self):
        e = make_pc_editor()
        add_confidant_entry(e, "Death", 14, rank=1, points=0)
        # Death rank 2 threshold = 5
        r = e.set_confidant_rank(13, 2, points=None)
        self.assertEqual(r["status"], "success")
        self.assertEqual(r["points"], 5)
        off = e.PC31_OFFSET_CONFIDANTS + 13 * e.PC31_CONFIDANT_STRIDE
        pts = struct.unpack_from("<H", e.parser.data_payload,
                                 off + e.PC31_CONFIDANT_PTS_OFF)[0]
        self.assertEqual(pts, 5)

    def test_explicit_99_points_written(self):
        e = make_pc_editor()
        add_confidant_entry(e, "Death", 14, rank=1, points=0)
        r = e.set_confidant_rank(13, 5, points=99)
        self.assertEqual(r["status"], "success")
        self.assertEqual(r["points"], 99)  # sentinel gone: 99 stays 99
        off = e.PC31_OFFSET_CONFIDANTS + 13 * e.PC31_CONFIDANT_STRIDE
        pts = struct.unpack_from("<H", e.parser.data_payload,
                                 off + e.PC31_CONFIDANT_PTS_OFF)[0]
        self.assertEqual(pts, 99)

    def test_points_none_unknown_threshold_leaves_field(self):
        e = make_pc_editor()
        add_confidant_entry(e, "Fool", 1, rank=1, points=42)  # story-locked: no table
        r = e.set_confidant_rank(0, 3, points=None)
        self.assertEqual(r["status"], "success")
        off = e.PC31_OFFSET_CONFIDANTS + 0 * e.PC31_CONFIDANT_STRIDE
        pts = struct.unpack_from("<H", e.parser.data_payload,
                                 off + e.PC31_CONFIDANT_PTS_OFF)[0]
        self.assertEqual(pts, 42)  # untouched


class TestPreservationAndCaps(unittest.TestCase):
    def test_stock_slot_preserves_unk_byte(self):
        e = make_pc_editor()
        # stock slot 0 of member 0: party base 0x2C + 0x38
        off = e.PC31_OFFSET_PARTY_BASE + 0 * e.PC31_PARTY_STRIDE + e.PC31_STOCK_BASE_REL
        d = bytearray(e.parser.data_payload)
        d[off + 5] = 0xAB  # unknown byte with a non-zero value
        e.parser.data_payload = bytes(d)
        e.set_persona_stock_slot(0, 0, persona_id=0x16B, level=50)
        self.assertEqual(e.parser.data_payload[off + 5], 0xAB)

    def test_party_stat_caps_at_999_on_pc(self):
        e = make_pc_editor()
        r = e.set_party_stat(1, hp=9999, sp=9999)
        self.assertEqual(r["status"], "success")
        off = e.PC31_OFFSET_PARTY_BASE + 1 * e.PC31_PARTY_STRIDE
        hp = struct.unpack_from("<H", e.parser.data_payload, off)[0]
        sp = struct.unpack_from("<H", e.parser.data_payload, off + 4)[0]
        self.assertEqual(hp, 999)
        self.assertEqual(sp, 999)

    def test_money_missing_block_is_noop(self):
        e = SaveEditor()  # 0x2D path, no blocks
        e.parser.blocks_raw = {}
        r = e.set_money(100)
        self.assertEqual(r["status"], "noop")

    def test_get_money_short_payload_no_recursion(self):
        e = SaveEditor()
        e.parser.is_pc_0x31 = True
        e.parser.data_payload = b"\x00" * 0x10  # way below 0x35C4
        self.assertEqual(e.get_money(), 0)  # would previously recurse infinitely


class TestSafetyValidation(unittest.TestCase):
    def test_stock_slot_rejects_invalid_persona_id(self):
        e = make_pc_editor()
        r = e.set_persona_stock_slot(0, 0, persona_id=0xFFFF)  # not in Personas.txt
        self.assertEqual(r["status"], "invalid")
        self.assertEqual(e.parser.data_payload, bytes(0x40000))  # untouched

    def test_stock_slot_rejects_invalid_skill_id(self):
        e = make_pc_editor()
        r = e.set_persona_stock_slot(0, 0, persona_id=0x16B, level=50,
                                     skills=[0xFFFF, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(r["status"], "invalid")

    def test_stock_slot_accepts_valid_persona(self):
        e = make_pc_editor()
        r = e.set_persona_stock_slot(0, 0, persona_id=0x16B, level=50)  # Raoul
        self.assertEqual(r["status"], "success")

    def test_equip_refuses_empty_slot(self):
        e = make_pc_editor()
        r = e.equip_persona(0, 5)  # slot 5 is all zeros
        self.assertEqual(r["status"], "invalid")
        self.assertEqual(e.parser.data_payload, bytes(0x40000))


if __name__ == "__main__":
    unittest.main()
