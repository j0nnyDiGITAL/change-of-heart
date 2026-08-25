# Phase 3 Design Spec: Global Geometry & Hard Shadow Pass (1:1 P5R Fidelity)

**Created:** 2026-08-25  
**Status:** APPROVED FOR IMPLEMENTATION  
**Ground Truth:** 146 official P5R screens (design/reference/), docs/UI_NORTH_STAR.md Law #5 (Parallelograms only) & Law #6 (Hard offset shadows).

---

## 1. Overview & Objective
Systematically refactor the visual geometry and shadow system across all Change of Heart stages to eliminate all rounded-corner artifacts (order-radius) and soft Gaussian blur shadows, achieving 100% authentic Atlus Persona 5 Royal mechanical angularity.

---

## 2. Core Architectural & Visual Changes

### A. Global Control Geometry (web-app/static/app.css)
1. **Interactive Inputs & Selects:**
   - Eliminate order-radius: 4px/6px/8px/12px.
   - Apply 	ransform: skew(-10deg) or clipped polygon chamfers (clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 8px 100%, 0 calc(100% - 8px))).
   - Text contents counter-skewed 	ransform: skew(10deg) to preserve crisp, undistorted font rendering.
2. **Buttons & Action Banners (.p5-btn-action, .filter-pill, .rank-stepper-btn):**
   - Pure sharp polygon geometry (order-radius: 0).
   - Hard offset shadows: ox-shadow: 3px 3px 0 #000 (idle) and ox-shadow: 4px 4px 0 var(--p5-blue-deep) (active/selected).
   - High-contrast inversion on hover (instant snap, no mushy easing).

### B. Modals, Dossiers & Dialog Frames
1. **Modal Windows (.p5-modal-content, .spotlight-dossier-grid):**
   - Sharp diagonal framing with high-contrast borders (2px solid var(--p5-white)).
   - Hard drop shadow partner: ox-shadow: 8px 8px 0 #000, 12px 12px 0 var(--p5-red-deep).
2. **Cards & List Items (.p5-card, .p5-tarot-card, .compendium-card):**
   - Zero rounded corners; crisp diagonal left-accent border tabs.

---

## 3. Verification & Invariants
1. **No Broken Invariants:** All 176 backend and parser unit tests remain 100% passing (python -m unittest discover -s tests).
2. **Syntax Validation:** 
ode --check web-app/static/app.js returns clean.
3. **Headless Visual Capture Verification:** All 10 canonical views captured via python tools/capture_ui_state.py to confirm zero layout overflow or clipped inputs.
