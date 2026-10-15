// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumReset.h"
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
 registerQuantumReset(calculator);
#endif
 eo.approximation=APPROXIMATION_EXACT;
 std::string bell="[1;0;0;1]/sqrt(2)",mixed="[1,0,0,0;0,0,0,0;0,0,0,0;0,0,0,1]/2";
 equal("qdephase("+bell+",0)",mixed);
 equal("qdephaseall("+bell+")",mixed);
 equal("qreset("+bell+",0)","[1,0,0,0;0,1,0,0;0,0,0,0;0,0,0,0]/2");
 equal("qresetall("+bell+")","qdensity(qbasis(0,4))");
 equal("qfeedforward("+bell+",0,1,[0,1;1,0],1)","[1,0,0,0;0,0,0,0;0,0,1,0;0,0,0,0]/2");
 equal("qindexedchannel(qdensity("+bell+"),vector([1,0;0,0],[0,1;0,0]),1)","[1,0,0,0;0,0,0,0;0,0,1,0;0,0,0,0]/2");
 equal("qdephase([1;i],0)","identity(2)");
 equal("qresetall([1;i])","[2,0;0,0]");
 for(unsigned state=0;state<8;++state)for(unsigned wire=0;wire<3;++wire) {
  std::string ket="qbasis("+std::to_string(state)+",8)",index=std::to_string(wire);
  equal("qreset("+ket+","+index+")","qdensity(qbasis("+std::to_string(state&~(1U<<(2-wire)))+",8))");
  equal("qdephase("+ket+","+index+")","qdensity("+ket+")");
 }
 // Ordered measured bits [2,0] make |101> outcome 3; correction flips the middle bit.
 equal("qfeedforward(qbasis(5,8),[2,0],3,[0,1;1,0],1)","qdensity(qbasis(7,8))");
 equal("qfeedforward(qbasis(5,8),[2,0],1,[0,1;1,0],1)","qdensity(qbasis(5,8))");
 for(const auto &expression:{"qreset([1;0;0],0)","qreset([1;0],1)","qdephase([1;0],[0,0])","qfeedforward([1;0],0,2,[0,1;1,0],0)","qfeedforward([1;0],0,0,[0,1;1,0],1)","qindexedchannel([1;0],vector([1,0;0,1]),0)","qindexedchannel(identity(2),vector([1,0;0,1]),1)"}) {
  while(calculator.message())calculator.nextMessage();
  calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid reset operation accepted: ")+expression);
  ++checks;
 }
 std::cout<<"PASS: "<<checks<<" quantum reset/feedforward checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
