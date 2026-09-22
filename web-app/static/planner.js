/* =========================================================================
   planner.js — Time Travel Planner (Tier 0) + Deadline Escape Hatch (Tier 2)
   ADR 0003. Loaded after app.js; depends on switchStage() hooks there.
   ========================================================================= */

/* ===================== TIME TRAVEL PLANNER (READ-ONLY) =====================
   ADR 0003 Tier 0: pure projection of /api/calendar. No save writes exist
   for the in-game date — this panel only informs the player.
   ========================================================================= */
let CALENDAR_PLAN = null;

async function loadCalendar() {
  try {
    const res = await fetch("/api/calendar");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    CALENDAR_PLAN = await res.json();
    renderCalendarMonthSelect();
    renderCalendarMonth();
    renderCalendarDeadlines();
  } catch (err) {
    console.error("loadCalendar failed:", err);
    const grid = document.getElementById("calendarMonthGrid");
    if (grid) grid.innerHTML = `<div class="calendar-empty">⚠️ Planner unavailable (${String(err).replace(/</g, "&lt;")})</div>`;
  }
}

function renderCalendarMonthSelect() {
  const sel = document.getElementById("calendarMonthSelect");
  if (!sel || !CALENDAR_PLAN) return;
  const prev = sel.value;
  sel.innerHTML = CALENDAR_PLAN.months
    .map((m) => `<option value="${m.month}">${m.name}</option>`)
    .join("");
  let defaultMonth = prev ? Number(prev) : (CALENDAR_PLAN.today ? CALENDAR_PLAN.today.month : 4);
  if (![...sel.options].some((o) => Number(o.value) === defaultMonth)) defaultMonth = 4;
  sel.value = String(defaultMonth);
}

function renderCalendarMonth() {
  const grid = document.getElementById("calendarMonthGrid");
  const badge = document.getElementById("calendarTodayBadge");
  if (!grid || !CALENDAR_PLAN) return;
  const sel = document.getElementById("calendarMonthSelect");
  const monthIdx = Number(sel ? sel.value : 4);
  const month = CALENDAR_PLAN.months.find((m) => m.month === monthIdx) || CALENDAR_PLAN.months[0];
  const today = CALENDAR_PLAN.today;

  if (badge) {
    badge.textContent = today
      ? `TODAY: ${today.label || `${today.month}/${today.day}`}`
      : "NO SAVE LOADED — FULL YEAR VIEW";
  }

  const cells = month.days
    .map((d) => {
      const isToday = today && today.month === month.month && today.day === d.day;
      const cls = ["cal-cell", `cal-${d.class}`, isToday ? "cal-is-today" : ""]
        .filter(Boolean)
        .join(" ");
      return `<div class="${cls}" title="${month.name} ${d.day} — ${d.weekday}">${d.day}</div>`;
    })
    .join("");
  grid.innerHTML = cells;
}

/* ===================== DEADLINE ESCAPE HATCH (TIER 2) =====================
   ADR 0003: rollback to a pre-deadline backup + D016-safe rank write so the
   game's own gate passes. Dry-run preview first, explicit typed confirm.
   ========================================================================= */
let ESCAPE_STATUS = null;

async function loadEscapeHatch() {
  const body = document.getElementById("escapeHatchBody");
  if (!body) return;
  try {
    const res = await fetch("/api/deadline-status");
    ESCAPE_STATUS = await res.json();
    renderEscapeHatch();
  } catch (err) {
    body.innerHTML = `<div class="calendar-empty">⚠️ Gate status unavailable</div>`;
  }
}

function renderEscapeHatch() {
  const body = document.getElementById("escapeHatchBody");
  if (!body || !ESCAPE_STATUS) return;
  if (!ESCAPE_STATUS.save_loaded) {
    body.innerHTML = `<div class="calendar-empty">Load a save to check the Maruki / Akechi gates.</div>`;
    return;
  }
  const gates = ESCAPE_STATUS.gates || [];
  const rows = gates.map((g) => {
    const badge = g.met
      ? `<span class="cal-status cal-met">RANK ${g.current_rank} ✔ MET</span>`
      : `<span class="cal-status cal-risk">RANK ${g.current_rank ?? "?"} — NEEDS ${g.required_rank}</span>`;
    const past = g.deadline_passed
      ? `<span class="cal-status cal-unknown">DEADLINE PASSED</span>`
      : `<span class="cal-count">deadline ${g.deadline}</span>`;
    const fixable = !g.met;
    return `<div class="cal-deadline-row ${g.met ? "" : "row-risk"}" style="margin-bottom:8px;">
      <div class="cal-deadline-head">
        <span class="cal-date">${g.confidant}</span>${badge}${past}
      </div>
      ${fixable ? `<button class="p5-btn-action" style="padding:5px 14px; font-size:12px;" onclick="openEscapeHatch('${g.gate_key}')"><span>PLAN ESCAPE</span></button>` : ""}
    </div>`;
  }).join("");
  const nBackups = (ESCAPE_STATUS.available_backups || []).length;
  body.innerHTML = `
    ${rows}
    <p style="font-size:11px; color:var(--p5-muted); margin-top:10px;">
      ${ESCAPE_STATUS.is_uploaded
        ? "Uploaded save: escape runs without a vault restore (no backup history)."
        : `${nBackups} backup(s) in the vault. A pre-deadline backup is required for the full escape; without one, only the rank write on the CURRENT date is offered (no calendar rollback).`}
      All runs create timestamped backups first — nothing is irreversible.
    </p>`;
}

