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

    def test_physical_wire_in_nested_include(self):
        main = self.put("main.qasm", 'OPENQASM 3.0;\ninclude "stdgates.inc";\ninclude "nested κ/entry.inc";\nbit result;\nresult = measure $3;')
        self.put("nested κ/gates.inc", "gate flip q { x q; }")
        entry = 'include "gates.inc";\nflip '
        for command in COMMANDS:
            args = ["--classical", "--source-file", str(main)]
            self.put("nested κ/entry.inc", entry + "$3;")
            circuit = self.run_import(command, args)["Circuit"]
            self.assertEqual(circuit["Qubits"], 4)
            self.assertEqual(circuit["Steps"], [
                {"Kind": "Gate", "Expression": "X", "Wires": [3]},
                {"Kind": "Measure", "Wires": [3], "ClassicalBit": 0},
            ])
            self.put("nested κ/entry.inc", entry + "$25;")
            message = self.run_import(command, args, success=False)
            self.assertIn("nested κ/entry.inc:2:", message)
            self.assertIn("Physical wire indices must be between 0 and 24", message)

    def test_dependency_parser_diagnostic(self):
        main = self.put("main.qasm", 'OPENQASM 3; include "nested κ/helper.inc"; qubit q;')
        self.put("nested κ/helper.inc", '// comment\r\ngate bad a { x a }\r\n')
        for command in COMMANDS:
            message = self.run_import(command, ["--source-file", str(main)], success=False)
            self.assertIn("nested κ/helper.inc:2:18:", message)
            self.assertIn("Unexpected token", message)

    def test_dependency_lowering_diagnostics(self):
        cases = [
            ('qubit[26] q;', 'Classical circuits support', 'qubit'),
            ('qubit[25] q; qubit extra;', 'Classical circuits support', 'qubit extra'),
            ('bit[64] b; bit extra;', 'Classical circuits support', 'bit extra'),
            ('int n=1; switch(n) { case 1 { } case 1 { } }',
             'Duplicate switch case value: 1', '1 { } }'),
            ('int n=1; int n=2;', 'Duplicate declaration in one scope: n', 'int n=2'),
            ('bit[2] b; if(b) { }', 'Whole-register truth conditions', 'if(b)'),
            ('bit[2] b; if(b == 4) { }', 'Condition constant is outside its register range.', 'if(b'),
            ('bit[2] b; switch(b) { case 1 { } }',
             'Switch targets require an integer expression;', 'switch(b)'),
            ('bit b; if(b) { bit c; }',
             'Register declarations inside runtime branches are not supported.', 'bit c'),
            ('int n; int k; switch(n) { case k { } }',
             'Switch case labels must be integer constants.', 'k {'),
            ('int n; switch(n) { case 1 { qubit q; } }',
             'Global declarations are not allowed in switch cases.', 'qubit q'),
            ('bit b; if(b) { bit b; }',
             'Non-integer shadowing is not yet supported by the importer.', 'bit b; }'),
            ('float t; if(t) { }', 'A bit expression requires an explicit cast or comparison.', 'if(t)'),
            ('float t; while(t) { }', 'A bit expression requires an explicit cast or comparison.', 'while(t)'),
            ('int n; if(bit[2](n)) { }', 'Integer-to-bit casts require equal explicit widths.', 'if(bit'),
            ('int n; while(bit[2](n)) { }', 'Integer-to-bit casts require equal explicit widths.', 'while(bit'),
            ('int n; for int i in [:n] { }', 'For-loop ranges require both endpoints.', 'for int'),
            ('bit[2] a; bit[3] b; if(a==b) { }', 'Classical operands have incompatible widths.', 'if(a'),
        ]
        main = self.put('main.qasm', 'OPENQASM 3; include "nested κ/helper.inc";')
        for source, detail, token in cases:
            for command in COMMANDS:
                for module in (False, True):
                    with self.subTest(source=source, command=command, module=module):
                        prefix = 'OPENQASM 3;\r\n' if module else '// dependency\r\n'
                        self.put('nested κ/helper.inc', prefix + '  ' + source + '\r\n')
                        args = ['--classical', '--source-file', str(main)]
                        if module:
                            args.append('--module-headers')
                        message = self.run_import(command, args, success=False)
                        self.assertIn('nested κ/helper.inc:2:' + str(source.index(token) + 3) + ':', message)
                        self.assertIn(detail, message)
                        plain = self.run_import(command, ['--classical'],
                                                'OPENQASM 3; ' + source, success=False)
                        self.assertIn(detail, plain)
                        self.assertNotIn('helper.inc', plain)

    def test_emission_dependency_diagnostics(self):
        cases = [
            ('qubit[25] q; qubit extra;', 'qubit extra', False, 'The circuit editor currently supports'),
            ('qubit q; for int i in [0:512] { x q; }', 'x q', False, 'The compiled circuit exceeds'),
            ('qubit q; for int i in [0:512] { x q; }', 'x q', True, 'Classical circuits support at most 512'),
            ('qubit[3] q; ctrl(3) @ gphase(pi) q[0],q[1],q[2];', 'ctrl(3)', False, 'Controlled global phase'),
            ('qubit q; delay[1ns] q;', 'delay', False, 'The editor cannot represent DelayInstruction.'),
            ('qubit q; delay[1ns] q;', 'delay', True, 'Classical circuit import cannot yet represent DelayInstruction.'),
            ('int n; for bool i in [0:n] { }', 'for bool', True, 'Runtime for loops currently require'),
        ]
        main = self.put('main.qasm', 'OPENQASM 3; include "stdgates.inc"; include "nested κ/body.inc";')
        for body, token, classical, detail in cases:
            for command in COMMANDS:
                for module in (False, True):
                    with self.subTest(body=body, classical=classical, command=command, module=module):
                        prefix = 'OPENQASM 3;\r\n' if module else '// dependency\r\n'
                        self.put('nested κ/body.inc', prefix + '  ' + body)
                        args = ['--source-file', str(main)]
                        if classical:
                            args.append('--classical')
                        if module:
                            args.append('--module-headers')
                        message = self.run_import(command, args, success=False)
                        self.assertIn(f'nested κ/body.inc:2:{body.index(token) + 3}: {detail}', message)

    def test_declaration_range_scope_locations(self):
        cases = [
            ('int ' + 'i' * 65 + ';', True, 0, 'Integer variable names must fit 64 UTF-16 code units.'),
            ('int n; for int ' + 'i' * 65 + ' in [0:n] { }', True, 7, 'Integer variable names must fit 64 UTF-16 code units.'),
            ('qubit[3] q; x q[0:0:2];', False, 12, 'Register ranges require integer bounds and a nonzero integer step.'),
            ('qubit[3] q; x q[0:0:2];', True, 12, 'Register ranges require integer bounds and a nonzero integer step.'),
            ('{' * 33 + 'int i;' + '}' * 33, True, 32, 'Classical scopes exceed 32 levels.'),
        ]
        main = self.put('main.qasm', 'OPENQASM 3; include "stdgates.inc"; include "nested κ/limits.inc";')
        for body, classical, offset, detail in cases:
            for command in COMMANDS:
                for module in (False, True):
                    with self.subTest(body=body, command=command, module=module, classical=classical):
                        prefix = 'OPENQASM 3;\r\n' if module else '// dependency\r\n'
                        self.put('nested κ/limits.inc', prefix + '  ' + body)
                        args = ['--source-file', str(main)]
                        if classical:
                            args.append('--classical')
                        if module:
                            args.append('--module-headers')
                        message = self.run_import(command, args, success=False)
                        self.assertEqual(message.strip(), f'nested κ/limits.inc:2:{offset + 3}: {detail}')

    def test_gate_arithmetic_locations(self):
        main = self.put('main.qasm', 'OPENQASM 3; include "stdgates.inc"; include "nested κ/angles.inc";')
        for body in ('qubit q; rx(1/0) q;', 'gate g a { rx(1/0) a; } qubit q; g q;'):
            self.put('nested κ/angles.inc', 'OPENQASM 3;\r\n  ' + body)
            for command in COMMANDS:
                for classical in (False, True):
                    with self.subTest(body=body, command=command, classical=classical):
                        args = ['--source-file', str(main), '--module-headers']
                        if classical:
                            args.append('--classical')
                        message = self.run_import(command, args, success=False)
                        self.assertEqual(message.strip(), f'nested κ/angles.inc:2:{body.index("rx(") + 3}: division by zero')

    def test_numerical_loop_transfer_file_import(self):
        cases = [
            ('while(true) { x q; break; h q; }', ['X']),
            ('int i=0; while(i<3) { i+=1; x q; continue; h q; }', ['X'] * 3),
            ('for int i in [0:2] { x q; break; h q; }', ['X']),
            ('for int i in [0:2] { x q; continue; h q; }', ['X'] * 3),
            ('for int i in [0:1] { for int j in [0:2] { x q; break; } h q; }', ['X', 'H'] * 2),
            ('int n=2; while(n>0) { n-=1; int n=0; x q; continue; }', ['X'] * 2),
        ]
        main = self.put('main.qasm', 'OPENQASM 3; include "stdgates.inc"; include "nested κ/loops.inc";')
        for body, gates in cases:
            self.put('nested κ/loops.inc', 'OPENQASM 3;\r\nqubit q; ' + body)
            for command in COMMANDS:
                with self.subTest(body=body, command=command):
                    result = self.run_import(command, ['--source-file', str(main), '--module-headers'])
                    self.assertEqual(result['Circuit'], {'Version': 1, 'Qubits': 1, 'Steps': [
                        {'Gate': gate, 'Angle': '', 'Wires': [0]} for gate in gates]})

    def test_numerical_transfer_scope_rejections(self):
        cases = [
            ('for int i in [0:0] { int n=0; if(false) { break; } int n=1; x q; }', 'int n=1', 'n'),
            ('int k=0; while(k<1) { k+=1; int n=0; if(false) { continue; } int n=1; x q; }', 'int n=1', 'n'),
            ('for int i in [0:0] { if(false) { break; } int i=1; x q; }', 'int i=1', 'i'),
        ]
        main = self.put('main.qasm', 'OPENQASM 3; qubit q; include "scope.inc";')
        for body, token, name in cases:
            self.put('scope.inc', '// original scope\n  ' + body)
            for command in COMMANDS:
                with self.subTest(body=body, command=command):
                    message = self.run_import(command, ['--source-file', str(main)], success=False)
                    self.assertEqual(message.strip(),
                                     f"scope.inc:2:{body.index(token) + 3}: Re-declaration of variable '{name}'")

    def test_validation_origin_file_locations(self):
        cases = [('qubit q; int n; for int i in [true:n] { x q; }',
          True,
          'for int',
          'For-loop range bounds and step require integers; cast Boolean values explicitly.'),
         ('def stop() -> int { return 2; } for int i in [true:stop()] { }',
          True,
          'true',
          'For-loop range bounds and step require integers; cast Boolean values explicitly.'),
         ('def start() -> bool { return true; } int n; for int i in [start():n] { }',
          True,
          'start():n',
          'For-loop range bounds and step require integers; cast Boolean values explicitly.'),
         ('def stop() -> int { return 2; } for int i in [0:true:stop()] { }',
          True,
          'true',
          'For-loop range bounds and step require integers; cast Boolean values explicitly.'),
         ('qubit q; int n; while(n) { int[65] k; }', True, 'int[65]', 'Integer width must be 1–64, or omitted.'),
         ('qubit q; int n; int[n] k;', True, 'int[n]', 'Integer widths must be compile-time constants.'),
         ('qubit q; int n; switch(n) { default { x q; } }',
          True,
          'switch',
          'Switch statements require at least one case.'),
         ('qubit q; rx(sqrt(-1)) q;', False, 'rx(', 'Gate parameters must be finite.'),
         ('qubit q; rx(sqrt(-1)) q;', True, 'rx(', 'Gate parameters must be finite.')]
        main = self.put('main.qasm', 'OPENQASM 3; include "stdgates.inc"; include "nested κ/validation.inc";')
        for body, classical, token, detail in cases:
            self.put('nested κ/validation.inc', 'OPENQASM 3;\r\n  ' + body)
            for command in COMMANDS:
                with self.subTest(body=body, command=command, classical=classical):
                    args = ['--source-file', str(main), '--module-headers']
                    if classical:
                        args.append('--classical')
                    message = self.run_import(command, args, success=False)
                    self.assertIn(f'nested κ/validation.inc:2:{body.index(token) + 3}: {detail}', message)

    def test_timed_gate_rejection(self):
        cases = [
            ('qubit q; x[1ns] q;', 'x['),
            ('gate g a { x[1ns] a; } qubit q; g q;', 'x['),
            ('def f(qubit a) { x[1ns] a; } qubit q; f(q);', 'x['),
            ('qubit q; gphase(pi)[1ns];', 'gphase'),
            ('qubit q; ctrl @ gphase(pi)[1ns] q;', 'ctrl'),
        ]
        main = self.put('main.qasm', 'OPENQASM 3; include "stdgates.inc"; include "nested κ/timed.inc";')
        for body, token in cases:
            self.put('nested κ/timed.inc', 'OPENQASM 3;\r\n  ' + body)
            for command in COMMANDS:
                for classical in (False, True):
                    with self.subTest(body=body, command=command, classical=classical):
                        mode = ['--classical'] if classical else []
                        message = self.run_import(command, ['--source-file', str(main), '--module-headers', *mode], success=False)
                        self.assertEqual(message.strip(),
                                         f'nested κ/timed.inc:2:{body.index(token) + 3}: Timed gates are not supported.')

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

    def test_lowering_and_assignment_emission_locations(self):
        cases = [
            ("qubit q;\nfor int i in [0:0:2] { x q; }", 4,
             "For-loop range step must not be zero.", (False, True)),
            ("bool b;\nb += true;", 4,
             "Boolean compound assignments are not yet supported.", (True,)),
            ("int n = 1;\nbit[2] b;\nb = bit[2](n);", 5,
             "Integer-to-bit casts require equal explicit widths.", (True,)),
            ("int n = 1;\nbit[2] b = bit[2](n);", 4,
             "Integer-to-bit casts require equal explicit widths.", (True,)),
        ]
        for module in (False, True):
            prologue = 'OPENQASM 3;\ninclude "stdgates.inc";\n' if module else '// original\n// dependency\n'
            main = self.put("main.qasm", 'OPENQASM 3; include "stdgates.inc"; include "sub dir/wrapper.inc";')
            self.put("sub dir/wrapper.inc", '// nested\ninclude "bad \u03ba.inc";')
            for body, line, expected, modes in cases:
                self.put("sub dir/bad \u03ba.inc", prologue + body.rsplit("\n", 1)[0] + "\n  " + body.rsplit("\n", 1)[1])
                for command in COMMANDS:
                    for classical in modes:
                        with self.subTest(module=module, body=body, command=command, classical=classical):
                            mode = ["--classical"] if classical else []
                            args = ["--source-file", str(main), *mode] + (["--module-headers"] if module else [])
                            message = self.run_import(command, args, success=False)
                            self.assertEqual(message.strip(), f"sub dir/bad \u03ba.inc:{line}:3: {expected}")
                            # The diagnostic text remains identical for paste-only input.
                            message = self.run_import(command, mode, source='OPENQASM 3;\n' + body, success=False)
                            self.assertEqual(message.strip(), expected)

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
