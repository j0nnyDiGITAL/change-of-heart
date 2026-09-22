"""
Persona 5 Royal Web Save Editor — High-Performance Local Web Backend
Serves a sleek, highly responsive Persona 5 Phantom Thief web application
with auto-save discovery, search-by-name dropdowns, human-friendly selectors,
and zero raw ID requirements.
"""

import os
import re
import sys
import json
import time
import base64
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Project paths (frozen PyInstaller vs source script)
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    PROJECT_ROOT = Path(sys._MEIPASS)
    WEB_APP_DIR = PROJECT_ROOT / "web-app"
else:
    # Depth-aware: this file ships BOTH at project root (main.py imports
    # "server") and under web-app/ (dev sibling). The root copy sits one
    # level higher, so __file__-relative math differs per location.
    _HERE = Path(__file__).resolve().parent
    if (_HERE / "web-app").is_dir() and (_HERE / "core").is_dir():
        PROJECT_ROOT = _HERE          # root copy
        WEB_APP_DIR = _HERE / "web-app"
    else:
        PROJECT_ROOT = _HERE.parent   # web-app copy
        WEB_APP_DIR = _HERE

sys.path.insert(0, str(PROJECT_ROOT))

from core.editor import SaveEditor, CONFIDANT_ARCANA_MAP, ROMANCEABLE_CONFIDANTS
from core.calendar_data import build_calendar_plan
from core import instances  # noqa: E402
from core.environment import (
    discover_steam_save_dirs,
    list_save_files,
    check_running_processes,
    create_timestamped_backup,
    list_backups,
    restore_backup,
)

