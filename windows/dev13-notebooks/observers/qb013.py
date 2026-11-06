"""Finite QB013 observation primitives and explicit notebook bootstrap.

Capture failures are recorded separately and never change conversion control
flow. The original graph's cached bound convert methods remain untouched.
"""
from functools import wraps


def _bind_observation_api(site_packages, source_hashes, importer):
    """Injected implementation: verify every gate before the first import.

    No hooks, conversions, graphs or parsers are constructed here. Source
    identity is necessary, not a proof of imported native semantics or full
    dependency closure. The public entry point fixes the reviewed digests.
    """
    import hashlib
    from pathlib import Path
    from types import SimpleNamespace

    root = Path(site_packages).resolve(strict=True)
    if not root.is_dir() or set(source_hashes) != set(API_SOURCE_HASHES):
        raise ValueError('INCOMPLETE_API_SOURCE_GATES')
    verified = {}
    for relative, expected in source_hashes.items():
        path = (root / relative).resolve(strict=True)
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError('API_SOURCE_OUTSIDE_ENVIRONMENT:' + relative)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError('API_SOURCE_CHANGED:' + relative)
        verified[relative] = actual

    modules = {}
    for name, relative in API_MODULE_PATHS.items():
        module = importer(name)
        origin = getattr(module, '__file__', None)
        if origin is None or Path(origin).resolve(strict=True) != (root / relative).resolve(strict=True):
            raise ValueError('API_MODULE_ORIGIN_MISMATCH:' + name)
        # Detect file replacement during import before exposing any API/hook.
        if hashlib.sha256(Path(origin).read_bytes()).hexdigest() != source_hashes[relative]:
            raise ValueError('API_SOURCE_CHANGED_DURING_IMPORT:' + relative)
        modules[name] = module

    def cls(module, name):
        value = getattr(modules[module], name, None)
        if not isinstance(value, type):
            raise ValueError('API_CLASS_MISSING:' + module + '.' + name)
        return value

    api = SimpleNamespace(
        QuantumCircuit=cls('qiskit.circuit.quantumcircuit', 'QuantumCircuit'),
        CirqCircuit=cls('cirq.circuits.circuit', 'AbstractCircuit'),
        MeasurementGate=cls('cirq.ops.measurement_gate', 'MeasurementGate'),
        IdentityGate=cls('cirq.ops.identity', 'IdentityGate'),
        StimCircuit=cls('stim', 'Circuit'),
        StimInstruction=cls('stim', 'CircuitInstruction'),
        Conversion=cls('qbraid.transpiler.edge', 'Conversion'),
        QasmParser=cls('qbraid.transpiler.conversions.qasm2.cirq_qasm_parser', 'QasmParser'),
    )
    for name in ('HPowGate', 'XPowGate', 'YPowGate', 'ZPowGate', 'CXPowGate', 'CZPowGate'):
        setattr(api, name, cls('cirq.ops.common_gates', name))
    operations = {
        'h': ('h', 'HGate'), 'x': ('x', 'XGate'), 'y': ('y', 'YGate'),
        'z': ('z', 'ZGate'), 's': ('s', 'SGate'), 'sdg': ('s', 'SdgGate'),
        'sx': ('sx', 'SXGate'), 'sxdg': ('sx', 'SXdgGate'),
        't': ('t', 'TGate'), 'tdg': ('t', 'TdgGate'),
        'cx': ('x', 'CXGate'), 'cz': ('z', 'CZGate'), 'id': ('i', 'IGate'),
    }
    api.qiskit_operations = {
        name: cls('qiskit.circuit.library.standard_gates.' + module, class_name)
        for name, (module, class_name) in operations.items()
    }
    api.qiskit_operations.update(measure=cls('qiskit.circuit.measure', 'Measure'),
                                barrier=cls('qiskit.circuit.barrier', 'Barrier'))
    api.measurement_key_name = getattr(modules['cirq.protocols.measurement_key_protocol'], 'measurement_key_name', None)
    api.conversion_method = getattr(api.Conversion, 'convert', None)
    api.public_module = modules['qbraid.transpiler']
    api.converter_module = modules['qbraid.transpiler.converter']
    api.ConversionGraph = cls('qbraid.transpiler.graph', 'ConversionGraph')
    api.transpile = getattr(api.converter_module, 'transpile', None)
    if (not callable(api.transpile) or getattr(api.public_module, 'transpile', None) is not api.transpile
            or not callable(getattr(api.ConversionGraph, 'add_conversion', None))
            or not callable(getattr(api.ConversionGraph, 'has_path', None))):
        raise ValueError('TRANSPILE_API_IDENTITY')
    api.stim_converter = getattr(modules['stimcirq._cirq_to_stim'], 'cirq_circuit_to_stim_circuit', None)
    api.known_conversion_functions = {
        'qiskit_to_qasm2': getattr(modules['qbraid.transpiler.conversions.qiskit.qiskit_to_qasm2'], 'qiskit_to_qasm2', None),
        'qasm2_to_cirq': getattr(modules['qbraid.transpiler.conversions.qasm2.qasm2_to_cirq'], 'qasm2_to_cirq', None),
        'cirq_to_stim': api.stim_converter,
    }
    if (not callable(api.measurement_key_name) or not callable(api.conversion_method)
            or not callable(getattr(api.QasmParser, 'parse', None))
            or not all(callable(value) for value in api.known_conversion_functions.values())):
        raise ValueError('API_CALLABLE_MISSING')
    for relative, expected in source_hashes.items():
        path = (root / relative).resolve(strict=True)
        if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('API_SOURCE_CHANGED_DURING_BINDING:' + relative)
    api.source_evidence = dict(site_packages=str(root), source_hashes=verified,
                               module_paths=dict(API_MODULE_PATHS), compiled_source_correspondence='unproved')
    return api


def bind_observation_api(site_packages):
    """Deferred SDK binding only; never activate automatically at import."""
    from importlib import import_module
    return _bind_observation_api(site_packages, API_SOURCE_HASHES, import_module)