async function openEscapeHatch(gateKey) {
  try {
    const res = await fetch("/api/deadline-escape", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ gate_key: gateKey, confirm: false }),
    });
    const plan = await res.json();
    if (!res.ok) { alert(plan.error || "Escape plan failed."); return; }
    if (plan.status === "noop") { alert(plan.message); return; }
    if (plan.status !== "ok") { alert(plan.message || plan.status); return; }

    const backupOptions = (plan.available_backups || [])
      .map((b) => `<option value="${b}">${b}</option>`)
      .join("");
    const g = plan.gate || {};
    const opsHtml = (plan.ops || []).map((o) => `<li>${o.description}</li>`).join("");
    const modal = document.createElement("div");
    modal.className = "p5-modal-backdrop";
    modal.id = "escapeHatchModal";
    modal.innerHTML = `
      <div class="p5-modal-content" style="max-width:560px;">
        <h3 style="font-family:var(--font-p5); letter-spacing:1px; color:var(--p5-crimson); margin-bottom:10px;">🚪 DEADLINE ESCAPE — ${g.confidant || ""}</h3>
        <div style="font-size:12px; color:var(--p5-muted); margin-bottom:10px;">
          Current Rank ${g.current_rank ?? "?"} → Target Rank ${g.required_rank} (deadline ${g.deadline})
        </div>
        <ol style="font-size:12px; color:#DDD; padding-left:18px; margin-bottom:12px;">${opsHtml}</ol>
        ${plan.available_backups && plan.available_backups.length
          ? `<label style="font-size:11px; color:var(--p5-muted);">RESTORE FROM BACKUP (pre-deadline):</label>
             <select id="escapeBackupSelect" class="p5-select" style="width:100%; margin:6px 0 12px;"><option value="">— no restore, write on current save —</option>${backupOptions}</select>`
          : `<p style="font-size:11px; color:var(--p5-yellow); margin-bottom:12px;">⚠ No vault backups found — the rank write will run on the CURRENT save (no calendar rollback).</p>`}
        <p style="font-size:11px; color:var(--p5-muted); margin-bottom:12px;">${plan.warning || ""}</p>
        <label style="font-size:11px; color:var(--p5-muted);">Type <b style="color:var(--p5-crimson);">TAKE MY HEART</b> to confirm:</label>
        <input id="escapeConfirmInput" class="p5-input" style="width:100%; margin:6px 0 12px;" autocomplete="off">
        <div style="display:flex; gap:10px;">
          <button class="p5-btn-action" id="escapeExecBtn"><span>EXECUTE ESCAPE</span></button>
          <button class="p5-btn-action secondary" onclick="document.getElementById('escapeHatchModal').remove()"><span>CANCEL</span></button>
        </div>
      </div>`;
    document.body.appendChild(modal);
    modal.classList.add("open");
    document.getElementById("escapeExecBtn").onclick = () => executeEscapeHatch(gateKey);
  } catch (err) {
    alert("Escape plan failed: " + err);
  }
}

