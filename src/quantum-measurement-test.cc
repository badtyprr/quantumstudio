// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumMeasurement.h"
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
 registerQuantumMeasurement(calculator);
#endif
 eo.approximation=APPROXIMATION_EXACT;
 equal("qprobs([3;4i])","[9/25;16/25]");
 equal("qprobs([3,0;0,1])","[3/4;1/4]");
 equal("qpurity([3;4i])","1");equal("qpurity([3,0;0,1])","5/8");
 equal("qexpect([0,-i;i,0],[1;i])","2");
 equal("qborn([0,-i;i,0],[1;i])","1");
 equal("qborn([1,0;0,0],[3,0;0,1])","3/4");
 equal("qvariance([1,0;0,-1],[1;1])","1");
 equal("qvariance([1,0;0,-1],[3,0;0,1])","3/4");
 equal("qpostselect([1,0;0,0],[3;4i])","[1;0]");
 equal("qpostselect([1,0;0,0],[3,0;0,1])","[1,0;0,0]");
 equal("qpostselect([1/2,-i/2;i/2,1/2],[1;0])","[1;i]/sqrt(2)");
 equal("qprobsub([1;0;0;1],0)","[1/2;1/2]");
 for(unsigned a=0;a<3;++a)for(unsigned b=0;b<3;++b)if(a!=b)for(unsigned state=0;state<8;++state) {
  unsigned outcome=(((state>>(2-a))&1)<<1)|((state>>(2-b))&1);
  std::string ket="qbasis("+std::to_string(state)+",8)", indices="["+std::to_string(a)+","+std::to_string(b)+"]";
  equal("qprobsub("+ket+","+indices+")","qbasis("+std::to_string(outcome)+",4)");
 }
 for(const auto &expression:{"qprobs(1)","qprobs([0;0])","qprobs([1,2,3;4,5,6])","qprobsub([1;0;0;0],[0,0])","qprobsub([1;0],1)","qpurity([0;0])","qvariance([0,1;0,0],[1;0])","qpostselect([1,0;0,1/2],[1;0])","qpostselect([1,0;0,0],[0;1])","qborn([1,0;0,0],[0;0])","qexpect([1,0;0,1],[1;0;0])"}) {
  while(calculator.message())calculator.nextMessage();
  calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid measurement accepted: ")+expression);
  ++checks;
 }
 std::cout<<"PASS: "<<checks<<" quantum measurement checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
