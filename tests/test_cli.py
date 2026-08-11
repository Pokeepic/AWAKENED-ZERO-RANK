"""Public command-line validation tests."""

from __future__ import annotations

import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from awakened_zero_rank.cli import main as cli_main
from awakened_zero_rank.persistence import save_simulation
from awakened_zero_rank.simulation import Simulation


class CliValidationTests(unittest.TestCase):
    def test_load_and_explicit_seed_are_mutually_exclusive(self) -> None:
        output, errors = StringIO(), StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            with self.assertRaises(SystemExit) as context:
                cli_main(("--load", "timeline.json", "--seed", "99"))

        self.assertEqual(context.exception.code, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("not allowed with argument", errors.getvalue())
        self.assertNotIn("Traceback", errors.getvalue())

    def test_nonpositive_days_use_standard_cli_error(self) -> None:
        output, errors = StringIO(), StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            with self.assertRaises(SystemExit) as context:
                cli_main(("--days", "0"))

        self.assertEqual(context.exception.code, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("error: --days must be at least 1", errors.getvalue())
        self.assertNotIn("Traceback", errors.getvalue())

    def test_verify_save_is_read_only_and_reports_json(self) -> None:
        simulation = Simulation(seed=73)
        simulation.run(5)
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "timeline.json"
            save_simulation(simulation, path)
            original = path.read_bytes()
            output = StringIO()

            with redirect_stdout(output):
                cli_main(("--verify-save", str(path)))

            self.assertEqual(path.read_bytes(), original)
        summary = json.loads(output.getvalue())
        self.assertEqual(summary["status"], "valid")
        self.assertEqual(summary["save_version"], 2)
        self.assertEqual(summary["integrity"], "verified")
        self.assertEqual(summary["seed"], 73)
        self.assertEqual(summary["day"], simulation.state.clock.day)
        self.assertEqual(summary["events"], len(simulation.state.events))

    def test_story_progress_is_read_only_and_reports_json(self) -> None:
        simulation = Simulation(seed=113)
        simulation.state.clock.day = 183
        simulation.step()
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "timeline.json"
            save_simulation(simulation, path)
            original = path.read_bytes()
            output = StringIO()

            with redirect_stdout(output):
                cli_main(("--story-progress", str(path)))

            self.assertEqual(path.read_bytes(), original)
        summary = json.loads(output.getvalue())
        self.assertEqual(summary["path"], str(path))
        self.assertEqual(summary["schema_version"], 3)
        self.assertEqual(summary["completed_count"], 1)
        self.assertEqual(summary["completed"][0]["tier"], "isolated")
        self.assertEqual(summary["next"]["key"], "arc_tokyo_fracture")
        self.assertFalse(summary["ending_reached"])

    def test_story_progress_rejects_simulation_options(self) -> None:
        output, errors = StringIO(), StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            with self.assertRaises(SystemExit) as context:
                cli_main(("--story-progress", "timeline.json", "--days", "1"))

        self.assertEqual(context.exception.code, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertIn(
            "--story-progress cannot use simulation options", errors.getvalue())

    def test_story_progress_reports_integrity_failure_cleanly(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "timeline.json"
            save_simulation(Simulation(seed=127), path)
            data = json.loads(path.read_text(encoding="utf-8"))
            data["seed"] += 1
            path.write_text(json.dumps(data), encoding="utf-8")
            output, errors = StringIO(), StringIO()

            with redirect_stdout(output), redirect_stderr(errors):
                with self.assertRaises(SystemExit) as context:
                    cli_main(("--story-progress", str(path)))

        self.assertEqual(context.exception.code, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("Save integrity check failed", errors.getvalue())
        self.assertNotIn("Traceback", errors.getvalue())

    def test_observer_snapshot_is_read_only_and_reports_json(self) -> None:
        simulation = Simulation(seed=157)
        simulation.run(40)
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "timeline.json"
            save_simulation(simulation, path)
            original = path.read_bytes()
            output = StringIO()

            with redirect_stdout(output):
                cli_main(("--observer-snapshot", str(path)))

            self.assertEqual(path.read_bytes(), original)
        snapshot = json.loads(output.getvalue())
        self.assertEqual(snapshot["path"], str(path))
        self.assertEqual(snapshot["schema_version"], 3)
        self.assertEqual(snapshot["seed"], 157)
        self.assertEqual(snapshot["clock"], {
            "day": simulation.state.clock.day,
            "slot": simulation.state.clock.slot.value,
        })
        self.assertEqual(snapshot["story"]["schema_version"], 3)
        self.assertEqual(
            [item["name"] for item in snapshot["relationships"]],
            sorted(simulation.state.protagonist.relationships),
        )

    def test_observer_snapshot_rejects_simulation_options(self) -> None:
        output, errors = StringIO(), StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            with self.assertRaises(SystemExit) as context:
                cli_main((
                    "--observer-snapshot", "timeline.json", "--technical-log",
                ))

        self.assertEqual(context.exception.code, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertIn(
            "--observer-snapshot cannot use simulation options",
            errors.getvalue(),
        )

    def test_observer_snapshot_reports_integrity_failure_cleanly(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "timeline.json"
            save_simulation(Simulation(seed=163), path)
            data = json.loads(path.read_text(encoding="utf-8"))
            data["seed"] += 1
            path.write_text(json.dumps(data), encoding="utf-8")
            output, errors = StringIO(), StringIO()

            with redirect_stdout(output), redirect_stderr(errors):
                with self.assertRaises(SystemExit) as context:
                    cli_main(("--observer-snapshot", str(path)))

        self.assertEqual(context.exception.code, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("Save integrity check failed", errors.getvalue())
        self.assertNotIn("Traceback", errors.getvalue())

    def test_observer_summary_reports_named_story_ending(self) -> None:
        simulation = Simulation(seed=151)
        simulation.state.clock.day = 1095
        from awakened_zero_rank.content import STORY_ANCHORS
        simulation.state.calendar_events_seen.extend(
            anchor.key for anchor in STORY_ANCHORS)
        simulation.state.story_outcomes.update(
            (anchor.key, "prepared") for anchor in STORY_ANCHORS)
        output = StringIO()
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "timeline.json"
            save_simulation(simulation, path)
            with redirect_stdout(output):
                cli_main(("--load", str(path), "--days", "1"))

        self.assertIn("Ending: The Zero-Rank Horizon", output.getvalue())
    def test_verify_legacy_save_reports_unavailable_integrity(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "legacy.json"
            save_simulation(Simulation(seed=19), path)
            data = json.loads(path.read_text(encoding="utf-8"))
            data["save_version"] = 1
            data.pop("save_digest")
            path.write_text(json.dumps(data), encoding="utf-8")
            output = StringIO()

            with redirect_stdout(output):
                cli_main(("--verify-save", str(path)))

        summary = json.loads(output.getvalue())
        self.assertEqual(summary["status"], "valid")
        self.assertEqual(summary["save_version"], 1)
        self.assertEqual(summary["integrity"], "legacy-unavailable")

    def test_verify_save_rejects_integrity_failure_cleanly(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "timeline.json"
            save_simulation(Simulation(seed=31), path)
            data = json.loads(path.read_text(encoding="utf-8"))
            data["seed"] += 1
            path.write_text(json.dumps(data), encoding="utf-8")
            output, errors = StringIO(), StringIO()

            with redirect_stdout(output), redirect_stderr(errors):
                with self.assertRaises(SystemExit) as context:
                    cli_main(("--verify-save", str(path)))

        self.assertEqual(context.exception.code, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("Save integrity check failed", errors.getvalue())
        self.assertNotIn("Traceback", errors.getvalue())

    def test_verify_save_rejects_simulation_options(self) -> None:
        output, errors = StringIO(), StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            with self.assertRaises(SystemExit) as context:
                cli_main(("--verify-save", "timeline.json", "--days", "1"))

        self.assertEqual(context.exception.code, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertIn(
            "--verify-save cannot use simulation options", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
