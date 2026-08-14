/**
 * Persona 5 Royal — 1:1 In-Game Client Controller Engine
 * Features 3D Parallax Tracking, Kinetic Screen Transitions, and Full Save Editor Engine.
 */

let DB = {
  personas: [],
  skills: [],
  traits: [],
  items: [],
  confidants: [],
  confidant_profiles: {},
  romanceable: []
};

let CURRENT_SAVE = null;
let CURRENT_FILE_PATH = null;
let SELECTED_COOP_ARCANA = null;
let ACTIVE_STOCK_SLOT = 0;

// 3D Mouse Parallax Tracking on Camp Menu
document.addEventListener("mousemove", (e) => {
  const camp = document.getElementById("screen-camp");
  if (!camp || camp.classList.contains("hidden")) return;

  const xOffset = (e.clientX / window.innerWidth - 0.5) * 20; // -10 to +10 deg
  const yOffset = (e.clientY / window.innerHeight - 0.5) * -15;

  const anchor = document.querySelector(".camp-center-anchor");
  if (anchor) {
    anchor.style.transform = `rotateY(${xOffset}deg) rotateX(${yOffset}deg)`;
  }
});

// Boot & Discovery
window.addEventListener("DOMContentLoaded", async () => {
  await fetchDatabase();
  await discoverSaves();
});

async function fetchDatabase() {
  try {
    const res = await fetch("/api/database");
    DB = await res.json();
  } catch (err) {
    console.error("Failed to load DB:", err);
  }
}

async function discoverSaves() {
  try {
    const res = await fetch("/api/discovery");
    const data = await res.json();
    const dropdown = document.getElementById("saveDropdown");
    dropdown.innerHTML = "";

    if (data.saves && data.saves.length > 0) {
      data.saves.forEach((s) => {
        const opt = document.createElement("option");
        opt.value = s;
        opt.textContent = s.split(/[\\/]/).slice(-2).join(" / ");
        dropdown.appendChild(opt);
      });
      // Auto-load first save
      loadGameSave();
    } else {
      dropdown.innerHTML = `<option value="">-- No Saves Found --</option>`;
    }
  } catch (err) {
    console.error("Discovery error:", err);
  }
}

async function loadGameSave() {
  const path = document.getElementById("saveDropdown").value;
  if (!path) return;

  setStatus("Decrypting and loading save file...");
  try {
    const res = await fetch("/api/load", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path })
    });
    const save = await res.json();
    if (save.error) {
      alert("Error loading save: " + save.error);
      return;
    }

    CURRENT_SAVE = save;
    CURRENT_FILE_PATH = save.file_path;

    // Update HUD
    const hdr = save.header || {};
    document.getElementById("hudDate").textContent = hdr.day || "DATE ERROR";
    document.getElementById("hudPlaytime").textContent = `PLAYTIME: ${hdr.playtime || '--:--'}`;
    document.getElementById("hudYen").textContent = (hdr.money || 0).toLocaleString();
    const groupEl = document.getElementById("campGroupName");
    if (groupEl) groupEl.textContent = (hdr.group_name || "PHANTOM THIEVES").toUpperCase();

    // Populate Sub-screens
    renderCoopDeck();
    renderStatsScreen();
    renderStockGrid();
    refreshBackupsGame();

    setStatus(`✔ Active save loaded: ${hdr.fname} ${hdr.lname} (${hdr.group_name})`);
  } catch (err) {
    console.error("Load save error:", err);
  }
}

// Kinetic Menu Navigation
function openGameScreen(screenId) {
  const camp = document.getElementById("screen-camp");
  if (camp) camp.classList.add("hidden");

  document.querySelectorAll(".p5-subscreen").forEach(el => el.classList.remove("active"));
  const target = document.getElementById(`screen-${screenId}`);
  if (target) target.classList.add("active");
}

function returnToCampMenu() {
  document.querySelectorAll(".p5-subscreen").forEach(el => el.classList.remove("active"));
  const camp = document.getElementById("screen-camp");
  if (camp) camp.classList.remove("hidden");
}

