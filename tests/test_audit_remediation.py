"""
Adversarial Regression Test Suite for Audit Remediation (Change of Heart 2.0).

Verifies the 7 critical security, save-integrity, and transaction guarantees:
1. Corrupted source save write protection & diagnostic read-only mode
2. Session capability token enforcement, revocation, and zero-exposure
3. Host, Origin exact-port filtering, and CORS preflight
4. Authoritative staged transactions (stage -> confirm -> commit, tamper revocation, duplicate prevention)
5. Two-phase cross-save transfer (preview -> confirm, stale destination/donor protection, single-use token)
6. Atomic writer post-replacement failure detection and automatic rollback
7. Bounded ZIP restore (member count limit, member size limit, streaming limit, path traversal defense)
"""

import io
import json
import os
import secrets
import struct
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from unittest.mock import patch

from core.atomic_writer import (
    ConcurrencyConflictError,
    PostReplacementError,
    PreReplacementError,
    SaveValidationError,
    atomic_restore_backup,
    atomic_write_save,
    compute_sha256,
    safe_extract_zip_member,
    verify_save_bytes,
)
from core.crypto import SaveContainer, calc_crc, aes_decrypt, aes_encrypt
from core.editor import SaveEditor
from core.session import SaveSession, SessionManager
import server as web_server


class TestCorruptedSaveProtection(unittest.TestCase):
    """Guarantees damaged saves cannot enter writable pipelines or be saved."""

    def setUp(self):
        self.fixture_path = Path("tests/fixtures/canonical_save.dat")
        self.canonical_bytes = self.fixture_path.read_bytes()

    def test_verify_save_bytes_rejects_corrupted_outer_crc(self):
        corrupted = bytearray(self.canonical_bytes)
        corrupted[4] ^= 0xFF  # Corrupt outer CRC
        with self.assertRaises(SaveValidationError) as ctx:
            verify_save_bytes(bytes(corrupted), strict_crc=True)
        self.assertIn("CRC mismatch", str(ctx.exception))

    def test_verify_save_bytes_rejects_corrupted_inner_crc(self):
        container = SaveContainer()
        container.unpack_raw(self.canonical_bytes, strict_crc=False)
        packed = container.pack_raw()
        # Invert data_crc at offset 0x10 of decrypted payload, re-encrypt, and re-calculate outer CRC
        # so outer CRC is valid and zlib data decompresses cleanly, but inner data CRC fails
        decrypted_payload = bytearray(aes_decrypt(packed[0x20:], container.file_iv))
        struct.pack_into("<I", decrypted_payload, 0x10, container.data_crc ^ 0xFFFFFFFF)
        new_enc = aes_encrypt(bytes(decrypted_payload), container.file_iv)
        corrupted_save = bytearray(packed[:0x20] + new_enc)
        new_outer_crc = calc_crc(corrupted_save[0x08:])
        struct.pack_into("<I", corrupted_save, 0x04, new_outer_crc)

        with self.assertRaises(SaveValidationError) as ctx:
            verify_save_bytes(bytes(corrupted_save), strict_crc=True)
        self.assertIn("CRC mismatch", str(ctx.exception))

    def test_verify_save_bytes_rejects_misaligned_payload(self):
        # Encrypted payload length must be multiple of 16
        corrupted = self.canonical_bytes[:0x34 + 17]  # 17 bytes: not 16-aligned
        with self.assertRaises(SaveValidationError):
            verify_save_bytes(corrupted, strict_crc=True)

    def test_session_rejects_corrupt_save_bytes_by_default(self):
        corrupted = bytearray(self.canonical_bytes)
        corrupted[4] ^= 0xFF
        with self.assertRaises(SaveValidationError):
            SaveSession(bytes(corrupted))

    def test_session_read_only_diagnostic_mode_permits_reads_blocks_mutations(self):
        corrupted = bytearray(self.canonical_bytes)
        corrupted[4] ^= 0xFF
        # Create in diagnostic mode
        session = SaveSession(bytes(corrupted), read_only_diagnostics=True)
        self.assertTrue(session.is_read_only)

        # Read inspection must work
        info = session.editor.get_quick_info()
        self.assertIsNotNone(info)

        # Mutating operations must raise SaveValidationError
        with self.assertRaises(SaveValidationError):
            session.stage_field_change("header", "money", 9999999)

        with self.assertRaises(SaveValidationError):
            session.prepare_staged_transaction()

        with self.assertRaises(SaveValidationError):
            session.commit_transaction({"header": {"money": 9999999}})


