"""Finite authored timing/state controls. Standard library only; no SDK imports."""
import contextlib
import io
import math
import unittest

import timing_reference as ref


def operation(name, qubits, params=None, clbits=None):
    return dict(name=name, qubits=qubits, params=[] if params is None else params,
                clbits=[] if clbits is None else clbits)


class TimingReferenceTests(unittest.TestCase):
    def test_retained_five_hand_derivations_and_thirteen_rejections(self):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            ref.main()
        self.assertIn('"positive": 5', stream.getvalue())
        self.assertIn('"rejections": 13', stream.getvalue())

    def test_observed_alap_exact_integer_mapping(self):
        fixture = ref.fixtures()[0]
        actual = ref.check_schedule(fixture['ops'], {'short': 5, 'long': 0}, 8)
        self.assertEqual(actual['ends_dt'], {'short': 8, 'long': 8})
        for starts, horizon in [({'short': 4, 'long': 0}, 8), ({'short': 5.0, 'long': 0}, 8),
                                ({'short': True, 'long': 0}, 8), ({'short': 5}, 8),
                                ({'short': 5, 'long': 0}, 9), ({'short': 5, 'long': 0}, 8.0)]:
            with self.subTest(starts=starts, horizon=horizon), self.assertRaises(ValueError):
                ref.check_schedule(fixture['ops'], starts, horizon)

    def test_duration_conversion_rejects_fractional_and_invalid_units(self):
        self.assertEqual(ref.duration_ticks(8e-9, 1e-9), 8)
        self.assertEqual(ref.duration_ticks(0, 1e-9), 0)
        for duration, dt in [(1.1e-9, 1e-9), (-1, 1), (1, 0), (1, -1),
                             (True, 1), (1, True), (float('inf'), 1), (1, float('nan'))]:
            with self.subTest(duration=duration, dt=dt), self.assertRaises(ValueError):
                ref.duration_ticks(duration, dt)

    def test_idle_complement_includes_unused_wires_and_barriers(self):
        ops = [ref.op('short', 'gate', 3, ['q:0']), ref.op('long', 'gate', 8, ['q:1']),
               ref.op('bar', 'barrier', 0, ['q:0', 'q:1'], ['short', 'long'])]
        starts = {'short': 5, 'long': 0, 'bar': 8}
        self.assertEqual(ref.padding_intervals(ops, starts, 8, 3), {'0': [[0, 5]], '1': [], '2': [[0, 8]]})

    def test_explicit_source_delay_is_occupied_not_inserted_padding(self):
        ops = [ref.op('delay', 'delay', 2, ['q:0']), ref.op('gate', 'gate', 3, ['q:0'], ['delay']),
               ref.op('other', 'gate', 8, ['q:1'])]
        starts = {'delay': 3, 'gate': 5, 'other': 0}
        self.assertEqual(ref.padding_intervals(ops, starts, 8, 2), {'0': [[0, 3]], '1': []})

    def test_unequal_measurement_durations_hold_classical_resources(self):
        f = ref.fixtures()[2]
        result = ref.check_schedule(f['ops'], f['late'], f['makespan'])
        self.assertEqual(result['ends_dt']['m0'], 10)
        self.assertEqual(result['ends_dt']['m1'], 12)
        altered = [dict(o, duration_dt=5) if o['id'] == 'm0' else o for o in f['ops']]
        with self.assertRaisesRegex(ValueError, 'ALAP_START_MISMATCH'):
            ref.check_schedule(altered, f['late'], f['makespan'])


