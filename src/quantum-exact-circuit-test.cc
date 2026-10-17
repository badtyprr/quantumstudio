// GPL-2.0-or-later; see COPYING.
#include "libqalculate/QuantumExactCircuit.h"
#include "libqalculate/Calculator.h"
#include <iostream>
#include <stdexcept>
using namespace QuantumExact;
namespace {
unsigned checks=0;EvaluationOptions exact;using Step=CircuitStep;
void check(bool ok){++checks;if(!ok)throw std::runtime_error("Exact circuit check failed: "+std::to_string(checks));}
MathStructure calc(const std::string &text){return CALCULATOR->calculate(text,exact);}
void equal(MathStructure actual,const std::string &expected){actual-=calc(expected);actual.eval(exact);check(actual.isZero());}
template<class E,class F>void rejects(F f){bool caught=false;try{f();}catch(const E &){caught=true;}check(caught);}
void distribution(unsigned qubits,unsigned bits,const std::vector<unsigned> &output,const std::vector<Step> &steps,
                  const std::map<std::uint64_t,std::string> &expected) {
 auto records=evaluateCircuit(qubits,bits,steps,65536,exact);
 auto result=weights(records,qubits,bits,output,65536,exact);check(result.size()==expected.size());
 for(const auto &item:expected)equal(result.at(item.first),item.second);
}
}
int main(){try {
 Calculator calculator;check(calculator.loadGlobalDefinitions());exact.approximation=APPROXIMATION_EXACT;
 TracePreservingMap X({calc("[0,1;1,0]")},4,exact),H({calc("[1,1;1,-1]/sqrt(2)")},4,exact);
 TracePreservingMap CX({calc("[1,0,0,0;0,1,0,0;0,0,0,1;0,0,1,0]")},16,exact);
 // Expected fractions independently obtained with explicit Fraction density matrices.
 // saved-before-reset
 distribution(1,64,{0},{Step::map(X, {0}),Step::measure(0,0),Step::reset(0)},{{1ULL,"1"}});
 // no-implicit-final-measurement
 distribution(1,64,{0},{Step::map(X, {0})},{{0ULL,"1"}});
 // empty-output
 distribution(1,64,{},{Step::map(H, {0}),Step::measure(0,0)},{{0ULL,"1"}});
 // bell-records
 distribution(2,64,{1,0},{Step::map(H, {0}),Step::map(CX, {0,1}),Step::measure(0,0),Step::measure(1,1)},{{0ULL,"1/2"},{3ULL,"1/2"}});
 // overwritten-outcome
 distribution(1,64,{0},{Step::map(H, {0}),Step::measure(0,0),Step::reset(0),Step::measure(0,0)},{{0ULL,"1"}});
 // branch-once
 distribution(1,64,{1,0},{Step::map(X, {0}),Step::measure(0,0),Step::branch(1ULL,1ULL,{Step::reset(0),Step::measure(0,0),Step::map(X, {0}),Step::measure(0,1)},{})},{{2ULL,"1"}});
 // else-body
 distribution(1,64,{0},{Step::branch(1ULL,1ULL,{},{Step::map(X, {0}),Step::measure(0,0)})},{{1ULL,"1"}});
 // little-endian-condition
 distribution(2,64,{1,0},{Step::map(X, {1}),Step::measure(1,1),Step::branch(3ULL,2ULL,{Step::map(X, {0}),Step::measure(0,0)},{})},{{3ULL,"1"}});
 // bit-63
 distribution(1,64,{63,0},{Step::map(X, {0}),Step::measure(0,63),Step::branch(9223372036854775808ULL,9223372036854775808ULL,{Step::measure(0,0)},{})},{{3ULL,"1"}});
 // readout-feedback
 distribution(1,64,{1,0},{Step::readout(ReadoutAssignment({0},calc("[1-(1/4),1/4;1/3,1-(1/3) ]"),exact)),Step::branch(1ULL,1ULL,{Step::map(X, {0})},{}),Step::measure(0,1)},{{0ULL,"3/4"},{3ULL,"1/4"}});
 // interference-before-measurement
 distribution(1,64,{0},{Step::map(H, {0}),Step::map(H, {0}),Step::measure(0,0)},{{0ULL,"1"}});
 // measurement-destroys-interference
 distribution(1,64,{0},{Step::map(H, {0}),Step::measure(0,0),Step::map(H, {0}),Step::measure(0,0)},{{0ULL,"1/2"},{1ULL,"1/2"}});
 // merged-records-retain-quantum-mixture
 distribution(2,64,{1},{Step::map(H, {0}),Step::map(CX, {0,1}),Step::measure(0,0),Step::reset(0),Step::measure(0,0),Step::measure(1,1)},{{0ULL,"1/2"},{1ULL,"1/2"}});
 TracePreservingMap rotation({calc("quantum: Ry(x)")},4,exact);
 using Bits=QuantumClassical::Bits;using Op=Bits::Binary;
 distribution(1,2,{1,0},{Step::map(X,{0}),Step::measure(0,0),Step::assign({1},Bits::read({0})),Step::assign({0},Bits::constant(1,0))},{{2,"1"}});
 distribution(0,3,{2,1,0},{Step::assign({0},Bits::constant(1,1)),Step::assign({1,2},Bits::read({0,1}))},{{3,"1"}});
 auto parity=Bits::binary(Op::Xor,Bits::read({0}),Bits::read({1}));
 distribution(3,3,{2,1,0},{Step::map(H,{0}),Step::map(H,{1}),Step::measure(0,0),Step::measure(1,1),Step::branch(parity,{Step::map(X,{2})}),Step::measure(2,2)},{{0,"1/4"},{5,"1/4"},{6,"1/4"},{3,"1/4"}});
 distribution(2,2,{1,0},{Step::map(H,{0}),Step::map(CX,{0,1}),Step::measure(0,0),Step::assign({0},Bits::constant(1,0)),Step::measure(1,1)},{{0,"1/2"},{2,"1/2"}});
 distribution(0,64,{63},{Step::assign({63},Bits::constant(1,1))},{{1,"1"}});
 // A body can overwrite the condition without changing the chosen path.
 distribution(0,2,{1,0},{Step::assign({0},Bits::constant(1,1)),Step::branch(Bits::read({0}),{Step::assign({0},Bits::constant(1,0)),Step::assign({1},Bits::constant(1,1))})},{{2,"1"}});
 distribution(0,1,{0},{Step::branch(Bits::constant(1,0),{},{Step::assign({0},Bits::constant(1,1))})},{{1,"1"}});
 rejects<std::invalid_argument>([&]{evaluateCircuit(0,2,{Step::assign({0},Bits::constant(2,0))},1,exact);});
 rejects<std::invalid_argument>([&]{evaluateCircuit(0,2,{Step::assign({0,0},Bits::constant(2,0))},1,exact);});
 rejects<std::out_of_range>([&]{evaluateCircuit(0,1,{Step::assign({1},Bits::constant(1,0))},1,exact);});
 rejects<std::out_of_range>([&]{evaluateCircuit(0,1,{Step::assign({0},Bits::read({1}))},1,exact);});
 rejects<std::invalid_argument>([&]{evaluateCircuit(0,2,{Step::branch(Bits::read({0,1}),{})},1,exact);});
 rejects<std::out_of_range>([&]{evaluateCircuit(0,1,{Step::branch(Bits::read({1}),{})},1,exact);});
 rejects<std::out_of_range>([&]{evaluateCircuit(0,1,{Step::branch(Bits::constant(1,0),{Step::assign({1},Bits::constant(1,0))})},1,exact);});
 // Reversed, non-adjacent targets retain caller ordering.
 distribution(3,2,{1,0},{Step::map(X,{2}),Step::map(CX,{2,0}),Step::measure(0,0),Step::measure(2,1)},{{3,"1"}});
 // Resetting one half of an entangled state preserves the other's mixture.
 distribution(2,1,{0},{Step::map(H,{0}),Step::map(CX,{0,1}),Step::reset(0),Step::measure(1,0)},{{0,"1/2"},{1,"1/2"}});
 distribution(1,1,{0},{Step::map(rotation,{0}),Step::measure(0,0)},{{0,"cos(x/2)^2"},{1,"sin(x/2)^2"}});
 TracePreservingMap damping({calc("[1,0;0,sqrt(3)/2]"),calc("[0,1/2;0,0]")},8,exact);
 distribution(1,1,{0},{Step::map(X,{0}),Step::map(damping,{0}),Step::measure(0,0)},{{0,"1/4"},{1,"3/4"}});
 ReadoutAssignment symbolic({0},calc("[cos(x)^2,sin(x)^2;sin(x)^2,cos(x)^2]"),exact);
 distribution(1,2,{1,0},{Step::readout(symbolic),Step::branch(1,1,{Step::map(X,{0})}),Step::measure(0,1)},{{0,"cos(x)^2"},{3,"sin(x)^2"}});
 distribution(0,0,{}, {},{{0,"1"}});
 MathStructure singleton;singleton.clearMatrix();singleton.resizeMatrix(1,1,calc("exp(i*x)"));
 TracePreservingMap globalPhase({singleton},1,exact);
 distribution(0,0,{}, {Step::map(globalPhase,{})},{{0,"1"}});
 std::vector<Step> body={Step::map(X,{0}),Step::measure(0,0)};
 auto snapshot=Step::branch(0,0,body);body.clear();distribution(1,1,{0},{snapshot},{{1,"1"}});
 rejects<std::out_of_range>([&]{evaluateCircuit(11,0,{},65536,exact);});
 rejects<std::out_of_range>([&]{evaluateCircuit(1,65,{},65536,exact);});
 rejects<std::length_error>([&]{evaluateCircuit(1,1,{},3,exact);});
 rejects<std::length_error>([&]{evaluateCircuit(1,1,{Step::map(H,{0}),Step::measure(0,0)},4,exact);});
 rejects<std::invalid_argument>([&]{evaluateCircuit(1,1,{Step::map(X,{})},16,exact);});
 rejects<std::invalid_argument>([&]{evaluateCircuit(2,1,{Step::map(CX,{0,0})},16,exact);});
 rejects<std::out_of_range>([&]{evaluateCircuit(1,1,{Step::map(X,{1})},16,exact);});
 rejects<std::out_of_range>([&]{evaluateCircuit(1,1,{Step::measure(0,1)},16,exact);});
 rejects<std::out_of_range>([&]{evaluateCircuit(0,1,{Step::reset(0)},16,exact);});
 rejects<std::out_of_range>([&]{evaluateCircuit(1,0,{Step::readout(symbolic)},16,exact);});
 rejects<std::invalid_argument>([&]{evaluateCircuit(1,1,{Step::branch(2,0,{})},16,exact);});
 rejects<std::invalid_argument>([&]{evaluateCircuit(1,1,{Step::branch(1,2,{})},16,exact);});
 rejects<std::out_of_range>([&]{evaluateCircuit(1,1,{Step::branch(1,1,{Step::reset(1)})},16,exact);});
 std::vector<Step> nested;
 for(unsigned k=0;k<32;++k){std::vector<Step> next={Step::branch(0,0,nested)};nested.swap(next);}
 distribution(0,0,{},nested,{{0,"1"}});
 rejects<std::length_error>([&]{evaluateCircuit(0,0,{Step::branch(0,0,nested)},1,exact);});
 std::vector<Step> wide(512,Step::reset(0));distribution(1,0,{},wide,{{0,"1"}});
 wide.push_back(Step::reset(0));rejects<std::length_error>([&]{evaluateCircuit(1,0,wide,4,exact);});
 RecordAccumulator accumulator(1,1,4,exact);accumulator.add(0,calc("[1,0;0,0]"));
 rejects<std::out_of_range>([&]{accumulator.add(2,calc("[1,0;0,0]"));});
 const auto cancellationDensity=calc("[1,0;0,0]");
 calculator.startControl();calculator.abort();
 rejects<std::runtime_error>([&]{evaluateCircuit(1,1,{Step::map(H,{0})},8,exact);});
 rejects<std::runtime_error>([&]{accumulator.add(0,cancellationDensity);});calculator.stopControl();
 equal(weights(accumulator.take(),1,1,{},4,exact).at(0),"1");
 std::cout<<"PASS: "<<checks<<" exact circuit checks.\n";return 0;
 }catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
