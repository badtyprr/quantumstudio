// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "Function.h"
#include "QuantumIndexed.h"
#include "QuantumGates.h"
#include "QuantumAlgebra.h"
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
 registerQuantumAlgebra(calculator);
 registerQuantumGates(calculator);
 registerQuantumIndexed(calculator);
#endif
 eo.approximation=APPROXIMATION_EXACT;
 equal("qsequence(vector(qmul([0,1;1,0],x)), [1;0], x)","[0;1]");
 equal("qsequence(vector(qsequence(vector(qmul([0,1;1,0],x)),x,x)), [1;0], x)","[0;1]");
 equal("qblocksum(qsequence(vector(qmul([0,1;1,0],x)),qbasis(x,2),x),0,1,x)","[0,0;1,0;0,1;0,0]");
 MathStructure stopped=calculator.parse("qsequence(vector(x),[1;0],x)"), cancelled;
 calculator.startControl();calculator.abort();
 int cancellationResult=calculator.getFunction("qsequence")->calculate(cancelled,stopped,eo);
 calculator.stopControl();
 if(cancellationResult!=0)throw std::runtime_error("Sequence ignored cancellation");
 ++checks;
 equal("qphasefunction(x,1,x)","[1,0;0,-1]");
 equal("qphasefunction(mod(x,2),2,x)","[1,0,0,0;0,-1,0,0;0,0,1,0;0,0,0,-1]");
 equal("qoraclefunction(x,1,1,x)","[1,0,0,0;0,1,0,0;0,0,0,1;0,0,1,0]");
 equal("qoraclefunction(mod(x,2),2,1,x)","qoracle([0,1,0,1],1)");
 equal("qoraclefunction(3-x,2,2,x)","qoracle([3,2,1,0],2)");
 equal("qtensorproduct([1,0;0,x],1,3,x)","[1,0,0,0,0,0,0,0;0,3,0,0,0,0,0,0;0,0,2,0,0,0,0,0;0,0,0,6,0,0,0,0;0,0,0,0,1,0,0,0;0,0,0,0,0,3,0,0;0,0,0,0,0,0,2,0;0,0,0,0,0,0,0,6]");
 equal("qblocksum(x,-1,1,x)","[-1,0,0;0,0,0;0,0,1]");
 equal("qblocksum([x,x+1],1,2,x)","[1,2,0,0;0,0,2,3]");
 equal("qblocksum([x;x+1],1,2,x)","[1,0;2,0;0,2;0,3]");
 equal("qtensorproduct([x;1],1,2,x)","[2;1;2;1]");
 equal("qblocksum(qblocksum(x,1,2,x),1,2,x)","[1,0,0,0;0,2,0,0;0,0,1,0;0,0,0,2]");
 equal("qblocksum(qblocksum(x,1,y,x),1,2,y)","[1,0,0;0,1,0;0,0,2]");
 equal("qblocksum(sum(x,1,2,x),1,2,x)","[3,0;0,3]");
 equal("qphasefunction(mod(sum(x,0,1,x),2),1,x)","[-1,0;0,-1]");
 for(const auto &expression:{"qsequence([x],identity(513),x)","qsequence([identity(513)],[1;0],x)","qsequence(vector(vector(x)),[1;0],x)","qphasefunction(x,2,x)","qphasefunction(0,10,x)","qphasefunction(0,1,1)","qoraclefunction(x,2,1,x)","qoraclefunction(-1,1,1,x)","qoraclefunction(0,5,5,x)","qblocksum(x,2,1,x)","qblocksum(x,0,32,x)","qblocksum(x,-1000001,0,x)","qtensorproduct([1;0],1,2,1)","qblocksum(identity(513),1,2,x)"}) {
  while(calculator.message())calculator.nextMessage();
  calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid indexed operation accepted: ")+expression);
  ++checks;
 }
 std::string excessive="qsequence([";
 for(int j=0;j<513;++j){if(j)excessive+=",";excessive+="x";}
 excessive+="],[1;0],x)";
 while(calculator.message())calculator.nextMessage();
 calculator.calculate(excessive,eo);bool boundError=false;
 while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)boundError=true;calculator.nextMessage();}
 if(!boundError)throw std::runtime_error("Sequence step bound ignored");
 ++checks;
 std::cout<<"PASS: "<<checks<<" indexed quantum checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
