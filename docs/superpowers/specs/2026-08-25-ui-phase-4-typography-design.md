# Phase 4 Design Spec: Ransom-Note Command Typography (1:1 P5R Fidelity)

**Created:** 2026-08-25  
**Status:** APPROVED FOR IMPLEMENTATION  
**Ground Truth:** Official P5R Screens (12558.jpg, 96158.jpg, 63559.jpg), docs/UI_NORTH_STAR.md Law #7 (Ransom-note typography for command words).

---

## 1. Overview & Objective
Transform stage command titles, primary card headers, and call-to-action banners into authentic cut-paper **ransom-note typography** (mixing display fonts Bebas Neue, Oswald, and Rubik Mono One/Permanent Marker with alternating black/white/red tile blocks and diagonal slash bars).

---

## 2. Typography & Structural Rules

### A. Ransom-Note Component Utility (.p5-ransom-banner)
1. **Multi-Font Word Architecture:**
   - Word blocks wrap alternating letter/word spans with distinct font families (--font-p5, --font-punk, 'Oswald', 'Bebas Neue').
   - Micro-rotations (
otate(-2deg), 
otate(1.5deg), 
otate(-1deg)) on individual letter blocks to create the cut-magazine collage aesthetic.
2. **High-Contrast Tile Substrates:**
   - Alternating black tiles with white text, white tiles with black text, and stage-accented slash bars (order-left: 6px solid var(--stage-accent)).
   - Hard offset shadows: ox-shadow: 4px 4px 0 #000, 6px 6px 0 var(--stage-accent).

### B. Stage Headline Refactoring (web-app/templates/index.html)
1. **Stage 1 (Daily Life):** ★ DAILY LIFE & PHANTOM IDENTITY
2. **Stage 2 (Item Studio):** ★ ITEM STUDIO & CHEAT SHOP
3. **Stage 3 (Velvet Room):** ★ VELVET ROOM & COMPENDIUM
4. **Stage 4 (God Presets):** ★ 1-CLICK GOD-TIER BUILDS
5. **Stage 5 (Backups Vault):** ★ SAFETY VAULT & BACKUPS

---

## 3. Verification & Invariants
1. **Test Suite Integrity:** All 176 backend unit tests remain 100% passing (python -m unittest discover -s tests).
2. **DOM / JS Integrity:** 
ode --check web-app/static/app.js returns clean.
3. **Invariant Checks:** python scripts/check-invariants.py passes 100%.
