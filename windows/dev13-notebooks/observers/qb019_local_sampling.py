from qiskit.primitives import StatevectorSampler

local_sampler = StatevectorSampler(seed=1731)
local_shots = 100
counts = local_sampler.run([qiskit_circuit], shots=local_shots).result()[0].data.meas.get_counts()
