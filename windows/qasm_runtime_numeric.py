"""Typed runtime numeric lowering; values are evaluated only by the worker."""
import math
import struct
from dataclasses import fields, is_dataclass
import openqasm3.ast as ast
from qasm_runtime_arrays import selection as array_selection

NUMERIC_TYPES=(ast.FloatType,ast.AngleType)
FUNCTIONS={'sin':'Sin','cos':'Cos','tan':'Tan','arcsin':'Arcsin','arccos':'Arccos',
           'arctan':'Arctan','exp':'Exp','log':'Log','sqrt':'Sqrt','floor':'Floor','ceiling':'Ceiling','mod':'Mod'}
def contains_numeric(value,variables):
    if getattr(value,"_quantum_array_extent",False):return False
    if hasattr(value,"_quantum_array"):return value._quantum_array["kind"] in ("Float","Angle")
    if isinstance(value,ast.Identifier):return value.name in variables
    if isinstance(value,ast.FloatLiteral):return True
    if isinstance(value,ast.Cast) and isinstance(value.type,NUMERIC_TYPES):return True
    if isinstance(value,ast.FunctionCall) and value.name.name in FUNCTIONS:return True
    if isinstance(value,(list,tuple)):return any(contains_numeric(v,variables) for v in value)
    if is_dataclass(value):return any(contains_numeric(getattr(value,f.name),variables) for f in fields(value) if f.name not in ('span','annotations'))
    return False

