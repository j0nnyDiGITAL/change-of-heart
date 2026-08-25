# Stage 1 (Leader Profile & Daily Life) 1:1 Atlus Implementation Plan

**Goal:** Reconstruct Stage 1 from a generic 2-card web grid into a 1:1 replica of the official P5R Status screen (27809.jpg).

**Tech Stack:** Vanilla CSS3 (clip-path, hard shadows, skewed shards), HTML5, JS bindings.

---

### Task 1: CSS Layout & Shard System
- Define .p5-status-stage-grid (left shard 1.2fr, right art 1fr).
- Define .p5-hero-name-shard (massive white angled polygon header).
- Define .p5-leader-showcase (Joker art + weathered [LEADER] stamp + red bold telemetry).
- Define .p5-social-stat-shards (horizontal angled stat modules).

### Task 2: Stage 1 Markup Overhaul
- Rewrite stage-daily_life to implement the shard composition.
- Connect existing IDs: #inputFname, #inputLname, #inputGroupName, #inputMoney, #socialStatsList.

### Task 3: Visual Verification
- Run test suite & check-invariants.py.
- Run python tools/capture_ui_state.py to produce visual capture of Stage 1.
