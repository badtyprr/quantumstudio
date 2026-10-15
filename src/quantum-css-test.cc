// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumAlgebra.h"
#include "QuantumCSS.h"
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
 registerQuantumAlgebra(calculator);registerQuantumCSS(calculator);
#endif
 eo.approximation=APPROXIMATION_EXACT;
 equal("qcssgenerators([1,1],[1,1])","vector(qtensor([0,1;1,0],[0,1;1,0]),qtensor([1,0;0,-1],[1,0;0,-1]))");
 equal("qcssstate([1,1],[1,1],0)","[1;0;0;1]/sqrt(2)");
 equal("qcssstate([1,1],[1,1],3)","[1;0;0;1]/sqrt(2)");
 equal("qcssencoder(vector(),[1,1,0;0,1,1])","[1,0;0,0;0,0;0,0;0,0;0,0;0,0;0,1]");
 equal("qcssencoder([1,1;1,1],[1,1])","[1;0;0;1]/sqrt(2)");
 equal("qcssencoder([0,0],vector())","identity(4)");
 equal("qcssencoder(vector(),[1,0;0,1])","[1;0;0;0]");
 auto row=[](unsigned x){return "["+std::to_string((x>>2)&1)+","+std::to_string((x>>1)&1)+","+std::to_string(x&1)+"]";};
 auto parity=[](unsigned x){return ((x>>2)^(x>>1)^x)&1;};
 for(unsigned x=0;x<8;++x)for(unsigned z=0;z<8;++z) {
  if(parity(x&z))continue;
  std::string hx=row(x),hz=row(z),encoder="qcssencoder("+hx+","+hz+")";
  unsigned logical=3-(x!=0)-(z!=0),columns=1U<<logical;
  equal("qmul(qdag("+encoder+"),"+encoder+")","identity("+std::to_string(columns)+")");
  for(unsigned u=0;u<8;++u)if(!parity(u&z)) {
   std::string expected="[";
   for(unsigned r=0;r<8;++r){if(r)expected+=";";expected+=(r==u || r==(u^x)) ? "1" : "0";}
   expected+=x ? "]/sqrt(2)" : "]";
   equal("qcssstate("+hx+","+hz+","+std::to_string(u)+")",expected);
  }
 }
 for(const auto &expression:{"qcssgenerators(vector(),vector())","qcssgenerators([1,0],[1,0])","qcssencoder([1,1],[1,1,0])","qcssencoder([1,2],vector())","qcssencoder(identity(10),vector())","qcssstate([1,1],[1,1],1)","qcssstate([1,1],[1,1],4)","qcssstate([1,1],[1,1],-1)","qcssstate([1,1],[1,1],1/2)"}) {
  while(calculator.message())calculator.nextMessage();
  calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid CSS construction accepted: ")+expression);
  ++checks;
 }
 std::cout<<"PASS: "<<checks<<" CSS code checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