class CaptureJournal:
    """Atomically replace this instance's own finite JSON evidence file.

    Flush each temporary file before replacement. This retains the previous
    complete checkpoint if serialization or replacement fails; it is not a
    guarantee against power loss. Failed temporary files remain evidence.
    """
    def __init__(self, path):
        from pathlib import Path
        self.path = Path(path).resolve()
        if self.path.exists() or not self.path.parent.is_dir():
            raise ValueError('FRESH_CAPTURE_PATH_REQUIRED')
        self.previous_sha256 = None
        self.revision = 0

    def write(self, payload):
        import hashlib
        import json
        import os
        import uuid
        if self.previous_sha256 is None:
            if self.path.exists():
                raise ValueError('CAPTURE_PATH_ALREADY_EXISTS')
        elif (not self.path.is_file()
              or hashlib.sha256(self.path.read_bytes()).hexdigest() != self.previous_sha256):
            raise ValueError('CAPTURE_FILE_CHANGED_EXTERNALLY')
        raw = json.dumps(dict(format_version=1, revision=self.revision + 1, payload=payload),
                         allow_nan=False, ensure_ascii=False, indent=2).encode('utf-8')
        temporary = self.path.with_name(self.path.name + '.' + uuid.uuid4().hex + '.tmp')
        with temporary.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, self.path)
        self.previous_sha256 = hashlib.sha256(raw).hexdigest()
        self.revision += 1


class ScopedConversions:
    """Observe callable attributes only during one delegated transpile call.

Snapshot functions must be read-only. Their failures are deferred to the
postcell check, so qBraid cannot mistake a capture error for a failed path.
"""
    def __init__(self, edges, snapshot, known_functions=None, checkpoint=None):
        self.edges = list(edges)
        self.snapshot = snapshot
        self.known_functions = dict(known_functions or {})
        self.checkpoint = checkpoint
        self.records = []
        self.diagnostics = []
        self.saved = []
        # In-memory objects only, never part of the JSON evidence. Each entry
        # corresponds to a recorded call, including failures (an empty dict).
        self.native_outputs = []
        self.active = False

    def _capture(self, record, key, value):
        try:
            record[key] = self.snapshot(value)
        except Exception as error:
            self.diagnostics.append(dict(stage=key, type=type(error).__name__, message=str(error)))

    def _checkpoint(self):
        if self.checkpoint is not None:
            try:
                self.checkpoint()
            except Exception as error:
                self.diagnostics.append(dict(stage='checkpoint', type=type(error).__name__, message=str(error)))

    def _wrap(self, edge, original):
        @wraps(original)
        def observed(*args, **kwargs):
            # Never derive routing from captured text; preserve all real args.
            record = dict(source=edge.source, target=edge.target, state='running',
                          ordinal=len(self.records),
                          function_identities=[name for name, function in self.known_functions.items()
                                               if original is function],
                          positional_argument_count=len(args), keyword_names=sorted(kwargs),
                          single_program_positional_call=(len(args) == 1 and not kwargs))
            self.records.append(record)
            native = {}
            self.native_outputs.append(native)
            if args:
                self._capture(record, 'input', args[0])
            self._checkpoint()
            try:
                result = original(*args, **kwargs)
            except BaseException as error:
                record['state'] = 'failed'
                try:
                    record['error'] = dict(type=type(error).__name__, message=str(error))
                except Exception as capture_error:
                    self.diagnostics.append(dict(stage='error', type=type(capture_error).__name__))
                self._checkpoint()
                raise
            record['state'] = 'succeeded'
            native['output'] = result
            self._capture(record, 'output', result)
            self._checkpoint()
            return result
        return observed

    def __enter__(self):
        if self.active or self.saved:
            raise ValueError('OBSERVER_ALREADY_USED')
        self.active = True
        seen = set()
        try:
            for edge in self.edges:
                if id(edge) in seen:
                    continue
                seen.add(id(edge))
                original = edge._conversion_func
                if not callable(original):
                    raise ValueError('NONCALLABLE_CONVERSION')
                wrapper = self._wrap(edge, original)
                self.saved.append((edge, original, wrapper))
                edge._conversion_func = wrapper
        except BaseException:
            self._restore()
            raise
        return self

    def _restore(self):
        for edge, original, wrapper in reversed(self.saved):
            try:
                if edge._conversion_func is wrapper:
                    edge._conversion_func = original
                elif edge._conversion_func is not original:
                    self.diagnostics.append(dict(stage='restore', type='UnexpectedReplacement',
                                                 source=edge.source, target=edge.target))
            except Exception as error:
                self.diagnostics.append(dict(stage='restore', type=type(error).__name__, message=str(error)))
        self.active = False
        self._checkpoint()

    def __exit__(self, error_type, error, traceback):
        self._restore()
        return False

    def require_complete(self):
        if self.active:
            raise ValueError('OBSERVER_STILL_ACTIVE')
        if self.diagnostics:
            raise ValueError('AUTHORED_CAPTURE_FAILED')
        for edge, original, wrapper in self.saved:
            if edge._conversion_func is not original:
                raise ValueError('OBSERVER_NOT_RESTORED')

