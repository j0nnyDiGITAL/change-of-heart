/**
 * Persona 5 Royal Save Editor — Official Atlus-Grade Client Controller
 */

let DB = {
  personas: [],
  skills: [],
  traits: [],
  items: [],
  confidants: [],
  confidant_profiles: {},
  romanceable: [],
  point_thresholds: {}
};

let CURRENT_SAVE = null;
let ACTIVE_MEMBER_INDEX = 0;
let CURRENT_CONFIDANT_FILTER = "all";
let ALLOW_UNSAFE_CONFIDANTS = false;
let INITIAL_CONFIDANT_RANKS = {};

// =========================================================================
// AUTHENTIC PERSONA 5 SYNTHETIC WEB AUDIO SFX ENGINE
// =========================================================================
const P5Audio = {
  ctx: null,
  init() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) this.ctx = new AudioCtx();
    }
  },
  playClick() {
    try {
      this.init();
      if (!this.ctx) return;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = "triangle";
      osc.frequency.setValueAtTime(880, this.ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(440, this.ctx.currentTime + 0.06);
      gain.gain.setValueAtTime(0.12, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.06);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start();
      osc.stop(this.ctx.currentTime + 0.06);
    } catch(e) {}
  },
  playSwitch() {
    try {
      this.init();
      if (!this.ctx) return;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(320, this.ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(960, this.ctx.currentTime + 0.09);
      gain.gain.setValueAtTime(0.15, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.09);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start();
      osc.stop(this.ctx.currentTime + 0.09);
    } catch(e) {}
  },
  playMax() {
    try {
      this.init();
      if (!this.ctx) return;
      const now = this.ctx.currentTime;
      [523.25, 659.25, 783.99, 1046.50].forEach((freq, i) => {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = "square";
        osc.frequency.setValueAtTime(freq, now + i * 0.05);
        gain.gain.setValueAtTime(0.08, now + i * 0.05);
        gain.gain.exponentialRampToValueAtTime(0.001, now + i * 0.05 + 0.12);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(now + i * 0.05);
        osc.stop(now + i * 0.05 + 0.12);
      });
    } catch(e) {}
  }
};

// Global click sound listener for buttons and interactive pills
document.addEventListener("click", (e) => {
  if (e.target.closest("button, .p5-btn-action, .p5-nav-item, .p5-tarot-card, .filter-pill, .stock-chip, .star-node")) {
    P5Audio.playClick();
  }
});


// Meta God Build Presets (Real P5R Persona & Skill IDs — verified against
// data/ tables 2026-08-16; the previous IDs were from a foreign numbering
// and produced junk personas / crashes in-game)
const GOD_BUILDS = {
  yoshitsune: {
    persona_id: 87,   // Yoshitsune (0x57)
    level: 99,
    trait_id: 58,     // Undying Fury (+30% Phys)
    skills: [
      215, // Hassou Tobi
      856, // Apt Pupil
      852, // Arms Master
      360, // Charge
      851, // Insta-Heal
      857, // Ali Dance
      873, // Drain Fire
      878  // Drain Ice
    ]
  },
  izanagi: {
    persona_id: 366,  // Izanagi-no-Okami Picaro (0x16E)
    level: 99,
    trait_id: 194,    // Country Maker (+100% DMG/DEF)
    skills: [
      713, // Myriad Truths
      986, // Almighty Boost
      987, // Almighty Amp
      984, // Magic Ability
      853, // Spell Master
      361, // Concentrate
      898, // Drain Curse
      861  // Victory Cry
    ]
  },
  raoul: {
    persona_id: 363,  // Raoul (0x16B)
    level: 99,
    trait_id: 179,    // Wealth of Lotus (+2 Turn Buffs)
    skills: [
      841, // Auto-Mataru
      844, // Auto-Maraku
      847, // Auto-Masuku
      716, // Phantom Show
      348, // Debilitate
      806, // Enduring Soul
      851, // Insta-Heal
      853  // Spell Master
    ]
  }
};

// Persona 5 Royal Canonical Elemental Affinities Database (By Canonical Name and Hex/Dec IDs)
// '-' (Neutral), 'Wk' (Weak), 'Str' (Resist), 'Nul' (Null), 'Rpl' (Repel), 'Dr' (Drain)
const P5R_BASE_AFFINITIES = {
  // Canonical Names
  "Arsene": { phys: "-", gun: "-", fire: "-", ice: "Wk", elec: "-", wind: "-", psy: "-", nuke: "-", bless: "Wk", curse: "Str" },
  "Shiisaa": { phys: "Str", gun: "Str", fire: "-", ice: "-", elec: "-", wind: "-", psy: "Wk", nuke: "Str", bless: "Nul", curse: "Wk" },
  "Jack Frost": { phys: "-", gun: "-", fire: "Wk", ice: "Nul", elec: "-", wind: "-", psy: "-", nuke: "-", bless: "-", curse: "-" },
  "Jack-o'-Lantern": { phys: "-", gun: "Wk", fire: "Str", ice: "Wk", elec: "-", wind: "Wk", psy: "-", nuke: "-", bless: "-", curse: "-" },
  "Pixie": { phys: "-", gun: "Wk", fire: "-", ice: "Wk", elec: "Str", wind: "-", psy: "-", nuke: "-", bless: "Str", curse: "Wk" },
  "Matador": { phys: "-", gun: "-", fire: "-", ice: "-", elec: "Wk", wind: "Nul", psy: "-", nuke: "-", bless: "-", curse: "-" },
  "Messiah Picaro": { phys: "-", gun: "-", fire: "Str", ice: "Str", elec: "Str", wind: "Str", psy: "Str", nuke: "Str", bless: "Rpl", curse: "Wk" },
  "Messiah": { phys: "-", gun: "-", fire: "Str", ice: "Str", elec: "Str", wind: "Str", psy: "Str", nuke: "Str", bless: "Rpl", curse: "Wk" },
  "Regent": { phys: "Str", gun: "Str", fire: "-", ice: "-", elec: "-", wind: "-", psy: "Wk", nuke: "Wk", bless: "Wk", curse: "Wk" },
  "Shiki-Ouji": { phys: "Nul", gun: "Nul", fire: "-", ice: "-", elec: "-", wind: "-", psy: "-", nuke: "Wk", bless: "Nul", curse: "Nul" },
  "Yoshitsune": { phys: "Nul", gun: "-", fire: "Str", ice: "-", elec: "Rpl", wind: "-", psy: "-", nuke: "-", bless: "Rpl", curse: "-" },
  "Izanagi-no-Okami Picaro": { phys: "Str", gun: "Str", fire: "Str", ice: "Str", elec: "Str", wind: "Str", psy: "Str", nuke: "Str", bless: "Str", curse: "Str" },
  "Izanagi-no-Okami": { phys: "Str", gun: "Str", fire: "Str", ice: "Str", elec: "Str", wind: "Str", psy: "Str", nuke: "Str", bless: "Str", curse: "Str" },
  "Raoul": { phys: "-", gun: "Str", fire: "-", ice: "-", elec: "-", wind: "-", psy: "-", nuke: "-", bless: "Wk", curse: "Nul" },
  "Satanael": { phys: "Str", gun: "Str", fire: "Str", ice: "Str", elec: "Str", wind: "Str", psy: "Str", nuke: "Str", bless: "Nul", curse: "Dr" },
  "Lucifer": { phys: "-", gun: "Str", fire: "Str", ice: "Str", elec: "Str", wind: "Str", psy: "-", nuke: "-", bless: "Wk", curse: "Dr" },
  "Captain Kidd": { phys: "-", gun: "-", fire: "-", ice: "-", elec: "Str", wind: "Wk", psy: "-", nuke: "-", bless: "-", curse: "-" },
  "Zorro": { phys: "-", gun: "-", fire: "-", ice: "-", elec: "Wk", wind: "Str", psy: "-", nuke: "-", bless: "-", curse: "-" },
  "Carmen": { phys: "-", gun: "-", fire: "Str", ice: "Wk", elec: "-", wind: "-", psy: "-", nuke: "-", bless: "-", curse: "-" },
  "Goemon": { phys: "-", gun: "-", fire: "Wk", ice: "Str", elec: "-", wind: "-", psy: "-", nuke: "-", bless: "-", curse: "-" },
  "Johanna": { phys: "-", gun: "-", fire: "-", ice: "-", elec: "-", wind: "-", psy: "Wk", nuke: "Str", bless: "Str", curse: "-" },
  "Necronomicon": { phys: "-", gun: "-", fire: "-", ice: "-", elec: "-", wind: "-", psy: "-", nuke: "-", bless: "-", curse: "-" },
  "Milady": { phys: "-", gun: "-", fire: "-", ice: "-", elec: "-", wind: "-", psy: "Str", nuke: "Wk", bless: "-", curse: "-" },
  "Robin Hood": { phys: "-", gun: "-", fire: "-", ice: "-", elec: "-", wind: "-", psy: "-", nuke: "-", bless: "Str", curse: "Wk" },
  "Cendrillon": { phys: "Str", gun: "-", fire: "-", ice: "-", elec: "-", wind: "-", psy: "-", nuke: "-", bless: "Nul", curse: "Wk" },
  "Odin": { phys: "-", gun: "-", fire: "-", ice: "-", elec: "Dr", wind: "Rpl", psy: "-", nuke: "-", bless: "-", curse: "Wk" },
  "Anubis": { phys: "-", gun: "-", fire: "-", ice: "-", elec: "-", wind: "-", psy: "-", nuke: "-", bless: "Nul", curse: "Nul" },
  "King Frost": { phys: "-", gun: "-", fire: "Wk", ice: "Dr", elec: "-", wind: "-", psy: "-", nuke: "-", bless: "Nul", curse: "-" },

  // ID Aliases
  1: { phys: "-", gun: "-", fire: "-", ice: "Wk", elec: "-", wind: "-", psy: "-", nuke: "-", bless: "Wk", curse: "Str" },
  201: { phys: "-", gun: "-", fire: "-", ice: "Wk", elec: "-", wind: "-", psy: "-", nuke: "-", bless: "Wk", curse: "Str" },
  220: { phys: "-", gun: "-", fire: "-", ice: "Wk", elec: "-", wind: "-", psy: "-", nuke: "-", bless: "Wk", curse: "Str" },
  60: { phys: "Str", gun: "Str", fire: "-", ice: "-", elec: "-", wind: "-", psy: "Wk", nuke: "Str", bless: "Nul", curse: "Wk" },
  314: { phys: "Str", gun: "Str", fire: "-", ice: "-", elec: "-", wind: "-", psy: "Wk", nuke: "Str", bless: "Nul", curse: "Wk" },
  5: { phys: "-", gun: "-", fire: "Wk", ice: "Nul", elec: "-", wind: "-", psy: "-", nuke: "-", bless: "-", curse: "-" },
  315: { phys: "-", gun: "-", fire: "Wk", ice: "Nul", elec: "-", wind: "-", psy: "-", nuke: "-", bless: "-", curse: "-" },
  285: { phys: "-", gun: "-", fire: "-", ice: "-", elec: "Wk", wind: "Nul", psy: "-", nuke: "-", bless: "-", curse: "-" },
  190: { phys: "-", gun: "-", fire: "Str", ice: "Str", elec: "Str", wind: "Str", psy: "Str", nuke: "Str", bless: "Rpl", curse: "Wk" },
  106: { phys: "Str", gun: "Str", fire: "-", ice: "-", elec: "-", wind: "-", psy: "Wk", nuke: "Wk", bless: "Wk", curse: "Wk" },
  51: { phys: "Nul", gun: "Nul", fire: "-", ice: "-", elec: "-", wind: "-", psy: "-", nuke: "Wk", bless: "Nul", curse: "Nul" },
  87: { phys: "Nul", gun: "-", fire: "Str", ice: "-", elec: "Rpl", wind: "-", psy: "-", nuke: "-", bless: "Rpl", curse: "-" },
  365: { phys: "Nul", gun: "-", fire: "Str", ice: "-", elec: "Rpl", wind: "-", psy: "-", nuke: "-", bless: "Rpl", curse: "-" },
  305: { phys: "Str", gun: "Str", fire: "Str", ice: "Str", elec: "Str", wind: "Str", psy: "Str", nuke: "Str", bless: "Str", curse: "Str" },
  333: { phys: "-", gun: "Str", fire: "-", ice: "-", elec: "-", wind: "-", psy: "-", nuke: "-", bless: "Wk", curse: "Nul" },
  363: { phys: "-", gun: "Str", fire: "-", ice: "-", elec: "-", wind: "-", psy: "-", nuke: "-", bless: "Wk", curse: "Nul" },
  170: { phys: "Str", gun: "Str", fire: "Str", ice: "Str", elec: "Str", wind: "Str", psy: "Str", nuke: "Str", bless: "Nul", curse: "Dr" },
  387: { phys: "Str", gun: "Str", fire: "Str", ice: "Str", elec: "Str", wind: "Str", psy: "Str", nuke: "Str", bless: "Nul", curse: "Dr" },
  230: { phys: "-", gun: "Str", fire: "Str", ice: "Str", elec: "Str", wind: "Str", psy: "-", nuke: "-", bless: "Wk", curse: "Dr" },
  253: { phys: "-", gun: "Str", fire: "Str", ice: "Str", elec: "Str", wind: "Str", psy: "-", nuke: "-", bless: "Wk", curse: "Dr" },
  388: { phys: "-", gun: "Str", fire: "Str", ice: "Str", elec: "Str", wind: "Str", psy: "-", nuke: "-", bless: "Wk", curse: "Dr" },
  202: { phys: "-", gun: "-", fire: "-", ice: "-", elec: "Str", wind: "Wk", psy: "-", nuke: "-", bless: "-", curse: "-" },
  203: { phys: "-", gun: "-", fire: "-", ice: "-", elec: "Wk", wind: "Str", psy: "-", nuke: "-", bless: "-", curse: "-" },
  204: { phys: "-", gun: "-", fire: "Str", ice: "Wk", elec: "-", wind: "-", psy: "-", nuke: "-", bless: "-", curse: "-" },
  205: { phys: "-", gun: "-", fire: "Wk", ice: "Str", elec: "-", wind: "-", psy: "-", nuke: "-", bless: "-", curse: "-" },
  206: { phys: "-", gun: "-", fire: "-", ice: "-", elec: "-", wind: "-", psy: "Wk", nuke: "Str", bless: "Str", curse: "-" },
  207: { phys: "-", gun: "-", fire: "-", ice: "-", elec: "-", wind: "-", psy: "Str", nuke: "Wk", bless: "-", curse: "-" },
  208: { phys: "-", gun: "-", fire: "-", ice: "-", elec: "-", wind: "-", psy: "-", nuke: "-", bless: "-", curse: "-" },
  209: { phys: "-", gun: "-", fire: "-", ice: "-", elec: "-", wind: "-", psy: "-", nuke: "-", bless: "Str", curse: "Wk" },
  240: { phys: "Str", gun: "-", fire: "-", ice: "-", elec: "-", wind: "-", psy: "-", nuke: "-", bless: "Nul", curse: "Wk" }
};

// Skill Passive Overrides (Resist, Null, Repel, Drain)
const PASSIVE_AFFINITY_SKILLS = {
  // Fire
  872: { elem: "fire", type: "Str" }, // Resist Fire
  873: { elem: "fire", type: "Nul" }, // Null Fire
  874: { elem: "fire", type: "Rpl" }, // Repel Fire
  875: { elem: "fire", type: "Dr"  }, // Drain Fire
  341: { elem: "fire", type: "Dr"  }, // Drain Fire (alt)
  // Ice
  877: { elem: "ice", type: "Str" }, // Resist Ice
  878: { elem: "ice", type: "Nul" }, // Null Ice
  879: { elem: "ice", type: "Rpl" }, // Repel Ice
  880: { elem: "ice", type: "Dr"  }, // Drain Ice
  834: { elem: "ice", type: "Dr"  }, // Drain Ice (alt)
  // Wind
  882: { elem: "wind", type: "Str" }, // Resist Wind
  883: { elem: "wind", type: "Nul" }, // Null Wind
  884: { elem: "wind", type: "Rpl" }, // Repel Wind
  885: { elem: "wind", type: "Dr"  }, // Drain Wind
  // Elec
  887: { elem: "elec", type: "Str" }, // Resist Elec
  888: { elem: "elec", type: "Nul" }, // Null Elec
  889: { elem: "elec", type: "Rpl" }, // Repel Elec
  890: { elem: "elec", type: "Dr"  }, // Drain Elec
  // Bless
  892: { elem: "bless", type: "Str" }, // Resist Bless
  893: { elem: "bless", type: "Nul" }, // Null Bless
  894: { elem: "bless", type: "Rpl" }, // Repel Bless
  895: { elem: "bless", type: "Dr"  }, // Drain Bless
  // Curse
  897: { elem: "curse", type: "Str" }, // Resist Curse
  898: { elem: "curse", type: "Nul" }, // Null Curse
  899: { elem: "curse", type: "Rpl" }, // Repel Curse
  900: { elem: "curse", type: "Dr"  }, // Drain Curse
  342: { elem: "curse", type: "Dr"  }, // Drain Curse (alt)
  // Phys
  902: { elem: "phys", type: "Str" }, // Resist Phys
  903: { elem: "phys", type: "Nul" }, // Null Phys
  904: { elem: "phys", type: "Rpl" }, // Repel Phys
  905: { elem: "phys", type: "Dr"  }  // Drain Phys
};

// Lifecycle
document.addEventListener("DOMContentLoaded", async () => {
  startUiHeartbeat(); // FIRST — prove the WebView UI is alive (main.py watchdog).
  // Must fire before any slow init: on slow machines loadDatabase/refreshDiscovery
  // can take >30s, and a late heartbeat would misfire the watchdog fallback.
  loadDatabase();
  refreshDiscovery();
  initInventoryKeyboard(); // R5: keyboard navigation for the item roster
});

// UI liveness ping — if these never arrive at the server, the native window's
// JS is dead (broken WebView2 Runtime) and main.py auto-falls-back to the
// system browser instead of leaving the user with a silent dead window.
function startUiHeartbeat() {
  const beat = () => fetch("/api/ui-heartbeat").catch(() => {});
  beat();
  setInterval(beat, 15000);
}

// Load Database
async function loadDatabase() {
  try {
    const res = await fetch("/api/database");
    DB = await res.json();
    hydrateItemOwnerMap();
    populatePersonaDropdown();
    populateTraitDropdown();
    // restore inventory view/chara/search from hash (ADR 0002 hash persistence)
    try {
      const h = new URLSearchParams(window.location.hash.replace(/^#/, ""));
      const v = h.get("inv"); if (v === "pouch" || v === "catalog") INVENTORY_VIEW = v;
      const c = h.get("cat"); if (c) CURRENT_UNIFIED_CATEGORY = c;
      const w = h.get("who"); if (w) INVENTORY_CHARA = w;
      const q = h.get("q"); if (q !== null) { UNIFIED_SEARCH_QUERY = decodeURIComponent(q); const inp = document.getElementById("unifiedItemSearchBox"); if (inp) inp.value = UNIFIED_SEARCH_QUERY; }
      setInventoryView(INVENTORY_VIEW);
      renderCharacterChips();
    } catch {}
    renderInventoryViews();
  } catch (err) {
    console.error("DB Load Error:", err);
  }
}

// Auto Discovery
async function refreshDiscovery() {
  try {
    const res = await fetch("/api/discovery");
    const data = await res.json();
    const dropdown = document.getElementById("saveFileDropdown");
    dropdown.innerHTML = "";

    if (data.saves && data.saves.length > 0) {
      data.saves.forEach((s) => {
        const opt = document.createElement("option");
        opt.value = s;
        opt.textContent = `🎮 ${s.split("\\").slice(-2).join(" / ")}`;
        dropdown.appendChild(opt);
      });
      await loadSaveFile();
    } else {
      dropdown.innerHTML = `<option value="">-- No Steam saves found (Use BROWSE button) --</option>`;
      setStatus("No saves auto-detected in standard folder — click 📂 BROWSE to select your save file.");
    }
  } catch (err) {
    console.error("Discovery error:", err);
  }
}

// Load Active Save File
async function loadSaveFile() {
  const path = document.getElementById("saveFileDropdown").value;
  if (!path) return;

  setStatus("Loading and decrypting P5R save file...");
  try {
    const res = await fetch("/api/load", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path })
    });
    const data = await res.json();
    if (data.error) {
      alert("Error: " + data.error);
      setStatus("Failed to load: " + data.error);
      return;
    }
    _applyLoadedSaveData(data, path);
  } catch (err) {
    console.error("Load save error:", err);
    setStatus("Error communicating with server.");
  }
}

// Manual Save File Picker (for custom paths / GamePass saves)
function onManualFileSelected(event) {
  const file = event.target.files?.[0];
  if (!file) return;

  setStatus(`Reading ${file.name}...`);
  const reader = new FileReader();
  reader.onload = async (e) => {
    try {
      const b64 = e.target.result.split(",")[1];
      setStatus("Decrypting uploaded save file...");
      const res = await fetch("/api/load-upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ data: b64, filename: file.name })
      });
      const data = await res.json();
      if (data.error) {
        alert("Load Error: " + data.error);
        setStatus("Failed to load: " + data.error);
        return;
      }
      // Add custom entry to dropdown
      const dropdown = document.getElementById("saveFileDropdown");
      const opt = document.createElement("option");
      opt.value = file.name;
      opt.textContent = `📂 ${file.name} (Uploaded)`;
      dropdown.prepend(opt);
      dropdown.value = file.name;

      _applyLoadedSaveData(data, file.name);
    } catch (err) {
      console.error("Manual load error:", err);
      setStatus("Failed to load file: " + err);
    }
  };
  reader.readAsDataURL(file);
}

function _applyLoadedSaveData(data, displayPath) {
  CURRENT_SAVE = data;
  CURRENT_FILE_PATH = data.file_path || displayPath;
  if (data.notice) renderSameSaveNotice(data.notice);
  INITIAL_CONFIDANT_RANKS = {};
  Object.entries(data.confidants || {}).forEach(([arc, c]) => {
    INITIAL_CONFIDANT_RANKS[arc] = c.rank || 0;
  });

  // Populate Active Inventory from Save — prefer normalized payload (S1)
  INVENTORY_NORMALIZED = data.inventory_normalized || null;
  INVENTORY_ITEM_COUNTS = {};
  if (INVENTORY_NORMALIZED && (INVENTORY_NORMALIZED.stacks || INVENTORY_NORMALIZED.owned_gear)) {
    Object.entries(INVENTORY_NORMALIZED.stacks || {}).forEach(([k, qty]) => {
      const id = parseInt(k);
      if (id > 0 && qty > 0) INVENTORY_ITEM_COUNTS[id] = Math.min(99, parseInt(qty));
    });
    Object.entries(INVENTORY_NORMALIZED.owned_gear || {}).forEach(([k, owned]) => {
      const id = parseInt(k);
      if (id > 0 && owned) INVENTORY_ITEM_COUNTS[id] = 1;
    });
    KEY_ITEM_UNLOCKED = false;
    if (INVENTORY_NORMALIZED.conflicts && INVENTORY_NORMALIZED.conflicts.length > 0) {
      console.warn("Inventory conflicts (count_region wins):", INVENTORY_NORMALIZED.conflicts);
      setStatus(`⚠ ${INVENTORY_NORMALIZED.conflicts.length} conflict(s) — count_region canonical.`);
    }
    if (INVENTORY_NORMALIZED.mirror_mismatches && INVENTORY_NORMALIZED.mirror_mismatches.length > 0) {
      console.warn("Mirror mismatches:", INVENTORY_NORMALIZED.mirror_mismatches);
      const descEl = document.getElementById("activeItemDescText");
      if (descEl) descEl.textContent = `⚠ Mirror mismatch detected — will be healed on save (primary wins).`;
    }
  } else {
    (data.inventory || []).forEach(entry => {
      if (entry.item_id > 0 && entry.quantity > 0) {
        INVENTORY_ITEM_COUNTS[entry.item_id] = entry.quantity;
      }
    });
  }

  STAGED_DIRTY.clear();
  window.__INVENTORY_BASELINE = JSON.stringify(INVENTORY_ITEM_COUNTS);
  refreshStagedBadge();
  renderSaveData();
  refreshBackups();
  updateIntegrityBadge(data.integrity);
  setStatus(`✔ Save loaded: ${displayPath.split("\\").pop()} (${data.header.day}) | Ready.`);
}

