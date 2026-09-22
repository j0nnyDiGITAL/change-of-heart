"""Tests for the read-only Time Travel Planner (ADR 0003 Tier 0).

Covers: fixed-calendar invariants, wiki-verified weekday math, deadline table
sanity, the build_calendar_plan() payload, and the /api/calendar endpoint
contract (works with and without a loaded save).
"""

import json
import re
import threading
import unittest
import urllib.request
from unittest import mock

from core.calendar_data import (
    DEADLINES, MONTH_LENGTHS, MONTH_ORDER, abs_day, build_calendar_plan,
    weekday,
)

# ---------------------------------------------------------------------------
# Pure data / math tests
# ---------------------------------------------------------------------------


class TestCalendarMath(unittest.TestCase):
    def test_year_totals_365_days(self):
        self.assertEqual(sum(MONTH_LENGTHS[m] for m in MONTH_ORDER), 365)

    def test_month_order_is_april_through_march(self):
        self.assertEqual(MONTH_ORDER, (4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3))

    def test_abs_day_boundaries(self):
        self.assertEqual(abs_day(4, 1), 1)           # 4/1 = day 1
        self.assertEqual(abs_day(4, 30), 30)
        self.assertEqual(abs_day(5, 1), 31)          # first day rollover
        self.assertEqual(abs_day(3, 31), 365)        # last day of the year

    def test_weekday_anchors_from_wiki(self):
        # Wiki-verified anchors: 4/1 Fri, 6/21 Tue, 1/1 Sun.
        self.assertEqual(weekday(4, 1), "Fri")
        self.assertEqual(weekday(6, 21), "Tue")
        self.assertEqual(weekday(1, 1), "Sun")

    def test_every_story_day_is_a_valid_date(self):
        from core.calendar_data import STORY_DAYS
        for month, days in STORY_DAYS.items():
            self.assertIn(month, MONTH_LENGTHS)
            for d in days:
                self.assertTrue(1 <= d <= MONTH_LENGTHS[month],
                                f"{month}/{d} out of range")


class TestDeadlineTable(unittest.TestCase):
    def test_all_palace_deadlines_present(self):
        keys = {e["key"] for e in DEADLINES}
        for expected in ("kamoshida", "madarame", "kaneshiro", "futaba",
                         "okumura", "sae", "shido", "maruki_palace"):
            self.assertIn(expected, keys)

    def test_sae_deadline_conservative(self):
        # Must be the EARLIEST hard date (11/17 treasure route), never 11/20.
        sae = next(e for e in DEADLINES if e["key"] == "sae")
        self.assertEqual((sae["month"], sae["day"]), (11, 17))

    def test_gate_rows_carry_required_ranks(self):
        maruki = next(e for e in DEADLINES if e["key"] == "councillor_gate")
        self.assertEqual(maruki["required_rank"], 9)
        justice = next(e for e in DEADLINES if e["key"] == "justice_gate")
        self.assertEqual(justice["required_rank"], 8)


# ---------------------------------------------------------------------------
# Planner payload tests
# ---------------------------------------------------------------------------


class TestBuildCalendarPlan(unittest.TestCase):
    def test_no_save_year_view(self):
        plan = build_calendar_plan()
        self.assertIsNone(plan["today"])
        self.assertEqual(plan["total_days"], 365)
        self.assertEqual(len(plan["months"]), 12)
        # Every month has the right number of day cells; the fixed schedule
        # is static, so story/deadline classes appear even without a save.
        for month in plan["months"]:
            self.assertEqual(len(month["days"]), MONTH_LENGTHS[month["month"]])
            self.assertTrue(
                all(d["class"] in ("open", "story", "deadline") for d in month["days"]))
        april = next(m for m in plan["months"] if m["month"] == 4)
        classes = {d["day"]: d["class"] for d in april["days"]}
        self.assertEqual(classes[29], "deadline")   # Kamoshida
        self.assertEqual(classes[11], "story")      # first day of school
        self.assertEqual(classes[28], "open")
        # Deadlines listed without countdowns.
        self.assertTrue(plan["deadlines"])
        self.assertTrue(all(row["days_left"] is None for row in plan["deadlines"]))
        self.assertIn("Read-only", plan["disclaimer"])

    def test_today_parsing_and_classification(self):
        # 7/4 of the game year is a Monday (real-calendar 2016 math).
        plan = build_calendar_plan(today_label="7/4(Mon)")
        self.assertEqual(plan["today"]["month"], 7)
        self.assertEqual(plan["today"]["day"], 4)
        self.assertEqual(plan["today"]["weekday"], "Mon")
        july = next(m for m in plan["months"] if m["month"] == 7)
        cells = {d["day"]: d["class"] for d in july["days"]}
        self.assertEqual(cells[4], "open")      # today itself, no special mark
        self.assertEqual(cells[9], "deadline")  # Kaneshiro
        self.assertEqual(cells[13], "story")    # finals
        self.assertEqual(cells[15], "story")
        self.assertEqual(cells[10], "open")     # partial-slot day NOT asserted

    def test_deadlines_after_today_only_with_countdown(self):
        plan = build_calendar_plan(today_label="7/4(Mon)")
        labels = [row["key"] for row in plan["deadlines"]]
        self.assertNotIn("kamoshida", labels)   # in the past → hidden
        self.assertNotIn("madarame", labels)
        self.assertIn("kaneshiro", labels)
        kaneshiro = next(r for r in plan["deadlines"] if r["key"] == "kaneshiro")
        self.assertEqual(kaneshiro["days_left"], 5)  # 7/9 - 7/4

    def test_gate_status_met_vs_at_risk(self):
        ranks = {"Councillor": {"rank": 9}, "Justice": {"rank": 3},
                 "Faith": {"rank": 0}}
        plan = build_calendar_plan(today_label="11/10(Thu)", confidant_ranks=ranks)
        by_key = {r["key"]: r for r in plan["deadlines"]}
        self.assertEqual(by_key["councillor_gate"]["status"], "met")
        self.assertEqual(by_key["councillor_gate"]["current_rank"], 9)
        self.assertEqual(by_key["justice_gate"]["status"], "at_risk")
        self.assertEqual(by_key["justice_gate"]["current_rank"], 3)
        # Faith's gate is January — still upcoming on 11/10.
        self.assertEqual(by_key["faith_gate"]["status"], "at_risk")

    def test_gate_status_unknown_without_ranks(self):
        plan = build_calendar_plan(today_label="11/10(Thu)")
        by_key = {r["key"]: r for r in plan["deadlines"]}
        self.assertEqual(by_key["councillor_gate"]["status"], "unknown")

    def test_deadline_on_today_marks_today_status(self):
        plan = build_calendar_plan(today_label="7/9(Sat)")
        kaneshiro = next(r for r in plan["deadlines"] if r["key"] == "kaneshiro")
        self.assertEqual(kaneshiro["status"], "today")
        self.assertEqual(kaneshiro["days_left"], 0)


