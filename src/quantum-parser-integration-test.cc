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
 equal(R"(quantum: \sum_{a_0=0}^{3}{a_0})","6");
 equal(R"(quantum: \sum_{a_{10}=0}^{3}{a_{10}^2})","14");
 equal(R"(quantum: \sum_{a_0=0}^{1}{\sum_{a_1=0}^{1}{a_0+a_1}})","4");
 equal(R"(quantum: \frac{1}{2}\sum_{a_0=0}^{1}{\sum_{a_1=0}^{1}{exp(2*pi*i*a_0/4)basis(2*a_1+a_0,4)}})","[1;i;1;i]/2");
 equal(R"(quantum: \prod_{a_0=1}^{3}{a_0})","6");
 equal(R"(quantum: \sum_{a_0=0}^{2}{a_0+\sum_{a_0=0}^{1}{a_0}})","6");
 equal(R"(quantum: \sum_{a_0=0}^{2}{\sum_{a_1=0}^{a_0}{a_1}})","4");
 equal(R"(quantum: \sum_{a_0=0}^{1}{|a_0>_2})","[1;1]");
 equal(R"(quantum: \sum_{\alpha_0=0}^{3}{\alpha_0})","6");
 equal(R"(quantum: \sum_{qsumindex_0=0}^{1}{\sum_{a_0=0}^{1}{qsumindex_0+a_0}})","4");
 equal(R"(quantum: \sum_{a_0=0}^{2}{\sum_{a_0=0}^{a_0}{a_0}})","4");
 equal(R"(quantum: \sum_{a_0=0}^{1}{\sum_{a_01=0}^{1}{a_0+a_01}})","4");
 equal(R"(quantum: \sum_{a_0=0}^{2}{a_0+sum(a_0,0,1,a_0)})","6");
 equal(R"(quantum: norm((\bigotimes_{a_0=0}^{1}{Ry(a_0*pi)})|00>-|01>))","0");
 equal(R"(quantum: \sum_{a_0=0}^{2}{a_0+sum(a_0,0,1,(a_0))})","6");
 equal(R"(quantum: \sum_{qboundindex_0=0}^{1}{\sum_{a_0=0}^{1}{qboundindex_0+a_0}})","4");
 equal(R"(quantum: \sum_{a_0=0}^{1}{|sum(b_0,0,a_0,b_0)>_4})","[1;1;0;0]");
 equal(R"(quantum: \sum_{a_0=0}^{1}{a_0+<1|phase_function(a_0,1,a_0)|1>})","-1");
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
 for(const auto &expression:{"quantum: |0","quantum: <0|H|", "quantum: |0> +",
     R"(quantum: \sum_{0_a=0}^{2}{0_a})",R"(quantum: \sum_{a_0+1=0}^{2}{a_0})"}) {
  while(calculator.message())calculator.nextMessage();
  MathStructure value=calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Malformed quantum syntax accepted: ")+expression);
  ++checks;
 }
 std::cout<<"PASS: "<<checks<<" parser integration checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
