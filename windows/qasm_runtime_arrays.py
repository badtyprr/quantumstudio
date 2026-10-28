"""Lower global runtime arrays to typed backing slots and checked selections."""
import copy
from dataclasses import fields, is_dataclass
import openqasm3.ast as ast
from qasm_source_diagnostics import error_at


def selection(node, integer):
    info = node._quantum_array
    return dict(Array=info['id'], Indices=[integer(index) for index in node._quantum_array_indices], Source=info['source'])


def lower_arrays(program):
    # Keep the established compile-time path when no array access depends on
    # runtime storage. Runtime lowering is selected for the whole allocation,
    # never independently for two uses of the same array.
    def walk(value):
        if is_dataclass(value):
            yield value
            for field in fields(value):
                if field.name not in ('span', 'annotations'): yield from walk(getattr(value, field.name))
        elif isinstance(value, (list, tuple)):
            for item in value: yield from walk(item)
    all_nodes = list(walk(program))
    names = {n.identifier.name for n in all_nodes if isinstance(n, ast.ClassicalDeclaration) and isinstance(n.type, ast.ArrayType)}
    if not names: return []
    runtime = {n.identifier.name for n in all_nodes if isinstance(n, ast.ClassicalDeclaration) and isinstance(n.type, (ast.IntType, ast.UintType, ast.BoolType, ast.FloatType, ast.AngleType, ast.BitType))}
    def depends(value): return any(isinstance(n, ast.Identifier) and n.name in runtime for n in walk(value))
    def uses_array(value): return any(isinstance(n, ast.Identifier) and n.name in names for n in walk(value))
    needed = False
    for node in all_nodes:
        if isinstance(node, ast.ClassicalDeclaration) and isinstance(node.type, ast.ArrayType):
            needed |= depends(node.init_expression) or any(isinstance(d, ast.IntegerLiteral) and d.value == 0 for d in node.type.dimensions)
        if isinstance(node, ast.ClassicalAssignment) and uses_array(node.lvalue): needed |= depends(node)
        if isinstance(node, (ast.IndexExpression, ast.IndexedIdentifier)) and uses_array(node):
            needed |= depends(node) or any(isinstance(n, ast.UnaryExpression) and n.op.name == '-' for n in walk(node))
        if isinstance(node, ast.BranchingStatement) and depends(node.condition):
            needed |= any(isinstance(n, ast.ClassicalAssignment) and uses_array(n.lvalue) for n in walk([node.if_block, node.else_block]))
        if isinstance(node, ast.WhileLoop) and uses_array(node.block): needed = True
        if isinstance(node, ast.ForInLoop) and depends(node.set_declaration) and uses_array(node.block): needed = True
    if not needed: return []
    constants = {}
    arrays = {}
    allocations = []
    used = set()

    def collect(value):
        if isinstance(value, ast.Identifier): used.add(value.name)
        elif isinstance(value, list):
            for item in value: collect(item)
        elif is_dataclass(value):
            for field in fields(value):
                if field.name not in ('span', 'annotations'): collect(getattr(value, field.name))
    collect(program)

    def constant(value):
        if isinstance(value, ast.IntegerLiteral): return value.value
        if isinstance(value, ast.Identifier) and value.name in constants: return constants[value.name]
        if isinstance(value, ast.UnaryExpression) and value.op.name == '-': return -constant(value.expression)
        if isinstance(value, ast.BinaryExpression) and value.op.name in ('+', '-', '*'):
            left, right = constant(value.lhs), constant(value.rhs)
            return {'+': lambda: left + right, '-': lambda: left - right, '*': lambda: left * right}[value.op.name]()
        raise error_at(value, 'Array dimensions and element widths must be constant integers.')

    def marker(info, indices, source):
        if len(indices) != len(info['dimensions']) or any(isinstance(i, (ast.RangeDefinition, ast.DiscreteSet)) for i in indices):
            raise error_at(source, 'Runtime array element access requires one scalar index per dimension.')
        node = ast.Identifier(info['backing'][0] if info['backing'] else '_qa_empty_' + str(info['id']))
        node._quantum_array = dict(info)
        span = getattr(source, 'span', None)
        if span is not None:
            node._quantum_array['source'] = 'line %d:%d array %s' % (span.start_line, span.start_column, info['name'])
        node._quantum_array_indices = indices
        node.span = getattr(source, 'span', None)
        return node

    def reference(value):
        if isinstance(value, ast.IndexedIdentifier):
            return value.name.name, [i for group in value.indices for i in group]
        if isinstance(value, ast.IndexExpression):
            indices = value.index if isinstance(value.index, list) else [value.index]
            name, earlier = reference(value.collection)
            return name, earlier + indices
        if isinstance(value, ast.Identifier): return value.name, []
        return None, []

    def expression(value):
        if isinstance(value, (ast.IndexedIdentifier, ast.IndexExpression)):
            name, indices = reference(value)
            if name in arrays: return marker(arrays[name], [expression(i) for i in indices], value)
        if isinstance(value, ast.SizeOf):
            name, indices = reference(value.target)
            if name in arrays and not indices:
                axis = 0 if value.index is None else constant(value.index)
                if not 0 <= axis < len(arrays[name]['dimensions']): raise error_at(value, 'sizeof axis is outside the array rank.')
                return ast.IntegerLiteral(arrays[name]['dimensions'][axis])
        if isinstance(value, ast.Identifier) and value.name in arrays:
            raise error_at(value, 'A whole runtime array requires an array reference or collection operation.')
        if isinstance(value, list): return [expression(item) for item in value]
        if is_dataclass(value):
            for field in fields(value):
                if field.name not in ('span', 'annotations'):
                    setattr(value, field.name, expression(getattr(value, field.name)))
        return value

    def flatten(value, shape):
        if not shape:
            if isinstance(value, ast.ArrayLiteral): raise error_at(value, 'Array initializer has too many dimensions.')
            return [expression(value)]
        if not isinstance(value, ast.ArrayLiteral) or len(value.values) != shape[0]:
            raise error_at(value, 'Array initializer shape does not match its declaration.')
        return [element for child in value.values for element in flatten(child, shape[1:])]

    result = []
    for statement in program.statements:
        if isinstance(statement, ast.ConstantDeclaration):
            try: constants[statement.identifier.name] = constant(statement.init_expression)
            except ValueError: pass
        if not isinstance(statement, ast.ClassicalDeclaration) or not isinstance(statement.type, ast.ArrayType):
            result.append(expression(statement));continue
        name = statement.identifier.name
        if name in arrays: raise error_at(statement, 'Duplicate array declaration.')
        dimensions = [constant(value) for value in statement.type.dimensions]
        if not 1 <= len(dimensions) <= 7 or any(type(d) is not int or not 0 <= d <= 4096 for d in dimensions):
            raise error_at(statement, 'Runtime arrays require one to seven dimensions, each from 0 to 4096.')
        size = 0 if 0 in dimensions else 1
        if size:
            for dimension in dimensions:
                if size > 4096 // dimension: raise error_at(statement, 'Runtime array allocation exceeds 4096 elements.')
                size *= dimension
        element = copy.deepcopy(statement.type.base_type)
        boolean = isinstance(element, ast.BoolType)
        if not isinstance(element, (ast.IntType, ast.UintType, ast.BoolType, ast.FloatType, ast.AngleType)):
            raise error_at(statement, 'Runtime arrays support int, uint, bool, float and angle elements.')
        width = 1 if boolean else (64 if isinstance(element, (ast.FloatType, ast.AngleType)) else 0) if element.size is None else constant(element.size)
        if boolean: element = ast.UintType(size=ast.IntegerLiteral(1))
        else: element.size = ast.IntegerLiteral(width) if width else None
        kind = 'Float' if isinstance(element, ast.FloatType) else 'Angle' if isinstance(element, ast.AngleType) else 'Unsigned' if isinstance(element, ast.UintType) else 'Signed'
        backing = []
        for k in range(size):
            candidate = '_qa_' + str(len(allocations)) + '_' + str(k)
            while candidate in used: candidate += '_'
            used.add(candidate);backing.append(candidate)
        info = dict(id=len(allocations), name=name, dimensions=dimensions, backing=backing, kind=kind, width=width, boolean=boolean, source='array '+name)
        arrays[name] = info;allocations.append(info)
        values = flatten(statement.init_expression, dimensions) if statement.init_expression is not None else [None] * size
        for target, value in zip(backing, values):
            if boolean and value is not None: value = ast.Cast(type=ast.BoolType(), argument=value)
            result.append(ast.ClassicalDeclaration(type=copy.deepcopy(element), identifier=ast.Identifier(target), init_expression=value))
    program.statements[:] = result
    return allocations


def declarations(allocations, integers, numeric):
    result = []
    for info in allocations:
        is_numeric = info['kind'] in ('Float', 'Angle')
        table = numeric if is_numeric else integers
        base = table[info['backing'][0]][0] if info['backing'] else len(table)
        if any(table[name][0] != base + k for k, name in enumerate(info['backing'])):
            raise ValueError('Runtime array backing slots must remain contiguous.')
        result.append(dict(Name=info['name'], Base=base, Dimensions=info['dimensions'], Width=info['width'], **{'NumericKind' if is_numeric else 'Signedness': info['kind']}))
    return result
