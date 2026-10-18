// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumAlgebra.h"
#include "QuantumIndexed.h"
#include "Variable.h"
#include "Function.h"
#include <iostream>
#include <stdexcept>
static unsigned checks=0;
static EvaluationOptions eo;
static void equal(const std::string &expression,const std::string &expected) {
 MathStructure value=CALCULATOR->calculate(expression,eo),reference=CALCULATOR->calculate(expected,eo);
 value.transform(COMPARISON_EQUALS,reference);value.eval(eo);
 if(!value.isNumber() || !value.number().isOne())throw std::runtime_error("Mismatch: "+expression+" vs "+expected+" -> "+value.print());
 ++checks;
}
int main(){try {
 Calculator calculator;if(!calculator.loadGlobalDefinitions())throw std::runtime_error("Definitions unavailable");
#ifdef LOCAL_CHECKPOINT
 registerQuantumAlgebra(calculator);
 registerQuantumIndexed(calculator);
#endif
 eo.approximation=APPROXIMATION_EXACT;
 // A matrix-valued unknown must not be broadcast as a scalar while other
 // substitutions in the same expression are still pending.
 const std::string indexedMixture=R"(quantum: replace(replace(replace(replace(replace(\sum_{k=0}^{m-1} p_k \rho_k,m,2),p_0,1/2),p_1,1/2),\rho_0,density(|0>)),\rho_1,density(|+>)))";
 MathStructure mixture=calculator.calculate(indexedMixture,eo);
 if(!mixture.isMatrix() || mixture.rows()!=2 || mixture.columns()!=2)throw std::runtime_error("Indexed mixture has the wrong shape");
 for(size_t row=1;row<=2;++row)for(size_t column=1;column<=2;++column) {
  const MathStructure &cell=*mixture.getElement(row,column);
  if(!cell.isNumber() || cell.number()!=Number(row==1 && column==1 ? 3 : 1,4))throw std::runtime_error("Indexed mixture requires scalar matrix entries");
 }
 ++checks;
 equal("quantum: replace(replace(x,x,y+1),y,2)","3");
 equal("quantum: replace(replace(x,x,x+1),x,2)","3");
 equal("quantum: replace(x+y,[x,y],[1,2])","3");
 equal("quantum: replace(x+x,x,2,1)","4");
 equal(R"(quantum: \sum_{k=0}^{1}{p_k})","quantum: p_0+p_1");
 equal(R"(quantum: \sum_{k=0}^{1}{\rho_k})","quantum: ρ_0+ρ_1");
 equal(R"(quantum: \sum_{j=0}^{1}{\sum_{k=0}^{1}{p_j_k}})","quantum: p_0_0+p_0_1+p_1_0+p_1_1");
 equal(R"(quantum: \sum_{k=0}^{1}{\sum_{k=0}^{1}{p_k}})","quantum: 2*(p_0+p_1)");
 equal(R"(quantum: \sum_{k=0}^{1}{p_j})","quantum: 2*p_j");
 equal(R"(quantum: \sum_{k=0}^{1}{p_kk})","quantum: 2*p_kk");
 equal(R"(quantum: \sum_{k=0}^{1}{"p_k"})",R"(2*"p_k")");
 equal(R"(quantum: \sum_{k=0}^{1}{p_k+"p_k"})",R"(quantum: p_0+p_1+2*"p_k")");
 equal(R"(quantum: \sum_{k=0}^{1}{p_k_k})","quantum: p_0_0+p_1_1");
 equal(R"(quantum: replace(\sum_{k=0}^{N-1}{p_k},N,2))","quantum: p_0+p_1");
 equal(R"(quantum: \sum_{\alpha=0}^{1}{p_\alpha})","quantum: p_0+p_1");
 equal(R"(quantum: \sum_{a_0=0}^{1}{p_{a_0}})","quantum: p_0+p_1");
 equal(R"(quantum: \sum_{j=0}^{1}{\sum_{k=0}^{j}{p_j_k}})","quantum: p_0_0+p_1_0+p_1_1");
 equal(R"(quantum: \sum_{k\in\{0,1\}}{p_k})","quantum: p_0+p_1");
 equal(R"(quantum: \sum_{k=-1}^{0}{p_k})",R"("p_-1"+"p_0")");
 equal(R"(quantum: \sum_{k\in\{1000000000000000000000000000000\}}{p_k})",R"("p_1000000000000000000000000000000")");
 defineQuantumStateFamily(calculator,"family_k",calculator.parse("[1;x]"),calculator.parse("x"));
 equal(R"(quantum: \sum_{k=0}^{1}{|family_k(k)>})","[2;1]");
 MathStructure deferredEnsemble=calculator.calculate(R"(quantum: \sum_{k=0}^{1}{|ensemble_k><ensemble_k|})",eo);
 const std::string copiedEnsemble=deferredEnsemble.print();
 calculator.addVariable(new KnownVariable("","ensemble_0",std::string("[1;0]")));
 calculator.addVariable(new KnownVariable("","ensemble_1",std::string("[0;1]")));
 defineQuantumStateFamily(calculator,"ensemble",calculator.parse("[1;x]"),calculator.parse("x"));
 deferredEnsemble.eval(eo);
 deferredEnsemble.transform(COMPARISON_EQUALS,calculator.calculate("identity(2)",eo));deferredEnsemble.eval(eo);
 if(!deferredEnsemble.isNumber() || !deferredEnsemble.number().isOne())throw std::runtime_error("Deferred indexed states did not resolve after definition");
 ++checks;
 equal("quantum: "+copiedEnsemble,"identity(2)");
 equal(R"(quantum: \sum_{k=0}^{1}{|ensemble_k><ensemble_k|})","quantum: |ensemble_0><ensemble_0|+|ensemble_1><ensemble_1|");
 equal(R"(quantum: replace(\sum_{k=0}^{N-1}{|ensemble_k><ensemble_k|},N,2))","quantum: |ensemble_0><ensemble_0|+|ensemble_1><ensemble_1|");
 equal(R"(quantum: \sum_{k=0}^{1}{|ensemble_k><ensemble_k|}/2)","identity(2)/2");
 eo.approximation=APPROXIMATION_APPROXIMATE;
 equal(R"(quantum: \sum_{k=0}^{1}{|ensemble_k><ensemble_k|}/2)","identity(2)/2");
 eo.approximation=APPROXIMATION_EXACT;
 while(calculator.message()) {
  if(calculator.message()->type()==MESSAGE_ERROR)throw std::runtime_error("Indexed labels emitted an evaluation error");
  calculator.nextMessage();
 }
 equal("quantum: sqrt(8*25GHz*0.5GHz)-0.5GHz","9.5 GHz");
 equal("quantum: (1GHz)/(1MHz)","1000");
 equal("quantum: (1mHz)/(1Hz)","1/1000");
 equal("quantum: (2GHz)^2","4 GHz^2");
 equal("quantum: 2GHz*|0>","[2 GHz;0]");
 for(auto angle:{ANGLE_UNIT_NONE,ANGLE_UNIT_RADIANS,ANGLE_UNIT_DEGREES,ANGLE_UNIT_GRADIANS}) {
  eo.parse_options.angle_unit=angle;
  equal("quantum: cos(pi rad)","-1");
  equal("quantum: sin(30 deg)","1/2");
  equal("quantum: tan(45 deg)","1");
  equal("quantum: sin(pi/6)","1/2");
  equal("quantum: replace(cos(theta rad),theta,pi)","-1");
  equal("quantum: replace(sin(theta deg),theta,30)","1/2");
  if(angle==ANGLE_UNIT_DEGREES)equal("sin(30)","1/2");
  if(angle==ANGLE_UNIT_GRADIANS)equal("cos(200)","-1");
 }
 eo.parse_options.angle_unit=ANGLE_UNIT_NONE;
 equal("quantum: |0>_1","qbasis(0,1)");
 equal("quantum: QFT_1|0>_1","qbasis(0,1)");
 equal(R"(quantum: \sum_{k=0}^{0}{|k>})","qbasis(0,1)");
 equal(R"(quantum: replace(\sum_{k=0}^{N-1}{|k>},N,1))","qbasis(0,1)");
 equal(R"(quantum: \frac{1}{\sqrt{385}}\sum_{k=0}^9 (k+1)\vert k\rangle)","[1;2;3;4;5;6;7;8;9;10]/sqrt(385)");
 equal(R"(quantum: \sum_{k=0}^{2}{|k><k|})","identity(3)");
 equal(R"(quantum: \sum_{k=0}^{2}{<k|k>})","3");
 equal(R"(quantum: replace(\sum_{k=0}^{N-1}{|k>},N,3))","[1;1;1]");
 equal(R"(quantum: \sum_{k=0}^{2}{\sum_{k=0}^{1}{|k>}})","[3;3]");
 equal(R"(quantum: replace(1/sqrt(|\Sigma|)\sum_{a\in\Sigma}{|a>},\Sigma,bitstrings(1)))","[1;1]/sqrt(2)");
 equal(R"(quantum: replace(cardinality(S),S,vector(2,3,3)))","2");
 equal(R"(quantum: replace(|S|,S,-3))","3");
 equal(R"(quantum: replace(\sum_{x\in S}{x},S,vector(2,3,3)))","5");
 equal(R"(quantum: replace(\sum_{k=0}^{N-1}{k},N,4))","6");
 equal(R"(quantum: replace(\sum_{k=0}^{N-1}{|k>_4},N,4))","[1;1;1;1]");
 equal(R"(quantum: replace(\sum_{k=0}^{N-1}{\sum_{k=0}^{1}{k}},N,3))","3");
 equal(R"(quantum: replace(\sum_{k=0}^{N-1}{\sum_{j=0}^{k}{j}},N,3))","4");
 equal(R"(quantum: replace(replace(\sum_{k=0}^{N-1}{\alpha^k},N,4),\alpha,2))","15");
 for(const char *expression:{R"(quantum: \sum_{k=0}^{N-1}{k})",R"(quantum: \sum_{k=L}^{N}{k})",R"(quantum: \sum_{k=0}^{2^m-1}{e^{2\pi i k\theta}})"}) {
  while(calculator.message())calculator.nextMessage();
  MathStructure value=calculator.calculate(expression,eo);
  if(!value.isFunction() || value.function()->referenceName()!="qsum")throw std::runtime_error("Symbolic sum was not retained");
  while(calculator.message()) {if(calculator.message()->type()==MESSAGE_ERROR)throw std::runtime_error("Symbolic sum reported an error");calculator.nextMessage();}
  ++checks;
 }
 equal("quantum: 1 <= |-2|","1");
 equal("quantum: 3 <= |-2|","0");
 equal("quantum: |-1| ≤ 2|-1/2|","1");
 equal(R"(quantum: |e^{2\pi i (-1/2)}-1| <= 2\pi|-1/2|)","1");
 equal(R"(quantum: \alpha|0>+\beta|1>)",R"(["α";"β"])");
 equal(R"(quantum: \gamma\delta)",R"("γ"*"δ")");
 equal("quantum: δ(1)","dirac(1)");
 equal("quantum: pi","pi");
 equal("quantum: alpha","fine_structure");
 equal("quantum: Σ",R"("Σ")");
 equal("quantum: Π",R"("Π")");

 equal(R"(quantum: \cos^2(\pi\theta))",R"(cos(pi*"θ")^2)");
 equal(R"(quantum: \sin^2(\pi\theta))",R"(sin(pi*"θ")^2)");
 equal(R"(quantum: replace(\cos^2(\pi\theta),\theta,1/3))","1/4");
 equal(R"(quantum: replace(\sin^2(\pi\theta),\theta,1/3))","3/4");
 equal(R"(quantum: e^{2\pi i\theta})",R"(exp(2*pi*i*"θ"))");
 equal("quantum: θ(0)","heaviside(0)");
 equal("quantum: θ(1)","1");
 equal("quantum: θ(-1)","0");
 equal("quantum: |x>_θ",R"(qbasis(x,"θ"))");

 equal("quantum: |x>_N","quantum: |x>_{N}");
 equal("quantum: QFT_N|x>_N","quantum: QFT_N|x>_{N}");
 calculator.addVariable(new KnownVariable("","registerdim",std::string("3")));
 equal("quantum: |1>_registerdim","[0;1;0]");
 equal("quantum: <1|_registerdim","[0,1,0]");
 equal("quantum: <1|_registerdim|1>_registerdim","1");
 for(const char *expression:{"quantum: |3>_registerdim","quantum: |-1>_registerdim","quantum: |1>_H"}) {
  while(calculator.message())calculator.nextMessage();calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid dimension-qualified ket accepted: ")+expression);++checks;
 }


 equal("quantum: |0>+|1>","[1;1]");
 equal("quantum: |0>-|1>","[1;-1]");
 equal("quantum: [1,2]+[3,4]","[4,6]");
 equal("quantum: 0+|0>","[1;0]");
 equal("quantum: |0>+0","[1;0]");
 equal("quantum: 0-|0>","[-1;0]");
 equal("quantum: 2+3-1","4");
 for(const char *expression:{"quantum: |0>-density(|0>)","quantum: |0>+identity(2)","quantum: [1;2]+[1,2]","quantum: [1;2]+[3;4;5]","quantum: 2+identity(2)","quantum: identity(2)-2"}) {
  while(calculator.message())calculator.nextMessage();calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid quantum sum accepted: ")+expression);++checks;
 }
 equal(R"(quantum: |\{0,1\}\cup\{1,2\}|)","3");
 equal(R"(quantum: |\{0,1\}∩\{1,2\}|)","1");
 equal(R"(quantum: |\{0,1,2\}∖\{1\}|^2)","4");
 equal(R"(quantum: |\{0,1\}∪(\{1,2\}∩\{2\})|)","3");
 equal(R"(quantum: |\{0,1\}∪\{1,2\}∩\{2\}|)","3");
 equal("quantum: |∅|","0");
 equal(R"(quantum: \lvert\{0,1\}^2\cup\emptyset\rvert)","4");
 equal(R"(quantum: |\{x\in\{0,1\}^2:<x|x>=1\}∩\{0,1\}^2|)","4");
 equal("quantum: |⟨101|(H⊗H⊗H)|000⟩|^2","1/8");
 equal(R"(quantum: bitstring(1,2)\in\{0,1\}^2)","1");
 equal(R"(quantum: bitstring(1,3)\notin\{0,1\}^2)","1");
 equal("quantum: 2∈vector(1,2,3)","1");
 equal("quantum: 4∉vector(1,2,3)","1");
 equal("quantum: member(1/2,vector(2/4,3))","1");
 equal("quantum: member(bitstring(1+1,2),vector(bitstring(2,2)))","1");
 equal("quantum: member(1,bitstrings(2))","0");
 equal("quantum: member(0,vector())","0");
 equal("quantum: member(bitstring(0,0),bitstrings(0))","1");
 equal(R"(quantum: |\{x\in\{0,1\}^2:x\in\{y\in\{0,1\}^2:bitvalue(y)<2\}\}|)","2");
 for(int mask=0;mask<16;++mask)for(int index=0;index<4;++index) {
  std::string collection="vector(";bool first=true;for(int k=0;k<4;++k)if(mask&(1<<k)){if(!first)collection+=",";first=false;collection+="bitstring("+std::to_string(k)+",2)";}collection+=")";
  equal("quantum: bitstring("+std::to_string(index)+",2)∈"+collection,(mask&(1<<index)) ? "1" : "0");
 }
 for(const char *expression:{"quantum: member(1,3)","quantum: member(1,identity(2))","quantum: member(bitstring(4,2),bitstrings(2))","quantum: member(1,vector(1,identity(2)))"}) {
  while(calculator.message())calculator.nextMessage();calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid membership accepted: ")+expression);++checks;
 }
 calculator.addVariable(new KnownVariable("","leftset",std::string("vector(0,1)")));
 calculator.addVariable(new KnownVariable("","rightset",std::string("vector(1,2)")));
 equal("quantum: |leftset|","2");
 equal("quantum: |leftset∪rightset|","3");
 equal("quantum: |(leftset∩rightset)|","1");
 equal("quantum: |-3|","3");
 equal("quantum: |3+4i|","5");
 equal("quantum: |(2-5)|^2","9");
 equal("quantum: |vector(7)|","1");
 calculator.addVariable(new KnownVariable("","oneset",std::string("vector(7)")));
 equal("quantum: |oneset|","1");
 equal("quantum: |bitstrings(0)|","1");
 equal(R"(quantum: \frac{1}{\sqrt{\vert leftset\vert}})","1/sqrt(2)");
 equal("quantum: |leftset|+|rightset|","4");
 equal("quantum: |(∅)|","0");
 eo.approximation=APPROXIMATION_APPROXIMATE;
 equal("quantum: |oneset|","1");
 eo.approximation=APPROXIMATION_EXACT;
 for(const char *expression:{"quantum: |identity(2)|","quantum: |bitstring(1,2)|","quantum: |leftset∪|","quantum: |(leftset|"}) {
  while(calculator.message())calculator.nextMessage();calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid bars accepted: ")+expression);++checks;
 }
 equal("quantum: cardinality(leftset∪rightset)","3");
 equal("quantum: cardinality(leftset∩rightset)","1");
 equal("quantum: cardinality(leftset∖rightset)","1");
 equal(R"(quantum: cardinality(leftset\cup rightset))","3");
 equal(R"(quantum: cardinality(\{0,1\}\cup\{1,2\}))","3");
 equal(R"(quantum: cardinality(\{0,1\}\cap\{1,2\}))","1");
 equal(R"(quantum: cardinality(\{0,1\}\setminus\{1,2\}))","1");
 equal(R"(quantum: cardinality(\varnothing))","0");
 equal(R"(quantum: cardinality(\emptyset))","0");
 equal("quantum: cardinality(∅)","0");
 equal(R"(quantum: cardinality(\{0,1\}∪\{1,2\}∩\{2\}))","3");
 equal(R"(quantum: cardinality((\{0,1\}∪\{1,2\})∩\{2\}))","1");
 equal(R"(quantum: cardinality(\{0,1,2\}∖\{1\}∖\{2\}))","1");
 equal(R"(quantum: cardinality(\{0,1\}^2\cup\emptyset))","4");
 equal(R"(quantum: cardinality(\{0,1\}^2\cap\emptyset))","0");
 equal(R"(quantum: cardinality(\{x\in\{0,1\}^2:bitvalue(x)<2\}\cup\{x\in\{0,1\}^2:bitvalue(x)>=2\}))","4");
 auto labelSet=[](int mask) {std::string s="vector(";bool first=true;for(int k=0;k<4;++k)if(mask&(1<<k)){if(!first)s+=",";first=false;s+="bitstring("+std::to_string(k)+",2)";}return s+")";};
 for(int left=0;left<16;++left)for(int right=0;right<16;++right) {
  std::string a=labelSet(left),b=labelSet(right);
  equal("quantum: sumset(2^bitvalue(k),union("+a+","+b+"),k)",std::to_string(left|right));
  equal("quantum: sumset(2^bitvalue(k),intersect("+a+","+b+"),k)",std::to_string(left&right));
  equal("quantum: sumset(2^bitvalue(k),setdiff("+a+","+b+"),k)",std::to_string(left&~right));
 }
 equal("quantum: cardinality(union(vector(bitstring(0,2)),vector(bitstring(0,3))))","2");
 equal("quantum: cardinality(intersect(vector(bitstring(0,2)),vector(bitstring(0,3))))","0");
 for(const auto &item:{std::pair<const char *,int>("union",3),{"intersect",2},{"setdiff",1}}) {
  MathStructure result=calculator.calculate(std::string("quantum: ")+item.first+"(vector(bitstring(1,2),bitstring(1,2),bitstring(1,2)),vector(bitstring(1,2),bitstring(1,2)),1)",eo);
  MathStructure label=calculator.calculate("quantum: bitstring(1,2)",eo);
  if(item.second==1 && result.equals(label))result.transform(STRUCT_VECTOR);
  if(!result.isVector() || result.size()!=static_cast<size_t>(item.second))throw std::runtime_error(std::string("Wrong binary multiset size: ")+item.first);++checks;
 }
 calculator.addVariable(new KnownVariable("","markedstrings",std::string("quantum: \\{x\\in\\{0,1\\}^3:bitvalue(x)<3\\}")));
 equal("quantum: |markedstrings|","3");
 equal("quantum: norm(vec(|markedstrings>-sumset(|x>,markedstrings,x)/sqrt(|markedstrings|)))","0");
 equal("quantum: |markedstrings>","[1;1;1;0;0;0;0;0]/sqrt(3)");
 equal("quantum: <markedstrings|markedstrings>","1");
 equal("quantum: <001|markedstrings>","1/sqrt(3)");
 equal("quantum: qketstate(vector(bitstring(0,2),bitstring(3,2),bitstring(0,2)))","[1;0;0;1]/sqrt(2)");
 equal("quantum: qketstate(bitstrings(0))","qbasis(0,1)");
 for(int width=1;width<=5;++width)equal("quantum: qketstate(bitstrings("+std::to_string(width)+"))","quantum: H^{\\otimes "+std::to_string(width)+"}|0^"+std::to_string(width)+">");
 for(const char *expression:{"quantum: qketstate(vector())","quantum: qketstate(vector(bitstring(0,2),bitstring(0,3)))","quantum: qketstate(vector(bitstring(0,2),1))","quantum: qketstate(vector(bitstring(4,2),bitstring(0,2)))"}) {
  while(calculator.message())calculator.nextMessage();calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid set ket accepted: ")+expression);++checks;
 }
 for(int width=1;width<=4;++width)for(int count=0;count<=(1<<width);++count) {
  std::string domain="\\{x\\in\\{0,1\\}^"+std::to_string(width)+":bitvalue(x)<"+std::to_string(count)+"\\}";
  equal("quantum: |"+domain+"|",std::to_string(count));
  equal("quantum: \\sum_{x\\in"+domain+"}{bitvalue(x)}",std::to_string(count*(count-1)/2));
 }
 equal(R"(quantum: norm(vec(\sum_{x\in\{x\in\{0,1\}^3:bitvalue(x)<3\}}{|x>}-|000>-|001>-|010>)))","0");
 equal(R"(quantum: |\{x\in\{0,1\}^0:bitvalue(x)=0\}|)","1");
 equal("quantum: cardinality(unique(vector(bitstring(1,2),bitstring(1,3),bitstring(1,2))))","2");
 equal("quantum: cardinality(unique(vector(bitstring(1+1,3),bitstring(2,3))))","1");
 equal("quantum: cardinality(unique([3,2,3,1]))","3");
 for(int a=0;a<8;++a)for(int b=0;b<8;++b) {
  std::string left="bitstring("+std::to_string(a)+",3)",right="bitstring("+std::to_string(b)+",3)";
  equal("quantum: bitvalue(bitxor("+left+","+right+"))",std::to_string(a^b));
  int intersection=a&b,parity=(intersection^(intersection>>1)^(intersection>>2))&1;
  equal("quantum: bitdot("+left+","+right+")",std::to_string(parity));
 }
 equal("quantum: qketstate(bitxor(bitstring(5,4),bitstring(6,4)))","quantum: |0011>");
 equal("quantum: bitxor(bitstring(5,3),[1,1,0])","[0,1,1]");
 equal("quantum: bitvalue(bitstring(0,0))","0");
 equal("quantum: bitdot(bitstring(0,0),bitstring(0,0))","0");
 equal("quantum: bitvalue(bitxor(bitstring(0,0),bitstring(0,0)))","0");
 equal("quantum: bitvalue(bitstring(1023,10))","1023");
 for(const char *expression:{"quantum: bitdot(bitstring(1,2),bitstring(1,3))","quantum: bitxor(bitstring(0,0),[0])","quantum: bitvalue(bitstring(4,2))","quantum: bitvalue(bitstring(0,11))"}) {
  while(calculator.message())calculator.nextMessage();calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid binary operation accepted: ")+expression);++checks;
 }
 equal(R"(quantum: \sum_{x\in\{0,1\}^2}{|x>})","[1;1;1;1]");
 equal(R"(quantum: \sum_{x\in\{0,1\}^2}{|x><x|})","identity(4)");
 equal(R"(quantum: \sum_{x\in\{0,1\}^2}{<x|x>})","4");
 equal(R"(quantum: |\{0,1\}^3|)","8");
 equal("quantum: cardinality(bitstrings(0))","1");
 equal("quantum: cardinality(bitstrings(10))","1024");
 equal(R"(quantum: \sum_{x\in\{0,1\}^2}{\sum_{x\in\{0,1\}^1}{|x>}})","[4;4]");
 equal("quantum: qketstate(bitstring(1,3))","[0;1;0;0;0;0;0;0]");
 for(const char *expression:{"quantum: bitstrings(-1)","quantum: bitstrings(11)","quantum: bitstrings(1/2)","quantum: bitstrings(n)","quantum: bitstring(4,2)","quantum: bitstring(-1,2)"}) {
  while(calculator.message())calculator.nextMessage();calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid binary domain accepted: ")+expression);++checks;
 }
 equal(R"(quantum: \lvert\{0,1,1\}\rvert)","2");
 equal(R"(quantum: \vert\{0,1,1\}\vert)","2");
 equal(R"(quantum: |\{0,1,1\}|)","2");
 equal(R"(quantum: \lvert\{\}\rvert)","0");
 equal(R"(quantum: \lvert\{7\}\rvert)","1");
 equal(R"(quantum: \lvert\{0,\ldots,7\}\rvert)","8");
 equal(R"(quantum: \left|\{k\in\{0,\ldots,7\}:k>3\}\right|)","4");
 equal("quantum: cardinality([0,1,1])","2");
 equal("quantum: cardinality([7])","1");
 equal("quantum: cardinality([1/2,2/4])","1");
 equal("quantum: cardinality(indexrange(0,1023))","1024");
 equal(R"(quantum: \sum_{n=1}^{3}{|\{0,\ldots,n\}|})","9");
 equal(R"(quantum: |\{0,1\}|^2)","4");
 calculator.addVariable(new KnownVariable("","markedindices",std::string("[0,2,2,5]")));
 equal("quantum: cardinality(markedindices)","3");
 calculator.addVariable(new KnownVariable("","singletonindices",std::string("quantum: [7]")));
 equal("quantum: cardinality(singletonindices)","1");
 equal(R"(quantum: \lfloor\pi/(4\sin^{-1}(\sqrt{|\{k\in\{0,\ldots,15\}:k<4\}|/16}))\rfloor)","1");
 equal(R"(quantum: \sin^2(3\sin^{-1}(\sqrt{|\{k\in\{0,\ldots,15\}:k<4\}|/16})))","1");
 equal(R"(quantum: \Bigl\lfloor\frac{\pi}{4}\sqrt{16}\Bigr\rfloor)","3");
 equal(R"(quantum: \lfloor-3/2\rfloor)","-2");
 equal(R"(quantum: \lceil-3/2\rceil)","-1");
 equal(R"(quantum: \lceil\lfloor3/2\rfloor+1/2\rceil)","2");
 equal(R"(quantum: \lfloor3/2\rfloor^2+\lceil3/2\rceil^2)","5");
 equal("quantum: ⌊3/2⌋","1");
 equal("quantum: ⌈3/2⌉","2");
 equal("quantum: ⌊-3/2⌋+⌈-3/2⌉","-3");
 equal("quantum: ⌈⌊3/2⌋+1/2⌉","2");
 equal(R"(quantum: \sum_{k=1}^{4}{\lfloor k/2\rfloor})","4");
 for(bool approximate:{false,true})for(const char *label:{"Bell","psi","undefinedvector","after CZ","afterCZ","today","undefined"}) {
  EvaluationOptions options=eo;options.approximation=approximate ? APPROXIMATION_APPROXIMATE : APPROXIMATION_EXACT;
  while(calculator.message())calculator.nextMessage();
  MathStructure value=calculator.calculate(std::string("quantum: |")+label+">",options);
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)throw std::runtime_error(std::string("Named state rejected: ")+label);calculator.nextMessage();}
  if(!value.isFunction() || value.function()->referenceName()!="qketstate" || value.size()!=1 || !value[0].isSymbolic() || value[0].symbol()!=label)throw std::runtime_error(std::string("State label was not preserved atomically: ")+label+" -> "+value.print()+" child="+(value.size() ? value[0].symbol() : "none"));++checks;
 }
 calculator.addVariable(new KnownVariable("","Bell",std::string("[1;0;0;1]/sqrt(2)")));
 calculator.addVariable(new KnownVariable("","psi",std::string("[1;i]/sqrt(2)")));
 equal("quantum: <Bell|Bell>","1");
 equal("quantum: <Bell|CZ|Bell>","0");
 equal("quantum: <psi|psi>","1");
 equal("quantum: |psi>","[1;i]/sqrt(2)");
 calculator.addVariable(new KnownVariable("","statevector",std::string("[1;i]/sqrt(2)")));
 calculator.addVariable(new KnownVariable("","scalarstate",std::string("3")));
 equal("quantum: |statevector>","[1;i]/sqrt(2)");
 equal("quantum: <statevector|statevector>","1");
 equal("quantum: |statevector><statevector|","[1,-i;i,1]/2");
 equal(R"(quantum: \sum_{x\in\{0,1,2\}}{|x>_3})","[1;1;1]");
 for(const char *expression:{"quantum: cardinality(3)","quantum: cardinality([[1]])","quantum: cardinality(identity(2))","quantum: cardinality(indexrange(0,1024))","quantum: |scalarstate>","quantum: <scalarstate|",R"(quantum: \sum_{x\in\{0,1,2\}}{|x>})"}) {
  while(calculator.message())calculator.nextMessage();
  calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Scalar named ket accepted: ")+expression);
  ++checks;
 }

 equal(R"(quantum: \sin^{-1}(1/2))","pi/6");
 equal(R"(quantum: \sin^{- 1}(1/2))","pi/6");
 equal(R"(quantum: \cos^{-\!1}(1/2))","pi/3");
 equal(R"(quantum: \cos^{-1}\biggl(1/2\biggr))","pi/3");
 equal(R"(quantum: \tan^{-1}{1})","pi/4");
 equal(R"(quantum: \sin^2(pi/6)+\cos^2(pi/6))","1");
 equal(R"(quantum: \sin^{-2}(pi/6))","4");
 equal(R"(quantum: \arcsin(1/2))","pi/6");
 equal(R"(quantum: \lfloor\pi/(4\sin^{-1}(1/2))\rfloor)","1");
 equal(R"(quantum: \sin^2((2\lfloor\pi/(4\sin^{-1}(1/2))\rfloor+1)\sin^{-1}(1/2)))","1");
 equal("quantum: sumset(k,indexrange(0,3),k)","6");
 equal(R"(quantum: \sum_{k\in\{0,\ldots,3\}}{k})","6");
 equal(R"(quantum: \sum_{k\in\{k\in\{0,\ldots,7\}:k\geq4\}}{k})","22");
 equal(R"(quantum: \sum_{n=1}^{3}{\sum_{k\in\{0,\dots,n-1\}}{k}})","4");
 equal(R"(quantum: \sum_{k\in\{0,\ldots,-1\}}{k})","0");
 equal(R"(quantum: \sum_{k\in\{3,\ldots,3\}}{k})","3");

 equal(R"(quantum: \sum_{\alpha\in\{1,3\}}{\sum_{a_0\in\{\alpha\in\{\alpha,\alpha+1\}:\alpha>1\}}{a_0}})","9");

 equal(R"(quantum: \{0,2,0\})","vector(0,2)");
 equal(R"(quantum: \{k\in\{-2,0,2,2\}:k\geq0\})","vector(0,2)");
 equal(R"(quantum: \{k\in\{0,2\}:k<0\})","vector()");
 equal(R"(quantum: \sum_{k\in\{j\in\{-1,0,2\}:j>=0\}}{k})","2");
 equal(R"(quantum: \sum_{k\in\{1,3\}}{\sum_{k\in\{k\in\{k,k+1\}:k>1\}}{k}})","9");
 equal(R"(quantum: \{\alpha\in\{-1,0,1\}:\alpha\geq0\})","vector(0,1)");

 equal(R"(quantum: \prod_{\alpha=1}^{2}{\sum_{\alpha\in\{2,3\}}{\alpha}})","25");
 equal(R"(quantum: \sum_{\alpha\in\{0,1\}}{\prod_{\alpha=2}^{3}{\alpha}})","12");

 equal(R"(quantum: \sum_{\alpha=0}^{1}{\sum_{\alpha\in\{2,3\}}{\alpha}})","10");

 equal(R"(quantum: \sum_{k=0}^{1}{\sum_{k\in\{2,3\}}{k}})","10");
 equal(R"(quantum: \sum_{k\in\{2,3\}}{\sum_{k=0}^{1}{k}})","2");
 equal(R"(quantum: sumset(k,[0,2,5],k))","7");

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
 equal("quantum: QFT_1","qbasis(0,1)");
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
