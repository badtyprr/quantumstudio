"""Exercise the real GUI/frozen compiler route and compare standalone exports."""
import argparse,hashlib,json,os,subprocess,uuid
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument("--package",type=Path);p.add_argument("--output",type=Path)
p.add_argument("--prepare-only",action="store_true",help="Write source fixtures and independent expectations without launching the GUI.")
a=p.parse_args();repo=Path(__file__).resolve().parent.parent
package=(a.package or repo/"dist/QuantumStudio").resolve()
out=(a.output or repo/"dist/composer-source-validation"/uuid.uuid4().hex).resolve()
assert not out.exists(),"Use a fresh audit output directory."
out.mkdir(parents=True)
compiler=package/"qasm-import/qasm-import.exe";app=package/"QuantumStudio.exe";worker=package/"quantum-worker.exe"
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
hashes={} if a.prepare_only else {"gui":digest(app),"compiler":digest(compiler),"worker":digest(worker)}
startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
results=[]
contract=json.loads((repo/"windows/fixtures/dev16-composer-contract.json").read_text(encoding="utf-8"))
for filename,expected_hash in contract["fixtures"].items():
    assert digest(repo/"windows/fixtures/qb004"/filename)==expected_hash,(filename,"original fixture hash mismatch")
contract_cases={case["name"]:case for case in contract["cases"]}

def expected_state(name,value,edited):
    # Native ket digits are q0,q1,..., not the displayed count-string order.
    if name=="strict":return "(|10>+|01>)/sqrt(2)" if edited else "(|00>+|11>)/sqrt(2)"
    if name=="oracle":
        data=f"{value ^ int(edited):03b}"[::-1]
        return "|"+data+str(value.bit_count()%2)+">"
    data="111" if edited else "011"
    return f"(|{data}0>-|{data}1>)/sqrt(2)"

def circuit_expression(circuit):
    value="|"+"0"*circuit["Qubits"]+">"
    for step in circuit["Steps"]:
        gate=step["Gate"];wires="["+",".join(map(str,step["Wires"]))+"]"
        assert gate in ("H","X","CNOT","Reset"),(gate,step)
        assert not step.get("Angle"),step
        value=(f"reset({value},{wires})" if gate=="Reset" else f"apply({gate},{value},{wires})")
    return value