async function executeEscapeHatch(gateKey) {
  const typed = (document.getElementById("escapeConfirmInput")?.value || "").trim().toUpperCase();
  if (typed !== "TAKE MY HEART") { alert("Confirmation phrase does not match."); return; }
  const backupName = document.getElementById("escapeBackupSelect")?.value || "";
  const btn = document.getElementById("escapeExecBtn");
  btn.disabled = true;
  try {
    const res = await fetch("/api/deadline-escape", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ gate_key: gateKey, confirm: true, backup_name: backupName }),
    });
    const data = await res.json();
    if (!res.ok) { alert(data.error || "Escape failed."); return; }
    document.getElementById("escapeHatchModal")?.remove();
    const restored = data.restored_from ? `Restored: ${data.restored_from}. ` : "";
    const bkp = data.backup ? ` Backup: ${data.backup}.` : "";
    const integrity = data.integrity && data.integrity.ok ? " Integrity ✔" : (data.integrity ? " ⚠ Check integrity panel." : "");
    alert(`ESCAPE COMPLETE — ${data.confidant} → Rank ${data.rank_written}. ${restored}${bkp}${integrity}\n\nReload the save in-game from the restored day and play forward — the game will evaluate the gate on its scheduled date.`);
    loadCalendar();
    loadEscapeHatch();
  } catch (err) {
    alert("Escape failed: " + err);
  } finally {
    btn.disabled = false;
  }
}

function renderCalendarDeadlines() {
  const list = document.getElementById("calendarDeadlinesList");
  if (!list || !CALENDAR_PLAN) return;
  const rows = CALENDAR_PLAN.deadlines || [];
  if (!rows.length) {
    list.innerHTML = `<div class="calendar-empty">✔ No upcoming deadlines — free roam until the finale.</div>`;
    return;
  }
  list.innerHTML = rows
    .map((r) => {
      const isGate = r.kind === "gate";
      const countdown =
        r.days_left === null || r.days_left === undefined
          ? ""
          : r.days_left === 0
            ? `<span class="cal-count cal-today">TODAY</span>`
            : `<span class="cal-count">in ${r.days_left}d</span>`;
      const gateBadge = !isGate
        ? ""
        : r.status === "met"
          ? `<span class="cal-status cal-met">RANK ${r.current_rank} ✔ MET</span>`
          : r.status === "at_risk"
            ? `<span class="cal-status cal-risk">RANK ${r.current_rank ?? "?"} — NEEDS ${r.required_rank}</span>`
            : `<span class="cal-status cal-unknown">RANK ? — NEEDS ${r.required_rank}</span>`;
      return `<div class="cal-deadline-row ${r.status === "at_risk" ? "row-risk" : ""}">
        <div class="cal-deadline-head">
          <span class="cal-date">${r.month}/${r.day}<small>(${r.weekday})</small></span>
          ${countdown}${gateBadge}
        </div>
        <div class="cal-deadline-label">${r.label}</div>
        <div class="cal-deadline-note">${r.note}</div>
      </div>`;
    })
    .join("");
}

/* ===================== TIME WARP (CHRONOS ENGINE, V2) =====================
   Script-derived, forward-only date advance with branch-bit resolution
   (ADR 0004). Clean runways behave exactly like v1. Story windows resolve
   through verified branch bits: the plan carries branch_choices the
   user must acknowledge, the arrival-day scheduler plays the equivalent
   scenes live. Writes: hdr.day + 0x3D70 mirror + verified bits only.
   ====================================================================== */
let WARP_PLAN = null;

