#include "libqalculate/QuantumClassicalIntegerExpression.h"
// GPL-2.0-or-later; see COPYING.
#include "libqalculate/QuantumTrajectory.h"
#include <cmath>
#include <iostream>
using namespace QuantumNumerics;
namespace {
unsigned checks=0;
void check(bool value){++checks;if(!value)throw std::runtime_error("Trajectory regression failed");}
template<class E,class F>void rejects(F f){bool caught=false;try{f();}catch(const E &){caught=true;}check(caught);}
}
int main(){try {
 using Step=TrajectoryStep;const double h=std::sqrt(.5);
 const std::vector<Complex> H={h,h,h,-h},X={0,1,1,0},Z={1,0,0,-1};
 const std::vector<Complex> CX={1,0,0,0,0,1,0,0,0,0,0,1,0,0,1,0};
 using Bits=QuantumClassical::Bits;using Op=Bits::Binary;
 using Int=QuantumClassical::Integer;using Type=QuantumClassical::IntegerType;using Expr=QuantumClassical::IntegerExpression;
 auto signedByte=Type::sized(Int::Signedness::Signed,8),machine=Type::machine(Int::Signedness::Signed);
 auto variable=Expr::read(signedByte,{0,1,2,3,4,5,6,7});
 auto literal=[&](std::uint64_t n){return Expr::constant(QuantumClassical::TypedInteger::fromBits(machine,n));};
 {
 auto slot=Expr::variable(signedByte,0);
 auto positiveSlot=Bits::integerCompare(Op::Greater,slot,literal(0));
 auto emit=Step::assign({0},Bits::constant(1,1));
 std::vector<Type> types={signedByte};
 auto run=[&](const std::vector<Step> &program,unsigned shots=20) {
  return sampleTrajectories(0,1,shots,7,{0},program,types,16);
 };
 check(run({Step::storeInteger(0,literal(3)),Step::branch(positiveSlot,{emit})}).at(1)==20);
 check(run({Step::storeInteger(0,literal(255)),Step::branch(positiveSlot,{emit})}).at(0)==20); // Cast to signed byte is -1.
 check(run({Step::storeInteger(0,literal(3)),Step::storeInteger(0,Expr::binary(Int::Operation::Subtract,slot,literal(5))),Step::branch(positiveSlot,{emit})}).at(0)==20);
 check(run({Step::branch(Bits::constant(1,0),{Step::storeInteger(0,slot)})}).at(0)==20);
 rejects<std::domain_error>([&]{run({Step::branch(positiveSlot,{emit})});});
 rejects<std::domain_error>([&]{run({Step::storeInteger(0,literal(1)),Step::clearInteger(0),Step::branch(positiveSlot,{emit})});});
 rejects<std::domain_error>([&]{run({Step::storeInteger(0,Expr::binary(Int::Operation::Divide,literal(1),literal(0)))});});
 rejects<std::out_of_range>([&]{run({Step::branch(Bits::constant(1,0),{Step::storeInteger(1,literal(1))})},0);});
 rejects<std::out_of_range>([&]{run({Step::clearInteger(1)},0);});
 rejects<std::invalid_argument>([&]{run({Step::storeInteger(0,Expr::variable(machine,0))},0);});
 rejects<std::out_of_range>([&]{sampleTrajectories(0,1,0,7,{0},{Step::storeInteger(0,literal(1))},16);});
 auto measured=Expr::read(Type::sized(Int::Signedness::Unsigned,1),{0});
 std::vector<Step> feedForward={Step::gate(H,{0}),Step::measure(0,0),Step::storeInteger(0,measured),
  Step::assign({0},Bits::constant(1,0)),Step::branch(positiveSlot,{Step::assign({0},Bits::constant(1,1))})};
 auto expected=sampleTrajectories(1,1,1000,42,{0},{Step::gate(H,{0}),Step::measure(0,0)},32);
 check(expected.size()==2);
 // Seed 42 begins with a one, then includes zeros. A later zero must not
 // inherit the initialized slot from an earlier shot.
 check(sampleTrajectories(1,1,1,42,{0},{Step::gate(H,{0}),Step::measure(0,0)},32).at(1)==1);
 rejects<std::domain_error>([&]{sampleTrajectories(1,1,1000,42,{0},
  {Step::gate(H,{0}),Step::measure(0,0),Step::branch(1,1,{Step::storeInteger(0,literal(1))}),Step::branch(positiveSlot,{})},types,32);});
 check(run({Step::storeInteger(0,literal(1)),Step::branch(positiveSlot,{Step::storeInteger(0,literal(0)),emit})}).at(1)==20);

 check(sampleTrajectories(1,1,1000,42,{0},feedForward,types,32)==expected);
 check(sampleTrajectories(0,0,10,1,{}, {Step::storeInteger(0,literal(3))},types,16).at(0)==10);
 rejects<Cancelled>([&]{sampleTrajectories(0,0,10,1,{}, {Step::storeInteger(0,literal(3))},types,16,[]{return true;});});
 }
 // Runtime loops observe each write and each measurement, with one shared
 // condition budget per shot rather than an independently reset nested cap.
 {
 auto yes=Bits::constant(1,1),no=Bits::constant(1,0);
 auto slot=Expr::variable(signedByte,0);
 auto positive=Bits::integerCompare(Op::Greater,slot,literal(0));
 auto decrement=Step::storeInteger(0,Expr::binary(Int::Operation::Subtract,slot,literal(1)));
 auto emit=Step::assign({0},Bits::constant(1,1));
 auto run=[&](const std::vector<Step> &program,std::size_t budget,unsigned shots=20) {
  return sampleTrajectories(0,1,shots,7,{0},program,{signedByte},16,Cancellation(),budget);
 };
 auto countdown=Step::whileLoop(positive,{decrement,emit});
 check(run({Step::storeInteger(0,literal(3)),countdown},4).at(1)==20);
 rejects<std::length_error>([&]{run({Step::storeInteger(0,literal(3)),countdown},3);});
 check(run({Step::storeInteger(0,literal(0)),countdown},1).at(0)==20);
 check(run({Step::whileLoop(no,{Step::storeInteger(0,slot)})},1).at(0)==20);
 rejects<std::domain_error>([&]{run({countdown},4);});
 rejects<std::domain_error>([&]{run({Step::storeInteger(0,literal(1)),Step::whileLoop(positive,{Step::clearInteger(0)})},4);});
 rejects<std::length_error>([&]{run({Step::whileLoop(yes,{})},3);});
 rejects<std::length_error>([&]{run({Step::whileLoop(no,{})},0);});
 check(run({},0).at(0)==20);
 check(run({Step::branch(no,{Step::whileLoop(yes,{})})},0).at(0)==20);
 check(run({Step::whileLoop(yes,{})},0,0).empty());
 auto nested=Step::whileLoop(positive,{Step::whileLoop(no,{}),decrement});
 check(run({Step::storeInteger(0,literal(2)),nested},5).at(0)==20);
 rejects<std::length_error>([&]{run({Step::storeInteger(0,literal(2)),nested},4);});
 rejects<std::out_of_range>([&]{run({Step::whileLoop(no,{Step::storeInteger(1,literal(0))})},1,0);});
 rejects<std::invalid_argument>([&]{run({Step::whileLoop(Bits::constant(2,0),{})},1,0);});
 rejects<std::out_of_range>([&]{run({Step::whileLoop(Bits::read({1}),{})},1,0);});
 std::vector<Step> body={emit,Step::assign({1},no)};
 auto snapshot=Step::whileLoop(Bits::read({1}),body);body.clear();
 check(sampleTrajectories(0,2,10,7,{0},{Step::assign({1},yes),snapshot},16).at(1)==10);
 std::vector<Step> levels;
 for(unsigned k=0;k<32;++k){std::vector<Step> next={Step::whileLoop(no,levels)};levels.swap(next);}
 check(run(levels,1).at(0)==20);
 rejects<std::length_error>([&]{run({Step::branch(no,levels)},1,0);});
 std::vector<Step> huge(4096,emit);
 rejects<std::length_error>([&]{run({Step::whileLoop(no,huge)},1,0);});
 // Repeated quantum measurement drives termination; a final reset must not
 // erase the saved classical outcome used by the loop.
 std::vector<Step> repeat={Step::whileLoop(Bits::complement(Bits::read({0})),
  {Step::gate(H,{0}),Step::measure(0,0)}),Step::reset(0)};
 check(sampleTrajectories(1,1,1000,42,{0},repeat,32).at(1)==1000);
 // A loop with one mandatory iteration preserves the random stream exactly.
 std::vector<Step> once={Step::assign({1},yes),Step::whileLoop(Bits::read({1}),
  {Step::gate(H,{0}),Step::measure(0,0),Step::assign({1},no)})};
 check(sampleTrajectories(1,2,1000,42,{0},once,32)==
  sampleTrajectories(1,2,1000,42,{0},{Step::gate(H,{0}),Step::measure(0,0)},32));
 unsigned polls=0;
 rejects<Cancelled>([&]{sampleTrajectories(0,0,1,7,{}, {Step::whileLoop(yes,{})},{},16,[&]{return ++polls==20;},100);});
 check(polls==20);
 }
 auto negative=Bits::integerCompare(Op::Less,variable,literal(0));
 auto quotient=Expr::binary(Int::Operation::Divide,literal(6),variable);
 auto isThree=Bits::integerCompare(Op::Equal,quotient,literal(3));
 auto setOutput=Step::assign({8},Bits::constant(1,1));
 check(sampleTrajectories(0,9,100,7,{8},{Step::assign({0,1,2,3,4,5,6,7},Bits::constant(8,255)),Step::branch(negative,{setOutput})},16).at(1)==100);
 check(sampleTrajectories(0,9,100,7,{8},{Step::assign({0,1,2,3,4,5,6,7},Bits::constant(8,2)),Step::branch(isThree,{setOutput})},16).at(1)==100);
 check(sampleTrajectories(0,9,100,7,{8},{Step::branch(Bits::constant(1,0),{Step::branch(isThree,{setOutput})})},16).at(0)==100);
 rejects<std::domain_error>([&]{sampleTrajectories(0,9,1,7,{8},{Step::branch(isThree,{setOutput})},16);});
 rejects<std::out_of_range>([&]{sampleTrajectories(0,7,0,7,{}, {Step::branch(Bits::constant(1,0),{Step::branch(negative,{})})},16);});

 check(sampleTrajectories(1,2,100,7,{1,0},{Step::gate(X,{0}),Step::measure(0,0),Step::assign({1},Bits::read({0})),Step::assign({0},Bits::constant(1,0))},32).at(2)==100);
 check(sampleTrajectories(0,3,100,7,{2,1,0},{Step::assign({0},Bits::constant(1,1)),Step::assign({1,2},Bits::read({0,1}))},16).at(3)==100);
 check(sampleTrajectories(0,64,100,7,{63},{Step::assign({63},Bits::constant(1,1))},16).at(1)==100);
 auto parity=Bits::binary(Op::Xor,Bits::read({0}),Bits::read({1}));
 auto parityCounts=sampleTrajectories(3,3,10000,7,{2,1,0},{Step::gate(H,{0}),Step::gate(H,{1}),Step::measure(0,0),Step::measure(1,1),Step::branch(parity,{Step::gate(X,{2})}),Step::measure(2,2)},128);
 check(parityCounts.size()==4);
 for(auto outcome:{0,3,5,6})check(parityCounts.count(outcome) && std::abs(int(parityCounts.at(outcome))-2500)<300);
 check(sampleTrajectories(0,2,100,7,{1,0},{Step::assign({0},Bits::constant(1,1)),Step::branch(Bits::read({0}),{Step::assign({0},Bits::constant(1,0)),Step::assign({1},Bits::constant(1,1))})},16).at(2)==100);
 check(sampleTrajectories(0,1,100,7,{0},{Step::branch(Bits::constant(1,0),{},{Step::assign({0},Bits::constant(1,1))})},16).at(1)==100);
 // Changing classical memory cannot change the previously measured qubit.
 check(sampleTrajectories(1,2,100,7,{1,0},{Step::gate(X,{0}),Step::measure(0,0),Step::assign({0},Bits::constant(1,0)),Step::measure(0,1)},32).at(2)==100);
 rejects<std::invalid_argument>([&]{sampleTrajectories(0,2,0,7,{}, {Step::assign({0},Bits::constant(2,0))},16);});
 rejects<std::invalid_argument>([&]{sampleTrajectories(0,2,0,7,{}, {Step::assign({0,0},Bits::constant(2,0))},16);});
 rejects<std::out_of_range>([&]{sampleTrajectories(0,1,0,7,{}, {Step::assign({1},Bits::constant(1,0))},16);});
 rejects<std::out_of_range>([&]{sampleTrajectories(0,1,0,7,{}, {Step::assign({0},Bits::read({1}))},16);});
 rejects<std::invalid_argument>([&]{sampleTrajectories(0,2,0,7,{}, {Step::branch(Bits::read({0,1}),{})},16);});
 rejects<std::out_of_range>([&]{sampleTrajectories(0,1,0,7,{}, {Step::branch(Bits::read({1}),{})},16);});
 rejects<std::out_of_range>([&]{sampleTrajectories(0,1,0,7,{}, {Step::branch(Bits::constant(1,0),{Step::assign({1},Bits::constant(1,0))})},16);});
 // Branch selection is latched at entry, not re-tested after each operation.
 std::vector<Step> block={Step::gate(X,{0}),Step::measure(0,0),
  Step::branch(1,1,{Step::reset(0),Step::measure(0,0),Step::gate(X,{1}),Step::measure(1,1)})};
 check(sampleTrajectories(2,2,100,7,{1,0},block,64).at(2)==100);
 check(sampleTrajectories(1,2,100,7,{1,0},{Step::branch(1,1,{}, {Step::gate(X,{0}),Step::measure(0,1)})},32).at(2)==100);
 check(sampleTrajectories(0,0,10,7,{}, {Step::branch(0,0,{})},16).at(0)==10);
 const std::uint64_t high=std::uint64_t(1)<<63;
 check(sampleTrajectories(1,64,10,7,{63},{Step::branch(high,0,{Step::branch(0,0,{Step::gate(X,{0}),Step::measure(0,63)})})},32).at(1)==10);
 rejects<std::out_of_range>([&]{sampleTrajectories(1,1,0,0,{0},{Step::branch(1,1,{Step::measure(0,1)})},32);});
 rejects<std::invalid_argument>([&]{sampleTrajectories(1,1,0,0,{0},{Step::branch(1,1,{}, {Step::gate({1,1,1,1},{0})})},32);});
 rejects<std::invalid_argument>([&]{sampleTrajectories(1,1,0,0,{0},{Step::branch(2,0,{})},32);});
 rejects<std::invalid_argument>([&]{sampleTrajectories(1,1,0,0,{0},{Step::branch(1,2,{})},32);});
 std::vector<Step> nested;
 for(unsigned k=0;k<32;++k){std::vector<Step> next={Step::branch(0,0,nested)};nested.swap(next);}
 check(sampleTrajectories(0,0,10,0,{},nested,16).at(0)==10);
 rejects<std::length_error>([&]{sampleTrajectories(0,0,0,0,{}, {Step::branch(0,0,nested)},16);});
 std::vector<Step> wide(4095,Step::reset(0));
 check(sampleTrajectories(1,1,1,0,{0},{Step::branch(0,0,wide)},32).at(0)==1);
 rejects<std::length_error>([&]{sampleTrajectories(1,1,0,0,{0},{Step::branch(0,0,wide,{Step::reset(0)})},32);});
 std::vector<Step> body={Step::gate(H,{0}),Step::measure(0,0)};
 Step snapshot=Step::branch(0,0,body);
 check(sampleTrajectories(1,1,1000,42,{0},{snapshot},32)==sampleTrajectories(1,1,1000,42,{0},body,32));
 body.clear();
 check(sampleTrajectories(1,1,1000,42,{0},{snapshot},32).size()==2);
 check(sampleTrajectories(0,1,10,7,{0},{Step::branch(1,0,{Step::readout({{0,1},{1,0}},{0})})},16).at(1)==10);
 unsigned branchCalls=0;
 rejects<Cancelled>([&]{sampleTrajectories(2,2,100,7,{1,0},block,64,[&]{return ++branchCalls==100;});});
 std::vector<Step> saved={Step::gate(H,{0}),Step::measure(0,0),Step::gate(X,{0}),Step::measure(0,1),Step::conditional(X,{1},1,1),Step::measure(1,2)};
 auto counts=sampleTrajectories(2,3,1000,42,{2,1,0},saved,64);
 check(counts.size()==2 && counts.count(2) && counts.count(5));check(counts[2]+counts[5]==1000);
 check(counts==sampleTrajectories(2,3,1000,42,{2,1,0},saved,64));
 check(counts!=sampleTrajectories(2,3,1000,43,{2,1,0},saved,64));
 check(sampleTrajectories(1,1,100,1,{0},{Step::gate(X,{0}),Step::measure(0,0),Step::reset(0),Step::measure(0,0)},32).at(0)==100);
 check(sampleTrajectories(1,64,10,1,{63,0},{Step::gate(X,{0}),Step::measure(0,63),Step::conditional(X,{0},std::uint64_t(1)<<63,std::uint64_t(1)<<63),Step::measure(0,0)},32).at(2)==10);
 // Teleport a complex state, then undo preparation on Bob. His measured
 // bit must always be zero; Alice's two recorded bits remain random.
 const double theta=.73,phi=1.19,c=std::cos(theta/2),s=std::sin(theta/2);
 const Complex phase=std::exp(Complex(0,phi));
 const std::vector<Complex> U={c,-s,phase*s,phase*c},inverse={c,std::conj(phase)*s,-s,std::conj(phase)*c};
 std::vector<Step> teleport={Step::gate(H,{1}),Step::gate(CX,{1,2}),Step::gate(U,{0}),Step::gate(CX,{0,1}),Step::gate(H,{0}),Step::measure(1,1),Step::measure(0,0),Step::conditional(X,{2},2,2),Step::conditional(Z,{2},1,1),Step::gate(inverse,{2}),Step::measure(2,2)};
 counts=sampleTrajectories(3,3,2000,1731,{2,1,0},teleport,128);check(counts.size()==4);
 unsigned total=0;for(auto entry:counts){check(entry.first<4);check(std::abs(int(entry.second)-500)<100);total+=entry.second;}check(total==2000);
 rejects<std::invalid_argument>([&]{sampleTrajectories(1,1,1,0,{0},{Step::conditional({1,1,1,1},{0},1,1)},32);});
 rejects<std::invalid_argument>([&]{sampleTrajectories(1,1,1,0,{0},{Step::conditional(X,{0},1,2)},32);});
 rejects<std::invalid_argument>([&]{sampleTrajectories(1,1,1,0,{0,0},{},32);});
 rejects<std::out_of_range>([&]{sampleTrajectories(1,1,1,0,{0},{Step::measure(0,1)},32);});
 rejects<std::out_of_range>([&]{sampleTrajectories(1,1,1,0,{0},{Step::reset(1)},32);});
 rejects<std::length_error>([&]{sampleTrajectories(2,1,1,0,{0},{},16);});
 rejects<Cancelled>([&]{sampleTrajectories(2,3,1000,0,{0},saved,64,[]{return true;});});
 unsigned calls=0;rejects<Cancelled>([&]{sampleTrajectories(2,3,1000,0,{0},saved,64,[&]{return ++calls==100;});});
 // Multi-bit conditions distinguish one complete pattern, and every shot
 // starts with fresh classical memory even if no measurement writes a bit.
 check(sampleTrajectories(1,2,10,0,{1,0},{Step::gate(X,{0}),Step::measure(0,0),Step::conditional(X,{0},3,1),Step::measure(0,1)},32).at(1)==10);
 check(sampleTrajectories(1,1,10,0,{0},{Step::conditional(X,{0},1,0),Step::measure(0,0)},32).at(1)==10);
 rejects<std::invalid_argument>([&]{sampleTrajectories(1,1,1,0,{0},{Step::conditional(X,{0},2,0)},32);});
 rejects<std::invalid_argument>([&]{sampleTrajectories(2,1,1,0,{0},{Step::gate(CX,{0,0})},64);});
 rejects<std::length_error>([&]{sampleTrajectories(26,1,0,0,{0},{},std::size_t(-1));});
 rejects<std::length_error>([&]{sampleTrajectories(0,65,0,0,{},{},16);});
 rejects<std::length_error>([&]{sampleTrajectories(0,0,1000001,0,{},{},16);});
 std::vector<Step> maximum(4096,Step::reset(0));check(sampleTrajectories(1,1,1,0,{0},maximum,32).at(0)==1);
 maximum.push_back(Step::reset(0));rejects<std::length_error>([&]{sampleTrajectories(1,1,1,0,{0},maximum,32);});
 check(sampleTrajectories(0,0,10,0,{}, {},16).at(0)==10);
 check(sampleTrajectories(1,1,0,0,{0},{},32).empty());
 const std::vector<std::vector<Complex>> damping={{1,0,0,h},{0,h,0,0}};
 std::vector<Step> noisyBell={Step::gate(H,{0}),Step::gate(CX,{0,1}),Step::channel(damping,{1}),Step::measure(0,0),Step::measure(1,1)};
 counts=sampleTrajectories(2,2,20000,42,{0,1},noisyBell,64);
 check(counts.size()==3 && counts.count(0) && counts.count(2) && counts.count(3));
 check(std::abs(int(counts[0])-10000)<400 && std::abs(int(counts[2])-5000)<300 && std::abs(int(counts[3])-5000)<300);
 check(counts==sampleTrajectories(2,2,20000,42,{0,1},noisyBell,64));
 check(counts!=sampleTrajectories(2,2,20000,43,{0,1},noisyBell,64));
 // Noise changes the quantum state but never rewrites a prior measurement.
 counts=sampleTrajectories(1,2,100,1,{0,1},{Step::gate(X,{0}),Step::measure(0,0),Step::channel({{1,0,0,0},{0,1,0,0}},{0}),Step::measure(0,1)},32);
 check(counts.size()==1 && counts.at(2)==100);
 counts=sampleTrajectories(1,1,10000,7,{0},{Step::gate(H,{0}),Step::channel({{h,0,0,h},{h,0,0,-h}},{0}),Step::gate(H,{0}),Step::measure(0,0)},32);
 check(counts.size()==2 && std::abs(int(counts.at(0))-5000)<300);
 rejects<std::invalid_argument>([&]{sampleTrajectories(1,1,0,0,{0},{Step::channel({{2,0,0,1}},{0})},32);});
 rejects<std::out_of_range>([&]{sampleTrajectories(1,1,1,0,{0},{Step::channel(damping,{1})},32);});
 rejects<std::invalid_argument>([&]{sampleTrajectories(2,1,1,0,{0},{Step::channel({CX},{0,0})},64);});
 calls=0;rejects<Cancelled>([&]{sampleTrajectories(2,2,20000,42,{0,1},noisyBell,64,[&]{return ++calls==100;});});
 // Assignment corrupts a record, not the physical state that was measured.
 const std::vector<std::vector<double>> flip={{0,1},{1,0}};
 counts=sampleTrajectories(1,2,100,7,{0,1},{Step::gate(X,{0}),Step::measure(0,0),Step::readout(flip,{0}),Step::measure(0,1)},32);
 check(counts.size()==1 && counts.at(1)==100);
 // Feedback uses the corrupted record; remeasurement of the original wire is unchanged.
 counts=sampleTrajectories(2,3,100,7,{0,1,2},{Step::measure(0,0),Step::readout(flip,{0}),Step::conditional(X,{1},1,1),Step::measure(1,1),Step::measure(0,2)},64);
 check(counts.size()==1 && counts.at(6)==100);
 std::vector<Step> readoutOnly={Step::readout({{.75,.25},{.5,.5}},{63})};
 counts=sampleTrajectories(0,64,20000,42,{63},readoutOnly,16);
 check(counts.size()==2 && std::abs(int(counts.at(1))-5000)<300);
 check(counts==sampleTrajectories(0,64,20000,42,{63},readoutOnly,16));
 check(counts!=sampleTrajectories(0,64,20000,43,{63},readoutOnly,16));
 counts=sampleTrajectories(0,64,100,7,{63,0},{Step::readout({{0,0,0,1},{0,1,0,0},{0,0,1,0},{1,0,0,0}},{63,0})},16);
 check(counts.size()==1 && counts.at(3)==100);
 check(sampleTrajectories(0,64,0,7,{63},readoutOnly,16).empty());
 rejects<std::out_of_range>([&]{sampleTrajectories(0,1,0,7,{0},readoutOnly,16);});
 rejects<std::invalid_argument>([&]{Step::readout({{.2,.2},{0,1}},{0});});
 calls=0;rejects<Cancelled>([&]{sampleTrajectories(0,64,20000,42,{63},readoutOnly,16,[&]{return ++calls==100;});});
 std::cout<<"PASS: "<<checks<<" numerical trajectory checks\n";
 }catch(const std::exception &error){std::cerr<<error.what()<<'\n';return 1;}}
