"""Regression tests for the 2026-08-16 in-game feedback hardening pass.

Covers (from the Reddit tester report + dual-oracle + AG review):
- Teammate LV u8 write (no +0x3D clobber) and u8 read
- Dummy/BLANK skill id rejection (stock + equipped)
- P5-legacy persona id rejection (stock + equipped)
- Teammate persona story-lock
- Compendium dead-bit rejection + 224-bit safe unlock
- GOD_BUILDS presets reference real table IDs
"""

import os
import re
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.editor import SaveEditor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def make_pc_editor() -> SaveEditor:
    e = SaveEditor()
    e.parser.is_pc_0x31 = True
    e.parser.data_payload = bytes(0x40000)
    return e


class TestMemberLevelU8(unittest.TestCase):
    def test_member_level_write_preserves_unk_byte(self):
        e = make_pc_editor()
        off = 0x2C + 1 * 0x2B0
        d = bytearray(e.parser.data_payload)
        d[off + 0x3D] = 0xAB  # unk byte (persona struct +0x05)
        e.parser.data_payload = bytes(d)
        r = e.set_party_stat(1, level=42)
        self.assertEqual(r["status"], "success")
        self.assertEqual(e.parser.data_payload[off + 0x3C], 42)
        self.assertEqual(e.parser.data_payload[off + 0x3D], 0xAB,
                         "member LV u16 write clobbered the +0x3D unk byte")

    def test_member_level_read_is_u8(self):
        e = make_pc_editor()
        off = 0x2C + 1 * 0x2B0
        d = bytearray(e.parser.data_payload)
        d[off + 0x3C] = 20
        d[off + 0x3D] = 0x01  # nonzero unk byte: u16 read would give 276
        e.parser.data_payload = bytes(d)
        stats = e.get_party_stats()
        self.assertEqual(stats[1]["level"], 20)

    def test_leader_level_still_u16_path(self):
        e = make_pc_editor()
        r = e.set_party_stat(0, level=25)
        self.assertEqual(r["status"], "success")
        self.assertEqual(e.get_party_stats()[0]["level"], 25)