async function planTimeWarp() {
  const msel = document.getElementById("warpMonth");
  const dsel = document.getElementById("warpDay");
  const out = document.getElementById("timeWarpResult");
  if (!msel || !dsel || !out) return;
  const m = Number(msel.value), d = Number(dsel.value);
  if (!m || !d) { out.innerHTML = `<span style="color:var(--p5-yellow);">Pick a destination month/day first.</span>`; return; }
  out.innerHTML = `<span style="color:var(--p5-muted);">Plotting course…</span>`;
  try {
    const res = await fetch("/api/time-travel", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_month: m, target_day: d, confirm: false }),
    });
    const plan = await res.json();
    if (!res.ok && plan.status !== "confirm_required") {
      out.innerHTML = `<div style="color:var(--p5-crimson); font-weight:700;">⛔ ${String(plan.reason || plan.error || "Plan refused").replace(/</g, "&lt;")}</div>
        ${plan.v2 && plan.v2.reason ? `<div style="color:var(--p5-muted); font-size:12px; margin-top:6px;">${String(plan.v2.reason).replace(/</g, "&lt;")}</div>` : ""}`;
      return;
    }
    if (plan.status === "invalid") {
      out.innerHTML = `<div style="color:var(--p5-crimson); font-weight:700;">⛔ ${String(plan.reason || "Plan refused").replace(/</g, "&lt;")}</div>`;
      return;
    }
    if (plan.status === "blocked") {
      const days = (plan.blocked_days || []).map((b) => b.date).join(", ");
      out.innerHTML = `<div style="color:var(--p5-crimson); font-weight:700;">⛔ WARP REFUSED — story events on: ${String(days).replace(/</g, "&lt;")}</div>
        ${plan.windows_overlapped && plan.windows_overlapped.length ? `<div style="color:var(--p5-yellow); font-size:12px; margin-top:6px;">Known windows crossed: ${plan.windows_overlapped.map((w) => `${String(w.label).replace(/</g, "&lt;")}${w.verified ? "" : " (branch bits not yet verified — not warpable)"}`).join("; ")}</div>` : ""}
        ${plan.v2 && plan.v2.reason ? `<div style="color:var(--p5-muted); font-size:12px; margin-top:6px;">${String(plan.v2.reason).replace(/</g, "&lt;")}</div>` : ""}`;
      return;
    }
    const cur = plan.current ? plan.current.date : "?";
    if (plan.status === "blocked_resolvable") {
      WARP_PLAN = { m, d, choices: (plan.v2.branch_choices || []).map((c) => c.choice_id) };
      const choiceCards = (plan.v2.branch_choices || []).map((c, i) => `
        <div class="warp-branch-card">
          <div style="font-weight:700; color:var(--p5-yellow);">BRANCH RESOLVED BY YOUR DESTINATION</div>
          <div style="margin:6px 0 2px 0; font-size:13px;">${String(c.label).replace(/</g, "&lt;")}</div>
          <div style="color:var(--p5-muted); font-size:12px; margin-bottom:6px;">${String(c.description).replace(/</g, "&lt;")}</div>
          ${(c.branches || []).map((b) => `<div style="font-size:12px; ${b.offered ? "color:var(--p5-cyan);" : "color:var(--p5-muted); text-decoration:line-through;"}">▸ ${String(b.branch).replace(/</g, "&lt;")} — ${String(b.why).replace(/</g, "&lt;")}</div>`).join("")}
          <div style="color:var(--p5-muted); font-size:11px; margin-top:6px;">State set on your save: ${(c.bits || []).map((b) => String(b.label).replace(/</g, "&lt;")).join(", ")}. Arrival ${String(c.arrival).replace(/</g, "&lt;")}: the game plays the scenes itself.</div>
        </div>`).join("");
      out.innerHTML = `<div style="color:var(--p5-yellow); font-weight:700;">⚡ WARP POSSIBLE WITH BRANCH RESOLUTION: ${cur} → ${plan.target.date} (${plan.days_skipped} days skipped)</div>
        ${choiceCards}
        <div style="color:var(--p5-muted); font-size:12px; margin:8px 0 10px 0;">The engine refused (story days ahead). Warp v2 pre-sets the verified branch bits the game checks, so the engine itself replays the story on arrival. Backup taken automatically.</div>
        <button class="p5-btn-action" style="padding:6px 18px; font-size:13px;" onclick="executeTimeWarp(${m}, ${d})"><span>ACKNOWLEDGE & WARP</span></button>`;
      return;
    }
    out.innerHTML = `<div style="color:var(--p5-cyan); font-weight:700;">✅ WARP VIABLE: ${cur} → ${plan.target.date} (${plan.days_skipped} days skipped)</div>
      <div style="color:var(--p5-muted); font-size:12px; margin:6px 0 10px 0;">Every skipped day is ambient/free per the game's own scheduler scripts. Writes: header day + day-counter mirror only, backup taken automatically.</div>
      <button class="p5-btn-action" style="padding:6px 18px; font-size:13px;" onclick="executeTimeWarp(${m}, ${d})"><span>EXECUTE TIME WARP</span></button>`;
  } catch (err) {
    out.innerHTML = `<div style="color:var(--p5-crimson);">Plan failed: ${String(err).replace(/</g, "&lt;")}</div>`;
  }
}

