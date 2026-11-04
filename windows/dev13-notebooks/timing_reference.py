# Scalar ALAP reference retained verbatim below from reviewed research SHA256
# b08f56cbedccdaded7e1834176e7a3d2fded11d230780b325623d84530df2b80.
"""Authored finite integer-dt DAG ALAP oracle. No SDK, source or provider execution."""
import hashlib
import json
import pathlib
import sys

KINDS={'gate','delay','barrier','measure','classical'}
def require(ok,code):
    if not ok:raise ValueError(code)

def schedule(operations):
    require(isinstance(operations,list) and operations,'EMPTY_OR_INVALID_DAG')
    nodes={}
    for o in operations:
        require(isinstance(o,dict) and set(o)=={'id','kind','duration_dt','resources','after'},'OP_SCHEMA')
        name=o['id'];require(isinstance(name,str) and bool(name) and name not in nodes,'DUPLICATE_OR_INVALID_ID')
        require(isinstance(o['kind'],str) and o['kind'] in KINDS,'UNSUPPORTED_KIND')
        duration=o['duration_dt'];require(type(duration) is int and duration>=0,'NONNEGATIVE_INTEGER_DT_REQUIRED')
        resources=o['resources'];require(isinstance(resources,list) and resources and all(isinstance(r,str) and len(r)>2 and r[:2] in ('q:','c:') for r in resources) and len(set(resources))==len(resources),'RESOURCE_SCHEMA')
        after=o['after'];require(isinstance(after,list) and all(isinstance(x,str) for x in after) and len(set(after))==len(after),'EDGE_SCHEMA')
        require(o['kind']!='barrier' or duration==0,'BARRIER_NONZERO_DURATION')
        if o['kind']=='measure':require(any(r.startswith('q:') for r in resources) and any(r.startswith('c:') for r in resources),'MEASUREMENT_RESOURCE_MAPPING_REQUIRED')
        nodes[name]=dict(o)
    successors={name:[] for name in nodes};indegree={name:0 for name in nodes}
    for name,o in nodes.items():
        for predecessor in o['after']:
            require(predecessor in nodes,'UNKNOWN_PREDECESSOR')
            successors[predecessor].append(name);indegree[name]+=1
    ready=sorted(name for name in nodes if indegree[name]==0);order=[]
    while ready:
        name=ready.pop(0);order.append(name)
        for child in successors[name]:
            indegree[child]-=1
            if indegree[child]==0:ready.append(child);ready.sort()
    require(len(order)==len(nodes),'CYCLIC_DAG')
    ancestors={}
    for name in order:
        ancestors[name]=set(nodes[name]['after'])
        for parent in nodes[name]['after']:ancestors[name].update(ancestors[parent])
    # The mapper, not this oracle, must provide resource ordering. Never invent one.
    for i,left in enumerate(order):
        for right in order[i+1:]:
            if set(nodes[left]['resources']) & set(nodes[right]['resources']):
                require(left in ancestors[right] or right in ancestors[left],'UNORDERED_RESOURCE_CONFLICT')
    early={}
    for name in order:
        early[name]=max((early[p]+nodes[p]['duration_dt'] for p in nodes[name]['after']),default=0)
    makespan=max(early[name]+nodes[name]['duration_dt'] for name in nodes)
    late={}
    for name in reversed(order):
        deadline=min((late[child] for child in successors[name]),default=makespan)
        late[name]=deadline-nodes[name]['duration_dt']
        require(late[name]>=early[name],'INFEASIBLE_LATEST_START')
    for name,o in nodes.items():
        for p in o['after']:require(late[p]+nodes[p]['duration_dt']<=late[name],'INTERNAL_EDGE_VIOLATION')
    return {'makespan_dt':makespan,'asap_starts_dt':early,'alap_starts_dt':late,'ends_dt':{n:late[n]+nodes[n]['duration_dt'] for n in nodes},'slack_dt':{n:late[n]-early[n] for n in nodes},'topological_order':order}

def op(name,kind,duration,resources,after=()):
    return {'id':name,'kind':kind,'duration_dt':duration,'resources':resources,'after':list(after)}

