"""Verify GUI smoke exports using openqasm3[parser] (tested with version 1.0.1).

Usage: python windows/test-qasm-export.py path/to/smoke.png
Run QuantumStudio.exe --smoke-test path/to/smoke.png first.
This development dependency is not needed to run Quantum Studio.
"""
import sys
from pathlib import Path
from openqasm3 import ast, parse

base = sys.argv[1]
for suffix, names, wires in [
    (".qasm", ["h", "cx", "s", "rx"], [[0], [0, 1], [1], [0]]),
    (".all.qasm", ["h", "x", "y", "z", "s", "t", "rx", "ry", "rz", "p", "cx", "cz", "swap", "ccx", "cy", "ch", "z", "cswap", "sdg", "tdg", "sx", "sx"],
     [[1]] * 10 + [[2, 0]] * 3 + [[2, 0, 1]] + [[2, 0]] * 2 + [[2, 0, 1]] * 2 + [[1]] * 4),
]:
    program = parse(Path(base + suffix).read_text(encoding="utf-8-sig"))
    assert program.version == "3.0"
    gates = [s for s in program.statements if isinstance(s, ast.QuantumGate)]
    assert [s.name.name for s in gates] == names
    assert [[q.indices[0][0].value for q in s.qubits] for s in gates] == wires
    assert any(isinstance(s, ast.QuantumReset) for s in program.statements)
    if suffix == ".all.qasm":
        resets = [s for s in program.statements if isinstance(s, ast.QuantumReset)]
        assert len(resets) == 2 and resets[-1].qubits.indices[0][0].value == 2
        measurements = [s for s in program.statements if isinstance(s, ast.QuantumMeasurementStatement)]
        assert len(measurements) == 1 and measurements[0].target is None
        assert measurements[0].measure.qubit.indices[0][0].value == 1
        assert len(gates[-1].modifiers) == 1 and gates[-1].modifiers[0].modifier.name == "inv"
        modifiers = gates[16].modifiers
        assert len(modifiers) == 1 and modifiers[0].modifier.name == "ctrl"
        assert modifiers[0].argument.value == 2
        for gate in gates[6:10]:
            angle = gate.arguments[0]
            assert isinstance(angle, ast.BinaryExpression) and angle.op.name == "/"
            assert isinstance(angle.lhs, ast.FloatLiteral) and angle.lhs.value == 1.0
            assert isinstance(angle.rhs, ast.FloatLiteral) and angle.rhs.value == 2.0
for suffix, expected in [
    (".feedback.qasm", [(2, 0, "x", 0), (2, 1, "x", 0), (2, 0, "z", 0), (2, 1, "z", 0)]),
    (".teleport.qasm", [(1, 1, "x", 2), (0, 1, "z", 2)]),
]:
    program = parse(Path(base + suffix).read_text(encoding="utf-8-sig"))
    dynamic = [s for s in program.statements if isinstance(s, (ast.ClassicalDeclaration, ast.QuantumMeasurementStatement, ast.BranchingStatement))]
    assert len(dynamic) == 3 * len(expected)
    for i, (wire, outcome, gate, target) in enumerate(expected):
        declaration, measurement, branch = dynamic[3*i:3*i+3]
        assert isinstance(declaration, ast.ClassicalDeclaration) and isinstance(declaration.type, ast.BitType)
        assert declaration.identifier.name == "m" + str(i)
        assert measurement.target.name == declaration.identifier.name
        assert measurement.measure.qubit.indices[0][0].value == wire
        assert branch.condition.op.name == "==" and branch.condition.lhs.name == measurement.target.name
        assert branch.condition.rhs.value == outcome and not branch.else_block
        assert len(branch.if_block) == 1 and branch.if_block[0].name.name == gate
        assert branch.if_block[0].qubits[0].indices[0][0].value == target
program = parse(Path(base + ".rotations.qasm").read_text(encoding="utf-8-sig"))
gates = [s for s in program.statements if isinstance(s, ast.QuantumGate)]
assert [s.name.name for s in gates] == ["cp", "crx", "cry", "crz"]
for gate in gates:
    assert [q.indices[0][0].value for q in gate.qubits] == [2, 0]
    assert gate.arguments[0].op.name == "/"
    assert gate.arguments[0].lhs.name == "pi" and gate.arguments[0].rhs.value == 2.0
