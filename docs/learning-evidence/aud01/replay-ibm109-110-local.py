"""Execute the published active-space construction and circuit ansatz examples."""
import argparse
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from qiskit.quantum_info import Statevector

p=argparse.ArgumentParser()
p.add_argument("notebook",type=Path);p.add_argument("report",type=Path)
a=p.parse_args()
raw=a.notebook.read_bytes()
digest=sha256(raw).hexdigest()
lesson={"0f3a767995ca2b9d4d161107d64bdaf12500687e611b5f16d22292dd67456c6d":109,
    "3222364ec09800b5b71ca4116ce9a687a17af726ae3bf26f933953bbd7e8485a":110}[digest]
env={"display":lambda figure:figure.canvas.draw()}
report=dict(notebook_sha256=digest,code_cells=[],qiskit=version("qiskit"))
for i,c in enumerate(json.loads(raw)["cells"]):
    if c["cell_type"]!="code":continue
    exec(compile("".join(c["source"]),f"IBM{lesson}:{i}","exec"),env)
    report["code_cells"].append(i)
    if lesson==109 and i in (25,29):
        h=env["H"] if i==25 else env["build_hamiltonian"](env["ecore"],env["h1e"],env["h2e"])
        particles=sum(env["mx"].nelecas)
        indices=[bits for bits in range(1<<h.num_qubits) if bits.bit_count()==particles]
        matrix=h.to_matrix(sparse=True)[indices,:][:,indices].toarray()
        assert np.allclose(matrix,matrix.conj().T)
        exact=float(np.linalg.eigvalsh(matrix)[0]);casci=float(env["mx"].e_tot)
        assert np.isclose(exact,casci,atol=1e-7,rtol=0),(exact,casci)
        report.setdefault("molecules",[]).append(dict(molecule="H2" if i==25 else "LiH",
            qubits=h.num_qubits,pauli_terms=len(h),active_electrons=int(particles),
            basis_states=len(indices),sector_energy=exact,casci_energy=casci))
    elif lesson==109 and i==40:
        from openfermion import QubitOperator,get_sparse_operator
        operator=QubitOperator("X0 Y1",0.25)+QubitOperator("Z1",-0.5)
        op=env["convert_openfermion_to_qiskit"](operator,2)
        from qiskit.quantum_info import SparsePauliOp
        assert np.allclose(op.to_matrix(),get_sparse_operator(operator,n_qubits=2).toarray())
        same_wire_indices=SparsePauliOp.from_sparse_list([("XY",[0,1],0.25),("Z",[1],-0.5)],num_qubits=2)
        assert not np.allclose(op.to_matrix(),same_wire_indices.to_matrix())
        report["conversion_convention"]="Matches the OpenFermion matrix in configured tensor order. Qiskit qubit indices run from the opposite end of the displayed label."
        report["converted_terms"]=op.to_list()
        report["converted_terms"]=[[name,str(value)] for name,value in report["converted_terms"]]
    elif lesson==110:
        from qiskit import QuantumCircuit
        for name,cls in list(env.items()):
            if not isinstance(cls,QuantumCircuit) or name in report.get("circuits",{}):continue
            bound=cls.assign_parameters(np.linspace(0.1,0.9,cls.num_parameters))
            state=Statevector.from_instruction(bound)
            assert state.is_valid()
            report.setdefault("circuits",{})[name]=dict(qubits=cls.num_qubits,parameters=cls.num_parameters,depth=cls.depth())
    plt.close("all")
a.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
