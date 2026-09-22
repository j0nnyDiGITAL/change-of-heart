"""Regression tests for the Deadline Escape Hatch (ADR 0003 Tier 2).

Scenario (r/Persona5 / Steam thread 3470612993482636987): the player reaches
11/18+ with Councillor < Rank 9 (or 11/17 with Justice < Rank 8) and the 3rd
semester is permanently locked, because the game evaluates those gates ON
their pinned dates. The hatch rolls the save back to a pre-deadline backup
from the vault and applies the missing rank with D016 preserve-surplus bond
points, so the game's own gate then passes legitimately.

Tests use REAL signed save containers (pack_raw → AES/zlib/dual-CRC) and the
real vault functions (create_timestamped_backup / list_backups /
restore_backup) on temp dirs — no mocks for the core paths.
"""

import io
import json
import os
import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.editor import SaveEditor, CONFIDANT_ARCANA_MAP
from core.environment import create_timestamped_backup, list_backups, restore_backup
from core.parser import SaveHeader
from core.calendar_data import abs_day

COUNCILLOR = 22  # arcana_id for set_confidant_rank (block stores save_id 35)
JUSTICE = 8
FAITH = 21


def make_real_pc_save(date_label="11/20(Fri)"):
    """Build a REAL signed PC save container with a header quick-info block.

    Real saves carry the save-select quick-info text ("11/20(Fri) Evening,
    Leblanc\nPLV:45 K\n...") inside the >=0x190 structured header block
    (parsed as SaveHeader.desc). We build the header the same way so the
    load -> mutate -> save_to_bytes -> reload pipeline behaves exactly as it
    does with genuine game files (text survives the roundtrip).
    """
    e = SaveEditor()
    e.parser.is_pc_0x31 = True
    e.parser.data_payload = bytes(0x40000)
    h = SaveHeader()
    h.playtime = 288000  # 80h
    h.level = 45
    h.desc = f"{date_label} Evening,Leblanc\nPLV:45 K\nPLAY TIME:80h 0m\nDIFFICULTY:Normal"
    # parser.header is what save_to_bytes() re-serializes on pack; container
    # header is what get_quick_info() scans in-memory. Set BOTH consistently.
    e.parser.header = h
    e.container.header_bytes = h.pack()
    return e


def write_confidant_block(ed, arcana_id, rank, points):
    """Write a confidant slot directly into the payload (arcana_id = API id)."""
    name = [k for k, v in CONFIDANT_ARCANA_MAP.items() if v == arcana_id][0]
    save_id = SaveEditor.CONFIDANT_SAVE_ID[name]
    if isinstance(save_id, (list, tuple)):
        save_id = save_id[0]
    d = bytearray(ed.parser.data_payload)
    # first empty slot
    for i in range(23):
        cand = ed.PC31_OFFSET_CONFIDANTS + i * ed.PC31_CONFIDANT_STRIDE
        if struct.unpack_from("<H", d, cand + ed.PC31_CONFIDANT_ID_OFF)[0] == 0:
            off = cand
            break
    else:
        raise AssertionError("no empty confidant slot")
    struct.pack_into("<H", d, off + ed.PC31_CONFIDANT_ID_OFF, save_id)
    struct.pack_into("<H", d, off + ed.PC31_CONFIDANT_RANK_OFF, rank)
    struct.pack_into("<H", d, off + ed.PC31_CONFIDANT_PTS_OFF, points)
    ed.parser.data_payload = bytes(d)


def to_disk(ed, path: Path):
    path.write_bytes(ed.save_to_bytes())


def fresh_editor(path: Path) -> SaveEditor:
    return SaveEditor(path.read_bytes())