class ObservedTranspile:
    """Observe one delegated call at a time; installation is a separate step.

    Setup/capture/persistence failures are deferred, never used as qBraid path
    failures. The original callable receives its exact arguments exactly once.
    Scope records are saved while running and after restoration, before any
    semantic checker may accept them.
    """
    def __init__(self, original, api, snapshot, journal):
        import inspect
        self.original = original
        self.signature = inspect.signature(original)
        self.api = api
        self.snapshot = snapshot
        self.journal = journal
        self.records = []
        self.diagnostics = []
        self.active = False
        self.public_events = []
        self.public_hooks_restored = None
        self.source_evidence = None
        self.before_call = None
        self.public_alias_seen = False
        self.postcells = []
        self.native_calls = []
        @wraps(original)
        def wrapper(*args, **kwargs):
            if self.before_call is not None:
                try:
                    self.before_call()
                except Exception as error:
                    self._error('before_call_capture', error)
            return self._call(*args, **kwargs)
        self.wrapper = wrapper

    def _error(self, stage, error):
        self.diagnostics.append(dict(stage=stage, type=type(error).__name__, message=str(error)))

    def checkpoint(self):
        try:
            self.journal.write(dict(transpile_calls=self.records, diagnostics=self.diagnostics, active=self.active,
                                    public_events=self.public_events, public_hooks_restored=self.public_hooks_restored,
                                    public_alias_seen=self.public_alias_seen, postcells=self.postcells,
                                    source_evidence=self.source_evidence))
        except Exception as error:
            self._error('checkpoint', error)

    def _call(self, *args, **kwargs):
        from contextlib import ExitStack
        if self.active:
            self.diagnostics.append(dict(stage='nested_call', type='UnsupportedNestedTranspile'))
            self.checkpoint()
            return self.original(*args, **kwargs)
        self.active = True
        record = dict(ordinal=len(self.records), state='running')
        self.records.append(record)
        native = {}
        self.native_calls.append(native)
        stack = ExitStack()
        program = None
        graph = None
        conversions = None
        parser = None
        try:
            try:
                arguments = self.signature.bind(*args, **kwargs).arguments
                program = arguments['program']; target = arguments['target']
                if type(target) is not str:
                    raise ValueError('TRANSPILE_TARGET_NOT_STRING')
                record['target'] = target
                record['input'] = self.snapshot(program)
                graph = arguments.get('conversion_graph')
                if graph is None:
                    raise ValueError('EXPLICIT_CONVERSION_GRAPH_REQUIRED')
                edges, evidence = cached_graph_inventory(graph, self.api.conversion_method)
                record['graph_before'] = evidence
                conversions = ScopedConversions(edges, self.snapshot, self.api.known_conversion_functions,
                                                self.checkpoint)
                native['conversions'] = conversions.native_outputs
                parser = ScopedQasmParser(self.api.QasmParser, self.snapshot, self.checkpoint)
                record.update(conversions=conversions.records, conversion_diagnostics=conversions.diagnostics,
                              parsers=parser.records, parser_diagnostics=parser.diagnostics)
                stack.enter_context(parser)
                stack.enter_context(conversions)
            except Exception as error:
                self._error('capture_setup', error)
                try:
                    stack.close()
                except Exception as cleanup_error:
                    self._error('setup_restore', cleanup_error)
            self.checkpoint()
            try:
                result = self.original(*args, **kwargs)
            except BaseException as error:
                record['state'] = 'failed'
                try:
                    record['original_error'] = dict(type=type(error).__name__, message=str(error))
                except Exception as capture_error:
                    self._error('original_error_capture', capture_error)
                raise
            else:
                record['state'] = 'succeeded'
                try:
                    record['output'] = self.snapshot(result)
                except Exception as error:
                    self._error('output_capture', error)
                return result
            finally:
                self.checkpoint()
        finally:
            try:
                stack.close()
            except Exception as error:
                self._error('scope_restore', error)
            try:
                if program is not None:
                    record['input_after'] = self.snapshot(program)
                if graph is not None:
                    _, record['graph_after'] = cached_graph_inventory(graph, self.api.conversion_method)
                record['scopes_restored'] = bool(conversions is not None and parser is not None
                    and not conversions.active and not parser.active
                    and parser.owner.parse is parser.original
                    and all(edge._conversion_func is original for edge, original, _ in conversions.saved))
            except Exception as error:
                self._error('input_after_capture', error)
            self.active = False
            self.checkpoint()

    def require_complete(self):
        if self.active or self.diagnostics:
            raise ValueError('AUTHORED_TRANSPILE_CAPTURE_FAILED')
        for record in self.records:
            if (record.get('state') not in ('succeeded', 'failed')
                    or record.get('scopes_restored') is not True
                    or record.get('conversion_diagnostics') or record.get('parser_diagnostics')):
                raise ValueError('AUTHORED_TRANSPILE_CAPTURE_FAILED')

    def verified_native_outputs(self, ordinal):
        """Return actual outputs for later authored native analysis.

        This verifies correspondence and no observed mutation, not the route or
        mathematical result. Callers must first accept the finite route, and
        repeat this check after any native analysis to detect mutation.
        """
        self.require_complete()
        if type(ordinal) is not int or not 0 <= ordinal < len(self.records):
            raise ValueError('NATIVE_CALL_ORDINAL')
        record = self.records[ordinal]
        native = self.native_calls[ordinal].get('conversions')
        rows = record.get('conversions')
        if (record.get('state') != 'succeeded' or native is None or rows is None
                or len(native) != len(rows)):
            raise ValueError('NATIVE_OUTPUTS_UNAVAILABLE')
        outputs = []
        for item, row in zip(native, rows):
            if row.get('state') != 'succeeded' or 'output' not in item or 'output' not in row:
                raise ValueError('NATIVE_OUTPUTS_UNAVAILABLE')
            value = item['output']
            if self.snapshot(value) != row['output']:
                raise ValueError('NATIVE_OUTPUT_MUTATED')
            outputs.append(value)
        return tuple(outputs)


