"""Read-only observer snapshot tests."""

from __future__ import annotations

import hashlib
import json
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from awakened_zero_rank import (
    compare_observer_snapshots,
    observer_snapshot,
    save_observer_snapshot,
    verify_observer_snapshot,
)
from awakened_zero_rank.content import STORY_ANCHORS
from awakened_zero_rank.persistence import load_simulation, save_simulation
from awakened_zero_rank.simulation import Simulation


def _redigest(snapshot: dict) -> None:
    content = {
        key: value for key, value in snapshot.items()
        if key not in {"identity", "path"}
    }
    payload = json.dumps(
        content, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    snapshot["identity"]["digest"] = hashlib.sha256(payload).hexdigest()


class ObserverSnapshotTests(unittest.TestCase):
    def test_empty_snapshot_is_json_ready_and_read_only(self) -> None:
        simulation = Simulation(seed=163)
        before = deepcopy(simulation.state)

        snapshot = observer_snapshot(simulation)

        self.assertEqual(simulation.state, before)
        self.assertEqual(snapshot["schema_version"], 4)
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

    def test_verifier_accepts_snapshot_and_external_path_provenance(self) -> None:
        snapshot = observer_snapshot(Simulation(seed=197))
        snapshot["path"] = "copies/ren.json"

        summary = verify_observer_snapshot(snapshot)

        self.assertEqual(summary, {
            "day": 1,
            "digest": snapshot["identity"]["digest"],
            "schema_version": 4,
            "seed": 197,
            "status": "valid",
        })

    def test_verifier_rejects_tampering_and_invalid_structure(self) -> None:
        snapshot = observer_snapshot(Simulation(seed=199))
        snapshot["protagonist"]["resources"]["money"] += 1
        with self.assertRaisesRegex(ValueError, "integrity check failed"):
            verify_observer_snapshot(snapshot)

        malformed = observer_snapshot(Simulation(seed=199))
        malformed["unexpected"] = True
        with self.assertRaisesRegex(ValueError, "top-level fields"):
            verify_observer_snapshot(malformed)

        unsupported = observer_snapshot(Simulation(seed=199))
        unsupported["schema_version"] = 2
        with self.assertRaisesRegex(ValueError, "Unsupported observer snapshot schema"):
            verify_observer_snapshot(unsupported)

    def test_economy_snapshot_tracks_live_state_without_mutation(self) -> None:
        simulation = Simulation(seed=271)
        simulation.run(32)
        before = deepcopy(simulation.state)

        economy = observer_snapshot(simulation)["economy"]

        self.assertEqual(simulation.state, before)
        self.assertEqual(economy, {
            "meal_cost": simulation.state.meal_cost,
            "rent_arrears": simulation.state.protagonist.rent_arrears,
            "rent_cost": simulation.state.protagonist.rent_cost,
            "rent_due_day": simulation.state.protagonist.rent_due_day,
            "rent_payments": simulation.state.rent_payments,
            "shop_visits": simulation.state.shop_visits,
            "wage_modifier": simulation.state.wage_modifier,
        })

    def test_verifier_rejects_redigested_invalid_economy(self) -> None:
        arrears = observer_snapshot(Simulation(seed=277))
        arrears["economy"]["rent_arrears"] = -1
        _redigest(arrears)
        with self.assertRaisesRegex(ValueError, "economy bounds"):
            verify_observer_snapshot(arrears)

        wages = observer_snapshot(Simulation(seed=277))
        wages["economy"]["wage_modifier"] = 101
        _redigest(wages)
        with self.assertRaisesRegex(ValueError, "wage modifier"):
            verify_observer_snapshot(wages)

    def test_verifier_rejects_redigested_invalid_resources(self) -> None:
        negative_money = observer_snapshot(Simulation(seed=251))
        negative_money["protagonist"]["resources"]["money"] = -1
        _redigest(negative_money)
        with self.assertRaisesRegex(ValueError, "resource bounds"):
            verify_observer_snapshot(negative_money)

        boolean_health = observer_snapshot(Simulation(seed=251))
        boolean_health["protagonist"]["resources"]["health"] = True
        _redigest(boolean_health)
        with self.assertRaisesRegex(ValueError, "resource health"):
            verify_observer_snapshot(boolean_health)

    def test_verifier_rejects_redigested_invalid_activity(self) -> None:
        oversized = observer_snapshot(Simulation(seed=257))
        event = {
            "action": "Rest",
            "day": 1,
            "outcome": "Recovered.",
            "reason": "Needed recovery.",
            "slot": "Morning",
        }
        oversized["activity"]["recent_events"] = [event] * 13
        _redigest(oversized)
        with self.assertRaisesRegex(ValueError, "recent events"):
            verify_observer_snapshot(oversized)

        out_of_order = observer_snapshot(Simulation(seed=257))
        out_of_order["clock"] = {"day": 2, "slot": "Morning"}
        out_of_order["activity"]["recent_events"] = [
            {**event, "slot": "Evening"},
            {**event, "slot": "Morning"},
        ]
        _redigest(out_of_order)
        with self.assertRaisesRegex(ValueError, "out of order"):
            verify_observer_snapshot(out_of_order)

    def test_verifier_rejects_events_at_or_after_observer_clock(self) -> None:
        event = {
            "action": "Rest",
            "day": 1,
            "outcome": "Recovered.",
            "reason": "Needed recovery.",
            "slot": "Morning",
        }
        current = observer_snapshot(Simulation(seed=367))
        current["activity"]["recent_events"] = [event]
        _redigest(current)
        with self.assertRaisesRegex(ValueError, "ahead of clock"):
            verify_observer_snapshot(current)

        future_simulation = Simulation(seed=367)
        future_simulation.run(1)
        future = observer_snapshot(future_simulation)
        future["activity"]["recent_events"][0]["slot"] = "Evening"
        _redigest(future)
        with self.assertRaisesRegex(ValueError, "ahead of clock"):
            verify_observer_snapshot(future)

        simulation = Simulation(seed=367)
        simulation.run(2)
        duplicate = observer_snapshot(simulation)
        duplicate["activity"]["recent_events"][1]["day"] = (
            duplicate["activity"]["recent_events"][0]["day"])
        duplicate["activity"]["recent_events"][1]["slot"] = (
            duplicate["activity"]["recent_events"][0]["slot"])
        _redigest(duplicate)
        with self.assertRaisesRegex(ValueError, "out of order"):
            verify_observer_snapshot(duplicate)

    def test_verifier_rejects_redigested_invalid_relationships_and_story(
            self) -> None:
        simulation = Simulation(seed=263)
        simulation.run(40)
        relationships = observer_snapshot(simulation)
        relationships["relationships"].reverse()
        _redigest(relationships)
        with self.assertRaisesRegex(ValueError, "not canonical"):
            verify_observer_snapshot(relationships)

        story = observer_snapshot(Simulation(seed=263))
        story["story"]["schema_version"] = 2
        _redigest(story)
        with self.assertRaisesRegex(ValueError, "story projection"):
            verify_observer_snapshot(story)

    def test_verifier_rejects_redigested_invalid_environment(self) -> None:
        alert = observer_snapshot(Simulation(seed=283))
        alert["environment"]["gate_alert_level"] = 4
        _redigest(alert)
        with self.assertRaisesRegex(ValueError, "gate alert level"):
            verify_observer_snapshot(alert)

        weather = observer_snapshot(Simulation(seed=283))
        weather["environment"]["temperature_c"] += 1
        _redigest(weather)
        with self.assertRaisesRegex(ValueError, "environment conditions"):
            verify_observer_snapshot(weather)

    def test_verifier_rejects_redigested_invalid_portals(self) -> None:
        unknown = observer_snapshot(Simulation(seed=293))
        unknown["portals"]["discovered"] = ["Unknown Gate"]
        _redigest(unknown)
        with self.assertRaisesRegex(ValueError, "discovered portals"):
            verify_observer_snapshot(unknown)

        simulation = Simulation(seed=293)
        simulation.run(60)
        bounds = observer_snapshot(simulation)
        self.assertTrue(bounds["portals"]["investigations"])
        bounds["portals"]["investigations"][0]["progress"] = 101
        _redigest(bounds)
        with self.assertRaisesRegex(ValueError, "investigation bounds"):
            verify_observer_snapshot(bounds)

        plan = observer_snapshot(Simulation(seed=293))
        plan["portals"]["active_plan"] = "Flooded Service Tunnel"
        _redigest(plan)
        with self.assertRaisesRegex(ValueError, "active portal plan"):
            verify_observer_snapshot(plan)
    def test_verifier_rejects_redigested_invalid_protagonist(self) -> None:
        identity = observer_snapshot(Simulation(seed=311))
        identity["protagonist"]["name"] = ""
        _redigest(identity)
        with self.assertRaisesRegex(ValueError, "protagonist identity"):
            verify_observer_snapshot(identity)

        rank = observer_snapshot(Simulation(seed=311))
        rank["protagonist"]["hunter_rank"] = "S"
        _redigest(rank)
        with self.assertRaisesRegex(ValueError, "protagonist status"):
            verify_observer_snapshot(rank)

        counters = observer_snapshot(Simulation(seed=311))
        counters["protagonist"]["progression"]["missions_completed"] = 1
        _redigest(counters)
        with self.assertRaisesRegex(ValueError, "mission counters"):
            verify_observer_snapshot(counters)

    def test_verifier_rejects_redigested_invalid_equipment(self) -> None:
        weapon = observer_snapshot(Simulation(seed=313))
        weapon["protagonist"]["equipment"]["weapon"] = "Padded Jacket"
        _redigest(weapon)
        with self.assertRaisesRegex(ValueError, "equipped weapon"):
            verify_observer_snapshot(weapon)

        quantity = observer_snapshot(Simulation(seed=313))
        quantity["protagonist"]["equipment"]["inventory"] = {"Field Knife": 0}
        _redigest(quantity)
        with self.assertRaisesRegex(ValueError, "inventory quantity"):
            verify_observer_snapshot(quantity)

        order = observer_snapshot(Simulation(seed=313))
        order["protagonist"]["equipment"]["inventory"] = {"Zeta": 1, "Alpha": 1}
        _redigest(order)
        with self.assertRaisesRegex(ValueError, "inventory is not canonical"):
            verify_observer_snapshot(order)

    def test_verifier_rejects_redigested_invalid_story_chronology(self) -> None:
        counts = observer_snapshot(Simulation(seed=331))
        counts["story"]["completed_count"] = 1
        _redigest(counts)
        with self.assertRaisesRegex(ValueError, "story counts"):
            verify_observer_snapshot(counts)

        next_anchor = observer_snapshot(Simulation(seed=331))
        next_anchor["story"]["next"]["days_remaining"] -= 1
        _redigest(next_anchor)
        with self.assertRaisesRegex(ValueError, "next story anchor"):
            verify_observer_snapshot(next_anchor)

        simulation = Simulation(seed=331)
        simulation.state.clock.day = STORY_ANCHORS[0].day
        simulation.state.calendar_events_seen.append(STORY_ANCHORS[0].key)
        simulation.state.story_outcomes[STORY_ANCHORS[0].key] = "resilient"
        authored = observer_snapshot(simulation)
        authored["story"]["completed"][0]["outcome"] = "Forged outcome"
        _redigest(authored)
        with self.assertRaisesRegex(ValueError, "story chronology"):
            verify_observer_snapshot(authored)

    def test_verifier_rejects_redigested_invalid_story_ending(self) -> None:
        simulation = Simulation(seed=337)
        simulation.state.clock.day = STORY_ANCHORS[-1].day
        simulation.state.calendar_events_seen.extend(
            anchor.key for anchor in STORY_ANCHORS)
        simulation.state.story_outcomes.update(
            (anchor.key, "prepared") for anchor in STORY_ANCHORS)
        ending = observer_snapshot(simulation)
        ending["story"]["ending"]["prepared_count"] -= 1
        _redigest(ending)
        with self.assertRaisesRegex(ValueError, "story ending"):
            verify_observer_snapshot(ending)

        status = observer_snapshot(Simulation(seed=337))
        status["story"]["ending_reached"] = 1
        _redigest(status)
        with self.assertRaisesRegex(ValueError, "ending status"):
            verify_observer_snapshot(status)

    def test_verifier_rejects_redigested_unknown_social_catalogue_data(
            self) -> None:
        simulation = Simulation(seed=349)
        simulation.run(40)
        relationship = observer_snapshot(simulation)
        self.assertTrue(relationship["relationships"])
        relationship["relationships"][0]["role"] = ""
        _redigest(relationship)
        with self.assertRaisesRegex(ValueError, "relationship identity"):
            verify_observer_snapshot(relationship)

        historical_role = observer_snapshot(simulation)
        historical_role["relationships"][0]["role"] = "former guild clerk"
        _redigest(historical_role)
        verify_observer_snapshot(historical_role)

        malformed_name = observer_snapshot(simulation)
        malformed_name["relationships"][0]["name"] = []
        _redigest(malformed_name)
        with self.assertRaisesRegex(ValueError, "relationship identity"):
            verify_observer_snapshot(malformed_name)

        portal_simulation = Simulation(seed=353)
        portal_simulation.run(60)
        collaborator = observer_snapshot(portal_simulation)
        self.assertTrue(collaborator["portals"]["investigations"])
        collaborator["portals"]["investigations"][0]["cooperating_npc"] = (
            "Unknown Observer")
        _redigest(collaborator)
        with self.assertRaisesRegex(ValueError, "portal collaborator"):
            verify_observer_snapshot(collaborator)

    def test_snapshot_comparison_ignores_path_provenance(self) -> None:
        left = observer_snapshot(Simulation(seed=379))
        right = deepcopy(left)
        left["path"] = "exports/left.json"
        right["path"] = "archives/right.json"

        left_before, right_before = deepcopy(left), deepcopy(right)
        comparison = compare_observer_snapshots(left, right)

        self.assertEqual(left, left_before)
        self.assertEqual(right, right_before)
        self.assertTrue(comparison["identical"])
        self.assertTrue(comparison["same_seed"])
        self.assertEqual(comparison["clock_delta_slots"], 0)
        self.assertEqual(comparison["clock_relation"], "same")
        self.assertEqual(comparison["update_mode"], "unchanged")
        self.assertEqual(comparison["recent_activity_relation"], "unchanged")
        self.assertEqual(comparison["changed_sections"], [])
        self.assertEqual(comparison["comparison_schema_version"], 6)
        self.assertEqual(comparison["observer_schema_version"], 4)
        self.assertEqual(comparison["left"]["digest"], comparison["right"]["digest"])

    def test_snapshot_comparison_reports_sorted_world_sections(self) -> None:
        simulation = Simulation(seed=383)
        left = observer_snapshot(simulation)
        simulation.step()
        right = observer_snapshot(simulation)

        comparison = compare_observer_snapshots(left, right)

        self.assertFalse(comparison["identical"])
        self.assertTrue(comparison["same_seed"])
        self.assertEqual(comparison["clock_delta_slots"], 1)
        self.assertEqual(comparison["clock_relation"], "forward")
        self.assertEqual(comparison["update_mode"], "animate")
        self.assertEqual(comparison["recent_activity_relation"], "append")
        self.assertEqual(
            comparison["changed_sections"],
            sorted(comparison["changed_sections"]),
        )
        self.assertIn("activity", comparison["changed_sections"])
        self.assertIn("clock", comparison["changed_sections"])
        self.assertNotIn("identity", comparison["changed_sections"])
        self.assertEqual(comparison["left"]["clock"], left["clock"])
        self.assertEqual(comparison["right"]["clock"], right["clock"])

        tampered = deepcopy(right)
        tampered["clock"]["day"] += 1
        with self.assertRaisesRegex(ValueError, "integrity check failed"):
            compare_observer_snapshots(left, tampered)

    def test_snapshot_comparison_reports_direction_and_seed_change(self) -> None:
        simulation = Simulation(seed=421)
        earlier = observer_snapshot(simulation)
        simulation.step()
        later = observer_snapshot(simulation)

        backward = compare_observer_snapshots(later, earlier)
        different_seed = compare_observer_snapshots(
            earlier, observer_snapshot(Simulation(seed=431)))

        self.assertEqual(backward["clock_relation"], "backward")
        self.assertEqual(backward["clock_delta_slots"], -1)
        self.assertEqual(backward["update_mode"], "replace")
        self.assertEqual(backward["recent_activity_relation"], "replace")
        self.assertTrue(backward["same_seed"])
        self.assertEqual(different_seed["clock_relation"], "same")
        self.assertEqual(different_seed["clock_delta_slots"], 0)
        self.assertFalse(different_seed["same_seed"])
        self.assertEqual(different_seed["update_mode"], "replace")
        self.assertIn("seed", different_seed["changed_sections"])

    def test_snapshot_comparison_refreshes_same_clock_changes(self) -> None:
        left = observer_snapshot(Simulation(seed=443))
        right = deepcopy(left)
        right["protagonist"]["current_goal"] = "Review the latest Gate report"
        _redigest(right)

        comparison = compare_observer_snapshots(left, right)

        self.assertEqual(comparison["clock_relation"], "same")
        self.assertEqual(comparison["clock_delta_slots"], 0)
        self.assertTrue(comparison["same_seed"])
        self.assertEqual(comparison["update_mode"], "refresh")
        self.assertEqual(comparison["changed_sections"], ["protagonist"])

    def test_snapshot_comparison_refreshes_clock_without_activity_append(
            self) -> None:
        left = observer_snapshot(Simulation(seed=447))
        right = deepcopy(left)
        right["clock"]["slot"] = "Afternoon"
        _redigest(right)

        comparison = compare_observer_snapshots(left, right)

        self.assertEqual(comparison["clock_delta_slots"], 1)
        self.assertEqual(comparison["recent_activity_relation"], "unchanged")
        self.assertEqual(comparison["update_mode"], "refresh")

    def test_snapshot_comparison_reports_multi_day_clock_distance(self) -> None:
        simulation = Simulation(seed=449)
        left = observer_snapshot(simulation)
        simulation.run(9)
        right = observer_snapshot(simulation)

        forward = compare_observer_snapshots(left, right)
        backward = compare_observer_snapshots(right, left)

        self.assertEqual(forward["clock_relation"], "forward")
        self.assertEqual(forward["clock_delta_slots"], 9)
        self.assertEqual(forward["update_mode"], "refresh")
        self.assertEqual(forward["recent_activity_relation"], "replace")
        self.assertEqual(backward["clock_relation"], "backward")
        self.assertEqual(backward["clock_delta_slots"], -9)

    def test_snapshot_publication_is_canonical_and_non_overwriting(self) -> None:
        snapshot = observer_snapshot(Simulation(seed=229))
        snapshot["path"] = "saves/ren.json"
        with TemporaryDirectory() as directory:
            destination = Path(directory) / "published" / "snapshot.json"

            result = save_observer_snapshot(snapshot, destination)

            self.assertEqual(result, destination)
            self.assertEqual(
                json.loads(destination.read_text(encoding="utf-8")),
                snapshot,
            )
            self.assertTrue(destination.read_bytes().endswith(b"\n"))
            verify_observer_snapshot(
                json.loads(destination.read_text(encoding="utf-8")))
            original = destination.read_bytes()
            with self.assertRaisesRegex(ValueError, "already exists"):
                save_observer_snapshot(snapshot, destination)
            self.assertEqual(destination.read_bytes(), original)

    def test_snapshot_publication_rejects_invalid_input_without_output(self) -> None:
        snapshot = observer_snapshot(Simulation(seed=233))
        snapshot["clock"]["day"] += 1
        with TemporaryDirectory() as directory:
            destination = Path(directory) / "snapshot.json"

            with self.assertRaisesRegex(ValueError, "integrity check failed"):
                save_observer_snapshot(snapshot, destination)

            self.assertFalse(destination.exists())

    def test_populated_snapshot_is_stable_across_save_and_load(self) -> None:
        simulation = Simulation(seed=167)
        simulation.run(40)
        simulation.state.protagonist.inventory.update({"Zeta": 1, "Alpha": 2})

        first = observer_snapshot(simulation)
        second = observer_snapshot(simulation)
        self.assertEqual(first, second)
        verify_observer_snapshot(first)
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