async function executeTimeWarp(m, d) {
  const out = document.getElementById("timeWarpResult");
  const body = { target_month: m, target_day: d, confirm: true };
  if (WARP_PLAN && WARP_PLAN.m === m && WARP_PLAN.d === d && WARP_PLAN.choices) {
    const acknowledged = confirm(
      `Branch choice: ${WARP_PLAN.choices.join(", ")}\n\n` +
      `The skipped story days are resolved through verified branch bits; the game replays the scenes on arrival.\n` +
      `A timestamped backup is taken automatically. Do not run P5R during the warp.\n\nProceed?`);
    if (!acknowledged) return;
    body.choice_ids = WARP_PLAN.choices;
  } else {
    if (!confirm(`Time warp to ${m}/${d}?\n\nA timestamped backup is taken automatically. Do not run P5R during the warp.`)) return;
  }
  try {
    const res = await fetch("/api/time-travel", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const r = await res.json();
    if (!res.ok) {
      out.innerHTML = `<div style="color:var(--p5-crimson);">⛔ ${String(r.error || r.message || "Warp refused").replace(/</g, "&lt;")}</div>`;
      return;
    }
    const bits = (r.bits_written || []).map((b) => String(b.label).replace(/</g, "&lt;")).join(", ");
    out.innerHTML = `<div style="color:var(--p5-cyan); font-weight:700;">🌀 TIME WARP COMPLETE — it is now ${r.plan.target.date}. Reload the save in P5R to continue from there.</div>
      ${bits ? `<div style="color:var(--p5-muted); font-size:12px; margin-top:4px;">Branch state written: ${bits}</div>` : ""}
      <div style="color:var(--p5-muted); font-size:12px; margin-top:4px;">Backup: ${String(r.backup || "n/a (uploaded save — use download)").replace(/</g, "&lt;")}</div>`;
    WARP_PLAN = null;
    if (typeof loadCalendar === "function") loadCalendar();
    if (typeof loadEscapeHatch === "function") loadEscapeHatch();
    if (typeof loadStatus === "function") loadStatus();
  } catch (err) {
    out.innerHTML = `<div style="color:var(--p5-crimson);">Warp failed: ${String(err).replace(/</g, "&lt;")}</div>`;
  }
}

/* ===================== PALACE SKIP (CHRONOS ENGINE) =====================
   Set guard + discovery bits, warp to deadline day. Engine replays
   post-clearance scenes on arrival. No event fabrication needed.
   ====================================================================== */
let PALACE_SKIP_CATALOG = null;

async function loadPalaceSkipCatalog() {
  try {
    const res = await fetch("/api/palace-skip", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    PALACE_SKIP_CATALOG = data.catalog || [];
    renderPalaceSkipPanel();
  } catch (err) {
    console.error("loadPalaceSkipCatalog failed:", err);
  }
}

function renderPalaceSkipPanel() {
  const body = document.getElementById("palaceSkipBody");
  if (!body || !PALACE_SKIP_CATALOG) return;

  const rows = PALACE_SKIP_CATALOG.map((p) => {
    const statusBadge = {
      available: `<span class="cal-status cal-met">AVAILABLE</span>`,
      cleared: `<span class="cal-status cal-met">CLEARED ✔</span>`,
      too_late: `<span class="cal-status cal-unknown">PAST DEADLINE</span>`,
      too_early: `<span class="cal-status cal-risk">PALACE NOT YET DISCOVERED</span>`,
      unknown: `<span class="cal-status cal-unknown">UNKNOWN</span>`,
    }[p.status] || `<span class="cal-status cal-unknown">${p.status}</span>`;

    const canSkip = p.status === "available";
    return `<div class="cal-deadline-row ${canSkip ? "" : "row-risk"}" style="margin-bottom:8px;">
      <div class="cal-deadline-head">
        <span class="cal-date">${p.label}</span>${statusBadge}
      </div>
      <div style="font-size:11px; color:var(--p5-muted);">
        Deadline: ${p.deadline} | Earliest entry: ${p.earliest_entry} | Unlocks: ${p.party_unlock}
      </div>
      ${canSkip ? `<div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:6px;">
        <button class="p5-btn-action" style="padding:5px 14px; font-size:12px;" onclick="planPalaceSkip('${p.palace_id}', 'claim')"><span>⚔ SKIP GRIND — KEEP CALENDAR</span></button>
        <button class="p5-btn-action secondary" style="padding:5px 14px; font-size:12px;" onclick="planPalaceSkip('${p.palace_id}', 'deadline')"><span>⏭ JUMP TO DEADLINE</span></button>
      </div>` : ""}
    </div>`;
  }).join("");

  body.innerHTML = rows || `<div class="calendar-empty">No palaces found.</div>`;
}

async function planPalaceSkip(palaceId, mode = "deadline") {
  const out = document.getElementById("palaceSkipResult");
  if (!out) return;
  out.innerHTML = `<span style="color:var(--p5-muted);">Planning skip…</span>`;
  try {
    const res = await fetch("/api/palace-skip", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ palace_id: palaceId, mode, confirm: false }),
    });
    const plan = await res.json();
    if (!res.ok || !plan.allowed) {
      out.innerHTML = `<div style="color:var(--p5-crimson); font-weight:700;">⛔ ${String(plan.reason || plan.error || "Skip refused").replace(/</g, "&lt;")}</div>`;
      return;
    }
    const bits = (plan.bits_to_write || []).map((b) => `<li>${String(b.label).replace(/</g, "&lt;")} (${String(b.bit_id).replace(/</g, "&lt;")})</li>`).join("");
    const notes = (plan.notes || []).map((n) => `<div style="font-size:11px; color:var(--p5-muted);">▸ ${String(n).replace(/</g, "&lt;")}</div>`).join("");
    const esc = (x) => String(x).replace(/</g, "&lt;");
    const isClaim = plan.mode === "claim";
    const headline = isClaim
      ? `✅ GRIND SKIP VIABLE: it is ${plan.current.date} — the clock will NOT move. All days until the ${plan.deadline} deadline stay yours.`
      : `✅ SKIP VIABLE: ${plan.current.date} → ${plan.target.date} (${plan.days_saved} days saved)`;
    out.innerHTML = `<div style="color:var(--p5-cyan); font-weight:700;">${headline}</div>
      <div style="font-size:12px; color:var(--p5-muted); margin:6px 0;">
        <b>${esc(plan.palace_label)}</b> — ${esc(plan.party_unlock)}
      </div>
      <div style="font-size:12px; color:#DDD; margin:6px 0;">Bits written:</div>
      <ol style="font-size:12px; color:#DDD; padding-left:18px; margin:4px 0 8px 0;">${bits}</ol>
      ${notes}
      <button class="p5-btn-action" style="padding:6px 18px; font-size:13px; margin-top:10px;" onclick="executePalaceSkip('${palaceId}', '${mode}')"><span>${isClaim ? "CLAIM CLEAR" : "EXECUTE PALACE SKIP"}</span></button>`;
  } catch (err) {
    out.innerHTML = `<div style="color:var(--p5-crimson);">Plan failed: ${String(err).replace(/</g, "&lt;")}</div>`;
  }
}