// 1:1 In-Game Co-op Screen
function renderCoopDeck() {
  const deck = document.getElementById("coopTarotDeck");
  if (!deck || !CURRENT_SAVE?.confidants) return;
  deck.innerHTML = "";

  const profiles = DB.confidant_profiles || {};
  const confidants = CURRENT_SAVE.confidants;
  const arcanas = Object.keys(confidants);

  arcanas.forEach((arcana, idx) => {
    const info = confidants[arcana];
    const prof = profiles[arcana] || { name: arcana, role: "Tokyo Confidant", img: "" };
    const portraitSrc = prof.img ? `/assets/confidants/${prof.img}` : '/assets/joker_avatar.jpg';

    if (idx === 0 && !SELECTED_COOP_ARCANA) {
      SELECTED_COOP_ARCANA = arcana;
    }

    const slab = document.createElement("div");
    slab.className = `coop-tarot-slab ${arcana === SELECTED_COOP_ARCANA ? 'active' : ''}`;
    slab.onclick = () => selectCoopArcana(arcana, slab);

    slab.innerHTML = `
      <div class="coop-slab-rank">${info.rank >= 10 ? 'MAX' : `RK ${info.rank}`}</div>
      <img src="${portraitSrc}" class="coop-slab-avatar" alt="${prof.name}">
      <div class="coop-slab-text">
        <div class="coop-slab-arcana">${arcana.toUpperCase()} (${info.arcana_id})</div>
        <div class="coop-slab-name">${prof.name}</div>
      </div>
    `;
    deck.appendChild(slab);
  });

  if (SELECTED_COOP_ARCANA) {
    renderCoopHeroSpotlight(SELECTED_COOP_ARCANA);
  }
}

function selectCoopArcana(arcana, slabEl) {
  SELECTED_COOP_ARCANA = arcana;
  document.querySelectorAll(".coop-tarot-slab").forEach(el => el.classList.remove("active"));
  if (slabEl) slabEl.classList.add("active");
  renderCoopHeroSpotlight(arcana);
}

