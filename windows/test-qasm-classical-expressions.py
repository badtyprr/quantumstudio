"""Source/frozen classical import equivalence and optional worker outcome checks."""
import argparse,importlib.util,json,os,subprocess,sys
from fractions import Fraction
from pathlib import Path
root=Path(__file__).resolve().parent.parent
p=argparse.ArgumentParser();p.add_argument('--worker',type=Path);p.add_argument('--source-only',action='store_true');a=p.parse_args()
spec=importlib.util.spec_from_file_location('qasm_expression_adapter',root/'windows/qasm-import.py');adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
header='OPENQASM 3.0; include "stdgates.inc"; '
unicode_name='𝑎'*31
cases=[
 ('computed-qloop-result-indices','def f(qubit a)->bool{x a;return true;}qubit[2] q;output bit[2] c;output bit[2] r;for int i in [0:1]{bool ok=f(q[i]);c[i]=1;r[i]=measure q[i];}',{'1111':'1'}),
 ('variable-qloop-static-shadow','const int M=1;const int N=1;def f(qubit a,int n){x a;}qubit[2] q;for int i in [0:M]{f(q[i],N);{int N=2;}}output bit[2] r;r=measure q;',{'11':'1'}),
 ('computed-qloop-local-actual','def f(qubit a,int n){if(n==1){x a;}}qubit[2] q;for int i in [0:1]{int n=1;f(q[i],n);}output bit[2] r;r=measure q;',{'11':'1'}),
 ('computed-qloop-forward','def f(qubit a,int i)->int{x a;return i+1;}qubit[3] q;int n=0;for int i in [0:2]{n=f(q[i],i);}output bit[3] r;output bit ok;r=measure q;ok=n==3;',{'1111':'1'}),
 ('computed-qloop-descending','def f(qubit a)->bool{x a;return true;}qubit[3] q;for int i in [2:-1:0]{bool ok=f(q[i]);}output bit[3] r;r=measure q;',{'111':'1'}),
 ('computed-qloop-stride','def f(qubit a)->bool{x a;return true;}qubit[4] q;for int i in [0:2:3]{bool ok=f(q[i]);}output bit[4] r;r=measure q;',{'0101':'1'}),
 ('qloop-empty','def f(qubit a)->bool{x a;return true;}qubit q;for int i in [1:0]{bool ok=f(q[i]);}output bit r;r=measure q;',{'0':'1'}),
 ('computed-qloop-outer-shadow','def f(qubit a,int i)->int{x a;return i;}qubit[2] q;int i=7;for int i in [0:1]{int n=f(q[i],i);}output bit[2] r;output bit ok;r=measure q;ok=i==7;',{'111':'1'}),
 ('computed-qloop-nested','def f(qubit a,qubit b)->bool{x a;x b;return true;}qubit[2] q;qubit[2] p;for int i in [0:1]{for int j in [0:1]{bool ok=f(q[i],p[j]);}}output bit[2] r;r=measure q;',{'00':'1'}),
 ('computed-qloop-activation','def f(qubit a)->bool{x a;return true;}def g(qubit[2] q)->bool{for int i in [0:1]{bool ok=f(q[i]);}return true;}qubit[2] q;bool done=g(q);output bit[2] r;r=measure q;',{'11':'1'}),
 ('computed-qwidth-spec', 'const uint SIZE=4;qubit[SIZE] q2;def flip(qubit[SIZE] r)->bool{x r;return true;}output bit[4] r;bool ok=flip(q2);r=measure q2;', {'1111':'1'}),
 ('computed-qwidth-arithmetic', 'const int BASE=2;const uint SIZE=BASE+1;def f(qubit[2*BASE-1] q)->bool{x q[2];return true;}qubit[SIZE] q;output bit[3] r;bool ok=f(q);r=measure q;', {'100':'1'}),
 ('computed-qwidth-caller-shadow', 'const int N=2;def f(qubit[N] a)->bool{x a[1];return true;}qubit[N] q;output bit[2] r;{int N=1;bool ok=f(q);}r=measure q;', {'10':'1'}),
 ('computed-qwidth-nested', 'const int N=2;def inner(qubit[N] a)->bool{x a[0];return true;}def outer(qubit[1+1] b)->bool{return inner(b);}qubit[2*N-2] q;output bit[2] r;bool ok=outer(q);r=measure q;', {'01':'1'}),
 ('computed-qwidth-cast', 'const uint[3] N=2;def f(qubit[int[4](N)] a)->bool{x a;return true;}qubit[uint[4](2)] q;output bit[2] r;bool ok=f(q);r=measure q;', {'11':'1'}),
 ('computed-qwidth-one', 'const int N=1;def f(qubit[N] a)->bool{x a;return true;}qubit[N] q;output bit r;bool ok=f(q);r=measure q;', {'1':'1'}),
 ('computed-qwidth-element', 'const int N=2;def f(qubit a)->bool{x a;return true;}qubit[N] q;output bit[2] r;bool ok=f(q[1]);r=measure q;', {'10':'1'}),
 ('computed-qwidth-negative-intermediate', 'def f(qubit[3+(-1)] a)->bool{x a;return true;}qubit[2] q;output bit[2] r;bool ok=f(q);r=measure q;', {'11':'1'}),
 ('computed-qwidth-minimum-constant', 'const int N=2;def f(qubit[N] a)->bool{return true;}qubit[2] q;output bit r;r=f(q);', {'1':'1'}),
 ('computed-qregister-index', 'def f(qubit[3] q)->bool{x q[1];return true;}qubit[3] q;output bit[3] r;bool ok=f(q);r=measure q;', {'010':'1'}),
 ('computed-qregister-nested', 'def g(qubit q)->bool{x q;return true;}def f(qubit[3] a)->bool{return g(a[2]);}def outer(qubit[3] a)->bool{return f(a);}qubit[3] q;output bit[3] r;bool ok=outer(q);r=measure q;', {'100':'1'}),
 ('computed-qregister-repeat', 'def f(qubit[2] a)->bool{x a;return true;}qubit[2] q;output bit[2] r;bool ok=f(q);ok=f(q);r=measure q;', {'00':'1'}),
 ('computed-qregister-measure-reset', 'def f(qubit[2] a)->bit[2]{bit[2] m=measure a;reset a;return m;}qubit[2] q;output bit[4] r;x q[0];r[0:1]=f(q);r[2:3]=measure q;', {'0001':'1'}),
 ('computed-qregister-collision', 'def f(qubit[2] a)->bool{x a[1];return true;}qubit[2] a;qubit[2] b;output bit[4] r;bool ok=f(b);r[0:1]=measure a;r[2:3]=measure b;', {'1000':'1'}),
 ('computed-qregister-width-one', 'def f(qubit[1] a)->bool{x a;return true;}qubit[1] q;output bit r;bool ok=f(q);r=measure q;', {'1':'1'}),
 ('computed-qregister-scope-restore', 'def f(qubit[2] a)->bool{x a[1];return true;}qubit[2] q;output bit[2] r;if(true){int q=1;r[0]=q==1;}bool ok=f(q);r=measure q;', {'10':'1'}),
 ('computed-concat-parity-hh', '\nconst int n = 2;\ndef parity(bit[n] cin) -> bit {\n  bit c = 0;\n  for int i in [0: n - 1] {\n    c ^= cin[i];\n  }\n  return c;\n}\nqubit q;\nqubit r;\nbit c;\nbit c2;\noutput bit result;\nh q;\nh r;\nc = measure q;\nc2 = measure r;\nresult = parity(c ++ c2);\n', {'0': '1/2', '1': '1/2'}),
 ('computed-concat-parity-00', '\nconst int n = 2;\ndef parity(bit[n] cin) -> bit {\n  bit c = 0;\n  for int i in [0: n - 1] {\n    c ^= cin[i];\n  }\n  return c;\n}\nqubit q;\nqubit r;\nbit c;\nbit c2;\noutput bit result;\n\n\nc = measure q;\nc2 = measure r;\nresult = parity(c ++ c2);\n', {'0': '1'}),
 ('computed-concat-parity-01', '\nconst int n = 2;\ndef parity(bit[n] cin) -> bit {\n  bit c = 0;\n  for int i in [0: n - 1] {\n    c ^= cin[i];\n  }\n  return c;\n}\nqubit q;\nqubit r;\nbit c;\nbit c2;\noutput bit result;\n\nx r;\nc = measure q;\nc2 = measure r;\nresult = parity(c ++ c2);\n', {'1': '1'}),
 ('computed-concat-parity-10', '\nconst int n = 2;\ndef parity(bit[n] cin) -> bit {\n  bit c = 0;\n  for int i in [0: n - 1] {\n    c ^= cin[i];\n  }\n  return c;\n}\nqubit q;\nqubit r;\nbit c;\nbit c2;\noutput bit result;\nx q;\n\nc = measure q;\nc2 = measure r;\nresult = parity(c ++ c2);\n', {'1': '1'}),
 ('computed-concat-parity-11', '\nconst int n = 2;\ndef parity(bit[n] cin) -> bit {\n  bit c = 0;\n  for int i in [0: n - 1] {\n    c ^= cin[i];\n  }\n  return c;\n}\nqubit q;\nqubit r;\nbit c;\nbit c2;\noutput bit result;\nx q;\nx r;\nc = measure q;\nc2 = measure r;\nresult = parity(c ++ c2);\n', {'0': '1'}),
 ('concat-mixed-width', 'bit[2] a="10";bit[3] b="101";output bit[5] r;r=a ++ b;', {'10110': '1'}),
 ('computed-concat-computed-operands', 'bit[2] a="10";bit[3] b="101";output bit[5] r;r=(a^"01") ++ (b&"011");', {'00111': '1'}),
 ('computed-concat-literal-operands', 'output bit[5] r;r="10" ++ "101";', {'10110': '1'}),
 ('computed-concat-precedence', 'bit a=1;bit b=0;bit c=1;output bit[2] r;r=a ++ b || c;', {'11': '1'}),

 ('range-runtime-returned-range', 'def bound(bit b)->int{return int(b)+1;}qubit q;bit b=1;output bit r;for int i in [0:bound(b)]{x q;}r=measure q;', {'1': '1'}),
 ('transfer-returned-condition-continue', 'def flip(qubit q)->bit{x q;return measure q;}qubit q;output bit r;while(flip(q)==1){continue;}r=measure q;', {'0': '1'}),
 ('computed-result-void-quantum-only', 'def f(qubit q){bit b=measure q;if(b==1){return;}x q;}qubit q;output bit r;x q;f(q);r=measure q;', {'1': '1'}),
 ('computed-result-void-no-arguments', 'def f(){return;}output bit r;f();', {'0': '1'}),
 ('computed-result-logical-and-skip', 'def flip(qubit q)->bool{x q;return true;}qubit q;bool take=false;output bit r;bool ignored=take&&flip(q);r=measure q;', {'0': '1'}),
 ('computed-result-logical-or-skip', 'def flip(qubit q)->bool{x q;return false;}qubit q;bool take=true;output bit r;bool ignored=take||flip(q);r=measure q;', {'0': '1'}),
 ('computed-result-logical-and-run', 'def flip(qubit q)->bool{x q;return true;}qubit q;bool take=true;output bit r;bool ignored=take&&flip(q);r=measure q;', {'1': '1'}),
 ('computed-result-logical-skip-undefined', 'def f(bit b)->bool{if(b==1){return true;}}bit b;output bit r;bool ok=false&&f(b);r=ok;', {'0': '1'}),
 ('computed-result-measured-parity', 'const int n=2;def parity(bit[n] cin)->bit{bit c;for int i in [0:n-1]{c^=cin[i];}return c;}qubit[2] q;bit[2] m;output bit r;x q[0];m=measure q;r=parity(m);', {'1': '1'}),
 ('computed-result-runtime-integer', 'def addone(int[8] v)->int[8]{return v+1;}qubit q;bit m;output bit r;m=measure q;int[8] value=addone(int[8](m));r=value==1;', {'1': '1'}),
 ('transfer-result-early-loop', 'def f(bit b)->bit{while(b==1){return b;}return 0;}bit m=1;output bit r;r=f(m);', {'1': '1'}),
 ('transfer-result-condition-reevaluation', 'def flipmeasure(qubit q)->bit{x q;return measure q;}qubit q;output bit r;while(flipmeasure(q)==1){}r=measure q;', {'0': '1'}),
 ('computed-result-nested-result', 'def readout(qubit q)->bit{return measure q;}def copied(bit v)->bit{return v;}qubit q;output bit r;x q;r=copied(readout(q));', {'1': '1'}),
 ('computed-result-xmeasure', '// Subroutine unchanged from the OpenQASM specification; driver added here.\ndef xmeasure(qubit q) -> bit { h q; return measure q; }\nqubit q;\noutput bit result;\nresult = xmeasure(q);', {'0': '1/2', '1': '1/2'}),
 ('computed-result-missing', 'def f(bit b)->bit{if(b==1){return b;}}bit b;output bit r;r=f(b);', None),
 ('computed-result-missing-discarded', 'def f(bit b)->bit{if(b==1){return b;}}bit b;output bit r;f(b);', None),
 ('computed-result-bool', 'def f(bit b)->bool{return b==1;}bit b=1;output bit r;r=f(b);', {'1': '1'}),
 ('computed-result-register', 'def f(bit[2] b)->bit[2]{return b;}bit[2] b="10";output bit[2] r;r=f(b);', {'10': '1'}),
 ('computed-return-early-void', 'def f(bit b,qubit q){if(b==1){return;}x q;}qubit q;bit m=1;output bit r;f(m,q);r=measure q;', {'0': '1'}),
 ('computed-return-fallthrough', 'def f(bit b,qubit q){if(b==1){return;}x q;}qubit q;bit m;output bit r;f(m,q);r=measure q;', {'1': '1'}),
 ('transfer-return-nested-loops', 'def f(bit b,qubit q){while(b==1){for int i in [0:1]{return;}x q;}x q;}qubit q;bit m=1;output bit r;f(m,q);r=measure q;', {'0': '1'}),
 ('computed-return-nested-call', 'def inner(bit b,qubit q){if(b==1){return;}x q;}def outer(bit b,qubit q){inner(b,q);x q;}qubit q;bit m=1;output bit r;outer(m,q);r=measure q;', {'1': '1'}),
 ('loop-return-reinitialize', 'def f(bit b,qubit q){if(b==1){return;}x q;}qubit q;bit again=1;bit flag=1;output bit r;while(again==1){f(flag,q);if(flag==0){again=0;}flag=0;}r=measure q;', {'1': '1'}),
 ('computed-return-local-before-return', 'def f(bit b,qubit q){int n=1;if(b==1){return;}if(n==1){x q;}}qubit q;bit m;output bit r;f(m,q);r=measure q;', {'1': '1'}),
 ('computed-return-switch-return', 'def f(bit b,qubit q){switch(int(b)){case 1{return;}default{x q;}}x q;}qubit q;bit m=1;output bit r;f(m,q);r=measure q;', {'0': '1'}),
 ('call-bit-nested', 'def inner(bit[2] v){v="00";}def outer(bit[2] v,qubit q){inner(v);if(v=="11"){x q;}}qubit q;bit[2] m="11";output bit r;outer(m,q);r=measure q;', {'1': '1'}),
 ('call-bit-local-measure', 'def f(bit v,qubit q){bit saved=measure q;if(saved==v){x q;}}qubit q;bit m=1;output bit r;x q;f(m,q);r=measure q;', {'0': '1'}),
 ('call-bit-local-shadow', 'def f(bit v,qubit q){bit local=v;{bit local=0;}if(local==1){x q;}}qubit q;bit m=1;output bit r;f(m,q);r=measure q;', {'1': '1'}),
 ('scope-call-bit-width-shadow', 'const int width=2;def f(bit[width] v,qubit q){if(v=="11"){x q;}}qubit q;bit[2] m="11";output bit r;{int width=1;f(m,q);}r=measure q;', {'1': '1'}),
 ('call-bit-measured','def f(bit value,qubit q){if(value==1){x q;}}qubit[2] q;bit m;output bit[2] r;h q[0];m=measure q[0];f(m,q[1]);r=measure q;',{'00':'1/2','11':'1/2'}),
 ('call-bit-snapshot','def f(bit value){value=0;}bit m=1;f(m);',{'1':'1'}),
 ('call-bit-local-width','def f(bit value){const int width=2;bit[width] local;local[0]=value;}bit m=1;f(m);',{'1':'1'}),
 ('call-bit-register','def f(bit[2] value,qubit q){value[0]=0;if(value=="10"){x q;}}qubit q;bit[2] m="11";output bit r;f(m,q);r=measure q;',{'1':'1'}),
 ('loop-call-bit-reset','def f(bit flag,qubit q){bit local;if(flag==1){local=1;}if(local==1){x q;}}qubit q;bit again=1;bit flag=1;output bit r;while(again==1){reset q;f(flag,q);if(flag==0){again=0;}flag=0;}r=measure q;',{'0':'1'}),
 ('computed-call-lexical-constant', 'const int k=1;def f(int n,qubit q){if(k==1){x q;}}qubit q;bit m;output bit r;m=measure q;{int k=0;f(int[32](m),q);}r=measure q;', {'1': '1'}),
 ('computed-call-lexical-width', 'const int width=8;def f(uint[width] n,qubit q){if(n==0){x q;}}qubit q;bit m;output bit r;m=measure q;{int width=1;f(uint[8](m),q);}r=measure q;', {'1': '1'}),
 ('computed-call-bool', 'def f(bool b,qubit target){if(b){x target;}}qubit[2] q;bit m;output bit r;x q[0];m=measure q[0];f(bool(int[32](m)),q[1]);r=measure q[1];', {'1': '1'}),
 ('loop-call-reinitialize', 'def f(int[32] n,qubit target){int[32] k=n;if(k==1){x target;}}qubit[2] q;bit m;output bit r;h q[0];m=measure q[0];int count=2;while(count>0){f(int[32](m),q[1]);count-=1;}r=measure q[1];', {'0': '1'}),
 ('computed-call-nested', 'def feedback(int[32] value, qubit target) {\n    int[32] local = value;\n    value = 0;\n    if (local == 1) { x target; }\n}\ndef pair(int[32] value, qubit target) {\n    feedback(value, target);\n    if (value == 1) { x target; }\n}\nqubit[4] q;\nbit m;\noutput bit[4] result;\nint[32] local = 7;\nh q[0];\nm = measure q[0];\nfeedback(int[32](m), q[1]);\nfor int i in [0:1] { pair(int[32](m), q[2]); }\nif (local == 7) { x q[3]; }\nresult = measure q;\n', {'1000': '1/2', '1011': '1/2'}),
 ('computed-call-snapshot', 'def f(int[32] n,qubit target){n=0;} qubit q;bit m;output bit r;x q;m=measure q;int[32] n=int[32](m);f(n,q);r=n==1;', {'1': '1'}),
 ('computed-call-alternating', 'def f(int[32] n,qubit target){int[32] local=n;if(local==1){x target;}} qubit[2] q;bit m;output bit r;h q[0];m=measure q[0];int[32] n=int[32](m);f(n,q[1]);f(1-n,q[1]);r=measure q[1];', {'1': '1'}),
 ('computed-call-switch', 'def f(int[32] n,qubit target){switch(n){case 0{int[32] n=1;if(n==1){x target;}}default{int[32] n=2;if(n==2){x target;}}}} qubit[2] q;bit m;output bit r;h q[0];m=measure q[0];f(int[32](m),q[1]);r=measure q[1];', {'1': '1'}),
 ('computed-call-fresh-local', 'def f(int[32] n,qubit target){int[32] value;if(n==1){value=1;}if(value==1){x target;}}qubit[2] q;bit m;output bit r;x q[0];m=measure q[0];f(int[32](m),q[1]);f(int[32](m)-1,q[1]);r=measure q[1];', None),
 ('local-output-empty','if(true){bit[2] scratch;scratch="11";}',{'':'1'}),
 ('local-output-global','bit result;if(true){bit[2] scratch;scratch="11";result=scratch[0];}',{'1':'1'}),
 ('local-output-measurement','qubit q;h q;bit result;if(true){bit scratch=measure q;result=scratch;}',{'0':'1/2','1':'1/2'}),
 ('local-output-wide','if(true){bit[64] scratch;scratch="1'+('0'*63)+'";}',{'':'1'}),
 ('local-output-subroutine','def run(){bit[2] scratch;scratch="11";}run();',{'':'1'}),
 ('local-output-nested','bit result;if(true){bit a="1";if(true){bit b="1";result=a & b;}}',{'1':'1'}),
 ('local-output-explicit','output bit result;bit other="1";if(true){bit scratch="1";result=scratch;}',{'1':'1'}),
 ('explicit-output-selection','output bit[2] result;bit[3] c="100";result=c[{2,0}];',{'01':'1'}),
 ('explicit-output-many','output bit a;bit[2] scratch="11";output bit[2] b;a="1";b="10";',{'101':'1'}),
 ('explicit-output-measured','qubit q;h q;bit scratch=measure q;output bit result;result=~scratch;',{'0':'1/2','1':'1/2'}),
 ('explicit-output-early-declaration','bit[2] scratch="11";output bit result;result="0";',{'0':'1'}),
 ('explicit-output-default','output bit result;bit scratch="1";',{'0':'1'}),
 ('explicit-output-wide','output bit[64] result;result="1'+('0'*63)+'";',{'1'+('0'*63):'1'}),
 ('typed-shift-unsigned-left','qubit q;x q;bit[8] c="10000000";c[0]=measure q;bit[8] out;out=c<<uint[8]("00000001");',{'0000001010000001':'1'}),
 ('typed-shift-unsigned-right','qubit q;x q;bit[8] c="10000000";c[0]=measure q;bit[8] out;out=c>>uint[8]("00000001");',{'0100000010000001':'1'}),
 ('variable-shift-unsigned-count','qubit q;x q;bit[8] c="10000000";c[0]=measure q;uint[8] n=uint[8](c);bit[8] out;out=c<<n;',{'0000000010000001':'1'}),
 ('typed-shift-unsigned-max','qubit q;x q;bit[8] c="10000000";c[0]=measure q;bit[8] out;out=c<<uint[64](18446744073709551615);',{'0000000010000001':'1'}),
 ('computed-shift-unsigned-bits','qubit q;x q;bit[8] c="10000000";c[0]=measure q;bit[8] out;out=c<<uint[8](c & "00000001");',{'0000001010000001':'1'}),
 ('boolean-bitcast-measured','qubit q;h q;bit c=measure q;bit d;d=bit[1](c=="1");',{'00':'1/2','11':'1/2'}),
 ('boolean-bitcast-negated','qubit q;h q;bit c=measure q;bit d;d=bit[1](!(c=="1"));',{'01':'1/2','10':'1/2'}),
 ('computed-boolean-bitcast-integer','qubit q;h q;bit c=measure q;bit d;d=bit[1](int[1](c)<0);',{'00':'1/2','11':'1/2'}),
 ('computed-boolean-bitcast-logical','qubit q;h q;bit c=measure q;bit d;d=bit[1]((c=="1") || (int[1](c)==0));',{'10':'1/2','11':'1/2'}),
 ('subroutine-local-bool','def f(qubit a){bool b=true;if(b){x a;}}qubit q;f(q);bit c=measure q;',{'1':'1'}),
 ('subroutine-local-repeat','def f(qubit a){int n=1;n+=1;if(n==2){x a;}}qubit q;f(q);f(q);bit c=measure q;',{'0':'1'}),
 ('subroutine-local-shadow','int n=3;def f(qubit a){int n=1;if(n==1){x a;}}qubit q;f(q);bit c=measure q;bit d=n==3;',{'11':'1'}),
 ('subroutine-local-nested','def inner(qubit a){int n=1;if(n==1){x a;}}def outer(qubit a){int n=2;inner(a);if(n==2){x a;}}qubit q;outer(q);bit c=measure q;',{'0':'1'}),
 ('subroutine-local-parameter','def f(int n,qubit a){n+=1;if(n==2){x a;}}qubit q;f(1,q);bit c=measure q;',{'1':'1'}),
 ('range-runtime-upper','int n=3;int total=0;bit c;for int i in [0:n]{total+=i;}c=total==6;',{'1':'1'}),
 ('range-runtime-signed-limit','int n=9223372036854775807;int total=0;bit c;for int i in [9223372036854775806:n]{total+=1;}c=total==2;',{'1':'1'}),
 ('range-runtime-unsigned-limit','uint n=18446744073709551615;int total=0;bit c;for uint i in [18446744073709551614:n]{total+=1;}c=total==2;',{'1':'1'}),
 ('range-runtime-negative-limit','int n=-9223372036854775808;int total=0;bit c;for int i in [-9223372036854775807:-1:n]{total+=1;}c=total==2;',{'1':'1'}),
 ('range-runtime-binding-width','int n=129;int total=0;bit c;for int[8] i in [127:n]{total+=i;}c=total==-128;',{'1':'1'}),
 ('range-runtime-nested','int n=2;int total=0;bit c;for int i in [0:n]{for int j in [0:i]{total+=1;}}c=total==6;',{'1':'1'}),
 ('range-runtime-in-static','int n=1;int total=0;bit c;for int j in [0:1]{for int i in [j:n]{total+=1;}}c=total==3;',{'1':'1'}),
 ('range-runtime-static-in-body','int n=1;int total=0;bit c;for int i in [0:n]{for int j in [0:1]{total+=j;}}c=total==2;',{'1':'1'}),
 ('range-runtime-local-lifetime','int n=1;bit c;for int i in [0:n]{int x;if(i==0){x=1;continue;}c=x==1;}',None),
 ('range-runtime-capture','int n=3;int total=0;bit c;for int i in [0:n]{total+=i;n=0;}c=total==6;',{'1':'1'}),
 ('range-runtime-binding-write','int n=2;int total=0;bit c;for int i in [0:n]{total+=i;i=9;}c=total==3;',{'1':'1'}),
 ('range-runtime-shadow','int i=7;int n=2;int total=0;bit c;for int i in [0:n]{total+=i;}c=total==3 && i==7;',{'1':'1'}),
 ('range-runtime-continue','int n=3;int total=0;bit c;for int i in [0:n]{if(i==1){continue;}total+=i;}c=total==5;',{'1':'1'}),
 ('range-runtime-break','int n=3;int total=0;bit c;for int i in [0:n]{total+=i;break;}c=total==0;',{'1':'1'}),
 ('range-runtime-end','int n=3;bit c;for int i in [0:n]{c=1;end;}c=0;',{'1':'1'}),
 ('range-runtime-descending','int n=5;int step=-2;int total=0;bit c;for int i in [n:step:0]{total+=i;}c=total==9;',{'1':'1'}),
 ('range-runtime-empty','int n=-1;bit c=1;for int i in [0:n]{c=0;}',{'1':'1'}),
 ('range-runtime-zero-step','int n=1;bit c;for int i in [0:0:n]{c=1;}',None),
 ('range-runtime-undefined','int n;bit c;for int i in [0:n]{c=1;}',None),
 ('range-runtime-feedback','qubit q;h q;bit b=measure q;int n=int[1](b);int total=0;bit c;for int i in [0:n]{total+=1;}c=total==1;',{'01':'1/2','10':'1/2'}),
 ('variable-range-positive-boundary','int n=0;bit c;for int i in [0:2:5]{n+=i;}c=n==6;',{'1':'1'}),
 ('variable-range-negative-boundary','int n=0;bit c;for int i in [5:-2:0]{n+=i;}c=n==9;',{'1':'1'}),
 ('transfer-range-boundary','int n=0;bit c;for int i in [0:2:5]{n+=i;continue;}c=n==6;',{'1':'1'}),
 ('end-for-after-continue','bit c;for int i in [0:2]{if(i==0){continue;}c=1;end;c=0;}c=0;',{'1':'1'}),
 ('end-for-before-break','bit c;for int i in [0:2]{c=1;end;break;}c=0;',{'1':'1'}),
 ('end-for-nested-transfer','bit c;for int i in [0:2]{for int j in [0:2]{break;}c=1;end;continue;}c=0;',{'1':'1'}),
 ('end-for-measurement','qubit q;h q;bit c=measure q;for int i in [0:2]{if(c){end;}continue;}c=1;',{'1':'1'}),
 ('end-unentered-loop','bit c;while(c){end;}',{'0':'1'}),
 ('end-top','bit c;end;c=1;',{'0':'1'}),
 ('end-saved','bit c=1;end;c=0;',{'1':'1'}),
 ('end-branch','bit c=1;if(c){end;}c=0;',{'1':'1'}),
 ('end-untaken','bit c;if(c){end;}c=1;',{'1':'1'}),
 ('end-nested','bit c;while(true){while(true){c=1;end;}c=0;}c=0;',{'1':'1'}),
 ('end-static-for','bit c;for int i in [0:2]{c=1;end;c=0;}c=0;',{'1':'1'}),
 ('end-measured','qubit q;h q;bit c=measure q;if(c){end;}c=1;',{'1':'1'}),
 ('end-undefined','int a;bit c;end;c=a==1;',{'0':'1'}),
 ('transfer-for-break','bit c;for int i in [0:2]{c=i==1;if(c){break;}}',{'1':'1'}),
 ('transfer-for-continue','int n=0;bit c;for int i in [0:3]{if(i==1){continue;}n+=i;}c=n==5;',{'1':'1'}),
 ('transfer-for-scoped-break','bit c;for int i in [0:2]{int a=3;c=a==3;break;}',{'1':'1'}),
 ('transfer-for-scoped-continue','bit c;for int i in [0:2]{int a=3;continue;c=a==3;}',{'0':'1'}),
 ('transfer-for-nested','int n=0;bit c;for int i in [0:1]{for int j in [0:2]{n+=1;break;}}c=n==2;',{'1':'1'}),
 ('transfer-for-in-while','int n=2;bit c;while(n>0){for int i in [0:2]{c=i==0;break;}n-=1;}',{'1':'1'}),
 ('transfer-for-while-ownership','int n=0;bit c;for int i in [0:2]{while(true){break;}n+=1;if(i==1){break;}}c=n==2;',{'1':'1'}),
 ('transfer-for-collision','int _for_active_1=7;bit c;for int i in [0:2]{break;}c=_for_active_1==7;',{'1':'1'}),
 ('transfer-for-fresh-local','bit c;for int i in [0:1]{int a;if(i==0){a=3;continue;}c=a==3;}',None),
 ('transfer-for-measured','qubit q;h q;bit c=measure q;for int i in [0:2]{if(c){break;}c=1;}',{'1':'1'}),
 ('transfer-for-wires','qubit[2] q;bit[2] c;for int i in [0:1]{x q[i];continue;x q[i];}c=measure q;',{'11':'1'}),
 ('transfer-for-discrete','int n=0;bit c;for int i in {1,3,7}{n+=i;if(i==3){break;}}c=n==4;',{'1':'1'}),
 ('transfer-break','bit c;while(true){c=1;break;c=0;}',{'1':'1'}),
 ('transfer-continue','int n=3;bit c;while(n>0){n-=1;continue;c=1;}',{'0':'1'}),
 ('transfer-shadow','int n=3;bit c;while(true){int n=9;{int k=2;c=n==9 && k==2;break;}}c=c && n==3;',{'1':'1'}),
 ('transfer-nested','int n=2;bit c;while(n>0){int k=7;while(true){int a=1;break;}c=k==7;n-=1;}',{'1':'1'}),
 ('transfer-continue-scope','int n=2;bit c;while(n>0){int k;n-=1;if(n==1){k=3;continue;}c=k==3;}',None),
 ('transfer-branch','bit c;while(true){if(c==0){int a=3;c=a==3;break;}c=0;}',{'1':'1'}),
 ('transfer-switch','int n=2;bit c;while(true){switch(n){case 2{int a=3;c=a==3;break;}default{c=0;}}c=0;}',{'1':'1'}),
 ('transfer-measurement','qubit q;h q;bit c=measure q;while(true){if(c){break;}c=1;break;}',{'1':'1'}),
 ('transfer-in-for','bit c;for int i in [0:1]{while(true){int a=2;c=i==1;break;}}',{'1':'1'}),
 ('transfer-followed-loop','bit c;while(true){c=1;break;}while(false){}',{'1':'1'}),
 ('loop-countdown','int[8] n=3;bit c;while(n>0){n-=1;c=n==0;}',{'1':'1'}),
 ('loop-bit','qubit q;bit c=1;while(c==1){c=0;}',{'0':'1'}),
 ('loop-false-scope','bit c;while(false){int a=1;}',{'0':'1'}),
 ('loop-nested','int n=2;bit c;while(n>0){int k=2;while(k>0){k-=1;}n-=1;c=k==0 && n==0;}',{'1':'1'}),
 ('loop-shadow','int n=2;bit c;while(n>0){int n=3;c=n==3;} ',None),
 ('loop-local-fresh','int n=2;bit c;while(n>0){int a;if(n==2){a=1;}c=a==1;n-=1;}',None),
 ('loop-boolean-measure','qubit q;x q;bool b=true;bit c;while(b){b=measure q;reset q;}c=!b;',{'1':'1'}),
 ('loop-measure-history','qubit q;h q;bit c=measure q;while(c){x q;c=measure q;}',{'0':'1'}),
 ('loop-boolean-local','qubit q;x q;int n=2;bit c;while(n>0){bool b=measure q;c=b;reset q;n-=1;}',{'0':'1'}),
 ('loop-for','int n=2;bit c;while(n>0){for int i in [0:1]{c=i==1;}n-=1;}',{'1':'1'}),
 ('loop-in-for','bit c;for int i in [0:1]{int n=2;while(n>0){n-=1;c=n==0;}}',{'1':'1'}),
 ('loop-switch','int n=2;bit c;while(n>0){switch(n){case 2{c=0;}default{c=1;}}n-=1;}',{'1':'1'}),
 ('loop-lazy-undefined','bool b;bit c;while(false && b){c=1;}',{'0':'1'}),
 ('loop-undefined','bool b;bit c;while(b){c=1;}',None),
 ('loop-infinite-empty','bit c;while(true){}',None),
 ('constant-switch-expression','bit c;switch(1+1){case 2{c=1;}}',{'1':'1'}),
 ('constant-switch-negative','bit c;switch(-1){case -1{c=1;}}',{'1':'1'}),
 ('constant-switch-cast','bit c;switch(int(true)){case 1{c=1;}}',{'1':'1'}),
 ('constant-switch-default','bit c;switch(3){case 2{c=0;}default{c=1;}}',{'1':'1'}),
 ('constant-switch-local','const int n=2;bit c;switch(n){case 2{const int k=1;c=k==1;}default{const int k=2;c=k==1;}}',{'1':'1'}),
 ('variable-switch-constant-mutation','int n=1;bit c;switch(1){case 1{n=2;c=1;}case 2{c=0;}}c=c && n==2;',{'1':'1'}),
 ('computed-switch-bool-add','bool b=true;bit c;switch(b+1){case 2{c=1;}}',{'1':'1'}),
 ('computed-switch-bool-pair','bool b=true;bit c;switch(b+b){case 2{c=1;}}',{'1':'1'}),
 ('computed-switch-bool-negative','bool b=true;bit c;switch(-b){case -1{c=1;}}',{'1':'1'}),
 ('computed-switch-bool-compare','int n=2;bit c;switch((n==2)+1){case 2{c=1;}}',{'1':'1'}),
 ('computed-switch-bool-guard','bool b;bit c;switch((false && b)+1){case 1{c=1;}}',{'1':'1'}),
 ('computed-switch-bool-undefined','bool b;bit c;switch(b+1){case 1{c=1;}}',None),
 ('variable-switch-match','int n=2;bit c;switch(n){case 1{c=0;}case 2{c=1;}default{c=0;}}',{'1':'1'}),
 ('variable-switch-default','int n=9;bit c;switch(n){case 1{c=0;}default{c=1;}}',{'1':'1'}),
 ('variable-switch-no-default','int n=9;bit c=1;switch(n){case 1{c=0;}}',{'1':'1'}),
 ('variable-switch-no-fallthrough','int n=1;bit c;switch(n){case 1{n=2;c=1;}case 2{c=0;}}',{'1':'1'}),
 ('variable-switch-labels','const int k=2;int n=3;bit c;switch(n){case 0,k,k+1{c=1;}}',{'1':'1'}),
 ('variable-switch-expression','int n=2;bit c;switch(n+1){case 3{c=1;}}',{'1':'1'}),
 ('variable-switch-negative','int[8] n=-2;bit c;switch(n){case -2{c=1;}}',{'1':'1'}),
 ('variable-switch-unsigned','uint n=18446744073709551615;bit c;switch(n){case 18446744073709551615{c=1;}}',{'1':'1'}),
 ('variable-switch-nested','int n=2;int m=3;bit c;switch(n){case 2{switch(m){case 3{c=1;}}}}',{'1':'1'}),
 ('variable-switch-scope','int n=2;bit c;switch(n){case 2{int n=3;c=n==3;}default{int n=4;c=n==3;}}c=c && n==2;',{'1':'1'}),
 ('variable-switch-loop','bit c;for int i in [0:1]{int n=i;switch(n){case 1{c=1;}default{c=0;}}}',{'1':'1'}),
 ('variable-switch-undefined','int n;bit c;switch(n){case 0{c=1;}default{c=0;}}',None),
 ('variable-switch-skipped','int n;bit c;if(c){switch(n){case 0{c=1;}}}',{'0':'1'}),
 ('variable-switch-popcount','int n=0;bit[3] c="101";switch(popcount(c)){case 2{c="111";}}',{'111':'1'}),
 ('computed-switch-measurement','qubit q;h q;bool b=measure q;bit c;switch(int(b)){case 1{x q;}}c=measure q;',{'0':'1'}),
 ('typed-switch-bitcast','bit[3] c="111";bit r;switch(int[3](c)){case -1{r=1;}}',{'1111':'1'}),
 ('typed-switch-constants','bit[2] c="01";bit r;switch(int[2](c)){case 1{const int k=1;r=k==1;}default{const int k=2;r=k==1;}}',{'101':'1'}),
 ('computed-switch-local-measurement','qubit q;int n=1;bit c;switch(n){case 1{bool b=measure q;c=!b;}}',{'1':'1'}),
 ('computed-bmeasure-initializer','qubit q;h q;bool b=measure q;bit c;c=b;',{'0':'1/2','1':'1/2'}),
 ('computed-bmeasure-assignment','qubit q;x q;bool b=false;b=measure q;bit c;c=b;',{'1':'1'}),
 ('computed-bmeasure-history','qubit q;h q;bool b=measure q;reset q;bool a=measure q;bit c;c=b && !a;',{'0':'1/2','1':'1/2'}),
 ('computed-bmeasure-feedback','qubit q;h q;bool b=measure q;if(b){x q;}bit c;c=measure q;',{'0':'1'}),
 ('computed-bmeasure-loop','qubit q;x q;bit c;for int i in [0:1]{bool b=measure q;c=b;reset q;}',{'0':'1'}),
 ('computed-bmeasure-shadow','qubit q;bool b=true;bit c;{bool b=measure q;c=!b;}c=c && b;',{'1':'1'}),
 ('computed-bmeasure-skipped','qubit q;bool b;bit c;if(c){b=measure q;}c=b;',None),
 ('computed-bmeasure-guard','qubit q;bool b;bit c;if(c){b=measure q;}c=false && b;',{'0':'1'}),
 ('computed-bmeasure-empty','qubit q;h q;bool b=measure q;',{'':'1'}),
 ('computed-bmeasure-collision','qubit q;bit _boolean_measurement=1;bool b=measure q;bit c;c=b;',{'01':'1'}),
 ('computed-bmeasure-capacity','qubit q;x q;bit[63] c;bool b=measure q;c[0]=b;',{'0'*62+'1':'1'}),
 ('computed-bool-variable','bool b=true;bit c;c=b;',{'1':'1'}),
 ('computed-bool-toggle','bool b=false;bit c;b=!b;c=b;',{'1':'1'}),
 ('computed-bool-copy','bool a=true;bool b=a;a=false;bit c;c=b;',{'1':'1'}),
 ('computed-bool-logical','bool a=true;bool b=false;bit c;c=a && !b;',{'1':'1'}),
 ('computed-bool-integer','int n=-2;bool b=n;bit c;c=b;',{'1':'1'}),
 ('computed-bool-zero','int n=0;bool b=n;bit c;c=!b;',{'1':'1'}),
 ('computed-bool-literal','bool b=2;bit c;c=b;',{'1':'1'}),
 ('computed-bool-popcount','bit[3] c="111";bool b=popcount(c);c[0]=!b;',{'110':'1'}),
 ('computed-bool-scalar-bits','bit a=1;bit c=0;bool b=a ^ c;c=b;',{'11':'1'}),
 ('computed-bool-compare','bool b=true;bit c;c=b==2;',{'0':'1'}),
 ('computed-bool-promote','bool a=true;bool b=true;int n=a+b;bit c;c=n==2;',{'1':'1'}),
 ('computed-bool-array-cast','bit[3] c="010";bool b=bool(c);c[0]=b;',{'011':'1'}),
 ('computed-bool-measurement','qubit q;bit c;h q;c=measure q;bool b=c;c=0;c=b;',{'0':'1/2','1':'1/2'}),
 ('computed-bool-feedback','qubit q;bit c;h q;c=measure q;bool b=c;if(b){x q;}c=measure q;',{'0':'1'}),
 ('computed-bool-shadow','bool b=true;bit c;{bool b=false;c=!b;}c=c && b;',{'1':'1'}),
 ('computed-bool-fresh','bit c;for int i in [0:1]{bool b;if(i==0){b=true;}else{c=b;}}',None),
 ('variable-boolean-uninitialized','bool b;bit c;c=b;',None),
 ('variable-boolean-guard','bool b;bit c;c=false && b;',{'0':'1'}),
 ('variable-rotate','int n=1;bit[3] c="001";c=rotl(c,n);',{'010':'1'}),
 ('variable-rotate-negative','int[8] n=-1;bit[3] c="001";c=rotl(c,n);',{'100':'1'}),
 ('variable-rotate-arithmetic','int n=1;bit[3] c="001";c=rotr(c,n+1);',{'010':'1'}),
 ('variable-rotate-min','int n=-9223372036854775808;bit[3] c="001";c=rotl(c,n);',{'010':'1'}),
 ('variable-rotate-unsigned','uint n=18446744073709551615;bit[3] c="001";c=rotl(c,n);',{'001':'1'}),
 ('variable-rotate-unsigned-arithmetic','uint n=18446744073709551615;bit[3] c="001";c=rotl(c,n+0);',{'001':'1'}),
 ('variable-rotate-undefined','int n;bit[3] c="001";c=rotl(c,n);',None),
 ('variable-rotate-overflow','int n=9223372036854775807;bit[3] c="001";c=rotl(c,n+1);',None),
 ('variable-rotate-guard','int n;bit[3] c="001";if(c==0){c=rotl(c,n);}',{'001':'1'}),
 ('computed-rotate-scalar','bit c=1;bit[3] r="001";r=rotl(r,int[8](c));',{'0101':'1'}),
 ('computed-rotate-expression','bit[3] c="001";c=rotl(c,uint[3](c ^ "111"));',{'001':'1'}),
 ('computed-rotate-measurement','qubit q;bit[3] c="001";bit m;h q;m=measure q;int n=int(m);c=rotl(c,n);',{'0001':'1/2','1010':'1/2'}),
 ('typed-rotate-nested','bit[3] c="111";bit[3] r="001";r=rotl(r,int[8](int[3](c)));',{'100111':'1'}),
 ('computed-scalar-widen','bit c=1;int[8] a=int[8](c);c=a==1;',{'1':'1'}),
 ('computed-scalar-zero','bit c=0;uint a=uint(c);c=a==0;',{'1':'1'}),
 ('computed-index-widen','bit[3] c="010";bit r;r=int[8](c[1])==1;',{'1010':'1'}),
 ('computed-index-constant','const int k=1;bit[3] c="010";bit r;r=uint[8](c[k])==1;',{'1010':'1'}),
 ('computed-scalar-history','qubit q;bit c;h q;c=measure q;int[8] a=int[8](c);c=0;c=a==1;',{'0':'1/2','1':'1/2'}),
 ('computed-index-history','qubit q;bit[2] c;h q;c[1]=measure q;int[8] a=int[8](c[1]);c=0;c[0]=a==1;',{'00':'1/2','01':'1/2'}),
 ('typed-one-register','bit[1] c="1";bit r;r=int[1](c)==-1;',{'11':'1'}),
 ('typed-one-slice','bit[3] c="010";bit r;r=int[1](c[1:1])==-1;',{'1010':'1'}),
 ('computed-xor','bit[3] c;bit r;r=uint[3](c ^ "111")==7;',{'1000':'1'}),
 ('computed-negative','bit[3] c;bit r;r=int[3](~c)==-1;',{'1000':'1'}),
 ('computed-store','bit[3] c;int[8] a=uint[3](c ^ "111");bit r;r=a==7;',{'1000':'1'}),
 ('computed-predicate','bit c;int[8] a=int[8](c==0);c=a==1;',{'1':'1'}),
 ('computed-guard','int a;bit c;int[8] b=int[8](true || a==0);c=b==1;',{'1':'1'}),
 ('computed-undefined','int a;bit c;int[8] b=int[8](a==0);c=b==0;',None),
 ('computed-not','bit c;int[8] a=int[8](!c);c=a==1;',{'1':'1'}),
 ('computed-bool','int a=-2;int[8] b=int[8](bool(a));bit c;c=b==1;',{'1':'1'}),
 ('computed-popcount','bit[3] c="101";uint n=uint(popcount(c));bit r;r=n==2;',{'1101':'1'}),
 ('computed-measurement','qubit q;bit c;h q;c=measure q;int[8] a=int[8](c==1);c=0;c=a==1;',{'0':'1/2','1':'1/2'}),
 ('variable-boolean-literal','int[8] a=int[8](true);bit c;c=a==1;',{'1':'1'}),
 ('scope-unicode','int '+unicode_name+'=1;bit c;{int '+unicode_name+'=2;c='+unicode_name+'==2;}c=c && '+unicode_name+'==1;',{'1':'1'}),
 ('scope-shadow','int a=1; bit c; if(a==1){int a=2; c=a==2;} c=c && a==1;',{'1':'1'}),
 ('scope-siblings','bit c=1; if(c){int a=2;c=a==2;}else{int a=3;c=a==2;}',{'1':'1'}),
 ('scope-else','bit c; if(c){int a=2;c=a==3;}else{int a=3;c=a==3;}',{'1':'1'}),
 ('scope-nested','int a=1; bit c; if(a==1){int a=2;if(a==2){int a=3;c=a==3;}c=c && a==2;}c=c && a==1;',{'1':'1'}),
 ('scope-loop','int sum=0; bit c; for int i in [0:2]{int t=i;sum+=t;}c=sum==3;',{'1':'1'}),
 ('scope-fresh','bit c; for int i in [0:1]{int t;if(i==0){t=7;}else{c=t==7;}}',None),
 ('scope-loop-shadow','int i=7;bit c;for int i in [0:2]{c=i==2;}c=c && i==7;',{'1':'1'}),
 ('scope-block','int a=1;bit c;{int a=2;c=a==2;}c=c && a==1;',{'1':'1'}),
 ('scope-collision','int a_scope_1=9;bit c;{int a=2;c=a==2;}c=c && a_scope_1==9;',{'1':'1'}),
 ('scope-constant-width','bit c=1;if(c){const uint n=8;int[n] t=7;c=t==7;}',{'1':'1'}),
 ('scope-self-initializer','int a=1;bit c;{int a=a+1;c=a==2;}',None),
 ('scope-measurement','qubit q;bit c;h q;c=measure q;if(c){int a=8;c=a==8;}else{int a=3;c=a==8;}',{'0':'1/2','1':'1/2'}),
 ('variable-arithmetic','int[8] counter=3; bit c; counter=counter**2-1; c=counter==8;',{'1':'1'}),
 ('variable-compound','int counter=3; bit c; counter+=2; counter*=3; counter-=1; counter/=2; counter%=4; c=counter==3;',{'1':'1'}),
 ('variable-undefined','int[8] counter; bit c; c=counter==0;',None),
 ('variable-guard','int counter; bit c; if(false && counter==0){c=1;}',{'0':'1'}),
 ('variable-initialize-later','int counter; bit c; counter=8; if(counter==8){c=1;}',{'1':'1'}),
 ('variable-cast','uint[8] a=255; int[8] b=int[8](a); bit c; c=b<0;',{'1':'1'}),
 ('variable-bitcast','uint[3] a=5; bit[3] c; c=bit[3](a);',{'101':'1'}),
 ('variable-bool','int a=-1; bit c; c=bool(a);',{'1':'1'}),
 ('variable-narrow','uint[3] a=8; bit c; c=a==0;',{'1':'1'}),
 ('variable-branch','int a=1; bit c; if(a==1){a=2; c=1;}else{a=3;} c=a==2;',{'1':'1'}),
 ('variable-loop','int counter=0; bit c; for int i in [0:2]{counter+=i;} c=counter==3;',{'1':'1'}),
 ('variable-const-width','const uint WIDTH=8; int[WIDTH] a=7; bit c; c=a==7;',{'1':'1'}),
 ('variable-measurement','qubit q; bit c; bit r; int[8] a; h q; c=measure q; a=int[1](c); r=a<0;',{'00':'1/2','11':'1/2'}),
 ('variable-history','qubit q; bit c; int a; h q; c=measure q; if(c){a=8;}else{a=3;} c=0; reset q; c=a==8;',{'0':'1/2','1':'1/2'}),
 ('variable-zero','int a=0; bit c; c=1/a==0;',None),
 ('typed-power','bit[3] c=2; bit r; if(int[3](c)**3==8){r=1;}',{'1010':'1'}),
 ('typed-power-right','bit[3] c=2; bit r; if(int[3](c)**3**2==512){r=1;}',{'1010':'1'}),
 ('typed-power-left','bit[3] c=2; bit r; if((int[3](c)**3)**2==64){r=1;}',{'1010':'1'}),
 ('typed-power-unary','bit[3] c=2; bit r; if(-int[3](c)**2 == -4){r=1;}',{'1010':'1'}),
 ('typed-power-negative-base','bit[3] c=2; bit r; if((-int[3](c))**2 == 4){r=1;}',{'1010':'1'}),
 ('typed-power-runtime-exponent','bit[3] c=3; bit r; if(2**int[3](c)==8){r=1;}',{'1011':'1'}),
 ('typed-power-negative-exponent','bit[3] c=7; bit r; if(2**int[3](c)==0){r=1;}',None),
 ('typed-power-overflow','bit[8] c=63; bit r; if(2**int[8](c)==0){r=1;}',None),
 ('typed-power-guard','bit[3] c=7; bit r; if(false && 2**int[3](c)==0){r=1;}',{'0111':'1'}),
 ('typed-power-wrap','bit[64] c=2; c=bit[64](uint[64](uint[64](c)**64));',{'0'*64:'1'}),
 ('typed-power-measure','qubit q; bit c; bit r; h q; c=measure q; if(2**uint[1](c)==2){r=1;}',{'00':'1/2','11':'1/2'}),
 ('classical-only-initializer','bit c=1;',{'1':'1'}),
 ('classical-only-overlap','bit[3] c="001"; c[1:2]=c[0:1];',{'011':'1'}),
 ('classical-only-functions','bit[3] c="101"; if(popcount(c)==2){c=rotl(c,1);}',{'011':'1'}),
 ('static-cast','qubit q; bit[3] c; c=int[3](1);',{'001':'1'}),
 ('literal-signed-cast','qubit q; bit[3] c; c=rotl("001",int[3]("111"));',{'100':'1'}),
 ('rotate-left','qubit q; bit[3] c="001"; c=rotl(c,1);',{'010':'1'}),
 ('rotate-negative','qubit q; bit[3] c="001"; c=rotr(c,-1);',{'010':'1'}),
 ('rotate-cast','qubit q; bit[3] c="111"; c=rotl("001",int[3](c));',{'100':'1'}),
 ('rotate-unsigned','qubit q; bit[3] c="111"; c=rotl("001",uint[3](c));',{'010':'1'}),
 ('popcount-branch','qubit q; bit[3] c="101"; if(popcount(c)==2){c="111";}',{'111':'1'}),
 ('popcount-literal','qubit q; bit c; if(popcount("111")==3){c=1;}',{'1':'1'}),
 ('rotate-count','qubit q; bit[3] c="101"; c=rotl(c,popcount(c));',{'110':'1'}),
 ('copy','qubit q; bit a; bit b; x q; a=measure q; b=a; a=0;',{'10':'1'}),
 ('overlap','qubit q; bit[3] c="001"; c[1:2]=c[0:1];',{'011':'1'}),
 ('initializer','qubit q; bit c=1; if(c) x q; c=measure q;',{'1':'1'}),
 ('loop','qubit q; bit[3] c; for int i in [0:2] {c[i]=1;}',{'111':'1'}),
 ('compound','qubit q; bit[4] c="1010"; c^="0011"; c<<=1;',{'0010':'1'}),
 ('reverse','qubit q; bit[3] c="001"; c[0:2]=c[2:-1:0];',{'100':'1'}),
 ('bit63','qubit q; bit[64] c; c[63]=1;',{'1'+'0'*63:'1'}),
 ('parity','qubit[3] q; bit[3] c; h q[0]; h q[1]; c[0]=measure q[0]; c[1]=measure q[1]; if(c[0]^c[1]) x q[2]; c[2]=measure q[2];',dict.fromkeys(['000','011','101','110'],'1/4')),
 ('branch-once','qubit q; bit c=1; if(c){c=0; x q;} c=measure q;',{'1':'1'}),
 ('comparison','qubit q; bit[2] c="10"; bit d; if(c>1 && c!=3) {d=1;}',{'110':'1'}),
 ('logical-assignment','bit a=1; bit b=0; bit r; r=a || b;',{'101':'1'}),
 ('logical-nested','bit a=1; bit b=0; if(a){if(a || b){b=1;}} a=0;',{'10':'1'}),
 ('logical-and-or','bit a=1; bit b=0; bit r; if((a==1 || b==1) && b==0){r=1;}',{'101':'1'}),
 ('typed-negative','bit[8] c="11111111"; bit r; if(int[8](c)<0){r=1;}',{'111111111':'1'}),
 ('typed-unsigned','bit[8] c="11111111"; bit r; if(uint[8](c)>0){r=1;}',{'111111111':'1'}),
 ('typed-narrowing','bit[8] c; bit r; if(int[8](c)<int[8](255)){r=1;}',{'000000000':'1'}),
 ('typed-minus','bit[8] c="00000010"; bit r; if(-int[8](c)<0){r=1;}',{'100000010':'1'}),
 ('typed-guard-zero','bit[8] c; bit r; if(int[8](c)!=0 && 6/int[8](c)==3){r=1;}',{'000000000':'1'}),
 ('typed-guard-two','bit[8] c="00000010"; bit r; if(int[8](c)!=0 && 6/int[8](c)==3){r=1;}',{'100000010':'1'}),
 ('typed-measurement','qubit q; bit c; bit r; h q; c=measure q; if(int[1](c)<0){r=1;}',{'00':'1/2','11':'1/2'}),
 ('typed-zero','bit[8] c; bit r; if(6/int[8](c)==3){r=1;}',None),
 ('typed-overflow','bit[64] c=1; if(int(c)+9223372036854775807>0){c[0]=0;}',None),
 ('typed-machine','bit[64] c; if(int(c)==0){c[0]=1;} ',{'0'*63+'1':'1'}),
 ('typed-bitcast','bit[3] c="011"; c=bit[3](int[3](int[3](c)+1));',{'100':'1'}),
 ('typed-bitcast-negative','bit[3] c="111"; c=bit[3](uint[3](int[3](c)));',{'111':'1'}),
 ('typed-bitcast-compare','bit[3] c="011"; bit r; if(bit[3](int[3](c))==3){r=1;}',{'1011':'1'}),
 ('typed-bitcast-measure','qubit q; bit c; h q; c=measure q; c=bit[1](int[1](c));',{'0':'1/2','1':'1/2'}),
 ('typed-bitcast-skipped','bit[3] c; if(c==1){c=bit[3](int[3](1/int[3](c)));}',{'000':'1'}),
 ('typed-bitcast-divzero','bit[3] c; c=bit[3](int[3](1/int[3](c)));',None),
 ('typed-bitcast-wide','bit[64] c=1; c=bit[64](uint[64](c));',{'0'*63+'1':'1'}),
 ('boolean-zero','bit[3] c; bit r; r=bool(c);',{'0000':'1'}),
 ('boolean-literal-zero','bit r; r=bool("00");',{'0':'1'}),
 ('boolean-literal-nonzero','bit r; r=bool("10");',{'1':'1'}),
 ('boolean-literal-branch','bit r; if(bool("10")){r=1;}',{'1':'1'}),
 ('boolean-nonzero','bit[3] c="100"; bit r; if(bool(c)){r=1;}',{'1100':'1'}),
 ('boolean-nested','bit[3] c="100"; bit r; r=bool(bool(c));',{'1100':'1'}),
 ('boolean-popcount','bit[3] c="100"; bit r; r=bool(popcount(c));',{'1100':'1'}),
 ('typed-boolean-negative','bit[3] c="100"; bit r; r=bool(int[3](c));',{'1100':'1'}),
 ('typed-boolean-arithmetic','bit[3] c="100"; bit r; r=bool(int[3](c)-int[3](c));',{'0100':'1'}),
 ('typed-boolean-guard','bit[3] c; bit r; if(bool(c) && 6/int[3](c)==3){r=1;}',{'0000':'1'}),
 ('boolean-measure','qubit q; bit c; bit r; h q; c=measure q; r=bool(c);',{'00':'1/2','11':'1/2'}),
 ('registers','qubit q; bit[2] c="10"; bit[2] d="10"; if(c==d){c=0;}',{'1000':'1'}),
]
checks=0
loop_fixture=(root/'windows/fixtures/runtime-subroutines/qbraid-loop-index.qasm').read_bytes()
loop_circuit=adapter.convert(loop_fixture.decode(),classical=True)
assert adapter.convert(loop_fixture.decode())=={'Version':1,'Qubits':4,'Steps':[{'Gate':gate,'Angle':'','Wires':[wire]} for gate,wire in [('H',0),('H',1),('H',2),('H',3),('X',3),('H',0)]]}
checks+=2
if not a.source_only:
 result=subprocess.run([str(root/'dist/QuantumStudio/qasm-import/qasm-import.exe'),'--classical'],input=loop_fixture,capture_output=True,timeout=30)
 assert result.returncode==0 and json.loads(result.stdout)==loop_circuit,result.stderr
 checks+=1
