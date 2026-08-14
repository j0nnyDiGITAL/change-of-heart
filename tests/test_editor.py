"""
Unit tests for p5r-save-editor.
Run with: python -m pytest tests/ -v
"""

import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.crc import calc_crc
from core.crypto import SaveContainer, aes_encrypt, aes_decrypt, align_offset, P5R_CRYPT_KEY
from core.editor import SaveEditor, CONFIDANT_ARCANA_MAP, ROMANCEABLE_CONFIDANTS
from core.parser import SaveHeader, PlayerNameBlock, pack_fixed_string


class TestCRC(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(calc_crc(b""), 0xFFFFFFFF)

    def test_known_vector(self):
        # Standard CRC-32/MPEG-2 check value for "123456789"
        self.assertEqual(calc_crc(b"123456789"), 0x0376E6E7)

    def test_data_magic(self):
        self.assertEqual(calc_crc(b"DATA"), 0x3965375A)

    def test_deterministic(self):
        buf = os.urandom(512)
        self.assertEqual(calc_crc(buf), calc_crc(buf))


class TestCrypto(unittest.TestCase):
    def test_key_is_32_bytes(self):
        self.assertEqual(len(P5R_CRYPT_KEY), 32)

    def test_aes_roundtrip(self):
        iv = b"\xAA" * 16
        plain = b"Persona 5 Royal save data test" * 4
        enc = aes_encrypt(plain, iv)
        dec = aes_decrypt(enc, iv)
        self.assertEqual(dec[: len(plain)], plain)

    def test_align(self):
        self.assertEqual(align_offset(0x40, 16), 0x40)
        self.assertEqual(align_offset(0x45, 16), 0x50)
        self.assertEqual(align_offset(0x50, 16), 0x50)


class TestParser(unittest.TestCase):
    def test_fixed_string_pack(self):
        self.assertEqual(pack_fixed_string("Ren", 8), b"Ren\x00\x00\x00\x00\x00")
        self.assertEqual(pack_fixed_string("AmamiyaRenTooLong", 8), b"AmamiyaR")

    def test_header_roundtrip(self):
        h = SaveHeader()
        h.playtime = 12345
        h.day = 42
        h.difficulty = 3
        h.lname = "Amamiya"
        h.fname = "Ren"
        h.desc = "test save"
        packed = h.pack()
        self.assertEqual(len(packed), 0x190)
        h2 = SaveHeader()
        h2.unpack(packed)
        self.assertEqual(h2.playtime, 12345)
        self.assertEqual(h2.day, 42)
        self.assertEqual(h2.difficulty, 3)
        self.assertEqual(h2.lname, "Amamiya")
        self.assertEqual(h2.fname, "Ren")
        self.assertEqual(h2.desc, "test save")

    def test_player_name_block_roundtrip(self):
        p = PlayerNameBlock()
        p.full_name_utf8 = "Ren Amamiya"
        p.last_name_game = "Amamiya"
        p.first_name_game = "Ren"
        p.group_name_game = "Phantom"
        p.group_name_utf8 = "Phantom Thieves"
        packed = p.pack()
        p2 = PlayerNameBlock()
        p2.unpack(packed)
        self.assertEqual(p2.full_name_utf8, "Ren Amamiya")
        self.assertEqual(p2.last_name_game, "Amamiya")
        self.assertEqual(p2.group_name_utf8, "Phantom Thieves")


class TestSaveContainerRoundtrip(unittest.TestCase):
    def _make_container(self):
        c = SaveContainer()
        c.header_bytes = os.urandom(0x1D0)
        c.data_bytes = os.urandom(4096)
        return c

    def test_pack_unpack_roundtrip(self):
        c = self._make_container()
        packed = c.pack_raw(compress=True, encrypt=True)
        self.assertTrue(packed.startswith(b"DATA"))
        self.assertEqual(len(packed) % 16, 0)  # AES block alignment

        c2 = SaveContainer()
        c2.unpack_raw(packed)
        self.assertEqual(c2.data_bytes, c.data_bytes)
        self.assertEqual(c2.header_bytes, c.header_bytes)
        self.assertEqual(c2.data_crc, calc_crc(c.data_bytes))

    def test_pack_unpack_no_compress(self):
        c = self._make_container()
        packed = c.pack_raw(compress=False, encrypt=True)
        c2 = SaveContainer()
        c2.unpack_raw(packed)
        self.assertEqual(c2.data_bytes, c.data_bytes)

    def test_bad_magic_rejected(self):
        c = SaveContainer()
        with self.assertRaises(ValueError):
            c.unpack_raw(b"\x00" * 64)


class TestEditor(unittest.TestCase):
    def _make_editor(self):
        e = SaveEditor()
        e.parser.header.fname = "Ren"
        e.parser.header.lname = "Amamiya"
        e.parser.player_names.first_name_game = "Ren"
        e.parser.player_names.last_name_game = "Amamiya"
        e.parser.player_names.group_name_utf8 = "Phantom Thieves"
        # Money block
        e.parser.blocks_raw[0x10001] = struct.pack("<I", 1000)
        # Social stats block
        e.parser.blocks_raw[0x10005] = struct.pack("<HHHHHHHHHH", 1, 20, 1, 20, 1, 20, 1, 20, 1, 20)
        # Confidant block (23 arcana * 8 bytes)
        e.parser.blocks_raw[0x10010] = b"\x00" * (23 * 8)
        # Character stats block (10 chars * 32 bytes)
        raw_chars = bytearray()
        for i in range(10):
            raw_chars += struct.pack("<HHHHH", 50, 999, 999, 999, 999) + b"\x00" * 22
        e.parser.blocks_raw[0x10002] = bytes(raw_chars)
        # Steam ID block
        e.parser.blocks_raw[0x10000] = struct.pack("<Q", 76561198000000000)
        return e

    def test_set_money(self):
        e = self._make_editor()
        e.set_money(9999999)
        self.assertEqual(e.get_money(), 9999999)
        e.set_money(50_000_000)  # should cap
        self.assertEqual(e.get_money(), 9999999)

    def test_set_player_names(self):
        e = self._make_editor()
        e.set_player_names("Kotone", "Shiomi", "SEES")
        self.assertEqual(e.parser.header.fname, "Kotone")
        self.assertEqual(e.parser.player_names.first_name_game, "Kotone")
        self.assertEqual(e.parser.player_names.group_name_utf8, "SEES")

    def test_social_stats(self):
        e = self._make_editor()
        e.set_social_stats(5, 3, 5, 1, 5)
        raw = e.parser.blocks_raw[0x10005]
        knowledge_rank = struct.unpack_from("<H", raw, 0)[0]
        charm_rank = struct.unpack_from("<H", raw, 4)[0]
        self.assertEqual(knowledge_rank, 5)
        self.assertEqual(charm_rank, 3)

    def test_third_semester_unlock(self):
        e = self._make_editor()
        res = e.unlock_third_semester()
        self.assertTrue(res["maruki_rank_updated"])
        raw = e.parser.blocks_raw[0x10010]
        # Maruki = arcana 22, rank at offset 22*8
        self.assertEqual(raw[22 * 8], 9)
        # Kasumi = arcana 21 -> rank 5
        self.assertEqual(raw[21 * 8], 5)
        # Akechi = arcana 8 -> rank 8
        self.assertEqual(raw[8 * 8], 8)

    def test_romance_repair(self):
        e = self._make_editor()
        # Set a leaked romance flag on Lovers (arcana 6)
        raw = bytearray(e.parser.blocks_raw[0x10010])
        struct.pack_into("<H", raw, 6 * 8 + 2, 0x02)
        e.parser.blocks_raw[0x10010] = bytes(raw)

        res = e.repair_romance_flags(target_arcana_id=6, romance_state=False)
        self.assertEqual(res["repaired_confidants"], 1)
        flags = struct.unpack_from("<H", e.parser.blocks_raw[0x10010], 6 * 8 + 2)[0]
        self.assertEqual(flags & 0x02, 0)

    def test_rebalance_stats(self):
        e = self._make_editor()
        res = e.rebalance_stats()
        self.assertEqual(res["normalized_party_count"], 10)
        raw = e.parser.blocks_raw[0x10002]
        max_hp = struct.unpack_from("<H", raw, 8)[0]
        self.assertLessEqual(max_hp, 700)
        self.assertGreater(max_hp, 100)

    def test_steam_rebind(self):
        e = self._make_editor()
        new_id = 76561198012345678
        res = e.rebind_steam_id(new_id)
        self.assertEqual(res["status"], "success")
        stored = struct.unpack_from("<Q", e.parser.blocks_raw[0x10000], 0)[0]
        self.assertEqual(stored, new_id)

    def test_compendium_unlock(self):
        e = self._make_editor()
        e.parser.blocks_raw[0x10020] = b"\x00" * 64
        res = e.unlock_compendium_100()
        self.assertEqual(res["status"], "success")
        self.assertTrue(all(b == 0xFF for b in e.parser.blocks_raw[0x10020]))

    def test_full_save_roundtrip(self):
        """End-to-end: build an editor, modify, save to bytes, reload, verify values survive."""
        e = self._make_editor()
        e.set_money(7777777)
        e.set_player_names("Joker", "P5R", "Phantoms")
        e.unlock_third_semester()

        packed = e.save_to_bytes(compress=True, encrypt=True)
        self.assertTrue(packed.startswith(b"DATA"))

        e2 = SaveEditor(packed)
        self.assertEqual(e2.get_money(), 7777777)
        self.assertEqual(e2.parser.header.fname, "Joker")
        raw = e2.parser.blocks_raw[0x10010]
        self.assertEqual(raw[22 * 8], 9)  # Maruki rank survives


if __name__ == "__main__":
    unittest.main()
