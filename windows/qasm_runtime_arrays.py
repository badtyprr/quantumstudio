"""Lower global runtime arrays to typed backing slots and checked selections."""
import copy
from dataclasses import dataclass, fields, is_dataclass
import openqasm3.ast as ast
from qasm_source_diagnostics import error_at
from qasm_runtime_wires import SourceQuantumRegisterView
from pyqasm.expressions import Qasm3ExprEvaluator


def split_reference(value):
    """Keep each bracket group intact while finding its backing expression."""
    groups=[];root=value
    while isinstance(root,(ast.IndexExpression,ast.IndexedIdentifier)):
        if isinstance(root,ast.IndexExpression):
            groups.insert(0,root.index if isinstance(root.index,list) else [root.index]);root=root.collection
        else:groups[0:0]=root.indices;root=root.name
    return root,groups


def array_selector_groups(groups,rank):
    """Consume consecutive brackets across remaining array dimensions first.

    This preserves the pinned importer multidimensional shorthand a[i][j].
    Once all dimensions are supplied, later brackets select the resulting view.
    """
    result=[];pending=[]
    for group in groups:
        pending.extend(group)
        if len(pending)>=rank:
            result.append(pending)
            rank-=sum(not isinstance(axis,ast.RangeDefinition) for axis in pending)
            pending=[]
    if pending:result.append(pending)
    return result


@dataclass
class SourceArrayView(ast.Expression):
    name: str
    element_type: object
    parent: object
    axes: list
    writable: bool = True

    @property
    def rank(self):return sum(isinstance(axis,ast.RangeDefinition) for axis in self.axes)


@dataclass
class ArrayCopyStatement(ast.Statement):
    destination: object
    sources: list


@dataclass
class ArrayReferenceCheck(ast.Statement):
    views: list
    shapes: list


@dataclass
class ArrayView:
    array: int
    parent: object
    axes: list
    writable: bool = True

    @property
    def rank(self):
        return sum(isinstance(axis, ast.RangeDefinition) for axis in self.axes)


def map_view(view, transform):
    """Visit geometry in parent/start/step/stop evaluation order."""
    if view is None:return None
    parent=map_view(view.parent,transform)
    axes=[]
    for axis in view.axes:
        if isinstance(axis,ast.RangeDefinition):
            axes.append(ast.RangeDefinition(start=None if axis.start is None else transform(axis.start),
                step=None if axis.step is None else transform(axis.step),
                end=None if axis.end is None else transform(axis.end)))
        else:axes.append(transform(axis))
    return ArrayView(view.array,parent,axes,view.writable)


def view_document(view, integer):
    result=dict(Array=view.array,Writable=view.writable,Axes=[])
    if view.parent is not None:result['Parent']=view_document(view.parent,integer)
    for axis in view.axes:
        if isinstance(axis,ast.RangeDefinition):
            result['Axes'].append(dict(Scalar=False,**{name:integer(value) for name,value in
                [('Start',axis.start),('Step',axis.step),('Stop',axis.end)] if value is not None}))
        else:result['Axes'].append(dict(Scalar=True,Start=integer(axis)))
    return result


