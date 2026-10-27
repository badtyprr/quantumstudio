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

    def test_dependency_parser_diagnostic(self):
        main = self.put("main.qasm", 'OPENQASM 3; include "nested κ/helper.inc"; qubit q;')
        self.put("nested κ/helper.inc", '// comment\r\ngate bad a { x a }\r\n')
        for command in COMMANDS:
            message = self.run_import(command, ["--source-file", str(main)], success=False)
            self.assertIn("nested κ/helper.inc:2:18:", message)
            self.assertIn("Unexpected token", message)

    def test_entry_suffix_parser_diagnostic(self):
        text = 'OPENQASM 3; include "helper.inc"; qubit q x q;'
        main = self.put("main.qasm", text)
        self.put("helper.inc", "// several\n// inserted\n// lines\n")
        for command in COMMANDS:
            message = self.run_import(command, ["--source-file", str(main)], success=False)
            self.assertIn(f"main.qasm:1:{text.index('x q') + 1}:", message)

    def test_dependency_semantic_diagnostic(self):
        main = self.put("main.qasm", 'OPENQASM 3; include "helper.inc"; g q;')
        self.put("helper.inc", "// original\nqubit q;\ngate g a { undefined_gate a; }\n")
        for command in COMMANDS:
            for mode in ([], ["--classical"]):
                message = self.run_import(command, ["--source-file", str(main), *mode], success=False)
                self.assertIn("helper.inc:3:", message)
                self.assertIn("Unsupported / undeclared QASM operation", message)
                self.assertNotIn("Error at line", message)

    def test_module_header_ast_diagnostic(self):
        main = self.put("main.qasm", 'OPENQASM 3; include "stdgates.inc"; include "helper.inc";')
        self.put("helper.inc", 'OPENQASM 3;\r\ninclude "stdgates.inc";\r\nif(true) { qubit q; }\r\n')
        for command in COMMANDS:
            message = self.run_import(command, ["--source-file", str(main), "--module-headers"], success=False)
            self.assertIn("helper.inc:3:12:", message)
            self.assertIn("qubit declarations must be global", message)

    def test_adapter_declaration_location_and_unchanged_stdin_message(self):
        dependency = "// original configuration\nduration elapsed = 1ns;\n"
        main = self.put("main.qasm", 'OPENQASM 3; include "settings.inc"; qubit q;')
        self.put("settings.inc", dependency)
        expected = "Classical circuit import supports bit registers, integer/Boolean, float32/64, angle variables and compile-time arrays; other classical declarations are not yet supported."
        for command in COMMANDS:
            message = self.run_import(command, ["--source-file", str(main), "--classical"], success=False)
            self.assertEqual(message.strip(), "settings.inc:2:1: " + expected)
            message = self.run_import(command, ["--classical"], source="OPENQASM 3;\n" + dependency + "qubit q;", success=False)
            self.assertEqual(message.strip(), expected)

    def test_adapter_runtime_gate_location_after_module_adaptation(self):
        main = self.put("main.qasm", 'OPENQASM 3; include "stdgates.inc"; include "parameters.inc";')
        self.put("parameters.inc", 'OPENQASM 3;\ninclude "stdgates.inc";\nbit b;\nqubit q;\nrx(b) q;')
        for command in COMMANDS:
            message = self.run_import(command, ["--source-file", str(main), "--module-headers", "--classical"], success=False)
            self.assertEqual(message.strip(), "parameters.inc:5:1: Cast bit operands explicitly before integer arithmetic.")

    def test_runtime_angle_cast_location(self):
        main = self.put("main.qasm", 'OPENQASM 3; include "stdgates.inc"; include "parameters.inc";')
        self.put("parameters.inc", 'int n = 1;\nqubit q;\nrx(float[16](n)) q;')
        for command in COMMANDS:
            message = self.run_import(command, ["--source-file", str(main), "--classical"], success=False)
            self.assertEqual(message.strip(), "parameters.inc:3:1: Use float32/64 or angle widths 1–64.")

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
                    classical = self.run_import(command, ["--source-file", str(main), "--module-headers", "--classical"])
                    self.assertEqual(classical["Circuit"]["Steps"],
                                     [{"Kind": "Gate", "Expression": step["Gate"], "Wires": step["Wires"]}
                                      for step in result["Circuit"]["Steps"]])
                    self.assertEqual(classical["Circuit"]["Qubits"], 4)
                    self.assertEqual(classical["Source"], result["Source"])
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

    def test_explicit_saved_source_check(self):
        dependency = self.put("module.inc", "gate g q { x q; }")
        main = self.put("main.qasm", 'OPENQASM 3; include "module.inc"; qubit q; g q;')
        for command in COMMANDS:
            dependency.write_text("gate g q { x q; }", encoding="utf-8")
            snapshot = self.run_import(command, ["--source-file", str(main)])["Source"]
            snapshot["Root"] = "Z:/saved/root/is/not/permission"
            source = json.dumps(snapshot)
            args = ["--check-source", "--source-root", str(self.root)]
            self.assertTrue(self.run_import(command, args, source)["Unchanged"])
            dependency.write_text("gate g q { h q; }", encoding="utf-8")
            result = self.run_import(command, args, source)
            self.assertFalse(result["Unchanged"])
            self.assertEqual(result["Files"][1]["Status"], "changed")
            dependency.unlink()
            self.assertEqual(self.run_import(command, args, source)["Files"][1]["Status"], "missing")
            for invalid in (["--check-source"], ["--check-source", "--source-root", ""], [*args, "--classical"],
                            [*args, "--source-file", str(main)]):
                self.run_import(command, invalid, source, success=False)

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

    def test_published_u_file_contract(self):
        text = "OPENQASM 3; qubit q; U(pi/2,pi/3,pi/7) q;"
        main = self.put("main.qasm", text)
        for command in COMMANDS:
            result = self.run_import(command, ["--source-file", str(main), "--published-u"])
            self.assertEqual(result["Circuit"], self.run_import(command, ["--published-u"], text))
            self.assertNotEqual(result["Circuit"], self.run_import(command, source=text))

    def test_module_mode_keeps_custom_duplicate_errors(self):
        self.put("module.inc", "OPENQASM 3.0; gate g q { x q; }")
        main = self.put("main.qasm", 'OPENQASM 3; include "module.inc"; qubit q; g q;')
        for command in COMMANDS:
            result = self.run_import(command, ["--source-file", str(main), "--module-headers"])
            self.assertEqual(result["Circuit"]["Steps"][0]["Gate"], "X")
        self.put("main.qasm", 'OPENQASM 3; include "module.inc"; include "module.inc"; qubit q; g q;')
        for command in COMMANDS:
            self.run_import(command, ["--source-file", str(main), "--module-headers"], success=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen")
    options = parser.parse_args()
    if options.frozen:
        COMMANDS.append([str(Path(options.frozen).resolve())])
    unittest.main(argv=[sys.argv[0]])
