// GPL-2.0-or-later; see COPYING.
#include "libqalculate/QuantumExactCircuit.h"
#include "libqalculate/Calculator.h"
#include <iostream>
using namespace QuantumExact;
using namespace QuantumClassical;
using Rotation=QuantumNumerics::RuntimeRotation;
using Axis=Rotation::Axis;using S=CircuitStep;using R=RealExpression;
unsigned checks=0;EvaluationOptions exact;
void check(bool ok){++checks;if(!ok)throw std::runtime_error("Exact runtime rotation check "+std::to_string(checks));}
template<class E,class F>void reject(F f){bool caught=false;try{f();}catch(const E&){caught=true;}check(caught);}
MathStructure calc(const std::string &text){return CALCULATOR->calculate(text,exact);}
void equal(MathStructure value,const std::string &expected){value-=calc(expected);value.eval(exact);if(!value.isZero())std::cerr<<value.print()<<'\n';check(value.isZero());}
int main(){try {
 Calculator calculator;check(calculator.loadGlobalDefinitions());exact.approximation=APPROXIMATION_EXACT;
 auto type=QuantumClassical::IntegerType::machine(Integer::Signedness::Signed);
 auto literal=[&](unsigned n){return IntegerExpression::constant(TypedInteger::fromBits(type,n));};
 auto variable=R::fromInteger(IntegerExpression::variable(type,0));
 auto measured=R::fromInteger(IntegerExpression::read(QuantumClassical::IntegerType::sized(Integer::Signedness::Unsigned,1),{0}));
 TracePreservingMap H({calc("[1,1;1,-1]/sqrt(2)")},4,exact);
 auto run=[&](const std::vector<S> &steps) {
  return weights(evaluateCircuit(2,2,steps,{type},65536,exact),2,2,{0,1},65536,exact);
 };
 for(auto axis:{Axis::X,Axis::Y}) {
  auto result=run({S::map(H,{0}),S::measure(0,0),S::rotate(Rotation(axis,measured),1),S::measure(1,1)});
  check(result.size()==3);equal(result.at(0),"1/2");
  equal(result.at(2),"cos(1/2)^2/2");equal(result.at(3),"sin(1/2)^2/2");
 }
 auto rotation=S::rotate(Rotation(Axis::Y,variable),0);
 auto result=run({S::storeInteger(0,literal(0)),rotation,S::storeInteger(0,literal(1)),rotation,S::measure(0,0)});
 equal(result.at(0),"cos(1/2)^2");equal(result.at(2),"sin(1/2)^2");
 result=run({S::forRange(0,RangeExpression(literal(0),literal(1),literal(1)),{rotation}),S::measure(0,0)});
 equal(result.at(0),"cos(1/2)^2");equal(result.at(2),"sin(1/2)^2");
 // Phase interference checks Rz, whose basis probabilities alone are unchanged.
 result=run({S::storeInteger(0,literal(1)),S::map(H,{0}),S::rotate(Rotation(Axis::Z,variable),0),S::map(H,{0}),S::measure(0,0)});
 // Interference probabilities in exponential form avoid requiring the
 // unrelated simplifier to prove Euler's identity against cos(theta/2)^2.
 equal(result.at(0),"(2+exp(i)+exp(-i))/4");equal(result.at(2),"(2-exp(i)-exp(-i))/4");
 // 0.1 must retain its binary64 value, not become the decimal rational 1/10.
 result=run({S::rotate(Rotation(Axis::Y,R::constant(0.1)),0),S::measure(0,0)});
 equal(result.at(2),"sin(3602879701896397/72057594037927936)^2");
 // Calculator entry preferences must not reinterpret generated internal numbers.
 auto preferences=exact;preferences.parse_options.base=16;
 preferences.parse_options.angle_unit=ANGLE_UNIT_DEGREES;
 auto records=evaluateCircuit(2,2,{S::rotate(Rotation(Axis::Y,R::constant(10)),0),S::measure(0,0)},
  {type},65536,preferences);
 auto preferred=weights(records,2,2,{0,1},65536,exact);
 equal(preferred.at(2),"sin(5)^2");
 reject<std::domain_error>([&]{run({rotation});});
 result=run({S::branch(1,1,{rotation})});equal(result.at(0),"1");
 auto absent=R::fromInteger(IntegerExpression::variable(type,1));
 reject<std::out_of_range>([&]{run({S::branch(1,1,{S::rotate(Rotation(Axis::X,absent),0)})});});
 reject<std::out_of_range>([&]{run({S::rotate(Rotation(Axis::Y,R::constant(0)),2)});});
 auto bad=R::binary(R::Operation::Divide,R::constant(1),R::constant(0));
 reject<std::domain_error>([&]{run({S::rotate(Rotation(Axis::Y,bad),0)});});
 std::cout<<"PASS: "<<checks<<" exact runtime rotation checks.\n";
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
