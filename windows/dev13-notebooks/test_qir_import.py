"""Real LLVM parsing tests for the explicit finite importer."""
import unittest
import pyqir
from qir_import import import_qir

HEADER = """define void @main() #0 {
entry:
%s
  ret void
}
declare void @__quantum__qis__h__body(ptr)
declare void @__quantum__qis__x__body(ptr)
declare void @__quantum__qis__cnot__body(ptr, ptr)
declare void @__quantum__qis__mz__body(ptr, ptr)
declare void @__quantum__rt__result_record_output(ptr, ptr)
attributes #0 = { "entry_point" "qir_profiles"="base" "required_num_qubits"="2" "required_num_results"="2" }
!llvm.module.flags = !{!0, !1, !2, !3}
!0 = !{i32 1, !"qir_major_version", i32 1}
!1 = !{i32 7, !"qir_minor_version", i32 0}
!2 = !{i32 1, !"dynamic_qubit_management", i1 false}
!3 = !{i32 1, !"dynamic_result_management", i1 false}
"""
H = '  call void @__quantum__qis__h__body(ptr null)'
CX = '  call void @__quantum__qis__cnot__body(ptr null, ptr inttoptr (i64 1 to ptr))'
M0 = '  call void @__quantum__qis__mz__body(ptr null, ptr null)'
M1 = '  call void @__quantum__qis__mz__body(ptr inttoptr (i64 1 to ptr), ptr inttoptr (i64 1 to ptr))'
O0 = '  call void @__quantum__rt__result_record_output(ptr null, ptr null)'
O1 = '  call void @__quantum__rt__result_record_output(ptr inttoptr (i64 1 to ptr), ptr null)'


def fixture(*calls):
    return (HEADER % "\n".join(calls)).encode()


