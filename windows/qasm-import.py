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

RUNTIME_SCALAR_TYPES=(ast.IntType,ast.UintType,ast.BoolType)


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
    runtime_integer_names={node.identifier.name for node in nodes(module.original_program)
                           if isinstance(node,ast.ClassicalDeclaration) and isinstance(node.type,RUNTIME_SCALAR_TYPES)}
    def integers(visitor):
        return getattr(visitor, '_quantum_integer_names', set())
    def runtime(visitor,value):
        return any(isinstance(item,ast.Identifier) and (item.name in visitor._global_creg_size_map or item.name in integers(visitor)) for item in nodes(value))
    def bit_function(value):
        return any(isinstance(item,ast.FunctionCall) and item.name.name in ('popcount','rotl','rotr') for item in nodes(value))
    def bitstring_boolean(value):
        return any(isinstance(item,ast.Cast) and isinstance(item.type,ast.BoolType) and any(isinstance(child,ast.BitstringLiteral) for child in nodes(item.argument)) for item in nodes(value))
    def normalize(visitor, value, depth=0, cast_distance=False, typed=False):
        typed=typed or any(isinstance(item,ast.Identifier) and item.name in integers(visitor) for item in nodes(value)) or (runtime(visitor,value) and any(isinstance(item,ast.Cast) and isinstance(item.type,(ast.IntType,ast.UintType)) for item in nodes(value)))
        if depth >= 32:
            raise ValueError('Classical expressions exceed 32 levels.')
        registers = visitor._global_creg_size_map
        if isinstance(value,ast.Identifier) and value.name in getattr(visitor,'_quantum_boolean_names',set()):
            result=ast.Cast(type=ast.BoolType(),argument=copy.deepcopy(value))
            result._quantum_boolean_value=True
            return result
        if isinstance(value, ast.Identifier) and (value.name in registers or value.name in integers(visitor)):
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
        if isinstance(value,ast.Cast) and isinstance(value.type,ast.BoolType) and (typed or runtime(visitor,value) or bit_function(value) or bitstring_boolean(value)):
            return ast.Cast(type=ast.BoolType(),argument=normalize(visitor,value.argument,depth+1,typed=typed))
        if isinstance(value,ast.Cast) and isinstance(value.type,(ast.IntType,ast.UintType,ast.BitType)) and (typed or cast_distance or runtime(visitor,value)):
            if isinstance(value.type,ast.BitType) and value.type.size is None:raise ValueError('Runtime bit-register casts require an explicit width.')
            if value.type.size is not None and runtime(visitor,value.type.size):raise ValueError("Integer cast widths must be compile-time constants.")
            size=0 if value.type.size is None else Qasm3ExprEvaluator.evaluate_expression(value.type.size)[0]
            if type(size) is not int or not 0<=size<=64 or (size==0 and value.type.size is not None):raise ValueError('Integer cast width must be 1–64.')
            argument=normalize(visitor,value.argument,depth+1,typed=typed)
            scalar=(isinstance(argument,ast.Identifier) and argument.name in getattr(visitor,'_quantum_scalar_bits',set()) or
                    isinstance(argument,ast.IndexExpression) and isinstance(argument.index,list) and
                    len(argument.index)==1 and isinstance(argument.index[0],ast.IntegerLiteral))
            if scalar and isinstance(value.type,(ast.IntType,ast.UintType)):
                # Scalar bits are Boolean values; bit[1] and one-element slices
                # remain registers and keep width-matched reinterpretation.
                argument=ast.Cast(type=ast.BoolType(),argument=argument)
            return ast.Cast(type=type(value.type)(size=ast.IntegerLiteral(size)),argument=argument)
        if isinstance(value, ast.BinaryExpression):
            if not typed and not runtime(visitor,value) and not bit_function(value) and not any(isinstance(item,ast.BitstringLiteral) for item in nodes(value)):
                result=Qasm3ExprEvaluator.evaluate_expression(value)[0]
                if type(result) not in (int,bool):raise ValueError('Expected an integer classical constant.')
                return ast.BooleanLiteral(result) if type(result) is bool else ast.IntegerLiteral(result)
            return ast.BinaryExpression(op=value.op, lhs=normalize(visitor,value.lhs,depth+1,typed=typed), rhs=normalize(visitor,value.rhs,depth+1,typed=typed))
        if isinstance(value, ast.UnaryExpression) and value.op.name in (('~','!','-') if typed else ('~','!')):
            return ast.UnaryExpression(op=value.op, expression=normalize(visitor,value.expression,depth+1,typed=typed))
        if isinstance(value, (ast.IntegerLiteral,ast.BooleanLiteral,ast.BitstringLiteral)):
            return copy.deepcopy(value)
        if runtime(visitor,value):
            raise ValueError('Unsupported runtime classical expression: '+type(value).__name__)
        result = Qasm3ExprEvaluator.evaluate_expression(value)[0]
        if type(result) not in (int,bool):
            raise ValueError('Classical bit expressions require integer or Boolean values.')
        return ast.IntegerLiteral(int(result))
    def assignment(visitor, statement):
        if getattr(statement,"_quantum_clear",False):
            return [] if visitor._check_only else [copy.deepcopy(statement)]
        name = statement.lvalue.name
        name = name.name if isinstance(name,ast.Identifier) else name
        integer_target = name in integers(visitor)
        if name not in visitor._global_creg_size_map and not integer_target:
            return original_assignment(visitor,statement)
        boolean_target=name in getattr(visitor,'_quantum_boolean_names',set())
        target = copy.deepcopy(statement.lvalue) if boolean_target else normalize(visitor,statement.lvalue)
        value = normalize(visitor,statement.rvalue,typed=integer_target)
        if boolean_target:
            if statement.op.name!='=':raise ValueError('Boolean compound assignments are not yet supported.')
            def implicit_boolean(item):
                if isinstance(item,ast.Identifier) and item.name in visitor._global_creg_size_map:
                    return item.name in getattr(visitor,'_quantum_scalar_bits',set())
                if isinstance(item,ast.BitstringLiteral):return False
                if isinstance(item,ast.IndexExpression):
                    return isinstance(item.index,list) and len(item.index)==1 and isinstance(item.index[0],ast.IntegerLiteral)
                if isinstance(item,ast.BinaryExpression) and item.op.name in ('&','|','^','<<','>>'):
                    return implicit_boolean(item.lhs) and (item.op.name in ('<<','>>') or implicit_boolean(item.rhs))
                if isinstance(item,ast.UnaryExpression) and item.op.name=='~':return implicit_boolean(item.expression)
                if isinstance(item,ast.FunctionCall) and item.name.name in ('rotl','rotr'):
                    return bool(item.arguments) and implicit_boolean(item.arguments[0])
                return True
            if not implicit_boolean(value):raise ValueError('Convert bit-register values explicitly with bool(...) before Boolean assignment.')
            converted=ast.Cast(type=ast.BoolType(),argument=value);converted._quantum_implicit_boolean=True
            value=ast.Cast(type=ast.UintType(size=ast.IntegerLiteral(1)),argument=converted)
        if statement.op.name != '=':
            operation = statement.op.name[:-1]
            if operation not in (('+','-','*','/','%','**') if integer_target else ('&','|','^','<<','>>')):
                raise ValueError('Unsupported classical assignment: '+statement.op.name)
            value = ast.BinaryExpression(op=ast.BinaryOperator[operation],lhs=copy.deepcopy(target),rhs=value)
        return [] if visitor._check_only else [ast.ClassicalAssignment(lvalue=target,op=ast.AssignmentOperator['='],rvalue=value)]
    def declaration(visitor, statement):
        if isinstance(statement.type,ast.BitType) and statement.type.size is None:
            visitor._quantum_scalar_bits=getattr(visitor,'_quantum_scalar_bits',set())|{statement.identifier.name}
        if isinstance(statement.type,RUNTIME_SCALAR_TYPES) and statement.identifier.name in runtime_integer_names:
            boolean=isinstance(statement.type,ast.BoolType)
            size = ast.IntegerLiteral(1) if boolean else statement.type.size
            if size is not None and runtime(visitor,size):raise ValueError('Integer widths must be compile-time constants.')
            width = 0 if size is None else Qasm3ExprEvaluator.evaluate_expression(size, const_expr=True)[0]
            if type(width) is not int or not 0<=width<=64 or (width==0 and size is not None):raise ValueError('Integer width must be 1–64, or omitted.')
            bare=copy.deepcopy(statement);bare.init_expression=None
            # Let the compiler validate the declaration and register its name,
            # but keep the value undefined for the runtime interpreter.
            original_declaration(visitor,bare)
            visitor._quantum_integer_names=integers(visitor)|{statement.identifier.name}
            if boolean:
                visitor._quantum_boolean_names=getattr(visitor,'_quantum_boolean_names',set())|{statement.identifier.name}
                bare.type=ast.UintType()
            bare.type.size=ast.IntegerLiteral(width)
            result=[] if visitor._check_only else [bare]
            if statement.init_expression is not None:
                result+=assignment(visitor,ast.ClassicalAssignment(lvalue=copy.deepcopy(statement.identifier),op=ast.AssignmentOperator['='],rvalue=statement.init_expression))
            return result
        if not isinstance(statement.type,ast.BitType) or statement.init_expression is None or isinstance(statement.init_expression,ast.QuantumMeasurement):
            return original_declaration(visitor,statement)
        bare = copy.deepcopy(statement);bare.init_expression=None
        result = original_declaration(visitor,bare)
        initial = ast.ClassicalAssignment(lvalue=copy.deepcopy(statement.identifier),op=ast.AssignmentOperator['='],rvalue=statement.init_expression)
        return result+assignment(visitor,initial)
    def branch(visitor, statement):
        if not runtime(visitor,statement.condition) and not bit_function(statement.condition) and not bitstring_boolean(statement.condition):
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


