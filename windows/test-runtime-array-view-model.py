"""Exercise view documents through save/load, export syntax and both workers."""
import argparse
import base64
import copy
import json
import os
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--adapter', type=Path, required=True)
parser.add_argument('--worker', type=Path)
args = parser.parse_args()
checks = 0
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(args.worker.resolve().parent / 'data')) if args.worker else os.environ

def integer(value):
    return dict(Kind='IntegerConstant', Signedness='Signed', Width=0, Value=str(value & ((1 << 64) - 1)))

def selection(*indices, array=0):
    return dict(Array=array, Indices=[integer(i) if isinstance(i, int) else i for i in indices], Source='model.qasm:3:2')

def element(*indices):
    return dict(Kind='IntegerArrayElement', Signedness='Signed', Width=0, Selection=selection(*indices))

def store(value, *indices):
    return dict(Kind='StoreInteger', ArrayTarget=selection(*indices), IntegerValue=integer(value))

def observe(value, expected):
    return dict(Kind='Assign', Wires=[0], ClassicalValue=dict(Kind='IntegerCompare', Operator='Equal', Left=value, Right=integer(expected)))

base = dict(Version=16, Qubits=0, Registers=[dict(Name='c', Size=1)], OutputBits=[0], LoopConditionBudget=1000000,
            Variables=[dict(Name='cell'+str(i), Signedness='Signed', Width=0) for i in range(6)], NumericVariables=[],
            Arrays=[dict(Name='values', Base=0, Dimensions=[2, 3], Signedness='Signed', Width=0)], Steps=[])

def run(document, expected=None, invalid=False, runtime_error=False):
    global checks
    result = subprocess.run([str(args.adapter.resolve())], input=json.dumps(document).encode(), capture_output=True, timeout=30)
    checks += 1
    if invalid:
        assert result.returncode and not result.stdout, result.stdout
        return
    assert result.returncode == 0, result.stderr
    encoded = json.loads(result.stdout)
    import openqasm3
    from qasm_concat_parser import concatenation_program
    try:concatenation_program(encoded['source']) or openqasm3.parse(encoded['source'])
    except Exception as error:raise AssertionError(encoded['source']) from error
    assert 'array[int[64], 2, 3] a0;' in encoded['source']
    for exact in (True, False):
        if not args.worker:continue
        process = subprocess.run([str(args.worker.resolve()), '--exact-circuit' if exact else '--sample'],
                                 input=base64.b64decode(encoded['exact' if exact else 'sampled']), capture_output=True, env=env, timeout=30)
        checks += 1
        if runtime_error:
            assert process.returncode and not process.stdout, process.stdout
        else:
            assert process.returncode == 0, process.stderr
            payload = json.loads(process.stdout)
            values = payload['probabilities' if exact else 'counts']
            assert values == {expected: '1' if exact else 10000}, values

def axis(value=None,start=None,stop=None,step=None):
    return dict(Scalar=value is not None,Start=integer(value) if value is not None else start,Stop=stop,Step=step)
def view(axes,writable=False,parent=None):return dict(Array=0,Writable=writable,Parent=parent,Axes=axes)
def selected(reference,*indices):return dict(Array=0,View=reference,Indices=[integer(i) if isinstance(i,int) else i for i in indices],Source='view.qasm:4:2')
def load(reference,*indices):return dict(Kind='IntegerArrayElement',Signedness='Signed',Width=0,Selection=selected(reference,*indices))
def save(reference,value,*indices):return dict(Kind='StoreInteger',ArrayTarget=selected(reference,*indices),IntegerValue=integer(value))
def extent(reference,axis=0):return dict(Kind='IntegerViewExtent',Signedness='Unsigned',Width=0,View=reference,ViewAxis=axis)
def check(*references):return dict(Kind='CheckArrayReferences',ArrayReferences=[dict(View=v,Shape=shape) for v,shape in references])
full=view([axis(),axis()],True)
readonly=view([axis(),axis()])
row=view([axis(1),axis()],True)
reverse=view([axis(step=integer(-1))],parent=row)
for steps,expected,failure in (
 ([check((readonly,[2,3])),observe(extent(row),3)],'1',False),
 ([save(row,7,-1),observe(load(reverse,0),7)],'1',False),
 ([check((readonly,[]),(full,[]))],'0',False),
 ([check((full,[]),(full,[]))],None,True),
 ([check((full,[3,2]))],None,True),
 ([observe(load(row,0),0)],None,True),
 ([check((view([axis(2),axis()]),[]))],None,True),
):
    doc=copy.deepcopy(base);doc['Steps']=steps;run(doc,expected,runtime_error=failure)
# Geometry-only variable uses must remain visible to export lifetime recovery.
doc=copy.deepcopy(base);doc['Variables'].append(dict(Name='geometry',Signedness='Signed',Width=0))
geometry=dict(Kind='IntegerVariable',Signedness='Signed',Width=0,Slot=6)
dynamic=view([dict(Scalar=True,Start=geometry),axis()])
doc['Steps']=[dict(Kind='ClearInteger',VariableSlot=6),dict(Kind='StoreInteger',VariableSlot=6,IntegerValue=integer(1)),check((dynamic,[3])),observe(extent(dynamic),3),dict(Kind='ClearInteger',VariableSlot=6)]
run(doc,'1')
# Address checks on scalar and empty-prefix views do not read backing data.
for reference in (view([axis(1),axis(2)]),row):
    doc=copy.deepcopy(base);doc['Steps']=[observe(dict(Kind='IntegerArrayExtent',Signedness='Signed',Width=0,Selection=selected(reference)),1)];run(doc,'1')
