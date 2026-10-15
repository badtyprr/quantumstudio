// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumHellinger.h"
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
 registerQuantumHellinger(calculator);
#endif
 eo.approximation=APPROXIMATION_EXACT;
 for(const char *p:{"[1,0]","[2,3]","[0,4,9]","[1/10,2/10,7/10]"}) {
  std::string a=p;
  equal("qhellingerfidelity("+a+","+a+")","1");
  equal("qhellingerdistance("+a+","+a+")","0");
 }
 equal("qhellingerfidelity([1,0],[0,1])","0");
 equal("qhellingerdistance([1,0],[0,1])","1");
 equal("qhellingerfidelity([1,0],[1,1])","1/2");
 equal("qhellingerdistance([1,0],[1,1])","sqrt(1-1/sqrt(2))");
 equal("qhellingerfidelity([4;9],[16,36])","1");
 equal("qhellingerdistance([4;9],[16,36])","0");
 equal("qhellingerfidelity(2,5)","1");
 equal("qhellingerdistance(2,5)","0");
 equal("qhellingerfidelity([1,4],[4,1])","16/25");
 equal("qhellingerdistance([1,4],[4,1])","1/sqrt(5)");
 equal("qhellingerfidelity([10^-400,1],[1,0])","10^-400/(1+10^-400)");
 equal("qhellingerfidelity([0,1,0],[0,7,0])","1");
 for(const auto &expression:{"qhellingerfidelity([0,0],[1,0])","qhellingerfidelity([-1,2],[1,2])","qhellingerdistance([i,1],[1,2])","qhellingerfidelity([1,2],[1,2,3])","qhellingerdistance([1,2;3,4],[1,2])","qhellingerfidelity([infinity,1],[1,2])","qhellingerdistance([x,1],[1,2])","qhellingerfidelity(vector(),[1])"}) {
  while(calculator.message())calculator.nextMessage();
  calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid distribution accepted: ")+expression);
  ++checks;
 }
 std::cout<<"PASS: "<<checks<<" Hellinger checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
