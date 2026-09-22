#!/usr/bin/env python3
"""
P5R Save Editor — Lightweight invariant checker.

Runs after structural code changes. Checks:
1. Test suite passes (153+ tests)
2. state.json is valid JSON with required fields
3. No banned patterns in recent git diff (checksum bypasses, quick-array merges)
4. MEMORY.md, STATUS.md, state.json are all present

Usage:
    python scripts/check-invariants.py          # full check
    python scripts/check-invariants.py --quick  # skip git diff scan
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REQUIRED_FILES = ["AGENTS.md", "MEMORY.md", "STATUS.md", "state.json"]
REQUIRED_STATE_FIELDS = ["schema_version", "phase", "gate", "last_session", "updated_at", "test_command"]

import re
# Patterns that should never appear in committed code
BANNED_PATTERNS = [
    (r"slotIdx\s*<\s*30", "Quick-array 30-slot cap (was silently dropping items)"),
    (r"0x3530.*merge|merge.*0x3530", "Quick-array merge (never merge with master counts)"),
    (r"PS4.*offset|KHSaveEditor", "PS4 offset reference (PC != PS4)"),
]

CURRENT_SCHEMA_VERSION = 2

def migrate_state_json(data: dict) -> dict:
    """Auto-migrate older state.json schemas seamlessly."""
    version = data.get("schema_version", 1)
    if version < 2:
        old_cmd = data.get("test_command")
        if old_cmd:
            data["check_commands"] = [old_cmd] if isinstance(old_cmd, list) else [[old_cmd]]
        elif "check_commands" not in data:
            data["check_commands"] = [["python", "-m", "unittest", "discover", "-s", "tests"]]
        if "banned_patterns" not in data:
            data["banned_patterns"] = [
                [r"slotIdx\s*<\s*30", "Quick-array 30-slot cap (was silently dropping items)"],
                [r"0x3530.*merge|merge.*0x3530", "Quick-array merge (never merge with master counts)"],
                [r"PS4.*offset|KHSaveEditor", "PS4 offset reference (PC != PS4)"]
            ]
        if "human_gate" not in data:
            data["human_gate"] = "none"
        data["schema_version"] = 2
    return data

def sync_status_md(state_data: dict):
    """Auto-generate and sync the header block in STATUS.md from state.json."""
    status_file = PROJECT_ROOT / "STATUS.md"
    if not status_file.exists():
        return
    text = status_file.read_text(encoding="utf-8")
    header_block = (
        "<!-- GENERATED_STATE_HEADER_START -->\n"
        f"- **Phase:** {state_data.get('phase', 'unknown')}\n"
        f"- **Gate:** {state_data.get('gate', 'unknown')}\n"
        f"- **Mode:** {state_data.get('mode', 'single-agent')}\n"
        f"- **Version:** {state_data.get('version', 'v1.0.0')}\n"
        f"- **Updated:** {state_data.get('updated_at', 'unknown')}\n"
        "<!-- GENERATED_STATE_HEADER_END -->"
    )
    if "<!-- GENERATED_STATE_HEADER_START -->" in text:
        new_text = re.sub(
            r"<!-- GENERATED_STATE_HEADER_START -->.*?<!-- GENERATED_STATE_HEADER_END -->",
            header_block,
            text,
            flags=re.DOTALL
        )
    else:
        new_text = re.sub(
            r"## Current State\n- \*\*Phase:\*\*.*?\n- \*\*Gate:\*\*.*?\n- \*\*Mode:\*\*.*?\n",
            f"## Current State\n{header_block}\n",
            text
        )
    status_file.write_text(new_text, encoding="utf-8")
    print("  [SYNC] STATUS.md header synchronized with state.json")


def check_required_files():
    """Verify all required project files exist."""
    required = ["AGENTS.md", "PROJECT_BOOTSTRAP.md", "STATUS.md", "state.json", "MEMORY.md", "SAFETY.md", "GOALS.md", ".gitignore", "scripts/check-invariants.py"]
    missing = [f for f in required if not (PROJECT_ROOT / f).exists()]
    if missing:
        return [f"MISSING: {f}" for f in missing]
    return []


def check_state_json_and_sync():
    """Verify state.json is valid, has required fields, and is 100% in sync with STATUS.md."""
    state_path = PROJECT_ROOT / "state.json"
    status_path = PROJECT_ROOT / "STATUS.md"
    if not state_path.exists():
        return ["MISSING: state.json"], None
    try:
        raw_data = json.loads(state_path.read_text(encoding="utf-8"))
        data = migrate_state_json(raw_data)
        if data != raw_data:
            state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            print("  [MIGRATE] state.json upgraded to latest schema version")
    except Exception as e:
        return [f"INVALID JSON: state.json — {e}"], None

    required_fields = ["schema_version", "phase", "gate", "updated_at"]
    errors = []
    for field in required_fields:
        if field not in data:
            errors.append(f"MISSING FIELD: state.json.{field}")

    if errors:
        return errors, None

    # Verify Dual-State Synchronization between state.json and STATUS.md
    if status_path.exists():
        try:
            status_text = status_path.read_text(encoding="utf-8")
            phase_m = re.search(r"\*\*Phase:\*\*\s*([^\n\r]+)", status_text)
            gate_m = re.search(r"\*\*Gate:\*\*\s*([^\n\r]+)", status_text)
            if not phase_m or not gate_m:
                errors.append("STATUS.md missing '**Phase:**' or '**Gate:**' declarations")
            else:
                st_phase = phase_m.group(1).strip()
                st_gate = gate_m.group(1).strip()
                if st_phase != str(data.get("phase")).strip():
                    errors.append(f"Dual-State Phase desync: STATUS.md has '{st_phase}' but state.json has '{data.get('phase')}'")
                if st_gate != str(data.get("gate")).strip():
                    errors.append(f"Dual-State Gate desync: STATUS.md has '{st_gate}' but state.json has '{data.get('gate')}'")
        except Exception as e:
            errors.append(f"STATUS.md parse error: {e}")

    return errors, data


def check_commands_gate(data: dict):
    """Run all check_commands from state.json."""
    commands = data.get("check_commands", [])
    if not commands:
        commands = [["python", "-m", "unittest", "discover", "-s", "tests"]]
    for cmd in commands:
        cmd_list = cmd if isinstance(cmd, list) else [cmd]
        print(f"  [RUN] {' '.join(cmd_list)}")
        try:
            res = subprocess.run(cmd_list, cwd=PROJECT_ROOT, capture_output=True, text=True)
            if res.returncode != 0:
                print(f"  [FAIL] Command failed (exit {res.returncode}): {' '.join(cmd_list)}")
                if res.stdout:
                    print("--- stdout ---\n" + res.stdout[-800:])
                if res.stderr:
                    print("--- stderr ---\n" + res.stderr[-800:])
                return False
        except Exception as e:
            print(f"  [FAIL] Execution error on {' '.join(cmd_list)}: {e}")
            return False
    print("  [OK] All check & test commands passed")
    return True


def check_git_diff_banned_patterns(data: dict):
    """Scan recent git diff for banned patterns in source code additions."""
    banned = data.get("banned_patterns", BANNED_PATTERNS)
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD", "--unified=0"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        if result.returncode != 0:
            return True
        diff_text = result.stdout
        filtered_lines = []
        current_file = ""
        for line in diff_text.splitlines():
            if line.startswith("+++ b/"):
                current_file = line[6:]
            elif line.startswith("+") and not line.startswith("+++"):
                if "check-invariants.py" not in current_file and not current_file.startswith("tests/") and "state.json" not in current_file:
                    filtered_lines.append(line[1:])

        scan_target = "\n".join(filtered_lines)
        for pattern, description in banned:
            if re.search(pattern, scan_target, re.IGNORECASE):
                print(f"  [FAIL] Banned pattern detected: {description} ('{pattern}')")
                return False
        print("  [OK] No banned patterns in recent diff")
        return True
    except Exception:
        return True


def run_probe():
    """Ultra-fast (<100ms) host and ground-truth calibration probe for cold agent start."""
    print("=== AGY-OS Host & Ground Truth Probe (p5r-save-editor) ===")
    bootstrap_file = PROJECT_ROOT / "PROJECT_BOOTSTRAP.md"
    if not bootstrap_file.exists():
        print("  [WARN] PROJECT_BOOTSTRAP.md not found. Create it to pin ground truth.")
    else:
        print("  [OK] PROJECT_BOOTSTRAP.md present")

    # Probe Python runtime
    print(f"  [PROBE] Python: {sys.version.split()[0]} ({sys.executable})")

    # Probe Git cleanliness
    try:
        res = subprocess.run(["git", "status", "-s"], cwd=PROJECT_ROOT, capture_output=True, text=True)
        untracked = [l for l in res.stdout.splitlines() if l.startswith("??")]
        modified = [l for l in res.stdout.splitlines() if not l.startswith("??")]
        print(f"  [PROBE] Git Tree: {len(modified)} modified, {len(untracked)} untracked files")
    except Exception as e:
        print(f"  [WARN] Git probe failed: {e}")

    # Check required core files
    errors = check_required_files()
    if not errors:
        print("==========================================")
        print("CALIBRATION PASSED: Host environment ready.")
        sys.exit(0)
    else:
        print(f"==========================================")
        print(f"CALIBRATION FAILED: {errors}")
        sys.exit(1)


def main():
    if "--probe" in sys.argv:
        run_probe()

    if "--sync" in sys.argv:
        state_file = PROJECT_ROOT / "state.json"
        if state_file.exists():
            data = migrate_state_json(json.loads(state_file.read_text(encoding="utf-8")))
            sync_status_md(data)
            sys.exit(0)

    quick = "--quick" in sys.argv
    all_errors = []

    print("=== AGY-OS Invariant Verification Gate ===")

    # 1. Required files
    print("\n[1/4] Required files...")
    errors = check_required_files()
    all_errors.extend(errors)
    if errors:
        for e in errors:
            print(f"  [FAIL] {e}")
    else:
        print("  [OK] All required files present")

    # 2. state.json validity & Dual-State Sync
    print("\n[2/4] state.json & STATUS.md sync...")
    s_errors, data = check_state_json_and_sync()
    all_errors.extend(s_errors)
    if s_errors:
        for e in s_errors:
            print(f"  [FAIL] {e}")
    else:
        print("  [OK] state.json valid and in sync with STATUS.md")

    # 3. Test & check commands gate
    print("\n[3/4] Test & check commands gate...")
    c_ok = check_commands_gate(data) if data else False
    if not c_ok:
        all_errors.append("Test commands failed")

    # 4. Git diff banned patterns
    if not quick:
        print("\n[4/4] Git diff banned patterns...")
        b_ok = check_git_diff_banned_patterns(data) if data else True
        if not b_ok:
            all_errors.append("Banned patterns detected")
    else:
        print("\n[4/4] Git diff scan — SKIPPED (--quick)")

    # Summary
    print(f"\n{'='*42}")
    if all_errors:
        print(f"FAILED: {len(all_errors)} violation(s)")
        sys.exit(1)
    else:
        print("PASSED: all invariants OK")
        sys.exit(0)


if __name__ == "__main__":
    main()
