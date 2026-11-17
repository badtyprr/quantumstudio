"""Authored native QB013 witnesses, separate from unchanged source execution.

Importing this module uses only the standard library. Native API binding and
execution are explicit; scalar expectations never come from an SDK.
"""
import math


def _bind_native_api(site_packages, importer):
    """Verify pinned bytes and module origins before exposing native APIs.

    These additional gates supplement the observer's gates and the execution
    environment inventory. They do not establish compiled-source correspondence.
    """
    import hashlib
    from pathlib import Path
    from types import SimpleNamespace
    root = Path(site_packages).resolve(strict=True)
    def verify():
        for relative, expected in NATIVE_SOURCE_HASHES.items():
            path = (root / relative).resolve(strict=True)
            if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError('NATIVE_SOURCE_CHANGED:' + relative)
    verify()
    modules = {}
    for name, relative in NATIVE_MODULE_PATHS.items():
        module = importer(name)
        origin = getattr(module, '__file__', None)
        if origin is None or Path(origin).resolve(strict=True) != (root / relative).resolve(strict=True):
            raise ValueError('NATIVE_MODULE_ORIGIN:' + name)
        modules[name] = module
    api = SimpleNamespace(
        Statevector=modules['qiskit.quantum_info.states.statevector'].Statevector,
        CirqCircuit=modules['cirq.circuits.circuit'].Circuit,
        CirqMoment=modules['cirq.circuits.moment'].Moment,
        Simulator=modules['cirq.sim.sparse_simulator'].Simulator,
        MeasurementGate=modules['cirq.ops.measurement_gate'].MeasurementGate,
        Tableau=modules['stim'].Tableau, complex128=modules['numpy'].complex128,
        ProgramConversionError=modules['qbraid.transpiler.exceptions'].ProgramConversionError,
        source_evidence=dict(source_hashes=dict(NATIVE_SOURCE_HASHES),
                             module_paths=dict(NATIVE_MODULE_PATHS), compiled_source_correspondence='unproved'))
    for name in ('Statevector', 'CirqCircuit', 'CirqMoment', 'Simulator', 'MeasurementGate', 'Tableau', 'complex128', 'ProgramConversionError'):
        if not isinstance(getattr(api, name), type):
            raise ValueError('NATIVE_API_CLASS:' + name)
    verify()
    return api


def bind_native_api(site_packages):
    from importlib import import_module
    return _bind_native_api(site_packages, import_module)


def build_control_cases(quantum_circuit, reference):
    """Build separately authored circuits and independent finite expectations.

    The Boolean oracle is synthesized only when its complete truth table is
    affine. Walsh expectations are computed independently from that table.
    Program objects stay outside serializable evidence in the returned pairs.
    """
    controls = []
    for name, operation, expected in (
            ('onehot-q0', 'x0', [0, 1, 0, 0]),
            ('onehot-q1', 'x1', [0, 0, 1, 0]),
            ('bell', 'bell', [1/math.sqrt(2), 0, 0, 1/math.sqrt(2)]),
            ('phase-bell', 'phase', [1/math.sqrt(2), 0, 0, -1/math.sqrt(2)])):
        circuit = quantum_circuit(2, 2)
        if operation.startswith('x'):
            circuit.x(int(operation[-1]))
        else:
            circuit.h(0); circuit.cx(0, 1)
            if operation == 'phase': circuit.z(0)
        circuit.measure(0, 0); circuit.measure(1, 1)
        probabilities = {i: abs(value)**2 for i, value in enumerate(expected) if value}
        controls.append((circuit, dict(id=name, family='mapping-and-coherence', qubits=2,
            measured_qubits=[0, 1], expected_state=expected, expected_probabilities=probabilities,
            shots=4096, seed=1731, frequency_tolerance=0.05 if len(probabilities) > 1 else 0.0)))
    for case in reference.cases():
        n = case['qubits']; table = case['truth_table']; constant = table[0]
        coefficients = [table[1 << q] ^ constant for q in range(n)]
        if any(value != (constant ^ (sum(coefficients[q]*((x >> q) & 1) for q in range(n)) % 2))
               for x, value in enumerate(table)):
            raise ValueError('UNSUPPORTED_NONAFFINE_CONTROL_ORACLE')
        circuit = quantum_circuit(n+1, n)
        circuit.x(n)
        for q in range(n+1): circuit.h(q)
        if constant: circuit.x(n)
        for q, coefficient in enumerate(coefficients):
            if coefficient: circuit.cx(q, n)
        for q in range(n): circuit.h(q)
        for q in range(n): circuit.measure(q, q)
        amplitudes = [value/case['amplitude_denominator'] for value in case['amplitude_numerators']]
        expected = [amplitudes[data]*(-1 if ancilla else 1)/math.sqrt(2)
                    for ancilla in range(2) for data in range(1 << n)]
        controls.append((circuit, dict(id=case['id'], family=case['family'], qubits=n+1,
            measured_qubits=list(range(n)), expected_state=expected,
            expected_probabilities={case['deterministic_integer']:1.0}, shots=128, seed=1731,
            frequency_tolerance=0.0, truth_table=list(table), oracle_constant=constant,
            oracle_linear_coefficients=coefficients)))
    return controls


