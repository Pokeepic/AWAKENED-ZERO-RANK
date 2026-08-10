"""Cross-process reproducibility checks for the public simulation CLI."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_timeline(*, seed: int, hash_seed: int) -> bytes:
    environment = os.environ.copy()
    environment["PYTHONHASHSEED"] = str(hash_seed)
    environment["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "awakened_zero_rank",
            "--days",
            "2",
            "--seed",
            str(seed),
            "--technical-log",
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
    )
    return result.stdout


class CrossProcessReproducibilityTests(unittest.TestCase):
    def test_seeded_timeline_ignores_python_hash_randomization(self) -> None:
        first = run_timeline(seed=42, hash_seed=1)
        second = run_timeline(seed=42, hash_seed=987654)

        self.assertEqual(first, second)
        self.assertTrue(first.startswith(b"AWAKENED ZERO RANK"))


if __name__ == "__main__":
    unittest.main()