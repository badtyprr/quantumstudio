// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumAlgebra.h"
#include "Variable.h"
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
 registerQuantumAlgebra(calculator);
#endif
 eo.approximation=APPROXIMATION_EXACT;
 equal("qketstate([1;i])","[1;i]");
 equal("qketstate([3;4])","[3;4]");
 MathStructure oversized;oversized.clearMatrix();oversized.resizeMatrix(1025,1,m_zero);
 calculator.addVariable(new KnownVariable("","oversizedstate",oversized));
 for(const char *expression:{"qketstate(3)","qketstate([1,0])","qketstate(identity(2))","qketstate(oversizedstate)"}) {
  while(calculator.message())calculator.nextMessage();
  calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid named state accepted: ")+expression);
  ++checks;
 }
 equal("qconj([1;i;2])","[1;-i;2]");
 equal("qconj([1,i,2])","[1,-i,2]");
 equal("qconj(2+3i)","2-3i");
 equal("qconj([1,i,2;3,4i,5])","[1,-i,2;3,-4i,5]");
 equal("qconj(qconj([1;i;2]))","[1;i;2]");
 equal("qdag([1,i])","[1;-i]");equal("qconj([1,i;2,3])","[1,-i;2,3]");
 equal("qtranspose([1,2;3,4])","[1,3;2,4]");
 equal("qmul(qdag([1;i]),[1;i])","2");
 equal("qadjacent([1;-1],[1;0])","[1;0;-1;0]");
 equal("qadjacent([1,i],[1,-1])","[1,-1,i,-i]");
 equal("qadjacent([1,0;0,1],[2;3])","[2;3]");
 equal("qnorm([3;4])","5");equal("qnormalize([3;4])","[3/5;4/5]");
 equal("qdensity([1;i])","[1,-i;i,1]");equal("qtrace([1,2;3,4])","5");
 equal("qtensor([1;0],[0;1])","[0;1;0;0]");
 equal("qtensorpow([0;1],3)","[0;0;0;0;0;0;0;1]");
 equal("qdirectsum([1,0;0,1],[2,0;0,2])","[1,0,0,0;0,1,0,0;0,0,2,0;0,0,0,2]");
 equal("qcontrolled([0,1;1,0])","[1,0,0,0;0,1,0,0;0,0,0,1;0,0,1,0]");
 equal("qcontrol([0,1;1,0],1,0)","[0,1,0,0;1,0,0,0;0,0,1,0;0,0,0,1]");
 equal("qcontrolpattern([0,1;1,0],1,1,1)","qcontrolled([0,1;1,0])");
 equal("qcomm([0,1;1,0],[0,-i;i,0])","[2i,0;0,-2i]");
 equal("qanticomm([0,1;1,0],[0,-i;i,0])","[0,0;0,0]");
 for(unsigned i=0;i<8;++i)for(unsigned j=0;j<8;++j)
  equal("qmul(qdag(qbasis("+std::to_string(i)+",8)),qbasis("+std::to_string(j)+",8))",i==j ? "1" : "0");
 for(const auto &expression:{"qadjacent([1,0;0,1],[1;2;3])","qadjacent(qbasis(0,64),qbasis(0,64))","qbasis(8,8)","qbasis(0,1025)","qnormalize([0;0])","qcontrol([0,1;1,0],9,0)","qcontrolpattern([0,1;1,0],1,1,2)","qtrace([1;2])","qmul([1,0;0,1],[1;2;3])"}) {
  while(calculator.message())calculator.nextMessage();
  calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid algebra accepted: ")+expression);
  ++checks;
 }
 std::cout<<"PASS: "<<checks<<" quantum algebra checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