for mutate in (
    lambda d:d.update(Version=15),
    lambda d:d['Steps'][0]['ArrayReferences'][0]['View'].update(Writable='yes'),
    lambda d:d['Steps'][0]['ArrayReferences'][0]['View'].update(Axes=[]),
    lambda d:d['Steps'][0]['ArrayReferences'][0].update(Shape=[6]),
    lambda d:d['Steps'][0]['ArrayReferences'][0].update(Shape=[-1,3]),
    lambda d:d['Steps'][0].update(IntegerValue=integer(1)),
    lambda d:d['Steps'][0].update(Kind='End'),
    lambda d:d['Steps'][0]['ArrayReferences'][0]['View']['Axes'][0].update(Scalar=True,Stop=integer(1)),
    lambda d:d['Steps'][0]['ArrayReferences'][0]['View'].update(Unexpected=True),
):
    doc=copy.deepcopy(base);doc['Steps']=copy.deepcopy([check((readonly,[]))]);mutate(doc);run(doc,invalid=True)
doc=copy.deepcopy(base);doc['Steps']=[save(readonly,1,0,0)];run(doc,invalid=True)
doc=copy.deepcopy(base);doc['Steps']=[observe(extent(row,1),1)];run(doc,invalid=True)
# Numeric arrays retain float32 rounding and readonly enforcement.
import struct
doc=copy.deepcopy(base);doc['NumericVariables']=[dict(Name='float'+str(i),NumericKind='Float',Width=32) for i in range(2)]
doc['Arrays'].append(dict(Name='floating',Base=0,Dimensions=[2],NumericKind='Float',Width=32))
fview=dict(Array=1,Writable=True,Axes=[axis()]);fselection=dict(Array=1,View=fview,Indices=[integer(-1)],Source='float.qasm:2:1')
real=dict(Kind='TypedConstant',NumericKind='Float',Width=64,ValueBits=str(struct.unpack('<Q',struct.pack('<d',16777217.0))[0]))
readreal=dict(Kind='ArrayElement',NumericKind='Float',Width=32,Selection=fselection)
doc['Steps']=[check((full,[]),(fview,[2])),dict(Kind='StoreNumeric',ArrayTarget=fselection,NumericValue=real),observe(dict(Kind='NumericCast',Signedness='Signed',Width=0,RealLeft=readreal),16777216)]
run(doc,'1')
# Numeric locals used only by view geometry must retain their lifetime.
doc=copy.deepcopy(base);doc['NumericVariables']=[dict(Name='selector',NumericKind='Float',Width=64)]
cast=dict(Kind='NumericCast',Signedness='Signed',Width=0,RealLeft=dict(Kind='Variable',NumericKind='Float',Width=64,Slot=0))
geometry=view([dict(Scalar=True,Start=cast),axis()])
real=dict(Kind='TypedConstant',NumericKind='Float',Width=64,ValueBits=str(struct.unpack('<Q',struct.pack('<d',1.0))[0]))
doc['Steps']=[dict(Kind='ClearNumeric',VariableSlot=0),dict(Kind='StoreNumeric',VariableSlot=0,NumericValue=real),check((geometry,[3])),observe(extent(geometry),3),dict(Kind='ClearNumeric',VariableSlot=0)]
run(doc,'1')
copy_base=copy.deepcopy(base);copy_base['Version']=17
row0=view([axis(0),axis()],True);row1=view([axis(1),axis()],True)
def copy_values(destination,*sources):return dict(Kind='CopyArray',ArrayCopy=dict(Destination=destination,Sources=list(sources)))
initial=[store(k+1,0,k) for k in range(3)]
doc=copy.deepcopy(copy_base);doc['Steps']=initial+[copy_values(row1,row0),observe(load(row1,2),3)];run(doc,'1')
last_two=view([axis(start=integer(1),stop=integer(2))],True,row0)
first=view([axis(start=integer(0),stop=integer(0))],False,row0)
doc['Steps']=initial+[copy_values(row0,last_two,first),observe(load(row0,2),1)];run(doc,'1')
for mutation in (
    lambda d:d.update(Version=16),
    lambda d:d['Steps'][3]['ArrayCopy']['Destination'].update(Writable=False),
    lambda d:d['Steps'][3]['ArrayCopy'].update(Sources=[]),
    lambda d:d['Steps'][3]['ArrayCopy'].update(Unknown=True),
    lambda d:d['Steps'][3].update(VariableSlot=0),
    lambda d:d['Steps'][3].update(Kind='CheckArrayReferences'),
):
    bad=copy.deepcopy(doc);mutation(bad);run(bad,invalid=True)
doc['Steps']=[copy_values(row1,row0)];run(doc,runtime_error=True)
doc['Steps']=[copy_values(row1,first)];run(doc,runtime_error=True)

print(f'PASS: {checks} array view model checks (source reimport still pending).')
