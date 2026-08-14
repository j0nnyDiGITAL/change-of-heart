"""
Roundtrip Test Harness for the P5R Save Editor.

Proves the full decrypt -> edit -> re-encrypt -> reload cycle on ALL SIX
oracle save slots (DATA11..DATA16) plus SYSTEM.DAT:

  1. NO-OP ROUNDTRIP  — unpack_raw -> pack_raw(compress, encrypt) ->
     unpack_raw again. Asserts the decrypted DATA payload (and header) is
     byte-identical. pack_raw regenerates the IV and may bump the timestamp,
     so we compare `container.data_bytes` / `container.header_bytes`, not the
     raw file bytes.
  2. MUTATION CYCLE   — on an in-memory COPY: set_money + set_confidant_rank
     + set_party_stat + set_social_stats + set_equipped_persona, then
     save_to_bytes() -> SaveEditor(reload) and assert every edited value
     survived AND both container CRCs (inner data CRC + outer file CRC)
     validate.

SAFETY: this module NEVER writes to the oracle directory
(C:/Users/kufis/p5r_buff_save). All mutated outputs are written only to the
scratch dir (default: <project>/diff/scratch_roundtrip/).

Run standalone:
    python scripts/roundtrip_harness.py [--scratch DIR] [--slots DATA11,...]

The unittest suite in tests/test_roundtrip_oracle.py drives the same
functions across every slot.
"""

import argparse
import hashlib
import os
import struct
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.crc import calc_crc
from core.crypto import SaveContainer
from core.editor import SaveEditor

ORACLE_DIR = r"C:/Users/kufis/p5r_buff_save"
DATA_SLOTS = [f"DATA{i:02d}" for i in range(11, 17)]  # DATA11..DATA16
SYSTEM_SLOT = "SYSTEM"
ALL_SLOTS = DATA_SLOTS + [SYSTEM_SLOT]
DEFAULT_SCRATCH = os.path.join(PROJECT_ROOT, "diff", "scratch_roundtrip")

# Mutation values (deterministic, distinct from oracle values where possible).
MUTATION = {
    "money": 1234567,
    "confidant_arcana": 13,   # Death (Tae Takemi) — present on full-clear slots
    "confidant_rank": 10,
    "confidant_points": 999,
    "party_slot": 1,          # Ryuji
    "party_hp": 500,
    "party_sp": 200,
    "social": {"knowledge": 5, "charm": 4, "proficiency": 3,
               "kindness": 4, "guts": 2},
    "persona_slot": 0,        # Joker
    "persona_id": 363,        # Raoul
    "persona_level": 99,
    "persona_exp": 1418647,
}

# Slots whose confidant block is verified-empty (all 23 save_ids == 0): the
# confidant setter is EXPECTED to noop there (oracle state, not a bug).
EMPTY_CONFIDANT_SLOTS = {"DATA16"}


def oracle_path(slot: str) -> str:
    """Full path of an oracle slot file. DATA11..16 -> DATA.DAT; SYSTEM -> SYSTEM.DAT."""
    if slot == SYSTEM_SLOT:
        return os.path.join(ORACLE_DIR, SYSTEM_SLOT, "SYSTEM.DAT")
    return os.path.join(ORACLE_DIR, slot, "DATA.DAT")


def slot_label(slot: str) -> str:
    return "SYSTEM.DAT" if slot == SYSTEM_SLOT else f"{slot}/DATA.DAT"


# ---------------------------------------------------------------------------
# Roundtrip primitives (shared by the CLI harness and the unittest suite)
# ---------------------------------------------------------------------------