def lower_numeric(value,variables,integer,bit,mode='Real',expected_width=None,target_float_width=64):
    """Callbacks lower numeric-free integer/bit subtrees with existing semantics."""
    def real_width(node):
        if node.get('Width') is not None:return node['Width']
        return real_width(node['Left'])
    def type_of_integer(node):
        if node['Kind']=='NumericCompare':return 'Signed',0
        if node['Kind'] in ('AngleRatio','AngleBits'):return 'Unsigned',real_width(node['RealLeft'])
        if node['Kind']=='IntegerBinary':
            types=[type_of_integer(node[k]) for k in ('Left','Right')]
            return ('Unsigned' if any(s=='Unsigned' and w in (0,64) for s,w in types) else 'Signed'),0
        return node['Signedness'],node['Width']
    def real(node,kind,width,target_width=64):
        if kind in ('Float','Angle'):return node,kind,width
        if kind=='Integer':return {'Kind':'TypedInteger','Width':target_width,'IntegerValue':node},'Float',target_width
        raise ValueError('Cast bit operands explicitly before numeric arithmetic.')
    def zero(kind,width):
        return {'Kind':'TypedConstant','NumericKind':kind,'Width':width,'ValueBits':'0'}
    def truth(item,explicit=False):
        node,kind,width=item
        if kind in ('Float','Angle'):
            comparison={'Kind':'NumericCompare','RealLeft':node,'RealRight':zero(kind,width)}
            return {'Kind':'IntegerCompare','Operator':'NotEqual','Left':comparison,'Right':{'Kind':'IntegerConstant','Signedness':'Signed','Width':0,'Value':'0'}},'Bits',1
        if kind=='Integer':return {'Kind':'IntegerCompare','Operator':'NotEqual','Left':node,'Right':{'Kind':'IntegerConstant','Signedness':'Signed','Width':0,'Value':'0'}},'Bits',1
        if width!=1:
            if not explicit:raise ValueError('Boolean conversion of bit registers requires an explicit cast.')
            return {'Kind':'Binary','Operator':'NotEqual','Left':node,'Right':{'Kind':'Constant','Width':width,'Value':'0'}},'Bits',1
        return item
    def parse(node,depth=0):
        if depth>=32:raise ValueError('Numeric expressions exceed 32 levels.')
        child=lambda x:parse(x,depth+1)
        if hasattr(node,'_quantum_array') and node._quantum_array['kind'] in ('Float','Angle'):
            info=node._quantum_array
            return dict(Kind='ArrayElement',NumericKind=info['kind'],Width=info['width'],Selection=array_selection(node,integer)),info['kind'],info['width']

        if isinstance(node,ast.Identifier) and node.name in variables:
            slot,kind,width=variables[node.name]
            return {'Kind':'Variable','NumericKind':kind,'Width':width,'Slot':slot},kind,width
        if isinstance(node,ast.FloatLiteral):
            if not math.isfinite(node.value):raise ValueError('Numeric constants must be finite.')
            return {'Kind':'TypedConstant','NumericKind':'Float','Width':64,'ValueBits':str(struct.unpack('>Q',struct.pack('>d',node.value))[0])},'Float',64
        if not contains_numeric(node,variables):
            if isinstance(node,(ast.BitstringLiteral,ast.IndexExpression)):
                result=bit(node);return result,'Bits',result['Width'] if result['Kind']=='Constant' else len(result['Bits']) if result['Kind']=='Read' else expected_width
            try:
                result=integer(node);sign,width=type_of_integer(result);return result,'Integer',width
            except ValueError:
                result=bit(node)
                width=result.get('Width') or (len(result['Bits']) if result['Kind']=='Read' else 1)
                return result,'Bits',width
        if isinstance(node,ast.Cast):
            operand,kind,width=child(node.argument)
            size=((1 if isinstance(node.type,ast.BitType) else 64) if node.type.size is None else node.type.size.value) if hasattr(node.type,'size') else None
            if isinstance(node.type,NUMERIC_TYPES):
                target='Float' if isinstance(node.type,ast.FloatType) else 'Angle'
                if type(size) is not int or (size not in (32,64) if target=='Float' else not 1<=size<=64):raise ValueError('Use float32/64 or angle widths 1–64.')
                if target=='Angle' and kind=='Bits':
                    if width!=size:raise ValueError('Bit-to-angle casts require matching widths.')
                    return {'Kind':'Bits','Width':size,'BitValue':operand},target,size
                operand,kind,width=real(operand,kind,width,size if target=='Float' else 64)
                if kind=='Angle' and target=='Float':raise ValueError('Angles cannot be cast to float.')
                return {'Kind':'Cast','NumericKind':target,'Width':size,'Left':operand},target,size
            if isinstance(node.type,ast.BoolType):return truth((operand,kind,width),explicit=True)
            if isinstance(node.type,(ast.IntType,ast.UintType)):
                size=0 if node.type.size is None else node.type.size.value
                sign='Signed' if isinstance(node.type,ast.IntType) else 'Unsigned'
                if kind=='Angle':raise ValueError('Angles cannot be cast to integer.')
                if kind=='Float':return {'Kind':'NumericCast','Signedness':sign,'Width':size,'RealLeft':operand},'Integer',size
                if kind=='Integer':return {'Kind':'IntegerCast','Signedness':sign,'Width':size,'Left':operand},kind,size
                if width==1 and (isinstance(node.argument,ast.BinaryExpression) and node.argument.op.name in ('==','!=','<','<=','>','>=','&&','||') or isinstance(node.argument,ast.Cast) and isinstance(node.argument.type,ast.BoolType)):
                    return {'Kind':'IntegerCast','Signedness':sign,'Width':size,'Left':{'Kind':'IntegerFromBits','Signedness':'Unsigned','Width':1,'Left':operand}},'Integer',size
                if width!=(size or 64):raise ValueError('Bit-to-integer casts require matching widths.')
                return {'Kind':'IntegerFromBits','Signedness':sign,'Width':size,'Left':operand},'Integer',size
            if isinstance(node.type,ast.BitType):
                if kind=='Bits' and width==size:return operand,kind,width
                if kind=='Angle':
                    if width!=size:raise ValueError('Angle-to-bit casts require matching widths.')
                    return {'Kind':'IntegerBits','Left':{'Kind':'AngleBits','RealLeft':operand}},'Bits',size
                if kind=='Integer' and (width or 64)==size:
                    if width==0:operand={'Kind':'IntegerCast','Signedness':type_of_integer(operand)[0],'Width':64,'Left':operand}
                    return {'Kind':'IntegerBits','Left':operand},'Bits',size
                raise ValueError('Bit casts require equal-width integer or angle operands.')
        if isinstance(node,ast.FunctionCall) and node.name.name in FUNCTIONS:
            name=node.name.name
            if len(node.arguments)!=(2 if name=='mod' else 1):raise ValueError('Incorrect numeric function argument count.')
            left,kind,width=real(*child(node.arguments[0]))
            if name=='mod':
                right,rkind,rwidth=real(*child(node.arguments[1]))
                if kind!=rkind or kind!='Float':raise ValueError('mod requires floats.')
                return {'Kind':'Binary','Operator':'Mod','Left':left,'Right':right},kind,max(width,rwidth)
            if kind=='Angle' and name not in ('sin','cos','tan'):raise ValueError('Only trigonometric functions accept angles.')
            return {'Kind':'Function','Function':FUNCTIONS[name],'Left':left},'Float',64 if kind=='Angle' else width
        if isinstance(node,ast.UnaryExpression):
            operand,kind,width=child(node.expression)
            if node.op.name=='!':
                operand,_,_=truth((operand,kind,width));return {'Kind':'Complement','Left':operand},'Bits',1
            if kind=='Integer' and node.op.name=='-':return {'Kind':'IntegerBinary','Operator':'Subtract','Left':integer(ast.IntegerLiteral(0)),'Right':operand},kind,0
            operand,kind,width=real(operand,kind,width)
            if node.op.name not in ('-','~') or node.op.name=='~' and kind!='Angle':raise ValueError('Unsupported numeric unary operation.')
            return {'Kind':'Function','Function':'Negate' if node.op.name=='-' else 'Complement','Left':operand},kind,width
        if isinstance(node,ast.BinaryExpression):
            left,lk,lw=child(node.lhs);right,rk,rw=child(node.rhs);op=node.op.name
            if op in ('&&','||'):
                left,_,_=truth((left,lk,lw));right,_,_=truth((right,rk,rw))
                return {'Kind':'Logical','Operator':'And' if op=='&&' else 'Or','Left':left,'Right':right},'Bits',1
            comparisons={'==':'Equal','!=':'NotEqual','<':'Less','<=':'LessEqual','>':'Greater','>=':'GreaterEqual'}
            if op in comparisons:
                if lk==rk=='Bits':
                    if lw!=rw:raise ValueError('Bit comparisons require matching widths.')
                    return {'Kind':'Binary','Operator':comparisons[op],'Left':left,'Right':right},'Bits',1
                if lk==rk=='Integer':return {'Kind':'IntegerCompare','Operator':comparisons[op],'Left':left,'Right':right},'Bits',1
                left,lk,lw=real(left,lk,lw,rw if rk=='Float' else 64);right,rk,rw=real(right,rk,rw,lw if lk=='Float' else 64)
                if (lk=='Angle' or rk=='Angle') and (lk!=rk or lw!=rw):raise ValueError('Angle comparisons require equal widths.')
                return {'Kind':'IntegerCompare','Operator':comparisons[op],'Left':{'Kind':'NumericCompare','RealLeft':left,'RealRight':right},'Right':integer(ast.IntegerLiteral(0))},'Bits',1
            if lk==rk=='Integer':
                operations={'+':'Add','-':'Subtract','*':'Multiply','/':'Divide','%':'Remainder','**':'Power'}
                if op not in operations:raise ValueError('Unsupported integer operation.')
                return {'Kind':'IntegerBinary','Operator':operations[op],'Left':left,'Right':right},'Integer',0
            if lk=='Angle' and rk=='Integer' and op in ('*','/','<<','>>'):
                sign,size=type_of_integer(right)
                if sign!='Unsigned' or op in ('*','/') and (size or 64)!=lw:raise ValueError('Angle scaling requires a matching-width unsigned integer; shifts require unsigned distance.')
                return {'Kind':'Scale','Scaling':{'*':'Multiply','/':'Divide','<<':'ShiftLeft','>>':'ShiftRight'}[op],'Left':left,'IntegerValue':right},lk,lw
            if lk==rk=='Angle' and op=='/':
                if lw!=rw:raise ValueError('Angle ratio requires equal widths.')
                return {'Kind':'AngleRatio','RealLeft':left,'RealRight':right},'Integer',lw
            left,lk,lw=real(left,lk,lw,rw if rk=='Float' else 64);right,rk,rw=real(right,rk,rw,lw if lk=='Float' else 64)
            operations={'+':'Add','-':'Subtract','*':'Multiply','/':'Divide','**':'Power','&':'And','|':'Or','^':'Xor'}
            if op not in operations:raise ValueError('Unsupported numeric operation.')
            if lk=='Angle' or rk=='Angle':
                if lk!=rk or lw!=rw or op not in ('+','-','&','|','^'):raise ValueError('Incompatible modular angle operands.')
            elif op in ('&','|','^'):raise ValueError('Bitwise numeric operations require angles.')
            return {'Kind':'Binary','Operator':operations[op],'Left':left,'Right':right},lk,max(lw,rw)
        raise ValueError('Unsupported typed numeric expression: '+type(node).__name__)
    result,kind,width=parse(value)
    if mode=='Real':return real(result,kind,width,target_float_width)[0]
    if mode=='Integer':
        if kind!='Integer':raise ValueError('An integer expression requires an explicit numeric cast.')
        return result
    if kind!='Bits':raise ValueError('A bit expression requires an explicit cast or comparison.')
    if expected_width is not None and width!=expected_width:raise ValueError('Classical expression width does not match its destination.')
    return result
