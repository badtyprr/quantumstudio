// GPL-2.0-or-later; see COPYING.
#include "libqalculate/QuantumExactPhase.h"
#include "libqalculate/Calculator.h"
#include <iostream>
#include <stdexcept>
#include <type_traits>
using namespace QuantumExact;
namespace {
unsigned checks=0;
void check(bool value){++checks;if(!value)throw std::runtime_error("Exact phase check "+std::to_string(checks));}
template<class E,class F>void rejects(F f){bool caught=false;try{f();}catch(const E&){caught=true;}check(caught);}
}
int main(){try {
 static_assert(!std::is_copy_constructible<PhaseBudget>::value,"A shared work budget cannot be cloned");
 Calculator calculator;
 PhaseBudget budget(256,256,100000);
 auto term=[&](Number f,Number a,Number b=Number(0)){return PhasePolynomial::term(f,a,b,budget);};
 const auto zero=PhasePolynomial(),one=term(0,1),minus=term(0,-1);
 check(zero.termCount()==0);check(one.termCount()==1);
 check(one.plus(minus,budget)==zero);
 check(one.times(zero,budget)==zero);
 auto root=term(0,0,1),invroot=term(0,0,Number(1,2));
 check(root.times(root,budget)==term(0,2));
 check(root.times(invroot,budget)==one);
 auto mixed=term(0,1,1),opposite=term(0,1,-1);
 check(mixed.times(opposite,budget)==minus);
 Number imaginary(0);imaginary.setImaginaryPart(1);
 check(term(0,imaginary).times(term(0,imaginary),budget)==minus);
 check(term(0,imaginary).conjugated(budget)==term(0,-imaginary));
 // Exact rational angles including nearby literals must remain distinct.
 auto p=term(Number(1,3),1),q=term(Number(1,6),1);
 check(p.times(q,budget)==term(Number(1,2),1));
 check(p.times(p.conjugated(budget),budget)==one);
 check(term(Number(1570796326,1000000000),1).plus(term(Number(1570796327,1000000000),1),budget).termCount()==2);
 // Rx normalization and composition, without using floating trigonometry.
 for(int k=-5;k<=5;++k) {
  auto positive=term(Number(k,14),Number(1,2));
  auto negative=term(Number(-k,14),Number(1,2));
  auto cosine=positive.plus(negative,budget);
  auto minusISine=negative.plus(positive.times(minus,budget),budget);
  check(cosine.times(cosine.conjugated(budget),budget).plus(
        minusISine.times(minusISine.conjugated(budget),budget),budget)==one);
  // Rx(t)^2 == Rx(2t), checking both diagonal and off-diagonal terms.
  auto diagonal=cosine.times(cosine,budget).plus(minusISine.times(minusISine,budget),budget);
  check(diagonal==term(Number(k,7),Number(1,2)).plus(term(Number(-k,7),Number(1,2)),budget));
  auto offDiagonal=cosine.times(minusISine,budget).times(term(0,2),budget);
  check(offDiagonal==term(Number(-k,7),Number(1,2)).plus(term(Number(k,7),Number(-1,2)),budget));
 }
 auto polynomial=p.plus(q.times(root,budget),budget).plus(term(Number(-1,5),imaginary),budget);
 check(polynomial.conjugated(budget).conjugated(budget)==polynomial);
 auto norm=polynomial.times(polynomial.conjugated(budget),budget);
 check(norm.conjugated(budget)==norm);
 check(polynomial.times(p.plus(q,budget),budget)==polynomial.times(p,budget).plus(polynomial.times(q,budget),budget));
 Number approximate(1,3);approximate.setApproximate();
 rejects<std::invalid_argument>([&]{term(approximate,1);});
 rejects<std::invalid_argument>([&]{term(0,approximate);});
 rejects<std::invalid_argument>([&]{term(0,0,approximate);});
 rejects<std::invalid_argument>([&]{term(imaginary,1);});
 Number infinity;infinity.setPlusInfinity();
 rejects<std::invalid_argument>([&]{term(infinity,1);});
 rejects<std::invalid_argument>([&]{term(0,infinity);});
 Number approximateImaginary;approximateImaginary.setImaginaryPart(approximate);
 rejects<std::invalid_argument>([&]{term(0,approximateImaginary);});
 rejects<std::invalid_argument>([]{PhaseBudget invalid(0,10,1);});
 rejects<std::invalid_argument>([]{PhaseBudget invalid(10,0,1);});
 PhaseBudget noWork(10,256,0);
 rejects<std::length_error>([&]{one.plus(one,noWork);});
 PhaseBudget shared(10,256,2);
 PhasePolynomial::term(0,1,0,shared);PhasePolynomial::term(0,2,0,shared);
 rejects<std::length_error>([&]{PhasePolynomial::term(0,3,0,shared);});
 PhaseBudget oneTerm(1,256,100);
 rejects<std::length_error>([&]{p.plus(q,oneTerm);});
 check(p==term(Number(1,3),1));check(q==term(Number(1,6),1));
 PhaseBudget smallNumber(10,4,100);
 rejects<std::length_error>([&]{PhasePolynomial::term(Number(1,17),1,0,smallNumber);});
 rejects<std::length_error>([&]{PhasePolynomial::term(0,16,0,smallNumber);});
 auto seven=term(0,7);
 rejects<std::length_error>([&]{seven.times(seven,smallNumber);});
 check(seven==term(0,7));
 bool cancel=false;PhaseBudget cancellable(256,256,1000,[&]{return cancel;});
 auto copy=polynomial.plus(zero,cancellable);cancel=true;
 rejects<std::runtime_error>([&]{polynomial.times(polynomial,cancellable);});
 rejects<std::runtime_error>([&]{zero.conjugated(cancellable);});
 check(copy==polynomial);
 unsigned cancellationChecks=0;
 PhaseBudget interrupted(256,256,1000,[&]{return ++cancellationChecks>12;});
 rejects<std::runtime_error>([&]{polynomial.times(polynomial,interrupted);});
 check(copy==polynomial);
 std::cout<<"PASS: "<<checks<<" exact phase checks\n";return 0;
}catch(const std::exception &error){std::cerr<<error.what()<<'\n';return 1;}}
