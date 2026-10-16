"""
Unit tests for Save Inspector and Save Comparison engine.
"""

import unittest
from pathlib import Path

from core.editor import SaveEditor
from core.inspector import compare_saves, inspect_save


class TestInspectorAndComparison(unittest.TestCase):

    def setUp(self):
        self.fixture_path = Path("tests/fixtures/canonical_save.dat")
        self.canonical_bytes = self.fixture_path.read_bytes()

    def test_inspect_canonical_save(self):
        """Canonical save fixture passes inspection with clean grade and valid CRCs."""
        report = inspect_save(self.canonical_bytes, file_path="canonical_save.dat")
        self.assertEqual(report["integrity_grade"], "CLEAN")
        self.assertTrue(report["container"]["magic_ok"])
        self.assertTrue(report["container"]["file_crc_ok"])
        self.assertTrue(report["container"]["data_crc_ok"])
        self.assertTrue(report["container"]["aes_encrypted"])
        self.assertTrue(report["compendium_mirror"]["in_sync"])
        self.assertIn("protagonist_name", report["quick_info"])
        self.assertIn("total_confidants", report["progression"])

    def test_compare_identical_saves(self):
        """Comparing identical saves yields 0 metadata diffs and 0 byte diffs."""
        diff = compare_saves(self.canonical_bytes, self.canonical_bytes)
        self.assertEqual(diff["metadata_diff"], {})
        self.assertEqual(diff["social_stats_diff"], {})
        self.assertEqual(diff["confidants_diff"], {})
        self.assertEqual(diff["inventory_diff"], {})
        self.assertEqual(diff["binary_diff"]["total_changed_bytes"], 0)

    def test_compare_modified_save(self):
        """Comparing modified save detects money and confidant rank deltas."""
        editor = SaveEditor(self.canonical_bytes)
        editor.set_money(1234567)
        editor.set_confidant_rank(0, 5)  # Fool arcana_id 0 to rank 5
        modified_bytes = editor.save_to_bytes()

        diff = compare_saves(self.canonical_bytes, modified_bytes)
        self.assertIn("money", diff["metadata_diff"])
        self.assertEqual(diff["metadata_diff"]["money"]["b"], 1234567)
        self.assertIn("Fool", diff["confidants_diff"])
        self.assertEqual(diff["confidants_diff"]["Fool"]["rank_b"], 5)
        self.assertTrue(diff["binary_diff"]["total_changed_bytes"] > 0)

    def test_session_staging_and_clearing(self):
        """Session correctly tracks field-level stages and supports clear."""
        from core.session import SaveSession
        session = SaveSession(self.canonical_bytes, file_path="dummy.dat")
        session.stage_field_change("Profile", "Money", 9999999, old_val=1000)
        session.stage_field_change("SocialStats", "Knowledge", 5, old_val=2)
        staged = session.get_staged_summary()
        self.assertEqual(len(staged), 2)
        session.clear_staged_changes()
        self.assertEqual(len(session.get_staged_summary()), 0)

    def test_session_semantic_transfer(self):
        """Cross-save transfer accurately merges money, social stats and compendium."""
        import tempfile
        from core.session import SaveSession

        # Source save with 5,000,000 yen and unlocked compendium
        src_editor = SaveEditor(self.canonical_bytes)
        src_editor.set_money(5000000)
        src_editor.unlock_compendium_100()
        src_bytes = src_editor.save_to_bytes()

        with tempfile.TemporaryDirectory() as td:
            dst_file = Path(td) / "DATA.DAT"
            dst_file.write_bytes(self.canonical_bytes)
            session = SaveSession(self.canonical_bytes, file_path=str(dst_file))
            self.assertNotEqual(session.editor.get_money(), 5000000)

            # Perform semantic transfer
            transfer_data = {
                "header": {"money": src_editor.get_money()},
                "compendium": {
                    "supported": True,
                    "registered": src_editor.get_compendium().get("registered", [])
                }
            }
            res = session.commit_transaction(transfer_data, strict_verification=True)
            self.assertEqual(res["status"], "success")
            self.assertEqual(session.editor.get_money(), 5000000)
            self.assertEqual(len(session.editor.get_compendium()["registered"]), 284)


if __name__ == "__main__":
    unittest.main()