class TestDeadlineGateStatus(unittest.TestCase):
    def test_gate_at_risk_before_deadline(self):
        ed = make_real_pc_save("11/10(Mon)")
        write_confidant_block(ed, COUNCILLOR, 3, 10)
        status = ed.deadline_gate_status()
        g = next(g for g in status["gates"] if g["gate_key"] == "councillor_gate")
        self.assertFalse(g["met"])
        self.assertFalse(g["deadline_passed"])
        self.assertEqual(g["current_rank"], 3)
        self.assertEqual(status["today"], (11, 10))
        self.assertTrue(status["date_known"])

    def test_gate_past_deadline_nov19_dec_jan_mar(self):
        for label, month in (("11/19(Sat)", 11), ("12/24(Sat)", 12),
                             ("1/10(Mon)", 1), ("2/25(Fri)", 2), ("3/5(Sat)", 3)):
            ed = make_real_pc_save(label)
            write_confidant_block(ed, COUNCILLOR, 3, 10)
            g = next(g for g in ed.deadline_gate_status()["gates"]
                     if g["gate_key"] == "councillor_gate")
            self.assertTrue(g["deadline_passed"], f"{label} should be past the 11/18 wall")

    def test_gate_not_past_on_deadline_day(self):
        ed = make_real_pc_save("11/18(Fri)")
        write_confidant_block(ed, COUNCILLOR, 3, 10)
        g = next(g for g in ed.deadline_gate_status()["gates"]
                 if g["gate_key"] == "councillor_gate")
        # 11/18 is the gate day itself — the game still evaluates it today.
        self.assertFalse(g["deadline_passed"])

    def test_met_gate_reports_met(self):
        ed = make_real_pc_save("11/20(Fri)")
        write_confidant_block(ed, COUNCILLOR, 9, 40)
        g = next(g for g in ed.deadline_gate_status()["gates"]
                 if g["gate_key"] == "councillor_gate")
        self.assertTrue(g["met"])

    def test_no_date_header_is_undetermined(self):
        e = SaveEditor()
        e.parser.is_pc_0x31 = True
        e.parser.data_payload = bytes(0x40000)
        e.container.header_bytes = b"\x00" * 16
        status = e.deadline_gate_status()
        self.assertFalse(status["date_known"])
        g = next(g for g in status["gates"] if g["gate_key"] == "justice_gate")
        self.assertFalse(g["deadline_passed"])
        self.assertFalse(g["met"])


class TestPlanDeadlineEscape(unittest.TestCase):
    def test_plan_returns_full_ops_for_at_risk_gate(self):
        ed = make_real_pc_save("11/20(Fri)")
        write_confidant_block(ed, COUNCILLOR, 3, 10)
        plan = ed.plan_deadline_escape("councillor_gate")
        self.assertEqual(plan["status"], "ok")
        ops = [o["op"] for o in plan["ops"]]
        self.assertIn("restore_backup", ops)
        self.assertIn("write_rank", ops)
        self.assertIn("resign_and_write", ops)
        write_op = next(o for o in plan["ops"] if o["op"] == "write_rank")
        self.assertEqual(write_op["rank"], 9)
        self.assertIn("preserve-surplus", write_op["points_semantics"])
        self.assertIn("D016", write_op["description"])
        self.assertTrue(plan["warning"])

    def test_plan_refuses_when_gate_met(self):
        ed = make_real_pc_save("11/20(Fri)")
        write_confidant_block(ed, COUNCILLOR, 9, 40)
        plan = ed.plan_deadline_escape("councillor_gate")
        self.assertEqual(plan["status"], "noop")

    def test_plan_refuses_unknown_gate(self):
        ed = make_real_pc_save("11/20(Fri)")
        self.assertEqual(ed.plan_deadline_escape("faith_gate")["status"], "invalid")

    def test_faith_gate_is_not_escape_hatchable(self):
        # 1/12 Faith gate deliberately excluded: block renumbering (33->36)
        # + 3rd-semester entry flags are event-matrix entangled (D008/D009).
        ed = make_real_pc_save("1/20(Wed)")
        write_confidant_block(ed, FAITH, 3, 10)
        plan = ed.plan_deadline_escape("faith_gate")
        self.assertEqual(plan["status"], "invalid")
        self.assertNotIn("faith_gate", SaveEditor.ESCAPE_HATCH_GATES)


