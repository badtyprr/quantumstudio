#ifndef QUANTUM_NUMERICAL_STATE_H
#define QUANTUM_NUMERICAL_STATE_H

#include <complex>
#include <cstddef>
#include <functional>
#include <stdexcept>
#include <vector>

namespace QuantumNumerics {
using Complex = std::complex<double>;
using Cancellation = std::function<bool()>;

class Cancelled : public std::runtime_error {
public:
 Cancelled() : std::runtime_error("Numerical state evolution cancelled") {}
};

// Numerical pure-state storage. Wire 0 is the leftmost (most significant) bit.
// This component does not change the symbolic calculator or circuit GUI limits.
class StateVector {
 unsigned qubits_;
 bool valid_ = true;
 std::vector<Complex> amplitudes_;
 void requireValid() const;
public:
 // Allocation is bounded before shifting or allocating. The current numerical
 // backend supports at most 25 qubits; callers can impose a smaller byte budget.
 explicit StateVector(unsigned qubits, std::size_t byteBudget,
                      const Cancellation &cancelled = Cancellation());
 StateVector(const StateVector &) = delete;
 StateVector &operator=(const StateVector &) = delete;
 unsigned qubits() const { return qubits_; }
 std::size_t size() const { return amplitudes_.size(); }
 bool valid() const { return valid_; }
 Complex amplitude(std::size_t index) const;
 double normSquared() const;
 // Row-major 2^k by 2^k unitary, for 1 <= k <= 3 distinct ordered wires.
 // The first listed wire is the local matrix's most significant bit.
 // Invalid arguments leave the state unchanged. Cancellation during mutation
 // invalidates it: partial evolution must never be used as a physical result.
 void apply(const std::vector<Complex> &unitary,
            const std::vector<unsigned> &wires,
            const Cancellation &cancelled = Cancellation());
};
}
#endif