class NotebookCapture:
    """Install owned public/graph hooks; preserve original notebook imports.

    The original source imports transpile after bootstrap. Cleanup replaces
    that owned alias with the original callable and never overwrites a foreign
    replacement. Original graph add/path calls still delegate exactly once.
    """
    def __init__(self, api, namespace, journal, snapshot=None):
        import inspect
        self.api = api; self.namespace = namespace
        self.controller = ObservedTranspile(api.transpile, api, snapshot or ProgramSnapshot(api), journal)
        self.controller.source_evidence = api.source_evidence
        self.hooks = []
        self.used = False
        self.active = False
        self.graphs = []
        self.missing = object()
        self.prior_alias = namespace.get('transpile', self.missing)
        self.controller.before_call = self._observe_alias
        self.specs = [(api.public_module, 'transpile', api.transpile, self.controller.wrapper),
                      (api.converter_module, 'transpile', api.transpile, self.controller.wrapper)]
        for name in ('add_conversion', 'has_path'):
            original = getattr(api.ConversionGraph, name)
            self.specs.append((api.ConversionGraph, name, original,
                               self._graph_wrapper(name, original, inspect.signature(original))))

    def _observe_alias(self):
        if self.namespace.get('transpile', self.missing) is self.controller.wrapper:
            self.controller.public_alias_seen = True

    def _graph_wrapper(self, name, original, signature):
        @wraps(original)
        def wrapper(*args, **kwargs):
            record = dict(method=name, state='running', ordinal=len(self.controller.public_events))
            self.controller.public_events.append(record)
            graph = None
            try:
                arguments = signature.bind(*args, **kwargs); arguments.apply_defaults()
                values = arguments.arguments; graph = values['self']
                if not any(graph is item for item in self.graphs):
                    self.graphs.append(graph)
                record['graph_ordinal'] = next(i for i, item in enumerate(self.graphs) if item is graph)
                _, record['before'] = cached_graph_inventory(graph, self.api.conversion_method)
                if name == 'has_path':
                    if type(values['source']) is not str or type(values['target']) is not str:
                        raise ValueError('GRAPH_PATH_ARGUMENTS')
                    record.update(source=values['source'], target=values['target'])
                else:
                    edge = values['edge']; overwrite = values['overwrite']
                    if type(overwrite) is not bool or type(edge.source) is not str or type(edge.target) is not str:
                        raise ValueError('GRAPH_ADD_ARGUMENTS')
                    record.update(source=edge.source, target=edge.target, overwrite=overwrite,
                                  function_identities=[key for key, value in self.api.known_conversion_functions.items()
                                                       if edge._conversion_func is value])
            except Exception as error:
                self.controller._error('graph_before_capture', error)
            self.controller.checkpoint()
            try:
                result = original(*args, **kwargs)
            except BaseException as error:
                record['state'] = 'failed'
                try:
                    record['original_error'] = dict(type=type(error).__name__, message=str(error))
                except Exception as capture_error:
                    self.controller._error('graph_error_capture', capture_error)
                raise
            else:
                record['state'] = 'succeeded'
                if result is None or type(result) is bool:
                    record['result'] = result
                else:
                    self.controller._error('graph_result_capture', ValueError('UNSUPPORTED_GRAPH_RESULT'))
                return result
            finally:
                try:
                    if graph is not None:
                        _, record['after'] = cached_graph_inventory(graph, self.api.conversion_method)
                except Exception as error:
                    self.controller._error('graph_after_capture', error)
                self.controller.checkpoint()
        return wrapper

    def install(self):
        if self.used or self.active:
            raise ValueError('NOTEBOOK_CAPTURE_ALREADY_USED')
        self.used = True
        try:
            for owner, name, original, wrapper in self.specs:
                if getattr(owner, name) is not original:
                    raise ValueError('PUBLIC_HOOK_IDENTITY:' + name)
                self.hooks.append((owner, name, original, wrapper))
                setattr(owner, name, wrapper)
            self.active = True
            self.controller.public_hooks_restored = False
            self.controller.checkpoint()
        except BaseException as error:
            self.controller._error('public_install', error)
            self.restore()
            raise

    def restore(self):
        restored = True
        for owner, name, original, wrapper in reversed(self.hooks):
            try:
                current = getattr(owner, name, self.missing)
                if current is wrapper:
                    setattr(owner, name, original)
                elif current is not original:
                    restored = False
                    self.controller._error('public_restore', ValueError('FOREIGN_HOOK:' + name))
            except Exception as error:
                restored = False
                self.controller._error('public_restore', error)
        alias = self.namespace.get('transpile', self.missing)
        if alias is self.controller.wrapper:
            self.namespace['transpile'] = self.api.transpile
        elif (alias is not self.api.transpile
              and (alias is not self.prior_alias or self.controller.public_alias_seen)):
            restored = False
            self.controller._error('alias_restore', ValueError('FOREIGN_TRANSPILE_ALIAS'))
        self.active = False
        self.controller.public_hooks_restored = restored and self.used
        self.controller.checkpoint()

    def require_complete(self):
        self.controller.require_complete()
        if not self.used or self.active or self.controller.public_hooks_restored is not True:
            raise ValueError('PUBLIC_HOOKS_NOT_RESTORED')

    def check_after(self, original_index, reference, audit):
        """Finite postcell checks; original stdout is audited separately by host."""
        import math
        expected = (13, 15, 19, 22)
        previous = self.controller.postcells
        if (len(previous) >= len(expected) or type(original_index) is not int
                or original_index != expected[len(previous)]
                or any(row['state'] != 'succeeded' for row in previous)):
            raise ValueError('QB013_POSTCELL_ORDER')
        entry = dict(after_original_index=original_index, state='running', checks=[])
        self.controller.postcells.append(entry)
        def require(ok, name):
            entry['checks'].append(dict(name=name, passed=bool(ok)))
            self.controller.checkpoint()
            if not ok: raise ValueError(name)
        try:
            require(self.active and all(getattr(owner, name, self.missing) is wrapper
                    for owner, name, _, wrapper in self.hooks), 'QB013_OWNED_HOOKS_ACTIVE')
            self.controller.require_complete()
            graph = self.namespace['graph']
            ordinals = [i for i, value in enumerate(self.graphs) if value is graph]
            require(len(ordinals) == 1, 'QB013_ORIGINAL_GRAPH_OBSERVED')
            ordinal = ordinals[0]
            if original_index == 13:
                edges, entry['graph'] = cached_graph_inventory(graph, self.api.conversion_method)
                matching = [edge for edge in edges if edge.source == 'cirq' and edge.target == 'stim']
                require(len(matching) == 1 and matching[0] is self.namespace['conversion']
                        and matching[0]._conversion_func is self.api.stim_converter,
                        'QB013_ORIGINAL_CONVERSION_CACHED')
                events = [event for event in self.controller.public_events
                          if event.get('graph_ordinal') == ordinal and event['method'] == 'add_conversion'
                          and event.get('source') == 'cirq' and event.get('target') == 'stim']
                entry['addition_events'] = events
                require(len(events) in (1, 2) and events[0].get('overwrite') is True
                        and events[-1]['state'] == 'succeeded'
                        and all(event.get('function_identities') == ['cirq_to_stim'] for event in events)
                        and (len(events) == 1 or (events[0]['state'] == 'failed'
                             and events[1].get('overwrite') is False)), 'QB013_ORIGINAL_ADD_OR_FALLBACK')
                entry['fallback_taken'] = len(events) == 2
            elif original_index == 15:
                start = previous[-2]['event_count']
                events = [event for event in self.controller.public_events[start:]
                          if event.get('graph_ordinal') == ordinal and event['method'] == 'has_path'
                          and event.get('source') == 'qiskit' and event.get('target') == 'stim']
                entry['path_events'] = events
                require(len(events) == 1 and events[0]['state'] == 'succeeded'
                        and events[0].get('result') is True, 'QB013_ORIGINAL_PATH_TRUE')
            elif original_index == 19:
                require(len(self.controller.records) == 1, 'QB013_SINGLE_ORIGINAL_TRANSPILE')
                record = self.controller.records[0]
                require(record['state'] == 'succeeded' and record.get('target') == 'stim'
                        and record.get('input') == record.get('input_after'), 'QB013_TRANSPILE_SUCCESS_UNCHANGED_INPUT')
                require(self.namespace.get('transpile') is self.controller.wrapper
                        and self.controller.public_alias_seen, 'QB013_ORIGINAL_IMPORTED_ALIAS')
                original = self.controller.snapshot(self.namespace['qiskit_circuit'])
                final = self.controller.snapshot(self.namespace['stim_circuit'])
                require(original == record['input'] and final == record['output'], 'QB013_ORIGINAL_PROGRAM_ENDPOINTS')
                entry['analysis'] = audit.analyze_conversion_states(reference, original, final,
                    record['conversions'], record['parsers'], [1/math.sqrt(2), 0, 0, 1/math.sqrt(2)])
                self.controller.checkpoint()  # Preserve mismatching calculated states before asserting.
                require(entry['analysis']['reference_semantic_acceptance'], 'QB013_REFERENCE_STATE_MISMATCH')
            else:
                require(len(self.controller.records) == 1, 'QB013_NO_ADDED_ORIGINAL_TRANSPILATIONS')
                require(self.controller.snapshot(self.namespace['stim_circuit']) == self.controller.records[0]['output'],
                        'QB013_STIM_PROGRAM_UNCHANGED_AFTER_SAMPLING')
                entry['original_sample_output_pending_host_audit'] = True
                entry['native_execution_verified'] = False
            entry.update(state='succeeded', event_count=len(self.controller.public_events))
            self.controller.checkpoint()
            self.controller.require_complete()
        except BaseException as error:
            entry.update(state='failed', error=dict(type=type(error).__name__, message=str(error)))
            self.controller.checkpoint()
            raise
        return entry


