// GPL-2.0-or-later; see COPYING.
#include "libqalculate/QuantumExactReadout.h"
#include "libqalculate/Calculator.h"
#include <iostream>
#include <stdexcept>
#include <utility>
using namespace QuantumExact;
namespace {
unsigned checks=0;EvaluationOptions exact;
void check(bool ok){++checks;if(!ok)throw std::runtime_error("Exact readout check failed: "+std::to_string(checks));}
MathStructure calc(const std::string &text){return CALCULATOR->calculate(text,exact);}
void equal(MathStructure actual,const std::string &expected){actual-=calc(expected);actual.eval(exact);check(actual.isZero());}
template<class E,class F>void rejects(F f){bool caught=false;try{f();}catch(const E &){caught=true;}check(caught);}
}
int main(){try {
 Calculator calculator;check(calculator.loadGlobalDefinitions());exact.approximation=APPROXIMATION_EXACT;
 MathStructure table=calc("[3/4,1/4;1/3,2/3]");std::vector<unsigned> bits={0};
 ReadoutAssignment asymmetric(bits,table,exact);
 auto zero=asymmetric.outcomes(0),one=asymmetric.outcomes(1);
 equal(zero.at(0),"3/4");equal(zero.at(1),"1/4");equal(one.at(0),"1/3");equal(one.at(1),"2/3");
 bits[0]=5;*table.getElement(1,1)=MathStructure(0);
 equal(asymmetric.outcomes(0).at(0),"3/4");check(asymmetric.bits()[0]==0);
 ReadoutAssignment copied(std::move(asymmetric));equal(copied.outcomes(0).at(1),"1/4");equal(asymmetric.outcomes(0).at(1),"1/4");
 ReadoutAssignment symbolic({0},calc("[cos(x)^2,sin(x)^2;sin(x)^2,cos(x)^2]"),exact);
 equal(symbolic.outcomes(0).at(0),"cos(x)^2");equal(symbolic.outcomes(1).at(0),"sin(x)^2");
 const std::uint64_t high=std::uint64_t(1)<<63;
 ReadoutAssignment flip({63,0},calc("[0,1,0,0;0,0,1,0;0,0,0,1;1,0,0,0]"),exact);
 check(flip.outcomes(high|32).size()==1);equal(flip.outcomes(high|32).at(high|33),"1");
 ReadoutAssignment reverse({0,63},calc("[0,1,0,0;0,0,1,0;0,0,0,1;1,0,0,0]"),exact);
 equal(reverse.outcomes(high|32).at(33),"1");
 ReadoutAssignment unchanged({0,1,2,3,4,5,6,7},calc("identity(256)"),exact);
 equal(unchanged.outcomes(high|255).at(high|255),"1");
 rejects<std::invalid_argument>([&]{ReadoutAssignment a({},calc("identity(2)"),exact);});
 rejects<std::invalid_argument>([&]{ReadoutAssignment a({0,1,2,3,4,5,6,7,8},calc("identity(2)"),exact);});
 rejects<std::invalid_argument>([&]{ReadoutAssignment a({0,0},calc("identity(4)"),exact);});
 rejects<std::out_of_range>([&]{ReadoutAssignment a({64},calc("identity(2)"),exact);});
 rejects<std::invalid_argument>([&]{ReadoutAssignment a({0},calc("identity(4)"),exact);});
 rejects<std::invalid_argument>([&]{ReadoutAssignment a({0},calc("[1;0]"),exact);});
 for(const char *bad:{"[1,-1;0,1]","[1,1;0,1]","[0,0;0,1]","[infinity,0;0,1]","[i,0;0,1]"})
  rejects<std::invalid_argument>([&]{ReadoutAssignment a({0},calc(bad),exact);});
 rejects<std::domain_error>([&]{ReadoutAssignment a({0},calc("[x,1-x;0,1]"),exact);});
 EvaluationOptions numeric=exact;numeric.approximation=APPROXIMATION_APPROXIMATE;
 auto approximate=calculator.calculate("[sqrt(2)/2,1-sqrt(2)/2;0,1]",numeric);
 rejects<std::domain_error>([&]{ReadoutAssignment a({0},approximate,exact);});
 calculator.startControl();calculator.abort();
 rejects<std::runtime_error>([&]{copied.outcomes(0);});calculator.stopControl();
 equal(copied.outcomes(0).at(0),"3/4");
 std::cout<<"PASS: "<<checks<<" exact readout checks.\n";return 0;
 }catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
