// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumAlgebra.h"
#include <iostream>
#include <stdexcept>
#include <cmath>
static unsigned checks=0;
static EvaluationOptions eo;
static void messages(bool expected=false) {
 bool error=false;while(CALCULATOR->message()) {error|=CALCULATOR->message()->type()==MESSAGE_ERROR;if(!expected)std::cerr<<CALCULATOR->message()->message()<<"\n";CALCULATOR->nextMessage();}
 if(error!=expected)throw std::runtime_error(expected ? "Missing rejection" : "Unexpected calculator error");
}
static MathStructure evaluate(const std::string &expression) {std::cerr<<"CHECK "<<expression<<"\n";auto value=CALCULATOR->calculate(expression,eo);messages();return value;}
static void equal(const std::string &expression,const std::string &expected) {
 auto value=evaluate("("+expression+")==("+expected+")");
 if(!value.isOne())throw std::runtime_error("Mismatch: "+expression+" expected "+expected+" got "+value.print());++checks;
}
static void reject(const std::string &expression) {CALCULATOR->calculate(expression,eo);try {messages(true);}catch(...) {throw std::runtime_error("Not rejected: "+expression);}++checks;}
static void small(MathStructure value) {
 EvaluationOptions numeric=eo;numeric.approximation=APPROXIMATION_APPROXIMATE;value.eval(numeric);messages();
 if(!value.isNumber() || value.number().isUndefined() || value.number().isInfinite(false) || std::hypot(value.number().realPart().floatValue(),value.number().imaginaryPart().floatValue())>1e-10)throw std::runtime_error("Nonzero residual: "+value.print());++checks;
}
int main() {try {
 Calculator instance;if(!instance.loadGlobalDefinitions())throw std::runtime_error("No definitions");eo.approximation=APPROXIMATION_EXACT;
 std::string p="qpovm(vector(0,1),vector([2,1;1,1]/3,[1,-1;-1,2]/3))";
 std::string z="qinstrument(vector(0,1),vector(vector([1,0;0,0]),vector([0,0;0,1])))";
 equal("qmeasurementvalid("+p+")","1");equal("qmeasurementvalid("+z+")","1");
 equal("qprobabilities("+p+",[1;1]/sqrt(2))","vector(5/6,1/6)");
 equal("qpoststate("+z+",[1;1]/sqrt(2),0)","[1,0;0,0]");
 equal("qpoststate("+z+",[1;1]/sqrt(2),1)","[0,0;0,1]");
 std::string e="qensemble(vector(0,1),vector(1/3,2/3),vector([1;0],[1;1]/sqrt(2)))";
 equal("qensemblevalid("+e+")","1");equal("qensembleaverage("+e+")","[2/3,1/3;1/3,1/3]");
 equal("qptracedim([1,0,0,1;0,0,0,0;0,0,0,0;1,0,0,1]/2,0,[2,2])","[1/2,0;0,1/2]");
 // Multiple Kraus operators in one outcome implement a reset, not a coherent sum.
 std::string reset="qinstrument(vector(7),vector(vector([1,0;0,0],[0,1;0,0])))";
 equal("qmeasurementvalid("+reset+")","1");equal("qpoststate("+reset+",[1;1]/sqrt(2),7)","[1,0;0,0]");
 equal("qprobabilities("+reset+",[1;1]/sqrt(2))","vector(1)");
 auto symbolic=evaluate("qmeasurementvalid(qpovm(vector(0,1),vector([x,0;0,1],[1-x,0;0,0])))");
 if(!symbolic.isFunction())throw std::runtime_error("Lost symbolic condition");++checks;
 for(const std::string &bad:{
  "qpovm(vector(0,1),vector([-1,0;0,1],[2,0;0,0]))",
  "qpovm(vector(0,1),vector([1,1;0,0],[0,-1;0,1]))",
  "qpovm(vector(0,1),vector([1,0;0,1],[1,0;0,1]))",
  "qpovm(vector(0,0),vector([1,0;0,0],[0,0;0,1]))",
  "qpovm(vector(0,1),vector(identity(2),identity(3)))",
  "qensemble(vector(0,1),vector(-1,2),vector([1;0],[0;1]))",
  "qensemble(vector(0,1),vector(1/2,1/2),vector([2;0],[0;1]))"})reject(bad);
 reject("qpoststate("+z+",[1;0],1)");reject("qprobabilities("+p+",[1;0;0])");reject("qpoststate("+p+",[1;0],0)");
 reject("qnaimark("+p+",1)");reject("qnaimark("+p+",3/2)");
 // Full unitary, padded non-qubit ancilla, and independent block probabilities.
 for(unsigned ancilla:{2u,3u}) {
  auto u=evaluate("qnaimark("+p+","+std::to_string(ancilla)+")");
  if(!u.isMatrix() || u.rows()!=2*ancilla || u.columns()!=2*ancilla)throw std::runtime_error("Missing full Naimark unitary: "+u.print());++checks;
  MathStructure gram=quantumAdjoint(u,eo);gram*=u;gram.eval(eo);messages();
  for(size_t r=0;r<u.rows();++r)for(size_t c=0;c<u.rows();++c) {MathStructure diff=*gram.getElement(r+1,c+1);if(r==c)diff-=1;small(diff);}
  for(unsigned k=0;k<ancilla;++k) {
   MathStructure probability;
   for(unsigned row=0;row<2;++row) {
    MathStructure amplitude=*u.getElement(2*k+row+1,1);amplitude+=*u.getElement(2*k+row+1,2);
    MathStructure conjugate(CALCULATOR->getFunction("conj"),&amplitude,NULL);conjugate.eval(eo);amplitude*=conjugate;amplitude/=2;probability+=amplitude;
   }
   probability-=MathStructure(k==0 ? Number(5,6) : k==1 ? Number(1,6) : Number(0));small(probability);
  }
 }
 std::cout<<"PASS: "<<checks<<" instrument checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}

