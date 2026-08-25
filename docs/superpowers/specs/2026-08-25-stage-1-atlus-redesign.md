# Stage 1 (Leader Profile & Daily Life) 1:1 Atlus Redesign Spec

**Reference Ground Truth:** design/reference/Persona-5-Royal03112021-110112-27809.jpg (Joker Status & Leader Profile)

---

## 1. Composition Breakdown (from 27809.jpg)
In 27809.jpg:
1. **Left Hero Shard:**
   - Giant white parallelogram shard (clip-path: polygon(0 0, 100% 0, 85% 100%, 0 100%)) holding the leader name in massive bold black lettering with L1/R1 nav badges.
   - Secondary black angled shard (ackground: #000; border: 3px solid #FFF; transform: skew(-10deg)) displaying Level and Next Level telemetry.
   - Neon Cyan (#00E5FF) HP bar shard and Magenta (#FF2A6D) SP bar shard.
2. **Right Leader Art & Calling Card Stamp:**
   - Full Joker bust cutout in stark monochrome + red contrast with the official [LEADER] stamp in weathered stencil font.
   - Massive diagonal **TOTAL EXP / TOTAL YEN** numerical display cutting across the bottom-right in bold red condensed typography.
3. **Bottom Social Stat Radar Matrix:**
   - 5 Social Stats (Knowledge, Guts, Proficiency, Kindness, Charm) arranged horizontally in angled black-and-white comic shards with active yellow stars.

---

## 2. Changes to Execute
- Modify web-app/static/app.css to add authentic .p5-status-stage-grid, .p5-hero-shard, .p5-leader-art-showcase, .p5-stat-shard, .p5-exp-ticker.
- Modify web-app/templates/index.html Stage 1 to use this exact shard layout instead of generic .grid-2 .p5-card boxes.
