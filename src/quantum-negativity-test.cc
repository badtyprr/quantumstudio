// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumNegativity.h"
#include "QuantumSubsystem.h"
#include <iostream>
#include <stdexcept>
#include <cmath>
static unsigned checks=0;static EvaluationOptions eo;
static void close(const std::string &expression,const std::string &expected) {
 MathStructure actual=CALCULATOR->calculate(expression,eo),reference=CALCULATOR->calculate(expected,eo);
 if(!actual.isNumber() || !reference.isNumber())throw std::runtime_error("Nonnumeric result: "+expression);
 Number error=actual.number();
 if(reference.isZero())error.abs();
 else {error/=reference.number();error-=1;error.abs();}
 if(!std::isfinite(error.floatValue()) || error.floatValue()>1e-9)throw std::runtime_error("Mismatch: "+expression+" got "+actual.print());
 ++checks;
}
int main(){try {
 Calculator calculator;if(!calculator.loadGlobalDefinitions())throw std::runtime_error("Definitions unavailable");
#ifdef LOCAL_CHECKPOINT
 registerQuantumNegativity(calculator);registerQuantumSubsystem(calculator);
#endif
 calculator.setPrecision(80);eo.approximation=APPROXIMATION_APPROXIMATE;
 close("qnegativity([1;0;0;1],0)","1/2");
 close("qlognegativity([1;0;0;1],0)","1");
 close("qnegativity([1;0;0;0],0)","0");
 close("qnegativitydim([1;0;0;0;1;0],0,[2,3])","1/2");
 close("qlognegativitydim([1;0;0;0;1;0],1,[2,3])","1");
 for(const char *epsilon:{"1e-14","1e-50","1e-150","1e-300"}) {
  std::string e=epsilon,ket="[1;0;0;"+e+"]";
  close("qnegativity("+ket+",0)",e+"/(1+("+e+")^2)");
  close("qlognegativity("+ket+",0)","2*("+e+")/ln(2)");
  close("qnegativity(qdensity("+ket+"),0)",e+"/(1+("+e+")^2)");
  close("qlognegativity(qdensity("+ket+"),0)","2*("+e+")/ln(2)");
 }
 close("qnegativity(identity(4),0)","0");
 close("qnegativity(qdensity([1;0;0;1]),0)","1/2");
 close("qnegativity(qdensity([1;0;0;1e-14]),0)","1e-14/(1+1e-28)");
 close("qnegativity(qdensity([1;1;1;-1]),0)","1/2");
 close("qlognegativity(qdensity([1;1;1;-1]),0)","1");
 close("qnegativity(qdensity([1;1;1;1]),0)","0");
 close("qnegativity(qdensity([1;0;0;1])/4+identity(4)/8,0)","1/8");
 close("qnegativity(qdensity([1;0;0;1])/6+identity(4)/6,0)","0");
 close("qnegativitydim(qdensity([1;0;0;0;1;0]),0,[2,3])","1/2");
 for(const auto &expression:{"qnegativity([0;0;0;0],0)","qnegativity([1;0;0;1],2)","qnegativitydim([1;0;0;1],0,[2,3])","qnegativity([1,1;0,1],0)","qnegativity([-1,0;0,2],0)","qnegativity([1;infinity],0)","qnegativity(identity(65),0)"}) {
  while(calculator.message())calculator.nextMessage();
  calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid negativity accepted: ")+expression);
  ++checks;
 }
 std::cout<<"PASS: "<<checks<<" negativity checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
