"""
Oracle roundtrip tests for the P5R save editor (unittest, NOT pytest).

Drives the roundtrip harness logic (scripts/roundtrip_harness.py) across all
six oracle save slots (DATA11..DATA16) plus SYSTEM.DAT:

  * no-op roundtrip:  unpack_raw -> pack_raw(compress, encrypt) -> unpack_raw
    and assert the decrypted DATA payload and header are byte-identical and
    both container CRCs validate.
  * mutation cycle:   set_money + set_confidant_rank + set_party_stat +
    set_social_stats + set_equipped_persona on an in-memory COPY, save to
    bytes, reload, and assert every edited value survived plus the container
    CRC validates. Mutated outputs are written ONLY to the scratch dir
    (diff/scratch_roundtrip/), never to the oracle dir.

Run:
    python -m unittest discover -s tests -v
"""

import hashlib
import os
import struct
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.crc import calc_crc
from core.crypto import SaveContainer
from core.editor import SaveEditor

sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))
from roundtrip_harness import (  # noqa: E402
    ALL_SLOTS,
    DATA_SLOTS,
    DEFAULT_SCRATCH,
    MUTATION,
    SYSTEM_SLOT,
    noop_roundtrip,
    mutation_cycle,
    oracle_path,
    slot_label,
)

ORACLE_AVAILABLE = all(os.path.isfile(oracle_path(s)) for s in ALL_SLOTS)


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


# Snapshot oracle hashes once at import so the isolation test can prove no
# test ever wrote to the oracle directory.
ORACLE_HASHES = {s: _sha256_file(oracle_path(s)) for s in ALL_SLOTS} if ORACLE_AVAILABLE else {}


def _make_noop_test(slot: str):
    """Factory: one no-op roundtrip test per oracle slot."""

    def test(self):
        with open(oracle_path(slot), "rb") as fh:
            raw = fh.read()
        res = noop_roundtrip(raw)  # asserts internally; re-assert for unittest
        self.assertTrue(res["data_identical"], f"{slot}: decrypted payload changed")
        self.assertTrue(res["header_identical"], f"{slot}: decrypted header changed")
        self.assertTrue(res["inner_crc_ok"], f"{slot}: inner data CRC invalid")
        self.assertTrue(res["outer_crc_ok"], f"{slot}: outer file CRC invalid")

    test.__name__ = f"test_noop_roundtrip_{slot.lower()}"
    test.__doc__ = f"No-op decrypt->pack->decrypt roundtrip on {slot_label(slot)}."
    return test


def _make_mutation_test(slot: str):
    """Factory: one full mutation-cycle test per DATA slot."""

    def test(self):
        with open(oracle_path(slot), "rb") as fh:
            raw = fh.read()
        res = mutation_cycle(raw, slot, write_scratch=True, scratch_dir=DEFAULT_SCRATCH)

        st = res["statuses"]
        # An edit that silently no-ops must FAIL the test.
        self.assertEqual(st["money"], "ok", f"{slot}: set_money did not apply ({st['money']!r})")
        self.assertEqual(st["party"], "success", f"{slot}: set_party_stat did not apply")
        self.assertEqual(st["social"], "ok", f"{slot}: set_social_stats did not apply")
        self.assertEqual(st["persona"], "success", f"{slot}: set_equipped_persona did not apply")
        if slot == "DATA16":
            self.assertEqual(st["confidant"], "noop",
                             f"{slot}: empty confidant block should noop, got {st['confidant']!r}")
        else:
            self.assertEqual(st["confidant"], "success",
                             f"{slot}: set_confidant_rank did not apply ({st['confidant']!r})")

        c = res["checks"]
        self.assertTrue(c["money"], f"{slot}: money {MUTATION['money']} did not survive reload")
        self.assertTrue(c["confidant"], f"{slot}: confidant rank/points did not survive reload")
        self.assertTrue(c["party"], f"{slot}: party HP/SP did not survive reload")
        self.assertTrue(c["social"], f"{slot}: social ranks did not survive reload")
        self.assertTrue(c["persona"], f"{slot}: equipped persona did not survive reload")

        # Container CRC must validate on the re-signed output.
        self.assertTrue(res["inner_crc_ok"], f"{slot}: inner data CRC invalid after mutation")
        self.assertTrue(res["outer_crc_ok"], f"{slot}: outer file CRC invalid after mutation")

        # The mutated copy lands in scratch, and only there.
        scratch_file = res.get("scratch_file")
        self.assertIsNotNone(scratch_file, f"{slot}: scratch file was not written")
        self.assertTrue(os.path.isfile(scratch_file), f"{slot}: scratch file missing")
        self.assertTrue(os.path.abspath(scratch_file).startswith(os.path.abspath(DEFAULT_SCRATCH)),
                        f"{slot}: scratch file escaped the scratch dir: {scratch_file}")
        with open(scratch_file, "rb") as fh:
            self.assertEqual(fh.read()[:4], b"DATA", f"{slot}: scratch file lost DATA magic")

    test.__name__ = f"test_mutation_cycle_{slot.lower()}"
    test.__doc__ = (f"Mutation cycle on {slot_label(slot)}: all edits survive reload "
                    f"+ CRCs validate (copy written to scratch only).")
    return test


