"""Authored QIR inspection; original notebook objects and files stay unchanged."""
import hashlib
import json
from collections import Counter
from pathlib import Path
import pyqir
import qirrunner

Path("original.qasm").write_text(qasm3_str, encoding="utf-8")
Path("original-inspected.ll").write_text(ir, encoding="utf-8")
Path("original-inspected.bc").write_bytes(module.bitcode)


def inspect_qir(value):
    entries = [f for f in value.functions if pyqir.is_entry_point(f)]
    if len(entries) != 1:
        raise AssertionError("Expected one QIR entry point")
    entry = entries[0]
    calls = []
    measured = set()
    measurement_map = []
    qis_operations = []
    output_results = []
    problems = []
    required_results = pyqir.required_num_results(entry)
    required_qubits = pyqir.required_num_qubits(entry)
    if len(entry.basic_blocks) != 1 or required_qubits != 2:
        problems.append(dict(kind="unsupported_shape"))
    for block in entry.basic_blocks:
        for instruction in block.instructions:
            if isinstance(instruction, pyqir.Call):
                name = instruction.callee.name
                args = instruction.args
                calls.append(dict(name=name, args=[str(arg) for arg in args]))
                if name.startswith("__quantum__qis__"):
                    ids = [pyqir.ptr_id(arg) for arg in args]
                    qis_operations.append(dict(name=name, ids=ids))
                    if name not in {"__quantum__qis__h__body", "__quantum__qis__x__body",
                                    "__quantum__qis__cnot__body", "__quantum__qis__mz__body"}:
                        problems.append(dict(kind="unsupported_instruction", name=name))
                    qubits = ids[:1] if name == "__quantum__qis__mz__body" else ids
                    if any(q is None or required_qubits is None or not 0 <= q < required_qubits for q in qubits):
                        problems.append(dict(kind="invalid_qubit_reference", name=name))
                elif name not in {"__quantum__rt__initialize", "__quantum__rt__result_record_output"}:
                    problems.append(dict(kind="unsupported_runtime_call", name=name))
                if name == "__quantum__qis__mz__body":
                    measured.add(pyqir.ptr_id(args[1]))
                    measurement_map.append([pyqir.ptr_id(args[0]), pyqir.ptr_id(args[1])])
                if name == "__quantum__rt__result_record_output":
                    result_id = pyqir.ptr_id(args[0])
                    output_results.append(result_id)
                    if result_id not in measured:
                        problems.append(dict(kind="unmeasured_result", result=result_id))
            elif instruction.opcode != pyqir.Opcode.RET:
                problems.append(dict(kind="unsupported_noncall_instruction", instruction=str(instruction)))
    for result_id in output_results:
        if result_id is None or required_results is None or not 0 <= result_id < required_results:
            problems.append(dict(kind="unallocated_result", result=result_id))
    return dict(entry_point=entry.name, required_qubits=required_qubits,
                required_results=required_results, calls=calls, measured_results=sorted(measured, key=str),
                measurement_map=measurement_map, qis_operations=qis_operations,
                output_results=output_results, result_accounting_errors=problems)


def read_counts(raw, shots):
    """Finite runner output protocol: each shot records logical q0 then q1."""
    current = None
    counts = Counter()
    for line in raw.splitlines():
        fields = line.split("\t")
        if fields == ["START"]:
            if current is not None:
                raise AssertionError("Nested shot")
            current = []
        elif fields[0] == "METADATA":
            if current is None:
                raise AssertionError("Metadata outside shot")
        elif fields[:2] == ["OUTPUT", "RESULT"] and len(fields) == 3 and fields[2] in {"0", "1"}:
            if current is None:
                raise AssertionError("Result outside shot")
            current.append(fields[2])
        elif fields == ["END", "0"]:
            if current is None or len(current) != 2:
                raise AssertionError("Expected exactly two results per shot")
            counts["".join(current)] += 1
            current = None
        else:
            raise AssertionError("Unsupported output record: " + line)
    if current is not None or sum(counts.values()) != shots:
        raise AssertionError("Incomplete shot output")
    return dict(counts)


report = dict(original=inspect_qir(module), accepted=False,
              original_runtime={"state": "not_run_pending_semantic_validation"}, authored_controls="not_run")
if report["original"]["qis_operations"] != [
        {"name": "__quantum__qis__h__body", "ids": [0]},
        {"name": "__quantum__qis__cnot__body", "ids": [0, 1]}]:
    raise AssertionError("Original H(0)/CNOT(0,1) semantics changed during conversion")
if not graph.has_edge("cirq", "qir"):
    raise AssertionError("Original graph conversion was not registered")
report["source_graph"] = dict(cirq_to_qir_registered=True,
                             actual_bell_conversion="braket -> qasm3 -> qir")
report["llvm_validation"] = {
    "original": module.verify(),
    "text_roundtrip": pyqir.Module.from_ir(pyqir.Context(), ir).verify(),
    "bitcode_roundtrip": pyqir.Module.from_bitcode(pyqir.Context(), module.bitcode).verify(),
}
stem = Path(module.source_filename).stem
report["original_exports"] = {}
for extension in (".ll", ".bc"):
    path = Path(stem + extension)
    raw = path.read_bytes()
    if extension == ".bc" and raw != module.bitcode:
        raise AssertionError("Original bitcode dump differs from module")
    if extension == ".ll" and raw.decode("utf-8").replace("\r\n", "\n") != ir:
        raise AssertionError("Original textual dump differs from module")
    report["original_exports"][path.name] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
