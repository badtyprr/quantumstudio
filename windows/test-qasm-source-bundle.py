"""Source dependency boundaries and deterministic expansion, without GUI or cloud."""
from pathlib import Path
import importlib.util
import tempfile
import unittest
from pyqasm import ValidationError

from qasm_source_bundle import capture_source, SourceError, MAX_BYTES, MAX_DEPTH, MAX_FILES


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


if __name__ == "__main__":
    unittest.main()
