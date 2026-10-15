// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumMatrixExp.h"
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
 if(!std::isfinite(value) || value>1e-12)throw std::runtime_error("Exponential mismatch");
 ++checks;
}
int main(){try {
 Calculator calculator;if(!calculator.loadGlobalDefinitions())throw std::runtime_error("Definitions unavailable");
#ifdef LOCAL_CHECKPOINT
 registerQuantumMatrixExp(calculator);
#endif
 calculator.setPrecision(60);EvaluationOptions eo;eo.approximation=APPROXIMATION_APPROXIMATE;
 for(const auto &t:{std::pair<const char *,const char *>("qexp(2)","exp(2)"),
 {"qsinhc(0)","1"},{"qsinhc(2)","sinh(2)/2"},
 {"qexp([1,0;0,-1])","[exp(1),0;0,exp(-1)]"},
 {"qexp([0,1;0,0])","[1,1;0,1]"},
 {"qexp([0,-i;-i,0])","[cos(1),-i*sin(1);-i*sin(1),cos(1)]"},
 {"qexp([0,1,0;0,0,1;0,0,0])","[1,1,1/2;0,1,1;0,0,1]"},
 {"qexp([0,-1,0;1,0,0;0,0,0])","[cos(1),-sin(1),0;sin(1),cos(1),0;0,0,1]"}})
  expectClose(calculator.calculate(t.first,eo),calculator.calculate(t.second,eo),eo);
 // Dimension >16 bypasses the exact quadratic reduction. N^2=0 gives exp(N)=I+N.
 MathStructure a,b,out;a.clearMatrix();a.resizeMatrix(17,17,m_zero);*a.getElement(1,17)=Number(3,2);
 b.setToIdentityMatrix(17);*b.getElement(1,17)=Number(3,2);
 if(!quantumMatrixExp(out,a,eo))throw std::runtime_error("Numerical path rejected");
 expectClose(out,b,eo);
 for(const auto &expression:{"qexp([1;2])","qexp([1,2])"}) {
  while(calculator.message())calculator.nextMessage();
  calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error("Invalid dimensions accepted");
  ++checks;
 }
 a.clearMatrix();a.resizeMatrix(65,65,m_zero);if(quantumMatrixExp(out,a,eo))throw std::runtime_error("Oversized matrix accepted");
  ++checks;
 std::cout<<"PASS: "<<checks<<" matrix exponential checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
