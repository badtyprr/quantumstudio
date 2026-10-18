// GPL-2.0-or-later; see COPYING.
#include "libqalculate/QuantumTrajectory.h"
#include <iostream>
#include <stdexcept>
using namespace QuantumClassical;
using namespace QuantumNumerics;
using Step=TrajectoryStep;using Expr=IntegerExpression;using Type=IntegerType;
using Sign=Integer::Signedness;using Op=Integer::Operation;
unsigned checks=0;
void check(bool ok){++checks;if(!ok)throw std::runtime_error("Trajectory range check failed: "+std::to_string(checks));}
template<class E,class F>void reject(F f){bool caught=false;try{f();}catch(const E&){caught=true;}check(caught);}
int main(){try {
 const auto machine=Type::machine(Sign::Signed);
 const auto binding=Expr::variable(machine,0),sum=Expr::variable(machine,1),stop=Expr::variable(machine,2);
 auto literal=[&](std::uint64_t n){return Expr::constant(TypedInteger::fromBits(machine,n));};
 auto range=[&](std::uint64_t start,std::uint64_t end,std::uint64_t step){return RangeExpression(literal(start),literal(end),literal(step));};
 auto add=Step::storeInteger(1,Expr::binary(Op::Add,sum,binding));
 auto emit=[&](unsigned n){return Step::assign({0},Bits::integerCompare(Bits::Binary::Equal,sum,literal(n)));};
 auto run=[&](std::vector<Step> body,std::size_t budget=1000,unsigned shots=10,const Cancellation &cancelled=Cancellation()) {
  return sampleTrajectories(0,1,shots,7,{0},body,{machine,machine,machine},16,cancelled,budget);
 };
 auto total=[&](RangeExpression bounds,std::vector<Step> body,unsigned expected) {
  check(run({Step::storeInteger(1,literal(0)),Step::forRange(0,bounds,body),emit(expected)}).at(1)==10);
 };
 total(range(0,3,1),{add},6);
 total(range(0,5,2),{add},6);
 total(range(5,0,~std::uint64_t(1)),{add},9);
 total(range(3,0,1),{add},0);
 total(range(0,3,~std::uint64_t(0)),{add},0);
 total(range(0,3,1),{add,Step::storeInteger(0,literal(99))},6);
 total(range(0,3,1),{Step::branch(Bits::integerCompare(Bits::Binary::Equal,binding,literal(1)),{Step::continueLoop()}),add},5);
 total(range(0,3,1),{add,Step::breakLoop(),Step::storeInteger(1,literal(99))},0);
 total(range(0,3,1),{add,Step::whileLoop(Bits::constant(1,1),{Step::breakLoop()})},6);
 total(range(0,3,1),{add,Step::forRange(2,range(0,2,1),{Step::breakLoop()})},6);
 check(run({Step::storeInteger(1,literal(0)),Step::storeInteger(2,literal(3)),
            Step::forRange(0,RangeExpression(literal(0),stop,literal(1)),{add,Step::storeInteger(2,literal(0))}),emit(6)}).at(1)==10);
 check(run({Step::storeInteger(1,literal(0)),Step::storeInteger(2,literal(1)),
            Step::forRange(0,RangeExpression(literal(0),literal(3),stop),{add,Step::storeInteger(2,literal(2))}),emit(6)}).at(1)==10);
 // The first shot's cursor and local binding must never leak to another shot.
 check(run({Step::storeInteger(1,literal(0)),Step::forRange(0,range(1,1,1),{add}),emit(1)},2,100).at(1)==100);
 reject<std::length_error>([&]{run({Step::forRange(0,range(0,2,1),{})},3);});
 check(run({Step::forRange(0,range(0,2,1),{})},4).at(0)==10);
 reject<std::length_error>([&]{run({Step::forRange(0,range(1,0,1),{})},0);});
 check(run({Step::forRange(0,range(1,0,1),{})},1).at(0)==10);
 check(run({Step::forRange(0,range(0,3,1),{Step::breakLoop()})},1).at(0)==10);
 reject<std::length_error>([&]{run({Step::forRange(0,range(0,0,1),{Step::whileLoop(Bits::constant(1,0),{})})},2);});
 check(run({Step::forRange(0,range(0,0,1),{Step::whileLoop(Bits::constant(1,0),{})})},3).at(0)==10);
 auto one=Step::assign({0},Bits::constant(1,1)),zero=Step::assign({0},Bits::constant(1,0));
 check(run({Step::forRange(0,range(0,3,1),{one,Step::endProgram(),zero}),zero},1).at(1)==10);
 for(auto bounds:{range(0,0,1),range(1,0,1)}) {
  reject<std::domain_error>([&]{run({Step::forRange(0,bounds,{}),Step::storeInteger(1,binding)});});
 }
 reject<std::domain_error>([&]{run({Step::forRange(0,range(0,2,1),{Step::breakLoop()}),Step::storeInteger(1,binding)});});
 reject<std::invalid_argument>([&]{run({Step::forRange(0,range(0,1,0),{})});});
 reject<std::domain_error>([&]{run({Step::forRange(0,RangeExpression(stop,literal(1),literal(1)),{})});});
 reject<std::out_of_range>([&]{run({Step::branch(Bits::constant(1,0),{Step::forRange(3,range(0,1,1),{})})},100,0);});
 reject<std::out_of_range>([&]{run({Step::forRange(0,RangeExpression(Expr::variable(machine,9),literal(1),literal(1)),{})},100,0);});
 reject<std::invalid_argument>([&]{run({Step::forRange(0,RangeExpression(Expr::variable(Type::sized(Sign::Signed,8),0),literal(1),literal(1)),{})},100,0);});
 check(run({Step::branch(Bits::constant(1,0),{Step::forRange(0,range(0,1,0),{})})},0).at(0)==10);
 reject<std::out_of_range>([&]{run({Step::forRange(0,range(1,0,1),{Step::measure(0,0)})},100,0);});
 unsigned calls=0;
 reject<Cancelled>([&]{run({Step::forRange(0,range(0,100000,1),{})},100000,1,[&]{return ++calls==100;});});
 std::vector<Step> nested;
 for(unsigned i=0;i<33;++i)nested=std::vector<Step>{Step::forRange(0,range(1,0,1),nested)};
 reject<std::length_error>([&]{run(nested,100,0);});
 auto unsigned64=Type::machine(Sign::Unsigned);
 auto u=[&](std::uint64_t n){return Expr::constant(TypedInteger::fromBits(unsigned64,n));};
 check(run({Step::forRange(0,RangeExpression(u(~std::uint64_t(1)),u(~std::uint64_t(0)),u(1)),{one})},3).at(1)==10);
 std::cout<<"PASS: "<<checks<<" trajectory range checks.\n";
}catch(const std::exception &error){std::cerr<<error.what()<<'\n';return 1;}}
