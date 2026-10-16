// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumGates.h"
#include <iostream>
#include <cmath>
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
 registerQuantumGates(calculator);
#endif
 eo.approximation=APPROXIMATION_EXACT;
 for(bool approximate:{false,true})for(const char *name:{"qft","qfourier"}) {
  EvaluationOptions symbolicOptions=eo;symbolicOptions.approximation=approximate ? APPROXIMATION_APPROXIMATE : APPROXIMATION_EXACT;
  MathStructure symbol(std::string("dimension_parameter"),true),expression;
  expression.set(calculator.getFunction(name),&symbol,NULL);
  while(calculator.message())calculator.nextMessage();
  expression.eval(symbolicOptions);
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)throw std::runtime_error("Symbolic Fourier dimension rejected");calculator.nextMessage();}
  if(!expression.isFunction() || expression.function()!=calculator.getFunction(name) || !expression.containsUnknowns())throw std::runtime_error("Symbolic Fourier operator was lost");++checks;
  MathStructure resolved=expression;resolved.replace(symbol,MathStructure(2));resolved.eval(symbolicOptions);
  MathStructure expected=calculator.calculate(std::string(name)+"(2)",symbolicOptions);
  if(approximate) {
   if(!resolved.isMatrix() || resolved.rows()!=expected.rows() || resolved.columns()!=expected.columns())throw std::runtime_error("Substituted Fourier shape differs");
   for(size_t row=1;row<=resolved.rows();++row)for(size_t col=1;col<=resolved.columns();++col) {
    const MathStructure &actual=*resolved.getElement(row,col), &reference=*expected.getElement(row,col);
    if(!actual.isNumber() || !reference.isNumber())throw std::runtime_error("Substituted Fourier entry is not numeric");
    Number difference=actual.number();difference.subtract(reference.number());difference.abs();
    if(!std::isfinite(difference.floatValue()) || difference.floatValue()>1e-10)throw std::runtime_error("Substituted Fourier entry differs");
   }
  } else {
   resolved.transform(COMPARISON_EQUALS,expected);resolved.eval(symbolicOptions);
   if(!resolved.isNumber() || !resolved.number().isOne())throw std::runtime_error("Substituted exact Fourier operator differs");
  }
  ++checks;
  expression.replace(symbol,MathStructure(0));expression.eval(symbolicOptions);bool invalid=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)invalid=true;calculator.nextMessage();}
  if(!invalid)throw std::runtime_error("Invalid substituted Fourier dimension accepted");++checks;
 }

 equal("qft(1)","[1,1;1,-1]/sqrt(2)");
 equal("qfourier(4)","[1,1,1,1;1,i,-1,-i;1,-1,1,-1;1,-i,-1,i]/2");
 equal("qft(2)","qfourier(4)");
 equal("qfourier(1)","matrix(1,1,[1])");
 equal("qclock(4)","[1,0,0,0;0,i,0,0;0,0,-1,0;0,0,0,-i]");
 equal("qshift(3)","[0,0,1;1,0,0;0,1,0]");
 equal("qphaseoracle(2,[0,3])","[-1,0,0,0;0,1,0,0;0,0,1,0;0,0,0,-1]");
 equal("qmul(qdiffusion(2),qmul(qphaseoracle(2,3),[1;1;1;1]/2))","[0;0;0;1]");
 for(unsigned state=0;state<8;++state)
  equal("qmul(qmodmul(2,5),qbasis("+std::to_string(state)+",8))","qbasis("+std::to_string(state<5 ? (2*state)%5 : state)+",8)");
 for(unsigned control=0;control<2;++control)for(unsigned target=0;target<3;++target)
  equal("qmul(qsumgate(2,3),qbasis("+std::to_string(3*control+target)+",6))","qbasis("+std::to_string(3*control+(target+control)%3)+",6)");
 for(unsigned table=0;table<16;++table)for(unsigned state=0;state<8;++state) {
  std::string entries="[";for(unsigned x=0;x<4;++x){if(x)entries+=",";entries+=std::to_string((table>>x)&1);}entries+="]";
  unsigned x=state>>1,y=state&1,result=2*x+(y^((table>>x)&1));
  equal("qmul(qoracle("+entries+",1),qbasis("+std::to_string(state)+",8))","qbasis("+std::to_string(result)+",8)");
 }
 for(const auto &expression:{"qmodmul(2,4)","qmodmul(1,513)","qoracle([0,2],1)","qoracle([0,1,0],1)","qphaseoracle(2,[0,0])","qphaseoracle(2,4)","qdiffusion(10)","qsumgate(64,64)","qft(7)","qfourier(0)","qshift(65)","qclock(0)"}) {
  while(calculator.message())calculator.nextMessage();
  calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid gate accepted: ")+expression);
  ++checks;
 }
 std::cout<<"PASS: "<<checks<<" quantum gate checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