def resolve_integer_scopes(program):
    """Give locals unique slots and preserve explicit scope-exit clears through unrolling.

    The compiler may flatten constant blocks and repeat loop bodies. Unique names
    prevent capture; clear markers retain lifetime boundaries after that flattening.
    Markers are private AST attributes, never syntax accepted from input text.
    """
    if not any(isinstance(node,ast.ClassicalDeclaration) and isinstance(node.type,RUNTIME_SCALAR_TYPES) for node in nodes(program)):return set()
    used={node.name for node in nodes(program) if isinstance(node,ast.Identifier)}
    scoped=set();serial=0
    def fresh(name):
        nonlocal serial
        base=name
        while len(base.encode('utf-16-le'))//2>44:base=base[:-1]
        while True:
            serial+=1;candidate=base+'_scope_'+str(serial)
            if candidate not in used:used.add(candidate);return candidate
    def expression(value,env):
        if isinstance(value,ast.Identifier):value.name=env.get(value.name,value.name)
        elif isinstance(value,list):
            for item in value:expression(item,env)
        elif is_dataclass(value):
            for field in fields(value):
                if field.name not in ('span','annotations') and not (isinstance(value,ast.FunctionCall) and field.name=='name'):
                    expression(getattr(value,field.name),env)
    def clear(name):
        result=ast.ClassicalAssignment(lvalue=ast.Identifier(name),op=ast.AssignmentOperator['='],rvalue=ast.IntegerLiteral(0))
        result._quantum_clear=True
        return result
    def block(body,parent,depth=0,declared=None):
        if depth>32:raise ValueError('Classical scopes exceed 32 levels.')
        env=dict(parent);declared=set() if declared is None else set(declared);local=[];result=[]
        for statement in body:
            if isinstance(statement,(ast.ClassicalDeclaration,ast.ConstantDeclaration)):
                name=statement.identifier.name
                if name in declared:raise ValueError('Duplicate declaration in one scope: '+name)
                declared.add(name);integer=isinstance(statement,ast.ClassicalDeclaration) and isinstance(statement.type,RUNTIME_SCALAR_TYPES)
                if depth and name in env and not integer:raise ValueError('Non-integer shadowing is not yet supported by the importer.')
                expression(statement.type,env)
                renamed=fresh(name) if depth and (integer or isinstance(statement,ast.ConstantDeclaration)) else name
                if integer:
                    if len(name.encode('utf-16-le'))//2>64:raise ValueError('Integer variable names must fit 64 UTF-16 code units.')
                    statement._quantum_scoped=depth>0
                    env[name]=renamed
                    if depth:scoped.add(renamed);local.append(renamed)
                expression(statement.init_expression,env)
                statement.identifier.name=renamed;env[name]=renamed
                result.append(statement)
            elif isinstance(statement,ast.BranchingStatement):
                expression(statement.condition,env)
                block(statement.if_block,env,depth+1);block(statement.else_block,env,depth+1)
                result.append(statement)
            elif isinstance(statement,ast.ForInLoop):
                expression(statement.type,env);expression(statement.set_declaration,env)
                name=statement.identifier.name;renamed=fresh(name) if name in env else name
                statement.identifier.name=renamed;inner=dict(env);inner[name]=renamed
                block(statement.block,inner,depth+1,{name});result.append(statement)
            elif isinstance(statement,ast.CompoundStatement):
                block(statement.statements,env,depth+1);result.extend(statement.statements)
            elif isinstance(statement,(ast.QuantumGateDefinition,ast.SubroutineDefinition)):
                if any(isinstance(item,ast.ClassicalDeclaration) and isinstance(item.type,RUNTIME_SCALAR_TYPES) for item in nodes(statement)):
                    raise ValueError('Integer declarations in subroutines require activation storage not yet supported.')
                result.append(statement)
            else:
                if any(isinstance(item,ast.ClassicalDeclaration) and isinstance(item.type,RUNTIME_SCALAR_TYPES) for item in nodes(statement)):
                    raise ValueError('Integer declarations in this control structure are not yet supported.')
                if isinstance(statement,ast.QuantumGate):
                    expression(statement.arguments,env);expression(statement.modifiers,env);expression(statement.qubits,env)
                elif isinstance(statement,ast.QubitDeclaration):
                    expression(statement.size,env)
                else:expression(statement,env)
                result.append(statement)
        result.extend(clear(name) for name in reversed(local));body[:]=result
    block(program.statements,{})
    if scoped and any(isinstance(item,(ast.BreakStatement,ast.ContinueStatement)) for item in nodes(program)):
        raise ValueError('Break and continue with scoped integers require lifetime-aware control flow not yet supported.')
    return scoped


