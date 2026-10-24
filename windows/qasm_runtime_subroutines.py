"""Lower bounded runtime calls to lexical blocks consumed by scope lowering.

Scalar arguments are snapshots, quantum arguments are references. No interpreter
state is stored here: the existing runtime declarations own initialization and
scope-exit cleanup, including a call repeated inside a runtime loop.
"""
import copy
from dataclasses import fields, is_dataclass
import openqasm3.ast as ast
from qasm_source_diagnostics import error_at


def lower_runtime_subroutines(program):
    scalar = (ast.IntType, ast.UintType, ast.BoolType)

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
    used = {node.name for node in walk(program) if isinstance(node, ast.Identifier)}
    runtime = set()
    registers = {}
    serial = calls = expanded = 0

    def fresh():
        nonlocal serial
        while True:
            serial += 1
            name = '_qcall_' + str(serial)
            if name not in used:
                used.add(name)
                return name

    def rewrite(value, bindings):
        if isinstance(value, ast.Identifier):
            return copy.deepcopy(bindings.get(value.name, value))
        if isinstance(value, ast.IndexedIdentifier) and value.name.name in bindings:
            raise error_at(value, 'Runtime calls currently require scalar quantum parameters without indexing.')
        if isinstance(value, list):
            return [rewrite(item, bindings) for item in value]
        if isinstance(value, tuple):
            return tuple(rewrite(item, bindings) for item in value)
        if is_dataclass(value):
            result = copy.copy(value)
            for field in fields(value):
                if field.name in ('span', 'annotations') or (field.name == 'name' and isinstance(value, (ast.FunctionCall, ast.QuantumGate))):
                    continue
                setattr(result, field.name, rewrite(getattr(value, field.name), bindings))
            return result
        return value

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
        if activations and call.name.name not in activations[-1]:
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
        if definition.return_type is not None or any(isinstance(n, ast.ReturnStatement) for n in walk(definition.body)):
            raise error_at(call, 'Runtime subroutines with return values or explicit returns are not yet supported.')
        if len(call.arguments) != len(definition.arguments):
            raise error_at(call, 'Subroutine argument count does not match its declaration.')
        bindings = {}; declarations = []; qubits = set()
        for formal, actual in zip(definition.arguments, call.arguments):
            name = formal.name.name
            if name in bindings:
                raise error_at(formal, 'Duplicate subroutine parameter: ' + name)
            if isinstance(formal, ast.QuantumArgument):
                if formal.size is not None:
                    raise error_at(formal, 'Runtime calls currently require scalar quantum parameters.')
                key = quantum_key(actual)
                if key in qubits:
                    raise error_at(call, 'Quantum subroutine arguments must not overlap.')
                qubits.add(key)
                bindings[name] = ast.IndexedIdentifier(name=ast.Identifier(key[0]), indices=[[ast.IntegerLiteral(key[1])]])
            elif isinstance(formal, ast.ClassicalArgument) and isinstance(formal.type, scalar):
                if formal.access is not None:
                    raise error_at(formal, 'Runtime scalar arguments are passed by value.')
                slot = ast.Identifier(fresh())
                # Actual expressions stay in the caller environment; never bind
                # an initializer to the newly introduced formal of the same name.
                declarations.append(ast.ClassicalDeclaration(type=copy.deepcopy(formal.type), identifier=slot, init_expression=copy.deepcopy(actual)))
                bindings[name] = slot
            else:
                raise error_at(formal, 'Runtime call arguments currently support scalar integers and Booleans.')
        activations.append(visibility[call.name.name])
        try:
            body = block(definition.body, bindings, True, depth + 1, set(bindings))
        finally:
            activations.pop()
        return ast.CompoundStatement(statements=declarations + body)

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
                if active and isinstance(node, ast.ClassicalDeclaration) and not isinstance(node.type, scalar):
                    raise error_at(node, 'Runtime subroutine locals currently support scalar integers and Booleans.')
                value = copy.copy(node)
                value.type = rewrite(node.type, env)
                if active:
                    env[name] = ast.Identifier(fresh())
                value.identifier = rewrite(node.identifier, env)
                value.init_expression = rewrite(node.init_expression, env)
                result.append(value)
                if isinstance(node, ast.ClassicalDeclaration) and isinstance(node.type, (ast.BitType,) + scalar):
                    runtime.add(value.identifier.name)
                continue
            if isinstance(node, ast.BranchingStatement):
                value = copy.copy(node); value.condition = rewrite(node.condition, env)
                value.if_block = block(node.if_block, env, active, depth)
                value.else_block = block(node.else_block, env, active, depth)
            elif isinstance(node, (ast.ForInLoop, ast.WhileLoop)):
                value = copy.copy(node); inner = dict(env)
                if isinstance(node, ast.ForInLoop):
                    value.type = rewrite(node.type, env); value.set_declaration = rewrite(node.set_declaration, env)
                    if active: inner[node.identifier.name] = ast.Identifier(fresh())
                    value.identifier = rewrite(node.identifier, inner)
                else:
                    value.while_condition = rewrite(node.while_condition, env)
                value.block = block(node.block, inner, active, depth)
            elif isinstance(node, ast.CompoundStatement):
                value = copy.copy(node); value.statements = block(node.statements, env, active, depth)
            elif isinstance(node, ast.SwitchStatement):
                value = copy.copy(node); value.target = rewrite(node.target, env)
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
                needs_runtime = active or any(isinstance(n, ast.Identifier) and n.name in runtime for n in walk(call.arguments))
                if needs_runtime: value = activate(call, depth)
            elif active and any(isinstance(n, ast.FunctionCall) and n.name.name in functions for n in walk(value)):
                raise error_at(node, 'Runtime subroutine calls must be standalone void statements.')
            result.append(value)
        return result

    # Process in source order so a forward declaration cannot become visible.
    result = []
    for node in program.statements:
        if isinstance(node, ast.SubroutineDefinition):
            if node.name.name in functions:
                raise error_at(node, 'Duplicate subroutine definition: ' + node.name.name)
            functions[node.name.name] = node
            visibility[node.name.name] = set(functions)
        if isinstance(node, ast.QubitDeclaration):
            size = node.size
            if size is None or isinstance(size, ast.IntegerLiteral):
                registers[node.qubit.name] = 1 if size is None else size.value
        result.extend(block([node], {}))
    program.statements[:] = result
