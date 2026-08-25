# Stage 1: Full-Bleed Status & Leader Hub (Authentic P5R Mouse Engine)

**Reference Ground Truth:** design/reference/Persona-5-Royal03112021-110112-27809.jpg (Status), design/reference/Persona-5-Royal03112021-110112-76684.jpg (Party/Stats), design/reference/Persona-5-Royal03112021-110112-26388.jpg (Calendar)

---

## 1. Design & UX Architecture

### A. Full-Bleed Game Canvas (No Web Forms / No Sidebar Incursion)
- Top strip features the authentic high-contrast calendar & clock block (20XX 2/1 WED, Leblanc, ¥ 9,999,999 with clock icon) from 26388.jpg.
- Stage 1 expands to full viewport width with the dynamic Shibuya crimson halftone backdrop.

### B. Left Asymmetric Shard Deck
1. **Interactive White Hero Shard (.p5-hero-name-shard):**
   - Renders **REN AMAMIYA** in massive bold condensed typography with black LV 99 badge.
   - **Click Action:** Clicking the shard triggers an in-place modal prompt to edit First Name, Last Name, and Phantom Thief Group Name.
2. **Combat Stats & Telemetry Block (.p5-hero-stats-shard):**
   - High-contrast black shard with neon cyan (#00E5FF) HP bar and magenta (#FF2A6D) SP bar.
   - Attack, Defense, and Down Shots stats with instant 1-click Max/Full Heal button.
3. **Speech Bubble View Switchers (.p5-speech-bubble-btn):**
   - Styled after the comic dialogue bubbles in 27809.jpg ([Social Stats], [Party Matrix], [Persona]).
   - Clicking [Social Stats] smoothly transitions the center view to the interactive 5-Point Human Parameter Star Radar.

### C. Right High-Impact Silhouette & Stencil Showcase
1. **Joker Silhouette:** Full-bleed cutout with crimson backlight and halftone manga dots.
2. **Weathered [LEADER] Stamp:** Angled red-border stencil badge.
3. **Massive TOTAL ASSETS / EXP Display:**
   - Huge bold red condensed numbers (¥ 9,999,999).
   - **Click Action:** Clicking opens a quick Yen adjust / Max Yen prompt with instant real-time sync.

---

## 2. Global Constraints
- Grounded directly in design/reference/ screenshots.
- Zero generic browser input boxes visible on the main game canvas — all editing is mouse-click driven via styled P5R prompt dialogs.
- 176/176 unit tests must pass before and after changes.
- Invariants via python scripts/check-invariants.py must remain 100% clean.
