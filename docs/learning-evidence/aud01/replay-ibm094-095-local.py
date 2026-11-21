"""Replay the pinned IBM SQD examples with local sampling backends."""
import argparse
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument("notebook",type=Path)
parser.add_argument("report",type=Path)
args=parser.parse_args()
raw=args.notebook.read_bytes()
digest=sha256(raw).hexdigest()
cells=json.loads(raw)["cells"]
env={}

def cell(index, changes=()):
    source="".join(cells[index]["source"])
    for before,after in changes:
        assert source.count(before)==1,before
        source=source.replace(before,after)
    exec(compile(source,f"{args.notebook.name} cell {index}","exec"),env)

if digest=="37477fb6301ec3616c6f1760d58ef621767ddedb8c162f66d7c5b517f3c2e272":
    import ffsim
    import numpy as np
    # Keep N2, geometry and basis. Use six active spatial orbitals so a
    # separate exact CASCI calculation can certify every selected-CI result.
    cell(5,[("n_frozen = 2","n_frozen = 4"),("range(n_frozen, mol.nao_nr())","range(n_frozen, 10)")])
    for index in (25,28):
        cell(index)
    sampler=ffsim.qiskit.FfsimSampler(seed=24,global_depolarizing=0.03)
    counts=sampler.run([env["circuit"]],shots=10000).result()[0].data.meas.get_counts()
    env["counts"]=counts
    cell(49)
    cell(51,[("samples_per_batch = 500","samples_per_batch = 28")])
    energies=env["e_hist"]
    exact=float(env["exact_energy"])
    assert energies.shape==(5,5) and np.isfinite(energies).all()
    assert energies.min()>=exact-1e-7
    assert energies.min()<env["scf"].e_tot and sum(counts.values())==10000
    n=env["num_orbitals"]
    sector=sum(freq for bits,freq in counts.items() if bits[:n].count("1")==env["num_elec_b"] and bits[n:].count("1")==env["num_elec_a"])
    assert 0<sector<10000
    report=dict(backend="FfsimSampler, seed 24, 3% global depolarizing noise",
        molecule="N2, 1 angstrom, 6-31g",active_spatial_orbitals=list(env["active_space"]),
        samples_per_batch=28,frozen_occupied_orbitals=4,electrons=env["nelec"],shots=10000,correct_particle_sector=sector,
        reference_hartree_fock=float(env["scf"].e_tot),exact_casci=exact,selected_ci=energies.tolist())
    packages=["ffsim","qiskit","pyscf","qiskit-addon-sqd"]
elif digest=="3ed488d16f7bab398f07d32f95853e1767c1de384095e3712598af6309d09f94":
    import numpy as np
    from qiskit import transpile
    from qiskit_aer import AerSimulator
    for index in (4,6,8,10):
        cell(index)
    simulator=AerSimulator(method="statevector",max_parallel_threads=4)
    circuits=transpile(env["circuits"],simulator,optimization_level=1,seed_transpiler=24)
    counts=simulator.run(circuits,shots=100000,seed_simulator=24).result().get_counts()
    env["counts_all"]=counts
    for index in (24,26,28):
        cell(index)
    # The noiseless starting circuit samples one determinant. The source
    # requests two eigenvalues even for that one-dimensional subspace.
    from qiskit_addon_sqd.qubit import project_operator_to_subspace, solve_qubit

    def solve_projected(bitstrings, operator, **options):
        if len(bitstrings)<=options["k"]:
            projected=project_operator_to_subspace(bitstrings,operator)
            return np.linalg.eigh(projected.toarray())
        return solve_qubit(bitstrings,operator,**options)

    env["solve_qubit"]=solve_projected
    cell(30)
    energies=env["ground_state_energies"]
    sector=[sum(freq for b,freq in sample.items() if b.count("1")==11) for sample in counts]
    assert len(counts)==5 and all(sum(sample.values())==100000 for sample in counts)
    assert all(value>0 for value in sector) and all(np.isfinite(energies))
    assert all(b<=a+1e-8 for a,b in zip(energies,energies[1:])) and energies[-1]<energies[0]
    report=dict(backend="Aer statevector, seed 24",qubits=22,krylov_dimension=5,
        shots_per_circuit=100000,postselected_shots=sector,unique_sample_counts=list(map(len,counts)),
        projected_energies=energies,source_reference_energy=-23.934184)
    packages=["qiskit","qiskit-aer","qiskit-addon-utils","qiskit-addon-sqd"]
else:
    raise ValueError("Expected the pinned SQD implementation or SKQD notebook")
report.update(notebook_sha256=digest,packages={name:version(name) for name in packages})
args.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