def audit_authored_samples(rows, occurrence_to_logical, case):
    """Audit every authored Stim measurement row under a proven wire mapping."""
    measured = case['measured_qubits']; shots = case['shots']
    if (type(rows) is not list or len(rows) != shots or type(shots) is not int or shots <= 0
            or measured != list(range(len(measured))) or not measured):
        raise ValueError('AUTHORED_SAMPLE_SCOPE')
    mapping = occurrence_to_logical
    if (not isinstance(mapping, (list, tuple)) or len(mapping) != len(measured)
            or any(type(q) is not int for q in mapping) or sorted(mapping) != measured):
        raise ValueError('AUTHORED_SAMPLE_MAPPING')
    counts = {}
    for row in rows:
        if type(row) is not list or len(row) != len(mapping) or any(type(bit) is not bool for bit in row):
            raise ValueError('AUTHORED_SAMPLE_ROW')
        outcome = sum(int(bit) << mapping[i] for i, bit in enumerate(row))
        counts[outcome] = counts.get(outcome, 0)+1
    expected = case['expected_probabilities']; tolerance = case['frequency_tolerance']
    if (type(expected) is not dict or not expected or any(type(key) is not int or not 0 <= key < 1 << len(measured)
            or type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= 1
            for key, value in expected.items()) or abs(sum(expected.values())-1) > 1e-12
            or type(tolerance) not in (int, float) or not math.isfinite(tolerance) or not 0 <= tolerance <= 0.05):
        raise ValueError('AUTHORED_SAMPLE_EXPECTATION')
    residuals = {key:abs(counts.get(key, 0)/shots-value) for key, value in expected.items()}
    return dict(raw_rows=rows, shots=shots, counts={str(k):v for k,v in sorted(counts.items())},
                occurrence_to_logical=list(mapping), frequency_tolerance=tolerance,
                frequency_residuals={str(k):v for k,v in residuals.items()},
                accepted=set(counts) <= set(expected) and all(value <= tolerance for value in residuals.values()),
                authored=True, original_sample=False, coherence_verified=False)


def sample_evidence(value):
    """Preserve valid rows exactly and tag anomalous values for strict JSON."""
    if type(value) is list:
        return [sample_evidence(item) for item in value]
    if value is None or type(value) in (bool, int, str):
        return value
    if type(value) is float:
        return value if math.isfinite(value) else dict(nonfinite=
            'NaN' if math.isnan(value) else ('Infinity' if value > 0 else '-Infinity'))
    if type(value) is complex:
        return dict(complex_components=[sample_evidence(value.real), sample_evidence(value.imag)])
    return dict(unsupported_type=type(value).__module__+'.'+type(value).__qualname__, representation=repr(value))