# ---------------------------------------------------------------------------
# Server endpoint tests (real handler, ephemeral port — test_ui_heartbeat style)
# ---------------------------------------------------------------------------


class TestCalendarEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import server as web_server
        cls.web_server = web_server
        cls.server = web_server.HTTPServer(("127.0.0.1", 0), web_server.P5RWebHandler)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def _get(self, path):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5) as r:
            return json.loads(r.read().decode("utf-8"))

    def test_calendar_endpoint_without_save(self):
        old_editor = self.web_server.CURRENT_EDITOR
        old_path = self.web_server.CURRENT_FILE_PATH
        self.web_server.CURRENT_EDITOR = None
        self.web_server.CURRENT_FILE_PATH = None
        try:
            data = self._get("/api/calendar")
            self.assertIsNone(data["today"])
            self.assertEqual(data["total_days"], 365)
            self.assertEqual(len(data["months"]), 12)
            self.assertTrue(data["deadlines"])
        finally:
            self.web_server.CURRENT_EDITOR = old_editor
            self.web_server.CURRENT_FILE_PATH = old_path

    def test_calendar_endpoint_with_save_uses_quick_info_date(self):
        editor = mock.MagicMock()
        editor.is_real_save.return_value = True
        editor.get_quick_info.return_value = {"day": "6/14(Tue)", "money": 1234}
        editor.get_confidant_ranks.return_value = {
            "Councillor": {"rank": 2}, "Justice": {"rank": 8}, "Faith": {"rank": 3},
        }
        old_editor = self.web_server.CURRENT_EDITOR
        old_path = self.web_server.CURRENT_FILE_PATH
        self.web_server.CURRENT_EDITOR = editor
        self.web_server.CURRENT_FILE_PATH = "unit-test.DAT"
        try:
            data = self._get("/api/calendar")
            self.assertEqual(data["today"]["month"], 6)
            self.assertEqual(data["today"]["day"], 14)
            self.assertEqual(data["today"]["weekday"], "Tue")
            by_key = {r["key"]: r for r in data["deadlines"]}
            self.assertEqual(by_key["councillor_gate"]["status"], "at_risk")
            self.assertEqual(by_key["justice_gate"]["status"], "met")
            # Faith's gate (1/12) is AFTER 6/14 in the Apr..Mar year.
            self.assertEqual(by_key["faith_gate"]["status"], "at_risk")
        finally:
            self.web_server.CURRENT_EDITOR = old_editor
            self.web_server.CURRENT_FILE_PATH = old_path

    def test_calendar_endpoint_unparseable_label_falls_back_to_year_view(self):
        editor = mock.MagicMock()
        editor.is_real_save.return_value = True
        editor.get_quick_info.return_value = {"day": None}
        editor.get_confidant_ranks.return_value = {}
        old_editor = self.web_server.CURRENT_EDITOR
        self.web_server.CURRENT_EDITOR = editor
        try:
            data = self._get("/api/calendar")
            self.assertIsNone(data["today"])
        finally:
            self.web_server.CURRENT_EDITOR = old_editor


if __name__ == "__main__":
    unittest.main()
