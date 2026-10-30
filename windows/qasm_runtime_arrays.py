"""Lower global runtime arrays to typed backing slots and checked selections."""
import copy
from dataclasses import fields, is_dataclass
import openqasm3.ast as ast
from qasm_source_diagnostics import error_at
from pyqasm.expressions import Qasm3ExprEvaluator


def selection(node, integer):
    info = node._quantum_array
    return dict(Array=info['id'], Indices=[integer(index) for index in node._quantum_array_indices], Source=info['source'])


def lower_arrays(program):
    def walk(value):
        if is_dataclass(value):
            yield value
            if isinstance(value,(ast.SubroutineDefinition,ast.QuantumGateDefinition)):return
            for field in fields(value):
                if field.name not in ('span','annotations'):yield from walk(getattr(value,field.name))
        elif isinstance(value,(list,tuple)):
            for item in value:yield from walk(item)
    all_nodes=list(walk(program))
    names={n.identifier.name for n in program.statements if isinstance(n,ast.ClassicalDeclaration) and isinstance(n.type,ast.ArrayType)}
    if not names:return []
    array_nodes={n.identifier.name:n for n in program.statements if isinstance(n,ast.ClassicalDeclaration) and isinstance(n.type,ast.ArrayType)}
    possibly_undefined={n.identifier.name for n in program.statements if isinstance(n,ast.ClassicalDeclaration) and isinstance(n.type,ast.ArrayType) and n.init_expression is None}
    scalar=(ast.IntType,ast.UintType,ast.BoolType,ast.FloatType,ast.AngleType)
    runtime={n.identifier.name for n in all_nodes if isinstance(n,ast.ClassicalDeclaration) and isinstance(n.type,scalar+(ast.BitType,))}-names
    constants={};selected=set(getattr(program,'_quantum_runtime_array_names',()));arrays={};allocations=[]
    used={n.name for n in all_nodes if isinstance(n,ast.Identifier)}
    charged=sum(isinstance(n,ast.ClassicalDeclaration) and isinstance(n.type,scalar) for n in all_nodes)

    def constant(value,depth=0):
        if depth>=32:raise error_at(value,'Constant expression exceeds 32 levels.')
        child=lambda item:constant(item,depth+1)
        if isinstance(value,ast.IntegerLiteral):return value.value
        if isinstance(value,ast.Identifier) and value.name in constants:return constants[value.name]
        if isinstance(value,ast.UnaryExpression) and value.op.name=='-':return -child(value.expression)
        if isinstance(value,ast.BinaryExpression) and value.op.name in ('+','-','*'):
            left,right=child(value.lhs),child(value.rhs)
            result={'+':lambda:left+right,'-':lambda:left-right,'*':lambda:left*right}[value.op.name]()
            if not -(1<<64)<=result<(1<<64):raise error_at(value,'Array constant exceeds 64 bits.')
            return result
        if isinstance(value,ast.Cast) and isinstance(value.type,(ast.IntType,ast.UintType)):
            type_=copy.deepcopy(value.type)
            if type_.size is not None:type_.size=ast.IntegerLiteral(child(type_.size))
            result,effects=Qasm3ExprEvaluator.evaluate_expression(ast.Cast(type=type_,argument=ast.IntegerLiteral(child(value.argument))),const_expr=True)
            if effects or type(result) is not int:raise error_at(value,'Array constant must be an integer.')
            return result
        raise error_at(value,'Array dimensions and element widths must be constant integers.')

    def remember(statement):
        if isinstance(statement,ast.ConstantDeclaration):
            try:constants[statement.identifier.name]=constant(ast.Cast(type=copy.deepcopy(statement.type),argument=statement.init_expression))
            except ValueError:pass

    def reference(value):
        if isinstance(value,ast.IndexedIdentifier):return value.name.name,[i for group in value.indices for i in group]
        if isinstance(value,ast.IndexExpression):
            name,earlier=reference(value.collection)
            return name,earlier+(value.index if isinstance(value.index,list) else [value.index])
        return (value.name,[]) if isinstance(value,ast.Identifier) else (None,[])

    def scan(value,hidden=frozenset(),controlled=False,dynamic=frozenset()):
        def depends(item):return any(isinstance(n,ast.Identifier) and n.name in (runtime|set(dynamic)|(selected-set(hidden))) for n in walk(item))
        if isinstance(value,list):
            local=set(hidden);local_dynamic=set(dynamic)
            for item in value:
                if isinstance(item,(ast.ClassicalDeclaration,ast.ConstantDeclaration)) and not isinstance(item.type,ast.ArrayType):local.add(item.identifier.name)
                if isinstance(item,ast.ClassicalDeclaration) and isinstance(item.type,scalar+(ast.BitType,)):local_dynamic.add(item.identifier.name)
                scan(item,local,controlled,local_dynamic)
            return
        if isinstance(value,(ast.SubroutineDefinition,ast.QuantumGateDefinition)):return
        if isinstance(value,ast.ClassicalDeclaration) and isinstance(value.type,ast.ArrayType) and value.identifier.name in names:
            zero=False
            try:zero=any(constant(d)==0 for d in value.type.dimensions)
            except ValueError:pass
            if zero or depends(value.init_expression):selected.add(value.identifier.name)
        if isinstance(value,ast.SizeOf):
            name,indices=reference(value.target)
            if name in names-hidden and indices:selected.add(name)
        if isinstance(value,ast.ClassicalAssignment):
            name,_=reference(value.lvalue)
            if name in names-hidden and (controlled or depends(value)):selected.add(name)
        if isinstance(value,(ast.IndexExpression,ast.IndexedIdentifier)):
            name,indices=reference(value)
            if name in names-hidden:
                negative=False
                for index in indices:
                    try:negative|=constant(index)<0
                    except ValueError:pass
                deferred=False
                if controlled:
                    try:
                        shape=[constant(d) for d in array_nodes[name].type.dimensions]
                        deferred=(name in possibly_undefined
                                  or any(isinstance(n,ast.Identifier) and n.name in hidden for n in walk(indices))
                                  or len(indices)!=len(shape)
                                  or any(not 0<=constant(i)<d for i,d in zip(indices,shape)))
                    except ValueError:deferred=True
                if deferred or negative or depends(indices):selected.add(name)
        if isinstance(value,ast.SwitchStatement):
            scan(value.target,hidden,controlled,dynamic)
            active=controlled or depends(value.target)
            for _,case in value.cases:scan(case.statements,hidden,active,dynamic)
            if value.default is not None:scan(value.default.statements,hidden,active,dynamic)
            return
        if isinstance(value,ast.BinaryExpression) and value.op.name in ('&&','||'):
            scan(value.lhs,hidden,controlled,dynamic)
            scan(value.rhs,hidden,True,dynamic);return
        if isinstance(value,ast.BranchingStatement):
            scan(value.condition,hidden,controlled,dynamic)
            active=controlled or depends(value.condition)
            scan(value.if_block,hidden,active,dynamic);scan(value.else_block,hidden,active,dynamic);return
        if isinstance(value,(ast.ForInLoop,ast.WhileLoop)):
            control=value.set_declaration if isinstance(value,ast.ForInLoop) else value.while_condition
            scan(control,hidden,controlled,dynamic)
            local=set(hidden);local_dynamic=set(dynamic)
            if isinstance(value,ast.ForInLoop):local.add(value.identifier.name)
            dynamic=depends(control) or getattr(value,'_quantum_runtime_for',False)
            if isinstance(value,ast.ForInLoop) and dynamic:local_dynamic.add(value.identifier.name)
            scan(value.block,local,controlled or isinstance(value,ast.WhileLoop) or dynamic,local_dynamic);return
        if is_dataclass(value):
            for field in fields(value):
                if field.name not in ('span','annotations'):scan(getattr(value,field.name),hidden,controlled,dynamic)

    # Dependency closure: reading a runtime array makes a destination runtime.
    while True:
        before=set(selected);constants.clear()
        for statement in program.statements:remember(statement);scan(statement)
        if before==selected:break
    if not selected:return []
    if len(selected)>4096:raise ValueError('Runtime storage exceeds 4096 array declarations.')
    constants.clear()

    def marker(info, indices, source, prefix=False):
        if (not 1<=len(indices)<=len(info['dimensions']) if prefix else len(indices)!=len(info['dimensions'])) or any(isinstance(i, (ast.RangeDefinition, ast.DiscreteSet)) for i in indices):
            raise error_at(source, 'Runtime array element access requires one scalar index per dimension.')
        node = ast.Identifier(info['backing'][0] if info['backing'] else '_qa_empty_' + str(info['id']))
        node._quantum_array = dict(info)
        span = getattr(source, 'span', None)
        if span is not None:
            node._quantum_array['source'] = 'line %d:%d array %s' % (span.start_line, span.start_column, info['name'])
        node._quantum_array_indices = indices
        node.span = getattr(source, 'span', None)
        return node

    def expression(value,hidden=frozenset()):
        if isinstance(value,tuple):return tuple(expression(item,hidden) for item in value)
        if isinstance(value,(ast.SubroutineDefinition,ast.QuantumGateDefinition)):return value
        if isinstance(value,list):
            local=set(hidden);result=[]
            for item in value:
                if isinstance(item,(ast.ClassicalDeclaration,ast.ConstantDeclaration)):local.add(item.identifier.name)
                result.append(expression(item,local))
            return result
        if isinstance(value,(ast.ClassicalDeclaration,ast.ConstantDeclaration)):
            value.type=expression(value.type,hidden)
            value.init_expression=expression(value.init_expression,hidden|{value.identifier.name})
            return value
        if isinstance(value,(ast.IndexedIdentifier,ast.IndexExpression)):
            name,indices=reference(value)
            if name in arrays and name not in hidden:return marker(arrays[name],[expression(i,hidden) for i in indices],value)
        if isinstance(value,ast.SizeOf):
            name,indices=reference(value.target)
            if name in arrays and name not in hidden and indices:
                if value.index is not None and constant(value.index)!=0:raise error_at(value,'Singleton slice extent supports axis zero.')
                if any(not isinstance(i,ast.RangeDefinition) or i.step is not None or i.start!=i.end for i in indices):raise error_at(value,'Runtime sizeof slices currently require singleton ranges.')
                node=marker(arrays[name],[expression(i.start,hidden) for i in indices],value,prefix=True)
                node._quantum_array_extent=True
                return node
            if name in arrays and name not in hidden and not indices:
                axis=0 if value.index is None else constant(value.index)
                if not 0<=axis<len(arrays[name]['dimensions']):raise error_at(value,'sizeof axis is outside the array rank.')
                return ast.IntegerLiteral(arrays[name]['dimensions'][axis])
        if isinstance(value,ast.Identifier) and value.name in arrays and value.name not in hidden:
            raise error_at(value,'A whole runtime array requires an array reference or collection operation.')
        if isinstance(value,ast.ForInLoop):
            value.set_declaration=expression(value.set_declaration,hidden)
            value.block=expression(value.block,hidden|{value.identifier.name});return value
        if is_dataclass(value):
            for field in fields(value):
                if field.name not in ('span','annotations'):setattr(value,field.name,expression(getattr(value,field.name),hidden))
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
        remember(statement)
        if not isinstance(statement, ast.ClassicalDeclaration) or not isinstance(statement.type, ast.ArrayType) or statement.identifier.name not in selected:
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
        if size>4096-charged:raise error_at(statement,'Runtime scalar and array storage exceeds 4096 slots.')
        charged+=size
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