def observe_wrapped_nonclifford(capture, graph, native_api, qid, journal, checkpoint):
    """Authored one-edge T rejection through qBraid, distinct from direct evidence."""
    capture.require_complete()
    if capture.api.converter_module.ProgramConversionError is not native_api.ProgramConversionError:
        raise ValueError('WRAPPED_ERROR_CLASS_IDENTITY')
    operation = capture.api.ZPowGate(exponent=0.25).on(qid)
    program = native_api.CirqCircuit(operation)
    expected = (f"Don't know how to translate {operation!r} into stim gates.\n"
                "- It doesn't have a _decompose_ method that returns stim-compatible operations.\n"
                "- It doesn't have a _stim_conversion_ method.\n")
    report = dict(state='running', authored=True, input=capture.controller.snapshot(program),
                  expected_inner_type='TypeError', expected_inner_message=expected,
                  explicit_path_limits=dict(max_path_attempts=1, max_path_depth=1))
    checkpoint(report)
    controller = type(capture.controller)(capture.api.transpile, capture.api,
                                         capture.controller.snapshot, journal)
    error = None
    try:
        returned = controller.wrapper(program, 'stim', conversion_graph=graph,
                                      max_path_attempts=1, max_path_depth=1)
        report['unexpected_return_type'] = type(returned).__module__+'.'+type(returned).__qualname__
    except Exception as caught:
        error = caught
        report['actual_error'] = dict(type=type(caught).__name__, message=str(caught), args_repr=repr(caught.args))
    report['conversion_calls'] = controller.records
    checkpoint(report)
    try:
        controller.require_complete()
        rows = controller.records
        if len(rows) != 1 or rows[0]['state'] != 'failed':
            raise ValueError('WRAPPED_ERROR_TRANSPILE_DISPOSITION')
        row = rows[0]; edges = row['conversions']
        if (row['input'] != row['input_after'] or row['graph_before'] != row['graph_after']
                or capture.controller.snapshot(program) != report['input']):
            raise ValueError('WRAPPED_ERROR_INPUT_OR_GRAPH_MUTATED')
        if (len(edges) != 1 or edges[0]['source'] != 'cirq' or edges[0]['target'] != 'stim'
                or edges[0]['state'] != 'failed' or edges[0]['function_identities'] != ['cirq_to_stim']
                or edges[0]['single_program_positional_call'] is not True
                or edges[0].get('error') != dict(type='TypeError', message=expected)):
            raise ValueError('WRAPPED_ERROR_INNER_MISMATCH')
        if (type(error) is not native_api.ProgramConversionError
                or not str(error).startswith("Failed to convert 'cirq' to 'stim'")
                or 'TypeError: '+expected not in str(error)):
            raise ValueError('WRAPPED_ERROR_OUTER_MISMATCH')
        report['state'] = 'succeeded'
    except Exception as failure:
        report['state'] = 'failed'
        report['verification_error'] = dict(type=type(failure).__name__, message=str(failure))
    checkpoint(report)
    return report


def run_authored_controls(capture, graph, native_api, reference, audit, journal_factory, checkpoint):
    """Run authored controls through the actual graph after original cleanup.

    Each control has its own conversion journal. Original notebook observations
    are never reused as control observations or amended by these calls.
    """
    capture.require_complete()
    snapshot = capture.controller.snapshot
    report = dict(state='running', controls=[], authored=True, original_notebook_execution=False)
    checkpoint(report)
    for index, (program, case) in enumerate(build_control_cases(capture.api.QuantumCircuit, reference)):
        metadata = dict(case, expected_state=[[complex(x).real, complex(x).imag] for x in case['expected_state']])
        row = dict(case=metadata, state='running')
        report['controls'].append(row); checkpoint(report)
        controller = type(capture.controller)(capture.api.transpile, capture.api, snapshot, journal_factory(index))
        try:
            result = controller.wrapper(program, 'stim', conversion_graph=graph)
            controller.require_complete()
            if len(controller.records) != 1 or controller.records[0]['state'] != 'succeeded':
                raise ValueError('AUTHORED_CONTROL_TRANSPILE_COUNT')
            observed = controller.records[0]
            if (observed['input'] != observed['input_after'] or observed['graph_before'] != observed['graph_after']):
                raise ValueError('AUTHORED_CONTROL_INPUT_OR_GRAPH_MUTATED')
            row['conversion'] = observed
            analysis = audit.analyze_conversion_states(reference, observed['input'], observed['output'],
                observed['conversions'], observed['parsers'], case['expected_state'])
            row['reference_analysis'] = analysis; checkpoint(report)
            if not analysis['reference_semantic_acceptance']:
                raise ValueError('AUTHORED_CONTROL_REFERENCE_MISMATCH')
            outputs = controller.verified_native_outputs(0)
            if len(outputs) != 3 or outputs[2] is not result:
                raise ValueError('AUTHORED_CONTROL_NATIVE_ENDPOINT')
            def native_checkpoint(value):
                row['native_analysis'] = value; checkpoint(report)
            native = observe_native_states(native_api, reference, snapshot,
                dict(qiskit=program, cirq=outputs[1], stim=result), native_checkpoint,
                required_qubits=case['qubits'])
            if native['state'] != 'succeeded':
                raise ValueError('AUTHORED_CONTROL_NATIVE_MISMATCH')
            samples = result.compile_sampler(seed=case['seed']).sample(shots=case['shots'])
            row['sample_container'] = dict(type=type(samples).__module__+'.'+type(samples).__qualname__,
                dtype=str(getattr(samples, 'dtype', 'unavailable')),
                shape=sample_evidence(getattr(samples, 'shape', None)))
            checkpoint(report)
            sample_rows = samples.tolist()
            row['raw_samples'] = sample_evidence(sample_rows)
            checkpoint(report)
            row['sampling'] = audit_authored_samples(sample_rows,
                analysis['route']['occurrence_to_logical'], case)
            checkpoint(report)
            controller.verified_native_outputs(0)
            if snapshot(program) != observed['input']:
                raise ValueError('AUTHORED_CONTROL_INPUT_MUTATED')
            if not row['sampling']['accepted']:
                raise ValueError('AUTHORED_CONTROL_SAMPLING_MISMATCH')
            row['state'] = 'succeeded'
        except Exception as error:
            row['state'] = 'failed'; row['error'] = dict(type=type(error).__name__, message=str(error))
            checkpoint(report)
            break
        checkpoint(report)
    report['state'] = 'succeeded' if len(report['controls']) == 18 and all(
        row['state'] == 'succeeded' for row in report['controls']) else 'failed'
    checkpoint(report)
    return report