class StateReferenceTests(unittest.TestCase):
    def test_bell_with_permuted_layout_and_nonzero_ancilla(self):
        ops = [operation('x', [0]), operation('h', [3]), operation('cx', [3, 1])]
        state, measurements = ref.scalar_state(ops, 5, global_phase=0.73)
        self.assertEqual(measurements, [])
        result = ref.check_density(ref.reduced_density(state, [3, 1]), ref.bell_density())
        self.assertLess(result['max_entry_error'], 1e-15)

    def test_asymmetric_layout_controls_detect_swapped_wires(self):
        for physical, logical_basis in [(3, 1), (1, 2)]:
            with self.subTest(physical=physical):
                state, _ = ref.scalar_state([operation('x', [physical]), operation('x', [0])], 5)
                expected = [[int(i == j == logical_basis) for j in range(4)] for i in range(4)]
                ref.check_density(ref.reduced_density(state, [3, 1]), expected)
                with self.assertRaisesRegex(ValueError, 'DENSITY_MISMATCH'):
                    ref.check_density(ref.reduced_density(state, [1, 3]), expected)

    def test_cx_orientation_is_not_symmetric(self):
        forward, _ = ref.scalar_state([operation('x', [0]), operation('cx', [0, 1])], 2)
        reverse, _ = ref.scalar_state([operation('x', [0]), operation('cx', [1, 0])], 2)
        self.assertEqual(forward, [0j, 0j, 0j, 1+0j])
        self.assertEqual(reverse, [0j, 1+0j, 0j, 0j])

    def test_coherent_bell_distinguished_from_mixture_and_opposite_phase(self):
        mixed = [[0.5, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0.5]]
        with self.assertRaisesRegex(ValueError, 'DENSITY_MISMATCH'):
            ref.check_density(mixed, ref.bell_density())
        state, _ = ref.scalar_state([operation('h', [0]), operation('cx', [0, 1]), operation('rz', [0], [math.pi])], 2)
        with self.assertRaisesRegex(ValueError, 'DENSITY_MISMATCH'):
            ref.check_density(ref.reduced_density(state, [0, 1]), ref.bell_density())

    def test_partial_trace_retains_entangled_ancilla_effect(self):
        state, _ = ref.scalar_state([operation('h', [0]), operation('cx', [0, 1]), operation('cx', [1, 2])], 3)
        density = ref.reduced_density(state, [0, 1])
        self.assertAlmostEqual(density[0][0].real, 0.5)
        self.assertAlmostEqual(density[3][3].real, 0.5)
        self.assertEqual(density[0][3], 0)
        with self.assertRaisesRegex(ValueError, 'DENSITY_MISMATCH'):
            ref.check_density(density, ref.bell_density())

    def test_sx_twice_is_x_and_h_twice_identity(self):
        for gate, expected in [('sx', [0j, 1+0j]), ('h', [1+0j, 0j])]:
            state, _ = ref.scalar_state([operation(gate, [0]), operation(gate, [0])], 1)
            self.assertLess(max(abs(a-b) for a, b in zip(state, expected)), 1e-15)

    def test_rz_relative_phase(self):
        state, _ = ref.scalar_state([operation('h', [0]), operation('rz', [0], [math.pi/2])], 1)
        self.assertAlmostEqual((state[1]/state[0]).real, 0)
        self.assertAlmostEqual((state[1]/state[0]).imag, 1)

    def test_final_measurement_mapping_retained_without_sampling(self):
        ops = [operation('h', [2]), operation('cx', [2, 0]), operation('barrier', [2, 0]),
               operation('measure', [2], clbits=[3]), operation('measure', [0], clbits=[1])]
        state, mapping = ref.scalar_state(ops, 3)
        self.assertEqual(mapping, [[2, 3], [0, 1]])
        ref.check_density(ref.reduced_density(state, [2, 0]), ref.bell_density())
        for extra in [operation('x', [1]), operation('measure', [2], clbits=[2]), operation('measure', [1], clbits=[1])]:
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                ref.scalar_state(ops+[extra], 3)

    def test_unsupported_gate_or_invalid_data_rejected(self):
        for op in [operation('reset', [0]), operation('t', [0]), operation('cx', [0]),
                   operation('x', [0, 0]), operation('x', [True]), operation('x', [-1]),
                   operation('rz', [0], [float('nan')]), operation('x', [0], [1]),
                   operation('delay', [0], [0.5]), operation('x', [0], clbits=[0])]:
            with self.subTest(op=op), self.assertRaises(ValueError):
                ref.scalar_state([op], 2)

    def test_bad_layout_norm_and_nonfinite_density_rejected(self):
        for layout in [[0, 0], [2], [True], [], '0']:
            with self.subTest(layout=layout), self.assertRaises(ValueError):
                ref.reduced_density([1, 0, 0, 0], layout)
        with self.assertRaisesRegex(ValueError, 'STATE_NORMALIZATION'):
            ref.reduced_density([0, 0], [0])
        with self.assertRaisesRegex(ValueError, 'NONFINITE_DENSITY'):
            ref.check_density([[float('nan')]], [[1]])


