"""Check the known-eigenphase example and exact reciprocal rounding in the Shor lesson."""
import argparse
from fractions import Fraction
from functools import lru_cache
from hashlib import sha256
import json
from math import pi, sin
import os
from pathlib import Path
import subprocess

parser=argparse.ArgumentParser()
parser.add_argument("package",type=Path)
parser.add_argument("windows",type=Path)
parser.add_argument("output",type=Path)
args=parser.parse_args()
worker=args.package.resolve()/"quantum-worker.exe"
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
here=Path(__file__).parent
source=json.loads((here/"ibm029-inventory.json").read_bytes())
records_path=args.windows/"records.json"
windows=json.loads((here/"ibm029-windows-unit-copy.json").read_bytes())
assert sha256(records_path.read_bytes()).hexdigest()==windows["records_sha256"]
records=json.loads(records_path.read_bytes())


@lru_cache(maxsize=1024)
def evaluate(expr,approximate=False):
    flags=["--approx"] if approximate else []
    proc=subprocess.run([worker,"--json",*flags],env=env,input=("quantum:"+expr).encode(),
                        capture_output=True,timeout=90,check=True)
    return json.loads(proc.stdout)


counts={}
def check(number,bindings,expected):
    record=records[number-1]
    assert record["id"]==source["rows"][number-1]["id"]+"-original" and record["restored_same"]
    assert record["label"]==record["reentry_label"]=="EXACT RESULT"
    for form in {record["copy"],record["second_copy"]}:
        for k,v in bindings.items():
            symbol="y" if k=="y" else f'"{k}"'
            form=f"replace(({form}),{symbol},({v}))"
        result=evaluate(f"({form})=({expected})")
        assert not result["approximate"] and result["copy_text"]=="1",(number,bindings,expected)
    counts[number]=counts.get(number,0)+1


distributions=[]
for width in (4,5):
    size=2**width
    ops=[]
    for j in range(width):
        power=2**(width-j-1)
        # On the specified eigenstate, a controlled power leaves the target
        # unchanged and multiplies the control's |1> amplitude by this phase.
        ops.extend([f"apply(H,s_0,[{j}])",f"apply([1,0;0,exp(i*2*pi*{power}/6)],s_0,[{j}])"])
    wires=",".join(map(str,range(width)))
    ops.append(f"apply(fourier({size})~,s_0,[{wires}])")
    expr=f"probs(sequence([{','.join(ops)}],basis(0,{size}),s_0),[{wires}])"
    result=evaluate(expr,True)
    assert result["approximate"] and (result["rows"],result["columns"])==(size,1)
    cells=[complex(cell[0].replace("−","-").replace(" ","").replace("i","j")) for cell in result["cells"]]
    assert all(abs(z.imag)<1e-12 for z in cells)
    observed=[z.real for z in cells]
    expected=[]
    for y in range(size):
        delta=pi*(1/6-y/size)
        expected.append((sin(size*delta)/(size*sin(delta)))**2)
    error=max(abs(a-b) for a,b in zip(observed,expected))
    assert error<1e-12 and abs(sum(observed)-1)<1e-12
    peak=max(range(size),key=observed.__getitem__)
    assert peak=={4:3,5:5}[width]
    rounded=int(Fraction(size,peak)+Fraction(1,2))
    assert rounded=={4:5,5:6}[width]
    distributions.append(dict(width=width,input=expr,probabilities=observed,max_error=error,
                              peak=peak,peak_probability=observed[peak],rounded_reciprocal=rounded))
    for y in range(1,size):
        vals=dict(m=width,y=y)
        check(199,vals,Fraction(y,size))
        check(203,vals,int(Fraction(size,y)+Fraction(1,2)))
        check(213,vals,int(Fraction(size,y)==Fraction(32,5)))
        check(219,vals,int(Fraction(size,y)==Fraction(16,3)))
        error=Fraction(y,size)-Fraction(1,6)
        for offset in (0,Fraction(1,size)):
            bindings=dict(m=width,y=y,r=6,ε=error+offset)
            check(241,bindings,int(offset==0))
            check(244,bindings,int(offset==0))
        check(255,dict(m=width,y=y,r=6,N=21),int(abs(error)<=Fraction(1,2*21**2)))
check(211,{},Fraction(68,100))
assert abs(distributions[1]["peak_probability"]-0.68)<0.01
report=dict(source=source["source"],notebook_sha256=source["source_sha256"],worker_sha256=sha256(worker.read_bytes()).hexdigest(),
            windows_worker_sha256=windows["worker_sha256"],windows_records_sha256=windows["records_sha256"],
            exact_cases=counts,distributions=distributions)
args.output.write_bytes((json.dumps(report,indent=2)+"\n").encode())
print(sum(counts.values()),"exact cases;",[(d["width"],d["peak"],round(d["peak_probability"],7)) for d in distributions])
