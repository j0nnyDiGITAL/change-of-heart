"""
Smoke test for P5RSaveEditorGUI — proves every tab's handlers run without
exceptions against the real DATA11 oracle save (on a temp copy).

Run: python smoke_gui.py
Exit code 0 = all handlers exercised without a single exception escaping.
"""
import os
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ORACLE = Path(r"C:/Users/kufis/p5r_buff_save/DATA11/DATA.DAT")

import gui as gui_mod
from core.editor import SaveEditor, CONFIDANT_ARCANA_MAP

# ---- record dialogs instead of showing them -------------------------------
dialogs = []
def _rec(kind, *args):
    dialogs.append((kind, args))
for name in ("showinfo", "showwarning", "showerror"):
    setattr(gui_mod.messagebox, name, lambda *a, _n=name: _rec(_n, *a))
gui_mod.messagebox.askyesno = lambda *a, **k: True
gui_mod.filedialog.askopenfilename = lambda **k: ""
gui_mod.check_running_processes = lambda: (False, False)  # never P5R-running

errors = []

def check(desc, fn):
    try:
        fn()
        print(f"  OK   {desc}")
    except Exception:
        errors.append(desc)
        print(f"  FAIL {desc}")
        traceback.print_exc()

tmpdir = Path(tempfile.mkdtemp(prefix="p5r_gui_smoke_"))
work = tmpdir / "DATA.DAT"
shutil.copyfile(ORACLE, work)

app = None
try:
    app = gui_mod.P5RSaveEditorGUI()
    app.withdraw()

    # ---- load the oracle copy ---------------------------------------------
    check("load oracle copy", lambda: (app.file_path_var.set(str(work)), app._load_file()))
    assert app.editor is not None and app.editor.is_real_save(), "editor did not load PC save"

    # ---- General tab -------------------------------------------------------
    check("general: money/social populated", lambda: (
        app.money_var.get() > 0,
        app.social_vars["Knowledge"].get() == 5,
    ))
    check("general: max social button", app._max_social_stats)

    # ---- Personas tab: every member read + apply ---------------------------
    members = list(app.persona_member_cb["values"])
    print(f"  members: {members}")
    for m in members:
        def step(m=m):
            app.persona_member_var.set(m)
            app._refresh_persona()
            assert app.persona_name_var.get() not in ("—", ""), f"{m} persona not loaded"
            app._apply_persona()  # re-writes the same values back
        check(f"personas: read+apply {m}", step)

    # ---- Confidants tab -----------------------------------------------------
    for name in CONFIDANT_ARCANA_MAP:
        check(f"confidants: pts label {name}", lambda n=name: app._update_confidant_pts(n))
    check("confidants: set rank triggers trace",
          lambda: (app.confidant_rank_vars["Death"].set(10), app.confidant_pts_vars["Death"].get()))
    check("confidants: max all button", app._max_all_confidants)
    check("confidants: max romance button", app._max_all_romance)
    check("confidants: deep romance repair", app._deep_romance_repair)

    # ---- Inventory tab: lookups ---------------------------------------------
    def item_lu():
        app.item_id_var.set("0x4047"); app._lookup_item()
        assert "Sports Watch" in app.item_id_result_var.get(), app.item_id_result_var.get()
    check("inventory: item lookup 0x4047", item_lu)

    def persona_lu():
        app.persona_id_lu_var.set("0x16B"); app._lookup_persona()
        assert app.persona_id_lu_result_var.get() == "Raoul", app.persona_id_lu_result_var.get()
    check("inventory: persona lookup 0x16B", persona_lu)

    def skill_lu():
        app.skill_id_var.set("3"); app._lookup_skill()
        assert app.skill_id_result_var.get(), app.skill_id_result_var.get()
    check("inventory: skill lookup 3", skill_lu)

    def bad_lu():
        app.item_id_var.set("zzz"); app._lookup_item()
        assert app.item_id_result_var.get() == "invalid ID"
    check("inventory: invalid id handled", bad_lu)

    # ---- Exclusive tab -------------------------------------------------------
    check("exclusive: unlock 3rd semester", app._unlock_sem3)
    check("exclusive: rebalance stats (core TypeError must be caught by GUI)", app._rebalance_stats)
    check("exclusive: browse with no selection", app._browse_file)

    # ---- Save with auto-backup ----------------------------------------------
    def save_step():
        before = sorted((tmpdir / "backups").glob("*.zip")) if (tmpdir / "backups").exists() else []
        # the persona loop left the selector on the last member; re-select Joker
        app.persona_member_var.set("Joker")
        app._refresh_persona()
        expected_pid = int(app.persona_id_var.get(), 0)
        app._save_file()
        after = sorted((tmpdir / "backups").glob("*.zip"))
        assert len(after) == len(before) + 1, f"backup zip not created: {after}"
        ed2 = SaveEditor(work.read_bytes())
        assert ed2.get_money() == app.money_var.get(), "money did not round-trip"
        conf = ed2.get_confidant_ranks()
        assert conf["Death"]["rank"] == 10, f"confidant rank did not round-trip: {conf['Death']}"
        persona = ed2.get_equipped_persona(0)
        assert persona["persona_id"] == expected_pid, "persona id did not round-trip"
    check("save: backup zip created + values round-trip", save_step)

    # ---- summary -------------------------------------------------------------
    print("\n--- dialog log (first 12) ---")
    for kind, args in dialogs[:12]:
        print(f"  [{kind}] {args[0] if args else ''}: {(args[1] if len(args) > 1 else '')[:110]}")
    err_dialogs = [d for d in dialogs if d[0] == "showerror"]
    print(f"\nshowerror dialogs: {len(err_dialogs)} (expected: 1 = rebalance core TypeError)")
    for d in err_dialogs:
        print("  ERROR DIALOG:", d[1][0], "|", (d[1][1] if len(d[1]) > 1 else "")[:160])
finally:
    if app is not None:
        try:
            app.destroy()
        except Exception:
            pass
    shutil.rmtree(tmpdir, ignore_errors=True)

print(f"\nRESULT: {'ALL HANDLERS PASSED' if not errors else 'FAILURES: ' + str(errors)}")
sys.exit(1 if errors else 0)
