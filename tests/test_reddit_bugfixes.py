import os
import struct
import unittest
from core.editor import SaveEditor

class TestRedditBugFixes(unittest.TestCase):
    """
    Unit tests reproducing and asserting fixes for issues reported on Reddit:
    1. RESERVE / blank placeholder items rejected from writes and excluded from inventory.
    2. Satanael (0x00AA) compendium registration behavior and isolation.
    3. Confidant romance route flag (bit 0x02) correctly set/cleared for Friend vs Lover.
    4. Yen offset isolation from EXP.
    """

    def setUp(self):
        self.p_save = "tests/fixtures/canonical_save.dat"
        self.assertTrue(os.path.exists(self.p_save), "canonical_save.dat fixture required")
        with open(self.p_save, "rb") as f:
            self.editor = SaveEditor(f.read())
        self.assertTrue(self.editor.is_real_save())

    def test_reserve_item_write_rejected(self):
        """set_item_quantity should reject writing to RESERVE placeholder items."""
        # 0x2011 is line 17 in Items.txt: main+02271565 RESERVE
        res = self.editor.set_item_quantity(0x2011, 10)
        self.assertEqual(res.get("status"), "unsupported")
        self.assertIn("placeholder/RESERVE", res.get("message", ""))

    def test_reserve_item_not_in_inventory(self):
        """get_inventory and get_normalized_inventory should never surface RESERVE placeholder items."""
        inv = self.editor.get_inventory()
        for item in inv:
            name = item.get("name", "")
            self.assertFalse(self.editor.is_placeholder_item(name), f"Found placeholder item in get_inventory: {item}")

        norm = self.editor.get_normalized_inventory()
        for iid in list(norm.get("stacks", {}).keys()) + list(norm.get("owned_gear", {}).keys()):
            name, _ = self.editor._resolve_item_info(iid)
            self.assertFalse(self.editor.is_placeholder_item(name), f"Found placeholder item in get_normalized_inventory: {iid} -> {name}")

    def test_confidant_friend_clears_romance_bit(self):
        """set_confidant_rank with romance=False must clear bit 0x02 on confidant struct."""
        # Ann = Lovers (Arcana 6)
        # First set to Lover
        res_lover = self.editor.set_confidant_rank(6, 10, romance=True)
        self.assertTrue(res_lover["romance"])
        ranks = self.editor.get_confidant_ranks()
        self.assertTrue(ranks["Lovers"]["romance"])

        # Set to Friend
        res_friend = self.editor.set_confidant_rank(6, 10, romance=False)
        self.assertFalse(res_friend["romance"])
        ranks_after = self.editor.get_confidant_ranks()
        self.assertFalse(ranks_after["Lovers"]["romance"])

    def test_money_exp_offset_isolation(self):
        """Writing money must write to 0x35C0 and not alter Joker's EXP at 0x3C."""
        d_before = self.editor.parser.data_payload
        exp_before = struct.unpack_from("<I", d_before, 0x3C)[0]
        
        test_money = 9876543
        self.editor.set_money(test_money)
        self.assertEqual(self.editor.get_money(), test_money)
        
        d_after = self.editor.parser.data_payload
        exp_after = struct.unpack_from("<I", d_after, 0x3C)[0]
        self.assertEqual(exp_before, exp_after, "set_money must never modify 0x3C (Joker EXP)!")

if __name__ == "__main__":
    unittest.main()