// Same-save soft notice (2026-08-16): one-line banner, auto-dismissed.
function renderSameSaveNotice(text) {
  const existing = document.getElementById("sameSaveNotice");
  if (existing) existing.remove();
  const banner = document.createElement("div");
  banner.id = "sameSaveNotice";
  banner.textContent = "⚠ " + text;
  banner.style.cssText = `
    position: fixed; top: 14px; left: 50%; transform: translateX(-50%);
    background: #3A2E1B; color: #FFD54F; border: 1px solid #FFD54F;
    padding: 10px 20px; border-radius: 6px; z-index: 9999;
    font-family: var(--font-p5); font-size: 13px; font-weight: 700;
    box-shadow: 0 4px 18px rgba(0,0,0,.5);
  `;
  document.body.appendChild(banner);
  setTimeout(() => {
    const el = document.getElementById("sameSaveNotice");
    if (el) el.remove();
  }, 8000);
}

// Render All Save Data
function renderSaveData() {
  if (!CURRENT_SAVE) return;

  // Header & Top Strip
  document.getElementById("inputFname").value = CURRENT_SAVE.header.fname || "";
  document.getElementById("inputLname").value = CURRENT_SAVE.header.lname || "";
  document.getElementById("inputGroupName").value = CURRENT_SAVE.header.group_name || "";
  document.getElementById("inputMoney").value = CURRENT_SAVE.header.money || 0;

  document.getElementById("topDayText").textContent = CURRENT_SAVE.header.day || "Unknown";
  document.getElementById("topPlaytimeText").textContent = CURRENT_SAVE.header.playtime || "Unknown";
  document.getElementById("topMoneyText").textContent = `¥${(CURRENT_SAVE.header.money || 0).toLocaleString()}`;

  // Social Stats
  renderSocialStats();

  // Party & Personas
  renderPartySelector();
  renderActiveMember();
  renderStockChips();

  // Confidants & Inventory
  renderConfidants();
  renderInventoryViews();

  // Compendium
  COMPENDIUM_DATA = CURRENT_SAVE.compendium || null;
  UNLOCK_COMPENDIUM_FLAG = false;
  renderCompendium();
}

// Social Stats Tooltips & Gating Reference
const SOCIAL_STAT_UNLOCKS = {
  Knowledge: [
    "Rank 1: Shujin Freshman Baseline",
    "Rank 2: Pass mid-term pop quizzes",
    "Rank 3: Unlock Hifumi Togo (Star) Shogi lessons",
    "Rank 4: Top 10 Midterm Exam placement",
    "Rank 5: 🔓 Unlocks Makoto Niijima (Priestess) Rank 6+ & Ace Exams"
  ],
  Guts: [
    "Rank 1: Milquetoast Baseline",
    "Rank 2: 🔓 Unlocks Dr. Tae Takemi (Death) Clinical Trials",
    "Rank 3: 🔓 Unlocks Sadayo Kawakami (Temperance) & Munehisa Iwai (Hanged)",
    "Rank 4: Unlock Big Bang Burger Captain Challenge",
    "Rank 5: 🔓 Unlocks Sadayo Kawakami (Temperance) Rank 8+ & Munehisa Iwai Max"
  ],
  Proficiency: [
    "Rank 1: Bumbling Baseline",
    "Rank 2: Craft basic lockpicks & infiltration tools",
    "Rank 3: Unlock Beef Bowl Shop Part-Time Job",
    "Rank 4: 🔓 Unlocks Sojiro Sakura (Hierophant) Rank 7+ Curry Master",
    "Rank 5: 🔓 Unlocks Haru Okumura (Empress) Rank 2+ & 100% Infiltration Tool Crafts"
  ],
  Kindness: [
    "Rank 1: Inoffensive Baseline",
    "Rank 2: 🔓 Unlocks Ann Takamaki (Lovers) Rank 2+",
    "Rank 3: Unlock Crossroads Bar Job & Plant Nutrition",
    "Rank 4: Unlock Sojiro Sakura (Hierophant) Rank 6",
    "Rank 5: 🔓 Unlocks Futaba Sakura (Hermit) Rank 2+"
  ],
  Charm: [
    "Rank 1: Existent Baseline",
    "Rank 2: Unlock Maid Cafe specials",
    "Rank 3: 🔓 Unlocks Makoto Niijima (Priestess) & Hifumi Togo (Star)",
    "Rank 4: 🔓 Unlocks Tae Takemi (Death) Rank 8+",
    "Rank 5: 🔓 Unlocks Makoto Niijima (Priestess) Rank 10 Max & Maid Slacking"
  ]
};

