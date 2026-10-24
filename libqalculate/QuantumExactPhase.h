// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_EXACT_PHASE_H
#define QUANTUM_EXACT_PHASE_H
#include "Number.h"
#include <cstddef>
#include <functional>
#include <map>

namespace QuantumExact {
// Shared across an execution, so many individually small operations cannot
// evade the work limit. Term limits apply to each polynomial; a circuit caller
// must additionally bound its number of simultaneously retained polynomials.
class PhaseBudget {
 std::size_t terms_,bits_,remaining_;
 std::function<bool()> cancelled_;
public:
 PhaseBudget(std::size_t maxTerms,std::size_t maxBits,std::size_t maxWork,
             std::function<bool()> cancelled={});
 PhaseBudget(const PhaseBudget &)=delete;
 PhaseBudget &operator=(const PhaseBudget &)=delete;
 void charge();
 void check(const Number &value) const;
 void checkTerms(std::size_t terms) const;
};

// Exact finite sums (a + b*sqrt(2))*exp(i*r), with rational radians r and
// Gaussian-rational a,b. In particular, decimal angles are never snapped to pi.
// All operations return a new value: failure/cancellation leaves operands intact.
// Unsupported/approximate numbers are rejected, not silently approximated.
class PhasePolynomial {
 struct Coefficient {Number a,b;};
 std::map<Number,Coefficient> terms_;
 void validate(PhaseBudget &budget) const;
 void insert(const Number &frequency,const Coefficient &value,PhaseBudget &budget);
public:
 PhasePolynomial()=default; // zero
 static PhasePolynomial term(const Number &frequency,const Number &a,
                             const Number &b,PhaseBudget &budget);
 PhasePolynomial plus(const PhasePolynomial &other,PhaseBudget &budget) const;
 PhasePolynomial times(const PhasePolynomial &other,PhaseBudget &budget) const;
 PhasePolynomial conjugated(PhaseBudget &budget) const;
 bool operator==(const PhasePolynomial &other) const;
 std::size_t termCount() const {return terms_.size();}
};
}
#endif
