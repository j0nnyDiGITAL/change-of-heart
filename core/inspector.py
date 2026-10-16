"""
Save Inspector and Semantic/Binary Comparison Engine for Persona 5 Royal Save Studio.

Provides non-destructive, read-only diagnostic inspection of save containers,
mirrored-field consistency, CRC integrity, and side-by-side comparison between two saves.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .crypto import SaveContainer, calc_crc
from .editor import SaveEditor, CONFIDANT_ARCANA_MAP
from .environment import check_running_processes
from tools.binary_diff_oracle import audit_save_mutation


def _get_editor_and_bytes(source: Union[SaveEditor, bytes, str, Path]) -> Tuple[SaveEditor, bytes]:
    """Helper to obtain both a SaveEditor instance and raw container bytes."""
    if isinstance(source, SaveEditor):
        raw = getattr(source, "_raw_buffer", b"")
        if not raw:
            raw = source.save_to_bytes()
        return source, raw
    elif isinstance(source, bytes):
        return SaveEditor(source), source
    elif isinstance(source, (str, Path)):
        p = Path(source).resolve()
        raw = p.read_bytes()
        return SaveEditor(raw), raw
    raise TypeError(f"Unsupported source type: {type(source)}")


def inspect_save(source: Union[SaveEditor, bytes, str, Path], file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Performs full read-only diagnostic inspection of a save file container.
    Analyzes container integrity, CRC validity, quick info, compendium mirrors,
    and running processes.
    """
    import struct
    editor, raw_bytes = _get_editor_and_bytes(source)
    container = editor.container

    path_str = file_path or getattr(editor, "_file_path", None) or "In-Memory Buffer"

    # Container checks
    magic = raw_bytes[:4] if len(raw_bytes) >= 4 else b""
    magic_ok = (magic == b"DATA")

    file_crc = struct.unpack("<I", raw_bytes[4:8])[0] if len(raw_bytes) >= 8 else 0
    calc_file_crc = calc_crc(raw_bytes[0x8:]) if len(raw_bytes) >= 8 else 0
    file_crc_ok = (file_crc == calc_file_crc)

    aes_ok = bool(container.file_flags & (1 << 31))
    calc_data_crc = calc_crc(container.data_bytes) if container.data_bytes else 0
    data_crc_ok = (container.data_crc == calc_data_crc)

    # Compendium mirror consistency check
    primary_mask_offset = SaveEditor.PC31_OFFSET_COMPENDIUM
    mirror_mask_offset = SaveEditor.PC31_OFFSET_COMPENDIUM + getattr(SaveEditor, "PC31_MIRROR_DELTA", 0x18510)
    d_bytes = container.data_bytes

    primary_reg_count = 0
    mirror_reg_count = 0
    mirrors_match = True

    if len(d_bytes) >= mirror_mask_offset + 29:
        primary_mask = d_bytes[primary_mask_offset:primary_mask_offset + 29]
        mirror_mask = d_bytes[mirror_mask_offset:mirror_mask_offset + 29]
        primary_reg_count = sum(bin(b).count("1") for b in primary_mask)
        mirror_reg_count = sum(bin(b).count("1") for b in mirror_mask)
        mirrors_match = (primary_mask == mirror_mask)

    # Process conflict status
    p5r_running, steam_running = check_running_processes()

    # Confidants summary
    confidants = editor.get_confidant_ranks()
    total_confidants = len(confidants)
    maxed_confidants = sum(1 for c in confidants.values() if (c.get("rank") if isinstance(c, dict) else c) == 10)
    romanced_confidants = [name for name, c in confidants.items() if isinstance(c, dict) and c.get("romance")]

    # Inventory & Stock counts
    inv = editor.get_inventory()
    stock = editor.get_persona_stock(0)
    stock_count = sum(1 for p in stock if p.get("persona_id", 0) > 0)

    # Quick info
    quick_info = editor.get_quick_info()
    hdr = editor.parser.header
    names = editor.parser.player_names

    # Integrity grade
    all_ok = magic_ok and file_crc_ok and data_crc_ok and aes_ok and mirrors_match
    integrity_grade = "CLEAN" if all_ok else ("WARNING" if magic_ok and aes_ok else "CORRUPTED")

    return {
        "file_path": path_str,
        "file_size": len(raw_bytes),
        "integrity_grade": integrity_grade,
        "container": {
            "magic": magic.decode("ascii", errors="replace"),
            "magic_ok": magic_ok,
            "file_crc": f"0x{file_crc:08X}",
            "calculated_file_crc": f"0x{calc_file_crc:08X}",
            "file_crc_ok": file_crc_ok,
            "data_crc": f"0x{container.data_crc:08X}",
            "calculated_data_crc": f"0x{calc_data_crc:08X}",
            "data_crc_ok": data_crc_ok,
            "aes_encrypted": aes_ok,
            "uncompressed_data_size": len(container.data_bytes),
        },
        "compendium_mirror": {
            "primary_registered_count": primary_reg_count,
            "mirror_registered_count": mirror_reg_count,
            "in_sync": mirrors_match,
        },
        "quick_info": {
            "protagonist_name": f"{hdr.fname} {hdr.lname}".strip(),
            "group_name": names.group_name_utf8,
            "money": editor.get_money(),
            "day": quick_info.get("day") or str(hdr.day),
            "level": quick_info.get("level") or "22",
            "playtime": quick_info.get("playtime"),
            "difficulty": quick_info.get("difficulty") or "Normal",
        },
        "progression": {
            "total_confidants": total_confidants,
            "maxed_confidants": maxed_confidants,
            "romanced": romanced_confidants,
            "personas_in_stock": stock_count,
            "inventory_item_count": len(inv),
        },
        "process_status": {
            "p5r_running": p5r_running,
            "steam_running": steam_running,
        },
    }


