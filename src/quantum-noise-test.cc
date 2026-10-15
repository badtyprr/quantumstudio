// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumNoise.h"
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
 registerQuantumNoise(calculator);
#endif
 eo.approximation=APPROXIMATION_EXACT;
 equal("qchannel([0,0;0,1],qamplitudedamping(3/4))","[3/4,0;0,1/4]");
 equal("qchannel([1,-i;i,1]/2,qphasedamping(3/4))","[1/2,-i/4;i/4,1/2]");
 equal("qchannel([1,-i;i,1]/2,qdepolarizing(1))","identity(2)/2");
 equal("qchannel([1,0;0,0],qdepolarizing(4/3))","[1/3,0;0,2/3]");
 equal("qchannel([1,-i;i,1]/2,qcombineddamping(1/4,1/2,1/4))","[9/16,-i/4;i/4,7/16]");
 equal("qchannel([0,0;0,1],qthermalrelaxation(1,2,ln(2),0))","[1/2,0;0,1/2]");
 equal("qchannel([1,-i;i,1]/2,qthermalrelaxation(infinity,infinity,5,1/4))","[1,-i;i,1]/2");
 equal("qchannel([1,-i;i,1]/2,qthermalrelaxation(1,1,0,1/4))","[1,-i;i,1]/2");
 equal("qchannel([1,0,0;0,2,0;0,0,3],vector([1,0,0;0,1,0]))","[1,0;0,2]");
 equal("qchannel(1,vector([1;0]))","[1,0;0,0]");
 for(unsigned rate=0;rate<=4;++rate)for(unsigned population=0;population<=4;++population) {
  std::string gamma=std::to_string(rate)+"/4",p=std::to_string(population)+"/4",ground="("+gamma+")*(1-"+p+")";
  equal("qchannel([0,0;0,1],qgeneralizeddamping("+gamma+","+p+"))","["+ground+",0;0,1-("+ground+")]");
 }
 for(const auto &expression:{"qamplitudedamping(-1/10)","qphasedamping(2)","qdepolarizing(3/2)","qgeneralizeddamping(1/2,2)","qcombineddamping(3/4,1/2,0)","qthermalrelaxation(1,3,1,0)","qthermalrelaxation(0,1,1,0)","qthermalrelaxation(1,1,-1,0)","qthermalrelaxation(1,1,infinity,0)","qchannel([1,0;0,1],vector([1;0]))"}) {
  while(calculator.message())calculator.nextMessage();
  calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid noise operation accepted: ")+expression);
  ++checks;
 }
 std::cout<<"PASS: "<<checks<<" quantum noise checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
