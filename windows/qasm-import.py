"""Compile OpenQASM 2/3 to the editor's validated circuit format.

Uses qBraid PyQASM 1.0.4. The adapter fails closed for AST operations that
cannot be represented by CircuitComposer; it never executes Python input.
"""
import json
import math
import sys
from dataclasses import fields, is_dataclass

import openqasm3.ast as ast
import pyqasm
from pyqasm.visitor import QasmVisitor
from pyqasm.expressions import Qasm3ExprEvaluator
from pyqasm.transformer import Qasm3Transformer
from pyqasm.validator import Qasm3Validator
from pyqasm.elements import Context


def unroll_preserving_phase(module, primitives, preserve_branches=False):
    """Adapt the pinned compiler's controlled-gphase lowering.

    PyQASM 1.0.4 lowers controlled gphase through its basic P decomposition,
    yielding Rz and losing a global phase. Emit a numeric P/CP node with the actual controls, preserving its phase.
    The helper is a single-request process; restore the method for test callers.
    """
    if pyqasm.__version__ != '1.0.4':
        raise ValueError('This compiler adapter requires PyQASM 1.0.4.')
    original = QasmVisitor._visit_phase_operation
    original_range = Qasm3Transformer.get_qubits_from_range_definition
    original_branch = QasmVisitor._visit_branching_statement
    def branch(visitor, statement):
        if not Qasm3ExprEvaluator.classical_register_in_expr(statement.condition):
            return original_branch(visitor, statement)
        # Preserve one decision at block entry. The pinned compiler expands
        # register comparisons with reversed bit significance.
        def reference(value):
            if isinstance(value, ast.Identifier):
                name, index = value.name, None
            elif isinstance(value, ast.IndexExpression) and isinstance(value.collection, ast.Identifier) and isinstance(value.index, list) and len(value.index) == 1:
                name = value.collection.name
                index = Qasm3ExprEvaluator.evaluate_expression(value.index[0])[0]
            else:
                raise ValueError('A runtime condition needs a classical register or one indexed bit.')
            size = visitor._global_creg_size_map.get(name)
            if size is None:
                raise ValueError('Unknown classical condition register: ' + name)
            if index is not None:
                if type(index) is not int or not 0 <= index < size:
                    raise ValueError('Classical condition index is outside its register.')
                visitor._is_branch_clbits.add((name, index))
                return ast.IndexExpression(collection=ast.Identifier(name), index=[ast.IntegerLiteral(index)])
            visitor._is_branch_clbits.update((name, bit) for bit in range(size))
            return ast.Identifier(name)
        condition = statement.condition
        if isinstance(condition, ast.BinaryExpression):
            if condition.op.name not in ('==', '!='):
                raise ValueError('Classical circuit import currently requires equality or inequality conditions.')
            if Qasm3ExprEvaluator.classical_register_in_expr(condition.rhs):
                raise ValueError('A classical comparison currently needs a constant right-hand side.')
            rhs = Qasm3ExprEvaluator.evaluate_expression(condition.rhs)[0]
            if type(rhs) not in (int, bool):
                raise ValueError('A classical comparison needs an integer or Boolean constant.')
            condition = ast.BinaryExpression(op=condition.op, lhs=reference(condition.lhs), rhs=ast.IntegerLiteral(int(rhs)))
        elif isinstance(condition, ast.UnaryExpression) and condition.op.name == '!':
            condition = ast.UnaryExpression(op=condition.op, expression=reference(condition.expression))
        else:
            condition = reference(condition)
        if visitor._in_branching_statement >= 32:
            raise ValueError('Classical circuit branches exceed 32 levels.')
        visitor._scope_manager.push_context(Context.BLOCK)
        visitor._scope_manager.push_scope({})
        visitor._scope_manager.increment_scope_level()
        visitor._in_branching_statement += 1
        try:
            yes = visitor.visit_basic_block(statement.if_block)
            no = visitor.visit_basic_block(statement.else_block)
            return [] if visitor._check_only else [ast.BranchingStatement(condition=condition, if_block=yes, else_block=no)]
        finally:
            visitor._scope_manager.decrement_scope_level()
            visitor._scope_manager.pop_scope()
            visitor._scope_manager.restore_context()
            visitor._in_branching_statement -= 1
            if not visitor._in_branching_statement:
                visitor._update_branching_gate_depths()
    def register_range(range_def, qreg_size, is_qubit_reg, op_node=None):
        # OpenQASM index ranges include their endpoint, unlike Python slices.
        start = 0 if range_def.start is None else Qasm3ExprEvaluator.evaluate_expression(range_def.start)[0]
        end = qreg_size-1 if range_def.end is None else Qasm3ExprEvaluator.evaluate_expression(range_def.end)[0]
        step = 1 if range_def.step is None else Qasm3ExprEvaluator.evaluate_expression(range_def.step)[0]
        if any(type(value) is not int for value in (start, end, step)) or step == 0:
            raise ValueError('Register ranges require integer bounds and a nonzero integer step.')
        for index in (start, end):
            Qasm3Validator.validate_register_index(index, qreg_size, qubit=is_qubit_reg, op_node=op_node)
        return list(range(start, end+(1 if step > 0 else -1), step))
    def phase(visitor, operation, inverse=False, ctrls=None):
        if not ctrls:
            return original(visitor, operation, inverse, ctrls)
        value = Qasm3ExprEvaluator.evaluate_expression(operation.argument)[0]
        if inverse:
            value = -value
        if len(ctrls) not in (1,2):
            raise ValueError("Controlled global phase currently supports one or two controls.")
        return [ast.QuantumGate(modifiers=[], name=ast.Identifier("p" if len(ctrls)==1 else "cp"),
                                arguments=[ast.FloatLiteral(value)], qubits=list(ctrls))]
    QasmVisitor._visit_phase_operation = phase
    Qasm3Transformer.get_qubits_from_range_definition = staticmethod(register_range)
    if preserve_branches:
        QasmVisitor._visit_branching_statement = branch
    try:
        module.unroll(max_loop_iters=4096, external_gates=list(primitives))
    finally:
        QasmVisitor._visit_phase_operation = original
        Qasm3Transformer.get_qubits_from_range_definition = staticmethod(original_range)
        QasmVisitor._visit_branching_statement = original_branch