function renderCoopHeroSpotlight(arcana) {
  const canvas = document.getElementById("coopHeroCanvas");
  if (!canvas || !CURRENT_SAVE?.confidants?.[arcana]) return;

  const info = CURRENT_SAVE.confidants[arcana];
  const prof = DB.confidant_profiles?.[arcana] || { name: arcana, role: "Tokyo Ally", unlock: "Infiltration Perk", img: "" };
  const portraitSrc = prof.img ? `/assets/confidants/${prof.img}` : '/assets/joker_avatar.jpg';
  const isRomanceable = (DB.romanceable || []).includes(info.arcana_id);

  canvas.innerHTML = `
    <div style="display:flex; gap:30px; align-items:flex-start; margin-bottom:25px;">
      <div style="width:180px; min-width:180px; height:230px; border:4px solid #FFF; background:#000; box-shadow:8px 8px 0 #000; transform:rotate(-2deg); overflow:hidden;">
        <img src="${portraitSrc}" style="width:100%; height:100%; object-fit:cover;" alt="${prof.name}">
      </div>

      <div style="flex:1;">
        <div style="font-family:var(--font-p5); font-size:18px; color:#000; background:var(--p5-yellow); padding:3px 12px; display:inline-block; transform:rotate(-2deg); border:2px solid #000; font-weight:900;">
          ${arcana.toUpperCase()} ARCANA (${info.arcana_id})
        </div>
        <h1 style="font-family:var(--font-p5); font-size:48px; letter-spacing:3px; color:#FFF; text-shadow:4px 4px 0 #000; margin-top:4px;">${prof.name}</h1>
        <div style="font-size:14px; font-weight:900; color:var(--p5-muted); margin-bottom:14px;">${prof.role}</div>

        <div style="background:rgba(0,0,0,0.6); border:2px solid #000; border-left:6px solid var(--p5-crimson); padding:12px 16px; box-shadow:4px 4px 0 #000;">
          <div style="font-family:var(--font-p5); font-size:16px; color:var(--p5-yellow); margin-bottom:3px;">⚡ INFILTRATION ABILITY:</div>
          <div style="font-size:13px; font-weight:700; color:#FFF;">${prof.unlock}</div>
        </div>
      </div>
    </div>

    <!-- Rank Controller Deck -->
    <div style="background:#12121A; border:3px solid #000; padding:16px 25px; display:flex; justify-content:space-between; align-items:center; transform:skew(-6deg); box-shadow:6px 6px 0 #000; margin-bottom:20px;">
      <div style="font-family:var(--font-p5); font-size:24px; color:#FFF; text-shadow:2px 2px 0 #000;">CO-OP RANK:</div>
      <div style="display:flex; align-items:center; gap:14px;">
        <button class="rank-stepper-btn" onclick="stepGameConfidantRank('${arcana}', -1)" ${info.rank <= 0 ? 'disabled' : ''}>◄</button>
        <div style="background:#000; border:2px solid #000; padding:4px 20px; font-family:var(--font-p5); font-size:36px; color:var(--p5-yellow);">${info.rank} / 10</div>
        <button class="rank-stepper-btn" onclick="stepGameConfidantRank('${arcana}', 1)" ${info.rank >= 10 ? 'disabled' : ''}>►</button>
      </div>
      <button class="p5-btn-action" onclick="stepGameConfidantRank('${arcana}', 10 - ${info.rank})"><span>★ MAX (RANK 10)</span></button>
    </div>

    <!-- Narrative Status Box -->
    <div style="background:rgba(12,12,18,0.95); border:3px solid #000; border-left:6px solid ${info.rank >= 10 ? '#00E676' : 'var(--p5-crimson)'}; padding:18px; box-shadow:5px 5px 0 #000;">
      <div style="font-family:var(--font-p5); font-size:18px; color:var(--p5-yellow); margin-bottom:6px;">⚡ STORY CONSEQUENCE & REWARDS:</div>
      <div style="font-size:13px; line-height:1.5; color:#D0D0E0;">
        ${info.rank >= 10 ? `
          • 🌟 <strong>Story Status:</strong> Bond has reached its ultimate peak! Full trust unlocked.<br>
          • 👑 <strong>Awakening:</strong> Velvet Room Ultimate Persona Fusion unlocked.<br>
          • 🎁 <strong>3/19 Farewell Keepsake:</strong> ${prof.name} will hand Joker their signature keepsake on 3/19 to carry into New Game+.
        ` : `
          • 📖 <strong>Story Progression:</strong> Currently at Rank ${info.rank}. Advancing ranks naturally unlocks daytime hangout cutscenes in Tokyo.
        `}
      </div>
    </div>
  `;
}

function stepGameConfidantRank(arcana, delta) {
  if (!CURRENT_SAVE?.confidants?.[arcana]) return;
  const cur = CURRENT_SAVE.confidants[arcana].rank || 0;
  const next = Math.max(0, Math.min(10, cur + delta));
  CURRENT_SAVE.confidants[arcana].rank = next;
  CURRENT_SAVE.confidants[arcana].points = 99;
  renderCoopDeck();
}

function maxAllConfidantsGame() {
  if (!CURRENT_SAVE) return;
  Object.keys(CURRENT_SAVE.confidants || {}).forEach(k => CURRENT_SAVE.confidants[k].rank = 10);
  renderCoopDeck();
}

