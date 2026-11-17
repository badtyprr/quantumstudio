#!/usr/bin/env python3
"""Flat arithmetic within the notation budget must not overflow the worker stack."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

WORKER = Path(sys.argv.pop(1) if len(sys.argv) > 1 else
              "quantum-worker" + (".exe" if os.name == "nt" else "")).resolve()


class FlatArithmeticTests(unittest.TestCase):
    def request(self, expression):
        return subprocess.run([str(WORKER), "--json"], input=expression.encode("utf-8"),
                              capture_output=True, timeout=30)

    def value(self, expression, expected):
        result = self.request(expression)
        self.assertEqual(result.returncode, 0, (result.returncode, result.stderr))
        self.assertEqual(result.stderr, b"")
        value = json.loads(result.stdout)
        self.assertFalse(value["approximate"])
        self.assertEqual(value["copy_text"].replace("−", "-"), str(expected))

    def test_flat_quantum_chains_at_budget(self):
        for operator, expected in [("+", 512), ("-", -510), ("*", 1)]:
            with self.subTest(operator=operator):
                self.value("quantum:" + operator.join(["1"] * 512), expected)

    def test_mixed_subtraction_preserves_order(self):
        # Left to right: 1-1+1-1+...-1 = 0. Reassociation can change this result.
        expression = "1" + "".join("-1" if i % 2 else "+1" for i in range(1, 512))
        self.value("quantum:" + expression, 0)

    def test_over_budget_remains_rejected(self):
        result = self.request("quantum:" + "+".join(["1"] * 513))
        self.assertEqual(result.returncode, 2, (result.returncode, result.stderr))
        self.assertIn(b"complexity limit", result.stderr)
        self.assertEqual(result.stdout, b"")

    def test_ordinary_arithmetic_control(self):
        self.value("+".join(["1"] * 512), 512)


if __name__ == "__main__":
    unittest.main()
