"""Pasted norm forms must preserve the norm order and outside power."""
import subprocess,json,math
from pathlib import Path
worker=Path(__file__).resolve().parent.parent/'dist/QuantumStudio/quantum-worker.exe'
forms=[r'\begin{Vmatrix}3&0\\0&4\end{Vmatrix}',r'\lVert [3,0;0,4]\rVert',r'\left\|[3,0;0,4]\right\|',r'\Biggl\Vert[3,0;0,4]\Biggr\Vert',r'\norm{[3,0;0,4]}','‖[3,0;0,4]‖']
checks=0
for form in forms:
    for suffix,expected in [('_1',7),('₁',7),('_2',5),('₁^2',49),('_{ F }',5),(r'_{ \mathrm{F} }',5),(r'_\mathrm{F}',5),(r'_{\infty}',4),('^2_1',49),('^{2}_{1}',49),('_{1}^{2}',49),('^{1/2}_{2}',math.sqrt(5))]:
        result=subprocess.run([str(worker),'--json','--approx'],input='quantum:'+form+suffix,encoding='utf-8',capture_output=True,timeout=20)
        assert result.returncode==0,(form+suffix,result.stderr)
        value=float(json.loads(result.stdout)['text']);assert abs(value-expected)<2e-9,(form+suffix,value,expected);checks+=1
for expression in [r'\begin{Vmatrix}1&0\\0&1\end{Vmatrix}',r'\begin{Vmatrix}1&0\\0&1\end{Vmatrix}^2',r'\norm{|0>}_{}',r'\norm{|0>}_{ }',r'\norm{|0>}^{}',r'\norm{X}_{0}',r'\norm{X}^{2}_{0}',r'\begin{Vmatrix}1&0\\0&1\end{bmatrix}_1']:
    result=subprocess.run([str(worker),'--json'],input='quantum:'+expression,encoding='utf-8',capture_output=True,timeout=20)
    assert result.returncode!=0,(expression,result.stdout);checks+=1
for expression,expected in [(r'\norm{|0>+|1>}^2','2'),(r'\begin{vmatrix}3&0\\0&4\end{vmatrix}','12')]:
    result=subprocess.run([str(worker),'--json'],input='quantum:'+expression,encoding='utf-8',capture_output=True,timeout=20)
    assert result.returncode==0 and json.loads(result.stdout)['text']==expected,(expression,result.stdout,result.stderr);checks+=1
print(f'PASS: {checks} TeX/Unicode matrix norm, formatted index, power order, invalid input, and unchanged ket/determinant checks.')
