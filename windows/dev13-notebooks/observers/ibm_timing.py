"""Passive timing capture. Importing this module never imports an SDK."""
import functools
import hashlib
import json
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


class PassiveCapture:
    """Delegate once; preserve original results/errors; fail in authored checks."""

    def __init__(self, draw_owner, draw_name, hooks, begin, finish, validate, output=Path('.')):
        self.draw_owner, self.draw_name = draw_owner, draw_name
        self.original_draw = getattr(draw_owner, draw_name)
        self.hooks = [(owner, name, getattr(owner, name), before, after, label)
                      for owner, name, before, after, label in hooks]
        self.begin, self.finish, self.validate = begin, finish, validate
        self.output = Path(output)
        self.active = None
        self.records = []
        self.checkpoints = 0
        self.outer_restored = False
        self.restore_errors = []
        self.aliases = []
        self.draw_proxy = self._draw_proxy()
        setattr(draw_owner, draw_name, self.draw_proxy)

    def _diagnostic(self, label, error):
        self.active['data']['diagnostics'].append(dict(stage=label, type=type(error).__name__, message=str(error)))

    def _capture(self, label, callback, *args):
        if callback is None:
            return
        try:
            callback(self.active, *args)
        except Exception as error:
            self._diagnostic(label, error)

    def _hook_proxy(self, original, before, after, label):
        @functools.wraps(original)
        def proxy(*args, **kwargs):
            if self.active is None:
                return original(*args, **kwargs)
            counts = self.active['data']['calls']
            counts[label] = counts.get(label, 0) + 1
            self._capture(label + ':before', before, args, kwargs)
            result = original(*args, **kwargs)
            self._capture(label + ':after', after, args, kwargs, result)
            return result
        return proxy

    def _draw_proxy(self):
        @functools.wraps(self.original_draw)
        def proxy(*args, **kwargs):
            if self.active is not None:
                self._diagnostic('draw', ValueError('REENTRANT_DRAW'))
                return self.original_draw(*args, **kwargs)
            record = dict(data=dict(ordinal=len(self.records)+1, calls={}, diagnostics=[],
                                    original_draw_succeeded=False, scoped_restored=False))
            self.records.append(record)
            self.active = record
            patches = []
            try:
                self._capture('draw:begin', self.begin, args, kwargs)
                for owner, name, original, before, after, label in self.hooks:
                    try:
                        require(getattr(owner, name) is original, 'HOOK_IDENTITY_CHANGED:' + label)
                        wrapper = self._hook_proxy(original, before, after, label)
                        setattr(owner, name, wrapper)
                        patches.append((owner, name, original, wrapper, label))
                    except Exception as error:
                        self._diagnostic('install:' + label, error)
                result = self.original_draw(*args, **kwargs)
                record['data']['original_draw_succeeded'] = True
                self._capture('draw:finish', self.finish, args, kwargs, result)
                return result
            except BaseException as error:
                record['data']['draw_path_error'] = dict(type=type(error).__name__, message=str(error))
                raise
            finally:
                restored = True
                for owner, name, original, wrapper, label in reversed(patches):
                    try:
                        require(getattr(owner, name) is wrapper, 'HOOK_REPLACED_DURING_DRAW:' + label)
                    except Exception as error:
                        self._diagnostic('restore:' + label, error)
                    try:
                        setattr(owner, name, original)
                        require(getattr(owner, name) is original, 'HOOK_RESTORATION_FAILED:' + label)
                    except Exception as error:
                        restored = False
                        self._diagnostic('restore:' + label, error)
                record['data']['scoped_restored'] = restored
                self.active = None
                if len(self.records) >= 2 or not record['data']['original_draw_succeeded']:
                    self.restore()
        return proxy

    def restore(self):
        """Buffer restoration diagnostics so an original exception survives."""
        if self.outer_restored:
            return
        try:
            require(getattr(self.draw_owner, self.draw_name) is self.draw_proxy, 'DRAW_PROXY_REPLACED')
        except Exception as error:
            self.restore_errors.append(dict(type=type(error).__name__, message=str(error)))
        try:
            setattr(self.draw_owner, self.draw_name, self.original_draw)
            require(getattr(self.draw_owner, self.draw_name) is self.original_draw, 'DRAW_RESTORATION_FAILED')
            for namespace, name in self.aliases:
                if namespace.get(name) is self.draw_proxy:
                    namespace[name] = self.original_draw
            self.outer_restored = True
        except Exception as error:
            self.restore_errors.append(dict(type=type(error).__name__, message=str(error)))

    def _save(self, data):
        data['outer_restored_at_save'] = self.outer_restored
        data['outer_restore_diagnostics'] = list(self.restore_errors)
        destination = self.output / ('timing-cell-' + str(data['ordinal']) + '.json')
        temporary = destination.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        temporary.replace(destination)

    def checkpoint(self):
        expected = self.checkpoints + 1
        try:
            require(expected <= 2 and len(self.records) == expected, 'DRAW_COUNT_MISMATCH')
            record = self.records[-1]
            data = record['data']
            try:
                require(data['original_draw_succeeded'] and data['scoped_restored'], 'DRAW_OR_RESTORATION_FAILED')
                require(not data['diagnostics'] and not self.restore_errors, 'OBSERVER_CAPTURE_FAILED')
                data['acceptance'] = self.validate(record)
                require(data['acceptance'].get('accepted') is True, 'TIMING_ACCEPTANCE_FAILED')
            except Exception as error:
                data['acceptance_error'] = dict(type=type(error).__name__, message=str(error))
                raise
            finally:
                self._save(data)
            self.checkpoints += 1
        except BaseException:
            self.restore()
            for record in self.records:
                self._save(record['data'])
            raise

    def cleanup(self):
        self.restore()
        for record in self.records:
            self._save(record['data'])
        require(self.outer_restored and not self.restore_errors, 'OBSERVER_RESTORATION_FAILED')

    def summary(self):
        require(self.checkpoints == 2 and len(self.records) == 2, 'INCOMPLETE_TIMING_OBSERVATIONS')
        require(self.outer_restored and not self.restore_errors, 'OBSERVER_RESTORATION_FAILED')
        return dict(accepted=True, original_cells=[3, 5], observations=[r['data'] for r in self.records],
                    outer_restored=True, whole_notebook_complete=False,
                    external_resources='Markdown/MDX/linked content and figures require separate interpretation')


