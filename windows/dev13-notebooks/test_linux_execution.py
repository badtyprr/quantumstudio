"""Hosted Linux prerequisite entry point; full lifecycle tests are not yet added."""
import argparse
from pathlib import Path
import sys
import subprocess
import unittest

from linux_lifecycle import _close_control, preflight


class PreflightFailureTests(unittest.TestCase):
    def test_early_exit_pipe_close_preserves_cleanup(self):
        process = subprocess.Popen([sys.executable, "-I", "-c", "pass"],
                                   stdin=subprocess.PIPE, text=True)
        process.wait(timeout=10)
        process.stdin.write("start\n")
        with self.assertRaises(OSError):
            process.stdin.flush()
        report = {"state": "succeeded"}
        _close_control(process, report)
        self.assertEqual(report["state"], "failed")
        self.assertIn("control_close_error", report)
        self.assertTrue(process.stdin.closed)
        self.assertEqual(process.wait(timeout=1), 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PreflightFailureTests))
        return 0 if result.wasSuccessful() else 1
    if args.output is None:
        parser.error("--preflight requires --output")
    report = preflight(args.output)
    print(report["state"])
    if report.get("error"):
        print(report["error"], file=sys.stderr)
    return 0 if report["state"] == "succeeded" else 1


if __name__ == "__main__":
    sys.exit(main())
