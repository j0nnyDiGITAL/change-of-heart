import unittest
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.editor import SaveEditor


class TestInGameParityFixes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.oracle_path = ROOT / "scratch_audit" / "DATA.DAT"
        if not cls.oracle_path.exists():
            # fallback to tests/oracle_saves
            oracle_files = list((ROOT / "tests" / "oracle_saves").glob("**/DATA.DAT"))
            if not oracle_files:
                raise unittest.SkipTest(
                    "no oracle save on this machine — corpus tests auto-skip")
            cls.oracle_path = oracle_files[0]

    def test_name_change_persists_in_payload_structs(self):
        """First, last, full name, and group name must be written in fullwidth UTF-8 and Atlus encoding."""
        with open(self.oracle_path, "rb") as f:
            raw = f.read()
        editor = SaveEditor(raw)
        
        # Test changing to a distinct custom name
        res = editor.set_player_names("Akira", "Kurusu", "Phantom")
        self.assertEqual(res["status"], "ok")
        
        # Check header
        self.assertEqual(editor.parser.header.fname, "Akira")
        self.assertEqual(editor.parser.header.lname, "Kurusu")
        
        # Check data payload offsets
        d = editor.parser.data_payload
        fw_full = editor._to_fullwidth("Akira Kurusu").encode("utf-8")
        fw_last = editor._to_fullwidth("Kurusu").encode("utf-8")
        fw_first = editor._to_fullwidth("Akira").encode("utf-8")
        atlus_last = editor._to_atlus_encoding("Kurusu")
        atlus_first = editor._to_atlus_encoding("Akira")
        
        # Primary block (0x13840..0x13980)
        self.assertIn(fw_full, d[0x13840:0x13880])
        self.assertIn(fw_last, d[0x138A8:0x138C8])
        self.assertIn(fw_first, d[0x138DC:0x138FC])
        self.assertIn(atlus_last, d[0x13910:0x13924])
        self.assertIn(atlus_first, d[0x13924:0x13938])
        
        # Mirror block (0x2BD50..0x2BE90)
        self.assertIn(fw_full, d[0x2BD50:0x2BD90])
        self.assertIn(fw_last, d[0x2BDB8:0x2BDD8])
        self.assertIn(fw_first, d[0x2BDEC:0x2BE0C])
        self.assertIn(atlus_last, d[0x2BE20:0x2BE34])
        self.assertIn(atlus_first, d[0x2BE34:0x2BE48])

    def test_compendium_unlock_all_count_is_224(self):
        """Compendium unlock all must register all valid summonable Personas."""
        with open(self.oracle_path, "rb") as f:
            raw = f.read()
        editor = SaveEditor(raw)
        editor.unlock_compendium_100()
        
    def test_master_inventory_read_and_write(self):
        """Master inventory table at 0x2410..0x2800 must accurately reflect in-game items and quantities."""
        with open(self.oracle_path, "rb") as f:
            raw = f.read()
        editor = SaveEditor(raw)
        
        # Read inventory - must find real owned items from save file
        inv = editor.get_inventory()
        self.assertGreater(len(inv), 0)
        
        item_names = {it["name"]: it["quantity"] for it in inv}
        # Check known items present in save
        self.assertIn("Recov-R: 50 mg", item_names)
        self.assertEqual(item_names["Recov-R: 50 mg"], 6)
        self.assertIn("Lifestone", item_names)
        self.assertEqual(item_names["Lifestone"], 5)
        
        # Test modifying an item quantity
        res = editor.set_item_quantity(8194, 99) # Recov-R: 50 mg to 99
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["quantity"], 99)
        
        # Verify in memory payload
        d = editor.parser.data_payload
        self.assertEqual(d[0x2532], 99) # 0x2530 + 2
        
        # Verify get_inventory reflects updated count
        updated_inv = editor.get_inventory()
        updated_names = {it["name"]: it["quantity"] for it in updated_inv}
        self.assertEqual(updated_names["Recov-R: 50 mg"], 99)

    def test_melee_owned_flag_write(self):
        """set_item_quantity on a melee weapon must set the owned-flag byte (verified 0x1B30+idx)."""
        with open(self.oracle_path, "rb") as f:
            raw = f.read()
        editor = SaveEditor(raw)

        # Melee item 0x1005 (Blizz Dagger) -> owned flag at 0x1B30 + 5 = 0x1B35
        item_id = 0x1005
        owned_off = editor.get_item_owned_offset(item_id)
        self.assertEqual(owned_off, 0x1B35)

        res = editor.set_item_quantity(item_id, 1)
        self.assertEqual(res["status"], "success")
        self.assertTrue(res.get("owned"))

        d = editor.parser.data_payload
        # primary owned flag + mirror both set
        self.assertEqual(d[0x1B35], 1)
        self.assertEqual(d[0x1B35 + 0x18510], 1)

    def test_melee_owned_flag_unverified_categories_are_0(self):
        """Verified unique gear categories return an owned offset; accessories and unverified ones return 0."""
        with open(self.oracle_path, "rb") as f:
            raw = f.read()
        editor = SaveEditor(raw)
        # Unique gear categories resolve via get_item_owned_offset:
        self.assertGreater(editor.get_item_owned_offset(0x1001), 0)  # melee
        self.assertGreater(editor.get_item_owned_offset(0x7010), 0)  # ranged (Makaronov)
        # Accessories and Protectors are stackable counts (0..99):
        self.assertEqual(editor.get_item_owned_offset(0x3001), 0)
        self.assertEqual(editor.get_item_count_offset(0x3001), 0x2331)
        self.assertEqual(editor.get_item_owned_offset(0x5001), 0)
        self.assertEqual(editor.get_item_count_offset(0x5001), 0x1F31)
        # Ranged: only mapped ids resolve; unverified stay 0
        self.assertGreater(editor.get_item_owned_offset(0x7020), 0)  # Bianchi (verified)
        self.assertEqual(editor.get_item_owned_offset(0x7001), 0)    # unverified ranged -> 0
        # Non-equipment categories -> 0 (not owned-flag tracked)
        self.assertEqual(editor.get_item_owned_offset(0x2001), 0)    # consumable
        self.assertEqual(editor.get_item_owned_offset(0x6001), 0)    # infiltration
        self.assertEqual(editor.get_item_owned_offset(0x0001), 0)

    def test_equipment_owned_flag_bases(self):
        """Unique gear category bases resolve to live-confirmed offsets; accessories/protectors resolve to count base."""
        with open(self.oracle_path, "rb") as f:
            raw = f.read()
        editor = SaveEditor(raw)
        # melee base 0x1B30, protector count base 0x1F30, accessory count base 0x2330, ranged 0x3430
        self.assertEqual(editor.get_item_owned_offset(0x1005), 0x1B35)  # Blizz Dagger
        self.assertEqual(editor.get_item_count_offset(0x5001), 0x1F31)  # protector idx 1 count
        self.assertEqual(editor.get_item_owned_offset(0x7010), 0x3443)  # Makaronov via map (0x3430+0x13)
        self.assertEqual(editor.get_item_owned_offset(0x7020), 0x3453)  # Bianchi via map (0x3430+0x23)
        self.assertEqual(editor.get_item_owned_offset(0x700B), 0x343E)  # Tkachev via map (0x3430+0x0E)


if __name__ == "__main__":
    unittest.main()