if report["original"]["result_accounting_errors"]:
    report["original_runtime"]["state"] = "not_run_invalid_result_accounting"
Path("qir-evidence.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

# These measured circuits are authored controls, not repaired original cells.
controls = {
    "bell": braket_circuit.copy().measure([0, 1]),
    "q0_one": Circuit().x(0).x(1).x(1).measure([0, 1]),
    "q1_one": Circuit().x(0).x(0).x(1).measure([0, 1]),
}
report["authored_controls"] = {}
for control_name, control in controls.items():
    qasm = transpile(control, "qasm3")
    control_module = qasm3_to_qir(qasm, name="authored-" + control_name)
    control_ir = str(control_module)
    Path("authored-" + control_name + ".qasm").write_text(qasm, encoding="utf-8")
    Path("authored-" + control_name + ".ll").write_text(control_ir, encoding="utf-8")
    Path("authored-" + control_name + ".bc").write_bytes(control_module.bitcode)
    inspection = inspect_qir(control_module)
    if inspection["result_accounting_errors"] or control_module.verify() is not None:
        raise AssertionError((control_name, inspection))
    if inspection["measurement_map"] != [[0, 0], [1, 1]] or inspection["output_results"] != [0, 1]:
        raise AssertionError("Unexpected physical qubit/result/output ordering")
    if control_name == "bell":
        if inspection["qis_operations"][:-2] != report["original"]["qis_operations"]:
            raise AssertionError("Measured Bell changed original premeasurement operations")
    shots = 4096 if control_name == "bell" else 256
    outcomes = {}
    for representation, data in [("text", control_ir.encode("utf-8")), ("bitcode", control_module.bitcode)]:
        outputs = []
        qirrunner.run_bytes(data, shots=shots, rng_seed=1731,
                            output_fn=lambda output: outputs.append(str(output)))
        raw_output = "".join(outputs)
        filename = "authored-" + control_name + "-" + representation + ".output.txt"
        Path(filename).write_text(raw_output, encoding="utf-8")
        counts = read_counts(raw_output, shots)
        if control_name == "bell":
            if set(counts) != {"00", "11"} or abs(counts["00"] / shots - 0.5) > 0.05:
                raise AssertionError((control_name, counts))
        elif counts != {"10" if control_name == "q0_one" else "01": shots}:
            raise AssertionError((control_name, counts))
        outcomes[representation] = dict(counts=counts, raw_output=filename,
            sha256=hashlib.sha256(Path(filename).read_bytes()).hexdigest())
    if outcomes["text"]["counts"] != outcomes["bitcode"]["counts"]:
        raise AssertionError("Text and bitcode execution disagree at fixed seed")
    report["authored_controls"][control_name] = dict(inspection=inspection, outcomes=outcomes,
        state="passed_counts_only", shots=shots, seed=1731, bit_order="logical q0, q1",
        expected_probabilities={"00": 0.5, "11": 0.5} if control_name == "bell" else
            {"10" if control_name == "q0_one" else "01": 1.0},
        probability_tolerance=0.05 if control_name == "bell" else 0,
        amplitudes_observed=False)
    Path("qir-evidence.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

report["authored_negative_controls"] = {}
try:
    pyqir.Module.from_ir(pyqir.Context(), "not LLVM IR")
except Exception as error:
    report["authored_negative_controls"]["invalid_ir"] = dict(type=type(error).__name__, message=str(error))
else:
    raise AssertionError("Malformed IR accepted")
unsupported = pyqir.Module.from_ir(pyqir.Context(), ir.replace("__quantum__qis__h__body", "__quantum__qis__unsupported__body"))
rejected = inspect_qir(unsupported)
if not any(p["kind"] == "unsupported_instruction" for p in rejected["result_accounting_errors"]):
    raise AssertionError("Unsupported instruction not rejected")
report["authored_negative_controls"]["unsupported_qis"] = dict(
    llvm_validation=unsupported.verify(), semantic_errors=rejected["result_accounting_errors"], runtime="not_run")
unallocated = pyqir.Module.from_ir(pyqir.Context(), ir.replace('"required_num_results"="2"', '"required_num_results"="1"'))
allocation_errors = inspect_qir(unallocated)["result_accounting_errors"]
if not any(p["kind"] == "unallocated_result" and p["result"] == 1 for p in allocation_errors):
    raise AssertionError("Out-of-range result was not rejected")
report["authored_negative_controls"]["unallocated_result"] = dict(
    llvm_validation=unallocated.verify(), semantic_errors=allocation_errors, runtime="not_run")
report["accepted"] = (all(value is None for value in report["llvm_validation"].values())
                       and not report["original"]["result_accounting_errors"]
                       and report["original_runtime"]["state"] == "passed")
Path("qir-evidence.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report))
