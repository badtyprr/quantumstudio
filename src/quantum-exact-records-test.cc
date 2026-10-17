// GPL-2.0-or-later; see COPYING.
#include "libqalculate/QuantumExactRecords.h"
#include "libqalculate/Calculator.h"
#include <iostream>
#include <stdexcept>
using namespace QuantumExact;
namespace {
unsigned checks=0;
EvaluationOptions exact;
void check(bool value) {++checks;if(!value)throw std::runtime_error("Exact record regression failed at check "+std::to_string(checks));}
MathStructure calc(const std::string &text) {return CALCULATOR->calculate(text,exact);}
void equal(MathStructure actual,const std::string &expected) {actual-=calc(expected);actual.eval(exact);check(actual.isZero());}
template<class E,class F> void rejects(F f) {bool caught=false;try{f();}catch(const E &){caught=true;}check(caught);}
}
int main() {try {
 Calculator calculator;check(calculator.loadGlobalDefinitions());
 exact.approximation=APPROXIMATION_EXACT;
 Records plus={{0,calc("[1,1;1,1]/2")}};
 auto measured=measure(plus,1,1,0,0,8,exact);
 check(measured.size()==2);
 auto mass=weights(measured,1,1,{0},8,exact);
 equal(mass.at(0),"1/2");equal(mass.at(1),"1/2");
 equal(*plus.at(0).getElement(1,2),"1/2"); // Input coherence survives in caller.
 equal(*measured.at(0).getElement(1,2),"0");
 equal(weights(measured,1,1,{},8,exact).at(0),"1");
 // Overwriting a record merges its quantum mixtures instead of replacing one.
 Records collision={{0,calc("[1,0,0,0;0,0,0,0;0,0,0,0;0,0,0,0]/2")},
                    {1,calc("[0,0,0,0;0,1,0,0;0,0,0,0;0,0,0,0]/2")}};
 auto merged=measure(collision,2,2,0,0,32,exact);
 check(merged.size()==1);
 equal(*merged.at(0).getElement(1,1),"1/2");equal(*merged.at(0).getElement(2,2),"1/2");
 auto later=measure(merged,2,2,1,1,32,exact);
 auto laterMass=weights(later,2,2,{1},32,exact);
 equal(laterMass.at(0),"1/2");equal(laterMass.at(1),"1/2");
 // Preserve symbolic mass without dividing by it or assuming it is nonzero.
 Records symbolic={{0,calc("[cos(x)^2,0;0,sin(x)^2]")}};
 auto symbolicMass=weights(measure(symbolic,1,1,0,0,8,exact),1,1,{0},8,exact);
 equal(symbolicMass.at(0),"cos(x)^2");equal(symbolicMass.at(1),"sin(x)^2");
 const std::uint64_t high=std::uint64_t(1)<<63;
 auto highRecords=measure(plus,1,64,0,63,8,exact);
 check(highRecords.count(high)==1);
 equal(weights(highRecords,1,64,{0,63},8,exact).at(1),"1/2");
 equal(weights(highRecords,1,64,{63,0},8,exact).at(2),"1/2");
 check(measure({{0,calc("[0,0;0,0]")}},1,1,0,0,4,exact).empty());
 equal(weights({{0,calc("[4,0;0,0]")}},1,1,{},4,exact).at(0),"4"); // Not silently normalized.
 rejects<std::length_error>([&]{measure(plus,1,1,0,0,4,exact);});
 equal(*plus.at(0).getElement(1,1),"1/2");
 rejects<std::out_of_range>([&]{measure(plus,1,1,1,0,8,exact);});
 rejects<std::out_of_range>([&]{measure(plus,1,1,0,1,8,exact);});
 rejects<std::out_of_range>([&]{weights(plus,1,65,{},8,exact);});
 rejects<std::out_of_range>([&]{weights(plus,11,1,{},8,exact);});
 rejects<std::out_of_range>([&]{weights({{2,plus.at(0)}},1,1,{},8,exact);});
 rejects<std::invalid_argument>([&]{weights(plus,1,1,{0,0},8,exact);});
 rejects<std::out_of_range>([&]{weights(plus,1,1,{1},8,exact);});
 rejects<std::invalid_argument>([&]{weights({{0,calc("[1;0]")}},1,1,{},8,exact);});
 calculator.startControl();calculator.abort();
 rejects<std::runtime_error>([&]{measure(plus,1,1,0,0,8,exact);});
 calculator.stopControl();
 equal(*plus.at(0).getElement(1,1),"1/2");
 std::cout<<"PASS: "<<checks<<" exact classical record checks.\n";
 return 0;
 }catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