def fixtures():
    return [
      {'id':'independent_resources','ops':[op('short','gate',3,['q:0']),op('long','gate',8,['q:1'])], 'makespan':8,'early':{'short':0,'long':0},'late':{'short':5,'long':0},'hand_derivation':'Two independent chains have lengths3 and8; common finish8 moves the short gate to5.'},
      {'id':'barrier_synchronization','ops':[op('a','gate',2,['q:0']),op('b','gate',5,['q:1']),op('sync','barrier',0,['q:0','q:1'],['a','b']),op('tail','gate',1,['q:0'],['sync'])], 'makespan':6,'early':{'a':0,'b':0,'sync':5,'tail':5},'late':{'a':3,'b':0,'sync':5,'tail':5},'hand_derivation':'Barrier waits for length5 branch; tail ends6. Latest barrier5 requires a to start3; barrier consumes no dt.'},
      {'id':'unequal_measurements_and_classical_dependency','ops':[op('h','gate',2,['q:0']),op('wait','delay',1,['q:1']),op('cx','gate',3,['q:0','q:1'],['h','wait']),op('bar','barrier',0,['q:0','q:1'],['cx']),op('m0','measure',4,['q:0','c:0'],['bar']),op('m1','measure',7,['q:1','c:1'],['bar']),op('use_c0','classical',2,['c:0'],['m0'])], 'makespan':12,'early':{'h':0,'wait':0,'cx':2,'bar':5,'m0':5,'m1':5,'use_c0':9},'late':{'h':0,'wait':1,'cx':2,'bar':5,'m0':6,'m1':5,'use_c0':10},'hand_derivation':'h2+cx3+m1(7)=12 is critical. The m0(4)+consumer2 suffix needs6, so m0 starts6 and consumer10. Explicit delay starts1. Consumer models a dependency token, not supported dynamic-circuit execution.'},
      {'id':'classical_read_after_measure','ops':[op('m','measure',5,['q:0','c:0']),op('consume','classical',3,['c:0'],['m']),op('parallel','gate',10,['q:1'])], 'makespan':10,'early':{'m':0,'consume':5,'parallel':0},'late':{'m':2,'consume':7,'parallel':0},'hand_derivation':'Independent10dt chain fixes horizon. Measurement5 plus dependent classical3 is an8dt chain and shifts to start2.'},
      {'id':'transitive_resource_order','ops':[op('a','gate',2,['q:0']),op('bridge','gate',3,['q:1'],['a']),op('b','delay',4,['q:0'],['bridge'])], 'makespan':9,'early':{'a':0,'bridge':2,'b':5},'late':{'a':0,'bridge':2,'b':5},'hand_derivation':'Explicit serial dependency2+3+4=9; q0 operations are transitively ordered.'},
    ]

