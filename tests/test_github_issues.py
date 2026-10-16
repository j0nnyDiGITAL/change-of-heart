import os
import unittest

import server
from core.editor import SaveEditor


class TestGithubIssue4LoadSavePlaytime(unittest.TestCase):
    """
    Regression test for GitHub issue #4: "Load Save" crashed with
    "unsupported operand type(s) for //: 'NoneType' and 'int'" when the
    save's header description text had no parseable "PLAY TIME:Xh Ym" line
    (localized saves, or saves where the game wrote the default desc).
    """

    FIXTURE = "tests/fixtures/canonical_save.dat"
    DESC_OFFSET = 0x91  # description text block inside the DECOMPRESSED header
    DESC_LEN = 256

    def _editor_from(self, data: bytes) -> SaveEditor:
        ed = SaveEditor(data)
        self.assertTrue(ed.is_real_save())
        return ed

    def _blank_desc_block(self, ed: SaveEditor) -> None:
        """Simulate a save whose header description text carries no
        'PLAY TIME:Xh Ym' line (e.g. a localized game version)."""
        hb = bytearray(ed.container.header_bytes)
        filler = b"Persona 5 Royal Save Data"
        hb[self.DESC_OFFSET:self.DESC_OFFSET + self.DESC_LEN] = (
            filler + b"\x00" * (self.DESC_LEN - len(filler))
        )
        ed.container.header_bytes = bytes(hb)

    def test_payload_with_playtime_line_unchanged(self):
        """Fixture WITH the PLAY TIME text line keeps its exact playtime string."""
        with open(self.FIXTURE, "rb") as f:
            ed = self._editor_from(f.read())
        payload = server._build_loaded_save_payload(ed, "test.dat")
        self.assertEqual(payload["header"]["playtime"], "999h 59m")

    def test_payload_without_playtime_line_no_crash(self):
        """Save WITHOUT a PLAY TIME text line loads; playtime degrades to 'Unknown'."""
        with open(self.FIXTURE, "rb") as f:
            ed = self._editor_from(f.read())
        self._blank_desc_block(ed)
        self.assertIsNone(ed.get_quick_info().get("playtime"))
        payload = server._build_loaded_save_payload(ed, "test.dat")
        self.assertEqual(payload["header"]["playtime"], "Unknown")