def selection(node, integer):
    info = node._quantum_array
    result=dict(Array=info['id'], Indices=[integer(index) for index in node._quantum_array_indices], Source=info['source'])
    if hasattr(node,'_quantum_array_view'):result['View']=view_document(node._quantum_array_view,integer)
    return result


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
        root,groups=split_reference(value)
        return (root.name if isinstance(root,ast.Identifier) else None),[index for group in groups for index in group]

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
        if (isinstance(value,ast.ClassicalDeclaration) and isinstance(value.type,scalar+(ast.BitType,))
                or isinstance(value,ast.ClassicalAssignment) and reference(value.lvalue)[0] not in names):
            # Scalar destinations execute in the worker, including constant-index
            # reads. Keep array element widths and definedness at that boundary.
            source=value.init_expression if isinstance(value,ast.ClassicalDeclaration) else value.rvalue
            for item in walk(source):
                if isinstance(item,(ast.IndexExpression,ast.IndexedIdentifier)):
                    name,_=reference(item)
                    if name in names-hidden:selected.add(name)
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
                if deferred or negative or depends(indices) or any(isinstance(i,ast.RangeDefinition) for i in indices):selected.add(name)
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

    def bound_view(value,hidden):
        if value.name not in arrays:raise error_at(value,'Array reference backing declaration is unavailable.')
        info=arrays[value.name];info['views']=True
        parent=bound_view(value.parent,hidden)[1] if value.parent is not None else None
        return info,ArrayView(info['id'],parent,[expression(axis,hidden) for axis in value.axes],value.writable)

    def sliced(value,hidden,force=False):
        root,groups=split_reference(value)
        if isinstance(root,SourceArrayView):
            info,parent=bound_view(root,hidden);rank=parent.rank
        else:
            if not isinstance(root,ast.Identifier) or root.name not in arrays or root.name in hidden:return None
            if not force and not any(isinstance(axis,ast.RangeDefinition) for group in groups for axis in group):return None
            info=arrays[root.name];rank=len(info['dimensions']);parent=None
        if len(groups)>32:raise error_at(value,'Array views exceed 32 nesting levels.')
        for group in array_selector_groups(groups,rank):
            if len(group)>rank:raise error_at(value,'Array view has more selectors than axes.')
            group=list(group)+[ast.RangeDefinition(start=None,end=None,step=None) for _ in range(rank-len(group))]
            if any(isinstance(axis,ast.DiscreteSet) for axis in group):raise error_at(value,'Array views require scalar or range selectors.')
            parent=ArrayView(info['id'],parent,[expression(axis,hidden) for axis in group],parent.writable if parent else True);rank=parent.rank
        info['views']=True
        return info,parent

    def expression(value,hidden=frozenset()):
        if isinstance(value,ArrayCopyStatement):
            info,value.destination=bound_view(value.destination,hidden);info['copies']=True
            value.sources=[bound_view(source,hidden)[1] for source in value.sources];return value
        if isinstance(value,SourceQuantumRegisterView):
            value.view=None
            value.selections=expression(value.selections,hidden)
            return value
        if isinstance(value,SourceArrayView):
            info,view=bound_view(value,hidden)
            if view.rank:raise error_at(value,'A whole array view requires a reference, copy or collection operation.')
            node=marker(info,[ast.IntegerLiteral(0)]*len(info['dimensions']),value)
            node._quantum_array_indices=[];node._quantum_array_view=view
            return node
        if isinstance(value,ArrayReferenceCheck):
            value.views=[bound_view(view,hidden)[1] for view in value.views];return value
        if isinstance(value,ast.ClassicalAssignment):
            chosen=sliced(value.lvalue,hidden)
            if chosen is not None and not chosen[1].writable:raise error_at(value,'Cannot write through a readonly array reference.')
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
            chosen=sliced(value,hidden)
            if chosen is not None:
                info,view=chosen
                if view.rank:raise error_at(value,'An array view requires a reference, copy or collection operation.')
                node=marker(info,[ast.IntegerLiteral(0)]*len(info['dimensions']),value)
                node._quantum_array_indices=[];node._quantum_array_view=view
                return node
            name,indices=reference(value)
            if name in arrays and name not in hidden:return marker(arrays[name],[expression(i,hidden) for i in indices],value)
        if isinstance(value,ast.SizeOf):
            prior_name,prior=reference(value.target)
            direct=isinstance(value.target,ast.IndexExpression) and isinstance(value.target.collection,ast.Identifier) or isinstance(value.target,ast.IndexedIdentifier) and len(value.target.indices)==1
            singleton=direct and prior_name in arrays and prior and (value.index is None or constant(value.index)==0) and all(isinstance(i,ast.RangeDefinition) and i.step is None and i.start==i.end and i.start is not None for i in prior)
            chosen=bound_view(value.target,hidden) if isinstance(value.target,SourceArrayView) else None if singleton else sliced(value.target,hidden,force=bool(prior))
            if chosen is not None:
                info,view=chosen;axis=0 if value.index is None else constant(value.index)
                if not 0<=axis<view.rank:raise error_at(value,'sizeof axis is outside the array view rank.')
                node=marker(info,[ast.IntegerLiteral(0)]*len(info['dimensions']),value)
                node._quantum_array_indices=[];node._quantum_array_view=view
                node._quantum_array_extent=True;node._quantum_view_axis=axis
                return node
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