class ProgramSnapshot:
    """Read-only finite program descriptions; no simulation or conversion.

The concrete binder supplies source-gated SDK classes/functions. Unknown
program/gate/target forms are capture errors, never silently omitted.
"""
    def __init__(self, api):
        self.api = api

    @staticmethod
    def _number(value):
        import math
        result = float(value)
        if not math.isfinite(result):
            raise ValueError('NONFINITE_PROGRAM_PARAMETER')
        return result

    def __call__(self, program):
        if isinstance(program, str):
            import re
            match = re.match(r'\s*OPENQASM\s+(2\.0|3(?:\.0)?)\s*;', program)
            if match is None:
                raise ValueError('UNKNOWN_STRING_PROGRAM')
            return dict(format='qasm', version=match.group(1), text=program)
        if isinstance(program, self.api.QuantumCircuit):
            def index(bit):
                return program.find_bit(bit).index
            operations = []
            for instruction in program.data:
                operation = instruction.operation
                standard = self.api.qiskit_operations.get(operation.name)
                if (standard is None or getattr(operation, 'base_class', None) is not standard
                        or getattr(operation, 'condition', None) is not None
                        or getattr(operation, 'blocks', ())):
                    raise ValueError('UNSUPPORTED_QISKIT_OPERATION:'+operation.name)
                operations.append(dict(name=operation.name,
                                       qubits=[index(q) for q in instruction.qubits],
                                       clbits=[index(c) for c in instruction.clbits],
                                       params=[self._number(p) for p in operation.params]))
            def registers(items):
                return [dict(name=r.name, size=len(r), indices=[index(bit) for bit in r]) for r in items]
            return dict(format='qiskit', qubits=program.num_qubits, clbits=program.num_clbits,
                        qregs=registers(program.qregs), cregs=registers(program.cregs),
                        global_phase=self._number(program.global_phase), operations=operations)
        if isinstance(program, self.api.CirqCircuit):
            qubits = sorted(program.all_qubits())
            q2i = {q: i for i, q in enumerate(qubits)}
            labels = [dict(type=type(q).__module__+'.'+type(q).__qualname__, text=str(q),
                           dimension=q.dimension) for q in qubits]
            if any(q['dimension'] != 2 for q in labels):
                raise ValueError('NONBINARY_CIRQ_QID')
            operations = []
            supported = ('HPowGate', 'XPowGate', 'YPowGate', 'ZPowGate', 'CXPowGate', 'CZPowGate', 'IdentityGate')
            for operation in program.all_operations():
                if getattr(operation, 'tags', ()):
                    raise ValueError('UNSUPPORTED_CIRQ_TAGS')
                gate = operation.gate
                name = type(gate).__name__
                row = dict(gate_class=name, qubits=[q2i[q] for q in operation.qubits])
                family = next((family for family in supported if getattr(self.api, family, None) is not None and isinstance(gate, getattr(self.api, family))), None)
                if isinstance(gate, self.api.MeasurementGate):
                    if getattr(gate, 'confusion_map', {}):
                        raise ValueError('UNSUPPORTED_CIRQ_MEASUREMENT_CONFUSION')
                    row.update(measurement_key=self.api.measurement_key_name(operation),
                               invert_mask=list(gate.invert_mask))
                elif family is not None:
                    row['gate_family'] = family
                    if family != 'IdentityGate':
                        row.update(exponent=self._number(gate.exponent),
                                   global_shift=self._number(gate.global_shift))
                else:
                    raise ValueError('UNSUPPORTED_CIRQ_GATE:'+name)
                operations.append(row)
            return dict(format='cirq', sorted_qubits=labels, operations=operations)
        if isinstance(program, self.api.StimCircuit):
            operations = []
            for instruction in program:
                if not isinstance(instruction, self.api.StimInstruction):
                    raise ValueError('UNSUPPORTED_STIM_BLOCK')
                if instruction.name not in ('I', 'X', 'Y', 'Z', 'H', 'S', 'S_DAG', 'SQRT_X', 'SQRT_X_DAG', 'CX', 'CZ', 'M', 'TICK', 'QUBIT_COORDS'):
                    raise ValueError('UNSUPPORTED_STIM_INSTRUCTION:'+instruction.name)
                arguments = instruction.gate_args_copy()
                if arguments and instruction.name != 'QUBIT_COORDS':
                    raise ValueError('UNSUPPORTED_STIM_ARGUMENTS:'+instruction.name)
                targets = instruction.targets_copy()
                if any(not target.is_qubit_target for target in targets):
                    raise ValueError('UNSUPPORTED_STIM_TARGET')
                operations.append(dict(name=instruction.name, qubits=[t.value for t in targets], inverted=[bool(t.is_inverted_result_target) for t in targets],
                                       args=[self._number(a) for a in arguments]))
            return dict(format='stim', text=str(program), qubits=program.num_qubits,
                        measurements=program.num_measurements, operations=operations)
        raise ValueError('UNSUPPORTED_PROGRAM_TYPE')

