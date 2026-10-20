"""Check source-aware compiler protocol and unchanged generated QB-004 modules."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
COMMANDS = [[sys.executable, str(HERE / "qasm-import.py")]]


class FileImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="qasm source ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="")
        return path

    def run_import(self, command, args=(), source="", success=True):
        result = subprocess.run([*command, *args], input=source.encode("utf-8"),
                                capture_output=True, timeout=30)
        self.assertEqual(result.returncode == 0, success, result.stderr.decode("utf-8", errors="replace"))
        return json.loads(result.stdout) if success else result.stderr.decode("utf-8")

    def test_generated_qb004_modules(self):
        for name, count in [("oracle", 3), ("bernvaz", 10)]:
            module = (HERE / "fixtures/qb004" / (name + ".qasm")).read_text(encoding="utf-8")
            self.put(name + ".qasm", module)
            header = 'OPENQASM 3.0; include "stdgates.inc";'
            call = f"qubit[3] q; qubit[1] a; {name}(q,a);"
            main = self.put("main.qasm", header + f'include "{name}.qasm";' + call)
            # The fixture's standalone prologue repeats the version and standard
            # library already declared by the importing program.
            inline = header + module[module.index("def "):] + call
            for command in COMMANDS:
                with self.subTest(module=name, command=command):
                    result = self.run_import(command, ["--source-file", str(main), "--module-headers"])
                    self.assertEqual(result["Circuit"], self.run_import(command, source=inline))
                    self.assertEqual(len(result["Circuit"]["Steps"]), count)
                    self.assertTrue(result["Source"]["ModuleHeaders"])
                    self.assertEqual(len(result["Source"]["Files"]), 2)
                    for file in result["Source"]["Files"]:
                        raw = (b"\xef\xbb\xbf" if file["Bom"] else b"") + file["Text"].encode("utf-8")
                        self.assertEqual(hashlib.sha256(raw).hexdigest(), file["Sha256"])
                    self.run_import(command, ["--source-file", str(main)], success=False)

    def test_stdin_remains_context_free(self):
        for command in COMMANDS:
            result = self.run_import(command, source="OPENQASM 3; qubit q; x q;")
            self.assertEqual(result["Steps"][0]["Gate"], "X")
            self.assertNotIn("Source", result)
            self.assertIn("includes", self.run_import(command, source='OPENQASM 3; include "local.inc"; qubit q;', success=False))

    def test_explicit_root_and_utf8_snapshot(self):
        self.put("λ.inc", "\ufeffgate g q { x q; }")
        main = self.put("sub dir/main.qasm", 'OPENQASM 3; include "../λ.inc"; qubit q; g q;')
        for command in COMMANDS:
            self.assertIn("outside", self.run_import(command, ["--source-file", str(main)], success=False))
            result = self.run_import(command, ["--source-file", str(main), "--source-root", str(self.root)])
            self.assertEqual(result["Circuit"]["Steps"][0]["Gate"], "X")
            module = next(f for f in result["Source"]["Files"] if f["Name"] == "λ.inc")
            self.assertTrue(module["Bom"])
            self.assertEqual(result["Source"]["Entry"], "sub dir/main.qasm")

    def test_module_version_checks(self):
        for root_header, child_header in [
            ("OPENQASM 3;", "OPENQASM 2.0;"),
            ("", "OPENQASM 3;"),
            ("OPENQASM 3.1;", "OPENQASM 3.10;"),
            ("OPENQASM 3;", "OPENQASM 3; OPENQASM 3;"),
        ]:
            main = self.put("main.qasm", root_header + 'include "module.inc"; qubit q;')
            self.put("module.inc", child_header)
            for command in COMMANDS:
                self.assertIn("version", self.run_import(command, ["--source-file", str(main), "--module-headers"], success=False))

    def test_option_errors(self):
        for args in [
            ["--source-file"], ["--source-root", str(self.root)], ["--module-headers"],
            ["--classical", "--classical"], ["--source-file", "x", "--source-file", "y"],
            ["--unknown"], ["--source-file", "--classical"],
        ]:
            for command in COMMANDS:
                with self.subTest(args=args):
                    self.run_import(command, args, success=False)

    def test_classical_file_contract(self):
        main = self.put("main.qasm", 'OPENQASM 3; include "stdgates.inc"; qubit q; bit c; h q; c=measure q;')
        for command in COMMANDS:
            result = self.run_import(command, ["--source-file", str(main), "--classical"])
            self.assertEqual(result["Circuit"], self.run_import(command, ["--classical"], main.read_text()))
            self.assertIn("Registers", result["Circuit"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen")
    options = parser.parse_args()
    if options.frozen:
        COMMANDS.append([str(Path(options.frozen).resolve())])
    unittest.main(argv=[sys.argv[0]])