def operation_key(operation):
    return json.dumps({k: operation[k] for k in ('name', 'qubits', 'clbits', 'params')},
                      sort_keys=True, separators=(',', ':'), allow_nan=False)


def match_operation_ids(originals, later, allow_replaced_delays=False):
    """Match repeated same-wire operations by occurrence, never a lossy key map.

    Independent-wire interleaving can change. Each wire's matched order must not.
    Delay replacement is explicit; it never becomes a new oracle input.
    """
    from collections import defaultdict, deque
    queues = defaultdict(deque)
    require(len({op['id'] for op in originals}) == len(originals), 'DUPLICATE_ORIGINAL_OPERATION')
    for operation in originals:
        if allow_replaced_delays and operation['name'] == 'delay':
            continue
        queues[operation_key(operation)].append(operation['id'])
    mapping, generated = [], []
    for index, operation in enumerate(later):
        if allow_replaced_delays and operation['name'] == 'delay':
            mapping.append(None)
            generated.append(index)
            continue
        key = operation_key(operation)
        require(bool(queues[key]), 'UNEXPLAINED_OPERATION_TRANSFORMATION')
        mapping.append(queues[key].popleft())
    require(not any(queues.values()), 'MISSING_ORIGINAL_OPERATION')
    def wires(operation):
        return ['q:' + str(q) for q in operation['qubits']] + ['c:' + str(c) for c in operation['clbits']]
    expected, actual = defaultdict(list), defaultdict(list)
    for operation in originals:
        if allow_replaced_delays and operation['name'] == 'delay':
            continue
        for wire in wires(operation):
            expected[wire].append(operation['id'])
    for operation, identity in zip(later, mapping):
        if identity is None:
            continue
        for wire in wires(operation):
            actual[wire].append(identity)
    require(dict(actual) == dict(expected), 'WIRE_OPERATION_ORDER_CHANGED')
    return mapping, generated


def match_isa_to_pre_alap(isa_operations, pre_alap_operations, second_layout):
    """Require the same operations under the verified second-stage wire map."""
    require(type(second_layout) is list and len(second_layout) == 5
            and all(type(q) is int for q in second_layout)
            and sorted(second_layout) == list(range(5)), 'INVALID_ISA_LAYOUT_DOMAIN')
    mapped = []
    for index, operation in enumerate(isa_operations):
        require(all(type(q) is int and 0 <= q < 5 for q in operation['qubits']), 'INVALID_ISA_QUBIT')
        mapped.append(dict(operation, id='isa' + str(index),
                           qubits=[second_layout[q] for q in operation['qubits']]))
    mapping, generated = match_operation_ids(mapped, pre_alap_operations)
    require(not generated, 'PRE_ALAP_OPERATION_INSERTED')
    return mapping


def compose_layouts(first, second, first_output_width, second_output_width):
    require(type(first_output_width) is int and type(second_output_width) is int
            and 1 <= first_output_width <= 8 and 1 <= second_output_width <= 8, 'INVALID_LAYOUT_WIDTH')
    require(type(first) is list and len(first) == 2 and len(set(first)) == 2
            and all(type(i) is int and 0 <= i < first_output_width for i in first), 'INVALID_FIRST_LAYOUT')
    require(type(second) is list and len(second) == first_output_width and len(set(second)) == len(second)
            and all(type(i) is int and 0 <= i < second_output_width for i in second), 'INVALID_SECOND_LAYOUT_DOMAIN')
    return [second[i] for i in first]