// Social Stats (Interactive 1-5 Nodes with Gating Tooltips)
function renderSocialStats() {
  const container = document.getElementById("socialStatsList");
  container.innerHTML = "";
  const stats = ["Knowledge", "Charm", "Proficiency", "Kindness", "Guts"];

  stats.forEach((s) => {
    const row = document.createElement("div");
    row.className = "stat-item";
    row.style.flexDirection = "column";
    row.style.alignItems = "stretch";
    row.style.gap = "6px";

    const curRank = CURRENT_SAVE.social_stats[s]?.rank || 5;
    const unlockHint = SOCIAL_STAT_UNLOCKS[s][curRank - 1] || "Social rank maxed";

    let nodesHtml = "";
    for (let r = 1; r <= 5; r++) {
      nodesHtml += `<div class="star-node ${r <= curRank ? 'active' : ''}" onclick="setSocialRank('${s}', ${r})">★ ${r}</div>`;
    }

    row.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div class="stat-title">${s} (Rank ${curRank})</div>
        <div class="star-rank-box">${nodesHtml}</div>
      </div>
      <div style="font-size:11px; color:#A0A0B5; background:rgba(0,0,0,0.3); padding:4px 8px; border-radius:3px; border-left:2px solid var(--p5-crimson);">
        ${unlockHint}
      </div>
    `;
    container.appendChild(row);
  });
}

function setSocialRank(stat, rank) {
  if (!CURRENT_SAVE) return;
  if (!CURRENT_SAVE.social_stats[stat]) CURRENT_SAVE.social_stats[stat] = {};
  CURRENT_SAVE.social_stats[stat].rank = rank;
  renderSocialStats();
}

function maxAllSocialStats() {
  if (!CURRENT_SAVE) return;
  ["Knowledge", "Charm", "Proficiency", "Kindness", "Guts"].forEach((s) => {
    if (!CURRENT_SAVE.social_stats[s]) CURRENT_SAVE.social_stats[s] = {};
    CURRENT_SAVE.social_stats[s].rank = 5;
  });
  renderSocialStats();
}

function setMaxYen() {
  document.getElementById("inputMoney").value = 9999999;
  if (CURRENT_SAVE) CURRENT_SAVE.header.money = 9999999;
  document.getElementById("topMoneyText").textContent = "¥9,999,999";
}

// Party & Personas
function renderPartySelector() {
  const select = document.getElementById("partyMemberSelect");
  if (select) select.innerHTML = "";

  const ribbon = document.getElementById("phantomThiefRibbon");
  if (ribbon) ribbon.innerHTML = "";

  (CURRENT_SAVE.party || []).forEach((m, idx) => {
    if (select) {
      const opt = document.createElement("option");
      opt.value = idx;
      opt.textContent = `${m.name} (LV ${m.level})`;
      select.appendChild(opt);
    }

    if (ribbon) {
      const placard = document.createElement("div");
      placard.className = `thief-placard ${idx === ACTIVE_MEMBER_INDEX ? 'active' : ''}`;
      placard.onclick = () => {
        if (typeof P5Audio !== "undefined") P5Audio.playSwitch();
        selectPartyMemberByIndex(idx);
      };

      placard.innerHTML = `
        <span class="thief-placard-slot">#${m.slot}</span>
        <span class="thief-placard-name">${m.name.toUpperCase()}</span>
        <span style="font-size:11px; font-weight:800; opacity:0.8;">LV ${m.level || 1}</span>
      `;
      ribbon.appendChild(placard);
    }
  });
}

function selectPartyMemberByIndex(idx) {
  const select = document.getElementById("partyMemberSelect");
  if (select) {
    select.value = idx;
  }
  ACTIVE_MEMBER_INDEX = idx;
  renderActiveMember();
  renderPartySelector(); // re-sync active state on placards
}

function renderActiveMember() {
  const select = document.getElementById("partyMemberSelect");
  if (select && select.value !== "") {
    ACTIVE_MEMBER_INDEX = parseInt(select.value) || 0;
  }
  const member = CURRENT_SAVE?.party ? CURRENT_SAVE.party[ACTIVE_MEMBER_INDEX] : null;
  if (!member) return;

  const isJoker = member.slot === 0;

  const charNameEl = document.getElementById("characterStageName");
  if (charNameEl) charNameEl.textContent = member.name.toUpperCase();

  document.getElementById("activeMemberBadge").textContent = `SLOT ${member.slot} // ${member.name.toUpperCase()}`;
  document.getElementById("memberLevel").value = member.level || 1;
  document.getElementById("memberHP").value = member.hp || 100;
  document.getElementById("memberSP").value = member.sp || 50;

  // Dynamic Party Standee Image Mapping
  const standeeImg = document.getElementById("partyMemberStandeeImg");
  if (standeeImg) {
    const nameKey = (member.name || "joker").toLowerCase().replace(/[^a-z]/g, "");
    let standeeFile = "joker.png";
    if (nameKey.includes("morgana") || nameKey.includes("mona")) standeeFile = "morgana.png";
    else if (nameKey.includes("ryuji") || nameKey.includes("skull")) standeeFile = "ryuji.png";
    else if (nameKey.includes("ann") || nameKey.includes("panther")) standeeFile = "ann.png";
    else if (nameKey.includes("yusuke") || nameKey.includes("fox")) standeeFile = "yusuke.png";
    else if (nameKey.includes("makoto") || nameKey.includes("queen")) standeeFile = "makoto.png";
    else if (nameKey.includes("futaba") || nameKey.includes("navi")) standeeFile = "futaba.png";
    else if (nameKey.includes("haru") || nameKey.includes("noir")) standeeFile = "haru.png";
    else if (nameKey.includes("akechi") || nameKey.includes("crow")) standeeFile = "akechi.png";
    else if (nameKey.includes("kasumi") || nameKey.includes("sumire") || nameKey.includes("violet")) standeeFile = "kasumi.png";
    else if (isJoker) standeeFile = "joker.png";
    standeeImg.src = `/assets/party/${standeeFile}?v=20260816e`;
  }

  // Configure Deck header and stock chips visibility
  const deckHeader = document.getElementById("personaDeckHeader");
  const stockChipsBox = document.getElementById("stockChipsContainer");
  const stockBadge = document.getElementById("stockSlotBadge");

  const evoBox = document.getElementById("partyEvolutionContainer");
  const evoSelect = document.getElementById("partyEvolutionSelect");
  const evoBadge = document.getElementById("partyEvolutionTierBadge");

  if (isJoker) {
    if (deckHeader) deckHeader.textContent = "🎭 EQUIPPED PERSONA & MOVESET";
    if (stockChipsBox) stockChipsBox.style.display = "flex";
    if (stockBadge) stockBadge.style.display = "inline";
    if (evoBox) evoBox.style.display = "none";
    const lockNote = document.getElementById("personaLockNote");
    if (lockNote) lockNote.style.display = "none";
    document.getElementById("personaSelect").disabled = false;
    renderStockChips();
    loadPersonaIntoDeck(ACTIVE_STOCK_SLOT);
  } else {
    if (deckHeader) deckHeader.textContent = `🎭 ${member.name.toUpperCase()}'S PERSONA`;
    if (stockChipsBox) stockChipsBox.style.display = "none";
    if (stockBadge) stockBadge.style.display = "none";
    if (evoBox) evoBox.style.display = "block";

    const pers = member.persona || {};
    const personaSelect = document.getElementById("personaSelect");
    personaSelect.value = pers.persona_id || 1;
    personaSelect.disabled = true;

    // Detect current evolution tier from persona_id
    const pid = pers.persona_id || 0;
    const EVOS = {
      1: { 0x00CA: 1, 0x00D4: 2, 0x00F2: 3 }, // Ryuji
      2: { 0x00CB: 1, 0x00D5: 2, 0x00F3: 3 }, // Morgana
      3: { 0x00CC: 1, 0x00E9: 2, 0x00F4: 3 }, // Ann
      4: { 0x00CD: 1, 0x00EA: 2, 0x00F5: 3 }, // Yusuke
      5: { 0x00CE: 1, 0x00EB: 2, 0x00F6: 3 }, // Makoto
      6: { 0x00CF: 1, 0x00EC: 2, 0x00F7: 3 }, // Haru
      7: { 0x00D0: 1, 0x00ED: 2, 0x00F8: 3 }, // Futaba
      8: { 0x00D1: 1, 0x00D2: 2, 0x00F9: 3 }, // Akechi
      9: { 0x00F0: 1, 0x00F1: 2, 0x00FA: 3 }, // Kasumi
    };
    const curTier = (EVOS[member.slot] && EVOS[member.slot][pid]) ? EVOS[member.slot][pid] : 1;
    if (evoSelect) evoSelect.value = curTier;
    if (evoBadge) {
      evoBadge.textContent = curTier === 1 ? "TIER 1 (BASE)" : (curTier === 2 ? "TIER 2 (AWAKENED)" : "TIER 3 (ROYAL)");
      evoBadge.style.background = curTier === 1 ? "#00E5FF" : (curTier === 2 ? "#FFD54F" : "#E040FB");
    }

    document.getElementById("personaLevel").value = pers.level || 1;
    document.getElementById("personaTraitSelect").value = pers.trait_id || 0;

    const lockNote = document.getElementById("personaLockNote");
    if (lockNote) {
      lockNote.style.display = "block";
      lockNote.textContent = `★ ${member.name}'s identity is locked to their canonical line — switch evolution tiers above.`;
    }

    const st = pers.stats || [10, 10, 10, 10, 10];
    document.getElementById("stat_st").value = st[0] || 10;
    document.getElementById("stat_ma").value = st[1] || 10;
    document.getElementById("stat_en").value = st[2] || 10;
    document.getElementById("stat_ag").value = st[3] || 10;
    document.getElementById("stat_lu").value = st[4] || 10;

    renderSkillsGrid(pers.skills || [0,0,0,0,0,0,0,0]);
    renderElementalAffinities(pers.persona_id || 1, pers.skills || [0,0,0,0,0,0,0,0]);

    // Update Velvet Room Persona Showcase for locked teammate
    const portraitEl = document.getElementById("velvetPersonaPortrait");
    if (portraitEl) {
      const pid = pers.persona_id || 1;
      portraitEl.src = `/assets/personas/${pid}.png?v=20260816`;
      portraitEl.style.display = "block";
    }
    const idBadge = document.getElementById("velvetPersonaIdBadge");
    if (idBadge) {
      const pid = pers.persona_id || 1;
      idBadge.textContent = `ID: 0x${pid.toString(16).toUpperCase().padStart(3, '0')} (${pid})`;
    }
  }
}

function onPartyEvolutionChange() {
  const member = CURRENT_SAVE?.party ? CURRENT_SAVE.party[ACTIVE_MEMBER_INDEX] : null;
  if (!member || member.slot === 0) return;

  const select = document.getElementById("partyEvolutionSelect");
  const tier = parseInt(select.value) || 1;

  const EVOS = {
    1: { 1: 0x00CA, 2: 0x00D4, 3: 0x00F2 }, // Ryuji
    2: { 1: 0x00CB, 2: 0x00D5, 3: 0x00F3 }, // Morgana
    3: { 1: 0x00CC, 2: 0x00E9, 3: 0x00F4 }, // Ann
    4: { 1: 0x00CD, 2: 0x00EA, 3: 0x00F5 }, // Yusuke
    5: { 1: 0x00CE, 2: 0x00EB, 3: 0x00F6 }, // Makoto
    6: { 1: 0x00CF, 2: 0x00EC, 3: 0x00F7 }, // Haru
    7: { 1: 0x00D0, 2: 0x00ED, 3: 0x00F8 }, // Futaba
    8: { 1: 0x00D1, 2: 0x00D2, 3: 0x00F9 }, // Akechi
    9: { 1: 0x00F0, 2: 0x00F1, 3: 0x00FA }, // Kasumi
  };

  const newPid = (EVOS[member.slot] && EVOS[member.slot][tier]) ? EVOS[member.slot][tier] : 0;
  if (newPid > 0) {
    if (!member.persona) member.persona = {};
    member.persona.persona_id = newPid;

    // Re-render UI
    const personaSelect = document.getElementById("personaSelect");
    if (personaSelect) personaSelect.value = newPid;

    const evoBadge = document.getElementById("partyEvolutionTierBadge");
    if (evoBadge) {
      evoBadge.textContent = tier === 1 ? "TIER 1 (BASE)" : (tier === 2 ? "TIER 2 (AWAKENED)" : "TIER 3 (ROYAL)");
      evoBadge.style.background = tier === 1 ? "#00E5FF" : (tier === 2 ? "#FFD54F" : "#E040FB");
    }

    const portraitEl = document.getElementById("velvetPersonaPortrait");
    if (portraitEl) portraitEl.src = `/assets/personas/${newPid}.png?v=20260816`;

    const idBadge = document.getElementById("velvetPersonaIdBadge");
    if (idBadge) idBadge.textContent = `ID: 0x${newPid.toString(16).toUpperCase().padStart(3, '0')} (${newPid})`;

    renderElementalAffinities(newPid, member.persona.skills || [0,0,0,0,0,0,0,0]);
    setStatus(`★ ${member.name}'s persona evolved to Tier ${tier} (0x${newPid.toString(16).toUpperCase()}) — armed for save.`);
  }
}

let ACTIVE_STOCK_SLOT = 0;

function renderStockChips() {
  const container = document.getElementById("stockChipsContainer");
  if (!container) return;
  container.innerHTML = "";

  const stock = CURRENT_SAVE?.joker_stock || [];
  for (let k = 0; k < 12; k++) {
    const entry = stock[k] || { slot: k, persona: null, level: 0, empty: true };
    const chip = document.createElement("button");
    const isActive = k === ACTIVE_STOCK_SLOT;
    chip.className = `filter-pill ${isActive ? 'active' : ''}`;
    chip.style.fontSize = "10px";
    chip.style.padding = "4px 8px";
    
    const label = entry.empty || !entry.persona ? `Slot ${k} (Empty)` : `Slot ${k}: ${entry.persona}`;
    chip.innerHTML = `${k === 0 ? '👑 ' : ''}${label}`;
    chip.onclick = () => selectStockSlot(k);
    container.appendChild(chip);
  }
}

function selectStockSlot(slotIdx) {
  ACTIVE_STOCK_SLOT = slotIdx;
  const stockBadge = document.getElementById("stockSlotBadge");
  if (stockBadge) stockBadge.textContent = slotIdx === 0 ? "SLOT 0 (EQUIPPED)" : `STOCK SLOT ${slotIdx}`;
  renderStockChips();
  loadPersonaIntoDeck(slotIdx);
}

function loadPersonaIntoDeck(stockIdx) {
  const stock = CURRENT_SAVE?.joker_stock || [];
  const entry = stock[stockIdx] || { persona_id: 0, level: 0, trait_id: 0, stats: [0,0,0,0,0], skills: [0,0,0,0,0,0,0,0], empty: true };

  const isEmpty = entry.empty || !entry.persona_id || entry.persona_id === 0;

  if (isEmpty) {
    document.getElementById("personaSelect").value = 0;
    document.getElementById("personaLevel").value = 0;
    document.getElementById("personaTraitSelect").value = 0;

    document.getElementById("stat_st").value = 0;
    document.getElementById("stat_ma").value = 0;
    document.getElementById("stat_en").value = 0;
    document.getElementById("stat_ag").value = 0;
    document.getElementById("stat_lu").value = 0;

    renderSkillsGrid([0,0,0,0,0,0,0,0]);
    renderElementalAffinities(0, [0,0,0,0,0,0,0,0]);
  } else {
    document.getElementById("personaSelect").value = entry.persona_id;
    document.getElementById("personaLevel").value = entry.level || 1;
    document.getElementById("personaTraitSelect").value = entry.trait_id || 0;

    const st = entry.stats || [10, 10, 10, 10, 10];
    document.getElementById("stat_st").value = st[0] || 10;
    document.getElementById("stat_ma").value = st[1] || 10;
    document.getElementById("stat_en").value = st[2] || 10;
    document.getElementById("stat_ag").value = st[3] || 10;
    document.getElementById("stat_lu").value = st[4] || 10;

    renderSkillsGrid(entry.skills || [0,0,0,0,0,0,0,0]);
    renderElementalAffinities(entry.persona_id, entry.skills || [0,0,0,0,0,0,0,0]);
  }

  const portraitEl = document.getElementById("velvetPersonaPortrait");
  if (portraitEl) {
    if (!isEmpty && entry.persona_id > 0) {
      portraitEl.src = `/assets/personas/${entry.persona_id}.png?v=20260816e`;
      portraitEl.style.display = "block";
    } else {
      portraitEl.style.display = "none";
    }
  }
}

function onPersonaSelectChange() {
  const pid = parseInt(document.getElementById("personaSelect").value) || 0;
  const portraitEl = document.getElementById("velvetPersonaPortrait");
  if (portraitEl) {
    if (pid > 0) {
      portraitEl.src = `/assets/personas/${pid}.png?v=20260816e`;
      portraitEl.style.display = "block";
    } else {
      portraitEl.style.display = "none";
    }
  }
  saveCurrentDeckToActiveTarget();
}

function saveCurrentDeckToActiveTarget() {
  if (!CURRENT_SAVE) return;

  const pid = parseInt(document.getElementById("personaSelect").value) || 0;
  const isEmpty = pid === 0;
  const pName = isEmpty ? "Empty Slot" : (DB.personas.find(p => p.id === pid)?.name || "Persona");
  const lvl = isEmpty ? 0 : (parseInt(document.getElementById("personaLevel").value) || 1);
  const trait = isEmpty ? 0 : (parseInt(document.getElementById("personaTraitSelect").value) || 0);
  const stats = isEmpty ? [0,0,0,0,0] : [
    parseInt(document.getElementById("stat_st").value) || 10,
    parseInt(document.getElementById("stat_ma").value) || 10,
    parseInt(document.getElementById("stat_en").value) || 10,
    parseInt(document.getElementById("stat_ag").value) || 10,
    parseInt(document.getElementById("stat_lu").value) || 10
  ];
  const skills = [];
  for (let i = 0; i < 8; i++) {
    const el = document.getElementById(`skillSlot_${i}`);
    skills.push(el ? parseInt(el.value) || 0 : 0);
  }

  const member = CURRENT_SAVE.party[ACTIVE_MEMBER_INDEX];
  if (!member) return;

  if (member.slot === 0) {
    // Joker: save to current stock slot
    if (!CURRENT_SAVE.joker_stock) CURRENT_SAVE.joker_stock = [];
    while (CURRENT_SAVE.joker_stock.length < 12) {
      CURRENT_SAVE.joker_stock.push({ slot: CURRENT_SAVE.joker_stock.length, empty: true });
    }

    CURRENT_SAVE.joker_stock[ACTIVE_STOCK_SLOT] = {
      slot: ACTIVE_STOCK_SLOT,
      persona_id: pid,
      persona: isEmpty ? null : pName,
      level: lvl,
      trait_id: trait,
      stats: stats,
      skills: skills,
      empty: isEmpty,
      flags: isEmpty ? 0 : 1
    };

    if (ACTIVE_STOCK_SLOT === 0 && !isEmpty) {
      member.persona = CURRENT_SAVE.joker_stock[0];
    }
    renderStockChips();
  } else {
    // Teammate: save directly to their persona
    member.persona = {
      persona_id: pid,
      persona: pName,
      level: lvl,
      trait_id: trait,
      stats: stats,
      skills: skills,
      flags: isEmpty ? 0 : 1
    };
  }

  renderElementalAffinities(pid, skills);
}

function maxPersonaStats() {
  document.getElementById("stat_st").value = 99;
  document.getElementById("stat_ma").value = 99;
  document.getElementById("stat_en").value = 99;
  document.getElementById("stat_ag").value = 99;
  document.getElementById("stat_lu").value = 99;
  saveCurrentDeckToActiveTarget();
}

function healActiveMember() {
  document.getElementById("memberHP").value = 999;
  document.getElementById("memberSP").value = 999;
  if (CURRENT_SAVE && CURRENT_SAVE.party && CURRENT_SAVE.party[ACTIVE_MEMBER_INDEX]) {
    CURRENT_SAVE.party[ACTIVE_MEMBER_INDEX].hp = 999;
    CURRENT_SAVE.party[ACTIVE_MEMBER_INDEX].sp = 999;
  }
}

function maxLevelActiveMember() {
  document.getElementById("memberLevel").value = 99;
  document.getElementById("personaLevel").value = 99;
  if (CURRENT_SAVE && CURRENT_SAVE.party && CURRENT_SAVE.party[ACTIVE_MEMBER_INDEX]) {
    CURRENT_SAVE.party[ACTIVE_MEMBER_INDEX].level = 99;
  }
  saveCurrentDeckToActiveTarget();
}

function renderSkillsGrid(skills) {
  const container = document.getElementById("skillsGrid");
  if (!container) return;
  container.innerHTML = "";

  for (let i = 0; i < 8; i++) {
    const curSkillId = (skills && skills[i]) ? (typeof skills[i] === 'object' ? skills[i].id : skills[i]) : 0;
    const select = document.createElement("select");
    select.className = "p5-select";
    select.id = `skillSlot_${i}`;
    select.style.fontSize = "12px";
    select.onchange = () => saveCurrentDeckToActiveTarget();

    const EL_NAMES = {0:"Phys",1:"Gun",2:"Fire",3:"Ice",4:"Elec",5:"Wind",6:"Psy",7:"Nuke",8:"Bless",9:"Curse",10:"Almighty"};
    let opts = `<option value="0">-- (Empty Skill) --</option>`;
    (DB.skills || []).forEach((sk) => {
      const meta = (DB.skill_meta || {})[sk.id];
      let tag = "";
      if (meta) {
        const el = EL_NAMES[meta.element] || (meta.element === 255 ? "—" : `E${meta.element}`);
        const cost = meta.cost > 0 ? (meta.costtype === 1 ? ` ${meta.cost}% HP` : meta.costtype === 2 ? ` ${meta.cost} SP` : "") : "";
        if (el !== "—" || cost) tag = ` [${el}${cost}]`;
      }
      opts += `<option value="${sk.id}" ${sk.id === curSkillId ? 'selected' : ''}>${sk.name}${tag}</option>`;
    });
    select.innerHTML = opts;
    container.appendChild(select);
  }
}

function populatePersonaDropdown() {
  const select = document.getElementById("personaSelect");
  if (!select) return;
  select.innerHTML = `<option value="0">-- (Empty Slot) --</option>`;
  (DB.personas || []).forEach((p) => {
    const opt = document.createElement("option");
    opt.value = p.id;
    opt.textContent = `${p.name} (ID: ${p.id})`;
    select.appendChild(opt);
  });
}

function populateTraitDropdown() {
  const select = document.getElementById("personaTraitSelect");
  if (!select) return;
  select.innerHTML = `<option value="0">-- None / Default --</option>`;
  (DB.traits || []).forEach((t) => {
    const opt = document.createElement("option");
    opt.value = t.id;
    opt.textContent = t.name;
    select.appendChild(opt);
  });
}

// Elemental Affinities & Passive Calculation Engine
const ELEMENT_CONFIG = [
  { key: "phys", label: "Phys", icon: "⚔️" },
  { key: "gun", label: "Gun", icon: "🔫" },
  { key: "fire", label: "Fire", icon: "🔥" },
  { key: "ice", label: "Ice", icon: "❄️" },
  { key: "elec", label: "Elec", icon: "⚡" },
  { key: "wind", label: "Wind", icon: "🌀" },
  { key: "psy", label: "Psy", icon: "🔮" },
  { key: "nuke", label: "Nuke", icon: "☢️" },
  { key: "bless", label: "Bless", icon: "✨" },
  { key: "curse", label: "Curse", icon: "💀" }
];

function renderElementalAffinities(personaId, skillsList) {
  const grid = document.getElementById("elementalAffinitiesGrid");
  if (!grid) return;
  grid.innerHTML = "";

  if (!personaId || personaId === 0) {
    const headerName = document.getElementById("affinityPersonaName");
    if (headerName) headerName.textContent = `EMPTY PERSONA SLOT`;
    ELEMENT_CONFIG.forEach(elem => {
      const badge = document.createElement("div");
      badge.className = "elem-badge";
      badge.innerHTML = `
        <span class="elem-icon">${elem.icon}</span>
        <span class="elem-lbl">${elem.label}</span>
        <span class="elem-aff neu">-</span>
      `;
      grid.appendChild(badge);
    });
    return;
  }

  const pObj = DB.personas.find(p => p.id === personaId);
  const pName = pObj?.name || "Persona";
  
  const baseAff = P5R_BASE_AFFINITIES[personaId] || P5R_BASE_AFFINITIES[pName] || { phys: "-", gun: "-", fire: "-", ice: "-", elec: "-", wind: "-", psy: "-", nuke: "-", bless: "-", curse: "-" };

  const headerName = document.getElementById("affinityPersonaName");
  if (headerName) headerName.textContent = `${pName.toUpperCase()} RESISTANCES`;

  // Extract equipped skill IDs
  const skillIds = (skillsList || []).map(s => typeof s === "object" ? s.id : parseInt(s) || 0);

  // Compute final effective affinity per element (Passives take priority)
  ELEMENT_CONFIG.forEach(elem => {
    let effective = baseAff[elem.key] || "-";

    // Check passives
    skillIds.forEach(skId => {
      const passive = PASSIVE_AFFINITY_SKILLS[skId];
      if (passive && passive.elem === elem.key) {
        effective = passive.type;
      }
    });

    const badge = document.createElement("div");
    badge.className = "elem-badge";
    
    let affClass = "neu";
    if (effective === "Wk") affClass = "wk";
    else if (effective === "Str") affClass = "str";
    else if (effective === "Nul") affClass = "nul";
    else if (effective === "Rpl") affClass = "rpl";
    else if (effective === "Dr") affClass = "dr";

    badge.innerHTML = `
      <span class="elem-icon">${elem.icon}</span>
      <span class="elem-lbl">${elem.label}</span>
      <span class="elem-aff ${affClass}">${effective}</span>
    `;
    grid.appendChild(badge);
  });
}

// Calendar-aware Date comparison helper (e.g. "6/15" vs "10/30")
function isStoryUnlocked(currentDayStr, unlockDateStr) {
  if (!currentDayStr || !unlockDateStr) return true;
  const parseMDay = (s) => {
    const m = s.match(/(\d+)\/(\d+)/);
    return m ? { month: parseInt(m[1]), day: parseInt(m[2]) } : null;
  };
  const cur = parseMDay(currentDayStr);
  const unl = parseMDay(unlockDateStr);
  if (!cur || !unl) return true;

  // In P5R, calendar runs April (Month 4) to March (Month 3 next year)
  const normCur = (cur.month < 4 ? cur.month + 12 : cur.month) * 100 + cur.day;
  const normUnl = (unl.month < 4 ? unl.month + 12 : unl.month) * 100 + unl.day;
  return normCur >= normUnl;
}

function toggleUnsafeConfidants(checkbox) {
  ALLOW_UNSAFE_CONFIDANTS = checkbox.checked;
  renderConfidants();
}

function filterConfidants(category, btn) {
  CURRENT_CONFIDANT_FILTER = category;
  document.querySelectorAll(".confidant-filter-bar .filter-pill").forEach((el) => el.classList.remove("active"));
  if (btn) btn.classList.add("active");
  renderConfidants();
}

function updateFilterCounts() {
  const profiles = DB.confidant_profiles || {};
  let totalVisible = 0;

  Object.entries(CURRENT_SAVE?.confidants || {}).forEach(([arcana, info]) => {
    const isMet = info.rank > 0;
    if (isMet || ALLOW_UNSAFE_CONFIDANTS) {
      totalVisible++;
    }
  });

  const allPill = document.getElementById("pillAll");
  if (allPill) allPill.textContent = `Met Confidants (${totalVisible})`;
}

// Spoiler-Safe Narrative Lore & Strategy Database
const CONFIDANT_LORE = {
  Fool: {
    stat_req: null,
    deadline: null,
    milestone: "Progresses naturally through pivotal campaign story milestones.",
    awakening: "Ultimate Arcana Fusion: Vishnu (Magician of Chaos).",
    keepsake: "Infinite Wild Card Affinity & Max Persona Deck Stock size carryover."
  },
  Magician: {
    stat_req: null,
    deadline: "Auto-advances through Palace infiltration milestones.",
    milestone: "Second Awakening transforms Zorro into Mercurius.",
    awakening: "Mercurius (Grants battle-wide revive and dodge skills).",
    keepsake: "Morgana's Bandana (Unlocks all Infiltration Tool crafts from Day 1 in NG+)."
  },
  Priestess: {
    stat_req: { Knowledge: 3, Charm: 5 },
    deadline: null,
    milestone: "Rank 9 holds the decision between Romantic Partner and Close Friend.",
    awakening: "Johanna evolves into Anat (Shadow Calc reveals full enemy item drops and weaknesses).",
    keepsake: "Buchimaru Badge (Instantly reveals shadow resistances and drops in NG+)."
  },
  Empress: {
    stat_req: { Proficiency: 5 },
    deadline: "Available late autumn (10/30). Requires max Proficiency to initiate.",
    milestone: "Rank 9 holds the decision between Romantic Partner and Close Friend.",
    awakening: "Milady evolves into Astarte (Unlocks Life Wall and SP Vegetable Farming).",
    keepsake: "Dyed Cloth (Maximizes SP recovery from harvested rooftop vegetables in NG+)."
  },
  Emperor: {
    stat_req: { Proficiency: 4 },
    deadline: null,
    milestone: "Deepens Joker's artistic camaraderie and resolve with Yusuke.",
    awakening: "Goemon evolves into Kamu Susano-o (Grants party-wide evasion buffs).",
    keepsake: "Painting of Hope (Allows instant skill card duplication and blank card painting in NG+)."
  },
  Hierophant: {
    stat_req: { Kindness: 4 },
    deadline: "Rank 4 pause until summer (8/21). Requires Kindness Lv 4 for Rank 7+.",
    milestone: "Solidifies Joker's bond with Sojiro as his legal guardian and mentor.",
    awakening: "Ultimate Arcana Fusion: Kohryu (Dragon of Harmony).",
    keepsake: "Recipe Notes (Unlocks Master Curry and Master Coffee brewing from Day 1 in NG+)."
  },
  Lovers: {
    stat_req: { Kindness: 2 },
    deadline: null,
    milestone: "Rank 9 holds the decision between Romantic Partner and Close Friend.",
    awakening: "Carmen evolves into Hecate (High Energy party magic buff and magic evasion).",
    keepsake: "Fashion Magazine (Grants Crocodile Tears and Girl Talk negotiation perks in NG+)."
  },
  Chariot: {
    stat_req: null,
    deadline: null,
    milestone: "Solidifies Ryuji's resolve and track team camaraderie.",
    awakening: "Captain Kidd evolves into Seiten Taisei (Immunity to lethal physical ambush hits).",
    keepsake: "Sports Watch (Unlocks Insta-Kill on lower-level Shadows while dashing in NG+)."
  },
  Justice: {
    stat_req: { Knowledge: 3, Charm: 4 },
    deadline: "11/17 (Crucial Cutoff: Must reach Rank 8 before mid-November).",
    milestone: "Reaching Rank 8 cements your rivalry bond, unlocking special narrative choices and epilogue scenes.",
    awakening: "Ultimate Arcana Fusion: Metatron (Herald of Order).",
    keepsake: "Duel Glove (Unlocks Detective Prince sleuth insights in NG+)."
  },
  Hermit: {
    stat_req: { Kindness: 4 },
    deadline: null,
    milestone: "Rank 9 holds the decision between Romantic Partner and Close Friend.",
    awakening: "Necronomicon evolves into Prometheus (Emergency Shift and Final Guard team shield).",
    keepsake: "Promised Note (Unlocks Treasure Skimmer and Position Hack hacks in NG+)."
  },
  Fortune: {
    stat_req: null,
    deadline: null,
    milestone: "Rank 9 holds the decision between Romantic Partner and Close Friend.",
    awakening: "Ultimate Arcana Fusion: Lakshmi (Goddess of Fortune).",
    keepsake: "Tarot Card (Unlocks Affinity, Money, and Celestial Fortune readings on Day 1 in NG+)."
  },
  Strength: {
    stat_req: null,
    deadline: "Advance via Persona Fusion Requests at the Velvet Room entrance.",
    milestone: "Deepens your rehabilitation trial under the Velvet Wardens.",
    awakening: "Ultimate Arcana Fusion: Zaou-Gongen (Lord of Discipline).",
    keepsake: "Cell Key (Allows summoning higher-level Personas beyond Joker's level via fee in NG+)."
  },
  Hanged: {
    stat_req: { Guts: 4 },
    deadline: null,
    milestone: "Unlocks untranslated custom weapon and gun modifications at Untouchable.",
    awakening: "Ultimate Arcana Fusion: Attis (Resurrective God).",
    keepsake: "Gecko Pin (Allows full custom firearm tuning and weapon discounts from Day 1 in NG+)."
  },
  "Hanged Man": {
    stat_req: { Guts: 4 },
    deadline: null,
    milestone: "Unlocks untranslated custom weapon and gun modifications at Untouchable.",
    awakening: "Ultimate Arcana Fusion: Attis (Resurrective God).",
    keepsake: "Gecko Pin (Allows full custom firearm tuning and weapon discounts from Day 1 in NG+)."
  },
  Death: {
    stat_req: { Guts: 2, Charm: 4 },
    deadline: null,
    milestone: "Rank 9 holds the decision between Romantic Partner and Close Friend.",
    awakening: "Ultimate Arcana Fusion: Alice (Queen of Hearts).",
    keepsake: "Doctor's Dog Tag (Unlocks 50% discount on SP Adhesives and Revival Medicines in NG+)."
  },
  Temperance: {
    stat_req: { Guts: 3 },
    deadline: "11/17 (Housework & school slack-off services pause during winter exam period).",
    milestone: "Rank 9 holds the decision between Romantic Partner and Close Friend.",
    awakening: "Ultimate Arcana Fusion: Ardha (Divine Synthesis).",
    keepsake: "Unlimited Free Time Pass (Allows summoning Kawakami for free massages on Day 1 in NG+)."
  },
  Devil: {
    stat_req: null,
    deadline: null,
    milestone: "Rank 9 holds the decision between Romantic Partner and Close Friend.",
    awakening: "Ultimate Arcana Fusion: Beelzebub (Lord of the Flies).",
    keepsake: "Interview Notes (Keeps Palace security alert levels at absolute zero in NG+)."
  },
  Tower: {
    stat_req: null,
    deadline: null,
    milestone: "Master high-level gun techniques under the King of Akihabara arcade.",
    awakening: "Ultimate Arcana Fusion: Mada (Intoxicating Titan).",
    keepsake: "Gun Controller (Unlocks Down Shot and Bullet Hail combat gun maneuvers in NG+)."
  },
  Star: {
    stat_req: { Knowledge: 3, Charm: 3 },
    deadline: null,
    milestone: "Rank 9 holds the decision between Romantic Partner and Close Friend.",
    awakening: "Ultimate Arcana Fusion: Lucifer (Morningstar).",
    keepsake: "Koma Piece (Unlocks mid-battle party member swapping and instant tactical escape in NG+)."
  },
  Moon: {
    stat_req: null,
    deadline: "Advances by completing Phan-Site Mementos requests.",
    milestone: "Deepens Phan-Site admin support across Shibuya.",
    awakening: "Ultimate Arcana Fusion: Sandalphon (Archangel of Melody).",
    keepsake: "Phan-Site Document (Grants backup party members 100% full combat EXP in NG+)."
  },
  Sun: {
    stat_req: null,
    deadline: "11/13 (Strict Cutoff: Campaign rallies terminate before election season).",
    milestone: "Master advanced speech extortion and smooth shadow negotiations.",
    awakening: "Ultimate Arcana Fusion: Asura (Lord of Fury).",
    keepsake: "Politician Sash (Allows recruiting shadows of higher level than Joker during hold-ups in NG+)."
  },
  Judgement: {
    stat_req: null,
    deadline: "Auto-advances through the interrogation narrative.",
    milestone: "Resolves the core investigation and prosecutorial interrogation.",
    awakening: "Ultimate Arcana Fusion: Satan (Great Adversary).",
    keepsake: "Prosecutor Badge (Carries master courtroom insight into NG+)."
  },
  Faith: {
    stat_req: null,
    deadline: "12/22 (Rank 5 Cap: First half must be completed before winter holidays).",
    milestone: "Rank 5 unlocks her winter story progression. Ranks 6–10 and Romance unlock in the Third Semester.",
    awakening: "Cendrillon evolves into Vanadis (Grants grappling ambush and critical combat perks).",
    keepsake: "Gymnast Ribbon (Unlocks grappling hook ambush on distant shadows from Day 1 in NG+)."
  },
  Councillor: {
    stat_req: null,
    deadline: "11/18 (CRITICAL CUTOFF: Must reach Rank 9 to unlock Third Semester & Royal True Ending).",
    milestone: "Reaching Rank 9 is the mandatory story prerequisite to unlock the Royal True Ending campaign.",
    awakening: "Ultimate Arcana Fusion: Futsunushi (Swordsman of Light).",
    keepsake: "Super Detox Treats (Grants automatic SP replenishment and status cures on Day 1 in NG+)."
  }
};

let ALL_CONFIDANT_INTEL_EXPANDED = false;

function toggleAllConfidantIntel() {
  ALL_CONFIDANT_INTEL_EXPANDED = !ALL_CONFIDANT_INTEL_EXPANDED;
  document.querySelectorAll(".confidant-intel-drawer").forEach(drawer => {
    if (ALL_CONFIDANT_INTEL_EXPANDED) {
      drawer.classList.add("open");
    } else {
      drawer.classList.remove("open");
    }
  });

  const btn = document.getElementById("btnToggleAllIntel");
  if (btn) {
    btn.innerHTML = `<span>${ALL_CONFIDANT_INTEL_EXPANDED ? '📕 COLLAPSE ALL INTEL' : '📖 EXPAND ALL INTEL'}</span>`;
  }
}

function toggleConfidantDrawer(arcanaId) {
  const drawer = document.getElementById(`drawer_${arcanaId}`);
  if (!drawer) return;
  drawer.classList.toggle("open");
}

function revealSpoilerMask(el) {
  el.classList.toggle("revealed");
}

function calculateDaysRemaining(currentDayStr, targetDateStr) {
  if (!currentDayStr || !targetDateStr) return null;
  const parseMDay = (s) => {
    const m = s.match(/(\d+)\/(\d+)/);
    return m ? { month: parseInt(m[1]), day: parseInt(m[2]) } : null;
  };
  const cur = parseMDay(currentDayStr);
  const tgt = parseMDay(targetDateStr);
  if (!cur || !tgt) return null;

  const curDayOfYear = (cur.month < 4 ? cur.month + 12 : cur.month) * 30 + cur.day;
  const tgtDayOfYear = (tgt.month < 4 ? tgt.month + 12 : tgt.month) * 30 + tgt.day;
  const diff = tgtDayOfYear - curDayOfYear;
  return diff > 0 ? diff : 0;
}

function openPortraitModal(imgSrc, name, role) {
  const modal = document.getElementById("portraitLightboxModal");
  const img = document.getElementById("lightboxImg");
  const title = document.getElementById("lightboxCharName");
  const roleEl = document.getElementById("lightboxRole");
  if (!modal || !img) return;

  img.src = imgSrc;
  if (title) title.textContent = name.toUpperCase();
  if (roleEl) roleEl.textContent = role.toUpperCase();
  modal.classList.add("open");
}

function closePortraitModal(e) {
  const modal = document.getElementById("portraitLightboxModal");
  if (modal) modal.classList.remove("open");
}

let SELECTED_CONFIDANT_ARCANA = null;

function renderConfidants() {
  try {
    updateFilterCounts();
    const rail = document.getElementById("confidantTarotRail");
    if (!rail) {
      console.warn("confidantTarotRail element not found");
      return;
    }
    rail.innerHTML = "";

    const profiles = DB.confidant_profiles || {};
    const romanceableList = DB.romanceable || [];
    const currentDay = CURRENT_SAVE?.header?.day || "";
    const confidants = CURRENT_SAVE?.confidants || {};

    if (Object.keys(confidants).length === 0) {
      rail.innerHTML = `<div style="text-align:center; padding:40px; color:var(--p5-muted);">No Confidant data loaded.</div>`;
      return;
    }

    const matchingArcanas = [];

    Object.entries(confidants).forEach(([arcana, info]) => {
      const prof = profiles[arcana] || { name: arcana, role: "Tokyo Confidant", type: "social", unlock: "Story Perk", img: "", unlock_date: "4/11" };
      
      // Filter matching
      if (CURRENT_CONFIDANT_FILTER === "romance" && prof.type !== "romance" && prof.type !== "romance_deadline") return;
      if (CURRENT_CONFIDANT_FILTER === "party" && prof.type !== "party") return;
      if (CURRENT_CONFIDANT_FILTER === "story_deadline" && prof.type !== "story_deadline" && prof.type !== "romance_deadline") return;
      if (CURRENT_CONFIDANT_FILTER === "social" && prof.type !== "social") return;

      const isMet = info.rank > 0;
      if (!isMet && !ALLOW_UNSAFE_CONFIDANTS) return;

      matchingArcanas.push(arcana);

      const card = document.createElement("div");
      const isRomanceable = romanceableList.includes(info.arcana_id);
      const isDeadline = prof.type === "story_deadline" || prof.type === "romance_deadline";
      const isSelected = arcana === SELECTED_CONFIDANT_ARCANA;

      card.className = `p5-tarot-card ${isRomanceable ? 'romance' : ''} ${isDeadline ? 'deadline' : ''} ${!isMet ? 'locked' : ''} ${isSelected ? 'active' : ''}`;
      card.onclick = () => selectConfidantArcana(arcana);

      const portraitSrc = prof.img ? `/assets/confidants/${prof.img}?v=20260816b` : '/assets/joker_avatar.jpg';

      card.innerHTML = `
        <div class="tarot-rank-badge ${info.rank >= 10 ? 'max' : ''}">${!isMet ? '🔒' : `RK ${info.rank}`}</div>
        <img src="${portraitSrc}" class="tarot-thumb" alt="${prof.name}">
        <div style="flex:1; min-width:0;">
          <div class="tarot-arcana">${arcana.toUpperCase()} (${info.arcana_id})</div>
          <div class="tarot-name">${prof.name}</div>
        </div>
      `;
      rail.appendChild(card);
    });

    // Auto-select first matching confidant if none selected
    if ((!SELECTED_CONFIDANT_ARCANA || !matchingArcanas.includes(SELECTED_CONFIDANT_ARCANA)) && matchingArcanas.length > 0) {
      SELECTED_CONFIDANT_ARCANA = matchingArcanas[0];
      // Update active card class
      const firstCard = rail.querySelector(".p5-tarot-card");
      if (firstCard) firstCard.classList.add("active");
    }

    if (SELECTED_CONFIDANT_ARCANA) {
      renderActiveConfidantSpotlight(SELECTED_CONFIDANT_ARCANA);
    }
  } catch (err) {
    console.error("renderConfidants error:", err);
  }
}

function selectConfidantArcana(arcana) {
  SELECTED_CONFIDANT_ARCANA = arcana;
  document.querySelectorAll(".p5-tarot-card").forEach(el => el.classList.remove("active"));
  const clicked = event?.currentTarget;
  if (clicked) clicked.classList.add("active");
  renderActiveConfidantSpotlight(arcana);
}

function getConfidantEventReadyPoints(arcana, rank) {
  // Rank button clicks intentionally stage a high affinity value so the
  // next natural hangout/event can trigger after saving. Keep this explicit
  // instead of hiding the 99 sentinel inside stepConfidantRank().
  if (!arcana || rank <= 0 || rank >= 10) return 0;
  return 99;
}

function getConfidantAffinityState(arcana, info) {
  const rank = Math.max(0, Math.min(10, parseInt(info?.rank || 0, 10)));
  const points = Math.max(0, parseInt(info?.points || 0, 10));
  const thresholds = DB.point_thresholds?.[arcana] || {};
  const nextRank = rank < 10 ? rank + 1 : null;
  const nextThreshold = nextRank ? thresholds[nextRank] : null;
  const hasPointGate = nextThreshold !== null && nextThreshold !== undefined;
  const eventReady = rank > 0 && rank < 10 && hasPointGate && points >= nextThreshold;
  const missing = hasPointGate ? Math.max(0, nextThreshold - points) : null;
  const pct = hasPointGate && nextThreshold > 0
    ? Math.max(0, Math.min(100, Math.round((points / nextThreshold) * 100)))
    : (eventReady || nextThreshold === 0 ? 100 : 0);

  return { rank, points, nextRank, nextThreshold, hasPointGate, eventReady, missing, pct };
}

function renderConfidantAffinityMeter(arcana, info) {
  const state = getConfidantAffinityState(arcana, info);
  const { rank, points, nextRank, nextThreshold, hasPointGate, eventReady, missing, pct } = state;
  const inputId = `affinityPointsInput_${arcana.replace(/\W/g, "_")}`;
  const inputHtml = `
    <label class="affinity-edit-box" for="${inputId}">
      <span>CURRENT</span>
      <input
        id="${inputId}"
        class="affinity-points-input"
        type="number"
        min="0"
        max="65535"
        step="1"
        value="${points}"
        onchange="setConfidantAffinityPoints('${arcana}', this.value)"
        onkeydown="if(event.key === 'Enter') this.blur();"
      >
      <span>PTS</span>
    </label>
  `;

  if (rank >= 10) {
    return `
      <div class="affinity-meter-card maxed">
        <div class="affinity-meter-head">
          <span>AFFINITY POINTS</span>
          <span class="affinity-state-badge maxed">BOND MAXED</span>
        </div>
        <div class="affinity-meter-main">
          ${inputHtml}
          <div class="affinity-copy">Rank 10 has no next event gate, but the stored point value can still be edited if you want exact save parity.</div>
        </div>
        <div class="affinity-quick-actions">
          <button class="affinity-mini-btn" onclick="stepConfidantAffinityPoints('${arcana}', -1)">-1</button>
          <button class="affinity-mini-btn" onclick="stepConfidantAffinityPoints('${arcana}', 1)">+1</button>
          <button class="affinity-mini-btn white" onclick="setConfidantAffinityPoints('${arcana}', 99)">SET 99</button>
        </div>
      </div>
    `;
  }

  if (!hasPointGate) {
    return `
      <div class="affinity-meter-card story-locked">
        <div class="affinity-meter-head">
          <span>AFFINITY POINTS</span>
          <span class="affinity-state-badge story">STORY / SPECIAL</span>
        </div>
        <div class="affinity-meter-main">
          ${inputHtml}
          <div class="affinity-copy">No reliable point gate is defined for this Arcana/rank. You can still write the stored points manually.</div>
        </div>
        <div class="affinity-quick-actions">
          <button class="affinity-mini-btn" onclick="stepConfidantAffinityPoints('${arcana}', -1)">-1</button>
          <button class="affinity-mini-btn" onclick="stepConfidantAffinityPoints('${arcana}', 1)">+1</button>
          <button class="affinity-mini-btn white" onclick="setConfidantAffinityPoints('${arcana}', 99)">SET 99</button>
        </div>
      </div>
    `;
  }

  return `
    <div class="affinity-meter-card ${eventReady ? 'ready' : 'building'}">
      <div class="affinity-meter-head">
        <span>AFFINITY POINTS</span>
        <span class="affinity-state-badge ${eventReady ? 'ready' : 'building'}">${eventReady ? 'EVENT READY' : `${missing} PTS TO EVENT`}</span>
      </div>
      <div class="affinity-meter-main">
        ${inputHtml}
        <div class="affinity-copy">
          ${eventReady
            ? `Next hangout should trigger the Rank ${nextRank} event. Saving after rank-click staging writes these points.`
            : `Needs ${nextThreshold} affinity points for the Rank ${nextRank} event trigger.`}
        </div>
      </div>
      <div class="affinity-track" title="${points} / ${nextThreshold} points toward Rank ${nextRank}">
        <div class="affinity-fill" style="width:${pct}%;"></div>
        <div class="affinity-threshold-mark"></div>
      </div>
      <div class="affinity-meter-foot">
        <span><strong>${points}</strong> / ${nextThreshold} pts</span>
        <span>Current Rank ${rank} → Event Rank ${nextRank}</span>
      </div>
      <div class="affinity-quick-actions">
        <button class="affinity-mini-btn" onclick="stepConfidantAffinityPoints('${arcana}', -10)">-10</button>
        <button class="affinity-mini-btn" onclick="stepConfidantAffinityPoints('${arcana}', -1)">-1</button>
        <button class="affinity-mini-btn" onclick="stepConfidantAffinityPoints('${arcana}', 1)">+1</button>
        <button class="affinity-mini-btn" onclick="stepConfidantAffinityPoints('${arcana}', 10)">+10</button>
        <button class="affinity-mini-btn ready" onclick="setConfidantAffinityPoints('${arcana}', ${nextThreshold})">EVENT READY</button>
        <button class="affinity-mini-btn white" onclick="setConfidantAffinityPoints('${arcana}', 99)">SET 99</button>
      </div>
    </div>
  `;
}

function setConfidantAffinityPoints(arcana, value) {
  if (!CURRENT_SAVE?.confidants?.[arcana]) return;
  const parsed = parseInt(value, 10);
  const nextPoints = Math.max(0, Math.min(65535, Number.isFinite(parsed) ? parsed : 0));
  CURRENT_SAVE.confidants[arcana].points = nextPoints;
  renderActiveConfidantSpotlight(arcana);
  renderConfidants();
  const state = getConfidantAffinityState(arcana, CURRENT_SAVE.confidants[arcana]);
  setStatus(`★ ${arcana} affinity points set to ${nextPoints}${state.eventReady ? ` — Rank ${state.nextRank} event ready.` : "."}`);
}

function stepConfidantAffinityPoints(arcana, delta) {
  const cur = parseInt(CURRENT_SAVE?.confidants?.[arcana]?.points || 0, 10);
  setConfidantAffinityPoints(arcana, cur + delta);
}

function renderActiveConfidantSpotlight(arcana) {
  const spotlight = document.getElementById("confidantHeroSpotlight");
  if (!spotlight || !CURRENT_SAVE?.confidants?.[arcana]) return;

  const info = CURRENT_SAVE.confidants[arcana];
  const profiles = DB.confidant_profiles || {};
  const romanceableList = DB.romanceable || [];
  const lore = CONFIDANT_LORE[arcana] || { milestone: "Deepens friendship.", awakening: "Ultimate Persona.", keepsake: "Special keepsake." };
  const prof = profiles[arcana] || { name: arcana, role: "Tokyo Confidant", unlock: "Story Perk", img: "" };
  const currentDay = CURRENT_SAVE?.header?.day || "";
  const socialStats = CURRENT_SAVE?.social_stats || {};

  const isRomanceable = romanceableList.includes(info.arcana_id);
  const isMaxed = info.rank >= 10;
  
  // Prefer full-body official standee if available
  const standeeKey = prof.img ? prof.img.replace('.png', '') : '';
  const fullStandeeSrc = `/assets/confidants_full/${standeeKey}.png?v=20260816`;
  const portraitSrc = prof.img ? `/assets/confidants/${prof.img}?v=20260816b` : '/assets/joker_avatar.jpg';

  let deadlineAlert = "";
  if (arcana === "Councillor") {
    const days = calculateDaysRemaining(currentDay, "11/18");
    deadlineAlert = `<div class="spotlight-deadline">⚠️ NOV 18 THIRD SEMESTER CUTOFF (${days !== null ? `${days} in-game days left` : 'CRITICAL'})</div>`;
  } else if (arcana === "Justice") {
    const days = calculateDaysRemaining(currentDay, "11/17");
    deadlineAlert = `<div class="spotlight-deadline">⚠️ NOV 17 DUEL & TRUE ENDING CUTOFF (${days !== null ? `${days} in-game days left` : 'CRITICAL'})</div>`;
  } else if (arcana === "Sun") {
    const days = calculateDaysRemaining(currentDay, "11/13");
    deadlineAlert = `<div class="spotlight-deadline">⚠️ NOV 13 SPEECH CAMPAIGN CUTOFF (${days !== null ? `${days} in-game days left` : 'CRITICAL'})</div>`;
  } else if (arcana === "Faith") {
    deadlineAlert = `<div class="spotlight-deadline" style="background:#FFFFFF; color:#000;">🔒 RANK 5 CAP (Ranks 6–10 locked until January 3rd Semester)</div>`;
  }

  // Stat Requirements
  let statChecksHtml = "";
  if (lore.stat_req) {
    Object.entries(lore.stat_req).forEach(([statName, reqRank]) => {
      const curRank = socialStats[statName]?.rank || 1;
      const isOk = curRank >= reqRank;
      statChecksHtml += `<span class="intel-stat-check ${isOk ? 'ok' : 'blocked'}">${isOk ? '✔' : '❌'} Req: ${statName} Lv ${reqRank} (Current: ${curRank})</span>`;
    });
  }

  const warning = getConfidantSafetyWarning(arcana, info.rank);
  const warningHtml = warning ? `
    <div class="spotlight-warning-box">
      <div style="font-weight:900; font-size:13px; margin-bottom:2px;">⚠️ SEQUENCE BREAK / STORY CUTSCENE ALERT:</div>
      <div>${warning.badge}</div>
    </div>
  ` : "";
  const affinityMeterHtml = renderConfidantAffinityMeter(arcana, info);

  spotlight.innerHTML = `
    <!-- Top Hero Banner with Huge Slanted Portrait & Nameplate -->
    <div class="spotlight-header-card">
      <div class="spotlight-portrait-frame" onclick="openPortraitModal('${fullStandeeSrc}', '${prof.name.replace(/'/g, "\\'")}', '${prof.role.replace(/'/g, "\\'")}')" title="Click to view full portrait">
        <img src="${fullStandeeSrc}" onerror="this.src='${portraitSrc}'" class="spotlight-full-portrait" alt="${prof.name}">
        <div class="spotlight-zoom-hint">🔍 FULL STANDEE</div>
      </div>

      <div class="spotlight-identity-block">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px;">
          <div class="spotlight-arcana-tag">${arcana.toUpperCase()} ARCANA (${info.arcana_id})</div>
          ${info.rank >= 10 ? '<span class="spotlight-status-badge max">★ BOND MAXED (10/10)</span>' : (info.rank >= 9 && isRomanceable ? '<span class="spotlight-status-badge romance">💖 LOVER RELATIONSHIP</span>' : `<span class="spotlight-status-badge">PROGRESSION (${info.rank}/10)</span>`)}
        </div>

        <h1 class="spotlight-character-name">${prof.name}</h1>
        <div class="spotlight-role-text">${prof.role}</div>

        <div class="spotlight-perk-card">
          <div style="font-family:var(--font-p5); font-size:14px; color:var(--p5-white); letter-spacing:1px; margin-bottom:2px;">⚡ SIGNATURE INFILTRATION ABILITY:</div>
          <div style="font-size:12px; color:#FFFFFF; font-weight:700; line-height:1.4;">${prof.unlock}</div>
        </div>

        ${deadlineAlert}
      </div>
    </div>

    <!-- Stepped Rank Adjustment Control Deck -->
    <div class="spotlight-rank-bar">
      <div style="font-family:var(--font-p5); font-size:22px; letter-spacing:1.5px; color:var(--p5-white); text-shadow:2px 2px 0 #000;">
        CO-OP RANK:
      </div>

      <div style="display:flex; align-items:center; gap:12px;">
        <button class="rank-stepper-btn" onclick="stepConfidantRank('${arcana}', -1)" ${info.rank <= 0 ? 'disabled' : ''}>◄</button>
        <div class="rank-display-box">
          <span class="rank-number-text">${info.rank}</span>
          <span style="font-size:14px; color:var(--p5-muted);">/ 10</span>
        </div>
        <button class="rank-stepper-btn" onclick="stepConfidantRank('${arcana}', 1)" ${info.rank >= 10 ? 'disabled' : ''}>►</button>
      </div>

      <button class="p5-btn-action" style="padding:8px 18px; font-size:16px;" onclick="stepConfidantRank('${arcana}', 10 - ${info.rank})">
        <span>★ MAX (RANK 10)</span>
      </button>

      ${isRomanceable && info.rank >= 9 ? `
        <div style="display:flex; align-items:center; gap:8px; margin-left:auto; background:rgba(255,42,109,0.15); padding:6px 12px; border:1px solid #FF2A6D; border-radius:4px;">
          <span style="font-size:12px; font-weight:900; color:#FF80AB;">RELATIONSHIP:</span>
          <button class="filter-pill ${info.romance ? 'active' : ''}" style="border-radius:4px; font-size:11px; padding:3px 8px; ${info.romance ? 'background:#FF2A6D; border-color:#FF2A6D;' : ''}" onclick="toggleConfidantRomance('${arcana}')">
            ${info.romance ? '💖 LOVER' : '🤝 FRIEND'}
          </button>
        </div>
      ` : ''}
    </div>

    ${affinityMeterHtml}

    ${warningHtml}

    <!-- In-Game Consequence & Lore Panels -->
    <div class="spotlight-dossier-grid">
      <!-- Live Rank Consequence -->
      <div class="dossier-panel" style="border-left-color:${info.rank >= 10 ? '#FFFFFF' : (info.rank >= 9 && isRomanceable ? '#FF2A6D' : 'var(--p5-crimson)')};">
        <div class="dossier-panel-title">
          <span>⚡ RANK ${info.rank} NARRATIVE IMPACT</span>
          <span style="color:${info.rank >= 10 ? '#FFFFFF' : 'var(--p5-cyan)'};">${info.rank >= 10 ? '✔ COMPLETED' : 'ACTIVE'}</span>
        </div>
        <div style="font-size:12px; line-height:1.5; color:#E0E0EE;">
          ${info.rank >= 10 ? `
            • 🌟 <strong>Story Status:</strong> Bond has reached its emotional zenith. Joker has earned ${prof.name}'s ultimate trust.<br>
            • 👑 <strong>Awakening / Fusion:</strong> Ultimate Arcana Persona unlocked in the Velvet Room.<br>
            • 🎁 <strong>3/19 Farewell Keepsake:</strong> ${prof.name} will hand Joker their sentimental farewell memento on the final day in Tokyo, carrying their signature ability into New Game+ from Day 1.
          ` : (info.rank >= 9 && isRomanceable ? `
            • 💖 <strong>Romance Route:</strong> Confession cutscene completed. Unlocks exclusive Christmas Eve & Valentine's Day dates.<br>
            • 🔓 <strong>Perks:</strong> Full clinical/service perks unlocked. Final Rank 10 event ready.
          ` : `
            • 📖 <strong>Story Pacing:</strong> Currently progressing through ${prof.name}'s Tokyo storyline at Rank ${info.rank}.<br>
            • 💡 <strong>Rank Up Impact:</strong> Reaching higher ranks unlocks signature abilities and deepens Joker's bond toward their 3/19 NG+ Farewell Gift.
          `)}
        </div>
      </div>

      <!-- Narrative Milestone & Gating -->
      <div class="dossier-panel">
        <div class="dossier-panel-title">🌟 STORY MILESTONE & STAT GATES</div>
        <div style="font-size:12px; line-height:1.45; color:#C0C0D0; margin-bottom:8px;">${lore.milestone}</div>
        ${statChecksHtml ? `<div style="display:flex; flex-wrap:wrap; gap:6px; margin-top:6px;">${statChecksHtml}</div>` : ''}
      </div>

      <!-- Persona Evolution & NG+ Keepsake Spoilers -->
      <div class="dossier-panel" style="grid-column: 1 / -1; border-left-color:var(--p5-white);">
        <div class="dossier-panel-title" style="color:var(--p5-white);">👑 ULTIMATE PERSONA AWAKENING & 3/19 NG+ KEEPSAKE</div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; font-size:12px; margin-top:6px;">
          <div>
            <strong>Velvet Room Ultimate Fusion:</strong><br>
            <span class="spoiler-mask ${isMaxed ? 'revealed' : ''}" onclick="revealSpoilerMask(this)" title="Click to reveal">${lore.awakening}</span>
          </div>
          <div>
            <strong>3/19 NG+ Farewell Keepsake:</strong><br>
            <span class="spoiler-mask ${isMaxed ? 'revealed' : ''}" onclick="revealSpoilerMask(this)" title="Click to reveal">${lore.keepsake}</span>
          </div>
        </div>
      </div>
    </div>
  `;
}

function toggleConfidantRomance(arcana) {
  if (!CURRENT_SAVE?.confidants?.[arcana]) return;
  const cur = Boolean(CURRENT_SAVE.confidants[arcana].romance);
  CURRENT_SAVE.confidants[arcana].romance = !cur;
  renderConfidants();
  setStatus(`★ ${arcana} relationship set to ${!cur ? '💖 LOVER' : '🤝 FRIEND'} — armed for save.`);
}

function stepConfidantRank(arcana, delta) {
  if (!CURRENT_SAVE?.confidants?.[arcana]) return;
  const cur = CURRENT_SAVE.confidants[arcana].rank || 0;
  const newRank = Math.max(0, Math.min(10, cur + delta));
  CURRENT_SAVE.confidants[arcana].rank = newRank;
  const stagedPoints = getConfidantEventReadyPoints(arcana, newRank);
  CURRENT_SAVE.confidants[arcana].points = stagedPoints;
  renderConfidants();
  const state = getConfidantAffinityState(arcana, CURRENT_SAVE.confidants[arcana]);
  setStatus(`★ ${arcana} Rank ${newRank} staged with ${state.points} affinity points${state.eventReady ? ` — Rank ${state.nextRank} event ready.` : "."}`);
}

function getConfidantSafetyWarning(arcana, newRank) {
  if (!CURRENT_SAVE) return null;
  const currentDay = CURRENT_SAVE?.header?.day || "";
  const prof = DB.confidant_profiles?.[arcana] || {};
  const isRomanceable = (DB.romanceable || []).includes(prof.arcana_id || 0) || prof.type === "romance" || prof.type === "romance_deadline";
  const origRank = (typeof INITIAL_CONFIDANT_RANKS !== "undefined" && INITIAL_CONFIDANT_RANKS[arcana] !== undefined) ? INITIAL_CONFIDANT_RANKS[arcana] : (CURRENT_SAVE.confidants?.[arcana]?.rank || 0);

  // 1. Romance Confession Cutscene Skip Warning
  if (isRomanceable && origRank < 9 && newRank >= 9) {
    return {
      type: "romance",
      badge: `🎬 CUTSCENE SKIP: You will permanently skip ${prof.name}'s Rank 9 Confession Scene! (Romance route dialogue choice will not trigger in-game).`,
      detail: `Setting ${prof.name || arcana} to Rank ${newRank} bypasses the romantic confession cutscene. You will get the perks immediately, but you will miss the romance dialogue choice.`
    };
  }

  // 2. Early-Game / Winter Cap Exceeded
  if (arcana === "Faith" && newRank > 5) {
    const isWinter = isStoryUnlocked(currentDay, "1/12");
    if (!isWinter) {
      return {
        type: "cap",
        badge: `⚠️ SEQUENCE BREAK: Exceeds Rank 5 School Cap! (Ranks 6–10 cutscenes are locked until Third Semester in January).`,
        detail: `Kasumi's storyline is hard-coded to pause at Rank 5. Forcing Ranks 6–10 now skips her story awakening cutscenes.`
      };
    }
  }

  // 3. Unmet Story Ally
  const isCalendarReady = isStoryUnlocked(currentDay, prof.unlock_date);
  if (!isCalendarReady && newRank > 0 && origRank === 0) {
    return {
      type: "unmet",
      badge: `🎬 SEQUENCE BREAK: Ally arrives on ${prof.unlock_date}. (Introductory story cutscenes will be skipped).`,
      detail: `${prof.name || arcana} has not been introduced on your current calendar date (${currentDay}). Forcing ranks skips their meeting cutscenes.`
    };
  }

  // 4. Intermediate Cutscene Skip (Jumping multiple ranks)
  if (newRank - origRank >= 2 && newRank > 0 && origRank > 0) {
    const skippedCount = newRank - origRank;
    return {
      type: "jump",
      badge: `🎬 CUTSCENE SKIP: Advancing from Rank ${origRank} ➔ ${newRank} will skip ${skippedCount} daytime hangout cutscenes in Tokyo!`,
      detail: `You will gain all intermediate battle perks immediately, but the character development cutscenes between Rank ${origRank} and ${newRank} will not play in-game.`
    };
  }

  return null;
}

function maxAllConfidants() {
  if (!CURRENT_SAVE) return;
  Object.keys(CURRENT_SAVE.confidants || {}).forEach((name) => {
    CURRENT_SAVE.confidants[name].rank = 10;
  });
  renderConfidants();
}

function collectAllSequenceBreakRisks() {
  if (!CURRENT_SAVE) return [];
  const risks = [];
  Object.entries(CURRENT_SAVE.confidants || {}).forEach(([arcana, info]) => {
    const w = getConfidantSafetyWarning(arcana, info.rank);
    if (w && (w.type === "romance" || w.type === "cap" || w.type === "unmet")) {
      risks.push({ arcana, ...w });
    }
  });
  return risks;
}

function closeSafetyModal(e) {
  const modal = document.getElementById("sequenceBreakSafetyModal");
  if (modal) modal.classList.remove("open");
}

function executeSaveAfterSafetyCheck() {
  closeSafetyModal();
  executeSavePayload();
}

// =========================================================================
// STAGE 3.75: COMPENDIUM REGISTRY LOGIC (GRANULAR & BATCH STUDIO)
// =========================================================================
let COMPENDIUM_DATA = null; // { supported, registered: [ids], count }
let ORIGINAL_COMPENDIUM_REGISTERED = [];
let COMPENDIUM_FILTER_MODE = "all"; // "all" | "registered" | "unregistered"
let COMPENDIUM_SEARCH_QUERY = "";
// Armed by Unlock ALL; makes /api/save run the verified backend
// unlock_compendium_100() (exact genuine-100% oracle parity) instead of the
// staged per-pid list, which silently cleared party/story mask bits.
let UNLOCK_COMPENDIUM_PENDING = false;

// Known DLC & Treasure Demon IDs in P5R
const DLC_PERSONA_IDS = [181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 362, 363, 366, 367, 368, 369, 370, 371];
const TREASURE_DEMON_IDS = [106, 107, 108, 109, 110, 111, 112, 113, 114]; // Regent, Queen's Necklace, Stone of Scone, Koh-i-Noor, Orlov, Emperor's Amulet, Hope Diamond, Crystal Skull, Orichalcum
// Mask bits the game NEVER sets (verified across real saves + NG++ 100% oracle).
const STUB_COMPENDIUM_IDS = new Set([1, 219, 220, 221, 222, 224]);
const STORY_COMPENDIUM_IDS = new Set([216, 218]);
// Party-member personas: the game registers these mask bits as members
// join, but they can never be summoned from the compendium. Rendered with
// a PARTY badge, non-interactive.
const PARTY_COMPENDIUM_IDS = new Set([
  170, 199, 202, 203, 204, 205, 206, 207, 208, 209, 210,
  212, 213, 214, 215, 217, 223, 225, 226, 227, 228, 231, 232,
  233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244,
  245, 246, 247, 248, 249, 250
]);
const UNNAMED_PERSONA_NAMES = new Set([
  "", "RESERVE", "???", "BLANK", "----------", "P5 Unused", "P6 Unused",
  "チャレンジ用フロスト", "チャレンジ用エンジェル", "タイマン用シンデレラ"
]);

function renderCompendium() {
  if (!COMPENDIUM_DATA && CURRENT_SAVE?.compendium) {
    COMPENDIUM_DATA = JSON.parse(JSON.stringify(CURRENT_SAVE.compendium));
    ORIGINAL_COMPENDIUM_REGISTERED = [...(COMPENDIUM_DATA.registered || [])];
  }
  if (!COMPENDIUM_DATA || !COMPENDIUM_DATA.supported) return;

  // Authentic P5R Velvet Room Compendium: All 246 summonable demon fusions (Base + Royal/DLC)
  // Non-summonable party/story entries and dead bits are excluded from the registerable denominator.
  const playableIds = (DB.personas || [])
    .filter(p => !UNNAMED_PERSONA_NAMES.has(p.name) && !p.name.startsWith("Lab "))
    .map(p => p.id)
    .filter(id => id >= 1 && id <= 437
      && !STUB_COMPENDIUM_IDS.has(id)
      && !STORY_COMPENDIUM_IDS.has(id)
      && !PARTY_COMPENDIUM_IDS.has(id));

  const total = playableIds.length; // 246 authentic summonable Personas
  const regSet = new Set(COMPENDIUM_DATA.registered || []);
  const count = playableIds.filter(id => regSet.has(id)).length;
  COMPENDIUM_DATA.count = count;
  const pct = total ? Math.round((count / total) * 100) : 0;

  const counter = document.getElementById("compendiumCounter");
  if (counter) counter.textContent = `${count} / ${total} REGISTERED (${pct}%)`;

  const bar = document.getElementById("compendiumProgressBar");
  if (bar) bar.style.width = pct + "%";

  const label = document.getElementById("compendiumPercentLabel");
  if (label) label.textContent = pct + "%";

  filterCompendiumGrid();
}

function filterCompendiumGrid() {
  const grid = document.getElementById("compendiumGrid");
  if (!grid || !COMPENDIUM_DATA) return;

  const searchInput = document.getElementById("compendiumSearchInput");
  const query = (searchInput ? searchInput.value : "").trim().toLowerCase();
  const regSet = new Set(COMPENDIUM_DATA.registered || []);
  const personas = DB.personas || [];
  // Full id->name map first (2026-08-16): party personas whose names
  // duplicate earlier ids (Satanael 0xD3, Carmen 0xDF, 0xE1-0xE8) are
  // dropped by the dropdown dedupe but must still render named here.
  const byId = { ...(DB.persona_names || {}) };
  for (const p of personas) byId[p.id] = p.name;

  grid.innerHTML = "";
  let visibleCount = 0;

  // Render only real, named personas (registerable) + the two STORY cards.
  const regIds = personas
    .filter(p => !UNNAMED_PERSONA_NAMES.has(p.name) && !p.name.startsWith("Lab "))
    .map(p => p.id)
    .filter(id => id >= 1 && id <= 437
      && !STUB_COMPENDIUM_IDS.has(id)
      && !STORY_COMPENDIUM_IDS.has(id)
      && !PARTY_COMPENDIUM_IDS.has(id));
  const renderIds = regIds
    .concat([...STORY_COMPENDIUM_IDS])
    .concat([...PARTY_COMPENDIUM_IDS])
    .sort((a, b) => a - b);
  const regCount = regIds.filter(id => regSet.has(id)).length;
  const unregCount = regIds.length - regCount;

  const allBtn = document.getElementById("filterCompAll");
  if (allBtn) allBtn.textContent = `ALL (${renderIds.length})`;

  const regBtn = document.getElementById("filterCompReg");
  if (regBtn) regBtn.textContent = `REGISTERED (${regCount})`;

  const unregBtn = document.getElementById("filterCompUnreg");
  if (unregBtn) unregBtn.textContent = `UNREGISTERED (${unregCount})`;

  for (const pid of renderIds) {
    const isStory = STORY_COMPENDIUM_IDS.has(pid);
    const isParty = PARTY_COMPENDIUM_IDS.has(pid);
    const isReg = !isStory && !isParty && regSet.has(pid);

    // Status filter
    if (COMPENDIUM_FILTER_MODE === "registered" && !isReg) continue;
    if (COMPENDIUM_FILTER_MODE === "unregistered" && (isReg || isStory || isParty)) continue;

    const name = byId[pid] || "?";
    const hexId = "0x" + pid.toString(16).toUpperCase().padStart(2, "0");

    // Search query filter
    if (query && !name.toLowerCase().includes(query) && !hexId.toLowerCase().includes(query) && !pid.toString().includes(query)) {
      continue;
    }

    visibleCount++;
    const isDlc = DLC_PERSONA_IDS.includes(pid);
    const isTreasure = TREASURE_DEMON_IDS.includes(pid);

    const isSpecial = isStory || isParty;
    const card = document.createElement("div");
    card.style.cssText = `
      background: ${isSpecial ? "#0B0B10" : isReg ? "linear-gradient(135deg, #1C1226, #0E0B16)" : "#09090D"};
      border: 1px solid ${isSpecial ? "#2A2A35" : isReg ? "#E040FB" : "#222"};
      border-left: 6px solid ${isSpecial ? "#4A4A5A" : isReg ? "#FFFFFF" : "#444"};
      padding: 10px 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      cursor: ${isSpecial ? "default" : "pointer"};
      border-radius: 4px;
      opacity: ${isSpecial ? "0.75" : "1"};
      transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
      box-shadow: ${isReg && !isSpecial ? "0 4px 15px rgba(0,230,118,0.1)" : "none"};
    `;
    card.title = isStory
      ? `${name} — story-exclusive persona; cannot be registered`
      : isParty
        ? `${name} — party-member persona; cannot be summoned`
        : `Click to ${isReg ? "un-register" : "register"} ${name} (ID: ${hexId})`;

    card.onmouseenter = (e) => {
      if (!isSpecial) {
        card.style.transform = "translateY(-3px)";
        card.style.boxShadow = "0 6px 20px rgba(0,0,0,0.8)";
      }
      const spot = document.getElementById("personaArtSpotlight");
      const img = document.getElementById("personaSpotlightImg");
      const title = document.getElementById("personaSpotlightTitle");
      const sub = document.getElementById("personaSpotlightSub");
      if (spot && img && title && sub) {
        img.src = `/assets/personas/${pid}.png`;
        img.onerror = () => { spot.style.display = "none"; };
        img.onload = () => {
          title.textContent = name;
          sub.textContent = `${hexId} (#${pid}) ${isDlc ? '• DLC' : isTreasure ? '• TREASURE DEMON' : ''}`;
          spot.style.display = "block";
          const rect = card.getBoundingClientRect();
          let leftPos = rect.right + 12;
          if (leftPos + 290 > window.innerWidth) leftPos = rect.left - 300;
          let topPos = Math.max(10, rect.top - 40);
          if (topPos + 340 > window.innerHeight) topPos = window.innerHeight - 350;
          spot.style.left = leftPos + "px";
          spot.style.top = topPos + "px";
        };
      }
    };
    card.onmouseleave = () => {
      card.style.transform = "translateY(0)";
      card.style.boxShadow = isReg ? "0 4px 15px rgba(0,230,118,0.1)" : "none";
      const spot = document.getElementById("personaArtSpotlight");
      if (spot) spot.style.display = "none";
    };
    card.onclick = () => {
      if (!isSpecial) togglePersonaRegistration(pid);
      const spot = document.getElementById("personaArtSpotlight");
      if (spot) spot.style.display = "none";
    };

    const left = document.createElement("div");
    left.style.cssText = "display:flex; align-items:center; gap:12px;";
    left.innerHTML = `
      <img src="/assets/personas/${pid}.png" onerror="this.style.display='none'" style="width:56px; height:56px; object-fit:contain; background:#0B0B10; border:1px solid #333; padding:3px; border-radius:4px; filter:${isSpecial ? 'grayscale(0.6) opacity(0.7)' : 'drop-shadow(0 2px 6px rgba(0,0,0,0.7))'}; flex-shrink:0;">
      <div>
        <div style="font-family:var(--font-p5); font-size:15px; letter-spacing:0.5px; color:${isSpecial ? '#888' : isReg ? '#FFF' : '#777'};">
          ${name} ${isDlc ? '<span style="font-size:9px; font-family:var(--font-body); font-weight:900; background:#FF2A6D; color:#FFF; padding:2px 5px; border-radius:2px;">DLC</span>' : ''} ${isTreasure ? '<span style="font-size:9px; font-family:var(--font-body); font-weight:900; background:#FFFFFF; color:#000; padding:2px 5px; border-radius:2px;">DEMON</span>' : ''}
        </div>
        <div style="font-size:11px; color:var(--p5-muted); font-family:monospace; margin-top:2px;"><span style="color:#555;">No.${pid}</span>${isDlc ? ' · DLC' : ''}</div>
      </div>
    `;

    const statusBadge = document.createElement("span");
    statusBadge.style.cssText = `
      font-size: 11px;
      font-weight: 900;
      padding: 3px 8px;
      font-family: var(--font-p5);
      background: ${isSpecial ? "#3A3A4A" : isReg ? "#FFFFFF" : "#222"};
      color: ${isSpecial ? "#BBB" : isReg ? "#000" : "#666"};
      border: 1px solid ${isSpecial ? "#3A3A4A" : isReg ? "#FFFFFF" : "#333"};
    `;
    statusBadge.textContent = isStory ? "STORY" : isParty ? "PARTY" : (isReg ? "REGISTERED" : "NOT REGISTERED");

    card.appendChild(left);
    card.appendChild(statusBadge);
    grid.appendChild(card);
  }

  const countLabel = document.getElementById("compendiumFilterCount");
  if (countLabel) countLabel.textContent = `Showing ${visibleCount} Personas`;

  if (visibleCount === 0) {
    grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:30px; color:var(--p5-muted);">No Personas match current filter or search criteria.</div>`;
  }
}

function setCompendiumFilter(mode, btnEl) {
  COMPENDIUM_FILTER_MODE = mode;
  document.querySelectorAll("#stage-compendium .p5-chip").forEach(c => c.classList.remove("active"));
  if (btnEl) btnEl.classList.add("active");
  filterCompendiumGrid();
}

function togglePersonaRegistration(pid) {
  if (!COMPENDIUM_DATA) return;
  if (STORY_COMPENDIUM_IDS.has(pid)) {
    alert(`⚠ ${pid === 216 ? "Anat" : "Prometheus"} is a story-exclusive persona — the game never registers it.`);
    return;
  }
  if (PARTY_COMPENDIUM_IDS.has(pid)) {
    alert(`⚠ That is a party-member persona — it cannot be summoned or toggled in the compendium.`);
    return;
  }
  const regSet = new Set(COMPENDIUM_DATA.registered || []);
  if (regSet.has(pid)) {
    regSet.delete(pid);
  } else {
    regSet.add(pid);
  }
  COMPENDIUM_DATA.registered = Array.from(regSet).sort((a, b) => a - b);
  COMPENDIUM_DATA.count = regSet.size;
  renderCompendium();
}

function unlockFullCompendium() {
  const regIds = (DB.personas || [])
    .filter(p => !UNNAMED_PERSONA_NAMES.has(p.name) && !p.name.startsWith("Lab "))
    .map(p => p.id)
    .filter(id => id >= 1 && id <= 437);

  if (!confirm(`Unlock ALL ${regIds.length} registerable personas in the Compendium?\n\nWrites a genuine 100% state: full registration bitmask + all Velvet Room records, matching a real 100% save.\n\nRemember to RE-SIGN SAVE.`)) return;
  UNLOCK_COMPENDIUM_PENDING = true;
  COMPENDIUM_DATA.registered = regIds.slice();
  COMPENDIUM_DATA.count = regIds.length;
  renderCompendium();
  setStatus(`★ 100% compendium unlock armed — click RE-SIGN SAVE to apply the verified full unlock.`);
}

function unlockDlcPersonas() {
  if (!COMPENDIUM_DATA) return;
  const regSet = new Set(COMPENDIUM_DATA.registered || []);
  DLC_PERSONA_IDS.forEach(id => regSet.add(id));
  COMPENDIUM_DATA.registered = Array.from(regSet).sort((a, b) => a - b);
  renderCompendium();
  setStatus("★ All DLC Personas registered in Compendium matrix.");
}

function unlockTreasureDemons() {
  if (!COMPENDIUM_DATA) return;
  const regSet = new Set(COMPENDIUM_DATA.registered || []);
  TREASURE_DEMON_IDS.forEach(id => regSet.add(id));
  COMPENDIUM_DATA.registered = Array.from(regSet).sort((a, b) => a - b);
  renderCompendium();
  setStatus("★ All Treasure Demons registered in Compendium matrix.");
}

function resetCompendiumToOriginal() {
  if (!confirm("Reset compendium back to the save file's original registration state?")) return;
  UNLOCK_COMPENDIUM_PENDING = false;
  COMPENDIUM_DATA.registered = [...ORIGINAL_COMPENDIUM_REGISTERED];
  COMPENDIUM_DATA.count = ORIGINAL_COMPENDIUM_REGISTERED.length;
  renderCompendium();
  setStatus("Compendium reset to original loaded state.");
}

// =========================================================================
// STAGE 3.5: INVENTORY & POUCH STUDIO LOGIC (TWO-PANEL INTUITIVE UI)
// =========================================================================
// STAGE 3.5: PERSONA 5 ROYAL UNIFIED ITEM STUDIO & LIVE DOSSIER
// =========================================================================
let CURRENT_UNIFIED_CATEGORY = "Consumable";
let UNIFIED_SEARCH_QUERY = "";
let SELECTED_ITEM_ID = null;
let INVENTORY_ITEM_COUNTS = {}; // id -> count (0..99 or 0/1). Zeroed ids stay present (explicit 0) — buildInventoryPayload diffs vs baseline.
const GEAR_CATEGORIES = new Set(["Melee", "Ranged", "Protector"]);
// VERIFIED count-array categories (editor.py get_item_count_offset): Consumable
// 0x2530/0x25AA/0x2600, Accessory 0x2330, Protector 0x1F30, SkillCard 0x2E30,
// Tool TOOL_OFFSET_BY_DB_ID, Treasure 0x2A30. All wired & writable.
const STACK_CATEGORIES = new Set(["Consumable", "Protector", "Accessory", "Infiltration", "SkillCard", "Treasure"]);
// Read-only categories. Only Outfit remains frozen: offsets ARE mapped
// (get_item_owned_offset 0x3230+idx) but writability is frozen per decision
// D008 pending final live-diff sign-off. KeyItem is writable-but-GUARDED (S4),
// not unwired. (Drift resolved 2026-08-21 — docs/INVENTORY_UX_REVIEW.md R8.)
const UNWIRED_CATEGORIES = new Set(["Outfit"]);
function getItemById(id) { return (DB.items || []).find(it => String(it.id) === String(id)) || null; }
function isGearCategory(cat) { return GEAR_CATEGORIES.has(cat); }
function isStackCategory(cat) { return STACK_CATEGORIES.has(cat); }
// Normalized payload mirrors for gear sentinel
let INVENTORY_NORMALIZED = null; // { owned_gear, stacks, conflicts, mirror_mismatches, unknown } from /api/load
let KEY_ITEM_UNLOCKED = false; // S4 guard: Key Items editing disabled until confirm

// ── S5b Dual-view + Character chips (Plan Phase 1-2) ──────────────────
let INVENTORY_VIEW = "pouch"; // "pouch" | "catalog"  (ADR 0002)
let INVENTORY_CHARA = "All";  // filter chip value (name, not EN_NAME)
const THIEF_LABELS = ["Joker","Ryuji","Morgana","Ann","Yusuke","Makoto","Haru","Futaba","Akechi","Kasumi"];
const CHIP_SUPPORT_CATS = new Set(["Melee","Ranged","Protector","Outfit"]); // where owner matters
// id -> owner English label (parsed from data/Weapon*.txt col 5; hydrated after DB load)
const ITEM_OWNER_BY_ID = new Map();
let STAGED_DIRTY = new Set(); // item_ids with unsaved staged delta (shared buffer mirror)

// ── UX pass 2026-08-21 (docs/INVENTORY_UX_REVIEW.md R1-R9) ────────────
let MAIN_LIST_BATCH = 150;          // R7: incremental render for the main roster
let GLOBAL_SEARCH_QUERY = "";       // R3: cross-category search ("")
let INV_RENDER_IDS = [];            // flat ordered ids currently rendered (keyboard nav)
const CATEGORY_CLUSTER_ORDER = ["Consumable", "Infiltration", "SkillCard", "Melee", "Ranged", "Protector", "Accessory", "Treasure", "Outfit", "KeyItem"];
const CATEGORY_CLUSTERS = [         // R4: 10 tabs -> 4 labeled clusters
  { label: "🧪 CONSUMABLES", cats: ["Consumable", "Infiltration", "SkillCard"] },
  { label: "⚔️ EQUIPMENT", cats: ["Melee", "Ranged", "Protector", "Accessory"] },
  { label: "💎 VALUABLES", cats: ["Treasure", "Outfit"] },
  { label: "📜 KEY", cats: ["KeyItem"] },
];

function belongsToChara(itemId, chara) {
  if (chara === "All") return true;
  const own = ITEM_OWNER_BY_ID.get(String(itemId)) || ITEM_OWNER_BY_ID.get(Number(itemId));
  if (!own) return chara === "All"; // no owner data → only visible under All
  return own === chara || own === "All";
}
function setInventoryView(view) {
  INVENTORY_VIEW = view === "catalog" ? "catalog" : "pouch";
  MAIN_LIST_BATCH = 150; // R7
  document.getElementById("viewPouchBtn")?.classList.toggle("active", INVENTORY_VIEW === "pouch");
  document.getElementById("viewCatalogBtn")?.classList.toggle("active", INVENTORY_VIEW === "catalog");
  const hint = document.getElementById("viewScopeHint");
  const catalog = document.getElementById("catalogSizeHint");
  if (hint) hint.textContent = INVENTORY_VIEW === "pouch" ? "Owned items only — fix your bag." : "Full game catalog — browse & own.";
  if (catalog) catalog.textContent = INVENTORY_VIEW === "catalog" && DB.items ? `${DB.items.length} knowable items` : "";
  // hash persistence
  try { const u = new URL(window.location.href); u.hash = `inv=${INVENTORY_VIEW}&cat=${CURRENT_UNIFIED_CATEGORY}&who=${INVENTORY_CHARA}&q=${encodeURIComponent(UNIFIED_SEARCH_QUERY)}`; history.replaceState(null,"",u); } catch {}
  renderUnifiedItemList();
}
function setInventoryChara(chara) {
  INVENTORY_CHARA = THIEF_LABELS.includes(chara) || chara === "All" ? chara : "All";
  MAIN_LIST_BATCH = 150; // R7
  try { const u = new URL(window.location.href); u.hash = `inv=${INVENTORY_VIEW}&cat=${CURRENT_UNIFIED_CATEGORY}&who=${INVENTORY_CHARA}&q=${encodeURIComponent(UNIFIED_SEARCH_QUERY)}`; history.replaceState(null,"",u); } catch {}
  renderCharacterChips();
  renderUnifiedItemList();
}
function renderCharacterChips() {
  const bar = document.getElementById("inventoryCharaChips");
  if (!bar) return;
  const enabled = CHIP_SUPPORT_CATS.has(CURRENT_UNIFIED_CATEGORY);
  bar.style.display = enabled ? "flex" : "none";
  if (!enabled) return;
  bar.innerHTML = "";
  for (const label of ["All", ...THIEF_LABELS]) {
    const btn = document.createElement("button");
    btn.className = "filter-pill" + (INVENTORY_CHARA === label ? " active" : "");
    btn.innerHTML = `<span>${label}</span>`;
    btn.title = label === "All" ? "Show all owners" : `Only ${label}'s gear`;
    btn.onclick = () => setInventoryChara(label);
    bar.appendChild(btn);
  }
}
function hydrateItemOwnerMap() {
  // data/ role column ("主人公"/"高卷杏"...) is already mapped to English display names in server.py's REFERENCE_DB (`... (Joker)` suffix), so we extract parenthesized owner.
  for (const it of (DB.items || [])) {
    const m = it.name.match(/\((Joker|Ryuji|Morgana|Ann|Yusuke|Makoto|Haru|Futaba|Akechi|Kasumi|All)\)\s*$/);
    if (m) ITEM_OWNER_BY_ID.set(String(it.id), m[1]);
  }
}

// Canonical Category Visual Themes & Glyph Badges
const P5R_CATEGORY_THEMES = {
  Consumable:   { glyph: "HP",   color: "#00E5FF", bg: "#002B33", name: "Consumable / Healing" },
  Infiltration: { glyph: "TOOL", color: "#FFD600", bg: "#332B00", name: "Infiltration Tool" },
  SkillCard:    { glyph: "CARD", color: "#E040FB", bg: "#2E0033", name: "Skill Card" },
  Melee:        { glyph: "BLD",  color: "#FF3D00", bg: "#330D00", name: "Melee Weapon" },
  Ranged:       { glyph: "GUN",  color: "#76FF03", bg: "#133300", name: "Firearm / Gun" },
  Protector:    { glyph: "ARM",  color: "#2979FF", bg: "#001733", name: "Protector / Armor" },
  Outfit:       { glyph: "CLO",  color: "#D500F9", bg: "#280033", name: "Outfit & Costume" },
  Accessory:    { glyph: "ACC",  color: "#FF4081", bg: "#330018", name: "Accessory / Ring" },
  Treasure:     { glyph: "GEM",  color: "#FFE600", bg: "#003318", name: "Material & Loot" },
  KeyItem:      { glyph: "KEY",  color: "#FFAB00", bg: "#332200", name: "Key & Story Item" }
};

// In-Game Item Descriptions & Effect Dictionary
const P5R_ITEM_DESCRIPTIONS = {
  'Life Stone': 'Restores 30% HP to one ally.',
  'Lifestone': 'Restores 30% HP to one ally.',
  'Protein': 'Greatly increases HP / Muscle training workout item for the gym.',
  'Moist Protein': 'High-grade workout protein. Increases max HP during gym sessions.',
  'Imported Protein': 'Exclusive high-protein supplement from overseas.',
  'Recov-R: 50 mg': 'Restores 50 HP to one ally. Developed by Tae Takemi.',
  'Recov-R: 100 mg': 'Restores 100 HP to one ally. Developed by Tae Takemi.',
  'Takemedic': 'Restores 200 HP to one ally. Developed by Tae Takemi.',
  'Peppery Nikuman': 'Restores 80 HP to one ally. A spicy Tokyo street food snack.',
  'Juicy Nikuman': 'Restores 100 HP to one ally. Steaming hot and filled with broth.',
  'Napolitan Nikuman': 'Restores 120 HP to one ally. Western-style street snack.',
  'Foreign Nikuman': 'Restores 150 HP to one ally. Exotic street food.',
  'Bead': 'Fully restores HP to one ally.',
  'Party in a Can': 'Restores 50 HP to all allies. Carbonated celebratory soft drink.',
  'Corned Beef Special': 'Restores 100 HP to one ally. Premium canned ration.',
  'Takemedic-All': 'Restores 100 HP to all allies. Tae Takemi clinical prescription.',
  'Takemedic-All V': 'Restores 200 HP to all allies. Tae Takemi advanced clinical medicine.',
  'Takemedic-All Z': 'Restores 300 HP to all allies. Tae Takemi master formula.',
  'Bead Chain': 'Fully restores HP to all allies.',
  'Soul Drop': 'Restores 10 SP to one ally.',
  'Snuff Soul': 'Restores 50 SP to one ally.',
  'Chewing Soul': 'Restores 100 SP to one ally.',
  'Soul Food': 'Fully restores SP to one ally.',
  'Revival Bead': 'Revives one fallen ally with 50% HP.',
  'Balm of Life': 'Revives one fallen ally with full HP.',
  'Nohar-M': 'Cleanses Dizzy, Forget, Sleep, and Hunger from one ally.',
  'Relax Gel': 'Cleanses Confuse, Fear, and Despair from one ally.',
  'Alert Capsule': 'Cleanses Rage and Brainwash from one ally.',
  'Amrita Soda': 'Cleanses all non-special status ailments for one ally.',
  'Soma': 'Fully restores HP and SP of all allies. Cleanses negative status effects.',
  'Leblanc Coffee': 'Restores 30 SP to one ally. Brewed at Café Leblanc.',
  'Master Coffee': 'Restores 100 SP to one ally. Brewed with Sojiro’s master beans.',
  'Leblanc Curry': 'Restores 20 SP to all allies. Homemade spiced curry.',
  'Master Curry': 'Restores 50 SP to all allies. Masterfully aged secret recipe.',
  'Lockpick': 'Picks standard Palace and Mementos locked treasure chests.',
  'Eternal Lockpick': 'Infinite use lockpick. Opens any Palace locked chest without breaking.',
  'Vanish Ball': 'Guarantees immediate escape from standard shadow encounters in Palaces.',
  'Spotlight': 'Draws enemy attacks to the user for 3 turns.',
  'Goho-M': 'Instantly teleports the party back to the Palace safe room entrance.',
  'Megido Bomb': 'Deals 150 Almighty damage to all foes.',
  'SP Adhesive 3': 'Accessory. Automatically restores 7 SP at the start of every combat turn.',
  'Omnipotent Orb': 'Legendary accessory. Nullifies all magical and physical attacks except Almighty.',
  'Crystal of Greed': 'Will Seed ring. Grants Attack Master and Charge to the wearer.',
  'Blank Card': 'A blank skill card that Yusuke Kitagawa can duplicate any skill onto.'
};

function getItemDescription(item) {
  if (P5R_ITEM_DESCRIPTIONS[item.name]) {
    return P5R_ITEM_DESCRIPTIONS[item.name];
  }
  if (item.category === "SkillCard") return `Skill Card: Teaches ${item.name} to any Persona.`;
  if (item.category === "Melee") return `Melee weapon equipment. Equippable by specific Phantom Thief.`;
  if (item.category === "Ranged") return `Firearm equipment. Fires high-potency elemental/standard rounds.`;
  if (item.category === "Protector") return `Protective armor equipment. Enhances Defense and Magic Evade.`;
  if (item.category === "Accessory") return `Accessory. Grants passive buffs or active combat skills.`;
  if (item.category === "Infiltration") return `Infiltration tool crafted at Joker’s hideout workdesk.`;
  if (item.category === "Treasure") return `Valuable shadow loot item. Sellable to Iwai at Untouchable for yen.`;
  if (item.category === "KeyItem") return `Story essential item, book, or confidant bond keepsake.`;
  return `Persona 5 Royal consumable inventory item.`;
}

function switchItemCategory(cat, btnEl) {
  CURRENT_UNIFIED_CATEGORY = cat;
  MAIN_LIST_BATCH = 150; // R7: reset batch on filter change
  document.querySelectorAll("#unifiedItemTabs .filter-pill").forEach(el => el.classList.remove("active"));
  if (btnEl) btnEl.classList.add("active");
  // reset character chip if category no longer supports it (keeps state sane)
  if (!CHIP_SUPPORT_CATS.has(cat)) INVENTORY_CHARA = "All";
  renderCharacterChips();
  try { const u = new URL(window.location.href); u.hash = `inv=${INVENTORY_VIEW}&cat=${cat}&who=${INVENTORY_CHARA}&q=${encodeURIComponent(UNIFIED_SEARCH_QUERY)}`; history.replaceState(null,"",u); } catch {}
  renderUnifiedItemList();
}

function onUnifiedSearchInput() {
  UNIFIED_SEARCH_QUERY = (document.getElementById("unifiedItemSearchBox")?.value || "").toLowerCase().trim();
  MAIN_LIST_BATCH = 150; // R7
  try { const u = new URL(window.location.href); u.hash = `inv=${INVENTORY_VIEW}&cat=${CURRENT_UNIFIED_CATEGORY}&who=${INVENTORY_CHARA}&q=${encodeURIComponent(UNIFIED_SEARCH_QUERY)}`; history.replaceState(null,"",u); } catch {}
  renderUnifiedItemList();
}

// R3: cross-category search — overrides the active tab, results grouped by category
function onGlobalSearchInput() {
  GLOBAL_SEARCH_QUERY = (document.getElementById("globalItemSearchBox")?.value || "").toLowerCase().trim();
  MAIN_LIST_BATCH = 150; // R7
  const btn = document.getElementById("clearGlobalSearchBtn");
  if (btn) btn.style.display = GLOBAL_SEARCH_QUERY ? "inline-flex" : "none";
  renderUnifiedItemList();
}
function clearGlobalSearch() {
  const box = document.getElementById("globalItemSearchBox");
  if (box) box.value = "";
  GLOBAL_SEARCH_QUERY = "";
  MAIN_LIST_BATCH = 150;
  const btn = document.getElementById("clearGlobalSearchBtn");
  if (btn) btn.style.display = "none";
  renderUnifiedItemList();
}

function updateCategoryTabBadges() {
  const allOwned = Object.entries(INVENTORY_ITEM_COUNTS)
    .map(([idStr, qty]) => {
      const id = parseInt(idStr);
      const item = getItemById(id) || { id, category: "Consumable" };
      return { ...item, qty: parseInt(qty) };
    })
    .filter(it => it.qty > 0);

  const countByCat = (c) => allOwned.filter(it => it.category === c).length;

  if (document.getElementById("catBadgeConsumable")) document.getElementById("catBadgeConsumable").textContent = countByCat("Consumable");
  if (document.getElementById("catBadgeInfiltration")) document.getElementById("catBadgeInfiltration").textContent = countByCat("Infiltration");
  if (document.getElementById("catBadgeSkillCard")) document.getElementById("catBadgeSkillCard").textContent = countByCat("SkillCard");
  if (document.getElementById("catBadgeMelee")) document.getElementById("catBadgeMelee").textContent = countByCat("Melee");
  if (document.getElementById("catBadgeRanged")) document.getElementById("catBadgeRanged").textContent = countByCat("Ranged");
  if (document.getElementById("catBadgeProtector")) document.getElementById("catBadgeProtector").textContent = countByCat("Protector");
  if (document.getElementById("catBadgeOutfit")) document.getElementById("catBadgeOutfit").textContent = countByCat("Outfit");
  if (document.getElementById("catBadgeAccessory")) document.getElementById("catBadgeAccessory").textContent = countByCat("Accessory");
  if (document.getElementById("catBadgeTreasure")) document.getElementById("catBadgeTreasure").textContent = countByCat("Treasure");
  if (document.getElementById("catBadgeKeyItem")) document.getElementById("catBadgeKeyItem").textContent = countByCat("KeyItem");

  const totalDistinct = allOwned.length;
  const globalCounter = document.getElementById("globalOwnedCounter");
  if (globalCounter) {
    globalCounter.textContent = `${totalDistinct} DISTINCT ITEMS IN BAG`;
  }
}

// Authentic In-Game Effect Sort Priority (Matches In-Game Screenshots 1:1)
const P5R_ITEM_SORT_PRIORITY = {
  // 1. HP Single-Target Recovery & Protein Items (Top of In-Game Screen)
  'Life Stone': 100, 'Lifestone': 100, 'Protein': 101, 'Moist Protein': 102, 'Imported Protein': 103,
  'Recov-R: 50 mg': 104, 'Recov-R: 100 mg': 105, 'Takemedic': 106,
  'Peppery Nikuman': 107, 'Juicy Nikuman': 108, 'Napolitan Nikuman': 109, 'Foreign Nikuman': 110,
  'Bead': 111, 'Party in a Can': 112, 'Corned Beef Special': 113, 'Sandwich': 114, 'Surprise Sando': 115,
  'Dipped Katsu Sando': 116, 'Fruit Danish': 117, 'Yakisoba Pan': 118, 'Fried Bread': 119, 'Jam Bread': 120,
  'Melon Pan': 121, 'Big Bang Burger': 122, 'Earth Burger': 123, 'Moon Burger': 124, 'Supernova Burger': 125,
  'Saturn Fries': 126, 'Karaage King': 127, 'Spring Fruit Pack': 128, 'Phantom Wafers': 129, 'Soothing Soba': 130,
  'Agodashi Oden': 131, 'Nostalgic Steak': 132, 'Sincere Omelette': 133, 'Angel Tart': 134, 'Moon Dango': 135,
  'Mixed Nuts': 136, 'Beni-Azuma': 137, 'Legendary Yaki-Imo': 138, 'Ann Cream Puffs': 139, 'Makoto Donuts': 140,
  'Sadayo Taiyaki': 141, 'Ryuji Dog': 142, 'Strawberry Daifuku': 143, 'Bland Cheese': 144, 'Sharp Cheese': 145,
  'Rich Cheese': 146, 'Pumpkin Soup': 147, 'Devil Fruit': 148,

  // 2. HP Party-Target Recovery
  'Takemedic-All': 200, 'Takemedic-All V': 201, 'Takemedic-All Z': 202, 'Bead Chain': 203, 'Salvation S': 204,

  // 3. SP Recovery (Single & Party)
  'Soul Drop': 300, 'Snuff Soul': 301, 'Chewing Soul': 302, 'Soul Food': 303, 'Amateur Coffee': 304,
  'Harsh Coffee': 305, 'Relaxing Coffee': 306, 'Leblanc Coffee': 307, 'Master Coffee': 308, 'Bitter Coffee': 309,
  'Acidic Coffee': 310, 'Decent Curry': 311, 'Leblanc Curry': 312, 'Master Curry': 313, 'Fire Curry': 314,
  'Blaze Curry': 315, 'Inferno Curry': 316, 'Amateur Curry': 317, 'Strawberry Curry': 318, 'Moonlight Carrot': 319,
  'Sun Tomato': 320, 'Earth Beans': 321, 'Star Onion': 322, 'Water of Rebirth': 323, 'Hogyoku Apple': 324,

  // 4. Revival Items
  'Revival Bead': 400, 'Balm of Life': 401, 'Band-Ace': 402, 'Reviv-All': 403, 'Renew-All': 404,

  // 5. Status Ailments & Cleansers
  'Nohar-M': 500, 'Relax Gel': 501, 'Alert Capsule': 502, 'Amrita Soda': 503, 'Soma': 504, 'Hiranya': 505,
  'Muscle Drink': 506, 'Odd Morsel': 507, 'Rancid Gravy': 508, 'Kajaclear-R': 509, 'Kundaclear-R': 510,
  'Magic Ointment': 511, 'Physical Ointment': 512, 'Rasetsu Ofuda': 513, 'Idaten Ofuda': 514, 'Kongou Ofuda': 515,
  'Empowering Ofuda': 516, 'Debilitator Ofuda': 517, 'Invincible Ofuda': 518, 'Strength Up Ofuda': 519, 'Magic Up Ofuda': 520,

  // 6. Battle Offense & Elemental Items
  'Molotov Cocktail': 600, 'Blowtorch': 601, 'Freeze Spray': 602, 'Dry Ice': 603, 'Air Cannon': 604,
  'Vacuum Cutter': 605, 'Stun Gun': 606, 'Magneto Coil': 607, 'Megido Bomb': 608, 'Sacramental Bread': 609,
  'Straw Doll': 610, 'Hell Magatama': 611, 'Cyclone Magatama': 612, 'Frost Magatama': 613, 'Arc Magatama': 614,
  'Psycho Bomb': 615, 'Psy-Wheel': 616, 'Atom Match': 617, 'Nuke Cracker': 618, 'Happy Bomb': 619,
  'Segaki Rice': 620, 'Curse Bomb': 621, 'Five-Inch Nail': 622, 'Godly Magatama': 623, 'Blast Magatama': 624,
  'Holy Magatama': 625, 'Grudge Magatama': 626, 'Fire Magatama': 627, 'Gale Magatama': 628, 'Shock Magatama': 629,
  'Ice Magatama': 630, 'Nuke Magatama': 631, 'Psy Magatama': 632, 'Bless Magatama': 633, 'Curse Magatama': 634
};

function getItemSortRank(item) {
  if (!item) return 99999;
  if (item.category === "Consumable" && P5R_ITEM_SORT_PRIORITY[item.name]) {
    return P5R_ITEM_SORT_PRIORITY[item.name];
  }
  return 1000 + (Number(item.id) & 0x0FFF);
}

// Render the In-Game Active Carried Items Roster — S5b dual view + UX pass:
// R3 global search (grouped by category), R7 incremental batches, R2 per-item
// revert, R8 Outfit read-only branch, R5 context-menu/keyboard hooks.
const CATEGORY_LABELS = { Consumable: "🧪 CONSUMABLES", Infiltration: "🔑 INFILTRATION TOOLS", SkillCard: "🎴 SKILL CARDS", Melee: "🗡️ MELEE", Ranged: "🔫 GUNS", Protector: "🛡️ ARMOR", Accessory: "💍 ACCESSORIES", Treasure: "💎 TREASURE", Outfit: "👗 OUTFITS", KeyItem: "📜 KEY ITEMS" };
function catLabel(cat) { return CATEGORY_LABELS[cat] || cat.toUpperCase(); }

function renderUnifiedItemList() {
  const container = document.getElementById("unifiedItemListContainer");
  if (!container || !DB.items) return;

  updateCategoryTabBadges();
  renderCharacterChips();

  const isCatalog = INVENTORY_VIEW === "catalog";
  const globalMode = !!GLOBAL_SEARCH_QUERY;

  const matchesBase = (item) => {
    const matchCat = globalMode || CURRENT_UNIFIED_CATEGORY === "All" || item.category === CURRENT_UNIFIED_CATEGORY;
    const matchSearch = !UNIFIED_SEARCH_QUERY || item.name.toLowerCase().includes(UNIFIED_SEARCH_QUERY);
    const matchChara = CHIP_SUPPORT_CATS.has(item.category) ? belongsToChara(item.id, INVENTORY_CHARA) : true;
    return matchCat && matchSearch && matchChara;
  };

  // Grouped render model: [{label, cat, items}] — headers only in global mode.
  let groups = [];
  if (globalMode) {
    const hits = (DB.items || [])
      .filter(it => it.name.toLowerCase().includes(GLOBAL_SEARCH_QUERY))
      .map(it => {
        const qty = INVENTORY_ITEM_COUNTS[it.id] || 0;
        const owned = qty > 0;
        const qtyView = isGearCategory(it.category) ? (owned ? 1 : 0) : qty;
        return { ...it, qty: qtyView, owned };
      })
      .filter(it => matchesBase(it) && (isCatalog ? true : it.qty > 0));
    for (const cat of CATEGORY_CLUSTER_ORDER) {
      const items = hits.filter(it => it.category === cat).sort((a, b) => getItemSortRank(a) - getItemSortRank(b));
      if (items.length) groups.push({ label: catLabel(cat), cat, items });
    }
  } else if (isCatalog) {
    // Full game catalog: every knowable item, joined with owned flag
    const list = (DB.items || []).map(it => {
      const qty = INVENTORY_ITEM_COUNTS[it.id] || 0;
      const owned = qty > 0;
      const qtyView = isGearCategory(it.category) ? (owned ? 1 : 0) : qty;
      return { ...it, qty: qtyView, owned };
    }).filter(matchesBase);
    groups = [{ label: "", cat: CURRENT_UNIFIED_CATEGORY, items: list.sort((a, b) => {
      if (a.owned !== b.owned) return a.owned ? -1 : 1;
      return getItemSortRank(a) - getItemSortRank(b);
    }) }];
  } else {
    // Owned Pouch: only owned in this save
    const list = Object.entries(INVENTORY_ITEM_COUNTS)
      .map(([idStr, qty]) => {
        const id = parseInt(idStr);
        const item = getItemById(id) || { id, name: `Item 0x${id.toString(16).toUpperCase()}`, category: "Consumable" };
        return { ...item, qty: parseInt(qty), owned: parseInt(qty) > 0 };
      })
      .filter(it => matchesBase(it) && it.qty > 0);
    groups = [{ label: "", cat: CURRENT_UNIFIED_CATEGORY, items: list.sort((a, b) => getItemSortRank(a) - getItemSortRank(b)) }];
  }

  // Flatten (category headers only in global search mode) + batch (R7).
  const renderItems = [];
  groups.forEach(g => {
    if (globalMode && g.items.length) renderItems.push({ type: "header", label: `${g.label} · ${g.items.length}` });
    g.items.forEach(it => renderItems.push({ type: "item", item: it }));
  });
  const totalItems = renderItems.filter(r => r.type === "item").length;
  const visible = renderItems.slice(0, Math.max(MAIN_LIST_BATCH, 0));

  container.innerHTML = "";
  INV_RENDER_IDS = [];

  if (totalItems === 0) {
    const emptyTitle = globalMode ? "NO MATCHES" : (isCatalog ? "NO MATCH" : "POCKET IS EMPTY");
    const emptySub = globalMode ? `Nothing in the bag or catalog matches "${GLOBAL_SEARCH_QUERY}".`
      : isCatalog ? `No catalog items match your filters.`
      : `Joker is not carrying any ${CURRENT_UNIFIED_CATEGORY}${INVENTORY_CHARA !== "All" ? ` for ${INVENTORY_CHARA}` : ""} items right now.`;
    const emptyCTA = (isCatalog || globalMode) ? "" : `<button class="p5-btn-action" style="background:#FFFFFF; border-color:#FFFFFF; color:#000; font-weight:900; padding:8px 18px; margin-top:6px;" onclick="setInventoryView('catalog')"><span>📚 BROWSE FULL CATALOG</span></button>`;
    container.innerHTML = `
      <div style="text-align:center; padding:60px 20px; color:var(--p5-muted);">
        <div style="font-family:var(--font-p5); font-size:24px; color:var(--p5-white); margin-bottom:8px;">${emptyTitle}</div>
        <p style="font-size:12px; margin-bottom:16px;">${emptySub}</p>
        ${emptyCTA}
        ${globalMode ? "" : `<button class="p5-btn-action" style="background:#FFFFFF; border-color:#FFFFFF; color:#000; font-weight:900; padding:8px 18px; margin-left:6px;" onclick="openAddItemModal()">
          <span>+ ADD ${CURRENT_UNIFIED_CATEGORY.toUpperCase()} ITEM</span>
        </button>`}
      </div>
    `;
    renderItemDossierSpotlight();
    return;
  }

  // Auto-select first rendered item if none selected or selection off-screen
  const flatIds = renderItems.filter(r => r.type === "item").map(r => String(r.item.id));
  if (!SELECTED_ITEM_ID || !flatIds.includes(String(SELECTED_ITEM_ID))) {
    const first = renderItems.find(r => r.type === "item");
    if (first) SELECTED_ITEM_ID = first.item.id;
  }

  visible.forEach(entry => {
    if (entry.type === "header") {
      const h = document.createElement("div");
      h.style.cssText = "font-family:var(--font-p5); font-size:12px; color:var(--p5-white); background:#000; padding:4px 10px; border-left:4px solid var(--p5-crimson); transform:skew(-6deg); position:sticky; top:0; z-index:2;";
      h.innerHTML = `<span style="display:inline-block; transform:skew(6deg);">${entry.label}</span>`;
      container.appendChild(h);
      return;
    }
    const item = entry.item;
    const isSelected = String(item.id) === String(SELECTED_ITEM_ID);
    const theme = P5R_CATEGORY_THEMES[item.category] || P5R_CATEGORY_THEMES.Consumable;
    const isGear = isGearCategory(item.category);
    const isKey = item.category === "KeyItem";
    const isOutfit = item.category === "Outfit"; // R8: read-only frozen (D008)
    const isOwnedDimmed = isCatalog && !item.owned;

    const row = document.createElement("div");
    row.onclick = () => selectUnifiedItem(item.id);
    row.oncontextmenu = (e) => { e.preventDefault(); openInvContextMenu(e, item.id); }; // R5

    row.style.cssText = `
      background: ${isSelected ? 'linear-gradient(90deg, #E60012 0%, #B8000E 100%)' : (isOwnedDimmed ? '#0B0B12' : '#11151E')};
      border: 1px solid ${isSelected ? '#FFF' : (isOwnedDimmed ? '#1E2538' : '#26334D')};
      border-left: 6px solid ${isSelected ? '#FFF' : theme.color};
      padding: 8px 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      cursor: pointer;
      transform: skew(-4deg);
      box-shadow: ${isSelected ? '4px 4px 0 #000' : '2px 2px 0 #000'};
      transition: transform 0.1s ease, background 0.1s ease;
      margin-bottom: 2px;
      opacity: ${isOwnedDimmed ? '0.62' : '1'};
    `;
    // Staged dirty dot + per-item revert (R2)
    const dirty = STAGED_DIRTY.has(String(item.id)) || STAGED_DIRTY.has(item.id);
    const dirtyDot = dirty ? `<span title="Staged (unsaved)" style="width:8px; height:8px; background:#FFD54F; border-radius:50%; display:inline-block; margin-left:6px; box-shadow:0 0 6px #FFD54F;"></span>` : '';
    const revertBtn = dirty ? `<button title="Revert to saved value" style="background:#222; border:1px solid #FFD54F; color:#FFD54F; width:20px; height:20px; border-radius:3px; font-size:11px; cursor:pointer; display:inline-flex; align-items:center; justify-content:center;" onclick="event.stopPropagation();revertItemToBaseline(${item.id})">↺</button>` : '';
    // Mirror/conflict warning on this id
    const mm = (INVENTORY_NORMALIZED?.mirror_mismatches || []).some(m => String(m.item_id) === String(item.id));
    const cf = (INVENTORY_NORMALIZED?.conflicts || []).some(c => String(c.item_id) === String(item.id));
    const warnBadge = mm ? `<span title="Mirror mismatch — will heal on Save" style="font-size:10px; color:#FF5252; font-weight:800; margin-left:6px;">⚠ MIRROR</span>` : cf ? `<span title="Count-region wins over pouch cache" style="font-size:10px; color:#FFA726; font-weight:800; margin-left:6px;">⚠ CONFLICT</span>` : '';

    const gearBadge = isGear ? `<span style="font-size:11px; color:${theme.color}; font-weight:900; margin-left:6px;">${item.qty ? '◆ OWNED' : '◇ NOT OWNED'}</span>` : '';
    // keyBadge enriched with owner when relevant
    const ownerSuffix = (item.ownerOwner || ITEM_OWNER_BY_ID.get(String(item.id)) || "");
    const ownerChip = ownerSuffix ? `<span style="font-size:10px; color:#BBB; background:#1E1E2A; padding:1px 5px; border-radius:3px; margin-left:6px;">${ownerSuffix}</span>` : "";
    const keyBadge = isKey ? `<span style="font-size:10px; color:#FFAB00; font-weight:800; background:#332200; padding:1px 5px; border-radius:3px; margin-left:6px;">🔒 KEY</span>` : ownerChip;
    const outfitBadge = isOutfit ? `<span style="font-size:11px; color:${theme.color}; font-weight:900; margin-left:6px;">${item.qty ? '◆ OWNED' : '◇ NOT OWNED'}</span><span title="Outfit writability frozen per decision D008 pending final live-diff sign-off" style="font-size:10px; color:#888; background:#222; padding:1px 5px; border-radius:3px; margin-left:6px;">🔒 FROZEN</span>` : '';
    let controls;
    if (isOutfit) {
      controls = `<div style="display:flex; align-items:center; gap:6px; flex-shrink:0; transform:skew(4deg);">
           <span style="font-size:11px; color:${item.qty ? '#FFFFFF' : '#888'}; font-weight:800;">${item.qty ? 'OWNED' : 'NOT OWNED'}</span>
           <span style="font-size:10px; color:#666;">read-only</span>
         </div>`;
    } else if (isGear) {
      controls = `<div style="display:flex; align-items:center; gap:6px; flex-shrink:0; transform:skew(4deg);" onclick="event.stopPropagation();">
           <span style="font-size:11px; color:${(item.owned === false || item.qty === 0) ? '#888' : '#FFFFFF'}; font-weight:800;">${(item.owned === false || item.qty === 0) ? 'NOT OWNED' : 'OWNED'}</span>
           <button class="p5-btn-action" style="padding:2px 10px; font-size:11px; ${(item.owned === false || item.qty === 0) ? 'background:#FFFFFF; border-color:#FFFFFF; color:#000;' : 'background:#330000; border-color:#FF3333; color:#FF8888;'}" onclick="setUnifiedItemQty(${item.id}, ${(item.owned === false || item.qty === 0) ? 1 : 0})">
             <span>${(item.owned === false || item.qty === 0) ? 'OWN' : 'UNEQUIP'}</span>
           </button>
           ${revertBtn}
           ${isCatalog ? `<span style="font-size:10px; color:${warnBadge ? '#BBB' : '#666'};">${warnBadge || dirtyDot || ''}</span>` : (warnBadge+dirtyDot)}
         </div>`;
    } else if (isKey) {
      controls = `<div style="display:flex; align-items:center; gap:6px; flex-shrink:0; transform:skew(4deg);" onclick="event.stopPropagation();">
           <span style="font-size:10px; color:#FFAB00;">Guarded</span>
           <button style="background:${KEY_ITEM_UNLOCKED ? '#332200' : '#222'}; border:1px solid #FFAB00; color:#FFAB00; cursor:pointer; padding:2px 8px; font-size:11px; font-weight:800;" onclick="toggleKeyItemLock()" title="Toggle key-item editing">${KEY_ITEM_UNLOCKED ? 'UNLOCKED' : 'LOCKED'}</button>
           ${KEY_ITEM_UNLOCKED ? `<button style="background:#330000; border:1px solid #FF3333; color:#FF8888; cursor:pointer; width:24px; height:24px; border-radius:3px; font-size:11px; display:flex; align-items:center; justify-content:center;" onclick="setUnifiedItemQty(${item.id}, 0)" title="Remove (guarded)">✕</button>` : ''}
           ${revertBtn}
         </div>`;
    } else {
      controls = `<div style="display:flex; align-items:center; gap:6px; flex-shrink:0; transform:skew(4deg);" onclick="event.stopPropagation();">
           <button class="rank-stepper-btn" style="width:24px; height:24px; font-size:13px;" onclick="stepUnifiedItemQty(${item.id}, -1)">-</button>
           <div style="background:#000; border:1px solid ${isSelected ? '#FFF' : 'var(--p5-white)'}; min-width:55px; text-align:center; padding:2px 8px; font-family:var(--font-p5); font-size:15px; color:var(--p5-white); border-radius:12px; transform:skew(-6deg);">
             <span style="display:inline-block; transform:skew(6deg);">✕ ${item.qty}</span>
           </div>
           <button class="rank-stepper-btn" style="width:24px; height:24px; font-size:13px;" onclick="stepUnifiedItemQty(${item.id}, 1)">+</button>
           <button class="p5-btn-action" style="padding:2px 6px; font-size:10px; ${item.qty === 99 ? 'background:#FFFFFF; border-color:#FFFFFF; color:#000;' : ''}" onclick="setUnifiedItemQty(${item.id}, ${item.qty === 99 ? 1 : 99})">
             <span>${item.qty === 99 ? 'MAX' : '99x'}</span>
           </button>
           <button style="background:#330000; border:1px solid #FF3333; color:#FF8888; cursor:pointer; width:24px; height:24px; border-radius:3px; font-size:11px; display:flex; align-items:center; justify-content:center;" onclick="setUnifiedItemQty(${item.id}, 0)" title="Remove item from bag">✕</button>
           ${revertBtn}
         </div>`;
    }

    row.innerHTML = `
      <div style="display:flex; align-items:center; gap:10px; min-width:0; transform:skew(4deg);">
        <!-- Category Glyph Box -->
        <div style="background:${isSelected ? '#000' : theme.bg}; color:${theme.color}; border:1px solid ${isSelected ? '#FFF' : theme.color}; padding:2px 6px; font-weight:900; font-size:10px; border-radius:2px; letter-spacing:1px; flex-shrink:0;">
          ${theme.glyph}
        </div>
        <!-- Item Name -->
        <div style="font-family:var(--font-p5); font-size:16px; font-weight:800; color:#FFFFFF; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${item.name}">
          ${item.name}
        </div>
        ${gearBadge}${keyBadge}${outfitBadge}
      </div>

      ${controls}
    `;

    container.appendChild(row);
    INV_RENDER_IDS.push(String(item.id));
  });

  // R7: Load More (incremental batches — mirrors Cheat Shop pattern)
  if (renderItems.length > visible.length) {
    const loadMore = document.createElement("button");
    loadMore.className = "p5-btn-action";
    loadMore.style.cssText = "margin:8px auto; padding:6px 14px; font-size:12px;";
    loadMore.textContent = `Load more (${totalItems - Math.min(MAIN_LIST_BATCH, renderItems.length)} remaining)`;
    loadMore.onclick = () => { MAIN_LIST_BATCH += 150; renderUnifiedItemList(); };
    container.appendChild(loadMore);
  }

  renderItemDossierSpotlight();
}

// R2 — restore one id to its loaded-save value
function revertItemToBaseline(itemId) {
  let base = {};
  try { base = JSON.parse(window.__INVENTORY_BASELINE || "{}"); } catch {}
  const restored = base[String(itemId)] || 0;
  // Explicit 0 (never delete): display treats 0 as absent, and the payload
  // diff omits ids whose current value equals baseline.
  INVENTORY_ITEM_COUNTS[itemId] = restored;
  STAGED_DIRTY.delete(String(itemId)); STAGED_DIRTY.delete(itemId);
  refreshStagedBadge();
  renderUnifiedItemList();
  setStatus(`↺ Reverted to saved value.`);
}

// ── R5: Right-click context menu + keyboard navigation ─────────────────
function openInvContextMenu(e, itemId) {
  closeInvContextMenu();
  selectUnifiedItem(itemId);
  const item = getItemById(itemId);
  if (!item) return;
  const cat = item.category;
  const qty = INVENTORY_ITEM_COUNTS[itemId] || 0;
  const dirty = STAGED_DIRTY.has(String(itemId)) || STAGED_DIRTY.has(itemId);
  const actions = [];
  if (isGearCategory(cat)) {
    actions.push(qty > 0 ? { label: "◇ Unequip", fn: () => setUnifiedItemQty(itemId, 0) }
                         : { label: "◆ Own", fn: () => setUnifiedItemQty(itemId, 1) });
  } else if (cat === "KeyItem") {
    if (KEY_ITEM_UNLOCKED) actions.push({ label: "✕ Remove", fn: () => setUnifiedItemQty(itemId, 0) });
  } else {
    actions.push({ label: "＋ Add 1", fn: () => stepUnifiedItemQty(itemId, 1) });
    actions.push({ label: "⇪ Max 99", fn: () => setUnifiedItemQty(itemId, 99) });
    if (qty > 0) actions.push({ label: "⧉ Duplicate stack", fn: () => { INVENTORY_ITEM_COUNTS[itemId] = Math.min(99, qty * 2); _markDirty(itemId); renderUnifiedItemList(); } });
    actions.push({ label: "✕ Discard", fn: () => setUnifiedItemQty(itemId, 0) });
  }
  if (dirty) actions.push({ label: "↺ Revert", fn: () => revertItemToBaseline(itemId) });
  actions.push({ label: "⧬ Copy ID 0x" + Number(itemId).toString(16).toUpperCase(), fn: () => navigator.clipboard && navigator.clipboard.writeText("0x" + Number(itemId).toString(16).toUpperCase()) });

  const menu = document.createElement("div");
  menu.id = "invContextMenu";
  menu.style.cssText = "position:fixed; z-index:100000; background:#0E0E14; border:2px solid var(--p5-crimson); box-shadow:6px 6px 0 #000; min-width:180px; padding:4px;";
  menu.innerHTML = actions.map((a, i) =>
    `<div data-i="${i}" style="padding:7px 12px; font-family:var(--font-p5); font-size:13px; color:#FFF; cursor:pointer;">${a.label}</div>`).join("");
  menu.onclick = (ev) => {
    const idx = ev.target.dataset && ev.target.dataset.i;
    if (idx !== undefined && actions[idx]) { closeInvContextMenu(); actions[idx].fn(); }
  };
  document.body.appendChild(menu);
  const mw = menu.offsetWidth, mh = menu.offsetHeight;
  menu.style.left = Math.min(e.clientX, window.innerWidth - mw - 8) + "px";
  menu.style.top = Math.min(e.clientY, window.innerHeight - mh - 8) + "px";
}
function closeInvContextMenu() {
  const m = document.getElementById("invContextMenu");
  if (m) m.remove();
}
document.addEventListener("click", closeInvContextMenu);

function initInventoryKeyboard() {
  document.addEventListener("keydown", (e) => {
    const stage = document.getElementById("stage-inventory");
    if (!stage || !stage.offsetParent) return; // inventory stage not visible
    if (e.target && ["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName)) return;
    if (!INV_RENDER_IDS.length) return;
    const idx = INV_RENDER_IDS.findIndex(id => id === String(SELECTED_ITEM_ID));
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      const next = e.key === "ArrowDown" ? Math.min(INV_RENDER_IDS.length - 1, idx + 1) : Math.max(0, idx - 1);
      SELECTED_ITEM_ID = INV_RENDER_IDS[next];
      renderUnifiedItemList();
      const rows = document.querySelectorAll("#unifiedItemListContainer > div[style]");
      rows.forEach(r => { if (r.style.background.includes("E60012")) r.scrollIntoView({ block: "nearest" }); });
    } else if (e.key === "+" || e.key === "=") {
      stepUnifiedItemQty(SELECTED_ITEM_ID, 1);
    } else if (e.key === "-" || e.key === "_") {
      stepUnifiedItemQty(SELECTED_ITEM_ID, -1);
    } else if (e.key === "m" || e.key === "M") {
      setUnifiedItemQty(SELECTED_ITEM_ID, 99);
    } else if (e.key === "Delete") {
      setUnifiedItemQty(SELECTED_ITEM_ID, 0);
    } else if (e.key === "Escape") {
      closeInvContextMenu();
    }
  });
}

// ── R9: Share codes (single item / whole bag) ───────────────────────────
// Format: COH1.<base64 JSON {"items":[[id,qty],...]}> — Gibbed-code inspired.
function makeShareCode(entries) {
  const payload = JSON.stringify({ items: entries.map(([id, q]) => [Number(id), Number(q)]) });
  return "COH1." + btoa(payload);
}
function parseShareCode(code) {
  code = (code || "").trim();
  if (!code.startsWith("COH1.")) return null;
  try {
    const obj = JSON.parse(atob(code.slice(5)));
    if (!obj || !Array.isArray(obj.items)) return null;
    return obj.items.filter(([id, q]) => Number(id) > 0 && Number(q) >= 0)
                    .map(([id, q]) => [Number(id), Math.min(99, Number(q))]);
  } catch { return null; }
}
function copyItemShareCode(itemId) {
  const qty = INVENTORY_ITEM_COUNTS[itemId] || 0;
  if (!(qty > 0)) { alert("Item is not in the bag — nothing to share."); return; }
  const code = makeShareCode([[itemId, qty]]);
  navigator.clipboard.writeText(code);
  setStatus(`📋 Share code copied (${getItemById(itemId)?.name || "item"}).`);
}
function exportBagShareCode() {
  const entries = Object.entries(INVENTORY_ITEM_COUNTS).filter(([, q]) => q > 0);
  if (!entries.length) { alert("Bag is empty."); return; }
  navigator.clipboard.writeText(makeShareCode(entries));
  setStatus(`📋 Bag share code copied (${entries.length} distinct items).`);
}
function importBagShareCode() {
  const code = prompt("Paste a COH1 share code:");
  if (!code) return;
  const entries = parseShareCode(code);
  if (!entries) { alert("Invalid share code."); return; }
  let applied = 0;
  entries.forEach(([id, q]) => {
    const item = getItemById(id);
    const cat = item ? item.category : "Consumable";
    if (cat === "KeyItem" && !KEY_ITEM_UNLOCKED) return; // guarded stays guarded
    if (q <= 0) { INVENTORY_ITEM_COUNTS[id] = 0; }
    else { INVENTORY_ITEM_COUNTS[id] = isGearCategory(cat) ? 1 : Math.max(INVENTORY_ITEM_COUNTS[id] || 0, q); }
    _markDirty(id); applied++;
  });
  renderUnifiedItemList();
  setStatus(`📥 Imported ${applied} item(s) from share code (staged — RE-SIGN to apply).`);
}

// ── R1: Pending-changes receipt (review before RE-SIGN) ────────────────
let PENDING_REVIEW_PAYLOAD = null;
function buildPendingChangesReceipt(normPayload) {
  const lines = [];
  const nameOf = (id) => { const it = getItemById(id); return it ? it.name : `Item 0x${Number(id).toString(16).toUpperCase()}`; };
  Object.entries(normPayload.stacks || {}).forEach(([idStr, to]) => {
    const from = (JSON.parse(window.__INVENTORY_BASELINE || "{}")[String(idStr)]) || 0;
    lines.push({ text: `${nameOf(idStr)}: ${from} → ${to}`, kind: to > 0 ? "change" : "remove" });
  });
  Object.entries(normPayload.owned_gear || {}).forEach(([idStr, owned]) => {
    const from = (JSON.parse(window.__INVENTORY_BASELINE || "{}")[String(idStr)]) || 0;
    lines.push({ text: `${nameOf(idStr)}: ${from ? "OWNED" : "not owned"} → ${owned ? "OWNED ◆" : "not owned ◇"}`, kind: owned ? "change" : "remove" });
  });
  return lines;
}
function showPendingChangesModal(lines, onConfirm) {
  const modal = document.getElementById("pendingChangesModal");
  if (!modal) { onConfirm(); return; }
  const countEl = document.getElementById("pendingChangesCount");
  if (countEl) countEl.textContent = String(lines.length);
  const listEl = document.getElementById("pendingChangesList");
  if (listEl) {
    listEl.innerHTML = lines.map(l => `
      <div style="display:flex; align-items:center; gap:8px; padding:5px 10px; border-left:3px solid ${l.kind === "remove" ? "#FF5252" : "#FFE600"}; background:#11151E; margin-bottom:4px;">
        <span style="font-size:10px; font-weight:900; color:${l.kind === "remove" ? "#FF5252" : "#FFE600"};">${l.kind === "remove" ? "REMOVE" : "SET"}</span>
        <span style="font-size:13px; color:#FFF;">${l.text}</span>
      </div>`).join("");
  }
  const confirmBtn = document.getElementById("pendingChangesConfirm");
  if (confirmBtn) confirmBtn.onclick = () => { modal.style.display = "none"; onConfirm(); };
  modal.style.display = "flex";
}

function selectUnifiedItem(itemId) {
  SELECTED_ITEM_ID = itemId;
  renderUnifiedItemList();
}

// Render the Active Item Spotlight Dossier on the Right
function renderItemDossierSpotlight() {
  const container = document.getElementById("itemDossierSpotlight");
  const descText = document.getElementById("activeItemDescText");
  if (!container || !DB.items) return;

  const item = DB.items.find(it => String(it.id) === String(SELECTED_ITEM_ID));
  if (!item) {
    if (descText) descText.textContent = "Select an item from your bag or click '+ ADD ITEM' to add items.";
    container.innerHTML = `
      <div style="text-align:center; padding:80px 10px; color:var(--p5-muted);">
        <div style="font-family:var(--font-p5); font-size:26px; color:var(--p5-white); margin-bottom:8px;">★ POCKET EMPTY ★</div>
        <p style="font-size:12px; max-width:320px; margin:0 auto 16px auto;">You don't have any ${CURRENT_UNIFIED_CATEGORY} items in your bag.</p>
        <button class="p5-btn-action" style="background:#FFFFFF; border-color:#FFFFFF; color:#000; font-weight:900; padding:10px 20px;" onclick="openAddItemModal()">
          <span>+ BROWSE & ADD ITEMS</span>
        </button>
      </div>
    `;
    return;
  }

  const qty = INVENTORY_ITEM_COUNTS[item.id] || INVENTORY_ITEM_COUNTS[String(item.id)] || 0;
  const theme = P5R_CATEGORY_THEMES[item.category] || P5R_CATEGORY_THEMES.Consumable;
  const desc = getItemDescription(item);

  if (descText) {
    descText.textContent = desc;
  }

  container.innerHTML = `
    <div>
      <!-- Header Badge -->
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
        <span style="background:${theme.bg}; color:${theme.color}; border:1px solid ${theme.color}; font-size:11px; font-weight:900; padding:3px 8px; text-transform:uppercase; letter-spacing:1px; transform:skew(-6deg);">
          <span style="display:inline-block; transform:skew(6deg);">${theme.name}</span>
        </span>
        <span style="font-size:11px; color:var(--p5-muted); font-family:monospace;">ID: 0x${item.id.toString(16).toUpperCase()} (${item.id})</span>
      </div>

      <!-- Item Title -->
      <div style="font-family:var(--font-p5); font-size:32px; color:#FFF; line-height:1.1; margin-bottom:14px; text-shadow:2px 2px 0 #000;">
        ${item.name}
      </div>

      <!-- In-Game Description Card -->
      <div style="background:#0D0D14; border:2px solid #000; border-left:6px solid ${theme.color}; padding:14px; margin-bottom:20px; box-shadow:4px 4px 0 #000;">
        <div style="font-size:11px; font-weight:800; color:var(--p5-white); margin-bottom:4px; text-transform:uppercase;">IN-GAME EFFECT / STATS</div>
        <div style="font-size:14px; color:#E0E0EE; line-height:1.5;">
          ${desc}
        </div>
      </div>

      ${(() => {
        if (isGearCategory(item.category)) {
          const owned = qty > 0;
          return `<div style="background:#14141F; border:2px solid #000; padding:16px; margin-bottom:20px; box-shadow:4px 4px 0 #000; text-align:center;">
            <div style="font-size:11px; font-weight:800; color:var(--p5-muted); margin-bottom:8px; text-transform:uppercase;">OWNED STATUS</div>
            <div style="font-family:var(--font-p5); font-size:22px; color:${owned ? '#FFFFFF' : '#888'}; margin-bottom:10px;">${owned ? '◆ OWNED' : '◇ NOT OWNED'}</div>
            <button class="p5-btn-action" style="padding:8px 18px; ${owned ? 'background:#330000; border-color:#FF3333; color:#FF8888;' : 'background:#FFFFFF; border-color:#FFFFFF; color:#000;'}" onclick="setUnifiedItemQty(${item.id}, ${owned ? 0 : 1})">
              <span>${owned ? 'UNEQUIP / REMOVE' : 'OWN THIS GEAR'}</span>
            </button>
          </div>`;
        }
        if (item.category === "KeyItem") {
          const locked = !KEY_ITEM_UNLOCKED;
          return `<div style="background:#332200; border:2px solid #FFAB00; padding:16px; margin-bottom:20px; box-shadow:4px 4px 0 #000;">
            <div style="font-size:11px; font-weight:800; color:#FFAB00; margin-bottom:6px;">⚠ KEY ITEM — GUARDED</div>
            <div style="font-size:12px; color:#E0E0EE; margin-bottom:10px;">Story-flag risk — editing may break progression. Keep read-only unless you know what you're doing.</div>
            <button class="p5-btn-action" style="padding:6px 12px; background:${locked ? '#222' : '#FFAB00'}; border-color:#FFAB00; color:${locked ? '#FFAB00' : '#000'}" onclick="toggleKeyItemLock()">
              <span>${locked ? '🔒 UNLOCK FOR EDITING' : '🔓 LOCK AGAIN'}</span>
            </button>
          </div>`;
        }
        return `<div style="background:#14141F; border:2px solid #000; padding:16px; margin-bottom:20px; box-shadow:4px 4px 0 #000;">
          <div style="font-size:11px; font-weight:800; color:var(--p5-muted); margin-bottom:8px; text-transform:uppercase;">BAG QUANTITY</div>
          <div style="display:flex; align-items:center; gap:10px;">
            <button class="rank-stepper-btn" style="width:36px; height:36px; font-size:18px;" onclick="stepUnifiedItemQty(${item.id}, -10)">-10</button>
            <button class="rank-stepper-btn" style="width:36px; height:36px; font-size:18px;" onclick="stepUnifiedItemQty(${item.id}, -1)">-1</button>
            <div style="background:#000; border:2px solid var(--p5-white); min-width:80px; text-align:center; padding:6px 12px; font-family:var(--font-p5); font-size:24px; color:var(--p5-white);">
              ${qty}
            </div>
            <button class="rank-stepper-btn" style="width:36px; height:36px; font-size:18px;" onclick="stepUnifiedItemQty(${item.id}, 1)">+1</button>
            <button class="rank-stepper-btn" style="width:36px; height:36px; font-size:18px;" onclick="stepUnifiedItemQty(${item.id}, 10)">+10</button>
          </div>
        </div>`;
      })()}
    </div>

    <!-- Bottom Action Buttons -->
    <div style="display:flex; gap:10px;">
      ${isGearCategory(item.category)
        ? `<button class="p5-btn-action" style="flex:1; padding:10px; background:#330000; border-color:#FF3333; color:#FF8888;" onclick="setUnifiedItemQty(${item.id}, 0)"><span>DISCARD</span></button>
           <button class="p5-btn-action" title="Copy a COH1 share code for this item" style="padding:10px; background:#222; border-color:#444; color:#BBB;" onclick="copyItemShareCode(${item.id})"><span>📋</span></button>`
        : item.category === "KeyItem"
          ? `<button class="p5-btn-action" style="flex:1; padding:10px; background:#222; border-color:#444; color:#888;" disabled><span>READ-ONLY (UNLOCK TO EDIT)</span></button>`
          : `<button class="p5-btn-action" style="flex:1; padding:10px;" onclick="setUnifiedItemQty(${item.id}, 99)"><span>SET TO 99x (MAX)</span></button>
             <button class="p5-btn-action" style="flex:1; background:#330000; border-color:#FF3333; color:#FF8888; padding:10px;" onclick="setUnifiedItemQty(${item.id}, 0)"><span>DISCARD (REMOVE)</span></button>
             <button class="p5-btn-action" title="Copy a COH1 share code for this item" style="padding:10px; background:#222; border-color:#444; color:#BBB;" onclick="copyItemShareCode(${item.id})"><span>📋</span></button>`}
    </div>
  `;
}

function toggleKeyItemLock() {
  if (!KEY_ITEM_UNLOCKED) {
    if (!confirm("⚠ Key Items are story flags — editing may break progression (e.g. confidant locks, 3rd semester). Unlock anyway?")) return;
  }
  KEY_ITEM_UNLOCKED = !KEY_ITEM_UNLOCKED;
  renderUnifiedItemList();
}

function _markDirty(itemId) { STAGED_DIRTY.add(String(itemId)); refreshStagedBadge(); }
function _clearDirty(itemId) { STAGED_DIRTY.delete(String(itemId)); STAGED_DIRTY.delete(itemId); refreshStagedBadge(); }
function refreshStagedBadge() {
  const badge = document.getElementById("stagedDirtyBadge");
  const btn = document.getElementById("discardStagedBtn");
  const n = STAGED_DIRTY.size;
  if (badge) { badge.style.display = n ? "inline-block" : "none"; badge.textContent = `● ${n} STAGED`; }
  if (btn) btn.style.display = n ? "inline-flex" : "none";
}
function discardStagedChanges() {
  try {
    const base = JSON.parse(window.__INVENTORY_BASELINE || "{}");
    INVENTORY_ITEM_COUNTS = base;
    STAGED_DIRTY.clear();
    refreshStagedBadge();
    renderUnifiedItemList();
    setStatus("Staged changes discarded — reverted to loaded save.");
  } catch {}
}

function stepUnifiedItemQty(itemId, delta) {
  const item = getItemById(itemId);
  const cat = item ? item.category : "Consumable";
  if (isGearCategory(cat)) {
    // Gear is owned toggle — any step flips. Explicit 0 (NOT delete):
    // buildInventoryPayload() diffs vs baseline, so a zeroed entry persists.
    const cur = INVENTORY_ITEM_COUNTS[itemId] || 0;
    INVENTORY_ITEM_COUNTS[itemId] = cur ? 0 : 1;
    _markDirty(itemId);
    renderUnifiedItemList();
    return;
  }
  if (cat === "KeyItem" && !KEY_ITEM_UNLOCKED) {
    alert("🔒 Key Items are guarded — unlock first.");
    return;
  }
  if (cat === "KeyItem" && !confirm("Modify Key Item? May break story flags — proceed?")) return;
  const cur = INVENTORY_ITEM_COUNTS[itemId] || 0;
  const next = Math.max(0, Math.min(99, cur + delta));
  INVENTORY_ITEM_COUNTS[itemId] = next;
  _markDirty(itemId);
  renderUnifiedItemList();
}

function setUnifiedItemQty(itemId, targetQty) {
  const item = getItemById(itemId);
  const cat = item ? item.category : "Consumable";
  if (isGearCategory(cat)) {
    INVENTORY_ITEM_COUNTS[itemId] = targetQty > 0 ? 1 : 0;
    _markDirty(itemId);
    renderUnifiedItemList();
    return;
  }
  if (cat === "KeyItem" && !KEY_ITEM_UNLOCKED) {
    alert("🔒 Key Items are guarded — unlock first.");
    return;
  }
  if (cat === "KeyItem" && targetQty !== 0 && !confirm("Modify Key Item? May break story flags — write anyway?")) return;
  INVENTORY_ITEM_COUNTS[itemId] = Math.max(0, Math.min(99, targetQty));
  _markDirty(itemId);
  renderUnifiedItemList();
}

// S2 persistence contract (RFC 6902 lesson: deletion must be EXPLICIT).
// Emits the minimal change-set vs __INVENTORY_BASELINE: untouched ids are
// OMITTED (server merge-patch semantics leave them alone — safe for
// incomplete reads & guarded categories), while user-zeroed ids are sent
// as explicit 0/false so discards actually persist.
function buildInventoryPayload() {
  const normPayload = { stacks: {}, owned_gear: {} };
  let base = {};
  try { base = JSON.parse(window.__INVENTORY_BASELINE || "{}"); } catch {}
  const ids = new Set([...Object.keys(base), ...Object.keys(INVENTORY_ITEM_COUNTS)]);
  ids.forEach(idStr => {
    const id = parseInt(idStr);
    const cur = INVENTORY_ITEM_COUNTS[id] || 0;
    const was = base[idStr] || 0;
    if (cur === was) return; // untouched — omit entirely
    const item = getItemById(id);
    const cat = item ? item.category : "Consumable";
    if (cat === "KeyItem" && !KEY_ITEM_UNLOCKED) return; // guarded: never emit
    if (isGearCategory(cat)) {
      normPayload.owned_gear[id] = cur > 0;
    } else {
      normPayload.stacks[id] = Math.max(0, Math.min(99, cur));
    }
  });
  return normPayload;
}

// =========================================================================
// ADD ITEM MODAL / CATALOG BROWSER
// =========================================================================
let MODAL_SEARCH_QUERY = "";
let MODAL_BATCH_SIZE = 50; // incremental virtualization (replaces slice(0,50) hard limit)

function openAddItemModal() {
  const modal = document.getElementById("addItemModal");
  const title = document.getElementById("modalCategoryTitle");
  if (!modal) return;
  if (title) title.textContent = `CHEAT SHOP — ${CURRENT_UNIFIED_CATEGORY.toUpperCase()}`;
  MODAL_SEARCH_QUERY = "";
  MODAL_BATCH_SIZE = 50;
  if (document.getElementById("modalItemSearchBox")) document.getElementById("modalItemSearchBox").value = "";
  modal.style.display = "flex";
  renderModalCatalog();
}

function closeAddItemModal() {
  const modal = document.getElementById("addItemModal");
  if (modal) modal.style.display = "none";
  renderUnifiedItemList();
}

function onModalSearchInput() {
  MODAL_SEARCH_QUERY = (document.getElementById("modalItemSearchBox")?.value || "").toLowerCase().trim();
  renderModalCatalog();
}

function renderModalCatalog() {
  const container = document.getElementById("modalCatalogList");
  if (!container || !DB.items) return;

  // Cheat Shop — single-category scoped (inherits main-tab category + chara chip).
  // NO global "All 2,204" desync; search is category-scoped. Unwired categories
  // (Outfit/KeyItem/SkillCard/Treasure/Infiltration) render read-only rows.
  const catalog = DB.items
    .filter(item => {
      const matchCat = item.category === CURRENT_UNIFIED_CATEGORY;
      const matchSearch = !MODAL_SEARCH_QUERY || item.name.toLowerCase().includes(MODAL_SEARCH_QUERY);
      return matchCat && matchSearch;
    })
    .sort((a, b) => getItemSortRank(a) - getItemSortRank(b));

  container.innerHTML = "";

  // ---- totals header ----
  const ownedCount = catalog.filter(it => (INVENTORY_ITEM_COUNTS[it.id] || 0) > 0).length;
  const totalsDiv = document.createElement("div");
  totalsDiv.style.cssText = "font-size:11px; color:var(--p5-muted); padding:6px 12px 8px 12px; border-bottom:1px solid #26334D;";
  totalsDiv.textContent = `Showing 1–${Math.min(MODAL_BATCH_SIZE, catalog.length)} of ${catalog.length} · ${ownedCount} Owned · ${catalog.length - ownedCount} Missing`;
  container.appendChild(totalsDiv);

  if (catalog.length === 0) {
    container.innerHTML += `
      <div style="text-align:center; padding:30px; color:var(--p5-muted);">
        <div style="font-family:var(--font-p5); font-size:18px; color:var(--p5-white); margin-bottom:4px;">NO ITEMS FOUND</div>
        <p style="font-size:12px;">No item matches "${MODAL_SEARCH_QUERY}".</p>
      </div>
    `;
    return;
  }

  // ---- incremental batch render (replaces hard 50-slice) ----
  const batch = catalog.slice(0, MODAL_BATCH_SIZE);
  batch.forEach(item => {
    const curQty = INVENTORY_ITEM_COUNTS[item.id] || 0;
    const isOwned = curQty > 0;
    const isGear = isGearCategory(item.category);
    const isKey = item.category === "KeyItem";
    const isUnwired = UNWIRED_CATEGORIES.has(item.category);
    const theme = P5R_CATEGORY_THEMES[item.category] || P5R_CATEGORY_THEMES.Consumable;

    // Action buttons — KeyItem guarded-add first; Outfit read-only (D008 freeze)
    let actionBtns;
    if (isKey) {
      actionBtns = `<button class="p5-btn-action" style="padding:4px 10px; font-size:11px; background:#332200; border-color:#FFAB00; color:#FFAB00;" onclick="addItemFromModal(${item.id}, 1)"><span>🔒 ADD KEY</span></button>`;
    } else if (isUnwired) {
      actionBtns = `<button class="p5-btn-action" style="padding:4px 10px; font-size:11px; background:#333; border-color:#555; color:#888; cursor:not-allowed;" disabled title="Outfit writability frozen per decision D008 pending final live-diff sign-off"><span>🔒 FROZEN</span></button>`;
    } else if (isGear) {
      actionBtns = `<button class="p5-btn-action" style="padding:4px 10px; font-size:11px; ${isOwned ? 'background:#330000; border-color:#FF3333; color:#FF8888;' : 'background:#FFFFFF; border-color:#FFFFFF; color:#000;'}" onclick="addItemFromModal(${item.id}, 1)"><span>${isOwned ? 'OWNED ◆' : 'OWN'}</span></button>`;
    } else {
      actionBtns = `<button class="p5-btn-action" style="padding:4px 10px; font-size:11px;" onclick="addItemFromModal(${item.id}, 1)"><span>+ 1x</span></button>
         <button class="p5-btn-action" style="padding:4px 10px; font-size:11px; background:#FF9F1C; border-color:#FF9F1C; color:#000;" onclick="addItemFromModal(${item.id}, 99)"><span>+ 99x</span></button>`;
    }

    const row = document.createElement("div");
    row.style.cssText = `
      background: ${isOwned ? '#142018' : '#14141E'};
      border: 1px solid ${isOwned ? '#FFE600' : '#26334D'};
      border-left: 4px solid ${theme.color};
      padding: 8px 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
    `;

    row.innerHTML = `
      <div style="flex:1; min-width:0;">
        <div style="display:flex; align-items:center; gap:6px;">
          <span style="font-size:9px; font-weight:900; color:${theme.color}; background:#000; padding:1px 4px; border:1px solid ${theme.color}; text-transform:uppercase;">
            ${theme.glyph}
          </span>
          <span style="font-family:var(--font-p5); font-size:15px; color:#FFF; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
            ${item.name}
          </span>
          ${isOwned ? `<span style="font-size:10px; color:#FFFFFF; font-weight:800; background:#003311; padding:0 5px; border-radius:3px;">${isGear ? 'OWNED ◆' : `IN BAG (✕${curQty})`}</span>` : ''}
          ${isGear && !isOwned ? `<span style="font-size:10px; color:#888; font-weight:800; background:#222; padding:0 5px; border-radius:3px;">NOT OWNED ◇</span>` : ''}
          ${isUnwired ? `<span title="Outfit writability frozen per decision D008 pending final live-diff sign-off" style="font-size:9px; color:#888; font-weight:800; background:#222; padding:0 5px; border-radius:3px;">🔒 READ-ONLY · FROZEN</span>` : ''}
        </div>
        <div style="font-size:11px; color:#999; margin-top:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
          ${getItemDescription(item)}
        </div>
      </div>

      <div style="display:flex; align-items:center; gap:6px; flex-shrink:0;">
        ${actionBtns}
      </div>
    `;

    container.appendChild(row);
  });

  // ---- Load More (incremental virtualization) ----
  if (catalog.length > MODAL_BATCH_SIZE) {
    const loadMore = document.createElement("button");
    loadMore.className = "p5-btn-action";
    loadMore.style.cssText = "margin:8px 12px; padding:6px 14px; font-size:12px;";
    loadMore.textContent = `Load ${Math.min(50, catalog.length - MODAL_BATCH_SIZE)} more`;
    loadMore.onclick = () => {
      MODAL_BATCH_SIZE = Math.min(MODAL_BATCH_SIZE + 50, 300); // hard cap — never render >300 DOM rows
      renderModalCatalog();
    };
    container.appendChild(loadMore);
  }
}

function addItemFromModal(itemId, addQty) {
  const item = getItemById(itemId);
  const cat = item ? item.category : "Consumable";
  if (isGearCategory(cat)) {
    INVENTORY_ITEM_COUNTS[itemId] = 1;
  } else if (cat === "KeyItem") {
    if (!KEY_ITEM_UNLOCKED && !confirm("Add Key Item? Story-flag risk — proceed?")) return;
    if (!KEY_ITEM_UNLOCKED) KEY_ITEM_UNLOCKED = true;
    INVENTORY_ITEM_COUNTS[itemId] = 1;
  } else {
    const cur = INVENTORY_ITEM_COUNTS[itemId] || 0;
    INVENTORY_ITEM_COUNTS[itemId] = Math.min(99, cur + addQty);
  }
  SELECTED_ITEM_ID = itemId;
  _markDirty(itemId);          // shared staged buffer — main tab pill shows ● STAGED
  renderModalCatalog();
  renderUnifiedItemList();
}

// Batch Actions
// maxCurrentTabItems() — REMOVED (bulk-own any category crosses unwired offsets 0xA000+/0x9000+/0x4000+;
// one-click corruption vector killed per speedrunner review — see docs/ITEM_STUDIO_REBUILD_PLAN.md §8)

function stockLeblancKitchen() {
  // Consumable-only preset (0x2000, verified 0x2530 base) — safe bulk write.
  const leblancItems = [
    8355, 8358, 8359, 8360, 8361, // Leblanc Coffee, Master Coffee, Decent Curry, Leblanc Curry, Master Curry
    8215, 8203, 8204, 8205, 8206  // Soma, Soul Drop, Snuff Soul, Chewing Soul, Soul Food
  ];
  if (!confirm(`Stock 99x of ${leblancItems.length} Leblanc consumables?`)) return;
  leblancItems.forEach(id => {
    INVENTORY_ITEM_COUNTS[id] = 99;
  });
  renderUnifiedItemList();
}

// stockInfiltrationKit() — REMOVED (writes Infiltration 0x6000, count-array offset UNVERIFIED by 2-save diff;
// docs/ITEM_STUDIO_REBUILD_PLAN.md §8 Risk: scope creep into wiring)

function stockClinicMedicine() {
  // Clinic meds = all Consumable 0x2000 (verified 0x2530..0x2600) — safe to 99x.
  const clinicIds = [
    8194, 8195, 8196, 8199, 8200, 8201, 8202, // Recov-R, Takemedic, Takemedic-All V/Z
    8207, 8208, 8210, 8211, 8212, 8216        // Revival Bead, Balm of Life, Nohar-M, Relax Gel, Amrita Soda
  ];
  if (!confirm(`Stock 99x of ${clinicIds.length} clinic meds?`)) return;
  clinicIds.forEach(id => {
    INVENTORY_ITEM_COUNTS[id] = 99;
  });
  renderUnifiedItemList();
}

function clearAllPouchItems() {
  if (confirm("Clear all carried items from Joker's bag?")) {
    INVENTORY_ITEM_COUNTS = {};
    renderUnifiedItemList();
  }
}

function renderInventoryViews() {
  renderUnifiedItemList();
}

function getCategoryColor(cat) {
  const theme = P5R_CATEGORY_THEMES[cat];
  return theme ? theme.color : "var(--p5-white)";
}

// 1-Click God Build Injectors
function injectGodBuild(buildKey) {
  if (!CURRENT_SAVE) {
    alert("Please load a save file first.");
    return;
  }
  const build = GOD_BUILDS[buildKey];
  if (!build) return;

  // Switch to Joker / Slot 0
  const mem = CURRENT_SAVE.party[0];
  if (!mem) return;

  // NOTE: deliberately does NOT touch mem.level / mem.hp / mem.sp — a god
  // build is the PERSONA, not Joker's own stats (fixed 2026-08-16 after
  // user feedback: injecting a build forced Joker to Lv99/999HP/999SP).

  const makeEntry = () => ({
    slot: 0,
    persona_id: build.persona_id,
    persona: DB.personas.find(p => p.id === build.persona_id)?.name || "God Persona",
    level: build.level,
    trait_id: build.trait_id,
    exp: 9999999,
    skills: build.skills,
    stats: [99, 99, 99, 99, 99],
    empty: false,
    flags: 1
  });

  const stock = CURRENT_SAVE.joker_stock || [];

  // 1. Already own this god persona? Update its slot in place (no dupes,
  //    no clobbering a different persona). Fixed 2026-08-16: the injector
  //    used to overwrite stock slot 0 blindly, destroying the previous god
  //    build on every injection.
  let target = stock.findIndex(s => s && !s.empty && s.persona_id === build.persona_id);
  let action;
  if (target >= 0) {
    action = "updated in place";
  } else {
    // 2. First empty slot (empty entries are all-zero 48-byte records).
    target = stock.findIndex(s => !s || s.empty || !s.persona_id);
    if (target < 0) {
      alert("⚠ All 12 persona stock slots are full — free a slot before injecting a God build.");
      return;
    }
    action = `placed in slot ${target}`;
  }

  const entry = makeEntry();
  entry.slot = target;
  stock[target] = entry;

  // 3. Equip it: slot 0 is the equipped persona, so swap in the client
  //    model (mirrors the backend equip_persona swap semantics).
  if (target !== 0) {
    const displaced = stock[0] || { slot: 0, persona_id: 0, level: 0, empty: true, flags: 0, persona: null, skills: [], stats: [] };
    entry.slot = 0;
    displaced.slot = target;
    stock[0] = entry;
    stock[target] = displaced;
  }

  // Equipped-persona block mirrors stock slot 0.
  mem.persona = { ...stock[0] };

  // Switch to Velvet Room Stage to show
  switchStage('velvet_room');
  document.getElementById("partyMemberSelect").value = 0;
  ACTIVE_STOCK_SLOT = 0;
  renderActiveMember();
  renderStockChips();
  alert(`★ God-Tier Build (${buildKey.toUpperCase()}) ${action} and equipped to Joker!`);
}

// Save Changes & Re-Sign
async function saveActiveSaveFile() {
  if (!CURRENT_SAVE || !CURRENT_FILE_PATH) {
    alert("No active save file loaded.");
    return;
  }

  // Check for Sequence Breaking Risks
  const risks = collectAllSequenceBreakRisks();
  if (risks.length > 0) {
    const listEl = document.getElementById("safetyWarningList");
    if (listEl) {
      listEl.innerHTML = risks.map(r => `
        <div style="background:rgba(0,0,0,0.5); border-left:3px solid #FF9F1C; padding:8px 10px; border-radius:0 4px 4px 0; font-size:11px;">
          <div style="font-weight:800; color:var(--p5-white); margin-bottom:2px;">${r.arcana}: <span style="color:#FF9F1C;">${r.badge}</span></div>
          <div style="color:#A0A0B5;">${r.detail}</div>
        </div>
      `).join("");
    }
    const modal = document.getElementById("sequenceBreakSafetyModal");
    if (modal) {
      modal.classList.add("open");
      return;
    }
  }

  await executeSavePayload();
}

async function executeSavePayload(skipReview) {
  if (!CURRENT_SAVE || !CURRENT_FILE_PATH) return;

  // Persist Header & Profile Inputs
  if (!CURRENT_SAVE.header) CURRENT_SAVE.header = {};
  CURRENT_SAVE.header.fname = document.getElementById("inputFname").value || "";
  CURRENT_SAVE.header.lname = document.getElementById("inputLname").value || "";
  CURRENT_SAVE.header.group_name = document.getElementById("inputGroupName").value || "";
  CURRENT_SAVE.header.money = parseInt(document.getElementById("inputMoney").value) || 0;

  // Ensure current active deck inputs are persisted
  if (CURRENT_SAVE.party && CURRENT_SAVE.party[ACTIVE_MEMBER_INDEX]) {
    const mem = CURRENT_SAVE.party[ACTIVE_MEMBER_INDEX];
    mem.level = parseInt(document.getElementById("memberLevel").value) || 1;
    mem.hp = parseInt(document.getElementById("memberHP").value) || 100;
    mem.sp = parseInt(document.getElementById("memberSP").value) || 50;

    if (!mem.persona) mem.persona = {};
    mem.persona.persona_id = parseInt(document.getElementById("personaSelect").value) || 1;
    mem.persona.level = parseInt(document.getElementById("personaLevel").value) || 1;
    mem.persona.trait_id = parseInt(document.getElementById("personaTraitSelect").value) || 0;

    const stats = [
      parseInt(document.getElementById("stat_st").value) || 10,
      parseInt(document.getElementById("stat_ma").value) || 10,
      parseInt(document.getElementById("stat_en").value) || 10,
      parseInt(document.getElementById("stat_ag").value) || 10,
      parseInt(document.getElementById("stat_lu").value) || 10
    ];
    mem.persona.stats = stats;

    const skills = [];
    for (let i = 0; i < 8; i++) {
      const el = document.getElementById(`skillSlot_${i}`);
      skills.push(el ? parseInt(el.value) || 0 : 0);
    }
    mem.persona.skills = skills;
  }

  // Persist Active Inventory — S1 normalized payload (preferred) + legacy
  // Minimal change-set vs load baseline: removals are EXPLICIT (0/false),
  // untouched ids omitted (server merge-patch leaves them alone).
  const normPayload = buildInventoryPayload();

  // R1: review receipt before the irreversible write
  const changeCount = Object.keys(normPayload.stacks).length + Object.keys(normPayload.owned_gear).length;
  if (!skipReview && changeCount > 0) {
    showPendingChangesModal(buildPendingChangesReceipt(normPayload), () => executeSavePayload(true));
    return;
  }
  CURRENT_SAVE.inventory_normalized = normPayload;
  // Legacy flat list also sent for backwards compat
  CURRENT_SAVE.inventory = [];
  let slotIdx = 0;
  Object.entries(INVENTORY_ITEM_COUNTS).forEach(([idStr, qty]) => {
    if (qty > 0) {
      const id = parseInt(idStr);
      const item = getItemById(id);
      const cat = item ? item.category : "Consumable";
      if (cat === "KeyItem" && !KEY_ITEM_UNLOCKED) return;
      const q = isGearCategory(cat) ? 1 : parseInt(qty);
      CURRENT_SAVE.inventory.push({ slot: slotIdx++, item_id: id, quantity: q });
    }
  });

  // Attach modified Compendium registration state
  if (COMPENDIUM_DATA) {
    CURRENT_SAVE.compendium = COMPENDIUM_DATA;
  }
  if (UNLOCK_COMPENDIUM_PENDING) {
    CURRENT_SAVE.unlock_compendium = true;
  }

  setStatus("Creating timestamped backup & re-signing save...");
  try {
    const res = await fetch("/api/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(CURRENT_SAVE)
    });
    const result = await res.json();
    if (result.error) {
      alert("Save Failed: " + result.error);
      setStatus("Error: " + result.error);
      return;
    }

    updateIntegrityBadge(result.integrity);
    refreshBackups();
    STAGED_DIRTY.clear(); refreshStagedBadge();
    UNLOCK_COMPENDIUM_PENDING = false;
    delete CURRENT_SAVE.unlock_compendium;
    window.__INVENTORY_BASELINE = JSON.stringify(INVENTORY_ITEM_COUNTS);
    // mirror/conflict will refresh on next load
    if (result.notice) renderSameSaveNotice(result.notice);
    if (result.download_data) {
      // Trigger instant browser download for uploaded files
      const blob = new Blob([Uint8Array.from(atob(result.download_data), c => c.charCodeAt(0))], { type: "application/octet-stream" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = CURRENT_FILE_PATH.replace(/^Uploaded \((.*)\)$/, "$1") || "DATA.DAT";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setStatus(`✔ Changes re-signed & downloaded as ${a.download}!`);
      alert(`★ Save successful! Downloaded updated save file (${a.download}) with verified AES & CRCs.`);
    } else {
      setStatus(`✔ Changes re-signed & saved! Auto-backup created: ${result.backup}`);
      alert("★ Save successful! CRCs & AES integrity verified and re-signed.");
    }
  } catch (err) {
    console.error("Save error:", err);
    setStatus("Failed to save changes.");
  }
}

// Backups
async function refreshBackups() {
  try {
    const res = await fetch("/api/backups");
    const data = await res.json();
    const select = document.getElementById("backupSelectDropdown");
    select.innerHTML = "";
    if (data.backups && data.backups.length > 0) {
      data.backups.forEach((b) => {
        const opt = document.createElement("option");
        opt.value = b;
        opt.textContent = `💾 ${b}`;
        select.appendChild(opt);
      });
    } else {
      select.innerHTML = `<option value="">-- No backups created yet --</option>`;
    }
  } catch (err) {
    console.error("Backups error:", err);
  }
}

async function restoreSelectedBackup() {
  const bname = document.getElementById("backupSelectDropdown").value;
  if (!bname) {
    alert("Select a backup first.");
    return;
  }
  if (!confirm(`Restore ${bname}? The current state will be backed up first.`)) return;

  try {
    const res = await fetch("/api/restore", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ backup_name: bname })
    });
    const data = await res.json();
    if (data.error) {
      alert("Restore failed: " + data.error);
      return;
    }
    alert(`Restored successfully! Prior state preserved in ${data.safety_backup}`);
    loadSaveFile();
  } catch (err) {
    alert("Restore error: " + err);
  }
}

// Navigation Stages (Snappy, Instant P5R Switching)
function switchStage(stageId, btnEl) {
  P5Audio.playSwitch();
  document.querySelectorAll(".p5-stage-view").forEach((el) => el.classList.remove("active"));
  document.querySelectorAll(".p5-nav-item").forEach((el) => el.classList.remove("active"));

  const target = document.getElementById(`stage-${stageId}`);
  if (target) {
    target.classList.add("active");
  }

  if (btnEl) {
    btnEl.classList.add("active");
  } else {
    const defaultBtn = document.querySelector(`.p5-nav-item[onclick*="'${stageId}'"]`);
    if (defaultBtn) defaultBtn.classList.add("active");
  }

  if (stageId === "inventory") {
    renderUnifiedItemList();
  } else if (stageId === "confidants") {
    renderConfidants();
  } else if (stageId === "compendium") {
    renderCompendium();
  }
}
function updateIntegrityBadge(rep) {
  const pill = document.getElementById("sidebarHealthPill");
  const text = document.getElementById("sidebarHealthText");
  if (!rep) return;

  if (rep.ok) {
    pill.className = "status-pill ok";
    text.textContent = "✔ AES + CRC SIGNED & VERIFIED";
  } else {
    pill.className = "status-pill";
    text.textContent = "✘ INTEGRITY MISMATCH";
  }
}

function setStatus(msg) {
  const el = document.getElementById("bottomStatus");
  if (el) el.textContent = msg;
}
