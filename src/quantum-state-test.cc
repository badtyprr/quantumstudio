// GPL-2.0-or-later; see COPYING.
#include "QuantumStateMetrics.h"
#include "Calculator.h"
#include <cmath>
#include <iostream>
#include <stdexcept>
static unsigned checks=0;
static EvaluationOptions eo;
static MathStructure parse(const std::string &s){return CALCULATOR->calculate(s,eo);}
static void compare(const MathStructure &out,const std::string &expected) {
 if(!out.isNumber())throw std::runtime_error("Nonnumeric metric");
 MathStructure reference=parse(expected);EvaluationOptions numeric=eo;numeric.approximation=APPROXIMATION_APPROXIMATE;reference.eval(numeric);
 if(!reference.isNumber())throw std::runtime_error("Nonnumeric reference");
 Number want=reference.number(),value=out.number();
 if(want.isZero()) {
  if(std::abs(value.floatValue())>1e-12)throw std::runtime_error("Expected zero at check "+std::to_string(checks)+", got "+std::to_string(value.floatValue()));
 } else {
  value.divide(want);
  if(!std::isfinite(value.floatValue()) || std::abs(value.floatValue()-1)>1e-8)
   throw std::runtime_error("Relative metric mismatch, expected "+expected);
 }
 ++checks;
}
static void metric(const std::string &a,const std::string &b,const std::string &expected,bool fidelity=true) {
 MathStructure out,x=parse(a),y=parse(b);
 if(!quantumTraceDistance(out,x,y,eo,fidelity))throw std::runtime_error("Metric rejected: "+a+", "+b);
 compare(out,expected);
}
int main(){try {
 Calculator calculator;if(!calculator.loadGlobalDefinitions())throw std::runtime_error("Definitions unavailable");
 calculator.setPrecision(60);eo.approximation=APPROXIMATION_EXACT;
 metric("[1;0]","[0;1]","0");metric("[1;i]","[1;i]","1");
 metric("[1;i]","[1;-i]","0");metric("[1;0]","[1;1]","1/2");
 metric("[1;0]","[0;1]","1",false);
 metric("[1,0;0,0]","[1/2,0;0,1/2]","1/2");
 metric("[1/2,0;0,1/2]","[1/2,0;0,1/2]","1");
 metric("[1,0;0,0]","[1/2,0;0,1/2]","1/2",false);
 for(int exponent:{8,16,40,100,200}) {
  std::string t="1e-"+std::to_string(exponent),expected=t+"^2/(1+"+t+"^2)";
  metric("[1;0]","["+t+";1]",expected);
  metric("["+t+";i]","[1;0]",expected);
  metric("[1e100;0]","[1e100*"+t+";1e100]",expected);
  metric("[1e-100;0]","["+t+";1]",expected);
 }
 for(int i=1;i<10;++i)for(int j=1;j<10;++j) {
  std::string p=std::to_string(i)+"/10",q=std::to_string(j)+"/10";
  std::string a="["+p+",0;0,1-"+p+"]";
  std::string b="[1/2,i*("+q+"-1/2);-i*("+q+"-1/2),1/2]";
  // For qubits F_squared = Tr(rho sigma)+2 sqrt(det(rho) det(sigma)).
  metric(a,b,"1/2+2*sqrt(("+p+")*(1-"+p+")*("+q+")*(1-"+q+"))");
 }
 // Cancellation in the density-matrix formula must not erase the overlap.
 metric("[1;1]","[1;-1+1e-12]","1e-24/(2*(1+(-1+1e-12)^2))");
 metric("[1,0;0,0]","[1e-16,0;0,1-1e-16]","1e-16");
 for(const auto &source:{"[1;0]","[1,0;0,0]","[1/2,0;0,1/2]","[1,i;-i,1]/2"}) {
  MathStructure out,state=parse(source);
  if(!quantumEntropy(out,state,eo))throw std::runtime_error("Entropy rejected");
  compare(out,std::string(source)=="[1/2,0;0,1/2]" ? "1" : "0");
 }
 for(const auto &source:{"[0;0]","[1,1;0,0]","[2,0;0,-1]","[infinity;0]","[interval(0,1);1]"}) {
  MathStructure out,state=parse(source),other=parse("[1;0]");
  if(quantumTraceDistance(out,state,other,eo,true))throw std::runtime_error("Invalid state accepted");
  ++checks;
 }
 std::cout<<"PASS: "<<checks<<" state metric checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
