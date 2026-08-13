"""Read-only observer snapshot tests."""

from __future__ import annotations

import hashlib
import json
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from awakened_zero_rank import (
    compare_observer_site_data,
    compare_observer_snapshots,
    load_observer_site_comparison_artifact,
    observer_presentation_contract,
    observer_snapshot,
    publish_observer_site_data,
    save_observer_presentation_contract,
    save_observer_site_comparison,
    save_observer_snapshot,
    verify_observer_presentation_contract,
    verify_observer_site_data,
    verify_observer_snapshot,
)
from awakened_zero_rank.models import TimeSlot
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

        for field, value in (
                ("rent_due_day", 7), ("rent_cost", 7_999),
                ("rent_arrears", 8_001), ("rent_payments", 2)):
            with self.subTest(field=field):
                ledger = observer_snapshot(Simulation(seed=57))
                ledger["economy"][field] = value
                _redigest(ledger)
                with self.assertRaisesRegex(ValueError, "rent ledger"):
                    verify_observer_snapshot(ledger)

        contradictory = observer_snapshot(Simulation(seed=57))
        contradictory["economy"]["rent_payments"] = 1
        contradictory["economy"]["rent_arrears"] = 1
        _redigest(contradictory)
        with self.assertRaisesRegex(ValueError, "rent ledger"):
            verify_observer_snapshot(contradictory)

        for day, slot in ((7, TimeSlot.LATE_NIGHT), (8, TimeSlot.MORNING)):
            with self.subTest(day=day, slot=slot):
                simulation = Simulation(seed=59)
                simulation.state.clock.day = day
                simulation.state.clock.slot = slot
                simulation.state.rent_payments = 1
                premature = observer_snapshot(simulation)
                _redigest(premature)
                with self.assertRaisesRegex(ValueError, "predates"):
                    verify_observer_snapshot(premature)

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

        undiscovered = observer_snapshot(simulation)
        undiscovered["portals"]["discovered"].remove(
            undiscovered["portals"]["investigations"][0]["portal_name"])
        _redigest(undiscovered)
        with self.assertRaisesRegex(ValueError, "undiscovered"):
            verify_observer_snapshot(undiscovered)

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

        lifecycle = observer_snapshot(Simulation(seed=311))
        lifecycle["protagonist"]["ability"] = "Threat Sense"
        _redigest(lifecycle)
        with self.assertRaisesRegex(ValueError, "protagonist status"):
            verify_observer_snapshot(lifecycle)

        points = observer_snapshot(Simulation(seed=311))
        points["protagonist"]["progression"]["rank_points"] = 30
        _redigest(points)
        with self.assertRaisesRegex(ValueError, "rank points"):
            verify_observer_snapshot(points)

        mission_simulation = Simulation(seed=311)
        mission_simulation.run(10)
        mission_points = observer_snapshot(mission_simulation)
        mission_points["protagonist"]["hunter_rank"] = "F"
        mission_points["protagonist"]["ability"] = "Threat Sense"
        mission_points["protagonist"]["progression"]["rank_points"] = 10
        _redigest(mission_points)
        with self.assertRaisesRegex(ValueError, "mission rank points"):
            verify_observer_snapshot(mission_points)

        impossible_award = observer_snapshot(mission_simulation)
        impossible_award["protagonist"]["hunter_rank"] = "F"
        impossible_award["protagonist"]["ability"] = "Threat Sense"
        impossible_award["protagonist"]["progression"]["missions_attempted"] = 1
        impossible_award["protagonist"]["progression"]["missions_completed"] = 1
        impossible_award["protagonist"]["progression"]["rank_points"] = 11
        _redigest(impossible_award)
        with self.assertRaisesRegex(ValueError, "mission rank points"):
            verify_observer_snapshot(impossible_award)

        counters = observer_snapshot(Simulation(seed=311))
        counters["protagonist"]["progression"]["missions_completed"] = 1
        _redigest(counters)
        with self.assertRaisesRegex(ValueError, "mission counters"):
            verify_observer_snapshot(counters)

    def test_verifier_requires_authored_awakening_chronology(self) -> None:
        cases = (
            (1, TimeSlot.MORNING, "F", "Threat Sense"),
            (3, TimeSlot.AFTERNOON, "F", "Threat Sense"),
            (3, TimeSlot.EVENING, "Unranked", "None"),
            (4, TimeSlot.MORNING, "Unranked", "None"),
        )
        for day, slot, rank, ability in cases:
            with self.subTest(day=day, slot=slot, rank=rank):
                simulation = Simulation(seed=315)
                simulation.state.clock.day = day
                simulation.state.clock.slot = slot
                snapshot = observer_snapshot(simulation)
                snapshot["protagonist"]["hunter_rank"] = rank
                snapshot["protagonist"]["ability"] = ability
                _redigest(snapshot)
                with self.assertRaisesRegex(ValueError, "Awakening chronology"):
                    verify_observer_snapshot(snapshot)

    def test_verifier_requires_lifecycle_current_goal(self) -> None:
        for steps, expected in (
                (0, "Earn enough yen to pay rent"),
                (10, "Register with the Tokyo Hunter Guild"),
                (13, "Survive gate work and reach Rank E")):
            with self.subTest(steps=steps):
                simulation = Simulation(seed=317)
                simulation.run(steps)
                snapshot = observer_snapshot(simulation)
                self.assertEqual(snapshot["protagonist"]["current_goal"], expected)
                snapshot["protagonist"]["current_goal"] = "Invented objective"
                _redigest(snapshot)
                with self.assertRaisesRegex(ValueError, "current goal"):
                    verify_observer_snapshot(snapshot)

    def test_verifier_requires_guild_registration_evidence(self) -> None:
        for steps in (12, 13):
            with self.subTest(steps=steps):
                simulation = Simulation(seed=319)
                simulation.run(steps)
                snapshot = observer_snapshot(simulation)
                names = {item["name"] for item in snapshot["relationships"]}
                self.assertEqual("Aiko Sato" in names, steps == 13)
                if steps == 12:
                    snapshot["relationships"].append({
                        "affection": 0, "familiarity": 5, "loyalty": 4,
                        "name": "Aiko Sato", "role": "F-rank guild clerk",
                        "tension": 0, "trust": 3,
                    })
                    snapshot["relationships"].sort(key=lambda item: item["name"])
                else:
                    snapshot["relationships"] = [
                        item for item in snapshot["relationships"]
                        if item["name"] != "Aiko Sato"]
                _redigest(snapshot)
                with self.assertRaisesRegex(ValueError, "Guild registration evidence"):
                    verify_observer_snapshot(snapshot)

    def test_verifier_requires_authored_relationship_chronology(self) -> None:
        boundaries = (
            ("Daichi Mori", 16, 17),
            ("Mei Kuroda", 21, 22),
            ("Haruto Ishikawa", 34, 35),
        )
        for name, before_steps, after_steps in boundaries:
            later = Simulation(seed=321)
            later.run(after_steps)
            authored_relationship = next(
                item for item in observer_snapshot(later)["relationships"]
                if item["name"] == name)
            for steps in (before_steps, after_steps):
                with self.subTest(name=name, steps=steps):
                    simulation = Simulation(seed=321)
                    simulation.run(steps)
                    snapshot = observer_snapshot(simulation)
                    names = {item["name"] for item in snapshot["relationships"]}
                    self.assertEqual(name in names, steps == after_steps)
                    if steps == before_steps:
                        snapshot["relationships"].append(authored_relationship)
                        snapshot["relationships"].sort(key=lambda item: item["name"])
                    else:
                        snapshot["relationships"] = [
                            item for item in snapshot["relationships"]
                            if item["name"] != name]
                    _redigest(snapshot)
                    with self.assertRaisesRegex(ValueError, "relationship chronology"):
                        verify_observer_snapshot(snapshot)

    def test_verifier_requires_relationship_introduction_evidence(self) -> None:
        for name, steps in (
                ("Aiko Sato", 13),
                ("Daichi Mori", 17),
                ("Mei Kuroda", 22),
                ("Haruto Ishikawa", 35)):
            with self.subTest(name=name):
                simulation = Simulation(seed=323)
                simulation.run(steps)
                snapshot = observer_snapshot(simulation)
                relationship = next(
                    item for item in snapshot["relationships"]
                    if item["name"] == name)
                relationship["trust"] += 1
                _redigest(snapshot)
                with self.assertRaisesRegex(
                        ValueError, "relationship introduction evidence"):
                    verify_observer_snapshot(snapshot)

    def test_verifier_requires_fixed_event_locations(self) -> None:
        for steps, expected_location in (
                (10, "Tokyo Awakening Bureau"),
                (13, "Tokyo Hunter Guild")):
            with self.subTest(steps=steps):
                simulation = Simulation(seed=325)
                simulation.run(steps)
                snapshot = observer_snapshot(simulation)
                self.assertEqual(
                    snapshot["protagonist"]["location"], expected_location)
                snapshot["protagonist"]["location"] = "Adachi Apartment"
                _redigest(snapshot)
                with self.assertRaisesRegex(ValueError, "fixed-event location"):
                    verify_observer_snapshot(snapshot)

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
        simulation.run(35)
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
        simulation.run(35)
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

    def test_presentation_contract_is_versioned_read_only_and_isolated(
            self) -> None:
        first = observer_presentation_contract()
        second = observer_presentation_contract()

        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertEqual(first["contract_schema_version"], 2)
        self.assertEqual(first["observer_schema_version"], 4)
        self.assertEqual(first["comparison_schema_version"], 8)
        self.assertTrue(first["read_only"])
        self.assertEqual(first["control_capabilities"], [])
        digest_payload = {
            key: value for key, value in first.items()
            if key != "contract_sha256"
        }
        canonical = json.dumps(
            digest_payload, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self.assertEqual(
            first["contract_sha256"], hashlib.sha256(canonical).hexdigest())
        self.assertEqual(len(first["contract_sha256"]), 64)
        self.assertEqual(first["animation_cues"], sorted(first["animation_cues"]))
        self.assertIn("other", first["animation_cues"])
        self.assertIn("story", first["animation_cues"])
        first["animation_cues"].append("client-local")
        self.assertNotIn("client-local", second["animation_cues"])

    def test_presentation_contract_verifier_accepts_without_mutation(
            self) -> None:
        contract = observer_presentation_contract()
        before = deepcopy(contract)

        summary = verify_observer_presentation_contract(contract)

        self.assertEqual(contract, before)
        self.assertEqual(summary, {
            "comparison_schema_version": 8,
            "contract_schema_version": 2,
            "contract_sha256": contract["contract_sha256"],
            "observer_schema_version": 4,
            "status": "valid",
        })

    def test_presentation_contract_verifier_rejects_changed_content(
            self) -> None:
        tampered = observer_presentation_contract()
        tampered["animation_cues"].append("control")
        with self.assertRaisesRegex(ValueError, "integrity check failed"):
            verify_observer_presentation_contract(tampered)

        unsupported = observer_presentation_contract()
        unsupported["control_capabilities"] = ["pause"]
        payload = {
            key: value for key, value in unsupported.items()
            if key != "contract_sha256"
        }
        canonical = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        unsupported["contract_sha256"] = hashlib.sha256(canonical).hexdigest()
        with self.assertRaisesRegex(ValueError, "unsupported"):
            verify_observer_presentation_contract(unsupported)

    def test_presentation_contract_publication_is_canonical_and_non_overwriting(
            self) -> None:
        contract = observer_presentation_contract()
        with TemporaryDirectory() as temporary_directory:
            target = Path(temporary_directory) / "nested" / "contract.json"

            published = save_observer_presentation_contract(contract, target)

            self.assertEqual(published, target)
            self.assertEqual(
                target.read_text(encoding="utf-8"),
                json.dumps(
                    contract, ensure_ascii=False, indent=2, sort_keys=True
                ) + "\n",
            )
            verify_observer_presentation_contract(
                json.loads(target.read_text(encoding="utf-8")))
            original = target.read_bytes()
            with self.assertRaisesRegex(ValueError, "already exists"):
                save_observer_presentation_contract(contract, target)
            self.assertEqual(target.read_bytes(), original)

    def test_presentation_contract_publication_rejects_before_creating_file(
            self) -> None:
        contract = observer_presentation_contract()
        contract["read_only"] = False
        with TemporaryDirectory() as temporary_directory:
            target = Path(temporary_directory) / "contract.json"

            with self.assertRaisesRegex(ValueError, "integrity check failed"):
                save_observer_presentation_contract(contract, target)

            self.assertFalse(target.exists())

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
        self.assertIsNone(comparison["appended_event"])
        self.assertIsNone(comparison["animation_cue"])
        self.assertEqual(comparison["changed_sections"], [])
        self.assertEqual(comparison["comparison_schema_version"], 8)
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
            comparison["appended_event"], right["activity"]["recent_events"][-1])
        self.assertIsNot(
            comparison["appended_event"], right["activity"]["recent_events"][-1])
        self.assertIn(comparison["animation_cue"], {
            "food", "rest", "work", "study", "train",
        })
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
        self.assertIsNone(backward["appended_event"])
        self.assertTrue(backward["same_seed"])
        self.assertEqual(different_seed["clock_relation"], "same")
        self.assertEqual(different_seed["clock_delta_slots"], 0)
        self.assertFalse(different_seed["same_seed"])
        self.assertEqual(different_seed["update_mode"], "replace")
        self.assertIn("seed", different_seed["changed_sections"])

    def test_snapshot_comparison_refreshes_same_clock_changes(self) -> None:
        left = observer_snapshot(Simulation(seed=443))
        right = deepcopy(left)
        right["protagonist"]["mood"] = "Steady"
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
        self.assertIsNone(comparison["appended_event"])
        self.assertIsNone(comparison["animation_cue"])
        self.assertEqual(comparison["update_mode"], "refresh")

    def test_snapshot_comparison_maps_stable_animation_cues(self) -> None:
        simulation = Simulation(seed=448)
        left = observer_snapshot(simulation)
        simulation.step()
        template = observer_snapshot(simulation)
        cases = {
            "Eat": "food",
            "Rest": "rest",
            "Part-time work": "work",
            "Pay rent arrears": "finance",
            "Study": "study",
            "Train": "train",
            "Seek treatment": "treatment",
            "Prepare portal": "portal_preparation",
            "Visit hunter shop": "shopping",
            "Talk with Aiko": "social",
            "Meet Daichi Mori": "social",
            "Guild patrol": "patrol",
            "Gate mission": "mission",
            "Tanabata evening": "festival",
            "Awakening assessment": "awakening",
            "Guild registration": "registration",
            "Rent deadline": "finance",
            "Investigation consequence": "consequence",
            STORY_ANCHORS[0].title: "story",
            "Historical custom action": "other",
        }

        for action, cue in cases.items():
            with self.subTest(action=action):
                right = deepcopy(template)
                right["activity"]["recent_events"][-1]["action"] = action
                _redigest(right)
                comparison = compare_observer_snapshots(left, right)
                self.assertEqual(comparison["animation_cue"], cue)
                self.assertEqual(comparison["update_mode"], "animate")

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
        self.assertIsNone(forward["appended_event"])
        self.assertIsNone(forward["animation_cue"])
        self.assertEqual(backward["clock_relation"], "backward")
        self.assertEqual(backward["clock_delta_slots"], -9)

    def test_site_data_publication_is_atomic_verified_and_non_overwriting(
            self) -> None:
        snapshot = observer_snapshot(Simulation(seed=457))
        snapshot["path"] = "saves/ren.json"
        with TemporaryDirectory() as directory:
            target = Path(directory) / "public" / "data"

            published = publish_observer_site_data(snapshot, target)

            self.assertEqual(published, target)
            self.assertEqual(
                sorted(path.name for path in target.iterdir()),
                ["observer-contract.json", "observer-snapshot.json"],
            )
            contract = json.loads(
                (target / "observer-contract.json").read_text(encoding="utf-8"))
            loaded_snapshot = json.loads(
                (target / "observer-snapshot.json").read_text(encoding="utf-8"))
            verify_observer_presentation_contract(contract)
            verify_observer_snapshot(loaded_snapshot)
            self.assertEqual(loaded_snapshot, snapshot)
            before = {
                path.name: path.read_bytes() for path in target.iterdir()
            }
            with self.assertRaisesRegex(ValueError, "already exists"):
                publish_observer_site_data(snapshot, target)
            self.assertEqual(
                {path.name: path.read_bytes() for path in target.iterdir()},
                before,
            )

    def test_site_data_publication_rejects_invalid_snapshot_without_directory(
            self) -> None:
        snapshot = observer_snapshot(Simulation(seed=461))
        snapshot["clock"]["day"] += 1
        with TemporaryDirectory() as directory:
            target = Path(directory) / "data"

            with self.assertRaisesRegex(ValueError, "integrity check failed"):
                publish_observer_site_data(snapshot, target)

            self.assertFalse(target.exists())

    def test_site_data_verifier_is_read_only_and_reports_identity(self) -> None:
        snapshot = observer_snapshot(Simulation(seed=487))
        with TemporaryDirectory() as directory:
            target = Path(directory) / "data"
            publish_observer_site_data(snapshot, target)
            before = {
                path.name: path.read_bytes() for path in target.iterdir()
            }

            summary = verify_observer_site_data(target)

            self.assertEqual(summary, {
                "contract_sha256": observer_presentation_contract()[
                    "contract_sha256"],
                "day": snapshot["clock"]["day"],
                "observer_schema_version": 4,
                "seed": 487,
                "snapshot_sha256": snapshot["identity"]["digest"],
                "status": "valid",
            })
            self.assertEqual(
                {path.name: path.read_bytes() for path in target.iterdir()},
                before,
            )

    def test_site_data_verifier_rejects_tampering_and_directory_drift(
            self) -> None:
        snapshot = observer_snapshot(Simulation(seed=491))
        with TemporaryDirectory() as directory:
            target = Path(directory) / "data"
            publish_observer_site_data(snapshot, target)
            snapshot_path = target / "observer-snapshot.json"
            original = snapshot_path.read_text(encoding="utf-8")
            snapshot_path.write_text(
                original.replace('"seed": 491', '"seed": 492'),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "integrity check failed"):
                verify_observer_site_data(target)
            snapshot_path.write_text(original, encoding="utf-8")
            (target / "unexpected.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "contents are malformed"):
                verify_observer_site_data(target)

    def test_site_data_comparison_reuses_verified_snapshot_semantics(
            self) -> None:
        simulation = Simulation(seed=509)
        left_snapshot = observer_snapshot(simulation)
        simulation.step()
        right_snapshot = observer_snapshot(simulation)
        with TemporaryDirectory() as directory:
            left = Path(directory) / "left"
            right = Path(directory) / "right"
            publish_observer_site_data(left_snapshot, left)
            publish_observer_site_data(right_snapshot, right)
            before = {
                (root.name, file.name): file.read_bytes()
                for root in (left, right) for file in root.iterdir()
            }

            comparison = compare_observer_site_data(left, right)

            self.assertTrue(comparison["contract_identical"])
            self.assertFalse(comparison["identical"])
            self.assertEqual(comparison["snapshot"]["update_mode"], "animate")
            self.assertEqual(comparison["snapshot"]["clock_delta_slots"], 1)
            self.assertEqual(comparison["left"]["status"], "valid")
            self.assertEqual(comparison["right"]["status"], "valid")
            self.assertEqual(
                {
                    (root.name, file.name): file.read_bytes()
                    for root in (left, right) for file in root.iterdir()
                },
                before,
            )

    def test_site_data_comparison_reports_identical_deployments(self) -> None:
        snapshot = observer_snapshot(Simulation(seed=521))
        with TemporaryDirectory() as directory:
            left = Path(directory) / "left"
            right = Path(directory) / "right"
            publish_observer_site_data(snapshot, left)
            publish_observer_site_data(snapshot, right)

            comparison = compare_observer_site_data(left, right)

            self.assertTrue(comparison["identical"])
            self.assertTrue(comparison["snapshot"]["identical"])
            self.assertEqual(
                comparison["left"]["snapshot_sha256"],
                comparison["right"]["snapshot_sha256"],
            )

    def test_site_comparison_artifact_is_verified_and_non_overwriting(
            self) -> None:
        simulation = Simulation(seed=557)
        left_snapshot = observer_snapshot(simulation)
        simulation.step()
        right_snapshot = observer_snapshot(simulation)
        with TemporaryDirectory() as directory:
            left = Path(directory) / "left"
            right = Path(directory) / "right"
            artifact_path = Path(directory) / "artifacts" / "comparison.json"
            publish_observer_site_data(left_snapshot, left)
            publish_observer_site_data(right_snapshot, right)
            comparison = compare_observer_site_data(left, right)

            published = save_observer_site_comparison(
                comparison, artifact_path)
            loaded = load_observer_site_comparison_artifact(artifact_path)

            self.assertEqual(published, artifact_path)
            self.assertEqual(loaded["artifact_schema_version"], 1)
            self.assertEqual(loaded["comparison"], comparison)
            self.assertEqual(len(loaded["comparison_sha256"]), 64)
            self.assertTrue(artifact_path.read_bytes().endswith(b"\n"))
            original = artifact_path.read_bytes()
            with self.assertRaisesRegex(ValueError, "already exists"):
                save_observer_site_comparison(comparison, artifact_path)
            self.assertEqual(artifact_path.read_bytes(), original)

    def test_site_comparison_artifact_rejects_digest_tampering(self) -> None:
        snapshot = observer_snapshot(Simulation(seed=563))
        with TemporaryDirectory() as directory:
            left = Path(directory) / "left"
            right = Path(directory) / "right"
            artifact_path = Path(directory) / "comparison.json"
            publish_observer_site_data(snapshot, left)
            publish_observer_site_data(snapshot, right)
            save_observer_site_comparison(
                compare_observer_site_data(left, right), artifact_path)
            artifact = json.loads(
                artifact_path.read_text(encoding="utf-8"))
            artifact["comparison"]["identical"] = False
            artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "integrity verification"):
                load_observer_site_comparison_artifact(artifact_path)

    def test_site_comparison_artifact_rejects_redigested_inconsistency(
            self) -> None:
        snapshot = observer_snapshot(Simulation(seed=569))
        with TemporaryDirectory() as directory:
            left = Path(directory) / "left"
            right = Path(directory) / "right"
            artifact_path = Path(directory) / "comparison.json"
            publish_observer_site_data(snapshot, left)
            publish_observer_site_data(snapshot, right)
            save_observer_site_comparison(
                compare_observer_site_data(left, right), artifact_path)
            artifact = json.loads(
                artifact_path.read_text(encoding="utf-8"))
            artifact["comparison"]["snapshot"]["same_seed"] = False
            payload = {
                "artifact_schema_version": artifact["artifact_schema_version"],
                "comparison": artifact["comparison"],
            }
            canonical = json.dumps(
                payload, ensure_ascii=False, sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            artifact["comparison_sha256"] = hashlib.sha256(
                canonical).hexdigest()
            artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "content is invalid"):
                load_observer_site_comparison_artifact(artifact_path)

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
