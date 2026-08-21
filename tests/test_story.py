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
        self.assertEqual(progress["schema_version"], 4)
        self.assertEqual(progress["completed"], [])
        self.assertEqual(progress["completed_count"], 0)
        self.assertEqual(progress["total_anchors"], 6)
        self.assertFalse(progress["ending_reached"])
        self.assertIsNone(progress["ending"])
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
        self.assertTrue(all(entry["scene"] for entry in progress["completed"]))
        self.assertTrue(all(
            entry["portal_consequence"] for entry in progress["completed"]))
        self.assertIsNone(progress["completed"][0]["international_link"])
        self.assertIn(
            "Busan", progress["completed"][2]["international_link"])
        self.assertEqual(progress["completed_count"], 6)
        self.assertTrue(progress["ending_reached"])
        self.assertEqual(progress["ending"]["id"], "zero-rank-horizon")
        self.assertEqual(progress["ending"]["prepared_count"], 6)
        self.assertEqual(progress["ending"]["title"], "The Zero-Rank Horizon")
        self.assertIsNone(progress["next"])

    def test_mixed_arc_receives_quiet_guardian_ending(self) -> None:
        state = Simulation(seed=139).state
        state.clock.day = 1095
        tiers = (
            "isolated", "resilient", "prepared",
            "resilient", "prepared", "resilient")
        state.calendar_events_seen.extend(anchor.key for anchor in STORY_ANCHORS)
        state.story_outcomes.update(
            (anchor.key, tier) for anchor, tier in zip(STORY_ANCHORS, tiers))

        ending = story_progress(state)["ending"]

        self.assertEqual(ending["id"], "quiet-guardian")
        self.assertEqual(ending["title"], "Tokyo's Quiet Guardian")
        self.assertEqual(ending["prepared_count"], 2)
        self.assertEqual(ending["resilient_count"], 3)
        self.assertEqual(ending["isolated_count"], 1)

    def test_legacy_arc_does_not_invent_a_named_ending(self) -> None:
        state = Simulation(seed=149).state
        state.clock.day = 1095
        state.calendar_events_seen.extend(anchor.key for anchor in STORY_ANCHORS)
        state.story_outcomes.update(
            (anchor.key, "legacy-unavailable") for anchor in STORY_ANCHORS)

        ending = story_progress(state)["ending"]

        self.assertEqual(ending["id"], "legacy-unavailable")
        self.assertEqual(ending["title"], "Legacy Ending Unavailable")
        self.assertEqual(ending["tier"], "legacy-unavailable")

    def test_prepared_finish_with_mixed_history_opens_corridor(self) -> None:
        state = Simulation(seed=151).state
        state.clock.day = 1095
        tiers = (
            "isolated", "resilient", "isolated",
            "resilient", "resilient", "prepared")
        state.story_outcomes.update(
            (anchor.key, tier) for anchor, tier in zip(STORY_ANCHORS, tiers))

        ending = story_progress(state)["ending"]

        self.assertEqual(ending["id"], "open-corridor")
        self.assertEqual(ending["title"], "The Open Corridor")
        self.assertEqual(ending["prepared_count"], 1)

    def test_isolated_history_with_resilient_finish_keeps_scarred_watch(self) -> None:
        state = Simulation(seed=157).state
        state.clock.day = 1095
        tiers = (
            "isolated", "isolated", "prepared",
            "isolated", "resilient", "resilient")
        state.story_outcomes.update(
            (anchor.key, tier) for anchor, tier in zip(STORY_ANCHORS, tiers))

        ending = story_progress(state)["ending"]

        self.assertEqual(ending["id"], "scarred-watch")
        self.assertEqual(ending["title"], "The Scarred Watch")
        self.assertEqual(ending["isolated_count"], 3)

if __name__ == "__main__":
    unittest.main()
