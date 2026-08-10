"""Failure-safety tests for deterministic simulation persistence."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from awakened_zero_rank.cli import main as cli_main
from awakened_zero_rank.persistence import load_simulation, save_simulation
from awakened_zero_rank.simulation import Simulation


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


if __name__ == "__main__":
    unittest.main()
