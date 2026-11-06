"""Exact Boolean/Walsh expectations; no quantum SDK or sampled expectations."""
from itertools import combinations


def walsh_numerators(values):
    """Amplitude numerator for H^n phase(f) H^n |0>; denominator len(values)."""
    values = tuple(values)
    size = len(values)
    if size < 2 or size & (size - 1) or any(type(v) is not int or v not in (0, 1) for v in values):
        raise ValueError('Expected a power-of-two Boolean truth table')
    return [sum((-1 if values[x] ^ ((x & y).bit_count() & 1) else 1)
                for x in range(size)) for y in range(size)]


def cases():
    rows = []
    tables = [(0, 0, 0, 0), (1, 1, 1, 1)]
    tables += [tuple(int(x in ones) for x in range(4)) for ones in combinations(range(4), 2)]
    for number, table in enumerate(tables):
        spectrum = walsh_numerators(table)
        rows.append(dict(id=f'dj2-{number}', family='Deutsch-Jozsa', qubits=2,
                         truth_table=list(table), amplitude_numerators=spectrum,
                         amplitude_denominator=4,
                         promise='constant' if len(set(table)) == 1 else 'balanced',
                         deterministic_integer=next(y for y, a in enumerate(spectrum) if abs(a) == 4)))
    for n, secret in [(2, s) for s in range(4)] + [(3, 1), (3, 4)]:
        table = [(x & secret).bit_count() & 1 for x in range(1 << n)]
        spectrum = walsh_numerators(table)
        rows.append(dict(id=f'bv{n}-{secret:0{n}b}', family='Bernstein-Vazirani', qubits=n,
                         secret_integer=secret, truth_table=table,
                         amplitude_numerators=spectrum, amplitude_denominator=1 << n,
                         deterministic_integer=secret))
    for row in rows:
        y = row['deterministic_integer']; n = row['qubits']
        row['expected_bits_q0_first'] = [(y >> q) & 1 for q in range(n)]
        row['expected_bits_msb_first'] = f'{y:0{n}b}'
    return rows


# Independent finite state reference. The reviewed Walsh reference above is
# retained byte-for-byte as a prefix; no SDK supplies matrices or expectations.
def _finite_real(value):
    import math
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('NONFINITE_REFERENCE_PARAMETER')
    return float(value)


def _matrix(name):
    import cmath
    import math
    one = [[1, 0], [0, 1]]
    gates = {
        'id': one, 'x': [[0, 1], [1, 0]], 'y': [[0, -1j], [1j, 0]],
        'z': [[1, 0], [0, -1]], 'h': [[1/math.sqrt(2), 1/math.sqrt(2)],
                                      [1/math.sqrt(2), -1/math.sqrt(2)]],
        's': [[1, 0], [0, 1j]], 'sdg': [[1, 0], [0, -1j]],
        't': [[1, 0], [0, cmath.exp(1j*math.pi/4)]],
        'tdg': [[1, 0], [0, cmath.exp(-1j*math.pi/4)]],
        'sx': [[(1+1j)/2, (1-1j)/2], [(1-1j)/2, (1+1j)/2]],
        'sxdg': [[(1-1j)/2, (1+1j)/2], [(1+1j)/2, (1-1j)/2]],
        # Local bit0 is the first target, including the CX control.
        'cx': [[1,0,0,0], [0,0,0,1], [0,0,1,0], [0,1,0,0]],
        'cz': [[1,0,0,0], [0,1,0,0], [0,0,1,0], [0,0,0,-1]],
    }
    if name not in gates:
        raise ValueError('UNSUPPORTED_REFERENCE_GATE:'+str(name))
    return gates[name]


def _apply(state, matrix, targets):
    size = 1 << len(targets)
    if len(matrix) != size or any(len(row) != size for row in matrix):
        raise ValueError('REFERENCE_GATE_ARITY')
    result = [0j] * len(state)
    clear = ~sum(1 << q for q in targets)
    for basis, amplitude in enumerate(state):
        local = sum(((basis >> q) & 1) << position for position, q in enumerate(targets))
        for target_basis in range(size):
            destination = (basis & clear) | sum(((target_basis >> p) & 1) << q
                                               for p, q in enumerate(targets))
            result[destination] += matrix[target_basis][local] * amplitude
    return result