# Authored measurement/assertion extension; upstream source bytes stay separate.
cases.append(('computed-qloop-upstream-driver',loop_fixture.decode().split('include "stdgates.inc";',1)[1]+'output bit[4] measured;output bit ok;measured=measure q;ok=new_var==4;',{'1'+format(i,'03b')+'0':'1/8' for i in range(8)}))
# Unchanged pinned PyQASM source: the upstream oracle is four H gates.
source_fixture=(root/'windows/fixtures/runtime-subroutines/qbraid-register-return.qasm').read_bytes()
def gates_in(value):
 if isinstance(value,dict):
  if value.get('Kind')=='Gate':yield value
  for child in value.values():yield from gates_in(child)
 elif isinstance(value,list):
  for child in value:yield from gates_in(child)
upstream_circuit=adapter.convert(source_fixture.decode(),classical=True)
assert [(g['Expression'],g['Wires']) for g in gates_in(upstream_circuit)]==[('H',[i]) for i in range(4)]
checks+=1
if not a.source_only:
 result=subprocess.run([str(root/'dist/QuantumStudio/qasm-import/qasm-import.exe'),'--classical'],input=source_fixture,capture_output=True,timeout=30)
 assert result.returncode==0 and json.loads(result.stdout)==upstream_circuit,result.stderr
 checks+=1
