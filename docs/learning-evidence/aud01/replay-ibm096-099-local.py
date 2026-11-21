"""Run the pinned IBM ML introduction, encoding and kernel notebooks locally."""
import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from qiskit.quantum_info import Statevector

parser=argparse.ArgumentParser()
parser.add_argument("notebook",type=Path)
parser.add_argument("report",type=Path)
parser.add_argument("--dataset",type=Path)
args=parser.parse_args()
raw=args.notebook.read_bytes()
sha=hashlib.sha256(raw).hexdigest()
cells=json.loads(raw)["cells"]
env={}
report={}
executed=[]

def run(i,changes=()):
    code="".join(cells[i]["source"])
    for old,new in changes:
        assert code.count(old)==1,old
        code=code.replace(old,new)
    exec(compile(code,f"{args.notebook.name} cell {i}","exec"),env)
    executed.append(i)

if sha=="aad7521b575bfd6090d4d738b336f1b786d9fce68db4cd7e675b306c200cf381":
    dataset=args.dataset.resolve()
    assert hashlib.sha256(dataset.read_bytes()).hexdigest()=="357b4356a558c5b8387e9765a955327fc2786b4d231483f57b7504ca0e3788ba"
    download=next(line for line in cells[5]["source"] if line.startswith("!wget"))
    run(5,[(download,""),('"dataset_graph7.csv"',repr(str(dataset))),("sampler = StatevectorSampler()","sampler = StatevectorSampler(seed=24)")])
    counts=env["counts"]
    observed=counts.get(0,0)/env["num_shots"]
    a,b=(Statevector.from_instruction(env[name]) for name in ("unitary1","unitary2"))
    exact=float(abs(a.inner(b))**2)
    assert sum(counts.values())==10000 and abs(observed-exact)<0.025
    report.update(dataset_source="https://raw.githubusercontent.com/qiskit-community/prototype-quantum-kernel-training/cd25fde180712d78a4ac8a5b8071443cec7ea68c/data/dataset_graph7.csv",
        dataset_sha256=hashlib.sha256(dataset.read_bytes()).hexdigest(),qubits=env["num_qubits"],
        features=env["num_features"],selected_rows=[14,19],shots=10000,seed=24,observed_overlap=observed,exact_overlap=exact)
elif sha=="09806407d3d3d6c7cc24de5f6ea0fd6a0a101f04b37fb8fcfc7eeaafeb2bc2a9":
    for i,c in enumerate(cells):
        if c["cell_type"]!="code":
            continue
        run(i)
        if i==3:
            basis=Statevector.from_instruction(env["qc"]).probabilities_dict()
            expected="".join(map(str,env["all_bits"][::-1]))
            assert basis=={expected:1.0}
            report["basis_encoding"]=expected
        elif i==6:
            amplitudes=Statevector.from_instruction(env["qc"]).data
            assert np.allclose(amplitudes,np.array([4,8,5,0])/np.sqrt(105))
            report["amplitude_probabilities"]=(abs(amplitudes)**2).tolist()
        elif i==33:
            assert env["encode"].num_parameters==0 and env["encode"].num_qubits==3
        elif i==56:
            assert env["i_plot"]==18
            report["pauli_maps_drawn"]=18
        elif i==59:
            assert env["n_data"]==list(range(3,10))
            report["cx_counts"]={name:[int(v-offset) for v in env[key]] for name,key,offset in
                [("zz","zz2gates",-0.5),("su2","su22gates",0),("z","z2gates",0),("pauli","p2gates",0.5)]}
        plt.close("all")
elif sha=="76b7eaf248593faf84d322d622c59c40b1cbc9abf897894de0795d422973858b":
    from qiskit.primitives import StatevectorSampler
    from sklearn.svm import SVC
    dataset=args.dataset.resolve()
    assert hashlib.sha256(dataset.read_bytes()).hexdigest()=="357b4356a558c5b8387e9765a955327fc2786b4d231483f57b7504ca0e3788ba"
    for i in (3,5,7):
        run(i)
    counts=StatevectorSampler(seed=24).run([env["overlap_circ"]],shots=10000).result()[0].data.meas.get_int_counts()
    env.update(counts=counts,num_shots=10000)
    run(17)
    small_pair=counts.get(0,0)/10000
    download=next(line for line in cells[26]["source"] if line.startswith("!wget"))
    run(26,[(download,""),('"dataset_graph7.csv"',repr(str(dataset)))])
    run(28)
    run(30)
    run(32,[("sampler = StatevectorSampler()","sampler = StatevectorSampler(seed=np.random.default_rng(24))")])
    run(34)
    run(36)
    features=np.concatenate([env["X_train"],env["X_test"]])
    states=np.array([Statevector.from_instruction(env["fm"].assign_parameters([*row,np.pi/2])).data for row in features])
    gram=abs(states.conj()@states.T)**2
    train,test=env["kernel_matrix"],env["test_matrix"]
    assert train.shape==(90,90) and test.shape==(30,90) and np.allclose(train,train.T)
    error=max(abs(train-gram[:90,:90]).max(),abs(test-gram[90:,:90]).max())
    assert error<0.035 and np.allclose(np.diag(train),1)
    exact=SVC(kernel="precomputed").fit(gram[:90,:90],env["train_labels"])
    score=exact.score(gram[90:,:90],env["test_labels"])
    report.update(seed=24,shots_per_pair=10000,training_pairs=4005,test_pairs=2700,
        small_pair_overlap=small_pair,max_absolute_kernel_error=float(error),
        sampled_test_accuracy=float(env["qml_score_precomputed_kernel"]),exact_test_accuracy=float(score),
        dataset_sha256=hashlib.sha256(dataset.read_bytes()).hexdigest())
else:
    raise ValueError("Expected a pinned IBM machine-learning notebook")
report.update(notebook_sha256=sha,executed_code_cells=executed,qiskit=version("qiskit"))
args.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
