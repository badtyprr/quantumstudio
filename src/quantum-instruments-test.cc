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
static void compression(const MathStructure &u,const std::vector<MathStructure> &effects) {
 size_t n=effects[0].rows();
 for(size_t k=0;k<effects.size();++k)for(size_t a=0;a<n;++a)for(size_t b=0;b<n;++b) {
  MathStructure actual;
  for(size_t row=0;row<n;++row) {
   MathStructure entry=*u.getElement(k*n+row+1,a+1);
   MathStructure conjugate(CALCULATOR->getFunction("conj"),&entry,NULL);conjugate.eval(eo);
   conjugate*=*u.getElement(k*n+row+1,b+1);actual+=conjugate;
  }
  actual-=*effects[k].getElement(a+1,b+1);small(actual);
 }
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
  compression(u,{evaluate("[2,1;1,1]/3"),evaluate("[1,-1;-1,2]/3")});
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
 reject("qpovm(vector(0,1),vector([x,0;0,-1],[1-x,0;0,2]))");
 auto labels=evaluate("qmeasurementvalid(qpovm(vector(x,y),vector([1,0;0,0],[0,0;0,1])))");
 if(!labels.isFunction())throw std::runtime_error("Symbolic distinct-label obligation lost");++checks;
 auto numeric=evaluate("qnaimark(qpovm(vector(0,1),vector([4,1,1;1,3,0;1,0,3]/10,[6,-1,-1;-1,7,0;-1,0,7]/10)),2)");
 if(!numeric.isMatrix() || numeric.rows()!=6 || numeric.columns()!=6)throw std::runtime_error("Missing numerical Naimark completion");++checks;
 compression(numeric,{evaluate("[4,1,1;1,3,0;1,0,3]/10"),evaluate("[6,-1,-1;-1,7,0;-1,0,7]/10")});
 MathStructure numericGram=quantumAdjoint(numeric,eo);numericGram*=numeric;numericGram.eval(eo);
 for(size_t r=0;r<6;++r)for(size_t c=0;c<6;++c) {MathStructure residual=*numericGram.getElement(r+1,c+1);if(r==c)residual-=1;small(residual);}
 for(const std::string &expression:{
  "qmeasurementvalid(qpovm(vector(0,1),vector(matrixparam(\"A\",2,2),matrixparam(\"B\",2,2))))",
  "qmeasurementvalid(qinstrument(vector(0),vector(vector(matrixparam(\"A\",3,2)))))",
  "qensemblevalid(qensemble(vector(0),vector(1),vector(matrixparam(\"A\",2,2))))",
  "qnaimark(qpovm(vector(0,1),vector(matrixparam(\"A\",x,x),matrixparam(\"B\",x,x))),y)"}) {
  auto value=evaluate(expression);if(!value.isFunction())throw std::runtime_error("Lost declared-matrix condition");++checks;
 }
 reject("qpovm(vector(0,1),vector(matrixparam(\"A\",2,2),matrixparam(\"B\",3,3)))");
 reject("qpovm(vector(0,1),vector(matrixparam(\"A\",2,2),[-1,0;0,1]))");
 equal("qmeasurementvalid(qinstrument(vector(0),vector(vector(qmatrix(1,1,vector(1))))))","1");
 equal("qmeasurementvalid(qinstrument(vector(0,1),vector(vector(qmatrix(1,2,vector(1,0))),vector(qmatrix(1,2,vector(0,1))))))","1");
 reject("qpovm(vector(0,1),vector([x,0,0;0,1,2;0,2,1],[1-x,0,0;0,0,-2;0,-2,0]))");
 reject("qpovm(vector(0),vector([1+1/10000000000000,0;0,1]))");
 reject("qmeasurementvalid(qinstrument(vector(0),vector(vector(matrixparam(\"A\",2,2),[infinity,infinity;infinity,infinity]))))");
 auto selection=evaluate("qpoststate("+z+",[1;1]/sqrt(2),x)");
 if(!selection.isFunction())throw std::runtime_error("Unknown outcome selector lost");++checks;
 equal("replace(qpoststate("+z+",[1;1]/sqrt(2),x),x,0)","[1,0;0,0]");
 equal("replace(qpoststate("+z+",[1;1]/sqrt(2),x),x,1)","[0,0;0,1]");
 reject("replace(qpoststate("+z+",[1;1]/sqrt(2),x),x,2)");
 eo.approximation=APPROXIMATION_APPROXIMATE;
 equal("qmeasurementvalid(qpovm(vector(0),vector([1+1/10000000000000,0;0,1])))","1");
 reject("qpovm(vector(0),vector([1+1/1000000,0;0,1]))");
 equal("qmeasurementvalid(qpovm(vector(0,\"red\"),vector([1,0;0,0],[0,0;0,1])))","1");
 reject("qpoststate(qinstrument(vector(\"red\",\"blue\"),vector(vector([1,0;0,0]),vector([0,0;0,1]))),[1;1]/sqrt(2),2)");
 std::cout<<"PASS: "<<checks<<" instrument checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}