def number(value):
    if not isinstance(value, (ast.IntegerLiteral, ast.FloatLiteral)):
        raise ValueError('An unresolved gate parameter remains after compilation.')
    if not math.isfinite(value.value):
        raise ValueError('Gate parameters must be finite.')
    return format(value.value, '.17g')


def lower_boolean_measurements(program):
    """Reuse one temporary measurement bit, copying each outcome into storage.

    The temporary is omitted from published outputs; Boolean variables keep
    independent values even after subsequent measurements overwrite the bit.
    """
    booleans={n.identifier.name for n in nodes(program) if isinstance(n,ast.ClassicalDeclaration) and isinstance(n.type,ast.BoolType)}
    if not booleans:return set()
    used={n.name for n in nodes(program) if isinstance(n,ast.Identifier)}
    name='_boolean_measurement';serial=0
    while name in used:serial+=1;name='_boolean_measurement_'+str(serial)
    changed=False
    def block(body):
        nonlocal changed
        result=[]
        for statement in body:
            target=None;measurement=None
            if isinstance(statement,ast.ClassicalDeclaration) and isinstance(statement.type,ast.BoolType) and isinstance(statement.init_expression,ast.QuantumMeasurement):
                target=copy.deepcopy(statement.identifier)
                measurement=ast.QuantumMeasurementStatement(measure=statement.init_expression,target=ast.Identifier(name))
                statement.init_expression=None;result.append(statement)
            elif isinstance(statement,ast.QuantumMeasurementStatement) and isinstance(statement.target,ast.Identifier) and statement.target.name in booleans:
                target=copy.deepcopy(statement.target);measurement=copy.deepcopy(statement);measurement.target=ast.Identifier(name)
            if measurement is not None:
                changed=True;result.append(measurement)
                result.append(ast.ClassicalAssignment(lvalue=target,op=ast.AssignmentOperator['='],rvalue=ast.Identifier(name)))
                continue
            if isinstance(statement,ast.BranchingStatement):block(statement.if_block);block(statement.else_block)
            elif isinstance(statement,ast.ForInLoop):block(statement.block)
            elif isinstance(statement,ast.CompoundStatement):block(statement.statements)
            result.append(statement)
        body[:]=result
    block(program.statements)
    if not changed:return set()
    program.statements.insert(0,ast.ClassicalDeclaration(type=ast.BitType(),identifier=ast.Identifier(name)))
    return {name}