PORT = 3000

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
    
    # Personas — filter out cut-content / legacy entries. The raw table
    # (464 ids) contains: id 0, "RESERVE"/"???"/blank names, "P5 Unused"
    # (0x167), and the compendium dead bits (P5-legacy duplicate entries the
    # game never uses in any context). Serving these lets users equip
    # persona ids with no Royal record/model -> Velvet Room / battle crash.
    # IDs >232 (Raoul 0x16B, William 0xF2, DLC space) are VALID for stock
    # editing (verified in oracle saves) — keep them.
    BAD_PERSONA_NAMES = {"", "RESERVE", "???", "BLANK", "----------", "P5 Unused"}
    ptable = ed._load_table("Personas.txt") or {}
    for pid, name in sorted(ptable.items()):
        if pid == 0 or name in BAD_PERSONA_NAMES or pid in SaveEditor.PC31_STOCK_LEGACY_IDS:
            continue
        if name.startswith("Lab "):  # dev/test-only personas, not in NAME.TBL
            continue
        db["personas"].append({"id": pid, "name": name})

    # Skills — strip dummy/placeholder slots: 0x0000-0x0009 (BLANK) plus
    # named placeholders and cut-content markers. They pass table validation
    # but produce corrupt persona cards / broken skill menus in battle.
    BAD_SKILL_NAMES = {"", "BLANK", "RESERVE", "----------", "not used"}
    # Names the game's own NAME.TBL does NOT contain (verified 2026-08-16
    # against the extracted EN name table). These are item names, test
    # skills, and dev strings that leaked into the Ruimusume dump.
    NON_SKILL_PREFIXES = (
        "adam skill", "ally", "roulette:", "shoes", "juice bar", "juicer bar",
        "energy drink", "soda", "ration", "drug store", "special coffee",
        "new curry", "sup hp", "sup sp", "support plus", "all-out lv",
        "dark akechi", "charisma speak",
    )
    # Skill ids whose dump name is not the game's name (corrected to the
    # NAME.TBL spelling) — dropdown display only; ids are unchanged.
    SKILL_NAME_FIXES = {
        123: "Med Burn", 126: "Med Freeze", 129: "Med Shock", 134: "Med Dizzy",
        137: "Med Confuse", 142: "Med Fear", 145: "Med Forget", 148: "Med Brainwash",
        153: "Med Sleep", 156: "Med Rage", 159: "Med Despair", 164: "Med All Ail",
        516: "Royal Jelly", 295: "Ultimate Support",
    }
    # Exact ids that are dev/test strings with no real skill definition.
    NON_SKILL_IDS = {658, 659, 660, 677, 734, 735, 751, 753, 663}
    stable = ed._load_table("Skill ID.txt") or {}
    for sid, name in sorted(stable.items()):
        nl = name.lower()
        if sid <= 0x09 or name in BAD_SKILL_NAMES or name.lower().startswith("unused:"):
            continue
        if sid in NON_SKILL_IDS or any(nl.startswith(p) for p in NON_SKILL_PREFIXES):
            continue
        db["skills"].append({"id": sid, "name": SKILL_NAME_FIXES.get(sid, name)})

    # Traits — same treatment as skills: 200 of 300 rows are RESERVE/blank
    # placeholders (verified 2026-08-16). Serve only the 100 named traits;
    # id 0 is offered as an explicit "None (unset)" option. Names corrected
    # to the game's NAME.TBL spelling (Savior/Skillful/Deathly Illness).
    BAD_TRAIT_NAMES = {"", "RESERVE", "???", "BLANK", "----------"}
    TRAIT_NAME_FIXES = {9: "Savior Bloodline", 73: "Skillful Combo", 102: "Deathly Illness"}
    ttable = ed._load_table("Traits.txt") or {}
    for tid, name in sorted(ttable.items()):
        if tid == 0:
            db["traits"].append({"id": 0, "name": "None (unset)"})
        elif name not in BAD_TRAIT_NAMES:
            db["traits"].append({"id": tid, "name": TRAIT_NAME_FIXES.get(tid, name)})

    # Skill metadata (element/cost/area) from the game's SKILL.TBL via
    # data/SkillMeta.txt (generated 2026-08-16 from decoded game fixture;
    # verified: Agi=4SP, Hassou Tobi=25%HP, Myriad Truths=40SP).
    skill_meta = {}
    meta_path = os.path.join(PROJECT_ROOT, "data", "SkillMeta.txt")
    try:
        with open(meta_path, encoding="utf-8") as mf:
            for ln in mf.read().splitlines()[1:]:
                pcol = ln.split("	")
                if len(pcol) >= 6 and pcol[0].strip().isdigit():
                    skill_meta[int(pcol[0])] = {
                        "element": int(pcol[1]),
                        "costtype": int(pcol[2]),
                        "cost": float(pcol[3]),
                        "area": int(pcol[4]),
                        "passive": int(pcol[5]),
                    }
    except OSError:
        pass
    db["skill_meta"] = skill_meta

    # Dedupe by NAME across all three lists (verified 2026-08-16): the
    # Ruimusume dumps carry one row per persona-slot, so one trait/skill/
    # persona can appear under several ids (e.g. "Ultimate Vessel" x9 =
    # ids 0x119-0x121, a single trait per the P5R Compendium; the corpus
    # of 12 real saves uses the LOWEST ids in each group — 0x119, and the
    # compendium-space persona ids). Keep the lowest id per name: it is the
    # canonical entry and the one real saves write.
    def _dedupe_by_name(items):
        seen = set()
        out = []
        for it in items:
            key = it["name"].lower()
            if key not in seen:
                seen.add(key)
                out.append(it)
        return out

    db["personas"] = _dedupe_by_name(db["personas"])
    # Full id->name map for the compendium grid (2026-08-16): party personas
    # whose names duplicate earlier ids (Satanael 0xD3, Carmen 0xDF, the
    # 0xE1-0xE8 block) are dropped by the dropdown dedupe but must still
    # render with their real names in the grid.
    db["persona_names"] = {
        pid: name for pid, name in sorted(ptable.items())
        if pid != 0 and name not in BAD_PERSONA_NAMES
    }
    db["skills"] = _dedupe_by_name(db["skills"])
    db["traits"] = _dedupe_by_name(db["traits"])
        
    # Items & Categories (100% Authentic In-Game 1-9 P5R Category Sequence)
    db["items"] = []
    data_dir = PROJECT_ROOT / "data"
    
    # Strict In-Game Category Order:
    # 1. Consumables (0x2000)
    # 2. Infiltration Tools & Materials (0x6000)
    # 3. Skill Cards (0x4000)
    # 4. Melee Weapons (0x1000)
    # 5. Ranged Weapons (0x7000)
    # 6. Protectors & Outfits (0x5000)
    # 7. Accessories (0x3000)
    # 8. Materials & Treasures (0x8000)
    # 9. Key Items & Story Essentials (0x9000)
    CATEGORY_MAPPING = [
        (0x2000, "Items.txt", "Consumable"),
        (0x6000, "Tools&materials.txt", "Infiltration"),
        (0x4000, "Skill Cards.txt", "SkillCard"),
        (0x1000, "Weapon melee.txt", "Melee"),
        (0x7000, "Weapon ranged.txt", "Ranged"),
        (0x5000, "Protectors.txt", "Protector"),
        (0x3000, "Accessories.txt", "Accessory"),
        (0x8000, "Treasure.txt", "Treasure"),
        (0x9000, "Keyitems&essentials.txt", "KeyItem"),
        (0xA000, "Outfits.txt", "Outfit"),
    ]

    seen_ids = set()
    # Item name fixes verified against the game's NAME.TBL (2026-08-16).
    ITEM_NAME_FIXES = {
        8270: "Money Distributor", 8271: "Item Distributor",
        8304: "Discharge Crystal", 8398: "Hifumi's Chocolate",
        8529: "Old Man's Elixir", 12400: "Vajra Belt",
        12417: "Blazing Horns", 12418: "Inferno Horns",
        12642: "Judgment Cross", 12736: "Spiral Rasetsu Anklet",
        12782: "Dazzling Netsuke", 8420: "Sakura Amezaiku",
        8375: "Oh! Shiruko",
    }
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

                    if (
                        en_name
                        and en_name not in ["EN_NAME", "BLANK", "RESERVE", "----------", "使用禁止", "Unused", "unused", "Unused Item"]
                        and "RESERVE" not in en_name
                        and "BLANK" not in en_name
                        and not en_name.lower().startswith("unused")
                    ):
                        iid = prefix | (idx & 0x0FFF)
                        if iid not in seen_ids:
                            seen_ids.add(iid)
                            # raw hex placeholder rows (e.g. "0x1E2") never
                            # resolve to a real item -- exclude them.
                            if re.match(r"^0x[0-9A-Fa-f]+$", en_name):
                                continue
                            
                            display_name = ITEM_NAME_FIXES.get(iid, en_name)
                            # For Protectors (0x5000), Melee (0x1000), Ranged (0x7000), Outfits (0xA000), append character owner if present
                            if prefix in (0x1000, 0x5000, 0x7000, 0xA000) and len(parts) >= 5 and parts[4].strip() and parts[4].strip() != "-":
                                role = parts[4].strip()
                                char_map = {
                                    "主人公": "Joker", "坂本龙司": "Ryuji", "摩尔加纳": "Morgana",
                                    "高卷杏": "Ann", "喜多川佑介": "Yusuke", "新岛真": "Makoto",
                                    "奥村春": "Haru", "佐仓双叶": "Futaba", "明智吾郎": "Akechi",
                                    "芳泽霞": "Kasumi", "ALL": "All"
                                }
                                eng_role = char_map.get(role, role)
                                if eng_role:
                                    display_name = f"{display_name} ({eng_role})"

                            db["items"].append({
                                "id": iid,
                                "name": display_name,
                                "category": cat
                            })
        except Exception as e:
            print(f"[P5R] Error loading {fname}: {e}")

    return db