def compare_native_state(expected, actual, actual_to_expected, precision):
    """Compare raw native pure-state density entries without renormalization.

    Stim's pinned tableau vector is complex64. Its fixed rounding allowance
    is separate from the strict scalar reference and complex128 observations.
    This proves only the specified zero-input state, modulo global phase.
    """
    limits = {'complex64': (1e-6, 1e-6), 'complex128': (1e-12, 1e-10)}
    if precision not in limits:
        raise ValueError('NATIVE_STATE_PRECISION')
    norm_tolerance, density_tolerance = limits[precision]
    size = len(expected)
    if size < 2 or size > 16 or size & (size-1) or len(actual) != size:
        raise ValueError('NATIVE_STATE_DIMENSION')
    for vector in (expected, actual):
        if any(type(x) not in (int, float, complex) or not math.isfinite(complex(x).real)
               or not math.isfinite(complex(x).imag) for x in vector):
            raise ValueError('NATIVE_STATE_NONFINITE')
    expected_norm = sum(abs(x)**2 for x in expected)
    actual_norm = sum(abs(x)**2 for x in actual)
    if abs(expected_norm-1) > 1e-12 or abs(actual_norm-1) > norm_tolerance:
        raise ValueError('NATIVE_STATE_NORMALIZATION')
    n = size.bit_length()-1
    mapping = actual_to_expected
    if (not isinstance(mapping, (list, tuple)) or len(mapping) != n
            or any(type(q) is not int for q in mapping) or sorted(mapping) != list(range(n))):
        raise ValueError('NATIVE_STATE_MAPPING')
    reordered = [0j]*size
    for basis, amplitude in enumerate(actual):
        destination = sum(((basis >> q) & 1) << mapping[q] for q in range(n))
        reordered[destination] = complex(amplitude)
    residual = max(abs(complex(expected[i])*complex(expected[j]).conjugate()
                       -reordered[i]*reordered[j].conjugate())
                   for i in range(size) for j in range(size))
    return dict(equivalent=residual <= density_tolerance, max_density_error=residual,
                density_tolerance=density_tolerance, norm_tolerance=norm_tolerance,
                actual_norm_squared=actual_norm, precision=precision,
                actual_to_expected=list(mapping),
                actual_state=[[complex(x).real, complex(x).imag] for x in actual],
                expected_state=[[complex(x).real, complex(x).imag] for x in expected],
                renormalized=False, global_phase_sensitive=False,
                all_input_unitary_equivalence=False)