def convert(source, published_u=False, classical=False):
    if len(source.encode('utf-8')) > 262144:
        raise ValueError('OpenQASM input must be at most 256 KB.')
    module = pyqasm.loads(source)
    hidden_registers=set()
    if classical:
        resolve_integer_scopes(module.original_program)
        hidden_registers=lower_boolean_measurements(module.original_program)
    if classical:
        runtime_names={node.identifier.name for node in nodes(module.original_program)
                   if isinstance(node,ast.ClassicalDeclaration) and isinstance(node.type,(ast.BitType,)+RUNTIME_SCALAR_TYPES)}
        def runtime(value):
            return any(isinstance(item,ast.Identifier) and item.name in runtime_names for item in nodes(value))
        integer_names={node.identifier.name for node in module.original_program.statements
                       if isinstance(node,ast.ClassicalDeclaration) and isinstance(node.type,RUNTIME_SCALAR_TYPES)}
        for node in nodes(module.original_program):
            if isinstance(node,ast.ForInLoop) and node.identifier.name in integer_names:
                raise ValueError('Loop variables cannot yet shadow runtime integer variables.')
            if isinstance(node,ast.SubroutineDefinition) and any(isinstance(item,ast.Identifier) and item.name in integer_names for item in nodes(node)):
                raise ValueError('Runtime integer variables in subroutines require scoped lowering not yet supported.')
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
            if not isinstance(node.type, (ast.BitType,)+RUNTIME_SCALAR_TYPES):
                raise ValueError('Classical circuit import supports bit registers and integer/Boolean variables; other classical declarations are not yet supported.')
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
        return classical_circuit(statements, published_u, hidden_registers)
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


