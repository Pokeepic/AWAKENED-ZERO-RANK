"""Public command-line validation tests."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import unittest

from awakened_zero_rank.cli import main as cli_main


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


if __name__ == "__main__":
    unittest.main()