async function executePalaceSkip(palaceId, mode = "deadline") {
  const out = document.getElementById("palaceSkipResult");
  const isClaim = mode === "claim";
  const msg = isClaim
    ? "CLAIM CLEAR for this palace?\n\nThe cleared flags are set but the calendar is NOT touched — you keep every day until the deadline. The objective flips to waiting for the change of heart, and all pinned scenes play on their scripted days.\n\nA timestamped backup is taken automatically. Do not run P5R during the skip.\n\nProceed?"
    : "Skip this palace?\n\nThe guard bit will be set and the clock warped to the deadline day. Post-clearance scenes play on arrival. A timestamped backup is taken automatically.\n\nDo not run P5R during the skip.";
  if (!confirm(msg)) return;
  try {
    const res = await fetch("/api/palace-skip", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ palace_id: palaceId, mode, confirm: true }),
    });
    const r = await res.json();
    if (!res.ok) {
      out.innerHTML = `<div style="color:var(--p5-crimson);">⛔ ${String(r.error || r.message || "Skip failed").replace(/</g, "&lt;")}</div>`;
      return;
    }
    const bits = (r.bits_written || []).map((b) => String(b.label).replace(/</g, "&lt;")).join(", ");
    const doneMsg = isClaim
      ? `⚔ PALACE CLEARED, CALENDAR KEPT — it is still ${r.plan.target.date}. The game now treats this palace as secured; play on and the change-of-heart plays on ${r.plan.deadline}.`
      : `🌀 PALACE SKIP COMPLETE — it is now ${r.plan.target.date}. Reload the save in P5R.`;
    out.innerHTML = `<div style="color:var(--p5-cyan); font-weight:700;">${doneMsg}</div>
      <div style="color:var(--p5-muted); font-size:12px; margin-top:4px;">Bits written: ${bits}</div>
      <div style="color:var(--p5-muted); font-size:12px; margin-top:4px;">Backup: ${String(r.backup || "n/a (uploaded save)").replace(/</g, "&lt;")}</div>`;
    loadPalaceSkipCatalog();
    if (typeof loadCalendar === "function") loadCalendar();
    if (typeof loadEscapeHatch === "function") loadEscapeHatch();
    if (typeof loadStatus === "function") loadStatus();
  } catch (err) {
    out.innerHTML = `<div style="color:var(--p5-crimson);">Skip failed: ${String(err).replace(/</g, "&lt;")}</div>`;
  }
}