class PassiveCaptureTests(unittest.TestCase):
    def fixture(self, before=None, fail=None, reentrant=False):
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace
        from observers.ibm_timing import PassiveCapture
        temporary = tempfile.TemporaryDirectory(prefix='timing-capture-unit-')
        self.addCleanup(temporary.cleanup)
        owner = SimpleNamespace()
        calls, figure = [], object()
        def inner(*args, **kwargs):
            calls.append((args, kwargs))
            if fail is not None:
                raise fail
            return figure
        owner.inner = inner
        def draw(*args, **kwargs):
            if reentrant and not getattr(owner, 'nested', False):
                owner.nested = True
                return owner.draw(*args, **kwargs)
            return owner.inner(*args, **kwargs)
        owner.draw = draw
        def validate(record):
            if record['data']['calls'] != {'inner': 1}:
                raise ValueError('HOOK_COUNT')
            return {'accepted': True}
        capture = PassiveCapture(owner, 'draw', [(owner, 'inner', before, None, 'inner')],
                                 None, None, validate, Path(temporary.name))
        return owner, capture, calls, figure, draw, inner

    def test_two_delegations_preserve_args_identity_and_restore(self):
        owner, capture, calls, figure, draw, inner = self.fixture()
        arg, value = object(), object()
        for ordinal in range(2):
            self.assertIs(owner.draw(arg, named=value), figure)
            self.assertIs(owner.inner, inner)
            self.assertEqual(calls[-1], ((arg,), {'named': value}))
            capture.checkpoint()
        self.assertEqual(len(calls), 2)
        self.assertIs(owner.draw, draw)
        self.assertTrue(capture.summary()['accepted'])
        self.assertFalse(capture.summary()['whole_notebook_complete'])

    def test_capture_error_does_not_change_source_return(self):
        def bad_capture(record, args, kwargs):
            raise ValueError('SERIALIZATION_FAILED')
        owner, capture, calls, figure, draw, inner = self.fixture(before=bad_capture)
        self.assertIs(owner.draw(3), figure)
        self.assertEqual(len(calls), 1)
        self.assertIs(owner.inner, inner)
        with self.assertRaisesRegex(ValueError, 'OBSERVER_CAPTURE_FAILED'):
            capture.checkpoint()
        self.assertIs(owner.draw, draw)
        saved = __import__('json').loads((capture.output/'timing-cell-1.json').read_text())
        self.assertEqual(saved['diagnostics'][0]['message'], 'SERIALIZATION_FAILED')
        self.assertTrue(saved['original_draw_succeeded'])

    def test_original_exception_object_is_preserved_and_restored(self):
        original = RuntimeError('ORIGINAL_EXCEPTION')
        owner, capture, calls, figure, draw, inner = self.fixture(fail=original)
        with self.assertRaises(RuntimeError) as raised:
            owner.draw('argument')
        self.assertIs(raised.exception, original)
        self.assertEqual(len(calls), 1)
        self.assertIs(owner.inner, inner)
        self.assertIs(owner.draw, draw)
        capture.cleanup()
        saved = __import__('json').loads((capture.output/'timing-cell-1.json').read_text())
        self.assertEqual(saved['draw_path_error']['message'], 'ORIGINAL_EXCEPTION')
        self.assertFalse(saved['original_draw_succeeded'])
        self.assertTrue(saved['outer_restored_at_save'])

    def test_keyboard_interrupt_not_swallowed(self):
        original = KeyboardInterrupt('cancel')
        owner, capture, calls, figure, draw, inner = self.fixture(fail=original)
        with self.assertRaises(KeyboardInterrupt) as raised:
            owner.draw()
        self.assertIs(raised.exception, original)
        self.assertIs(owner.inner, inner)
        self.assertIs(owner.draw, draw)

    def test_reentrant_draw_delegates_but_fails_authored_check(self):
        owner, capture, calls, figure, draw, inner = self.fixture(reentrant=True)
        self.assertIs(owner.draw(), figure)
        self.assertEqual(len(calls), 1)
        with self.assertRaisesRegex(ValueError, 'OBSERVER_CAPTURE_FAILED'):
            capture.checkpoint()
        self.assertIs(owner.inner, inner)
        self.assertIs(owner.draw, draw)

    def test_missing_draw_fails_before_accepted_checkpoint(self):
        owner, capture, calls, figure, draw, inner = self.fixture()
        with self.assertRaisesRegex(ValueError, 'DRAW_COUNT_MISMATCH'):
            capture.checkpoint()
        self.assertEqual(calls, [])
        self.assertIs(owner.draw, draw)

    def test_replaced_hook_does_not_silently_pass(self):
        owner, capture, calls, figure, draw, inner = self.fixture()
        replacement = lambda: figure
        owner.inner = replacement
        self.assertIs(owner.draw(), figure)
        self.assertIs(owner.inner, replacement)
        with self.assertRaisesRegex(ValueError, 'OBSERVER_CAPTURE_FAILED'):
            capture.checkpoint()
        self.assertIs(owner.draw, draw)

    def test_cleanup_before_draw_restores_outer_identity(self):
        owner, capture, calls, figure, draw, inner = self.fixture()
        capture.cleanup()
        self.assertIs(owner.draw, draw)
        self.assertIs(owner.inner, inner)
        self.assertEqual(calls, [])
        with self.assertRaisesRegex(ValueError, 'INCOMPLETE_TIMING_OBSERVATIONS'):
            capture.summary()


