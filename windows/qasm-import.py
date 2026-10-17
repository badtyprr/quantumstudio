"""Compile OpenQASM 2/3 to the editor's validated circuit format.

Uses qBraid PyQASM 1.0.4. The adapter fails closed for AST operations that
cannot be represented by CircuitComposer; it never executes Python input.
"""
import json
import math
import sys
import copy
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
    original_assignment = QasmVisitor._visit_classical_assignment
    original_declaration = QasmVisitor._visit_classical_declaration
    def runtime(visitor,value):
        return any(isinstance(item,ast.Identifier) and item.name in visitor._global_creg_size_map for item in nodes(value))
    def bit_function(value):
        return any(isinstance(item,ast.FunctionCall) and item.name.name in ('popcount','rotl','rotr') for item in nodes(value))
    def normalize(visitor, value, depth=0, cast_distance=False):
        if depth >= 32:
            raise ValueError('Classical expressions exceed 32 levels.')
        registers = visitor._global_creg_size_map
        if isinstance(value, ast.Identifier) and value.name in registers:
            return copy.deepcopy(value)
        if isinstance(value, ast.IndexedIdentifier):
            if len(value.indices)!=1:
                raise ValueError('Expected one classical index dimension.')
            value = ast.IndexExpression(collection=value.name, index=value.indices[0])
        if isinstance(value, ast.IndexExpression) and isinstance(value.collection, ast.Identifier) and value.collection.name in registers:
            def integer(item):
                if runtime(visitor,item):
                    raise ValueError('Runtime classical indices are not yet supported.')
                result = Qasm3ExprEvaluator.evaluate_expression(item)[0]
                if type(result) is not int:
                    raise ValueError('Classical indices must be integers.')
                return ast.IntegerLiteral(result)
            index = value.index
            if isinstance(index, ast.DiscreteSet):
                index = ast.DiscreteSet(values=[integer(item) for item in index.values])
            elif isinstance(index, list) and len(index) == 1:
                item = index[0]
                if isinstance(item, ast.RangeDefinition):
                    item = ast.RangeDefinition(start=None if item.start is None else integer(item.start),
                                              end=None if item.end is None else integer(item.end),
                                              step=None if item.step is None else integer(item.step))
                else:
                    item = integer(item)
                index = [item]
            else:
                raise ValueError('Expected one classical index or slice.')
            return ast.IndexExpression(collection=copy.deepcopy(value.collection), index=index)
        if isinstance(value,ast.FunctionCall) and value.name.name in ('popcount','rotl','rotr'):
            expected=1 if value.name.name=='popcount' else 2
            if len(value.arguments)!=expected:raise ValueError('Wrong number of classical bit-function arguments.')
            return ast.FunctionCall(name=copy.deepcopy(value.name),arguments=[normalize(visitor,item,depth+1,cast_distance=(value.name.name in ('rotl','rotr') and index==1)) for index,item in enumerate(value.arguments)])
        if isinstance(value,ast.Cast) and isinstance(value.type,(ast.IntType,ast.UintType)) and (cast_distance or runtime(visitor,value)):
            if value.type.size is None:raise ValueError('Runtime integer casts need an explicit width.')
            size=Qasm3ExprEvaluator.evaluate_expression(value.type.size)[0]
            if type(size) is not int or not 1<=size<=64:raise ValueError('Integer cast width must be 1–64.')
            return ast.Cast(type=type(value.type)(size=ast.IntegerLiteral(size)),argument=normalize(visitor,value.argument,depth+1))
        if isinstance(value, ast.BinaryExpression):
            if not runtime(visitor,value) and not bit_function(value) and not any(isinstance(item,ast.BitstringLiteral) for item in nodes(value)):
                result=Qasm3ExprEvaluator.evaluate_expression(value)[0]
                if type(result) not in (int,bool):raise ValueError('Expected an integer classical constant.')
                return ast.BooleanLiteral(result) if type(result) is bool else ast.IntegerLiteral(result)
            return ast.BinaryExpression(op=value.op, lhs=normalize(visitor,value.lhs,depth+1), rhs=normalize(visitor,value.rhs,depth+1))
        if isinstance(value, ast.UnaryExpression) and value.op.name in ('~','!'):
            return ast.UnaryExpression(op=value.op, expression=normalize(visitor,value.expression,depth+1))
        if isinstance(value, (ast.IntegerLiteral,ast.BooleanLiteral,ast.BitstringLiteral)):
            return copy.deepcopy(value)
        if runtime(visitor,value):
            raise ValueError('Unsupported runtime classical expression: '+type(value).__name__)
        result = Qasm3ExprEvaluator.evaluate_expression(value)[0]
        if type(result) not in (int,bool):
            raise ValueError('Classical bit expressions require integer or Boolean values.')
        return ast.IntegerLiteral(int(result))
    def assignment(visitor, statement):
        name = statement.lvalue.name
        name = name.name if isinstance(name,ast.Identifier) else name
        if name not in visitor._global_creg_size_map:
            return original_assignment(visitor,statement)
        target = normalize(visitor,statement.lvalue)
        value = normalize(visitor,statement.rvalue)
        if statement.op.name != '=':
            operation = statement.op.name[:-1]
            if operation not in ('&','|','^','<<','>>'):
                raise ValueError('Unsupported classical bit assignment: '+statement.op.name)
            value = ast.BinaryExpression(op=ast.BinaryOperator[operation],lhs=copy.deepcopy(target),rhs=value)
        return [] if visitor._check_only else [ast.ClassicalAssignment(lvalue=target,op=ast.AssignmentOperator['='],rvalue=value)]
    def declaration(visitor, statement):
        if not isinstance(statement.type,ast.BitType) or statement.init_expression is None or isinstance(statement.init_expression,ast.QuantumMeasurement):
            return original_declaration(visitor,statement)
        bare = copy.deepcopy(statement);bare.init_expression=None
        result = original_declaration(visitor,bare)
        initial = ast.ClassicalAssignment(lvalue=copy.deepcopy(statement.identifier),op=ast.AssignmentOperator['='],rvalue=statement.init_expression)
        return result+assignment(visitor,initial)
    def branch(visitor, statement):
        if not runtime(visitor,statement.condition) and not bit_function(statement.condition):
            return original_branch(visitor, statement)
        # Preserve the expression and choose the body only during execution.
        condition = normalize(visitor,statement.condition)
        for item in nodes(condition):
            if isinstance(item,ast.Identifier) and item.name in visitor._global_creg_size_map:
                visitor._is_branch_clbits.update((item.name,bit) for bit in range(visitor._global_creg_size_map[item.name]))
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
        QasmVisitor._visit_classical_assignment = assignment
        QasmVisitor._visit_classical_declaration = declaration
    try:
        module.unroll(max_loop_iters=4096, external_gates=list(primitives))
    finally:
        QasmVisitor._visit_phase_operation = original
        Qasm3Transformer.get_qubits_from_range_definition = staticmethod(original_range)
        QasmVisitor._visit_branching_statement = original_branch
        QasmVisitor._visit_classical_assignment = original_assignment
        QasmVisitor._visit_classical_declaration = original_declaration


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
    if classical:
        bit_names={node.identifier.name for node in nodes(module.original_program)
                   if isinstance(node,ast.ClassicalDeclaration) and isinstance(node.type,ast.BitType)}
        def runtime(value):
            return any(isinstance(item,ast.Identifier) and item.name in bit_names for item in nodes(value))
        for node in nodes(module.original_program):
            index=(node.indices if isinstance(node,ast.IndexedIdentifier) else node.index if isinstance(node,ast.IndexExpression) else None)
            if index is not None and runtime(index):
                raise ValueError('Runtime register indices are not yet supported by the circuit importer.')
            if isinstance(node,(ast.QubitDeclaration,ast.BitType)) and node.size is not None and runtime(node.size):
                raise ValueError('Runtime register sizes are not yet supported by the circuit importer.')
            if isinstance(node,ast.AliasStatement) and runtime(node.value):
                raise ValueError('Classical aliases are not yet supported by the circuit importer.')
            control=(node.while_condition if isinstance(node,ast.WhileLoop) else
                     node.set_declaration if isinstance(node,ast.ForInLoop) else
                     node.target if isinstance(node,ast.SwitchStatement) else None)
            if control is not None and runtime(control):
                raise ValueError('Runtime loops and switch statements require control flow not yet supported by the circuit importer.')
            if isinstance(node,ast.QuantumGate) and runtime(node.arguments) or isinstance(node,ast.QuantumPhase) and runtime(node.argument):
                raise ValueError('Runtime gate parameters are not yet supported by the circuit importer.')
            if isinstance(node,ast.FunctionCall) and node.name.name not in ('popcount','rotl','rotr') and runtime(node.arguments):
                raise ValueError('Runtime function arguments are not yet supported by the circuit importer.')
            targets=(node.qubits if isinstance(node,(ast.QuantumGate,ast.QuantumPhase,ast.QuantumReset,ast.QuantumBarrier)) else
                     node.qubit if isinstance(node,ast.QuantumMeasurement) else None)
            if targets is not None and runtime(targets):
                raise ValueError('Runtime quantum targets are not yet supported by the circuit importer.')
    if published_u and not str(module.original_program.version).startswith('3'):
        raise ValueError('The published OpenQASM 3 U convention requires an OpenQASM 3 program.')
    # PyQASM recognizes built-in includes but does not resolve arbitrary files.
    # Reject these before compilation, rather than pretend their content ran.
    for node in nodes(module.original_program):
        if classical and isinstance(node, ast.ClassicalDeclaration):
            if not isinstance(node.type, ast.BitType):
                raise ValueError('Classical circuit import currently supports bit registers; other classical declarations are not yet supported.')
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


