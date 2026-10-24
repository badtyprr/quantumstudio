// GPL-2.0-or-later; see COPYING.
#include "libqalculate/QuantumExactPhaseCircuit.h"
#include "libqalculate/Calculator.h"
#include <iostream>
#include <stdexcept>
using namespace QuantumExact;
using Step=CircuitStep;
namespace {
unsigned checks=0;EvaluationOptions exact;
void check(bool value){++checks;if(!value)throw std::runtime_error("Exact phase circuit check "+std::to_string(checks));}
template<class E,class F>void rejects(F f){bool caught=false;try{f();}catch(const E&){caught=true;}check(caught);}
MathStructure calc(const std::string &s){return CALCULATOR->calculate(s,exact);}
}
int main(){try {
 Calculator calculator;check(calculator.loadGlobalDefinitions());exact.approximation=APPROXIMATION_EXACT;
 auto gate=[&](const char *name,const std::vector<unsigned> &wires){return Step::map(TracePreservingMap({calc(std::string("quantum: ")+name)},65536,exact),wires);};
 PhaseBudget budget(4096,4096,10000000);PhaseCircuitLimits limits{65536,100000,500000};
 std::map<std::uint64_t,std::string> out;
 auto compare=[&](unsigned qubits,unsigned bits,const std::vector<Step> &steps,const std::vector<unsigned> &selected,bool numerical=false) {
  check(tryPhaseCircuitWeights(qubits,bits,steps,selected,out,budget,limits));
  auto expected=weights(evaluateCircuit(qubits,bits,steps,65536,exact),qubits,bits,selected,65536,exact);
  check(out.size()==expected.size());
  for(auto &item:expected){
   check(out.count(item.first)==1);auto difference=calc(out.at(item.first));difference-=item.second;
   auto options=exact;if(numerical)options.approximation=APPROXIMATION_APPROXIMATE;
   difference.eval(options);
   if(numerical){check(difference.isNumber());Number error=difference.number();check(error.abs());check(error<Number(1,1,-12));}
   else check(difference.isZero());
  }
 };
 compare(0,0,{},{});check(out.at(0)=="1");
 compare(1,1,{gate("H",{0}),Step::measure(0,0)},{0});check(out.at(0)=="0.5" && out.at(1)=="0.5");
 compare(2,2,{gate("H",{0}),gate("CNOT",{0,1}),Step::measure(0,0),Step::measure(1,1)},{1,0});
 compare(3,3,{gate("H",{2}),gate("CNOT",{2,1}),Step::measure(0,0),Step::measure(1,1),Step::measure(2,2)},{2,1,0});
 check(out.count(0)==1 && out.count(6)==1);
 compare(2,2,{gate("H",{0}),gate("H",{1}),Step::measure(0,0),Step::measure(1,1)},{0});
 compare(2,64,{gate("H",{0}),gate("X",{1}),Step::measure(0,63),Step::measure(1,63)},{63});check(out.at(1)=="1");
 // Exponential and trigonometric exact forms need not simplify to the same
 // tree in the general evaluator. Check their numerical difference here;
 // exact phase normalization/composition is covered by the arithmetic suite.
 compare(1,1,{gate("Rx(0.1)",{0}),Step::measure(0,0)},{0},true);
 compare(1,1,{gate("H",{0}),gate("S",{0}),gate("Rz(0.3)",{0}),gate("H",{0}),Step::measure(0,0)},{0},true);
 compare(1,1,{gate("Rz(0.1)",{0}),Step::measure(0,0)},{0});check(out.at(0)=="1");
 compare(1,1,{gate("[3/5,-4/5;4/5,3/5]",{0}),Step::measure(0,0)},{0});check(out.at(0)=="0.36" && out.at(1)=="0.64");
 compare(1,1,{gate("[5/13,-12/13;12/13,5/13]",{0}),Step::measure(0,0)},{0});check(out.at(0)=="25/169" && out.at(1)=="144/169");
 compare(1,1,{gate("Ry(-0.25)",{0}),Step::measure(0,0)},{});
 compare(1,1,{gate("Rx(0.12345678901234567)",{0})},{0});check(out.at(0)=="1");
 const std::map<std::uint64_t,std::string> sentinel{{99,"unchanged"}};out=sentinel;
 check(!tryPhaseCircuitWeights(1,1,{gate("H",{0}),Step::measure(0,0),gate("H",{0})},{0},out,budget,limits));check(out==sentinel);
 check(!tryPhaseCircuitWeights(1,1,{gate("Ry(x)",{0}),Step::measure(0,0)},{0},out,budget,limits));check(out==sentinel);
 check(!tryPhaseCircuitWeights(1,1,{Step::reset(0)},{0},out,budget,limits));check(out==sentinel);
 PhaseBudget smallBits(100,4,10000);
 check(!tryPhaseCircuitWeights(1,1,{gate("Rz(0.12345678901234567)",{0}),Step::reset(0)},{0},out,smallBits,limits));check(out==sentinel);
 TracePreservingMap channel({calc("[1,0;0,0]"),calc("[0,0;0,1]")},16,exact);
 check(!tryPhaseCircuitWeights(1,1,{Step::map(channel,{0})},{0},out,budget,limits));check(out==sentinel);
 rejects<std::out_of_range>([&]{tryPhaseCircuitWeights(11,1,{}, {},out,budget,limits);});
 rejects<std::out_of_range>([&]{tryPhaseCircuitWeights(1,65,{}, {},out,budget,limits);});
 rejects<std::out_of_range>([&]{tryPhaseCircuitWeights(1,1,{}, {1},out,budget,limits);});
 rejects<std::invalid_argument>([&]{tryPhaseCircuitWeights(1,1,{}, {0,0},out,budget,limits);});
 rejects<std::out_of_range>([&]{tryPhaseCircuitWeights(1,1,{Step::measure(1,0)}, {0},out,budget,limits);});
 rejects<std::out_of_range>([&]{tryPhaseCircuitWeights(1,1,{gate("X",{1})}, {0},out,budget,limits);});
 rejects<std::invalid_argument>([&]{tryPhaseCircuitWeights(2,1,{gate("CNOT",{0,0})}, {0},out,budget,limits);});
 rejects<std::invalid_argument>([&]{tryPhaseCircuitWeights(2,1,{gate("X",{0,1})}, {0},out,budget,limits);});
 PhaseCircuitLimits tiny{1,100,100};
 rejects<std::length_error>([&]{tryPhaseCircuitWeights(1,1,{gate("H",{0}),Step::measure(0,0)},{0},out,budget,tiny);});
 tiny={65536,1,100};
 rejects<std::length_error>([&]{tryPhaseCircuitWeights(1,1,{gate("H",{0}),Step::measure(0,0)},{0},out,budget,tiny);});
 tiny={65536,100,5};
 rejects<std::length_error>([&]{tryPhaseCircuitWeights(1,1,{gate("H",{0}),Step::measure(0,0)},{0},out,budget,tiny);});
 PhaseBudget cancelled(4096,4096,10000,[]{return true;});
 rejects<std::runtime_error>([&]{tryPhaseCircuitWeights(1,1,{}, {},out,cancelled,limits);});check(out==sentinel);
 std::cout<<"PASS: "<<checks<<" exact phase circuit checks\n";return 0;
}catch(const std::exception &error){std::cerr<<error.what()<<'\n';return 1;}}
