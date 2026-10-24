"""Lower bounded runtime calls to lexical blocks consumed by scope lowering.

Scalar arguments are snapshots, quantum arguments are references. No interpreter
state is stored here: the existing runtime declarations own initialization and
scope-exit cleanup, including a call repeated inside a runtime loop.
"""
import copy
from dataclasses import fields, is_dataclass
import openqasm3.ast as ast
from pyqasm.maps.expressions import CONSTANTS_MAP
from qasm_source_diagnostics import error_at


def lower_runtime_subroutines(program):
    scalar = (ast.IntType, ast.UintType, ast.BoolType)
    values = scalar + (ast.BitType,)

    def walk(value):
        if is_dataclass(value):
            yield value
            for field in fields(value):
                if field.name not in ('span', 'annotations'):
                    yield from walk(getattr(value, field.name))
        elif isinstance(value, (list, tuple)):
            for item in value:
                yield from walk(item)

    functions = {}; visibility = {}; activations = []
    constants = {}; constant_cache = {}
    used = {node.name for node in walk(program) if isinstance(node, ast.Identifier)}
    runtime = set()
    registers = {}
    bit_storage = []
    serial = calls = expanded = copied_nodes = 0

    def fresh():
        nonlocal serial
        while True:
            serial += 1
            name = '_qcall_' + str(serial)
            if name not in used:
                used.add(name)
                return name

    def rewrite(value, bindings, lexical=None):
        nonlocal copied_nodes
        if lexical is None:
            lexical = bool(activations)
        if isinstance(value, ast.Identifier):
            if lexical and value.name not in bindings and value.name not in CONSTANTS_MAP:
                raise error_at(value, 'Name is not visible in this subroutine scope: ' + value.name)
            bound = bindings.get(value.name, value)
            copied_nodes += sum(1 for _ in walk(bound))
            if copied_nodes > 65536:
                raise error_at(value, 'Runtime subroutine binding expansion exceeds 65536 AST nodes.')
            return copy.deepcopy(bound)
        if isinstance(value, ast.IndexedIdentifier) and isinstance(bindings.get(value.name.name), ast.IndexedIdentifier):
            raise error_at(value, 'Runtime calls currently require scalar quantum parameters without indexing.')
        if isinstance(value, list):
            return [rewrite(item, bindings, lexical) for item in value]
        if isinstance(value, tuple):
            return tuple(rewrite(item, bindings, lexical) for item in value)
        if is_dataclass(value):
            result = copy.copy(value)
            for field in fields(value):
                if field.name in ('span', 'annotations') or (field.name == 'name' and isinstance(value, (ast.FunctionCall, ast.QuantumGate))):
                    continue
                setattr(result, field.name, rewrite(getattr(value, field.name), bindings, lexical))
            return result
        return value

    def constant_value(name, depth=0):
        if name in constant_cache:
            return constant_cache[name]
        if depth >= 32:
            raise error_at(constants[name][1], 'Runtime constant bindings exceed 32 nesting levels.')
        position, declaration = constants[name]
        dependencies = {n.name for n in walk(declaration) if isinstance(n, ast.Identifier)}
        bindings = {key: constant_value(key, depth + 1) for key in dependencies
                    if key in constants and constants[key][0] < position}
        result = ast.Cast(type=rewrite(declaration.type, bindings, lexical=True),
                          argument=rewrite(declaration.init_expression, bindings, lexical=True))
        constant_cache[name] = result
        return result

    def quantum_key(value):
        if isinstance(value, ast.IndexExpression) and isinstance(value.collection, ast.Identifier):
            value = ast.IndexedIdentifier(name=value.collection, indices=[value.index])
        if isinstance(value, ast.Identifier) and registers.get(value.name) == 1:
            return value.name, 0
        if isinstance(value, ast.IndexedIdentifier) and len(value.indices) == 1 and len(value.indices[0]) == 1:
            index = value.indices[0][0]
            size = registers.get(value.name.name)
            if isinstance(index, ast.IntegerLiteral) and size is not None and 0 <= index.value < size:
                return value.name.name, index.value
        raise error_at(value, 'Runtime call quantum arguments require a scalar qubit or a fixed literal register index.')

    def activate(call, depth):
        nonlocal calls, expanded
        if activations and visibility[call.name.name] > activations[-1]:
            raise error_at(call, 'A subroutine can only call previously declared routines or itself.')
        if depth >= 32:
            raise error_at(call, 'Subroutine call nesting exceeds 32 levels.')
        calls += 1
        if calls > 4096:
            raise error_at(call, 'Subroutine expansion exceeds 4096 calls.')
        definition = functions[call.name.name]
        expanded += sum(1 for _ in walk(definition.body))
        if expanded > 65536:
            raise error_at(call, 'Runtime subroutine expansion exceeds 65536 AST nodes.')
        if definition.return_type is not None and not isinstance(definition.return_type, values):
            raise error_at(call, 'Runtime return values currently support integers, Booleans and bit registers.')
        returns = [n for n in walk(definition.body) if isinstance(n, ast.ReturnStatement)]
        # Validate before control-flow lowering drops unreachable tails.
        for statement in returns:
            if definition.return_type is None and statement.expression is not None:
                raise error_at(statement, 'A void subroutine cannot return a value.')
            if definition.return_type is not None and statement.expression is None:
                raise error_at(statement, 'A typed subroutine must return a value.')
        has_return = bool(returns)
        if len(call.arguments) != len(definition.arguments):
            raise error_at(call, 'Subroutine argument count does not match its declaration.')
        references = {n.name for n in walk(definition) if isinstance(n, ast.Identifier)}
        constant_bindings = {name: constant_value(name) for name in references
                             if name in constants and constants[name][0] < visibility[call.name.name]}
        bindings = dict(constant_bindings)
        parameters = set(); declarations = []; qubits = set()
        for formal, actual in zip(definition.arguments, call.arguments):
            name = formal.name.name
            if name in parameters:
                raise error_at(formal, 'Duplicate subroutine parameter: ' + name)
            parameters.add(name)
            if isinstance(formal, ast.QuantumArgument):
                if formal.size is not None:
                    raise error_at(formal, 'Runtime calls currently require scalar quantum parameters.')
                key = quantum_key(actual)
                if key in qubits:
                    raise error_at(call, 'Quantum subroutine arguments must not overlap.')
                qubits.add(key)
                bindings[name] = ast.IndexedIdentifier(name=ast.Identifier(key[0]), indices=[[ast.IntegerLiteral(key[1])]])
            elif isinstance(formal, ast.ClassicalArgument) and isinstance(formal.type, values):
                if formal.access is not None:
                    raise error_at(formal, 'Runtime scalar arguments are passed by value.')
                slot = ast.Identifier(fresh())
                # Actual expressions stay in the caller environment; never bind
                # an initializer to the newly introduced formal of the same name.
                declared_type = rewrite(formal.type, constant_bindings, lexical=True)
                declaration = ast.ClassicalDeclaration(type=declared_type, identifier=slot, init_expression=copy.deepcopy(actual))
                declarations.append(bit_declaration(declaration) if isinstance(declared_type, ast.BitType) else declaration)
                bindings[name] = slot
            else:
                raise error_at(formal, 'Runtime call arguments currently support integers, Booleans and bit registers.')
        result_slot = None; result_type = None; prefix = []
        if definition.return_type is not None:
            result_type = rewrite(definition.return_type, constant_bindings, lexical=True)
            if isinstance(result_type, ast.BitType) and result_type.size is None:
                result_type.size = ast.IntegerLiteral(1)
            result_slot = ast.Identifier(fresh())
            # Integer storage preserves an undefined result on missing-return
            # paths. Bit storage would silently initialize that result to zero.
            storage_type = copy.deepcopy(result_type)
            if isinstance(storage_type, ast.BitType):
                storage_type = ast.UintType(size=storage_type.size or ast.IntegerLiteral(1))
            prefix.append(ast.ClassicalDeclaration(type=storage_type, identifier=result_slot, init_expression=None))
            runtime.add(result_slot.name)
        activations.append(visibility[call.name.name])
        try:
            body = block(definition.body, bindings, True, depth + 1, parameters)
        finally:
            activations.pop()
        if has_return:
            returned = ast.Identifier(fresh())
            declarations.append(ast.ClassicalDeclaration(type=ast.BoolType(), identifier=returned, init_expression=ast.BooleanLiteral(False)))
            body, _ = return_control(body, returned, result_slot=result_slot, result_type=result_type)
        prefix.append(ast.CompoundStatement(statements=declarations + body))
        if result_slot is not None:
            # Also detect a missing return when the caller discards the value.
            prefix.append(ast.ClassicalAssignment(lvalue=copy.deepcopy(result_slot), op=ast.AssignmentOperator['='], rvalue=copy.deepcopy(result_slot)))
            return prefix, ast.Cast(type=result_type, argument=copy.deepcopy(result_slot))
        return prefix, None

    def return_control(body, returned, level=0, result_slot=None, result_type=None):
        """Exit an activation without introducing an extra budgeted loop.

        Keep each remaining tail together under its guard, so declarations in
        that tail stay visible to later statements. Loop transfers and integer
        cleanup are subsequently handled by their existing lowering passes.
        """
        if level >= 32:
            raise error_at(returned, 'Return control exceeds 32 levels of nesting.')
        result = []
        def child_control(items):
            return return_control(items, returned, level + 1, result_slot, result_type)
        for index, node in enumerate(body):
            if isinstance(node, ast.ReturnStatement):
                if result_slot is not None:
                    expression = node.expression
                    if isinstance(expression, ast.QuantumMeasurement):
                        measured = ast.Identifier(fresh())
                        bit_storage.append(ast.ClassicalDeclaration(type=copy.deepcopy(result_type) if isinstance(result_type, ast.BitType) else ast.BitType(), identifier=measured, init_expression=None))
                        result.append(ast.QuantumMeasurementStatement(measure=expression, target=measured))
                        expression = measured
                    converted = ast.Cast(type=copy.deepcopy(result_type), argument=expression)
                    if isinstance(result_type, ast.BitType):
                        converted = ast.Cast(type=ast.UintType(size=copy.deepcopy(result_type.size)), argument=expression)
                    result.append(ast.ClassicalAssignment(lvalue=copy.deepcopy(result_slot), op=ast.AssignmentOperator['='], rvalue=converted))
                result.append(ast.ClassicalAssignment(lvalue=copy.deepcopy(returned), op=ast.AssignmentOperator['='], rvalue=ast.BooleanLiteral(True)))
                return result, True
            may_return = False
            if isinstance(node, ast.BranchingStatement):
                node.if_block, left = child_control(node.if_block)
                node.else_block, right = child_control(node.else_block)
                may_return = left or right
            elif isinstance(node, ast.CompoundStatement):
                node.statements, may_return = child_control(node.statements)
            elif isinstance(node, ast.SwitchStatement):
                for _, case in node.cases:
                    case.statements, child = child_control(case.statements)
                    may_return |= child
                if node.default is not None:
                    node.default.statements, child = child_control(node.default.statements)
                    may_return |= child
            elif isinstance(node, (ast.ForInLoop, ast.WhileLoop)):
                node.block, may_return = child_control(node.block)
                if may_return:
                    node.block.append(ast.BranchingStatement(condition=copy.deepcopy(returned), if_block=[ast.BreakStatement()], else_block=[]))
            result.append(node)
            if may_return:
                tail, _ = child_control(body[index + 1:])
                if tail:
                    condition = ast.UnaryExpression(op=ast.UnaryOperator['!'], expression=copy.deepcopy(returned))
                    result.append(ast.BranchingStatement(condition=condition, if_block=tail, else_block=[]))
                return result, True
        return result, False

    def bit_declaration(declaration):
        # Allocate storage once, but initialize on every activation, including
        # runtime-loop re-entry. Generated bits are never implicit outputs.
        bare = copy.deepcopy(declaration); bare.init_expression = None
        bit_storage.append(bare)
        initial = declaration.init_expression
        if isinstance(initial, ast.QuantumMeasurement):
            return ast.QuantumMeasurementStatement(measure=initial, target=declaration.identifier)
        if initial is None:
            target_type = copy.deepcopy(declaration.type)
            if target_type.size is None: target_type.size = ast.IntegerLiteral(1)
            initial = ast.Cast(type=target_type, argument=ast.IntegerLiteral(0))
        return ast.ClassicalAssignment(lvalue=declaration.identifier, op=ast.AssignmentOperator['='], rvalue=initial)

    def runtime_call(call, active):
        definition = functions[call.name.name]
        if active or any(isinstance(n, ast.Identifier) and n.name in runtime for n in walk(call.arguments)):
            return True
        if definition.return_type is not None:
            return any(isinstance(a, ast.QuantumArgument) for a in definition.arguments)
        # An explicit void return needs structured exit lowering even when the
        # signature contains no classical arguments (or no arguments at all).
        return any(isinstance(n, ast.ReturnStatement) for n in walk(definition.body))

    def expression_calls(value, active, depth):
        """Return effects in evaluation order and the expression that uses them."""
        prefix = []
        if isinstance(value, list):
            result = []
            for item in value:
                effects, rewritten = expression_calls(item, active, depth)
                prefix.extend(effects); result.append(rewritten)
            return prefix, result
        if not isinstance(value, (ast.Expression, ast.RangeDefinition, ast.DiscreteSet)):
            return prefix, value
        if isinstance(value, ast.BinaryExpression) and value.op.name in ('&&', '||'):
            left_effects, left = expression_calls(value.lhs, active, depth)
            right_effects, right = expression_calls(value.rhs, active, depth)
            if right_effects:
                # Keep the worker's short-circuit semantics when the RHS has
                # statements: skipped operands must not measure or change qubits.
                slot = ast.Identifier(fresh()); runtime.add(slot.name)
                declaration = ast.ClassicalDeclaration(type=ast.BoolType(), identifier=slot,
                    init_expression=ast.Cast(type=ast.BoolType(), argument=left))
                condition = copy.deepcopy(slot)
                if value.op.name == '||':
                    condition = ast.UnaryExpression(op=ast.UnaryOperator['!'], expression=condition)
                assignment = ast.ClassicalAssignment(lvalue=copy.deepcopy(slot), op=ast.AssignmentOperator['='],
                    rvalue=ast.Cast(type=ast.BoolType(), argument=right))
                branch = ast.BranchingStatement(condition=condition, if_block=right_effects + [assignment], else_block=[])
                return left_effects + [declaration, branch], copy.deepcopy(slot)
            result = copy.copy(value); result.lhs = left; result.rhs = right
            return left_effects, result
        result = copy.copy(value)
        for field in fields(value):
            if field.name in ('span', 'annotations', 'name'):
                continue
            effects, rewritten = expression_calls(getattr(value, field.name), active, depth)
            prefix.extend(effects); setattr(result, field.name, rewritten)
        if isinstance(result, ast.FunctionCall) and result.name.name in functions:
            if runtime_call(result, active):
                effects, replacement = activate(result, depth)
                if replacement is None:
                    raise error_at(value, 'A void subroutine cannot be used as a value.')
                return prefix + effects, replacement
        return prefix, result

    def block(body, parent, active=False, depth=0, declared=None):
        env = dict(parent); declared = set() if declared is None else set(declared)
        result = []
        for node in body:
            if getattr(node, 'annotations', None):
                raise error_at(node, 'Annotated operations require semantics the editor does not support.')
            if isinstance(node, (ast.SubroutineDefinition, ast.QuantumGateDefinition)):
                result.append(node); continue
            if isinstance(node, (ast.ClassicalDeclaration, ast.ConstantDeclaration)):
                name = node.identifier.name
                if active and name in declared:
                    raise error_at(node, 'Duplicate declaration in one subroutine scope: ' + name)
                declared.add(name)
                if active and isinstance(node, ast.ClassicalDeclaration) and not isinstance(node.type, values):
                    raise error_at(node, 'Runtime subroutine locals currently support integers, Booleans and bit registers.')
                value = copy.copy(node)
                value.type = rewrite(node.type, env)
                if active:
                    env[name] = ast.Identifier(fresh())
                value.identifier = rewrite(node.identifier, env)
                value.init_expression = rewrite(node.init_expression, env)
                effects, value.init_expression = expression_calls(value.init_expression, active, depth)
                if effects and isinstance(node, ast.ConstantDeclaration):
                    raise error_at(node, 'A constant cannot depend on a runtime subroutine result.')
                result.extend(effects)
                if active and isinstance(node, ast.ConstantDeclaration):
                    # Hoisted bit-storage widths must carry their lexical
                    # constants, not refer back into the activation body.
                    env[name] = ast.Cast(type=copy.deepcopy(value.type), argument=copy.deepcopy(value.init_expression))
                result.append(bit_declaration(value) if active and isinstance(value, ast.ClassicalDeclaration) and isinstance(value.type, ast.BitType) else value)
                if isinstance(node, ast.ClassicalDeclaration) and isinstance(node.type, (ast.BitType,) + scalar):
                    runtime.add(value.identifier.name)
                continue
            if isinstance(node, ast.BranchingStatement):
                value = copy.copy(node); value.condition = rewrite(node.condition, env)
                effects, value.condition = expression_calls(value.condition, active, depth)
                result.extend(effects)
                value.if_block = block(node.if_block, env, active, depth)
                value.else_block = block(node.else_block, env, active, depth)
            elif isinstance(node, (ast.ForInLoop, ast.WhileLoop)):
                value = copy.copy(node); inner = dict(env)
                if isinstance(node, ast.ForInLoop):
                    value.type = rewrite(node.type, env); value.set_declaration = rewrite(node.set_declaration, env)
                    effects, value.set_declaration = expression_calls(value.set_declaration, active, depth)
                    result.extend(effects)
                    if active: inner[node.identifier.name] = ast.Identifier(fresh())
                    value.identifier = rewrite(node.identifier, inner)
                else:
                    value.while_condition = rewrite(node.while_condition, env)
                value.block = block(node.block, inner, active, depth)
                if isinstance(node, ast.WhileLoop):
                    effects, condition = expression_calls(value.while_condition, active, depth)
                    if effects:
                        stop = ast.BranchingStatement(condition=ast.UnaryExpression(op=ast.UnaryOperator['!'], expression=condition), if_block=[ast.BreakStatement()], else_block=[])
                        value.while_condition = ast.BooleanLiteral(True)
                        value.block = effects + [stop] + value.block
            elif isinstance(node, ast.CompoundStatement):
                value = copy.copy(node); value.statements = block(node.statements, env, active, depth)
            elif isinstance(node, ast.SwitchStatement):
                value = copy.copy(node); value.target = rewrite(node.target, env)
                effects, value.target = expression_calls(value.target, active, depth)
                result.extend(effects)
                value.cases = []
                for labels, case in node.cases:
                    lowered = copy.copy(case)
                    lowered.statements = block(case.statements, env, active, depth)
                    value.cases.append((rewrite(labels, env), lowered))
                if node.default is not None:
                    value.default = copy.copy(node.default)
                    value.default.statements = block(node.default.statements, env, active, depth)
            else:
                value = rewrite(node, env)
            call = value.expression if isinstance(value, ast.ExpressionStatement) else None
            if isinstance(call, ast.FunctionCall) and call.name.name in functions:
                effects, call.arguments = expression_calls(call.arguments, active, depth)
                result.extend(effects)
                if runtime_call(call, active):
                    effects, _ = activate(call, depth)
                    result.extend(effects)
                    continue
            elif not isinstance(value, (ast.BranchingStatement, ast.ForInLoop, ast.WhileLoop, ast.CompoundStatement, ast.SwitchStatement)):
                for field in fields(value):
                    if field.name in ('span', 'annotations'):
                        continue
                    effects, rewritten = expression_calls(getattr(value, field.name), active, depth)
                    result.extend(effects); setattr(value, field.name, rewritten)
            result.append(value)
        return result

    # Process in source order so a forward declaration cannot become visible.
    result = []
    for position, node in enumerate(program.statements):
        if isinstance(node, ast.ConstantDeclaration):
            if node.identifier.name in constants:
                raise error_at(node, 'Duplicate constant declaration: ' + node.identifier.name)
            # Expand only constants used by runtime calls, under a copy budget.
            # Static-only programs retain the compiler's existing evaluator.
            constants[node.identifier.name] = (position, node)
        if isinstance(node, ast.SubroutineDefinition):
            if node.name.name in functions:
                raise error_at(node, 'Duplicate subroutine definition: ' + node.name.name)
            functions[node.name.name] = node
            visibility[node.name.name] = position
        if isinstance(node, ast.QubitDeclaration):
            size = node.size
            if size is None or isinstance(size, ast.IntegerLiteral):
                registers[node.qubit.name] = 1 if size is None else size.value
        result.extend(block([node], {}))
    program.statements[:] = bit_storage + result
    return {declaration.identifier.name for declaration in bit_storage}
