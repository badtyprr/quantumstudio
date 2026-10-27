// GPL-2.0-or-later; see COPYING.
#include "libqalculate/Calculator.h"
#include "libqalculate/QuantumExactCircuit.h"
#include "libqalculate/QuantumTrajectory.h"
#include "libqalculate/QuantumClassicalIntegerStorage.h"
#include <iostream>
#include <cmath>
using R=QuantumClassical::RealExpression;using V=QuantumClassical::NumericValue;using T=QuantumClassical::NumericType;
using I=QuantumClassical::IntegerExpression;using B=QuantumClassical::Bits;using IT=QuantumClassical::IntegerType;
using TI=QuantumClassical::TypedInteger;using Sign=QuantumClassical::Integer::Signedness;
using E=QuantumExact::CircuitStep;using S=QuantumNumerics::TrajectoryStep;using G=QuantumNumerics::RuntimeGate;
unsigned checks=0;
void check(bool value){++checks;if(!value)throw std::runtime_error("Runtime numeric check "+std::to_string(checks));}
template<class Error,class F>void rejects(F f){bool caught=false;try{f();}catch(const Error&){caught=true;}check(caught);}
int main(){try {
 Calculator calculator;check(calculator.loadGlobalDefinitions());EvaluationOptions exact;exact.approximation=APPROXIMATION_EXACT;
 QuantumClassical::RuntimeStorage frame({}, {T::floating(32),T::angle(8)});
 auto f=R::variable(T::floating(32),0),a=R::variable(T::angle(8),1);
 f.validate(0,frame);rejects<std::domain_error>([&]{f.evaluateTyped(0,0,frame);});
 frame.numeric().write(0,V::floating(16777217));check(f.evaluateTyped(0,0,frame).floatingValue()==16777216);
 auto one=R::constant(V::floating(1,32));auto difference=R::binary(R::Operation::Subtract,R::binary(R::Operation::Add,f,one),f);
 check(difference.evaluateTyped(0,0,frame).floatingValue()==0);
 frame.numeric().write(1,V::fromBits(T::angle(8),128));check(a.evaluateTyped(0,0,frame).exactRadians()=="(2*pi*128/256)");
 auto integer=I::fromNumeric(IT::sized(Sign::Signed,32),f);check(integer.evaluate(0,0,frame).value().bits()==16777216);
 auto angleBits=B::fromInteger(I::angleBits(a));check(angleBits.evaluate(0,0,frame)==128);
 auto equal=B::integerCompare(B::Binary::Equal,I::numericCompare(a,R::constant(V::fromBits(T::angle(8),128))),I::constant(TI::fromBits(IT::machine(Sign::Signed),0)));
 check(equal.evaluate(0,0,frame)==1);
 auto ratio=I::angleRatio(a,R::constant(V::fromBits(T::angle(8),64)));check(ratio.evaluate(0,0,frame).value().bits()==2);
 auto bitsAngle=R::fromBits(8,B::constant(8,255));check(bitsAngle.evaluateTyped(0,0,frame).bits()==255);
 // Every cross-domain edge contributes to the existing expression limits.
 auto nested=R::constant(1.0);bool bounded=false;
 for(int k=0;k<40;k++){try{nested=R::fromInteger(I::fromNumeric(IT::machine(Sign::Signed),nested));}catch(const std::length_error&){bounded=true;break;}}
 check(bounded);
 auto falseCondition=B::logical(B::Binary::And,B::constant(1,0),B::integerCompare(B::Binary::Equal,I::fromNumeric(IT::machine(Sign::Signed),R::variable(T::floating(32),0)),I::constant(TI::fromBits(IT::machine(Sign::Signed),0))));
 frame.numeric().clear(0);check(falseCondition.evaluate(0,0,frame)==0);
 const auto h=calculator.calculate("quantum:H",exact);QuantumExact::TracePreservingMap H({h},4,exact);
 const double half=std::sqrt(.5);const std::vector<QuantumNumerics::Complex> sampleH={half,half,half,-half};
 for(bool modular:{false,true}) {
  const auto type=modular ? T::angle(8) : T::floating(32);
  const auto variable=R::variable(type,0);
  const auto measured=I::read(IT::sized(Sign::Unsigned,1),{0});
  const auto converted=modular ? R::scale(V::Scaling::Multiply,R::constant(V::fromBits(type,128)),I::cast(IT::sized(Sign::Unsigned,8),measured)) : R::fromInteger(measured,32);
  const auto parameter=modular ? variable : R::binary(R::Operation::Multiply,R::constant(std::acos(-1.0)),variable);
  G gate(G::Kind::Y,{parameter});
  // Erase both distinguishing quantum and classical measurement state before
  // consuming the stored value: only the numeric slot keeps histories distinct.
  std::vector<E> exactSteps={E::map(H,{0}),E::measure(0,0),E::storeNumeric(0,converted),E::reset(0),E::assign({0},B::constant(1,0)),E::parameterized(gate,{1}),E::measure(1,1)};
  auto outcomes=QuantumExact::evaluateCircuit(2,2,exactSteps,{},4096,exact,1000,{type});
  check(outcomes.size()==2);
  EvaluationOptions approximate=exact;approximate.approximation=APPROXIMATION_APPROXIMATE;
  auto probabilities=QuantumExact::weights(outcomes,2,2,{1,0},4096,exact);
  for(const auto &entry:probabilities){check(entry.first==0 || entry.first==2);auto probability=entry.second;probability.eval(approximate);check(probability.isNumber() && std::abs(probability.number().floatValue()-.5)<1e-12);}
  std::vector<S> sampledSteps={S::gate(sampleH,{0}),S::measure(0,0),S::storeNumeric(0,converted),S::reset(0),S::assign({0},B::constant(1,0)),S::parameterized(gate,{1}),S::measure(1,1)};
  auto counts=QuantumNumerics::sampleTrajectories(2,2,10000,731,{1},sampledSteps,{},65536,{},1000,{type});check(counts.size()==2);check(std::abs(static_cast<int>(counts[0])-5000)<200);
  std::vector<E> undefinedSteps={E::parameterized(gate,{1})};rejects<std::domain_error>([&]{QuantumExact::evaluateCircuit(2,2,undefinedSteps,{},4096,exact,1000,{type});});
 }
 std::vector<E> angleGate={E::storeNumeric(0,R::constant(V::fromBits(T::angle(8),128))),E::parameterized(G(G::Kind::Y,{R::variable(T::angle(8),0)}),{0}),E::measure(0,0)};
 auto exactAngle=QuantumExact::evaluateCircuit(1,1,angleGate,{},4096,exact,1000,{T::angle(8)});check(exactAngle.size()==1 && exactAngle.begin()->first==1);
 std::cout<<"PASS: "<<checks<<" runtime numeric integration checks.\n";return 0;
}catch(const std::exception &error){std::cerr<<error.what()<<'\n';return 1;}}
