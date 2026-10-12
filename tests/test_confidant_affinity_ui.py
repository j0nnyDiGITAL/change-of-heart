"""Guardrails for the Confidant affinity-points UI meter."""

import os
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_JS = os.path.join(ROOT, "web-app", "static", "app.js")
APP_CSS = os.path.join(ROOT, "web-app", "static", "app.css")


class TestConfidantAffinityUi(unittest.TestCase):
    def test_spotlight_renders_affinity_meter_from_current_points(self):
        with open(APP_JS, encoding="utf-8") as f:
            src = f.read()

        self.assertIn("function getConfidantAffinityState", src)
        self.assertIn("renderConfidantAffinityMeter(arcana, info)", src)
        self.assertIn("affinity-points-input", src)
        self.assertIn("EVENT READY", src)
        self.assertIn("points / nextThreshold", src)

    def test_rank_clicks_stage_event_ready_points_and_refresh_meter(self):
        with open(APP_JS, encoding="utf-8") as f:
            src = f.read()

        self.assertIn("const stagedPoints = getConfidantEventReadyPoints(arcana, newRank);", src)
        self.assertIn("CURRENT_SAVE.confidants[arcana].points = stagedPoints;", src)
        self.assertNotIn("CURRENT_SAVE.confidants[arcana].points = 99;", src)

    def test_affinity_points_are_manually_editable(self):
        with open(APP_JS, encoding="utf-8") as f:
            src = f.read()

        self.assertIn("function setConfidantAffinityPoints", src)
        self.assertIn("affinityPointsInput_", src)
        self.assertIn("onchange=\"setConfidantAffinityPoints", src)
        self.assertIn("CURRENT_SAVE.confidants[arcana].points = nextPoints;", src)

    def test_affinity_meter_uses_existing_p5_style_classes(self):
        with open(APP_CSS, encoding="utf-8") as f:
            src = f.read()

        self.assertIn(".affinity-meter-card", src)
        self.assertIn(".affinity-fill", src)
        self.assertIn(".affinity-state-badge.ready", src)


if __name__ == "__main__":
    unittest.main()
