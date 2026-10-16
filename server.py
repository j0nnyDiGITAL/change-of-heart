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
from datetime import datetime
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
from core import instances  # noqa: E402
from core.environment import (
    discover_steam_save_dirs,
    list_save_files,
    check_running_processes,
    create_timestamped_backup,
    create_memory_backup_zip,
    list_backups,
    restore_backup,
)
from core.session import SESSION_MANAGER, SaveSession
from core.atomic_writer import (
    atomic_write_save,
    atomic_restore_backup,
    ConcurrencyConflictError,
    SaveValidationError,
    compute_sha256,
)
from core.inspector import inspect_save, compare_saves

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
    # Item name fixes verified against the game's NAME.TBL (2026-08-16 + 2026-10-11).
    ITEM_NAME_FIXES = SaveEditor.ITEM_NAME_FIXES
    for prefix, fname, cat in CATEGORY_MAPPING:
        p = data_dir / fname
        if not p.exists():
            continue
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                for idx, line in enumerate(f):
                    parts = line.strip().split("\t")
                    en_name = None
                    jp_name = parts[2].strip() if len(parts) >= 3 else ""
                    if len(parts) >= 4:
                        en_name = parts[3].strip()
                    elif len(parts) == 1 and parts[0]:
                        en_name = parts[0].strip()

                    if (
                        en_name
                        and en_name not in ["EN_NAME", "BLANK", "RESERVE", "----------", "—", "-", "–", "???", "使用禁止", "Unused", "unused", "Unused Item"]
                        and jp_name not in ("リザーブ", "ブランク", "未使用", "使用禁止")
                        and "RESERVE" not in en_name
                        and "BLANK" not in en_name
                        and not en_name.lower().startswith("unused")
                        and not SaveEditor.is_placeholder_item(en_name)
                    ):
                        iid = prefix | (idx & 0x0FFF)
                        if iid not in seen_ids:
                            seen_ids.add(iid)
                            # raw hex placeholder rows (e.g. "0x1E2") never
                            # resolve to a real item -- exclude them.
                            if re.match(r"^0x[0-9A-Fa-f]+$", en_name):
                                continue
                            
                            display_name = ITEM_NAME_FIXES.get(iid, en_name)
                            # For Protectors (0x5000), Melee (0x1000), Ranged (0x7000), Outfits (0xA000), append character owner if present and not already suffixed
                            if prefix in (0x1000, 0x5000, 0x7000, 0xA000) and len(parts) >= 5 and parts[4].strip() and parts[4].strip() != "-":
                                role = parts[4].strip()
                                char_map = {
                                    "主人公": "Joker", "坂本龙司": "Ryuji", "摩尔加纳": "Morgana",
                                    "高卷杏": "Ann", "喜多川佑介": "Yusuke", "新岛真": "Makoto",
                                    "奥村春": "Haru", "佐仓双叶": "Futaba", "明智吾郎": "Akechi",
                                    "芳泽霞": "Kasumi", "ALL": "All"
                                }
                                eng_role = char_map.get(role, role)
                                if eng_role and not display_name.endswith(f"({eng_role})"):
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
BUILD_ID = "v2.0.0-final"
CURRENT_EDITOR = None
CURRENT_FILE_PATH = None
CURRENT_ORIGINAL_BYTES = None

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

    # Parse accurate playtime from authoritative quick_info seconds.
    # quick_info["playtime"] is None when the header description text has no
    # parseable "PLAY TIME:Xh Ym" line (e.g. localized saves); the
    # container-header u32 fallback is a garbage value (> 500000) in genuine
    # saves, so an undeterminable playtime degrades to "Unknown" instead of
    # reaching // arithmetic (GitHub issue #4: NoneType // int on Load Save).
    playtime_sec = quick_info.get("playtime")
    if not isinstance(playtime_sec, int) or playtime_sec < 0:
        header_pt = hdr.playtime
        playtime_sec = header_pt if isinstance(header_pt, int) and 0 < header_pt <= 500000 else None
    playtime_display = (
        f"{playtime_sec // 3600}h {(playtime_sec % 3600) // 60}m"
        if playtime_sec is not None else "Unknown"
    )

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
            "day": quick_info.get("day") or str(hdr.day),
            "level": quick_info.get("level") or "22",
            "playtime": playtime_display
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

    def _host_allowed(self):
        """Host header check to protect against DNS rebinding attacks."""
        host_hdr = self.headers.get("Host", "")
        if not host_hdr:
            return True
        host_name = host_hdr.split(":")[0].strip().lower()
        return host_name in ("127.0.0.1", "localhost", "::1", "[::1]")

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
        if not self._host_allowed():
            self.send_json(400, {"error": "Invalid Host header."})
            return
        if not self._origin_allowed():
            self.send_json(403, {"error": "Cross-origin requests are not allowed."})
            return
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self';"
            )
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
            session = SESSION_MANAGER.get_session()
            self.send_json(200, {
                "pid": os.getpid(),
                "save": (session.file_path if session else CURRENT_FILE_PATH) or "",
                "session_id": session.session_id if session else None,
                "token": session.capability_token if session else None,
                "revision": session.revision if session else None,
            })
            return
        elif parsed.path == "/api/inspect":
            session = SESSION_MANAGER.get_session()
            if session:
                report = inspect_save(session.editor, file_path=session.file_path)
                self.send_json(200, report)
            elif CURRENT_FILE_PATH and os.path.exists(CURRENT_FILE_PATH):
                report = inspect_save(Path(CURRENT_FILE_PATH))
                self.send_json(200, report)
            else:
                self.send_json(400, {"error": "No save file loaded to inspect."})
            return
        elif parsed.path == "/api/stage":
            session = SESSION_MANAGER.get_session()
            if session:
                self.send_json(200, {"staged_changes": session.get_staged_summary()})
            else:
                self.send_json(200, {"staged_changes": []})
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
            session = SESSION_MANAGER.get_session()
            active_path = (session.file_path if session else CURRENT_FILE_PATH)
            if not active_path or not os.path.exists(active_path):
                self.send_json(200, {"backups": []})
                return
            backups = [p.name for p in list_backups(Path(active_path))]
            self.send_json(200, {"backups": backups})
            return

        super().do_GET()

    def do_POST(self):
        global CURRENT_EDITOR, CURRENT_FILE_PATH, CURRENT_ORIGINAL_BYTES, LAST_REQUEST_TS
        LAST_REQUEST_TS = time.time()
        if not self._host_allowed():
            self.send_json(400, {"error": "Invalid Host header."})
            return
        if not self._origin_allowed():
            self.send_json(403, {"error": "Cross-origin requests are not allowed."})
            return

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 32 * 1024 * 1024:
            self.send_json(413, {"error": "Request body too large (maximum 32MB)."})
            return

        body = self.rfile.read(content_length)
        data = {}
        if body:
            try:
                data = json.loads(body.decode("utf-8"))
            except Exception:
                pass

        token = self.headers.get("X-Session-Token") or (data.get("token") if isinstance(data, dict) else None)
        parsed = urlparse(self.path)

        if parsed.path == "/api/load":
            path_str = data.get("path", "").strip()
            if not path_str:
                self.send_json(400, {"error": "Save file path is required."})
                return
            p = Path(path_str).resolve()
            if not p.is_file():
                self.send_json(400, {"error": "Save file not found."})
                return
            if p.stat().st_size > 5 * 1024 * 1024:
                self.send_json(400, {"error": "Save file exceeds 5MB limit."})
                return
            try:
                raw = p.read_bytes()
                session = SESSION_MANAGER.create_session(raw, file_path=str(p), is_uploaded=False)
                CURRENT_EDITOR = session.editor
                CURRENT_FILE_PATH = session.file_path
                CURRENT_ORIGINAL_BYTES = session.baseline_bytes
                instances.update_save(CURRENT_FILE_PATH)
                resp = _build_loaded_save_payload(session.editor, CURRENT_FILE_PATH)
                resp["session_id"] = session.session_id
                resp["token"] = session.capability_token
                resp["revision"] = session.revision
                resp["baseline_sha256"] = session.baseline_sha256
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
                if len(raw_bytes) > 5 * 1024 * 1024:
                    self.send_json(400, {"error": "Uploaded save exceeds 5MB limit."})
                    return
                session = SESSION_MANAGER.create_session(raw_bytes, file_path=f"Uploaded ({filename})", is_uploaded=True)
                CURRENT_EDITOR = session.editor
                CURRENT_FILE_PATH = session.file_path
                CURRENT_ORIGINAL_BYTES = session.baseline_bytes
                instances.update_save(CURRENT_FILE_PATH)
                resp = _build_loaded_save_payload(session.editor, CURRENT_FILE_PATH)
                resp["session_id"] = session.session_id
                resp["token"] = session.capability_token
                resp["revision"] = session.revision
                resp["baseline_sha256"] = session.baseline_sha256
                self.send_json(200, resp)
            except Exception as e:
                self.send_json(500, {"error": f"Failed to load uploaded save: {str(e)}"})

        elif parsed.path == "/api/save":
            session = SESSION_MANAGER.get_session_by_token(token) or SESSION_MANAGER.get_session()
            if not session:
                self.send_json(400, {"error": "No save file loaded."})
                return

            p5r_run, _ = check_running_processes()
            if p5r_run:
                self.send_json(409, {"error": "P5R.exe is currently running! Please close the game before saving."})
                return

            try:
                # Session handles transaction commit, including data.get("unlock_compendium") -> unlock_compendium_100()
                commit_res = session.commit_transaction(data, strict_verification=True)
                CURRENT_EDITOR = session.editor
                CURRENT_ORIGINAL_BYTES = session.baseline_bytes
                _conflicts = instances.find_conflicts(session.file_path)
                if _conflicts:
                    commit_res["notice"] = (
                        "This save is also open in another window."
                    )
                self.send_json(200, commit_res)
            except ConcurrencyConflictError as ce:
                self.send_json(409, {"error": str(ce), "conflict": True})
            except SaveValidationError as ve:
                self.send_json(400, {"error": f"Save validation failed: {str(ve)}"})
            except Exception as e:
                self.send_json(500, {"error": f"Failed to save file: {str(e)}"})

        elif parsed.path == "/api/restore":
            backup_name = data.get("backup_name", "")
            session = SESSION_MANAGER.get_session_by_token(token) or SESSION_MANAGER.get_session()
            if not session or not session.file_path or not backup_name:
                self.send_json(400, {"error": "Missing backup file or active save path."})
                return
            if not re.fullmatch(r"[A-Za-z0-9_.\-]+", backup_name):
                self.send_json(400, {"error": "Invalid backup name."})
                return
            try:
                p = Path(session.file_path).resolve()
                backups_dir = (p.parent / "backups").resolve()
                backup_zip = (backups_dir / backup_name).resolve()
                if backup_zip.parent != backups_dir:
                    self.send_json(400, {"error": "Path traversal attempt detected."})
                    return
                restore_res = atomic_restore_backup(
                    target_path=p,
                    backup_zip=backup_zip,
                    expected_baseline_sha256=session.baseline_sha256,
                )
                restored_bytes = p.read_bytes()
                session.baseline_bytes = restored_bytes
                session.baseline_sha256 = compute_sha256(restored_bytes)
                session.editor = SaveEditor(restored_bytes)
                session.revision += 1
                CURRENT_EDITOR = session.editor
                CURRENT_ORIGINAL_BYTES = session.baseline_bytes
                safety_name = Path(restore_res["backup_path"]).name if restore_res.get("backup_path") else "pre_restore_backup.zip"
                self.send_json(200, {"status": "success", "safety_backup": safety_name})
            except ConcurrencyConflictError as ce:
                self.send_json(409, {"error": str(ce), "conflict": True})
            except Exception as e:
                self.send_json(500, {"error": f"Restore failed: {str(e)}"})

        elif parsed.path == "/api/compare":
            target_path = data.get("target_path", "").strip()
            session = SESSION_MANAGER.get_session_by_token(token) or SESSION_MANAGER.get_session()
            if not session:
                self.send_json(400, {"error": "No active save loaded for comparison."})
                return
            if not target_path or not Path(target_path).is_file():
                self.send_json(400, {"error": "Valid comparison target save path is required."})
                return
            try:
                cmp_res = compare_saves(
                    session.baseline_bytes,
                    Path(target_path),
                    label_a="Current Save",
                    label_b=Path(target_path).name,
                )
                self.send_json(200, cmp_res)
            except Exception as e:
                self.send_json(500, {"error": f"Comparison failed: {str(e)}"})

        elif parsed.path == "/api/stage":
            session = SESSION_MANAGER.get_session_by_token(token) or SESSION_MANAGER.get_session()
            if not session:
                self.send_json(400, {"error": "No active save session."})
                return
            action = data.get("action", "stage")
            if action == "clear":
                session.clear_staged_changes()
                self.send_json(200, {"status": "success", "staged_changes": []})
            else:
                cat = data.get("category", "general")
                key = data.get("key", "unspecified")
                val = data.get("value")
                old_val = data.get("old_value")
                session.stage_field_change(cat, key, val, old_val=old_val)
                self.send_json(200, {"status": "success", "staged_changes": session.get_staged_summary()})

        elif parsed.path == "/api/transfer":
            source_path = data.get("source_path", "").strip()
            opts = data.get("transfer_options")
            if isinstance(opts, dict):
                categories = [k for k, v in opts.items() if v]
            else:
                categories = data.get("categories", ["money", "inventory", "compendium", "personas"])

            session = SESSION_MANAGER.get_session_by_token(token) or SESSION_MANAGER.get_session()
            if not session:
                self.send_json(400, {"error": "No active destination save session."})
                return
            if not source_path or not Path(source_path).is_file():
                self.send_json(400, {"error": "Valid source save path is required for transfer."})
                return
            try:
                src_bytes = Path(source_path).read_bytes()
                src_editor = SaveEditor(src_bytes)
                transfer_data = {}
                if "money" in categories:
                    transfer_data["header"] = {"money": src_editor.get_money()}
                if "social_stats" in categories:
                    transfer_data["social_stats"] = src_editor.get_social_stats()
                if "inventory" in categories:
                    transfer_data["inventory_normalized"] = src_editor.get_normalized_inventory()
                if "compendium" in categories:
                    src_comp = set(src_editor.get_compendium().get("registered", []))
                    cur_comp = set(session.editor.get_compendium().get("registered", []))
                    transfer_data["compendium"] = {
                        "supported": True,
                        "registered": sorted(list(src_comp | cur_comp)),
                    }
                if "personas" in categories:
                    transfer_data["joker_stock"] = src_editor.get_persona_stock(0)

                res = session.commit_transaction(transfer_data, strict_verification=True)
                CURRENT_EDITOR = session.editor
                CURRENT_ORIGINAL_BYTES = session.baseline_bytes
                self.send_json(200, {"status": "success", "transferred_categories": categories, "result": res})
            except Exception as e:
                self.send_json(500, {"error": f"Transfer failed: {str(e)}"})

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
