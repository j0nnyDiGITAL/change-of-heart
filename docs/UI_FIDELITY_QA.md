# UI FIDELITY QA & DESIGN SYSTEM — OPERATION CHANGE OF HEART

**Project:** Change of Heart — Persona 5 Royal Save Editor  
**Repository:** https://github.com/j0nnyDiGITAL/change-of-heart  
**Date:** October 16, 2026  
**Primary Composition Target:** 1920x1080 (Responsive down to 1280x720, Windows Scaling 100%, 125%, 150%)  

---

## 1. Persona 5 Royal Visual Identity Guidelines

### Color Palette (Hex & Authentic Tokens)
- **Phantom Red:** `#E60012` (Primary brand accent, angular badges, focus borders)
- **True Charcoal / Void Black:** `#0D0D0D` / `#000000` (Background canvas, high-contrast framing)
- **Paper Off-White:** `#F5F5F5` / `#FFFFFF` (High-contrast typography, polygon text slabs)
- **P5 Yellow (Highlight):** `#FFE600` (Stats, active meter bars, level badges)
- **Velvet Cyan / Blue:** `#00D2FF` / `#0A192F` (Velvet Room compendium theme)
- **Untouchable Lime:** `#8BC34A` / `#2E3B23` (Airsoft shop inventory theme)
- **Cooperation Amber:** `#FFA000` / `#332200` (Confidant bond dossier theme)

### Geometry & Shape Language
- **Sharp Corners Only:** `border-radius: 0px` globally. Zero rounded corporate cards.
- **Skewed Angles:** Asymmetrical -10° to -14° parallelogram containers with counter-skewed text (`transform: skewX(-10deg)` container, `transform: skewX(10deg)` inner text).
- **Hard Offset Shadows:** Deep crisp black drop-shadows (`box-shadow: 4px 4px 0 #000, 8px 8px 0 rgba(0,0,0,0.5)`).
- **Ransom-Note Typography:** Multi-font cut-paper display banners combining sans-serif, bold display, and rotated glyph boxes.

---

## 2. Interaction & Motion Targets

| Interaction | Target Latency / Duration | Easing Curve |
|---|---|---|
| Focus feedback | <= 50 ms | `cubic-bezier(0.1, 0.9, 0.2, 1.0)` |
| Menu cursor shift | 80–120 ms | `cubic-bezier(0.2, 0.8, 0.2, 1.0)` |
| Minor panel transition | 120–180 ms | `cubic-bezier(0.2, 0.8, 0.2, 1.0)` |
| Screen entrance wipe | 220–320 ms | `cubic-bezier(0.0, 0.0, 0.2, 1.0)` |
| Screen exit wipe | 140–200 ms | `cubic-bezier(0.4, 0.0, 1.0, 1.0)` |
| Confirmation effect | 90–150 ms | `steps(2, start)` / quick flash |

### Accessibility & Reduced Motion
- Full keyboard navigation (`Tab`, `ArrowUp`, `ArrowDown`, `Enter`, `Escape`).
- `prefers-reduced-motion` media query and manual UI toggle that immediately disables all transitions and motion delays (`transition-duration: 0.01ms !important`).