def observe_native_states(api, reference, snapshot, programs, checkpoint, required_qubits=2):
    """Observe actual objects through separately authored premeasurement copies.

    Raw observations and errors are checkpointed before any acceptance decision.
    This helper does not establish conversion provenance or wire correspondence.
    It accepts only the finite terminal-measurement semantics already understood
    by the independent scalar reference, and checks original objects afterward.
    """
    if set(programs) != {'qiskit', 'cirq', 'stim'}:
        raise ValueError('NATIVE_PROGRAM_SET')
    before = {name: snapshot(program) for name, program in programs.items()}
    expected = {name: reference.state_from_snapshot(value) for name, value in before.items()}
    if (type(required_qubits) is not int or not 1 <= required_qubits <= 4
            or any(value['qubits'] != required_qubits for value in expected.values())):
        raise ValueError('NATIVE_FINITE_QUBIT_SCOPE')
    report = dict(state='running', observations={}, errors=[], original_snapshots=before,
                  authored_premeasurement_analysis=True, overall_semantic_acceptance=False)
    checkpoint(report)
    for name, program in programs.items():
        row = dict(state='running')
        report['observations'][name] = row
        checkpoint(report)
        try:
            if name == 'qiskit':
                copied = program.remove_final_measurements(inplace=False)
                if list(copied.qubits) != list(program.qubits) or copied.num_qubits != required_qubits:
                    raise ValueError('NATIVE_QISKIT_COPY_WIRES')
                if any(item.operation.name == 'measure' for item in copied.data):
                    raise ValueError('NATIVE_QISKIT_MEASUREMENT_REMAINS')
                vector = api.Statevector.from_instruction(copied).data
                row['adaptation'] = 'authored remove_final_measurements(inplace=False); original unchanged'
            elif name == 'cirq':
                qids = sorted(program.all_qubits())
                # Terminal-measurement semantics were gated above, including
                # invert masks. Strip quantum measurements, not readout flips.
                copied = api.CirqCircuit(api.CirqMoment(
                    op for op in moment.operations if not isinstance(op.gate, api.MeasurementGate))
                    for moment in program)
                vector = api.Simulator(dtype=api.complex128).simulate(
                    copied, qubit_order=list(reversed(qids)), initial_state=0).final_state_vector
                row['adaptation'] = 'authored terminal MeasurementGate filtering; readout inversion remains separate'
                row['axis_order'] = 'reverse of actual sorted Qids, producing little-endian sorted-Qid indices'
            else:
                copied = program.copy()
                tableau = api.Tableau.from_circuit(copied, ignore_measurement=True,
                                                 ignore_noise=False, ignore_reset=False)
                if len(tableau) != required_qubits:
                    raise ValueError('NATIVE_STIM_TABLEAU_WIDTH')
                vector = tableau.to_state_vector(endian='little')
                row['adaptation'] = 'authored tableau of copy ignoring previously validated terminal measurements only'
            row['dtype'] = str(vector.dtype)
            values = vector.tolist()
            def json_component(value):
                if math.isfinite(value):
                    return value
                return {'nonfinite': 'NaN' if math.isnan(value) else ('Infinity' if value > 0 else '-Infinity')}
            row['raw_state'] = [[json_component(complex(x).real), json_component(complex(x).imag)]
                                for x in values]
            precision = 'complex64' if name == 'stim' else 'complex128'
            if row['dtype'] != precision:
                raise ValueError('NATIVE_UNEXPECTED_DTYPE')
            row['comparison'] = compare_native_state(expected[name]['state'], values, list(range(required_qubits)), precision)
            row['state'] = 'succeeded'
        except Exception as error:
            row['state'] = 'failed'
            row['error'] = dict(type=type(error).__name__, message=str(error))
        finally:
            try:
                after = snapshot(program)
                row['original_snapshot_after'] = after
                row['original_unchanged'] = after == before[name]
                if not row['original_unchanged']:
                    report['errors'].append(dict(program=name, type='NativeObservationMutatedOriginal'))
            except Exception as error:
                report['errors'].append(dict(program=name, stage='snapshot_after',
                                             type=type(error).__name__, message=str(error)))
            checkpoint(report)
        if row['state'] != 'succeeded' or report['errors']:
            break
    report['final_original_snapshots'] = {}
    for name, program in programs.items():
        try:
            final = snapshot(program)
            report['final_original_snapshots'][name] = final
            if final != before[name]:
                report['errors'].append(dict(program=name, stage='final_snapshot',
                                             type='NativeObservationMutatedOriginal'))
        except Exception as error:
            report['errors'].append(dict(program=name, stage='final_snapshot',
                                         type=type(error).__name__, message=str(error)))
    report['state'] = 'succeeded' if (len(report['observations']) == 3 and not report['errors']
        and all(row['state'] == 'succeeded' and row['original_unchanged']
                and row['comparison']['equivalent'] for row in report['observations'].values())) else 'failed'
    checkpoint(report)
    return report


