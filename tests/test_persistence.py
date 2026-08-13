"""Failure-safety tests for deterministic simulation persistence."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from awakened_zero_rank.cli import main as cli_main
from awakened_zero_rank.persistence import load_simulation, save_simulation
from awakened_zero_rank.simulation import Simulation
from awakened_zero_rank.story import story_progress


class PersistenceSafetyTests(unittest.TestCase):
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

    def test_hunter_rank_requires_matching_rank_points(self) -> None:
        simulation = Simulation(seed=72)
        simulation.state.protagonist.rank_points = 30
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "timeline.json"
            with self.assertRaisesRegex(ValueError, "rank points"):
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
        simulation.state.clock.day = 183
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
        simulation.state.clock.day = 183
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
        self.assertEqual(progress["schema_version"], 3)
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