hooks=tuple(getattr(adapter.QasmVisitor,name) for name in ['_visit_classical_assignment','_visit_classical_declaration','_visit_branching_statement','_visit_function_call'])
# Compiler-only boundary cases avoid allocating a 25-qubit simulation state.
width_boundary='0'
for _ in range(8): width_boundary='('+width_boundary+'+'+width_boundary+')'
width_boundary=width_boundary.replace('0','2',1)  # 511 nodes, exactly two.
for width in ('25', 'uint[64](25)', 'int('+width_boundary+')', '-('*30+'2'+')'*30):
 source=header+'def f(qubit['+width+'] a)->bool{return true;}qubit['+('25' if '25' in width else '2')+'] q;bool ok=f(q);'
 circuit=adapter.convert(source,classical=True)
 assert circuit['Qubits']==(25 if '25' in width else 2),circuit
 checks+=1
 if not a.source_only:
  result=subprocess.run([str(root/'dist/QuantumStudio/qasm-import/qasm-import.exe'),'--classical'],input=source.encode(),capture_output=True,timeout=30)
  assert result.returncode==0 and json.loads(result.stdout)==circuit,result.stderr;checks+=1

# An evaluator tripwire proves costly syntax is rejected before arithmetic.
from unittest.mock import patch
from qasm_source_diagnostics import LocatedError
for width in ('2**(2**32)', '1<<1000000000', 'int[1000000000](2)', 'int[1<<30](2)', '0*(1<<1000000000)+2'):
 program=adapter.pyqasm.loads(header+'def f(qubit['+width+'] a)->bool{return true;}qubit[2] q;bool ok=f(q);').original_program
 with patch.object(adapter.Qasm3ExprEvaluator,'evaluate_expression',side_effect=AssertionError('Width preflight reached arithmetic')):
  try:adapter.lower_runtime_subroutines(program)
  except LocatedError:checks+=1
  else:raise AssertionError('Expensive width was accepted')
