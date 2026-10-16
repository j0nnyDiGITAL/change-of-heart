# P5R ASSET & REFERENCE MANIFEST — OPERATION CHANGE OF HEART

**Project:** Change of Heart — Persona 5 Royal Save Editor  
**Repository:** https://github.com/j0nnyDiGITAL/change-of-heart  
**Date:** October 16, 2026  
**Distribution Policy:** Strict Dual-Mode Policy — Public builds MUST function completely and attractively with pure SVG / CSS / original art fallback without requiring proprietary extracted game files. Local extracted game assets are used for owner's private high-fidelity experience.

---

## 1. Verified Reference Screenshots

The following reference captures are stored locally in `design/reference/` and serve as visual ground truth for proportions, geometry, and color:

| Reference Name | File Path | Resolution | Screen / Visual Role | Visual Features to Emulate |
|---|---|---|---|---|
| **Status Joker (Hero)** | `design/reference/Persona-5-Royal03112021-110211-15585.jpg` (`76684.jpg`) | 1920x1080 | Status Main Screen | Full-height Joker cutout on left, angled white polygon name card, stat polygons, red background slash |
| **Status Telemetry** | `design/reference/Persona-5-Royal03112021-110122-41845.jpg` (`27809.jpg`) | 1920x1080 | Combat Shards / Stats | Neon combat stat shards, HP/SP meters, EXP bar, level placard |
| **Menu Ribbon** | `design/reference/Persona-5-Royal03112021-110214-63538.jpg` (`63559.jpg`) | 1920x1080 | Bottom Ribbon Ticker | Bottom navigation tape with skewed black/white text labels, red accent pins |
| **Velvet Room** | `design/reference/Persona-5-Royal03112021-110122-28140.jpg` (`228140.jpg`) | 1920x1080 | Velvet Room Register | Deep blue/cyan architectural lattice, gothic guillotine framing, high-contrast white typography |
| **Airsoft Shop** | `design/reference/Persona-5-Royal03112021-110212-30894.jpg` (`89783.jpg`) | 1920x1080 | Untouchable Inventory | Lime-green and gunmetal theme, 10-pocket tabs, tactical item dossier |
| **Confidant Dossier** | `design/reference/Persona-5-Royal03112021-110213-50281.jpg` | 1920x1080 | Cooperation / Dossier | Amber-gold arcana card layout, character silhouette, rank star meter, bond notes |
| **Contact Sheets** | `design/reference/contact_sheets/sheet_01.png` .. `sheet_08.png` | Various | UI Design System | Official P5R typography, speech bubbles, alert banners, button prompts |

---

## 2. Local Asset Inventory

- **Persona Artwork:** 232 character PNGs located in `web-app/static/assets/personas/` (`1.png` through `461.png`).
- **Confidant Portraits:** 24 arcana character PNGs located in `web-app/static/assets/confidants/` and `web-app/static/assets/confidants_full/`.
- **Party Members:** Official party portraits in `web-app/static/assets/party/` (Joker, Ryuji, Morgana, Ann, Yusuke, Makoto, Futaba, Haru, Akechi, Kasumi).
- **Brand & Theme Assets:** `change_of_heart_logo.jpg`, SVG icons in `web-app/static/assets/icons/`.

---

## 3. Fallback Resource Strategy

1. **Missing Image Handling:** All `<img>` tags in the redesign include `onerror="this.src='/static/assets/placeholder_persona.svg'"` or pure CSS geometric placeholders.
2. **Offline Self-Containment:** Zero CDN dependencies. All fonts (`p5r-font`, `rubik`, `source-sans`), styles, scripts, and SVG icons are embedded locally in `web-app/static/`.
3. **Distribution Boundary:** The PyInstaller `.spec` and packaging scripts package only authorized assets; extracted game binaries (`BASE.CPK`) remain strictly outside the repository.