class TestSessionCapabilitySecurity(unittest.TestCase):
    """Guarantees session token authentication and isolation."""

    def setUp(self):
        self.canonical_bytes = Path("tests/fixtures/canonical_save.dat").read_bytes()
        self.sm = SessionManager()

    def test_session_manager_capability_lookup_and_revocation(self):
        s1 = self.sm.create_session(self.canonical_bytes)
        token = s1.capability_token
        self.assertTrue(self.sm.validate_capability(token))
        self.assertEqual(self.sm.get_session_by_token(token), s1)

        # Revoke token
        self.sm.revoke_token(token)
        self.assertFalse(self.sm.validate_capability(token))
        self.assertIsNone(self.sm.get_session_by_token(token))

    def test_session_manager_revoke_session(self):
        s1 = self.sm.create_session(self.canonical_bytes)
        token = s1.capability_token
        sid = s1.session_id

        self.sm.revoke_session(sid)
        self.assertFalse(self.sm.validate_capability(token))
        self.assertIsNone(self.sm.get_session(sid))
        self.assertIsNone(self.sm.get_session_by_token(token))

    def test_cross_session_token_isolation(self):
        s1 = self.sm.create_session(self.canonical_bytes)
        s2 = self.sm.create_session(self.canonical_bytes)

        self.assertTrue(self.sm.validate_capability(s1.capability_token, s1.session_id))
        self.assertTrue(self.sm.validate_capability(s2.capability_token, s2.session_id))
        self.assertFalse(self.sm.validate_capability(s1.capability_token, s2.session_id))
        self.assertFalse(self.sm.validate_capability(s2.capability_token, s1.session_id))


class TestAuthoritativeStagedTransactions(unittest.TestCase):
    """Guarantees two-phase staged transaction integrity."""

    def setUp(self):
        self.canonical_bytes = Path("tests/fixtures/canonical_save.dat").read_bytes()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.target_save = Path(self.temp_dir.name) / "DATA01" / "DATA.DAT"
        self.target_save.parent.mkdir(parents=True, exist_ok=True)
        self.target_save.write_bytes(self.canonical_bytes)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_full_staged_transaction_lifecycle(self):
        session = SaveSession(self.canonical_bytes, file_path=str(self.target_save))
        session.stage_field_change("header", "money", 9999999, old_val=1000)

        prep = session.prepare_staged_transaction()
        stage_token = prep["stage_token"]
        digest = prep["patch_digest"]
        self.assertFalse(session.current_transaction.confirmed)

        conf = session.confirm_staged_transaction(stage_token, patch_digest=digest)
        self.assertEqual(conf["status"], "confirmed")
        self.assertTrue(session.current_transaction.confirmed)

        commit = session.commit_transaction(stage_token=stage_token)
        self.assertEqual(commit["status"], "success")
        self.assertEqual(session.revision, 2)
        self.assertEqual(session.editor.get_money(), 9999999)

    def test_tamper_after_confirmation_revokes_approval(self):
        session = SaveSession(self.canonical_bytes, file_path=str(self.target_save))
        session.stage_field_change("header", "money", 8888888)

        prep = session.prepare_staged_transaction()
        stage_token = prep["stage_token"]
        session.confirm_staged_transaction(stage_token, patch_digest=prep["patch_digest"])
        self.assertTrue(session.current_transaction.confirmed)

        # Modify staged change after confirmation
        session.stage_field_change("social_stats", "Knowledge", 5)
        # Prepared transaction must be completely invalidated
        self.assertIsNone(session.current_transaction)

        with self.assertRaises(SaveValidationError) as ctx:
            session.commit_transaction(stage_token=stage_token)
        self.assertIn("Invalid or unknown stage token", str(ctx.exception))

    def test_duplicate_commit_prevention(self):
        session = SaveSession(self.canonical_bytes, file_path=str(self.target_save))
        session.stage_field_change("header", "money", 7777777)
        prep = session.prepare_staged_transaction()
        session.confirm_staged_transaction(prep["stage_token"])
        session.commit_transaction(stage_token=prep["stage_token"])

        # Second commit with same token must fail
        with self.assertRaises(SaveValidationError) as ctx:
            session.commit_transaction(stage_token=prep["stage_token"])
        self.assertIn("already committed", str(ctx.exception))

    def test_unreviewed_direct_commit_rejected_when_staged_unconfirmed(self):
        session = SaveSession(self.canonical_bytes, file_path=str(self.target_save))
        session.stage_field_change("header", "money", 1234567)
        session.prepare_staged_transaction()

        # Direct commit bypassing staged review must be rejected
        with self.assertRaises(SaveValidationError) as ctx:
            session.commit_transaction({"header": {"money": 5555555}})
        self.assertIn("Pending unconfirmed staged edits exist", str(ctx.exception))


