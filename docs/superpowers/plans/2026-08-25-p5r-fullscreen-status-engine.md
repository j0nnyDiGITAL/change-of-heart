# Full-Bleed Status & Leader Hub Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Transform Stage 1 (Daily Life & Leader Profile) into an authentic, full-bleed, mouse-driven Persona 5 Royal Status screen grounded in official reference 27809.jpg and 76684.jpg.

**Architecture:** Pure CSS3 asymmetric shards, comic speech-bubble controls, high-contrast monochrome character art, and modal prompt overlays for mouse-driven text/number editing.

**Tech Stack:** Vanilla CSS3 (clip-path polygons, hard drop shadows, skew transforms), HTML5, JS bindings, Python unittest.

## Global Constraints
- Ground truth from 27809.jpg and 76684.jpg in design/reference/.
- Zero standard HTML form input boxes on the primary Status canvas (replaced with interactive styled shards and Atlus prompt overlays).
- All 176 backend unit tests must pass before and after changes.
- Invariant checks via python scripts/check-invariants.py must remain 100% clean.

---

### Task 1: Core Layout CSS & Shard Component Engine
**Files:**
- Modify: web-app/static/app.css

- [ ] **Step 1: Write CSS rules for full-bleed Status canvas, hero name polygon, combat stats shard, speech-bubble switchers, and prompt overlays**
- [ ] **Step 2: Validate syntax via node --check web-app/static/app.js**

---

### Task 2: Stage 1 Template Overhaul & Mouse Dialog Handlers
**Files:**
- Modify: web-app/templates/index.html
- Modify: web-app/static/app.js

- [ ] **Step 1: Overhaul Stage 1 HTML structure with authentic shards and speech-bubble view toggles**
- [ ] **Step 2: Wire mouse click events in app.js for name editing modal, quick yen editor, and social stats radar**
- [ ] **Step 3: Run unit test suite and invariant checks**

---

### Task 3: Visual Verification & Reference Comparison
**Files:**
- Run: tools/capture_ui_state.py
- Update: walkthrough.md

- [ ] **Step 1: Capture live browser screenshot of redesigned Stage 1**
- [ ] **Step 2: Compare against design/reference/Persona-5-Royal03112021-110112-27809.jpg**
- [ ] **Step 3: Commit and sync state**
