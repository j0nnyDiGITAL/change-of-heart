"""
Graphical User Interface (GUI) for Persona 5 Royal Save Editor
Uses Tkinter for cross-platform desktop control.

v1.1 — exposes the full verified SaveEditor feature set:
  * Personas tab: per-member equipped persona read/edit
  * Confidants tab: per-arcana rank point thresholds + story-locked hints
  * Inventory tab: item / persona / skill name lookups (dead bulk stubs removed)
  * Auto-backup of the target file before every write
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Optional
import struct

from core.editor import SaveEditor, CONFIDANT_ARCANA_MAP, ROMANCEABLE_CONFIDANTS
from core.environment import (
    discover_steam_save_dirs,
    list_save_files,
    check_running_processes,
    create_timestamped_backup,
    list_backups,
    restore_backup,
)

# Party slot names (matches SaveEditor.get_party_stats ordering)
PARTY_SLOT_NAMES = ["Joker", "Ryuji", "Morgana", "Ann", "Yusuke",
                    "Makoto", "Futaba", "Haru", "Akechi", "Kasumi"]

# Arcana -> in-game character display name (human-first labels).
CONFIDANT_DISPLAY_NAMES = {
    "Fool": "Igor",
    "Magician": "Morgana",
    "Priestess": "Makoto Niijima",
    "Empress": "Haru Okumura",
    "Emperor": "Yusuke Kitagawa",
    "Hierophant": "Sojiro Sakura",
    "Lovers": "Ann Takamaki",
    "Chariot": "Ryuji Sakamoto",
    "Justice": "Goro Akechi",
    "Hermit": "Futaba Sakura",
    "Fortune": "Chihaya Mifune",
    "Strength": "Caroline & Justine",
    "Hanged Man": "Munehisa Iwai",
    "Death": "Tae Takemi",
    "Temperance": "Sadayo Kawakami",
    "Devil": "Ichiko Ohya",
    "Tower": "Shinya Oda",
    "Star": "Hifumi Togo",
    "Moon": "Yuuki Mishima",
    "Sun": "Toranosuke Yoshida",
    "Judgement": "Sae Niijima",
    "Faith": "Kasumi Yoshizawa",
    "Councillor": "Takuto Maruki",
}


class P5RSaveEditorGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Persona 5 Royal (Steam) Save Editor v1.1")
        self.geometry("960x680")
        self.minsize(800, 550)

        self.editor: Optional[SaveEditor] = None
        self.current_file: Optional[Path] = None
        self._loaded_baseline: Optional[bytes] = None  # dirty-tracking anchor

        self._apply_persona5_theme()
        self._build_ui()
        self._auto_discover()

    def _apply_persona5_theme(self):
        """Configure sleek Persona 5 Phantom Thief high-contrast dark theme."""
        self.configure(bg="#0F0F11")
        style = ttk.Style(self)
        style.theme_use("clam")

        # Color Palette: Persona 5 Phantom Red, Pure Black, Dark Charcoal, Blood Crimson, Pure White
        P5_RED = "#D90429"
        P5_DARK_RED = "#8D0801"
        P5_BG = "#0F0F11"
        P5_PANEL = "#18181C"
        P5_FG = "#FFFFFF"
        P5_ACCENT = "#EF233C"
        P5_MUTED = "#8E8E93"

        style.configure(".", background=P5_BG, foreground=P5_FG, font=("Segoe UI", 9))
        style.configure("TFrame", background=P5_BG)
        style.configure("TLabel", background=P5_BG, foreground=P5_FG)
        style.configure("TLabelframe", background=P5_PANEL, foreground=P5_ACCENT, relief="solid", borderwidth=1)
        style.configure("TLabelframe.Label", background=P5_PANEL, foreground=P5_ACCENT, font=("Segoe UI", 10, "bold"))
        
        style.configure("TButton", background=P5_RED, foreground="#FFFFFF", font=("Segoe UI", 9, "bold"), borderwidth=0, padding=(10, 6))
        style.map("TButton",
                  background=[("active", P5_ACCENT), ("disabled", "#2A2A2E")],
                  foreground=[("disabled", "#55555A")])

        # Prominent Action Button Style (e.g. Save / Resign)
        style.configure("Action.TButton", background="#D90429", foreground="#FFFFFF", font=("Segoe UI", 10, "bold"), padding=(16, 8))
        style.map("Action.TButton",
                  background=[("active", "#FF0033"), ("disabled", "#2A2A2E")],
                  foreground=[("disabled", "#55555A")])

        style.configure("TNotebook", background=P5_BG, borderwidth=0)
        style.configure("TNotebook.Tab", background="#1C1C22", foreground="#8E8E93", padding=[16, 8], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab",
                  background=[("selected", P5_RED), ("active", P5_DARK_RED)],
                  foreground=[("selected", "#FFFFFF"), ("active", "#FFFFFF")])

        style.configure("TEntry", fieldbackground="#24242A", foreground="#FFFFFF", insertcolor="#FFFFFF", borderwidth=1)
        style.configure("TCombobox", fieldbackground="#24242A", background=P5_RED, foreground="#FFFFFF")
        style.configure("TSpinbox", fieldbackground="#24242A", foreground="#FFFFFF", arrowcolor="#FFFFFF")
        style.configure("TCheckbutton", background=P5_BG, foreground=P5_FG)
        style.map("TCheckbutton", background=[("active", P5_BG)])

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        # Top Stylized Persona 5 Banner
        banner = tk.Frame(self, bg="#D90429", height=45)
        banner.pack(fill=tk.X, side=tk.TOP)
        banner.pack_propagate(False)

        title_lbl = tk.Label(
            banner, text="★ PERSONA 5 ROYAL // PHANTOM SAVE EDITOR ★",
            font=("Segoe UI Black", 13, "italic bold"),
            bg="#D90429", fg="#FFFFFF", padx=15
        )
        title_lbl.pack(side=tk.LEFT, fill=tk.Y)

        sub_lbl = tk.Label(
            banner, text="PC STEAM NATIVE (0x31) // VERIFIED ENGINE v1.2",
            font=("Segoe UI", 8, "bold"),
            bg="#D90429", fg="#FFCCCC", padx=10
        )
        sub_lbl.pack(side=tk.RIGHT, fill=tk.Y)

        # Top Bar - File & Discovery
        top_frame = ttk.LabelFrame(self, text=" SAVE FILE SELECTION & INTEGRITY ")
        top_frame.pack(fill=tk.X, padx=12, pady=(8, 4))

        ttk.Label(top_frame, text="File Path:").pack(side=tk.LEFT, padx=5, pady=5)
        self.file_path_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.file_path_var, width=55).pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)

        ttk.Button(top_frame, text="Browse...", command=self._browse_file).pack(side=tk.LEFT, padx=4, pady=5)
        ttk.Button(top_frame, text="Load", command=self._load_file).pack(side=tk.LEFT, padx=4, pady=5)

        # Integrity health badge (header CRC / data CRC / AES)
        self.health_var = tk.StringVar(value="— no save loaded —")
        self.health_label = ttk.Label(
            top_frame, textvariable=self.health_var,
            font=("Segoe UI", 9, "bold"), foreground="#8E8E93",
        )
        self.health_label.pack(side=tk.RIGHT, padx=10, pady=5)

        # Global search: jump straight to the tab + field for a typed name
        # (item / persona / confidant / party member). Works with no save
        # loaded too — static name tables are searched.
        search_row = ttk.Frame(top_frame)
        search_row.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=(0, 6))
        ttk.Label(search_row, text="🔍 Search:").pack(side=tk.LEFT, padx=(6, 4))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var, width=32)
        search_entry.pack(side=tk.LEFT, padx=4)
        search_entry.bind("<Return>", lambda e: self._global_search())
        ttk.Button(search_row, text="Search", command=self._global_search).pack(side=tk.LEFT, padx=4)
        ttk.Label(search_row, text="(item, persona, confidant, party member)",
                  foreground="#8E8E93").pack(side=tk.LEFT, padx=8)

        # Tabbed Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.tab_home = ttk.Frame(self.notebook)
        self.tab_general = ttk.Frame(self.notebook)
        self.tab_personas = ttk.Frame(self.notebook)
        self.tab_inventory = ttk.Frame(self.notebook)
        self.tab_confidants = ttk.Frame(self.notebook)
        self.tab_exclusive = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_home, text=" ⚡ Quick Actions ")
        self.notebook.add(self.tab_general, text=" Characters & Player ")
        self.notebook.add(self.tab_personas, text=" Personas ")
        self.notebook.add(self.tab_inventory, text=" Items ")
        self.notebook.add(self.tab_confidants, text=" Confidants ")
        self.notebook.add(self.tab_exclusive, text=" Tools & Undo ")

        self._build_tab_general()
        self._build_tab_personas()
        self._build_tab_inventory()
        self._build_tab_confidants()
        self._build_tab_exclusive()
        # Home tab builds last: it references vars created by the tabs above.
        self._build_tab_home()

        # Bottom Bar - Save & Backup
        bottom_frame = tk.Frame(self, bg="#141418", height=50)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=0, pady=0)
        bottom_frame.pack_propagate(False)

        self.status_var = tk.StringVar(value="Ready. Select or auto-discover a P5R save file.")
        status_lbl = tk.Label(
            bottom_frame, textvariable=self.status_var,
            bg="#141418", fg="#BBBBBB", font=("Segoe UI", 9), anchor=tk.W, padx=12
        )
        status_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Dirty-change indicator (oracle #1: dirty state + save summary)
        self.dirty_var = tk.StringVar(value="")
        dirty_lbl = tk.Label(
            bottom_frame, textvariable=self.dirty_var,
            bg="#141418", fg="#D90429", font=("Segoe UI", 9, "bold"), padx=8
        )
        dirty_lbl.pack(side=tk.LEFT)

        save_btn = ttk.Button(
            bottom_frame, text="SAVE CHANGES & RE-SIGN (CRC+AES) ★",
            style="Action.TButton",
            command=self._save_file
        )
        save_btn.pack(side=tk.RIGHT, padx=12, pady=6)

        self._wire_dirty_tracking()

    def _build_tab_home(self):
        """⚡ Quick Actions — one-click power moves (oracle #1 recommendation)."""
        f = ttk.Frame(self.tab_home, padding=14)
        f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(f, text="One-click power moves — no ID hunting, no tab-hopping.",
                  font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(0, 10))

        # Row 1: money + social stats
        row1 = ttk.LabelFrame(f, text=" 💰 Money & Social Stats ")
        row1.pack(fill=tk.X, pady=6)
        ttk.Label(row1, text="Yen:").grid(row=0, column=0, sticky=tk.W, padx=8, pady=4)
        ttk.Spinbox(row1, from_=0, to=9999999, textvariable=self.money_var, width=12).grid(row=0, column=1, padx=4)
        ttk.Button(row1, text="Max Money (¥9,999,999)", command=lambda: self.money_var.set(9999999)).grid(row=0, column=2, padx=8)
        ttk.Button(row1, text="Max All Social Stats", command=self._max_social_stats).grid(row=0, column=3, padx=8)

        # Row 2: confidant quick moves
        row2 = ttk.LabelFrame(f, text=" 💖 Confidants ")
        row2.pack(fill=tk.X, pady=6)
        ttk.Button(row2, text="Max All Confidants (Rank 10)", command=self._max_all_confidants).grid(row=0, column=0, padx=8, pady=6)
        ttk.Button(row2, text="Max All Romance Flags", command=self._max_all_romance).grid(row=0, column=1, padx=8)
        ttk.Button(row2, text="Deep Romance Repair", command=self._deep_romance_repair).grid(row=0, column=2, padx=8)

        # Row 3: rescue tools
        row3 = ttk.LabelFrame(f, text=" 🛟 Rescue Tools ")
        row3.pack(fill=tk.X, pady=6)
        ttk.Button(row3, text="Unlock 3rd Semester", command=self._unlock_sem3).grid(row=0, column=0, padx=8, pady=6)
        ttk.Button(row3, text="Re-Balance Party Stats", command=self._rebalance_stats).grid(row=0, column=1, padx=8)

        # Row 4: backup / undo
        row4 = ttk.LabelFrame(f, text=" ↩ Undo / Restore (backups) ")
        row4.pack(fill=tk.X, pady=6)
        ttk.Button(row4, text="Refresh Backups", command=self._refresh_backups).grid(row=0, column=0, padx=8, pady=6)
        self.backup_combo_var = tk.StringVar()
        self.backup_combo = ttk.Combobox(row4, textvariable=self.backup_combo_var, width=46, state="readonly")
        self.backup_combo.grid(row=0, column=1, padx=4)
        ttk.Button(row4, text="Restore Selected", command=self._restore_backup).grid(row=0, column=2, padx=8)
        ttk.Label(row4, text="Every save auto-backs-up first. Pick a backup and restore to roll back.",
                  foreground="gray").grid(row=1, column=0, columnspan=3, sticky=tk.W, padx=8, pady=(0, 6))

        ttk.Label(f, text="Changes are applied on 'Save Changes & Re-Sign' — you'll see a summary of exactly what changed before anything is written.",
                  foreground="gray", wraplength=760).pack(anchor=tk.W, pady=(12, 0))

    def _build_tab_general(self):
        f = ttk.Frame(self.tab_general, padding=10)
        f.pack(fill=tk.BOTH, expand=True)

        # Player Names
        ttk.Label(f, text="Joker First Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.fname_var = tk.StringVar()
        ttk.Entry(f, textvariable=self.fname_var).grid(row=0, column=1, sticky=tk.EW, pady=5)

        ttk.Label(f, text="Joker Last Name:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.lname_var = tk.StringVar()
        ttk.Entry(f, textvariable=self.lname_var).grid(row=1, column=1, sticky=tk.EW, pady=5)

        ttk.Label(f, text="Phantom Thief Team Name:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.gname_var = tk.StringVar()
        ttk.Entry(f, textvariable=self.gname_var).grid(row=2, column=1, sticky=tk.EW, pady=5)

        # Yen
        ttk.Label(f, text="Yen / Money:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.money_var = tk.IntVar()
        ttk.Entry(f, textvariable=self.money_var).grid(row=3, column=1, sticky=tk.EW, pady=5)

        # Social Stats
        sf = ttk.LabelFrame(f, text=" Social Stats (Level 1-5) ")
        sf.grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=10)

        self.social_vars = {}
        stats = ["Knowledge", "Charm", "Proficiency", "Kindness", "Guts"]
        for i, s in enumerate(stats):
            ttk.Label(sf, text=f"{s}:").grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
            var = tk.IntVar(value=5)
            self.social_vars[s] = var
            ttk.Spinbox(sf, from_=1, to=5, textvariable=var, width=5).grid(row=i, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Button(sf, text="Set All Social Stats to Max (5)", command=self._max_social_stats).grid(row=5, column=0, columnspan=2, pady=5)

        # Party Stats Grid (player data — lives with Characters & Player)
        pf = ttk.LabelFrame(f, text=" Party Stats (10 character slots) ")
        pf.grid(row=5, column=0, columnspan=2, sticky=tk.EW, pady=10)

        headers = ["Character", "Level", "HP", "SP", "MaxHP", "MaxSP"]
        for col, h in enumerate(headers):
            ttk.Label(pf, text=h, font=("Segoe UI", 9, "bold")).grid(row=0, column=col, padx=4, pady=4)

        self.party_vars = {}
        self.party_spinboxes = {}
        for i in range(10):
            self.party_vars[i] = {
                "level": tk.IntVar(value=1), "hp": tk.IntVar(value=1),
                "sp": tk.IntVar(value=1), "max_hp": tk.IntVar(value=1),
                "max_sp": tk.IntVar(value=1),
            }
            self.party_spinboxes[i] = {}
            ttk.Label(pf, text=PARTY_SLOT_NAMES[i]).grid(row=i + 1, column=0, padx=4, pady=2)
            for col, key in enumerate(["level", "hp", "sp", "max_hp", "max_sp"], start=1):
                spin = ttk.Spinbox(pf, from_=1, to=999, textvariable=self.party_vars[i][key], width=6)
                spin.grid(row=i + 1, column=col, padx=4, pady=2)
                self.party_spinboxes[i][key] = spin

        ttk.Label(pf, text="Note: only slots the game has populated are active; untouched slots keep their values. "
                           "MaxHP/MaxSP are not yet located in the PC payload and are read-only there.",
                  foreground="gray").grid(row=12, column=0, columnspan=6, sticky=tk.W, padx=4, pady=6)

    def _build_tab_personas(self):
        f = ttk.Frame(self.tab_personas, padding=10)
        f.pack(fill=tk.BOTH, expand=True)

        # Member selector
        sel = ttk.Frame(f)
        sel.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(sel, text="Party Member:").pack(side=tk.LEFT, padx=5)
        self.persona_member_var = tk.StringVar()
        self.persona_member_cb = ttk.Combobox(sel, textvariable=self.persona_member_var,
                                              state="readonly", width=14)
        self.persona_member_cb.pack(side=tk.LEFT, padx=5)
        self.persona_member_cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_persona())
        ttk.Button(sel, text="Refresh", command=self._refresh_persona).pack(side=tk.LEFT, padx=5)
        self.persona_status_var = tk.StringVar(value="Select a member to view their equipped persona.")
        ttk.Label(sel, textvariable=self.persona_status_var, foreground="gray").pack(side=tk.LEFT, padx=10)

        # Read-only summary
        info = ttk.LabelFrame(f, text=" Equipped Persona (read-only) ")
        info.pack(fill=tk.X, pady=5)

        self.persona_name_var = tk.StringVar(value="—")
        self.persona_lvl_disp_var = tk.StringVar(value="—")
        self.persona_trait_disp_var = tk.StringVar(value="—")
        self.persona_exp_disp_var = tk.StringVar(value="—")
        self.persona_flags_var = tk.StringVar(value="—")
        self.persona_stats_var = tk.StringVar(value="—")

        ttk.Label(info, text="Persona:").grid(row=0, column=0, sticky=tk.W, padx=6, pady=2)
        ttk.Label(info, textvariable=self.persona_name_var, font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky=tk.W, padx=6)
        ttk.Label(info, text="Level:").grid(row=0, column=2, sticky=tk.W, padx=6)
        ttk.Label(info, textvariable=self.persona_lvl_disp_var).grid(row=0, column=3, sticky=tk.W, padx=6)
        ttk.Label(info, text="Trait:").grid(row=1, column=0, sticky=tk.W, padx=6)
        ttk.Label(info, textvariable=self.persona_trait_disp_var).grid(row=1, column=1, sticky=tk.W, padx=6)
        ttk.Label(info, text="EXP:").grid(row=1, column=2, sticky=tk.W, padx=6)
        ttk.Label(info, textvariable=self.persona_exp_disp_var).grid(row=1, column=3, sticky=tk.W, padx=6)
        ttk.Label(info, text="Flags:").grid(row=2, column=0, sticky=tk.W, padx=6)
        ttk.Label(info, textvariable=self.persona_flags_var).grid(row=2, column=1, sticky=tk.W, padx=6)
        ttk.Label(info, text="Stats (St/Ma/En/Ag/Lu):").grid(row=2, column=2, sticky=tk.W, padx=6)
        ttk.Label(info, textvariable=self.persona_stats_var).grid(row=2, column=3, sticky=tk.W, padx=6)

        # Editable fields
        edit = ttk.LabelFrame(f, text=" Edit Persona ")
        edit.pack(fill=tk.BOTH, expand=True, pady=5)

        # NAME-driven controls (always visible, human-first).
        ttk.Label(edit, text="Persona:").grid(row=0, column=0, sticky=tk.W, padx=6, pady=3)
        self.persona_pick_var = tk.StringVar()
        self.persona_pick_cb = ttk.Combobox(edit, textvariable=self.persona_pick_var, width=30)
        self.persona_pick_cb.grid(row=0, column=1, padx=4, columnspan=2, sticky=tk.W)
        self.persona_pick_cb.bind("<<ComboboxSelected>>", self._pick_persona_by_name)
        ttk.Label(edit, text="Level:").grid(row=0, column=3, sticky=tk.W, padx=(12, 2))
        self.persona_level_var = tk.IntVar(value=1)
        ttk.Spinbox(edit, from_=1, to=99, textvariable=self.persona_level_var, width=5).grid(row=0, column=4, padx=2)

        # Advanced: raw ID entry fields hidden behind a toggle (default off).
        adv = ttk.LabelFrame(edit, text=" Advanced (raw IDs) ")
        adv.grid(row=1, column=0, columnspan=6, sticky=tk.EW, padx=6, pady=6)
        self.show_raw_ids_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(adv, text="Show raw IDs", variable=self.show_raw_ids_var,
                        command=self._toggle_raw_ids).grid(row=0, column=0, columnspan=6, sticky=tk.W, padx=6, pady=2)

        pid_lbl = ttk.Label(adv, text="Persona ID:")
        pid_lbl.grid(row=1, column=0, sticky=tk.W, padx=6, pady=2)
        self.persona_id_var = tk.StringVar()
        id_ent = ttk.Entry(adv, textvariable=self.persona_id_var, width=8)
        id_ent.grid(row=1, column=1, padx=2)
        self.persona_id_name_var = tk.StringVar(value="—")
        ttk.Label(adv, textvariable=self.persona_id_name_var, foreground="#1a6e1a", width=22).grid(row=1, column=2, sticky=tk.W, padx=4)
        self.persona_id_var.trace_add("write", lambda *a: self._update_persona_id_name())

        trait_lbl = ttk.Label(adv, text="Trait ID:")
        trait_lbl.grid(row=1, column=3, sticky=tk.W, padx=(12, 2))
        self.persona_trait_var = tk.StringVar()
        trait_ent = ttk.Entry(adv, textvariable=self.persona_trait_var, width=8)
        trait_ent.grid(row=1, column=4, padx=2)
        self.persona_trait_name_var = tk.StringVar(value="—")
        ttk.Label(adv, textvariable=self.persona_trait_name_var, foreground="#1a6e1a", width=24).grid(row=1, column=5, sticky=tk.W, padx=4)
        self.persona_trait_var.trace_add("write", lambda *a: self._update_trait_name())

        exp_lbl = ttk.Label(adv, text="EXP:")
        exp_lbl.grid(row=2, column=0, sticky=tk.W, padx=6, pady=2)
        self.persona_exp_var = tk.StringVar()
        exp_ent = ttk.Entry(adv, textvariable=self.persona_exp_var, width=10)
        exp_ent.grid(row=2, column=1, sticky=tk.W, padx=4)

        skills_lbl = ttk.Label(adv, text="Skills (IDs, 0 = empty):")
        skills_lbl.grid(row=3, column=0, columnspan=6, sticky=tk.W, padx=6, pady=2)
        self.persona_skill_vars = []
        self.persona_skill_name_vars = []
        self._raw_id_hideable = []
        for i in range(8):
            col = (i % 2) * 3          # two skill cells per row
            row = 4 + (i // 2)         # 4 rows of 2
            s_lbl = ttk.Label(adv, text=f"S{i + 1}:")
            s_lbl.grid(row=row, column=col, sticky=tk.W, padx=(6, 2), pady=2)
            var = tk.StringVar()
            ent = ttk.Entry(adv, textvariable=var, width=7)
            ent.grid(row=row, column=col + 1, padx=2)
            name_var = tk.StringVar(value="—")
            ttk.Label(adv, textvariable=name_var, foreground="#1a6e1a", width=22).grid(row=row, column=col + 2, sticky=tk.W, padx=4)
            self.persona_skill_vars.append(var)
            self.persona_skill_name_vars.append(name_var)
            var.trace_add("write", lambda *a, idx=i: self._update_skill_name(idx))
            self._raw_id_hideable.append((s_lbl, s_lbl.grid_info()))
            self._raw_id_hideable.append((ent, ent.grid_info()))

        # Raw-ID labels + entry fields toggle; the name labels stay visible.
        for w in (pid_lbl, id_ent, trait_lbl, trait_ent, exp_lbl, exp_ent, skills_lbl):
            self._raw_id_hideable.append((w, w.grid_info()))
        self._toggle_raw_ids()  # apply the default hidden state

        btn_row = ttk.Frame(edit)
        btn_row.grid(row=2, column=0, columnspan=6, sticky=tk.W, padx=6, pady=6)
        ttk.Button(btn_row, text="Apply to Save", command=self._apply_persona).pack(side=tk.LEFT, padx=5)
        ttk.Label(btn_row, text="Applies to the in-memory editor; use 'Save Changes & Re-Sign' to write to disk.",
                  foreground="gray").pack(side=tk.LEFT, padx=10)

    def _build_tab_inventory(self):
        f = ttk.Frame(self.tab_inventory, padding=10)
        f.pack(fill=tk.BOTH, expand=True)

        # Human-first: find items by NAME. The ID is filled in automatically.
        sf = ttk.LabelFrame(f, text=" 🔍 Find an item by name ")
        sf.pack(fill=tk.X, pady=(0, 8))

        self.item_name_pick_var = tk.StringVar()
        self.item_name_cb = ttk.Combobox(sf, textvariable=self.item_name_pick_var, width=56)
        self.item_name_cb.pack(side=tk.LEFT, padx=6, pady=5)
        self.item_name_result_var = tk.StringVar(value="Pick an item from the list — its ID fills in automatically.")
        ttk.Label(sf, textvariable=self.item_name_result_var, foreground="#1a6e1a").pack(side=tk.LEFT, padx=8)
        self.item_name_cb.bind("<<ComboboxSelected>>", self._pick_item_by_name)
        self.item_name_cb.bind("<Return>", self._pick_item_by_name)
        # Debounced filtering (oracle: 150-250ms avoids Tkinter stutter on 700+
        # items; >=2 chars minimum per the same review).
        self._item_filter_job = None
        self.item_name_pick_var.trace_add("write", lambda *a: self._schedule_item_filter())

        ttk.Label(sf, text="(type to filter — e.g. 'med', 'soma', 'lockpick')",
                  foreground="gray").pack(anchor=tk.W, padx=6, pady=(0, 5))

        # Advanced: raw ID lookups (power users / verification only)
        lf = ttk.LabelFrame(f, text=" 🧪 Advanced — raw ID lookups (power users) ")
        lf.pack(fill=tk.X, pady=(0, 8))

        self.item_id_var = tk.StringVar()
        self.item_id_result_var = tk.StringVar(value="—")
        self.persona_id_lu_var = tk.StringVar()
        self.persona_id_lu_result_var = tk.StringVar(value="—")
        self.skill_id_var = tk.StringVar()
        self.skill_id_result_var = tk.StringVar(value="—")

        ttk.Label(lf, text="Item ID:").grid(row=0, column=0, sticky=tk.W, padx=6, pady=3)
        ttk.Entry(lf, textvariable=self.item_id_var, width=10).grid(row=0, column=1, padx=4)
        ttk.Button(lf, text="Look up", command=self._lookup_item).grid(row=0, column=2, padx=4)
        ttk.Label(lf, textvariable=self.item_id_result_var, foreground="#1a6e1a").grid(row=0, column=3, sticky=tk.W, padx=6)

        ttk.Label(lf, text="Persona ID:").grid(row=1, column=0, sticky=tk.W, padx=6, pady=3)
        ttk.Entry(lf, textvariable=self.persona_id_lu_var, width=10).grid(row=1, column=1, padx=4)
        ttk.Button(lf, text="Look up", command=self._lookup_persona).grid(row=1, column=2, padx=4)
        ttk.Label(lf, textvariable=self.persona_id_lu_result_var, foreground="#1a6e1a").grid(row=1, column=3, sticky=tk.W, padx=6)

        ttk.Label(lf, text="Skill ID:").grid(row=2, column=0, sticky=tk.W, padx=6, pady=3)
        ttk.Entry(lf, textvariable=self.skill_id_var, width=10).grid(row=2, column=1, padx=4)
        ttk.Button(lf, text="Look up", command=self._lookup_skill).grid(row=2, column=2, padx=4)
        ttk.Label(lf, textvariable=self.skill_id_result_var, foreground="#1a6e1a").grid(row=2, column=3, sticky=tk.W, padx=6)

    def _build_tab_confidants(self):
        container = ttk.Frame(self.tab_confidants)
        container.pack(fill=tk.BOTH, expand=True)

        # Scrollable grid
        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.confidant_frame = ttk.Frame(canvas)
        self.confidant_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.confidant_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Header row
        ttk.Label(self.confidant_frame, text="Confidant", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky=tk.W, padx=8, pady=5)
        ttk.Label(self.confidant_frame, text="Rank (0-10)", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=1, padx=8, pady=5)
        ttk.Label(self.confidant_frame, text="Romance", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=2, padx=8, pady=5)
        ttk.Label(self.confidant_frame, text="Points written for rank", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=3, sticky=tk.W, padx=8, pady=5)

        self.confidant_rank_vars = {}
        self.confidant_romance_vars = {}
        self.confidant_pts_vars = {}
        for row, (name, arc_id) in enumerate(CONFIDANT_ARCANA_MAP.items(), start=1):
            display = CONFIDANT_DISPLAY_NAMES.get(name, name)
            ttk.Label(self.confidant_frame, text=display).grid(
                row=row, column=0, sticky=tk.W, padx=8, pady=2)
            rank_var = tk.IntVar(value=0)
            ttk.Spinbox(self.confidant_frame, from_=0, to=10, textvariable=rank_var, width=5).grid(
                row=row, column=1, padx=8, pady=2)
            self.confidant_rank_vars[name] = rank_var
            if arc_id in ROMANCEABLE_CONFIDANTS:
                rom_var = tk.BooleanVar(value=False)
                ttk.Checkbutton(self.confidant_frame, text="♥", variable=rom_var).grid(
                    row=row, column=2, padx=8, pady=2)
                self.confidant_romance_vars[name] = rom_var
            pts_var = tk.StringVar(value="—")
            ttk.Label(self.confidant_frame, textvariable=pts_var, foreground="#1a6e1a").grid(
                row=row, column=3, sticky=tk.W, padx=8, pady=2)
            self.confidant_pts_vars[name] = pts_var
            rank_var.trace_add("write", lambda *a, n=name: self._update_confidant_pts(n))

        # Buttons row
        btn_row = ttk.Frame(self.tab_confidants)
        btn_row.pack(fill=tk.X, padx=10, pady=6)
        ttk.Button(btn_row, text="Max All Confidants (Rank 10)", command=self._max_all_confidants).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_row, text="Max All Romance Flags", command=self._max_all_romance).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_row, text="Deep Romance Repair (Clean Leaked Bitmasks)", command=self._deep_romance_repair).pack(side=tk.LEFT, padx=5)

        # Safe Mode / Smart Clamping (default ON): guardrail warnings before
        # writing ranks the current in-game calendar cannot support.
        self.safe_mode_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            btn_row,
            text="Safe Mode (calendar-aware rank warnings)",
            variable=self.safe_mode_var,
        ).pack(side=tk.RIGHT, padx=8)

        # Hover tooltips for story-deadline confidants.
        self._tooltips: dict = {}
        for name in ("Faith", "Councillor"):
            if name in self.confidant_rank_vars:
                self._attach_rank_tooltip(name)

    def _build_tab_exclusive(self):
        f = ttk.Frame(self.tab_exclusive, padding=10)
        f.pack(fill=tk.BOTH, expand=True)

        # 3rd Semester Unlocker
        box1 = ttk.LabelFrame(f, text=" 🌟 3rd Semester Emergency Rescue Tool ")
        box1.pack(fill=tk.X, pady=10, padx=5)

        ttk.Label(
            box1,
            text="Locked out of 3rd Semester if Maruki wasn't Rank 9 by Nov 18?\nThis button forces Maruki Rank 9, Kasumi Rank 5, Akechi Rank 8, and flips story bitmasks in unison.",
            wraplength=700,
        ).pack(anchor=tk.W, padx=5, pady=5)

        ttk.Button(box1, text="Unlock 3rd Semester Now", command=self._unlock_sem3).pack(anchor=tk.W, padx=5, pady=5)

        # Stat De-Bloater
        box2 = ttk.LabelFrame(f, text=" ⚖️ Stat De-Bloater / Normalizer ")
        box2.pack(fill=tk.X, pady=10, padx=5)

        ttk.Label(
            box2,
            text="Downloaded a 100% GameBanana save with boring 999 HP/SP overkill?\nThis tool recalculates legal level-based HP/SP caps while keeping all items, gear, and NG+ unlocks.",
            wraplength=700,
        ).pack(anchor=tk.W, padx=5, pady=5)

        ttk.Button(box2, text="Re-Balance Party HP/SP Stats", command=self._rebalance_stats).pack(anchor=tk.W, padx=5, pady=5)

        # 100% Compendium box REMOVED 2026-08-14: the 0x20000 64-byte layout was
        # disproven against the 100% oracle save (43/896 flagged vs 232 expected).
        # unlock_compendium_100() honestly returns "unsupported" on PC saves;
        # advertising a dead feature with a false mapping claim is worse than
        # not having the button. Do not re-add without a verified layout.

        # Backup Restore moved to the ⚡ Quick Actions home tab (2026-08-14).

    # ------------------------------------------------------------- discovery
    def _auto_discover(self):
        steam_dirs = discover_steam_save_dirs()
        if steam_dirs:
            saves = list_save_files(steam_dirs[0])
            if saves:
                self.file_path_var.set(str(saves[0]))
                self._load_file()

    def _browse_file(self):
        path = filedialog.askopenfilename(filetypes=[("Save Files", "*.BIN *.DAT"), ("All Files", "*.*")])
        if path:
            self.file_path_var.set(path)
            self._load_file()

    # ---------------------------------------------------------------- load
    def _load_file(self):
        path_str = self.file_path_var.get().strip()
        if not path_str:
            messagebox.showwarning("No File Selected", "Please select or browse for a P5R save file (.BIN / .DAT).")
            return

        p = Path(path_str)
        if not p.exists() or p.is_dir():
            messagebox.showerror("Error", f"Save file not found or is a directory: {p}")
            return

        try:
            self.editor = SaveEditor(p.read_bytes())
            self.current_file = p
            self._loaded_baseline = p.read_bytes()  # dirty-tracking anchor

            # Populate UI
            hdr = self.editor.parser.header
            names = self.editor.parser.player_names

            self.fname_var.set(hdr.fname)
            self.lname_var.set(hdr.lname)
            self.gname_var.set(names.group_name_utf8)
            self.money_var.set(self.editor.get_money())

            # Social stats (populated from save so an untouched spinbox never
            # silently overwrites the player's real ranks on save)
            social = self.editor.get_social_stats()
            for sname, info in social.items():
                if sname in self.social_vars:
                    self.social_vars[sname].set(info.get("rank", 5))

            # Confidants
            confidants = self.editor.get_confidant_ranks()
            for name, info in confidants.items():
                if name in self.confidant_rank_vars:
                    self.confidant_rank_vars[name].set(info["rank"])
                if name in self.confidant_romance_vars:
                    self.confidant_romance_vars[name].set(info["romance"])
                self._update_confidant_pts(name)

            # Party stats
            party = self.editor.get_party_stats()
            is_pc = self.editor.is_real_save()
            for entry in party:
                slot_vars = self.party_vars.get(entry["slot"])
                if slot_vars:
                    for key, var in slot_vars.items():
                        val = entry.get(key)
                        if val is None:
                            # max_hp/max_sp are not located on PC payloads —
                            # leave the box disabled instead of crashing on None
                            var.set(0)
                            spin = self.party_spinboxes.get(entry["slot"], {}).get(key)
                            if spin is not None:
                                spin.config(state="disabled")
                        else:
                            var.set(val)

            # Personas tab: member list + auto-load first member
            member_names = [e.get("name", PARTY_SLOT_NAMES[e["slot"]]) for e in party] or PARTY_SLOT_NAMES
            self.persona_member_cb["values"] = member_names
            if member_names:
                self.persona_member_var.set(member_names[0])
                self._refresh_persona()

            self.status_var.set(f"Loaded save: {p.name} | Days: {hdr.day} | Playtime: {hdr.playtime // 3600}h {(hdr.playtime % 3600) // 60}m")
            if is_pc:
                qi = self.editor.get_quick_info()
                self.status_var.set(
                    f"Loaded REAL PC save: {p.name} | Day ~{qi.get('day', '?')} | Level ~{qi.get('level', '?')} | "
                    f"Money ~{qi.get('money', '?')}"
                )
            self._update_health_badge()

            # Populate name-driven dropdowns (items + personas).
            if hasattr(self, "_item_name_rev"):
                del self._item_name_rev
            self._filter_item_names()
            if hasattr(self, "persona_pick_cb"):
                self.persona_pick_cb["values"] = list(self._persona_name_to_id())
            self._clear_dirty()
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load save file:\n{e}")

    # ---------------------------------------------------------------- save
    def _save_file(self):
        if not self.editor or not self.current_file:
            messagebox.showwarning("Warning", "No active save file loaded.")
            return

        p5r_run, _ = check_running_processes()
        if p5r_run:
            if not messagebox.askyesno("Process Guard Warning", "P5R.exe is currently running! Modifying saves while game is active can cause corruption.\n\nDo you want to proceed anyway?"):
                return

        # Safe Mode: warn before writing ranks the in-game calendar rejects.
        warnings = self._guardrail_warnings()
        if warnings:
            msg = (
                "Safe Mode flags these confidant ranks for the current in-game date:\n\n"
                + "\n".join("• " + w for w in warnings)
                + "\n\nWrite them anyway?"
            )
            if not messagebox.askyesno("Safe Mode Warning", msg):
                return

        # Human confirm: show exactly what changed before writing (oracle #1).
        summary = self._changes_summary()
        if summary:
            msg = (
                "The following changes will be written:\n\n"
                + "\n".join("• " + s for s in summary)
                + "\n\nA timestamped backup is created first. Continue?"
            )
            if not messagebox.askyesno("Confirm Changes", msg):
                return

        # Auto-backup BEFORE any write (timestamped ZIP next to the target)
        try:
            backup_path = create_timestamped_backup(self.current_file)
        except Exception as e:
            messagebox.showerror("Backup Failed", f"Could not create backup ZIP; save aborted to protect your file.\n\n{e}")
            return

        try:
            # Apply UI inputs
            self.editor.parser.header.fname = self.fname_var.get()
            self.editor.parser.header.lname = self.lname_var.get()
            self.editor.set_player_names(self.fname_var.get(), self.lname_var.get(), self.gname_var.get())
            self.editor.set_money(self.money_var.get())

            stats = {s: self.social_vars[s].get() for s in self.social_vars}
            self.editor.set_social_stats(stats["Knowledge"], stats["Charm"], stats["Proficiency"], stats["Kindness"], stats["Guts"])

            # Confidants
            for name, var in self.confidant_rank_vars.items():
                arc_id = CONFIDANT_ARCANA_MAP[name]
                romance = None
                if name in self.confidant_romance_vars:
                    romance = bool(self.confidant_romance_vars[name].get())
                self.editor.set_confidant_rank(arc_id, int(var.get()), 99, romance)

            # Party stats (only populated slots). On PC payloads max_hp/max_sp
            # are not yet located — passing them would make the core API skip
            # the whole write, so they are omitted there.
            is_pc = self.editor.is_real_save()
            for slot, slot_vars in self.party_vars.items():
                kwargs = dict(
                    level=int(slot_vars["level"].get()),
                    hp=int(slot_vars["hp"].get()),
                    sp=int(slot_vars["sp"].get()),
                )
                if not is_pc:
                    kwargs.update(
                        max_hp=int(slot_vars["max_hp"].get()),
                        max_sp=int(slot_vars["max_sp"].get()),
                    )
                self.editor.set_party_stat(slot, **kwargs)

            # Write file
            out_bytes = self.editor.save_to_bytes()
            self.current_file.write_bytes(out_bytes)

            # Refresh integrity badge against the written bytes.
            self.editor = SaveEditor(self.current_file.read_bytes())
            self._loaded_baseline = self.current_file.read_bytes()
            self._update_health_badge()
            self._clear_dirty()

            if is_pc:
                messagebox.showinfo(
                    "Success",
                    "Save file re-signed and saved successfully!\n\n"
                    f"Backup saved to:\n{backup_path.name}\n\n"
                    "All edits were applied to the PC payload (names, money, social stats,\n"
                    "confidants, party, personas) and the file was re-signed (CRC + AES).",
                )
                self.status_var.set(f"Saved (PC format, all edits applied): {self.current_file.name} | Backup: {backup_path.name}")
            else:
                messagebox.showinfo("Success", f"Save file re-signed and saved successfully!\n\nBackup saved to:\n{backup_path.name}")
                self.status_var.set(f"Saved successfully: {self.current_file.name} (Backup: {backup_path.name})")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save changes:\n{e}")

    # ------------------------------------------------------ confidant points
    def _confidant_pts_text(self, name: str, rank: int) -> str:
        """What set_confidant_rank(..., points=99) will actually write."""
        if rank >= 10:
            return "MAX rank"
        ed = self.editor
        thresholds = (ed or SaveEditor).CONFIDANT_POINT_THRESHOLDS
        story_locked = (ed or SaveEditor).CONFIDANT_STORY_LOCKED
        if name in story_locked:
            return "story-locked (rank follows plot)"
        pts = thresholds.get(name, {}).get(rank)
        if pts is None:
            return "no table data (writes 99)"
        return f"writes {pts} pts to reach rank {rank}"

    def _update_confidant_pts(self, name: str):
        var = self.confidant_pts_vars.get(name)
        if var is not None:
            var.set(self._confidant_pts_text(name, int(self.confidant_rank_vars[name].get())))

    # -------------------------------------------------- guardrails + health
    def _wire_dirty_tracking(self):
        """Mark the session dirty when any editable widget changes."""
        self._dirty = False
        self._dirty_after_job = None

        def _mark(*_a):
            self._dirty = True
            self.dirty_var.set("● UNSAVED CHANGES")
            if self._dirty_after_job is not None:
                self.after_cancel(self._dirty_after_job)
            self._dirty_after_job = self.after(600, self._update_dirty_summary)

        for var in [self.money_var, self.fname_var, self.lname_var, self.gname_var]:
            var.trace_add("write", _mark)
        for var in self.social_vars.values():
            var.trace_add("write", _mark)
        for var in self.confidant_rank_vars.values():
            var.trace_add("write", _mark)
        for var in self.confidant_romance_vars.values():
            var.trace_add("write", _mark)
        for slot_vars in self.party_vars.values():
            for var in slot_vars.values():
                var.trace_add("write", _mark)

    def _clear_dirty(self):
        self._dirty = False
        self.dirty_var.set("")

    def _update_dirty_summary(self):
        """Replace the dirty badge with a short live summary of changes."""
        if not self._dirty:
            self.dirty_var.set("")
            return
        lines = self._changes_summary()
        if lines:
            self.dirty_var.set("● " + " | ".join(lines[:3]))
        else:
            self.dirty_var.set("● UNSAVED CHANGES")

    def _changes_summary(self) -> list:
        """Human-readable list of field changes vs the loaded baseline."""
        if not self.editor or self._loaded_baseline is None:
            return []
        try:
            base = SaveEditor(self._loaded_baseline)
        except Exception:
            return []
        if not base.is_real_save() or not self.editor.is_real_save():
            return []
        db = base.parser.data_payload
        dc = self.editor.parser.data_payload
        out = []

        def u16(o):
            return struct.unpack_from("<H", dc, o)[0] if len(dc) >= o + 2 else None

        def u16b(o):
            return struct.unpack_from("<H", db, o)[0] if len(db) >= o + 2 else None

        m0, m1 = self.editor.get_money(), base.get_money()
        if m0 != m1:
            out.append(f"Money {m1:,} → {m0:,}")

        social = self.editor.get_social_stats()
        sb = base.get_social_stats()
        for sname, info in social.items():
            r0, r1 = info.get("rank"), sb.get(sname, {}).get("rank")
            if r0 != r1:
                out.append(f"{sname} Lv{r1} → Lv{r0}")

        conf = self.editor.get_confidant_ranks()
        cb = base.get_confidant_ranks()
        for name, info in conf.items():
            r0, r1 = info["rank"], cb.get(name, {}).get("rank", 0)
            if r0 != r1:
                disp = CONFIDANT_DISPLAY_NAMES.get(name, name)
                out.append(f"{disp} R{r1} → R{r0}")

        party = self.editor.get_party_stats()
        pb = base.get_party_stats()
        for e0, e1 in zip(party, pb):
            nm = e0.get("name", PARTY_SLOT_NAMES[e0["slot"]])
            for k in ("level", "hp", "sp"):
                v0, v1 = e0.get(k), e1.get(k)
                if v0 is not None and v1 is not None and v0 != v1:
                    out.append(f"{nm} {k.upper()} {v1} → {v0}")
        return out

    def _attach_rank_tooltip(self, name: str):
        """Attach a hover tooltip to a confidant rank spinbox."""
        label = ttk.Label(self.confidant_frame, text="ⓘ", foreground="#2a6fb0")
        label.grid(row=list(CONFIDANT_ARCANA_MAP.keys()).index(name) + 1, column=4, padx=2)
        text = {
            "Faith": "Kasumi caps at rank 5 until the 3rd semester (January). "
                     "Ranks 6-10 only exist after the story reveal.",
            "Councillor": "Maruki must reach rank 9 by Nov 18 or the 3rd semester "
                          "locks out. He is unavailable after that date.",
        }[name]
        tip = self._make_tooltip(label, text)
        self._tooltips[name] = tip

    def _make_tooltip(self, widget, text: str):
        """Create a minimal hover tooltip bound to a widget."""
        tip = tk.Toplevel(self)
        tip.withdraw()
        tip.overrideredirect(True)
        ttk.Label(tip, text=text, background="#ffffe0", relief="solid",
                  borderwidth=1, padding=(6, 3), wraplength=320).pack()

        def _show(_e=None):
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + 20
            tip.geometry(f"+{x}+{y}")
            tip.deiconify()

        def _hide(_e=None):
            tip.withdraw()

        widget.bind("<Enter>", _show)
        widget.bind("<Leave>", _hide)
        tip.bind("<Leave>", _hide)
        return tip

    def _update_health_badge(self):
        """Refresh the top-bar integrity badge from the loaded editor."""
        if not self.editor:
            self.health_var.set("— no save loaded —")
            self.health_label.configure(foreground="#666666")
            return
        rep = self.editor.integrity_report()
        if rep.get("ok"):
            self.health_var.set("✔ CRC + AES verified")
            self.health_label.configure(foreground="#1a6e1a")
        else:
            parts = []
            if rep.get("file_crc_ok") is False:
                parts.append("file CRC")
            if rep.get("data_crc_ok") is False:
                parts.append("data CRC")
            if rep.get("aes_ok") is False:
                parts.append("AES")
            self.health_var.set("✘ MISMATCH: " + ", ".join(parts))
            self.health_label.configure(foreground="#b00020")

    def _guardrail_warnings(self) -> list:
        """Collect Safe-Mode warnings for the currently entered confidant ranks."""
        if not self.editor or not self.safe_mode_var.get():
            return []
        warnings = []
        for name, var in self.confidant_rank_vars.items():
            rank = int(var.get())
            warnings.extend(self.editor.confidant_guardrails(name, rank))
        return warnings

    # ------------------------------------------------------- backup restore
    def _refresh_backups(self):
        if not self.current_file:
            messagebox.showwarning("No File", "Load a save file first.")
            return
        backups = list_backups(self.current_file)
        names = [p.name for p in backups]
        self.backup_combo_var.set(names[0] if names else "")
        self.backup_combo["values"] = names
        self.status_var.set(f"{len(backups)} backup(s) found for {self.current_file.name}")

    def _restore_backup(self):
        if not self.current_file:
            messagebox.showwarning("No File", "Load a save file first.")
            return
        name = self.backup_combo_var.get()
        if not name:
            messagebox.showwarning("No Backup", "No backup selected. Refresh the list first.")
            return
        backup_zip = self.current_file.parent / "backups" / name
        p5r_run, _ = check_running_processes()
        if p5r_run:
            messagebox.showerror(
                "Process Guard",
                "P5R.exe is running — close the game before restoring a backup.",
            )
            return
        if not messagebox.askyesno(
            "Confirm Restore",
            f"Restore {name}?\n\nThe current state will be backed up first, "
            "so this is reversible.",
        ):
            return
        try:
            safety = restore_backup(self.current_file, backup_zip)
        except Exception as e:
            messagebox.showerror("Restore Failed", str(e))
            return
        # Reload the restored file into the editor + UI.
        try:
            self.editor = SaveEditor(self.current_file.read_bytes())
            self._load_file()
        except Exception as e:
            messagebox.showerror("Reload Failed", f"Backup restored but reload failed: {e}")
            return
        self.status_var.set(
            f"Restored {name} | prior state kept in {safety.name}"
        )

    # --------------------------------------------------------------- personas
    def _slot_for_name(self, name: str) -> Optional[int]:
        if not name:
            return None
        if self.editor:
            for e in self.editor.get_party_stats():
                if e.get("name") == name:
                    return e["slot"]
        if name in PARTY_SLOT_NAMES:
            return PARTY_SLOT_NAMES.index(name)
        return None

    def _refresh_persona(self):
        if not self.editor:
            self.persona_status_var.set("No save loaded.")
            return
        name = self.persona_member_var.get()
        slot = self._slot_for_name(name)
        if slot is None:
            self.persona_status_var.set("Pick a party member.")
            return
        p = self.editor.get_equipped_persona(slot)
        if "persona_id" not in p:
            self.persona_status_var.set(f"{name}: {p.get('message', 'no persona data')}")
            return

        self.persona_name_var.set(p["persona"])
        self.persona_lvl_disp_var.set(str(p["level"]))
        self.persona_trait_disp_var.set(p["trait"])
        self.persona_exp_disp_var.set(f"{p['exp']:,}")
        self.persona_flags_var.set(f"0x{p['flags']:04X}")
        st = p["stats"]
        self.persona_stats_var.set(f"{st['st']} / {st['ma']} / {st['en']} / {st['ag']} / {st['lu']}")

        self.persona_id_var.set(str(p["persona_id"]))
        self.persona_level_var.set(p["level"])
        self.persona_trait_var.set(str(p["trait_id"]))
        self.persona_exp_var.set(str(p["exp"]))
        for i in range(8):
            sid = p["skills"][i]["id"]
            self.persona_skill_vars[i].set(str(sid))
            self.persona_skill_name_vars[i].set(p["skills"][i]["name"])

        self.persona_status_var.set(
            f"Loaded {name} (slot {slot}) — persona_id 0x{p['persona_id']:04X} ({p['persona']})"
        )

    def _update_persona_id_name(self):
        if not self.editor:
            return
        s = self.persona_id_var.get().strip()
        try:
            self.persona_id_name_var.set(self.editor.get_persona_name(int(s, 0)) if s else "—")
        except ValueError:
            self.persona_id_name_var.set("invalid")

    def _update_trait_name(self):
        if not self.editor:
            return
        s = self.persona_trait_var.get().strip()
        try:
            self.persona_trait_name_var.set(self.editor.get_trait_name(int(s, 0)) if s else "—")
        except ValueError:
            self.persona_trait_name_var.set("invalid")

    def _update_skill_name(self, idx: int):
        if not self.editor:
            return
        s = self.persona_skill_vars[idx].get().strip()
        try:
            self.persona_skill_name_vars[idx].set(self.editor.get_skill_name(int(s, 0)) if s else "—")
        except ValueError:
            self.persona_skill_name_vars[idx].set("invalid")

    def _apply_persona(self):
        if not self.editor:
            messagebox.showwarning("Warning", "No active save file loaded.")
            return
        name = self.persona_member_var.get()
        slot = self._slot_for_name(name)
        if slot is None:
            messagebox.showwarning("Warning", "Pick a party member first.")
            return
        try:
            persona_id = int(self.persona_id_var.get().strip(), 0) if self.persona_id_var.get().strip() else None
            level = self.persona_level_var.get()
            trait_id = int(self.persona_trait_var.get().strip(), 0) if self.persona_trait_var.get().strip() else None
            exp = int(self.persona_exp_var.get().strip(), 0) if self.persona_exp_var.get().strip() else None
            skills = [int(v.get().strip(), 0) if v.get().strip() else 0 for v in self.persona_skill_vars]
        except ValueError:
            messagebox.showerror("Persona Error", "Persona/Trait/Skill IDs and EXP must be integers (decimal or 0x hex).")
            return

        try:
            res = self.editor.set_equipped_persona(
                slot, persona_id=persona_id, level=level, trait_id=trait_id,
                exp=exp, skills=skills,
            )
            self._refresh_persona()
            self.status_var.set(f"Persona updated for {name} (slot {slot}) — press Save Changes to write to disk.")
            messagebox.showinfo("Persona Updated", f"Slot {slot} ({name}) equipped persona written to the editor.\n\n{res.get('message', '')}")
        except Exception as e:
            messagebox.showerror("Persona Error", f"Could not apply persona edits:\n{e}")

    def _toggle_raw_ids(self):
        """Show/hide the raw-ID entry fields behind the 'Advanced' toggle.

        Name labels beside the entries stay visible either way; only the raw
        ID entry fields and their descriptive labels are hidden (default off).
        """
        show = self.show_raw_ids_var.get()
        for w, info in getattr(self, "_raw_id_hideable", []):
            if show:
                w.grid(**{k: v for k, v in info.items() if k != "in"})
            else:
                w.grid_remove()

    def _persona_name_to_id(self) -> dict:
        """Reverse map: persona display name -> id (built once per session)."""
        if not hasattr(self, "_persona_name_rev"):
            self._persona_name_rev = {}
            if self.editor:
                for iid, nm in self.editor._load_table("Personas.txt").items():
                    nm = nm.strip()
                    if nm and nm not in ("BLANK", "RESERVE") and nm not in self._persona_name_rev:
                        self._persona_name_rev[nm] = iid
        return self._persona_name_rev

    def _pick_persona_by_name(self, _event=None):
        """User picked a persona name -> fill the raw ID field."""
        name = self.persona_pick_var.get().strip()
        rev = self._persona_name_to_id()
        if name in rev:
            self.persona_id_var.set(str(rev[name]))
            self._update_persona_id_name()

    # -------------------------------------------------------------- lookups
    def _item_name_to_id(self) -> dict:
        """Reverse map: item display name -> id (built once per session)."""
        if not hasattr(self, "_item_name_rev"):
            self._item_name_rev = {}
            if self.editor:
                for iid, nm in self.editor._load_item_names().items():
                    nm = nm.strip()
                    if nm and nm not in self._item_name_rev:
                        self._item_name_rev[nm] = iid
        return self._item_name_rev

    def _schedule_item_filter(self):
        """Debounce item-name filtering (150ms) so typing never stutters."""
        if self._item_filter_job is not None:
            self.after_cancel(self._item_filter_job)
        self._item_filter_job = self.after(150, self._run_item_filter)

    def _run_item_filter(self):
        self._item_filter_job = None
        self._filter_item_names()

    def _filter_item_names(self):
        """Live-filter the item dropdown by what the user typed.

        Filtering runs only at >= 2 typed chars (oracle: full-list filtering
        on every keystroke stutters with 700+ items). Below that, show a
        small starter list so the box is never dead.
        """
        rev = self._item_name_to_id()
        if not rev:
            self.item_name_cb["values"] = []
            return
        q = self.item_name_pick_var.get().strip().lower()
        if len(q) < 2:
            # Starter list for browsing without typing.
            names = [n for n in rev if n.lower().startswith(("a", "b", "s", "m", "l"))][:120]
        else:
            names = [n for n in rev if q in n.lower()][:300]
        self.item_name_cb["values"] = names

    def _pick_item_by_name(self, _event=None):
        """User picked a name from the dropdown -> show id, fill the raw box."""
        name = self.item_name_pick_var.get().strip()
        rev = self._item_name_rev
        if not rev or name not in rev:
            self.item_name_result_var.set("Not found in item tables.")
            return
        iid = rev[name]
        self.item_name_result_var.set(f"{name}  →  ID {iid} (0x{iid:04X})")
        # Keep the advanced box in sync (harmless, helps verification).
        self.item_id_var.set(f"0x{iid:04X}")
        self._lookup_item()

    def _lookup_id(self, entry_var, result_var, fn):
        s = entry_var.get().strip()
        if not s:
            result_var.set("enter an ID")
            return
        try:
            iid = int(s, 0)
        except ValueError:
            result_var.set("invalid ID")
            return
        result_var.set(fn(iid))

    def _lookup_item(self):
        self._lookup_id(self.item_id_var, self.item_id_result_var,
                        lambda i: self.editor.get_item_name(i) if self.editor else "load a save first")

    def _lookup_persona(self):
        self._lookup_id(self.persona_id_lu_var, self.persona_id_lu_result_var,
                        lambda i: self.editor.get_persona_name(i) if self.editor else "load a save first")

    def _lookup_skill(self):
        self._lookup_id(self.skill_id_var, self.skill_id_result_var,
                        lambda i: self.editor.get_skill_name(i) if self.editor else "load a save first")

    # -------------------------------------------------------- global search
    def _static_item_names(self) -> dict:
        """Item name->id reverse map that also works with no save loaded."""
        rev = self._item_name_to_id()
        if rev:
            return rev
        return {nm.strip(): iid for iid, nm in SaveEditor()._load_item_names().items()
                if nm.strip()}

    def _static_persona_names(self) -> dict:
        """Persona name->id reverse map that also works with no save loaded."""
        rev = self._persona_name_to_id()
        if rev:
            return rev
        return {nm.strip(): iid for iid, nm in SaveEditor()._load_table("Personas.txt").items()
                if nm.strip() and nm.strip() not in ("BLANK", "RESERVE")}

    def _global_search(self, _event=None):
        """Jump to the tab + field matching a typed item/persona/confidant/member name.

        Case-insensitive; exact match first, then substring fallback. Works
        with no save loaded (static name tables are searched).
        """
        q = self.search_var.get().strip()
        if not q:
            self.status_var.set("Type an item, persona, confidant, or party member name to search.")
            return
        ql = q.lower()

        def _found(kind, msg):
            self.status_var.set(f"Found: {msg} ({kind})")
            return True

        # (a) items
        for nm, iid in self._static_item_names().items():
            if nm.lower() == ql:
                self.notebook.select(self.tab_inventory)
                self.item_name_pick_var.set(nm)
                self._pick_item_by_name()
                _found("item", nm)
                return
        # (b) personas
        for nm, pid in self._static_persona_names().items():
            if nm.lower() == ql:
                self.notebook.select(self.tab_personas)
                self.persona_pick_var.set(nm)
                self._pick_persona_by_name()
                _found("persona", nm)
                return
        # (c) confidants (display name; arcana key accepted as a bonus)
        for arc, nm in CONFIDANT_DISPLAY_NAMES.items():
            if nm.lower() == ql or arc.lower() == ql:
                self.notebook.select(self.tab_confidants)
                self.status_var.set(
                    f"Found: {nm} (confidant) — set Rank / Romance on this tab."
                )
                return
        # (d) party members -> personas tab member selector
        for nm in PARTY_SLOT_NAMES:
            if nm.lower() == ql:
                self.notebook.select(self.tab_personas)
                if self.persona_member_cb["values"]:
                    self.persona_member_var.set(nm)
                    self._refresh_persona()
                self.status_var.set(f"Found: {nm} (party member) — persona editor on this tab.")
                return

        # Substring fallback across all four tables (first hit wins).
        for nm, iid in self._static_item_names().items():
            if ql in nm.lower():
                self.notebook.select(self.tab_inventory)
                self.item_name_pick_var.set(nm)
                self._pick_item_by_name()
                _found("item", nm)
                return
        for nm, pid in self._static_persona_names().items():
            if ql in nm.lower():
                self.notebook.select(self.tab_personas)
                self.persona_pick_var.set(nm)
                self._pick_persona_by_name()
                _found("persona", nm)
                return
        for arc, nm in CONFIDANT_DISPLAY_NAMES.items():
            if ql in nm.lower() or ql in arc.lower():
                self.notebook.select(self.tab_confidants)
                self.status_var.set(
                    f"Found: {nm} (confidant) — set Rank / Romance on this tab."
                )
                return
        for nm in PARTY_SLOT_NAMES:
            if ql in nm.lower():
                self.notebook.select(self.tab_personas)
                if self.persona_member_cb["values"]:
                    self.persona_member_var.set(nm)
                    self._refresh_persona()
                self.status_var.set(f"Found: {nm} (party member) — persona editor on this tab.")
                return

        self.status_var.set(f"No match for '{q}'")

    # ------------------------------------------------------------- actions
    def _max_social_stats(self):
        for var in self.social_vars.values():
            var.set(5)

    def _max_all_confidants(self):
        for var in self.confidant_rank_vars.values():
            var.set(10)  # trace refreshes the points labels

    def _max_all_romance(self):
        for var in self.confidant_romance_vars.values():
            var.set(True)

    def _deep_romance_repair(self):
        if not self.editor:
            return
        try:
            res = self.editor.repair_romance_flags()
            messagebox.showinfo("Romance Repair", res["message"])
        except Exception as e:
            messagebox.showerror("Romance Repair Error", f"Could not repair romance flags:\n{e}")

    def _unlock_sem3(self):
        if not self.editor:
            return
        try:
            res = self.editor.unlock_third_semester()
            for name in self.confidant_rank_vars:
                self._update_confidant_pts(name)
            messagebox.showinfo("3rd Semester Unlocked", res["message"])
        except Exception as e:
            messagebox.showerror("3rd Semester Unlock Error", f"Could not unlock 3rd semester:\n{e}")

    def _rebalance_stats(self):
        if not self.editor:
            return
        try:
            res = self.editor.rebalance_stats()
            messagebox.showinfo("Stats Re-Balanced", res["message"])
        except Exception as e:
            messagebox.showerror("Rebalance Error", f"Could not re-balance stats:\n{e}")

    def _unlock_compendium(self):
        if not self.editor:
            messagebox.showwarning("No Save Loaded", "Please load a save file first.")
            return
        try:
            res = self.editor.unlock_compendium_100()
            if res.get("status") == "success":
                messagebox.showinfo("Compendium Unlocked", res.get("message", "Compendium 100% unlocked."))
                self.status_var.set("Compendium 100% unlocked (all personas registered) — press Save Changes to write to disk.")
            else:
                messagebox.showwarning("Notice", res.get("message", "Unable to unlock compendium."))
        except Exception as e:
            messagebox.showerror("Compendium Error", f"Could not unlock compendium:\n{e}")


if __name__ == "__main__":
    app = P5RSaveEditorGUI()
    app.mainloop()
