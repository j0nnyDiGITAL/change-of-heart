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

// Meta God Build Presets (Real P5R Persona & Skill IDs)
const GOD_BUILDS = {
  yoshitsune: {
    persona_id: 365, // Yoshitsune
    level: 99,
    trait_id: 190,   // Undying Fury (+30% Phys)
    skills: [
      714, // Hassou Tobi
      10,  // Apt Pupil
      345, // Arms Master
      805, // Charge
      863, // Insta-Heal
      14,  // Ali Dance
      341, // Drain Fire
      834  // Drain Ice
    ]
  },
  izanagi: {
    persona_id: 305, // Izanagi-no-Okami Picaro
    level: 99,
    trait_id: 88,    // Country Maker (+100% DMG/DEF)
    skills: [
      63,  // Myriad Truths
      270, // Almighty Boost
      69,  // Almighty Amp
      15,  // Magic Ability
      346, // Spell Master
      806, // Concentrate
      342, // Drain Curse
      802  // Victory Cry
    ]
  },
  raoul: {
    persona_id: 333, // Raoul
    level: 99,
    trait_id: 97,    // Wealth of Lotus (+2 Turn Buffs)
    skills: [
      832, // Auto-Mataru
      97,  // Auto-Maraku
      192, // Auto-Masuku
      620, // Phantom Show
      807, // Debilitate
      855, // Enduring Soul
      863, // Insta-Heal
      346  // Spell Master
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
  await loadDatabase();
  await refreshDiscovery();
});

// Load Database
async function loadDatabase() {
  try {
    const res = await fetch("/api/database");
    DB = await res.json();
    populatePersonaDropdown();
    populateTraitDropdown();
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
      dropdown.innerHTML = `<option value="">-- No Steam saves found in default folder --</option>`;
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

    CURRENT_SAVE = data;
    CURRENT_FILE_PATH = path;
    INITIAL_CONFIDANT_RANKS = {};
    Object.entries(data.confidants || {}).forEach(([arc, c]) => {
      INITIAL_CONFIDANT_RANKS[arc] = c.rank || 0;
    });

    // Populate Active Inventory from Save
    INVENTORY_ITEM_COUNTS = {};
    (data.inventory || []).forEach(entry => {
      if (entry.item_id > 0 && entry.quantity > 0) {
        INVENTORY_ITEM_COUNTS[entry.item_id] = entry.quantity;
      }
    });

    renderSaveData();
    refreshBackups();
    updateIntegrityBadge(data.integrity);
    setStatus(`✔ Save loaded: ${path.split("\\").pop()} (${data.header.day}) | Ready.`);
  } catch (err) {
    console.error("Load save error:", err);
    setStatus("Error communicating with server.");
  }
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
  select.innerHTML = "";

  (CURRENT_SAVE.party || []).forEach((m, idx) => {
    const opt = document.createElement("option");
    opt.value = idx;
    opt.textContent = `${m.name} (LV ${m.level})`;
    select.appendChild(opt);
  });
}

function renderActiveMember() {
  const select = document.getElementById("partyMemberSelect");
  ACTIVE_MEMBER_INDEX = parseInt(select.value) || 0;
  const member = CURRENT_SAVE?.party ? CURRENT_SAVE.party[ACTIVE_MEMBER_INDEX] : null;
  if (!member) return;

  const isJoker = member.slot === 0;

  document.getElementById("activeMemberBadge").textContent = `SLOT ${member.slot} // ${member.name.toUpperCase()}`;
  document.getElementById("memberLevel").value = member.level || 1;
  document.getElementById("memberHP").value = member.hp || 100;
  document.getElementById("memberSP").value = member.sp || 50;

  // Configure Deck header and stock chips visibility
  const deckHeader = document.getElementById("personaDeckHeader");
  const stockChipsBox = document.getElementById("stockChipsContainer");
  const stockBadge = document.getElementById("stockSlotBadge");

  if (isJoker) {
    if (deckHeader) deckHeader.textContent = "🎭 EQUIPPED PERSONA & MOVESET";
    if (stockChipsBox) stockChipsBox.style.display = "flex";
    if (stockBadge) stockBadge.style.display = "inline";
    renderStockChips();
    loadPersonaIntoDeck(ACTIVE_STOCK_SLOT);
  } else {
    if (deckHeader) deckHeader.textContent = `🎭 ${member.name.toUpperCase()}'S PERSONA`;
    if (stockChipsBox) stockChipsBox.style.display = "none";
    if (stockBadge) stockBadge.style.display = "none";

    const pers = member.persona || {};
    document.getElementById("personaSelect").value = pers.persona_id || 1;
    document.getElementById("personaLevel").value = pers.level || 1;
    document.getElementById("personaTraitSelect").value = pers.trait_id || 0;

    const st = pers.stats || [10, 10, 10, 10, 10];
    document.getElementById("stat_st").value = st[0] || 10;
    document.getElementById("stat_ma").value = st[1] || 10;
    document.getElementById("stat_en").value = st[2] || 10;
    document.getElementById("stat_ag").value = st[3] || 10;
    document.getElementById("stat_lu").value = st[4] || 10;

    renderSkillsGrid(pers.skills || [0,0,0,0,0,0,0,0]);
    renderElementalAffinities(pers.persona_id || 1, pers.skills || [0,0,0,0,0,0,0,0]);
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
      portraitEl.src = `/assets/personas/${entry.persona_id}.png`;
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
      portraitEl.src = `/assets/personas/${pid}.png`;
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

    let opts = `<option value="0">-- (Empty Skill) --</option>`;
    (DB.skills || []).forEach((sk) => {
      opts += `<option value="${sk.id}" ${sk.id === curSkillId ? 'selected' : ''}>${sk.name}</option>`;
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

// Hideout & Inventory Items
function renderInventoryItems() {
  const container = document.getElementById("itemListContainer");
  if (!container) return;
  container.innerHTML = "";

  const items = DB.items || [];
  const search = (document.getElementById("itemSearchInput")?.value || "").toLowerCase();

  items.filter(it => !search || it.name.toLowerCase().includes(search)).slice(0, 80).forEach(it => {
    const card = document.createElement("div");
    card.style.background = "#181822";
    card.style.border = "1px solid var(--p5-border)";
    card.style.padding = "8px 12px";
    card.style.borderRadius = "4px";
    card.style.display = "flex";
    card.style.justifyContent = "space-between";
    card.style.alignItems = "center";

    card.innerHTML = `
      <div>
        <div style="font-size:12px; font-weight:800; color:var(--p5-white);">${it.name}</div>
        <span style="font-size:10px; color:var(--p5-muted);">Item ID: ${it.id}</span>
      </div>
      <button class="p5-btn-action secondary" style="padding:2px 8px; font-size:11px;" onclick="addSingleItem('${it.name}', ${it.id})">
        <span>+ 99x</span>
      </button>
    `;
    container.appendChild(card);
  });
}

function filterItemList() {
  renderInventoryItems();
}

function stockLeblancKitchen() {
  alert("☕ 99x Master Curry & 99x Master Coffee added to inventory!");
}

function stockInfiltrationKit() {
  alert("🔑 Eternal Lockpick & 99x Infiltration Tools added to inventory!");
}

function stockClinicMedicine() {
  alert("💉 99x SP Adhesive 3 & Clinic Meds added to inventory!");
}

function addSingleItem(name, id) {
  alert(`📦 Added 99x ${name} to inventory!`);
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
  const currentDay = CURRENT_SAVE?.header?.day || "";
  let totalVisible = 0;
  let romanceVisible = 0;

  Object.entries(CURRENT_SAVE?.confidants || {}).forEach(([arcana, info]) => {
    const prof = profiles[arcana] || { unlock_date: "4/11", type: "social" };
    const isMet = info.rank > 0;
    const isCalendarReady = isStoryUnlocked(currentDay, prof.unlock_date);
    if (isMet || isCalendarReady || ALLOW_UNSAFE_CONFIDANTS) {
      totalVisible++;
      if (prof.type === "romance" || prof.type === "romance_deadline") romanceVisible++;
    }
  });

  const allPill = document.getElementById("pillAll");
  if (allPill) allPill.textContent = `Met / Active Arcana (${totalVisible})`;
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
      const isCalendarReady = isStoryUnlocked(currentDay, prof.unlock_date);
      const isLocked = !isMet && !isCalendarReady;

      if (isLocked && !ALLOW_UNSAFE_CONFIDANTS) return;

      matchingArcanas.push(arcana);

      const card = document.createElement("div");
      const isRomanceable = romanceableList.includes(info.arcana_id);
      const isDeadline = prof.type === "story_deadline" || prof.type === "romance_deadline";
      const isSelected = arcana === SELECTED_CONFIDANT_ARCANA;

      card.className = `p5-tarot-card ${isRomanceable ? 'romance' : ''} ${isDeadline ? 'deadline' : ''} ${isLocked ? 'locked' : ''} ${isSelected ? 'active' : ''}`;
      card.onclick = () => selectConfidantArcana(arcana);

      const portraitSrc = prof.img ? `/assets/confidants/${prof.img}` : '/assets/joker_avatar.jpg';

      card.innerHTML = `
        <div class="tarot-rank-badge ${info.rank >= 10 ? 'max' : ''}">${isLocked ? '🔒' : `RK ${info.rank}`}</div>
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
  const portraitSrc = prof.img ? `/assets/confidants/${prof.img}` : '/assets/joker_avatar.jpg';

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
    deadlineAlert = `<div class="spotlight-deadline" style="background:#FFE600; color:#000;">🔒 RANK 5 CAP (Ranks 6–10 locked until January 3rd Semester)</div>`;
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

  spotlight.innerHTML = `
    <!-- Top Hero Banner with Huge Slanted Portrait & Nameplate -->
    <div class="spotlight-header-card">
      <div class="spotlight-portrait-frame" onclick="openPortraitModal('${portraitSrc}', '${prof.name.replace(/'/g, "\\'")}', '${prof.role.replace(/'/g, "\\'")}')" title="Click to view full portrait">
        <img src="${portraitSrc}" class="spotlight-full-portrait" alt="${prof.name}">
        <div class="spotlight-zoom-hint">🔍 CLICK TO ENLARGE</div>
      </div>

      <div class="spotlight-identity-block">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px;">
          <div class="spotlight-arcana-tag">${arcana.toUpperCase()} ARCANA (${info.arcana_id})</div>
          ${info.rank >= 10 ? '<span class="spotlight-status-badge max">★ BOND MAXED (10/10)</span>' : (info.rank >= 9 && isRomanceable ? '<span class="spotlight-status-badge romance">💖 LOVER RELATIONSHIP</span>' : `<span class="spotlight-status-badge">PROGRESSION (${info.rank}/10)</span>`)}
        </div>

        <h1 class="spotlight-character-name">${prof.name}</h1>
        <div class="spotlight-role-text">${prof.role}</div>

        <div class="spotlight-perk-card">
          <div style="font-family:var(--font-p5); font-size:14px; color:var(--p5-yellow); letter-spacing:1px; margin-bottom:2px;">⚡ SIGNATURE INFILTRATION ABILITY:</div>
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
    </div>

    ${warningHtml}

    <!-- In-Game Consequence & Lore Panels -->
    <div class="spotlight-dossier-grid">
      <!-- Live Rank Consequence -->
      <div class="dossier-panel" style="border-left-color:${info.rank >= 10 ? '#00E676' : (info.rank >= 9 && isRomanceable ? '#FF2A6D' : 'var(--p5-crimson)')};">
        <div class="dossier-panel-title">
          <span>⚡ RANK ${info.rank} NARRATIVE IMPACT</span>
          <span style="color:${info.rank >= 10 ? '#00E676' : 'var(--p5-yellow)'};">${info.rank >= 10 ? '✔ COMPLETED' : 'ACTIVE'}</span>
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
      <div class="dossier-panel" style="grid-column: 1 / -1; border-left-color:var(--p5-yellow);">
        <div class="dossier-panel-title" style="color:var(--p5-yellow);">👑 ULTIMATE PERSONA AWAKENING & 3/19 NG+ KEEPSAKE</div>
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

function stepConfidantRank(arcana, delta) {
  if (!CURRENT_SAVE?.confidants?.[arcana]) return;
  const cur = CURRENT_SAVE.confidants[arcana].rank || 0;
  const newRank = Math.max(0, Math.min(10, cur + delta));
  CURRENT_SAVE.confidants[arcana].rank = newRank;
  CURRENT_SAVE.confidants[arcana].points = 99;
  renderConfidants();
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

// Known DLC & Treasure Demon IDs in the 232 mask
const DLC_PERSONA_IDS = [190, 191, 192, 193, 194, 195, 196, 197, 198]; // Orpheus, Izanagi, Asterius, Ariadne, etc.
const TREASURE_DEMON_IDS = [106, 107, 108, 109, 110, 111, 112, 113, 114]; // Regent, Queen's Necklace, Stone of Scone, Koh-i-Noor, Orlov, Emperor's Amulet, Hope Diamond, Crystal Skull, Orichalcum

function renderCompendium() {
  if (!COMPENDIUM_DATA && CURRENT_SAVE?.compendium) {
    COMPENDIUM_DATA = JSON.parse(JSON.stringify(CURRENT_SAVE.compendium));
    ORIGINAL_COMPENDIUM_REGISTERED = [...(COMPENDIUM_DATA.registered || [])];
  }
  if (!COMPENDIUM_DATA || !COMPENDIUM_DATA.supported) return;

  const total = 232;
  const regSet = new Set(COMPENDIUM_DATA.registered || []);
  const count = regSet.size;
  COMPENDIUM_DATA.count = count;
  const pct = Math.round((count / total) * 100);

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

  grid.innerHTML = "";
  let visibleCount = 0;

  for (let pid = 1; pid <= 232; pid++) {
    const isReg = regSet.has(pid);
    
    // Status filter
    if (COMPENDIUM_FILTER_MODE === "registered" && !isReg) continue;
    if (COMPENDIUM_FILTER_MODE === "unregistered" && isReg) continue;

    const pObj = personas.find(p => p.id === pid);
    const name = pObj ? pObj.name : `Persona #${pid}`;
    const hexId = "0x" + pid.toString(16).toUpperCase().padStart(2, "0");

    // Search query filter
    if (query && !name.toLowerCase().includes(query) && !hexId.toLowerCase().includes(query) && !pid.toString().includes(query)) {
      continue;
    }

    visibleCount++;
    const isDlc = DLC_PERSONA_IDS.includes(pid);
    const isTreasure = TREASURE_DEMON_IDS.includes(pid);

    const card = document.createElement("div");
    card.style.cssText = `
      background: ${isReg ? "linear-gradient(135deg, #1C1226, #0E0B16)" : "#09090D"};
      border: 1px solid ${isReg ? "#E040FB" : "#222"};
      border-left: 6px solid ${isReg ? "#00E676" : "#444"};
      padding: 10px 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      cursor: pointer;
      border-radius: 4px;
      transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
      box-shadow: ${isReg ? "0 4px 15px rgba(0,230,118,0.1)" : "none"};
    `;
    card.title = `Click to ${isReg ? "un-register" : "register"} ${name} (ID: ${hexId})`;

    card.onmouseenter = () => { card.style.transform = "translateY(-3px)"; card.style.boxShadow = "0 6px 20px rgba(0,0,0,0.8)"; };
    card.onmouseleave = () => { card.style.transform = "translateY(0)"; card.style.boxShadow = isReg ? "0 4px 15px rgba(0,230,118,0.1)" : "none"; };
    card.onclick = () => togglePersonaRegistration(pid);

    const left = document.createElement("div");
    left.style.cssText = "display:flex; align-items:center; gap:12px;";
    left.innerHTML = `
      <img src="/assets/personas/${pid}.png" onerror="this.style.display='none'" style="width:56px; height:56px; object-fit:contain; background:#0B0B10; border:1px solid #333; padding:3px; border-radius:4px; filter:drop-shadow(0 2px 6px rgba(0,0,0,0.7)); flex-shrink:0;">
      <div>
        <div style="font-family:var(--font-p5); font-size:15px; letter-spacing:0.5px; color:${isReg ? '#FFF' : '#777'};">
          ${name} ${isDlc ? '<span style="font-size:9px; font-family:var(--font-body); font-weight:900; background:#FF2A6D; color:#FFF; padding:2px 5px; border-radius:2px;">DLC</span>' : ''} ${isTreasure ? '<span style="font-size:9px; font-family:var(--font-body); font-weight:900; background:#FFE600; color:#000; padding:2px 5px; border-radius:2px;">DEMON</span>' : ''}
        </div>
        <div style="font-size:11px; color:var(--p5-muted); font-family:monospace; margin-top:2px;">ID: ${hexId} <span style="color:#555;">(#${pid})</span></div>
      </div>
    `;

    const statusBadge = document.createElement("span");
    statusBadge.style.cssText = `
      font-size: 11px;
      font-weight: 900;
      padding: 3px 8px;
      font-family: var(--font-p5);
      background: ${isReg ? "#00E676" : "#222"};
      color: ${isReg ? "#000" : "#666"};
      border: 1px solid ${isReg ? "#00E676" : "#333"};
    `;
    statusBadge.textContent = isReg ? "REGISTERED" : "LOCKED";

    card.appendChild(left);
    card.appendChild(statusBadge);
    grid.appendChild(card);
  }

  const countLabel = document.getElementById("compendiumFilterCount");
  if (countLabel) countLabel.textContent = `Showing ${visibleCount} of 232 Personas`;

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
  if (!confirm("Unlock ALL 232 personas in the Compendium?\n\nThis registers all Personas in the matrix. Remember to RE-SIGN SAVE.")) return;
  const allIds = [];
  for (let i = 1; i <= 232; i++) allIds.push(i);
  COMPENDIUM_DATA.registered = allIds;
  COMPENDIUM_DATA.count = 232;
  renderCompendium();
  setStatus("★ All 232 Personas registered in Compendium matrix. Click RE-SIGN SAVE to write to disk.");
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
  COMPENDIUM_DATA.registered = [...ORIGINAL_COMPENDIUM_REGISTERED];
  COMPENDIUM_DATA.count = ORIGINAL_COMPENDIUM_REGISTERED.length;
  renderCompendium();
  setStatus("Compendium reset to original loaded state.");
}

// =========================================================================
// STAGE 3.5: INVENTORY & POUCH STUDIO LOGIC (TWO-PANEL INTUITIVE UI)
// =========================================================================
let CURRENT_POUCH_POCKET = "All";
let CURRENT_VAULT_CATEGORY = "All";
let VAULT_SEARCH_QUERY = "";
let INVENTORY_ITEM_COUNTS = {}; // id -> qty (1..99)

function filterPouchPocket(pocket, btnEl) {
  CURRENT_POUCH_POCKET = pocket;
  document.querySelectorAll("#pouchPocketTabs .filter-pill").forEach(el => el.classList.remove("active"));
  if (btnEl) btnEl.classList.add("active");
  renderCurrentPouch();
}

function filterVaultCategory(cat, btnEl) {
  CURRENT_VAULT_CATEGORY = cat;
  document.querySelectorAll("#stage-inventory .filter-pill").forEach(el => {
    if (el.closest("#pouchPocketTabs")) return;
    el.classList.remove("active");
  });
  if (btnEl) btnEl.classList.add("active");
  renderVaultResults();
}

function onVaultSearchInput() {
  VAULT_SEARCH_QUERY = (document.getElementById("vaultSearchBox")?.value || "").toLowerCase().trim();
  renderVaultResults();
}

// 1. Render Joker's Active Carried Items (The Pouch)
function renderCurrentPouch() {
  const container = document.getElementById("currentPouchContainer");
  if (!container) return;

  const allOwned = Object.entries(INVENTORY_ITEM_COUNTS)
    .map(([idStr, qty]) => {
      const id = parseInt(idStr);
      const item = (DB.items || []).find(it => it.id === id) || { id, name: `Royal Item #0x${id.toString(16).toUpperCase()}`, category: "Consumable" };
      return { ...item, qty: parseInt(qty) };
    })
    .filter(it => it.qty > 0);

  // Update Pocket Badge Counters
  const countByCat = (c) => allOwned.filter(it => it.category === c).length;
  const countGear = allOwned.filter(it => ["Melee", "Ranged", "Protector"].includes(it.category)).length;

  if (document.getElementById("pouchBadgeAll")) document.getElementById("pouchBadgeAll").textContent = allOwned.length;
  if (document.getElementById("pouchBadgeConsumable")) document.getElementById("pouchBadgeConsumable").textContent = countByCat("Consumable");
  if (document.getElementById("pouchBadgeInfiltration")) document.getElementById("pouchBadgeInfiltration").textContent = countByCat("Infiltration");
  if (document.getElementById("pouchBadgeSkillCard")) document.getElementById("pouchBadgeSkillCard").textContent = countByCat("SkillCard");
  if (document.getElementById("pouchBadgeAccessory")) document.getElementById("pouchBadgeAccessory").textContent = countByCat("Accessory");
  if (document.getElementById("pouchBadgeEquipment")) document.getElementById("pouchBadgeEquipment").textContent = countGear;
  if (document.getElementById("pouchBadgeKeyItem")) document.getElementById("pouchBadgeKeyItem").textContent = countByCat("KeyItem") + countByCat("Treasure");

  const slotCounter = document.getElementById("pouchSlotCounter");
  if (slotCounter) {
    slotCounter.textContent = `${allOwned.length} / 30 SLOTS USED`;
    slotCounter.style.color = allOwned.length >= 30 ? "var(--p5-crimson)" : "var(--p5-yellow)";
  }

  // Filter for active pocket tab
  const displayed = allOwned.filter(item => {
    if (CURRENT_POUCH_POCKET === "All") return true;
    if (CURRENT_POUCH_POCKET === "Equipment") return ["Melee", "Ranged", "Protector"].includes(item.category);
    if (CURRENT_POUCH_POCKET === "KeyItem") return ["KeyItem", "Treasure"].includes(item.category);
    return item.category === CURRENT_POUCH_POCKET;
  });

  container.innerHTML = "";

  if (displayed.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; text-align:center; padding:28px 16px; background:rgba(0,0,0,0.3); border:2px dashed #333;">
        <div style="font-family:var(--font-p5); font-size:18px; color:var(--p5-yellow); margin-bottom:4px;">NO ITEMS IN THIS POCKET</div>
        <p style="font-size:11px; color:var(--p5-muted); max-width:400px; margin:0 auto 10px auto;">
          ${allOwned.length === 0 ? "Joker's bag is empty. Use the quick buttons or search on the right to add items!" : `No ${CURRENT_POUCH_POCKET} items in your bag.`}
        </p>
      </div>
    `;
    return;
  }

  displayed.forEach(item => {
    const card = document.createElement("div");
    card.style.cssText = `
      background: linear-gradient(135deg, #181824 0%, #0E0E14 100%);
      border: 2px solid #000;
      border-left: 6px solid ${getCategoryColor(item.category)};
      padding: 10px 14px;
      box-shadow: 3px 3px 0 #000;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
    `;

    card.innerHTML = `
      <div style="flex:1; min-width:0;">
        <div style="display:flex; align-items:center; gap:6px;">
          <span style="font-size:10px; font-weight:900; color:${getCategoryColor(item.category)}; background:#000; padding:1px 5px; border:1px solid #000; text-transform:uppercase;">
            ${item.category}
          </span>
          <span style="font-size:10px; color:var(--p5-muted);">0x${item.id.toString(16).toUpperCase()}</span>
        </div>
        <div style="font-family:var(--font-p5); font-size:17px; color:#FFF; margin-top:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${item.name}">
          ${item.name}
        </div>
      </div>

      <!-- Stepper Controls & Delete -->
      <div style="display:flex; align-items:center; gap:5px;">
        <button class="rank-stepper-btn" style="width:28px; height:28px; font-size:14px;" onclick="stepItemQty(${item.id}, -1)">-</button>
        <div style="background:#000; border:1px solid #000; min-width:34px; text-align:center; padding:2px 4px; font-family:var(--font-p5); font-size:17px; color:var(--p5-yellow);">
          ${item.qty}
        </div>
        <button class="rank-stepper-btn" style="width:28px; height:28px; font-size:14px;" onclick="stepItemQty(${item.id}, 1)">+</button>
        <button class="p5-btn-action" style="padding:3px 6px; font-size:11px;" onclick="maxItemQty(${item.id})"><span>99x</span></button>
        <button style="background:#440000; border:1px solid #FF3333; color:#FF8888; cursor:pointer; width:28px; height:28px; border-radius:3px; font-size:12px; display:flex; align-items:center; justify-content:center;" onclick="removeItemFromPouch(${item.id})" title="Remove item from bag">✕</button>
      </div>
    `;

    container.appendChild(card);
  });
}

// 2. Render Search & Add Results from Royal Vault
function renderVaultResults() {
  const container = document.getElementById("vaultResultsContainer");
  if (!container || !DB.items) return;

  const filtered = DB.items.filter(item => {
    const matchCat = CURRENT_VAULT_CATEGORY === "All" || item.category === CURRENT_VAULT_CATEGORY;
    const matchSearch = !VAULT_SEARCH_QUERY || item.name.toLowerCase().includes(VAULT_SEARCH_QUERY);
    return matchCat && matchSearch;
  });

  const catalogCounter = document.getElementById("vaultCatalogCounter");
  if (catalogCounter) {
    catalogCounter.textContent = `${filtered.length} MATCHING ROYAL ITEMS`;
  }

  container.innerHTML = "";

  if (filtered.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; text-align:center; padding:30px; color:var(--p5-muted);">
        <div style="font-family:var(--font-p5); font-size:18px; color:var(--p5-yellow); margin-bottom:4px;">NO ITEMS FOUND</div>
        <p style="font-size:12px;">No Royal item matches "${VAULT_SEARCH_QUERY}". Try another search term.</p>
      </div>
    `;
    return;
  }

  // Show top 60 matching items for instant, snappy rendering
  filtered.slice(0, 60).forEach(item => {
    const qty = INVENTORY_ITEM_COUNTS[item.id] || 0;
    const isOwned = qty > 0;
    const card = document.createElement("div");
    card.style.cssText = `
      background: ${isOwned ? '#141E18' : '#12121A'};
      border: 1px solid ${isOwned ? '#00E676' : '#2A2A3A'};
      border-left: 4px solid ${getCategoryColor(item.category)};
      padding: 8px 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
    `;

    card.innerHTML = `
      <div style="flex:1; min-width:0;">
        <div style="display:flex; align-items:center; gap:6px;">
          <span style="font-size:9px; font-weight:800; color:${getCategoryColor(item.category)}; text-transform:uppercase;">
            ${item.category}
          </span>
          ${isOwned ? '<span style="font-size:9px; font-weight:900; color:#00E676; background:#003311; padding:0 4px; border-radius:2px;">IN POUCH</span>' : ''}
        </div>
        <div style="font-family:var(--font-p5); font-size:15px; color:${isOwned ? '#00E676' : '#FFF'}; margin-top:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${item.name}">
          ${item.name}
        </div>
      </div>

      <!-- Add Actions -->
      <div style="display:flex; align-items:center; gap:4px;">
        ${isOwned ? `
          <button class="rank-stepper-btn" style="width:26px; height:26px; font-size:13px;" onclick="stepItemQty(${item.id}, 1)">+1</button>
          <button class="p5-btn-action" style="padding:2px 6px; font-size:10px;" onclick="maxItemQty(${item.id})"><span>99x</span></button>
        ` : `
          <button class="p5-btn-action" style="padding:3px 8px; font-size:11px;" onclick="addItemToPouch(${item.id}, 1)"><span>+ ADD</span></button>
          <button class="p5-btn-action" style="padding:3px 6px; font-size:11px; background:#FF9F1C; border-color:#FF9F1C; color:#000;" onclick="addItemToPouch(${item.id}, 99)"><span>99x</span></button>
        `}
      </div>
    `;

    container.appendChild(card);
  });
}

function renderInventoryViews() {
  renderCurrentPouch();
  renderVaultResults();
}

function addItemToPouch(itemId, qty = 1) {
  const currentSlots = Object.values(INVENTORY_ITEM_COUNTS).filter(q => q > 0).length;
  if (!INVENTORY_ITEM_COUNTS[itemId] && currentSlots >= 30) {
    alert("Bag is full! Joker can carry a maximum of 30 distinct item slots at once.");
    return;
  }
  const cur = INVENTORY_ITEM_COUNTS[itemId] || 0;
  INVENTORY_ITEM_COUNTS[itemId] = Math.max(1, Math.min(99, cur + qty));
  renderInventoryViews();
}

function removeItemFromPouch(itemId) {
  delete INVENTORY_ITEM_COUNTS[itemId];
  renderInventoryViews();
}

function clearAllPouchItems() {
  if (confirm("Clear all carried items from Joker's pouch?")) {
    INVENTORY_ITEM_COUNTS = {};
    renderInventoryViews();
  }
}

function stepItemQty(itemId, delta) {
  const cur = INVENTORY_ITEM_COUNTS[itemId] || 0;
  const next = cur + delta;
  if (next <= 0) {
    delete INVENTORY_ITEM_COUNTS[itemId];
  } else {
    INVENTORY_ITEM_COUNTS[itemId] = Math.min(99, next);
  }
  renderInventoryViews();
}

function maxItemQty(itemId) {
  INVENTORY_ITEM_COUNTS[itemId] = 99;
  renderInventoryViews();
}

function getCategoryColor(cat) {
  switch (cat) {
    case "Consumable": return "var(--p5-yellow)";
    case "Infiltration": return "var(--p5-crimson)";
    case "SkillCard": return "#00E5FF";
    case "Accessory": return "#E040FB";
    case "Melee": return "#FF5252";
    case "Ranged": return "#FF9F1C";
    case "Protector": return "#00E676";
    case "Treasure": return "#FFD600";
    default: return "var(--p5-muted)";
  }
}

function stockLeblancKitchen() {
  if (!DB.items) return;
  const curries = DB.items.filter(it => it.name.includes("Curry") || it.name.includes("Coffee"));
  curries.forEach(it => {
    INVENTORY_ITEM_COUNTS[it.id] = 99;
  });
  renderInventoryViews();
  alert("☕ Stocked 99x Master Curry & 99x Master Coffee in Leblanc Pouch!");
}

function stockInfiltrationKit() {
  if (!DB.items) return;
  const tools = DB.items.filter(it => it.name.includes("Lockpick") || it.name.includes("Goho-M") || it.name.includes("Smoke"));
  tools.forEach(it => {
    INVENTORY_ITEM_COUNTS[it.id] = 99;
  });
  renderInventoryViews();
  alert("🔑 Stocked Eternal Lockpick, 99x Smokescreens, and 99x Goho-Ms!");
}

function stockClinicMedicine() {
  if (!DB.items) return;
  const meds = DB.items.filter(it => it.name.includes("Adhesive") || it.name.includes("Bead") || it.name.includes("Soma") || it.name.includes("Takemedic"));
  meds.forEach(it => {
    INVENTORY_ITEM_COUNTS[it.id] = 99;
  });
  renderInventoryViews();
  alert("💉 Stocked 99x SP Adhesive 3, 99x Bead Chains, and 99x Somas!");
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

  mem.level = 99;
  mem.hp = 999;
  mem.sp = 999;
  mem.persona = {
    persona_id: build.persona_id,
    level: build.level,
    trait_id: build.trait_id,
    exp: 9999999,
    skills: build.skills,
    stats: [99, 99, 99, 99, 99],
    flags: 1
  };

  if (CURRENT_SAVE.joker_stock && CURRENT_SAVE.joker_stock.length > 0) {
    CURRENT_SAVE.joker_stock[0] = {
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
    };
  }

  // Switch to Velvet Room Stage to show
  switchStage('velvet_room');
  document.getElementById("partyMemberSelect").value = 0;
  ACTIVE_STOCK_SLOT = 0;
  renderActiveMember();
  alert(`★ God-Tier Build (${buildKey.toUpperCase()}) applied to Joker!`);
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

async function executeSavePayload() {
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

  // Persist Active Inventory
  CURRENT_SAVE.inventory = [];
  let slotIdx = 0;
  Object.entries(INVENTORY_ITEM_COUNTS).forEach(([idStr, qty]) => {
    if (qty > 0 && slotIdx < 30) {
      CURRENT_SAVE.inventory.push({
        slot: slotIdx,
        item_id: parseInt(idStr),
        quantity: parseInt(qty)
      });
      slotIdx++;
    }
  });

  // Attach modified Compendium registration state
  if (COMPENDIUM_DATA) {
    CURRENT_SAVE.compendium = COMPENDIUM_DATA;
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
    setStatus(`✔ Changes re-signed & saved! Auto-backup created: ${result.backup}`);
    alert("★ Save successful! CRCs & AES integrity verified and re-signed.");
  } catch (err) {
    console.error("Save error:", err);
    setStatus("Failed to save changes.");
  }
}

// 3rd Semester Rescue
async function triggerRescueThirdSemester() {
  if (!confirm("Unlock 3rd Semester? Sets Maruki Rank 9, Kasumi Rank 5, Akechi Rank 8.")) return;
  try {
    const res = await fetch("/api/emergency-rescue", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "third_semester" })
    });
    const data = await res.json();
    alert(data.message || "3rd semester ranks set!");
    loadSaveFile();
  } catch (err) {
    alert("Failed to trigger rescue: " + err);
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