class TestApplyDeadlineEscapeEndToEnd(unittest.TestCase):
    """Full pipeline on REAL signed containers + REAL vault, temp dir only."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.save_path = Path(self.tmp.name) / "DATA01.DAT"
        self.backup_dir = self.save_path.parent / "backups"

    def _make_pre_deadline_backup(self):
        """Build a pre-deadline save (11/12, Maruki R3 p30) and vault it."""
        pre = make_real_pc_save("11/12(Sat)")
        write_confidant_block(pre, COUNCILLOR, 3, 30)
        pre_disk = self.save_path.parent / "pre.DAT"
        to_disk(pre, pre_disk)
        zip_path = self.backup_dir / f"DATA01_backup_20261112_120000.zip"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(pre_disk, arcname=self.save_path.name)
        pre_disk.unlink()
        return zip_path

    def _make_post_deadline_current_state(self):
        """The tragic present: 11/24 save on disk, Maruki still R3."""
        cur = make_real_pc_save("11/24(Tue)")
        write_confidant_block(cur, COUNCILLOR, 3, 30)
        to_disk(cur, self.save_path)

    def test_confirm_required_first(self):
        ed = make_real_pc_save("11/24(Tue)")
        write_confidant_block(ed, COUNCILLOR, 3, 30)
        res = ed.apply_deadline_escape("councillor_gate")
        self.assertEqual(res["status"], "confirm_required")

    def test_full_escape_restores_writes_and_resigns(self):
        bz = self._make_pre_deadline_backup()
        self._make_post_deadline_current_state()

        ed = fresh_editor(self.save_path)
        # sanity: current state is post-deadline and at risk
        status = ed.deadline_gate_status()
        g = next(x for x in status["gates"] if x["gate_key"] == "councillor_gate")
        self.assertTrue(g["deadline_passed"] and not g["met"])
        self.assertEqual(status["today"], (11, 24))

        res = ed.apply_deadline_escape(
            "councillor_gate", backup_zip=str(bz), save_file=str(self.save_path),
            confirm=True)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["rank_written"], 9)
        self.assertEqual(res["restored_from"], bz.name)

        # The server persists res["bytes"] to disk; verify the persisted
        # roundtrip with a fresh editor on the real signed file:
        mutated_bytes = res["bytes"]
        self.save_path.write_bytes(mutated_bytes)
        mutated = fresh_editor(self.save_path)
        self.assertTrue(mutated.integrity_report()["ok"])
        ranks = mutated.get_confidant_ranks()
        self.assertGreaterEqual(ranks["Councillor"]["rank"], 9)
        # Date must be the RESTORED pre-deadline date, not the old 11/24.
        self.assertEqual(mutated.get_quick_info()["day"].split()[0], "11/12(Sat)")

    def test_escape_preserves_surplus_points_d016(self):
        # pre-deadline backup: Maruki R3 with 30 pts (threshold for 9 is 40).
        pre = make_real_pc_save("11/12(Sat)")
        write_confidant_block(pre, COUNCILLOR, 3, 30)
        pre_disk = self.save_path.parent / "pre.DAT"
        to_disk(pre, pre_disk)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        bz = self.backup_dir / "DATA01_backup_surplus.zip"
        with zipfile.ZipFile(bz, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(pre_disk, arcname=self.save_path.name)
        pre_disk.unlink()
        # The tragic present on disk: 11/24, still R3 (post-deadline state).
        cur = make_real_pc_save("11/24(Tue)")
        write_confidant_block(cur, COUNCILLOR, 3, 30)
        to_disk(cur, self.save_path)

        ed = fresh_editor(self.save_path)
        res = ed.apply_deadline_escape("councillor_gate", backup_zip=str(bz),
                                       save_file=str(self.save_path), confirm=True)
        self.assertEqual(res["status"], "success")
        mutated = SaveEditor(res["bytes"])
        entry = mutated.get_confidant_ranks()["Councillor"]
        # D016: raise → max(current 30, threshold 40) = 40, never bare-less
        self.assertGreaterEqual(entry["points"], 30)
        self.assertGreaterEqual(entry["rank"], 9)

    def test_same_rank_rerun_preserves_exact_points(self):
        # Running the hatch twice (or on an already-R9 save state) must not
        # wipe surplus: D016 same-rank rule.
        ed = make_real_pc_save("11/12(Sat)")
        write_confidant_block(ed, COUNCILLOR, 9, 77)
        res = ed.apply_deadline_escape("councillor_gate", confirm=True)
        self.assertEqual(res["status"], "success")
        entry = ed.get_confidant_ranks()["Councillor"]
        self.assertEqual(entry["points"], 77)

    def test_restore_refuses_mismatched_archive(self):
        ed = make_real_pc_save("11/24(Tue)")
        self.save_path.write_bytes(ed.save_to_bytes())
        other = self.save_path.parent / "OTHER.DAT"
        other_ed = make_real_pc_save("10/1(Thu)")
        to_disk(other_ed, other)
        bad_zip = self.backup_dir / "DATA01_backup_mismatch.zip"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(bad_zip, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(other, arcname="WRONGNAME.DAT")
        res = ed.apply_deadline_escape("councillor_gate", backup_zip=str(bad_zip),
                                       save_file=str(self.save_path), confirm=True)
        # restore_backup raises ValueError on name mismatch → surfaced as invalid
        self.assertEqual(res["status"], "invalid")
        self.assertIn("does not contain", res["message"])

    def test_missing_backup_file_reported(self):
        ed = make_real_pc_save("11/24(Tue)")
        self.save_path.write_bytes(ed.save_to_bytes())
        res = ed.apply_deadline_escape(
            "councillor_gate", backup_zip=str(self.backup_dir / "ghost.zip"),
            save_file=str(self.save_path), confirm=True)
        self.assertEqual(res["status"], "invalid")

    def test_justice_gate_escape(self):
        pre = make_real_pc_save("11/10(Mon)")
        write_confidant_block(pre, JUSTICE, 6, 55)
        pre_disk = self.save_path.parent / "pre.DAT"
        to_disk(pre, pre_disk)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        bz = self.backup_dir / "DATA01_backup_justice.zip"
        with zipfile.ZipFile(bz, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(pre_disk, arcname=self.save_path.name)
        pre_disk.unlink()

        cur = make_real_pc_save("11/19(Sat)")
        write_confidant_block(cur, JUSTICE, 6, 55)
        to_disk(cur, self.save_path)
        ed = fresh_editor(self.save_path)
        res = ed.apply_deadline_escape("justice_gate", backup_zip=str(bz),
                                       save_file=str(self.save_path), confirm=True)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["rank_written"], 8)
        mutated = SaveEditor(res["bytes"])
        self.assertGreaterEqual(mutated.get_confidant_ranks()["Justice"]["rank"], 8)


class TestVaultIntegration(unittest.TestCase):
    """The hatch must compose with the real vault helpers it reuses."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.save_path = Path(self.tmp.name) / "DATA01.DAT"

    def test_list_and_restore_roundtrip(self):
        ed = make_real_pc_save("11/12(Sat)")
        to_disk(ed, self.save_path)
        first = create_timestamped_backup(self.save_path)
        # mutate
        ed2 = fresh_editor(self.save_path)
        write_confidant_block(ed2, COUNCILLOR, 3, 30)
        self.save_path.write_bytes(ed2.save_to_bytes())
        backups = list_backups(self.save_path)
        self.assertIn(first, backups)
        # restore → date reverts to pre-deadline label
        restore_backup(self.save_path, first)
        ed3 = fresh_editor(self.save_path)
        self.assertEqual(ed3.get_quick_info()["day"].split()[0], "11/12(Sat)")
        # safety backup of the mutated state exists (reversible restore)
        self.assertGreaterEqual(len(list_backups(self.save_path)), 2)


