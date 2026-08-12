"""Public command-line validation tests."""

from __future__ import annotations

import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from awakened_zero_rank import observer_snapshot
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
        self.assertEqual(snapshot["schema_version"], 4)
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

    def test_snapshot_output_publishes_exact_printed_payload(self) -> None:
        simulation = Simulation(seed=239)
        with TemporaryDirectory() as temporary_directory:
            save_path = Path(temporary_directory) / "timeline.json"
            snapshot_path = Path(temporary_directory) / "snapshot.json"
            save_simulation(simulation, save_path)
            save_before = save_path.read_bytes()
            output = StringIO()

            with redirect_stdout(output):
                cli_main((
                    "--observer-snapshot", str(save_path),
                    "--snapshot-output", str(snapshot_path),
                ))

            self.assertEqual(save_path.read_bytes(), save_before)
            self.assertEqual(
                json.loads(snapshot_path.read_text(encoding="utf-8")),
                json.loads(output.getvalue()),
            )
            original = snapshot_path.read_bytes()
            errors = StringIO()
            with redirect_stdout(StringIO()), redirect_stderr(errors):
                with self.assertRaises(SystemExit) as context:
                    cli_main((
                        "--observer-snapshot", str(save_path),
                        "--snapshot-output", str(snapshot_path),
                    ))
            self.assertEqual(context.exception.code, 2)
            self.assertIn("destination already exists", errors.getvalue())
            self.assertEqual(snapshot_path.read_bytes(), original)

    def test_snapshot_output_requires_observer_snapshot_mode(self) -> None:
        output, errors = StringIO(), StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            with self.assertRaises(SystemExit) as context:
                cli_main(("--snapshot-output", "snapshot.json"))

        self.assertEqual(context.exception.code, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertIn(
            "--snapshot-output requires --observer-snapshot",
            errors.getvalue(),
        )

    def test_verify_observer_snapshot_is_read_only_and_reports_summary(self) -> None:
        snapshot = observer_snapshot(Simulation(seed=211))
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "snapshot.json"
            path.write_text(json.dumps(snapshot), encoding="utf-8")
            original = path.read_bytes()
            output = StringIO()

            with redirect_stdout(output):
                cli_main(("--verify-observer-snapshot", str(path)))

            self.assertEqual(path.read_bytes(), original)
        summary = json.loads(output.getvalue())
        self.assertEqual(summary["path"], str(path))
        self.assertEqual(summary["status"], "valid")
        self.assertEqual(summary["schema_version"], 4)
        self.assertEqual(summary["seed"], 211)
        self.assertEqual(summary["day"], 1)
        self.assertEqual(summary["digest"], snapshot["identity"]["digest"])

    def test_verify_observer_snapshot_rejects_simulation_options(self) -> None:
        output, errors = StringIO(), StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            with self.assertRaises(SystemExit) as context:
                cli_main((
                    "--verify-observer-snapshot", "snapshot.json", "--days", "1",
                ))

        self.assertEqual(context.exception.code, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertIn(
            "--verify-observer-snapshot cannot use simulation options",
            errors.getvalue(),
        )

    def test_verify_observer_snapshot_reports_tampering_cleanly(self) -> None:
        snapshot = observer_snapshot(Simulation(seed=223))
        snapshot["clock"]["day"] += 1
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "snapshot.json"
            path.write_text(json.dumps(snapshot), encoding="utf-8")
            output, errors = StringIO(), StringIO()

            with redirect_stdout(output), redirect_stderr(errors):
                with self.assertRaises(SystemExit) as context:
                    cli_main(("--verify-observer-snapshot", str(path)))

        self.assertEqual(context.exception.code, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("Observer snapshot integrity check failed", errors.getvalue())
        self.assertNotIn("Traceback", errors.getvalue())

    def test_compare_observer_snapshots_is_read_only_and_reports_json(
            self) -> None:
        simulation = Simulation(seed=389)
        left = observer_snapshot(simulation)
        simulation.step()
        right = observer_snapshot(simulation)
        with TemporaryDirectory() as temporary_directory:
            left_path = Path(temporary_directory) / "left.json"
            right_path = Path(temporary_directory) / "right.json"
            left_path.write_text(json.dumps(left), encoding="utf-8")
            right_path.write_text(json.dumps(right), encoding="utf-8")
            left_before = left_path.read_bytes()
            right_before = right_path.read_bytes()
            output = StringIO()

            with redirect_stdout(output):
                cli_main((
                    "--compare-observer-snapshots",
                    str(left_path), str(right_path),
                ))

            self.assertEqual(left_path.read_bytes(), left_before)
            self.assertEqual(right_path.read_bytes(), right_before)
        comparison = json.loads(output.getvalue())
        self.assertEqual(comparison["left_path"], str(left_path))
        self.assertEqual(comparison["right_path"], str(right_path))
        self.assertFalse(comparison["identical"])
        self.assertTrue(comparison["same_seed"])
        self.assertEqual(comparison["clock_delta_slots"], 1)
        self.assertEqual(comparison["clock_relation"], "forward")
        self.assertEqual(comparison["update_mode"], "animate")
        self.assertEqual(comparison["recent_activity_relation"], "append")
        self.assertEqual(
            comparison["appended_event"],
            right["activity"]["recent_events"][-1],
        )
        self.assertIn("clock", comparison["changed_sections"])

    def test_compare_observer_snapshots_rejects_simulation_options(self) -> None:
        output, errors = StringIO(), StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            with self.assertRaises(SystemExit) as context:
                cli_main((
                    "--compare-observer-snapshots", "left.json", "right.json",
                    "--days", "1",
                ))

        self.assertEqual(context.exception.code, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertIn(
            "--compare-observer-snapshots cannot use simulation options",
            errors.getvalue(),
        )

    def test_observer_comparison_equality_gate_accepts_identical(self) -> None:
        snapshot = observer_snapshot(Simulation(seed=401))
        with TemporaryDirectory() as temporary_directory:
            left = Path(temporary_directory) / "left.json"
            right = Path(temporary_directory) / "right.json"
            left.write_text(json.dumps(snapshot), encoding="utf-8")
            right.write_text(json.dumps(snapshot), encoding="utf-8")
            output = StringIO()

            with redirect_stdout(output):
                cli_main((
                    "--compare-observer-snapshots", str(left), str(right),
                    "--require-identical",
                ))

        comparison = json.loads(output.getvalue())
        self.assertTrue(comparison["identical"])
        self.assertEqual(comparison["clock_delta_slots"], 0)
        self.assertEqual(comparison["recent_activity_relation"], "unchanged")
        self.assertIsNone(comparison["appended_event"])
        self.assertEqual(comparison["changed_sections"], [])

    def test_observer_comparison_equality_gate_reports_drift(self) -> None:
        simulation = Simulation(seed=409)
        left_snapshot = observer_snapshot(simulation)
        simulation.step()
        right_snapshot = observer_snapshot(simulation)
        with TemporaryDirectory() as temporary_directory:
            left = Path(temporary_directory) / "left.json"
            right = Path(temporary_directory) / "right.json"
            left.write_text(json.dumps(left_snapshot), encoding="utf-8")
            right.write_text(json.dumps(right_snapshot), encoding="utf-8")
            output = StringIO()

            with (
                    redirect_stdout(output),
                    self.assertRaises(SystemExit) as context):
                cli_main((
                    "--compare-observer-snapshots", str(left), str(right),
                    "--require-identical",
                ))

        self.assertEqual(context.exception.code, 1)
        comparison = json.loads(output.getvalue())
        self.assertFalse(comparison["identical"])
        self.assertTrue(comparison["same_seed"])
        self.assertEqual(comparison["clock_delta_slots"], 1)
        self.assertEqual(comparison["clock_relation"], "forward")
        self.assertEqual(comparison["update_mode"], "animate")
        self.assertEqual(comparison["recent_activity_relation"], "append")
        self.assertEqual(
            comparison["appended_event"],
            right_snapshot["activity"]["recent_events"][-1],
        )
        self.assertIn("clock", comparison["changed_sections"])

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
