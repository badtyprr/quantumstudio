"""Explicit finite static-QIR import; never execute LLVM or repair its semantics."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

import pyqir

MAX_BYTES = 1024 * 1024
MAX_INSTRUCTIONS = 4096
# Matches the existing native exact-circuit wire limit; sampled execution can
# support more, but this wire bound fits either engine. Other budgets still apply.
MAX_QUBITS = 10
GATES = {
    "h__body": ("h", 1), "x__body": ("x", 1), "y__body": ("y", 1),
    "z__body": ("z", 1), "s__body": ("s", 1), "s__adj": ("sdg", 1),
    "t__body": ("t", 1), "t__adj": ("tdg", 1),
    "cnot__body": ("cx", 2), "cz__body": ("cz", 2),
}


def terminal_output_targets(statements):
    """Alias only a bijection of terminal measurements and final records.

    Interleaved records, overwritten result slots and duplicate output records
    need independent snapshots. Preserve their general lowering unchanged.
    """
    phase = 'gates'
    measured, recorded = [], []
    for statement in statements:
        if isinstance(statement, str):
            if phase != 'gates':
                return None
        elif statement[0] == 'measure':
            if phase == 'outputs':
                return None
            phase = 'measurements'
            measured.append(statement[2])
        else:
            phase = 'outputs'
            recorded.append(statement[2])
    if (not recorded or len(measured) != len(set(measured))
            or len(recorded) != len(set(recorded)) or set(measured) != set(recorded)):
        return None
    return {result: len(recorded)-1-ordinal for ordinal, result in enumerate(recorded)}


def import_qir(raw, *, bitcode=False):
    """Translate one void, argument-free, static entry point to OpenQASM3.

    Preserve measurement writes and output snapshots in instruction order.
    Unsupported features reject the entire input before any output is written.
    """
    if type(raw) is not bytes or not raw or len(raw) > MAX_BYTES:
        raise ValueError("QIR_INPUT_SIZE")
    context = pyqir.Context()
    try:
        module = (pyqir.Module.from_bitcode(context, raw) if bitcode
                  else pyqir.Module.from_ir(context, raw.decode("utf-8")))
    except Exception as error:
        raise ValueError("QIR_PARSE_FAILED") from error
    if module.verify() is not None:
        raise ValueError("QIR_INVALID_LLVM")
    version = (pyqir.qir_major_version(module), pyqir.qir_minor_version(module))
    if (version not in {(1, 0), (1, 1), (2, 0)}
            or pyqir.dynamic_qubit_management(module) is not False
            or pyqir.dynamic_result_management(module) is not False):
        raise ValueError("QIR_UNSUPPORTED_PROFILE")
    entries = [f for f in module.functions if pyqir.is_entry_point(f)]
    if len(entries) != 1:
        raise ValueError("QIR_ENTRY_POINT_COUNT")
    entry = entries[0]
    if entry.params or not entry.type.ret.is_void or len(entry.basic_blocks) != 1:
        raise ValueError("QIR_ENTRY_POINT_SHAPE")
    qubits = pyqir.required_num_qubits(entry)
    results = pyqir.required_num_results(entry)
    if type(qubits) is not int or not 1 <= qubits <= MAX_QUBITS:
        raise ValueError("QIR_QUBIT_LIMIT")
    if type(results) is not int or not 0 <= results <= 64:
        raise ValueError("QIR_RESULT_LIMIT")
    instructions = entry.basic_blocks[0].instructions
    if len(instructions) > MAX_INSTRUCTIONS:
        raise ValueError("QIR_INSTRUCTION_LIMIT")
    if not instructions or instructions[-1].opcode != pyqir.Opcode.RET:
        raise ValueError("QIR_TERMINATOR")
    statements = []
    measured = set()
    outputs = 0
    initialized = False

    def static_id(value, bound, label):
        if not isinstance(value.type, pyqir.PointerType):
            raise ValueError("QIR_POINTER_TYPE:" + label)
        number = pyqir.ptr_id(value)
        if type(number) is not int or not 0 <= number < bound:
            raise ValueError("QIR_STATIC_ID:" + label)
        return number

    for ordinal, instruction in enumerate(instructions[:-1]):
        if not isinstance(instruction, pyqir.Call):
            raise ValueError("QIR_UNSUPPORTED_INSTRUCTION:" + str(ordinal))
        callee = instruction.callee
        if (not isinstance(callee, pyqir.Function) or callee.basic_blocks
                or not callee.type.ret.is_void
                # PyQIR 0.12 exposes varargs only in the printed LLVM declaration.
                or re.search(r"^declare [^\n]*?@__quantum__\w+\([^\n\"]*?\.\.\.\)", str(callee), re.MULTILINE)):
            raise ValueError("QIR_UNSUPPORTED_CALLEE:" + str(ordinal))
        name = callee.name
        args = instruction.args
        if len(args) != len(callee.params):
            raise ValueError("QIR_CALL_SIGNATURE:" + name)
        if name in ("__quantum__qis__rx__body", "__quantum__qis__ry__body", "__quantum__qis__rz__body"):
            if (len(args) != 2 or not callee.params[0].type.is_double
                    or not isinstance(callee.params[1].type, pyqir.PointerType)
                    or not isinstance(args[0], pyqir.FloatConstant) or not args[0].type.is_double):
                raise ValueError("QIR_ROTATION_SIGNATURE:" + name)
            angle = args[0].value
            if not math.isfinite(angle):
                raise ValueError("QIR_NONFINITE_ROTATION")
            target = static_id(args[1], qubits, "qubit")
            gate = name.split("__")[-2]
            statements.append(f"{gate}({angle!r}) q[{target}];")
            continue
        if any(not isinstance(a.type, pyqir.PointerType) for a in args):
            raise ValueError("QIR_CALL_SIGNATURE:" + name)
        if name == "__quantum__rt__initialize":
            if initialized or ordinal != 0 or len(args) != 1 or pyqir.ptr_id(args[0]) != 0:
                raise ValueError("QIR_INITIALIZE")
            initialized = True
        elif name == "__quantum__rt__result_record_output":
            if len(args) != 2 or pyqir.ptr_id(args[1]) != 0:
                raise ValueError("QIR_OUTPUT_SIGNATURE")
            result = static_id(args[0], results, "result")
            if result not in measured:
                raise ValueError("QIR_UNMEASURED_OUTPUT:" + str(result))
            if outputs >= 64:
                raise ValueError("QIR_OUTPUT_LIMIT")
            statements.append(("output", outputs, result))
            outputs += 1
        elif name == "__quantum__qis__mz__body":
            if len(args) != 2:
                raise ValueError("QIR_MEASUREMENT_SIGNATURE")
            qubit = static_id(args[0], qubits, "qubit")
            result = static_id(args[1], results, "result")
            statements.append(("measure", qubit, result))
            measured.add(result)
        elif name.startswith("__quantum__qis__") and name[len("__quantum__qis__"):] in GATES:
            gate, arity = GATES[name[len("__quantum__qis__"):]]
            if len(args) != arity:
                raise ValueError("QIR_GATE_ARITY:" + name)
            targets = [static_id(a, qubits, "qubit") for a in args]
            if len(set(targets)) != arity:
                raise ValueError("QIR_GATE_TARGET_ALIAS")
            statements.append(gate + " " + ", ".join(f"q[{q}]" for q in targets) + ";")
        else:
            raise ValueError("QIR_UNSUPPORTED_CALL:" + name)
    targets = terminal_output_targets(statements)
    if targets is None and outputs and results + outputs > 64:
        raise ValueError("QIR_CLASSICAL_STORAGE_LIMIT")
    lines = ['OPENQASM 3.0;', 'include "stdgates.inc";', f'qubit[{qubits}] q;']
    if outputs:
        if targets is None:
            lines.append(f"bit[{results}] result;")
        lines.append(f"output bit[{outputs}] out;")
    for statement in statements:
        if isinstance(statement, str):
            lines.append(statement)
        elif statement[0] == "measure":
            _, qubit, result = statement
            prefix = (f"out[{targets[result]}] = " if targets is not None
                      else f"result[{result}] = " if outputs else "")
            lines.append(prefix + f"measure q[{qubit}];")
        else:
            _, ordinal, result = statement
            # OpenQASM bitstrings display highest index first; QIR records
            # appear chronologically. Snapshot each record at its call site.
            if targets is None:
                lines.append(f"out[{outputs - 1 - ordinal}] = result[{result}];")
    qasm = "\n".join(lines) + "\n"
    return dict(route="qir-to-openqasm3", source_sha256=hashlib.sha256(raw).hexdigest(),
                source_format="bitcode" if bitcode else "llvm-ir", entry_point=entry.name,
                qubits=qubits, result_slots=results, output_slots=outputs,
                output_order="QIR record order, leftmost bit first",
                output_lowering="terminal-measurement-aliases" if targets is not None else "record-snapshots",
                openqasm=qasm, execution_performed=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--bitcode", action="store_true")
    parser.add_argument("--output", type=Path, help="New OpenQASM file; existing files are refused")
    args = parser.parse_args()
    with args.source.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    result = import_qir(raw, bitcode=args.bitcode)
    if args.output:
        with args.output.open("xb") as stream:
            stream.write(result["openqasm"].encode("utf-8"))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
