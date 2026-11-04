import json
from qiskit.quantum_info import Operator, Statevector

def classical_oracle(circuit):
    width=circuit.num_qubits
    truth=[]
    expected=np.zeros((2**width,2**width),dtype=complex)
    for basis in range(2**width):
        bits=[(basis>>i)&1 for i in range(width)]
        for item in circuit.data:
            name=item.operation.name; wires=[circuit.find_bit(q).index for q in item.qubits]
            if name=='barrier':continue
            if name=='x':bits[wires[0]]^=1
            elif name in ('cx','ccx','mcx'):
                if all(bits[i] for i in wires[:-1]):bits[wires[-1]]^=1
            else:raise AssertionError(('unmodeled source gate',name))
        final=sum(bit<<i for i,bit in enumerate(bits));expected[final,basis]=1
        x=basis & ((1<<(width-1))-1)
        if final & ((1<<(width-1))-1)!=x:raise AssertionError('input changed')
        if basis < 1<<(width-1):truth.append(bits[-1])
        elif bits[-1] != (1^truth[x]):raise AssertionError('not XOR oracle')
    residual=float(np.max(np.abs(Operator(circuit).data-expected)))
    if residual>1e-12:raise AssertionError(residual)
    return truth,residual

truth,operator_residual=classical_oracle(f)
n=f.num_qubits-1;size=1<<n
if sum(truth) not in (0,size//2,size):raise AssertionError('promise violated')
walsh=np.array([sum((-1)**(truth[x]+((x&y).bit_count()%2)) for x in range(size))/size for y in range(size)])
expected_state=np.concatenate([walsh,-walsh])/np.sqrt(2)
circuit=compile_circuit(f)
state=Statevector.from_instruction(circuit.remove_final_measurements(inplace=False))
residual=float(np.max(np.abs(state.data-expected_state)))
if residual>1e-12:raise AssertionError(residual)
probabilities=walsh**2
counts=AerSimulator().run(circuit,shots=4096,seed_simulator=1731).result().get_counts()
if sum(counts.values())!=4096:raise AssertionError(counts)
if any(abs(counts.get(f'{i:0{n}b}',0)/4096-probabilities[i])>.05 for i in range(size)):raise AssertionError(counts)
expected_label='constant' if sum(truth) in (0,size) else 'balanced'
if dj_algorithm(f)!=expected_label:raise AssertionError('classification')
secrets=['0000','0001','1000','1011','1111'];bv=[]
for secret in secrets:
    oracle=bv_query(secret);actual_truth,op_res=classical_oracle(oracle)
    expected_truth=[(x&int(secret,2)).bit_count()%2 for x in range(1<<len(secret))]
    if actual_truth!=expected_truth:raise AssertionError((secret,actual_truth))
    compiled=compile_circuit(oracle);v=Statevector.from_instruction(compiled.remove_final_measurements(inplace=False))
    expected=np.zeros(1<<(len(secret)+1));expected[int(secret,2)]=1/np.sqrt(2);expected[int(secret,2)+(1<<len(secret))]=-1/np.sqrt(2)
    error=float(np.max(np.abs(v.data-expected)))
    if error>1e-12:raise AssertionError(error)
    observed=AerSimulator().run(compiled,shots=256,seed_simulator=1731).result().get_counts()
    if observed!={secret:256} or bv_algorithm(oracle)!=secret:raise AssertionError(observed)
    bv.append(dict(secret=secret,operator_residual=op_res,state_residual=error,counts=observed))
print(json.dumps(dict(original_generated_truth=truth,operator_residual=operator_residual,state_residual=residual,expected_probabilities=probabilities.tolist(),counts=counts,label=expected_label,bv=bv)))