def noop_roundtrip(raw: bytes) -> dict:
    """unpack -> pack_raw -> unpack; assert payload byte-identity + CRCs.

    Returns a dict of booleans:
      data_identical, header_identical, inner_crc_ok, outer_crc_ok, data_len
    Raises AssertionError on any mismatch.
    """
    c1 = SaveContainer()
    c1.unpack_raw(raw)

    packed = c1.pack_raw(compress=True, encrypt=True)

    c2 = SaveContainer()
    c2.unpack_raw(packed)

    data_identical = c2.data_bytes == c1.data_bytes
    header_identical = c2.header_bytes == c1.header_bytes
    inner_crc_ok = c2.data_crc == calc_crc(c2.data_bytes)
    outer_file_crc = struct.unpack_from("<I", packed, 4)[0]
    outer_crc_ok = outer_file_crc == calc_crc(packed[8:])

    assert data_identical, "no-op roundtrip changed the decrypted DATA payload!"
    assert header_identical, "no-op roundtrip changed the decrypted HEADER!"
    assert inner_crc_ok, "inner data CRC invalid after no-op repack"
    assert outer_crc_ok, "outer file CRC invalid after no-op repack"

    return {
        "data_identical": data_identical,
        "header_identical": header_identical,
        "inner_crc_ok": inner_crc_ok,
        "outer_crc_ok": outer_crc_ok,
        "data_len": len(c1.data_bytes),
    }


def _confidant_available(ed: SaveEditor) -> bool:
    """True when the confidant block holds at least one non-zero save_id."""
    d = ed.parser.data_payload
    for i in range(23):
        off = ed.PC31_OFFSET_CONFIDANTS + i * ed.PC31_CONFIDANT_STRIDE
        if off + 16 > len(d):
            break
        if struct.unpack_from("<H", d, off + ed.PC31_CONFIDANT_ID_OFF)[0] != 0:
            return True
    return False