def verify_state(expression,expected,mixed=False):
    target=f"density({expected})" if mixed else expected
    query=f"quantum:norm(vec(({expression})-({target})))"
    run=subprocess.run([str(worker),"--json","--approx"],input=query.encode("utf-8"),capture_output=True,timeout=30,
                       env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data")))
    assert run.returncode==0,(query,run.stderr)
    residual=complex(json.loads(run.stdout)["text"].replace("−","-").replace(" ","").replace("i","j"))
    assert abs(residual)<1e-12,(query,residual)
    return abs(residual)
def normalized(circuit):
    return {"Version":circuit["Version"],"Qubits":circuit["Qubits"],
            "Steps":[dict(Gate=s["Gate"],Wires=s["Wires"],Angle=s.get("Angle") or "") for s in circuit["Steps"]]}
for name,value,count in (("strict",0,2),("oracle",0,3),("oracle",1,4),("oracle",2,4),("oracle",4,4),("bernvaz",0,10)):
    label=f"{name}-{value}"
    assert contract_cases[label]["original"]==expected_state(name,value,False)
    assert contract_cases[label]["edited"]==expected_state(name,value,True)
    folder=out/(label+" Unicode κ");folder.mkdir()
    entry=folder/"main κ.qasm"
    if name=="strict":
        dependency=folder/"helper.qasm"
        dependency.write_text("gate pair a,b { h a; cx a,b; }\n",encoding="utf-8")
        body='include "helper.qasm"; qubit[2] q; pair q[0],q[1];'
    else:
        modules=folder/"nested modules λ";modules.mkdir()
        dependency=modules/(name+".qasm")
        dependency.write_bytes((repo/"windows/fixtures/qb004"/(name+".qasm")).read_bytes())
        wrapper=folder/"wrapper.inc"
        wrapper.write_text(f'include "nested modules λ/{name}.qasm";\n',encoding="utf-8")
        preparation=" ".join(f"x q[{bit}];" for bit in range(3) if value & (1<<bit))
        body=f'include "wrapper.inc"; qubit[3] q; qubit[1] ancilla; {preparation} {name}(q,ancilla);'
    entry.write_text('OPENQASM 3.0; include "stdgates.inc"; '+body+"\n",encoding="utf-8-sig")
    paths=(entry,dependency) if name=="strict" else (entry,wrapper,dependency)
    expected_sources={path.relative_to(folder).as_posix():path.read_bytes() for path in paths}
    if a.prepare_only:
        results.append(dict(name=label,entry=str(entry),source_hashes={key:hashlib.sha256(raw).hexdigest() for key,raw in expected_sources.items()},
                            expected_original=expected_state(name,value,False),expected_edited=expected_state(name,value,True)))
        continue
    report=folder/"composer.txt"
    command=[str(app),"--composer-source-qasm-test",str(entry),str(report)]
    if name!="strict":command.append("modules")
    run=subprocess.run(command,capture_output=True,timeout=90,startupinfo=startup)
    assert run.returncode==0 and report.exists(),(name,run.returncode,report.read_text() if report.exists() else run.stderr)
    assert report.read_text().startswith("PASS:"),report.read_text()
    document=json.loads(Path(str(report)+".qcircuit").read_text(encoding="utf-8-sig"))
    assert document["Format"]=="QuantumStudio.SourceCircuit" and not document["Classical"] and not document["PublishedU"]
    source=document["Source"];assert source["Entry"]==entry.name and source["ModuleHeaders"]==(name!="strict")
    captured={f["Name"]:f for f in source["Files"]};assert set(captured)==set(expected_sources)
    for filename,raw in expected_sources.items():
        f=captured[filename]
        assert (b"\xef\xbb\xbf" if f["Bom"] else b"")+f["Text"].encode("utf-8")==raw
        assert f["Sha256"]==hashlib.sha256(raw).hexdigest() and (folder/filename).read_bytes()==raw
    assert len(document["Circuit"]["Steps"])==count
    semantic=[]
    for edited in (False,True):
        suffix=".edited" if edited else ""
        saved=json.loads(Path(str(report)+suffix+".qcircuit").read_text(encoding="utf-8-sig"))
        assert saved["Source"]==document["Source"],(label,"edited source snapshot changed")
        assert saved["OriginalCircuitSha256"]==document["OriginalCircuitSha256"]
        expected_circuit=normalized(document["Circuit"])
        if edited:expected_circuit["Steps"].append(dict(Gate="X",Wires=[0],Angle=""))
        assert normalized(saved["Circuit"])==expected_circuit
        exported=Path(str(report)+suffix+".qasm").read_bytes()
        rebuilt=subprocess.run([str(compiler)],input=exported,capture_output=True,timeout=30)
        assert rebuilt.returncode==0,(label,edited,rebuilt.stderr)
        restored=json.loads(rebuilt.stdout)
        expected_circuit["Steps"]=[dict(Gate="Reset",Wires=[i],Angle="") for i in range(expected_circuit["Qubits"])]+expected_circuit["Steps"]
        assert normalized(restored)==expected_circuit
        expected=expected_state(name,value,edited)
        actual=Path(str(report)+suffix+".expression.txt").read_text(encoding="utf-8")
        semantic.append(dict(edited=edited,expected=expected,
                             editor_residual=verify_state(actual,expected),
                             saved_residual=verify_state(circuit_expression(saved["Circuit"]),expected),
                             reimport_residual=verify_state(circuit_expression(restored),expected,True)))
    screenshots=[str(report)+suffix for suffix in (".png",".edited.png",".minimum.png")]
    assert all(Path(path).exists() for path in screenshots)
    results.append(dict(name=label,passed=True,operations=count,source_files=len(expected_sources),screenshots=screenshots,semantic=semantic))
if a.prepare_only:
    assert {row["name"] for row in results}==set(contract_cases)
    (out/"prepared.json").write_text(json.dumps(dict(executed=False,results=results),indent=2)+"\n",encoding="utf-8")
    print("Prepared six cases; no GUI, compiler or worker execution.")
    raise SystemExit(0)
assert {"gui":digest(app),"compiler":digest(compiler),"worker":digest(worker)}==hashes
assert {row["name"] for row in results}==set(contract_cases)
(out/"audit.json").write_text(json.dumps(dict(passed=True,package=str(package),hashes=hashes,results=results,
    scope="Numerical composer source import and standalone circuit equivalence; no complete notebook or changed-dependency claim."),indent=2)+"\n")
print("PASS: six frozen composer source imports, twelve original/edited round trips and 36 independent state checks.")