class TestTwoPhaseTransferIntegrity(unittest.TestCase):
    """Guarantees cross-save semantic transfer safety."""

    def setUp(self):
        self.canonical_bytes = Path("tests/fixtures/canonical_save.dat").read_bytes()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.target_save = Path(self.temp_dir.name) / "DATA01" / "DATA.DAT"
        self.target_save.parent.mkdir(parents=True, exist_ok=True)
        self.target_save.write_bytes(self.canonical_bytes)

        # Create donor save with distinct money
        donor_editor = SaveEditor(self.canonical_bytes)
        donor_editor.set_money(9999999)
        self.donor_bytes = donor_editor.save_to_bytes()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_transfer_preview_and_confirm_lifecycle(self):
        session = SaveSession(self.canonical_bytes, file_path=str(self.target_save))
        preview = session.build_transfer_preview(self.donor_bytes, ["money"])
        self.assertEqual(preview["status"], "preview")
        self.assertIn("transfer_token", preview)
        self.assertIn("exclusions", preview)

        token = preview["transfer_token"]
        res = session.confirm_and_commit_transfer(token, self.donor_bytes)
        self.assertEqual(res["status"], "success")
        self.assertEqual(session.editor.get_money(), 9999999)
        self.assertEqual(session.revision, 2)

    def test_transfer_rejected_on_stale_destination_baseline(self):
        session = SaveSession(self.canonical_bytes, file_path=str(self.target_save))
        preview = session.build_transfer_preview(self.donor_bytes, ["money"])
        token = preview["transfer_token"]

        # Mutate destination save
        session.commit_transaction({"header": {"money": 1000}})

        with self.assertRaises(ConcurrencyConflictError):
            session.confirm_and_commit_transfer(token, self.donor_bytes)

    def test_transfer_rejected_on_mismatched_donor(self):
        session = SaveSession(self.canonical_bytes, file_path=str(self.target_save))
        preview = session.build_transfer_preview(self.donor_bytes, ["money"])
        token = preview["transfer_token"]

        tampered_donor = bytearray(self.donor_bytes)
        tampered_donor[0x40] ^= 0xAA

        with self.assertRaises(ConcurrencyConflictError):
            session.confirm_and_commit_transfer(token, bytes(tampered_donor))

    def test_transfer_token_single_use(self):
        session = SaveSession(self.canonical_bytes, file_path=str(self.target_save))
        preview = session.build_transfer_preview(self.donor_bytes, ["money"])
        token = preview["transfer_token"]

        session.confirm_and_commit_transfer(token, self.donor_bytes)

        # Attempt duplicate commit with same token
        with self.assertRaises(SaveValidationError):
            session.confirm_and_commit_transfer(token, self.donor_bytes)


