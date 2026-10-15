// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumBinary.h"
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
 registerQuantumBinary(calculator);
#endif
 eo.approximation=APPROXIMATION_EXACT;
 equal("qbits(5,4)","[0,1,0,1]");
 equal("qbitvalue([1;0;1])","5");
 equal("qbitxor([1,0,1],[1;1;0])","[0,1,1]");
 equal("qbitdot([1,1,0],[1,1,1])","0");
 equal("qbitdot([1,0,1],[1,1,0])","1");
 equal("qgf2rref([0,1,1;1,1,0;1,0,1])","[1,0,1;0,1,1;0,0,0]");
 equal("qgf2nullspace([0,1,1;1,1,0;1,0,1])","[1;1;1]");
 equal("qgf2nullspace([1,0,1,1;0,1,1,0])","[1,1;1,0;1,0;0,1]");
 equal("qgf2nullspace([0,0;0,0])","identity(2)");
 equal("qgf2nullspace(identity(2))","vector()");
 equal("qgf2mul([1,1],[1;1])","[0]");
 equal("qgf2mul([1,1,0;0,1,1],[1,0;1,1;0,1])","[0,1;1,0]");
 equal("qlineargate([1,0;1,1])","[1,0,0,0;0,1,0,0;0,0,0,1;0,0,1,0]");
 equal("qlineargate([0,1;1,0])","[1,0,0,0;0,0,1,0;0,1,0,0;0,0,0,1]");
 for(unsigned value=0;value<64;++value)equal("qbitvalue(qbits("+std::to_string(value)+",6))",std::to_string(value));
 equal("qbitvalue(qbits(2^1023+1,1024))","2^1023+1");
 // Exhaust all 2x2 matrices; determinant parity independently determines rank.
 for(unsigned mask=0;mask<16;++mask) {
  unsigned a=(mask>>3)&1,b=(mask>>2)&1,c=(mask>>1)&1,d=mask&1;
  std::string m="["+std::to_string(a)+","+std::to_string(b)+";"+std::to_string(c)+","+std::to_string(d)+"]";
  unsigned det=(a*d)^(b*c),rank=det ? 2 : mask ? 1 : 0;
  equal("qgf2rank("+m+")",std::to_string(rank));
  if(det) {
   equal("qgf2inverse("+m+")","["+std::to_string(d)+","+std::to_string(b)+";"+std::to_string(c)+","+std::to_string(a)+"]");
   equal("qgf2mul("+m+",qgf2inverse("+m+"))","identity(2)");
   for(unsigned x=0;x<4;++x) {
    unsigned y=(((a*((x>>1)&1))^(b*(x&1)))<<1)|((c*((x>>1)&1))^(d*(x&1)));
    equal("qmul(qlineargate("+m+"),qbasis("+std::to_string(x)+",4))","qbasis("+std::to_string(y)+",4)");
   }
  }
 }
 for(const auto &expression:{"qbits(4,2)","qbits(-1,2)","qbits(1,0)","qbits(1,1025)","qbitvalue([1,2])","qbitdot([1,0],[1])","qbitxor(vector(),vector())","qbitvalue([1,0;0,1])","qgf2rank([1,i])","qgf2rank(identity(129))","qgf2mul([1,0],[1,0])","qgf2inverse([1,1;1,1])","qgf2inverse([1,0,0;0,1,0])","qlineargate([1,1;1,1])","qlineargate(identity(10))"}) {
  while(calculator.message())calculator.nextMessage();
  calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid binary operation accepted: ")+expression);
  ++checks;
 }
 std::cout<<"PASS: "<<checks<<" binary algebra checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