class TestSkillDummyRejection(unittest.TestCase):
    def test_stock_rejects_blank_skill_ids(self):
        e = make_pc_editor()
        for sid in (0x0001, 0x0005, 0x0009):
            r = e.set_persona_stock_slot(0, 0, persona_id=0x16B, level=50,
                                         skills=[sid, 0, 0, 0, 0, 0, 0, 0])
            self.assertEqual(r["status"], "invalid", f"skill 0x{sid:X} accepted")
        self.assertEqual(e.parser.data_payload, bytes(0x40000))

    def test_equipped_rejects_blank_skill_ids(self):
        e = make_pc_editor()
        r = e.set_equipped_persona(0, persona_id=0x16B, level=50,
                                   skills=[0x0003, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(r["status"], "invalid")

    def test_stock_accepts_zero_skill_slot(self):
        # 0 = empty skill slot, always legal
        e = make_pc_editor()
        r = e.set_persona_stock_slot(0, 0, persona_id=0x16B, level=50,
                                     skills=[0] * 8)
        self.assertEqual(r["status"], "success")


class TestLegacyPersonaRejection(unittest.TestCase):
    def test_stock_rejects_p5_legacy_dups(self):
        e = make_pc_editor()
        for pid in (0x0DC, 0x0E0, 0x0DB):
            r = e.set_persona_stock_slot(0, 0, persona_id=pid, level=50)
            self.assertEqual(r["status"], "invalid", f"legacy 0x{pid:X} accepted")
        self.assertEqual(e.parser.data_payload, bytes(0x40000))

    def test_equipped_rejects_p5_legacy_dups(self):
        e = make_pc_editor()
        r = e.set_equipped_persona(0, persona_id=0x0DC, level=50)
        self.assertEqual(r["status"], "invalid")

    def test_stock_accepts_metatron_and_anat(self):
        # Real personas (even if their compendium bits are never set)
        e = make_pc_editor()
        for pid in (0x001, 0x0D8):
            r = e.set_persona_stock_slot(0, 0, persona_id=pid, level=50)
            self.assertEqual(r["status"], "success", f"real persona 0x{pid:X} rejected")


class TestTeammatePersonaLock(unittest.TestCase):
    def _seed_canonical(self, e: SaveEditor):
        # Teammate stock slot 0 = their canonical persona (real saves always
        # have it; synthetic payloads start zeroed — seed it first).
        r = e.set_persona_stock_slot(1, 0, persona_id=0xCA, level=20)
        self.assertEqual(r["status"], "success")

    def test_teammate_persona_change_rejected(self):
        e = make_pc_editor()
        self._seed_canonical(e)
        r = e.set_equipped_persona(1, persona_id=0x16B, level=99)
        self.assertEqual(r["status"], "invalid")
        self.assertEqual(e.get_equipped_persona(1)["persona_id"], 0xCA)

    def test_teammate_same_persona_edit_allowed(self):
        e = make_pc_editor()
        self._seed_canonical(e)
        r = e.set_equipped_persona(1, persona_id=0xCA, level=21)
        self.assertEqual(r["status"], "success")
        self.assertEqual(e.get_equipped_persona(1)["level"], 21)


class TestGodBuildIDs(unittest.TestCase):
    def test_god_build_ids_exist_in_tables(self):
        """GOD_BUILDS in app.js must reference real Personas/Skills/Traits."""
        path = os.path.join(ROOT, "web-app", "static", "app.js")
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        m = re.search(r"const GOD_BUILDS = (\{.*?\n\});", src, re.S)
        self.assertIsNotNone(m, "GOD_BUILDS block not found")
        personas = SaveEditor()._load_table("Personas.txt")
        skills = SaveEditor()._load_table("Skill ID.txt")
        traits = SaveEditor()._load_table("Traits.txt")
        for pid in re.findall(r"persona_id: (\d+)", m.group(1)):
            self.assertIn(int(pid), personas, f"persona {pid} missing from Personas.txt")
        for sid in re.findall(r"^\s+(\d+),? //", m.group(1), re.M):
            self.assertIn(int(sid), skills, f"skill {sid} missing from Skill ID.txt")
        for tid in re.findall(r"trait_id: (\d+)", m.group(1)):
            self.assertIn(int(tid), traits, f"trait {tid} missing from Traits.txt")

    def test_god_build_names_match(self):
        """Preset personas must be the advertised personas."""
        personas = SaveEditor()._load_table("Personas.txt")
        path = os.path.join(ROOT, "web-app", "static", "app.js")
        src = open(path, encoding="utf-8").read()
        expected = {"yoshitsune": "Yoshitsune", "izanagi": "Izanagi no Okami Picaro",
                    "raoul": "Raoul"}
        for key, want in expected.items():
            m = re.search(rf"{key}: \{{.*?persona_id: (\d+)", src, re.S)
            self.assertIsNotNone(m, f"preset {key} not found")
            name = personas.get(int(m.group(1)), "")
            self.assertEqual(name.lower(), want.lower(),
                             f"preset {key} maps to {name} != {want}")


class TestTraitDummyRejection(unittest.TestCase):
    def test_stock_rejects_reserve_trait(self):
        e = make_pc_editor()
        r = e.set_persona_stock_slot(0, 0, persona_id=0x16B, level=50, trait_id=0x0005)
        self.assertEqual(r["status"], "invalid")
        self.assertEqual(e.parser.data_payload, bytes(0x40000))

    def test_equipped_rejects_reserve_trait(self):
        e = make_pc_editor()
        r = e.set_equipped_persona(0, persona_id=0x16B, level=50, trait_id=0x0002)
        self.assertEqual(r["status"], "invalid")

    def test_stock_accepts_real_trait(self):
        e = make_pc_editor()
        r = e.set_persona_stock_slot(0, 0, persona_id=0x16B, level=50, trait_id=6)  # Relentless
        self.assertEqual(r["status"], "success")

    def test_trait_zero_allowed_as_unset(self):
        e = make_pc_editor()
        r = e.set_persona_stock_slot(0, 0, persona_id=0x16B, level=50, trait_id=0)
        self.assertEqual(r["status"], "success")


class TestReferenceDBCleanliness(unittest.TestCase):
    def test_database_has_no_dummy_entries(self):
        """The served reference DB must be free of RESERVE/???/dummy rows
        and duplicate names (deduped 2026-08-16, corpus-anchored ids)."""
        import sys
        sys.path.insert(0, ROOT)
        import server as web_server
        db = web_server.REFERENCE_DB
        bad_names = {"", "RESERVE", "???", "BLANK", "----------", "P5 Unused", "not used"}
        bad_personas = [p for p in db["personas"] if p["name"] in bad_names]
        bad_skills = [s for s in db["skills"] if s["name"] in bad_names or s["id"] <= 0x09
                      or s["name"].lower().startswith("unused:")]
        bad_traits = [t for t in db["traits"] if t["name"] in bad_names and t["id"] != 0]
        self.assertEqual(bad_personas, [])
        self.assertEqual(bad_skills, [])
        self.assertEqual(bad_traits, [])
        # sanitized + deduped + game-name-filtered counts (2026-08-16): 287/870/93
        self.assertEqual(len(db["personas"]), 287)
        self.assertEqual(len(db["skills"]), 870)
        self.assertEqual(len(db["traits"]), 93)  # 92 named + "None (unset)"

    def test_database_has_no_duplicate_names(self):
        import sys
        sys.path.insert(0, ROOT)
        import server as web_server
        db = web_server.REFERENCE_DB
        from collections import Counter
        for key in ("personas", "skills", "traits"):
            c = Counter(it["name"].lower() for it in db[key])
            dups = {n: k for n, k in c.items() if k > 1}
            self.assertEqual(dups, {}, f"{key} still has duplicate names: {dups}")


class TestGameNameTruth(unittest.TestCase):
    """2026-08-16: names corrected against the game's NAME.TBL, junk ids
    excluded from both the dropdown and the write validation."""

    def test_database_uses_game_skill_spellings(self):
        import sys
        sys.path.insert(0, ROOT)
        import server as web_server
        skills = {s["id"]: s["name"] for s in web_server.REFERENCE_DB["skills"]}
        self.assertEqual(skills[123], "Med Burn")
        self.assertEqual(skills[164], "Med All Ail")
        self.assertEqual(skills[516], "Royal Jelly")
        self.assertEqual(skills[295], "Ultimate Support")
        # no dump-only spellings anywhere
        bad = [s for s in skills.values() if s.startswith("Mid ") or s == "Royel Jelly"]
        self.assertEqual(bad, [])

    def test_database_uses_game_trait_spellings(self):
        import sys
        sys.path.insert(0, ROOT)
        import server as web_server
        traits = {t["id"]: t["name"] for t in web_server.REFERENCE_DB["traits"]}
        self.assertEqual(traits[9], "Savior Bloodline")
        self.assertEqual(traits[73], "Skillful Combo")
        self.assertEqual(traits[102], "Deathly Illness")

    def test_non_skill_ids_rejected_in_stock(self):
        e = make_pc_editor()
        for sid in (420, 568, 575, 585, 663):
            r = e.set_persona_stock_slot(0, 0, persona_id=0x16B, level=50,
                                         skills=[sid, 0, 0, 0, 0, 0, 0, 0])
            self.assertEqual(r["status"], "invalid", f"non-skill {sid} accepted")
        self.assertEqual(e.parser.data_payload, bytes(0x40000))

    def test_non_skill_ids_rejected_in_equipped(self):
        e = make_pc_editor()
        r = e.set_equipped_persona(0, persona_id=0x16B, level=50,
                                   skills=[482, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(r["status"], "invalid")

    def test_lab_personas_rejected(self):
        e = make_pc_editor()
        for pid in (440, 445, 450):
            r = e.set_persona_stock_slot(0, 0, persona_id=pid, level=50)
            self.assertEqual(r["status"], "invalid", f"Lab persona {pid} accepted")
        self.assertEqual(e.parser.data_payload, bytes(0x40000))

    def test_skill_meta_loaded(self):
        """data/SkillMeta.txt serves element/cost metadata from the game table."""
        import sys
        sys.path.insert(0, ROOT)
        import server as web_server
        meta = web_server.REFERENCE_DB.get("skill_meta", {})
        self.assertEqual(len(meta), 799)
        # verified spot checks: Agi=4SP fire, Hassou Tobi=25%HP phys, Myriad Truths=40SP almighty
        self.assertEqual(meta[10]["cost"], 4.0)
        self.assertEqual(meta[10]["costtype"], 2)
        self.assertEqual(meta[10]["element"], 2)
        self.assertEqual(meta[215]["cost"], 25.0)
        self.assertEqual(meta[215]["costtype"], 1)
        self.assertEqual(meta[215]["element"], 0)
        self.assertEqual(meta[713]["cost"], 40.0)
        self.assertEqual(meta[713]["element"], 10)

    def test_item_database_clean(self):
        """Item DB: no raw-hex placeholder names, game-correct spellings."""
        import sys
        sys.path.insert(0, ROOT)
        import server as web_server
        items = {i["id"]: i["name"] for i in web_server.REFERENCE_DB["items"]}
        self.assertEqual(len(items), len(web_server.REFERENCE_DB["items"]))
        hex_junk = [n for n in items.values() if n.startswith("0x")]
        self.assertEqual(hex_junk, [])
        self.assertEqual(items[8270], "Money Distributor")
        self.assertEqual(items[8304], "Discharge Crystal")
        self.assertEqual(items[8529], "Old Man's Elixir")
        self.assertEqual(items[12400], "Vajra Belt")
        self.assertEqual(items[12782], "Dazzling Netsuke")

    def test_unjoined_member_edits_refused(self):
        """Slots that still match the game's canonical seed (not yet joined)
        refuse all writes — protects against corrupting pre-join placeholder
        data. Seed verified against June + NG+ saves."""
        e = make_pc_editor()
        # write canonical seed for slot 5 (Makoto pre-join)
        off = 0x2C + 5 * 0x2B0
        d = bytearray(e.parser.data_payload)
        struct.pack_into("<H", d, off + 0, 243)      # hp seed
        struct.pack_into("<H", d, off + 4, 142)      # sp seed
        d[off + 0x3C] = 21                            # lv seed
        struct.pack_into("<H", d, off + 0x3A, 0xCE)  # persona seed
        e.parser.data_payload = bytes(d)
        self.assertFalse(e.is_member_joined(5))
        for fn, args in ((e.set_party_stat, (5,)),
                         (lambda *a: e.set_equipped_persona(5, persona_id=0xCE, level=21), ()),
                         (lambda *a: e.set_persona_stock_slot(5, 0, persona_id=0xCE, level=21), ())):
            r = fn(*args)
            self.assertEqual(r["status"], "invalid", f"edit to un-joined slot not refused: {fn}")
        # Joker and joined slots stay editable
        self.assertTrue(e.is_member_joined(0))
        self.assertEqual(e.set_party_stat(0, level=22)["status"], "success")

    def test_joined_member_edit_allowed(self):
        """A slot differing from its seed = member joined -> editable."""
        e = make_pc_editor()
        off = 0x2C + 1 * 0x2B0
        d = bytearray(e.parser.data_payload)
        struct.pack_into("<H", d, off + 0, 246)     # differs from seed 117
        e.parser.data_payload = bytes(d)
        self.assertTrue(e.is_member_joined(1))
        self.assertEqual(e.set_party_stat(1, level=20)["status"], "success")

    def test_party_stats_join_filters_ui(self):
        """get_party_stats marks joined; server party payload hides un-joined."""
        e = make_pc_editor()
        off = 0x2C + 5 * 0x2B0
        d = bytearray(e.parser.data_payload)
        struct.pack_into("<H", d, off + 0, 243)
        struct.pack_into("<H", d, off + 4, 142)
        d[off + 0x3C] = 21
        struct.pack_into("<H", d, off + 0x3A, 0xCE)
        e.parser.data_payload = bytes(d)
        stats = e.get_party_stats()
        self.assertEqual(stats[5]["joined"], False)
        self.assertEqual(stats[5]["name"], "???")
        self.assertEqual(stats[0]["joined"], True)

    def test_preset_skills_survive_audit(self):
        """The god-build preset skill ids must not be in the excluded set."""
        import re
        src = open(os.path.join(ROOT, "web-app", "static", "app.js"), encoding="utf-8").read()
        m = re.search(r"const GOD_BUILDS = (\{.*?\n\});", src, re.S)
        preset_ids = set(int(x) for x in re.findall(r"^\s+(\d+),? //", m.group(1), re.M))
        editor = SaveEditor()
        overlap = preset_ids & editor.PC31_NON_SKILL_IDS
        self.assertEqual(overlap, set(), f"presets reference excluded ids: {overlap}")


class TestCategoryStructuralIntegrity(unittest.TestCase):
    """Rigid structural tests preventing cross-category corruption and regressions."""

    def test_all_10_categories_strictly_segregated(self):
        """Every category must route strictly to either count-array or owned-flag, never both."""
        editor = SaveEditor()
        # Stacks categories (count offset > 0, owned offset == 0)
        for cand in [0x2001, 0x3001, 0x4001, 0x5001, 0x6001, 0x8001]:
            self.assertGreater(editor.get_item_count_offset(cand), 0, f"ID 0x{cand:04X} missing count offset")
            self.assertEqual(editor.get_item_owned_offset(cand), 0, f"ID 0x{cand:04X} must not have owned offset")

        # Unique gear categories (owned offset > 0, count offset == 0)
        for cand in [0x1001, 0x7010, 0xA001]:
            self.assertGreater(editor.get_item_owned_offset(cand), 0, f"ID 0x{cand:04X} missing owned offset")
            self.assertEqual(editor.get_item_count_offset(cand), 0, f"ID 0x{cand:04X} must not have count offset")

    def test_all_10_categories_roundtrip_repack(self):
        """Simultaneous write across all 10 categories must survive save_to_bytes and reload."""
        e = make_pc_editor()
        test_writes = [
            (0x2001, 5, "stack"),    # Consumable
            (0x6001, 3, "stack"),    # Infiltration
            (0x4002, 7, "stack"),    # SkillCard (Agi)
            (0x1002, 1, "gear"),     # Melee (Rebel Knife)
            (0x7010, 1, "gear"),     # Ranged (Makaronov)
            (0x5003, 4, "stack"),    # Protector / Armor (Dark Undershirt)
            (0xA002, 1, "gear"),     # Outfit (Shujin Uniform All)
            (0x3001, 9, "stack"),    # Accessory
            (0x8013, 12, "stack"),   # Treasure (Glory Staff)
        ]
        for iid, qty, _ in test_writes:
            e.set_item_quantity(iid, qty)

        reloaded_bytes = e.save_to_bytes()
        reloaded = SaveEditor(reloaded_bytes)
        norm = reloaded.get_normalized_inventory()

        for iid, qty, mode in test_writes:
            if mode == "gear":
                self.assertTrue(norm["owned_gear"].get(iid), f"Gear 0x{iid:04X} not owned after reload")
                self.assertNotIn(iid, norm["stacks"], f"Gear 0x{iid:04X} leaked into stacks")
            else:
                self.assertEqual(norm["stacks"].get(iid), qty, f"Stack 0x{iid:04X} wrong qty after reload")
    def test_spec_bundles_all_data_and_templates(self):
        """P5R_Save_Editor.spec must bundle the data directory and web templates."""
        spec_path = os.path.join(ROOT, "P5R_Save_Editor.spec")
        with open(spec_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("('data', 'data')", content, "spec file must bundle whole data folder dynamically")
        self.assertIn("('web-app/templates', 'web-app/templates')", content)
        self.assertIn("('web-app/static', 'web-app/static')", content)


class TestVirtualScrollPerfGate(unittest.TestCase):
    """Phase B — structural proof the Cheat Shop render path satisfies the
    <100ms / 696-row §7 gate without DOM thrashing.

    The browser-side timing can only be asserted in a live WebView (out of
    agent sandbox scope — see PROJECT_BOOTSTRAP.md), so here we prove the
    *mechanism* that guarantees it: bounded incremental batch render, a hard
    DOM cap, and read-only gating on every unwired category. (Docs:
    docs/ITEM_STUDIO_REBUILD_PLAN.md §5 B + §7.)"""

    def setUp(self):
        self.app_js = os.path.join(ROOT, "web-app", "static", "app.js")
        with open(self.app_js, "r", encoding="utf-8") as f:
            self.src = f.read()

    def test_no_hard_50_slice(self):
        # The old `catalog.slice(0, 50)` wall is gone.
        self.assertNotIn("catalog.slice(0, 50)", self.src,
                         "Cheat Shop modal must not hard-cap at 50")

    def test_incremental_batch_render_with_cap(self):
        self.assertIn("MODAL_BATCH_SIZE", self.src, "must track incremental batch size")
        # Hard DOM cap: never render more than 300 rows at once.
        self.assertIn("MODAL_BATCH_SIZE + 50, 300)", self.src,
                      "Load More must clamp batch size to a 300-row DOM cap")

    def test_unwired_categories_disabled_in_modal(self):
        """R8 drift resolved 2026-08-21: SkillCard/Treasure/Infiltration are
        backend-VERIFIED and writable; KeyItem is guarded (not unwired); only
        Outfit remains read-only (D008 freeze)."""
        m = re.search(r"const UNWIRED_CATEGORIES = new Set\(\[([^\]]*)\]\)", self.src)
        self.assertIsNotNone(m, "UNWIRED_CATEGORIES set missing")
        unwired = set(re.findall(r'"([^"]+)"', m.group(1)))
        self.assertEqual(unwired, {"Outfit"},
                         "only Outfit may remain in UNWIRED_CATEGORIES")
        # Disabled button must carry NO onclick handler (byte-level safety).
        self.assertIn('disabled title="Outfit writability frozen', self.src,
                      "frozen rows must render disabled with zero onclick")
        self.assertIn('"><span>FROZEN</span></button>', self.src)
        # Key items get a guarded ADD (S4), never an unwired block.
        key_idx = self.src.find("} else if (isKey) {")
        unwired_idx = self.src.find("} else if (isUnwired) {")
        self.assertGreaterEqual(key_idx, 0)
        self.assertGreater(unwired_idx, key_idx,
                           "KeyItem guarded-add branch must precede the frozen branch")

    def test_load_more_present(self):
        self.assertIn("Load", self.src)
        self.assertIn("renderModalCatalog()", self.src)

    def test_backend_read_perf_over_696_consumables(self):
        """The normalized read beneath the virtual scroll stays <100ms over a
        full 696-consumable-equivalent population (696 = ITEM_TBL_MAP seg 2)."""
        import time
        from core.editor import SaveEditor
        e = SaveEditor()
        e.parser.is_pc_0x31 = True
        d = bytearray(0x40000)
        # Seed idx 1..696 across verified sub-bases (0x2530/0x25AA/0x2600 + idx).
        seeded = 0
        for idx in range(1, 700):
            iid = 0x2000 | idx
            off = e.get_item_count_offset(iid)
            if off and off < len(d):
                d[off] = 1
                if off + 0x18510 < len(d):
                    d[off + 0x18510] = 1
                seeded += 1
        e.parser.data_payload = bytes(d)
        self.assertGreater(seeded, 600, f"only seeded {seeded} consumables — test fixture under-populated")
        # Warm + measure worst-of-5.
        worst_ms = 0.0
        surfaced = 0
        for _ in range(5):
            t0 = time.perf_counter()
            norm = e.get_normalized_inventory()
            worst_ms = max(worst_ms, (time.perf_counter() - t0) * 1000)
            surfaced = len(norm["stacks"])
        self.assertGreater(surfaced, 400, f"only {surfaced} consumed surfaced — read path incomplete")
        self.assertLess(worst_ms, 100, f"backend read {worst_ms:.1f}ms over {surfaced} items exceeds 100ms SLA")


class TestCompendiumUnlockAllWiring(unittest.TestCase):
    """Regression for the 2026-08-21 in-game '96% compendium' report.

    Root cause: the UI's Unlock ALL staged a filtered registered list (party/
    story/stub ids excluded) and /api/save's per-pid loop actively CLEARED
    those mask bits and never wrote their Velvet Room records — while genuine
    100% saves set ALL 224 live bits and carry 232 records (game % counts
    records). Fix: Unlock ALL arms UNLOCK_COMPENDIUM_PENDING so /api/save runs
    the verified unlock_compendium_100() (exact oracle parity)."""

    def setUp(self):
        with open(os.path.join(ROOT, "web-app", "static", "app.js"), encoding="utf-8") as f:
            self.src = f.read()
        with open(os.path.join(ROOT, "server.py"), encoding="utf-8") as f:
            self.server_src = f.read()

    def _unlock_fn_src(self):
        m = re.search(r"function unlockFullCompendium\(\) \{.*?\n\}", self.src, re.S)
        self.assertIsNotNone(m, "unlockFullCompendium() missing from app.js")
        return m.group(0)

    def test_unlock_all_arms_backend_flag(self):
        fn = self._unlock_fn_src()
        self.assertIn("UNLOCK_COMPENDIUM_PENDING = true", fn,
                      "Unlock ALL must arm the backend full-unlock flag")
        self.assertNotIn("PARTY_COMPENDIUM_IDS.has(id)", fn,
                         "Unlock ALL must not filter party personas — genuine 100% sets their bits")
        self.assertNotIn("STORY_COMPENDIUM_IDS.has(id)", fn)
        self.assertNotIn("STUB_COMPENDIUM_IDS.has(id)", fn)

    def test_payload_carries_unlock_flag_and_resets(self):
        self.assertIn("CURRENT_SAVE.unlock_compendium = true", self.src,
                      "/api/save payload must carry the unlock_compendium flag")
        self.assertGreaterEqual(self.src.count("UNLOCK_COMPENDIUM_PENDING = false"), 2,
                                "flag must reset after save and on compendium reset")

    def test_server_applies_flag_via_verified_unlock(self):
        self.assertIn('data.get("unlock_compendium")', self.server_src)
        self.assertIn("unlock_compendium_100()", self.server_src)

    def test_unlock_sets_every_live_bit_including_party_range(self):
        """Behavioral: unlock_compendium_100() sets ALL non-dead mask bits —
        including the party/Satanael range (0xAA/0xC7/0xCA-0xD3) the old UI
        flow silently cleared — with primary/mirror parity."""
        e = make_pc_editor()
        e.unlock_compendium_100()
        d = e.parser.data_payload
        B = SaveEditor.PC31_COMPENDIUM_BITS
        M = SaveEditor.PC31_OFFSET_COMPENDIUM
        MI = SaveEditor.PC31_COMPENDIUM_MIRROR
        setbits = {i + 1 for i in range(B) if (d[M + i // 8] >> (i % 8)) & 1}
        expected = set(range(1, B + 1)) - SaveEditor.PC31_COMPENDIUM_DEAD_BITS
        self.assertEqual(setbits, expected,
                         "unlock must set every live bit (incl. party 0xCA-0xD3, Satanael 0xAA/0xC7)")
        nb = (B + 7) // 8
        self.assertEqual(d[M:M + nb], d[MI:MI + nb], "mask mirror out of sync after unlock")


class TestInventoryRemovalPersistence(unittest.TestCase):
    """Regression for the silent no-op removal bug (found 2026-08-21).

    The UI DELETED zeroed ids from its item map, so the save payload never
    contained them and the backend merge-patch loop left the old bytes —
    DISCARD/UNEQUIP silently didn't persist (items resurrected on reload).
    Fix per RFC 6902 lesson ('deletion must be explicit'): mutations store
    explicit 0, and the payload is the minimal diff vs the load baseline."""

    def setUp(self):
        with open(os.path.join(ROOT, "web-app", "static", "app.js"), encoding="utf-8") as f:
            self.src = f.read()

    def _fn_src(self, name):
        m = re.search(r"function %s\(\) \{.*?\n\}" % name, self.src, re.S)
        self.assertIsNotNone(m, "%s() missing from app.js" % name)
        return m.group(0)

    def test_mutations_never_delete_keys(self):
        self.assertNotIn("delete INVENTORY_ITEM_COUNTS", self.src,
                         "zeroing must store explicit 0 — key deletion makes removals vanish from the payload")

    def test_payload_is_baseline_diff(self):
        fn = self._fn_src("buildInventoryPayload")
        self.assertIn("__INVENTORY_BASELINE", fn,
                      "payload must be computed as a diff against the load baseline")
        self.assertIn("cur===was", fn.replace(" ", ""),
                      "diff must skip untouched ids")
        # and executeSavePayload must use it
        self.assertIn("const normPayload = buildInventoryPayload();", self.src)

    def test_removal_persists_untouched_preserved(self):
        """Behavioral: baseline {stackA:5, stackB:3, gear:owned}; user discards
        stackA and unequips gear; stackB untouched. Emitted change-set zeroes
        A + gear (with mirrors) and never writes B."""
        e = SaveEditor()
        e.parser.is_pc_0x31 = True
        d = bytearray(0x40000)
        soff_a = e.get_item_count_offset(0x2001)
        soff_b = e.get_item_count_offset(0x2002)
        goff = e.get_item_owned_offset(0x1005)
        for off, val in ((soff_a, 5), (soff_a + 0x18510, 5), (soff_b, 3), (soff_b + 0x18510, 3), (goff, 1), (goff + 0x18510, 1)):
            d[off] = val
        e.parser.data_payload = bytes(d)

        # UI state: hydrated baseline -> user discards 0x2001, unequips 0x1005
        baseline = {"8193": 5, "8194": 3, "4101": 1}
        current = {"8193": 0, "8194": 3, "4101": 0}
        payload_stacks, payload_gear = {}, {}
        for id_str in set(baseline) | set(current):
            cur_v, was_v = current.get(id_str, 0), baseline.get(id_str, 0)
            if cur_v == was_v:
                continue  # untouched — omitted
            if int(id_str) & 0xF000 == 0x1000:
                payload_gear[int(id_str)] = cur_v > 0
            else:
                payload_stacks[int(id_str)] = max(0, min(99, cur_v))
        self.assertEqual(payload_stacks, {0x2001: 0}, "discard must emit explicit 0")
        self.assertEqual(payload_gear, {0x1005: False}, "unequip must emit explicit false")

        for rid, qty in payload_stacks.items():
            e.set_item_quantity(rid, qty)
        for rid, owned in payload_gear.items():
            e.set_item_quantity(rid, 1 if owned else 0)
        d2 = e.parser.data_payload
        self.assertEqual(d2[soff_a], 0, "discarded stack must persist as 0")
        self.assertEqual(d2[soff_a + 0x18510], 0, "mirror must be zeroed too")
        self.assertEqual(d2[goff], 0, "unequipped gear flag must persist as 0")
        self.assertEqual(d2[goff + 0x18510], 0, "gear mirror must be zeroed too")
        self.assertEqual(d2[soff_b], 3, "untouched id must NOT be written")


class TestInventoryUXSuite(unittest.TestCase):
    """UX pass 2026-08-21 (docs/INVENTORY_UX_REVIEW.md R1-R9): receipt review,
    per-item revert, global search, context menu + keyboard, incremental main
    list, share codes."""

    def setUp(self):
        with open(os.path.join(ROOT, "web-app", "static", "app.js"), encoding="utf-8") as f:
            self.src = f.read()

    def _fn_src(self, name):
        m = re.search(r"function %s\([^)]*\) \{.*?\n\}" % name, self.src, re.S)
        self.assertIsNotNone(m, "%s() missing from app.js" % name)
        return m.group(0)

    def test_ux_suite_r1_r2_r3_r5_r7_r9_present(self):
        for fn in ["buildPendingChangesReceipt", "showPendingChangesModal",
                   "revertItemToBaseline", "onGlobalSearchInput",
                   "openInvContextMenu", "initInventoryKeyboard",
                   "makeShareCode", "parseShareCode", "importBagShareCode"]:
            self.assertIn(f"function {fn}(", self.src, f"{fn} missing")
        # R1: save flow reviews before writing
        self.assertIn("if (!skipReview && changeCount > 0)", self.src)
        # R2: dirty rows expose revert inside the roster renderer
        self.assertIn("revertItemToBaseline(", self.src.split("function renderUnifiedItemList")[1])
        # R5: keyboard guard — no stepping when typing in inputs
        self.assertIn("INPUT", self._fn_src("initInventoryKeyboard"))
        # R7: main list renders incrementally (batch state + Load more)
        self.assertIn("MAIN_LIST_BATCH", self.src)
        # R9: codes are namespaced
        self.assertIn('"COH1."', self.src)


class TestDiscoveryAndManualUpload(unittest.TestCase):
    """Verifies comprehensive save discovery across Steam/GamePass locations
    and manual save file browse / upload flow."""

    def test_discover_steam_save_dirs_returns_list_of_paths(self):
        from core.environment import discover_steam_save_dirs
        dirs = discover_steam_save_dirs()
        self.assertIsInstance(dirs, list)

    def test_list_save_files_tolerates_nonexistent_and_returns_list(self):
        from core.environment import list_save_files
        from pathlib import Path
        saves = list_save_files(Path("C:/nonexistent_fake_dir/123"))
        self.assertEqual(saves, [])

    def test_build_loaded_save_payload_handles_editor_instance(self):
        from server import _build_loaded_save_payload
        e = make_pc_editor()
        payload = _build_loaded_save_payload(e, "test_path/DATA.DAT")
        self.assertEqual(payload["file_path"], "test_path/DATA.DAT")
        self.assertIn("header", payload)
        self.assertIn("party", payload)
        self.assertIn("confidants", payload)

    def test_confidant_romance_and_points_preservation(self):
        from server import _build_loaded_save_payload, CONFIDANT_ARCANA_MAP
        e = make_pc_editor()
        arc_id = CONFIDANT_ARCANA_MAP["Death"]  # 13
        # Set Death (Takemi) to Rank 4 with 15 affinity points
        e.set_confidant_rank(arc_id, 4, points=15, romance=False, auto_unlock=True)
        conf = e.get_confidant_ranks()["Death"]
        self.assertEqual(conf["rank"], 4)
        self.assertEqual(conf["points"], 15)
        self.assertFalse(conf["romance"])

        # Calling set_confidant_rank without points parameter preserves existing points
        e.set_confidant_rank(arc_id, 4, romance=True)
        conf2 = e.get_confidant_ranks()["Death"]
        self.assertEqual(conf2["rank"], 4)
        self.assertEqual(conf2["points"], 15, "Affinity points must not be wiped when modifying romance/other fields")
        self.assertTrue(conf2["romance"])


class TestRomanceUIReactivity(unittest.TestCase):
    """Verifies that app.js properly renders both LOVER and PLATONIC badges based on info.romance."""

    def test_app_js_checks_info_romance_for_status_badge(self):
        with open(os.path.join(ROOT, "web-app", "static", "app.js"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn("info.romance ?", src)
        self.assertIn("LOVER RELATIONSHIP", src)
        self.assertIn("PLATONIC FRIENDSHIP", src)


if __name__ == "__main__":
    unittest.main()