def state_from_snapshot(program):
    """Return the zero-input state before terminal Z measurements, at most4q.

    Preserve measurement/annotation records separately. Reject mid-circuit
    measurement, noise, resets and unsupported gates; do not simulate collapse
    or infer sampling results. Snapshot provenance is the caller's obligation.
    """
    import cmath
    import math
    kind = program['format']
    if kind not in ('qiskit', 'cirq', 'stim'):
        raise ValueError('UNSUPPORTED_REFERENCE_FORMAT')
    count = len(program['sorted_qubits']) if kind == 'cirq' else program['qubits']
    if type(count) is not int or not 1 <= count <= 4:
        raise ValueError('REFERENCE_QUBIT_SCOPE')
    if kind == 'cirq' and any(q.get('dimension') != 2 for q in program['sorted_qubits']):
        raise ValueError('REFERENCE_QID_DIMENSION')
    if kind == 'qiskit' and (type(program['clbits']) is not int or program['clbits'] < 0):
        raise ValueError('REFERENCE_CLBIT_COUNT')
    state = [1+0j] + [0j] * ((1 << count)-1)
    measurements = []; annotations = []
    phase = _finite_real(program['global_phase']) if kind == 'qiskit' else 0.0
    state[0] *= cmath.exp(1j*phase)

    def targets(values, unique=True, allow_empty=False):
        if (not isinstance(values, list) or (not values and not allow_empty)
                or any(type(q) is not int or not 0 <= q < count for q in values)
                or (unique and len(set(values)) != len(values))):
            raise ValueError('REFERENCE_TARGETS')
        return values

    def apply(matrix, qubits):
        nonlocal state
        if measurements:
            raise ValueError('UNSUPPORTED_POST_MEASUREMENT_GATE')
        state = _apply(state, matrix, targets(qubits))

    for index, operation in enumerate(program['operations']):
        if kind == 'qiskit':
            name = operation['name']; qubits = targets(operation['qubits'])
            if operation['params'] != []:
                raise ValueError('UNSUPPORTED_REFERENCE_PARAMETERS')
            if name == 'barrier':
                if operation['clbits'] != []: raise ValueError('REFERENCE_BARRIER_CLBITS')
                annotations.append(dict(index=index, kind='barrier', qubits=qubits)); continue
            if name == 'measure':
                bits = operation['clbits']
                if (len(qubits) != 1 or not isinstance(bits, list) or len(bits) != 1
                        or type(bits[0]) is not int or not 0 <= bits[0] < program['clbits']):
                    raise ValueError('REFERENCE_MEASUREMENT_SHAPE')
                measurements.append(dict(index=index, qubits=qubits, clbits=bits)); continue
            if operation['clbits'] != []: raise ValueError('REFERENCE_GATE_CLBITS')
            apply(_matrix(name), qubits)
        elif kind == 'cirq':
            qubits = targets(operation['qubits'])
            if 'measurement_key' in operation:
                mask = operation['invert_mask']
                if (type(operation['measurement_key']) is not str or not isinstance(mask, list)
                        or len(mask) > len(qubits) or any(type(x) is not bool for x in mask)):
                    raise ValueError('REFERENCE_MEASUREMENT_SHAPE')
                measurements.append(dict(index=index, qubits=qubits, key=operation['measurement_key'],
                                         inverted=mask+[False]*(len(qubits)-len(mask)))); continue
            family = operation['gate_family']
            if family == 'IdentityGate':
                dimension = 1 << len(qubits)
                matrix = [[int(i == j) for j in range(dimension)] for i in range(dimension)]
            else:
                names = dict(HPowGate='h', XPowGate='x', YPowGate='y', ZPowGate='z',
                             CXPowGate='cx', CZPowGate='cz')
                if family not in names: raise ValueError('UNSUPPORTED_REFERENCE_CIRQ_FAMILY')
                base = _matrix(names[family]); dimension = len(base)
                exponent = _finite_real(operation['exponent']); shift = _finite_real(operation['global_shift'])
                minus = cmath.exp(1j*math.pi*exponent)
                global_factor = cmath.exp(1j*math.pi*exponent*shift)
                matrix = [[global_factor*((int(i == j)+base[i][j])/2
                           +minus*(int(i == j)-base[i][j])/2)
                           for j in range(dimension)] for i in range(dimension)]
            apply(matrix, qubits)
        else:
            name = operation['name']; qubits = targets(operation['qubits'], unique=False, allow_empty=name=='TICK')
            inverted = operation['inverted']; arguments = operation['args']
            if (not isinstance(inverted, list) or len(inverted) != len(qubits)
                    or any(type(x) is not bool for x in inverted)):
                raise ValueError('REFERENCE_STIM_INVERSION_SHAPE')
            if name == 'M':
                if arguments != []: raise ValueError('UNSUPPORTED_NOISY_MEASUREMENT')
                measurements.extend(dict(index=index, qubits=[q], inverted=[flag])
                                    for q, flag in zip(qubits, inverted)); continue
            if any(inverted): raise ValueError('UNSUPPORTED_NONMEASUREMENT_INVERSION')
            if name in ('TICK', 'QUBIT_COORDS'):
                if name == 'TICK' and (qubits or arguments): raise ValueError('REFERENCE_TICK_SHAPE')
                if name == 'QUBIT_COORDS' and len(qubits) != 1: raise ValueError('REFERENCE_COORDINATE_SCOPE')
                annotations.append(dict(index=index, kind=name, qubits=qubits,
                                        args=[_finite_real(x) for x in arguments])); continue
            if arguments != []: raise ValueError('UNSUPPORTED_REFERENCE_STIM_ARGUMENTS')
            names = dict(I='id', X='x', Y='y', Z='z', H='h', S='s', S_DAG='sdg',
                         SQRT_X='sx', SQRT_X_DAG='sxdg', CX='cx', CZ='cz')
            if name not in names: raise ValueError('UNSUPPORTED_REFERENCE_STIM_GATE')
            width = 2 if name in ('CX', 'CZ') else 1
            if len(qubits) % width: raise ValueError('REFERENCE_GATE_ARITY')
            for start in range(0, len(qubits), width):
                apply(_matrix(names[name]), qubits[start:start+width])
    norm = sum(abs(value)**2 for value in state)
    if kind == 'stim' and (type(program['measurements']) is not int or program['measurements'] != len(measurements)):
        raise ValueError('REFERENCE_MEASUREMENT_COUNT')
    if not math.isfinite(norm) or abs(norm-1) > 1e-12:
        raise ValueError('REFERENCE_STATE_NORMALIZATION')
    return dict(state=state, qubits=count, measurements=measurements, annotations=annotations,
                convention='little-endian, zero input, before terminal Z measurements',
                norm_squared=norm, original_global_phase=phase)