def classical_expression(value, registers, expected_width=None, variables=None, integer_only=False):
    variables=variables or {}
    operations={'&':'And','|':'Or','^':'Xor','<<':'ShiftLeft','>>':'ShiftRight',
                '==':'Equal','!=':'NotEqual','<':'Less','<=':'LessEqual','>':'Greater','>=':'GreaterEqual',
                '&&':'And','||':'Or'}
    comparisons={'==','!=','<','<=','>','>='}
    def width(node):
        if isinstance(node,ast.Identifier) and node.name in variables:
            raise ValueError("Convert integer variables explicitly with bool(...) or bit[n](...) before using them as bits.")
        if isinstance(node,ast.Cast) and isinstance(node.type,ast.BoolType):return 1
        if isinstance(node,ast.Cast) and isinstance(node.type,ast.BitType):return node.type.size.value
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
    arithmetic={'+':'Add','-':'Subtract','*':'Multiply','/':'Divide','%':'Remainder','**':'Power'}
    def integer_value(node):
        return (getattr(node,'_quantum_boolean_value',False) or isinstance(node,ast.Identifier) and node.name in variables or
                isinstance(node,ast.Cast) and isinstance(node.type,(ast.IntType,ast.UintType)) or
                isinstance(node,ast.BinaryExpression) and node.op.name in arithmetic or
                isinstance(node,ast.UnaryExpression) and node.op.name=='-')
    def integer_type(node):
        if node['Kind']!='IntegerBinary':return node['Signedness'],node['Width']
        # Match the runtime's arithmetic promotion: only unsigned 64-bit
        # operands require an unsigned machine result; narrower values fit int.
        operands=[integer_type(node[key]) for key in ('Left','Right')]
        return ('Unsigned' if any(sign=='Unsigned' and (size or 64)==64 for sign,size in operands) else 'Signed'),0
    def bound(depth):
        nonlocal count
        count+=1
        if count>512 or depth>=32:raise ValueError('Classical expressions exceed 512 nodes or 32 levels.')
    def integer(node,depth):
        bound(depth)
        if isinstance(node,ast.Cast) and isinstance(node.type,ast.BoolType):
            child,size=build(node,None,depth+1)
            if size!=1:raise ValueError('Boolean values require one bit.')
            return {'Kind':'IntegerFromBits','Signedness':'Unsigned','Width':1,'Left':child}
        if isinstance(node,ast.Identifier) and node.name in variables:
            slot,sign,size=variables[node.name]
            return {'Kind':'IntegerVariable','Slot':slot,'Signedness':sign,'Width':size}
        if isinstance(node,(ast.IntegerLiteral,ast.BooleanLiteral)):
            value=int(node.value) if isinstance(node,ast.BooleanLiteral) else node.value
            if type(value) is not int or not -(1<<63)<=value<(1<<64):raise ValueError('Integer literal exceeds 64 bits.')
            return {'Kind':'IntegerConstant','Signedness':'Signed' if value<(1<<63) else 'Unsigned','Width':0,'Value':str(value&((1<<64)-1))}
        if isinstance(node,ast.Cast) and isinstance(node.type,(ast.IntType,ast.UintType)):
            size=node.type.size.value;storage=size or 64
            if type(size) is not int or not 0<=size<=64:raise ValueError('Invalid integer cast width.')
            sign='Signed' if isinstance(node.type,ast.IntType) else 'Unsigned'
            boolean=(isinstance(node.argument,ast.Cast) and isinstance(node.argument.type,ast.BoolType) or
                     isinstance(node.argument,ast.BinaryExpression) and node.argument.op.name in comparisons|{'&&','||'} or
                     isinstance(node.argument,ast.UnaryExpression) and node.argument.op.name=='!')
            if boolean:
                # Booleans convert numerically (true -> +1), unlike bit-vector
                # reinterpretation. Count the intermediate unsigned one-bit node.
                bound(depth+1)
                child,child_width=build(node.argument,1,depth+2)
                if child_width!=1:raise ValueError('Boolean conversion requires one bit.')
                return {'Kind':'IntegerCast','Signedness':sign,'Width':size,'Left':{
                    'Kind':'IntegerFromBits','Signedness':'Unsigned','Width':1,'Left':child}}
            if isinstance(node.argument,(ast.Identifier,ast.IndexExpression)) and not integer_value(node.argument):
                bits=classical_indices(node.argument,registers)
                if len(bits)!=storage:raise ValueError('Bit-to-integer casts require matching widths.')
                return {'Kind':'IntegerRead','Signedness':sign,'Width':size,'Bits':bits}
            if isinstance(node.argument,ast.BitstringLiteral):
                if node.argument.width!=storage:raise ValueError('Bit-to-integer casts require matching widths.')
                return {'Kind':'IntegerConstant','Signedness':sign,'Width':size,'Value':str(node.argument.value)}
            if not integer_value(node.argument) and not isinstance(node.argument,(ast.IntegerLiteral,ast.BooleanLiteral)):
                child,child_width=build(node.argument,storage,depth+1)
                if child_width!=storage:raise ValueError('Bit-to-integer casts require matching widths.')
                return {'Kind':'IntegerFromBits','Signedness':sign,'Width':size,'Left':child}
            return {'Kind':'IntegerCast','Signedness':sign,'Width':size,'Left':integer(node.argument,depth+1)}
        if isinstance(node,ast.UnaryExpression) and node.op.name=='-':
            if isinstance(node.expression,ast.IntegerLiteral):
                magnitude=node.expression.value
                if type(magnitude) is not int or not 0<=magnitude<=(1<<63):raise ValueError('Negative literals must fit signed 64 bits.')
                return {'Kind':'IntegerConstant','Signedness':'Signed','Width':0,'Value':str((-magnitude)&((1<<64)-1))}
            return {'Kind':'IntegerBinary','Operator':'Subtract','Left':integer(ast.IntegerLiteral(0),depth+1),'Right':integer(node.expression,depth+1)}
        if isinstance(node,ast.BinaryExpression) and node.op.name in arithmetic:
            return {'Kind':'IntegerBinary','Operator':arithmetic[node.op.name],'Left':integer(node.lhs,depth+1),'Right':integer(node.rhs,depth+1)}
        raise ValueError('Cast bit operands explicitly before integer arithmetic.')
    def build(node,hint=None,depth=0):
        bound(depth)
        if isinstance(node,ast.Cast) and isinstance(node.type,ast.BoolType):
            # Expand into the existing comparison model; count the added zero.
            bound(depth+1)
            if integer_value(node.argument):
                return {'Kind':'IntegerCompare','Operator':'NotEqual','Left':integer(node.argument,depth+1),'Right':{'Kind':'IntegerConstant','Signedness':'Signed','Width':0,'Value':'0'}},1
            child,size=build(node.argument,None,depth+1)
            if getattr(node,'_quantum_implicit_boolean',False) and size!=1 and not (isinstance(node.argument,ast.IntegerLiteral) or isinstance(node.argument,ast.FunctionCall) and node.argument.name.name=='popcount'):
                raise ValueError('Convert bit expressions explicitly with bool(...) before Boolean assignment.')
            return {'Kind':'Binary','Operator':'NotEqual','Left':child,'Right':{'Kind':'Constant','Width':size,'Value':'0'}},1
        if isinstance(node,ast.Cast) and isinstance(node.type,ast.BitType):
            size=node.type.size.value;child=integer(node.argument,depth+1)
            if type(size) is not int or not 1<=size<=64 or child.get('Width')!=size:raise ValueError('Integer-to-bit casts require equal explicit widths.')
            return {'Kind':'IntegerBits','Left':child},size
        if isinstance(node,ast.BinaryExpression) and node.op.name in comparisons and (integer_value(node.lhs) or integer_value(node.rhs)):
            return {'Kind':'IntegerCompare','Operator':operations[node.op.name],'Left':integer(node.lhs,depth+1),'Right':integer(node.rhs,depth+1)},1
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
            elif (isinstance(distance,ast.Cast) and isinstance(distance.type,(ast.IntType,ast.UintType)) and
                  isinstance(distance.argument,(ast.Identifier,ast.IndexExpression,ast.BitstringLiteral)) and not integer_value(distance.argument)):
                encoded,dw=build(distance.argument,None,depth+1)
                if distance.type.size.value!=dw:raise ValueError('Bit-to-integer casts require matching widths.')
                signed='Signed' if isinstance(distance.type,ast.IntType) else 'Unsigned'
            elif integer_value(distance):
                # The bit-rotation engine consumes a bit pattern plus sign.
                # Explicitly size the value without changing its numeric value.
                bound(depth+1);bound(depth+2)
                child=integer(distance,depth+3);signed,_=integer_type(child)
                encoded={'Kind':'IntegerBits','Left':{'Kind':'IntegerCast','Signedness':signed,'Width':64,'Left':child}}
            elif isinstance(distance,ast.FunctionCall) and distance.name.name=='popcount':
                encoded,dw=build(distance,None,depth+1);signed='Unsigned'
            else:raise ValueError('Rotation distance requires an integer expression, popcount, or an explicit integer cast.')
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
    if integer_only:return integer(value,0)
    result,size=build(value,expected_width)
    if expected_width is not None and size!=expected_width:raise ValueError('Classical assignment or condition width mismatch.')
    return result