GATES = {name.lower(): name for name in (
    'H', 'X', 'Y', 'Z', 'S', 'T', 'Sdg', 'Tdg', 'SX', 'SXdg',
    'Rx', 'Ry', 'Rz', 'P', 'CZ', 'SWAP', 'CCX', 'CY', 'CH', 'CCZ',
    'CSWAP', 'CP', 'CRx', 'CRy', 'CRz', 'Rxx', 'Ryy', 'Rzz', 'Rzx')}
GATES.update(cx='CNOT', cnot='CNOT', u='U3', U='U3', u3='U3')
GATES.update(u1='P')
GATES.update(iswap='iSWAP')

def gate_steps(statement, wire, published_u=False):
    name = statement.name.name
    if name not in GATES and name not in ('id', 'i', 'u2'):
        raise ValueError('The editor cannot represent compiled gate: ' + name)
    args = [number(a) for a in statement.arguments]
    wires = [wire(q) for q in statement.qubits]
    gate = GATES.get(name, name)
    phase = 0.0
    if published_u and name == 'U':
        if len(args) != 3:
            raise ValueError('U requires three parameters.')
        # The published OpenQASM 3 matrix is exp(i*theta/2) times the
        # IBM/Qiskit cos/sin matrix. Keep this phase when adding controls.
        phase = float(args[0]) / 2
    if name == 'u2':
        if len(args) != 2:
            raise ValueError('u2 requires two parameters.')
        gate, args = 'U3', [format(math.pi / 2, '.17g')] + args
    prefix, suffix, repeats = [], [], 1
    offsets, offset = {}, 0
    for modifier in statement.modifiers:
        if modifier.modifier.name in ('ctrl', 'negctrl'):
            value = 1.0 if modifier.argument is None else float(number(modifier.argument))
            if not value.is_integer() or not 1 <= value <= 7:
                raise ValueError('Invalid control count.')
            offsets[id(modifier)] = offset
            offset += int(value)
    for modifier in reversed(statement.modifiers):
        kind = modifier.modifier.name
        if kind == 'pow':
            value = float(number(modifier.argument))
            if not value.is_integer() or abs(value) > 64:
                raise ValueError('Gate powers must be integers between -64 and 64.')
            repeats *= abs(int(value))
            if repeats > 64:
                raise ValueError('The gate power exceeds 64 steps.')
            if value >= 0:
                continue
            kind = 'inv'
        if kind == 'inv':
            phase = -phase
            inverse = {'S':'Sdg', 'Sdg':'S', 'T':'Tdg', 'Tdg':'T', 'SX':'SXdg', 'SXdg':'SX',
                       'iSWAP':'iSWAPdg', 'iSWAPdg':'iSWAP', 'CiSWAP':'CiSWAPdg', 'CiSWAPdg':'CiSWAP'}
            if gate in inverse:
                gate = inverse[gate]
            elif gate in ('U3', 'CU3'):
                args = [number(ast.FloatLiteral(-float(args[i]))) for i in (0,2,1)]
            elif args:
                args = [number(ast.FloatLiteral(-float(a))) for a in args]
            elif gate not in ('H','X','Y','Z','CNOT','CZ','CY','CH','CCX','CCZ','SWAP','CSWAP','id','i'):
                raise ValueError('Unsupported inverse gate: ' + gate)
        elif kind in ('ctrl', 'negctrl'):
            controls = 1 if modifier.argument is None else int(number(modifier.argument))
            # Fixed phase gates are P(theta), including their relative phase.
            fixed_phase = {'S': math.pi/2, 'Sdg': -math.pi/2,
                           'T': math.pi/4, 'Tdg': -math.pi/4}
            if gate in fixed_phase:
                if args:
                    raise ValueError('Fixed phase gates do not accept parameters.')
                args = [format(fixed_phase[gate], '.17g')]
                gate = 'P'
            mapping = {'X':'CNOT','Y':'CY','Z':'CZ','H':'CH','P':'CP','Rx':'CRx','Ry':'CRy','Rz':'CRz','CNOT':'CCX','CZ':'CCZ','SWAP':'CSWAP','U3':'CU3'}
            mapping.update(iSWAP='CiSWAP', iSWAPdg='CiSWAPdg')
            for _ in range(controls):
                if gate not in mapping:
                    raise ValueError('Controlled gate is not representable: ' + gate)
                gate = mapping[gate]
            if kind == 'negctrl':
                start = offsets[id(modifier)]
                selected = wires[start:start+controls]
                prefix = [{'Gate':'X','Angle':'','Wires':[w]} for w in selected] + prefix
                suffix += [{'Gate':'X','Angle':'','Wires':[w]} for w in reversed(selected)]
        else:
            raise ValueError('Unsupported gate modifier: ' + kind)
    required = 3 if gate in ('CCX','CCZ','CSWAP','CiSWAP','CiSWAPdg') else 2 if gate in ('CNOT','CZ','CY','CH','SWAP','CP','CRx','CRy','CRz','Rxx','Ryy','Rzz','Rzx','CU3','iSWAP','iSWAPdg') else 1
    parameters = 3 if gate in ('U3','CU3') else 1 if gate in ('Rx','Ry','Rz','P','CP','CRx','CRy','CRz','Rxx','Ryy','Rzz','Rzx') else 0
    if len(wires) != required or len(set(wires)) != len(wires) or len(args) != parameters:
        raise ValueError('Incorrect qubit or parameter count for ' + name)
    if gate in ('id','i'):
        return []
    operations = ([{'Gate':g,'Angle':a,'Wires':wires} for g,a in
                   [('CP',args[2]),('CRy',args[0]),('CP',args[1])]] if gate=='CU3' else
                  [{'Gate':gate,'Angle':','.join(args),'Wires':wires}]) * repeats
    if gate == 'iSWAPdg':
        # iSWAP^-1 = (Z tensor Z) iSWAP, with no dropped global phase.
        operations = ([{'Gate':'iSWAP','Angle':'','Wires':wires}] +
                      [{'Gate':'Z','Angle':'','Wires':[w]} for w in wires]) * repeats
    elif gate in ('CiSWAP','CiSWAPdg'):
        # iSWAP = SWAP CZ (S tensor S). Control every factor, including phase.
        angle = format((-1 if gate.endswith('dg') else 1) * math.pi/2, '.17g')
        operations = ([{'Gate':'CP','Angle':angle,'Wires':[wires[0],w]} for w in wires[1:]] +
                      [{'Gate':'CCZ','Angle':'','Wires':wires},
                       {'Gate':'CSWAP','Angle':'','Wires':wires}]) * repeats
    if phase and repeats:
        operations.append({'Gate':'P' if offset else 'GPhase',
                           'Angle':format(phase*repeats,'.17g'),'Wires':[wires[0]]})
    return prefix + operations + suffix