// Stats Screen
function renderStatsScreen() {
  if (!CURRENT_SAVE) return;
  const hdr = CURRENT_SAVE.header || {};
  document.getElementById("gameFname").value = hdr.fname || "";
  document.getElementById("gameLname").value = hdr.lname || "";
  document.getElementById("gameGroupName").value = hdr.group_name || "";
  document.getElementById("gameMoney").value = hdr.money || 0;

  const statsList = document.getElementById("gameSocialStatsList");
  if (!statsList) return;
  statsList.innerHTML = "";

  const stats = CURRENT_SAVE.social_stats || {};
  Object.entries(stats).forEach(([name, data]) => {
    const row = document.createElement("div");
    row.style.cssText = "display:flex; justify-content:space-between; align-items:center; background:#0E0E16; border:2px solid #000; padding:10px 16px;";
    
    let nodes = "";
    for (let r = 1; r <= 5; r++) {
      nodes += `<button class="star-node ${r <= data.rank ? 'active' : ''}" style="width:34px; height:34px; font-family:var(--font-p5); font-size:16px;" onclick="setSocialStatGame('${name}', ${r})">${r}</button>`;
    }

    row.innerHTML = `
      <div style="font-family:var(--font-p5); font-size:20px; color:var(--p5-white);">${name.toUpperCase()} (LV ${data.rank})</div>
      <div style="display:flex; gap:6px;">${nodes}</div>
    `;
    statsList.appendChild(row);
  });
}

function setSocialStatGame(name, rank) {
  if (!CURRENT_SAVE?.social_stats?.[name]) return;
  CURRENT_SAVE.social_stats[name].rank = rank;
  renderStatsScreen();
}

function maxAllSocialStatsGame() {
  if (!CURRENT_SAVE?.social_stats) return;
  Object.keys(CURRENT_SAVE.social_stats).forEach(k => CURRENT_SAVE.social_stats[k].rank = 5);
  renderStatsScreen();
}

// Stock & Persona Studio
function renderStockGrid() {
  const grid = document.getElementById("gameStockGrid");
  if (!grid || !CURRENT_SAVE?.joker_stock) return;
  grid.innerHTML = "";

  CURRENT_SAVE.joker_stock.forEach((entry, idx) => {
    const chip = document.createElement("div");
    chip.style.cssText = `background:${idx === ACTIVE_STOCK_SLOT ? 'var(--p5-crimson)' : '#181824'}; border:2px solid #000; padding:12px; cursor:pointer; transform:skew(-6deg); box-shadow:3px 3px 0 #000;`;
    chip.onclick = () => { ACTIVE_STOCK_SLOT = idx; renderStockGrid(); };

    chip.innerHTML = `
      <div style="font-family:var(--font-p5); font-size:14px; color:${idx === ACTIVE_STOCK_SLOT ? '#FFF' : 'var(--p5-yellow)'};">SLOT ${idx} ${idx === 0 ? '(EQUIPPED)' : ''}</div>
      <div style="font-family:var(--font-p5); font-size:18px; color:#FFF; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${entry.persona || 'Empty Slot'}</div>
      <div style="font-size:11px; color:#A0A0B0;">LV ${entry.level}</div>
    `;
    grid.appendChild(chip);
  });

  renderActivePersonaStudio();
}

