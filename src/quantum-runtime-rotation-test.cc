// GPL-2.0-or-later; see COPYING.
#include "libqalculate/QuantumTrajectory.h"
#include "libqalculate/QuantumClassicalIntegerStorage.h"
#include <cmath>
#include <iostream>
using namespace QuantumNumerics;
using namespace QuantumClassical;
using S=TrajectoryStep;using R=RealExpression;using A=RuntimeRotation::Axis;
unsigned checks=0;
void check(bool ok){++checks;if(!ok)throw std::runtime_error("Runtime rotation check "+std::to_string(checks));}
template<class E,class F>void reject(F f){bool caught=false;try{f();}catch(const E&){caught=true;}check(caught);}
int main(){try {
 const double pi=std::acos(-1.0),h=std::sqrt(.5);
 const std::vector<Complex> H={h,h,h,-h};
 auto type=IntegerType::machine(Integer::Signedness::Signed);
 auto literal=[&](unsigned n){return IntegerExpression::constant(TypedInteger::fromBits(type,n));};
 auto theta=R::binary(R::Operation::Multiply,R::constant(pi),R::fromInteger(IntegerExpression::variable(type,0)));
 IntegerStorage storage({type});storage.write(0,TypedInteger::fromBits(type,1));
 // Check complex phases directly: computational-basis measurements alone
 // would miss a wrong sign in Rx or Rz.
 for(auto axis:{A::X,A::Y,A::Z}) {
  auto m=RuntimeRotation(axis,theta).matrix(0,0,storage);
  std::vector<Complex> expected=axis==A::X ? std::vector<Complex>{0,Complex(0,-1),Complex(0,-1),0} :
   axis==A::Y ? std::vector<Complex>{0,-1,1,0} : std::vector<Complex>{Complex(0,-1),0,0,Complex(0,1)};
  for(unsigned i=0;i<4;++i)check(std::abs(m[i]-expected[i])<1e-14);
 }
 auto sample=[&](const std::vector<S> &steps,unsigned shots=1000){return sampleTrajectories(2,2,shots,731,{0,1},steps,{type},1024);};
 auto measured=R::binary(R::Operation::Multiply,R::constant(pi),R::fromInteger(IntegerExpression::read(IntegerType::sized(Integer::Signedness::Unsigned,1),{0})));
 for(auto axis:{A::X,A::Y}) {
  auto counts=sample({S::gate(H,{0}),S::measure(0,0),S::rotate(RuntimeRotation(axis,measured),1),S::measure(1,1)},10000);
  check(counts.size()==2);check(counts[0]+counts[3]==10000);check(std::abs(int(counts[0])-5000)<250);
 }
 // Repeated uses must re-read mutations instead of caching the first angle.
 auto rotation=S::rotate(RuntimeRotation(A::Y,theta),0);
 auto counts=sample({S::storeInteger(0,literal(0)),rotation,S::storeInteger(0,literal(1)),rotation,S::measure(0,0)});
 check(counts.size()==1 && counts[2]==1000);
 // Rz(pi) between Hadamards changes |0> to |1>.
 counts=sample({S::storeInteger(0,literal(1)),S::gate(H,{0}),S::rotate(RuntimeRotation(A::Z,theta),0),S::gate(H,{0}),S::measure(0,0)});
 check(counts.size()==1 && counts[2]==1000);
 reject<std::domain_error>([&]{sample({rotation});});
 // An unreachable body validates declarations, but never reads undefined slots.
 counts=sample({S::branch(1,1,{rotation})});check(counts[0]==1000);
 auto missing=R::fromInteger(IntegerExpression::variable(type,1));
 reject<std::out_of_range>([&]{sample({S::branch(1,1,{S::rotate(RuntimeRotation(A::X,missing),0)})});});
 reject<std::out_of_range>([&]{sample({S::rotate(RuntimeRotation(A::Y,R::constant(0)),2)});});
 reject<std::invalid_argument>([&]{RuntimeRotation(static_cast<A>(9),theta);});
 auto bad=R::binary(R::Operation::Divide,R::constant(1),R::constant(0));
 reject<std::domain_error>([&]{sample({S::rotate(RuntimeRotation(A::X,bad),0)});});
 // Every shot starts with fresh undefined variable storage.
 reject<std::domain_error>([&]{sample({rotation,S::storeInteger(0,literal(1))});});
 std::cout<<"PASS: "<<checks<<" runtime rotation checks.\n";
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