def finite_json(value):
    """Preserve symbolic canvas coordinates and reject unknown object coercion."""
    import enum
    import math
    import numbers
    if value is None or type(value) in (str, bool):
        return value
    if isinstance(value, enum.Enum):
        return dict(enum=type(value).__module__ + '.' + type(value).__qualname__,
                    name=value.name, value=finite_json(value.value))
    if isinstance(value, numbers.Integral):
        return int(value)
    if isinstance(value, numbers.Real):
        require(math.isfinite(value), 'NONFINITE_DRAWING_VALUE')
        return float(value)
    if isinstance(value, (list, tuple)):
        return [finite_json(item) for item in value]
    if type(value) is dict:
        require(all(type(key) is str for key in value), 'NONSTRING_DRAWING_KEY')
        return {key: finite_json(item) for key, item in value.items()}
    if type(value).__module__.split('.')[0] == 'numpy' and hasattr(value, 'tolist'):
        return finite_json(value.tolist())
    raise ValueError('UNSUPPORTED_DRAWING_VALUE:' + type(value).__module__ + '.' + type(value).__qualname__)


def canvas_bit_identity(circuit, bit, quantum_type, classical_type):
    """Use the captured program's canonical bit membership, never repr/id."""
    quantum = type(bit) is quantum_type
    classical = type(bit) is classical_type
    require(quantum != classical, 'UNSUPPORTED_CANVAS_BIT_TYPE')
    require(all(type(item) is quantum_type for item in circuit.qubits)
            and all(type(item) is classical_type for item in circuit.clbits), 'INVALID_CANVAS_BIT_CONTEXT')
    domain = circuit.qubits if quantum else circuit.clbits
    opposite = circuit.clbits if quantum else circuit.qubits
    matches = [index for index, item in enumerate(domain) if item == bit]
    require(len(matches) == 1 and not any(item == bit for item in opposite), 'AMBIGUOUS_OR_FOREIGN_CANVAS_BIT')
    index = circuit.find_bit(bit).index
    require(type(index) is int and index >= 0 and index == matches[0], 'CANVAS_BIT_INDEX_MISMATCH')
    return dict(kind='qubit' if quantum else 'clbit', index=index)


def serialize_datum(datum, bit_identity):
    meta = datum.meta
    if type(meta) is dict and 'bits' in meta:
        require(type(meta['bits']) in (list, tuple), 'INVALID_DRAWING_METADATA_BITS')
        require(all(type(key) is str for key in meta), 'NONSTRING_DRAWING_KEY')
        meta = {key: ([bit_identity(bit) for bit in value] if key == 'bits' else finite_json(value))
                for key, value in meta.items()}
    else:
        meta = finite_json(meta)
    result = dict(kind=type(datum).__name__, data_type=finite_json(datum.data_type),
                  xvals=finite_json(datum.xvals), yvals=finite_json(datum.yvals),
                  bits=None if datum.bits is None else [bit_identity(bit) for bit in datum.bits], meta=meta,
                  styles=finite_json(datum.styles))
    if hasattr(datum, 'text'):
        result.update(text=finite_json(datum.text), latex=finite_json(datum.latex))
    return result


def integer_tick(value):
    import operator
    require(type(value) is not bool, 'BOOLEAN_TICK')
    try:
        result = operator.index(value)
    except TypeError as error:
        raise ValueError('NONINTEGER_TICK') from error
    require(result >= 0, 'NEGATIVE_TICK')
    return result


def snapshot_operation(op, qubits, clbits, container):
    require(getattr(op, 'condition', None) is None and not getattr(op, 'blocks', ()), 'UNSUPPORTED_CONDITIONAL_OPERATION')
    require(op.name in {'id', 'h', 'x', 'sx', 'rz', 'cx', 'delay', 'barrier', 'measure'}, 'UNSUPPORTED_TIMING_OPERATION:' + op.name)
    params = finite_json(list(op.params))
    if op.name == 'delay':
        require(op.unit == 'dt', 'DELAY_UNIT_NOT_DT')
        params = [integer_tick(op.duration)]
    return dict(name=op.name, qubits=[container.find_bit(q).index for q in qubits],
                clbits=[container.find_bit(c).index for c in clbits], params=params)


def snapshot_circuit(circuit):
    return [snapshot_operation(i.operation, i.qubits, i.clbits, circuit) for i in circuit.data]


