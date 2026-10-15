// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumGeometry.h"
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
 registerQuantumGeometry(calculator);
#endif
 eo.approximation=APPROXIMATION_EXACT;
 equal("qbloch([1;0])","[0;0;1]");equal("qbloch([0;1])","[0;0;-1]");
 equal("qbloch([1;1])","[1;0;0]");equal("qbloch([1;-1])","[-1;0;0]");
 equal("qbloch([1;i])","[0;1;0]");equal("qbloch([1;-i])","[0;-1;0]");
 equal("qbloch([3,0;0,1])","[0;0;1/2]");
 equal("qblochsub([1;0;0;1],0)","[0;0;0]");
 equal("qblochsub(qdensity([1;0;0;1]),1)","[0;0;0]");
 equal("qreflection([3;4i])","[7,24i;-24i,-7]/25");
 equal("qphasereflection([1;0],pi/2)","[i,0;0,1]");
 for(unsigned state=0;state<8;++state)for(unsigned wire=0;wire<3;++wire)
  equal("qblochsub(qbasis("+std::to_string(state)+",8),"+std::to_string(wire)+")",(state&(1U<<(2-wire))) ? "[0;0;-1]" : "[0;0;1]");
 for(const auto &state:{"[1;0]","[1;i]","[3;4i]","[1;2;3]"}) {
  std::string r="qreflection("+std::string(state)+")";unsigned n=std::string(state)=="[1;2;3]" ? 3 : 2;
  equal("qmul("+r+","+r+")","identity("+std::to_string(n)+")");
  equal("qmul("+r+","+state+")","-"+std::string(state));
 }
 for(const auto &expression:{"qbloch([0;0])","qbloch([1,1;0,1])","qbloch([2,0;0,-1])","qblochsub([1;0],1)","qreflection([0;0])","qreflection([1,0;0,1])","qphasereflection([1;0],i)","qphasereflection([1;0],infinity)"}) {
  while(calculator.message())calculator.nextMessage();
  calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid geometry operation accepted: ")+expression);
  ++checks;
 }
 std::cout<<"PASS: "<<checks<<" quantum geometry checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