def mutation_cycle(raw: bytes, slot: str, *, write_scratch: bool = False,
                   scratch_dir: str = DEFAULT_SCRATCH) -> dict:
    """Full mutation cycle on a copy: edit -> save -> reload -> verify.

    Edits: set_money, set_confidant_rank (Death arcana 13; falls back to
    Chariot arcana 7 when Death is absent), set_party_stat (slot 1),
    set_social_stats, set_equipped_persona (slot 0).

    `slot` is the oracle slot label (DATA11..DATA16) used for scratch
    filenames. `write_scratch=True` additionally writes the re-encrypted
    output file into scratch_dir (never the oracle dir).

    Returns a dict with per-edit statuses + read-back verification flags.
    Raises AssertionError if any edit no-ops (unless the slot's confidant
    block is verified empty) or if any value fails to survive reload.
    """
    ed = SaveEditor(raw)  # operates on its own in-memory copy

    # --- apply edits, tracking status so silent no-ops FAIL loudly ----------
    st = {}
    st["money"] = ed.set_money(MUTATION["money"]).get("status")

    conf_expected_noop = slot in EMPTY_CONFIDANT_SLOTS
    arcana = MUTATION["confidant_arcana"]
    if _confidant_available(ed) and not conf_expected_noop:
        ranks = ed.get_confidant_ranks()
        if ranks.get("Death", {}).get("rank", 0) == 0:
            arcana = 7  # Chariot — present on NG+ slots (DATA13/15)
        target_rank = MUTATION["confidant_rank"]
        r = ed.set_confidant_rank(arcana, target_rank, points=MUTATION["confidant_points"])
        st["confidant"] = r.get("status")
        assert r.get("status") == "success", (
            f"confidant edit silently no-oped: {r!r} (arcana {arcana})")
    else:
        # Verified-empty block (DATA16): setter MUST report noop, never corrupt.
        before = ed.parser.data_payload
        r = ed.set_confidant_rank(arcana, MUTATION["confidant_rank"],
                                  points=MUTATION["confidant_points"])
        st["confidant"] = r.get("status")
        assert r.get("status") == "noop", (
            f"expected confidant noop on empty block, got {r!r}")
        assert ed.parser.data_payload == before, "noop confidant edit changed payload!"
        target_rank = MUTATION["confidant_rank"]

    st["party"] = ed.set_party_stat(MUTATION["party_slot"], hp=MUTATION["party_hp"],
                                    sp=MUTATION["party_sp"]).get("status")
    assert st["party"] == "success", f"party edit failed: {st['party']!r}"

    s = MUTATION["social"]
    st["social"] = ed.set_social_stats(knowledge=s["knowledge"], charm=s["charm"],
                                       proficiency=s["proficiency"],
                                       kindness=s["kindness"], guts=s["guts"]).get("status")

    st["persona"] = ed.set_equipped_persona(MUTATION["persona_slot"],
                                            persona_id=MUTATION["persona_id"],
                                            level=MUTATION["persona_level"],
                                            exp=MUTATION["persona_exp"]).get("status")
    assert st["persona"] == "success", f"persona edit failed: {st['persona']!r}"

    # --- save + container CRC validation -----------------------------------
    out = ed.save_to_bytes(compress=True, encrypt=True)
    assert out[:4] == b"DATA", "saved output lost the DATA magic"
    v = SaveContainer()
    v.unpack_raw(out)
    inner_crc_ok = v.data_crc == calc_crc(v.data_bytes)
    outer_file_crc = struct.unpack_from("<I", out, 4)[0]
    outer_crc_ok = outer_file_crc == calc_crc(out[8:])
    assert inner_crc_ok, "inner data CRC invalid after mutation save"
    assert outer_crc_ok, "outer file CRC invalid after mutation save"

    # --- reload and verify every edited value survived ---------------------
    ed2 = SaveEditor(out)
    checks = {}
    checks["money"] = ed2.get_money() == MUTATION["money"]
    assert checks["money"], f"money did not survive reload: {ed2.get_money()}"

    if st["confidant"] == "success":
        conf = ed2.get_confidant_ranks()
        name = "Death" if arcana == 13 else "Chariot"
        entry = conf.get(name, {})
        checks["confidant"] = (entry.get("rank") == target_rank
                               and entry.get("points") == MUTATION["confidant_points"])
        assert checks["confidant"], f"confidant {name} did not survive: {entry!r}"
    else:
        checks["confidant"] = True  # verified noop on empty block

    party = ed2.get_party_stats()[MUTATION["party_slot"]]
    checks["party"] = (party["hp"] == MUTATION["party_hp"]
                       and party["sp"] == MUTATION["party_sp"])
    assert checks["party"], f"party stats did not survive: {party!r}"

    soc = ed2.get_social_stats()
    checks["social"] = (soc["Knowledge"]["rank"] == 5 and soc["Charm"]["rank"] == 4
                        and soc["Proficiency"]["rank"] == 3
                        and soc["Guts"]["rank"] == 2 and soc["Kindness"]["rank"] == 4)
    assert checks["social"], f"social stats did not survive: {soc!r}"

    p = ed2.get_equipped_persona(MUTATION["persona_slot"])
    checks["persona"] = (p["persona_id"] == MUTATION["persona_id"]
                         and p["level"] == MUTATION["persona_level"]
                         and p["exp"] == MUTATION["persona_exp"])
    assert checks["persona"], f"equipped persona did not survive: {p!r}"

    result = {
        "statuses": st,
        "confidant_arcana_used": arcana,
        "checks": checks,
        "inner_crc_ok": inner_crc_ok,
        "outer_crc_ok": outer_crc_ok,
        "output_len": len(out),
    }

    if write_scratch:
        os.makedirs(scratch_dir, exist_ok=True)
        fname = f"{slot}.DAT"  # e.g. DATA11.DAT — never touches the oracle dir
        dst = os.path.join(scratch_dir, fname)
        with open(dst, "wb") as fh:
            fh.write(out)
        result["scratch_file"] = dst
        result["scratch_sha256"] = hashlib.sha256(out).hexdigest()[:16]

    return result