def snapshot_layout(input_circuit, output_circuit, allow_identity=False):
    layout = output_circuit.layout
    if layout is None:
        require(allow_identity and list(input_circuit.qubits) == list(output_circuit.qubits), 'UNPROVEN_LAYOUT_IDENTITY')
        return dict(mapping=list(range(len(input_circuit.qubits))), proof='unchanged wire order plus separately checked operation correspondence')
    require(layout._input_qubit_count == len(input_circuit.qubits), 'LAYOUT_INPUT_DOMAIN_MISMATCH')
    require(layout._output_qubit_list is not None and list(layout._output_qubit_list) == list(output_circuit.qubits), 'LAYOUT_OUTPUT_DOMAIN_MISMATCH')
    require(all(layout.input_qubit_mapping.get(bit) == index for index, bit in enumerate(input_circuit.qubits)), 'LAYOUT_INPUT_IDENTITY_MISMATCH')
    mapping = list(layout.final_index_layout(filter_ancillas=True))
    require(len(mapping) == len(input_circuit.qubits) and all(type(i) is int and 0 <= i < len(output_circuit.qubits) for i in mapping)
            and len(set(mapping)) == len(mapping), 'INVALID_LAYOUT_PERMUTATION')
    return dict(mapping=mapping, input_width=len(input_circuit.qubits), output_width=len(output_circuit.qubits),
                initial=list(layout.initial_index_layout(filter_ancillas=True)), routing=list(layout.routing_permutation()),
                proof='input mapping identities and explicit input/output layout domains')


def merge_intervals(intervals):
    merged = []
    for start, end in sorted(intervals):
        require(type(start) is int and type(end) is int and 0 <= start <= end, 'INVALID_IDLE_INTERVAL')
        if start == end:
            continue
        if merged and start == merged[-1][1]:
            merged[-1][1] = end
        else:
            require(not merged or start >= merged[-1][1], 'OVERLAPPING_IDLE_INTERVALS')
            merged.append([start, end])
    return merged


def check_padding(pre_ops, starts, horizon, padded, padded_starts, width):
    """Source delays may be replaced; check total idle coverage independently."""
    require(type(width) is int and 1 <= width <= 8 and type(horizon) is int and horizon >= 0, 'INVALID_PADDING_DOMAIN')
    require(len(padded) == len(padded_starts), 'PADDING_START_COUNT_MISMATCH')
    occupied = {q: [] for q in range(width)}
    observed = {q: [] for q in range(width)}
    for operation in pre_ops:
        if operation['name'] == 'delay':
            continue
        for q in operation['qubits']:
            occupied[q].append((starts[operation['id']], starts[operation['id']] + operation['duration_dt']))
    for operation, start in zip(padded, padded_starts):
        if operation['name'] == 'delay':
            require(len(operation['qubits']) == 1, 'MULTIWIRE_DELAY')
            observed[operation['qubits'][0]].append([start, start + operation['params'][0]])
    expected = {}
    for q, intervals in occupied.items():
        cursor, gaps = 0, []
        for start, end in sorted(intervals):
            require(start >= cursor and end <= horizon, 'INVALID_OCCUPIED_INTERVAL')
            if start > cursor:
                gaps.append([cursor, start])
            cursor = end
        if cursor < horizon:
            gaps.append([cursor, horizon])
        expected[str(q)] = merge_intervals(gaps)
        require(merge_intervals(observed[q]) == expected[str(q)], 'PADDING_COVERAGE_MISMATCH:' + str(q))
    return expected


def density_json(matrix):
    return [[[complex(value).real, complex(value).imag] for value in row] for row in matrix]


def state_acceptance(reference, operations, width, layout, global_phase):
    state, measurements = reference.scalar_state(operations, width, global_phase)
    density = reference.reduced_density(state, layout)
    result = reference.check_density(density, reference.bell_density())
    result.update(density=density_json(density), measurement_mapping=measurements,
                  state=[[a.real, a.imag] for a in state], logical_to_physical=layout,
                  convention='physical little-endian; density ignores global phase; final measurements not sampled')
    return result


