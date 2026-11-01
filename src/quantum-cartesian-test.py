"""DEV-10 source-adapted Cartesian and family fixtures (independent finite oracles)."""
import json, os, subprocess, sys
from pathlib import Path
worker=str(Path(sys.argv[1] if len(sys.argv)>1 else 'quantum-worker'+('.exe' if os.name=='nt' else '')).resolve())
checks=0
def data(expression, reject=False):
    global checks
    p=subprocess.run([worker,'--json']+flags,input=('quantum:'+expression).encode(),capture_output=True,timeout=30)
    assert (p.returncode!=0)==reject,(expression,p.returncode,p.stdout,p.stderr)
    checks+=1
    return None if reject else json.loads(p.stdout)

for flags in [[], ['--approx']]:
    for expression, expected in [
        (r'cardinality(\{0,1,2\}^{2})','9'),
        ('cardinality(cartesian(vector(0,1),vector(2,3,4)))','6'),
        ('member(tuple(1,4),cartesian(vector(0,1),vector(2,3,4)))','1'),
        ('member(tuple(4,1),cartesian(vector(0,1),vector(2,3,4)))','0'),
        ('cardinality(cartesian(vector(),vector(2)))','0'),
        ('cardinality(cartesianpower(vector(),0))','1'),
        ('member(tuple(),cartesianpower(vector(),0))','1'),
        ('cardinality(cartesianpower(vector(7),3))','1'),
        ('member(tuple(7,7,7),cartesianpower(vector(7),3))','1'),
        (r'replace(cardinality(\{0,1\}^n),n,3)','8'),
        (r'replace(cardinality(\{0,\ldots,n-1\}),n,3)','3'),
        (r'replace(cardinality(\{0,\ldots,n-1\}),n,0)','0'),
        ('cardinality(setimage(k%2,vector(0,1,2,3),k))','2'),
        ('sumset(k,setimage(j%2,vector(0,1,2,3),j),k)','1'),
        ('cardinality(setimage(bitstring(k,5),vector(19,5,5,19,26,1,1,26),k))','4'),
        (r'cardinality(\{k^2:k\in\{0,1,2\}\})','3'),
        ('sumset(k,setimage(sumset(k+j,vector(0,1),j),vector(2,3),k),k)','12'),
        (r'replace(cardinality(\{k\in\{0,1\}:k=x\}),x,0)','1'),
        (r'replace(cardinality(\{k\in\{0,1\}:k=x\}),x,2)','0'),
        ('cardinality(cartesianpower(vector(1,1),10))','1'),
        ('member(tuple(x,1),cartesian(vector(x),vector(1)))','1'),
        ('cardinality(setimage(1,vector(x,y),k))','1'),
        ('sumset(k,setimage(sumset(k,vector(2,3),k),vector(0,1),k),k)','5'),
        ('cardinality(union(vector(1,1),vector(1),1))','1'),
        ('cardinality(intersect(vector(1,1),vector(1),1))','1'),
    ]:
        value=data(expression)
        assert value['text']==expected,(expression,value,expected)

    for expression in [r'cardinality(\{0,1\}^n)',r'cardinality(\{0,\ldots,n-1\})',
                       'cardinality(cartesian(Σ,Γ))','setimage(k^2,Σ,k)',
                       r'cardinality(\{k\in\{0,1\}:k=x\})',
                       'cardinality(cartesianpower(vector(x,y),2))']:
        value=data(expression)
        assert value['text'] not in ['0','1','2','4']
        copy=data(value['copy_text'])
        assert copy['display_text']==value['display_text'],(expression,value,copy)
    pending=data('cardinality(cartesianpower(vector(x,y),11))')
    assert data('replace('+pending['copy_text']+',y,x)')['text']=='1'

    for expression in ['cartesianpower(vector(0,1),-1)','cartesianpower(vector(0,1),1/2)',
                       'cartesianpower(Σ,-1)','cartesian(vector(0,1),2)',
                       'member(tuple(0,bitstring(-1,2)),Σ)',
                       'setfilter(2,vector(0,1),k)',
                       'cartesianpower(vector(0,1),11)']:
        data(expression,True)
    for expression, expected in [(r'\{0,1\}^0','1'),(r'\{3,\ldots,3\}','1'),
                                 (r'\{0,\ldots,-1\}','0'),
                                 (r'\{7\}','1'),(r'\{\}','0'),('cartesianpower(vector(7),3)','1'),
                                 ('setimage(1,vector(0,1),k)','1'),
                                 ('cartesian(vector(),vector(2))','0')]:
        original=data(expression)
        assert data('cardinality('+original['copy_text']+')')['text']==expected, (expression,original)
print(f'{checks} Cartesian and indexed-family checks passed')