function initTimeWarpSelects() {
  const msel = document.getElementById("warpMonth");
  const dsel = document.getElementById("warpDay");
  if (!msel || !dsel) return;
  const months = [[4,"April"],[5,"May"],[6,"June"],[7,"July"],[8,"August"],[9,"September"],[10,"October"],[11,"November"],[12,"December"]];
  msel.innerHTML = months.map(([v, n]) => `<option value="${v}">${n}</option>`).join("");
  msel.value = "8";
  const fillDays = () => {
    const mdays = {4:30,5:31,6:30,7:31,8:31,9:30,10:31,11:30,12:31};
    const md = Number(msel.value);
    const prev = dsel.value;
    dsel.innerHTML = Array.from({length: mdays[md]}, (_, i) => `<option value="${i + 1}">${i + 1}</option>`).join("");
    const wanted = Number(prev);
    dsel.value = String(wanted >= 1 && wanted <= mdays[md] ? wanted : Math.min(20, mdays[md]));
  };
  fillDays();
  msel.onchange = fillDays;
}
initTimeWarpSelects();

/* ===================== FULL TIME WARP (CHRONOS V3) =====================
   Complete time machine: clock + ALL palace guard/discovery bits + daily
   event flags, forward AND backward. Same engine the CLI tests used
   (POST /api/full-time-warp). The v2 card above only handles clean
   runways / verified-branch windows — this card goes anywhere on the
   calendar, both directions, with full state sync.
   ====================================================================== */
const FTW_MONTHS = [[4,"April"],[5,"May"],[6,"June"],[7,"July"],[8,"August"],[9,"September"],[10,"October"],[11,"November"],[12,"December"]];
const FTW_MDAYS = {4:30,5:31,6:30,7:31,8:31,9:30,10:31,11:30,12:31};
let FTW_PLAN = null;

function initFtwSelects() {
  const msel = document.getElementById("ftwMonth");
  const dsel = document.getElementById("ftwDay");
  if (!msel || !dsel) return;
  msel.innerHTML = FTW_MONTHS.map(([v, n]) => `<option value="${v}">${n}</option>`).join("");
  const fillDays = () => {
    const prev = dsel.value;
    const md = Number(msel.value);
    dsel.innerHTML = Array.from({length: FTW_MDAYS[md]}, (_, i) => `<option value="${i + 1}">${i + 1}</option>`).join("");
    const wanted = Number(prev);
    dsel.value = String(wanted >= 1 && wanted <= FTW_MDAYS[md] ? wanted : 1);
  };
  fillDays();
  msel.onchange = fillDays;
}