NATIVE_MODULE_PATHS = {'qiskit.quantum_info.states.statevector': 'qiskit/quantum_info/states/statevector.py', 'cirq.circuits.circuit': 'cirq/circuits/circuit.py', 'cirq.circuits.moment': 'cirq/circuits/moment.py', 'cirq.sim.sparse_simulator': 'cirq/sim/sparse_simulator.py', 'cirq.ops.measurement_gate': 'cirq/ops/measurement_gate.py', 'stim': 'stim/__init__.py', 'numpy': 'numpy/__init__.py'}
NATIVE_SOURCE_HASHES = {'qiskit/circuit/quantumcircuit.py': 'd70c1c9350a94c2e07ae9fef24746a95633c36846719d8789c4a98185f11b281', 'qiskit/quantum_info/states/statevector.py': '99a23bd835a54b2ce02327f3ce6d30c44961d4a6bd192ab886f30ff0405bf7f4', 'qiskit/transpiler/passes/utils/remove_final_measurements.py': 'a5ed4511ab3c047f59666c02cc6bcc82839eb1c06285b0c0e5dcefc26ce0cd43', 'qiskit/_accelerate.pyd': '4fe0996035b2e0bdf169a2ad6834afe3b244bc782ef9d1f4eb824f159fe29f80', 'cirq/transformers/measurement_transformers.py': '7b01d3798f10b846025da72de17542283f9508200683739a422543a27487f1d1', 'cirq/circuits/circuit.py': 'ade0cba8b323dd264cfb3fbbbcb661bf2e174539e690ad078a06e49c5b4c0cb0', 'cirq/sim/simulator.py': '77910532e9e3ccf013af9a773b87bcc7473e11edc17775d078e7f23d70703ec4', 'cirq/sim/state_vector.py': 'fae3c237b323a2b2997c3f8b654dfed0b77be3352098e583e1c1b1e41c41d476', 'cirq/sim/state_vector_simulator.py': 'b872bc9c4580bb4a0e9601a1c07b27c04d390716355f6184a0ca72a02e4af433', 'cirq/sim/sparse_simulator.py': '10b46141b9469c47f218c26e334419e50d33957107b96e8ba2f599fc0e937ee3', 'cirq/ops/qubit_order.py': 'da309013a6de6e1c244e987126f3df02f1a9d7a0f279eb3e7ab6cfac173889bc', 'stim/__init__.pyi': '39569e7779770c50f496a3cb46753aed748ac98c790d706479f3c280de36e28a', 'stim/__init__.py': '3a6351ab2d211ec938c659b0ceb1df786a35b5799d9d8e35b9be19ce2f193445', 'stim/_detect_machine_architecture.cp312-win_amd64.pyd': 'f1ff4f3277490e93204e7f05571676f66974ca2be7697e1ccfe48226d3a1a197', 'stim/_stim_polyfill.cp312-win_amd64.pyd': '7ca9489a5ac6f96d1c18ab4d66578372103ca6536b11448f608a3d82f41ab2dc', 'stim/_stim_sse2.cp312-win_amd64.pyd': '5e5b0cccd60266723d06c746eb8aaad18b3e72980cc5130ec4f7af46cf3c1880', 'cirq/circuits/moment.py': '83a80f80ebd1c7bb157319668f33ef77b524745944942c3b6c7ada85686b2b93', 'cirq/ops/measurement_gate.py': 'c9cf5c71bce9cbeb22e53285ef6566aeacea82cc60ffad115c25873a3d5df70f', 'numpy/__init__.py': 'ad238e76e8c6fbd56a19e6c894864cf466bd2ed76004cac89e78c019fa625607'}

NATIVE_MODULE_PATHS['qbraid.transpiler.exceptions'] = 'qbraid/transpiler/exceptions.py'
NATIVE_SOURCE_HASHES['qbraid/transpiler/exceptions.py'] = '51a5ef6482494713c25931a17b24b7cd9d9dfd6ee062a52882e260db6eb03c76'