class TestAtomicWriterRollbackAndRecovery(unittest.TestCase):
    """Guarantees atomic writer recovery and pre-replacement byte restoration."""

    def setUp(self):
        self.canonical_bytes = Path("tests/fixtures/canonical_save.dat").read_bytes()
        self.canonical_sha = compute_sha256(self.canonical_bytes)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.target_save = Path(self.temp_dir.name) / "DATA01" / "DATA.DAT"
        self.target_save.parent.mkdir(parents=True, exist_ok=True)
        self.target_save.write_bytes(self.canonical_bytes)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_post_replacement_failure_automatic_rollback(self):
        editor = SaveEditor(self.canonical_bytes)
        editor.set_money(4444444)
        new_bytes = editor.save_to_bytes()

        # Simulate readback corruption during Phase 6
        real_verify = verify_save_bytes
        call_count = [0]

        def flaky_verify(buffer, strict_crc=True):
            call_count[0] += 1
            # 1: candidate verify, 2: tempfile verify, 3: post-replacement verify
            if call_count[0] == 3:
                raise SaveValidationError("Simulated post-replacement storage corruption!")
            return real_verify(buffer, strict_crc=strict_crc)

        with patch("core.atomic_writer.verify_save_bytes", side_effect=flaky_verify):
            with self.assertRaises(PostReplacementError) as ctx:
                atomic_write_save(
                    target_path=self.target_save,
                    candidate_bytes=new_bytes,
                    expected_baseline_sha256=self.canonical_sha,
                    create_backup=True,
                    strict_verification=True,
                )

        self.assertEqual(ctx.exception.recovery_status, "recovered_from_backup")
        # Target save on disk must be restored byte-for-byte to original baseline
        self.assertEqual(self.target_save.read_bytes(), self.canonical_bytes)