for body in ('qubit q;output bit r;', 'qubit q;input bit r;'):
 try:adapter.convert(header+body)
 except ValueError as error:assert 'require classical circuit import' in str(error);checks+=1
 else:raise AssertionError('Numerical import discarded explicit IO: '+body)
 if not a.source_only:
  result=subprocess.run([str(root/'dist/QuantumStudio/qasm-import/qasm-import.exe')],input=(header+body).encode(),capture_output=True,timeout=30)
  assert result.returncode!=0 and b'require classical circuit import' in result.stderr and not result.stdout;checks+=1
rejected=['bit[8] c=8; bit r; if(int[c](c)<0){r=1;}','bit[8] c; bit r; if(int[7](c)<0){r=1;}', 'bit[8] c; bit r; if(int[8](c)+c>0){r=1;}', 'bit[8] c; bit r; if(int[0](c)<0){r=1;}', 'bit[8] c; bit r; if(int[8](c)<-9223372036854775809){r=1;}', 'qubit q; bit[3] c; c=rotl(c);',
          'qubit q; bit[3] c; c=rotr(c,1,2);',
          'qubit q; bit[3] c; c=rotl(c,-9223372036854775809);',
          'qubit q; bit[3] c; c=rotl(c,int[4](c));',
          'qubit q; bit[3] c; c=rotl(c,c);',
          'qubit q; bit c; if(popcount(c,c)==1){c=1;}', 'qubit q; bit c=2;', 'qubit q; bit[2] c; c="1";',
          'qubit q; bit[2] c; c[0]=c[2];', 'qubit q; bit[3] c; c[0:2]=c[0:1];',
          'qubit q; bit c; c=measure q; rx(float(c)) q;',
          'qubit[2] q; bit c=1; x q[c];',
          'qubit[2] q; bit c=1; c=measure q[c];',
          'qubit q; bit[2] c; bit d=1; c[d]=measure q;',
          'qubit q; bit[2] c; let d=c; d=1;',
          'qubit q; bit c; c+=1;', 'qubit q; bit[2] c; if(c>4) x q;']