class MappingTests(unittest.TestCase):
    def test_repeated_operations_have_distinct_ids_and_wire_order(self):
        from observers.ibm_timing import match_operation_ids
        originals = [dict(id='x0a', **operation('x', [0])), dict(id='h1', **operation('h', [1])),
                     dict(id='rz0', **operation('rz', [0], [0.2])), dict(id='x0b', **operation('x', [0]))]
        later = [originals[i] for i in [1, 0, 2, 3]]
        self.assertEqual(match_operation_ids(originals, later), (['h1', 'x0a', 'rz0', 'x0b'], []))
        with self.assertRaisesRegex(ValueError, 'WIRE_OPERATION_ORDER_CHANGED'):
            match_operation_ids(originals, [originals[i] for i in [0, 3, 2, 1]])
        with self.assertRaisesRegex(ValueError, 'MISSING_ORIGINAL_OPERATION'):
            match_operation_ids(originals, later[:-1])

    def test_padding_identity_is_not_treated_as_original_operation(self):
        from observers.ibm_timing import match_operation_ids
        originals = [dict(id='d', **operation('delay', [0], [2])), dict(id='x', **operation('x', [0]))]
        later = [operation('delay', [0], [5]), operation('x', [0])]
        self.assertEqual(match_operation_ids(originals, later, True), ([None, 'x'], [0]))
        with self.assertRaises(ValueError):
            match_operation_ids(originals, later)
        with self.assertRaises(ValueError):
            match_operation_ids(originals, later+[operation('h', [0])], True)

    def test_layout_composition_has_verified_domain_and_direction(self):
        from observers.ibm_timing import compose_layouts
        self.assertEqual(compose_layouts([3, 1], [4, 2, 0, 1, 3], 5, 5), [1, 2])
        for first, second in [([3, 1], [0, 1]), ([3, 1], [0, 1, 1, 3, 4]),
                              ([True, 1], [0, 1, 2, 3, 4]), ([5, 1], [0, 1, 2, 3, 4])]:
            with self.subTest(first=first, second=second), self.assertRaises(ValueError):
                compose_layouts(first, second, 5, 5)

    def test_symbolic_drawing_serialization_preserves_values(self):
        import enum
        from types import SimpleNamespace
        from observers.ibm_timing import serialize_datum
        class Coordinate(enum.Enum):
            LEFT = 'LEFT'
        bit = object()
        datum = SimpleNamespace(data_type='Box.SchedGate', xvals=[0, Coordinate.LEFT], yvals=[0., 1.],
                                bits=[bit], meta=None, styles={'color': 'blue'}, text='X', latex='$X$')
        result = serialize_datum(datum, lambda b: 'q:2' if b is bit else 'unknown')
        self.assertEqual(result['xvals'][1]['name'], 'LEFT')
        self.assertEqual(result['bits'], ['q:2'])
        self.assertIsNone(result['meta'])
        self.assertEqual(result['text'], 'X')

    def test_drawing_unknown_nonfinite_or_lossy_keys_rejected(self):
        from observers.ibm_timing import finite_json
        for value in [object(), float('nan'), float('inf'), {1: 'ambiguous'}, 1j]:
            with self.subTest(value=type(value).__name__), self.assertRaises(ValueError):
                finite_json(value)


