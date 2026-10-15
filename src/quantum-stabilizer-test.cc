// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumAlgebra.h"
#include "QuantumStabilizer.h"
#include <vector>
#include <iostream>
#include <stdexcept>
static unsigned checks=0;
static EvaluationOptions eo;
static void equal(const std::string &expression,const std::string &expected) {
 MathStructure value=CALCULATOR->calculate("("+expression+")==("+expected+")",eo);
 if(!value.isNumber() || !value.number().isOne())throw std::runtime_error("Mismatch: "+expression+" vs "+expected);
 ++checks;
}
static bool truth(const std::string &expression) {
 MathStructure value=CALCULATOR->calculate(expression,eo);
 if(!value.isNumber())throw std::runtime_error("Undecidable test premise");
 return value.number().isOne();
}
static void rejected(const std::string &expression) {
 while(CALCULATOR->message())CALCULATOR->nextMessage();
 CALCULATOR->calculate(expression,eo);bool error=false;
 while(CALCULATOR->message()){if(CALCULATOR->message()->type()==MESSAGE_ERROR)error=true;CALCULATOR->nextMessage();}
 if(!error)throw std::runtime_error("Invalid stabilizer accepted: "+expression);
 ++checks;
}
int main(){try {
 Calculator calculator;if(!calculator.loadGlobalDefinitions())throw std::runtime_error("Definitions unavailable");
#ifdef LOCAL_CHECKPOINT
 registerQuantumStabilizer(calculator);registerQuantumAlgebra(calculator);
#endif
 eo.approximation=APPROXIMATION_EXACT;
 const char *pauli[]={"identity(2)","[0,1;1,0]","[0,-i;i,0]","[1,0;0,-1]"};
 std::vector<std::string> words;
 for(unsigned sign=0;sign<2;++sign)for(auto a:pauli)for(auto b:pauli)words.push_back(std::string(sign ? "-" : "")+"qtensor("+a+","+b+")");
 for(size_t a=0;a<words.size();++a)for(size_t b=a;b<words.size();++b) {
  std::string generators="vector("+words[a]+","+words[b]+")";
  std::string projector="qmul((identity(4)+("+words[a]+"))/2,(identity(4)+("+words[b]+"))/2)";
  if(!truth("qmul("+words[a]+","+words[b]+")==qmul("+words[b]+","+words[a]+")") || truth("qtrace("+projector+")==0")) {rejected("qstabilizerdimension("+generators+")");continue;}
  equal("qstabilizerprojector("+generators+")",projector);
  equal("qstabilizerdimension("+generators+")","qtrace("+projector+")");
 }
 equal("qstabilizercorrection(vector(qtensor([1,0;0,-1],[1,0;0,-1]),qtensor([0,1;1,0],[0,1;1,0])),[1,1])","qtensor(identity(2),[0,-i;i,0])");
 std::string five="vector(";
 for(const char *label:{"XZZXI","IXZZX","XIXZZ","ZXIXZ"}) {
  std::string word;
  for(const char *c=label;*c;++c) {
   std::string factor=pauli[*c=='I' ? 0 : *c=='X' ? 1 : *c=='Y' ? 2 : 3];
   word=word.empty() ? factor : "qtensor("+word+","+factor+")";
  }
  if(five!="vector(")five+=",";
  five+=word;
 }
 five+=")";
 equal("qstabilizerparameters("+five+")","[5,1,3]");
 equal("qpauliword(1,1,1,3)","[0,-i;i,0]");
 equal("qpauliword(2,1,2,0)","qtensor([1,0;0,-1],[0,1;1,0])");
 std::string g="vector(qtensor([1,0;0,-1],identity(2)),qtensor(identity(2),[1,0;0,-1]))";
 for(unsigned x=0;x<4;++x) {
  std::string syndrome="["+std::to_string(x>>1)+","+std::to_string(x&1)+"]";
  equal("qstabilizersyndrome("+g+",qpauliword(2,"+std::to_string(x)+",0,0))",syndrome);
  equal("qstabilizercorrection("+g+","+syndrome+")","qpauliword(2,"+std::to_string(x)+",0,0)");
 }
 equal("qstabilizerparameters(vector(qpauliword(3,0,6,0),qpauliword(3,0,3,0)))","[3,1,1]");
 equal("qstabilizerdistance(vector(qpauliword(4,15,0,0),qpauliword(4,0,15,0)))","2");
 equal("qstabilizerdimension(vector([1,0;0,-1],[1,0;0,-1]))","1");
 equal("qstabilizercorrection([1,0;0,-1],1)","[0,1;1,0]");
 for(const auto &expression:{"qstabilizerdimension(vector())","qstabilizerdimension([1,1;0,1])","qstabilizerdimension(i*identity(2))","qstabilizerdimension(vector(identity(2),identity(4)))","qstabilizercorrection(vector([1,0;0,-1],[1,0;0,-1]),[0,1])","qstabilizercorrection(identity(2),1)","qstabilizercorrection([1,0;0,-1],2)","qstabilizersyndrome([1,0;0,-1],identity(4))","qstabilizerdistance([1,0;0,-1])","qpauliword(1,2,0,0)","qpauliword(1,0,0,4)","qpauliword(10,0,0,0)"})rejected(expression);
 std::cout<<"PASS: "<<checks<<" stabilizer checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
