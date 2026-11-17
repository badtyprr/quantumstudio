"""Source dependency boundaries and deterministic expansion, without GUI or cloud."""
from pathlib import Path
import copy
import importlib.util
import logging
import tempfile
import unittest
from pyqasm import ValidationError

from qasm_source_bundle import capture_source, check_snapshot, SourceError, MAX_BYTES, MAX_DEPTH, MAX_FILES
from qasm_source_diagnostics import compile_source, error_at, copy_span, diagnostic_context


class SourceBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="")
        return path

    def test_control_flow_dependency_diagnostics(self):
        spec = importlib.util.spec_from_file_location("qasm_import", Path(__file__).with_name("qasm-import.py"))
        compiler = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(compiler)
        cases = [
            ('bit[2] b; if(b == 4) { }', 'if(b',
             'Condition constant is outside its register range.'),
            ('bit[2] b; switch(b) { case 1 { } }', 'switch(b)',
             'Switch targets require an integer expression; use an explicit integer cast.'),
            ('bit b; if(b) { bit c; }', 'bit c',
             'Register declarations inside runtime branches are not supported.'),
            ('int n; int k; switch(n) { case k { } }', 'k {',
             'Switch case labels must be integer constants.'),
            ('int n; switch(n) { case 1 { qubit q; } }', 'qubit q',
             'Global declarations are not allowed in switch cases.'),
            ('bit b; if(b) { bit b; }', 'bit b; }',
             'Non-integer shadowing is not yet supported by the importer.'),
            ('float t; if(t) { }', 'if(t)',
             'A bit expression requires an explicit cast or comparison.'),
            ('float t; while(t) { }', 'while(t)',
             'A bit expression requires an explicit cast or comparison.'),
            ('int n; if(bit[2](n)) { }', 'if(bit',
             'Integer-to-bit casts require equal explicit widths.'),
            ('int n; while(bit[2](n)) { }', 'while(bit',
             'Integer-to-bit casts require equal explicit widths.'),
            ('int n; for int i in [:n] { }', 'for int',
             'For-loop ranges require both endpoints.'),
            ('bit[2] a; bit[3] b; if(a==b) { }', 'if(a',
             'Classical operands have incompatible widths.'),
        ]
        main = self.put('main.qasm', 'OPENQASM 3; include "sub dir/wrapper.inc";')
        self.put('sub dir/wrapper.inc', 'include "bad κ.inc";')
        for body, token, message in cases:
            for module in (False, True):
                with self.subTest(body=body, module=module):
                    prefix = 'OPENQASM 3;\r\n' if module else '// dependency\r\n'
                    self.put('sub dir/bad κ.inc', prefix + '  ' + body)
                    bundle = capture_source(main, module_headers=module)
                    with self.assertRaises(SourceError) as caught:
                        compile_source(bundle, compiler.convert, classical=True)
                    self.assertEqual(str(caught.exception),
                                     f'sub dir/bad κ.inc:2:{body.index(token) + 3}: {message}')
            with self.assertRaises(ValueError) as caught:
                compiler.convert('OPENQASM 3; ' + body, classical=True)
            self.assertEqual(str(caught.exception), message)

    def test_emission_dependency_diagnostics(self):
        spec = importlib.util.spec_from_file_location("qasm_import", Path(__file__).with_name("qasm-import.py"))
        compiler = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(compiler)
        cases = [
            ('qubit[26] q;', 'qubit', False, 'The circuit editor currently supports 1–25 qubits.'),
            ('qubit[25] q; qubit extra;', 'qubit extra', False,
             'The circuit editor currently supports 1–25 qubits.'),
            ('qubit q; for int i in [0:512] { x q; }', 'x q', False,
             'The compiled circuit exceeds the editor limit of 512 steps.'),
            ('qubit q; for int i in [0:512] { x q; }', 'x q', True,
             'Classical circuits support at most 512 total operations.'),
            ('qubit[3] q; ctrl(3) @ gphase(pi) q[0],q[1],q[2];', 'ctrl(3)', False,
             'Controlled global phase currently supports one or two controls.'),
            ('qubit[3] q; ctrl(3) @ gphase(pi) q[0],q[1],q[2];', 'ctrl(3)', True,
             'Controlled global phase currently supports one or two controls.'),
            ('qubit q; delay[1ns] q;', 'delay', False,
             'The editor cannot represent DelayInstruction. Runtime classical feedback, timing and pulse programs require a richer execution model.'),
            ('qubit q; delay[1ns] q;', 'delay', True,
             'Classical circuit import cannot yet represent DelayInstruction.'),
            ('int n; for bool i in [0:n] { }', 'for bool', True,
             'Runtime for loops currently require an integer binding and a range.'),
        ]
        main = self.put('main.qasm', 'OPENQASM 3; include "stdgates.inc"; include "nested κ/body.inc";')
        for body, token, classical, message in cases:
            for module in (False, True):
                with self.subTest(body=body, classical=classical, module=module):
                    prefix = 'OPENQASM 3;\r\n' if module else '// dependency\r\n'
                    self.put('nested κ/body.inc', prefix + '  ' + body)
                    with self.assertRaises(SourceError) as caught:
                        compile_source(capture_source(main, module_headers=module), compiler.convert, classical=classical)
                    self.assertEqual(str(caught.exception),
                                     f'nested κ/body.inc:2:{body.index(token) + 3}: {message}')
            with self.assertRaises(ValueError) as caught:
                compiler.convert('OPENQASM 3; include "stdgates.inc"; ' + body, classical=classical)
            self.assertEqual(str(caught.exception), message)

    def test_expanded_gate_provenance_and_limit_boundary(self):
        spec = importlib.util.spec_from_file_location("qasm_import", Path(__file__).with_name("qasm-import.py"))
        compiler = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(compiler)
        self.put('defs.inc', 'gate inner a {\n    x a;\n}\ngate outer a {\n  inner a;\n}')
        prefix = 'OPENQASM 3; include "stdgates.inc"; include "defs.inc"; qubit q; '
        for classical, message in ((False, 'The compiled circuit exceeds the editor limit of 512 steps.'),
                                   (True, 'Classical circuits support at most 512 total operations.')):
            with self.subTest(classical=classical):
                main = self.put('main.qasm', prefix + 'for int i in [0:511] { outer q; }')
                result = compile_source(capture_source(main), compiler.convert, classical=classical)
                self.assertEqual(len(result['Steps']), 512)
                self.put('main.qasm', prefix + 'for int i in [0:512] { outer q; }')
                with self.assertRaises(SourceError) as caught:
                    compile_source(capture_source(main), compiler.convert, classical=classical)
                self.assertEqual(str(caught.exception), 'defs.inc:2:5: ' + message)
        main = self.put('main.qasm', 'OPENQASM 3;')
        with self.assertRaises(SourceError) as caught:
            compile_source(capture_source(main), compiler.convert)
        self.assertEqual(str(caught.exception), 'main.qasm: The circuit editor currently supports 1–25 qubits.')

    def test_timed_gates_are_not_silently_converted(self):
        spec = importlib.util.spec_from_file_location("qasm_import", Path(__file__).with_name("qasm-import.py"))
        compiler = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(compiler)
        cases = [
            'qubit q; x[1ns] q;',
            'qubit q; x[0ns] q;',
            'gate g a { x[1ns] a; } qubit q; g q;',
            'def f(qubit a) { x[1ns] a; } qubit q; f(q);',
        ]
        main = self.put('main.qasm', 'OPENQASM 3; include "stdgates.inc"; include "nested κ/timed.inc";')
        for body in cases:
            for classical in (False, True):
                for module in (False, True):
                    with self.subTest(body=body, classical=classical, module=module):
                        prefix = 'OPENQASM 3;\r\n' if module else '// dependency\r\n'
                        self.put('nested κ/timed.inc', prefix + '  ' + body)
                        with self.assertRaises(SourceError) as caught:
                            compile_source(capture_source(main, module_headers=module), compiler.convert, classical=classical)
                        self.assertEqual(str(caught.exception),
                                         f'nested κ/timed.inc:2:{body.index("x[") + 3}: Timed gates are not supported.')
                with self.subTest(body=body, classical=classical, route='stdin'):
                    with self.assertRaises(ValueError) as caught:
                        compiler.convert('OPENQASM 3; include "stdgates.inc"; ' + body, classical=classical)
                    self.assertEqual(str(caught.exception), 'Timed gates are not supported.')
                with self.subTest(body=body, classical=classical, route='untimed'):
                    untimed = body.replace('x[1ns]', 'x').replace('x[0ns]', 'x')
                    result = compiler.convert('OPENQASM 3; include "stdgates.inc"; ' + untimed, classical=classical)
                    self.assertEqual(result['Qubits'], 1)
                    expected = ({'Kind': 'Gate', 'Expression': 'X', 'Wires': [0]} if classical else
                                {'Gate': 'X', 'Angle': '', 'Wires': [0]})
                    self.assertEqual(result['Steps'], [expected])

    def test_timed_global_phase_is_not_lost_by_parser(self):
        spec = importlib.util.spec_from_file_location("qasm_import", Path(__file__).with_name("qasm-import.py"))
        compiler = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(compiler)
        cases = [
            ('qubit q; gphase(pi)[1ns];', 'gphase'),
            ('qubit q; ctrl @ gphase(pi)[1ns] q;', 'ctrl'),
            ('qubit q; bit a; bit b; let c = a ++ b; gphase(pi)[1ns];', 'gphase'),
        ]
        main = self.put('main.qasm', 'OPENQASM 3; include "phase.inc";')
        for body, token in cases:
            self.put('phase.inc', '// dependency\n  ' + body)
            for classical in (False, True):
                with self.subTest(body=body, classical=classical):
                    with self.assertRaises(SourceError) as caught:
                        compile_source(capture_source(main), compiler.convert, classical=classical)
                    self.assertEqual(str(caught.exception),
                                     f'phase.inc:2:{body.index(token) + 3}: Timed gates are not supported.')

    def test_declaration_range_and_scope_locations(self):
        spec = importlib.util.spec_from_file_location("qasm_import", Path(__file__).with_name("qasm-import.py"))
        compiler = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(compiler)
        cases = [
            ('int ' + 'n' * 65 + ';', 0, True, 'Integer variable names must fit 64 UTF-16 code units.'),
            ('float ' + 'n' * 65 + ';', 0, True, 'Integer variable names must fit 64 UTF-16 code units.'),
            ('int ' + '𝑎' * 33 + ';', 0, True, 'Integer variable names must fit 64 UTF-16 code units.'),
            ('int n; for int ' + 'i' * 65 + ' in [0:n] { }', 7, True,
             'Integer variable names must fit 64 UTF-16 code units.'),
            ('qubit[3] q; x q[0:0:2];', 12, False, 'Register ranges require integer bounds and a nonzero integer step.'),
            ('qubit[3] q; x q[0:0:2];', 12, True, 'Register ranges require integer bounds and a nonzero integer step.'),
            ('{' * 33 + 'int n;' + '}' * 33, 32, True, 'Classical scopes exceed 32 levels.'),
        ]
        for statement, offset in [('if(true) { }', 0), ('while(false) { }', 0),
                                  ('for int i in [0:0] { }', 0), ('switch(0) { case 0 { } }', 19)]:
            cases.append(('{' * 32 + statement + '}' * 32, 32 + offset, True,
                          'Classical scopes exceed 32 levels.'))
        main = self.put('main.qasm', 'OPENQASM 3; include "stdgates.inc"; include "limits.inc";')
        for body, offset, classical, message in cases:
            self.put('limits.inc', '// dependency\n  ' + body)
            with self.subTest(body=body, classical=classical):
                with self.assertRaises(SourceError) as caught:
                    compile_source(capture_source(main), compiler.convert, classical=classical)
                self.assertEqual(str(caught.exception), f'limits.inc:2:{offset + 3}: {message}')
        for body in ('int ' + 'n' * 64 + ';', 'int ' + '𝑎' * 32 + ';', '{' * 32 + 'int n;' + '}' * 32):
            with self.subTest(valid=body):
                result = compiler.convert('OPENQASM 3; ' + body, classical=True)
                self.assertEqual(len(result['Variables']), 1)

    def mapped_token(self, bundle, token, name, original, occurrence=0):
        offset = -1
        for _ in range(occurrence + 1):
            offset = bundle.expanded.index(token, offset + 1)
        line = bundle.expanded.count("\n", 0, offset) + 1
        column = offset - bundle.expanded.rfind("\n", 0, offset) - 1
        where = bundle.location(line, column)
        original_offset = original.index(token)
        self.assertEqual((where.name, where.line, where.column, where.synthetic),
                         (name, original.count("\n", 0, original_offset) + 1,
                          original_offset - original.rfind("\n", 0, original_offset) - 1, False))

    def test_source_map_nested_inline_and_unicode(self):
        main_text = 'OPENQASM 3; /* κ */ include "sub dir/g.inc"; qubit q;\nouter q;'
        child_text = '// α\r\ninclude "../h.inc"; gate outer a { inner a; }'
        helper_text = '// β\r\ngate inner b { x b; }'
        main = self.put("main κ.qasm", main_text)
        self.put("sub dir/g.inc", child_text)
        helper = self.put("h.inc", helper_text)
        bundle = capture_source(main)
        self.mapped_token(bundle, "qubit q", "main κ.qasm", main_text)
        self.mapped_token(bundle, "outer q", "main κ.qasm", main_text)
        self.mapped_token(bundle, "gate outer", "sub dir/g.inc", child_text)
        self.mapped_token(bundle, "x b", "h.inc", helper_text)
        helper.unlink()
        self.mapped_token(bundle, "x b", "h.inc", helper_text)

    def test_source_map_repeated_include_and_separators(self):
        text = 'include "g.inc"; include "g.inc";'
        main = self.put("main.qasm", text)
        source = "gate g q { x q; }"
        self.put("g.inc", source)
        bundle = capture_source(main)
        for occurrence in (0, 1):
            self.mapped_token(bundle, "x q", "g.inc", source, occurrence)
        self.assertEqual(bundle.location(1, 0).name, "main.qasm")
        self.assertTrue(bundle.location(1, 0).synthetic)
        # The separator after the first dependency belongs to that include.
        where = bundle.location(2, len(source))
        self.assertEqual((where.name, where.line, where.column, where.synthetic),
                         ("main.qasm", 1, 0, True))

    def test_source_map_adapted_headers_and_standard_includes(self):
        main_text = 'OPENQASM 3; include "stdgates.inc"; include "g.inc"; qubit q; g q;'
        child_text = 'OPENQASM 3;\r\ninclude "stdgates.inc"; gate g a { x a; }'
        main = self.put("main.qasm", main_text)
        self.put("g.inc", child_text)
        bundle = capture_source(main, module_headers=True)
        self.mapped_token(bundle, "gate g", "g.inc", child_text)
        self.mapped_token(bundle, "x a", "g.inc", child_text)
        self.mapped_token(bundle, "qubit q", "main.qasm", main_text)
        self.assertEqual(bundle.expanded.count('include "stdgates.inc";'), 1)

    def test_source_map_empty_and_eof(self):
        main = self.put("main.qasm", "")
        bundle = capture_source(main)
        self.assertEqual((bundle.location(1, 0).line, bundle.location(1, 0).column), (1, 0))
        main.write_bytes(b"\xef\xbb\xbf// Unicode \xce\xba\r\n")
        bundle = capture_source(main)
        where = bundle.location(2, 0)
        self.assertEqual((where.name, where.line, where.column, where.synthetic),
                         ("main.qasm", 2, 0, False))
        self.assertTrue(bundle.files[0].bom)

    def test_source_map_rejects_invalid_coordinates(self):
        bundle = capture_source(self.put("main.qasm", "//a\n//b"))
        for line, column in ((0, 0), (1, -1), (True, 0), (1, False), (1.0, 0),
                             (3, 0), (1, 4), (2, 4), (1000000000, 0)):
            with self.subTest(line=line, column=column), self.assertRaises(ValueError):
                bundle.location(line, column)

    def test_diagnostic_scope_restores_logger_and_preserves_options(self):
        bundle = capture_source(self.put("main.qasm", "OPENQASM 3; qubit q;"))
        logger = logging.getLogger("pyqasm")
        filters, handlers, propagate = list(logger.filters), list(logger.handlers), logger.propagate
        expected = object()
        def success(source, **options):
            self.assertEqual(source, bundle.expanded)
            self.assertEqual(options, {"classical": True, "published_u": False})
            return expected
        self.assertIs(compile_source(bundle, success, classical=True, published_u=False), expected)
        def failure(source, **options):
            raise ValueError("A location-free adapter error.")
        with self.assertRaisesRegex(SourceError, "^main.qasm: A location-free adapter error."):
            compile_source(bundle, failure)
        self.assertEqual(logger.filters, filters)
        self.assertEqual(logger.handlers, handlers)
        self.assertEqual(logger.propagate, propagate)
        self.assertEqual(bundle.expanded, "OPENQASM 3; qubit q;")

    def test_invalid_compiler_span_does_not_invent_location(self):
        bundle = capture_source(self.put("main.qasm", "OPENQASM 3; qubit q;"))
        def failure(source, **options):
            logging.getLogger("pyqasm").error("Error at line 99, column 0 in QASM file")
            raise ValueError("Missing usable source span.")
        with self.assertRaisesRegex(SourceError, "^main.qasm: Missing usable source span."):
            compile_source(bundle, failure)

    def test_adapter_location_without_span_does_not_guess(self):
        bundle = capture_source(self.put("main.qasm", "OPENQASM 3; qubit q;"))
        def failure(source, **options):
            raise error_at(object(), "No original AST span.")
        with self.assertRaisesRegex(SourceError, "^main.qasm: No original AST span."):
            compile_source(bundle, failure)

    def test_adapter_location_with_invalid_span_does_not_guess(self):
        from types import SimpleNamespace
        bundle = capture_source(self.put("main.qasm", "OPENQASM 3; qubit q;"))
        node = SimpleNamespace(span=SimpleNamespace(start_line=999, start_column=0))
        def failure(source, **options):
            raise error_at(node, "Invalid original AST span.")
        with self.assertRaisesRegex(SourceError, "^main.qasm: Invalid original AST span."):
            compile_source(bundle, failure)

    def test_lowering_context_preserves_inner_and_missing_spans(self):
        from types import SimpleNamespace
        bundle = capture_source(self.put("main.qasm", "OPENQASM 3;\nqubit q;"))
        located = SimpleNamespace(span=SimpleNamespace(start_line=2, start_column=0))
        for original, expected in ((located, "main.qasm:2:1: failure"),
                                   (object(), "main.qasm: failure")):
            synthesized = copy_span(SimpleNamespace(), original)
            def failure(source):
                with diagnostic_context(synthesized):
                    raise ValueError("failure")
            with self.assertRaises(SourceError) as caught:
                compile_source(bundle, failure)
            self.assertEqual(str(caught.exception), expected)
        inner = error_at(located, "inner")
        with self.assertRaises(type(inner)) as caught:
            with diagnostic_context(object()):
                raise inner
        self.assertIs(caught.exception, inner)

    def test_nested_spaces_and_snapshot(self):
        main = self.put("main.qasm", 'OPENQASM 3; include "stdgates.inc";\ninclude "sub dir/gate.inc";\nqubit q; g q;')
        self.put("sub dir/gate.inc", 'include "../helper.inc"; gate g q { h q; }')
        helper = self.put("helper.inc", "// helper\n")
        bundle = capture_source(main)
        self.assertEqual(len(bundle.files), 3)
        self.assertIn('include "stdgates.inc";', bundle.expanded)
        self.assertIn("gate g", bundle.expanded)
        self.assertNotIn('include "../helper.inc"', bundle.expanded)
        self.assertEqual(bundle.changed_files(), ())
        original = bundle.expanded
        helper.write_text("// changed", encoding="utf-8")
        self.assertEqual(bundle.changed_files(), ("helper.inc",))
        self.assertEqual(bundle.expanded, original)
        helper.unlink()
        self.assertEqual(bundle.changed_files(), ("helper.inc",))
        self.assertTrue(any(p.name == "sub dir/gate.inc" for p in bundle.pieces))

    def test_comments_and_repeated_includes(self):
        main = self.put("main.qasm", '// include "absent";\n/* include "absent"; */\ninclude "g.inc"; include "g.inc";')
        self.put("g.inc", "gate g q { x q; } // trailing comment")
        bundle = capture_source(main)
        self.assertEqual(len(bundle.files), 2)
        self.assertEqual(bundle.expanded.count("gate g"), 2)
        self.assertIn("// trailing comment\n", bundle.expanded)

    def test_non_qasm_text_is_not_an_include(self):
        for text in ['pragma include "absent.inc";\n', 'cal { include "absent.inc"; }']:
            with self.subTest(text=text):
                bundle = capture_source(self.put("main.qasm", text))
                self.assertEqual(len(bundle.files), 1)
                self.assertEqual(bundle.expanded, text)

    def test_missing_cycle_and_malformed(self):
        for text, expected in [
            ('\ninclude "missing.inc";', "main.qasm:2"),
            ('include "main.qasm";', "Include cycle"),
            ('include "missing.inc"', "semicolon"),
        ]:
            with self.subTest(text=text):
                with self.assertRaisesRegex(SourceError, expected):
                    capture_source(self.put("main.qasm", text))

    def test_paths_need_explicit_root(self):
        self.put("outside.inc", "gate g q { x q; }")
        main = self.put("project/main.qasm", 'include "../outside.inc";')
        with self.assertRaisesRegex(SourceError, "outside"):
            capture_source(main)
        self.assertIn("gate g", capture_source(main, root=self.root).expanded)
        for filename in ("C:/outside.inc", "C:outside.inc", "/outside.inc", "//host/share", "x:stream", "..\\outside.inc"):
            with self.subTest(filename=filename):
                with self.assertRaisesRegex(SourceError, "relative filename"):
                    capture_source(self.put("main.qasm", f'include "{filename}";'))

    def test_utf8_and_bom(self):
        main = self.put("main.qasm", '\ufeff// α\ninclude "λ.inc";')
        self.put("λ.inc", "// λ\n")
        bundle = capture_source(main)
        self.assertFalse(bundle.expanded.startswith("\ufeff"))
        self.assertEqual(bundle.changed_files(), ())
        (self.root / "λ.inc").write_bytes(b"\xff")
        with self.assertRaisesRegex(SourceError, "UTF-8"):
            capture_source(main)

    def test_depth_and_size_limits(self):
        for k in range(MAX_DEPTH + 1):
            self.put(f"{k}.inc", f'include "{k+1}.inc";' if k < MAX_DEPTH else "")
        with self.assertRaisesRegex(SourceError, "nesting"):
            capture_source(self.root / "0.inc")
        with self.assertRaisesRegex(SourceError, "bytes"):
            capture_source(self.put("large.qasm", " " * (MAX_BYTES + 1)))
        self.put("large.inc", "//" + "x" * (MAX_BYTES // 2))
        with self.assertRaisesRegex(SourceError, "Expanded source"):
            capture_source(self.put("repeat.qasm", 'include "large.inc"; include "large.inc";'))
        self.put("large2.inc", "//" + "y" * (MAX_BYTES // 2))
        with self.assertRaisesRegex(SourceError, "Source bundle exceeds"):
            capture_source(self.put("total.qasm", 'include "large.inc"; include "large2.inc";'))
        for k in range(MAX_FILES):
            self.put(f"leaf{k}.inc", "")
        main = self.put("files.qasm", "".join(f'include "leaf{k}.inc";' for k in range(MAX_FILES)))
        with self.assertRaisesRegex(SourceError, "exceeds 64"):
            capture_source(main)

    def test_link_boundary_and_retarget(self):
        a = self.put("a.inc", "// first")
        b = self.put("b.inc", "// second")
        link = self.root / "link.inc"
        try:
            link.symlink_to(a)
        except OSError as error:
            self.skipTest(f"Symlink creation unavailable: {error}")
        main = self.put("main.qasm", 'include "link.inc";')
        bundle = capture_source(main)
        self.assertEqual(bundle.changed_files(), ())
        link.unlink()
        link.symlink_to(b)
        self.assertEqual(bundle.changed_files(), ("link.inc",))
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / "outside.inc"
            target.write_text("// outside", encoding="utf-8")
            link.unlink()
            link.symlink_to(target)
            with self.assertRaisesRegex(SourceError, "outside"):
                capture_source(main)

    def test_compilation_matches_inline_and_keeps_duplicate_errors(self):
        spec = importlib.util.spec_from_file_location("qasm_import", Path(__file__).with_name("qasm-import.py"))
        compiler = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(compiler)
        module = "gate entangle a,b { h a; cx a,b; }"
        header = 'OPENQASM 3; include "stdgates.inc";'
        call = "qubit[2] q; entangle q[0],q[1];"
        self.put("module.inc", module)
        main = self.put("main.qasm", header + 'include "module.inc";' + call)
        self.assertEqual(compiler.convert(capture_source(main).expanded), compiler.convert(header + module + call))
        self.put("main.qasm", header + 'include "module.inc"; include "module.inc";' + call)
        with self.assertRaises(ValidationError):
            compiler.convert(capture_source(main).expanded)

    def test_parent_after_directory_link_keeps_identity(self):
        self.put("sub/deep/unused", "")
        self.put("sub/module.inc", "// selected")
        self.put("module.inc", "// different")
        link = self.root / "alias"
        try:
            link.symlink_to(self.root / "sub/deep", target_is_directory=True)
        except OSError as error:
            self.skipTest(f"Directory symlink creation unavailable: {error}")
        main = self.put("main.qasm", 'include "alias/../module.inc";')
        bundle = capture_source(main)
        self.assertEqual(bundle.changed_files(), ())
        # Windows and POSIX may resolve parent traversal across links differently.
        selected = (link / "../module.inc").resolve()
        self.assertIn(selected.read_text(encoding="utf-8"), bundle.expanded)

    def test_saved_snapshot_checks_explicit_root_and_preserves_snapshot(self):
        main = self.put("main.qasm", '\ufeffinclude "sub dir/λ.inc";')
        dependency = self.put("sub dir/λ.inc", "// original")
        snapshot = capture_source(main).snapshot()
        snapshot["Root"] = "Z:/nonexistent/untrusted-saved-root"
        original = copy.deepcopy(snapshot)
        result = check_snapshot(snapshot, root=self.root)
        self.assertTrue(result["Unchanged"])
        dependency.write_text("// changed", encoding="utf-8")
        result = check_snapshot(snapshot, root=self.root)
        self.assertEqual([r["Status"] for r in result["Files"]], ["unchanged", "changed"])
        dependency.unlink()
        result = check_snapshot(snapshot, root=self.root)
        self.assertEqual([r["Status"] for r in result["Files"]], ["unchanged", "missing"])
        self.assertEqual(snapshot, original)

    def test_snapshot_rejects_invalid_paths_and_hashes_before_disk_reads(self):
        from unittest.mock import patch
        snapshot = capture_source(self.put("main.qasm", "// original")).snapshot()
        malformed = []
        for name in ("../escape", "a/../../escape", "C:/secret", "/secret", "a\\b", "a:stream"):
            candidate = copy.deepcopy(snapshot)
            candidate["Bindings"][0]["Path"] = name
            malformed.append(candidate)
        for field, value in (("Sha256", "0" * 64), ("Text", "\ud800"), ("Bom", 1)):
            candidate = copy.deepcopy(snapshot)
            candidate["Files"][0][field] = value
            malformed.append(candidate)
        candidate = copy.deepcopy(snapshot)
        candidate["Version"] = True
        malformed.append(candidate)
        for candidate in malformed:
            with self.subTest(candidate=repr(candidate)), patch.object(Path, "resolve", side_effect=AssertionError("unexpected filesystem access")):
                with self.assertRaises(SourceError):
                    check_snapshot(candidate, root=self.root)

    def test_snapshot_reports_retargeted_and_escaped_links_without_reading_them(self):
        a = self.put("a.inc", "// same")
        b = self.put("b.inc", "// same")
        link = self.root / "link.inc"
        try:
            link.symlink_to(a)
        except OSError as error:
            self.skipTest(f"Symlink creation unavailable: {error}")
        snapshot = capture_source(self.put("main.qasm", 'include "link.inc";')).snapshot()
        link.unlink()
        link.symlink_to(b)
        result = check_snapshot(snapshot, root=self.root)
        self.assertEqual(result["Files"][1]["Status"], "retargeted")
        with tempfile.TemporaryDirectory() as outside:
            external = Path(outside) / "secret"
            external.write_text("// same", encoding="utf-8")
            link.unlink()
            link.symlink_to(external)
            result = check_snapshot(snapshot, root=self.root)
            self.assertEqual(result["Files"][1]["Status"], "unavailable")

    def test_snapshot_reports_oversized_files_without_changing_captured_bytes(self):
        main = self.put("main.qasm", "// original")
        snapshot = capture_source(main).snapshot()
        main.write_bytes(b" " * (MAX_BYTES + 1))
        self.assertEqual(check_snapshot(snapshot, root=self.root)["Files"][0]["Status"], "unavailable")
        self.assertEqual(snapshot["Files"][0]["Text"], "// original")

    def test_snapshot_empty_root_never_defaults_to_working_directory(self):
        from unittest.mock import patch
        snapshot = capture_source(self.put("main.qasm", "// original")).snapshot()
        for root in (None, "", "   "):
            with self.subTest(root=root), patch.object(Path, "resolve", side_effect=AssertionError("unexpected filesystem access")):
                with self.assertRaisesRegex(SourceError, "Select a source root"):
                    check_snapshot(snapshot, root=root)


if __name__ == "__main__":
    unittest.main()