def nodes(value):
    if is_dataclass(value):
        yield value
        for field in fields(value):
            if field.name not in ('span', 'annotations'):
                yield from nodes(getattr(value, field.name))
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from nodes(item)


def number(value):
    if not isinstance(value, (ast.IntegerLiteral, ast.FloatLiteral)):
        raise ValueError('An unresolved gate parameter remains after compilation.')
    if not math.isfinite(value.value):
        raise ValueError('Gate parameters must be finite.')
    return format(value.value, '.17g')


def convert(source, published_u=False, classical=False):
    if len(source.encode('utf-8')) > 262144:
        raise ValueError('OpenQASM input must be at most 256 KB.')
    module = pyqasm.loads(source)
    if published_u and not str(module.original_program.version).startswith('3'):
        raise ValueError('The published OpenQASM 3 U convention requires an OpenQASM 3 program.')
    # PyQASM recognizes built-in includes but does not resolve arbitrary files.
    # Reject these before compilation, rather than pretend their content ran.
    for node in nodes(module.original_program):
        if classical and isinstance(node, ast.ClassicalAssignment):
            raise ValueError('Runtime classical assignments are not yet supported by the classical circuit importer.')
        if classical and isinstance(node, ast.ClassicalDeclaration):
            if not isinstance(node.type, ast.BitType) or (node.init_expression is not None and not isinstance(node.init_expression, ast.QuantumMeasurement)):
                raise ValueError('Classical circuit import supports bit registers initialized to zero or by measurement; other classical declarations are not yet supported.')
        if isinstance(node, ast.Include) and node.filename not in ('stdgates.inc', 'qelib1.inc'):
            raise ValueError('Only stdgates.inc and qelib1.inc includes are supported.')
        if getattr(node, 'annotations', None):
            raise ValueError('Annotated operations require semantics the editor does not support.')
    # Preserve primitive gates: generic decomposition may preserve a unitary
    # only up to global phase. The calculator exposes exact state amplitudes.
    defined = {n.name.name for n in nodes(module.original_program) if isinstance(n, ast.QuantumGateDefinition)}
    primitives = {n.name.name for n in nodes(module.original_program) if isinstance(n, ast.QuantumGate)} - defined
    unroll_preserving_phase(module, primitives, preserve_branches=classical)
    statements = module.unrolled_ast.statements
    if classical:
        return classical_circuit(statements, published_u)
    registers, count = {}, 0
    for statement in statements:
        if isinstance(statement, ast.QubitDeclaration):
            size = 1 if statement.size is None else statement.size.value
            registers[statement.qubit.name] = (count, size)
            count += size
    if not 1 <= count <= 25:
        raise ValueError('The circuit editor currently supports 1–25 qubits.')

    def wire(value):
        if isinstance(value, ast.Identifier):
            start, size = registers[value.name]
            if size != 1:
                raise ValueError('A register operation was not expanded by the compiler.')
            return start
        if not isinstance(value, ast.IndexedIdentifier) or len(value.indices) != 1 or len(value.indices[0]) != 1:
            raise ValueError('Unresolved qubit reference.')
        start, size = registers[value.name.name]
        index = value.indices[0][0].value
        if not isinstance(index, int) or not 0 <= index < size:
            raise ValueError('Qubit index is outside its register.')
        return start + index

    steps = []
    for statement in statements:
        if isinstance(statement, (ast.Include, ast.QubitDeclaration, ast.QuantumBarrier)):
            continue
        if isinstance(statement, ast.ClassicalDeclaration):
            if not isinstance(statement.type, ast.BitType) or statement.init_expression is not None:
                raise ValueError('Unresolved classical state remains after compilation.')
            continue
        angle = ''
        if isinstance(statement, ast.QuantumGate):
            if statement.duration is not None:
                raise ValueError('Timed gates are not supported.')
            steps.extend(gate_steps(statement, wire, published_u))
            if len(steps) > 512:
                raise ValueError('The compiled circuit exceeds the editor limit of 512 steps.')
            continue
        elif isinstance(statement, ast.QuantumPhase):
            if statement.modifiers:
                if (len(statement.modifiers) != 1 or statement.modifiers[0].modifier != ast.GateModifierName.ctrl
                        or statement.modifiers[0].argument.value != len(statement.qubits)):
                    raise ValueError('Unresolved controlled global phase.')
                wires = [wire(q) for q in statement.qubits]
                if len(wires) not in (1,2) or len(set(wires)) != len(wires):
                    raise ValueError('Controlled global phase currently supports one or two distinct controls.')
                gate, angle = ('P' if len(wires)==1 else 'CP'), number(statement.argument)
            else:
                gate, angle, wires = 'GPhase', number(statement.argument), [0]
        elif isinstance(statement, ast.QuantumReset):
            gate, wires = 'Reset', [wire(statement.qubits)]
        elif isinstance(statement, ast.QuantumMeasurementStatement):
            gate, wires = 'Measure', [wire(statement.measure.qubit)]
        else:
            raise ValueError('The editor cannot represent ' + type(statement).__name__ +
                             '. Runtime classical feedback, timing and pulse programs require a richer execution model.')
        steps.append({'Gate': gate, 'Angle': angle, 'Wires': wires})
        if len(steps) > 512:
            raise ValueError('The compiled circuit exceeds the editor limit of 512 steps.')
    return {'Version': 1, 'Qubits': count, 'Steps': steps}


