# Phase 4 Implementation Plan: Ransom-Note Command Typography

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Implement authentic cut-paper ransom-note display typography across all stage headlines and major command banners in Change of Heart.

**Architecture:** Define modular CSS utility classes (.p5-ransom-banner, .ransom-word, .ransom-tile) in web-app/static/app.css and update stage headers in web-app/templates/index.html.

**Tech Stack:** Pure Vanilla CSS, HTML5, Google Fonts (Bebas Neue, Oswald, Rubik Mono One, Permanent Marker).

## Global Constraints
- Ground truth from official screens in design/reference/ and docs/UI_NORTH_STAR.md Law #7.
- Zero emojis; text tiles and geometric cutouts only.
- All 176 backend unit tests must pass before and after changes.
- Invariant checks via python scripts/check-invariants.py must remain 100% clean.

---

### Task 1: CSS Ransom-Note Component System
**Files:**
- Modify: web-app/static/app.css

- [ ] **Step 1: Implement .p5-ransom-banner, .ransom-word, and .ransom-tile in app.css**
  - Add font-family alternating classes with micro-rotations.
  - Implement hard offset shadow backing and stage-accent slash bars.

- [ ] **Step 2: Verify syntax & run unit tests**
  - Run python -m unittest discover -s tests.

---

### Task 2: Stage Headline & Card Header Markup Elevation
**Files:**
- Modify: web-app/templates/index.html

- [ ] **Step 1: Refactor stage headlines across all 5 stages in index.html**
  - Convert standard <h2> tags to use .p5-ransom-banner styling with alternating word tiles.

- [ ] **Step 2: Complete invariant & test verification**
  - Run python scripts/check-invariants.py.