def cached_graph_inventory(graph, conversion_method):
    """Read actual cached graph callables; do not compute or steer any route.

Return real edge instances separately from JSON-ready evidence. The caller
must defer any capture failure until the authored postcell checkpoint.
"""
    cached = []
    rows = []
    identities = {}
    pairs = set()
    for start, end in graph.edge_list():
        data = graph.get_edge_data(start, end)
        method = data['func']
        edge = getattr(method, '__self__', None)
        if edge is None or getattr(method, '__func__', None) is not conversion_method:
            raise ValueError('UNSUPPORTED_CACHED_CONVERSION_CALLABLE')
        source, target = graph[start], graph[end]
        if edge.source != source or edge.target != target:
            raise ValueError('CACHED_EDGE_ENDPOINT_MISMATCH')
        if (source, target) in pairs:
            raise ValueError('DUPLICATE_CACHED_EDGE')
        pairs.add((source, target))
        if id(edge) not in identities:
            identities[id(edge)] = len(cached)
            cached.append(edge)
        function = edge._conversion_func
        rows.append(dict(source=source, target=target, edge_ordinal=identities[id(edge)],
                         function_module=getattr(function, '__module__', None),
                         function_qualname=getattr(function, '__qualname__', None)))
    listed = list(graph.conversions())
    listed_ordinals = [identities.get(id(edge)) for edge in listed]
    evidence = dict(cached_edges=rows, listed_edge_ordinals=listed_ordinals,
                    listed_and_cached_identity_sets_match=(len(listed) == len(cached)
                        and len({id(edge) for edge in listed}) == len(listed)
                        and {id(edge) for edge in listed} == set(identities)))
    return cached, evidence

class ScopedQasmParser:
    """Observe the actual normalized parser input, never regenerate it."""
    def __init__(self, parser_class, snapshot, checkpoint=None):
        import inspect
        self.owner = parser_class
        self.original = parser_class.parse
        self.signature = inspect.signature(self.original)
        self.snapshot = snapshot
        self.checkpoint = checkpoint
        self.records = []
        self.diagnostics = []
        self.active = False
        self.used = False
        self.wrapper = self._wrapper()

    def _capture(self, record, stage, action):
        try:
            record[stage] = action()
        except Exception as error:
            self.diagnostics.append(dict(stage=stage, type=type(error).__name__, message=str(error)))

    def _checkpoint(self):
        if self.checkpoint is not None:
            try:
                self.checkpoint()
            except Exception as error:
                self.diagnostics.append(dict(stage='checkpoint', type=type(error).__name__, message=str(error)))

    def _wrapper(self):
        @wraps(self.original)
        def observed(*args, **kwargs):
            record = dict(state='running')
            self.records.append(record)
            def input_text():
                qasm = self.signature.bind(*args, **kwargs).arguments['qasm']
                if type(qasm) is not str:
                    raise ValueError('PARSER_INPUT_NOT_TEXT')
                return qasm
            self._capture(record, 'normalized_parser_input', input_text)
            self._checkpoint()
            try:
                result = self.original(*args, **kwargs)
            except BaseException as error:
                record['state'] = 'failed'
                self._capture(record, 'original_error', lambda:dict(type=type(error).__name__, message=str(error)))
                self._checkpoint()
                raise
            record['state'] = 'succeeded'
            self._capture(record, 'parsed_circuit', lambda:self.snapshot(result.circuit))
            def registers():
                def rows(values):
                    if not isinstance(values, dict) or any(
                            type(name) is not str or not name or type(size) is not int or size < 1
                            for name, size in values.items()):
                        raise ValueError('PARSER_REGISTER_SHAPE')
                    return [dict(name=name, size=size) for name, size in values.items()]
                quantum = rows(result.qregs); classical = rows(result.cregs)
                if set(result.qregs) & set(result.cregs):
                    raise ValueError('PARSER_REGISTER_DOMAIN_COLLISION')
                if type(result.supportedFormat) is not bool or type(result.qelib1Include) is not bool:
                    raise ValueError('PARSER_HEADER_FLAGS')
                return dict(qregs=quantum, cregs=classical,
                            supported_format=result.supportedFormat, qelib1_include=result.qelib1Include)
            self._capture(record, 'parsed_registers', registers)
            self._checkpoint()
            return result
        return observed

    def __enter__(self):
        if self.active or self.used or self.owner.parse is not self.original:
            raise ValueError('PARSER_OBSERVER_IDENTITY')
        self.owner.parse = self.wrapper
        self.active = True
        self.used = True
        return self

    def __exit__(self, error_type, error, traceback):
        if self.owner.parse is self.wrapper:
            self.owner.parse = self.original
        elif self.owner.parse is not self.original:
            self.diagnostics.append(dict(stage='restore', type='UnexpectedParserReplacement'))
        self.active = False
        self._checkpoint()
        return False

    def require_complete(self):
        if self.active or self.owner.parse is not self.original or self.diagnostics:
            raise ValueError('AUTHORED_PARSER_CAPTURE_FAILED')