rejected += ['def f(bit v){const int n=int(v)+1;bit[n] local;}bit m=1;f(m);', 'def f(bit[2] v){v[2]=0;}bit[2] m;f(m);', 'def f(bit[64] v){}bit[64] m;f(m);', 'def f(bit v){bit[0] local;}bit m;f(m);', 'def f(bit v,qubit q){x q[0];}qubit q;bit m;f(m,q);']
rejected += ['bit[3] c; c=bit[3](int[3](c)+1);','bit[3] c; c=bit[3](int(c));','bit[3] c; c=bit[2](int[3](c));','bit[3] c; c=bit[c](int[3](c));','bit[3] c; c=bit[0](int[3](c));','bit[64] c; c=bit[64](int(c));']
rejected += ['qubit q;bit c=measure q;bit[2] d;d=bit[2](c=="1");',
             'qubit q;bit c=measure q;bit[2] d;d=bit[2](!(c=="1"));']
rejected += ['int[0] a;','uint[65] a;','int a=3; int[a] b;','int a=1; while(a){a=0;}',
             'int a=1; qubit[2] q; x q[a];',
             'int a=1; def f() -> int {return a;}','int a=1; int a=2;',
             'int a=1; bit[2] c; c[a]=1;','float[16] a=1.0;','int a=b; int b=1;', 'int '+('a'*65)+';']
