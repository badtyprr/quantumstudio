"""Lower bounded runtime calls to lexical blocks consumed by scope lowering.

Scalar arguments are snapshots, quantum arguments are references. No interpreter
state is stored here: the existing runtime declarations own initialization and
scope-exit cleanup, including a call repeated inside a runtime loop.
"""
import copy
from dataclasses import fields, is_dataclass
import openqasm3.ast as ast
from pyqasm.maps.expressions import CONSTANTS_MAP
from pyqasm.expressions import Qasm3ExprEvaluator
from pyqasm.exceptions import ValidationError
from qasm_source_diagnostics import error_at


def lower_runtime_subroutines(program):
    scalar = (ast.IntType, ast.UintType, ast.BoolType, ast.FloatType, ast.AngleType)
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
    collection_arrays=set()
    array_names={n.identifier.name for n in program.statements if isinstance(n,ast.ClassicalDeclaration) and isinstance(n.type,ast.ArrayType)}
    array_scopes=[set(array_names)]
    geometry_scopes=[{}]
    collection_scopes=[{n.identifier.name:copy.deepcopy(n.type) for n in program.statements if isinstance(n,ast.ClassicalDeclaration)}]
    registers = {}
    register_declarations = {}
    register_arrays = set()
    classical_scopes = [set()]
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

    def quantum_width(expression, bindings):
        """Evaluate a closed, bounded integer subset before allocating qubits.

        The pinned evaluator owns cast/range semantics. Preflight excludes its
        unbounded powers/shifts and visitor-dependent identifier/function paths.
        With 512 nodes and 64-bit leaves, even intermediate products are bounded.
        """
        closed = rewrite(expression, bindings, lexical=True)
        pending = [(closed, 0)]; count = 0
        while pending:
            node, depth = pending.pop(); count += 1
            if count > 512 or depth >= 32:
                raise error_at(expression, 'Quantum-register widths exceed 512 expression nodes or 32 nesting levels.')
            if isinstance(node, ast.IntegerLiteral):
                if type(node.value) is not int or node.value.bit_length() > 64:
                    raise error_at(expression, 'Quantum-register width literals must fit in 64 bits.')
            elif isinstance(node, ast.UnaryExpression) and node.op.name == '-':
                pending.append((node.expression, depth + 1))
            elif isinstance(node, ast.BinaryExpression) and node.op.name in ('+', '-', '*'):
                pending.extend([(node.lhs, depth + 1), (node.rhs, depth + 1)])
            elif isinstance(node, ast.Cast) and isinstance(node.type, (ast.IntType, ast.UintType)):
                size = node.type.size
                if size is not None and (not isinstance(size, ast.IntegerLiteral) or
                                         type(size.value) is not int or not 1 <= size.value <= 64):
                    raise error_at(expression, 'Quantum-register width integer casts require literal sizes from 1 to 64.')
                pending.append((node.argument, depth + 1))
            else:
                raise error_at(expression, 'Quantum-register widths support integer constants, integer casts, unary minus and +, -, * only.')
        try:
            value, statements = Qasm3ExprEvaluator.evaluate_expression(closed, const_expr=True)
        except (ValidationError, ArithmeticError, ValueError) as error:
            raise error_at(expression, 'Invalid quantum-register width: ' + str(error)) from error
        if type(value) is not int or statements:
            raise error_at(expression, 'Quantum-register widths must be compile-time integers.')
        if not 1 <= value <= 25:
            raise error_at(expression, 'Supported quantum-register widths are from 1 to 25.')
        return value

    def register_size(name):
        if name not in registers and name in register_declarations:
            declaration, position = register_declarations[name]
            references = {n.name for n in walk(declaration.size) if isinstance(n, ast.Identifier)}
            bindings = {key: constant_value(key) for key in references
                        if key in constants and constants[key][0] < position}
            registers[name] = quantum_width(declaration.size, bindings)
        return registers.get(name)

    def quantum_key(value):
        if isinstance(value, ast.IndexExpression) and isinstance(value.collection, ast.Identifier):
            value = ast.IndexedIdentifier(name=value.collection, indices=[value.index])
        if isinstance(value, ast.Identifier) and register_size(value.name) == 1:
            return value.name, 0
        if isinstance(value, ast.IndexedIdentifier) and len(value.indices) == 1 and len(value.indices[0]) == 1:
            index = value.indices[0][0]
            size = register_size(value.name.name)
            if isinstance(index, ast.IntegerLiteral) and size is not None and 0 <= index.value < size:
                return value.name.name, index.value
        raise error_at(value, 'Runtime call quantum arguments require a scalar qubit or a fixed literal register index.')

    def check_quantum_name(value):
        reference = value
        if isinstance(reference, ast.IndexExpression):
            reference = reference.collection
        if isinstance(reference, ast.IndexedIdentifier):
            reference = reference.name
        if isinstance(reference, ast.Identifier) and any(reference.name in scope for scope in classical_scopes):
            raise error_at(value, 'A classical caller binding cannot be used as a quantum argument.')

    def quantum_binding(formal, actual, constant_bindings):
        """Return the caller reference and its identities for one overlap check.

        Whole-register references keep their AST shape so the existing unroller
        owns gate broadcasting and literal indexing. No quantum state is copied.
        """
        check_quantum_name(actual)
        if formal.size is None:
            key = quantum_key(actual)
            return ast.IndexedIdentifier(name=ast.Identifier(key[0]), indices=[[ast.IntegerLiteral(key[1])]]), {key}
        width = quantum_width(formal.size, constant_bindings)
        if not isinstance(actual, ast.Identifier) or actual.name not in register_arrays:
            raise error_at(actual, 'Runtime quantum-register arguments currently require a whole declared register.')
        size = register_size(actual.name)
        if size != width:
            raise error_at(actual, 'Quantum-register argument width does not match its parameter.')
        return copy.deepcopy(actual), {(actual.name, index) for index in range(size)}

    def activate(call, depth, active=False):
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
            raise error_at(call, 'Runtime return values support integers, Booleans, float32/64, angles and bit registers.')
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
            # Capture each actual before evaluating the next actual's calls.
            # Hoisting all nested effects first changes error/measurement order.
            effects, actual = expression_calls(actual, active, depth)
            declarations.extend(effects)
            name = formal.name.name
            if name in parameters:
                raise error_at(formal, 'Duplicate subroutine parameter: ' + name)
            if isinstance(formal, ast.QuantumArgument):
                width_bindings = {key: value for key, value in constant_bindings.items() if key not in parameters}
                binding, identities = quantum_binding(formal, actual, width_bindings)
                if qubits.intersection(identities):
                    raise error_at(call, 'Quantum subroutine arguments must not overlap.')
                qubits.update(identities)
                bindings[name] = binding
            elif isinstance(formal, ast.ClassicalArgument) and isinstance(formal.type, values):
                if formal.access is not None:
                    raise error_at(formal, 'Runtime scalar arguments are passed by value.')
                slot = ast.Identifier(fresh())
                # Actual expressions stay in the caller environment; never bind
                # an initializer to the newly introduced formal of the same name.
                declared_type = rewrite(formal.type, constant_bindings, lexical=True)
                declaration = ast.ClassicalDeclaration(type=declared_type, identifier=slot, init_expression=copy.deepcopy(actual))
                collection_scopes[-1][slot.name]=declared_type
                declarations.append(bit_declaration(declaration) if isinstance(declared_type, ast.BitType) else declaration)
                bindings[name] = slot
            else:
                raise error_at(formal, 'Runtime call arguments support integers, Booleans, float32/64, angles and bit registers.')
            parameters.add(name)
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
        if active:
            return True
        # walk already visits descendants: recursive classification here would
        # repeatedly traverse overlapping argument trees (exponential work).
        for node in walk(call):
            if isinstance(node, ast.Identifier) and node.name in runtime:
                return True
            if isinstance(node, ast.FunctionCall) and node.name.name in functions:
                definition = functions[node.name.name]
                if definition.return_type is not None:
                    if any(isinstance(a, ast.QuantumArgument) for a in definition.arguments):
                        return True
                elif any(isinstance(n, ast.ReturnStatement) for n in walk(definition.body)):
                    # Explicit void returns need structured exit lowering.
                    return True
        return False

    def specialize_loop(node, env, active, depth):
        """Expand literal ranges needed by quantum call indices before binding.

        Each iteration remains a lexical block. Reject binding mutation and
        shadowing rather than substituting a literal into a mutable binding.
        """
        nonlocal expanded
        name = node.identifier.name
        def needs_index(items, visible):
            # Match declaration order and block visibility before block_body
            # has registered the local runtime actuals. A later sibling local
            # must not turn a call using a global constant into a runtime call.
            visible = set(visible)
            for item in items:
                if isinstance(item, (ast.SubroutineDefinition, ast.QuantumGateDefinition)):
                    continue
                children = []
                if isinstance(item, ast.BranchingStatement):
                    children = [item.if_block, item.else_block]
                elif isinstance(item, (ast.ForInLoop, ast.WhileLoop)):
                    children = [item.block]
                elif isinstance(item, ast.CompoundStatement):
                    children = [item.statements]
                elif isinstance(item, ast.SwitchStatement):
                    children = [case.statements for _, case in item.cases]
                    if item.default is not None: children.append(item.default.statements)
                expressions = [getattr(item, field.name) for field in fields(item)
                               if field.name not in ('span', 'annotations', 'block', 'if_block', 'else_block', 'statements', 'cases', 'default')]
                for call in walk(expressions):
                    if not isinstance(call, ast.FunctionCall) or call.name.name not in functions:
                        continue
                    local_actual = any(isinstance(n, ast.Identifier) and n.name in visible for n in walk(call.arguments))
                    if not runtime_call(call, active or local_actual):
                        continue
                    for formal, actual in zip(functions[call.name.name].arguments, call.arguments):
                        if isinstance(formal, ast.QuantumArgument):
                            for index in walk(actual):
                                if isinstance(index, (ast.IndexExpression, ast.IndexedIdentifier)):
                                    indices = index.index if isinstance(index, ast.IndexExpression) else index.indices
                                    if any(isinstance(n, ast.Identifier) and n.name == name for n in walk(indices)):
                                        return True
                if any(needs_index(child, visible) for child in children):
                    return True
                if isinstance(item, ast.ClassicalDeclaration) and isinstance(item.type, values):
                    visible.add(item.identifier.name)
                elif isinstance(item, ast.ConstantDeclaration):
                    visible.discard(item.identifier.name)
            return False

        if not needs_index(node.block, set()):
            return None

        def literal(value):
            sign = 1
            if isinstance(value, ast.UnaryExpression) and value.op.name == '-':
                sign = -1; value = value.expression
            if not isinstance(value, ast.IntegerLiteral) or type(value.value) is not int or value.value.bit_length() > 64:
                raise error_at(node, 'Quantum-call loop ranges require literal integers of at most 64 bits.')
            return sign * value.value

        domain = node.set_declaration
        if not isinstance(domain, ast.RangeDefinition) or not isinstance(node.type, (ast.IntType, ast.UintType)):
            raise error_at(node, 'Quantum-call index loops require integer literal ranges.')
        start, stop = literal(domain.start), literal(domain.end)
        step = 1 if domain.step is None else literal(domain.step)
        if step == 0:
            raise error_at(node, 'Quantum-call index loop step must be nonzero.')
        size = node.type.size
        if size is not None and (not isinstance(size, ast.IntegerLiteral) or not 1 <= size.value <= 64):
            raise error_at(node, 'Quantum-call index loop types require literal widths from 1 to 64.')
        width = 32 if size is None else size.value
        minimum = -(1 << (width - 1)) if isinstance(node.type, ast.IntType) else 0
        maximum = (1 << (width - (1 if isinstance(node.type, ast.IntType) else 0))) - 1
        count = max(0, (stop - start) // step + 1)
        if count and not (minimum <= start <= maximum and minimum <= start + (count - 1) * step <= maximum):
            raise error_at(node, 'Quantum-call loop values do not fit their declared integer type.')
        for child in walk(node.block):
            if isinstance(child, (ast.BreakStatement, ast.ContinueStatement, ast.ReturnStatement)):
                raise error_at(child, 'Specialized quantum-call loops do not support control transfers.')
            if isinstance(child, (ast.ClassicalDeclaration, ast.ConstantDeclaration, ast.ForInLoop)) and child.identifier.name == name:
                raise error_at(child, 'Specialized quantum-call loop bindings must not be shadowed.')
            target = child.lvalue if isinstance(child, ast.ClassicalAssignment) else child.target if isinstance(child, ast.QuantumMeasurementStatement) else None
            if isinstance(target, ast.IndexedIdentifier): target = target.name
            if isinstance(target, ast.IndexExpression): target = target.collection
            if isinstance(target, ast.Identifier) and target.name == name:
                raise error_at(child, 'Specialized quantum-call loop bindings must not be assigned.')
        cost = count * sum(1 for _ in walk(node.block))
        if count > 4096 or expanded + cost > 65536:
            raise error_at(node, 'Quantum-call loop expansion exceeds 4096 iterations or 65536 AST nodes.')
        expanded += cost
        result = []
        for iteration in range(count):
            inner = dict(env); inner[name] = ast.IntegerLiteral(start + iteration * step)
            result.append(ast.CompoundStatement(statements=block(node.block, inner, active, depth)))
        return result

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
        if isinstance(value, ast.FunctionCall) and value.name.name in functions and runtime_call(value, active):
            effects, replacement = activate(value, depth, active)
            if replacement is None:
                raise error_at(value, 'A void subroutine cannot be used as a value.')
            return effects, replacement
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
        return prefix, result

    def block(body, parent, active=False, depth=0, declared=None, classical_names=()):
        # Call actuals are resolved before expansion, even for unused formals.
        # Keep caller shadowing lexical; leaving a block restores the register.
        classical_scopes.append(set(classical_names))
        array_scopes.append(set(array_scopes[-1])-set(classical_names))
        geometry_scopes.append(dict(geometry_scopes[-1]))
        for name in classical_names:geometry_scopes[-1][name]=ast.Identifier(name)
        collection_scopes.append({name:type_ for name,type_ in collection_scopes[-1].items() if name not in classical_names})
        try:
            return block_body(body, parent, active, depth, declared)
        finally:
            classical_scopes.pop()
            array_scopes.pop()
            collection_scopes.pop()
            geometry_scopes.pop()

    def collection_geometry(value,env):
        references={n.name for n in walk(value) if isinstance(n,ast.Identifier)}
        bindings={name:constant_value(name) for name in references if name in constants}
        bindings.update(geometry_scopes[-1]);bindings.update(env)
        return rewrite(value,bindings,lexical=False)

    def collection_integer(value, env):
        value=collection_geometry(value,env)
        pending=[(value,0)];count=0
        while pending:
            item,level=pending.pop();count+=1
            if count>512 or level>=32:raise error_at(value,'Collection geometry exceeds expression bounds.')
            if isinstance(item,ast.IntegerLiteral):
                if type(item.value) is not int or item.value.bit_length()>64:raise error_at(value,'Collection geometry must fit in 64 bits.')
            elif isinstance(item,ast.UnaryExpression) and item.op.name=='-':pending.append((item.expression,level+1))
            elif isinstance(item,ast.BinaryExpression) and item.op.name in ('+','-','*'):
                pending.extend(((item.lhs,level+1),(item.rhs,level+1)))
            elif isinstance(item,ast.Cast) and isinstance(item.type,(ast.IntType,ast.UintType)):
                if item.type.size is not None and (not isinstance(item.type.size,ast.IntegerLiteral) or not 1<=item.type.size.value<=64):raise error_at(value,'Collection integer cast widths must be 1 to 64.')
                pending.append((item.argument,level+1))
            else:raise error_at(value,'Collection geometry currently requires constant integer arithmetic.')
        result,effects=Qasm3ExprEvaluator.evaluate_expression(value,const_expr=True)
        if type(result) is not int or effects:raise error_at(value,'Collection geometry requires integers.')
        return result

    def collection_values(value,env):
        reference=rewrite(value,env);indices=None
        if isinstance(reference,ast.IndexExpression):
            indices=reference.index;reference=reference.collection
        if not isinstance(reference,ast.Identifier):return None
        type_=collection_scopes[-1].get(reference.name)
        if isinstance(type_,ast.ArrayType):
            if len(type_.dimensions)!=1:raise error_at(value,'Collection iteration requires a one-dimensional array or view.')
            length=collection_integer(type_.dimensions[0],env);bits=False
            collection_arrays.add(reference.name)
        elif isinstance(type_,ast.BitType) and type_.size is not None:
            length=collection_integer(type_.size,env);bits=True
        else:return None
        if not 0<=length<=(64 if bits else 4096):raise error_at(value,'Collection allocation exceeds its storage limit.')
        positions=list(range(length))
        if indices is not None:
            if not isinstance(indices,list) or len(indices)!=1 or not isinstance(indices[0],ast.RangeDefinition):raise error_at(value,'Collection selection requires a one-dimensional slice.')
            range_=indices[0]
            step=1 if range_.step is None else collection_integer(range_.step,env)
            if step==0:raise error_at(value,'Collection slice step must not be zero.')
            if length==0 and range_.start is None and range_.end is None:return []
            start=(0 if step>0 else length-1) if range_.start is None else collection_integer(range_.start,env)
            stop=(length-1 if step>0 else 0) if range_.end is None else collection_integer(range_.end,env)
            if not bits:
                if start<0:start+=length
                if stop<0:stop+=length
            if not 0<=start<length or not 0<=stop<length:raise error_at(value,'Collection slice endpoint is outside its allocation.')
            positions=list(range(start,stop+(1 if step>0 else -1),step))
        if len(positions)>64:raise error_at(value,'Runtime collections support at most 64 values.')
        return [ast.IndexExpression(collection=copy.deepcopy(reference),index=[ast.IntegerLiteral(i)]) for i in positions]

    def collection_loop(node, env, active, depth):
        """Snapshot a finite value sequence, then use the existing range engine.

        The cursor is independent of the user binding, so assignments, continue
        and break retain the same transfer and cleanup semantics as range loops.
        """
        if not isinstance(node.type, values):
            raise error_at(node, 'Collection loops require an integer, Boolean, float, angle or bit binding.')
        if len(node.set_declaration.values) > 64:
            raise error_at(node, 'Runtime collections support at most 64 values.')
        binding_type = rewrite(node.type, env)
        if isinstance(binding_type,ast.BitType) and binding_type.size is not None and collection_integer(binding_type.size,env)!=1:raise error_at(node,'Bit collection bindings must have width one.')
        def local(declaration):return bit_declaration(declaration) if isinstance(binding_type,ast.BitType) else declaration
        prefix = []; snapshots = []
        for item in node.set_declaration.values:
            effects, value = expression_calls(copy.deepcopy(item) if getattr(node,'_quantum_resolved_collection',False) else rewrite(item, env), active, depth)
            prefix.extend(effects)
            slot = ast.Identifier(fresh()); runtime.add(slot.name)
            prefix.append(local(ast.ClassicalDeclaration(type=copy.deepcopy(binding_type), identifier=slot, init_expression=value)))
            snapshots.append(slot)
        cursor = ast.Identifier(fresh()); binding = ast.Identifier(fresh()); count = ast.Identifier(fresh())
        runtime.update((cursor.name, binding.name, count.name))
        # Retain a runtime bound through export/reimport too; a literal-only
        # range would be reclassified as compile-time by the pinned compiler.
        prefix.append(ast.ClassicalDeclaration(type=ast.IntType(size=ast.IntegerLiteral(32)),
            identifier=count, init_expression=ast.IntegerLiteral(len(snapshots))))
        inner = dict(env); inner[node.identifier.name] = binding
        body = block(node.block, inner, active, depth, classical_names=(binding.name,))
        def dispatch(first, last):
            if first == last:
                return []
            if last-first == 1:
                return [ast.ClassicalAssignment(lvalue=copy.deepcopy(binding), op=ast.AssignmentOperator['='],
                    rvalue=copy.deepcopy(snapshots[first]))]
            middle = (first+last)//2
            return [ast.BranchingStatement(
                condition=ast.BinaryExpression(op=ast.BinaryOperator['<'], lhs=copy.deepcopy(cursor), rhs=ast.IntegerLiteral(middle)),
                if_block=dispatch(first, middle), else_block=dispatch(middle, last))]
        loop = ast.ForInLoop(type=ast.IntType(size=ast.IntegerLiteral(32)), identifier=cursor,
            set_declaration=ast.RangeDefinition(start=ast.IntegerLiteral(0),
                end=ast.BinaryExpression(op=ast.BinaryOperator['-'], lhs=count, rhs=ast.IntegerLiteral(1)), step=None),
            block=[local(ast.ClassicalDeclaration(type=binding_type, identifier=binding, init_expression=None))] + dispatch(0, len(snapshots)) + body)
        loop._quantum_runtime_for = True
        loop.span = node.span
        return ast.CompoundStatement(statements=prefix + [loop])

    def block_body(body, parent, active=False, depth=0, declared=None):
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
                if not isinstance(node.type,ast.ArrayType):array_scopes[-1].discard(name)
                if active and isinstance(node, ast.ClassicalDeclaration) and not isinstance(node.type, values):
                    raise error_at(node, 'Runtime subroutine locals support integers, Booleans, float32/64, angles and bit registers.')
                value = copy.copy(node)
                value.type = rewrite(node.type, env)
                if active:
                    env[name] = ast.Identifier(fresh())
                value.identifier = rewrite(node.identifier, env)
                classical_scopes[-1].add(value.identifier.name)
                collection_scopes[-1][value.identifier.name]=collection_geometry(value.type,env)
                value.init_expression = rewrite(node.init_expression, env)
                geometry_scopes[-1][name]=collection_geometry(ast.Cast(type=copy.deepcopy(value.type),argument=copy.deepcopy(value.init_expression)),env) if isinstance(node,ast.ConstantDeclaration) else copy.deepcopy(value.identifier)
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
                if isinstance(node, ast.ForInLoop):
                    collection=collection_values(node.set_declaration,env)
                    if collection is not None:
                        value=copy.copy(node);value.set_declaration=ast.DiscreteSet(values=collection);value._quantum_resolved_collection=True
                        result.append(collection_loop(value,env,active,depth));continue
                    if isinstance(node.set_declaration, ast.DiscreteSet):
                        if len(node.set_declaration.values) > 64:
                            raise error_at(node, 'Runtime collections support at most 64 values.')
                        # Keep the pinned compiler's literal quantum-call path
                        # until runtime reference binding is lowered separately.
                        static_quantum_calls = not active and not any(
                            isinstance(item, ast.Identifier) and item.name in runtime or
                            isinstance(item, ast.FunctionCall) and item.name.name in functions and runtime_call(item, active)
                            for item in walk(rewrite(node.set_declaration, env))) and any(
                            isinstance(item, ast.FunctionCall) and item.name.name in functions
                            and any(isinstance(arg, ast.QuantumArgument) for arg in functions[item.name.name].arguments)
                            and not runtime_call(item, active) for item in walk(node.block))
                        if not static_quantum_calls:
                            result.append(collection_loop(node, env, active, depth))
                            continue
                    specialized = specialize_loop(node, env, active, depth)
                    if specialized is not None:
                        result.extend(specialized)
                        continue
                value = copy.copy(node); inner = dict(env)
                if isinstance(node, ast.ForInLoop):
                    value.type = rewrite(node.type, env); value.set_declaration = rewrite(node.set_declaration, env)
                    effects, value.set_declaration = expression_calls(value.set_declaration, active, depth)
                    result.extend(effects)
                    if active: inner[node.identifier.name] = ast.Identifier(fresh())
                    value.identifier = rewrite(node.identifier, inner)
                else:
                    value.while_condition = rewrite(node.while_condition, env)
                value.block = block(node.block, inner, active, depth,
                    classical_names=(value.identifier.name,) if isinstance(node, ast.ForInLoop) else ())
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
                if runtime_call(call, active):
                    effects, _ = activate(call, depth, active)
                    result.extend(effects)
                    continue
            elif isinstance(value,ast.ClassicalAssignment) and isinstance(value.lvalue,ast.IndexedIdentifier) and value.lvalue.name.name in array_scopes[-1]:
                effects,rhs=expression_calls(value.rvalue,active,depth)
                indices=[]
                raw_indices=[index for group in value.lvalue.indices for index in group]
                lowered_indices=[expression_calls(index,active,depth) for index in raw_indices]
                capture=bool(effects) or any(prefix for prefix,_ in lowered_indices)
                for prefix,index in lowered_indices:
                    result.extend(prefix)
                    if capture:
                        # Check before narrowing to a signed snapshot: UINT64_MAX
                        # must fail bounds rather than turn into the valid -1.
                        probe=indices+[index]
                        target=ast.IndexExpression(collection=copy.deepcopy(value.lvalue.name),index=[ast.RangeDefinition(start=copy.deepcopy(i),end=copy.deepcopy(i),step=None) for i in probe])
                        check=ast.Identifier(fresh());runtime.add(check.name)
                        result.append(ast.ClassicalDeclaration(type=ast.IntType(),identifier=check,init_expression=ast.SizeOf(target=target,index=None)))
                        slot=ast.Identifier(fresh());runtime.add(slot.name)
                        result.append(ast.ClassicalDeclaration(type=ast.IntType(),identifier=slot,init_expression=index));index=slot
                    indices.append(index)
                value.lvalue.indices=[indices]
                result.extend(effects);value.rvalue=rhs
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
        if isinstance(node, (ast.ClassicalDeclaration, ast.ConstantDeclaration)):
            classical_scopes[0].add(node.identifier.name)
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
            register_declarations[node.qubit.name] = (node, position)
            if size is not None:
                register_arrays.add(node.qubit.name)
            if size is None or isinstance(size, ast.IntegerLiteral):
                registers[node.qubit.name] = 1 if size is None else size.value
        if isinstance(node,ast.ClassicalDeclaration):collection_scopes[0][node.identifier.name]=collection_geometry(node.type,{})
        result.extend(block([node], {}))
    program.statements[:] = bit_storage + result
    program._quantum_runtime_array_names=collection_arrays
    return {declaration.identifier.name for declaration in bit_storage}