def start_notebook_capture(namespace):
    """Explicit authored bootstrap, called only inside the reserved kernel."""
    import sys
    from pathlib import Path
    if '_qb013_capture' in namespace:
        raise ValueError('NOTEBOOK_CAPTURE_NAMESPACE_COLLISION')
    for name, attribute in (('_qb013_reference', 'state_from_snapshot'),
                            ('_qb013_audit', 'analyze_conversion_states')):
        if not callable(getattr(namespace.get(name), attribute, None)):
            raise ValueError('NOTEBOOK_CAPTURE_PREAMBLE_MISSING:' + name)
    journal = CaptureJournal(Path.cwd() / 'qb013-capture.json')
    api = bind_observation_api(Path(sys.prefix) / 'Lib' / 'site-packages')
    capture = NotebookCapture(api, namespace, journal)
    try:
        capture.install()
        capture.controller.require_complete()
    except BaseException:
        capture.restore()
        raise
    return capture


# Reviewed installed wheel identities; no SDK is imported at module load.
API_MODULE_PATHS = {'qiskit.circuit.quantumcircuit': 'qiskit/circuit/quantumcircuit.py', 'qiskit.circuit.measure': 'qiskit/circuit/measure.py', 'qiskit.circuit.barrier': 'qiskit/circuit/barrier.py', 'cirq.circuits.circuit': 'cirq/circuits/circuit.py', 'cirq.ops.common_gates': 'cirq/ops/common_gates.py', 'cirq.ops.identity': 'cirq/ops/identity.py', 'cirq.ops.measurement_gate': 'cirq/ops/measurement_gate.py', 'cirq.protocols.measurement_key_protocol': 'cirq/protocols/measurement_key_protocol.py', 'stim': 'stim/__init__.py', 'qbraid.transpiler.edge': 'qbraid/transpiler/edge.py', 'qbraid.transpiler.conversions.qasm2.cirq_qasm_parser': 'qbraid/transpiler/conversions/qasm2/cirq_qasm_parser.py', 'qiskit.circuit.library.standard_gates.h': 'qiskit/circuit/library/standard_gates/h.py', 'qiskit.circuit.library.standard_gates.x': 'qiskit/circuit/library/standard_gates/x.py', 'qiskit.circuit.library.standard_gates.y': 'qiskit/circuit/library/standard_gates/y.py', 'qiskit.circuit.library.standard_gates.z': 'qiskit/circuit/library/standard_gates/z.py', 'qiskit.circuit.library.standard_gates.s': 'qiskit/circuit/library/standard_gates/s.py', 'qiskit.circuit.library.standard_gates.sx': 'qiskit/circuit/library/standard_gates/sx.py', 'qiskit.circuit.library.standard_gates.t': 'qiskit/circuit/library/standard_gates/t.py', 'qiskit.circuit.library.standard_gates.i': 'qiskit/circuit/library/standard_gates/i.py'}

API_MODULE_PATHS['stimcirq._cirq_to_stim'] = 'stimcirq/_cirq_to_stim.py'
API_MODULE_PATHS['qbraid.transpiler.conversions.qiskit.qiskit_to_qasm2'] = 'qbraid/transpiler/conversions/qiskit/qiskit_to_qasm2.py'
API_MODULE_PATHS['qbraid.transpiler.conversions.qasm2.qasm2_to_cirq'] = 'qbraid/transpiler/conversions/qasm2/qasm2_to_cirq.py'
API_MODULE_PATHS['qbraid.transpiler'] = 'qbraid/transpiler/__init__.py'
API_MODULE_PATHS['qbraid.transpiler.converter'] = 'qbraid/transpiler/converter.py'
API_MODULE_PATHS['qbraid.transpiler.graph'] = 'qbraid/transpiler/graph.py'

