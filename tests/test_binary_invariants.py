"""
Unit tests for binary difference oracle and payload preservation invariants.
"""

import unittest
from pathlib import Path

from core.editor import SaveEditor
from core.binary_oracle import audit_save_mutation, verify_no_op_preservation


class TestBinaryInvariants(unittest.TestCase):

    def setUp(self):
        self.fixture_path = Path("tests/fixtures/canonical_save.dat")
        self.canonical_bytes = self.fixture_path.read_bytes()

    def test_noop_roundtrip_zero_payload_deltas(self):
        """Loading and re-saving without changes produces bitwise identical data payload."""
        is_preserved = verify_no_op_preservation(self.canonical_bytes)
        self.assertTrue(is_preserved, "Decrypted data payload must have 0 changed bytes on no-op re-save")

    def test_money_mutation_is_isolated(self):
        """Money edit modifies only the 4-byte offset at 0x0020..0x0024."""
        editor = SaveEditor(self.canonical_bytes)
        editor.set_money(1234567)
        modified_bytes = editor.save_to_bytes()

        audit = audit_save_mutation(self.canonical_bytes, modified_bytes)
        self.assertEqual(audit["status"], "ok")
        self.assertFalse(audit["has_unknown_mutations"])
        self.assertEqual(len(audit["diffs"]), 1)
        self.assertEqual(audit["diffs"][0]["offset"], 0x035C0)
        self.assertEqual(audit["diffs"][0]["region"], "MONEY")

    def test_social_stats_mutation_is_isolated(self):
        """Social stats edit modifies only the mapped social stats offsets."""
        editor = SaveEditor(self.canonical_bytes)
        editor.set_social_stats(1, 1, 1, 1, 1)
        modified_bytes = editor.save_to_bytes()

        audit = audit_save_mutation(self.canonical_bytes, modified_bytes)
        self.assertEqual(audit["status"], "ok")
        self.assertFalse(audit["has_unknown_mutations"])
        for diff in audit["diffs"]:
            self.assertIn("SOCIAL_STATS", diff["region"])

    def test_compendium_registration_mutation_touches_only_masks_and_slots(self):
        """Toggling a compendium persona modifies only documented mask and slot ranges."""
        editor = SaveEditor(self.canonical_bytes)
        # Register a persona
        editor.set_compendium_registration(0x0001, True)
        modified_bytes = editor.save_to_bytes()

        audit = audit_save_mutation(self.canonical_bytes, modified_bytes)
        self.assertEqual(audit["status"], "ok")
        self.assertFalse(audit["has_unknown_mutations"])
        for diff in audit["diffs"]:
            self.assertTrue(
                "COMPENDIUM" in diff["region"],
                f"Unexpected mutation in non-compendium region: {diff['region']} at 0x{diff['offset']:05X}"
            )


if __name__ == "__main__":
    unittest.main()