def run_slot(slot: str, scratch_dir: str, write_scratch: bool) -> dict:
    """Run both roundtrips for one oracle slot; return a summary dict."""
    with open(oracle_path(slot), "rb") as fh:
        raw = fh.read()
    noop = noop_roundtrip(raw)
    if slot == SYSTEM_SLOT:
        # SYSTEM.DAT is a version-0x7 payload: the PC-0x31 game-semantic
        # setters do not apply (party/social/confidant/persona offsets are
        # wrong for it). The editor-level money write + reload still proves
        # container integrity: payload preserved, CRCs valid.
        ed = SaveEditor(raw)
        ed.set_money(MUTATION["money"])
        out = ed.save_to_bytes(compress=True, encrypt=True)
        ed2 = SaveEditor(out)
        assert ed2.get_money() == MUTATION["money"], "SYSTEM.DAT money did not survive"
        v = SaveContainer()
        v.unpack_raw(out)
        assert v.data_crc == calc_crc(v.data_bytes), "SYSTEM.DAT inner CRC invalid"
        outer = struct.unpack_from("<I", out, 4)[0]
        assert outer == calc_crc(out[8:]), "SYSTEM.DAT outer CRC invalid"
        summary = {
            "slot": slot, "noop": noop,
            "mutation": {"statuses": {"money": "ok"}, "checks": {"money": True},
                         "inner_crc_ok": True, "outer_crc_ok": True,
                         "output_len": len(out), "note": "v0x7 payload: container-level only"},
        }
        if write_scratch:
            os.makedirs(scratch_dir, exist_ok=True)
            dst = os.path.join(scratch_dir, "SYSTEM.DAT")
            with open(dst, "wb") as fh:
                fh.write(out)
            summary["mutation"]["scratch_file"] = dst
        return summary

    summary = {"slot": slot, "noop": noop}
    summary["mutation"] = mutation_cycle(raw, slot, write_scratch=write_scratch,
                                         scratch_dir=scratch_dir)
    summary["mutation"]["confidant_arcana_used"] = summary["mutation"].get("confidant_arcana_used")
    return summary


def run_all(scratch_dir: str = DEFAULT_SCRATCH, slots=None,
            write_scratch: bool = True) -> int:
    """Run every slot; print a summary table; return 0 on full pass else 1."""
    slots = slots or ALL_SLOTS
    print(f"Roundtrip harness — oracle dir: {ORACLE_DIR}")
    print(f"Scratch dir (mutations only ever written here): {scratch_dir}")
    print()
    hdr = f"{'slot':<10} {'payload':>8} {'noop':>5} {'money':>6} {'conf':>5} {'party':>6} {'social':>7} {'persona':>8} {'crc':>5}"
    print(hdr)
    print("-" * len(hdr))
    failures = []
    for slot in slots:
        try:
            res = run_slot(slot, scratch_dir, write_scratch)
            m = res["mutation"]
            if slot == SYSTEM_SLOT:
                row = (f"{slot_label(slot):<10} {'v0x7':>8} {'OK':>5} "
                       f"{'OK' if m['checks']['money'] else 'FAIL':>6} {'-':>5} {'-':>6} {'-':>7} {'-':>8} {'OK':>5}")
            else:
                c = m["checks"]
                row = (f"{slot_label(slot):<10} {'0x31':>8} {'OK':>5} "
                       f"{'OK' if c['money'] else 'FAIL':>6} "
                       f"{'OK' if c['confidant'] else 'FAIL':>5} "
                       f"{'OK' if c['party'] else 'FAIL':>6} "
                       f"{'OK' if c['social'] else 'FAIL':>7} "
                       f"{'OK' if c['persona'] else 'FAIL':>8} "
                       f"{'OK' if m['inner_crc_ok'] and m['outer_crc_ok'] else 'FAIL':>5}")
            print(row)
            if slot == SYSTEM_SLOT:
                print(f"    note: {m['note']}")
            elif m["confidant_arcana_used"] != 13:
                print(f"    note: confidant edited via arcana {m['confidant_arcana_used']} "
                      f"(Death absent on {slot})")
        except Exception as exc:  # noqa: BLE001 - harness must report per-slot
            failures.append(slot)
            print(f"{slot_label(slot):<10} ERROR: {type(exc).__name__}: {exc}")
    print("-" * len(hdr))
    if failures:
        print(f"FAILED slots: {', '.join(failures)}")
        return 1
    print(f"ALL {len(slots)} slots passed (no-op roundtrip + mutation cycle).")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scratch", default=DEFAULT_SCRATCH,
                    help="scratch dir for mutated copies (default: diff/scratch_roundtrip)")
    ap.add_argument("--slots", default=",".join(ALL_SLOTS),
                    help="comma-separated slot list (default: all 7)")
    ap.add_argument("--no-write", action="store_true",
                    help="do not write scratch files (dry run)")
    args = ap.parse_args(argv)
    slots = [s.strip() for s in args.slots.split(",") if s.strip()]
    return run_all(args.scratch, slots=slots, write_scratch=not args.no_write)


if __name__ == "__main__":
    sys.exit(main())
