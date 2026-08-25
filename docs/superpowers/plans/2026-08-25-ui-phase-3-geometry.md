# Phase 3 Implementation Plan: Global Geometry & Hard Shadows

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Eliminate all rounded-corner artifacts (order-radius) and soft Gaussian blur shadows across all Change of Heart stages, applying authentic Atlus P5R parallelogram and clipped-chamfer geometry with hard offset shadows.

**Architecture:** Refactor base utility and component rules in web-app/static/app.css and element markup in web-app/templates/index.html to standardize on skew(-10deg) geometry, clip-path chamfers, and crisp directional ox-shadow: Npx Npx 0 <color>.

**Tech Stack:** Pure Vanilla CSS, HTML5, PyWebView, Python unittest.

## Global Constraints
- Ground truth from 146 official game screens in design/reference/ and docs/UI_NORTH_STAR.md Law #5 & #6.
- Zero border-radius on primary controls, inputs, and buttons.
- All 176 backend unit tests must pass before and after changes.
- Invariant checks via python scripts/check-invariants.py must remain 100% clean.

---

### Task 1: Global Input, Search, and Dropdown Geometry
**Files:**
- Modify: web-app/static/app.css
- Modify: web-app/templates/index.html

- [ ] **Step 1: Refactor input and select box classes in app.css**
  - Set order-radius: 0; on .p5-input, .p5-select, .p5-search-box, #unifiedItemSearchBox, #compendiumSearchInput.
  - Add hard offset shadow ox-shadow: 3px 3px 0 #000;.
  - Apply skewed wrapper styling with counter-skewed text for clean legibility.

- [ ] **Step 2: Verify syntax & run tests**
  - Run 
ode --check web-app/static/app.js and python -m unittest discover -s tests.

---

### Task 2: Action Buttons, Steppers & Filter Pills Geometry
**Files:**
- Modify: web-app/static/app.css

- [ ] **Step 1: Refactor button and pill classes in app.css**
  - Set order-radius: 0; on .p5-btn-action, .filter-pill, .rank-stepper-btn, .category-tab.
  - Replace soft box-shadows with directional hard offset shadows (ox-shadow: 3px 3px 0 #000;, active ox-shadow: 4px 4px 0 var(--p5-blue-deep);).
  - Wire crisp solid color hover/active states.

- [ ] **Step 2: Verify syntax & run tests**
  - Run 
ode --check web-app/static/app.js and python -m unittest discover -s tests.

---

### Task 3: Modals, Dossiers & Shard Card Paneling
**Files:**
- Modify: web-app/static/app.css

- [ ] **Step 1: Update modal and card border geometry**
  - Set order-radius: 0; on .p5-modal-content, .p5-card, .dossier-panel, .spotlight-header-card.
  - Apply double hard drop shadow ox-shadow: 6px 6px 0 #000, 10px 10px 0 var(--p5-red-deep);.

- [ ] **Step 2: Run complete verification suite & capture state**
  - Run python scripts/check-invariants.py.
