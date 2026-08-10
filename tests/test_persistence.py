"""Failure-safety tests for deterministic simulation persistence."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

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

if __name__ == "__main__":
    unittest.main()