class BoundHelperTests(unittest.TestCase):
    def test_imported_draw_alias_is_restored(self):
        fixture = PassiveCaptureTests(methodName='test_cleanup_before_draw_restores_outer_identity')
        self.addCleanup(fixture.doCleanups)
        owner, capture, calls, figure, draw, inner = fixture.fixture()
        namespace = {'draw': owner.draw}
        capture.aliases = [(namespace, 'draw')]
        capture.cleanup()
        self.assertIs(namespace['draw'], draw)
        self.assertIs(owner.draw, draw)

    def test_source_delay_merged_with_idle_padding_is_accounted(self):
        from observers.ibm_timing import check_padding
        originals = [dict(id='delay', duration_dt=2, **operation('delay', [0], [2])),
                     dict(id='x', duration_dt=3, **operation('x', [0])),
                     dict(id='other', duration_dt=8, **operation('x', [1]))]
        padded = [operation('delay', [0], [5]), operation('x', [0]), operation('x', [1])]
        self.assertEqual(check_padding(originals, {'delay': 3, 'x': 5, 'other': 0}, 8, padded, [0, 5, 0], 2), {'0': [[0, 5]], '1': []})
        with self.assertRaisesRegex(ValueError, 'PADDING_COVERAGE_MISMATCH'):
            check_padding(originals, {'delay': 3, 'x': 5, 'other': 0}, 8, padded, [1, 5, 0], 2)

    def test_layout_domain_checks_use_actual_input_bits(self):
        from types import SimpleNamespace
        from observers.ibm_timing import snapshot_layout
        bits = [object(), object()]
        output_bits = [object(), object(), object()]
        layout = SimpleNamespace(_input_qubit_count=2, _output_qubit_list=output_bits,
            input_qubit_mapping={bits[0]: 0, bits[1]: 1}, final_index_layout=lambda **kw: [2, 0],
            initial_index_layout=lambda **kw: [2, 0], routing_permutation=lambda: [0, 1, 2])
        source = SimpleNamespace(qubits=bits)
        output = SimpleNamespace(qubits=output_bits, layout=layout)
        self.assertEqual(snapshot_layout(source, output)['mapping'], [2, 0])
        layout.input_qubit_mapping = {bits[0]: 1, bits[1]: 0}
        with self.assertRaisesRegex(ValueError, 'LAYOUT_INPUT_IDENTITY_MISMATCH'):
            snapshot_layout(source, output)
        output.layout = None
        with self.assertRaisesRegex(ValueError, 'UNPROVEN_LAYOUT_IDENTITY'):
            snapshot_layout(source, output, True)

    def test_source_gate_fails_before_any_sdk_import(self):
        import builtins
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from observers.ibm_timing import bind_timing
        original_import = builtins.__import__
        imports = []
        def guarded(name, *args, **kwargs):
            if name.startswith('qiskit'):
                imports.append(name)
                raise AssertionError('SDK_IMPORT_FORBIDDEN')
            return original_import(name, *args, **kwargs)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'qiskit').mkdir(); (root/'qiskit/source.py').write_text('changed')
            with patch('sysconfig.get_path', return_value=directory), patch('builtins.__import__', guarded):
                with self.assertRaisesRegex(ValueError, 'INSTALLED_QISKIT_SOURCE_CHANGED'):
                    bind_timing(None, {}, {'source.py': '0'*64})
        self.assertEqual(imports, [])

    def test_integer_ticks_reject_bool_float_and_negative(self):
        from observers.ibm_timing import integer_tick
        self.assertEqual(integer_tick(0), 0)
        for value in (True, 1.0, -1, float('inf')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                integer_tick(value)


class ContractBindingTests(unittest.TestCase):
    def test_descriptor_and_reference_hashes_bind_all_authored_roles(self):
        import hashlib
        import json
        from pathlib import Path
        import execution
        root = Path(__file__).resolve().parent
        contract = json.loads((root/'contracts/ibm-timing.json').read_text(encoding='utf-8'))
        cells = [{'cell_type': row['type']} for row in contract['source']['cells']]
        observers, lifecycle = execution._observer_sources(contract, cells)
        self.assertEqual(list(observers), [3, 5])
        self.assertEqual([i for i, c in enumerate(cells) if c['cell_type'] == 'code'], [3, 5])
        self.assertEqual(len(cells), 8)
        self.assertEqual(lifecycle['cleanup_timeout_seconds'], 5)
        for descriptor in [contract['witness'], contract['reference']]:
            self.assertEqual(hashlib.sha256((root/descriptor['path']).read_text(encoding='utf-8').encode()).hexdigest(), descriptor['sha256'])
        namespace = {}
        exec(compile(contract['preamble'], 'authored-reference-bootstrap', 'exec'), namespace)
        self.assertEqual(namespace['_timing_reference_source'], (root/'timing_reference.py').read_text(encoding='utf-8'))
        self.assertEqual(namespace['_timing_reference'].schedule(ref.fixtures()[0]['ops'])['makespan_dt'], 8)

    def test_all_sdk_gate_paths_are_relative_and_extension_is_bound(self):
        from pathlib import PurePosixPath
        from observers.ibm_timing import SOURCE_HASHES
        self.assertEqual(len(SOURCE_HASHES), 24)
        self.assertIn('_accelerate.pyd', SOURCE_HASHES)
        for path, expected in SOURCE_HASHES.items():
            self.assertFalse(PurePosixPath(path).is_absolute())
            self.assertNotIn('..', PurePosixPath(path).parts)
            self.assertEqual(len(expected), 64)
            self.assertTrue(all(c in '0123456789abcdef' for c in expected))

    def test_profile_inventory_requires_all_sixty_two_exact_pins(self):
        import hashlib
        import json
        from pathlib import Path
        import execution
        root = Path(__file__).resolve().parent
        profile = json.loads((root/'profiles/timing-win-py312.json').read_text())
        raw = (root/profile['lock']).read_text().encode()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), profile['lock_sha256'])
        pins = execution._locked_distribution_versions(raw.decode())
        self.assertEqual(len(pins), 62)
        self.assertEqual(pins['qiskit'], '2.6.1')
        self.assertIn('qiskit[all]==2.6.1', raw.decode())
        self.assertTrue(profile['exact_packages'])