class ImportTests(unittest.TestCase):
    def test_terminal_output_permutation_uses_direct_measurement_targets(self):
        report = import_qir(fixture(H, CX, M0, M1, O1, O0))
        self.assertEqual(report['output_lowering'], 'terminal-measurement-aliases')
        self.assertNotIn('] result;', report['openqasm'])
        self.assertIn('out[0] = measure q[0];\nout[1] = measure q[1];', report['openqasm'])

    def test_snapshot_cases_do_not_alias(self):
        for calls in [(M0, O0, M1, O1), (M0, M0, O0), (M0, O0, O0),
                      (M0, M1, O0), (M0, H, O0)]:
            report = import_qir(fixture(*calls))
            self.assertEqual(report['output_lowering'], 'record-snapshots')
            self.assertIn('bit[2] result;', report['openqasm'])

    def test_bell_ir_and_bitcode_agree(self):
        raw = fixture(H, CX, M0, M1, O0, O1)
        text = import_qir(raw)
        bitcode = pyqir.Module.from_ir(pyqir.Context(), raw.decode()).bitcode
        binary = import_qir(bitcode, bitcode=True)
        self.assertEqual(text['openqasm'], binary['openqasm'])
        self.assertEqual(text['output_slots'], 2)
        self.assertIn('h q[0];\ncx q[0], q[1];', text['openqasm'])
        self.assertFalse(text['execution_performed'])

    def test_output_order_and_snapshots_survive_result_overwrite(self):
        raw = fixture(M1, O1, M0, O0, '  call void @__quantum__qis__x__body(ptr null)', M0, O0)
        qasm = import_qir(raw)['openqasm']
        self.assertIn('out[2] = result[1];', qasm)
        self.assertIn('out[1] = result[0];\nx q[0];\nresult[0] = measure q[0];\nout[0] = result[0];', qasm)

    def test_unitary_only_keeps_no_output(self):
        report = import_qir(fixture(H, CX))
        self.assertEqual(report['output_slots'], 0)
        self.assertNotIn('measure', report['openqasm'])
        self.assertNotIn('output bit', report['openqasm'])

    def test_unrecorded_measurements_are_discarded_without_visible_storage(self):
        report = import_qir(fixture(H, M0))
        self.assertEqual(report['output_slots'], 0)
        self.assertIn('measure q[0];', report['openqasm'])
        self.assertNotIn('\nbit[', report['openqasm'])
        self.assertNotIn('result[', report['openqasm'])

    def test_unmeasured_result_is_not_repaired(self):
        for calls in ((H, CX, O0, O1), (M0, O1)):
            with self.assertRaisesRegex(ValueError, 'QIR_UNMEASURED_OUTPUT'):
                import_qir(fixture(*calls))

    def test_unknown_calls_and_noncall_instructions_rejected(self):
        for raw in (fixture(H).replace(b'__quantum__qis__h__body', b'__quantum__qis__unknown__body'),
                    fixture('  %x = add i32 1, 2')):
            with self.assertRaisesRegex(ValueError, 'QIR_UNSUPPORTED'):
                import_qir(raw)

    def test_static_resource_bounds_and_aliases(self):
        for raw in (fixture(CX).replace(b'(i64 1 to ptr)', b'(i64 2 to ptr)'),
                    fixture(CX).replace(b'ptr inttoptr (i64 1 to ptr)', b'ptr null'),
                    fixture(H).replace(b'required_num_qubits"="2', b'required_num_qubits"="11'),
                    fixture(H).replace(b'required_num_results"="2', b'required_num_results"="65')):
            with self.assertRaises(ValueError):
                import_qir(raw)

    def test_native_width_boundary_preserves_highest_wire(self):
        for width in range(5, 11):
            raw = fixture(f'  call void @__quantum__qis__x__body(ptr inttoptr (i64 {width-1} to ptr))')
            raw = raw.replace(b'required_num_qubits"="2', f'required_num_qubits"="{width}'.encode())
            for bitcode, source in [(False, raw), (True, pyqir.Module.from_ir(pyqir.Context(), raw.decode()).bitcode)]:
                report = import_qir(source, bitcode=bitcode)
                self.assertEqual(report['qubits'], width)
                self.assertIn(f'x q[{width-1}];', report['openqasm'])
        with self.assertRaisesRegex(ValueError, 'QIR_STATIC_ID:qubit'):
            import_qir(raw.replace(b'i64 9 to ptr', b'i64 10 to ptr'))

    def test_five_qubit_invalid_result_is_not_repaired(self):
        raw = fixture(M0, O0, '  call void @__quantum__rt__result_record_output(ptr inttoptr (i64 4 to ptr), ptr null)')
        raw = raw.replace(b'required_num_qubits"="2', b'required_num_qubits"="5')
        raw = raw.replace(b'required_num_results"="2', b'required_num_results"="4')
        for bitcode, source in [(False, raw), (True, pyqir.Module.from_ir(pyqir.Context(), raw.decode()).bitcode)]:
            with self.assertRaisesRegex(ValueError, 'QIR_STATIC_ID:result'):
                import_qir(source, bitcode=bitcode)

    def test_dynamic_profile_and_multiple_blocks_rejected(self):
        for raw in (fixture(H).replace(b'i1 false', b'i1 true'),
                    fixture('  br label %next\nnext:'),
                    fixture(H).replace(b'"entry_point"', b'"not_entry_point"')):
            with self.assertRaises(ValueError):
                import_qir(raw)

    def test_bad_signature_and_named_output_rejected(self):
        raw = fixture(O0).replace(b'ptr null, ptr null', b'ptr null, ptr inttoptr (i64 1 to ptr)')
        with self.assertRaisesRegex(ValueError, 'QIR_OUTPUT_SIGNATURE'):
            import_qir(raw)
        raw = fixture('  call void @__quantum__qis__h__body(i64 0)').replace(b'h__body(ptr)', b'h__body(i64)')
        with self.assertRaisesRegex(ValueError, 'QIR_CALL_SIGNATURE'):
            import_qir(raw)

    def test_combined_native_storage_limit(self):
        raw = fixture(M0, O0).replace(b'required_num_results"="2', b'required_num_results"="63')
        self.assertEqual(import_qir(raw)['output_slots'], 1)
        with self.assertRaisesRegex(ValueError, 'QIR_CLASSICAL_STORAGE_LIMIT'):
            import_qir(raw.replace(b'required_num_results"="63', b'required_num_results"="64'))

    def test_instruction_limit(self):
        self.assertEqual(import_qir(fixture(*([H] * 4095)))['output_slots'], 0)
        with self.assertRaisesRegex(ValueError, 'QIR_INSTRUCTION_LIMIT'):
            import_qir(fixture(*([H] * 4096)))

    def test_supported_name_cannot_hide_function_body(self):
        raw = fixture(H).replace(b'declare void @__quantum__qis__h__body(ptr)',
                                b'define void @__quantum__qis__h__body(ptr %q) { ret void }')
        with self.assertRaisesRegex(ValueError, 'QIR_UNSUPPORTED_CALLEE'):
            import_qir(raw)

    def test_cli_preserves_existing_file_and_writes_nothing_on_rejection(self):
        import subprocess
        import sys
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / 'source.ll', root / 'output.qasm'
            source.write_bytes(fixture(H))
            output.write_bytes(b'keep me')
            command = [sys.executable, '-E', '-s', '-B', str(Path(__file__).with_name('qir_import.py')),
                       str(source), '--output', str(output)]
            run = subprocess.run(command, capture_output=True, timeout=30)
            self.assertNotEqual(run.returncode, 0)
            self.assertEqual(output.read_bytes(), b'keep me')
            output.unlink()
            source.write_bytes(fixture(O0))
            run = subprocess.run(command, capture_output=True, timeout=30)
            self.assertNotEqual(run.returncode, 0)
            self.assertFalse(output.exists())

    def test_size_and_invalid_llvm_rejected(self):
        for raw in (b'', b'x' * (1024 * 1024 + 1), b'not llvm', b'\xff'):
            with self.assertRaises(ValueError):
                import_qir(raw)


if __name__ == '__main__':
    unittest.main(verbosity=2)
