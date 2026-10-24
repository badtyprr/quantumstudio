// GPL-2.0-or-later; see COPYING.
#include "QuantumExactPhase.h"
#include <stdexcept>
#include <utility>

namespace QuantumExact {
PhaseBudget::PhaseBudget(std::size_t maxTerms,std::size_t maxBits,std::size_t maxWork,
 std::function<bool()> cancelled):terms_(maxTerms),bits_(maxBits),remaining_(maxWork),cancelled_(std::move(cancelled)) {
 if(!terms_ || !bits_)throw std::invalid_argument("Exact phases require positive term and integer-size limits");
}
void PhaseBudget::charge() {
 if(cancelled_ && cancelled_())throw std::runtime_error("Exact phase evaluation cancelled");
 if(!remaining_)throw std::length_error("Exact phase work budget exceeded");
 --remaining_;
}
void PhaseBudget::check(const Number &value) const {
 if(value.isApproximate())throw std::invalid_argument("Exact phase coefficients cannot be approximate");
 for(const auto &part:{value.realPart(),value.imaginaryPart()}) {
  if(!part.isRational())throw std::invalid_argument("Exact phases require rational real and imaginary parts");
  const auto &r=part.internalRational();
  if(mpz_sizeinbase(mpq_numref(r),2)>bits_ || mpz_sizeinbase(mpq_denref(r),2)>bits_)
   throw std::length_error("Exact phase integer-size budget exceeded");
 }
}
void PhaseBudget::checkTerms(std::size_t terms) const {
 if(terms>terms_)throw std::length_error("Exact phase term budget exceeded");
}
void PhasePolynomial::validate(PhaseBudget &budget) const {
 budget.charge();budget.checkTerms(terms_.size());
 for(const auto &term:terms_) {
  budget.charge();budget.check(term.first);budget.check(term.second.a);budget.check(term.second.b);
 }
}
void PhasePolynomial::insert(const Number &frequency,const Coefficient &value,PhaseBudget &budget) {
 budget.charge();budget.check(frequency);budget.check(value.a);budget.check(value.b);
 if(!frequency.isReal())throw std::invalid_argument("Exact phase frequencies must be rational real radians");
 if(value.a.isZero() && value.b.isZero())return;
 auto found=terms_.find(frequency);
 if(found==terms_.end()) {
  // Check before insertion, rather than temporarily exceeding the allocation cap.
  if(terms_.size()==static_cast<std::size_t>(-1))throw std::length_error("Exact phase term count overflow");
  budget.checkTerms(terms_.size()+1);terms_.emplace(frequency,value);
 } else {
  Coefficient combined{found->second.a+value.a,found->second.b+value.b};
  budget.check(combined.a);budget.check(combined.b);
  if(combined.a.isZero() && combined.b.isZero())terms_.erase(found);
  else found->second=std::move(combined);
 }
}
PhasePolynomial PhasePolynomial::term(const Number &frequency,const Number &a,const Number &b,PhaseBudget &budget) {
 PhasePolynomial result;result.insert(frequency,{a,b},budget);return result;
}
PhasePolynomial PhasePolynomial::plus(const PhasePolynomial &other,PhaseBudget &budget) const {
 validate(budget);other.validate(budget);
 PhasePolynomial result;
 for(const auto &term:terms_)result.insert(term.first,term.second,budget);
 for(const auto &term:other.terms_)result.insert(term.first,term.second,budget);
 return result;
}
PhasePolynomial PhasePolynomial::times(const PhasePolynomial &other,PhaseBudget &budget) const {
 validate(budget);other.validate(budget);
 PhasePolynomial result;
 for(const auto &left:terms_)for(const auto &right:other.terms_) {
  budget.charge();
  const auto &x=left.second;const auto &y=right.second;
  result.insert(left.first+right.first,{x.a*y.a+(x.b*y.b)*2,x.a*y.b+x.b*y.a},budget);
 }
 return result;
}
namespace {
Number conjugate(const Number &value) {
 Number result=value.realPart();result.setImaginaryPart(-value.imaginaryPart());return result;
}
}
PhasePolynomial PhasePolynomial::conjugated(PhaseBudget &budget) const {
 validate(budget);PhasePolynomial result;
 for(const auto &term:terms_)
  result.insert(-term.first,{conjugate(term.second.a),conjugate(term.second.b)},budget);
 return result;
}
bool PhasePolynomial::operator==(const PhasePolynomial &other) const {
 if(terms_.size()!=other.terms_.size())return false;
 auto right=other.terms_.begin();
 for(auto left=terms_.begin();left!=terms_.end();++left,++right)
  if(left->first!=right->first || left->second.a!=right->second.a || left->second.b!=right->second.b)return false;
 return true;
}
bool PhasePolynomial::rationalConstant(Number &value) const {
 if(terms_.empty()){value=0;return true;}
 if(terms_.size()!=1 || !terms_.begin()->first.isZero() || !terms_.begin()->second.b.isZero() ||
    !terms_.begin()->second.a.isReal())return false;
 value=terms_.begin()->second.a;return true;
}
}