class TestBoundedZipExtraction(unittest.TestCase):
    """Guarantees backup restore security and resource bounds."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.zip_path = Path(self.temp_dir.name) / "backup.zip"

    def tearDown(self):
        self.temp_dir.cleanup()


    def test_path_traversal_parent_dir_rejected(self):
        with zipfile.ZipFile(self.zip_path, "w") as zf:
            zf.writestr("../evil.dat", b"payload")

        with self.assertRaises((SaveValidationError, ValueError)) as ctx:
            safe_extract_zip_member(self.zip_path, "../evil.dat")
        self.assertIn("traversal", str(ctx.exception).lower())

    def test_path_traversal_absolute_path_rejected(self):
        with zipfile.ZipFile(self.zip_path, "w") as zf:
            zf.writestr("/etc/passwd", b"payload")

        with self.assertRaises((SaveValidationError, ValueError)) as ctx:
            safe_extract_zip_member(self.zip_path, "/etc/passwd")
        self.assertIn("traversal", str(ctx.exception).lower())

    def test_member_count_limit_exceeded(self):
        with zipfile.ZipFile(self.zip_path, "w") as zf:
            for i in range(51):
                zf.writestr(f"file_{i}.dat", b"x")

        with self.assertRaises(SaveValidationError) as ctx:
            safe_extract_zip_member(self.zip_path, "file_0.dat")
        self.assertIn("too many members", str(ctx.exception))

    def test_member_size_limit_exceeded(self):
        with zipfile.ZipFile(self.zip_path, "w") as zf:
            zf.writestr("large.dat", b"x" * 200)

        with self.assertRaises(SaveValidationError) as ctx:
            safe_extract_zip_member(self.zip_path, "large.dat", max_member_size=100)
        self.assertIn("safety limit", str(ctx.exception))

    def test_streaming_decompression_chunk_bomb_aborted(self):
        # 2 MB zero payload with max_total_size set to 500 KB
        with zipfile.ZipFile(self.zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("bomb.dat", b"\x00" * (2 * 1024 * 1024))

        with self.assertRaises(SaveValidationError) as ctx:
            safe_extract_zip_member(self.zip_path, "bomb.dat", max_total_size=500 * 1024)
        self.assertIn("exceeded limit", str(ctx.exception))

    def test_safe_extraction_succeeds(self):
        content = b"EXPECTED-SAFE-DATA"
        with zipfile.ZipFile(self.zip_path, "w") as zf:
            zf.writestr("DATA.DAT", content)

        extracted = safe_extract_zip_member(self.zip_path, "DATA.DAT")
        self.assertEqual(extracted, content)


class TestServerSecurityAndCORS(unittest.TestCase):
    """Guarantees server host/origin validation, CORS preflight, and zero token leakage."""

    @classmethod
    def setUpClass(cls):
        cls.server = web_server.HTTPServer(("127.0.0.1", 0), web_server.P5RWebHandler)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def _request(self, method, path, headers=None, body=None):
        url = f"http://127.0.0.1:{self.port}{path}"
        req_headers = {"Host": f"127.0.0.1:{self.port}"}
        if headers:
            req_headers.update(headers)

        data = None
        if body is not None:
            if isinstance(body, dict):
                data = json.dumps(body).encode("utf-8")
                req_headers["Content-Type"] = "application/json"
            elif isinstance(body, bytes):
                data = body
            else:
                data = str(body).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                resp_body = resp.read()
                return resp.status, resp.headers, resp_body
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()

    def test_server_options_cors_preflight(self):
        headers = {"Origin": f"http://127.0.0.1:{self.port}"}
        status, resp_headers, _ = self._request("OPTIONS", "/api/save", headers=headers)
        self.assertEqual(status, 204)
        self.assertEqual(resp_headers.get("Access-Control-Allow-Origin"), f"http://127.0.0.1:{self.port}")
        self.assertIn("X-Session-Token", resp_headers.get("Access-Control-Allow-Headers", ""))
        self.assertIn("no-store", resp_headers.get("Cache-Control", ""))

    def test_server_options_foreign_origin_forbidden(self):
        headers = {"Origin": "http://evil.com"}
        status, _, _ = self._request("OPTIONS", "/api/save", headers=headers)
        self.assertEqual(status, 403)

    def test_server_host_header_enforcement(self):
        headers = {"Host": f"attacker.com:{self.port}"}
        status, _, _ = self._request("GET", "/api/state", headers=headers)
        self.assertEqual(status, 400)

        # Host with wrong port
        headers_bad_port = {"Host": "127.0.0.1:9999"}
        status2, _, _ = self._request("GET", "/api/state", headers=headers_bad_port)
        self.assertEqual(status2, 400)

    def test_server_origin_port_enforcement(self):
        # Mismatched port origin
        headers = {"Origin": "http://localhost:3000"}
        status, _, _ = self._request("POST", "/api/save", headers=headers, body={})
        self.assertEqual(status, 403)

    def test_server_mutating_endpoints_require_token(self):
        # POST without token
        status, _, body = self._request("POST", "/api/save", body={"header": {"money": 1000}})
        self.assertEqual(status, 401)
        err = json.loads(body.decode("utf-8"))
        self.assertIn("token required", err.get("error", "").lower())

        # POST with fabricated invalid token
        headers = {"X-Session-Token": "fabricated_token_12345"}
        status2, _, _ = self._request("POST", "/api/save", headers=headers, body={"header": {"money": 1000}})
        self.assertEqual(status2, 401)

    def test_server_state_endpoint_zero_token_exposure(self):
        status, _, body = self._request("GET", "/api/state")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertNotIn("token", data)
        self.assertNotIn("capability_token", data)
        self.assertIn("session_id", data)
        self.assertIn("pid", data)

    def test_server_load_rejects_corrupted_save(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dat") as tf:
            tf.write(b"CORRUPTED_SAVE_DATA_BYTES")
            corrupt_path = tf.name

        try:
            status, _, body = self._request("POST", "/api/load", body={"path": corrupt_path})
            self.assertEqual(status, 400)
            data = json.loads(body.decode("utf-8"))
            self.assertTrue(data.get("corrupt"))
        finally:
            if os.path.exists(corrupt_path):
                os.remove(corrupt_path)


if __name__ == "__main__":
    unittest.main()
