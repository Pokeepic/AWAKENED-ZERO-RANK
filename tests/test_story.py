"""Read-only story progress tests."""

from __future__ import annotations

from copy import deepcopy
import unittest

from awakened_zero_rank.content import STORY_ANCHORS
from awakened_zero_rank.simulation import Simulation
from awakened_zero_rank.story import story_progress


class StoryProgressTests(unittest.TestCase):
    def test_empty_progress_is_read_only_and_reports_first_anchor(self) -> None:
        state = Simulation(seed=107).state
        before = deepcopy(state)

        progress = story_progress(state)

        self.assertEqual(state, before)
        self.assertEqual(progress["schema_version"], 1)
        self.assertEqual(progress["completed"], [])
        self.assertEqual(progress["completed_count"], 0)
        self.assertEqual(progress["total_anchors"], 6)
        self.assertFalse(progress["ending_reached"])
        self.assertEqual(progress["next"], {
            "day": 183,
            "days_remaining": 182,
            "key": "arc_adachi_warning",
            "title": "The Adachi Warning",
        })

    def test_progress_orders_outcomes_and_detects_the_ending(self) -> None:
        state = Simulation(seed=109).state
        state.clock.day = 1095
        state.calendar_events_seen.extend(anchor.key for anchor in STORY_ANCHORS)
        state.story_outcomes.update(
            (anchor.key, "prepared") for anchor in reversed(STORY_ANCHORS))

        progress = story_progress(state)

        self.assertEqual(
            [entry["key"] for entry in progress["completed"]],
            [anchor.key for anchor in STORY_ANCHORS])
        self.assertTrue(all(
            entry["tier"] == "prepared" and entry["outcome"]
            for entry in progress["completed"]))
        self.assertEqual(progress["completed_count"], 6)
        self.assertTrue(progress["ending_reached"])
        self.assertIsNone(progress["next"])


if __name__ == "__main__":
    unittest.main()