class TestServerEndpoint(unittest.TestCase):
    """/api/deadline-status + /api/deadline-escape via the real handler."""

    @classmethod
    def setUpClass(cls):
        import threading
        import urllib.request
        cls.urllib = urllib.request
        import server as web_server
        cls.web_server = web_server
        cls.server = web_server.HTTPServer(("127.0.0.1", 0), web_server.P5RWebHandler)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def _post(self, path, payload):
        req = self.urllib.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=json_bytes(payload), headers={"Content-Type": "application/json"})
        with self.urllib.urlopen(req, timeout=5) as r:
            return json.loads(r.read().decode("utf-8"))

    def _get(self, path):
        with self.urllib.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5) as r:
            return json.loads(r.read().decode("utf-8"))

    def test_status_endpoint_no_save(self):
        old = (self.web_server.CURRENT_EDITOR, self.web_server.CURRENT_FILE_PATH)
        self.web_server.CURRENT_EDITOR = None
        self.web_server.CURRENT_FILE_PATH = None
        try:
            data = self._get("/api/deadline-status")
            self.assertFalse(data["save_loaded"])
            self.assertEqual(data["gates"], [])
        finally:
            self.web_server.CURRENT_EDITOR, self.web_server.CURRENT_FILE_PATH = old

    def test_escape_dry_run_and_rejection_flow(self):
        old = (self.web_server.CURRENT_EDITOR, self.web_server.CURRENT_FILE_PATH)
        ed = make_real_pc_save("11/24(Tue)")
        write_confidant_block(ed, COUNCILLOR, 3, 30)
        self.web_server.CURRENT_EDITOR = ed
        self.web_server.CURRENT_FILE_PATH = "Uploaded (test.DAT)"
        try:
            plan = self._post("/api/deadline-escape", {"gate_key": "councillor_gate"})
            self.assertEqual(plan["status"], "ok")
            self.assertTrue(any(o["op"] == "write_rank" for o in plan["ops"]))
        finally:
            self.web_server.CURRENT_EDITOR, self.web_server.CURRENT_FILE_PATH = old

    def test_escape_unknown_gate_is_invalid(self):
        old = (self.web_server.CURRENT_EDITOR, self.web_server.CURRENT_FILE_PATH)
        self.web_server.CURRENT_EDITOR = make_real_pc_save("11/24(Tue)")
        self.web_server.CURRENT_FILE_PATH = "Uploaded (test.DAT)"
        try:
            data = self._post("/api/deadline-escape", {"gate_key": "nope"})
            self.assertEqual(data["status"], "invalid")
        finally:
            self.web_server.CURRENT_EDITOR, self.web_server.CURRENT_FILE_PATH = old


def json_bytes(payload):
    import json as _json
    return _json.dumps(payload).encode("utf-8")


if __name__ == "__main__":
    unittest.main()
