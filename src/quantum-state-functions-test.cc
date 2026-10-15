// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumStateFunctions.h"
#include <cmath>
#include <iostream>
#include <stdexcept>
int main(){try {
 Calculator calculator;
 if(!calculator.loadGlobalDefinitions())throw std::runtime_error("Definitions unavailable");
#ifdef LOCAL_CHECKPOINT
 // Local extraction validation only; native CI exercises constructor registration.
 registerQuantumStateFunctions(calculator);
#endif
 calculator.setPrecision(60);EvaluationOptions eo;eo.approximation=APPROXIMATION_APPROXIMATE;
 unsigned checks=0;
 for(const auto &test:{std::pair<const char *,const char *>("qrootfidelity([1;0],[1e-200;1])","1e-200"),
 {"qfidelity([1;0],[1e-200;1])","1e-400"},
 {"qentropy([1,0;0,1])","1"},{"qentropybase([1,0;0,1],4)","1/2"},
 {"qtracedistance([1;0],[0;1])","1"},
 {"qtracenorm([3,0;0,4])","7"},{"qspectralnorm([3,0;0,4])","4"},
 {"qfrobeniusnorm([3,0;0,4])","5"},{"qschatten([3,0;0,4],2)","5"}}) {
  MathStructure value=calculator.calculate(test.first,eo),expected=calculator.calculate(test.second,eo);
  if(!value.isNumber() || !expected.isNumber())throw std::runtime_error(std::string("Nonnumeric result: ")+test.first);
  Number ratio=value.number();if(!ratio.divide(expected.number()) || !std::isfinite(ratio.floatValue()) || std::abs(ratio.floatValue()-1)>1e-9)throw std::runtime_error(std::string("Incorrect result: ")+test.first);
  ++checks;
 }
 for(const auto &expression:{"qschmidt([1;0;0;1],0)","qschmidtdim([1;0;0;0;1;0],0,[2,3])"}) {
  MathStructure value=calculator.calculate(expression,eo);
  if(!value.isMatrix() || value.rows()!=2 || value.columns()!=1)throw std::runtime_error("Schmidt shape mismatch");
  for(size_t k=1;k<=2;++k)if(std::abs(value.getElement(k,1)->number().floatValue()-1/std::sqrt(2.0))>1e-9)throw std::runtime_error("Schmidt value mismatch");
  ++checks;
 }
 for(const auto &expression:{"qentropy()","qentropybase([1,0;0,1],1)","qrootfidelity([0;0],[1;0])","qschmidt([1;0;0;1],2)","qschmidtdim([1;0;0;1],0,[2,3])","qspectralnorm(infinity)"}) {
  while(calculator.message())calculator.nextMessage();
  MathStructure value=calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()) {if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error || value.isNumber())throw std::runtime_error(std::string("Invalid call accepted: ")+expression);
  ++checks;
 }
 std::cout<<"PASS: "<<checks<<" registered state-function checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
