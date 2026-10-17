// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_EXACT_OPERATION_H
#define QUANTUM_EXACT_OPERATION_H
#include "MathStructure.h"
#include <vector>

namespace QuantumExact {
// An owned square Kraus map with sum(K† K)=I proved in exact arithmetic.
// One operator is a unitary gate. Multiple operators form a channel.
// Input/output Hilbert-space dimensions are equal powers of two.
class TracePreservingMap {
 std::vector<MathStructure> operators_;
 std::size_t dimension_;
public:
 // maxEntries bounds total input matrix entries (not expression byte size).
 // Throws invalid_argument for malformed/nonphysical input, domain_error
 // when completeness cannot be proved, and length_error on resource limits.
 TracePreservingMap(const std::vector<MathStructure> &operators,
                    std::size_t maxEntries, const EvaluationOptions &options);
 // Copy even from rvalues: a moved-from empty operator list would invalidate
 // this type's trace-preservation guarantee while leaving it callable.
 TracePreservingMap(const TracePreservingMap &) = default;
 TracePreservingMap &operator=(TracePreservingMap other) {
  // Copy before mutation so allocation failures cannot mix certified maps.
  operators_.swap(other.operators_);
  const std::size_t old=dimension_;dimension_=other.dimension_;other.dimension_=old;
  return *this;
 }
 const std::vector<MathStructure> &operators() const {return operators_;}
 std::size_t dimension() const {return dimension_;}
};
}
#endif