def bind_timing(reference, notebook_namespace, source_hashes):
    """Called only by the authored bootstrap after the runtime gate is reserved."""
    import inspect
    import sysconfig
    qiskit_root = Path(sysconfig.get_path('platlib')) / 'qiskit'
    for relative, expected in source_hashes.items():
        require(hashlib.sha256((qiskit_root / relative).read_bytes()).hexdigest() == expected,
                'INSTALLED_QISKIT_SOURCE_CHANGED:' + relative)
    # No Qiskit import or hook is installed until every Python/extension gate passes.
    import qiskit
    from qiskit.circuit import Qubit, Clbit
    from qiskit.visualization import timeline
    from qiskit.visualization.timeline.core import DrawerCanvas
    from qiskit.visualization.timeline.plotters import MplPlotter
    from qiskit.transpiler.passes.scheduling.scheduling.alap import ALAPScheduleAnalysis
    from qiskit.transpiler.passes.scheduling.scheduling.base_scheduler import BaseScheduler
    from qiskit.transpiler.passes.scheduling.padding.base_padding import BasePadding
    draw_signature = inspect.signature(timeline.draw)

    def begin(record, args, kwargs):
        bound = draw_signature.bind(*args, **kwargs)
        bound.apply_defaults()
        program, target = bound.arguments['program'], bound.arguments['target']
        require(program is notebook_namespace.get('isa_circuit'), 'DRAW_INPUT_NOT_ORIGINAL_ISA')
        source = notebook_namespace['qc']
        require(len(source.qubits) == 2 and len(program.qubits) == 5 and target is not None, 'FINITE_SOURCE_WIDTH_REQUIRED')
        require(getattr(program, '_op_start_times') is None, 'EXPECTED_UNSCHEDULED_ORIGINAL_INPUT')
        constraints = {key: getattr(target, key) for key in ('granularity', 'min_length', 'pulse_alignment', 'acquire_alignment')}
        require(all(type(v) is int and v == 1 for v in constraints.values()), 'UNSUPPORTED_ALIGNMENT')
        reference.duration_ticks(0, target.dt)
        record.update(program=program, target=target, source=source)
        record['data'].update(dt=target.dt, constraints=constraints, isa_operations=snapshot_circuit(program),
                              original_operations=snapshot_circuit(source), isa_global_phase=float(program.global_phase),
                              layout_a=snapshot_layout(source, program), source_hashes=source_hashes,
                              compiled_source_correspondence='unverified; extension bytes bound to reviewed wheel')

    def alap_before(record, args, kwargs):
        analysis, dag = args[:2]
        require(analysis.property_set['time_unit'] == 'dt' and analysis.property_set.get('clbit_write_latency', 0) == 0,
                'UNSUPPORTED_SCHEDULER_UNITS_OR_LATENCY')
        nodes = list(dag.topological_op_nodes())
        identities = {node: 'n' + str(i) for i, node in enumerate(nodes)}
        record.update(pre_nodes=nodes, node_ids=identities, pre_dag=dag)
        operations, oracle = [], []
        for node in nodes:
            operation = snapshot_operation(node.op, node.qargs, node.cargs, dag)
            name = operation['name']
            raw_seconds = None
            if name == 'barrier':
                duration = 0
            elif name == 'delay':
                duration = operation['params'][0]
            else:
                props = record['target'].get(name)
                props = props.get(tuple(operation['qubits'])) if props is not None else None
                require(props is not None and props.duration is not None, 'MISSING_TARGET_DURATION')
                raw_seconds = props.duration
                duration = reference.duration_ticks(raw_seconds, record['target'].dt)
            identity = identities[node]
            operation.update(id=identity, duration_dt=duration, target_seconds=raw_seconds,
                             after=[identities[p] for p in dag.predecessors(node) if p in identities])
            operations.append(operation)
            kind = name if name in {'barrier', 'delay', 'measure'} else 'gate'
            oracle.append(dict(id=identity, kind=kind, duration_dt=duration,
                resources=['q:' + str(q) for q in operation['qubits']] + ['c:' + str(c) for c in operation['clbits']],
                after=operation['after']))
        record['data'].update(pre_alap_operations=operations, oracle_operations=oracle,
                              scalar_expected=reference.schedule(oracle), actual_duration_ticks={}, clbit_write_latency=0,
                              time_unit='dt')

    def duration_after(record, args, kwargs, result):
        node = args[1]
        identity = record['node_ids'][node]
        durations = record['data']['actual_duration_ticks']
        require(identity not in durations, 'DUPLICATE_DURATION_LOOKUP')
        durations[identity] = integer_tick(result)

    def alap_after(record, args, kwargs, result):
        analysis = args[0]
        require(result is record['pre_dag'], 'ALAP_DAG_IDENTITY_CHANGED')
        starts = analysis.property_set['node_start_time']
        require(set(starts) == set(record['pre_nodes']), 'ALAP_NODE_SET_CHANGED')
        record['data']['alap_starts'] = {record['node_ids'][n]: integer_tick(t) for n, t in starts.items()}

    def padding_before(record, args, kwargs):
        padding, dag = args[:2]
        require(dag is record['pre_dag'] and padding.property_set['time_unit'] == 'dt', 'PADDING_INPUT_CHANGED')
        starts = {record['node_ids'][n]: integer_tick(t) for n, t in padding.property_set['node_start_time'].items()}
        require(starts == record['data']['alap_starts'], 'POST_ALAP_START_CHANGED')

    def padding_after(record, args, kwargs, dag):
        padding = args[0]
        nodes = list(dag.topological_op_nodes())
        operations = [dict(id='p' + str(i), **snapshot_operation(n.op, n.qargs, n.cargs, dag)) for i, n in enumerate(nodes)]
        times = [integer_tick(padding.property_set['node_start_time'][n]) for n in nodes]
        mapping, generated = match_operation_ids(record['data']['pre_alap_operations'], operations, True)
        for identity, time in zip(mapping, times):
            if identity is not None:
                require(record['data']['alap_starts'][identity] == time, 'PADDING_CHANGED_START')
        record['data'].update(padded_operations=operations, padded_starts=times, padding_mapping=mapping,
                              generated_delay_indices=generated, horizon=integer_tick(dag._duration))

    def transpile_after(record, args, kwargs, result):
        require(args and args[0] is record['program'] and kwargs.get('target') is record['target']
                and kwargs.get('optimization_level') == 0 and kwargs.get('scheduling_method') == 'alap', 'DRAWER_TRANSPILE_CALL_CHANGED')
        operations = snapshot_circuit(result)
        mapping, _ = match_operation_ids(record['data']['padded_operations'], operations)
        expected_times = {op['id']: time for op, time in zip(record['data']['padded_operations'], record['data']['padded_starts'])}
        times = [integer_tick(t) for t in result.op_start_times]
        require(len(times) == len(operations) and times == [expected_times[i] for i in mapping], 'DRAWER_SCHEDULE_CHANGED')
        record['scheduled'] = result
        record['data'].update(scheduled_operations=operations, scheduled_starts=times,
                              scheduled_global_phase=float(result.global_phase), layout_b=snapshot_layout(record['program'], result, True))
        record['data']['isa_to_pre_alap_mapping'] = match_isa_to_pre_alap(
            record['data']['isa_operations'], record['data']['pre_alap_operations'], record['data']['layout_b']['mapping'])

    def bit_identity(record, bit):
        return canvas_bit_identity(record['scheduled'], bit, Qubit, Clbit)

    def dataset(record, items):
        result = []
        for ordinal, (key, datum) in enumerate(items):
            data = serialize_datum(datum, lambda bit: bit_identity(record, bit))
            result.append(dict(ordinal=ordinal, original_local_key=str(key), data=data,
                               content_sha256=hashlib.sha256(json.dumps(data, sort_keys=True, allow_nan=False).encode()).hexdigest()))
        return result

    def canvas_after(record, args, kwargs, result):
        canvas = args[0]
        require(kwargs.get('program', args[1] if len(args) > 1 else None) is record['program'], 'CANVAS_PROGRAM_CHANGED')
        record['canvas'] = canvas
        record['data']['stored_canvas_data'] = dataset(record, canvas._collections.items())

    def plotter_after(record, args, kwargs, result):
        plotter = args[0]
        require(plotter.canvas is record['canvas'], 'PLOTTER_CANVAS_CHANGED')
        record['plotter'] = plotter
        record['data'].update(filtered_canvas_data=dataset(record, plotter.canvas.collections),
            canvas_time_range=finite_json(plotter.canvas.time_range),
            canvas_lanes=[dict(bit=bit_identity(record, bit), position=finite_json(position))
                          for bit, position in plotter.canvas.assigned_coordinates.items()],
            formatter=finite_json(plotter.canvas.formatter))

    def image_after(record, args, kwargs, result):
        require(args[0] is record['plotter'] and result is args[0].figure, 'IMAGE_FIGURE_IDENTITY_CHANGED')
        record['figure'] = result

    def finish(record, args, kwargs, result):
        require(result is record['figure'], 'DRAW_RETURN_IDENTITY_CHANGED')
        record['data'].update(same_figure_identity=True,
            original_png_association='Original cell PNG retained by engine; formatter-to-Figure byte association not intercepted',
            stored_canvas_limit='Already style-filtered for classical bits; local hash-key replacements possible; not semantic operation stream')

    def validate(record):
        data = record['data']
        expected_calls = {name: 1 for name in ('alap', 'padding', 'transpile', 'canvas', 'plotter', 'image')}
        expected_calls['duration'] = len(data['pre_alap_operations'])
        require(data['calls'] == expected_calls, 'HOOK_CALL_COUNT_MISMATCH')
        require(data['actual_duration_ticks'] == {o['id']: o['duration_dt'] for o in data['pre_alap_operations']}, 'SDK_DURATION_CONVERSION_MISMATCH')
        expected = reference.check_schedule(data['oracle_operations'], data['alap_starts'], data['horizon'])
        require(expected == data['scalar_expected'], 'ORACLE_INPUT_CHANGED')
        idle = check_padding(data['pre_alap_operations'], data['alap_starts'], data['horizon'],
                             data['padded_operations'], data['padded_starts'], 5)
        logical = compose_layouts(data['layout_a']['mapping'], data['layout_b']['mapping'], 5, 5)
        first = state_acceptance(reference, data['isa_operations'], 5, data['layout_a']['mapping'], data['isa_global_phase'])
        final = state_acceptance(reference, data['scheduled_operations'], 5, logical, data['scheduled_global_phase'])
        expected_measures = 0 if data['ordinal'] == 1 else 2
        source_measurements = [[op['qubits'][0], op['clbits'][0]] for op in data['original_operations'] if op['name'] == 'measure']
        require(source_measurements == ([] if expected_measures == 0 else [[0, 0], [1, 1]]), 'ORIGINAL_MEASUREMENT_MAPPING_CHANGED')
        require(sorted(first['measurement_mapping']) == sorted([[data['layout_a']['mapping'][q], c] for q, c in source_measurements]), 'ISA_MEASUREMENT_MAPPING_CHANGED')
        require(sorted(final['measurement_mapping']) == sorted([[logical[q], c] for q, c in source_measurements]), 'DRAWER_MEASUREMENT_MAPPING_CHANGED')
        require(data['same_figure_identity'] and data['filtered_canvas_data'] and data['stored_canvas_data'], 'MISSING_DRAWING_ASSOCIATION')
        return dict(accepted=True, idle_intervals=idle, first_transpile_state=first, drawer_state=final,
                    integer_timing_exact=True, density_tolerance=reference.STATE_TOLERANCE,
                    diagram_geometry_is_not_timing_oracle=True)

    hooks = [(ALAPScheduleAnalysis, 'run', alap_before, alap_after, 'alap'),
             (BaseScheduler, '_get_node_duration', None, duration_after, 'duration'),
             (BasePadding, 'run', padding_before, padding_after, 'padding'),
             (qiskit, 'transpile', None, transpile_after, 'transpile'),
             (DrawerCanvas, 'load_program', None, canvas_after, 'canvas'),
             (MplPlotter, '__init__', None, plotter_after, 'plotter'),
             (MplPlotter, 'get_image', None, image_after, 'image')]
    capture = PassiveCapture(timeline, 'draw', hooks, begin, finish, validate)
    capture.aliases = [(notebook_namespace, 'draw')]
    return capture


