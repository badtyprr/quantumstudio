"""Check every amplitude of the source's 5x5 CPU circuit using an independent grid calculation."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np

p=argparse.ArgumentParser()
p.add_argument("notebook",type=Path);p.add_argument("output",type=Path)
args=p.parse_args()
raw=args.notebook.read_bytes()
assert hashlib.sha256(raw).hexdigest()=="221d531613cbf4f74db1f9df4faf2c28d462c13480f28b5b559ec2ffc0f1697d"
cells=json.loads(raw)["cells"]
env={}
def cell(i):
    exec(compile("".join(cells[i]["source"]),f"QB007-cell-{i}","exec"),env)
cell(2)
env["random"].seed(1739)
for i in [4,7,9,11,14,17,23]:cell(i)
cirq=env["cirq"]
order=env["qubits"]
circuit=cirq.drop_terminal_measurements(env["circuit"])
assert len(order)==25
actual=cirq.Simulator(dtype=np.complex64,seed=1739).simulate(circuit,qubit_order=order).final_state_vector
h,jr,jc=(np.array(env[key]) for key in ("h","jr","jc"))
edges=[(5*r+c,5*r+c+1,jc[r,c]) for r in range(5) for c in range(4)]
edges += [(5*r+c,5*(r+1)+c,jr[r,c]) for r in range(4) for c in range(5)]
n=2**25
reference=np.empty(n,dtype=np.complex64)
energy=np.empty(n,dtype=np.int8)
# Each wire is a row-major grid coordinate, with the first wire most significant.
chunk=2**18
phase=np.exp(1j*np.pi*.3)
powers=np.power(phase,np.arange(66))/np.sqrt(n)
for start in range(0,n,chunk):
    bits=np.arange(start,start+chunk,dtype=np.uint32)
    spin=[((bits>>(24-i))&1).astype(np.int8) for i in range(25)]
    exponents=np.zeros(chunk,dtype=np.int8)
    grid_energy=np.zeros(chunk,dtype=np.int8)
    for i,sign in enumerate(h.flat):
        if sign==1:exponents+=spin[i]
        grid_energy+=int(sign)*(1-2*spin[i])
    for i,j,sign in edges:
        level=int(sign==1)
        exponents+=(spin[i]==level)&(spin[j]==level)
        grid_energy+=int(sign)*(1-2*(spin[i]^spin[j]))
    reference[start:start+chunk]=powers[exponents]
    energy[start:start+chunk]=grid_energy
# Final fractional-X layer, including the Cirq XPow phase convention.
diag=(1+phase)/2;off=(1-phase)/2
for bit in range(25):
    width=1<<bit
    pairs=reference.reshape(-1,2,width)
    for row in range(0,len(pairs),max(1,chunk//width)):
        group=pairs[row:row+max(1,chunk//width)]
        a=group[:,0,:].copy();b=group[:,1,:]
        group[:,0,:]=diag*a+off*b
        group[:,1,:]=off*a+diag*b
overlap=0j;norm_a=norm_b=energy1=energy2=0.
for start in range(0,n,chunk):
    sl=slice(start,start+chunk)
    a=actual[sl].astype(np.complex128);b=reference[sl].astype(np.complex128)
    probs=np.abs(b)**2
    overlap+=np.vdot(a,b);norm_a+=np.vdot(a,a).real;norm_b+=probs.sum()
    energy1+=probs@energy[sl];energy2+=probs@np.square(energy[sl],dtype=np.float64)
alignment=overlap/abs(overlap)
error=max(float(np.max(np.abs(reference[i:i+chunk]-alignment*actual[i:i+chunk]))) for i in range(0,n,chunk))
fidelity=float(abs(overlap)**2/(norm_a*norm_b))
assert abs(norm_a-1)<1e-4 and abs(norm_b-1)<1e-4 and 1-fidelity<1e-8 and error<1e-7,(norm_a,norm_b,fidelity,error)
mean=energy1/norm_b;variance=energy2/norm_b-mean**2
outcomes=cirq.Simulator(seed=7817).run(env["circuit"],repetitions=10000).measurements["x"]
calc=env["energy_func"](5,h,jr,jc)
sample=np.array([calc(bits) for bits in outcomes])
indices=outcomes.astype(np.uint32)@(2**np.arange(24,-1,-1,dtype=np.uint32))
np.testing.assert_array_equal(sample,energy[indices])
stderr=float(np.sqrt(variance/len(sample)))
assert abs(sample.mean()-mean)<6*stderr
args.output.write_text(json.dumps(dict(seed=1739,sampling_seed=7817,states=n,exact_reference_norm=norm_b,simulator_norm=norm_a,
    fidelity=fidelity,max_aligned_amplitude_error=error,mean_energy=mean,variance=variance,sampled_energy=float(sample.mean()),shots=len(sample),standard_error=stderr,
    h=h.tolist(),jr=jr.tolist(),jc=jc.tolist()),indent=2)+"\n")
