"""
Persona 5 Royal Web Save Editor — High-Performance Local Web Backend
Serves a sleek, highly responsive Persona 5 Phantom Thief web application
with auto-save discovery, search-by-name dropdowns, human-friendly selectors,
and zero raw ID requirements.
"""

import os
import sys
import json
import base64
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Project paths (frozen PyInstaller vs source script)
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    PROJECT_ROOT = Path(sys._MEIPASS)
    WEB_APP_DIR = PROJECT_ROOT / "web-app"
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    WEB_APP_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(PROJECT_ROOT))

from core.editor import SaveEditor, CONFIDANT_ARCANA_MAP, ROMANCEABLE_CONFIDANTS
from core.environment import (
    discover_steam_save_dirs,
    list_save_files,
    check_running_processes,
    create_timestamped_backup,
    list_backups,
    restore_backup,
)

PORT = 5055

# Cached reference tables for human-readable search & autocompletion
def build_reference_db():
    ed = SaveEditor()
    CONFIDANT_PROFILES = {
        'Fool': {'name': 'Igor', 'role': 'Prison Master', 'type': 'story', 'unlock': 'Wild Talk / Persona Fusion', 'img': 'igor.png', 'unlock_date': '4/11'},
        'Magician': {'name': 'Morgana', 'role': 'Phantom Guide / Mona', 'type': 'party', 'unlock': 'Infiltration Tools / Pickpocket', 'img': 'morgana.png', 'unlock_date': '4/15'},
        'Priestess': {'name': 'Makoto Niijima', 'role': 'Queen / Strategist', 'type': 'romance', 'unlock': 'Shadow Calc / Analysis', 'img': 'makoto.png', 'unlock_date': '6/24'},
        'Empress': {'name': 'Haru Okumura', 'role': 'Noir / Heiress', 'type': 'romance', 'unlock': 'Vegetable Gardening / SP Veggies', 'img': 'haru.png', 'unlock_date': '10/30'},
        'Emperor': {'name': 'Yusuke Kitagawa', 'role': 'Fox / Artist', 'type': 'party', 'unlock': 'Skill Card Duplication', 'img': 'yusuke.png', 'unlock_date': '6/18'},
        'Hierophant': {'name': 'Sojiro Sakura', 'role': 'Leblanc Owner / Boss', 'type': 'social', 'unlock': 'Master Coffee & Curry Brewing', 'img': 'sojiro.png', 'unlock_date': '4/20'},
        'Lovers': {'name': 'Ann Takamaki', 'role': 'Panther / Model', 'type': 'romance', 'unlock': 'Baton Pass / Girl Talk', 'img': 'ann.png', 'unlock_date': '5/6'},
        'Chariot': {'name': 'Ryuji Sakamoto', 'role': 'Skull / Track Star', 'type': 'party', 'unlock': 'Insta-Kill / Dash Ambush', 'img': 'ryuji.png', 'unlock_date': '4/12'},
        'Justice': {'name': 'Goro Akechi', 'role': 'Crow / Detective Prince', 'type': 'story_deadline', 'unlock': 'Sleuth Instinct (Deadline: 11/17)', 'img': 'akechi.png', 'unlock_date': '6/10'},
        'Hermit': {'name': 'Futaba Sakura', 'role': 'Oracle / Hacker', 'type': 'romance', 'unlock': 'Position Hack / Moral Support', 'img': 'futaba.png', 'unlock_date': '8/31'},
        'Fortune': {'name': 'Chihaya Mifune', 'role': 'Shinjuku Fortune Teller', 'type': 'romance', 'unlock': 'Affinity & Money Luck Reading', 'img': 'chihaya.png', 'unlock_date': '6/22'},
        'Strength': {'name': 'Caroline & Justine', 'role': 'Velvet Wardens', 'type': 'story', 'unlock': 'Special Guillotine / Paid Fusion', 'img': 'twins.png', 'unlock_date': '5/18'},
        'Hanged Man': {'name': 'Munehisa Iwai', 'role': 'Airsoft Shop Owner', 'type': 'social', 'unlock': 'Custom Gun Modifications', 'img': 'iwai.png', 'unlock_date': '5/6'},
        'Death': {'name': 'Tae Takemi', 'role': 'Yongen Clinic Doctor', 'type': 'romance', 'unlock': 'Clinic Medicine Discount & SP Adhesives', 'img': 'takemi.png', 'unlock_date': '4/18'},
        'Temperance': {'name': 'Sadayo Kawakami', 'role': 'Homeroom Teacher / Maid', 'type': 'romance', 'unlock': 'Housework Slack-off & Special Massage', 'img': 'kawakami.png', 'unlock_date': '5/24'},
        'Devil': {'name': 'Ichiko Ohya', 'role': 'Paparazzi Journalist', 'type': 'romance', 'unlock': 'Palace Security Alert Reduction', 'img': 'ohya.png', 'unlock_date': '6/23'},
        'Tower': {'name': 'Shinya Oda', 'role': 'Gamer Kid / King', 'type': 'social', 'unlock': 'Down Shot / Bullet Hail', 'img': 'shinya.png', 'unlock_date': '9/4'},
        'Star': {'name': 'Hifumi Togo', 'role': 'Kanda Shogi Master', 'type': 'romance', 'unlock': 'Togo System / Battle Party Swap', 'img': 'hifumi.png', 'unlock_date': '6/25'},
        'Moon': {'name': 'Yuuki Mishima', 'role': 'Phan-Site Admin', 'type': 'social', 'unlock': 'EXP Share & Backup Party EXP', 'img': 'mishima.png', 'unlock_date': '5/6'},
        'Sun': {'name': 'Toranosuke Yoshida', 'role': 'Shibuya Politician', 'type': 'social', 'unlock': 'Extortion / Smooth Talk Negotiations', 'img': 'yoshida.png', 'unlock_date': '5/6'},
        'Judgement': {'name': 'Sae Niijima', 'role': 'Prosecutor / Inquisitor', 'type': 'story', 'unlock': 'Story Progression Arcana', 'img': 'sae.png', 'unlock_date': '7/9'},
        'Faith': {'name': 'Kasumi Yoshizawa', 'role': 'Violet / Gymnast', 'type': 'romance_deadline', 'unlock': 'Chaotic Foil (Rank 5 Cap until Jan)', 'img': 'kasumi.png', 'unlock_date': '5/30'},
        'Councillor': {'name': 'Dr. Takuto Maruki', 'role': 'Shujin Counselor', 'type': 'story_deadline', 'unlock': 'Flow / Detox (Req: Rank 9 by 11/18)', 'img': 'maruki.png', 'unlock_date': '5/13'}
    }

    db = {
        "personas": [],
        "skills": [],
        "traits": [],
        "items": [],
        "confidants": list(CONFIDANT_ARCANA_MAP.keys()),
        "confidant_profiles": CONFIDANT_PROFILES,
        "romanceable": list(ROMANCEABLE_CONFIDANTS),
        "story_locked_confidants": list(SaveEditor.CONFIDANT_STORY_LOCKED),
        "point_thresholds": SaveEditor.CONFIDANT_POINT_THRESHOLDS,
    }
    
    # Personas
    ptable = ed._load_table("Personas.txt") or {}
    for pid, name in sorted(ptable.items()):
        db["personas"].append({"id": pid, "name": name})
        
    # Skills
    stable = ed._load_table("Skill ID.txt") or {}
    for sid, name in sorted(stable.items()):
        db["skills"].append({"id": sid, "name": name})
        
    # Traits
    ttable = ed._load_table("Traits.txt") or {}
    for tid, name in sorted(ttable.items()):
        db["traits"].append({"id": tid, "name": name})
        
    # Items & Categories (100% Authentic 16-bit P5R ID Resolution)
    db["items"] = []
    data_dir = PROJECT_ROOT / "data"
    
    CATEGORY_MAPPING = [
        (0x1000, "Weapon melee.txt", "Melee"),
        (0x2000, "Items.txt", "Consumable"),
        (0x3000, "Accessories.txt", "Accessory"),
        (0x4000, "Skill Cards.txt", "SkillCard"),
        (0x5000, "Clothes.txt", "Protector"),
        (0x6000, "Tools&materials.txt", "Infiltration"),
        (0x7000, "Weapon ranged.txt", "Ranged"),
        (0x8000, "Treasure.txt", "Treasure"),
        (0x9000, "Keyitems&essentials.txt", "KeyItem"),
    ]

    seen_ids = set()
    for prefix, fname, cat in CATEGORY_MAPPING:
        p = data_dir / fname
        if not p.exists():
            continue
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                for idx, line in enumerate(f):
                    parts = line.strip().split("\t")
                    en_name = None
                    if len(parts) >= 4:
                        en_name = parts[3].strip()
                    elif len(parts) == 1 and parts[0]:
                        en_name = parts[0].strip()

                    if en_name and en_name not in ["EN_NAME", "BLANK", "RESERVE", "----------", "使用禁止"] and "RESERVE" not in en_name and "BLANK" not in en_name:
                        iid = prefix | (idx & 0x0FFF)
                        if iid not in seen_ids:
                            seen_ids.add(iid)
                            db["items"].append({
                                "id": iid,
                                "name": en_name,
                                "category": cat
                            })
        except Exception as e:
            print(f"[P5R] Error loading {fname}: {e}")

    return db

