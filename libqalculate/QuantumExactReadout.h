// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_EXACT_READOUT_H
#define QUANTUM_EXACT_READOUT_H
#include "MathStructure.h"
#include <cstdint>
#include <map>
#include <vector>

namespace QuantumExact {
// Exact row-stochastic assignment: rows are old records, columns new records.
// The first selected classical bit is most significant in the table index.
class ReadoutAssignment {
 std::vector<unsigned> bits_;
 MathStructure table_;
 std::uint64_t mask_;
public:
 // One to eight distinct targets within a 64-bit record, at most 256² entries.
 // Invalid probabilities throw invalid_argument; unproved constraints or
 // approximate entries throw domain_error. Symbolic proofs are preserved.
 ReadoutAssignment(const std::vector<unsigned> &bits, const MathStructure &table,
                   const EvaluationOptions &options);
 // Preserve the certificate even when constructed from an rvalue.
 ReadoutAssignment(const ReadoutAssignment &) = default;
 ReadoutAssignment &operator=(const ReadoutAssignment &) = delete;
 const std::vector<unsigned> &bits() const {return bits_;}
 std::map<std::uint64_t,MathStructure> outcomes(std::uint64_t record) const;
};
}
#endif
