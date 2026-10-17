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
 std::cout<<"PASS: "<<checks<<" numerical trajectory checks\n";
 }catch(const std::exception &error){std::cerr<<error.what()<<'\n';return 1;}}