class BindingPathTests(unittest.TestCase):
    """Whole callback chain over authored fake SDK objects, not a Qiskit run."""

    def run_path(self, shifted_start=False, missing_padding=False):
        import hashlib
        import sys
        import tempfile
        from pathlib import Path
        from types import ModuleType, SimpleNamespace
        from unittest.mock import patch
        from observers.ibm_timing import bind_timing
        temporary = tempfile.TemporaryDirectory(prefix='timing-binding-unit-')
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name)
        (output/'qiskit').mkdir()
        (output/'qiskit/source.py').write_bytes(b'authored fake SDK')
        modules = {}
        names = ['qiskit', 'qiskit.visualization', 'qiskit.visualization.timeline',
            'qiskit.visualization.timeline.core', 'qiskit.visualization.timeline.plotters',
            'qiskit.transpiler', 'qiskit.transpiler.passes', 'qiskit.transpiler.passes.scheduling',
            'qiskit.transpiler.passes.scheduling.scheduling', 'qiskit.transpiler.passes.scheduling.scheduling.alap',
            'qiskit.transpiler.passes.scheduling.scheduling.base_scheduler',
            'qiskit.transpiler.passes.scheduling.padding', 'qiskit.transpiler.passes.scheduling.padding.base_padding']
        for name in names:
            modules[name] = ModuleType(name)
            modules[name].__path__ = []
        qiskit, timeline = modules['qiskit'], modules['qiskit.visualization.timeline']
        modules['qiskit.visualization'].timeline = timeline
        class Circuit:
            def __init__(self, qubits, clbits, specs, layout=None, times=None):
                self.qubits, self.clbits, self.layout = qubits, clbits, layout
                self.global_phase, self._op_start_times = 0, times
                self.data = []
                for name, qs, cs, duration in specs:
                    op = SimpleNamespace(name=name, params=[duration] if name=='delay' else [],
                                         unit='dt', duration=duration)
                    self.data.append(SimpleNamespace(operation=op, qubits=[qubits[q] for q in qs], clbits=[clbits[c] for c in cs]))
            def find_bit(self, bit):
                return SimpleNamespace(index=(self.qubits if bit in self.qubits else self.clbits).index(bit))
            @property
            def op_start_times(self):
                return self._op_start_times
        class Node:
            def __init__(self, instruction):
                self.op, self.name = instruction.operation, instruction.operation.name
                self.qargs, self.cargs = instruction.qubits, instruction.clbits
        class Dag:
            def __init__(self, circuit):
                self.qubits, self.clbits = circuit.qubits, circuit.clbits
                self.nodes = [Node(i) for i in circuit.data]
                self.edges = {}; last = {}
                for node in self.nodes:
                    wires = node.qargs + node.cargs
                    self.edges[node] = list(dict.fromkeys(last[w] for w in wires if w in last))
                    for wire in wires: last[wire] = node
            def topological_op_nodes(self): return iter(self.nodes)
            def predecessors(self, node): return iter(self.edges[node])
            def find_bit(self, bit): return SimpleNamespace(index=(self.qubits if bit in self.qubits else self.clbits).index(bit))
        class Target:
            dt=1.; granularity=1; min_length=1; pulse_alignment=1; acquire_alignment=1
            def get(self, name):
                if name == 'h': return {(0,): SimpleNamespace(duration=2.)}
                if name == 'cx': return {(0,1): SimpleNamespace(duration=3.)}
                if name == 'measure': return {(0,): SimpleNamespace(duration=4.), (1,): SimpleNamespace(duration=7.)}
                return None
        class Scheduler:
            def _get_node_duration(self, node, dag): return node.op.duration
        class Alap(Scheduler):
            def __init__(self): self.property_set={'time_unit':'dt'}
            def run(self, dag):
                starts = [0,2,5,8,5] if len(dag.nodes)==5 else [0,2]
                if shifted_start: starts[0] = 1
                for node in dag.nodes: self._get_node_duration(node,dag)
                self.property_set['node_start_time'] = dict(zip(dag.nodes, starts))
                return dag
        class Padding:
            def __init__(self, property_set): self.property_set=property_set
            def run(self, dag):
                measured = len(dag.nodes)==5
                horizon = 12 if measured else 5
                specs = [(n.name,[dag.qubits.index(q) for q in n.qargs],[dag.clbits.index(c) for c in n.cargs],n.op.duration) for n in dag.nodes]
                times = [self.property_set['node_start_time'][n] for n in dag.nodes]
                delays = [(1,0,2)] + ([(0,5,3)] if measured else []) + [(q,0,horizon) for q in (2,3,4)]
                if missing_padding: delays=delays[:-1]
                for q,start,duration in delays:
                    specs.append(('delay',[q],[],duration));times.append(start)
                circuit=Circuit(dag.qubits,dag.clbits,specs,times=times)
                padded=Dag(circuit);padded._duration=horizon;padded.circuit=circuit
                self.property_set['node_start_time']=dict(zip(padded.nodes,times))
                return padded
        def transpile(program, **kwargs):
            dag=Dag(program);analysis=Alap();analysis.run(dag)
            return Padding(analysis.property_set).run(dag).circuit
        qiskit.transpile=transpile
        class Canvas:
            def load_program(self, program, target):
                scheduled=qiskit.transpile(program,scheduling_method='alap',target=target,optimization_level=0)
                datum=SimpleNamespace(data_type='gate',xvals=[0,2],yvals=[0,1],bits=[scheduled.qubits[0]],meta=None,styles={})
                self._collections={'local-key':datum};self.collections=list(self._collections.items())
                self.assigned_coordinates={q:float(i) for i,q in enumerate(scheduled.qubits)}
                self.time_range=(0,12);self.formatter={}
        class Plotter:
            def __init__(self, canvas): self.canvas=canvas;self.figure=object()
            def get_image(self): return self.figure
        def draw(program, target=None):
            canvas=Canvas();canvas.load_program(program=program,target=target)
            return Plotter(canvas=canvas).get_image()
        timeline.draw=draw
        modules['qiskit.visualization.timeline.core'].DrawerCanvas=Canvas
        modules['qiskit.visualization.timeline.plotters'].MplPlotter=Plotter
        modules['qiskit.transpiler.passes.scheduling.scheduling.alap'].ALAPScheduleAnalysis=Alap
        modules['qiskit.transpiler.passes.scheduling.scheduling.base_scheduler'].BaseScheduler=Scheduler
        modules['qiskit.transpiler.passes.scheduling.padding.base_padding'].BasePadding=Padding
        namespace={};retained=[]
        with patch.dict(sys.modules,modules),patch('sysconfig.get_path',return_value=str(output)):
            capture=bind_timing(ref,namespace,{'source.py':hashlib.sha256(b'authored fake SDK').hexdigest()})
            capture.output=output
            for measured in (False,True):
                source_bits=[object(),object()];physical=[object() for _ in range(5)];clbits=[object(),object()] if measured else []
                specs=[('h',[0],[],2),('cx',[0,1],[],3)]
                if measured: specs += [('barrier',[0,1],[],0),('measure',[0],[0],4),('measure',[1],[1],7)]
                source=Circuit(source_bits,clbits,specs)
                layout=SimpleNamespace(_input_qubit_count=2,_output_qubit_list=physical,
                    input_qubit_mapping={b:i for i,b in enumerate(source_bits)},
                    final_index_layout=lambda **kw:[0,1],initial_index_layout=lambda **kw:[0,1],routing_permutation=lambda:list(range(5)))
                program=Circuit(physical,clbits,specs,layout=layout)
                namespace.update(qc=source,isa_circuit=program,draw=timeline.draw)
                figure=namespace['draw'](program,target=Target())
                retained.append(figure)
                try: capture.checkpoint()
                except ValueError:
                    self.assertIs(timeline.draw,draw)
                    self.assertIs(namespace['draw'],draw)
                    return capture,retained,False
            capture.cleanup()
            self.assertIs(timeline.draw,draw)
            return capture,retained,True

    def test_full_two_cell_callback_path_with_hand_schedules(self):
        capture,figures,accepted=self.run_path()
        self.assertTrue(accepted)
        result=capture.summary()
        self.assertTrue(result['accepted'])
        self.assertEqual([r['horizon'] for r in result['observations']],[5,12])
        self.assertEqual([r['acceptance']['drawer_state']['measurement_mapping'] for r in result['observations']],[[],[[0,0],[1,1]]])
        self.assertEqual(len(figures),2)

    def test_shifted_actual_schedule_fails_after_original_draw(self):
        capture,figures,accepted=self.run_path(shifted_start=True)
        self.assertFalse(accepted)
        self.assertEqual(len(figures),1)
        self.assertTrue(capture.records[0]['data']['original_draw_succeeded'])
        self.assertEqual(capture.records[0]['data']['acceptance_error']['message'],'ALAP_START_MISMATCH')

    def test_missing_unused_wire_padding_fails_after_original_draw(self):
        capture,figures,accepted=self.run_path(missing_padding=True)
        self.assertFalse(accepted)
        self.assertEqual(len(figures),1)
        self.assertIn('PADDING_COVERAGE_MISMATCH',capture.records[0]['data']['acceptance_error']['message'])