def run_notebook_witness(capture, graph, qiskit_program, stim_program, reference, audit):
    """One authored verification entrypoint; original output audit stays on host."""
    import sys
    from pathlib import Path
    root = Path.cwd()
    journal_type = type(capture.controller.journal)
    journal = journal_type(root / 'qb013-witness.json')
    report = dict(state='running', native_accepted=False, whole_notebook_complete=False,
                  original_stdout_pending_host_audit=True, authored=True)
    def persist(): journal.write(report)
    persist()
    try:
        capture.require_complete()
        postcells = capture.controller.postcells
        if [row.get('after_original_index') for row in postcells] != [13,15,19,22] or any(
                row.get('state') != 'succeeded' for row in postcells):
            raise ValueError('ORIGINAL_POSTCELL_PROTOCOL_INCOMPLETE')
        if len(capture.controller.records) != 1:
            raise ValueError('ORIGINAL_TRANSPILE_COUNT')
        original = capture.controller.records[0]
        snapshot = capture.controller.snapshot
        if (snapshot(qiskit_program) != original['input'] or snapshot(stim_program) != original['output']):
            raise ValueError('ORIGINAL_NAMESPACE_ENDPOINT_CHANGED')
        expected = [1/math.sqrt(2),0,0,1/math.sqrt(2)]
        report['original_reference_analysis'] = audit.analyze_conversion_states(reference,
            original['input'],original['output'],original['conversions'],original['parsers'],expected)
        persist()
        if not report['original_reference_analysis']['reference_semantic_acceptance']:
            raise ValueError('ORIGINAL_REFERENCE_MISMATCH')
        outputs = capture.controller.verified_native_outputs(0)
        if len(outputs) != 3 or outputs[2] is not stim_program:
            raise ValueError('ORIGINAL_NATIVE_ENDPOINT_CHANGED')
        api = bind_native_api(Path(sys.prefix)/'Lib'/'site-packages')
        report['native_source_evidence'] = api.source_evidence; persist()
        def original_checkpoint(value): report['original_native_analysis']=value; persist()
        native = observe_native_states(api,reference,snapshot,
            dict(qiskit=qiskit_program,cirq=outputs[1],stim=stim_program),original_checkpoint)
        if native['state'] != 'succeeded': raise ValueError('ORIGINAL_NATIVE_MISMATCH')
        def controls_checkpoint(value): report['controls']=value; persist()
        controls = run_authored_controls(capture,graph,api,reference,audit,
            lambda index:journal_type(root/f'qb013-control-{index:02d}.json'),controls_checkpoint)
        if controls['state'] != 'succeeded': raise ValueError('AUTHORED_CONTROLS_FAILED')
        def negative_checkpoint(value): report['wrapped_error']=value; persist()
        negative = observe_wrapped_nonclifford(capture,graph,api,sorted(outputs[1].all_qubits())[0],
            journal_type(root/'qb013-wrapped-error.json'),negative_checkpoint)
        if negative['state'] != 'succeeded': raise ValueError('AUTHORED_WRAPPED_ERROR_FAILED')
        capture.require_complete(); capture.controller.verified_native_outputs(0)
        if snapshot(qiskit_program) != original['input'] or snapshot(stim_program) != original['output']:
            raise ValueError('ORIGINAL_CHANGED_AFTER_AUTHORED_CONTROLS')
        report.update(state='succeeded',native_accepted=True)
    except Exception as error:
        report.update(state='failed',error=dict(type=type(error).__name__,message=str(error)))
    persist()
    return dict(state=report['state'],native_accepted=report['native_accepted'],
        whole_notebook_complete=False,original_stdout_pending_host_audit=True,
        witness_artifact='qb013-witness.json',
        limitations=['Original source/setup/output/graph rendering requires host artifact audit',
                     'Finite zero-input states and authored controls, not all-input unitary equivalence',
                     'No hardware/provider execution or compiled-source correspondence'])


NATIVE_SOURCE_HASHES['cirq/ops/gate_operation.py'] = 'd28fa5916412c2d7454e8acc1d85cbffb57112f69099423a44fa65d23e60bf14'

if __name__ == '__main__':
    import json
    print(json.dumps(run_notebook_witness(_qb013_capture, graph, qiskit_circuit, stim_circuit,
                                         _qb013_reference, _qb013_audit), allow_nan=False))
