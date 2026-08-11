"""Read-only observer snapshot tests."""

from __future__ import annotations

import hashlib
import json
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from awakened_zero_rank import observer_snapshot
from awakened_zero_rank.persistence import load_simulation, save_simulation
from awakened_zero_rank.simulation import Simulation


class ObserverSnapshotTests(unittest.TestCase):
    def test_empty_snapshot_is_json_ready_and_read_only(self) -> None:
        simulation = Simulation(seed=163)
        before = deepcopy(simulation.state)

        snapshot = observer_snapshot(simulation)

        self.assertEqual(simulation.state, before)
        self.assertEqual(snapshot["schema_version"], 3)
        self.assertEqual(snapshot["seed"], 163)
        self.assertEqual(snapshot["clock"], {"day": 1, "slot": "Morning"})
        self.assertEqual(snapshot["protagonist"]["name"], "Ren Takahashi")
        self.assertEqual(snapshot["relationships"], [])
        self.assertEqual(snapshot["activity"], {
            "key_memories": [],
            "recent_events": [],
        })
        self.assertEqual(snapshot["story"]["schema_version"], 3)
        json.dumps(snapshot, sort_keys=True)

    def test_activity_is_bounded_and_preserves_recent_order(self) -> None:
        simulation = Simulation(seed=179)
        simulation.run(24)

        activity = observer_snapshot(simulation)["activity"]

        self.assertEqual(len(activity["recent_events"]), 12)
        self.assertEqual(
            [event["action"] for event in activity["recent_events"]],
            [event.action for event in simulation.state.events[-12:]],
        )
        self.assertEqual(
            [event["day"] for event in activity["recent_events"]],
            [event.day for event in simulation.state.events[-12:]],
        )
        self.assertLessEqual(len(activity["key_memories"]), 5)
        self.assertEqual(
            [memory["summary"] for memory in activity["key_memories"]],
            [memory.summary for memory in simulation.state.protagonist.memories[:5]],
        )
        self.assertTrue(all(
            event["reason"] and event["outcome"]
            for event in activity["recent_events"]
        ))

    def test_identity_is_canonical_and_changes_after_a_transition(self) -> None:
        simulation = Simulation(seed=191)
        before = observer_snapshot(simulation)
        unsigned = {
            key: value for key, value in before.items()
            if key != "identity"
        }
        canonical = json.dumps(
            unsigned, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        self.assertEqual(before["identity"], {
            "algorithm": "sha256",
            "digest": hashlib.sha256(canonical).hexdigest(),
        })
        self.assertEqual(len(before["identity"]["digest"]), 64)

        simulation.step()
        after = observer_snapshot(simulation)

        self.assertNotEqual(after["identity"]["digest"], before["identity"]["digest"])

    def test_populated_snapshot_is_stable_across_save_and_load(self) -> None:
        simulation = Simulation(seed=167)
        simulation.run(40)
        simulation.state.protagonist.inventory.update({"Zeta": 1, "Alpha": 2})

        first = observer_snapshot(simulation)
        second = observer_snapshot(simulation)
        self.assertEqual(first, second)
        self.assertEqual(
            list(first["protagonist"]["equipment"]["inventory"]),
            sorted(simulation.state.protagonist.inventory),
        )
        self.assertEqual(
            [item["name"] for item in first["relationships"]],
            sorted(simulation.state.protagonist.relationships),
        )

        with TemporaryDirectory() as directory:
            path = Path(directory) / "observer-save.json"
            save_simulation(simulation, path)
            restored = load_simulation(path)

        self.assertEqual(observer_snapshot(restored), first)


if __name__ == "__main__":
    unittest.main()