async function planFullTimeWarp() {
  const msel = document.getElementById("ftwMonth");
  const dsel = document.getElementById("ftwDay");
  const out = document.getElementById("ftwResult");
  if (!msel || !dsel || !out) return;
  const m = Number(msel.value), d = Number(dsel.value);
  if (!m || !d) { out.innerHTML = `<span style="color:var(--p5-yellow);">Pick a destination month/day first.</span>`; return; }
  out.innerHTML = `<span style="color:var(--p5-muted);">Plotting course…</span>`;
  try {
    const res = await fetch("/api/full-time-warp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_month: m, target_day: d, confirm: false }),
    });
    const plan = await res.json();
    if (!res.ok) {
      out.innerHTML = `<div style="color:var(--p5-crimson); font-weight:700;">⛔ ${String(plan.error || "Plan refused").replace(/</g, "&lt;")}</div>`;
      return;
    }
    FTW_PLAN = { m, d };
    const s = plan.summary || {};
    const cur = plan.current ? plan.current.date : "?";
    const tgt = plan.target ? plan.target.date : `${m}/${d}`;
    const dir = plan.direction === "backward" ? "◀ BACKWARD" : "▶ FORWARD";
    const esc = (x) => String(x).replace(/</g, "&lt;");
    const ch = plan.changes;
    let detail;
    if (ch) {
      const rows = (ch.palace_changes || []).map((pc) => {
        const bits = [];
        if (pc.guard_change) bits.push(`guard ${pc.guard_change.from} → <b style="color:var(--p5-cyan);">${pc.guard_change.to}</b>`);
        if (pc.discovery_change) bits.push(`discovery ${pc.discovery_change.from} → <b style="color:var(--p5-cyan);">${pc.discovery_change.to}</b>`);
        return `<div style="font-size:12px; color:var(--p5-muted);">▸ ${esc(pc.label)}: ${bits.join(", ")}</div>`;
      }).join("");
      const ef = ch.event_flag_changes || {};
      const flagLine = (ef.set || ef.clear)
        ? `<div style="font-size:12px; color:var(--p5-muted); margin-top:4px;">▸ Daily event flags: <b style="color:var(--p5-cyan);">+${ef.set || 0}</b> set, <b style="color:var(--p5-cyan);">−${ef.clear || 0}</b> cleared</div>`
        : `<div style="font-size:12px; color:var(--p5-muted); margin-top:4px;">▸ Daily event flags: no changes needed</div>`;
      detail = `${rows || `<div style="font-size:12px; color:var(--p5-muted);">▸ Palace flags: no changes needed — your save already matches this date.</div>`}${flagLine}`;
    } else {
      const palaceRows = Object.entries(plan.palaces || {}).map(([pid, ps]) =>
        `<div style="font-size:12px; color:var(--p5-muted);">▸ ${esc(pid)}: guard <b style="color:${ps.guard ? "var(--p5-cyan)" : "var(--p5-muted)"};">${ps.guard ? "SET" : "clear"}</b>, discovery <b style="color:${ps.discovery ? "var(--p5-cyan)" : "var(--p5-muted)"};">${ps.discovery ? "SET" : "clear"}</b></div>`).join("");
      detail = palaceRows;
    }
    const deltaBits = ch ? ((ch.palace_changes || []).reduce((n, pc) => n + (pc.guard_change ? 1 : 0) + (pc.discovery_change ? 1 : 0), 0) + (ch.event_flag_changes ? (ch.event_flag_changes.set || 0) + (ch.event_flag_changes.clear || 0) : 0)) : null;
    out.innerHTML = `<div style="color:var(--p5-cyan); font-weight:700;">${dir} WARP: ${esc(cur)} → ${esc(tgt)}</div>
      <div style="color:var(--p5-muted); font-size:12px; margin:6px 0 4px 0;">${ch ? `Changes to YOUR save: ${deltaBits} bits` + (deltaBits === 1 ? " (a single flag — nothing else moves)" : "") + ". Clock is always rewritten. Backup taken automatically." : `Syncs: palace guards (set ${(s.guards_set || []).length} / clear ${(s.guards_cleared || []).length}), discoveries (set ${(s.discoveries_set || []).length} / clear ${(s.discoveries_cleared || []).length}), event flags (+${s.event_flags_on || 0} on / −${s.event_flags_off || 0} off) and the clock. Backup taken automatically.`}</div>
      ${detail}
      <button class="p5-btn-action" style="padding:6px 18px; font-size:13px; margin-top:10px;" onclick="executeFullTimeWarp(${m}, ${d})"><span>EXECUTE FULL TIME WARP</span></button>`;
  } catch (err) {
    out.innerHTML = `<div style="color:var(--p5-crimson);">Plan failed: ${String(err).replace(/</g, "&lt;")}</div>`;
  }
}

async function executeFullTimeWarp(m, d) {
  const out = document.getElementById("ftwResult");
  const msg = `FULL TIME WARP to ${m}/${d}\n\n` +
    `This writes: the clock, ALL palace guard/discovery bits and ALL daily event flags ` +
    `for the destination date — every day between now and then is synced in one pass, ` +
    `so any date on the calendar is reachable, forward or backward.\n\n` +
    `A timestamped backup is taken automatically. Do not run P5R during the warp.\n\nProceed?`;
  if (!confirm(msg)) return;
  try {
    const res = await fetch("/api/full-time-warp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_month: m, target_day: d, confirm: true }),
    });
    const r = await res.json();
    if (!res.ok) {
      out.innerHTML = `<div style="color:var(--p5-crimson);">⛔ ${String(r.error || r.reason || "Warp refused").replace(/</g, "&lt;")}</div>`;
      return;
    }
    const tgt = r.plan && r.plan.target ? r.plan.target.date : `${m}/${d}`;
    const nb = (r.bits_written || []).length;
    out.innerHTML = `<div style="color:var(--p5-cyan); font-weight:700;">🌀 FULL TIME WARP COMPLETE — it is now ${tgt}. Reload the save in P5R to continue from there.</div>
      <div style="color:var(--p5-muted); font-size:12px; margin-top:4px;">Flag operations written: ${nb}</div>
      <div style="color:var(--p5-muted); font-size:12px; margin-top:4px;">Backup: ${String(r.backup || "n/a (uploaded save — use download)").replace(/</g, "&lt;")}</div>`;
    FTW_PLAN = null;
    if (typeof loadCalendar === "function") loadCalendar();
    if (typeof loadEscapeHatch === "function") loadEscapeHatch();
    if (typeof loadStatus === "function") loadStatus();
  } catch (err) {
    out.innerHTML = `<div style="color:var(--p5-crimson);">Warp failed: ${String(err).replace(/</g, "&lt;")}</div>`;
  }
}

initFtwSelects();
