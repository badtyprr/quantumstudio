"""Exercise the real GUI/frozen compiler route and compare standalone exports."""
import argparse,hashlib,json,subprocess,uuid
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument("--package",type=Path);p.add_argument("--output",type=Path)
a=p.parse_args();repo=Path(__file__).resolve().parent.parent
package=(a.package or repo/"dist/QuantumStudio").resolve()
out=(a.output or repo/"dist/composer-source-validation"/uuid.uuid4().hex).resolve()
assert not out.exists(),"Use a fresh audit output directory."
out.mkdir(parents=True)
compiler=package/"qasm-import/qasm-import.exe";app=package/"QuantumStudio.exe"
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
hashes={"gui":digest(app),"compiler":digest(compiler)}
startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
results=[]
def normalized(circuit):
    return {"Version":circuit["Version"],"Qubits":circuit["Qubits"],
            "Steps":[dict(Gate=s["Gate"],Wires=s["Wires"],Angle=s.get("Angle") or "") for s in circuit["Steps"]]}
for name,count in (("strict",2),("oracle",3),("bernvaz",10)):
    folder=out/(name+" Unicode κ");folder.mkdir()
    entry=folder/"main κ.qasm"
    if name=="strict":
        dependency=folder/"helper.qasm"
        dependency.write_text("gate pair a,b { h a; cx a,b; }\n",encoding="utf-8")
        body='include "helper.qasm"; qubit[2] q; pair q[0],q[1];'
    else:
        dependency=folder/(name+".qasm")
        dependency.write_bytes((repo/"windows/fixtures/qb004"/(name+".qasm")).read_bytes())
        body=f'include "{name}.qasm"; qubit[3] q; qubit[1] ancilla; {name}(q,ancilla);'
    entry.write_text('OPENQASM 3.0; include "stdgates.inc"; '+body+"\n",encoding="utf-8-sig")
    expected_sources={path.name:path.read_bytes() for path in (entry,dependency)}
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
    exported=Path(str(report)+".qasm").read_bytes()
    rebuilt=subprocess.run([str(compiler)],input=exported,capture_output=True,timeout=30)
    assert rebuilt.returncode==0,(name,rebuilt.stderr)
    # Standalone export explicitly prepares |0...0>; the composer starts in
    # that state implicitly. Require exactly that reset prefix, then identical
    # operations and wire order, rather than discarding arbitrary reset gates.
    expected=normalized(document["Circuit"])
    expected["Steps"]=[dict(Gate="Reset",Wires=[i],Angle="") for i in range(expected["Qubits"])]+expected["Steps"]
    assert normalized(json.loads(rebuilt.stdout))==expected
    assert len(document["Circuit"]["Steps"])==count
    screenshots=[str(report)+suffix for suffix in (".png",".edited.png",".minimum.png")]
    assert all(Path(path).exists() for path in screenshots)
    results.append(dict(name=name,passed=True,operations=count,source_files=2,screenshots=screenshots))
assert digest(app)==hashes["gui"] and digest(compiler)==hashes["compiler"]
(out/"audit.json").write_text(json.dumps(dict(passed=True,package=str(package),hashes=hashes,results=results,
    scope="Numerical composer source import and standalone circuit equivalence; no complete notebook or changed-dependency claim."),indent=2)+"\n")
print("PASS: three frozen composer source imports, original bytes, undo/save/reopen and standalone export equivalence.")
