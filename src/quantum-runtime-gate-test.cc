// GPL-2.0-or-later; see COPYING.
#include "libqalculate/QuantumTrajectory.h"
#include "libqalculate/QuantumExactCircuit.h"
#include "libqalculate/Calculator.h"
#include "libqalculate/QuantumClassicalIntegerStorage.h"
#include <cmath>
#include <iostream>
using namespace QuantumNumerics;
using namespace QuantumClassical;
using G=RuntimeGate;using K=G::Kind;using R=RealExpression;
unsigned checks=0;
void check(bool value){++checks;if(!value)throw std::runtime_error("Runtime gate check "+std::to_string(checks));}
template<class E,class F>void reject(F f){bool caught=false;try{f();}catch(const E&){caught=true;}check(caught);}
void closeComplex(Complex a,Complex b){check(std::abs(a-b)<1e-12);}
int main(){try {
 Calculator calculator;check(calculator.loadGlobalDefinitions());EvaluationOptions exact;exact.approximation=APPROXIMATION_EXACT;
 const double pi=std::acos(-1.0),h=std::sqrt(.5);IntegerStorage empty({});
 auto matrix=[&](K k,std::vector<R> p,unsigned controls=0,unsigned state=0,int power=1){return G(k,p,controls,state,power).evaluate(0,0,empty).matrix();};
 // Controlled P is not controlled Rz: compare every matrix entry, including
 // the control-zero sector, rather than only computational-basis probabilities.
 auto p=matrix(K::Phase,{R::constant(pi)},1,1);auto z=matrix(K::Z,{R::constant(pi)},1,1);
 for(unsigned r=0;r<4;++r)for(unsigned c=0;c<4;++c)closeComplex(p[r*4+c],r==c ? (r==3 ? -1 : 1) : 0);
 closeComplex(z[10],Complex(0,-1));closeComplex(z[15],Complex(0,1));closeComplex(z[0],1);
 auto global=matrix(K::GlobalPhase,{R::constant(pi)},2,1);
 for(unsigned r=0;r<4;++r)for(unsigned c=0;c<4;++c)closeComplex(global[r*4+c],r==c ? (r==1 ? -1 : 1) : 0);
 // Mixed controls 01 activate exactly their two-dimensional block.
 auto mixed=matrix(K::Y,{R::constant(pi)},2,1);
 for(unsigned r=0;r<8;++r)for(unsigned c=0;c<8;++c) {
  Complex expected=(r==c && (r<2 || r>3)) ? 1 : 0;
  if(r==2 && c==3)expected=-1;if(r==3 && c==2)expected=1;
  closeComplex(mixed[r*8+c],expected);
 }
 // U3's three parameters have independent effects. The published convention
 // multiplies the active block by exp(i theta/2), not the identity block.
 auto u=matrix(K::U3,{R::constant(pi/2),R::constant(pi),R::constant(pi/2)},1,1);
 auto published=matrix(K::PublishedU,{R::constant(pi/2),R::constant(pi),R::constant(pi/2)},1,1);
 const std::vector<Complex> expected={h,Complex(0,-h),-h,Complex(0,-h)};
 for(unsigned r=0;r<2;++r)for(unsigned c=0;c<2;++c) {
  closeComplex(u[(r+2)*4+c+2],expected[r*2+c]);
  closeComplex(published[(r+2)*4+c+2],expected[r*2+c]*Complex(h,h));
 }
 closeComplex(published[0],1);closeComplex(published[5],1);
 auto inverse=matrix(K::U3,{R::constant(pi/2),R::constant(pi),R::constant(pi/2)},1,1,-1);
 for(unsigned r=0;r<4;++r)for(unsigned c=0;c<4;++c) {
  Complex entry=0;for(unsigned k=0;k<4;++k)entry+=u[r*4+k]*inverse[k*4+c];closeComplex(entry,r==c ? 1 : 0);
 }
 for(int power:{-64,0,64}) {
  auto m=matrix(K::Phase,{R::constant(pi/2)},0,0,power);closeComplex(m[0],1);closeComplex(m[3],1);
 }
 reject<std::invalid_argument>([&]{G(K::U3,{R::constant(1)});});
 reject<std::out_of_range>([&]{G(K::Phase,{R::constant(1)},1,2);});
 reject<std::length_error>([&]{G(K::Phase,{R::constant(1)},3,0);});
 reject<std::out_of_range>([&]{G(K::Phase,{R::constant(1)},0,0,65);});
 auto bad=R::binary(R::Operation::Divide,R::constant(1),R::constant(0));
 reject<std::domain_error>([&]{matrix(K::U3,{R::constant(0),R::constant(0),bad},0,0,0);});
 using T=TrajectoryStep;using S=QuantumExact::CircuitStep;
 const std::vector<Complex> H={h,h,h,-h};
 auto value=R::fromInteger(IntegerExpression::variable(QuantumClassical::IntegerType::machine(Integer::Signedness::Signed),0));
 G phase(K::GlobalPhase,{value},1,1);
 auto type=QuantumClassical::IntegerType::machine(Integer::Signedness::Signed);
 IntegerStorage powers({type});auto exponent=IntegerExpression::variable(type,0);
 G powered(K::Phase,{R::constant(pi/2)},0,0,exponent);
 for(unsigned k:{0U,1U,2U,64U}) {
  powers.write(0,TypedInteger::fromBits(type,k));auto m=powered.evaluate(0,0,powers).matrix();
  closeComplex(m[3],Complex(std::cos(k*pi/2),std::sin(k*pi/2)));
 }
 powers.write(0,TypedInteger::fromBits(type,65));reject<std::out_of_range>([&]{powered.evaluate(0,0,powers);});
 powers.clear(0);reject<std::domain_error>([&]{powered.evaluate(0,0,powers);});
 auto literal=IntegerExpression::constant(TypedInteger::fromBits(type,1));
 auto sampled=sampleTrajectories(1,1,10000,731,{0},{T::storeInteger(0,literal),T::gate(H,{0}),T::parameterized(phase,{0}),T::gate(H,{0}),T::measure(0,0)},{type},65536);
 check(std::abs(double(sampled[1])/10000-std::pow(std::sin(.5),2))<.02);
 QuantumExact::TracePreservingMap exactH({calculator.calculate("[1,1;1,-1]/sqrt(2)",exact)},4,exact);
 auto records=QuantumExact::evaluateCircuit(1,1,{S::storeInteger(0,literal),S::map(exactH,{0}),S::parameterized(phase,{0}),S::map(exactH,{0}),S::measure(0,0)},{type},65536,exact);
 auto probabilities=QuantumExact::weights(records,1,1,{0},65536,exact);
 auto difference=probabilities.at(1);difference-=calculator.calculate("(2-exp(i)-exp(-i))/4",exact);difference.eval(exact);check(difference.isZero());
 reject<std::domain_error>([&]{sampleTrajectories(1,1,1,1,{0},{T::parameterized(phase,{0})},{type},65536);});
 reject<std::invalid_argument>([&]{T::parameterized(phase,{});});
 std::cout<<"PASS: "<<checks<<" runtime gate checks.\n";
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