def classical_circuit(statements, published_u):
    quantum, classical, named = {}, {}, []
    nq = nc = 0
    for statement in statements:
        if isinstance(statement, ast.QubitDeclaration):
            size = 1 if statement.size is None else statement.size.value
            quantum[statement.qubit.name] = (nq, size)
            nq += size
        elif isinstance(statement, ast.ClassicalDeclaration):
            if not isinstance(statement.type, ast.BitType) or statement.init_expression is not None:
                raise ValueError('Unresolved classical initialization after compilation.')
            size = 1 if statement.type.size is None else statement.type.size.value
            if type(size) is not int or size < 1:
                raise ValueError('Classical registers need a positive integer size.')
            name = statement.identifier.name
            classical[name] = (nc, size)
            named.append({'Name': name, 'Size': size})
            nc += size
    if not 1 <= nq <= 25 or not 0 <= nc <= 64:
        raise ValueError('Classical circuits support 1–25 qubits and up to 64 classical bits.')

    def reference(value, registers, whole=False):
        if isinstance(value, ast.Identifier):
            start, size = registers[value.name]
            if whole:
                return start, size
            if size != 1:
                raise ValueError('Register operation was not expanded by the compiler.')
            return start
        if isinstance(value, ast.IndexedIdentifier):
            name, indices = value.name.name, value.indices
            if len(indices) != 1:
                raise ValueError('Unresolved register index.')
            indices = indices[0]
        elif isinstance(value, ast.IndexExpression) and isinstance(value.collection, ast.Identifier):
            name, indices = value.collection.name, value.index
        else:
            raise ValueError('Unresolved register reference.')
        if not isinstance(indices, list) or len(indices) != 1 or not isinstance(indices[0], ast.IntegerLiteral):
            raise ValueError('Expected one literal register index.')
        start, size = registers[name]
        index = indices[0].value
        if type(index) is not int or not 0 <= index < size:
            raise ValueError('Register index is outside its declaration.')
        return (start+index, 1) if whole else start+index

    count = 0
    def lower(body, depth=0):
        nonlocal count
        result = []
        def append(step):
            nonlocal count
            count += 1
            if count > 512:
                raise ValueError('Classical circuits support at most 512 total operations.')
            result.append(step)
        for statement in body:
            if isinstance(statement, (ast.Include, ast.QuantumBarrier)):
                continue
            if isinstance(statement, (ast.QubitDeclaration, ast.ClassicalDeclaration)):
                if depth:
                    raise ValueError('Register declarations inside runtime branches are not supported.')
                continue
            if isinstance(statement, ast.BranchingStatement):
                if depth >= 32:
                    raise ValueError('Classical circuits support at most 32 nested branches.')
                condition = statement.condition
                negate = False
                if isinstance(condition, ast.BinaryExpression) and condition.op.name in ('==', '!=') and isinstance(condition.rhs, ast.IntegerLiteral):
                    target, expected = condition.lhs, condition.rhs.value
                    negate = condition.op.name == '!='
                elif isinstance(condition, ast.UnaryExpression) and condition.op.name == '!':
                    target, expected = condition.expression, 0
                else:
                    target, expected = condition, 1
                start, size = reference(target, classical, whole=True)
                if not isinstance(condition, ast.BinaryExpression) and size != 1:
                    raise ValueError('Whole-register truth conditions require an explicit comparison.')
                if type(expected) is not int or not 0 <= expected < (1 << size):
                    raise ValueError('Condition constant is outside its register range.')
                yes, no = lower(statement.if_block, depth+1), lower(statement.else_block, depth+1)
                if negate:
                    yes, no = no, yes
                append({'Kind': 'Branch', 'Mask': str(((1 << size)-1) << start), 'Value': str(expected << start), 'WhenTrue': yes, 'WhenFalse': no})
            elif isinstance(statement, ast.QuantumMeasurementStatement):
                wire = reference(statement.measure.qubit, quantum)
                if statement.target is None:
                    append({'Kind': 'Channel', 'Expression': 'phase_damping(1)', 'Wires': [wire]})
                else:
                    append({'Kind': 'Measure', 'Wires': [wire], 'ClassicalBit': reference(statement.target, classical)})
            elif isinstance(statement, ast.QuantumReset):
                append({'Kind': 'Reset', 'Wires': [reference(statement.qubits, quantum)]})
            elif isinstance(statement, ast.QuantumGate):
                if statement.duration is not None:
                    raise ValueError('Timed gates are not supported.')
                for step in gate_steps(statement, lambda q: reference(q, quantum), published_u):
                    name, angle = step['Gate'], step['Angle']
                    expression = '(exp(i*('+angle+'))*I)' if name == 'GPhase' else name+('('+angle+')' if angle else '')
                    append({'Kind': 'Gate', 'Expression': expression, 'Wires': step['Wires']})
            elif isinstance(statement, ast.QuantumPhase) and not statement.modifiers:
                append({'Kind': 'Gate', 'Expression': '(exp(i*('+number(statement.argument)+'))*I)', 'Wires': [0]})
            else:
                raise ValueError('Classical circuit import cannot yet represent '+type(statement).__name__+'.')
        return result
    return {'Version': 2, 'Qubits': nq, 'Registers': named, 'OutputBits': list(reversed(range(nc))), 'Steps': lower(statements)}


if __name__ == '__main__':
    # Redirected Windows streams otherwise inherit the local code page, while
    # the GUI consumes UTF-8. Keep diagnostics readable in every locale.
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8', errors='backslashreplace')
    try:
        source_bytes = sys.stdin.buffer.read(262145)
        if len(source_bytes) > 262144:
            raise ValueError('OpenQASM input must be at most 256 KB.')
        source = source_bytes.decode('utf-8-sig')
        if len(set(sys.argv[1:])) != len(sys.argv[1:]) or any(arg not in ('--published-u', '--classical') for arg in sys.argv[1:]):
            raise ValueError('Usage: qasm-import.exe [--published-u] [--classical] (OpenQASM on stdin)')
        result = convert(source, published_u='--published-u' in sys.argv[1:], classical='--classical' in sys.argv[1:])
        sys.stdout.write(json.dumps(result))
    except Exception as error:
        sys.stderr.write(str(error)[:4096] + '\n')
        sys.exit(1)
