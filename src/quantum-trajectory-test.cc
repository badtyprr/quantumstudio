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
