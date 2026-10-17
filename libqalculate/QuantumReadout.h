#ifndef QUANTUM_READOUT_H
#define QUANTUM_READOUT_H
#include <cstdint>
#include <vector>

namespace QuantumNumerics {
// Classical assignment, not a quantum channel. Row m contains P(recorded n|m).
// Targets are classical bit indices (0 has weight 1); the first target is the
// most significant bit of a matrix index. Other memory bits are preserved.
// Supports 1-8 distinct targets in a 64-bit register. Rows must sum to one
// within 1e-12; sampling uses each row's actual sum to absorb rounding error.
// Orientation follows Qiskit Aer ReadoutError:
// https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.noise.ReadoutError.html
class ReadoutAssignment {
public:
 ReadoutAssignment(const std::vector<unsigned> &targets,
                   const std::vector<std::vector<double>> &probabilities);
 std::uint64_t apply(std::uint64_t memory,double uniformDraw) const;
private:
 std::vector<unsigned> bits;
 std::vector<std::vector<double>> rows;
 std::vector<long double> totals;
 std::uint64_t mask;
};
}
#endif
