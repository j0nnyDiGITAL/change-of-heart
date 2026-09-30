"""Regression tests for the zamasu2020 bond-points wipe bug (2026-08-24).

Scenario: user raised ONE social stat (Proficiency 3->4) and every confidant
that was "ready to rank up in a single visit" lost its surplus bond points
("didn't have a deep enough bond"). Root cause: the save flow re-wrote ALL
confidants with rank-threshold points, destroying accumulated surplus; and
set_social_stats re-wrote all five stats to bare thresholds.

Invariant: an edit to one system must never destroy accrued progress in
another, and same-rank rewrites must preserve exact points.
"""

import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.editor import SaveEditor
from core.editor import CONFIDANT_ARCANA_MAP as _ARCANA_MAP


def make_pc_editor():
    e = SaveEditor()
    e.parser.is_pc_0x31 = True
    e.parser.data_payload = bytes(0x40000)
    return e


def write_confidant(ed, arcana_id, rank, points):
    d = bytearray(ed.parser.data_payload)
    off = ed.PC31_OFFSET_CONFIDANTS  # first slot
    # find slot with this id or take slot 0-style empty
    for i in range(23):
        cand = ed.PC31_OFFSET_CONFIDANTS + i * ed.PC31_CONFIDANT_STRIDE
        eid = struct.unpack_from("<H", d, cand + ed.PC31_CONFIDANT_ID_OFF)[0]
        if eid == arcana_id:
            off = cand
            break
    else:
        off = ed.PC31_OFFSET_CONFIDANTS
        save_id = SaveEditor.CONFIDANT_SAVE_ID[[k for k, v in _ARCANA_MAP.items() if v == arcana_id][0]]
    struct.pack_into("<H", d, off + ed.PC31_CONFIDANT_ID_OFF, save_id)
    struct.pack_into("<H", d, off + ed.PC31_CONFIDANT_RANK_OFF, rank)
    struct.pack_into("<H", d, off + ed.PC31_CONFIDANT_PTS_OFF, points)
    ed.parser.data_payload = bytes(d)


def read_confidant(ed, arcana_id):
    d = ed.parser.data_payload
    save_id = SaveEditor.CONFIDANT_SAVE_ID[[k for k, v in _ARCANA_MAP.items() if v == arcana_id][0]]
    for i in range(23):
        cand = ed.PC31_OFFSET_CONFIDANTS + i * ed.PC31_CONFIDANT_STRIDE
        if struct.unpack_from("<H", d, cand + ed.PC31_CONFIDANT_ID_OFF)[0] == save_id:
            return {
                "rank": struct.unpack_from("<H", d, cand + ed.PC31_CONFIDANT_RANK_OFF)[0],
                "points": struct.unpack_from("<H", d, cand + ed.PC31_CONFIDANT_PTS_OFF)[0],
            }
    return None


DEATH = 13  # Tae Takemi arcana_id (set_confidant_rank API); block stores save_id 14


class TestBondPointsPreservation(unittest.TestCase):
    def test_same_rank_rewrite_preserves_surplus_points(self):
        """The exact zamasu2020 bug: re-saving a confidant at its current rank
        must NOT reset points to the rank threshold."""
        ed = make_pc_editor()
        write_confidant(ed, DEATH, rank=4, points=100)  # surplus: threshold is 15
        ed.set_confidant_rank(DEATH, 4)  # UI re-sends same rank, no points
        after = read_confidant(ed, DEATH)
        self.assertEqual(after["rank"], 4)
        self.assertEqual(after["points"], 100, "surplus bond points were wiped")

    def test_rank_up_preserves_surplus_carryover(self):
        """Raising rank keeps points above the new rank's threshold (in-game
        surplus carries over)."""
        ed = make_pc_editor()
        write_confidant(ed, DEATH, rank=4, points=100)
        ed.set_confidant_rank(DEATH, 5)  # threshold for rank 5 is 20
        after = read_confidant(ed, DEATH)
        self.assertEqual(after["rank"], 5)
        self.assertEqual(after["points"], 100, "carryover surplus lost on rank-up")

    def test_explicit_lowering_uses_threshold(self):
        ed = make_pc_editor()
        write_confidant(ed, DEATH, rank=6, points=80)
        ed.set_confidant_rank(DEATH, 4)  # threshold 15 — lowering is intentional
        after = read_confidant(ed, DEATH)
        self.assertEqual(after["rank"], 4)
        self.assertEqual(after["points"], 15)

    def test_proficiency_raise_preserves_other_confidant_points(self):
        """Full user flow: social-stat edit + full-confidant re-save must leave
        untouched confidants' points byte-identical."""
        ed = make_pc_editor()
        write_confidant(ed, DEATH, rank=4, points=100)

        # Social stats: Knowledge rank 3 (82 pts), Proficiency rank 3 (34 pts)
        base = ed.PC31_OFFSET_SOCIAL_STATS
        d = bytearray(ed.parser.data_payload)
        struct.pack_into("<H", d, base + 0, 82)   # Knowledge
        struct.pack_into("<H", d, base + 4, 50)   # Proficiency: rank 3 + surplus
        ed.parser.data_payload = bytes(d)

        # User raises Proficiency to rank 4; UI re-sends everything else as-is
        ed.set_social_stats(knowledge=3, charm=1, proficiency=4, guts=1, kindness=1)

        soc = ed.get_social_stats()
        self.assertEqual(soc["Proficiency"]["rank"], 4)
        self.assertGreaterEqual(soc["Proficiency"]["points"], 60)
        # Knowledge had 82 pts (rank 3, surplus 0 over threshold 82) -> unchanged
        self.assertEqual(soc["Knowledge"]["points"], 82,
                         "untouched stat's surplus was reset by a neighbor's edit")

        # Confidant untouched by the whole flow
        self.assertEqual(read_confidant(ed, DEATH)["points"], 100)

    def test_server_forwards_explicit_bond_points_from_ui_payload(self):
        """The UI stages explicit bond points when rank arrows are used; the
        save endpoint must forward them instead of silently preserving the old
        value for a same-rank round trip (for example 3 -> 4 -> 3)."""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "server.py"), encoding="utf-8") as f:
            server_src = f.read()

        self.assertIn('points = int(cdata["points"])', server_src)
        self.assertIn("points=points", server_src)


if __name__ == "__main__":
    unittest.main()