program = parse(Path(base + ".iswap.qasm").read_text(encoding="utf-8-sig"))
gates = [s for s in program.statements if isinstance(s, ast.QuantumGate)]
assert [s.name.name for s in gates] == ["x", "swap", "s", "s", "cz"]
assert [[q.indices[0][0].value for q in g.qubits] for g in gates] == [[2], [2, 0], [2], [0], [2, 0]]
program = parse(Path(base + ".fsim.qasm").read_text(encoding="utf-8-sig"))
gates = [s for s in program.statements if isinstance(s, ast.QuantumGate)]
assert [s.name.name for s in gates] == ["h", "h", "cx", "rz", "cx", "h", "h", "rx", "rx", "cx", "rz", "cx", "rx", "rx", "cp"]
# Evaluate the actual parsed export on every basis vector, including the idle wire.
import subprocess
def angle_text(node):
    if isinstance(node, ast.Identifier):
        assert node.name == "pi"
        return "pi"
    if isinstance(node, (ast.FloatLiteral, ast.IntegerLiteral)):
        return str(node.value)
    if isinstance(node, ast.UnaryExpression):
        return "(" + node.op.name + angle_text(node.expression) + ")"
    if isinstance(node, ast.BinaryExpression):
        return "(" + angle_text(node.lhs) + node.op.name + angle_text(node.rhs) + ")"
    raise AssertionError(type(node))
worker = Path(__file__).resolve().parent.parent / "dist/QuantumStudio/quantum-worker.exe"
# ECR exports a global phase plus standard gates. Compare every complex
# amplitude with the independently specified matrix, including the idle wire.
import cmath
import math
ecr_program = parse(Path(base + ".ecr.qasm").read_text(encoding="utf-8-sig"))
ecr_gates = [s for s in ecr_program.statements if isinstance(s, ast.QuantumGate)]
assert [s.name.name for s in ecr_gates] == ['s','sx','cx','x']
assert [[q.indices[0][0].value for q in s.qubits] for s in ecr_gates] == [[2],[0],[2,0],[2]]
phases = [s for s in ecr_program.statements if isinstance(s, ast.QuantumPhase)]
assert len(phases) == 1 and not phases[0].qubits and not phases[0].modifiers
phase_text = angle_text(phases[0].argument)
phase_angle = eval(phase_text, {'__builtins__': {}}, {'pi': math.pi})
assert abs(phase_angle+math.pi/4)<1e-14
ecr_matrix = [[0,0,1,1j],[0,0,1j,1],[1,-1j,0,0],[-1j,1,0,0]]
single_gates = {'s': [[1,0],[0,1j]], 'sx': [[(1+1j)/2,(1-1j)/2],[(1-1j)/2,(1+1j)/2]], 'x': [[0,1],[1,0]]}
for index in range(8):
    actual = [complex(k==index)*cmath.exp(1j*phase_angle) for k in range(8)]
    for gate in ecr_gates:
        wires = [q.indices[0][0].value for q in gate.qubits]
        updated = [0j]*8
        for column, amplitude in enumerate(actual):
            if gate.name.name == 'cx':
                row = column ^ ((1 << (2-wires[1])) if column & (1 << (2-wires[0])) else 0)
                updated[row] += amplitude
            else:
                mask = 1 << (2-wires[0])
                bit = int(bool(column & mask))
                for rowbit in (0,1):
                    row = (column & ~mask) | rowbit*mask
                    updated[row] += single_gates[gate.name.name][rowbit][bit]*amplitude
        actual = updated
    column = 2*(index & 1)+((index >> 2) & 1)
    expected = [0j]*8
    for row in range(4):
        target = (index & 2) | (row >> 1) | ((row & 1) << 2)
        expected[target] = ecr_matrix[row][column]/math.sqrt(2)
    assert max(abs(x-y) for x,y in zip(actual,expected))<1e-14, (index,actual,expected)
for index in range(8):
    state = "|" + format(index, "03b") + ">"
    value = state
    for gate in gates:
        name = {"h":"H", "cx":"CNOT", "rz":"Rz", "rx":"Rx", "cp":"CP"}[gate.name.name]
        if gate.arguments:
            name += "(" + angle_text(gate.arguments[0]) + ")"
        wires = ",".join(str(q.indices[0][0].value) for q in gate.qubits)
        value = "apply(" + name + "," + value + ",[" + wires + "])"
    expression = "quantum:norm((" + value + ")-apply(fSim(pi/3,pi/4)," + state + ",[2,0]))"
    result = subprocess.run([str(worker)], input=expression, encoding="utf-8", capture_output=True)
    assert result.returncode == 0 and result.stdout.strip() == "0", (index, result.stdout, result.stderr)
