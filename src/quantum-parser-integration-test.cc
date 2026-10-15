// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumAlgebra.h"
#include <iostream>
#include <stdexcept>
static unsigned checks=0;
static EvaluationOptions eo;
static void equal(const std::string &expression,const std::string &expected) {
 MathStructure value=CALCULATOR->calculate(expression,eo),reference=CALCULATOR->calculate(expected,eo);
 value.transform(COMPARISON_EQUALS,reference);value.eval(eo);
 if(!value.isNumber() || !value.number().isOne())throw std::runtime_error("Mismatch: "+expression+" vs "+expected);
 ++checks;
}
int main(){try {
 Calculator calculator;if(!calculator.loadGlobalDefinitions())throw std::runtime_error("Definitions unavailable");
#ifdef LOCAL_CHECKPOINT
 registerQuantumAlgebra(calculator);
#endif
 eo.approximation=APPROXIMATION_EXACT;
 equal("quantum: |⟨101|(H⊗H⊗H)|000⟩|^2","1/8");
 equal("quantum: ⟨0|H|0⟩","1/sqrt(2)");
 equal("quantum: norm(|->)","1");
 equal("quantum: |+><+|","[1,1;1,1]/2");
 equal("quantum: <1|X|0>","1");
 equal("  quantum: <0|0>","1");
 equal("\xEF\xBB\xBFquantum: <1|0>","0");
 equal("quantum: \\frac{1}{2}","1/2");
 equal("2+3*4","14");
 equal("sin(pi/2)","1");
 for(const char *input:{"quantum: |->"," quantum: |->"}) {
  std::string expression=input,to;
  if(calculator.hasToExpression(expression,true) || calculator.hasToExpression(expression,true,eo) || calculator.separateToExpression(expression,to,eo,true,true))throw std::runtime_error("Ket mistaken for conversion");
  if(expression!=input || !to.empty())throw std::runtime_error("Conversion probe changed expression");
  ++checks;
 }
 if(!calculator.hasToExpression("1 m -> cm",true,eo))throw std::runtime_error("Ordinary conversion disabled");
 ++checks;
 for(const auto &expression:{"quantum: |0","quantum: <0|H|", "quantum: |0> +"}) {
  while(calculator.message())calculator.nextMessage();
  MathStructure value=calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Malformed quantum syntax accepted: ")+expression);
  ++checks;
 }
 std::cout<<"PASS: "<<checks<<" parser integration checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