REFERENCE_DB = build_reference_db()
CURRENT_EDITOR = None
CURRENT_FILE_PATH = None

class P5RWebHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_APP_DIR / "static"), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            template_path = WEB_APP_DIR / "templates" / "index.html"
            with open(template_path, "rb") as f:
                self.wfile.write(f.read())
            return
        elif parsed.path == "/game" or parsed.path == "/game/":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            game_index = PROJECT_ROOT / "p5r-game-client" / "index.html"
            with open(game_index, "rb") as f:
                self.wfile.write(f.read())
            return
        elif parsed.path.startswith("/game/"):
            rel_file = parsed.path[len("/game/"):]
            game_file = PROJECT_ROOT / "p5r-game-client" / rel_file
            if game_file.exists() and game_file.is_file():
                self.send_response(200)
                if rel_file.endswith(".css"):
                    self.send_header("Content-type", "text/css; charset=utf-8")
                elif rel_file.endswith(".js"):
                    self.send_header("Content-type", "application/javascript; charset=utf-8")
                else:
                    self.send_header("Content-type", "application/octet-stream")
                self.end_headers()
                with open(game_file, "rb") as f:
                    self.wfile.write(f.read())
                return
        elif parsed.path == "/api/database":
            self.send_json(200, REFERENCE_DB)
            return
        elif parsed.path == "/api/discovery":
            dirs = discover_steam_save_dirs()
            saves = []
            if dirs:
                for s in list_save_files(dirs[0]):
                    saves.append(str(s))
            self.send_json(200, {"discovered_dirs": [str(d) for d in dirs], "saves": saves})
            return
        elif parsed.path == "/api/backups":
            global CURRENT_FILE_PATH
            if not CURRENT_FILE_PATH or not os.path.exists(CURRENT_FILE_PATH):
                self.send_json(200, {"backups": []})
                return
            backups = [p.name for p in list_backups(Path(CURRENT_FILE_PATH))]
            self.send_json(200, {"backups": backups})
            return

        super().do_GET()

    def do_POST(self):
        global CURRENT_EDITOR, CURRENT_FILE_PATH
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        data = {}
        if body:
            try:
                data = json.loads(body.decode("utf-8"))
            except Exception:
                pass

        if parsed.path == "/api/load":
            path_str = data.get("path", "").strip()
            if not path_str or not os.path.exists(path_str):
                self.send_json(400, {"error": "Save file path does not exist."})
                return
            try:
                p = Path(path_str)
                with open(p, "rb") as f:
                    raw = f.read()
                CURRENT_EDITOR = SaveEditor(raw)
                CURRENT_FILE_PATH = str(p)

                # Assemble clean full payload
                hdr = CURRENT_EDITOR.parser.header
                names = CURRENT_EDITOR.parser.player_names
                quick_info = CURRENT_EDITOR.get_quick_info()
                integrity = CURRENT_EDITOR.integrity_report()
                confidants = CURRENT_EDITOR.get_confidant_ranks()
                social = CURRENT_EDITOR.get_social_stats()
                party = CURRENT_EDITOR.get_party_stats()

                # Get equipped persona info for each party member
                party_personas = []
                for entry in party:
                    slot = entry["slot"]
                    p_info = CURRENT_EDITOR.get_equipped_persona(slot)
                    party_personas.append({
                        "slot": slot,
                        "name": entry.get("name", f"Member {slot}"),
                        "level": entry.get("level", 1),
                        "hp": entry.get("hp", 100),
                        "sp": entry.get("sp", 50),
                        "persona": p_info
                    })

                # Parse accurate playtime from authoritative quick_info seconds
                playtime_sec = quick_info.get("playtime") or hdr.playtime or 0
                if playtime_sec > 500000: # if raw unscaled counter, normalize from quick_info
                    playtime_sec = quick_info.get("playtime", 0)

                # Get Joker's full 12-slot stock persona inventory
                joker_stock = CURRENT_EDITOR.get_persona_stock(0)
                inventory = CURRENT_EDITOR.get_inventory()
                compendium = CURRENT_EDITOR.get_compendium()

                resp = {
                    "file_path": CURRENT_FILE_PATH,
                    "header": {
                        "fname": hdr.fname,
                        "lname": hdr.lname,
                        "group_name": names.group_name_utf8,
                        "money": CURRENT_EDITOR.get_money(),
                        "day": quick_info.get("day", str(hdr.day)),
                        "level": quick_info.get("level", "22"),
                        "playtime": f"{playtime_sec // 3600}h {(playtime_sec % 3600) // 60}m"
                    },
                    "social_stats": social,
                    "confidants": confidants,
                    "party": party_personas,
                    "joker_stock": joker_stock,
                    "inventory": inventory,
                    "compendium": compendium,
                    "integrity": integrity
                }
                self.send_json(200, resp)
            except Exception as e:
                self.send_json(500, {"error": f"Failed to load save: {str(e)}"})

        elif parsed.path == "/api/save":
            if not CURRENT_EDITOR or not CURRENT_FILE_PATH:
                self.send_json(400, {"error": "No save file loaded."})
                return

            p5r_run, _ = check_running_processes()
            if p5r_run:
                self.send_json(409, {"error": "P5R.exe is currently running! Please close the game before saving."})
                return

            try:
                # 1. Automatic Timestamped Backup
                p = Path(CURRENT_FILE_PATH)
                backup_path = create_timestamped_backup(p)

                # 2. Apply Header Edits
                hdr_in = data.get("header", {})
                CURRENT_EDITOR.set_player_names(
                    hdr_in.get("fname", ""),
                    hdr_in.get("lname", ""),
                    hdr_in.get("group_name", "")
                )
                if "money" in hdr_in:
                    CURRENT_EDITOR.set_money(int(hdr_in["money"]))

                # 3. Apply Social Stats
                soc_in = data.get("social_stats", {})
                if soc_in:
                    def _extract_stat_rank(val):
                        if isinstance(val, dict):
                            return int(val.get("rank", 5))
                        return int(val) if val is not None else 5

                    CURRENT_EDITOR.set_social_stats(
                        _extract_stat_rank(soc_in.get("Knowledge", 5)),
                        _extract_stat_rank(soc_in.get("Charm", 5)),
                        _extract_stat_rank(soc_in.get("Proficiency", 5)),
                        _extract_stat_rank(soc_in.get("Kindness", 5)),
                        _extract_stat_rank(soc_in.get("Guts", 5)),
                    )

                # 4. Apply Confidants
                conf_in = data.get("confidants", {})
                for cname, cdata in conf_in.items():
                    if cname in CONFIDANT_ARCANA_MAP:
                        arc_id = CONFIDANT_ARCANA_MAP[cname]
                        rank = int(cdata.get("rank", 0)) if isinstance(cdata, dict) else int(cdata)
                        CURRENT_EDITOR.set_confidant_rank(arc_id, rank, auto_unlock=True)

                # 5. Apply Party & Persona
                party_in = data.get("party", [])
                for member in party_in:
                    slot = member.get("slot")
                    if slot is not None:
                        CURRENT_EDITOR.set_party_stat(
                            slot,
                            level=int(member.get("level", 1)),
                            hp=int(member.get("hp", 100)),
                            sp=int(member.get("sp", 50))
                        )
                        pers = member.get("persona")
                        if pers and "persona_id" in pers:
                            CURRENT_EDITOR.set_equipped_persona(
                                slot,
                                persona_id=int(pers.get("persona_id", 0)),
                                level=int(pers.get("level", 1)),
                                trait_id=int(pers.get("trait_id", 0)),
                                exp=int(pers.get("exp", 0)),
                                skills=[int(s) for s in pers.get("skills", [0]*8)],
                                stats=[int(st) for st in pers.get("stats", [10]*5)],
                                flags=int(pers.get("flags", 1))
                            )

                # 5b. Apply Joker's 12-slot Persona Stock
                stock_in = data.get("joker_stock", [])
                for s_entry in stock_in:
                    s_slot = s_entry.get("slot")
                    if s_slot is not None and 0 <= s_slot < 12:
                        pid = int(s_entry.get("persona_id", 0))
                        CURRENT_EDITOR.set_persona_stock_slot(
                            member_slot=0,
                            stock_k=s_slot,
                            persona_id=pid,
                            level=int(s_entry.get("level", 1)),
                            trait_id=int(s_entry.get("trait_id", 0)),
                            exp=int(s_entry.get("exp", 0)),
                            skills=[int(s) for s in s_entry.get("skills", [0]*8)],
                            stats=[int(st) for st in s_entry.get("stats", [10]*5)],
                            flags=int(s_entry.get("flags", 1))
                        )

                # 5c. Apply Active Inventory Items
                inv_in = data.get("inventory", [])
                for entry in inv_in:
                    slot = entry.get("slot")
                    if slot is not None and 0 <= slot < 30:
                        iid = int(entry.get("item_id", 0))
                        qty = int(entry.get("quantity", 0))
                        CURRENT_EDITOR.set_inventory_slot(slot, iid, qty)

                # 5d. Apply Compendium Registrations
                if data.get("unlock_compendium"):
                    CURRENT_EDITOR.unlock_compendium_100()
                elif "compendium" in data and isinstance(data["compendium"], dict):
                    comp_in = data["compendium"]
                    if "registered" in comp_in and isinstance(comp_in["registered"], list):
                        target_set = set(comp_in["registered"])
                        for pid in range(1, 233):
                            CURRENT_EDITOR.set_compendium_registration(pid, pid in target_set)

                # 6. Repack & Sign
                out_bytes = CURRENT_EDITOR.save_to_bytes()
                p.write_bytes(out_bytes)

                # Reload for fresh integrity validation
                CURRENT_EDITOR = SaveEditor(p.read_bytes())
                integrity = CURRENT_EDITOR.integrity_report()

                self.send_json(200, {
                    "status": "success",
                    "backup": backup_path.name,
                    "integrity": integrity,
                    "message": "Save file successfully re-signed and saved!"
                })
            except Exception as e:
                self.send_json(500, {"error": f"Failed to save file: {str(e)}"})

        elif parsed.path == "/api/restore":
            backup_name = data.get("backup_name", "")
            if not CURRENT_FILE_PATH or not backup_name:
                self.send_json(400, {"error": "Missing backup file or save path."})
                return
            try:
                p = Path(CURRENT_FILE_PATH)
                backup_zip = p.parent / "backups" / backup_name
                safety = restore_backup(p, backup_zip)
                CURRENT_EDITOR = SaveEditor(p.read_bytes())
                self.send_json(200, {"status": "success", "safety_backup": safety.name})
            except Exception as e:
                self.send_json(500, {"error": f"Restore failed: {str(e)}"})

        elif parsed.path == "/api/emergency-rescue":
            action = data.get("action")
            if not CURRENT_EDITOR:
                self.send_json(400, {"error": "No save loaded."})
                return
            if action == "third_semester":
                res = CURRENT_EDITOR.unlock_third_semester()
                self.send_json(200, res)
            else:
                self.send_json(400, {"error": "Unknown emergency action."})

    def send_json(self, code, payload):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

def start_server():
    server = HTTPServer(("127.0.0.1", PORT), P5RWebHandler)
    print(f"[P5R] Persona 5 Royal Web App running at http://127.0.0.1:{PORT}")
    print("[P5R] Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[P5R] Server stopped.")

if __name__ == "__main__":
    start_server()
