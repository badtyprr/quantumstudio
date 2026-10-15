// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumMatrixPower.h"
#include <cmath>
#include <iostream>
#include <stdexcept>
static unsigned checks=0;
static void expectClose(MathStructure actual,MathStructure expected,const EvaluationOptions &eo) {
 actual.eval(eo);expected.eval(eo);
 if(actual.isMatrix() && expected.isMatrix()) {
  if(actual.rows()!=expected.rows() || actual.columns()!=expected.columns())throw std::runtime_error("Shape mismatch");
  for(size_t r=1;r<=actual.rows();++r)for(size_t c=1;c<=actual.columns();++c)expectClose(*actual.getElement(r,c),*expected.getElement(r,c),eo);
  return;
 }
 actual-=expected;actual.eval(eo);
 if(!actual.isNumber())throw std::runtime_error("Nonnumeric difference");
 Number error=actual.number();error.abs();double value=error.floatValue();
 if(!std::isfinite(value) || value>1e-12)throw std::runtime_error("Matrix power mismatch");
 ++checks;
}
int main(){try {
 Calculator calculator;if(!calculator.loadGlobalDefinitions())throw std::runtime_error("Definitions unavailable");
#ifdef LOCAL_CHECKPOINT
 registerQuantumMatrixPower(calculator);
#endif
 calculator.setPrecision(60);EvaluationOptions eo;eo.approximation=APPROXIMATION_APPROXIMATE;
 for(const auto &t:{std::pair<const char *,const char *>("qpower(4,1/2)","2"),
 {"qsqrt([4,0;0,9])","[2,0;0,3]"},
 {"qpower([1,2;0,1],0)","[1,0;0,1]"},
 {"qpower([1,2;0,1],-1)","[1,-2;0,1]"},
 {"qpower([1,2;0,1],3)","[1,6;0,1]"},
 {"qsqrt([0,1;1,0])","[(1+i)/2,(1-i)/2;(1-i)/2,(1+i)/2]"},
 {"qlogm([1,0;0,-1])","[0,0;0,i*pi]"},
 {"qlogm([0,1;1,0])","[i*pi/2,-i*pi/2;-i*pi/2,i*pi/2]"},
 {"qsqrt([5,4;4,5])","[2,1;1,2]"},
 {"qsqrt([1,2,3;2,4,6;3,6,9])","[1,2,3;2,4,6;3,6,9]/sqrt(14)"},
 {"qlogm([5,4;4,5])","[ln(9)/2,ln(9)/2;ln(9)/2,ln(9)/2]"},
 {"qpower([0,-1;1,0],1/2)","[1/sqrt(2),-1/sqrt(2);1/sqrt(2),1/sqrt(2)]"}})
  expectClose(calculator.calculate(t.first,eo),calculator.calculate(t.second,eo),eo);
 // Non-diagonal matrices must retain tiny positive eigenvalues in positive powers.
 for(int exponent:{16,28,100,200}) {
  std::string text="qsqrt([2,1,0;1,2,0;0,0,1e-"+std::to_string(exponent)+"] )";
  MathStructure value=calculator.calculate(text,eo),expected=calculator.calculate("1e-"+std::to_string(exponent/2),eo);
  if(!value.isMatrix() || !value.getElement(3,3)->isNumber())throw std::runtime_error("Small eigenvalue result missing");
  Number ratio=value.getElement(3,3)->number();ratio/=expected.number();
  if(!std::isfinite(ratio.floatValue()) || std::abs(ratio.floatValue()-1)>1e-9)throw std::runtime_error("Small eigenvalue erased");
  ++checks;
 }
 for(const auto &expression:{"qlogm([0,0;0,1])","qsqrt([1;2])","qpower([1;2],0)","qlogm([1,2;0,1])"}) {
  while(calculator.message())calculator.nextMessage();
  calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid operation accepted: ")+expression);
  ++checks;
 }
 std::cout<<"PASS: "<<checks<<" matrix power/logarithm checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
