#!/usr/bin/env python3
"""
Deterministic verification for the P5R GUI human-first UX upgrade (2026-08-14).

Independent checker — run AFTER the subagent reports done. Verdicts come from
source assertions + test/smoke exit codes, not from reading the report.

Usage: env -u PYTHONPATH python verify_gui_ux.py
Exit 0 = all checks pass. Prints each check line.
"""
import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"E:\ai-workspace\knowledge-base\projects\p5r-save-editor")
GUI = ROOT / "gui.py"

fails = []


def check(name, ok, detail=""):
    mark = "OK  " if ok else "FAIL"
    print(f"  [{mark}] {name}" + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        fails.append(name)


# 1. Syntax
src = GUI.read_text(encoding="utf-8")
try:
    ast.parse(src)
    check("syntax: gui.py parses", True)
except SyntaxError as e:
    check("syntax: gui.py parses", False, f"line {e.lineno}: {e.msg}")

# 2. Contract methods (smoke test + handlers)
REQUIRED_METHODS = [
    "_load_file", "_save_file", "_browse_file",
    "_max_social_stats", "_max_all_confidants", "_max_all_romance",
    "_deep_romance_repair", "_unlock_sem3", "_rebalance_stats", "_unlock_compendium",
    "_refresh_persona", "_apply_persona", "_refresh_backups", "_restore_backup",
    "_update_health_badge", "_update_confidant_pts", "_confidant_pts_text",
    "_update_persona_id_name", "_update_trait_name", "_update_skill_name",
    "_lookup_item", "_lookup_persona", "_lookup_skill",
    "_pick_item_by_name", "_filter_item_names", "_schedule_item_filter", "_run_item_filter",
    "_item_name_to_id", "_persona_name_to_id", "_pick_persona_by_name",
    "_wire_dirty_tracking", "_clear_dirty", "_update_dirty_summary", "_changes_summary",
    "_guardrail_warnings", "_make_tooltip", "_attach_rank_tooltip",
]
missing = [m for m in REQUIRED_METHODS if f"def {m}(" not in src]
check("contracts: all handler methods present", not missing,
      f"missing: {missing}")

# 3. New-task methods (search box)
for m in ["_global_search", "_search_names"]:
    if f"def {m}(" in src:
        check(f"task1: method {m} present", True)
        break
else:
    check("task1: global-search method present", False, "no _global_search/_search_names")

# 4. Widget var contracts (string-referenced by smoke test)
REQUIRED_VARS = [
    "file_path_var", "money_var", "social_vars", "persona_member_cb", "persona_member_var",
    "persona_name_var", "persona_id_var", "persona_level_var", "persona_trait_var",
    "persona_exp_var", "persona_skill_vars", "persona_skill_name_vars", "persona_status_var",
    "confidant_rank_vars", "confidant_pts_vars", "confidant_romance_vars",
    "item_id_var", "item_id_result_var", "persona_id_lu_var", "persona_id_lu_result_var",
    "skill_id_var", "skill_id_result_var",
    "party_vars", "party_spinboxes", "backup_combo_var", "backup_combo",
    "health_var", "health_label", "dirty_var",
    "item_name_pick_var", "item_name_cb", "item_name_result_var",
    "persona_pick_var", "persona_pick_cb",
    "fname_var", "lname_var", "gname_var",
]
missing_vars = [v for v in REQUIRED_VARS if f"self.{v}" not in src]
check("contracts: widget vars referenced", not missing_vars,
      f"missing: {missing_vars}")

# 5. Theme survival
theme_ok = all(t in src for t in ("P5_RED", "#0F0F11", "#18181C", "#D90429"))
check("theme: colors preserved", theme_ok)

# 6. Task 2 — tab regroup (new player-perspective names)
NEW_TABS = ["Quick Actions", "Characters & Player", "Personas", "Items", "Confidants", "Tools & Undo"]
missing_tabs = [t for t in NEW_TABS if t not in src]
check("task2: tabs renamed to player perspective", not missing_tabs,
      f"missing: {missing_tabs}")

# 7. Task 2 — party grid moved OUT of inventory tab
inv_fn = src.split("def _build_tab_inventory")[1].split("\n    # ")[0] if "def _build_tab_inventory" in src else ""
party_in_inv = "self.party_vars = {}" in inv_fn
check("task2: party grid no longer built in inventory tab", not party_in_inv)

# 8. Task 3 — MAX affordance
check("task3: MAX rank text in _confidant_pts_text", "MAX" in src.split("def _confidant_pts_text")[1].split("\n    # ")[0] if "def _confidant_pts_text" in src else False)
check("task3: 'Advanced' raw-IDs collapsible present", "Advanced" in src and "Show raw IDs" in src)

# 9. Task 4 — Undo first-class header
check("task4: Undo / Restore header", "Undo / Restore" in src)

# 10. Unit tests
r = subprocess.run(
    [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
    cwd=str(ROOT), capture_output=True, text=True, timeout=300,
)
tail = (r.stdout or "").strip().splitlines()[-3:]
detail = " | ".join(tail)
combined = (r.stdout or "") + (r.stderr or "")
if not tail:
    detail = (r.stderr or "").strip().splitlines()[-3:]
    detail = " | ".join(detail) if isinstance(detail, list) else str(detail)
if r.stderr:
    detail += " | STDERR: " + r.stderr.strip().splitlines()[-1]
ok = r.returncode == 0 and "OK" in combined
check("tests: unittest suite passes (70)", ok, detail)

# 11. Headless GUI smoke
r = subprocess.run(
    [sys.executable, "smoke_gui.py"],
    cwd=str(ROOT), capture_output=True, text=True, timeout=300,
)
ok = "ALL HANDLERS PASSED" in r.stdout
check("smoke: ALL HANDLERS PASSED", ok, r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "no output")

print()
if fails:
    print(f"RESULT: {len(fails)} FAILURES — {fails}")
    sys.exit(1)
print("RESULT: ALL VERIFICATION CHECKS PASSED")
sys.exit(0)