REFERENCE_DB = build_reference_db()
# Pre-serialized + gzipped once at boot: /api/database serves the same bytes
# every time, so paying json.dumps + gzip per request is pure waste on slow
# CPUs (Gruphius slow-machine report, 2026-08-25).
import gzip as _gzip
_REFERENCE_DB_JSON = json.dumps(REFERENCE_DB).encode("utf-8")
_REFERENCE_DB_GZ = _gzip.compress(_REFERENCE_DB_JSON, mtime=0)
BUILD_ID = "audit-2026-08-16"
CURRENT_EDITOR = None
CURRENT_FILE_PATH = None

def _build_loaded_save_payload(editor: SaveEditor, file_path: str) -> dict:
    hdr = editor.parser.header
    names = editor.parser.player_names
    quick_info = editor.get_quick_info()
    integrity = editor.integrity_report()
    confidants = editor.get_confidant_ranks()
    social = editor.get_social_stats()
    party = editor.get_party_stats()

    # Only show members who have actually joined the story.
    party = [p for p in party if p.get("joined", False)]

    # Get equipped persona info for each party member
    party_personas = []
    for entry in party:
        slot = entry["slot"]
        p_info = editor.get_equipped_persona(slot)
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
    if playtime_sec > 500000:
        playtime_sec = quick_info.get("playtime", 0)

    joker_stock = editor.get_persona_stock(0)
    inventory = editor.get_inventory()
    try:
        inventory_norm = editor.get_normalized_inventory()
    except Exception:
        inventory_norm = {}
    compendium = editor.get_compendium()

    resp = {
        "file_path": file_path,
        "header": {
            "fname": hdr.fname,
            "lname": hdr.lname,
            "group_name": names.group_name_utf8,
            "money": editor.get_money(),
            "day": quick_info.get("day", str(hdr.day)),
            "level": quick_info.get("level", "22"),
            "playtime": f"{playtime_sec // 3600}h {(playtime_sec % 3600) // 60}m"
        },
        "social_stats": social,
        "confidants": confidants,
        "party": party_personas,
        "joker_stock": joker_stock,
        "inventory": inventory,
        "inventory_normalized": inventory_norm,
        "compendium": compendium,
        "integrity": integrity
    }
    _conflicts = instances.find_conflicts(file_path)
    if _conflicts:
        resp["notice"] = (
            "This save is also open in another window — last save wins."
        )
    return resp

# UI liveness tracking (watchdog for broken-WebView2 silent failures).
# The frontend pings /api/ui-heartbeat after the UI boots and every 15s after
# any successful API call. If the native window's JS never checks in, main.py
# auto-falls-back to the system browser instead of leaving a dead window.
LAST_UI_HEARTBEAT = 0.0  # unix ts of last heartbeat; 0 = never seen
LAST_REQUEST_TS = 0.0    # unix ts of last HTTP request (idle-shutdown tracking)

