"""Capture classical-bit alias geometry and snapshot its values for iteration."""
import copy
from dataclasses import dataclass
import openqasm3.ast as ast
from qasm_runtime_arrays import SourceArrayView, ArrayReferenceCheck, split_reference
from qasm_source_diagnostics import error_at


@dataclass
class SourceBitAlias(ast.Expression):
    view: object


class BitAliases:
    def __init__(self, fresh, declare_array, capture_view, integer, lookup):
        self.fresh=fresh;self.declare_array=declare_array;self.capture_view=capture_view
        self.integer=integer;self.lookup=lookup
        self.identity=None;self.registers={};self.bits=[];self.arrays={}

    @staticmethod
    def range(start,end):
        return ast.RangeDefinition(start=start,end=end,step=None)

    @staticmethod
    def binary(op,left,right):
        return ast.BinaryExpression(op=ast.BinaryOperator[op],lhs=left,rhs=right)

    @staticmethod
    def size(view):
        return ast.SizeOf(target=copy.deepcopy(view),index=ast.IntegerLiteral(0)) if view.rank else ast.IntegerLiteral(1)

    @staticmethod
    def element(view,index):
        if not view.rank:return copy.deepcopy(view)
        return SourceArrayView(name=view.name,element_type=view.element_type,parent=copy.deepcopy(view),axes=[index],writable=False)

    def array(self,type_,values=None):
        declaration=self.declare_array(type_,64,values)
        name=declaration.identifier.name;self.arrays[name]=declaration
        return SourceArrayView(name=name,element_type=type_,parent=None,
                               axes=[self.range(ast.IntegerLiteral(0),ast.IntegerLiteral(63))])

    def whole_register(self,root,type_):
        if root.name in self.registers:return copy.deepcopy(self.registers[root.name])
        width=1 if type_.size is None else self.integer(type_.size)
        if not 1<=width<=64 or len(self.bits)+width>64:raise error_at(root,'Classical aliases support at most 64 physical bits.')
        if self.identity is None:
            self.identity=self.array(ast.UintType(size=ast.IntegerLiteral(32)))
        offset=len(self.bits)
        for index in range(width):
            self.bits.append(copy.deepcopy(root) if type_.size is None else ast.IndexExpression(collection=copy.deepcopy(root),index=[ast.IntegerLiteral(index)]))
        view=SourceArrayView(name=self.identity.name,element_type=self.identity.element_type,parent=None,
                            axes=[self.range(ast.IntegerLiteral(offset),ast.IntegerLiteral(offset+width-1))],writable=False)
        self.registers[root.name]=view
        return copy.deepcopy(view)

    def recognizes(self,value):
        if isinstance(value,ast.Concatenation):return self.recognizes(value.lhs) or self.recognizes(value.rhs)
        root,_=split_reference(value)
        return isinstance(root,SourceBitAlias) or isinstance(root,ast.Identifier) and isinstance(self.lookup(root.name),ast.BitType)

    def bind(self,value,active,depth):
        if not self.recognizes(value):return None
        if isinstance(value,ast.Concatenation):
            parts=[]
            def flatten(item):
                if isinstance(item,ast.Concatenation):flatten(item.lhs);flatten(item.rhs)
                else:parts.append(item)
            flatten(value)
            return self.concatenate(parts,active,depth,value)
        root,groups=split_reference(value)
        if len(groups)>31:raise error_at(value,'Classical alias selection exceeds 32 levels.')
        view=copy.deepcopy(root.view) if isinstance(root,SourceBitAlias) else self.whole_register(root,self.lookup(root.name))
        for group_index,group in enumerate(groups):
            if len(group)!=1:raise error_at(value,'Classical aliases have one dimension.')
            if isinstance(group[0],ast.DiscreteSet):
                parts=[ast.IndexExpression(collection=SourceBitAlias(copy.deepcopy(view)),index=[copy.deepcopy(index)]) for index in group[0].values]
                effects,alias=self.concatenate(parts,active,depth,value)
                remaining=groups[group_index+1:]
                selected=alias
                for rest in remaining:selected=ast.IndexExpression(collection=selected,index=copy.deepcopy(rest))
                suffix,result=self.bind(selected,active,depth)
                return effects+suffix,result
            view=ast.IndexExpression(collection=view,index=copy.deepcopy(group))
        effects,view=self.capture_view(view,active,depth,quantum=True)
        if view.rank>1:raise error_at(value,'Classical aliases have one dimension.')
        if view.rank:
            # A zero-width alias is invalid even when no loop consumes it.
            first=SourceArrayView(name=view.name,element_type=view.element_type,parent=copy.deepcopy(view),
                                  axes=[self.range(ast.IntegerLiteral(0),ast.IntegerLiteral(0))],writable=False)
            effects.append(ArrayReferenceCheck(views=[first],shapes=[[1]]))
        return effects,SourceBitAlias(view)

    def loop(self,cursor,stop,body):
        # Retain a runtime bound through export/reimport, including singleton aliases.
        count=ast.Identifier(self.fresh())
        declaration=ast.ClassicalDeclaration(type=ast.IntType(size=ast.IntegerLiteral(32)),identifier=count,init_expression=stop)
        value=ast.ForInLoop(type=ast.IntType(size=ast.IntegerLiteral(32)),identifier=cursor,
                           set_declaration=self.range(ast.IntegerLiteral(0),self.binary('-',copy.deepcopy(count),ast.IntegerLiteral(1))),block=body)
        value._quantum_runtime_for=True
        return ast.CompoundStatement(statements=[declaration,value])

    @staticmethod
    def store(view,index,value):
        target=ast.IndexedIdentifier(name=ast.Identifier(view.name),indices=[[index]])
        return ast.ClassicalAssignment(lvalue=target,op=ast.AssignmentOperator['='],rvalue=value)

    def initialize_identity_values(self):
        # Geometry-only aliases do not read this map. Avoid emitting 64 stores
        # unless concatenation or a scalar gather actually needs identities.
        self.arrays[self.identity.name].init_expression=ast.ArrayLiteral(values=[ast.IntegerLiteral(i) for i in range(64)])

    def concatenate(self,parts,active,depth,source):
        if not 1<=len(parts)<=64:raise error_at(source,'Classical aliases require 1 to 64 nonempty selections.')
        combined=self.array(ast.UintType(size=ast.IntegerLiteral(32)))
        count=ast.Identifier(self.fresh())
        effects=[ast.ClassicalDeclaration(type=ast.IntType(size=ast.IntegerLiteral(32)),identifier=count,init_expression=ast.IntegerLiteral(0))]
        for part in parts:
            result=self.bind(part,active,depth)
            if result is None:raise error_at(part,'Classical aliases cannot mix bits and qubits.')
            prefix,alias=result;effects.extend(prefix)
            self.initialize_identity_values()
            cursor=ast.Identifier(self.fresh());prior=ast.Identifier(self.fresh())
            selected=self.element(alias.view,copy.deepcopy(cursor))
            previous=self.element(combined,copy.deepcopy(prior))
            # Compare physical identity singleton views before each append.
            identities=[SourceArrayView(name=self.identity.name,element_type=self.identity.element_type,parent=None,
                                        axes=[self.range(copy.deepcopy(index),copy.deepcopy(index))]) for index in (selected,previous)]
            check=ArrayReferenceCheck(views=identities,shapes=[[1],[1]])
            body=[self.loop(prior,copy.deepcopy(count),[check]),self.store(combined,copy.deepcopy(count),selected),
                  ast.ClassicalAssignment(lvalue=copy.deepcopy(count),op=ast.AssignmentOperator['+='],rvalue=ast.IntegerLiteral(1))]
            effects.append(self.loop(cursor,self.size(alias.view),body))
        combined.axes=[self.range(ast.IntegerLiteral(0),self.binary('-',copy.deepcopy(count),ast.IntegerLiteral(1)))];combined.writable=False
        return effects,SourceBitAlias(combined)

    def snapshot(self,alias):
        values=self.array(ast.BoolType());effects=[]
        for index,bit in enumerate(self.bits):
            effects.append(self.store(values,ast.IntegerLiteral(index),copy.deepcopy(bit)))
        if alias.view.rank==1 and alias.view.name==self.identity.name:
            selected=copy.deepcopy(alias.view)
            view=selected
            while view is not None:
                view.name=values.name
                view.element_type=ast.BoolType()
                view.writable=False
                view=view.parent
            return effects,selected
        selected=self.array(ast.BoolType())
        self.initialize_identity_values()
        cursor=ast.Identifier(self.fresh())
        physical=self.element(alias.view,copy.deepcopy(cursor))
        read=self.element(values,physical)
        effects.append(self.loop(cursor,self.size(alias.view),[self.store(selected,copy.deepcopy(cursor),read)]))
        selected.axes=[self.range(ast.IntegerLiteral(0),self.binary('-',self.size(alias.view),ast.IntegerLiteral(1)))];selected.writable=False
        return effects,selected