API_SOURCE_HASHES = {'cirq/__init__.py': 'ad47ef403b72c026a4da6250a2284e4b24631b141a84af983aff74f6eb34c393', 'cirq/circuits/circuit.py': 'ade0cba8b323dd264cfb3fbbbcb661bf2e174539e690ad078a06e49c5b4c0cb0', 'cirq/ops/common_gates.py': '58536bbf168741d7d2ff6b26d3e2aeab855a1fea9c81b24e162dbf3c179c057d', 'cirq/ops/eigen_gate.py': '191b4b30bd8b6d306f54c3656abe5223374354ae941cbde547000f47a24e3ce4', 'cirq/ops/identity.py': '2277d2f2cc54d29253d16d46be9f90c02d7ed531804ea296415f4e64468555bf', 'cirq/ops/measurement_gate.py': 'c9cf5c71bce9cbeb22e53285ef6566aeacea82cc60ffad115c25873a3d5df70f', 'cirq/ops/named_qubit.py': '5b31acc60923448f2b4baf76ce922b292deb581174c2f5fbe868ec4a717e83b9', 'cirq/ops/pauli_gates.py': '353b7a25dd56ae592acaf10334a4cbbf3491e69138226afe4834d952cde03e00', 'cirq/ops/raw_types.py': '2003c56eaa2a4d7f58e438d9c7d9a19a8e389ca458f3af27c9ffc7e5a07f8b11', 'cirq/protocols/measurement_key_protocol.py': 'beaa318e6b61b664359d66e2ed77787ddc4535ee72dd62fb0d9910dccfd53e77', 'pyqasm/entrypoint.py': '9068ac27239289ab93787f0e480861cda2302ab57a1678cfbead04ec2fb5b1b1', 'pyqasm/modules/base.py': '231a553ae528fb770a0653811a12088b66dd6f5ccf98621c1201cb6e17f08ef8', 'pyqasm/modules/qasm2.py': '17fcb29f94c0b6c2158b388ef4a44d7121ae8d75968bb19edc1abda9c8719ad9', 'qbraid/__init__.py': '77da1f319238ef1158821a05ecad8dbd0cb058af8230e3379a1f3ca8eb2a1b93', 'qbraid/passes/qasm/compat.py': '967359e5ad4708f0cfc4e341f6aff4189e313d0f96d538dc3e3367ee38f2ce60', 'qbraid/transpiler/__init__.py': '39b7119992a060dfd3f304b95be7be0d1ba9fabe9f1a8aa23cd03bdaaab81346', 'qbraid/transpiler/conversions/qasm2/cirq_qasm_parser.py': '4c147e5e4d0d52b9cfca3c68fc7dd6ac456002ff161a809739e19ae9d4dc9f67', 'qbraid/transpiler/conversions/qasm2/qasm2_to_cirq.py': '38f5fdd9f6a6580ac1cc9621adde6550460f81b3d47d9dee5f211f6bb3d78d0f', 'qbraid/transpiler/conversions/qiskit/qiskit_to_qasm2.py': 'a24321099306a016a22f0c59b460efa7e65301093e2aab44e938a7a45114e4e0', 'qbraid/transpiler/converter.py': '8c77b3a0f0dfeebd544dcba3c570f28f0705ddde0498d0e466ece05305487050', 'qbraid/transpiler/edge.py': '8f0816d6637b0de1c711474f8c5b104e21bada74308a4ab678f704be5e3e798e', 'qbraid/transpiler/graph.py': '415636a57a0fa1cb8cb3467e90042fbde03e078bd225fc072a32bb5433a61b25', 'qiskit/__init__.py': 'ab0eb8d04b9a5b33d80030895c5ffbfd7f23d1041f408cf3f98610dd7e946168', 'qiskit/_accelerate.pyd': '4fe0996035b2e0bdf169a2ad6834afe3b244bc782ef9d1f4eb824f159fe29f80', 'qiskit/circuit/__init__.py': '1857eaa10be44a1270ca5b4252dd5fee81f2f8a9e7ade2dfce209188a2703414', 'qiskit/circuit/barrier.py': 'faa77a6cfee43c4aa84f535fb0ad1fb8ac9fca9956c20b4e129a4d82ac3141c1', 'qiskit/circuit/instruction.py': '058fd7f47d4ad1d61e428f48cc0f18bf8bc364f7555e1f83057a4c7f20fe82ab', 'qiskit/circuit/library/__init__.py': 'f13b126d1649b5c1ecf533824fef6afa8d333a038d64c63a7009971740e2e073', 'qiskit/circuit/library/standard_gates/__init__.py': '6c4b58c0083aa4b14312a11f96d7fdef8276bd05efa7422642886d1ad17fa844', 'qiskit/circuit/library/standard_gates/h.py': '34314a6e590ff56abfd1a0779cb25f818ba661e745e574111859a8ee5197b1d5', 'qiskit/circuit/library/standard_gates/i.py': '36ad7071aec0f4a1001f9218cd076f99ecafb8d2150140e5f90dac5c2d2d79fd', 'qiskit/circuit/library/standard_gates/s.py': '240a225692606676830db3971910adbd0d033bb106e76be7f20d3320ed524345', 'qiskit/circuit/library/standard_gates/sx.py': '947a0b1116b34bce763dd5693f34038d88a6af49799a3a42ebe4b297c1a3617a', 'qiskit/circuit/library/standard_gates/t.py': '3ff8ddb84c8d1654e5dff53b6fe0c4043d435c05554f229f3e851b24eeded315', 'qiskit/circuit/library/standard_gates/x.py': '0b2df77730961226800ed8de6d99296c9472f0eba676a6d1c5eb661424519227', 'qiskit/circuit/library/standard_gates/y.py': '182a3bcc3e851e9df5040e1c23aa42107d138f1e0bc8aeadcbe1a7d6b78e8fc2', 'qiskit/circuit/library/standard_gates/z.py': '0889bc0ec78e3802b4ba75996302f4ceebfba8d8b7ba76ab3764eb3f8a5e367f', 'qiskit/circuit/measure.py': 'ef581196048758098310be73857315c65099d84bf5beb8d2e6a17324927c3d2d', 'qiskit/circuit/quantumcircuit.py': 'd70c1c9350a94c2e07ae9fef24746a95633c36846719d8789c4a98185f11b281', 'qiskit/circuit/singleton.py': 'e2e462ca6f879d4d5eb6573ae12fdc56ee1cbdea21f9bf85bf34dde04bd08107', 'qiskit/qasm2/export.py': '5e7c72a4867fa7b38335d5a0cd2c92345f47080fe3b15ab2a48b5b623cdf7741', 'stim/__init__.py': '3a6351ab2d211ec938c659b0ceb1df786a35b5799d9d8e35b9be19ce2f193445', 'stim/__init__.pyi': '39569e7779770c50f496a3cb46753aed748ac98c790d706479f3c280de36e28a', 'stim/_detect_machine_architecture.cp312-win_amd64.pyd': 'f1ff4f3277490e93204e7f05571676f66974ca2be7697e1ccfe48226d3a1a197', 'stim/_stim_polyfill.cp312-win_amd64.pyd': '7ca9489a5ac6f96d1c18ab4d66578372103ca6536b11448f608a3d82f41ab2dc', 'stim/_stim_sse2.cp312-win_amd64.pyd': '5e5b0cccd60266723d06c746eb8aaad18b3e72980cc5130ec4f7af46cf3c1880', 'stimcirq/_cirq_to_stim.py': 'a0af8888780154641540dfa5ed4051ce3b6a0fd337e4f96c7fd0b942200860df'}

if __name__ == '__main__':
    _qb013_capture = start_notebook_capture(globals())
