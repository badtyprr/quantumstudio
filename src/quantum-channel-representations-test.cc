// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumChannelRepresentations.h"
#include <iostream>
#include <stdexcept>
static unsigned checks=0;
static EvaluationOptions eo;
static void equal(const std::string &expression,const std::string &expected) {
 MathStructure value=CALCULATOR->calculate("("+expression+")==("+expected+")",eo);
 if(!value.isNumber() || !value.number().isOne()){std::cerr<<CALCULATOR->calculate(expression,eo).print()<<" vs "<<CALCULATOR->calculate(expected,eo).print()<<"\n";}
 if(!value.isNumber() || !value.number().isOne())throw std::runtime_error("Mismatch: "+expression+" vs "+expected);
 ++checks;
}
int main(){try {
 Calculator calculator;if(!calculator.loadGlobalDefinitions())throw std::runtime_error("Definitions unavailable");
#ifdef LOCAL_CHECKPOINT
 registerQuantumChannelRepresentations(calculator);
#endif
 eo.approximation=APPROXIMATION_EXACT;
 equal("qsuperop(vector(identity(2)))","identity(4)");
 equal("qchoi(vector(identity(2)))","qdensity([1;0;0;1])");
 equal("qchi(vector(identity(2)))","[2,0,0,0;0,0,0,0;0,0,0,0;0,0,0,0]");
 equal("qptm(vector(identity(2)))","identity(4)");
 equal("qsuperop(vector([1,0;0,i]))","[1,0,0,0;0,i,0,0;0,0,-i,0;0,0,0,1]");
 equal("qptm(vector([1,0;0,i]))","[1,0,0,0;0,0,-1,0;0,1,0,0;0,0,0,1]");
 equal("qchi(vector([1,0;0,i]))","[1,0,0,i;0,0,0,0;0,0,0,0;-i,0,0,1]");
 equal("qsuperop(vector([1,0;0,1/2],[0,sqrt(3)/2;0,0]))","[1,0,0,3/4;0,1/2,0,0;0,0,1/2,0;0,0,0,1/4]");
 equal("qptm(vector([1,0;0,1/2],[0,sqrt(3)/2;0,0]))","[1,0,0,0;0,1/2,0,0;0,0,1/2,0;3/4,0,0,1/4]");
 equal("qchoi(vector([1,0,0;0,1,0]))","qdensity([1;0;0;1;0;0])");
 equal("qsuperop(vector([1,i]))","[1,i,-i,1]");
 equal("qchoi(vector([1;i]))","[1,-i;i,1]");
 for(const auto &matrix:{"[1,i;2,3]","[0,1;-i,0]","[1,2,3;4,i,6]"}) {
  std::string k=matrix;
  equal("qsuperop(vector("+k+"))","qtensor(qconj("+k+"),"+k+")");
 }
 equal("qsuperop(vector([1;i;2]))","[1;i;2;-i;1;-2i;2;2i;4]");
 equal("qptm(vector(identity(4)))","identity(16)");
 for(const auto &expression:{"qchoi(vector())","qptm(vector(identity(3)))","qchi(vector([1,0,0;0,1,0]))","qsuperop(vector(identity(2),identity(3)))","qchoi(vector(identity(32)))"}) {
  while(calculator.message())calculator.nextMessage();
  calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid channel conversion accepted: ")+expression);
  ++checks;
 }
 std::cout<<"PASS: "<<checks<<" quantum channel representation checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
