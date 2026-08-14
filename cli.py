"""
Command-Line Interface (CLI) for Persona 5 Royal (P5R) Save Editor
"""

import argparse
import sys
from pathlib import Path

from core.editor import SaveEditor
from core.environment import (
    discover_steam_save_dirs,
    list_save_files,
    check_running_processes,
    create_timestamped_backup,
)


def command_dump(args):
    path_in = Path(args.input)
    if not path_in.exists():
        print(f"Error: Input save file '{path_in}' does not exist.")
        sys.exit(1)

    path_out = Path(args.output) if args.output else path_in.with_suffix(".decrypted.bin")

    print(f"[+] Loading & decrypting save: {path_in}")
    editor = SaveEditor(path_in.read_bytes())

    # Save raw decrypted payload
    header_b, data_b = editor.parser.pack()
    raw_payload = header_b + data_b
    path_out.write_bytes(raw_payload)
    print(f"[✓] Dumped raw decrypted save payload ({len(raw_payload)} bytes) to: {path_out}")


def command_repack(args):
    path_in = Path(args.input)
    if not path_in.exists():
        print(f"Error: Input file '{path_in}' does not exist.")
        sys.exit(1)

    path_out = Path(args.output) if args.output else path_in.with_suffix(".repacked.BIN")

    print(f"[+] Repacking & encrypting: {path_in}")
    editor = SaveEditor()
    editor.container.data_bytes = path_in.read_bytes()
    repacked_bytes = editor.save_to_bytes(compress=True, encrypt=True)

    path_out.write_bytes(repacked_bytes)
    print(f"[✓] Repacked encrypted save ({len(repacked_bytes)} bytes) to: {path_out}")


def command_edit(args):
    path_in = Path(args.input)
    if not path_in.exists():
        print(f"Error: Input save file '{path_in}' does not exist.")
        sys.exit(1)

    # Process check
    p5r_run, steam_run = check_running_processes()
    if p5r_run:
        print("[Warning] P5R.exe is currently running! Editing save files while game is active may cause corruption.")
        if not args.force:
            print("Aborting. Close P5R or use --force to override.")
            sys.exit(1)

    # Create backup
    if not args.no_backup:
        backup_zip = create_timestamped_backup(path_in)
        print(f"[+] Automatic backup created: {backup_zip}")

    editor = SaveEditor(path_in.read_bytes())

    if args.money is not None:
        editor.set_money(args.money)
        print(f"[+] Yen set to: {args.money}")

    if args.first_name or args.last_name or args.group_name:
        fname = args.first_name or editor.parser.header.fname
        lname = args.last_name or editor.parser.header.lname
        gname = args.group_name or editor.parser.player_names.group_name_utf8
        editor.set_player_names(fname, lname, gname)
        print(f"[+] Updated Player Names: {fname} {lname} | Team: {gname}")

    if args.max_social_stats:
        editor.set_social_stats(5, 5, 5, 5, 5)
        print("[+] Social Stats set to Level 5 (Max)")

    out_path = Path(args.output) if args.output else path_in
    out_path.write_bytes(editor.save_to_bytes())
    print(f"[✓] Successfully saved changes to: {out_path}")


def command_repair_3rd_semester(args):
    path_in = Path(args.input)
    if not path_in.exists():
        print(f"Error: Input save file '{path_in}' does not exist.")
        sys.exit(1)

    if not args.no_backup:
        backup_zip = create_timestamped_backup(path_in)
        print(f"[+] Automatic backup created: {backup_zip}")

    editor = SaveEditor(path_in.read_bytes())
    res = editor.unlock_third_semester()
    print(f"[✓] {res['message']}")

    out_path = Path(args.output) if args.output else path_in
    out_path.write_bytes(editor.save_to_bytes())
    print(f"[✓] Saved updated file to: {out_path}")


def command_rebalance_stats(args):
    path_in = Path(args.input)
    if not path_in.exists():
        print(f"Error: Input save file '{path_in}' does not exist.")
        sys.exit(1)

    if not args.no_backup:
        backup_zip = create_timestamped_backup(path_in)
        print(f"[+] Automatic backup created: {backup_zip}")

    editor = SaveEditor(path_in.read_bytes())
    res = editor.rebalance_stats()
    print(f"[✓] {res['message']}")

    out_path = Path(args.output) if args.output else path_in
    out_path.write_bytes(editor.save_to_bytes())
    print(f"[✓] Saved re-balanced file to: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Persona 5 Royal (P5R) Steam Save Editor")
    subparsers = parser.add_subparsers(dest="command")

    # Dump
    sp_dump = subparsers.add_parser("dump", help="Dump decrypted raw save payload")
    sp_dump.add_argument("input", help="Input save file (e.g. DATA01.BIN)")
    sp_dump.add_argument("-o", "--output", help="Output decrypted file path")

    # Repack
    sp_repack = subparsers.add_parser("repack", help="Repack raw binary into encrypted save")
    sp_repack.add_argument("input", help="Input raw payload file")
    sp_repack.add_argument("-o", "--output", help="Output encrypted DATA01.BIN path")

    # Edit
    sp_edit = subparsers.add_parser("edit", help="Edit save values")
    sp_edit.add_argument("input", help="Input save file (e.g. DATA01.BIN)")
    sp_edit.add_argument("-o", "--output", help="Output file path")
    sp_edit.add_argument("--money", type=int, help="Set Yen amount")
    sp_edit.add_argument("--first-name", help="Set Joker's First Name")
    sp_edit.add_argument("--last-name", help="Set Joker's Last Name")
    sp_edit.add_argument("--group-name", help="Set Phantom Thief Group Name")
    sp_edit.add_argument("--max-social-stats", action="store_true", help="Set all social stats to 5")
    sp_edit.add_argument("--force", action="store_true", help="Force edit even if P5R.exe is running")
    sp_edit.add_argument("--no-backup", action="store_true", help="Skip automatic backup creation")

    # Repair 3rd Semester
    sp_sem3 = subparsers.add_parser("repair-3rd-semester", help="Unlock 3rd Semester & fix Maruki/Kasumi/Akechi flags")
    sp_sem3.add_argument("input", help="Input save file (e.g. DATA01.BIN)")
    sp_sem3.add_argument("-o", "--output", help="Output file path")
    sp_sem3.add_argument("--no-backup", action="store_true", help="Skip automatic backup creation")

    # Re-balance Stats
    sp_reb = subparsers.add_parser("rebalance-stats", help="De-bloat 999 HP/SP back to level caps")
    sp_reb.add_argument("input", help="Input save file (e.g. DATA01.BIN)")
    sp_reb.add_argument("-o", "--output", help="Output file path")
    sp_reb.add_argument("--no-backup", action="store_true", help="Skip automatic backup creation")

    args = parser.parse_args()

    if args.command == "dump":
        command_dump(args)
    elif args.command == "repack":
        command_repack(args)
    elif args.command == "edit":
        command_edit(args)
    elif args.command == "repair-3rd-semester":
        command_repair_3rd_semester(args)
    elif args.command == "rebalance-stats":
        command_rebalance_stats(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
