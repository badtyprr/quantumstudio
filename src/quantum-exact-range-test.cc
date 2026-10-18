// GPL-2.0-or-later; see COPYING.
#include "libqalculate/QuantumExactCircuit.h"
#include "libqalculate/Calculator.h"
#include <iostream>
using namespace QuantumClassical;using namespace QuantumExact;
using Step=CircuitStep;using Expr=IntegerExpression;using Type=QuantumClassical::IntegerType;using Sign=Integer::Signedness;
unsigned checks=0;EvaluationOptions exact;
void check(bool ok){++checks;if(!ok)throw std::runtime_error("Exact range check failed: "+std::to_string(checks));}
template<class E,class F>void reject(F f){bool caught=false;try{f();}catch(const E&){caught=true;}check(caught);}
MathStructure calc(const std::string &text){return CALCULATOR->calculate(text,exact);}
int main(){try {
 Calculator calculator;check(calculator.loadGlobalDefinitions());exact.approximation=APPROXIMATION_EXACT;
 const auto machine=Type::machine(Sign::Signed);
 auto literal=[&](std::uint64_t n){return Expr::constant(TypedInteger::fromBits(machine,n));};
 auto range=[&](std::uint64_t first,std::uint64_t last,std::uint64_t step){return RangeExpression(literal(first),literal(last),literal(step));};
 const auto binding=Expr::variable(machine,0),sum=Expr::variable(machine,1),stop=Expr::variable(machine,2);
 auto run=[&](const std::vector<Step> &steps,std::size_t budget=1000,std::size_t cells=256) {
  return weights(evaluateCircuit(0,2,steps,{machine,machine,machine},cells,exact,budget),0,2,{1,0},cells,exact);
 };
 auto distribution=[&](const std::vector<Step> &steps,std::map<std::uint64_t,std::string> expected,std::size_t budget=1000) {
  auto result=run(steps,budget);check(result.size()==expected.size());
  for(const auto &item:expected){auto difference=result.at(item.first);difference-=calc(item.second);difference.eval(exact);check(difference.isZero());}
 };
 const auto one=Step::assign({0},Bits::constant(1,1)),zero=Step::assign({0},Bits::constant(1,0));
 const auto add=Step::storeInteger(1,Expr::binary(Integer::Operation::Add,sum,binding));
 auto emit=[&](unsigned n){return Step::assign({0},Bits::integerCompare(Bits::Binary::Equal,sum,literal(n)));};
 auto total=[&](RangeExpression bounds,std::vector<Step> body,unsigned n) {
  distribution({Step::storeInteger(1,literal(0)),Step::forRange(0,bounds,body),emit(n)},{{1,"1"}});
 };
 total(range(0,3,1),{add},6);total(range(0,5,2),{add},6);
 total(range(5,0,~std::uint64_t(1)),{add},9);total(range(3,0,1),{add},0);
 total(range(0,3,1),{add,Step::storeInteger(0,literal(99))},6);
 total(range(0,3,1),{Step::branch(Bits::integerCompare(Bits::Binary::Equal,binding,literal(1)),{Step::continueLoop()}),add},5);
 total(range(0,3,1),{add,Step::breakLoop(),Step::storeInteger(1,literal(99))},0);
 total(range(0,3,1),{add,Step::whileLoop(Bits::constant(1,1),{Step::breakLoop()})},6);
 total(range(0,3,1),{add,Step::forRange(2,range(0,2,1),{Step::breakLoop()})},6);
 distribution({Step::storeInteger(1,literal(0)),Step::storeInteger(2,literal(3)),Step::forRange(0,RangeExpression(literal(0),stop,literal(1)),{add,Step::storeInteger(2,literal(0))}),emit(6)},{{1,"1"}});
 distribution({Step::forRange(0,range(0,3,1),{one,Step::endProgram(),zero}),zero},{{1,"1"}},1);
 distribution({Step::forRange(0,range(0,3,1),{Step::breakLoop()})},{{0,"1"}},1);
 reject<std::length_error>([&]{run({Step::forRange(0,range(0,2,1),{})},3);});
 distribution({Step::forRange(0,range(0,2,1),{})},{{0,"1"}},4);
 reject<std::length_error>([&]{run({Step::forRange(0,range(1,0,1),{})},0);});
 distribution({Step::forRange(0,range(1,0,1),{})},{{0,"1"}},1);
 reject<std::length_error>([&]{run({Step::forRange(0,range(0,0,1),{Step::whileLoop(Bits::constant(1,0),{})})},2);});
 distribution({Step::forRange(0,range(0,0,1),{Step::whileLoop(Bits::constant(1,0),{})})},{{0,"1"}},3);
 for(auto bounds:{range(0,0,1),range(1,0,1)})reject<std::domain_error>([&]{run({Step::forRange(0,bounds,{}),Step::storeInteger(1,binding)});});
 reject<std::domain_error>([&]{run({Step::forRange(0,range(0,2,1),{Step::breakLoop()}),Step::storeInteger(1,binding)});});
 reject<std::invalid_argument>([&]{run({Step::forRange(0,range(0,1,0),{})});});
 reject<std::domain_error>([&]{run({Step::forRange(0,RangeExpression(stop,literal(1),literal(1)),{})});});
 reject<std::out_of_range>([&]{run({Step::branch(Bits::constant(1,0),{Step::forRange(3,range(0,1,1),{})})});});
 reject<std::out_of_range>([&]{run({Step::forRange(0,range(1,0,1),{Step::measure(0,0)})});});
 std::vector<Step> nested;for(unsigned n=0;n<33;++n)nested=std::vector<Step>{Step::forRange(0,range(1,0,1),nested)};
 reject<std::length_error>([&]{run(nested);});
 const auto coin=Step::readout(ReadoutAssignment({0},calc("[1/2,1/2;1/2,1/2]"),exact));
 const auto bit=Expr::read(Type::sized(Sign::Unsigned,1),{0});
 // Both histories become visibly identical after the first iteration. Their
 // captured end values differ; merging before exhaustion would lose that fact.
 distribution({coin,Step::storeInteger(1,literal(0)),Step::forRange(0,RangeExpression(literal(0),bit,literal(1)),
               {Step::storeInteger(1,Expr::binary(Integer::Operation::Add,sum,literal(1))),zero}),
               Step::assign({1},Bits::integerCompare(Bits::Binary::Equal,sum,literal(2)))},{{0,"1/2"},{2,"1/2"}});
 distribution({coin,Step::forRange(0,range(0,2,1),{Step::branch(Bits::read({0}),{Step::endProgram()})}),zero},{{0,"1/2"},{1,"1/2"}});
 // Measurement histories born inside a loop retain full probability mass.
 distribution({Step::forRange(0,range(0,2,1),{coin,Step::branch(Bits::read({0}),{Step::breakLoop()})})},{{0,"1/8"},{1,"7/8"}});
 reject<std::length_error>([&]{run({Step::forRange(0,range(0,0,1),{coin})},2);});
 distribution({Step::forRange(0,range(0,0,1),{coin})},{{0,"1/2"},{1,"1/2"}},3);
 reject<std::length_error>([&]{run({Step::forRange(0,range(0,0,1),{coin})},100,3);});
 calculator.startControl(20);
 reject<std::runtime_error>([&]{run({Step::forRange(0,range(0,1000000000,1),{})},1000000001);});
 calculator.stopControl();
 std::cout<<"PASS: "<<checks<<" exact range checks.\n";
}catch(const std::exception &error){std::cerr<<error.what()<<'\n';return 1;}}
