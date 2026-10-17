// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumSuperoperators.h"
#include <iostream>
#include <stdexcept>
static unsigned checks=0;
static EvaluationOptions eo;
static void equal(const std::string &expression,const std::string &expected) {
 MathStructure value=CALCULATOR->calculate("("+expression+")==("+expected+")",eo);
 if(!value.isNumber() || !value.number().isOne())throw std::runtime_error("Mismatch: "+expression+" vs "+expected);
 ++checks;
}
int main(){try {
 Calculator calculator;if(!calculator.loadGlobalDefinitions())throw std::runtime_error("Definitions unavailable");
#ifdef LOCAL_CHECKPOINT
 registerQuantumSuperoperators(calculator);
#endif
 eo.approximation=APPROXIMATION_EXACT;
 equal("qunvec(qmul(qlindblad([0,exp(i*x);0,0]),qvec([0,0;0,1])),2)","[1,0;0,-1]");

 equal("qvec([1,2,3;4,5,6])","[1;4;2;5;3;6]");
 equal("qvec([1,i,3])","[1;i;3]");
 equal("qunvec([1;4;2;5;3;6],2)","[1,2,3;4,5,6]");
 equal("qpaulivec([0,-i;i,0])","[0;0;sqrt(2);0]");
 equal("qunpaulivec([0;0;sqrt(2);0])","[0,-i;i,0]");
 equal("qunvec(qmul(qsprepost([0,-i;i,0],[1,0;0,i]),qvec([0,1;1,0])),2)","[-i,0;0,-1]");
 equal("qunvec(qmul(qspre([1,2;3,4]),qvec([i,1;2,3])),2)","[i+4,7;3i+8,15]");
 equal("qunvec(qmul(qspost([1,0;0,i]),qvec([i,1;2,3])),2)","[i,i;2,3i]");
 equal("qunvec(qmul(qlindblad([0,i;0,0]),qvec([0,0;0,1])),2)","[1,0;0,-1]");
 equal("qunvec(qmul(qliouvillianclosed([1,0;0,-1]),qvec([1,1;1,1]/2)),2)","[0,-i;i,0]");
 equal("qunvec(qmul(qliouvillian([0,0;0,0],vector([0,1;0,0])),qvec([0,0;0,1])),2)","[1,0;0,-1]");
 equal("qunvec(qmul(qsprepost([1,2,3;4,5,6],[1,0,i,2;0,1,3,4]),qvec([1,2;3,4;5,6])),2)","[22,28,84+22i,156;49,64,192+49i,354]");
 for(unsigned row=0;row<4;++row)for(unsigned column=0;column<4;++column) {
  std::string matrix="qmul(qbasis("+std::to_string(row)+",4),qdag(qbasis("+std::to_string(column)+",4)))*i";
  equal("qunpaulivec(qpaulivec("+matrix+"))",matrix);
 }
 for(const auto &expression:{"qunvec([1;2;3],2)","qpaulivec(identity(3))","qunpaulivec([1;2;3])","qspre([1;2])","qlindblad([1;0])","qliouvillianclosed([0,1;0,0])","qliouvillian(identity(2),vector(identity(3)))"}) {
  while(calculator.message())calculator.nextMessage();
  calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid superoperator accepted: ")+expression);
  ++checks;
 }
 std::cout<<"PASS: "<<checks<<" quantum superoperator checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
