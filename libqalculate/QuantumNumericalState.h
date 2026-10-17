#ifndef QUANTUM_NUMERICAL_STATE_H
#define QUANTUM_NUMERICAL_STATE_H

#include <complex>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <map>
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
 // Terminal computational-basis samples; does not collapse or modify the state.
 // Result bits follow the supplied wire order (first wire is most significant).
 // An empty wire list yields outcome 0. At most 1,000,000 shots are allowed;
 // sampling storage and returned counts are additional to the state byte budget.
 std::map<std::uint64_t, unsigned> sampleCounts(unsigned shots,
            const std::vector<unsigned> &wires, std::uint64_t seed,
            const Cancellation &cancelled = Cancellation()) const;
 // Measure one wire in the computational basis and collapse this state.
 // uniformDraw must be finite in [0,1); callers own the seeded random stream.
 // Validation and cancellation before mutation leave the state unchanged.
 // Cancellation during collapse invalidates the state, as with apply().
 bool measure(unsigned wire, double uniformDraw,
              const Cancellation &cancelled = Cancellation());
 // Sample one branch of a trace-preserving Kraus channel on 1-3 wires.
 // Returns the selected Kraus index. Draw and cancellation follow measure().
 // Accepts 1-256 finite square matrices with sum(K dagger K)=I within 1e-12.
 // Uses bounded local buffers, never another full state. Caller-owned matrices
 // are additional to the state budget. Invalid arguments leave the state intact.
 std::size_t channel(const std::vector<std::vector<Complex>> &kraus,
            const std::vector<unsigned> &wires,double uniformDraw,
            const Cancellation &cancelled = Cancellation());
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