@unittest.skipUnless(ORACLE_AVAILABLE, "oracle save files not present")
class TestOracleNoOpRoundtrip(unittest.TestCase):
    """Container-level no-op roundtrip for every oracle slot + SYSTEM.DAT."""
    pass


for _slot in ALL_SLOTS:
    _t = _make_noop_test(_slot)
    setattr(TestOracleNoOpRoundtrip, _t.__name__, _t)
del _slot, _t


@unittest.skipUnless(ORACLE_AVAILABLE, "oracle save files not present")
class TestOracleMutationCycle(unittest.TestCase):
    """Full edit->save->reload mutation cycle for every DATA slot."""
    pass


for _slot in DATA_SLOTS:
    _t = _make_mutation_test(_slot)
    setattr(TestOracleMutationCycle, _t.__name__, _t)
del _slot, _t


@unittest.skipUnless(ORACLE_AVAILABLE, "oracle save files not present")
class TestSystemDat(unittest.TestCase):
    """SYSTEM.DAT is a v0x7 payload — container-level integrity only."""

    def test_system_dat_editor_cycle(self):
        with open(oracle_path(SYSTEM_SLOT), "rb") as fh:
            raw = fh.read()
        ed = SaveEditor(raw)
        ed.set_money(MUTATION["money"])
        out = ed.save_to_bytes(compress=True, encrypt=True)
        self.assertTrue(out.startswith(b"DATA"))
        ed2 = SaveEditor(out)
        self.assertEqual(ed2.get_money(), MUTATION["money"],
                         "SYSTEM.DAT money did not survive save->reload")
        v = SaveContainer()
        v.unpack_raw(out)
        self.assertEqual(v.data_crc, calc_crc(v.data_bytes),
                         "SYSTEM.DAT inner data CRC invalid after repack")
        outer = struct.unpack_from("<I", out, 4)[0]
        self.assertEqual(outer, calc_crc(out[8:]),
                         "SYSTEM.DAT outer file CRC invalid after repack")


@unittest.skipUnless(ORACLE_AVAILABLE, "oracle save files not present")
class TestOracleKnownValues(unittest.TestCase):
    """Known-good values on oracle DATA11 (regression anchors)."""

    def test_data11_money_and_confidant(self):
        with open(oracle_path("DATA11"), "rb") as fh:
            ed = SaveEditor(fh.read())
        self.assertEqual(ed.get_money(), 9893651)
        death = ed.get_confidant_ranks()["Death"]
        self.assertEqual(death["arcana_id"], 13)
        self.assertEqual(death["rank"], 10)

    def test_data11_party_and_persona(self):
        with open(oracle_path("DATA11"), "rb") as fh:
            ed = SaveEditor(fh.read())
        ryuji = ed.get_party_stats()[1]
        self.assertEqual((ryuji["hp"], ryuji["sp"], ryuji["level"]), (675, 249, 99))
        p = ed.get_equipped_persona(0)
        self.assertEqual(p["persona_id"], 363)  # Raoul
        self.assertEqual(p["exp"], 1418647)
        self.assertGreaterEqual(p["level"], 80)  # oracle reads 85 (task: "Lv99-ish")

    def test_data11_social_stats_all_maxed(self):
        with open(oracle_path("DATA11"), "rb") as fh:
            ed = SaveEditor(fh.read())
        social = ed.get_social_stats()
        for name in ("Knowledge", "Charm", "Proficiency", "Guts", "Kindness"):
            self.assertEqual(social[name]["rank"], 5, f"{name} should be max rank")
            thresh = ed.PC31_SOCIAL_THRESHOLDS[name][4]
            self.assertGreaterEqual(social[name]["points"], thresh,
                                    f"{name} points below max-rank threshold")


@unittest.skipUnless(ORACLE_AVAILABLE, "oracle save files not present")
class TestOracleIsolation(unittest.TestCase):
    """The oracle directory must be byte-identical after the whole suite."""

    def test_zz_oracle_files_untouched(self):
        for slot in ALL_SLOTS:
            self.assertEqual(
                _sha256_file(oracle_path(slot)), ORACLE_HASHES[slot],
                f"{slot_label(slot)} was modified by a test — oracle dir must stay read-only!")


if __name__ == "__main__":
    unittest.main()
