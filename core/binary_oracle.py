"""
Binary difference oracle and invariant verifier for Persona 5 Royal save files.

Analyzes byte-level deltas between original and modified decrypted save payloads,
classifies changed offset ranges against verified field maps, and detects any
unintended, corrupting, or unmapped byte mutations.
"""

from typing import Any, Dict, List, Optional, Tuple

from core.crypto import SaveContainer
from core.editor import SaveEditor

# Authoritative documented field offset ranges in the uncompressed data payload (PC 0x31)
DOCUMENTED_OFFSET_RANGES = [
    ("MONEY", 0x035C0, 0x035C4),
    ("SOCIAL_STATS", 0x139E0, 0x139EA),
    ("PARTY_STAT_BLOCK", 0x0050, 0x0110),
    ("JOKER_STOCK", 0x0110, 0x0410),
    ("INVENTORY_MELEE_FLAG", 0x02000, 0x02050),
    ("INVENTORY_RANGED_FLAG", 0x02050, 0x020A0),
    ("INVENTORY_CONSUMABLES", 0x02534, 0x02A80),
    ("INVENTORY_KEY_ITEMS", 0x02900, 0x02A50),
    ("INVENTORY_INFILTRATION", 0x031B0, 0x03478),
    ("COMPENDIUM_PRIMARY_STRUCT_ARRAY", 0x04270, 0x09460),
    ("COMPENDIUM_PRIMARY_MASK", 0x09973, 0x09990),
    ("INVENTORY_STACKS_AND_FLAGS", 0x13000, 0x13530),
    ("CONFIDANTS_BLOCK", 0x136A0, 0x13840),
    ("PLAYER_NAMES_PC31", 0x13840, 0x139AC),
    ("COMPENDIUM_MIRROR_STRUCT_ARRAY", 0x1C780, 0x21970),
    ("COMPENDIUM_MIRROR_MASK", 0x21E83, 0x21EA0),
]


def find_byte_diff_ranges(
    original: bytes,
    modified: bytes,
    chunk_threshold: int = 16,
) -> List[Dict[str, Any]]:
    """
    Finds contiguous ranges of modified bytes between original and modified buffers.
    Returns list of dicts with: offset, length, old_bytes, new_bytes.
    """
    if len(original) != len(modified):
        raise ValueError(f"Payload length mismatch: original {len(original)} vs modified {len(modified)}")

    diffs = []
    in_diff = False
    start = 0

    for i in range(len(original)):
        if original[i] != modified[i]:
            if not in_diff:
                in_diff = True
                start = i
        else:
            if in_diff:
                in_diff = False
                diffs.append({
                    "offset": start,
                    "length": i - start,
                    "old_bytes": original[start:i],
                    "new_bytes": modified[start:i],
                })

    if in_diff:
        diffs.append({
            "offset": start,
            "length": len(original) - start,
            "old_bytes": original[start:],
            "new_bytes": modified[start:],
        })

    return diffs


def classify_diff_range(offset: int, length: int) -> str:
    """Classifies a changed byte range against documented game save regions."""
    end = offset + length
    matched_regions = []
    for name, r_start, r_end in DOCUMENTED_OFFSET_RANGES:
        if not (end <= r_start or offset >= r_end):
            matched_regions.append(name)

    if matched_regions:
        return "/".join(matched_regions)
    return "UNKNOWN_UNMAPPED_MUTATION"


def audit_save_mutation(
    original_bytes: bytes,
    modified_bytes: bytes,
) -> Dict[str, Any]:
    """
    Audits a save mutation from original to modified save container.
    Decrypts both payloads, measures exact byte diffs, classifies regions,
    and returns an invariant verification report.
    """
    c_orig = SaveContainer()
    c_orig.unpack_raw(original_bytes)

    c_mod = SaveContainer()
    c_mod.unpack_raw(modified_bytes)

    data_diffs = find_byte_diff_ranges(c_orig.data_bytes, c_mod.data_bytes)

    classified_diffs = []
    has_unknown_mutations = False

    for diff in data_diffs:
        region = classify_diff_range(diff["offset"], diff["length"])
        is_unknown = (region == "UNKNOWN_UNMAPPED_MUTATION")
        if is_unknown:
            has_unknown_mutations = True
        classified_diffs.append({
            "offset_hex": f"0x{diff['offset']:05X}",
            "offset": diff["offset"],
            "length": diff["length"],
            "region": region,
            "is_known": not is_unknown,
            "old_hex": diff["old_bytes"][:16].hex(),
            "new_hex": diff["new_bytes"][:16].hex(),
        })

    total_changed_bytes = sum(d["length"] for d in data_diffs)

    return {
        "status": "fail" if has_unknown_mutations else "ok",
        "total_changed_bytes": total_changed_bytes,
        "diff_count": len(classified_diffs),
        "has_unknown_mutations": has_unknown_mutations,
        "diffs": classified_diffs,
    }


def verify_no_op_preservation(original_bytes: bytes) -> bool:
    """
    Verifies that loading a save and re-saving without edits produces
    100% bitwise identity in the decrypted data payload.
    """
    editor = SaveEditor(original_bytes)
    resaved_bytes = editor.save_to_bytes()

    audit = audit_save_mutation(original_bytes, resaved_bytes)
    return audit["total_changed_bytes"] == 0