def compare_states(expected, actual, actual_to_expected=None, tolerance=1e-10):
    """Compare pure-state density matrices; report global-phase-insensitive scope."""
    import math
    size = len(expected)
    if size < 2 or size > 16 or size & (size-1) or len(actual) != size:
        raise ValueError('REFERENCE_STATE_DIMENSION')
    for vector in (expected, actual):
        if any(type(x) not in (int, float, complex) or not math.isfinite(complex(x).real)
               or not math.isfinite(complex(x).imag) for x in vector):
            raise ValueError('NONFINITE_REFERENCE_STATE')
        if abs(sum(abs(x)**2 for x in vector)-1) > 1e-12:
            raise ValueError('REFERENCE_STATE_NORMALIZATION')
    n = size.bit_length()-1
    mapping = list(range(n)) if actual_to_expected is None else actual_to_expected
    if (not isinstance(mapping, (list, tuple)) or len(mapping) != n
            or any(type(q) is not int for q in mapping) or sorted(mapping) != list(range(n))):
        raise ValueError('REFERENCE_STATE_MAPPING')
    tolerance = _finite_real(tolerance)
    if tolerance <= 0 or tolerance > 1e-10: raise ValueError('REFERENCE_STATE_TOLERANCE')
    reordered = [0j] * size
    for basis, amplitude in enumerate(actual):
        destination = sum(((basis >> q) & 1) << mapping[q] for q in range(n))
        reordered[destination] = complex(amplitude)
    residual = max(abs(complex(expected[i])*complex(expected[j]).conjugate()
                       -reordered[i]*reordered[j].conjugate()) for i in range(size) for j in range(size))
    return dict(equivalent=residual <= tolerance, max_density_error=residual, tolerance=tolerance,
                actual_to_expected=list(mapping), global_phase_sensitive=False,
                all_input_unitary_equivalence=False)
