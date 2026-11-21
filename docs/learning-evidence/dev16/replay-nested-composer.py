"""Compare nested source, stand-alone composer export and a parity / phase-kickback oracle."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
import numpy as np
from qiskit.quantum_info import Statevector
from qiskit import QuantumCircuit
p=argparse.ArgumentParser();p.add_argument("package",type=Path);p.add_argument("fixtures",type=Path);p.add_argument("output",type=Path)
args=p.parse_args();pkg=args.package.resolve();root=args.output.resolve();root.mkdir(parents=True,exist_ok=False)
def digest(data):return hashlib.sha256(data).hexdigest()
def simulate(circuit):
    assert circuit["Qubits"]==4
    qc=QuantumCircuit(4)
    for step in circuit["Steps"]:
        gate=step["Gate"].lower(); wires=step["Wires"]
        if gate=="reset":
            assert not qc.count_ops().keys()-{"reset"}
        else:
            assert gate in ("x","h","cx","cnot"),step
            getattr(qc,"cx" if gate=="cnot" else gate)(*wires)
    return Statevector.from_instruction(qc).probabilities()
app=pkg/"QuantumStudio.exe";compiler=pkg/"qasm-import/qasm-import.exe"
report=[]
for name in ("oracle","bernvaz"):
    for bits in range(8):
        folder=root/f"{name} {bits} κ";nested=folder/"nested λ";nested.mkdir(parents=True)
        original=(args.fixtures/(name+".qasm")).read_bytes()
        dep=nested/(name+".qasm");dep.write_bytes(original)
        wrapper=folder/"wrapper.qasm";wrapper.write_text(f'include "nested λ/{name}.qasm";\n',encoding="utf8")
        prep="".join(f"x q[{i}]; " for i in range(3) if bits & (1<<i))
        body=f"qubit[3] q; qubit[1] ancilla; {prep}{name}(q,ancilla);\n"
        entry=folder/"source κ.qasm";entry.write_text('OPENQASM 3.0; include "stdgates.inc"; include "wrapper.qasm"; '+body,encoding="utf-8-sig")
        out=folder/"result"
        res=subprocess.run([app,"--composer-source-qasm-test",entry,out,"modules"],capture_output=True,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
        assert res.returncode==0,(res.returncode,out.read_text() if out.exists() else res.stderr)
        assert out.read_text(encoding="utf-8-sig").startswith("PASS")
        doc=json.loads(out.with_suffix(".qcircuit").read_bytes())
        captured=doc["Source"]["Files"]
        assert len(captured)==3
        for file in captured:
            raw=(folder/file["Name"]).read_bytes()
            assert digest(raw)==file["Sha256"] and raw==(b"\xef\xbb\xbf" if file["Bom"] else b"")+file["Text"].encode()
        assert dep.read_bytes()==original
        exported=out.with_suffix(".qasm").read_bytes()
        rebound=subprocess.run([compiler],input=exported,capture_output=True,check=True,timeout=30)
        rebuilt=json.loads(rebound.stdout)
        # Inline the published subroutine body independently of the include resolver.
        inline=original.decode("utf-8-sig").split('include "stdgates.inc";',1)[1]
        direct=subprocess.run([compiler],input=('OPENQASM 3.0; include "stdgates.inc"; '+inline+body).encode(),capture_output=True,check=True,timeout=30)
        expected=np.zeros(16)
        if name=="oracle":expected[bits+(bits.bit_count()%2)*8]=1
        else:expected[[bits^6,(bits^6)+8]]=.5
        for circuit in (doc["Circuit"],rebuilt,json.loads(direct.stdout)):
            np.testing.assert_allclose(simulate(circuit),expected,atol=1e-12)
        report.append(dict(module=name,input=bits,expected=expected.tolist(),export_sha256=digest(exported),module_sha256=digest(original)))
        (root/"numerical.json").write_text(json.dumps(report,indent=2))