def classical_circuit(statements, published_u, hidden_registers=None):
    hidden_registers=hidden_registers or set()
    quantum, classical, named = {}, {}, []
    variables, declarations = {}, []
    nq = nc = 0
    declarations_in_order=list(nodes(statements))
    # Allocate generated bits last so original register indices do not move.
    declarations_in_order.sort(key=lambda n:isinstance(n,ast.ClassicalDeclaration) and n.identifier.name in hidden_registers)
    for statement in declarations_in_order:
        if isinstance(statement, ast.QubitDeclaration):
            size = 1 if statement.size is None else statement.size.value
            quantum[statement.qubit.name] = (nq, size)
            nq += size
        elif isinstance(statement, ast.ClassicalDeclaration):
            if isinstance(statement.type,(ast.IntType,ast.UintType)):
                name=statement.identifier.name;size=statement.type.size.value
                sign='Signed' if isinstance(statement.type,ast.IntType) else 'Unsigned'
                if len(name.encode('utf-16-le'))//2>64:raise ValueError('Integer variable names must fit 64 UTF-16 code units.')
                if name in variables:
                    if variables[name][1:]!=(sign,size):raise ValueError('Inconsistent repeated integer declaration.')
                    continue
                if len(variables)>=4096:raise ValueError('Excessive integer declarations.')
                variables[name]=(len(variables),sign,size)
                declarations.append({'Name':name,'Signedness':sign,'Width':size})
                continue
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
    version = 5 if declarations else 2
    def expression_version(node):
        if not isinstance(node,dict):return 3
        return max(6 if node.get('Kind')=='IntegerFromBits' else 4 if node.get('Kind')=='Logical' or node.get('Kind','').startswith('Integer') else 3,
                   expression_version(node.get('Left')),expression_version(node.get('Right')))
    def lower(body, depth=0):
        nonlocal count,version
        result = []
        def append(step):
            nonlocal count,version
            if 'ClassicalValue' in step:version=max(version,expression_version(step['ClassicalValue']))
            if 'IntegerValue' in step:version=max(version,expression_version(step['IntegerValue']))
            count += 1
            if count > 512:
                raise ValueError('Classical circuits support at most 512 total operations.')
            result.append(step)
        for statement in body:
            if isinstance(statement, (ast.Include, ast.QuantumBarrier)):
                continue
            if isinstance(statement,ast.ClassicalDeclaration) and isinstance(statement.type,(ast.IntType,ast.UintType)):
                if getattr(statement,'_quantum_scoped',False):append({'Kind':'ClearInteger','VariableSlot':variables[statement.identifier.name][0]})
                continue
            if isinstance(statement, (ast.QubitDeclaration, ast.ClassicalDeclaration)):
                if depth:
                    raise ValueError('Register declarations inside runtime branches are not supported.')
                continue
            if isinstance(statement, ast.ClassicalAssignment):
                if getattr(statement,'_quantum_clear',False):
                    append({'Kind':'ClearInteger','VariableSlot':variables[statement.lvalue.name][0]})
                    continue
                if isinstance(statement.lvalue,ast.Identifier) and statement.lvalue.name in variables:
                    append({'Kind':'StoreInteger','VariableSlot':variables[statement.lvalue.name][0],
                            'IntegerValue':classical_expression(statement.rvalue,classical,variables=variables,integer_only=True)})
                    continue
                targets=classical_indices(statement.lvalue,classical)
                if len(set(targets))!=len(targets):raise ValueError('Assignment targets must be distinct.')
                append({'Kind':'Assign','Wires':targets,'ClassicalValue':classical_expression(statement.rvalue,classical,len(targets),variables)})
            elif isinstance(statement, ast.BranchingStatement):
                if depth >= 32:
                    raise ValueError('Classical circuits support at most 32 nested branches.')
                condition = statement.condition
                simple = (isinstance(condition,(ast.Identifier,ast.IndexExpression)) or
                          isinstance(condition,ast.UnaryExpression) and condition.op.name=='!' or
                          isinstance(condition,ast.BinaryExpression) and condition.op.name in ('==','!=') and isinstance(condition.rhs,ast.IntegerLiteral))
                simple=simple and not any(isinstance(item,ast.Identifier) and item.name in variables for item in nodes(condition))
                if not simple:
                    append({'Kind':'ExpressionBranch','ClassicalValue':classical_expression(condition,classical,1,variables),
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
                    append({'Kind':'ExpressionBranch','ClassicalValue':classical_expression(condition,classical,1,variables),
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
    visible_bits=[bit for name,(start,size) in classical.items() if name not in hidden_registers for bit in range(start,start+size)]
    result={'Version': version, 'Qubits': nq, 'Registers': named, 'OutputBits': list(reversed(visible_bits)), 'Steps': steps}
    if declarations or version>=6:result['Variables']=declarations
    return result


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
