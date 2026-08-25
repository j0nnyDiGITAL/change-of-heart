# Change of Heart: Ground-Up Persona 5 Royal Native Menu Engine Plan

Goal: Rebuild the frontend layout from scratch into a full-bleed, sidebar-free, authentic in-game P5R menu system.

Tech Stack: Vanilla CSS3 (full-bleed viewport, clip-path, hard shadows), HTML5, JS bindings, Python unittest.

---

Task 1: CSS Viewport and Ribbon Navigation Architecture
- Remove .p5-sidebar rules and expand .p5-main-stage to 100vw x 100vh.
- Build .p5-bottom-nav-ticker (modeled after 12558.jpg and 63559.jpg) with animated active highlight shards.
- Build .p5-film-strip-save-bar (modeled after 95615.jpg) across top-left.

Task 2: HTML Template Reconstruction
- Delete sidebar aside from web-app/templates/index.html.
- Add bottom ribbon navigation bar with 7 stage tabs.
- Place film-strip save selector at top.
- Expand stages to full width.

Task 3: JS Event Bindings and Unit Test Suite
- Update stage switching handlers in app.js.
- Ensure all 176 tests pass.
- Run invariant checks.

Task 4: Visual Regression and Reference Capture
- Run capture_ui_state.py and verify against 12558.jpg and 27809.jpg.