def compare_saves(
    source_a: Union[SaveEditor, bytes, str, Path],
    source_b: Union[SaveEditor, bytes, str, Path],
    label_a: str = "Save A",
    label_b: str = "Save B",
) -> Dict[str, Any]:
    """
    Performs full semantic and binary comparison between two P5R save files.
    Compares:
    - Quick info & money
    - Social stats
    - Confidant ranks & romance
    - Persona stock slots
    - Compendium registrations
    - Inventory carried items
    - Byte-level diff ranges & classified regions
    """
    ed_a, raw_a = _get_editor_and_bytes(source_a)
    ed_b, raw_b = _get_editor_and_bytes(source_b)

    # 1. Quick Info diff
    qa = ed_a.get_quick_info()
    qb = ed_b.get_quick_info()
    ha = ed_a.parser.header
    hb = ed_b.parser.header
    na = ed_a.parser.player_names
    nb = ed_b.parser.player_names

    metadata_diff = {}
    if (ha.fname, ha.lname) != (hb.fname, hb.lname):
        metadata_diff["name"] = {"a": f"{ha.fname} {ha.lname}", "b": f"{hb.fname} {hb.lname}"}
    if na.group_name_utf8 != nb.group_name_utf8:
        metadata_diff["group_name"] = {"a": na.group_name_utf8, "b": nb.group_name_utf8}
    if ed_a.get_money() != ed_b.get_money():
        metadata_diff["money"] = {"a": ed_a.get_money(), "b": ed_b.get_money()}
    if qa.get("day") != qb.get("day"):
        metadata_diff["day"] = {"a": qa.get("day"), "b": qb.get("day")}
    if qa.get("level") != qb.get("level"):
        metadata_diff["level"] = {"a": qa.get("level"), "b": qb.get("level")}

    # 2. Social stats diff
    sa = ed_a.get_social_stats()
    sb = ed_b.get_social_stats()
    social_diff = {}
    for stat in ["Knowledge", "Charm", "Proficiency", "Guts", "Kindness"]:
        ra = sa.get(stat, {}).get("rank", 0) if isinstance(sa.get(stat), dict) else sa.get(stat, 0)
        rb = sb.get(stat, {}).get("rank", 0) if isinstance(sb.get(stat), dict) else sb.get(stat, 0)
        if ra != rb:
            social_diff[stat] = {"a": ra, "b": rb}

    # 3. Confidants diff
    ca = ed_a.get_confidant_ranks()
    cb = ed_b.get_confidant_ranks()
    confidants_diff = {}
    all_arcana = set(ca.keys()) | set(cb.keys())
    for arc in sorted(all_arcana):
        entry_a = ca.get(arc, {})
        entry_b = cb.get(arc, {})
        rank_a = entry_a.get("rank", 0) if isinstance(entry_a, dict) else int(entry_a or 0)
        rank_b = entry_b.get("rank", 0) if isinstance(entry_b, dict) else int(entry_b or 0)
        rom_a = entry_a.get("romance", False) if isinstance(entry_a, dict) else False
        rom_b = entry_b.get("romance", False) if isinstance(entry_b, dict) else False
        if rank_a != rank_b or rom_a != rom_b:
            confidants_diff[arc] = {
                "rank_a": rank_a,
                "rank_b": rank_b,
                "romance_a": rom_a,
                "romance_b": rom_b,
            }

    # 4. Compendium diff
    compa = set(ed_a.get_compendium().get("registered", []))
    compb = set(ed_b.get_compendium().get("registered", []))
    comp_diff = {
        "count_a": len(compa),
        "count_b": len(compb),
        "only_in_a": sorted(list(compa - compb)),
        "only_in_b": sorted(list(compb - compa)),
    }

    # 5. Inventory diff
    inva = {it.get("item_id"): it.get("quantity", 0) for it in ed_a.get_inventory()}
    invb = {it.get("item_id"): it.get("quantity", 0) for it in ed_b.get_inventory()}
    all_items = set(inva.keys()) | set(invb.keys())
    inventory_diff = {}
    for iid in sorted(all_items):
        qa = inva.get(iid, 0)
        qb = invb.get(iid, 0)
        if qa != qb:
            inventory_diff[iid] = {"a": qa, "b": qb}

    # 6. Binary level audit
    binary_audit = audit_save_mutation(raw_a, raw_b)

    return {
        "labels": {"a": label_a, "b": label_b},
        "metadata_diff": metadata_diff,
        "social_stats_diff": social_diff,
        "confidants_diff": confidants_diff,
        "compendium_diff": comp_diff,
        "inventory_diff": inventory_diff,
        "binary_diff": {
            "total_changed_bytes": binary_audit["total_changed_bytes"],
            "diff_count": binary_audit["diff_count"],
            "regions": sorted(list({d["region"] for d in binary_audit["diffs"]})),
        },
    }