class AuthoredControlTests(unittest.TestCase):
    def run_controls(self, bad_mapping=False, fail_at=None):
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace
        from observers.ibm_timing import authored_layout_controls
        temporary = tempfile.TemporaryDirectory(prefix='timing-controls-unit-')
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name)
        class Circuit:
            def __init__(self, width):
                self.qubits=[object() for _ in range(width)];self.clbits=[];self.data=[];self.layout=None;self.global_phase=0
            def find_bit(self, bit):return SimpleNamespace(index=self.qubits.index(bit))
            def add(self,name,qs,params=None):
                self.data.append(SimpleNamespace(operation=SimpleNamespace(name=name,params=params or []),
                    qubits=[self.qubits[q] for q in qs],clbits=[]))
            def x(self,q):self.add('x',[q])
            def h(self,q):self.add('h',[q])
            def cx(self,c,t):self.add('cx',[c,t])
            def rz(self,theta,q):self.add('rz',[q],[theta])
        calls=[]
        def transpile(circuit,**kwargs):
            calls.append(kwargs)
            if len(calls)==fail_at:raise RuntimeError('AUTHORED_TRANSPILE_FAILURE')
            actual=[3,1] if len(circuit.qubits)==2 else [2,4,0,1,3]
            output=Circuit(5)
            for inst in circuit.data:
                output.add(inst.operation.name,[actual[circuit.find_bit(q).index] for q in inst.qubits],list(inst.operation.params))
            reported=actual[:]
            if bad_mapping and len(actual)==5:
                reported[1],reported[3]=reported[3],reported[1]
            output.layout=SimpleNamespace(_input_qubit_count=len(circuit.qubits),_output_qubit_list=output.qubits,
                input_qubit_mapping={q:i for i,q in enumerate(circuit.qubits)},
                final_index_layout=lambda **kw:reported,initial_index_layout=lambda **kw:reported,
                routing_permutation=lambda:list(range(5)))
            return output
        capture=SimpleNamespace(summary=lambda:{'accepted':True},outer_restored=True,hooks=[],
                                records=[{'target':object()},{'target':object()}],output=output)
        api=SimpleNamespace(QuantumCircuit=Circuit,transpile=transpile)
        try:result=authored_layout_controls(capture,ref,api)
        except Exception as error:return output,None,calls,error
        return output,result,calls,None

    def test_six_independent_controls_use_two_nontrivial_layouts(self):
        output,result,calls,error=self.run_controls()
        self.assertIsNone(error)
        self.assertTrue(result['accepted'])
        self.assertEqual(len(calls),12)
        self.assertEqual(len(result['cases']),6)
        self.assertTrue(all(case['composed_layout']==[1,4] for case in result['cases']))
        self.assertEqual([c['name'] for c in result['cases'][:3]],['logical-q0-one','logical-q1-one','phase-bell'])
        self.assertTrue(all(c['seed_transpiler']==1731 for c in calls))

    def test_wrong_reported_layout_fails_and_retains_raw_density(self):
        import json
        output,result,calls,error=self.run_controls(bad_mapping=True)
        self.assertEqual(str(error),'DENSITY_MISMATCH')
        saved=json.loads((output/'timing-controls.json').read_text())
        self.assertEqual(saved['state'],'failed')
        self.assertFalse(saved['accepted'])
        self.assertIn('actual_density',saved['cases'][0])
        self.assertIn('expected_density',saved['cases'][0])
        self.assertEqual(len(calls),2)

    def test_later_control_failure_preserves_prior_case(self):
        import json
        output,result,calls,error=self.run_controls(fail_at=3)
        self.assertEqual(str(error),'AUTHORED_TRANSPILE_FAILURE')
        saved=json.loads((output/'timing-controls.json').read_text())
        self.assertEqual(saved['cases'][0]['state'],'succeeded')
        self.assertEqual(saved['cases'][1]['state'],'failed')
        self.assertIn('source_operations',saved['cases'][1])
        self.assertFalse(saved['accepted'])