program = parse(Path(base + ".u3.qasm").read_text(encoding="utf-8-sig"))
gates = [s for s in program.statements if isinstance(s, ast.QuantumGate)]
assert [s.name.name for s in gates] == ["p", "ry", "p", "p", "ry", "p"]
assert [g.qubits[0].indices[0][0].value for g in gates] == [2, 2, 2, 0, 0, 0]
for index in range(8):
    state = "|" + format(index, "03b") + ">"
    value = state
    for gate in gates:
        name = {"p":"P", "ry":"Ry"}[gate.name.name]
        value = "apply(" + name + "(" + angle_text(gate.arguments[0]) + ")," + value + "," + str(gate.qubits[0].indices[0][0].value) + ")"
    expression = "quantum:norm((" + value + ")-apply(U3(pi/3,pi,pi/2),apply(H," + state + ",2),0))"
    result = subprocess.run([str(worker)], input=expression, encoding="utf-8", capture_output=True)
    assert result.returncode == 0 and result.stdout.strip() == "0", (index, result.stdout, result.stderr)
program = parse(Path(base + ".edited.qasm").read_text(encoding="utf-8-sig"))
gates = [s for s in program.statements if isinstance(s, ast.QuantumGate)]
assert len(gates) == 64 and [g.name.name for g in gates] == ["x"] + ["h"] * 63
assert all(g.qubits[0].indices[0][0].value == 0 for g in gates)
program = parse(Path(base + ".fswap.qasm").read_text(encoding="utf-8-sig"))
gates = [s for s in program.statements if isinstance(s, ast.QuantumGate)]
assert [g.name.name for g in gates] == ["x", "x", "swap", "cz"]
assert [[q.indices[0][0].value for q in g.qubits] for g in gates] == [[0], [1], [0, 1], [0, 1]]
program = parse(Path(base + ".interactions.qasm").read_text(encoding="utf-8-sig"))
gates = [s for s in program.statements if isinstance(s, ast.QuantumGate)]
assert len(gates) == 22
for index in range(8):
    state = "|" + format(index, "03b") + ">"
    value = state
    for gate in gates:
        name = {"h":"H", "cx":"CNOT", "rz":"Rz", "rx":"Rx"}[gate.name.name]
        if gate.arguments:
            name += "(" + angle_text(gate.arguments[0]) + ")"
        wires = ",".join(str(q.indices[0][0].value) for q in gate.qubits)
        value = "apply(" + name + "," + value + ",[" + wires + "])"
    expected = state
    for name in ["Rxx", "Ryy", "Rzz", "Rzx"]:
        expected = "apply(" + name + "(pi/2)," + expected + ",[2,0])"
    result = subprocess.run([str(worker)], input="quantum:norm((" + value + ")-(" + expected + "))", encoding="utf-8", capture_output=True)
    assert result.returncode == 0 and result.stdout.strip() == "0", (index, result.stdout, result.stderr)
program = parse(Path(base + ".reordered.qasm").read_text(encoding="utf-8-sig"))
gates = [s for s in program.statements if isinstance(s, ast.QuantumGate)]
assert [g.name.name for g in gates] == ["h", "cx"]
assert [[q.indices[0][0].value for q in g.qubits] for g in gates] == [[0], [0, 1]]
program = parse(Path(base + ".correction.qasm").read_text(encoding="utf-8-sig"))
value = "|00000>"
measured = {}
syndromes = []
for statement in program.statements:
    if isinstance(statement, ast.QuantumGate):
        name = {"h":"H", "s":"S", "x":"X", "cx":"CNOT"}[statement.name.name]
        wires = ",".join(str(q.indices[0][0].value) for q in statement.qubits)
        value = "apply(" + name + "," + value + ",[" + wires + "])"
    elif isinstance(statement, ast.QuantumMeasurementStatement):
        measured[statement.target.name] = statement.measure.qubit.indices[0][0].value
    elif isinstance(statement, ast.BranchingStatement):
        condition = statement.condition
        assert condition.op.name == "&&" and len(statement.if_block) == 1 and not statement.else_block
        parts = [condition.lhs, condition.rhs]
        assert all(p.op.name == "==" for p in parts)
        wires = [measured[p.lhs.name] for p in parts]
        outcome = 2 * parts[0].rhs.value + parts[1].rhs.value
        gate = statement.if_block[0]
        target = gate.qubits[0].indices[0][0].value
        assert gate.name.name == "x"
        syndromes.append((wires, outcome, target))
        value = "feedforward(" + value + ",[" + ",".join(map(str,wires)) + "]," + str(outcome) + ",X," + str(target) + ")"
