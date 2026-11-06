"""Finite transcription of inspected IBM025 diagrams; exact reference arithmetic."""
import hashlib
import itertools
import json
from fractions import Fraction as F
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PLAN_SHA='95e0314a9af5d0c3acef46deb86fb1dba164ee0d228a03d34109c3902b390c31'
SOURCE_SHA='ec06bb65c2b394c9d5053a3dcbcf9407972a8fdca1fed4f0de8c357e91a72df7'
ZERO=(F(0),)*4
ONE=(F(1),F(0),F(0),F(0))
Z=(F(0),F(1),F(0),F(0))
ZD=(F(0),F(0),F(0),F(-1))
HFACTOR=(F(0),F(1,2),F(0),F(-1,2))
GATES=[('H',2),('CX',1,2),('TD',2),('CX',0,2),('T',2),('CX',1,2),('TD',2),('CX',0,2),('T',1),('T',2),('CX',0,1),('T',0),('TD',1),('H',2),('CX',0,1)]

def require(condition,label):
    if not condition:raise AssertionError(label)
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def add(a,b):return tuple(x+y for x,y in zip(a,b))
def neg(a):return tuple(-x for x in a)
def mul(a,b):
    result=[F(0)]*4
    for i,x in enumerate(a):
        for j,y in enumerate(b):
            k=i+j
            result[k%4]+=(-1 if k>=4 else 1)*x*y
    return tuple(result)
def apply(vector,gate):
    out=list(vector);kind,q=gate[:2]
    if kind=='CX':
        target=gate[2]
        for i,a in enumerate(vector):out[i^((1<<target) if i&(1<<q) else 0)]=a
    elif kind in ('T','TD'):
        for i,a in enumerate(vector):
            if i&(1<<q):out[i]=mul(a,Z if kind=='T' else ZD)
    else:
        require(kind=='H','known gate')
        for i in range(len(vector)):
            if not i&(1<<q):
                j=i|(1<<q)
                out[i]=mul(HFACTOR,add(vector[i],vector[j]))
                out[j]=mul(HFACTOR,add(vector[i],neg(vector[j])))
    return out
def swap_bits(i,a,b):
    return i^((1<<a)|(1<<b)) if ((i>>a)^(i>>b))&1 else i
def serialize(v):return [[str(x) for x in a] for a in v]

def main():
    require(digest(ROOT/'PLAN.md')==PLAN_SHA,'frozen plan')
    sourcepath=ROOT.parent/'ibm025-source-analysis/source.ipynb'
    require(digest(sourcepath)==SOURCE_SHA,'source')
    render=json.loads((ROOT/'render-manifest.json').read_bytes())
    require(render['acquisition_manifest_sha256']=='6377ceb37b0e164ac2c89905360ca3946bcbd00e9e6ae2cec0314b98cd9e8ad7','acquisition')
    require(len(render['records'])==8,'eight images')
    for r in render['records']:
        require(digest(r['input'])==r['source_sha256'],'original SVG')
        require(digest(r['output'])==r['output_sha256'],'inspected PNG')
    s=''.join(json.loads(sourcepath.read_bytes())['cells'][0]['source'])
    body=s[1727:2023].split('\\begin{pmatrix}\n')[1].split('\\end{pmatrix}')[0]
    matrix=[[int(x.strip()) for x in row.strip().split('&')] for row in body.strip().split('\\\\')]
    require(len(matrix)==8 and all(len(row)==8 for row in matrix),'original matrix dimensions')
    require(mul(Z,ZD)==ONE,'exact phase inverse')
    require(add(mul(HFACTOR,HFACTOR),mul(HFACTOR,HFACTOR))==ONE,'exact Hadamard normalization')
    cases={k:[] for k in ['toffoli','decomposition','and','or','fanout','swap','clean_query','inverse_query']}
    for i in range(8):
        a,b,c=i&1,(i>>1)&1,(i>>2)&1
        result=a+2*b+4*(c^(a&b))
        column=[matrix[r][i] for r in range(8)]
        require(column==[int(r==result) for r in range(8)],'pictured Toffoli')
        cases['toffoli'].append({'input':i,'output':result,'original_column':column})
        vector=[ONE if j==i else ZERO for j in range(8)]
        for gate in GATES:vector=apply(vector,gate)
        require(vector==[tuple([F(v),F(0),F(0),F(0)]) for v in column],'decomposition exact full column including phase')
        cases['decomposition'].append({'input':i,'full_column_cyclotomic_coefficients':serialize(vector)})
    for a,b in itertools.product(range(2),repeat=2):
        and_actual=(a,b,0^(a&b))
        require(and_actual==(a,b,int(bool(a) and bool(b))),'AND')
        na,nb=a^1,b^1
        or_actual=(na,nb,(0^(na&nb))^1)
        require(or_actual==(1-a,1-b,int(bool(a) or bool(b))),'OR full leftover state')
        cases['and'].append({'input':[a,b,0],'output':and_actual})
        cases['or'].append({'input':[a,b,0],'output':or_actual})
    for a in range(2):
        out=(a,0^a);require(out==(a,a),'FANOUT basis')
        cases['fanout'].append({'input':[a,0],'output':out})
    for a,b in itertools.product(range(2),repeat=2):
        x,y=a,b;y^=x;x^=y;y^=x
        require((x,y)==(b,a),'pictured SWAP')
        cases['swap'].append({'input':[a,b],'output':[x,y]})
    for f in itertools.product(range(2),repeat=4):
        def compute(i):return i^(f[i&3]<<2)
        for x,y in itertools.product(range(4),range(2)):
            initial=x+(y<<3)
            first=swap_bits(compute(initial),0,2)
            copied=first^((first&1)<<3)
            final=compute(swap_bits(copied,0,2))
            expected=x+((y^f[x])<<3)
            require(final==expected and not final&4,'clean query pictured top-output ordering')
            cases['clean_query'].append({'f':f,'x':x,'y':y,'stages':[initial,first,copied,final]})
    for f in itertools.permutations(range(4)):
        inverse=[f.index(y) for y in range(4)]
        for x in range(4):
            low,high=x,0;high^=f[low];computed=[low,high]
            low,high=high,low;swapped=[low,high]
            high^=inverse[low]
            require((low,high)==(f[x],0),'pictured swap before inverse-query')
            cases['inverse_query'].append({'f':f,'x':x,'stages_low_high':[[x,0],computed,swapped,[low,high]]})
    counts={k:len(v) for k,v in cases.items()}
    require(list(counts.values())==[8,8,4,4,2,4,128,96],'frozen counts')
    result={'scope':'Exact diagram transcription plus disclosed finite schematic instances; not native acceptance',
            'plan_sha256':PLAN_SHA,'source_sha256':SOURCE_SHA,'script_sha256':digest(__file__),
            'render_manifest_sha256':digest(ROOT/'render-manifest.json'),'gates':GATES,'counts':counts,'total':sum(counts.values()),
            'arithmetic':'Q[z]/(z^4+1) rational coefficients, z=exp(i*pi/4); exact full amplitudes including phase',
            'numerical_tolerance':None,'cases':cases}
    (ROOT/'check-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'counts':counts,'total':result['total']}))

if __name__=='__main__':main()