class P5RWebHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_APP_DIR / "static"), **kwargs)

    def log_message(self, format, *args):  # noqa: A002
        pass

    def handle_error(self, request, client_address):
        """Capture handler exceptions to a file (frozen exe has no console)."""
        import traceback
        try:
            err_path = os.path.join(
                os.environ.get("TEMP", "."), "P5R_handler_errors.log"
            )
            with open(err_path, "a", encoding="utf-8") as fh:
                fh.write(
                    f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                    f"from {client_address}: {self.command} {self.path}\n"
                )
                traceback.print_exc(file=fh)
        except Exception:
            pass

    def _origin_allowed(self):
        """CSRF guard: any browser-sent Origin must be a loopback origin.

        Browsers attach an Origin header to cross-site requests; a malicious
        page must not be able to drive this local API. Requests with no
        Origin (curl, webview navigation, same-origin GET) are allowed.
        """
        origin = self.headers.get("Origin")
        if not origin:
            return True
        try:
            from urllib.parse import urlsplit
            host = (urlsplit(origin).hostname or "").lower()
        except Exception:
            return False
        return host in ("127.0.0.1", "localhost", "::1")

    def do_GET(self):
        global CURRENT_EDITOR, CURRENT_FILE_PATH, LAST_REQUEST_TS
        LAST_REQUEST_TS = time.time()
        if not self._origin_allowed():
            self.send_json(403, {"error": "Cross-origin requests are not allowed."})
            return
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
            game_dir = PROJECT_ROOT / "p5r-game-client"
            game_file = (game_dir / rel_file).resolve()
            try:
                game_file.relative_to(game_dir.resolve())
            except ValueError:
                self.send_json(400, {"error": "Invalid game asset path."})
                return
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
        elif parsed.path == "/api/ui-heartbeat":
            global LAST_UI_HEARTBEAT
            LAST_UI_HEARTBEAT = time.time()
            self.send_json(200, {"status": "alive"})
            return
        elif parsed.path == "/api/heartbeat-status":
            age = (time.time() - LAST_UI_HEARTBEAT) if LAST_UI_HEARTBEAT else None
            self.send_json(200, {
                "ever_seen": LAST_UI_HEARTBEAT > 0,
                "last_heartbeat_age_s": round(age, 1) if age is not None else None,
            })
            return
        elif parsed.path == "/api/build":
            self.send_json(200, {"build": BUILD_ID})
            return
        elif parsed.path == "/api/state":
            self.send_json(200, {
                "pid": os.getpid(),
                "save": CURRENT_FILE_PATH or "",
            })
            return
        elif parsed.path == "/api/database":
            accepts_gzip = "gzip" in (self.headers.get("Accept-Encoding") or "")
            body = _REFERENCE_DB_GZ if accepts_gzip else _REFERENCE_DB_JSON
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            if accepts_gzip:
                self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        elif parsed.path == "/api/discovery":
            dirs = discover_steam_save_dirs()
            saves = []
            for d in dirs:
                for s in list_save_files(d):
                    s_str = str(s)
                    if s_str not in saves:
                        saves.append(s_str)
            self.send_json(200, {"discovered_dirs": [str(d) for d in dirs], "saves": saves})
            return
        elif parsed.path == "/api/backups":
            if not CURRENT_FILE_PATH or not os.path.exists(CURRENT_FILE_PATH):
                self.send_json(200, {"backups": []})
                return
            backups = [p.name for p in list_backups(Path(CURRENT_FILE_PATH))]
            self.send_json(200, {"backups": backups})
            return
        elif parsed.path == "/api/calendar":
            # READ-ONLY Time Travel Planner (ADR 0003 Tier 0).
            # Pure data projection of the fixed P5R schedule; performs no
            # save mutation and never touches the event-flag matrix.
            today_label = None
            ranks = None
            if CURRENT_EDITOR is not None:
                try:
                    if CURRENT_EDITOR.is_real_save():
                        qi = CURRENT_EDITOR.get_quick_info() or {}
                        today_label = qi.get("day")
                        ranks = CURRENT_EDITOR.get_confidant_ranks()
                except Exception:
                    today_label = None  # degrade to year view, never 500
            self.send_json(200, build_calendar_plan(today_label, ranks))
            return
        elif parsed.path == "/api/deadline-status":
            # Read-only escape-hatch status (ADR 0003 Tier 2).
            status = {"gates": [], "today": None, "date_known": False,
                      "available_backups": [], "is_uploaded": False,
                      "save_loaded": CURRENT_EDITOR is not None}
            if CURRENT_EDITOR is not None:
                try:
                    status.update(CURRENT_EDITOR.deadline_gate_status())
                except Exception:
                    pass
            is_uploaded = bool(CURRENT_FILE_PATH and CURRENT_FILE_PATH.startswith("Uploaded ("))
            status["is_uploaded"] = is_uploaded
            if CURRENT_FILE_PATH and not is_uploaded and os.path.exists(CURRENT_FILE_PATH):
                try:
                    status["available_backups"] = [p.name for p in list_backups(Path(CURRENT_FILE_PATH))]
                except Exception:
                    status["available_backups"] = []
            self.send_json(200, status)
            return

        super().do_GET()

    def do_POST(self):
        global CURRENT_EDITOR, CURRENT_FILE_PATH, LAST_REQUEST_TS
        LAST_REQUEST_TS = time.time()
        if not self._origin_allowed():
            self.send_json(403, {"error": "Cross-origin requests are not allowed."})
            return
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
            if not path_str:
                self.send_json(400, {"error": "Save file path is required."})
                return
            p = Path(path_str).resolve()
            if not p.is_file():
                self.send_json(400, {"error": "Save file not found."})
                return
            try:
                with open(p, "rb") as f:
                    raw = f.read()
                CURRENT_EDITOR = SaveEditor(raw)
                CURRENT_FILE_PATH = str(p)
                instances.update_save(CURRENT_FILE_PATH)
                resp = _build_loaded_save_payload(CURRENT_EDITOR, CURRENT_FILE_PATH)
                self.send_json(200, resp)
            except Exception as e:
                self.send_json(500, {"error": f"Failed to load save: {str(e)}"})

        elif parsed.path == "/api/load-upload":
            raw_b64 = data.get("data", "")
            filename = data.get("filename", "DATA.DAT")
            if not raw_b64:
                self.send_json(400, {"error": "No file content uploaded."})
                return
            try:
                raw_bytes = base64.b64decode(raw_b64)
                CURRENT_EDITOR = SaveEditor(raw_bytes)
                CURRENT_FILE_PATH = f"Uploaded ({filename})"
                instances.update_save(CURRENT_FILE_PATH)
                resp = _build_loaded_save_payload(CURRENT_EDITOR, CURRENT_FILE_PATH)
                self.send_json(200, resp)
            except Exception as e:
                self.send_json(500, {"error": f"Failed to load uploaded save: {str(e)}"})

        elif parsed.path == "/api/save":
            if not CURRENT_EDITOR or not CURRENT_FILE_PATH:
                self.send_json(400, {"error": "No save file loaded."})
                return

            p5r_run, _ = check_running_processes()
            if p5r_run:
                self.send_json(409, {"error": "P5R.exe is currently running! Please close the game before saving."})
                return

            try:
                is_uploaded = CURRENT_FILE_PATH.startswith("Uploaded (")
                p = None
                backup_path_name = "N/A (Uploaded save)"
                if not is_uploaded:
                    # 1. Automatic Timestamped Backup
                    p = Path(CURRENT_FILE_PATH)
                    backup_path = create_timestamped_backup(p)
                    backup_path_name = backup_path.name

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
                        romance = bool(cdata.get("romance", False)) if isinstance(cdata, dict) and "romance" in cdata else None
                        CURRENT_EDITOR.set_confidant_rank(arc_id, rank, romance=romance, auto_unlock=True)

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
                            # Safely extract skills
                            raw_skills = pers.get("skills", [0]*8)
                            parsed_skills = []
                            for s in raw_skills:
                                if isinstance(s, dict):
                                    parsed_skills.append(int(s.get("id", 0)))
                                else:
                                    parsed_skills.append(int(s) if s is not None else 0)

                            # Safely extract stats
                            raw_stats = pers.get("stats", [10]*5)
                            parsed_stats = []
                            if isinstance(raw_stats, dict):
                                parsed_stats = [
                                    int(raw_stats.get("st", 10)),
                                    int(raw_stats.get("ma", 10)),
                                    int(raw_stats.get("en", 10)),
                                    int(raw_stats.get("ag", 10)),
                                    int(raw_stats.get("lu", 10))
                                ]
                            elif isinstance(raw_stats, list):
                                parsed_stats = [int(st) if st is not None else 10 for st in raw_stats]
                            else:
                                parsed_stats = [10]*5

                            CURRENT_EDITOR.set_equipped_persona(
                                slot,
                                persona_id=int(pers.get("persona_id", 0)),
                                level=int(pers.get("level", 1)),
                                trait_id=int(pers.get("trait_id", 0)),
                                exp=int(pers.get("exp", 0)),
                                skills=parsed_skills,
                                stats=parsed_stats,
                                flags=int(pers.get("flags", 1))
                            )

                # 5b. Apply Joker's 12-slot Persona Stock
                stock_in = data.get("joker_stock", [])
                for s_entry in stock_in:
                    s_slot = s_entry.get("slot")
                    if s_slot is not None and 0 <= s_slot < 12:
                        pid = int(s_entry.get("persona_id", 0))

                        # Safely extract skills
                        raw_skills = s_entry.get("skills", [0]*8)
                        parsed_skills = []
                        for s in raw_skills:
                            if isinstance(s, dict):
                                parsed_skills.append(int(s.get("id", 0)))
                            else:
                                parsed_skills.append(int(s) if s is not None else 0)

                        # Safely extract stats
                        raw_stats = s_entry.get("stats", [10]*5)
                        parsed_stats = []
                        if isinstance(raw_stats, dict):
                            parsed_stats = [
                                int(raw_stats.get("st", 10)),
                                int(raw_stats.get("ma", 10)),
                                int(raw_stats.get("en", 10)),
                                int(raw_stats.get("ag", 10)),
                                int(raw_stats.get("lu", 10))
                            ]
                        elif isinstance(raw_stats, list):
                            parsed_stats = [int(st) if st is not None else 10 for st in raw_stats]
                        else:
                            parsed_stats = [10]*5

                        CURRENT_EDITOR.set_persona_stock_slot(
                            member_slot=0,
                            stock_k=s_slot,
                            persona_id=pid,
                            level=int(s_entry.get("level", 1)),
                            trait_id=int(s_entry.get("trait_id", 0)),
                            exp=int(s_entry.get("exp", 0)),
                            skills=parsed_skills,
                            stats=parsed_stats,
                            flags=int(s_entry.get("flags", 1))
                        )

                # 5c. Apply Active Inventory Items — prefers normalized payload
                norm_in = data.get("inventory_normalized")
                if isinstance(norm_in, dict) and (norm_in.get("stacks") or norm_in.get("owned_gear")):
                    # New path: stacks + owned_gear from S1 normalized model
                    for raw_id, qty in (norm_in.get("stacks") or {}).items():
                        try:
                            iid = int(raw_id) if isinstance(raw_id, str) else int(raw_id)
                        except Exception:
                            continue
                        CURRENT_EDITOR.set_item_quantity(iid, int(qty))
                    for raw_id, owned in (norm_in.get("owned_gear") or {}).items():
                        try:
                            iid = int(raw_id) if isinstance(raw_id, str) else int(raw_id)
                        except Exception:
                            continue
                        CURRENT_EDITOR.set_item_quantity(iid, 1 if owned else 0)
                else:
                    # Legacy path: flat inventory list
                    inv_in = data.get("inventory", [])
                    for entry in inv_in:
                        iid = int(entry.get("item_id", 0))
                        qty = int(entry.get("quantity", 0))
                        slot = entry.get("slot")
                        if iid > 0:
                            if slot is not None and 0 <= slot < 30:
                                CURRENT_EDITOR.set_inventory_slot(slot, iid, qty)
                            else:
                                CURRENT_EDITOR.set_item_quantity(iid, qty)

                # 5d. Apply Compendium Registrations
                if data.get("unlock_compendium"):
                    CURRENT_EDITOR.unlock_compendium_100()
                elif "compendium" in data and isinstance(data["compendium"], dict):
                    comp = data["compendium"]
                    if comp and comp.get("supported"):
                        registered_list = set(comp.get("registered", []))
                        for pid in range(1, CURRENT_EDITOR.PC31_COMPENDIUM_MAX_ID + 1):
                            is_reg = pid in registered_list
                            CURRENT_EDITOR.set_compendium_registration(pid, is_reg)
                        # Sanitize any rogue bytes in the gap
                        d_tmp = bytearray(CURRENT_EDITOR.parser.data_payload)
                        for gap_start, gap_end in ((0x09460, 0x09940), (0x21970, 0x21E50)):
                            if gap_end <= len(d_tmp):
                                d_tmp[gap_start:gap_end] = b"\x00" * (gap_end - gap_start)
                        CURRENT_EDITOR.parser.data_payload = bytes(d_tmp)

                # 6. Repack & Sign
                out_bytes = CURRENT_EDITOR.save_to_bytes()
                if p:
                    p.write_bytes(out_bytes)
                    CURRENT_EDITOR = SaveEditor(p.read_bytes())
                else:
                    CURRENT_EDITOR = SaveEditor(out_bytes)
                integrity = CURRENT_EDITOR.integrity_report()

                resp = {
                    "status": "success",
                    "backup": backup_path_name,
                    "integrity": integrity,
                    "download_data": base64.b64encode(out_bytes).decode("ascii") if is_uploaded else None,
                    "message": "Save file successfully re-signed and saved!"
                }
                _conflicts = instances.find_conflicts(CURRENT_FILE_PATH)
                if _conflicts:
                    resp["notice"] = (
                        "This save is also open in another window — last save wins."
                    )
                self.send_json(200, resp)
            except Exception as e:
                self.send_json(500, {"error": f"Failed to save file: {str(e)}"})

        elif parsed.path == "/api/restore":
            backup_name = data.get("backup_name", "")
            if not CURRENT_FILE_PATH or not backup_name:
                self.send_json(400, {"error": "Missing backup file or save path."})
                return
            if not re.fullmatch(r"[A-Za-z0-9_.\-]+", backup_name):
                self.send_json(400, {"error": "Invalid backup name."})
                return
            try:
                p = Path(CURRENT_FILE_PATH)
                backup_zip = p.parent / "backups" / backup_name
                safety = restore_backup(p, backup_zip)
                CURRENT_EDITOR = SaveEditor(p.read_bytes())
                self.send_json(200, {"status": "success", "safety_backup": safety.name})
            except Exception as e:
                self.send_json(500, {"error": f"Restore failed: {str(e)}"})

        elif parsed.path == "/api/deadline-escape":
            # ADR 0003 Tier 2: deadline escape hatch.
            # confirm=false → dry-run plan (read-only). confirm=true →
            # optional vault restore + D016-compliant rank write + re-sign,
            # always preceded by a timestamped backup (vault restore already
            # makes its own reversible safety backup of the current state).
            if not CURRENT_EDITOR or not CURRENT_FILE_PATH:
                self.send_json(400, {"error": "No save file loaded."})
                return
            gate_key = (data.get("gate_key") or "").strip()
            confirm = data.get("confirm") is True
            backup_name = (data.get("backup_name") or "").strip()
            is_uploaded = CURRENT_FILE_PATH.startswith("Uploaded (")
            try:
                if not confirm:
                    plan = CURRENT_EDITOR.plan_deadline_escape(gate_key)
                    backups = []
                    if not is_uploaded and Path(CURRENT_FILE_PATH).exists():
                        backups = [p.name for p in list_backups(Path(CURRENT_FILE_PATH))]
                    plan["available_backups"] = backups
                    plan["is_uploaded"] = is_uploaded
                    self.send_json(200, plan)
                    return

                p5r_run, _ = check_running_processes()
                if p5r_run:
                    self.send_json(409, {"error": "P5R.exe is currently running! Close the game before using the escape hatch."})
                    return
                if backup_name:
                    if is_uploaded:
                        self.send_json(400, {"error": "Uploaded saves have no backup vault — reload the real save file first."})
                        return
                    if not re.fullmatch(r"[A-Za-z0-9_.\-]+", backup_name):
                        self.send_json(400, {"error": "Invalid backup name."})
                        return
                    backup_zip = str(Path(CURRENT_FILE_PATH).parent / "backups" / backup_name)
                else:
                    backup_zip = None

                res = CURRENT_EDITOR.apply_deadline_escape(
                    gate_key, backup_zip=backup_zip,
                    save_file=None if is_uploaded else CURRENT_FILE_PATH,
                    confirm=True)
                if res.get("status") != "success":
                    self.send_json(res.get("http", 400), {"error": res.get("message", "Escape hatch refused."),
                                                          "status": res.get("status")})
                    return

                resp = {"status": "success",
                        "gate_key": res.get("gate_key"),
                        "confidant": res.get("confidant"),
                        "rank_written": res.get("rank_written"),
                        "restored_from": res.get("restored_from")}
                if is_uploaded:
                    out_bytes = res.get("bytes")
                    CURRENT_EDITOR = SaveEditor(out_bytes)
                    CURRENT_FILE_PATH = f"Uploaded (escaped)"
                    resp["download_data"] = base64.b64encode(out_bytes).decode("ascii")
                    resp["integrity"] = CURRENT_EDITOR.integrity_report()
                else:
                    p = Path(CURRENT_FILE_PATH)
                    # Guarantee: backup before every disk write.
                    bkp = create_timestamped_backup(p)
                    p.write_bytes(res["bytes"])
                    CURRENT_EDITOR = SaveEditor(p.read_bytes())
                    instances.update_save(CURRENT_FILE_PATH)
                    resp["backup"] = bkp.name
                    resp["integrity"] = CURRENT_EDITOR.integrity_report()
                resp["gate_status"] = CURRENT_EDITOR.deadline_gate_status()
                self.send_json(200, resp)
            except FileNotFoundError as e:
                self.send_json(400, {"error": str(e)})
            except ValueError as e:
                self.send_json(400, {"error": str(e)})
            except Exception as e:
                self.send_json(500, {"error": f"Escape hatch failed: {str(e)}"})

        elif parsed.path == "/api/palace-skip":
            # CHRONOS Palace Skip: set guard + discovery bits, warp to
            # deadline day. Engine replays post-clearance scenes on arrival.
            if not CURRENT_EDITOR or not CURRENT_FILE_PATH:
                self.send_json(400, {"error": "No save file loaded."})
                return
            try:
                from core.chronos import (
                    build_palace_skip_plan, apply_palace_skip,
                    PALACE_SKIP_CATALOG, load_model, MODEL_PATH,
                )
                if not os.path.exists(MODEL_PATH):
                    self.send_json(503, {"error": "chronos_model.json missing."})
                    return
                palace_id = (data.get("palace_id") or "").strip()
                mode = data.get("mode") or "deadline"
                confirm = data.get("confirm") is True

                if not palace_id:
                    # List available palaces
                    catalog = []
                    for p in PALACE_SKIP_CATALOG:
                        cat_entry = {
                            "palace_id": p["palace_id"],
                            "label": p["label"],
                            "deadline": "%d/%d" % p["deadline"],
                            "earliest_entry": "%d/%d" % p["earliest_entry"],
                            "party_unlock": p.get("party_unlock", ""),
                        }
                        # Check current state
                        try:
                            from core.chronos import (
                                day_index, _bit_location)
                            cur_day = CURRENT_EDITOR.parser.header.day
                            deadline_idx = day_index(*p["deadline"])
                            entry_idx = day_index(*p["earliest_entry"])
                            payload = CURRENT_EDITOR.parser.data_payload
                            g_byte, g_bit = _bit_location(
                                p["guard_bit"]["table"], p["guard_bit"]["index"])
                            cleared = bool(payload[g_byte] & (1 << g_bit))
                            cat_entry["status"] = (
                                "cleared" if cleared else
                                "too_late" if cur_day >= deadline_idx else
                                "too_early" if cur_day < entry_idx else
                                "available"
                            )
                        except Exception:
                            cat_entry["status"] = "unknown"
                        catalog.append(cat_entry)
                    self.send_json(200, {"catalog": catalog})
                    return

                if not confirm:
                    plan = build_palace_skip_plan(CURRENT_EDITOR, palace_id,
                                                  mode=mode)
                    self.send_json(200, plan)
                    return

                p5r_run, _ = check_running_processes()
                if p5r_run:
                    self.send_json(409, {"error": "P5R.exe is currently running! Close the game before skipping a palace."})
                    return

                res = apply_palace_skip(CURRENT_EDITOR, palace_id, mode=mode)
                if res.get("status") != "success":
                    self.send_json(400, {"status": res.get("status"),
                                         "plan": res.get("plan")})
                    return

                out_bytes = CURRENT_EDITOR.save_to_bytes()
                resp = {"status": "success", "plan": res["plan"],
                        "wrote": res["wrote"],
                        "bits_written": res.get("bits_written", [])}
                is_uploaded = CURRENT_FILE_PATH.startswith("Uploaded (")
                if is_uploaded:
                    CURRENT_EDITOR = SaveEditor(out_bytes)
                    CURRENT_FILE_PATH = "Uploaded (palace-skipped)"
                    resp["download_data"] = base64.b64encode(out_bytes).decode("ascii")
                    resp["integrity"] = CURRENT_EDITOR.integrity_report()
                else:
                    p = Path(CURRENT_FILE_PATH)
                    bkp = create_timestamped_backup(p)
                    p.write_bytes(out_bytes)
                    CURRENT_EDITOR = SaveEditor(p.read_bytes())
                    instances.update_save(CURRENT_FILE_PATH)
                    resp["backup"] = bkp.name
                    resp["integrity"] = CURRENT_EDITOR.integrity_report()
                self.send_json(200, resp)
            except ValueError as e:
                self.send_json(400, {"error": str(e)})
            except Exception as e:
                self.send_json(500, {"error": f"Palace skip failed: {str(e)}"})

        elif parsed.path == "/api/time-travel":
            # CHRONOS: calendar time travel (ADR 0003 Tier-1 upgrade).
            # confirm=false -> read-only plan (per-day classification from the
            # bundled calendar model). confirm=true -> hdr.day + 0x3D70
            # mirror write, re-sign, timestamped backup before every disk write.
            if not CURRENT_EDITOR or not CURRENT_FILE_PATH:
                self.send_json(400, {"error": "No save file loaded."})
                return
            try:
                from core.chronos import (apply_time_travel, build_time_travel_plan,
                                          build_time_travel_plan_v2,
                                          apply_time_travel_v2,
                                          load_model, MODEL_PATH)
                if not os.path.exists(MODEL_PATH):
                    self.send_json(503, {"error": "chronos_model.json missing."})
                    return
                model = load_model()
                t_month = int(data.get("target_month") or 0)
                t_day = int(data.get("target_day") or 0)
                confirm = data.get("confirm") is True
                if not confirm:
                    # V2 plan (ADR 0004): adds branch_choices for known story
                    # windows (status blocked_resolvable) instead of a bare
                    # refusal; ok/invalid unchanged.
                    plan = build_time_travel_plan_v2(
                        model, CURRENT_EDITOR.parser.header.day, t_month, t_day)
                    self.send_json(200, plan)
                    return
                p5r_run, _ = check_running_processes()
                if p5r_run:
                    self.send_json(409, {"error": "P5R.exe is currently running! Close the game before time travel."})
                    return
                is_uploaded = CURRENT_FILE_PATH.startswith("Uploaded (")
                choice_ids = data.get("choice_ids") or None
                if choice_ids:
                    res = apply_time_travel_v2(CURRENT_EDITOR, model, t_month,
                                               t_day, choice_ids=choice_ids)
                else:
                    res = apply_time_travel_v2(CURRENT_EDITOR, model, t_month, t_day)
                if res.get("status") == "confirm_required":
                    self.send_json(400, {"status": "confirm_required",
                                         "plan": res.get("plan"),
                                         "message": res.get("message")})
                    return
                if res.get("status") != "success":
                    self.send_json(400, {"status": res.get("status"), "plan": res.get("plan")})
                    return
                out_bytes = CURRENT_EDITOR.save_to_bytes()
                resp = {"status": "success", "plan": res["plan"], "wrote": res["wrote"]}
                if res.get("bits_written"):
                    resp["bits_written"] = res["bits_written"]
                if is_uploaded:
                    CURRENT_EDITOR = SaveEditor(out_bytes)
                    CURRENT_FILE_PATH = "Uploaded (time-traveled)"
                    resp["download_data"] = base64.b64encode(out_bytes).decode("ascii")
                    resp["integrity"] = CURRENT_EDITOR.integrity_report()
                else:
                    p = Path(CURRENT_FILE_PATH)
                    # Guarantee: backup before every disk write.
                    bkp = create_timestamped_backup(p)
                    p.write_bytes(out_bytes)
                    CURRENT_EDITOR = SaveEditor(p.read_bytes())
                    instances.update_save(CURRENT_FILE_PATH)
                    resp["backup"] = bkp.name
                    resp["integrity"] = CURRENT_EDITOR.integrity_report()
                self.send_json(200, resp)
            except ValueError as e:
                self.send_json(400, {"error": str(e)})
            except Exception as e:
                self.send_json(500, {"error": f"Time travel failed: {str(e)}"})

        elif parsed.path == "/api/full-time-warp":
            # CHRONOS V3: full time warp with complete flag sync.
            # Sets clock fields + palace guard/discovery bits + daily event flags.
            # confirm=false -> read-only plan; confirm=true -> apply + re-sign.
            if not CURRENT_EDITOR or not CURRENT_FILE_PATH:
                self.send_json(400, {"error": "No save file loaded."})
                return
            try:
                from core.chronos import (
                    apply_full_time_warp, load_model, MODEL_PATH,
                    day_index, index_to_month_day,
                )
                if not os.path.exists(MODEL_PATH):
                    self.send_json(503, {"error": "chronos_model.json missing."})
                    return
                model = load_model()
                t_month = int(data.get("target_month") or 0)
                t_day = int(data.get("target_day") or 0)
                direction = data.get("direction", "auto")
                confirm = data.get("confirm") is True

                if not confirm:
                    # Build read-only plan
                    from core.chronos import _palace_state_for_day, _event_flags_for_day
                    cur_day = CURRENT_EDITOR.parser.header.day
                    cur_m, cur_d = index_to_month_day(cur_day)
                    try:
                        tgt_idx = day_index(t_month, t_day)
                    except KeyError:
                        self.send_json(400, {"error": "Invalid target date."})
                        return
                    if direction == "auto":
                        d = "forward" if tgt_idx > cur_day else "backward"
                    else:
                        d = direction
                    palace_state = _palace_state_for_day(tgt_idx)
                    event_flags = _event_flags_for_day(model, tgt_idx)
                    from core.chronos import plan_full_time_warp_changes
                    changes = plan_full_time_warp_changes(CURRENT_EDITOR.parser, model, tgt_idx)
                    plan = {
                        "current": {"hdr_day": cur_day, "date": "%d/%d" % (cur_m, cur_d)},
                        "target": {"hdr_day": tgt_idx, "date": "%d/%d" % (t_month, t_day)},
                        "direction": d,
                        "palaces": {pid: {"guard": ps["guard"], "discovery": ps["discovery"]}
                                    for pid, ps in palace_state.items()},
                        "summary": {
                            "guards_set": [pid for pid, ps in palace_state.items() if ps["guard"]],
                            "guards_cleared": [pid for pid, ps in palace_state.items() if not ps["guard"]],
                            "discoveries_set": [pid for pid, ps in palace_state.items() if ps["discovery"]],
                            "discoveries_cleared": [pid for pid, ps in palace_state.items() if not ps["discovery"]],
                            "event_flags_on": len(event_flags["bits_on"]),
                            "event_flags_off": len(event_flags["bits_off"]),
                        },
                        "changes": changes,
                    }
                    self.send_json(200, plan)
                    return

                p5r_run, _ = check_running_processes()
                if p5r_run:
                    self.send_json(409, {"error": "P5R.exe is currently running! Close the game before time warp."})
                    return

                res = apply_full_time_warp(CURRENT_EDITOR, model, t_month, t_day,
                                           direction=direction)
                if res.get("status") != "success":
                    self.send_json(400, {"status": res.get("status"),
                                         "reason": res.get("reason")})
                    return

                out_bytes = CURRENT_EDITOR.save_to_bytes()
                resp = {"status": "success", "plan": res["plan"],
                        "wrote": res["wrote"]}
                if res.get("bits_written"):
                    resp["bits_written"] = res["bits_written"]
                is_uploaded = CURRENT_FILE_PATH.startswith("Uploaded (")
                if is_uploaded:
                    CURRENT_EDITOR = SaveEditor(out_bytes)
                    CURRENT_FILE_PATH = "Uploaded (full-time-warp)"
                    resp["download_data"] = base64.b64encode(out_bytes).decode("ascii")
                    resp["integrity"] = CURRENT_EDITOR.integrity_report()
                else:
                    p = Path(CURRENT_FILE_PATH)
                    bkp = create_timestamped_backup(p)
                    p.write_bytes(out_bytes)
                    CURRENT_EDITOR = SaveEditor(p.read_bytes())
                    instances.update_save(CURRENT_FILE_PATH)
                    resp["backup"] = bkp.name
                    resp["integrity"] = CURRENT_EDITOR.integrity_report()
                self.send_json(200, resp)
            except ValueError as e:
                self.send_json(400, {"error": str(e)})
            except Exception as e:
                self.send_json(500, {"error": f"Full time warp failed: {str(e)}"})

    def send_json(self, code, payload):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        # Reflect only loopback Origins (see _origin_allowed) — never "*".
        origin = self.headers.get("Origin")
        if origin and self._origin_allowed():
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
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

def main():
    start_server()


if __name__ == "__main__":
    main()