def classical_indices(value, registers):
    if isinstance(value,ast.Identifier):
        start,size=registers[value.name];return list(range(start,start+size))
    if not isinstance(value,ast.IndexExpression) or not isinstance(value.collection,ast.Identifier):
        raise ValueError('Expected a classical register or slice.')
    start,size=registers[value.collection.name];index=value.index
    if isinstance(index,ast.DiscreteSet):
        selected=[item.value for item in index.values]
    elif isinstance(index,list) and len(index)==1:
        item=index[0]
        if isinstance(item,ast.RangeDefinition):
            first=0 if item.start is None else item.start.value
            last=size-1 if item.end is None else item.end.value
            step=1 if item.step is None else item.step.value
            if not step or any(type(x) is not int for x in (first,last,step)) or not 0<=first<size or not 0<=last<size:
                raise ValueError('Invalid classical slice bounds.')
            selected=list(range(first,last+(1 if step>0 else -1),step))
        else:
            selected=[item.value]
    else:
        raise ValueError('Expected one classical index or slice.')
    if not selected or any(type(x) is not int or not 0<=x<size for x in selected):
        raise ValueError('Classical index is outside its register.')
    return [start+x for x in selected]


def classical_expression(value, registers, expected_width=None):
    operations={'&':'And','|':'Or','^':'Xor','<<':'ShiftLeft','>>':'ShiftRight',
                '==':'Equal','!=':'NotEqual','<':'Less','<=':'LessEqual','>':'Greater','>=':'GreaterEqual',
                '&&':'And','||':'Or'}
    comparisons={'==','!=','<','<=','>','>='}
    def width(node):
        if isinstance(node,(ast.Identifier,ast.IndexExpression)):return len(classical_indices(node,registers))
        if isinstance(node,ast.BitstringLiteral):return node.width
        if isinstance(node,ast.BooleanLiteral):return 1
        if isinstance(node,ast.UnaryExpression):return 1 if node.op.name=='!' else width(node.expression)
        if isinstance(node,ast.FunctionCall) and node.name.name in ('popcount','rotl','rotr'):
            if len(node.arguments)!=(1 if node.name.name=='popcount' else 2):raise ValueError('Wrong number of bit-function arguments.')
            return 64 if node.name.name=='popcount' else width(node.arguments[0])
        if isinstance(node,ast.BinaryExpression):
            if node.op.name in comparisons or node.op.name in ('&&','||'):return 1
            return width(node.lhs) or width(node.rhs)
        return None
    count=0
    def build(node,hint=None,depth=0):
        nonlocal count
        count+=1
        if count>512 or depth>=32:raise ValueError('Classical expressions exceed 512 nodes or 32 levels.')
        if isinstance(node,(ast.Identifier,ast.IndexExpression)):
            bits=classical_indices(node,registers);return {'Kind':'Read','Bits':bits},len(bits)
        if isinstance(node,(ast.IntegerLiteral,ast.BooleanLiteral,ast.BitstringLiteral)):
            value=int(node.value);size=width(node) or hint or max(1,value.bit_length())
            if not 1<=size<=64 or not 0<=value<(1<<size):raise ValueError('Classical constant does not fit its width.')
            return {'Kind':'Constant','Width':size,'Value':str(value)},size
        if isinstance(node,ast.FunctionCall) and node.name.name in ('popcount','rotl','rotr'):
            name=node.name.name
            if len(node.arguments)!=(1 if name=='popcount' else 2):raise ValueError('Wrong number of bit-function arguments.')
            operand,size=build(node.arguments[0],None if name=='popcount' else hint,depth+1)
            if name=='popcount':return {'Kind':'PopulationCount','Left':operand},64
            distance=node.arguments[1]
            if isinstance(distance,ast.IntegerLiteral):
                if not -(1<<63)<=distance.value<(1<<63):raise ValueError('Rotation distance must fit signed 64 bits.')
                encoded,dw=build(ast.IntegerLiteral(distance.value&((1<<64)-1)),64,depth+1);signed='Signed'
            elif isinstance(distance,ast.Cast) and isinstance(distance.type,(ast.IntType,ast.UintType)):
                encoded,dw=build(distance.argument,None,depth+1)
                if distance.type.size.value!=dw:raise ValueError('Bit-to-integer casts require matching widths.')
                signed='Signed' if isinstance(distance.type,ast.IntType) else 'Unsigned'
            elif isinstance(distance,ast.FunctionCall) and distance.name.name=='popcount':
                encoded,dw=build(distance,None,depth+1);signed='Unsigned'
            else:raise ValueError('Rotation distance requires an integer, popcount, or an explicit width-matched integer cast.')
            return {'Kind':'Rotate','RotationDirection':'Left' if name=='rotl' else 'Right','DistanceInterpretation':signed,'Left':operand,'Right':encoded},size
        if isinstance(node,ast.UnaryExpression) and node.op.name in ('~','!'):
            operand,size=build(node.expression,hint,depth+1)
            if node.op.name=='!' and size!=1:raise ValueError('Logical negation requires a one-bit value.')
            return {'Kind':'Complement','Left':operand},size
        if isinstance(node,ast.BinaryExpression) and node.op.name in operations:
            op=node.op.name;shift=op in ('<<','>>');logical=op in ('&&','||')
            size=1 if logical else width(node.lhs) or (None if shift else width(node.rhs)) or (None if op in comparisons else hint)
            left,lw=build(node.lhs,size,depth+1)
            right,rw=build(node.rhs,None if shift else lw,depth+1)
            if (not shift and lw!=rw) or (logical and lw!=1):raise ValueError('Classical operands have incompatible widths.')
            return {'Kind':'Logical' if logical else 'Binary','Operator':operations[op],'Left':left,'Right':right},1 if op in comparisons else lw
        raise ValueError('Unsupported classical bit expression: '+type(node).__name__)
    result,size=build(value,expected_width)
    if expected_width is not None and size!=expected_width:raise ValueError('Classical assignment or condition width mismatch.')
    return result


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
    if not 0 <= nq <= 25 or not 0 <= nc <= 64:
        raise ValueError('Classical circuits support 0–25 qubits and up to 64 classical bits.')

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
    version = 2
    def expression_version(node):
        if not isinstance(node,dict):return 3
        return max(4 if node.get('Kind')=='Logical' else 3,
                   expression_version(node.get('Left')),expression_version(node.get('Right')))
    def lower(body, depth=0):
        nonlocal count,version
        result = []
        def append(step):
            nonlocal count,version
            if 'ClassicalValue' in step:version=max(version,expression_version(step['ClassicalValue']))
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
            if isinstance(statement, ast.ClassicalAssignment):
                targets=classical_indices(statement.lvalue,classical)
                if len(set(targets))!=len(targets):raise ValueError('Assignment targets must be distinct.')
                append({'Kind':'Assign','Wires':targets,'ClassicalValue':classical_expression(statement.rvalue,classical,len(targets))})
            elif isinstance(statement, ast.BranchingStatement):
                if depth >= 32:
                    raise ValueError('Classical circuits support at most 32 nested branches.')
                condition = statement.condition
                simple = (isinstance(condition,(ast.Identifier,ast.IndexExpression)) or
                          isinstance(condition,ast.UnaryExpression) and condition.op.name=='!' or
                          isinstance(condition,ast.BinaryExpression) and condition.op.name in ('==','!=') and isinstance(condition.rhs,ast.IntegerLiteral))
                if not simple:
                    append({'Kind':'ExpressionBranch','ClassicalValue':classical_expression(condition,classical,1),
                            'WhenTrue':lower(statement.if_block,depth+1),'WhenFalse':lower(statement.else_block,depth+1)})
                    continue
                negate = False
                if isinstance(condition, ast.BinaryExpression) and condition.op.name in ('==', '!=') and isinstance(condition.rhs, ast.IntegerLiteral):
                    target, expected = condition.lhs, condition.rhs.value
                    negate = condition.op.name == '!='
                elif isinstance(condition, ast.UnaryExpression) and condition.op.name == '!':
                    target, expected = condition.expression, 0
                else:
                    target, expected = condition, 1
                try:
                    start, size = reference(target, classical, whole=True)
                except ValueError:
                    append({'Kind':'ExpressionBranch','ClassicalValue':classical_expression(condition,classical,1),
                            'WhenTrue':lower(statement.if_block,depth+1),'WhenFalse':lower(statement.else_block,depth+1)})
                    continue
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
    steps=lower(statements)
    return {'Version': version, 'Qubits': nq, 'Registers': named, 'OutputBits': list(reversed(range(nc))), 'Steps': steps}


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
