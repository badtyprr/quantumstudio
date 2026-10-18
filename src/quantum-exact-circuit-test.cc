#include "libqalculate/QuantumClassicalIntegerExpression.h"
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
 using Int=QuantumClassical::Integer;using Type=QuantumClassical::IntegerType;using Expr=QuantumClassical::IntegerExpression;
 auto signedByte=Type::sized(Int::Signedness::Signed,8),machine=Type::machine(Int::Signedness::Signed);
 auto variable=Expr::read(signedByte,{0,1,2,3,4,5,6,7});
 auto literal=[&](std::uint64_t n){return Expr::constant(QuantumClassical::TypedInteger::fromBits(machine,n));};
 {
 auto yes=Bits::constant(1,1),no=Bits::constant(1,0);
 auto emit=Step::assign({0},yes),clear=Step::assign({0},no);
 auto slot=Expr::variable(signedByte,0);
 auto positive=Bits::integerCompare(Op::Greater,slot,literal(0));
 auto decrement=Step::storeInteger(0,Expr::binary(Int::Operation::Subtract,slot,literal(1)));
 auto run=[&](const std::vector<Step> &program,std::size_t budget=8) {
  return weights(evaluateCircuit(0,1,program,{signedByte},64,exact,budget),0,1,{0},64,exact);
 };
 for(auto transfer:{Step::breakLoop(),Step::continueLoop()}) {
  rejects<std::invalid_argument>([&]{run({transfer});});
  rejects<std::invalid_argument>([&]{run({Step::branch(no,{transfer})},0);});
  rejects<std::out_of_range>([&]{run({Step::whileLoop(no,{transfer,Step::storeInteger(1,literal(0))})},1);});
 }
 equal(run({Step::whileLoop(yes,{Step::breakLoop(),emit})},1).at(0),"1");
 equal(run({Step::whileLoop(yes,{Step::breakLoop()}),emit},1).at(1),"1");
 rejects<std::length_error>([&]{run({Step::whileLoop(yes,{Step::breakLoop()})},0);});
 equal(run({Step::whileLoop(yes,{Step::branch(yes,{Step::breakLoop()}),Step::whileLoop(yes,{})})},1).at(0),"1");
 auto once=Step::whileLoop(Bits::complement(Bits::read({0})),{emit,Step::continueLoop(),clear});
 equal(run({once},2).at(1),"1");
 rejects<std::length_error>([&]{run({once},1);});
 equal(run({Step::storeInteger(0,literal(3)),Step::whileLoop(positive,{decrement,Step::branch(yes,{Step::continueLoop()}),emit})},4).at(0),"1");
 equal(run({Step::storeInteger(0,literal(2)),Step::whileLoop(positive,{Step::whileLoop(yes,{Step::breakLoop()}),decrement}),emit},5).at(1),"1");
 equal(run({Step::storeInteger(0,literal(1)),Step::whileLoop(positive,{once,decrement,clear})},4).at(0),"1");
 rejects<std::length_error>([&]{run({Step::whileLoop(yes,{Step::continueLoop()})},3);});
 // Matching classical bits and variables must not merge pending break with
 // fallthrough. Each half of this measured mixture follows a different suffix.
 distribution(1,1,{0},{Step::map(H,{0}),Step::measure(0,0),Step::whileLoop(yes,{
  Step::branch(Bits::read({0}),{clear,Step::breakLoop()},{clear}),
  Step::map(X,{0}),Step::measure(0,0),Step::breakLoop()})},{{0,"1/2"},{1,"1/2"}});
 distribution(1,1,{0},{Step::map(rotation,{0}),Step::measure(0,0),Step::whileLoop(yes,{
  Step::branch(Bits::read({0}),{clear,Step::breakLoop()},{clear}),
  Step::map(X,{0}),Step::measure(0,0),Step::breakLoop()})},{{0,"sin(x/2)^2"},{1,"cos(x/2)^2"}});
 auto mixed=evaluateCircuit(1,1,{Step::storeInteger(0,literal(1)),Step::map(H,{0}),Step::measure(0,0),
  Step::whileLoop(positive,{decrement,Step::branch(Bits::read({0}),{clear,Step::continueLoop()},{clear}),emit})},
  {signedByte},64,exact,4);
 auto outcome=weights(mixed,1,1,{0},64,exact);check(outcome.size()==2);
 equal(outcome.at(0),"1/2");equal(outcome.at(1),"1/2");
 // Pending transfers bypass even a nested loop's undefined condition.
 rejects<std::length_error>([&]{run({Step::whileLoop(yes,{Step::branch(yes,{Step::continueLoop()}),Step::whileLoop(positive,{})})},2);});
 }
 {
 auto yes=Bits::constant(1,1),no=Bits::constant(1,0);
 auto slot=Expr::variable(signedByte,0);
 auto positive=Bits::integerCompare(Op::Greater,slot,literal(0));
 auto decrement=Step::storeInteger(0,Expr::binary(Int::Operation::Subtract,slot,literal(1)));
 auto emit=Step::assign({0},yes);
 auto run=[&](const std::vector<Step> &program,std::size_t budget) {
  return weights(evaluateCircuit(0,1,program,{signedByte},64,exact,budget),0,1,{0},64,exact);
 };
 auto countdown=Step::whileLoop(positive,{decrement,emit});
 equal(run({Step::storeInteger(0,literal(3)),countdown},4).at(1),"1");
 rejects<std::length_error>([&]{run({Step::storeInteger(0,literal(3)),countdown},3);});
 equal(run({Step::storeInteger(0,literal(0)),countdown},1).at(0),"1");
 equal(run({Step::whileLoop(no,{Step::storeInteger(0,slot)})},1).at(0),"1");
 rejects<std::domain_error>([&]{run({countdown},4);});
 rejects<std::domain_error>([&]{run({Step::storeInteger(0,literal(1)),Step::whileLoop(positive,{Step::clearInteger(0)})},4);});
 rejects<std::length_error>([&]{run({Step::whileLoop(yes,{})},3);});
 rejects<std::length_error>([&]{run({Step::whileLoop(no,{})},0);});
 equal(run({},0).at(0),"1");
 equal(run({Step::branch(no,{Step::whileLoop(yes,{})})},0).at(0),"1");
 auto nested=Step::whileLoop(positive,{Step::whileLoop(no,{}),decrement});
 equal(run({Step::storeInteger(0,literal(2)),nested},5).at(0),"1");
 rejects<std::length_error>([&]{run({Step::storeInteger(0,literal(2)),nested},4);});
 rejects<std::out_of_range>([&]{run({Step::whileLoop(no,{Step::storeInteger(1,literal(0))})},1);});
 rejects<std::invalid_argument>([&]{run({Step::whileLoop(Bits::constant(2,0),{})},1);});
 rejects<std::out_of_range>([&]{run({Step::whileLoop(Bits::read({1}),{})},1);});
 std::vector<Step> mutableBody={emit,Step::assign({1},no)};
 auto snapshot=Step::whileLoop(Bits::read({1}),mutableBody);mutableBody.clear();
 distribution(0,2,{0},{Step::assign({1},yes),snapshot},{{1,"1"}});
 std::vector<Step> levels;
 for(unsigned k=0;k<32;++k){std::vector<Step> next={Step::whileLoop(no,levels)};levels.swap(next);}
 equal(run(levels,1).at(0),"1");
 rejects<std::length_error>([&]{run({Step::branch(no,levels)},1);});
 rejects<std::length_error>([&]{run({Step::whileLoop(no,std::vector<Step>(512,emit))},1);});
 auto measured=Expr::read(Type::sized(Int::Signedness::Unsigned,1),{0});
 // Histories leave the loop at different times. Matching output bits must not
 // merge distinct live variable values before each history has finished.
 std::vector<Step> history={Step::map(H,{0}),Step::measure(0,0),Step::storeInteger(0,measured),
  Step::assign({0},no),Step::reset(0),Step::whileLoop(positive,{Step::map(X,{0}),decrement}),Step::measure(0,0)};
 auto result=weights(evaluateCircuit(1,1,history,{signedByte},16,exact,3),1,1,{0},16,exact);
 check(result.size()==2);equal(result.at(0),"1/2");equal(result.at(1),"1/2");
 rejects<std::length_error>([&]{evaluateCircuit(1,1,history,{signedByte},16,exact,2);});
 // New measurement histories inside the body are carried into the next test.
 std::vector<Step> repeated={Step::storeInteger(0,literal(2)),Step::whileLoop(positive,
  {Step::map(H,{0}),Step::measure(0,0),decrement})};
 result=weights(evaluateCircuit(1,1,repeated,{signedByte},16,exact,5),1,1,{0},16,exact);
 check(result.size()==2);equal(result.at(0),"1/2");equal(result.at(1),"1/2");
 rejects<std::length_error>([&]{evaluateCircuit(1,1,repeated,{signedByte},16,exact,4);});
 distribution(1,1,{0},{Step::assign({0},yes),Step::whileLoop(Bits::read({0}),
  {Step::map(rotation,{0}),Step::assign({0},no)}),Step::measure(0,0)},{{0,"cos(x/2)^2"},{1,"sin(x/2)^2"}});
 // Almost-sure termination has infinite exact support: never silently return
 // the exited probability mass as a complete normalized result.
 rejects<std::length_error>([&]{evaluateCircuit(1,1,{Step::whileLoop(Bits::complement(Bits::read({0})),
  {Step::map(H,{0}),Step::measure(0,0)})},{},16,exact,8);});
 calculator.startControl(20);
 rejects<std::runtime_error>([&]{evaluateCircuit(0,0,{Step::whileLoop(yes,{})},{},1,exact,std::size_t(-1));});
 calculator.stopControl();
 equal(run({},0).at(0),"1");
 }

 {
 rejects<std::length_error>([&]{evaluateCircuit(0,0,{},std::vector<Type>(2,signedByte),1,exact);});
 rejects<std::length_error>([&]{evaluateCircuit(1,1,{Step::map(H,{0}),Step::measure(0,0)},std::vector<Type>(5,signedByte),8,exact);});
 std::vector<Type> types={signedByte};auto slot=Expr::variable(signedByte,0);
 auto positive=Bits::integerCompare(Op::Greater,slot,literal(0));
 auto emit=Step::assign({0},Bits::constant(1,1));
 auto run=[&](const std::vector<Step> &program){return evaluateCircuit(0,1,program,types,64,exact);};
 equal(weights(run({Step::storeInteger(0,literal(3)),Step::branch(positive,{emit})}),0,1,{0},64,exact).at(1),"1");
 equal(weights(run({Step::storeInteger(0,literal(255)),Step::branch(positive,{emit})}),0,1,{0},64,exact).at(0),"1");
 equal(weights(run({Step::storeInteger(0,literal(3)),Step::storeInteger(0,Expr::binary(Int::Operation::Subtract,slot,literal(5))),Step::branch(positive,{emit})}),0,1,{0},64,exact).at(0),"1");
 rejects<std::domain_error>([&]{run({Step::branch(positive,{emit})});});
 rejects<std::domain_error>([&]{run({Step::storeInteger(0,literal(1)),Step::clearInteger(0),Step::branch(positive,{emit})});});
 rejects<std::out_of_range>([&]{run({Step::branch(Bits::constant(1,0),{Step::storeInteger(1,literal(1))})});});
 rejects<std::invalid_argument>([&]{run({Step::storeInteger(0,Expr::variable(machine,0))});});
 equal(weights(run({Step::branch(Bits::constant(1,0),{Step::storeInteger(0,slot)})}),0,1,{0},64,exact).at(0),"1");
 auto measured=Expr::read(Type::sized(Int::Signedness::Unsigned,1),{0});
 std::vector<Step> program={Step::map(H,{0}),Step::measure(0,0),Step::storeInteger(0,measured),
  Step::assign({0},Bits::constant(1,0)),Step::reset(0)};
 auto marginal=evaluateCircuit(1,1,program,types,8,exact);
 check(marginal.size()==1);equal(weights(marginal,1,1,{0},8,exact).at(0),"1");
 program.push_back(Step::branch(positive,{Step::map(X,{0})}));program.push_back(Step::measure(0,0));
 auto output=weights(evaluateCircuit(1,1,program,types,8,exact),1,1,{0},8,exact);
 check(output.size()==2);equal(output.at(0),"1/2");equal(output.at(1),"1/2");
 rejects<std::length_error>([&]{evaluateCircuit(1,1,program,types,4,exact);});
 // Undefined and initialized-zero states cannot merge after erasing the bit.
 rejects<std::domain_error>([&]{evaluateCircuit(1,1,{Step::map(H,{0}),Step::measure(0,0),
  Step::branch(1,1,{Step::storeInteger(0,literal(0))}),Step::assign({0},Bits::constant(1,0)),Step::branch(positive,{})},types,8,exact);});
 // Clearing both histories permits merging within a two-record budget before
 // a new measurement splits them again.
 std::vector<Step> clearProgram={Step::map(H,{0}),Step::measure(0,0),Step::storeInteger(0,measured),
  Step::assign({0},Bits::constant(1,0)),Step::reset(0),Step::clearInteger(0),Step::map(H,{0}),Step::measure(0,0)};
 auto cleared=weights(evaluateCircuit(1,1,clearProgram,types,8,exact),1,1,{0},8,exact);
 check(cleared.size()==2);equal(cleared.at(0),"1/2");equal(cleared.at(1),"1/2");
 }
 auto negative=Bits::integerCompare(Op::Less,variable,literal(0));
 auto quotient=Expr::binary(Int::Operation::Divide,literal(6),variable);
 auto isThree=Bits::integerCompare(Op::Equal,quotient,literal(3));
 auto setOutput=Step::assign({8},Bits::constant(1,1));
 distribution(0,9,{8},{Step::assign({0,1,2,3,4,5,6,7},Bits::constant(8,255)),Step::branch(negative,{setOutput})},{{1,"1"}});
 distribution(0,9,{8},{Step::assign({0,1,2,3,4,5,6,7},Bits::constant(8,2)),Step::branch(isThree,{setOutput})},{{1,"1"}});
 distribution(0,9,{8},{Step::branch(Bits::constant(1,0),{Step::branch(isThree,{setOutput})})},{{0,"1"}});
 rejects<std::domain_error>([&]{evaluateCircuit(0,9,{Step::branch(isThree,{setOutput})},65536,exact);});
 rejects<std::out_of_range>([&]{evaluateCircuit(0,7,{Step::branch(Bits::constant(1,0),{Step::branch(negative,{})})},65536,exact);});

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
 }catch(const std::exception &e){std::cerr<<"After "<<checks<<" checks: "<<e.what()<<'\n';return 1;}}