def main():
    passed=[]
    for f in fixtures():
        result=schedule(f['ops'])
        require(result['makespan_dt']==f['makespan'] and result['asap_starts_dt']==f['early'] and result['alap_starts_dt']==f['late'],'HAND_DERIVED_FIXTURE_MISMATCH:'+f['id'])
        passed.append(dict(f,result=result))
    negatives=[('quantum_conflict',[op('a','gate',2,['q:0']),op('b','gate',3,['q:0'])],'UNORDERED_RESOURCE_CONFLICT'),('missing_classical_dependency',[op('m','measure',5,['q:0','c:0']),op('consume','classical',3,['c:0'])],'UNORDERED_RESOURCE_CONFLICT'),('cycle',[op('a','gate',1,['q:0'],['b']),op('b','gate',1,['q:1'],['a'])],'CYCLIC_DAG'),('unknown_parent',[op('a','gate',1,['q:0'],['absent'])],'UNKNOWN_PREDECESSOR'),('barrier_duration',[op('a','barrier',1,['q:0'])],'BARRIER_NONZERO_DURATION'),('measure_missing_classical',[op('a','measure',1,['q:0'])],'MEASUREMENT_RESOURCE_MAPPING_REQUIRED'),('unsupported_controlflow',[op('a','if_else',1,['q:0'])],'UNSUPPORTED_KIND')]
    for label,value in [('negative',-1),('fractional',.5),('nonfinite_nan',float('nan')),('nonfinite_inf',float('inf')),('float_integer',1.0),('boolean',True)]:negatives.append((label,[op('a','gate',value,['q:0'])],'NONNEGATIVE_INTEGER_DT_REQUIRED'))
    rejections=[]
    for name,operations,code in negatives:
        try:schedule(operations)
        except ValueError as error:require(str(error)==code,'WRONG_REJECTION:'+name);rejections.append({'id':name,'diagnostic':str(error)})
        else:raise ValueError('EXPECTED_REJECTION:'+name)
    require(passed[0]['result']['alap_starts_dt']!=passed[0]['result']['asap_starts_dt'],'ASAP_NOT_DISTINGUISHED')
    root=pathlib.Path(__file__).resolve().parent
    result={'scope':'authored integer-dt scalar DAG oracle, not Qiskit scheduling','script_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'python':sys.version,'positive_fixtures':passed,'negative_fixtures':rejections,'counts':{'positive':len(passed),'rejections':len(rejections)},'assumptions':['fixed directed ordering for every shared exclusive resource','durations are already mapped exact nonnegative integer dt','zero-duration barriers still have ordering edges','measurement holds declared quantum/classical resources for its whole duration','no alignment constraints, conditional latency or feedback semantics','all disconnected components share minimal makespan horizon'],'actual_Qiskit_execution':False}
    if '--write' in sys.argv:(root/'ibm-timing-alap-reference.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(result['counts']))
if __name__=='__main__':main()

# Independent finite state/layout and timing-table checks; standard library only.
import cmath
import math

STATE_TOLERANCE = 1e-10
TICK_TOLERANCE = 1e-9


def finite_number(value):
    require(type(value) in (int, float) and math.isfinite(value), 'FINITE_REAL_REQUIRED')
    return value


def duration_ticks(seconds, dt):
    finite_number(seconds)
    finite_number(dt)
    require(seconds >= 0 and dt > 0, 'INVALID_DURATION_UNIT')
    ratio = seconds / dt
    require(math.isfinite(ratio), 'INVALID_DURATION_UNIT')
    ticks = round(ratio)
    require(abs(ratio - ticks) <= TICK_TOLERANCE, 'FRACTIONAL_TARGET_TICKS')
    return ticks


def check_schedule(operations, observed_starts, observed_horizon):
    expected = schedule(operations)
    require(type(observed_starts) is dict and set(observed_starts) == set(expected['alap_starts_dt']),
            'OBSERVED_OPERATION_SET_MISMATCH')
    require(all(type(v) is int and v >= 0 for v in observed_starts.values()), 'OBSERVED_INTEGER_TICKS_REQUIRED')
    require(type(observed_horizon) is int and observed_horizon == expected['makespan_dt'], 'SCHEDULE_HORIZON_MISMATCH')
    require(observed_starts == expected['alap_starts_dt'], 'ALAP_START_MISMATCH')
    return expected


def padding_intervals(operations, starts, horizon, num_qubits):
    """Expected idle complements from pre-padding operations, never padded input."""
    require(type(num_qubits) is int and 1 <= num_qubits <= 8, 'FINITE_QUBIT_COUNT_REQUIRED')
    check_schedule(operations, starts, horizon)
    occupied = {q: [] for q in range(num_qubits)}
    for operation in operations:
        for resource in operation['resources']:
            if resource.startswith('q:'):
                label = resource[2:]
                require(label.isdigit() and str(int(label)) == label and int(label) in occupied, 'INVALID_PHYSICAL_WIRE')
                start = starts[operation['id']]
                occupied[int(label)].append((start, start + operation['duration_dt']))
    result = {}
    for q, intervals in occupied.items():
        cursor, gaps = 0, []
        for start, end in sorted(intervals):
            require(start >= cursor, 'OVERLAPPING_QUANTUM_INTERVALS')
            if start > cursor:
                gaps.append([cursor, start])
            cursor = end
        if cursor < horizon:
            gaps.append([cursor, horizon])
        result[str(q)] = gaps
    return result


def _gate_matrix(name, params):
    require(type(params) is list, 'INVALID_GATE_PARAMETERS')
    for value in params:
        finite_number(value)
    if name == 'rz':
        require(len(params) == 1, 'INVALID_GATE_PARAMETERS')
        angle = params[0] / 2
        return [[cmath.exp(-1j * angle), 0], [0, cmath.exp(1j * angle)]]
    require(not params, 'INVALID_GATE_PARAMETERS')
    if name == 'id':
        return [[1, 0], [0, 1]]
    if name == 'x':
        return [[0, 1], [1, 0]]
    if name == 'h':
        scale = 1 / math.sqrt(2)
        return [[scale, scale], [scale, -scale]]
    if name == 'sx':
        return [[(1+1j)/2, (1-1j)/2], [(1-1j)/2, (1+1j)/2]]
    raise ValueError('UNSUPPORTED_UNITARY_GATE:' + str(name))


def scalar_state(operations, num_qubits, global_phase=0):
    """Little-endian physical state, independently defined matrices and CX.

    Final measurement is recorded, not sampled. Only trailing measure/barrier/
    delay records may follow the first measurement; no mid-circuit adaptation.
    """
    require(type(num_qubits) is int and 1 <= num_qubits <= 8, 'FINITE_QUBIT_COUNT_REQUIRED')
    require(type(operations) is list, 'INVALID_UNITARY_OPERATIONS')
    finite_number(global_phase)
    state = [0j] * (1 << num_qubits)
    state[0] = cmath.exp(1j * global_phase)
    measured_q, measured_c, measurements = set(), set(), []
    for operation in operations:
        require(type(operation) is dict and set(operation) == {'name', 'qubits', 'clbits', 'params'}, 'UNITARY_OPERATION_SCHEMA')
        name, qubits, clbits, params = (operation[k] for k in ('name', 'qubits', 'clbits', 'params'))
        require(type(name) is str and type(qubits) is list and bool(qubits)
                and all(type(q) is int and 0 <= q < num_qubits for q in qubits)
                and len(set(qubits)) == len(qubits), 'INVALID_GATE_QUBITS')
        require(type(clbits) is list and type(params) is list, 'INVALID_GATE_PARAMETERS')
        if name == 'measure':
            require(len(qubits) == len(clbits) == 1 and not params and type(clbits[0]) is int and clbits[0] >= 0,
                    'INVALID_MEASUREMENT_MAPPING')
            require(qubits[0] not in measured_q and clbits[0] not in measured_c, 'DUPLICATE_MEASUREMENT_MAPPING')
            measured_q.add(qubits[0]); measured_c.add(clbits[0])
            measurements.append([qubits[0], clbits[0]])
            continue
        require(not clbits, 'UNSUPPORTED_CLASSICAL_OPERATION')
        if name == 'barrier':
            require(not params, 'INVALID_GATE_PARAMETERS')
            continue
        if name == 'delay':
            require(len(qubits) == 1 and len(params) == 1 and type(params[0]) is int and params[0] >= 0,
                    'INVALID_DELAY_TICKS')
            continue
        require(not measurements, 'NONFINAL_MEASUREMENT')
        if name == 'cx':
            require(len(qubits) == 2 and not params, 'INVALID_CX')
            control, target = qubits
            updated = [0j] * len(state)
            for index, amplitude in enumerate(state):
                destination = index ^ (1 << target) if index & (1 << control) else index
                updated[destination] = amplitude
            state = updated
        else:
            require(len(qubits) == 1, 'INVALID_GATE_ARITY')
            matrix = _gate_matrix(name, params)
            bit = 1 << qubits[0]
            for zero in range(len(state)):
                if zero & bit:
                    continue
                one = zero | bit
                a, b = state[zero], state[one]
                state[zero] = matrix[0][0]*a + matrix[0][1]*b
                state[one] = matrix[1][0]*a + matrix[1][1]*b
    require(abs(sum(abs(a)**2 for a in state) - 1) <= STATE_TOLERANCE, 'STATE_NORMALIZATION')
    return state, measurements


def reduced_density(state, logical_to_physical):
    require(type(state) is list and len(state) >= 2 and len(state) & (len(state)-1) == 0, 'INVALID_STATE_SIZE')
    num_qubits = len(state).bit_length() - 1
    require(type(logical_to_physical) is list and bool(logical_to_physical)
            and all(type(q) is int and 0 <= q < num_qubits for q in logical_to_physical)
            and len(set(logical_to_physical)) == len(logical_to_physical), 'INVALID_LOGICAL_LAYOUT')
    require(all(type(a) in (int, float, complex) and math.isfinite(complex(a).real)
                and math.isfinite(complex(a).imag) for a in state), 'INVALID_STATE_AMPLITUDE')
    require(abs(sum(abs(a)**2 for a in state)-1) <= STATE_TOLERANCE, 'STATE_NORMALIZATION')
    others = [q for q in range(num_qubits) if q not in logical_to_physical]
    groups = {}
    for physical, amplitude in enumerate(state):
        logical = sum(((physical >> q) & 1) << i for i, q in enumerate(logical_to_physical))
        ancilla = sum(((physical >> q) & 1) << i for i, q in enumerate(others))
        vector = groups.setdefault(ancilla, [0j] * (1 << len(logical_to_physical)))
        vector[logical] = complex(amplitude)
    size = 1 << len(logical_to_physical)
    return [[sum(v[row]*v[col].conjugate() for v in groups.values()) for col in range(size)] for row in range(size)]


def check_density(actual, expected):
    require(type(actual) is list and type(expected) is list and len(actual) == len(expected) and len(actual) > 0,
            'DENSITY_SHAPE')
    size = len(expected)
    require(all(type(row) is list and len(row) == size for row in actual+expected), 'DENSITY_SHAPE')
    for row in actual+expected:
        require(all(type(a) in (int, float, complex) and math.isfinite(complex(a).real)
                    and math.isfinite(complex(a).imag) for a in row), 'NONFINITE_DENSITY')
    error = max(abs(actual[i][j]-expected[i][j]) for i in range(size) for j in range(size))
    trace_error = abs(sum(actual[i][i] for i in range(size))-1)
    require(error <= STATE_TOLERANCE and trace_error <= STATE_TOLERANCE, 'DENSITY_MISMATCH')
    return dict(max_entry_error=error, trace_error=trace_error)


def bell_density():
    return [[0.5, 0, 0, 0.5], [0, 0, 0, 0], [0, 0, 0, 0], [0.5, 0, 0, 0.5]]