rejected += ['bit c;{int a=1;}c=a==1;', 'bit c;{int a=1;int a=2;}', 'bit c;{int '+('a'*65)+';}']
rejected += ['int '+('𝑎'*33)+';', 'int a=1;bit c;{const int a=2;c=a==2;}']
rejected += ['bit[3] c;int a=uint[2](~c);','bit[3] c;int a=int[3](popcount(c));',
             'bit[3] c;int a=uint[3](c ^ "11");','bit[3] c;bit r;r=false && uint[2](~c)==0;']
rejected += ['bit[1] c;int a=int[8](c);','bit[3] c;int a=int[8](c[1:1]);',
             'bit[3] c;int a=int[8](c[{1}]);','bit[3] c;int a=int[8](c[3]);']
rejected += ['bit[3] c; c=rotl(c,c);','bit[3] c;c=rotr(c,bool(c));',
             'bit[3] c;c=rotl(c,int[2](c ^ "111"));']
rejected += ['bit[1] c;bool b=c;','bit[3] c;bool b=c ^ "111";',
             'bit[3] c;bool b=c[0:0];','bool b="1";','bool b=false;b+=1;',
             'bit c;{bool b=true;}c=b;','bool b=true;bool b=false;']
rejected += ['int n=1;def f(){if(true){int n=2;}int x=n;}',
             'int n=1;def f(){int x=n;int n=2;}',
             'int n=1;def f(){for int n in [0:1]{}int x=n;}',
             'def f(qubit a){\n@custom\nx a;}qubit q;f(q);',
             'def f(){f();}f();']
