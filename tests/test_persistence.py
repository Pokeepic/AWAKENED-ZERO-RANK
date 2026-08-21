"""Failure-safety tests for deterministic simulation persistence."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from io import StringIO
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from awakened_zero_rank.cli import main as cli_main
from awakened_zero_rank.models import (DelayedConsequence, DialogueExchange,
                                       Memory, PortalInvestigation, TimeSlot)
from awakened_zero_rank.persistence import load_simulation, save_simulation
from awakened_zero_rank.simulation import Simulation
from awakened_zero_rank.story import story_progress


class PersistenceSafetyTests(unittest.TestCase):
    def test_rank_e_equipment_round_trips_through_save(self) -> None:
        simulation = Simulation(seed=42)
        simulation.run(300)
        protagonist = simulation.state.protagonist
        self.assertIn(protagonist.hunter_rank, {"E", "D", "C"})
        protagonist.add_item("Reinforced Machete")
        protagonist.add_item("Gateweave Vest")
        protagonist.equipped_weapon = "Reinforced Machete"
        protagonist.equipped_armor = "Gateweave Vest"

        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"
            save_simulation(simulation, destination)
            restored = load_simulation(destination)

        self.assertEqual(restored.state.protagonist.equipped_weapon,
                         "Reinforced Machete")
        self.assertEqual(restored.state.protagonist.equipped_armor,
                         "Gateweave Vest")

    def test_rank_f_cannot_save_rank_e_equipment(self) -> None:
        simulation = Simulation(seed=43)
        simulation.run(20)
        protagonist = simulation.state.protagonist
        self.assertEqual(protagonist.hunter_rank, "F")
        protagonist.add_item("Reinforced Machete")
        protagonist.equipped_weapon = "Reinforced Machete"

        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"
            with self.assertRaisesRegex(ValueError, "hunter rank is too low"):
                save_simulation(simulation, destination)

    def test_failed_atomic_replace_preserves_existing_save(self) -> None:
        simulation = Simulation(seed=42)
        simulation.run(4)

        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"
            destination.write_text("existing timeline", encoding="utf-8")

            with patch(
                    "awakened_zero_rank.persistence.os.replace",
                    side_effect=OSError("injected replace failure")):
                with self.assertRaisesRegex(OSError, "injected replace failure"):
                    save_simulation(simulation, destination)

            self.assertEqual(
                destination.read_text(encoding="utf-8"), "existing timeline")
            self.assertEqual(
                list(destination.parent.glob(f".{destination.name}.*.tmp")), [])

    def test_invalid_state_cannot_replace_existing_save(self) -> None:
        simulation = Simulation(seed=47)
        simulation.state.protagonist.health = 101
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"
            destination.write_text("existing timeline", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "protagonist.health"):
                save_simulation(simulation, destination)

            self.assertEqual(
                destination.read_text(encoding="utf-8"), "existing timeline")
            self.assertEqual(
                list(destination.parent.glob(f".{destination.name}.*.tmp")), [])

    def test_unknown_location_cannot_replace_existing_save(self) -> None:
        simulation = Simulation(seed=53)
        simulation.state.protagonist.location = "Unknown District"
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"
            destination.write_text("existing timeline", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "protagonist.location"):
                save_simulation(simulation, destination)

            self.assertEqual(
                destination.read_text(encoding="utf-8"), "existing timeline")

    def test_tampered_integrity_checked_save_is_rejected(self) -> None:
        simulation = Simulation(seed=17)
        simulation.run(8)

        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"
            save_simulation(simulation, destination)
            data = json.loads(destination.read_text(encoding="utf-8"))
            data["state"]["protagonist"]["money"] += 1
            destination.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "integrity check failed"):
                load_simulation(destination)

    def test_cli_reports_integrity_failure_without_traceback(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"
            save_simulation(Simulation(seed=23), destination)
            data = json.loads(destination.read_text(encoding="utf-8"))
            data["seed"] += 1
            destination.write_text(json.dumps(data), encoding="utf-8")
            output, errors = StringIO(), StringIO()

            with redirect_stdout(output), redirect_stderr(errors):
                with self.assertRaises(SystemExit) as context:
                    cli_main(("--load", str(destination)))

        self.assertEqual(context.exception.code, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("Cannot load timeline: Save integrity check failed", errors.getvalue())
        self.assertNotIn("Traceback", errors.getvalue())

    def test_cli_reports_missing_save_without_traceback(self) -> None:
        output, errors = StringIO(), StringIO()
        with TemporaryDirectory() as temporary_directory:
            missing = Path(temporary_directory) / "missing.json"
            with redirect_stdout(output), redirect_stderr(errors):
                with self.assertRaises(SystemExit) as context:
                    cli_main(("--load", str(missing)))

        self.assertEqual(context.exception.code, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("Cannot load timeline:", errors.getvalue())
        self.assertNotIn("Traceback", errors.getvalue())

    def test_cli_reports_save_failure_without_traceback(self) -> None:
        output, errors = StringIO(), StringIO()

        with patch(
                "awakened_zero_rank.cli.save_simulation",
                side_effect=OSError("injected save failure")):
            with redirect_stdout(output), redirect_stderr(errors):
                with self.assertRaises(SystemExit) as context:
                    cli_main(("--days", "1", "--save", "timeline.json"))

        self.assertEqual(context.exception.code, 2)
        self.assertIn("AWAKENED ZERO RANK", output.getvalue())
        self.assertIn("Cannot save timeline: injected save failure", errors.getvalue())
        self.assertNotIn("Timeline saved to", output.getvalue())
        self.assertNotIn("Traceback", errors.getvalue())

    def test_cli_reports_semantic_save_failure_without_traceback(self) -> None:
        output, errors = StringIO(), StringIO()
        with patch(
                "awakened_zero_rank.cli.save_simulation",
                side_effect=ValueError("invalid current timeline")):
            with redirect_stdout(output), redirect_stderr(errors):
                with self.assertRaises(SystemExit) as context:
                    cli_main(("--days", "1", "--save", "timeline.json"))

        self.assertEqual(context.exception.code, 2)
        self.assertIn(
            "Cannot save timeline: invalid current timeline", errors.getvalue())
        self.assertNotIn("Timeline saved to", output.getvalue())
        self.assertNotIn("Traceback", errors.getvalue())

    def test_legacy_save_with_impossible_state_is_rejected(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "legacy.json"
            save_simulation(Simulation(seed=41), destination)
            data = json.loads(destination.read_text(encoding="utf-8"))
            data["save_version"] = 1
            data.pop("save_digest")
            data["state"]["protagonist"]["health"] = 101
            destination.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(
                    ValueError, "protagonist.health"):
                load_simulation(destination)

    def test_redigested_unknown_equipment_is_rejected(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"
            save_simulation(Simulation(seed=59), destination)
            data = json.loads(destination.read_text(encoding="utf-8"))
            data.pop("save_digest")
            data["state"]["protagonist"]["equipped_weapon"] = "Ghost Blade"
            payload = json.dumps(
                data, ensure_ascii=False, sort_keys=True,
                separators=(",", ":")).encode("utf-8")
            data["save_digest"] = hashlib.sha256(payload).hexdigest()
            destination.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "equipped_weapon"):
                load_simulation(destination)

    def test_redigested_mismatched_portal_investigation_is_rejected(self) -> None:
        simulation = Simulation(seed=61)
        simulation.run(24)
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"
            save_simulation(simulation, destination)
            data = json.loads(destination.read_text(encoding="utf-8"))
            data.pop("save_digest")
            investigations = data["state"]["portal_investigations"]
            name = next(iter(investigations))
            investigations[name]["portal_name"] = "Unknown Portal"
            payload = json.dumps(
                data, ensure_ascii=False, sort_keys=True,
                separators=(",", ":")).encode("utf-8")
            data["save_digest"] = hashlib.sha256(payload).hexdigest()
            destination.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "portal_investigations"):
                load_simulation(destination)

    def test_active_portal_plan_requires_investigation(self) -> None:
        simulation = Simulation(seed=67)
        simulation.state.active_portal_plan = "Flooded Service Tunnel"
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"

            with self.assertRaisesRegex(ValueError, "active_portal_plan"):
                save_simulation(simulation, destination)

            self.assertFalse(destination.exists())

    def test_portal_investigation_requires_discovery(self) -> None:
        simulation = Simulation(seed=69)
        simulation.run(24)
        self.assertTrue(simulation.state.portal_investigations)
        simulation.state.discovered_portals.clear()
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"
            with self.assertRaisesRegex(ValueError, "must be discovered"):
                save_simulation(simulation, destination)
            self.assertFalse(destination.exists())

    def test_hunter_rank_requires_matching_ability(self) -> None:
        simulation = Simulation(seed=70)
        simulation.state.protagonist.ability = "Threat Sense"
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"
            with self.assertRaisesRegex(ValueError, "protagonist lifecycle"):
                save_simulation(simulation, destination)
            self.assertFalse(destination.exists())

    def test_hunter_status_requires_authored_awakening_chronology(self) -> None:
        cases = (
            (1, TimeSlot.MORNING, "F", "Threat Sense"),
            (3, TimeSlot.AFTERNOON, "F", "Threat Sense"),
            (3, TimeSlot.EVENING, "Unranked", "None"),
            (4, TimeSlot.MORNING, "Unranked", "None"),
        )
        for day, slot, rank, ability in cases:
            with self.subTest(day=day, slot=slot, rank=rank), TemporaryDirectory() as temporary_directory:
                simulation = Simulation(seed=82)
                simulation.state.clock.day = day
                simulation.state.clock.slot = slot
                simulation.state.protagonist.hunter_rank = rank
                simulation.state.protagonist.ability = ability
                destination = Path(temporary_directory) / "timeline.json"
                with self.assertRaisesRegex(ValueError, "Awakening chronology"):
                    save_simulation(simulation, destination)
                self.assertFalse(destination.exists())

    def test_current_goal_requires_lifecycle_consistency(self) -> None:
        for steps in (0, 10, 13):
            with self.subTest(steps=steps), TemporaryDirectory() as temporary_directory:
                simulation = Simulation(seed=84)
                simulation.run(steps)
                simulation.state.protagonist.current_goal = "Invented objective"
                destination = Path(temporary_directory) / "timeline.json"
                with self.assertRaisesRegex(ValueError, "current goal"):
                    save_simulation(simulation, destination)
                self.assertFalse(destination.exists())

    def test_guild_registration_requires_authored_evidence(self) -> None:
        for steps in (12, 13):
            with self.subTest(steps=steps), TemporaryDirectory() as temporary_directory:
                simulation = Simulation(seed=86)
                simulation.run(steps)
                if steps == 12:
                    simulation.state.protagonist.guild_registered = True
                else:
                    simulation.state.protagonist.relationships.pop("Aiko Sato")
                destination = Path(temporary_directory) / "timeline.json"
                with self.assertRaisesRegex(ValueError, "Guild registration evidence"):
                    save_simulation(simulation, destination)
                self.assertFalse(destination.exists())

    def test_relationships_require_authored_introduction_chronology(self) -> None:
        boundaries = (
            ("Daichi Mori", 16, 17),
            ("Mei Kuroda", 21, 22),
            ("Haruto Ishikawa", 34, 35),
        )
        for name, before_steps, after_steps in boundaries:
            later = Simulation(seed=88)
            later.run(after_steps)
            authored_relationship = later.state.protagonist.relationships[name]
            for steps in (before_steps, after_steps):
                with self.subTest(name=name, steps=steps), TemporaryDirectory() as temporary_directory:
                    simulation = Simulation(seed=88)
                    simulation.run(steps)
                    if steps == before_steps:
                        simulation.state.protagonist.relationships[name] = authored_relationship
                    else:
                        simulation.state.protagonist.relationships.pop(name)
                    destination = Path(temporary_directory) / "timeline.json"
                    with self.assertRaisesRegex(ValueError, "relationship chronology"):
                        save_simulation(simulation, destination)
                    self.assertFalse(destination.exists())

    def test_relationship_introductions_require_authored_evidence(self) -> None:
        for name, steps in (
                ("Aiko Sato", 13),
                ("Daichi Mori", 17),
                ("Mei Kuroda", 22),
                ("Haruto Ishikawa", 35)):
            with self.subTest(name=name), TemporaryDirectory() as temporary_directory:
                simulation = Simulation(seed=90)
                simulation.run(steps)
                simulation.state.protagonist.relationships[name].meetings += 1
                destination = Path(temporary_directory) / "timeline.json"
                with self.assertRaisesRegex(
                        ValueError, "relationship introduction evidence"):
                    save_simulation(simulation, destination)
                self.assertFalse(destination.exists())

    def test_fixed_events_require_authored_locations(self) -> None:
        for steps, expected_location in (
                (10, "Tokyo Awakening Bureau"),
                (13, "Tokyo Hunter Guild")):
            with self.subTest(steps=steps), TemporaryDirectory() as temporary_directory:
                simulation = Simulation(seed=92)
                simulation.run(steps)
                self.assertEqual(
                    simulation.state.protagonist.location, expected_location)
                simulation.state.protagonist.location = "Adachi Apartment"
                destination = Path(temporary_directory) / "timeline.json"
                with self.assertRaisesRegex(ValueError, "fixed-event location"):
                    save_simulation(simulation, destination)
                self.assertFalse(destination.exists())

    def test_fixed_events_require_authored_state_evidence(self) -> None:
        for steps, mutate, message in (
                (10, lambda simulation: setattr(
                    simulation.state.protagonist, "ability_mastery", 2),
                 "Awakening mastery chronology"),
                (13, lambda simulation: setattr(
                    simulation.state, "gate_alert_level", 1),
                 "Guild alert evidence")):
            with self.subTest(steps=steps), TemporaryDirectory() as temporary_directory:
                simulation = Simulation(seed=94)
                simulation.run(steps)
                mutate(simulation)
                destination = Path(temporary_directory) / "timeline.json"
                with self.assertRaisesRegex(ValueError, message):
                    save_simulation(simulation, destination)
                self.assertFalse(destination.exists())

    def test_ability_mastery_cannot_predate_awakening(self) -> None:
        for steps in (0, 9):
            with self.subTest(steps=steps), TemporaryDirectory() as temporary_directory:
                simulation = Simulation(seed=105)
                simulation.run(steps)
                simulation.state.protagonist.ability_mastery = 1
                destination = Path(temporary_directory) / "timeline.json"
                with self.assertRaisesRegex(ValueError, "mastery chronology"):
                    save_simulation(simulation, destination)
                self.assertFalse(destination.exists())

    def test_awakened_mastery_cannot_revert_to_zero(self) -> None:
        for steps in (11, 13, 40):
            with self.subTest(steps=steps), TemporaryDirectory() as temporary_directory:
                simulation = Simulation(seed=106)
                simulation.run(steps)
                simulation.state.protagonist.ability_mastery = 0
                destination = Path(temporary_directory) / "timeline.json"
                with self.assertRaisesRegex(ValueError, "mastery chronology"):
                    save_simulation(simulation, destination)
                self.assertFalse(destination.exists())

    def test_fixed_events_require_empty_hunter_record_evidence(self) -> None:
        for steps in (10, 13):
            with self.subTest(steps=steps), TemporaryDirectory() as temporary_directory:
                simulation = Simulation(seed=95)
                simulation.run(steps)
                protagonist = simulation.state.protagonist
                protagonist.rank_points = 10
                protagonist.missions_attempted = 1
                protagonist.missions_completed = 1
                destination = Path(temporary_directory) / "timeline.json"
                with self.assertRaisesRegex(ValueError, "hunter record chronology"):
                    save_simulation(simulation, destination)
                self.assertFalse(destination.exists())

    def test_hunter_record_cannot_predate_registration(self) -> None:
        for steps in (0, 10, 13):
            with self.subTest(steps=steps), TemporaryDirectory() as temporary_directory:
                simulation = Simulation(seed=103)
                simulation.run(steps)
                simulation.state.protagonist.missions_attempted = 1
                destination = Path(temporary_directory) / "timeline.json"
                with self.assertRaisesRegex(ValueError, "hunter record chronology"):
                    save_simulation(simulation, destination)
                self.assertFalse(destination.exists())

    def test_fixed_events_require_empty_equipment_evidence(self) -> None:
        for steps in (10, 13):
            with self.subTest(steps=steps), TemporaryDirectory() as temporary_directory:
                simulation = Simulation(seed=96)
                simulation.run(steps)
                protagonist = simulation.state.protagonist
                protagonist.inventory["Field Knife"] = 1
                protagonist.equipped_weapon = "Field Knife"
                destination = Path(temporary_directory) / "timeline.json"
                with self.assertRaisesRegex(ValueError, "equipment chronology"):
                    save_simulation(simulation, destination)
                self.assertFalse(destination.exists())

    def test_equipment_cannot_predate_registration(self) -> None:
        for steps in (0, 10, 13):
            with self.subTest(steps=steps), TemporaryDirectory() as temporary_directory:
                simulation = Simulation(seed=101)
                simulation.run(steps)
                protagonist = simulation.state.protagonist
                protagonist.inventory["Field Knife"] = 1
                protagonist.equipped_weapon = "Field Knife"
                destination = Path(temporary_directory) / "timeline.json"
                with self.assertRaisesRegex(ValueError, "equipment chronology"):
                    save_simulation(simulation, destination)
                self.assertFalse(destination.exists())

    def test_fixed_events_require_empty_portal_evidence(self) -> None:
        for steps in (10, 13):
            with self.subTest(steps=steps), TemporaryDirectory() as temporary_directory:
                simulation = Simulation(seed=97)
                simulation.run(steps)
                simulation.state.discovered_portals.append(
                    "Ashen Shopping Arcade")
                destination = Path(temporary_directory) / "timeline.json"
                with self.assertRaisesRegex(ValueError, "portal chronology"):
                    save_simulation(simulation, destination)
                self.assertFalse(destination.exists())

    def test_portal_evidence_cannot_predate_registration(self) -> None:
        for steps in (0, 10, 13):
            with self.subTest(steps=steps), TemporaryDirectory() as temporary_directory:
                simulation = Simulation(seed=102)
                simulation.run(steps)
                simulation.state.discovered_portals.append(
                    "Ashen Shopping Arcade")
                destination = Path(temporary_directory) / "timeline.json"
                with self.assertRaisesRegex(ValueError, "portal chronology"):
                    save_simulation(simulation, destination)
                self.assertFalse(destination.exists())

    def test_fixed_events_require_authored_activity_evidence(self) -> None:
        for steps in (10, 13):
            with self.subTest(steps=steps), TemporaryDirectory() as temporary_directory:
                simulation = Simulation(seed=98)
                simulation.run(steps)
                simulation.state.events[-1] = replace(
                    simulation.state.events[-1], action="Invented event")
                destination = Path(temporary_directory) / "timeline.json"
                with self.assertRaisesRegex(ValueError, "activity evidence"):
                    save_simulation(simulation, destination)
                self.assertFalse(destination.exists())

    def test_fixed_events_require_authored_memory_evidence(self) -> None:
        for steps, day in ((10, 3), (13, 4)):
            with self.subTest(steps=steps), TemporaryDirectory() as temporary_directory:
                simulation = Simulation(seed=99)
                simulation.run(steps)
                simulation.state.protagonist.memories = [
                    memory for memory in simulation.state.protagonist.memories
                    if memory.day != day]
                destination = Path(temporary_directory) / "timeline.json"
                with self.assertRaisesRegex(ValueError, "memory (?:evidence|chronology)"):
                    save_simulation(simulation, destination)
                self.assertFalse(destination.exists())

    def test_fixed_event_memories_follow_their_chronology(self) -> None:
        awakening = Memory(
            3, "Awakening assessment: Awakened at Rank F with Threat Sense.", 10)
        registration = Memory(
            4, "Guild registration: Aiko Sato issued an F-rank license; "
            "travel and filing cost ¥0.", 8)
        for steps, mutate in (
                (9, lambda memories: memories.append(awakening)),
                (11, lambda memories: memories.clear()),
                (12, lambda memories: memories.append(registration)),
                (14, lambda memories: memories.clear())):
            with self.subTest(steps=steps), TemporaryDirectory() as temporary_directory:
                simulation = Simulation(seed=107)
                simulation.run(steps)
                mutate(simulation.state.protagonist.memories)
                destination = Path(temporary_directory) / "timeline.json"
                with self.assertRaisesRegex(ValueError, "memory chronology"):
                    save_simulation(simulation, destination)
                self.assertFalse(destination.exists())

    def test_events_must_precede_save_clock(self) -> None:
        for steps, slot in ((1, TimeSlot.AFTERNOON), (2, TimeSlot.LATE_NIGHT)):
            with self.subTest(steps=steps, slot=slot), TemporaryDirectory() as temporary_directory:
                simulation = Simulation(seed=108)
                simulation.run(steps)
                simulation.state.events[-1] = replace(
                    simulation.state.events[-1],
                    day=simulation.state.clock.day,
                    slot=slot)
                destination = Path(temporary_directory) / "timeline.json"
                with self.assertRaisesRegex(ValueError, "ahead of clock"):
                    save_simulation(simulation, destination)
                self.assertFalse(destination.exists())

    def test_events_cannot_share_a_clock_position(self) -> None:
        simulation = Simulation(seed=109)
        simulation.run(2)
        simulation.state.events[-1] = replace(
            simulation.state.events[-1],
            day=simulation.state.events[-2].day,
            slot=simulation.state.events[-2].slot)
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"
            with self.assertRaisesRegex(ValueError, "strictly chronological order"):
                save_simulation(simulation, destination)
            self.assertFalse(destination.exists())

    def test_events_require_complete_text(self) -> None:
        for field in ("action", "reason", "outcome"):
            with self.subTest(field=field), TemporaryDirectory() as temporary_directory:
                simulation = Simulation(seed=110)
                simulation.run(1)
                simulation.state.events[-1] = replace(
                    simulation.state.events[-1], **{field: ""})
                destination = Path(temporary_directory) / "timeline.json"
                destination.write_text("existing timeline", encoding="utf-8")
                with self.assertRaisesRegex(
                        ValueError, rf"events\[0\]\.{field}.*non-empty text"):
                    save_simulation(simulation, destination)
                self.assertEqual(
                    destination.read_text(encoding="utf-8"), "existing timeline")

    def test_memories_require_summary_text(self) -> None:
        simulation = Simulation(seed=111)
        simulation.state.protagonist.memories.append(Memory(1, "", 1))
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"
            destination.write_text("existing timeline", encoding="utf-8")
            with self.assertRaisesRegex(
                    ValueError, r"memories\[0\]\.summary.*non-empty text"):
                save_simulation(simulation, destination)
            self.assertEqual(
                destination.read_text(encoding="utf-8"), "existing timeline")

    def test_dialogue_history_requires_complete_text(self) -> None:
        fields = ("intention", "ren_line", "npc_name", "npc_line", "reaction")
        exchange = DialogueExchange(
            1, "Ask for guidance", "How should I prepare?", "Aiko Sato",
            "Watch the exits first.", "attentive")
        for field in fields:
            with self.subTest(field=field), TemporaryDirectory() as temporary_directory:
                simulation = Simulation(seed=112)
                simulation.state.protagonist.dialogue_history.append(
                    replace(exchange, **{field: ""}))
                destination = Path(temporary_directory) / "timeline.json"
                destination.write_text("existing timeline", encoding="utf-8")
                with self.assertRaisesRegex(
                        ValueError, rf"dialogue_history\[0\]\.{field}.*non-empty text"):
                    save_simulation(simulation, destination)
                self.assertEqual(
                    destination.read_text(encoding="utf-8"), "existing timeline")

    def test_dialogue_history_must_be_chronological(self) -> None:
        simulation = Simulation(seed=113)
        simulation.state.protagonist.dialogue_history.extend((
            DialogueExchange(
                2, "Ask for guidance", "How should I prepare?", "Aiko Sato",
                "Watch the exits first.", "attentive"),
            DialogueExchange(
                1, "Express gratitude", "Thank you.", "Aiko Sato",
                "Stay careful.", "pleased")))
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"
            destination.write_text("existing timeline", encoding="utf-8")
            with self.assertRaisesRegex(
                    ValueError, r"dialogue_history.*chronological order"):
                save_simulation(simulation, destination)
            self.assertEqual(
                destination.read_text(encoding="utf-8"), "existing timeline")

    def test_delayed_consequences_require_complete_text(self) -> None:
        consequence = DelayedConsequence(
            due_day=2, source="Portal investigation", people=(),
            description="A warning reaches the guild.")
        for field in ("source", "description"):
            with self.subTest(field=field), TemporaryDirectory() as temporary_directory:
                simulation = Simulation(seed=114)
                simulation.state.delayed_consequences.append(
                    replace(consequence, **{field: ""}))
                destination = Path(temporary_directory) / "timeline.json"
                destination.write_text("existing timeline", encoding="utf-8")
                with self.assertRaisesRegex(
                        ValueError,
                        rf"delayed_consequences\[0\]\.{field}.*non-empty text"):
                    save_simulation(simulation, destination)
                self.assertEqual(
                    destination.read_text(encoding="utf-8"), "existing timeline")

    def test_portal_investigation_requires_preparation_strategy(self) -> None:
        simulation = Simulation(seed=115)
        simulation.run(14)
        portal_name = "Ashen Shopping Arcade"
        simulation.state.discovered_portals.append(portal_name)
        simulation.state.portal_investigations[portal_name] = PortalInvestigation(
            portal_name=portal_name, preparation_strategy="")
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"
            destination.write_text("existing timeline", encoding="utf-8")
            with self.assertRaisesRegex(
                    ValueError, r"preparation_strategy.*non-empty text"):
                save_simulation(simulation, destination)
            self.assertEqual(
                destination.read_text(encoding="utf-8"), "existing timeline")

    def test_hunter_rank_requires_matching_rank_points(self) -> None:
        simulation = Simulation(seed=72)
        simulation.state.protagonist.rank_points = 30
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"
            with self.assertRaisesRegex(ValueError, "rank points"):
                save_simulation(simulation, destination)
            self.assertFalse(destination.exists())

    def test_hunter_shop_cannot_predate_registration(self) -> None:
        for steps in (0, 10, 13):
            with self.subTest(steps=steps), TemporaryDirectory() as temporary_directory:
                simulation = Simulation(seed=100)
                simulation.run(steps)
                simulation.state.shop_visits = 1
                destination = Path(temporary_directory) / "timeline.json"
                with self.assertRaisesRegex(ValueError, "shop chronology"):
                    save_simulation(simulation, destination)
                self.assertFalse(destination.exists())

    def test_rank_points_require_completed_mission_evidence(self) -> None:
        simulation = Simulation(seed=74)
        protagonist = simulation.state.protagonist
        protagonist.hunter_rank = "F"
        protagonist.ability = "Threat Sense"
        protagonist.rank_points = 10
        simulation.state.clock.day = 3
        simulation.state.clock.slot = TimeSlot.EVENING
        protagonist.location = "Tokyo Awakening Bureau"
        protagonist.ability_mastery = 1
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"
            with self.assertRaisesRegex(ValueError, "mission evidence"):
                save_simulation(simulation, destination)
            self.assertFalse(destination.exists())

    def test_rank_points_require_exact_mission_awards(self) -> None:
        simulation = Simulation(seed=76)
        protagonist = simulation.state.protagonist
        protagonist.hunter_rank = "F"
        protagonist.ability = "Threat Sense"
        protagonist.missions_attempted = 1
        protagonist.missions_completed = 1
        protagonist.rank_points = 11
        simulation.state.clock.day = 3
        simulation.state.clock.slot = TimeSlot.EVENING
        protagonist.location = "Tokyo Awakening Bureau"
        protagonist.ability_mastery = 1
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"
            with self.assertRaisesRegex(ValueError, "exact awards"):
                save_simulation(simulation, destination)
            self.assertFalse(destination.exists())

    def test_rent_ledger_requires_authored_consistency(self) -> None:
        mutations = {
            "due day": lambda simulation: setattr(
                simulation.state.protagonist, "rent_due_day", 7),
            "cost": lambda simulation: setattr(
                simulation.state.protagonist, "rent_cost", 7_999),
            "excess arrears": lambda simulation: setattr(
                simulation.state.protagonist, "rent_arrears", 8_001),
            "duplicate payment": lambda simulation: setattr(
                simulation.state, "rent_payments", 2),
            "paid with arrears": lambda simulation: (
                setattr(simulation.state, "rent_payments", 1),
                setattr(simulation.state.protagonist, "rent_arrears", 1)),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name), TemporaryDirectory() as temporary_directory:
                simulation = Simulation(seed=78)
                mutate(simulation)
                destination = Path(temporary_directory) / "timeline.json"
                with self.assertRaisesRegex(ValueError, "rent ledger"):
                    save_simulation(simulation, destination)
                self.assertFalse(destination.exists())

    def test_rent_ledger_cannot_predate_deadline(self) -> None:
        for day, slot in ((7, TimeSlot.LATE_NIGHT), (8, TimeSlot.MORNING)):
            with self.subTest(day=day, slot=slot), TemporaryDirectory() as temporary_directory:
                simulation = Simulation(seed=80)
                simulation.run(13)
                simulation.state.clock.day = day
                simulation.state.clock.slot = slot
                simulation.state.protagonist.hunter_rank = "F"
                simulation.state.protagonist.ability = "Threat Sense"
                simulation.state.rent_payments = 1
                destination = Path(temporary_directory) / "timeline.json"
                with self.assertRaisesRegex(ValueError, "predates"):
                    save_simulation(simulation, destination)
                self.assertFalse(destination.exists())

    def test_unknown_relationship_cannot_replace_existing_save(self) -> None:
        simulation = Simulation(seed=71)
        simulation.run(20)
        relationship = simulation.state.protagonist.relationships.pop("Aiko Sato")
        simulation.state.protagonist.relationships["Unknown Clerk"] = relationship
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"
            destination.write_text("existing timeline", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "relationships"):
                save_simulation(simulation, destination)

            self.assertEqual(
                destination.read_text(encoding="utf-8"), "existing timeline")

    def test_redigested_unknown_portal_collaborator_is_rejected(self) -> None:
        simulation = Simulation(seed=73)
        simulation.run(24)
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"
            save_simulation(simulation, destination)
            data = json.loads(destination.read_text(encoding="utf-8"))
            data.pop("save_digest")
            investigation = next(iter(
                data["state"]["portal_investigations"].values()))
            investigation["cooperating_npc"] = "Unknown Researcher"
            payload = json.dumps(
                data, ensure_ascii=False, sort_keys=True,
                separators=(",", ":")).encode("utf-8")
            data["save_digest"] = hashlib.sha256(payload).hexdigest()
            destination.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "cooperating_npc"):
                load_simulation(destination)

    def test_redigested_future_event_is_rejected(self) -> None:
        simulation = Simulation(seed=79)
        simulation.run(20)
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"
            save_simulation(simulation, destination)
            data = json.loads(destination.read_text(encoding="utf-8"))
            data.pop("save_digest")
            data["state"]["events"][0]["day"] = data["state"]["clock"]["day"] + 1
            payload = json.dumps(
                data, ensure_ascii=False, sort_keys=True,
                separators=(",", ":")).encode("utf-8")
            data["save_digest"] = hashlib.sha256(payload).hexdigest()
            destination.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, r"events\[0\]\.day"):
                load_simulation(destination)

    def test_unknown_consequence_participant_cannot_be_saved(self) -> None:
        simulation = Simulation(seed=83)
        simulation.run(80)
        consequence = simulation.state.delayed_consequences[0]
        object.__setattr__(consequence, "people", ("Unknown Witness",))
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"

            with self.assertRaisesRegex(ValueError, "delayed_consequences"):
                save_simulation(simulation, destination)

            self.assertFalse(destination.exists())

    def test_redigested_invalid_story_outcome_is_rejected(self) -> None:
        simulation = Simulation(seed=103)
        simulation.run(35)
        simulation.state.clock.day = 183
        simulation.state.clock.slot = TimeSlot.MORNING
        simulation.step()
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"
            save_simulation(simulation, destination)
            data = json.loads(destination.read_text(encoding="utf-8"))
            data.pop("save_digest")
            data["state"]["story_outcomes"]["arc_adachi_warning"] = "perfect"
            payload = json.dumps(
                data, ensure_ascii=False, sort_keys=True,
                separators=(",", ":")).encode("utf-8")
            data["save_digest"] = hashlib.sha256(payload).hexdigest()
            destination.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "story_outcomes"):
                load_simulation(destination)

    def test_missing_legacy_story_ledger_migrates_honestly(self) -> None:
        simulation = Simulation(seed=131)
        simulation.run(35)
        simulation.state.clock.day = 183
        simulation.state.clock.slot = TimeSlot.MORNING
        simulation.step()
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"
            save_simulation(simulation, destination)
            data = json.loads(destination.read_text(encoding="utf-8"))
            data.pop("save_digest")
            data["state"].pop("story_outcomes")
            payload = json.dumps(
                data, ensure_ascii=False, sort_keys=True,
                separators=(",", ":")).encode("utf-8")
            data["save_digest"] = hashlib.sha256(payload).hexdigest()
            destination.write_text(json.dumps(data), encoding="utf-8")

            restored = load_simulation(destination)

        self.assertEqual(
            restored.state.story_outcomes,
            {"arc_adachi_warning": "legacy-unavailable"})
        progress = story_progress(restored.state)
        self.assertEqual(progress["schema_version"], 4)
        self.assertEqual(progress["completed"][0]["tier"], "legacy-unavailable")
        self.assertIn("unavailable", progress["completed"][0]["outcome"])

    def test_redigested_story_ledger_cannot_skip_anchors(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"
            save_simulation(Simulation(seed=137), destination)
            data = json.loads(destination.read_text(encoding="utf-8"))
            data.pop("save_digest")
            data["state"]["calendar_events_seen"] = ["arc_tokyo_fracture"]
            data["state"]["story_outcomes"] = {
                "arc_tokyo_fracture": "resilient"}
            payload = json.dumps(
                data, ensure_ascii=False, sort_keys=True,
                separators=(",", ":")).encode("utf-8")
            data["save_digest"] = hashlib.sha256(payload).hexdigest()
            destination.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "chronological prefix"):
                load_simulation(destination)

    def test_redigested_impossible_state_fails_cli_validation(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"
            save_simulation(Simulation(seed=43), destination)
            data = json.loads(destination.read_text(encoding="utf-8"))
            data.pop("save_digest")
            data["state"]["protagonist"]["money"] = -1
            payload = json.dumps(
                data, ensure_ascii=False, sort_keys=True,
                separators=(",", ":")).encode("utf-8")
            data["save_digest"] = hashlib.sha256(payload).hexdigest()
            destination.write_text(json.dumps(data), encoding="utf-8")
            output, errors = StringIO(), StringIO()

            with redirect_stdout(output), redirect_stderr(errors):
                with self.assertRaises(SystemExit) as context:
                    cli_main(("--verify-save", str(destination)))

        self.assertEqual(context.exception.code, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("protagonist.money", errors.getvalue())
        self.assertNotIn("Traceback", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
