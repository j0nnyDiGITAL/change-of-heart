"""
Unit tests for transactional SaveSession manager, capabilities, revisions, and concurrency.
"""

import tempfile
import unittest
from pathlib import Path

from core.atomic_writer import ConcurrencyConflictError, compute_sha256
from core.session import SaveSession, SessionManager


class TestSessionTransactions(unittest.TestCase):

    def setUp(self):
        self.fixture_path = Path("tests/fixtures/canonical_save.dat")
        self.canonical_bytes = self.fixture_path.read_bytes()
        self.canonical_sha = compute_sha256(self.canonical_bytes)

        self.temp_dir = tempfile.TemporaryDirectory()
        self.target_save = Path(self.temp_dir.name) / "DATA01" / "DATA.DAT"
        self.target_save.parent.mkdir(parents=True, exist_ok=True)
        self.target_save.write_bytes(self.canonical_bytes)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_session_creation(self):
        """Creating a session initializes token, baseline, revision 1, and editor."""
        session = SaveSession(self.canonical_bytes, file_path=str(self.target_save))
        self.assertTrue(len(session.session_id) >= 16)
        self.assertTrue(len(session.capability_token) >= 24)
        self.assertEqual(session.baseline_sha256, self.canonical_sha)
        self.assertEqual(session.revision, 1)
        self.assertEqual(session.staged_changes, {})

    def test_staged_changes_summary(self):
        """Staged changes are tracked cleanly in pending ledger."""
        session = SaveSession(self.canonical_bytes, file_path=str(self.target_save))
        session.stage_field_change("header", "money", 9999999, old_val=1000)
        session.stage_field_change("social_stats", "Knowledge", 5, old_val=3)

        summary = session.get_staged_summary()
        self.assertEqual(len(summary), 2)
        fields = {item["field"] for item in summary}
        self.assertIn("money", fields)
        self.assertIn("Knowledge", fields)

        session.clear_staged_changes()
        self.assertEqual(session.get_staged_summary(), [])

    def test_commit_transaction_success(self):
        """Commit applies changes, increments revision, updates baseline, and persists."""
        session = SaveSession(self.canonical_bytes, file_path=str(self.target_save))
        payload = {
            "header": {"money": 7777777},
            "social_stats": {"Knowledge": 5, "Charm": 5, "Proficiency": 5, "Kindness": 5, "Guts": 5},
        }

        res = session.commit_transaction(payload)
        self.assertEqual(res["status"], "success")
        self.assertEqual(session.revision, 2)
        self.assertNotEqual(session.baseline_sha256, self.canonical_sha)
        self.assertEqual(session.editor.get_quick_info()["money"], 7777777)
        self.assertTrue(self.target_save.exists())

    def test_commit_transaction_failure_preserves_in_memory_state(self):
        """If commit fails on concurrency conflict, active in-memory session is unmodified."""
        session = SaveSession(self.canonical_bytes, file_path=str(self.target_save))
        orig_money = session.editor.get_quick_info()["money"]

        # External modification
        self.target_save.write_bytes(b"DATA" + b"\x00" * 100)

        with self.assertRaises(ConcurrencyConflictError):
            session.commit_transaction({"header": {"money": 1234567}})

        # In-memory baseline and editor must be intact
        self.assertEqual(session.revision, 1)
        self.assertEqual(session.baseline_sha256, self.canonical_sha)
        self.assertEqual(session.editor.get_quick_info()["money"], orig_money)

    def test_session_manager_capability_token(self):
        """SessionManager maps and validates process-local capability tokens."""
        sm = SessionManager()
        s1 = sm.create_session(self.canonical_bytes, file_path=str(self.target_save))

        self.assertTrue(sm.validate_capability(s1.capability_token))
        self.assertTrue(sm.validate_capability(s1.capability_token, s1.session_id))
        self.assertFalse(sm.validate_capability("invalid_token"))
        self.assertFalse(sm.validate_capability(s1.capability_token, "wrong_session_id"))

        retrieved = sm.get_session_by_token(s1.capability_token)
        self.assertEqual(retrieved.session_id, s1.session_id)


if __name__ == "__main__":
    unittest.main()