def authored_layout_controls(capture, reference, api=None):
    """Separate post-source SDK controls, with expectations fixed before calls.

    Two targets x three circuits; no extra original draw or source-cell change.
    Explicit nontrivial initial layout and seed affect only authored controls.
    """
    import math
    capture.summary()
    require(capture.outer_restored, 'CONTROLS_REQUIRE_RESTORED_ORIGINAL_DRAW')
    for owner, name, original, before, after, label in capture.hooks:
        require(getattr(owner, name) is original, 'CONTROLS_REQUIRE_RESTORED_HOOK:' + label)
    if api is None:
        import qiskit as api
    report = dict(state='running', accepted=False, scope='authored post-source controls, not original notebook outputs', cases=[])
    destination = capture.output / 'timing-controls.json'
    def checkpoint():
        temporary = destination.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        temporary.replace(destination)
    checkpoint()
    try:
        for target_index, record in enumerate(capture.records):
            for name, basis in [('logical-q0-one', 1), ('logical-q1-one', 2), ('phase-bell', None)]:
                case = dict(target_ordinal=target_index+1, name=name, state='running',
                            initial_layout=[3, 1], seed_transpiler=1731)
                report['cases'].append(case)
                checkpoint()
                source = api.QuantumCircuit(2)
                if basis is None:
                    source.h(0); source.cx(0, 1); source.rz(math.pi/2, 0)
                    expected = [[0.5, 0, 0, -0.5j], [0,0,0,0], [0,0,0,0], [0.5j,0,0,0.5]]
                else:
                    source.x(0 if basis == 1 else 1)
                    expected = [[int(i == j == basis) for j in range(4)] for i in range(4)]
                case.update(source_operations=snapshot_circuit(source), expected_density=density_json(expected))
                checkpoint()
                first = api.transpile(source, target=record['target'], optimization_level=1,
                                      initial_layout=[3, 1], seed_transpiler=1731)
                a = snapshot_layout(source, first)
                first_operations = snapshot_circuit(first)
                first_state, first_measurements = reference.scalar_state(first_operations, len(first.qubits), float(first.global_phase))
                first_density = reference.reduced_density(first_state, a['mapping'])
                case.update(first_operations=first_operations, layout_a=a, first_global_phase=float(first.global_phase),
                            first_density=density_json(first_density), first_raw_state=[[v.real,v.imag] for v in first_state])
                checkpoint()
                require(not first_measurements, 'AUTHORED_CONTROL_HAS_MEASUREMENT')
                case['first_comparison'] = reference.check_density(first_density, expected)
                checkpoint()
                final = api.transpile(first, target=record['target'], optimization_level=0,
                                      scheduling_method='alap', seed_transpiler=1731)
                b = snapshot_layout(first, final, True)
                operations = snapshot_circuit(final)
                logical = compose_layouts(a['mapping'], b['mapping'], len(first.qubits), len(final.qubits))
                state, measurements = reference.scalar_state(operations, len(final.qubits), float(final.global_phase))
                require(not measurements, 'AUTHORED_CONTROL_HAS_MEASUREMENT')
                density = reference.reduced_density(state, logical)
                case.update(final_operations=operations, layout_b=b, composed_layout=logical,
                            final_global_phase=float(final.global_phase), actual_density=density_json(density),
                            raw_state=[[v.real,v.imag] for v in state])
                checkpoint()  # Retain mismatching observations before evaluating them.
                case['comparison'] = reference.check_density(density, expected)
                case['state'] = 'succeeded'
                checkpoint()
        require(len(report['cases']) == 6, 'AUTHORED_CONTROL_COUNT')
        report.update(state='succeeded', accepted=True)
        checkpoint()
        return report
    except BaseException as error:
        report.update(state='failed', error=dict(type=type(error).__name__, message=str(error)))
        if report['cases'] and report['cases'][-1]['state'] == 'running':
            report['cases'][-1]['state'] = 'failed'
        checkpoint()
        raise


