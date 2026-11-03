// GPL-2.0-or-later; see COPYING.
#include "libqalculate/QuantumNumericalState.h"
#include <array>
#include <cmath>
#include <iostream>

using QuantumNumerics::Complex;
using QuantumNumerics::StateVector;
namespace {
unsigned checks=0;
constexpr double tolerance=1e-12;
const std::vector<Complex> x={0,1,1,0};
const std::vector<Complex> h={std::sqrt(.5),std::sqrt(.5),std::sqrt(.5),-std::sqrt(.5)};
const std::vector<Complex> cx={1,0,0,0, 0,1,0,0, 0,0,0,1, 0,0,1,0};
void check(bool condition,const char *message) {
 ++checks;if(!condition)throw std::runtime_error(message);
}
// Algebraic encoder adaptation, not the IBM-060 pictured encoder. Local wire 6
// holds the input. Three free bits generate 1001011,0101101,0011110; the
// logical coset representative 0000111 differs from 1111111 by a dual word.
void encode(StateVector &state,unsigned offset) {
 state.apply(cx,{offset+6,offset+4});state.apply(cx,{offset+6,offset+5});
 for(unsigned q=0;q<3;++q)state.apply(h,{offset+q});
 for(auto pair:std::vector<std::array<unsigned,2>>{{0,3},{0,5},{0,6},{1,3},{1,4},{1,6},{2,3},{2,4},{2,5}})
  state.apply(cx,{offset+pair[0],offset+pair[1]});
}
// Independent oracle: literal IBM-062 dual-code set, not encoder gate replay.
const unsigned dual[]={0b0000000,0b0011110,0b0101101,0b0110011,
                       0b1001011,0b1010101,0b1100110,0b1111000};
int coset(unsigned word) {
 for(unsigned v:dual) {if(word==v)return 0;if(word==(v^127))return 1;}
 return -1;
}
void compare(const StateVector &state,const std::array<Complex,4> &logical) {
 double leakage=0;std::array<Complex,4> overlaps={};
 for(unsigned basis=0;basis<16384;++basis) {
  int a=coset(basis>>7),b=coset(basis&127);
  Complex expected=(a<0 || b<0)?Complex(0):logical[2*a+b]/8.;
  Complex actual=state.amplitude(basis);
  check(std::abs(actual-expected)<tolerance,"Steane amplitude or relative phase differs");
  if(a<0 || b<0)leakage+=std::norm(actual);
  else overlaps[2*a+b]+=actual/8.;
 }
 for(unsigned k=0;k<4;++k)check(std::abs(overlaps[k]-logical[k])<tolerance,"Logical overlap differs");
 // Full amplitude comparison also checks components orthogonal to each uniform
 // coset vector; computational support alone would miss that leakage.
 double projected=0;for(auto overlap:overlaps)projected+=std::norm(overlap);
 check(leakage<tolerance,"Outside-coset leakage");
 check(std::abs(state.normSquared()-projected)<tolerance,"Code-space leakage");
 check(std::abs(state.normSquared()-1)<tolerance,"State normalization differs");
}
void transversal(StateVector &state) {
 for(unsigned q=0;q<7;++q)state.apply(cx,{q,q+7});
}
}
int main() {try {
 for(unsigned input=0;input<4;++input) {
  StateVector state(14,16384*sizeof(Complex));
  if(input&2)state.apply(x,{6});if(input&1)state.apply(x,{13});
  encode(state,0);encode(state,7);
  std::array<Complex,4> expected={};expected[input]=1;compare(state,expected);
  transversal(state);expected={};expected[input^((input>>1)&1)]=1;compare(state,expected);
 }
 // Four nonzero complex coefficients. No column-wise phase alignment is used.
 StateVector coherent(14,16384*sizeof(Complex));
 coherent.apply(h,{6});coherent.apply({1,0,0,Complex(0,1)},{6});
 const double a=std::sqrt(1./3),b=std::sqrt(2./3),s=std::sqrt(.5);
 coherent.apply({a,-b,b,a},{13});encode(coherent,0);encode(coherent,7);
 std::array<Complex,4> expected={s*a,s*b,Complex(0,s*a),Complex(0,s*b)};
 compare(coherent,expected);transversal(coherent);std::swap(expected[2],expected[3]);compare(coherent,expected);
 std::cout<<"PASS: "<<checks<<" Steane transversal checks; 4 columns and complex witness; tolerance 1e-12\n";
 return 0;
} catch(const std::exception &error) {std::cerr<<error.what()<<'\n';return 1;}}