class IsaBridgeTests(unittest.TestCase):
    def test_actual_second_layout_maps_isa_to_pre_alap(self):
        from observers.ibm_timing import match_isa_to_pre_alap
        isa = [operation('h',[3]), operation('cx',[3,1]), operation('measure',[3],clbits=[0])]
        pre = [dict(id='n0',**operation('h',[1])), dict(id='n1',**operation('cx',[1,4])),
               dict(id='n2',**operation('measure',[1],clbits=[0]))]
        self.assertEqual(match_isa_to_pre_alap(isa,pre,[2,4,0,1,3]),['isa0','isa1','isa2'])
        with self.assertRaises(ValueError):
            match_isa_to_pre_alap(isa,pre,list(range(5)))

    def test_identity_and_canceling_gates_cannot_hide_behind_bell_density(self):
        from observers.ibm_timing import match_isa_to_pre_alap
        isa = [operation('h',[0]),operation('cx',[0,1])]
        for extra in [[operation('id',[0])], [operation('x',[0]),operation('x',[0])]]:
            with self.subTest(extra=extra):
                altered = isa + extra
                state,_ = ref.scalar_state(altered,5)
                ref.check_density(ref.reduced_density(state,[0,1]),ref.bell_density())
                with self.assertRaisesRegex(ValueError,'UNEXPLAINED_OPERATION_TRANSFORMATION'):
                    match_isa_to_pre_alap(isa,[dict(op,id='n'+str(i)) for i,op in enumerate(altered)],list(range(5)))

    def test_lost_timing_directive_is_rejected(self):
        from observers.ibm_timing import match_isa_to_pre_alap
        isa = [operation('h',[0]),operation('cx',[0,1]),operation('barrier',[0,1])]
        with self.assertRaisesRegex(ValueError,'MISSING_ORIGINAL_OPERATION'):
            match_isa_to_pre_alap(isa,[dict(op,id='n'+str(i)) for i,op in enumerate(isa[:2])],list(range(5)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