rejected += ['def f0(){}'+''.join('def f'+str(i)+'(){f'+str(i-1)+'();f'+str(i-1)+'();}' for i in range(1,13))+'f12();']
rejected += ['bit[1] c;bool b=c ^ "1";','bit[1] c;bool b=~c;',
             'bit[1] c;bool b=rotl(c,1);','bit[1] c;bool b=c << 1;']
rejected += ['qubit q;bit[64] c;bool b=measure q;','qubit[2] q;bool b=measure q;',
             'qubit q;bool b;b[0]=measure q;','qubit q;bool b;\n@unsupported\nb=measure q;']
boolean_broad='c'
for _ in range(8):boolean_broad='('+boolean_broad+' | '+boolean_broad+')'
rejected.append('bit c; bit r; r=bool('+boolean_broad+');') # Comparison plus zero exceeds 512 nodes.
rejected.append('bit c;int a=int(bool('+boolean_broad+'));') # Mixed Boolean/integer tree shares one budget.
integer_broad='n'
for _ in range(8):integer_broad='('+integer_broad+' + '+integer_broad+')'
rejected.append('int n=1;bit[3] c;c=rotl(c,'+integer_broad+');') # Rotation wrappers share the expression budget.
rejected += ['int n=1;switch(n){case 1,1{}}','int n=1;switch(n){case 1{}case 1{}}',
             'int n=1;int m=1;switch(n){case m{}}','int n=1;switch(n){case true{}}',
             'bool n=true;switch(n){case 1{}}','bit n;switch(n){case 0{}}',
             'int n=1;switch(n==1){case 1{}}','int n=1;switch(n){case 1{}default{qubit q;}}',
             'int n=1;bit c;switch(n){case 1{int a=2;}}c=a==2;',
             'int n=1;switch(n){case 1{}case 2{int a=2;int a=3;}}']
rejected += ['int n=1;switch(n){case 1{}case 2{bit c;c=missing;}}',
             'int n=1;\n@unsupported\nswitch(n){case 1{}}']
rejected += ['bit c;switch(true){case 1{c=1;}}','bit c;switch(1==1){case 1{c=1;}}',
             'bit c;switch(1.5){case 1{c=1;}}','bit c;switch(0){case 1{}case 1{}}',
             'int n=1;bit c;switch(1){case n{c=1;}}']
rejected += ['bit c;break;','bit c;continue;',
             'bit c;while(c){int a=1;}c=a==1;', 'bit c;while(c){qubit q;}',
             'bit c;while(c){bit b;}', 'bit c;while(c){int a=1;int a=2;}']
rejected += ['bit c;while(false){gate custom q {x q;}}',
             'bit c;while(false){def f(){}}',
             'bit c;'+('while(false){'*33)+('}'*33),
             'bit c;while(false){c=missing;}']
rejected += ['int n=2;bit c;for int i in [true:n]{c=1;}',
             'bool b=true;int n=2;bit c;for int i in [b:n]{c=1;}',
             'int n=2;bit c;for int i in [0:n>1]{c=1;}',
             'int n=2;bit c;for int i in [0:n]{}c=i==0;',
             'int n=2;qubit[3] q;for int i in [0:n]{x q[i];}']
rejected += ['qubit q;bit[8] c;c[0]=measure q;c=c<<int[8](c);',
             'qubit q;bit[8] c;c[0]=measure q;int[8] n=int[8](c);c=c>>n;',
             'qubit q;bit[8] c;c[0]=measure q;c=c<<uint[7](c);']
rejected += ['output bit r;output bit r;',
             'bit r;output bit r;',
             'output int[8] r;',
             'input bit r;',
             'bit c;if(c){output bit r;}',
             'output bit[65] r;',
             'output bit[0] r;']
rejected += ['@unsupported\noutput bit r;']
rejected += ['def f(int n,qubit a,qubit b){} qubit q;bit c;f(int(c),q,q);', 'def f(int n,qubit q){return 1;}qubit q;bit c;f(int(c),q);', 'def f(int n,qubit q){}qubit q;bit c;f(int(c));', 'def f(int n,qubit q){f(n,q);}qubit q;bit c;f(int(c),q);', 'def f(int n,qubit q){array[int[8],2] b;}qubit q;bit c;f(int(c),q);']
rejected += ['def f(int n,qubit q){g(n,q);}def g(int n,qubit q){}qubit q;bit c;f(int(c),q);', 'def f(int n,qubit q){}qubit q;bit c;\n@custom\nf(int(c),q);']
rejected += ['def f(int n,qubit q){if(missing==1){x q;}}qubit q;bit m;{int missing=1;f(int(m),q);}', 'def f(int n,qubit q){if(later==1){x q;}}const int later=1;qubit q;bit m;f(int(m),q);']
rejected += ['def f(int n){return;return 1;}int n=0;f(n);',
             'def f(int n){return;if(n==0){return 1;}}int n=0;f(n);']
# Expansion and lexical-binding budgets must reject before allocating unbounded ASTs.
rejected += ['def f(int n){}int n=1;'+('f(n);'*4097)]
rejected += ['const int a0=1;'+''.join('const int a'+str(i)+'=a'+str(i-1)+'+a'+str(i-1)+';' for i in range(1,21))+'def f(int n){if(a20>0){n=0;}}int n=1;f(n);']
rejected += ['output bit r;r=1 ++ 0;', 'output bit[64] r;r="'+('0'*33)+'" ++ "'+('0'*32)+'";']
rejected += [
 'def f(qubit[2] a)->bool{return true;}qubit[2] q;output bit r;if(true){int q=1;bool ok=f(q);r=ok;}',
 'def f(qubit[2] a)->bool{return true;}qubit[2] q;for int q in [0:1]{bool ok=f(q);}',
 'def f(qubit a)->bool{return true;}qubit q;if(true){int q=1;bool ok=f(q);}',
 'def f(qubit[3] a)->bool{return true;}qubit[2] q;bool ok=f(q);',
 'def f(qubit[2] a,qubit[2] b)->bool{return true;}qubit[2] q;bool ok=f(q,q);',
 'def f(qubit[2] a,qubit b)->bool{return true;}qubit[2] q;bool ok=f(q,q[1]);',
 'def f(qubit b,qubit[2] a)->bool{return true;}qubit[2] q;bool ok=f(q[1],q);',
 'def f(qubit[2] a)->bool{x a[2];return true;}qubit[2] q;bool ok=f(q);',
 'def f(qubit[2] a,int i)->bool{x a[i];return true;}qubit[2] q;int i=1;bool ok=f(q,i);',
 'def f(qubit a)->bool{x a[0];return true;}qubit q;bool ok=f(q);',
 'def f(qubit[2] a)->bool{return true;}qubit[3] q;bool ok=f(q[0:1]);',
 'def f(qubit[2] a)->bool{return true;}qubit[2] q;let b=q;bool ok=f(b);',
 'def f(qubit[1] a)->bool{return true;}qubit q;bool ok=f(q);',
 'def f(qubit[1] a,qubit[2] b)->bool{cx a,b;return true;}qubit[1] a;qubit[2] b;bool ok=f(a,b);',
 # Mixed scalar/register gate broadcasting is a separate unroller limitation.
 'def f(qubit control,qubit[2] targets)->bool{cx control,targets;return true;}qubit c;qubit[2] q;bool ok=f(c,q);',
]
# Width rejection happens before the pinned evaluator sees expensive operators.
width_bad = ['0', '-1', '26', '1.5', 'true', 'int(true)', 'int(2.5)', '1==1',
             '2/1', '2%1', '2**(2**32)', '1<<1000000000', 'int[1000000000](2)',
             'int[0](2)', 'int[65](2)', 'int[2](2)', 'uint[2](-1)', str(1<<64)]
for width in width_bad:
 rejected.append('def f(qubit['+width+'] a)->bool{return true;}qubit[2] q;bool ok=f(q);')
 rejected.append('def f(qubit[2] a)->bool{return true;}qubit['+width+'] q;bool ok=f(q);')
