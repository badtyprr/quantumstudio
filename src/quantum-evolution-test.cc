// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumEvolution.h"
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
 registerQuantumEvolution(calculator);
#endif
 eo.approximation=APPROXIMATION_EXACT;
 equal("qevolution([1,0;0,-1],pi/2)","[-i,0;0,i]");
 equal("qevolution([0,1;1,0],pi/2)","[0,-i;-i,0]");
 equal("qevolution([0,-i;i,0],pi/2)","[0,-1;1,0]");
 equal("qevolution([1,i;-i,2],0)","identity(2)");
 equal("qevolution([0,1;1,0],-pi/2)","[0,i;i,0]");
 equal("qevolution(identity(3),pi)","-identity(3)");
 equal("qevolution([1,i;-i,1],pi/2)","[0,-i;i,0]");
 for(const auto &expression:{"qevolution([1,2;0,1],1)","qevolution([i,0;0,1],1)","qevolution(identity(2),i)","qevolution(identity(2),[1,2])","qevolution([1,2,3;4,5,6],1)","qevolution(1,1)","qevolution(identity(65),0)","qevolution(identity(2),infinity)"}) {
  while(calculator.message())calculator.nextMessage();
  calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid evolution accepted: ")+expression);
  ++checks;
 }
 std::cout<<"PASS: "<<checks<<" Hamiltonian evolution checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
