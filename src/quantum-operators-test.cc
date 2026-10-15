// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumOperators.h"
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
 registerQuantumOperators(calculator);
#endif
 eo.approximation=APPROXIMATION_EXACT;
 equal("qjx(1/2)","[0,1;1,0]/2");equal("qjy(1/2)","[0,-i;i,0]/2");equal("qjz(1/2)","[1,0;0,-1]/2");
 for(unsigned twice=1;twice<=6;++twice) {
  std::string j=std::to_string(twice)+"/2",x="qjx("+j+")",y="qjy("+j+")",z="qjz("+j+")";
  equal("qcomm("+x+","+y+")","i*"+z);
  equal("qjplus("+j+")",x+"+i*"+y);
  equal("qjminus("+j+")",x+"-i*"+y);
  equal(x+"^2+"+y+"^2+"+z+"^2","("+j+")*(1+"+j+")*identity("+std::to_string(twice+1)+")");
 }
 equal("qcreate(4)","qdag(qdestroy(4))");
 equal("qmul(qcreate(4),qdestroy(4))","qnumberop(4)");
 equal("qcomm(qdestroy(4),qcreate(4))","[1,0,0,0;0,1,0,0;0,0,1,0;0,0,0,-3]");
 equal("qmul(qdestroy(4),qbasis(2,4))","sqrt(2)*qbasis(1,4)");
 equal("qmul(qfdestroy(3,1),qbasis(6,8))","-qbasis(4,8)");
 for(unsigned a=0;a<3;++a)for(unsigned b=0;b<3;++b) {
  std::string first="qfdestroy(3,"+std::to_string(a)+")",second="qfdestroy(3,"+std::to_string(b)+")",create="qfcreate(3,"+std::to_string(b)+")";
  equal("qanticomm("+first+","+second+")","0*identity(8)");
  equal("qanticomm("+first+","+create+")",a==b ? "identity(8)" : "0*identity(8)");
 }
 equal("qspinadd(qjz(1/2),3)","[7/2,0;0,5/2]");equal("qspinadd(3,qjz(1/2))","[7/2,0;0,5/2]");
 for(const auto &expression:{"qjx(1/3)","qjy(32)","qjplus(-1/2)","qfdestroy(3,3)","qfcreate(10,0)","qdestroy(1)","qcreate(513)","qnumberop(3/2)","qspinadd([1;2],1)"}) {
  while(calculator.message())calculator.nextMessage();
  calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid operator accepted: ")+expression);
  ++checks;
 }
 std::cout<<"PASS: "<<checks<<" quantum operator checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