SOURCE_HASHES = {'_accelerate.pyd': '4fe0996035b2e0bdf169a2ad6834afe3b244bc782ef9d1f4eb824f159fe29f80', 'circuit/duration.py': 'ad0110b2c40c326e8bf042af04c619c3eefb247ab54f1be7043dd3fb1cac3890', 'circuit/quantumcircuit.py': 'd70c1c9350a94c2e07ae9fef24746a95633c36846719d8789c4a98185f11b281', 'dagcircuit/dagcircuit.py': '6bea43540e83afa0a61e5fdcc479820ad7104edea03aca6ed200ecf3323ed646', 'providers/fake_provider/generic_backend_v2.py': '14c5869bce8b700ec21ebaf2fec7459f544f81951689a05201d9e06cefa16149', 'transpiler/instruction_durations.py': '84ef252f6e02950ca322e4e1cf2012821f52c5868813fa465bf512124bd3cac6', 'transpiler/layout.py': '8edf25740ce9f6bb9686b300571736a8318dd85f933ae3731f10ee4d05cd22e4', 'transpiler/passes/optimization/contract_idle_wires_in_control_flow.py': 'f8f68d75f5ad30ed067165eb7d0df70eb222c113c1a1f1d796da741ee0369ada', 'transpiler/passes/routing/star_prerouting.py': '61579da74b96bfe31eb65ad4c186d922301a70bdb1b2886981b23dc9460a1199', 'transpiler/passes/scheduling/padding/base_padding.py': 'cbdb10a947098ce8a467ba6ca0e3a8cec7395d60bcfe35aca465da9226be25bc', 'transpiler/passes/scheduling/padding/pad_delay.py': '7dfc9a8116795f55fcb6cd702bcd0bdb6d571730d930401381ce820d23e15ffb', 'transpiler/passes/scheduling/scheduling/alap.py': '9760534de36744b1eca49e25ae64a849f1e5425b78e22f6f94de30f7ed237244', 'transpiler/passes/scheduling/scheduling/base_scheduler.py': '49a6806a9dac043bd52105183e3c7b65fd801d2d90ee72410298d45eb97be6ab', 'transpiler/passes/scheduling/time_unit_conversion.py': '9c03c5a990ec36239e25268857d058c7ddd6eabaa2100ae293278a3cca497ceb', 'transpiler/passmanager.py': '31b1b1ef04b31e5b33e42673cadc89d685cb746bc2c2386de19a8ff0ef9a2a0f', 'transpiler/preset_passmanagers/builtin_plugins.py': 'f87df958485a4a422bc494a056a800afc49f8acddc1203008d91d44a3cede467', 'transpiler/preset_passmanagers/common.py': 'a1e54b5a7f211cc6462909c4e0e3bdc7f23bafd2545a1afb0cc2a19d60991e3a', 'transpiler/target.py': 'fa0df41779f782d473aa088ea4438121023fe5cffce9ac423c9c167698df58c8', 'visualization/timeline/core.py': 'fd345bd3d0ac1bf0b05c1f1c3ab27f5d928fd49b9ccf8c9ebafd9d5912e75a96', 'visualization/timeline/drawings.py': '228ec12f686f62c9d0be7f66ba33ae51750c69e830248b46fb3365ca79168924', 'visualization/timeline/interface.py': '3eaa7422cd9c5157788dc24cc884cb8182b9d465b5a7704be29a7e39ee570093', 'visualization/timeline/plotters/base_plotter.py': 'fc872943d5c24ae50fd81a13c04ef7c3e65e8c3b2fa4f47e91e52918acabef26', 'visualization/timeline/plotters/matplotlib.py': '403d6ba9870fcea6464dabee017e0d2a88b68e4de41b65696adf799ff1b4dfbc', 'visualization/timeline/types.py': '27635f7005ca3aeeab9f1de7ef7bf3e3af3132c6cba4f6a458cde2f6c0f3e819'}

if __name__ == "__main__":
    _timing_observer = bind_timing(_timing_reference, globals(), SOURCE_HASHES)
