// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumAlgebra.h"
#include "QuantumIndexed.h"
#include <iostream>
#include <stdexcept>
static unsigned checks=0;
static EvaluationOptions eo;
static void equal(const std::string &expression,const std::string &expected) {
 MathStructure value=CALCULATOR->calculate(expression,eo),reference=CALCULATOR->calculate(expected,eo);
 value.transform(COMPARISON_EQUALS,reference);value.eval(eo);
 if(!value.isNumber() || !value.number().isOne())throw std::runtime_error("Mismatch: "+expression+" vs "+expected);
 ++checks;
}
int main(){try {
 Calculator calculator;if(!calculator.loadGlobalDefinitions())throw std::runtime_error("Definitions unavailable");
#ifdef LOCAL_CHECKPOINT
 registerQuantumAlgebra(calculator);
 registerQuantumIndexed(calculator);
#endif
 eo.approximation=APPROXIMATION_EXACT;
 equal(R"(quantum: \sum_{k\in\{0,2,5\}}{k^2})","29");
 equal(R"(quantum: \sum_{k\in\{1,1,2\}} k+1)","4");
 equal(R"(quantum: \sum_{k\in\{\}}{k})","0");
 equal(R"(quantum: \sum_{k\in\{0,1\}} |k>_2<k|_2)","identity(2)");
 equal(R"(quantum: \sum_{a_0\in\{1,3\}}{\sum_{a_0\in\{a_0,a_0+1\}}{a_0}})","10");

 equal("quantum: \\tilde{x}-\\widetilde{x}","0");
 equal("quantum: \\sum_{\\tilde{k}=0}^{3} \\tilde{k}","6");
 equal("quantum: \\sum_{\\tilde{k}=0}^{2} (\\tilde{k}+k)","3+3*k");
 equal("quantum: |||0>||","1");
 equal("quantum: <0||0>","1");
 equal("quantum: ||X||_1","qtracenorm([0,1;1,0])");
 equal("quantum: ||(|0><0|-|+><+|)||_1","qtracenorm([1,0;0,0]-[1,1;1,1]/2)");
 equal("quantum: |||0><0|||_1","qtracenorm([1,0;0,0])");
 equal("quantum: |⟨101|(H⊗H⊗H)|000⟩|^2","1/8");
 equal("quantum: cirq.XPowGate(exponent=1/2)","[1+i,1-i;1-i,1+i]/2");
 equal("quantum: cirq.XPowGate(exponent=1,global_shift=1/2)","[0,i;i,0]");
 equal("quantum: cirq.ZPowGate(exponent=1/2)","[1,0;0,i]");
 equal("quantum: cirq.CZPowGate(exponent=1/2)","[1,0,0,0;0,1,0,0;0,0,1,0;0,0,0,i]");
 equal("quantum: controlled(cirq.XPowGate(exponent=1,global_shift=1/2))","[1,0,0,0;0,1,0,0;0,0,0,i;0,0,i,0]");

 equal("quantum: ⟨0|H|0⟩","1/sqrt(2)");
 equal("quantum: norm(|->)","1");
 equal("quantum: |+><+|","[1,1;1,1]/2");
 equal("quantum: <1|X|0>","1");
 equal("  quantum: <0|0>","1");
 equal("\xEF\xBB\xBFquantum: <1|0>","0");
 equal("quantum: \\frac{1}{2}","1/2");
 equal(R"(quantum: \sum_{a_0=0}^{3}{a_0})","6");
 equal(R"(quantum: \sum_{a_{10}=0}^{3}{a_{10}^2})","14");
 equal(R"(quantum: \sum_{a_0=0}^{1}{\sum_{a_1=0}^{1}{a_0+a_1}})","4");
 equal(R"(quantum: \frac{1}{2}\sum_{a_0=0}^{1}{\sum_{a_1=0}^{1}{exp(2*pi*i*a_0/4)basis(2*a_1+a_0,4)}})","[1;i;1;i]/2");
 equal(R"(quantum: \prod_{a_0=1}^{3}{a_0})","6");
 equal(R"(quantum: \sum_{a_0=0}^{2}{a_0+\sum_{a_0=0}^{1}{a_0}})","6");
 equal(R"(quantum: \sum_{a_0=0}^{2}{\sum_{a_1=0}^{a_0}{a_1}})","4");
 equal(R"(quantum: \sum_{a_0=0}^{1}{|a_0>_2})","[1;1]");
 equal(R"(quantum: \sum_{\alpha_0=0}^{3}{\alpha_0})","6");
 equal(R"(quantum: \sum_{qsumindex_0=0}^{1}{\sum_{a_0=0}^{1}{qsumindex_0+a_0}})","4");
 equal(R"(quantum: \sum_{a_0=0}^{2}{\sum_{a_0=0}^{a_0}{a_0}})","4");
 equal(R"(quantum: \sum_{a_0=0}^{1}{\sum_{a_01=0}^{1}{a_0+a_01}})","4");
 equal(R"(quantum: \sum_{a_0=0}^{2}{a_0+sum(a_0,0,1,a_0)})","6");
 equal(R"(quantum: norm((\bigotimes_{a_0=0}^{1}{Ry(a_0*pi)})|00>-|01>))","0");
 equal(R"(quantum: \sum_{a_0=0}^{2}{a_0+sum(a_0,0,1,(a_0))})","6");
 equal(R"(quantum: \sum_{qboundindex_0=0}^{1}{\sum_{a_0=0}^{1}{qboundindex_0+a_0}})","4");
 equal(R"(quantum: \sum_{a_0=0}^{1}{|sum(b_0,0,a_0,b_0)>_4})","[1;1;0;0]");
 equal(R"(quantum: \sum_{a_0=0}^{1}{a_0+<1|phase_function(a_0,1,a_0)|1>})","-1");
 equal(R"(quantum: \frac{1}{2}\begin{pmatrix}1&1&1&1\\[1mm]1&i&-1&-i\\[1mm]1&-1&1&-1\\[1mm]1&-i&-1&i\end{pmatrix})","qfourier(4)");
 equal(R"(quantum: \frac{1}{2}\sum_{a_0=0}^{1}{\sum_{a_1=0}^{1}{exp(2*pi*i*a_0/4)|a_1 a_0>}})","[1;i;1;i]/2");
 equal(R"(quantum: \sum_{a_0=0}^{1}{|1 a_0 0>})","[0;0;0;0;1;0;1;0]");
 equal(R"(quantum: \sum_{a_0=0}^{1}{<a_0 1|0 a_0>})","0");
 equal(R"(quantum: \sum_{a_0=0}^{1}{\sum_{a_1=0}^{1}{\ket{a_1 a_0}}})","[1;1;1;1]");
 equal(R"(quantum: \sum_{a_0=0}^{0}{|a_0 0 0 0 0 0 0 0 0 0>})","qbasis(0,1024)");
 equal(R"(quantum: \sum_{k=0}^{2} k+1)","4");
 equal(R"(quantum: \sum_{k=0}^{2} (k+1))","6");
 equal(R"(quantum: 2\sum_{k=0}^{2} k^2+1)","11");
 equal(R"(quantum: \prod_{k=1}^{3} k)","6");
 equal(R"(quantum: \sum_{a_0=0}^{1} \sum_{a_1=0}^{1} \vert a_1 a_0\rangle)","[1;1;1;1]");
 equal(R"(quantum: \frac{1}{2}\sum_{a_0=0}^{1}\sum_{a_1=0}^{1} e^{2*pi*i*a_0/4}\vert a_1 a_0\rangle)","[1;i;1;i]/2");
 equal(R"(quantum: \sum_{a_0=0}^{2} (a_0+\sum_{a_0=0}^{1} a_0))","6");
 equal(R"(quantum: norm((\bigotimes_{k=0}^{1} H)|00>))","1");
 equal(R"(quantum: \sum_{k=0}^{1} |+>)","sqrt(2)*[1;1]");
 equal(R"(quantum: \sum_{k=0}^{2} -k)","-3");
 equal(R"(quantum: max(\sum_{k=0}^{2} k,4))","4");
 equal(R"(quantum: (\sum_{k=0}^{2} k)^2)","9");
 equal(R"(quantum: \sum_{k=0}^{2} k-1)","2");
 equal(R"(quantum: \sum_{k=1}^{2} 1/k)","3/2");
 equal(R"(quantum: \bigoplus_{k=0}^{1} X)","qdirectsum([0,1;1,0],[0,1;1,0])");
 equal(R"(quantum: ∑_{k=0}^{2} k)","3");
 equal(R"(quantum: \frac{1}{2}\sum_{a_0=0}^1\sum_{a_1=0}^1 e^{2\pi i a_0/4}\vert a_1 a_0\rangle)","[1;i;1;i]/2");
 equal(R"(quantum: \mathrm{QFT}_4)","[1,1,1,1;1,i,-1,-i;1,-1,1,-1;1,-i,-1,i]/2");
 equal("quantum: QFT₄|01>","[1;i;-1;-i]/2");
 equal("quantum: QFT_16|0000>","matrix(16,1,[1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1])/4");
 equal(R"(quantum: QFT_{2^2}^\dagger QFT_4)","identity(4)");
 equal("quantum: QFT_1","matrix(1,1,[1])");
 equal("quantum: QFT_3|0>_3","[1;1;1]/sqrt(3)");
 for(unsigned phase=0;phase<4;++phase) {
  equal(R"(quantum: QFT_4^\dagger(\frac{1}{2}\sum_{a_0=0}^1\sum_{a_1=0}^1 e^{2\pi i(2*a_1+a_0)*)"+std::to_string(phase)+R"(/4}\vert a_1 a_0\rangle))",
        "qbasis("+std::to_string(phase)+",4)");
 }
 equal("quantum: (|0>-|1>)|0>","[1;0;-1;0]");
 equal("quantum: (|0>-|1>)(|0>+|1>)","[1;1;-1;-1]");
 equal("quantum: (<0|+i<1|)(<0|-<1|)","[1,-1,i,-i]");
 equal(R"(quantum: \frac{1}{2}(|0>-|1>)|0>+\frac{1}{2}(|0>-|1>)|1>)","[1;1;-1;-1]/2");
 equal("quantum: H(|0>+|1>)","[sqrt(2);0]");
 equal("quantum: (|0>+|1>)(<0|-<1|)","[1,-1;1,-1]");
 equal("quantum: (<0|-<1|)(|0>+|1>)","0");
 for(int a=0;a<2;++a) {
  equal("quantum: |0⊕"+std::to_string(a)+">_2-|1⊕"+std::to_string(a)+">_2",a ? "[-1;1]" : "[1;-1]");
 }
 equal(R"(quantum: \sum_{a_0=0}^1 (|0\oplus a_0>_2-|1\oplus a_0>_2))","[0;0]");
 equal("quantum: |(1+1)⊕3>_4","[0;1;0;0]");
 equal("quantum: <(1+1)⊕3|_4","[0,1,0,0]");
 equal("quantum: |2⊕3⊕1>_4","[1;0;0;0]");
 equal("quantum: |00⊕11>","[0;0;0;1]");
 equal("quantum: |0⊕0>_2 ⊕ |1>","qdirectsum([1;0],[0;1])");
 for(int f0=0;f0<2;++f0)for(int f1=0;f1<2;++f1) {
  std::string x=std::to_string(f0),y=std::to_string(f1);
  equal("quantum: (|0⊕"+x+">_2-|1⊕"+x+">_2)|0>/2+(|0⊕"+y+">_2-|1⊕"+y+">_2)|1>/2",
        "["+std::to_string(1-2*f0)+";"+std::to_string(1-2*f1)+";"+std::to_string(2*f0-1)+";"+std::to_string(2*f1-1)+"]/2");
 }
 equal("quantum: |trace(I⊕I)>_8","qbasis(4,8)");
 equal("quantum: |mod(2⊕3,2)>_2","[0;1]");
 equal("quantum: 5⊕6","3");
 equal("quantum: (2+3)⊕(2*3)","3");
 equal("quantum: X⊕Z","qdirectsum([0,1;1,0],[1,0;0,-1])");
 equal("quantum: if(0⊕1=1,|1>,|0>)","[0;1]");
 equal(R"(quantum: \sum_{a_0=0}^1 {(-1)^{a_0\oplus 1}|a_0>_2})","[-1;1]");
 for(int f0=0;f0<2;++f0)for(int f1=0;f1<2;++f1) {
  std::string x=std::to_string(f0),y=std::to_string(f1);
  equal("quantum: (-1)^"+x+" |-> (|0>+(-1)^("+x+"⊕"+y+")|1>)/sqrt(2)",
        "["+std::to_string(1-2*f0)+";"+std::to_string(1-2*f1)+";"+std::to_string(2*f0-1)+";"+std::to_string(2*f1-1)+"]/2");
 }
 equal(R"(quantum: \begin{cases}|0> & \text{if $1=1$}\\[1mm]|1> & \text{if $1=0$}\end{cases})","[1;0]");
 equal(R"(quantum: \begin{cases}|0> & 0\\|1> & \text{otherwise}\end{cases})","[0;1]");
 equal(R"(quantum: \begin{cases}|0> & 1\\1/0 & \text{otherwise}\end{cases})","[1;0]");
 equal(R"(quantum: 2\begin{cases}3 & 1\\4 & 0\end{cases}+1)","7");
 equal(R"(quantum: \sum_{a_0=0}^1 {\begin{cases}|0> & a_0=0\\|1> & a_0=1\end{cases}})","[1;1]");
 equal(R"(quantum: \begin{cases}\begin{cases}4 & 1\end{cases} & 1\\5 & 0\end{cases})","4");
 equal(R"(quantum: \begin{cases}\begin{bmatrix}1&0\\0&1\end{bmatrix} & 1\\X & 0\end{cases})","[1,0;0,1]");
 equal(R"(quantum: \begin{cases}|0,1> & 1\\|1,0> & 1\end{cases})","[0;1;0;0]");
 if(!calculator.calculate(R"(quantum: \begin{cases}1 & 0\\2 & 0\end{cases})",eo).isUndefined())throw std::runtime_error("Unmatched cases must be undefined");
 ++checks;
 for(int f0=0;f0<2;++f0)for(int f1=0;f1<2;++f1) {
  std::string x=std::to_string(f0),y=std::to_string(f1);
  equal("quantum: \\begin{cases}(-1)^"+x+" |->|0> & \\text{if $"+x+"\\oplus "+y+"=0$}\\\\[1mm](-1)^"+x+" |->|1> & \\text{if $"+x+"\\oplus "+y+"=1$}\\end{cases}",
        "(-1)^"+x+"*qtensor([1;-1]/sqrt(2),qbasis("+std::to_string(f0^f1)+",2))");
 }
 equal("quantum: sequence([apply(H,s_0,[0]),apply(X,s_0,[0])],|0>,s_0)","[1;1]/sqrt(2)");
 equal("quantum: sequence([apply(X,s_0,[0]),reset(s_0,[0])],|0>,s_0)","[1,0;0,0]");
 equal("quantum: sequence([],|1>,s_0)","[0;1]");
 std::string longSequence="quantum: sequence([";
 for(int k=0;k<512;++k){if(k)longSequence+=",";longSequence+="apply(X,s_0,[0])";}
 equal(longSequence+"],|0>,s_0)","[1;0]");
 equal("quantum: sequence([sequence([apply(X,s_0,[0])],s_0,s_0),apply(X,s_0,[0])],|0>,s_0)","[1;0]");
 equal(R"(quantum: \sum_{s_0=0}^1 {sequence([apply(X,s_0,[0])],|s_0>_2,s_0)})","[1;1]");
 equal("quantum: sequence([channel(density(s_0),amplitude_damping(1),0),apply(X,s_0,[0])],|1>,s_0)","[0,0;0,1]");
 equal("quantum: sequence([dephase(s_0,[0])],|+>,s_0)","[1,0;0,1]/2");
 equal("quantum: sequence([feedforward(s_0,0,1,X,1)],|+0>,s_0)","[1,0,0,0;0,0,0,0;0,0,0,0;0,0,0,1]/2");
 equal("2+3*4","14");
 equal("sin(pi/2)","1");
 for(const char *input:{"quantum: |->"," quantum: |->"}) {
  std::string expression=input,to;
  if(calculator.hasToExpression(expression,true) || calculator.hasToExpression(expression,true,eo) || calculator.separateToExpression(expression,to,eo,true,true))throw std::runtime_error("Ket mistaken for conversion");
  if(expression!=input || !to.empty())throw std::runtime_error("Conversion probe changed expression");
  ++checks;
 }
 if(!calculator.hasToExpression("1 m -> cm",true,eo))throw std::runtime_error("Ordinary conversion disabled");
 ++checks;
 for(const auto &expression:{"quantum: sequence([1],|0>,s_0)","quantum: sequence([],1,s_0)","quantum: sequence([s_0],|0>,1)","quantum: sequence([apply(X,s_0,[2])],|0>,s_0)","quantum: sequence([apply(X,s_0,[0]);s_0],|0>,s_0)","quantum: -1⊕1","quantum: 0.5⊕1","quantum: i⊕1","quantum: X⊕1","quantum: |-1⊕-2>_2","quantum: |0.5⊕1>_2","quantum: |i⊕1>_2","quantum: |2⊕1>_2","quantum: (|0>+|1>)*|0>","quantum: QFT_0","quantum: QFT_65","quantum: QFT_{-1}",R"(quantum: \sum_{k=0}^{2})",R"(quantum: (\sum_{k=0}^{2}))","quantum: |0","quantum: <0|H|", "quantum: |0> +",
     R"(quantum: |a_0 0 0 0 0 0 0 0 0 0 0>)",R"(quantum: \sum_{a_0=2}^{2}{|a_0 0>})",R"(quantum: \sum_{a_0=-1}^{-1}{|a_0 0>})",
     R"(quantum: \sum_{0_a=0}^{2}{0_a})",R"(quantum: \sum_{a_0+1=0}^{2}{a_0})"}) {
  while(calculator.message())calculator.nextMessage();
  MathStructure value=calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Malformed quantum syntax accepted: ")+expression);
  ++checks;
 }
 std::cout<<"PASS: "<<checks<<" parser integration checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
