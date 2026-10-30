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
from qasm_runtime_wires import WireReferenceCheck, QuantumSelectorTypeCheck, SourceQuantumSelection, SourceQuantumRegisterView
from qasm_runtime_arrays import SourceArrayView, ArrayReferenceCheck, ArrayCopyStatement, split_reference, array_selector_groups
from qasm_runtime_bit_aliases import BitAliases, SourceBitAlias


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
    quantum_backings={}; global_alias_bindings={}; global_alias_names=set(); static_quantum_aliases={}; quantum_view_count=0
    bit_storage = []; array_temporaries=[]; array_backing_types={}
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
        if isinstance(value,ast.IndexedIdentifier) and isinstance(bindings.get(value.name.name),SourceQuantumRegisterView):
            result=rewrite(value.name,bindings,lexical)
            for group in value.indices:result=ast.IndexExpression(collection=result,index=rewrite(group,bindings,lexical))
            return result
        if isinstance(value,ast.IndexedIdentifier) and isinstance(bindings.get(value.name.name),(SourceArrayView,SourceBitAlias)):
            result=rewrite(value.name,bindings,lexical)
            for group in value.indices:result=ast.IndexExpression(collection=result,index=rewrite(group,bindings,lexical))
            return result
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

    def quantum_key(value, required=True):
        if isinstance(value, ast.IndexExpression) and isinstance(value.collection, ast.Identifier):
            value = ast.IndexedIdentifier(name=value.collection, indices=[value.index])
        if isinstance(value, ast.Identifier) and register_size(value.name) == 1:
            return value.name, 0
        if isinstance(value, ast.IndexedIdentifier) and len(value.indices) == 1 and len(value.indices[0]) == 1:
            index = value.indices[0][0]
            size = register_size(value.name.name)
            if isinstance(index, ast.IntegerLiteral) and size is not None:
                if not 0 <= index.value < size:
                    raise error_at(value,'Quantum register index is out of bounds.')
                return value.name.name, index.value
        if required:raise error_at(value, 'Runtime call quantum arguments require a scalar qubit or a fixed literal register index.')
        return None

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

    def capture_scalar_qubit(actual):
        """Check the caller selector before saving it or evaluating later actuals."""
        check_quantum_name(actual)
        actual=copy.deepcopy(actual)
        prefix=[]
        if isinstance(actual,SourceQuantumRegisterView):
            prefix.append(ArrayReferenceCheck(views=[copy.deepcopy(actual.view)],shapes=[[1]]))
            actual=SourceQuantumSelection(register=copy.deepcopy(actual.register),index=SourceArrayView(name=actual.view.name,element_type=actual.view.element_type,parent=copy.deepcopy(actual.view),axes=[ast.IntegerLiteral(0)],writable=False))
        check=WireReferenceCheck(targets=[copy.deepcopy(actual)]);check.span=getattr(actual,'span',None)
        effects=prefix+[check]
        if isinstance(actual,SourceQuantumSelection):
            slot=ast.Identifier(fresh());runtime.add(slot.name)
            effects.append(ast.ClassicalDeclaration(type=ast.IntType(size=ast.IntegerLiteral(32)),identifier=slot,init_expression=copy.deepcopy(actual.index)))
            actual.index=copy.deepcopy(slot)
            return effects,actual
        if isinstance(actual,ast.IndexExpression) and isinstance(actual.collection,ast.Identifier):
            actual=ast.IndexedIdentifier(name=actual.collection,indices=[actual.index])
        if isinstance(actual,ast.IndexedIdentifier):
            if len(actual.indices)!=1 or len(actual.indices[0])!=1 or isinstance(actual.indices[0][0],(ast.RangeDefinition,ast.DiscreteSet)):
                raise error_at(actual,'Scalar quantum arguments require one integer selector.')
            slot=ast.Identifier(fresh());runtime.add(slot.name)
            effects.append(ast.ClassicalDeclaration(type=ast.IntType(size=ast.IntegerLiteral(32)),identifier=slot,
                init_expression=copy.deepcopy(actual.indices[0][0])))
            actual.indices=[[copy.deepcopy(slot)]]
        elif not isinstance(actual,ast.Identifier):
            raise error_at(actual,'Scalar quantum arguments require a qubit reference.')
        return effects,actual

    def register_view_binding(formal,actual,constant_bindings,active,depth,alias_depth=0):
        nonlocal quantum_view_count
        quantum_view_count+=1
        if quantum_view_count>4096 or alias_depth>=32:raise error_at(actual,'Quantum reference expansion exceeds 4096 views or 32 alias levels.')
        check_quantum_name(actual)
        if isinstance(actual,ast.Concatenation):
            effects,binding=concatenate_quantum_views(actual,active,depth)
            if formal is None:return effects,binding,None
            suffix,binding,width=register_view_binding(formal,binding,constant_bindings,active,depth)
            return effects+suffix,binding,width
        root,groups=split_reference(actual)
        groups=[group if isinstance(group,list) else [group] for group in groups]
        if isinstance(root,ast.Identifier) and root.name in static_quantum_aliases:
            selected=copy.deepcopy(static_quantum_aliases[root.name])
            for group in groups:selected=ast.IndexExpression(collection=selected,index=copy.deepcopy(group))
            return register_view_binding(formal,selected,constant_bindings,active,depth,alias_depth+1)
        if isinstance(root,ast.Concatenation):
            effects,binding=concatenate_quantum_views(root,active,depth)
            selected=binding
            for group in groups:selected=ast.IndexExpression(collection=selected,index=copy.deepcopy(group))
            suffix,binding,width=register_view_binding(formal,selected,constant_bindings,active,depth,alias_depth+1)
            return effects+suffix,binding,width
        if isinstance(root,SourceQuantumRegisterView):
            register=copy.deepcopy(root.register);selected=copy.deepcopy(root.view)
        elif isinstance(root,ast.Identifier) and root.name in register_declarations:
            register=[ast.Identifier(name) for name in register_declarations];width=register_size(root.name)
            offset=0
            for name in register_declarations:
                if name==root.name:break
                offset+=register_size(name)
            if root.name not in quantum_backings:
                name=fresh();type_=ast.ArrayType(base_type=ast.UintType(size=ast.IntegerLiteral(32)),dimensions=[ast.IntegerLiteral(width)])
                array_temporaries.append(ast.ClassicalDeclaration(type=type_,identifier=ast.Identifier(name),init_expression=ast.ArrayLiteral(values=[ast.IntegerLiteral(offset+i) for i in range(width)])))
                quantum_backings[root.name]=name;array_backing_types[name]=type_;collection_arrays.add(name)
            name=quantum_backings[root.name];collection_scopes[-1][name]=array_backing_types[name];array_scopes[-1].add(name)
            selected=ast.Identifier(name)
        else:return None
        if any(isinstance(axis,ast.DiscreteSet) for group in groups for axis in group):
            if not groups or len(groups[0])!=1 or not isinstance(groups[0][0],ast.DiscreteSet):raise error_at(actual,'Quantum index sets require one register axis.')
            values=groups[0][0].values
            if not 1<=len(values)<=25:raise error_at(actual,'Quantum index sets require 1 to 25 entries.')
            parts=[ast.IndexExpression(collection=copy.deepcopy(root),index=[copy.deepcopy(value)]) for value in values]
            joined=parts[0]
            for part in parts[1:]:joined=ast.Concatenation(lhs=joined,rhs=part)
            prefix,binding,_=register_view_binding(None,joined,constant_bindings,active,depth)
            selected=binding
            for group in groups[1:]:selected=ast.IndexExpression(collection=selected,index=copy.deepcopy(group))
            suffix,binding,width=register_view_binding(formal,selected,constant_bindings,active,depth)
            return prefix+suffix,binding,width
        for group in groups:selected=ast.IndexExpression(collection=selected,index=copy.deepcopy(group))
        effects,view=capture_array_view(selected,True,depth,nonnegative=True,quantum=True)
        if formal is None:
            if view.rank==0:
                axis=view.axes[-1];view.axes[-1]=ast.RangeDefinition(start=copy.deepcopy(axis),end=copy.deepcopy(axis),step=None)
            if view.rank!=1:raise error_at(actual,'Quantum aliases require a one-dimensional register selection.')
            first=SourceArrayView(name=view.name,element_type=view.element_type,parent=copy.deepcopy(view),axes=[ast.RangeDefinition(start=ast.IntegerLiteral(0),end=ast.IntegerLiteral(0),step=None)],writable=False)
            effects.append(ArrayReferenceCheck(views=[first],shapes=[[]]))
            return effects,SourceQuantumRegisterView(register=register,view=view,selections=[]),None
        width=quantum_width(formal.size,constant_bindings)
        effects.append(ArrayReferenceCheck(views=[copy.deepcopy(view)],shapes=[[width]]))
        selections=[SourceQuantumSelection(register=copy.deepcopy(register),index=SourceArrayView(name=view.name,element_type=view.element_type,parent=copy.deepcopy(view),axes=[ast.IntegerLiteral(i)],writable=False)) for i in range(width)]
        return effects,SourceQuantumRegisterView(register=register,view=view,selections=selections),width

    def concatenate_quantum_views(actual,active,depth):
        parts=[]
        def flatten(value,level=0):
            if level>=32:raise error_at(actual,'Quantum concatenation exceeds 32 nesting levels.')
            if isinstance(value,ast.Concatenation):flatten(value.lhs,level+1);flatten(value.rhs,level+1)
            else:parts.append(value)
            if len(parts)>25:raise error_at(actual,'Quantum concatenation supports at most 25 parts.')
        flatten(actual)
        effects=[];views=[]
        for part in parts:
            captured=register_view_binding(None,part,{},True,depth)
            if captured is None:raise error_at(part,'Dynamic quantum concatenation requires declared registers or captured views.')
            prefix,view,_=captured;effects.extend(prefix);views.append(view)
        name=fresh();type_=ast.ArrayType(base_type=ast.UintType(size=ast.IntegerLiteral(32)),dimensions=[ast.IntegerLiteral(25)])
        array_temporaries.append(ast.ClassicalDeclaration(type=type_,identifier=ast.Identifier(name),init_expression=None));array_backing_types[name]=type_;collection_arrays.add(name)
        total=ast.Identifier(fresh());runtime.add(total.name)
        effects.append(ast.ClassicalDeclaration(type=ast.IntType(size=ast.IntegerLiteral(32)),identifier=total,init_expression=ast.IntegerLiteral(0)))
        for view in views:
            start=ast.Identifier(fresh());runtime.add(start.name)
            effects.append(ast.ClassicalDeclaration(type=ast.IntType(size=ast.IntegerLiteral(32)),identifier=start,init_expression=copy.deepcopy(total)))
            effects.append(ast.ClassicalAssignment(lvalue=copy.deepcopy(total),op=ast.AssignmentOperator['+='],rvalue=ast.SizeOf(target=copy.deepcopy(view.view),index=ast.IntegerLiteral(0))))
            destination=SourceArrayView(name=name,element_type=copy.deepcopy(type_.base_type),parent=None,axes=[ast.RangeDefinition(start=start,end=ast.BinaryExpression(op=ast.BinaryOperator['-'],lhs=copy.deepcopy(total),rhs=ast.IntegerLiteral(1)),step=None)])
            effects.append(ArrayReferenceCheck(views=[copy.deepcopy(destination)],shapes=[[]]))
            effects.append(ArrayCopyStatement(destination=destination,sources=[copy.deepcopy(view.view)]))
        view=SourceArrayView(name=name,element_type=copy.deepcopy(type_.base_type),parent=None,axes=[ast.RangeDefinition(start=ast.IntegerLiteral(0),end=ast.BinaryExpression(op=ast.BinaryOperator['-'],lhs=copy.deepcopy(total),rhs=ast.IntegerLiteral(1)),step=None)],writable=False)
        register=[ast.Identifier(name) for name in register_declarations]
        left=ast.Identifier(fresh());right=ast.Identifier(fresh());runtime.update((left.name,right.name))
        def selected(index):return SourceQuantumSelection(register=copy.deepcopy(register),index=SourceArrayView(name=name,element_type=copy.deepcopy(type_.base_type),parent=copy.deepcopy(view),axes=[copy.deepcopy(index)],writable=False))
        check=WireReferenceCheck(targets=[selected(left),selected(right)]);check.span=actual.span
        def loop(cursor,start,body):
            result=ast.ForInLoop(type=ast.IntType(size=ast.IntegerLiteral(32)),identifier=cursor,set_declaration=ast.RangeDefinition(start=start,end=ast.BinaryExpression(op=ast.BinaryOperator['-'],lhs=copy.deepcopy(total),rhs=ast.IntegerLiteral(1)),step=None),block=body)
            result._quantum_runtime_for=True;result.span=actual.span;return result
        effects.append(loop(left,ast.IntegerLiteral(0),[loop(right,ast.BinaryExpression(op=ast.BinaryOperator['+'],lhs=copy.deepcopy(left),rhs=ast.IntegerLiteral(1)),[check])]))
        return effects,SourceQuantumRegisterView(register=register,view=view,selections=[])

    def is_array_target(value):
        value,_=split_reference(value)
        return isinstance(value,SourceArrayView) or isinstance(value,ast.Identifier) and value.name in array_scopes[-1] and isinstance(collection_scopes[-1].get(value.name),ast.ArrayType)

    def capture_array_view(actual,active,depth,capture=True,nonnegative=False,quantum=False):
        root,groups=split_reference(actual);effects=[]
        if isinstance(root,SourceArrayView):view=copy.deepcopy(root)
        else:
            declared=collection_scopes[-1].get(root.name) if isinstance(root,ast.Identifier) else None
            if not isinstance(declared,ast.ArrayType) or root.name not in array_scopes[-1]:raise error_at(actual,'Array arguments require an array reference.')
            collection_arrays.add(root.name)
            view=SourceArrayView(name=root.name,element_type=copy.deepcopy(declared.base_type),parent=None,
                axes=[ast.RangeDefinition(start=None,end=None,step=None) for _ in declared.dimensions])
        view.span=getattr(actual,'span',None)
        if len(groups)>31:raise error_at(actual,'Array references exceed 32 nesting levels.')
        for group_index,group in enumerate(array_selector_groups(groups,view.rank)):
            if len(group)>view.rank:raise error_at(actual,'Too many array selectors.')
            axes=[ast.RangeDefinition(start=None,end=None,step=None) for _ in range(view.rank)]
            child=SourceArrayView(name=view.name,element_type=view.element_type,parent=None if group_index==0 and isinstance(root,ast.Identifier) else view,axes=axes,writable=view.writable)
            child.span=getattr(actual,'span',None)
            if not capture:
                for index,axis in enumerate(group):
                    if isinstance(axis,ast.DiscreteSet):raise error_at(actual,'Array references require scalar or range selectors.')
                    axes[index]=copy.deepcopy(axis)
                view=child;continue
            for index,axis in enumerate(group):
                if isinstance(axis,ast.DiscreteSet):raise error_at(actual,'Array references require scalar or range selectors.')
                scalar=not isinstance(axis,ast.RangeDefinition)
                for field,value in [('scalar',axis)] if scalar else [('start',axis.start),('step',axis.step),('end',axis.end)]:
                    if value is None:continue
                    prefix,value=expression_calls(value,active,depth);effects.extend(prefix)
                    if quantum:effects.append(QuantumSelectorTypeCheck(index=copy.deepcopy(value)))
                    if scalar:axes[index]=value
                    else:setattr(axes[index],field,value)
                    # Validate before narrowing or evaluating a later selector's calls.
                    probe=copy.deepcopy(child)
                    if field=='step' and probe.axes[index].end is None:
                        # The source parser requires a stop for stepped ranges.
                        # Check the step on a singleton at the effective start;
                        # the real stop is evaluated and checked next.
                        start=probe.axes[index].start
                        if start is None:
                            negative=ast.Cast(type=ast.IntType(),argument=ast.BinaryExpression(op=ast.BinaryOperator['<'],lhs=copy.deepcopy(value),rhs=ast.IntegerLiteral(0)))
                            last=ast.BinaryExpression(op=ast.BinaryOperator['-'],lhs=ast.Cast(type=ast.IntType(),argument=ast.SizeOf(target=copy.deepcopy(view),index=ast.IntegerLiteral(index))),rhs=ast.IntegerLiteral(1))
                            start=ast.BinaryExpression(op=ast.BinaryOperator['*'],lhs=negative,rhs=last)
                        probe.axes[index].end=copy.deepcopy(start)
                    if probe.rank==0:
                        # Address-only validation of a scalar selection retains
                        # one singleton axis; it never reads the selected value.
                        probe.axes[-1]=ast.RangeDefinition(start=copy.deepcopy(probe.axes[-1]),end=copy.deepcopy(probe.axes[-1]),step=None)
                    effects.append(ArrayReferenceCheck(views=[probe],shapes=[[]]))
                    if nonnegative and field!='step':
                        # Check the original integer expression before adding a
                        # cast: implicit float-to-index conversion is forbidden.
                        unsigned=copy.deepcopy(probe)
                        converted=ast.Cast(type=ast.UintType(size=ast.IntegerLiteral(64)),argument=copy.deepcopy(value))
                        if scalar:unsigned.axes[index]=ast.RangeDefinition(start=converted,end=copy.deepcopy(converted),step=None)
                        else:setattr(unsigned.axes[index],field,converted)
                        effects.append(ArrayReferenceCheck(views=[unsigned],shapes=[[]]))
                    slot=ast.Identifier(fresh());runtime.add(slot.name)
                    if field=='step':
                        # A stride larger than any backing dimension selects at
                        # most one element. Clamp magnitude before signed storage
                        # so UINT64_MAX cannot silently reverse the direction.
                        effects.append(ast.ClassicalDeclaration(type=ast.IntType(),identifier=slot,init_expression=None))
                        def assign(expression):return ast.ClassicalAssignment(lvalue=copy.deepcopy(slot),op=ast.AssignmentOperator['='],rvalue=expression)
                        below=ast.BranchingStatement(condition=ast.BinaryExpression(op=ast.BinaryOperator['<'],lhs=ast.Cast(type=ast.IntType(),argument=copy.deepcopy(value)),rhs=ast.UnaryExpression(op=ast.UnaryOperator['-'],expression=ast.IntegerLiteral(4096))),
                            if_block=[assign(ast.UnaryExpression(op=ast.UnaryOperator['-'],expression=ast.IntegerLiteral(4097)))],else_block=[assign(value)])
                        effects.append(ast.BranchingStatement(condition=ast.BinaryExpression(op=ast.BinaryOperator['>'],lhs=copy.deepcopy(value),rhs=ast.IntegerLiteral(4096)),
                            if_block=[assign(ast.IntegerLiteral(4097))],else_block=[below]))
                    else:effects.append(ast.ClassicalDeclaration(type=ast.IntType(),identifier=slot,init_expression=value))
                    if scalar:axes[index]=slot
                    else:setattr(axes[index],field,slot)
            view=child
        return effects,view

    def array_signature(type_):
        if not isinstance(type_,scalar):raise error_at(type_,'Runtime arrays support int, uint, bool, float and angle elements.')
        width=1 if isinstance(type_,ast.BoolType) else (64 if isinstance(type_,(ast.FloatType,ast.AngleType)) else 0) if type_.size is None else collection_integer(type_.size,{})
        return type(type_),width

    def array_rank(value):
        root,groups=split_reference(value)
        rank=root.rank if isinstance(root,SourceArrayView) else len(collection_scopes[-1][root.name].dimensions)
        for group in array_selector_groups(groups,rank):
            if len(group)>rank:raise error_at(value,'Too many array selectors.')
            rank-=sum(not isinstance(axis,ast.RangeDefinition) for axis in group)
        return rank

    def literal_array(value,element_type,active,depth):
        def flatten(node):
            if not isinstance(node,ast.ArrayLiteral):return [],[node]
            if len(node.values)>4096:raise error_at(node,'Array literal dimension exceeds 4096.')
            children=[flatten(child) for child in node.values]
            tail=children[0][0] if children else []
            if any(shape!=tail for shape,_ in children):raise error_at(node,'Array literal has inconsistent nested shape.')
            return [len(children)]+tail,[item for _,items in children for item in items]
        shape,values=flatten(value)
        if not 1<=len(shape)<=7:raise error_at(value,'Array literals require one to seven dimensions.')
        name=fresh();type_=ast.ArrayType(base_type=copy.deepcopy(element_type),dimensions=[ast.IntegerLiteral(size) for size in shape])
        array_temporaries.append(ast.ClassicalDeclaration(type=type_,identifier=ast.Identifier(name),init_expression=None));collection_arrays.add(name);array_backing_types[name]=type_
        effects=[]
        for offset,item in enumerate(values):
            prefix,item=expression_calls(item,active,depth);effects.extend(prefix)
            indices=[];position=offset
            for size in reversed(shape):indices.insert(0,ast.IntegerLiteral(position%size));position//=size
            assignment=ast.ClassicalAssignment(lvalue=ast.IndexedIdentifier(name=ast.Identifier(name),indices=[indices]),op=ast.AssignmentOperator['='],rvalue=item)
            assignment.span=getattr(value,'span',None);effects.append(assignment)
        return effects,SourceArrayView(name=name,element_type=element_type,parent=None,axes=[ast.RangeDefinition(start=None,end=None,step=None) for _ in shape],writable=False)

    def array_copy(target,value,active,depth):
        effects,destination=capture_array_view(target,active,depth)
        if not destination.rank or not destination.writable:raise error_at(target,'Array copy needs a writable array destination.')
        effects.append(ArrayReferenceCheck(views=[copy.deepcopy(destination)],shapes=[[]]))
        operands=[]
        def flatten(node):
            if isinstance(node,ast.Concatenation):flatten(node.lhs);flatten(node.rhs)
            else:operands.append(node)
        flatten(value)
        if len(operands)>64:raise error_at(value,'Array concatenation supports at most 64 sources.')
        sources=[]
        for position,operand in enumerate(operands):
            literal=isinstance(operand,ast.ArrayLiteral)
            prefix,source=literal_array(operand,destination.element_type,active,depth) if literal else capture_array_view(operand,active,depth);effects.extend(prefix)
            if source.rank!=destination.rank or array_signature(source.element_type)!=array_signature(destination.element_type):raise error_at(value,'Array copy ranks and element types must match.')
            if literal and isinstance(target,ast.Identifier):
                wanted=[collection_integer(size,{}) for size in array_backing_types[destination.name].dimensions]
                actual=[size.value for size in array_backing_types[source.name].dimensions]
                if wanted!=actual:raise error_at(value,'Array initializer shape does not match its declaration.')
            if not literal and any(isinstance(item,ast.FunctionCall) and item.name.name in functions for item in walk(operands[position+1:])):
                # A later operand may call a routine that mutates this backing.
                # Copy only this selection into an equally shaped private backing;
                # untouched/undefined cells outside the selection are never read.
                name=fresh();type_=copy.deepcopy(array_backing_types[source.name])
                array_temporaries.append(ast.ClassicalDeclaration(type=type_,identifier=ast.Identifier(name),init_expression=None));collection_arrays.add(name)
                captured=copy.deepcopy(source);current=captured
                while current is not None:current.name=name;current.writable=True;current=current.parent
                effects.append(ArrayCopyStatement(destination=captured,sources=[source]));source=copy.deepcopy(captured)
            source.writable=False;sources.append(source)
        effects.append(ArrayCopyStatement(destination=destination,sources=sources))
        return effects

    def array_binding(formal,actual,constant_bindings,active,depth,capture=True):
        effects,view=capture_array_view(actual,active,depth,capture)
        wanted=rewrite(formal.type,constant_bindings,lexical=True)
        if array_signature(wanted.base_type)!=array_signature(view.element_type):raise error_at(actual,'Array element type does not match the formal.')
        shape=[collection_integer(d,{}) for d in wanted.dimensions] if isinstance(wanted.dimensions,list) else []
        if any(not 0<=d<=4096 for d in shape):raise error_at(formal,'Array formal dimensions must be from 0 to 4096.')
        rank=len(shape) if shape else collection_integer(wanted.dimensions,{})
        if not 1<=rank<=7 or view.rank!=rank:raise error_at(actual,'Array reference rank does not match the formal.')
        if formal.access not in (ast.AccessControl.mutable,ast.AccessControl.readonly):raise error_at(formal,'Array formals require readonly or mutable access.')
        writable=formal.access==ast.AccessControl.mutable
        if writable and not view.writable:raise error_at(actual,'Cannot regain mutable access from a readonly reference.')
        view.writable=writable
        effects.append(ArrayReferenceCheck(views=[copy.deepcopy(view)],shapes=[shape]))
        return effects,view,shape

    def empty_scalar_qubit_helper(definition):
        return not definition.body and definition.return_type is None and bool(definition.arguments) and all(isinstance(formal,ast.QuantumArgument) and formal.size is None for formal in definition.arguments)

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
        if empty_scalar_qubit_helper(definition) and not any(isinstance(item,(ast.FunctionCall,SourceQuantumRegisterView,SourceQuantumSelection)) for item in walk(call.arguments)):
            if len(definition.arguments)>25:raise error_at(call,'Quantum reference checks support at most25 targets.')
            if len({formal.name.name for formal in definition.arguments})!=len(definition.arguments):raise error_at(call,'Duplicate subroutine parameter.')
            for actual in call.arguments:check_quantum_name(actual)
            check=WireReferenceCheck(targets=copy.deepcopy(call.arguments));check.span=call.span
            return [check],None
        references = {n.name for n in walk(definition) if isinstance(n, ast.Identifier)}
        constant_bindings = {name: constant_value(name) for name in references
                             if name in constants and constants[name][0] < visibility[call.name.name]}
        bindings = dict(constant_bindings)
        parameters = set(); declarations = []; qubits = set(); quantum_actuals=[]; quantum_widths=[]; needs_quantum_preflight=False; array_views=[]; array_shapes=[]
        check_only=not definition.body and definition.return_type is None and all(isinstance(formal,ast.ClassicalArgument) and isinstance(formal.type,ast.ArrayReferenceType) for formal in definition.arguments) and not any(isinstance(item,ast.FunctionCall) for item in walk(call.arguments))
        for formal, actual in zip(definition.arguments, call.arguments):
            # Capture each actual before evaluating the next actual's calls.
            # Hoisting all nested effects first changes error/measurement order.
            if isinstance(formal,ast.ClassicalArgument) and isinstance(formal.type,ast.ArrayReferenceType):
                name=formal.name.name
                if name in parameters:raise error_at(formal,'Duplicate subroutine parameter: '+name)
                effects,binding,shape=array_binding(formal,actual,constant_bindings,active,depth,capture=not check_only)
                if not check_only:declarations.extend(effects)
                bindings[name]=binding;array_views.append(binding);array_shapes.append(shape);parameters.add(name)
                continue
            if isinstance(formal,ast.QuantumArgument) and formal.size is not None and not (isinstance(actual,ast.Identifier) and actual.name in register_declarations):
                name=formal.name.name
                if name in parameters:raise error_at(formal,'Duplicate subroutine parameter: '+name)
                check_quantum_name(actual)
                width_bindings={key:value for key,value in constant_bindings.items() if key not in parameters}
                captured=register_view_binding(formal,actual,width_bindings,active,depth)
                if captured is not None:
                    effects,binding,width=captured;declarations.extend(effects)
                    quantum_actuals.append(copy.deepcopy(binding));quantum_widths.append(width);needs_quantum_preflight=True
                    bindings[name]=binding;parameters.add(name)
                    continue
            # Once the enclosing call is runtime, nested actual calls must also
            # execute in order rather than being folded by the static visitor.
            effects, actual = expression_calls(actual, True, depth)
            declarations.extend(effects)
            name = formal.name.name
            if name in parameters:
                raise error_at(formal, 'Duplicate subroutine parameter: ' + name)
            if isinstance(formal, ast.QuantumArgument):
                width_bindings = {key: value for key, value in constant_bindings.items() if key not in parameters}
                if formal.size is None:
                    fixed=quantum_key(actual,required=False)
                    identities={fixed} if fixed is not None else set()
                    if qubits.intersection(identities):
                        raise error_at(call,'Quantum subroutine arguments must not overlap.')
                    qubits.update(identities)
                    if identities:
                        binding,_=quantum_binding(formal,actual,width_bindings)
                    else:
                        needs_quantum_preflight=True
                        effects,binding=capture_scalar_qubit(actual)
                        declarations.extend(effects)
                    quantum_actuals.append(copy.deepcopy(binding));quantum_widths.append(1)
                elif not isinstance(actual,ast.Identifier) or actual.name not in register_arrays:
                    check_quantum_name(actual)
                    if isinstance(actual,ast.Identifier) and actual.name in register_declarations and actual.name not in register_arrays:
                        raise error_at(actual,'A register parameter requires a register reference.')
                    captured=register_view_binding(formal,actual,width_bindings,active,depth)
                    if captured is not None:
                        effects,binding,width=captured;declarations.extend(effects)
                    else:
                        width=quantum_width(formal.size,width_bindings)
                        check=WireReferenceCheck(targets=[copy.deepcopy(actual)],widths=[width]);check.span=call.span
                        declarations.append(check)
                        binding=copy.deepcopy(actual) if isinstance(actual,ast.Identifier) else ast.Identifier(fresh())
                        if not isinstance(actual,ast.Identifier):
                            declarations.append(ast.AliasStatement(target=copy.deepcopy(binding),value=copy.deepcopy(actual)))
                    quantum_actuals.append(copy.deepcopy(binding));quantum_widths.append(width);needs_quantum_preflight=True
                else:
                    binding, identities = quantum_binding(formal, actual, width_bindings)
                    if qubits.intersection(identities):
                        raise error_at(call, 'Quantum subroutine arguments must not overlap.')
                    qubits.update(identities)
                    quantum_actuals.extend(ast.IndexedIdentifier(name=ast.Identifier(register),indices=[[ast.IntegerLiteral(index)]]) for register,index in sorted(identities))
                    quantum_widths.extend([1]*len(identities))
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
        if needs_quantum_preflight:
            if sum(quantum_widths)>25:raise error_at(call,'Quantum calls support at most 25 referenced qubits.')
            check=WireReferenceCheck(targets=quantum_actuals,widths=quantum_widths);check.span=call.span;declarations.append(check)
        if len(array_views)>64:raise error_at(call,'Calls support at most 64 array references.')
        if array_views:declarations.append(ArrayReferenceCheck(views=copy.deepcopy(array_views),shapes=array_shapes))
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
            if isinstance(node,(ast.IndexExpression,ast.IndexedIdentifier)) and is_array_target(node):
                return True
            if isinstance(node, ast.Identifier) and node.name in runtime:
                return True
            if isinstance(node, ast.FunctionCall) and node.name.name in functions:
                definition = functions[node.name.name]
                if any(isinstance(a,ast.ClassicalArgument) and isinstance(a.type,ast.ArrayReferenceType) for a in definition.arguments):return True
                if empty_scalar_qubit_helper(definition):return True
                if definition.return_type is not None:
                    if any(isinstance(a, ast.QuantumArgument) for a in definition.arguments):
                        return True
                elif any(isinstance(n, ast.ReturnStatement) for n in walk(definition.body)):
                    # Explicit void returns need structured exit lowering.
                    return True
        return False

    def capture_range_bounds(bounds,depth):
        captured=copy.deepcopy(bounds);effects=[]
        # Capture in source order before any later bound's call effects. The
        # importer infers exact integer storage types after normalization.
        for field in ('start','step','end'):
            bound=getattr(captured,field)
            if bound is None:continue
            prefix,bound=expression_calls(bound,True,depth);effects.extend(prefix)
            slot=ast.Identifier(fresh());runtime.add(slot.name)
            capture=ast.ClassicalDeclaration(type=ast.IntType(),identifier=slot,init_expression=bound)
            capture._quantum_range_capture=True;effects.append(capture)
            setattr(captured,field,slot)
        return effects,captured

    def runtime_quantum_loop(node, env, active, depth):
        """Use runtime binding when literal call-loop expansion cannot preserve semantics."""
        nonlocal expanded
        active=active or any(isinstance(item,ast.Identifier) and item.name in runtime
                            for item in walk(rewrite(node.set_declaration,env)))
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
                    if empty_scalar_qubit_helper(functions[call.name.name]):continue
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

        def runtime_range():
            if not isinstance(node.set_declaration,ast.RangeDefinition) or not isinstance(node.type,(ast.IntType,ast.UintType)):
                raise error_at(node,'Quantum-call range loops require an integer binding and a range.')
            value=copy.copy(node);value.type=rewrite(node.type,env)
            effects,value.set_declaration=capture_range_bounds(rewrite(node.set_declaration,env),depth)
            binding=ast.Identifier(fresh());runtime.add(binding.name)
            inner=dict(env);inner[node.identifier.name]=binding;value.identifier=binding
            value.block=block(node.block,inner,True,depth,classical_names=(binding.name,),
                              collection_types={binding.name:copy.deepcopy(value.type)})
            value._quantum_runtime_for=True
            return effects+[value]

        def literal(value):
            sign = 1
            if isinstance(value, ast.UnaryExpression) and value.op.name == '-':
                sign = -1; value = value.expression
            if not isinstance(value, ast.IntegerLiteral) or type(value.value) is not int or value.value.bit_length() > 64:
                raise ValueError('Not a literal range')
            return sign * value.value

        domain = node.set_declaration
        if not isinstance(domain, ast.RangeDefinition) or not isinstance(node.type, (ast.IntType, ast.UintType)):
            raise error_at(node, 'Quantum-call index loops require integer literal ranges.')
        try:
            start, stop = literal(domain.start), literal(domain.end)
            step = 1 if domain.step is None else literal(domain.step)
        except ValueError:return runtime_range()
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
            return runtime_range()
        for child in walk(node.block):
            if isinstance(child, (ast.BreakStatement, ast.ContinueStatement, ast.ReturnStatement)):
                return runtime_range()
            if isinstance(child, (ast.ClassicalDeclaration, ast.ConstantDeclaration, ast.ForInLoop)) and child.identifier.name == name:
                return runtime_range()
            target = child.lvalue if isinstance(child, ast.ClassicalAssignment) else child.target if isinstance(child, ast.QuantumMeasurementStatement) else None
            if isinstance(target, ast.IndexedIdentifier): target = target.name
            if isinstance(target, ast.IndexExpression): target = target.collection
            if isinstance(target, ast.Identifier) and target.name == name:
                return runtime_range()
        cost = count * sum(1 for _ in walk(node.block))
        if count > 4096 or expanded + cost > 65536:
            return runtime_range()
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
        if isinstance(value,(ast.IndexExpression,ast.IndexedIdentifier)) and isinstance(split_reference(value)[0],SourceQuantumRegisterView):
            root,groups=split_reference(value);selected=copy.deepcopy(root.view)
            if len(groups)!=1 or len(groups[0])!=1 or isinstance(groups[0][0],(ast.RangeDefinition,ast.DiscreteSet)):
                raise error_at(value,'Indexed register formals require one scalar index.')
            prefix,index=expression_calls(groups[0][0],True,depth)
            raw=SourceQuantumSelection(register=copy.deepcopy(root.register),index=copy.deepcopy(index))
            check=WireReferenceCheck(targets=[raw]);check.span=getattr(value,'span',None);prefix.append(check)
            selected=ast.IndexExpression(collection=selected,index=[index])
            effects,view=capture_array_view(selected,True,depth,nonnegative=True,quantum=True)
            if view.rank:raise error_at(value,'Indexed register formals require one scalar index.')
            return prefix+effects,SourceQuantumSelection(register=copy.deepcopy(root.register),index=view)
        if isinstance(value,(ast.IndexExpression,ast.IndexedIdentifier)) and is_array_target(value) and any(isinstance(item,ast.FunctionCall) and item.name.name in functions for item in walk(value)):
            return capture_array_view(value,active,depth)
        if isinstance(value,ast.SizeOf) and is_array_target(value.target) and any(isinstance(item,ast.FunctionCall) and item.name.name in functions for item in walk(value.target)):
            effects,target=capture_array_view(value.target,active,depth)
            return effects,ast.SizeOf(target=target,index=copy.deepcopy(value.index))
        if isinstance(value,ast.RangeDefinition) and any(isinstance(item,ast.FunctionCall) and item.name.name in functions for item in walk(value)):
            return capture_range_bounds(value,depth)
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

    def block(body, parent, active=False, depth=0, declared=None, classical_names=(), collection_types=None):
        # Call actuals are resolved before expansion, even for unused formals.
        # Keep caller shadowing lexical; leaving a block restores the register.
        classical_scopes.append(set(classical_names))
        array_scopes.append(set(array_scopes[-1])-set(classical_names))
        geometry_scopes.append(dict(geometry_scopes[-1]))
        for name in classical_names:geometry_scopes[-1][name]=ast.Identifier(name)
        collection_scopes.append({name:type_ for name,type_ in collection_scopes[-1].items() if name not in classical_names})
        collection_scopes[-1].update(collection_types or {})
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

    def bit_collection_loop(node, reference, env, active, depth):
        root,groups=split_reference(reference)
        if isinstance(root,SourceBitAlias) or isinstance(reference,ast.Concatenation) or any(isinstance(axis,ast.DiscreteSet) for group in groups for axis in group):
            captured=bit_aliases.bind(reference,active,depth)
            if captured is not None:
                effects,alias=captured
                prefix,view=bit_aliases.snapshot(alias);effects.extend(prefix)
                effects.append(array_collection_loop(node,view,env,active,depth))
                return ast.CompoundStatement(statements=effects)
        type_=collection_scopes[-1].get(root.name) if isinstance(root,ast.Identifier) else None
        if not isinstance(type_,ast.BitType) or type_.size is None:return None
        width=collection_integer(type_.size,{})
        if not 1<=width<=64:raise error_at(node,'Bit collections require widths from 1 to 64.')
        name=fresh();backing=ast.ArrayType(base_type=ast.BoolType(),dimensions=[ast.IntegerLiteral(width)])
        array_temporaries.append(ast.ClassicalDeclaration(type=backing,identifier=ast.Identifier(name),init_expression=None));collection_arrays.add(name);array_backing_types[name]=backing
        collection_scopes[-1][name]=backing;array_scopes[-1].add(name)
        selected=ast.Identifier(name)
        for group in groups:
            if len(group)!=1 or not isinstance(group[0],ast.RangeDefinition):raise error_at(node,'Bit collection selection requires a one-dimensional slice.')
            axis=copy.deepcopy(group[0])
            selected=ast.IndexExpression(collection=selected,index=[axis])
        # Capture selector calls before reading the register's values.
        effects,view=capture_array_view(selected,active,depth,nonnegative=True)
        effects.append(ArrayReferenceCheck(views=[copy.deepcopy(view)],shapes=[[]]))
        for index in range(width):
            effects.append(ast.ClassicalAssignment(lvalue=ast.IndexedIdentifier(name=ast.Identifier(name),indices=[[ast.IntegerLiteral(index)]]),op=ast.AssignmentOperator['='],rvalue=ast.IndexExpression(collection=copy.deepcopy(root),index=[ast.IntegerLiteral(index)])))
        effects.append(array_collection_loop(node,view,env,active,depth))
        return ast.CompoundStatement(statements=effects)

    def array_collection_loop(node, reference, env, active, depth):
        """Capture geometry and selected values once before the first iteration."""
        if array_rank(reference)!=1:raise error_at(node,'Collection iteration requires a one-dimensional array or view.')
        if not isinstance(node.type,values):raise error_at(node,'Collection loops require a scalar binding.')
        binding_type=rewrite(node.type,env)
        if isinstance(binding_type,ast.BitType) and binding_type.size is not None and collection_integer(binding_type.size,env)!=1:raise error_at(node,'Bit collection bindings must have width one.')
        prefix,view=capture_array_view(reference,active,depth)
        name=fresh();type_=copy.deepcopy(array_backing_types[view.name])
        array_temporaries.append(ast.ClassicalDeclaration(type=type_,identifier=ast.Identifier(name),init_expression=None));collection_arrays.add(name)
        snapshot=copy.deepcopy(view);current=snapshot
        while current is not None:current.name=name;current.writable=True;current=current.parent
        prefix.append(ArrayCopyStatement(destination=snapshot,sources=[view]))
        cursor=ast.Identifier(fresh());binding=ast.Identifier(fresh());count=ast.Identifier(fresh())
        runtime.update((cursor.name,binding.name,count.name))
        prefix.append(ast.ClassicalDeclaration(type=ast.IntType(),identifier=count,init_expression=ast.SizeOf(target=copy.deepcopy(snapshot),index=ast.IntegerLiteral(0))))
        inner=dict(env);inner[node.identifier.name]=binding
        body=block(node.block,inner,active,depth,classical_names=(binding.name,),collection_types={binding.name:copy.deepcopy(binding_type)})
        declaration=ast.ClassicalDeclaration(type=binding_type,identifier=binding,init_expression=ast.IndexExpression(collection=copy.deepcopy(snapshot),index=[copy.deepcopy(cursor)]))
        if isinstance(binding_type,ast.BitType):declaration=bit_declaration(declaration)
        loop=ast.ForInLoop(type=ast.IntType(),identifier=cursor,set_declaration=ast.RangeDefinition(start=ast.IntegerLiteral(0),end=ast.BinaryExpression(op=ast.BinaryOperator['-'],lhs=count,rhs=ast.IntegerLiteral(1)),step=None),block=[declaration]+body)
        loop._quantum_runtime_for=True;loop.span=node.span
        return ast.CompoundStatement(statements=prefix+[loop])

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
        body = block(node.block, inner, active, depth, classical_names=(binding.name,),
            collection_types={binding.name: copy.deepcopy(binding_type)})
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

    def dynamic_alias_operation(operation,depth):
        if isinstance(operation,(ast.QuantumGate,ast.QuantumPhase)):
            operands=operation.qubits or []
            def replace(op,targets):op.qubits=targets
        elif isinstance(operation,ast.QuantumReset):
            operands=[operation.qubits]
            def replace(op,targets):op.qubits=targets[0]
        elif isinstance(operation,ast.QuantumMeasurementStatement):
            operands=[operation.measure.qubit]
            def replace(op,targets):op.measure.qubit=targets[0]
        else:return None
        if not any(isinstance(value,SourceQuantumRegisterView) and not value.selections for value in operands):return None
        if not 1<=len(operands)<=3:raise error_at(operation,'Quantum operations support one to three operands.')
        prefix=[];groups=[]
        for operand in operands:
            if isinstance(operand,SourceQuantumRegisterView):groups.append(copy.deepcopy(operand));continue
            if isinstance(operand,SourceQuantumSelection):
                effects,selected=capture_scalar_qubit(operand);prefix.extend(effects);groups.append(selected);continue
            captured=register_view_binding(None,operand,{},True,depth)
            if captured is None:raise error_at(operation,'Dynamic alias broadcasting requires declared registers or captured quantum views.')
            effects,view,_=captured;prefix.extend(effects);groups.append(view)
        if isinstance(operation,ast.QuantumMeasurementStatement) and operation.target is not None:
            target=operation.target
            if isinstance(target,ast.Identifier):
                type_=collection_scopes[-1].get(target.name)
                if type_ is None:type_=next((d.type for d in bit_storage if d.identifier.name==target.name),None)
                if not isinstance(type_,ast.BitType):raise error_at(operation,'Quantum alias measurements require a bit destination.')
                width=1 if type_.size is None else collection_integer(type_.size,{})
            elif isinstance(target,ast.IndexedIdentifier) and len(target.indices)==1:
                group=target.indices[0] if isinstance(target.indices[0],list) else [target.indices[0]]
                if len(group)!=1:raise error_at(operation,'Measurement destinations require one register axis.')
                axis=group[0]
                if isinstance(axis,ast.DiscreteSet):width=len(axis.values)
                elif isinstance(axis,ast.RangeDefinition):
                    type_=collection_scopes[-1].get(target.name.name)
                    if not isinstance(type_,ast.BitType):raise error_at(operation,'Measurement destination is not a bit register.')
                    total_width=1 if type_.size is None else collection_integer(type_.size,{})
                    step=1 if axis.step is None else collection_integer(axis.step,{})
                    start=(total_width-1 if step<0 else 0) if axis.start is None else collection_integer(axis.start,{})
                    stop=(0 if step<0 else total_width-1) if axis.end is None else collection_integer(axis.end,{})
                    if step==0:raise error_at(operation,'Measurement destination stride cannot be zero.')
                    distance=stop-start
                    width=0 if distance*step<0 else distance//step+1
                    # Pass the same explicit endpoints to the pinned visitor;
                    # its omitted-start default does not follow reverse strides.
                    axis.start=ast.IntegerLiteral(start);axis.end=ast.IntegerLiteral(stop);axis.step=ast.IntegerLiteral(step)
                else:width=1
            else:raise error_at(operation,'Quantum alias measurements require a bit-register destination.')
            if not 1<=width<=64:raise error_at(operation,'Measurement destination width must be from 1 to 64.')
            view=groups[0]
            prefix.append(ArrayReferenceCheck(views=[copy.deepcopy(view.view)],shapes=[[width]]))
            view.selections=[SourceQuantumSelection(register=copy.deepcopy(view.register),index=SourceArrayView(name=view.view.name,element_type=view.view.element_type,parent=copy.deepcopy(view.view),axes=[ast.IntegerLiteral(i)],writable=False)) for i in range(width)]
            result=copy.deepcopy(operation);replace(result,[view]);return prefix+[result]
        count=ast.Identifier(fresh());runtime.add(count.name)
        prefix.append(ast.ClassicalDeclaration(type=ast.IntType(size=ast.IntegerLiteral(32)),identifier=count,init_expression=ast.IntegerLiteral(1)))
        def extent(group):return ast.SizeOf(target=copy.deepcopy(group.view),index=ast.IntegerLiteral(0)) if isinstance(group,SourceQuantumRegisterView) else ast.IntegerLiteral(1)
        for group in groups:
            size=extent(group)
            prefix.append(ast.BranchingStatement(condition=ast.BinaryExpression(op=ast.BinaryOperator['>'],lhs=copy.deepcopy(size),rhs=copy.deepcopy(count)),if_block=[ast.ClassicalAssignment(lvalue=copy.deepcopy(count),op=ast.AssignmentOperator['='],rvalue=size)],else_block=[]))
        def targets(cursor):
            result=[]
            for group in groups:
                if isinstance(group,SourceQuantumSelection):result.append(copy.deepcopy(group));continue
                # A one-qubit register broadcasts; all other widths must match.
                many=ast.Cast(type=ast.IntType(),argument=ast.BinaryExpression(op=ast.BinaryOperator['!='],lhs=extent(group),rhs=ast.IntegerLiteral(1)))
                index=ast.BinaryExpression(op=ast.BinaryOperator['*'],lhs=many,rhs=copy.deepcopy(cursor))
                selected=SourceArrayView(name=group.view.name,element_type=group.view.element_type,parent=copy.deepcopy(group.view),axes=[index],writable=False)
                result.append(SourceQuantumSelection(register=copy.deepcopy(group.register),index=selected))
            return result
        for preflight in (True,False):
            cursor=ast.Identifier(fresh());runtime.add(cursor.name)
            selected=targets(cursor)
            if preflight:
                body=[WireReferenceCheck(targets=selected)];body[0].span=operation.span
            else:
                op=copy.deepcopy(operation);replace(op,selected);body=[op]
            loop=ast.ForInLoop(type=ast.IntType(size=ast.IntegerLiteral(32)),identifier=cursor,set_declaration=ast.RangeDefinition(start=ast.IntegerLiteral(0),end=ast.BinaryExpression(op=ast.BinaryOperator['-'],lhs=copy.deepcopy(count),rhs=ast.IntegerLiteral(1)),step=None),block=body)
            loop._quantum_runtime_for=True;loop.span=operation.span;prefix.append(loop)
        return prefix

    def block_body(body, parent, active=False, depth=0, declared=None):
        env = dict(parent); declared = set() if declared is None else set(declared)
        result = []
        for node in body:
            if getattr(node, 'annotations', None):
                raise error_at(node, 'Annotated operations require semantics the editor does not support.')
            if isinstance(node, (ast.SubroutineDefinition, ast.QuantumGateDefinition)):
                result.append(node); continue
            if isinstance(node,ast.AliasStatement):
                if node.target.name in declared:raise error_at(node,'Duplicate declaration in one scope: '+node.target.name)
                actual=rewrite(node.value,env)
                captured_bits=bit_aliases.bind(actual,active,depth)
                if captured_bits is not None:
                    effects,binding=captured_bits;result.extend(effects)
                    env[node.target.name]=binding;declared.add(node.target.name)
                    node._quantum_bound_view=copy.deepcopy(binding)
                    continue
                dynamic=active or any(isinstance(item,(SourceQuantumRegisterView,SourceQuantumSelection,ast.FunctionCall,ast.Concatenation)) or isinstance(item,ast.Identifier) and (item.name in runtime or item.name not in constants and any(item.name in scope for scope in classical_scopes)) for item in walk(actual))
                if dynamic:
                    name=node.target.name
                    if name in declared:raise error_at(node,'Duplicate declaration in one scope: '+name)
                    captured=register_view_binding(None,actual,{},active,depth)
                    if captured is not None:
                        effects,binding,_=captured;result.extend(effects);env[name]=binding;declared.add(name)
                        node._quantum_bound_view=copy.deepcopy(binding)
                        continue
                if len(classical_scopes)>2:
                    name=node.target.name;bound=ast.Identifier(fresh())
                    static_quantum_aliases[bound.name]=copy.deepcopy(actual)
                    env[name]=bound;declared.add(name)
                    alias=ast.AliasStatement(target=copy.deepcopy(bound),value=actual);alias.span=node.span
                    result.append(alias);continue
                declared.add(node.target.name)
            if isinstance(node, (ast.ClassicalDeclaration, ast.ConstantDeclaration)):
                name = node.identifier.name
                if name in declared and (active or isinstance(env.get(name),(SourceQuantumRegisterView,SourceBitAlias))):
                    raise error_at(node, 'Duplicate declaration in one subroutine scope: ' + name)
                declared.add(name)
                if not isinstance(node.type,ast.ArrayType):array_scopes[-1].discard(name)
                if active and isinstance(node, ast.ClassicalDeclaration) and not isinstance(node.type, values):
                    raise error_at(node, 'Runtime subroutine locals support integers, Booleans, float32/64, angles and bit registers.')
                value = copy.copy(node)
                value.type = rewrite(node.type, env)
                if active:
                    env[name] = ast.Identifier(fresh())
                elif isinstance(env.get(name),(SourceQuantumRegisterView,SourceBitAlias)):env[name]=ast.Identifier(name)
                value.identifier = rewrite(node.identifier, env)
                classical_scopes[-1].add(value.identifier.name)
                collection_scopes[-1][value.identifier.name]=collection_geometry(value.type,env)
                if isinstance(value.type,ast.ArrayType):array_backing_types[value.identifier.name]=copy.deepcopy(collection_scopes[-1][value.identifier.name])
                value.init_expression = rewrite(node.init_expression, env)
                if isinstance(value.type,ast.ArrayType) and value.init_expression is not None and (not isinstance(value.init_expression,ast.ArrayLiteral) or any(isinstance(item,ast.FunctionCall) and item.name.name in functions for item in walk(value.init_expression))):
                    initial=value.init_expression;value.init_expression=None;result.append(value)
                    result.extend(array_copy(value.identifier,initial,active,depth));continue
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
                    reference=rewrite(node.set_declaration,env)
                    if is_array_target(reference):
                        result.append(array_collection_loop(node,reference,env,active,depth));continue
                    bit_loop=bit_collection_loop(node,reference,env,active,depth)
                    if bit_loop is not None:result.append(bit_loop);continue
                    if isinstance(node.set_declaration, ast.DiscreteSet):
                        if len(node.set_declaration.values) > 64:
                            raise error_at(node, 'Runtime collections support at most 64 values.')
                        result.append(collection_loop(node, env, active, depth))
                        continue
                    specialized = runtime_quantum_loop(node, env, active, depth)
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
            elif isinstance(value,ast.ClassicalAssignment) and is_array_target(value.lvalue) and array_rank(value.lvalue)>0:
                if value.op.name!='=':raise error_at(value,'Array copies use simple assignment.')
                result.extend(array_copy(value.lvalue,value.rvalue,active,depth));continue
            elif isinstance(value,ast.ClassicalAssignment) and is_array_target(value.lvalue) and (any(isinstance(item,(ast.RangeDefinition,SourceArrayView)) for item in walk(value.lvalue)) or value.op.name!='=' and any(isinstance(item,ast.FunctionCall) and item.name.name in functions for item in walk(value.rvalue))):
                effects,rhs=expression_calls(value.rvalue,active,depth)
                capture=bool(effects) or any(isinstance(item,ast.FunctionCall) and item.name.name in functions for item in walk(value.lvalue))
                if capture:
                    prefix,target=capture_array_view(value.lvalue,active,depth)
                    if target.rank:raise error_at(value,'Array copies require bulk assignment lowering.')
                    if not target.writable:raise error_at(value,'Cannot write through a readonly reference.')
                    result.extend(prefix);value.lvalue=target
                    if effects and value.op.name!='=':
                        saved=ast.Identifier(fresh());runtime.add(saved.name)
                        result.append(ast.ClassicalDeclaration(type=copy.deepcopy(target.element_type),identifier=saved,init_expression=copy.deepcopy(target)))
                        rhs=ast.BinaryExpression(op=ast.BinaryOperator[value.op.name[:-1]],lhs=copy.deepcopy(saved),rhs=rhs);value.op=ast.AssignmentOperator['=']
                result.extend(effects);value.rvalue=rhs
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
            alias_operation=dynamic_alias_operation(value,depth)
            if alias_operation is not None:result.extend(alias_operation)
            else:result.append(value)
        return result

    def bit_alias_array(type_,width,initial):
        name=fresh();backing=ast.ArrayType(base_type=copy.deepcopy(type_),dimensions=[ast.IntegerLiteral(width)])
        declaration=ast.ClassicalDeclaration(type=backing,identifier=ast.Identifier(name),init_expression=initial)
        array_temporaries.append(declaration)
        collection_arrays.add(name);array_backing_types[name]=backing
        return declaration

    def bit_alias_name():
        name=fresh();runtime.add(name);return name

    def bit_alias_type(name):
        visible=any(name in scope for scope in classical_scopes) or any(d.identifier.name==name for d in bit_storage)
        return collection_scopes[-1].get(name) if visible else None

    bit_aliases=BitAliases(bit_alias_name,bit_alias_array,capture_array_view,
                           lambda value:collection_integer(value,{}),bit_alias_type)

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
        if isinstance(node,(ast.ClassicalDeclaration,ast.ConstantDeclaration,ast.QubitDeclaration)):
            name=node.qubit.name if isinstance(node,ast.QubitDeclaration) else node.identifier.name
            if name in global_alias_bindings:raise error_at(node,'Duplicate global declaration: '+name)
        if isinstance(node,ast.AliasStatement) and (node.target.name in global_alias_names or node.target.name in classical_scopes[0] or node.target.name in register_declarations):
            raise error_at(node,'Duplicate global alias: '+node.target.name)
        result.extend(block([node], global_alias_bindings))
        if isinstance(node,ast.AliasStatement):
            global_alias_names.add(node.target.name)
            if hasattr(node,'_quantum_bound_view'):global_alias_bindings[node.target.name]=node._quantum_bound_view
            else:static_quantum_aliases[node.target.name]=copy.deepcopy(node.value)
    program.statements[:] = array_temporaries + bit_storage + result
    program._quantum_runtime_array_names=collection_arrays
    return {declaration.identifier.name for declaration in bit_storage}