rejected += [
 'int N=2;def f(qubit[N] a)->bool{return true;}qubit[2] q;bool ok=f(q);',
 'def f(qubit[N] a)->bool{return true;}const int N=2;qubit[2] q;bool ok=f(q);',
 'qubit[N] q;const int N=2;def f(qubit[2] a)->bool{return true;}bool ok=f(q);',
 'const int N=2;def f(int N,qubit[N] a)->bool{return true;}qubit[2] q;bool ok=f(2,q);',
 'def f(int N,qubit[N] a)->bool{return true;}qubit[2] q;bool ok=f(2,q);',
 'const int N=2;def f(qubit[N] a)->bool{return true;}qubit[3] q;bool ok=f(q);',
 'const int N=1;def f(qubit[N] a)->bool{return true;}qubit q;bool ok=f(q);',
 'const int N=2;def f(qubit[N] a,qubit[N] b)->bool{return true;}qubit[N] q;bool ok=f(q,q);',
 'const int N=later;const int later=2;def f(qubit[N] a)->bool{return true;}qubit[2] q;bool ok=f(q);',
 'int value=2;const int N=value;def f(qubit[N] a)->bool{return true;}qubit[2] q;bool ok=f(q);',
 'def value()->int{return 2;}const int N=value();def f(qubit[N] a)->bool{return true;}qubit[2] q;bool ok=f(q);',
 'const bool N=true;def f(qubit[N] a)->bool{return true;}qubit[1] q;bool ok=f(q);',
 'const int[2] N=2;def f(qubit[N] a)->bool{return true;}qubit[2] q;bool ok=f(q);',
]
width_broad='1'
for _ in range(9): width_broad='('+width_broad+'+'+width_broad+')'
rejected.append('def f(qubit['+width_broad+'] a)->bool{return true;}qubit[2] q;bool ok=f(q);')
rejected.append('def f(qubit['+('-('*33)+'2'+(')'*33)+'] a)->bool{return true;}qubit[2] q;bool ok=f(q);')
rejected.append('const int a0=1;'+''.join('const int a'+str(i)+'=a'+str(i-1)+'+a'+str(i-1)+';' for i in range(1,21))+'def f(qubit[a20] a)->bool{return true;}qubit[2] q;bool ok=f(q);')
rejected.append('const int a0=2;'+''.join('const int a'+str(i)+'=a'+str(i-1)+';' for i in range(1,34))+'def f(qubit[a33] a)->bool{return true;}qubit[2] q;bool ok=f(q);')
loop_prefix='def f(qubit a)->bool{x a;return true;}qubit[2] q;'
rejected += [loop_prefix+body for body in [
 'for int i in [0:1]{i=1;bool ok=f(q[i]);}',
 'for int i in [0:1]{{int i=0;bool ok=f(q[i]);}}',
 'for int i in [0:1]{bool ok=f(q[i]);break;}',
 'for int i in [0:1]{bool ok=f(q[i]);continue;}',
 'int n=1;for int i in [0:n]{bool ok=f(q[i]);}',
 'for int i in [0:0:1]{bool ok=f(q[i]);}',
 'for int i in [0:2]{bool ok=f(q[i]);}',
 'for int i in [0:1]{bool ok=f(q[i+0]);}',
 'for uint[1] i in [0:2]{bool ok=f(q[i]);}',
 'for int i in [0:4096]{bool ok=f(q[i]);}',
 'for int i in [0:18446744073709551616]{bool ok=f(q[i]);}',
 'for int i in [0:1]{for int i in [0:1]{bool ok=f(q[i]);}}',
]]
rejected.append('def f(qubit a,qubit b)->bool{return true;}qubit[2] q;for int i in [0:1]{bool ok=f(q[i],q[i]);}')
for body in rejected:
 try:adapter.convert(header+body,classical=True)
 except Exception:checks+=1
 else:raise AssertionError('Unsupported or invalid source was accepted: '+body)
 assert tuple(getattr(adapter.QasmVisitor,name) for name in ['_visit_classical_assignment','_visit_classical_declaration','_visit_branching_statement','_visit_function_call'])==hooks
 if not a.source_only:
  result=subprocess.run([str(root/'dist/QuantumStudio/qasm-import/qasm-import.exe'),'--classical'],input=(header+body).encode(),capture_output=True,timeout=30)
  assert result.returncode!=0 and result.stderr and not result.stdout,(body,result.stdout);checks+=1
def n(*v):return ''.join(str(x)+'\n' for x in v).encode()
ops=['And','Or','Xor','ShiftLeft','ShiftRight','Equal','NotEqual','Less','LessEqual','Greater','GreaterEqual']
def expression(e):
 k=e['Kind']
 if k=='Constant':return n(0,e['Width'],e['Value'])
 if k=='Read':return n(1,len(e['Bits']),*e['Bits'])
 if k=='IntegerBits':return n(8)+integer_expression(e['Left'])
 if k=='IntegerCompare':return n(6,ops.index(e['Operator'])-5)+integer_expression(e['Left'])+integer_expression(e['Right'])
 if k=='Logical':return n(7,0 if e['Operator']=='And' else 1)+expression(e['Left'])+expression(e['Right'])
 if k=='Complement':return n(2)+expression(e['Left'])
 if k=='PopulationCount':return n(4)+expression(e['Left'])
 if k=='Rotate':return n(5,0 if e['RotationDirection']=='Left' else 1,0 if e['DistanceInterpretation']=='Unsigned' else 1)+expression(e['Left'])+expression(e['Right'])
 return n(3,ops.index(e['Operator']))+expression(e['Left'])+expression(e['Right'])
def integer_expression(e):
 k=e['Kind']
 if k=='IntegerBinary':return n(3,['Add','Subtract','Multiply','Divide','Remainder','Power'].index(e['Operator']))+integer_expression(e['Left'])+integer_expression(e['Right'])
 t=n(0 if e['Signedness']=='Signed' else 1,e['Width'])
 if k=='IntegerFromBits':return n(5)+t+expression(e['Left'])
 if k=='IntegerConstant':return n(0)+t+n(e['Value'])
 if k=='IntegerRead':return n(1)+t+n(*e['Bits'])
 if k=='IntegerVariable':return n(4)+t+n(e['Slot'])
 assert k=='IntegerCast'
 return n(2)+t+integer_expression(e['Left'])

def steps(body):
 out=b''
 for s in body:
  kind=s['Kind']
  if kind=='Assign':out+=n(7,len(s['Wires']),*s['Wires'])+expression(s['ClassicalValue'])
  elif kind in ('Branch','ExpressionBranch'):
   out+=(n(6,s['Mask'],s['Value']) if kind=='Branch' else n(8)+expression(s['ClassicalValue']))
   for key in ['WhenTrue','WhenFalse']:out+=n(len(s[key]))+steps(s[key])
  elif kind=='End':out+=n(14)
  elif kind in ('Break','Continue'):out+=n(12 if kind=='Break' else 13)
  elif kind=='While':out+=n(11)+expression(s['ClassicalValue'])+n(len(s['WhenTrue']))+steps(s['WhenTrue'])
  elif kind=='ForRange':out+=n(15,s['VariableSlot'])+b''.join(integer_expression(s['Range'][key]) for key in ['Start','Stop','Step'])+n(len(s['WhenTrue']))+steps(s['WhenTrue'])
  elif kind=='ClearInteger':out+=n(10,s['VariableSlot'])
  elif kind=='StoreInteger':out+=n(9,s['VariableSlot'])+integer_expression(s['IntegerValue'])
  elif kind=='Reset':out+=n(2,s['Wires'][0])
  elif kind=='Measure':out+=n(1,s['Wires'][0],s['ClassicalBit'])
  else:
   assert kind=='Gate';matrix=s['Expression'].encode();out+=n(0,len(s['Wires']),*s['Wires'],len(matrix))+matrix
 return out
for name,body,expected in cases:
 source=header+body;circuit=adapter.convert(source,classical=True)
 if name=='transfer-shadow':
  sequence=circuit['Steps'][1]['WhenTrue'];index=next(i for i,s in enumerate(sequence) if s['Kind']=='Break')
  assert sequence[index-2:index]==[{'Kind':'ClearInteger','VariableSlot':2},{'Kind':'ClearInteger','VariableSlot':1}],sequence
  checks+=1
 assert circuit['Version']==(5 if name in ('subroutine-local-shadow','computed-qloop-local-actual') else 2 if name.startswith('subroutine-local-') or name in ('local-output-subroutine','qloop-empty') else 10 if name.startswith('range-runtime-') else 9 if name.startswith('end-') else 8 if name.startswith('transfer-') else 7 if name.startswith('loop-') else 6 if name.startswith('computed-') or name in ('variable-measurement','typed-measurement','typed-power-measure','typed-bitcast-measure') else 5 if name.startswith(('variable-','scope-')) else 4 if name.startswith('typed-') or name in ('comparison','logical-assignment','logical-nested','logical-and-or') else 3),(name,circuit)
 if name.startswith('computed-bmeasure-'):
  total=sum(r['Size'] for r in circuit['Registers'])
  assert circuit['Registers'][-1]['Size']==1 and circuit['OutputBits']==list(reversed(range(total-1))),(name,circuit)
  checks+=1
 if name=='scope-siblings':
  branch=next(step for step in circuit['Steps'] if step['Kind']=='Branch')
  assert branch['WhenTrue'][-1]['Kind']==branch['WhenFalse'][-1]['Kind']=='ClearInteger'
  assert branch['WhenTrue'][-1]['VariableSlot']!=branch['WhenFalse'][-1]['VariableSlot']
 if name.startswith('classical-only-'):assert circuit['Qubits']==0,(name,circuit)
 # The overlap case must retain a simultaneous read of both old source bits.
 if name=='overlap':assert circuit['Steps'][1]=={'Kind':'Assign','Wires':[1,2],'ClassicalValue':{'Kind':'Read','Bits':[0,1]}}
 checks+=1
 if not a.source_only:
  result=subprocess.run([str(root/'dist/QuantumStudio/qasm-import/qasm-import.exe'),'--classical'],input=source.encode(),capture_output=True,timeout=30)
  assert result.returncode==0 and json.loads(result.stdout)==circuit,(name,result.stderr);checks+=1
 if a.worker:
  worker=a.worker.resolve();bits=sum(r['Size'] for r in circuit['Registers']);output=circuit['OutputBits']
  for exact in (True,False):
   protocol=(b'QEXACT3\n' if exact else b'QSAMPLE4\n') if circuit['Version']==4 else (b'QEXACT2\n' if exact else b'QSAMPLE3\n')
   declarations=b''
   if circuit['Version']>=5:
    protocol=b'QEXACT4\n' if exact else b'QSAMPLE5\n'
    if circuit['Version']>=6:protocol=b'QEXACT5\n' if exact else b'QSAMPLE6\n'
    declarations=n(len(circuit['Variables']))+b''.join(n(0 if v['Signedness']=='Signed' else 1,v['Width']) for v in circuit['Variables'])
   if circuit['Version']>=7:
    protocol=(b'QEXACT8\n' if exact else b'QSAMPLE9\n') if circuit['Version']>=9 else (b'QEXACT7\n' if exact else b'QSAMPLE8\n') if circuit['Version']>=8 else (b'QEXACT6\n' if exact else b'QSAMPLE7\n')
    assert circuit['LoopConditionBudget']==1000000
    declarations+=n(32) # Bound intentionally nonterminating test programs.
   payload=protocol+n(circuit['Qubits'])+(b'' if exact else n(10000,1731))+n(bits)+declarations+n(len(output),*output,len(circuit['Steps']))+steps(circuit['Steps'])
   if circuit['Version']>=10:payload=(b'QEXACT9\n' if exact else b'QSAMPLE10\n')+payload[len(protocol):]
   run=subprocess.run([str(worker),'--exact-circuit' if exact else '--sample'],input=payload,capture_output=True,timeout=30,env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/'data')))
   if expected is None:
    assert run.returncode!=0 and run.stderr and not run.stdout,(name,run.stdout);checks+=1;continue
   assert run.returncode==0 and not run.stderr,(name,run.stderr);value=json.loads(run.stdout)
   if exact:assert {k:Fraction(v) for k,v in value['probabilities'].items()}=={k:Fraction(v) for k,v in expected.items()},(name,value)
   else:
    actual=value['counts'];assert set(actual)==set(expected) and sum(actual.values())==10000,(name,value)
    for k,v in expected.items():assert abs(actual[k]/10000-float(Fraction(v)))<.04,(name,value)
   checks+=1
print('PASS: '+str(checks)+' classical expression import checks.')
