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
 equal("qsumset(x^2,vector(0,2,5),x)","29");
 equal("qsumset(x,vector(1,1,2,2),x)","3");
 equal("qsumset(x,vector(1/2,2/4),x)","1/2");
 equal("qsumset(x,vector(1/2,0.5),x)","1/2");
 equal("qsumset(x,vector(3),x)","3");
 equal("qsumset(x,vector(),x)","0");
 equal("qsumset(qdensity(qbasis(x,2)),vector(0,1),x)","identity(2)");
 equal("qsumset(qsumset(x,vector(1,2),x),vector(4,5),x)","6");
 equal("qsumset(qsumset(x,vector(x,x+1),x),vector(1,3),x)","10");
 equal("qsumset(qsumset(x+y,vector(1,2),y),vector(3,4),x)","20");

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
 for(const auto &expression:{"qsumset(x,3,x)","qsumset(x,[1,2;3,4],x)","qsumset(x,vector(1,2),1)","qsequence(vector(x),matrix(1025,1,vector(1)),x)","qsequence(vector(matrix(1025,1,vector(1))),[1;0],x)","qsequence(vector(vector(x)),[1;0],x)","qphasefunction(x,2,x)","qphasefunction(0,10,x)","qphasefunction(0,1,1)","qoraclefunction(x,2,1,x)","qoraclefunction(-1,1,1,x)","qoraclefunction(0,5,5,x)","qblocksum(x,2,1,x)","qblocksum(x,0,32,x)","qblocksum(x,-1000001,0,x)","qtensorproduct([1;0],1,2,1)","qblocksum(identity(513),1,2,x)"}) {
  while(calculator.message())calculator.nextMessage();
  calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid indexed operation accepted: ")+expression);
  ++checks;
 }
 MathStructure setStopped=calculator.parse("qsumset(x,vector(1,2),x)");
 calculator.startControl();calculator.abort();
 cancellationResult=calculator.getFunction("qsumset")->calculate(cancelled,setStopped,eo);
 calculator.stopControl();
 if(cancellationResult!=0)throw std::runtime_error("Set sum ignored cancellation");
 ++checks;
 std::string largeSet="qsumset(x,vector(";
 for(int j=0;j<1025;++j){if(j)largeSet+=",";largeSet+=std::to_string(j);}
 largeSet+="),x)";
 while(calculator.message())calculator.nextMessage();
 calculator.calculate(largeSet,eo);bool setBoundError=false;
 while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)setBoundError=true;calculator.nextMessage();}
 if(!setBoundError)throw std::runtime_error("Set sum ignored collection bound");
 ++checks;
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