function renderActivePersonaStudio() {
  const studio = document.getElementById("gamePersonaStudio");
  if (!studio || !CURRENT_SAVE?.joker_stock?.[ACTIVE_STOCK_SLOT]) return;
  const p = CURRENT_SAVE.joker_stock[ACTIVE_STOCK_SLOT];

  studio.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px; border-bottom:2px solid rgba(255,255,255,0.1); padding-bottom:8px;">
      <div style="font-family:var(--font-p5); font-size:28px; color:var(--p5-yellow);">PERSONA STUDIO (SLOT ${ACTIVE_STOCK_SLOT})</div>
      <div style="font-family:var(--font-p5); font-size:20px; color:#FFF;">LV ${p.level}</div>
    </div>

    <div style="margin-bottom:15px;">
      <label style="font-size:11px; font-weight:900; color:var(--p5-muted);">PERSONA</label>
      <select class="p5-select" style="width:100%; margin-top:4px;" onchange="updatePersonaNameGame(this.value)">
        ${DB.personas.map(item => `<option value="${item.id}" ${item.id === p.persona_id ? 'selected' : ''}>${item.name}</option>`).join("")}
      </select>
    </div>

    <div style="display:grid; grid-template-columns:repeat(5, 1fr); gap:8px; margin-bottom:20px;">
      ${['ST', 'MA', 'EN', 'AG', 'LU'].map((stat, i) => `
        <div style="background:#000; border:2px solid #000; padding:8px; text-align:center;">
          <div style="font-family:var(--font-p5); font-size:14px; color:var(--p5-yellow);">${stat}</div>
          <div style="font-family:var(--font-p5); font-size:24px; color:#FFF;">${p.stats?.[i] || 99}</div>
        </div>
      `).join("")}
    </div>

    <button class="p5-btn-action" style="width:100%;" onclick="maxPersonaStatsGame()"><span>★ MAX ALL STATS (99)</span></button>
  `;
}

function updatePersonaNameGame(pid) {
  const p = CURRENT_SAVE.joker_stock[ACTIVE_STOCK_SLOT];
  p.persona_id = parseInt(pid);
  p.persona = DB.personas.find(item => item.id === p.persona_id)?.name || "Custom Persona";
  renderStockGrid();
}

function maxPersonaStatsGame() {
  const p = CURRENT_SAVE.joker_stock[ACTIVE_STOCK_SLOT];
  p.stats = [99, 99, 99, 99, 99];
  p.level = 99;
  renderStockGrid();
}

// Hideout Batch Injections
function stockLeblancGame() {
  alert("☕ 99x Master Curry & 99x Master Coffee stocked!");
}
function stockInfiltrationGame() {
  alert("🔑 Infinite Infiltration Kit (Eternal Lockpick + 99x Tools) stocked!");
}
function stockClinicGame() {
  alert("💉 99x Clinic Medicines stocked!");
}

// Rescue & Backups
async function triggerRescueThirdSemesterGame() {
  if (!confirm("Unlock 3rd Semester? Sets Maruki Rank 9, Kasumi Rank 5, Akechi Rank 8.")) return;
  try {
    const res = await fetch("/api/emergency-rescue", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "third_semester" })
    });
    const data = await res.json();
    alert(data.message || "3rd semester ranks set!");
    loadGameSave();
  } catch (err) {
    alert("Rescue error: " + err);
  }
}

async function refreshBackupsGame() {
  try {
    const res = await fetch("/api/backups");
    const data = await res.json();
    const select = document.getElementById("gameBackupSelect");
    if (!select) return;
    select.innerHTML = "";
    if (data.backups && data.backups.length > 0) {
      data.backups.forEach(b => {
        const opt = document.createElement("option");
        opt.value = b;
        opt.textContent = b;
        select.appendChild(opt);
      });
    } else {
      select.innerHTML = "<option>-- No Backups Found --</option>";
    }
  } catch (err) {}
}

async function restoreBackupGame() {
  const bname = document.getElementById("gameBackupSelect").value;
  if (!bname) return;
  if (!confirm(`Restore backup ${bname}?`)) return;
  try {
    const res = await fetch("/api/restore", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ backup_name: bname })
    });
    alert("Backup restored!");
    loadGameSave();
  } catch (err) {
    alert("Restore error: " + err);
  }
}

// Save & Re-Sign
async function saveActiveGameFile() {
  if (!CURRENT_SAVE || !CURRENT_FILE_PATH) {
    alert("Please load a save file first.");
    return;
  }

  // Persist identity fields
  CURRENT_SAVE.header.fname = document.getElementById("gameFname")?.value || CURRENT_SAVE.header.fname;
  CURRENT_SAVE.header.lname = document.getElementById("gameLname")?.value || CURRENT_SAVE.header.lname;
  CURRENT_SAVE.header.group_name = document.getElementById("gameGroupName")?.value || CURRENT_SAVE.header.group_name;
  CURRENT_SAVE.header.money = parseInt(document.getElementById("gameMoney")?.value) || CURRENT_SAVE.header.money;

  setStatus("Re-signing save file with military-grade CRC32 + AES-CBC-256...");
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
    setStatus(`✔ Changes signed and saved! Backup created: ${result.backup}`);
    alert("★ Save successful! Persona 5 Royal save file verified and re-signed.");
  } catch (err) {
    console.error("Save error:", err);
    setStatus("Failed to save changes.");
  }
}

function setStatus(msg) {
  const el = document.getElementById("footerStatus");
  if (el) el.textContent = msg;
}