assert syndromes == [([3,4],2,0), ([3,4],3,1), ([3,4],1,2)]
result = subprocess.run([str(worker)], input="quantum:tr((ptrace("+value+",[1,2,3,4])-density(|i>))^2)", encoding="utf-8", capture_output=True)
assert result.returncode == 0 and result.stdout.strip() == "0", (result.stdout,result.stderr)
program = parse(Path(base + ".r.qasm").read_text(encoding="utf-8-sig"))
gates = [s for s in program.statements if isinstance(s, ast.QuantumGate)]
assert [g.name.name for g in gates] == ["rz", "rx", "rz"]
assert all(g.qubits[0].indices[0][0].value == 2 for g in gates)
for index in range(8):
    state = "|" + format(index, "03b") + ">"
    value = state
    for gate in gates:
        name = {"rz": "Rz", "rx": "Rx"}[gate.name.name]
        value = "apply(" + name + "(" + angle_text(gate.arguments[0]) + ")," + value + ",2)"
    expression = "quantum:norm((" + value + ")-apply(R(pi/3,pi/4)," + state + ",2))"
    result = subprocess.run([str(worker)], input=expression, encoding="utf-8", capture_output=True)
    assert result.returncode == 0 and result.stdout.strip() == "0", (index, result.stdout, result.stderr)
print("PASS: OpenQASM syntax, editing, ordered wires, two-bit feedback, error correction, and exact gate decompositions.")

# Independent complex simulation of parity-gate exports on ordered wires [2,0].
# Expected matrices are the IBM definitions permuted to first-wire-most-significant.
for name in ("XXPlusYY", "XXMinusYY"):
    program = parse(Path(base + "." + name + ".qasm").read_text(encoding="utf-8-sig"))
    instructions = [s for s in program.statements if isinstance(s, ast.QuantumGate)]
    c, z = math.cos(math.pi/6), -1j*math.sin(math.pi/6)
    positive, negative = z*cmath.exp(1j*math.pi/4), z*cmath.exp(-1j*math.pi/4)
    matrix = ([[1,0,0,0],[0,c,positive,0],[0,negative,c,0],[0,0,0,1]] if name=="XXPlusYY" else
              [[c,0,0,negative],[0,1,0,0],[0,0,1,0],[positive,0,0,c]])
    for index in range(8):
        actual = [complex(k==index) for k in range(8)]
        for gate in instructions:
            wires = [q.indices[0][0].value for q in gate.qubits]
            kind = gate.name.name
            if gate.arguments:
                angle = eval(angle_text(gate.arguments[0]), {"__builtins__": {}}, {"pi":math.pi})
            if kind=="h": single = [[1/math.sqrt(2),1/math.sqrt(2)],[1/math.sqrt(2),-1/math.sqrt(2)]]
            elif kind=="rx": single = [[math.cos(angle/2),-1j*math.sin(angle/2)],[-1j*math.sin(angle/2),math.cos(angle/2)]]
            elif kind=="rz": single = [[cmath.exp(-1j*angle/2),0],[0,cmath.exp(1j*angle/2)]]
            else: assert kind=="cx",kind
            updated = [0j]*8
            for column, amplitude in enumerate(actual):
                if kind=="cx":
                    row = column ^ ((1 << (2-wires[1])) if column & (1 << (2-wires[0])) else 0)
                    updated[row] += amplitude
                else:
                    mask = 1 << (2-wires[0]); bit = int(bool(column & mask))
                    for rowbit in (0,1): updated[(column & ~mask) | rowbit*mask] += single[rowbit][bit]*amplitude
            actual = updated
        column = 2*(index & 1)+((index >> 2) & 1)
        expected = [0j]*8
        for row in range(4): expected[(index & 2) | (row >> 1) | ((row & 1) << 2)] = matrix[row][column]
        assert max(abs(x-y) for x,y in zip(actual,expected))<1e-14,(name,index,actual,expected)
print("PASS: XXPlusYY and XXMinusYY exports, all basis states and complex amplitudes with a spectator wire.")
