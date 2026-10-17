// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "QuantumSubsystem.h"
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
 registerQuantumSubsystem(calculator);
#endif
 eo.approximation=APPROXIMATION_EXACT;
 equal("qapply([1,0;0,exp(i*x)],identity(2)/2,0)","identity(2)/2");
 equal("qapply([1,0;0,exp(i*x)],[1,1;1,1]/2,0)","[1,exp(-i*x);exp(i*x),1]/2");

 equal("qptrace([1,0,0,1;0,0,0,0;0,0,0,0;1,0,0,1]/2,0)","[1/2,0;0,1/2]");
 equal("qptranspose([1,0,0,1;0,0,0,0;0,0,0,0;1,0,0,1]/2,0)","[1,0,0,0;0,0,1,0;0,1,0,0;0,0,0,1]/2");
 equal("qptracedim(qdensity(qbasis(5,6)),0,[2,3])","qdensity(qbasis(2,3))");
 equal("qptracedim(qdensity(qbasis(5,6)),[0,1],[2,3])","1");
 equal("qptransposedim(qptransposedim(qdensity([1;i;2;3;4;5]),1,[2,3]),1,[2,3])","qdensity([1;i;2;3;4;5])");
 equal("qpermutedim(qbasis(4,6),[1,0],[2,3])","qbasis(3,6)");
 equal("qpermute([0,1,0,0],[1,0])","[0,0,1,0]");
 equal("qpermute(qdensity([1;i;2;3]),[1,0])","qdensity([1;2;i;3])");
 equal("qapply([1,0;0,i],qdensity([1;1;0;0]),1)","qdensity([1;i;0;0])");
 // The ket path supplies an independent outer-product reference for U rho U†.
 // Include nonunitary operators, complex coherences and every ordered wire pair.
 const std::string coherent="[1;i;2-i;0;-1;3*i;1+i;2]";
 for(unsigned wire=0;wire<3;++wire)for(const auto &gate:{"[0,-i;i,0]","[1,0;0,i]","[1,i;2,3-i]"}) {
  std::string index=std::to_string(wire),operation=gate;
  equal("qapply("+operation+",qdensity("+coherent+"),"+index+")","qdensity(qapply("+operation+","+coherent+","+index+"))");
 }
 for(unsigned first=0;first<3;++first)for(unsigned second=0;second<3;++second)if(first!=second) {
  std::string wires="["+std::to_string(first)+","+std::to_string(second)+"]";
  for(const auto &gate:{"[1,0,0,0;0,1,0,0;0,0,0,-i;0,0,i,0]","[1,i,0,2;0,2,0,0;1,0,3-i,0;0,0,i,1]"}) {
   std::string operation=gate;
   equal("qapply("+operation+",qdensity("+coherent+"),"+wires+")","qdensity(qapply("+operation+","+coherent+","+wires+"))");
  }
 }
 for(unsigned wire=0;wire<3;++wire) {
  std::string index=std::to_string(wire),gate="[1,i;2,3-i]",other="[0;1;i;0;1;0;0;2]";
  equal("qapply("+gate+",(qdensity("+coherent+")+2*qdensity("+other+"))/3,"+index+")",
        "(qdensity(qapply("+gate+","+coherent+","+index+"))+2*qdensity(qapply("+gate+","+other+","+index+")))/3");
 }
 for(unsigned wire=0;wire<3;++wire)for(unsigned state=0;state<8;++state) {
  std::string ket="qbasis("+std::to_string(state)+",8)";
  equal("qapply([0,1;1,0],"+ket+","+std::to_string(wire)+")","qbasis("+std::to_string(state^(1U<<(2-wire)))+",8)");
 }
 for(unsigned control=0;control<3;++control)for(unsigned target=0;target<3;++target)if(control!=target)for(unsigned state=0;state<8;++state) {
  unsigned result=(state&(1U<<(2-control))) ? state^(1U<<(2-target)) : state;
  equal("qapply([1,0,0,0;0,1,0,0;0,0,0,1;0,0,1,0],qbasis("+std::to_string(state)+",8),["+std::to_string(control)+","+std::to_string(target)+"])","qbasis("+std::to_string(result)+",8)");
 }
 for(const auto &expression:{"qptrace([1;0],0)","qptrace([1,0;0,1],1)","qptranspose([1,0;0,1],[0,0])","qptracedim([1,0;0,1],0,[2,3])","qptransposedim([1,0;0,1],0,[0,2])","qpermute([1;0;0;0],[0,0])","qpermutedim([1;0],[0],[3])","qapply([0,1;1,0],[1;0],1)","qapply([1,0,0,0;0,1,0,0;0,0,1,0;0,0,0,1],[1;0;0;0],[0,0])"}) {
  while(calculator.message())calculator.nextMessage();
  calculator.calculate(expression,eo);bool error=false;
  while(calculator.message()){if(calculator.message()->type()==MESSAGE_ERROR)error=true;calculator.nextMessage();}
  if(!error)throw std::runtime_error(std::string("Invalid subsystem operation accepted: ")+expression);
  ++checks;
 }
 std::cout<<"PASS: "<<checks<<" quantum subsystem checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
