// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_CLASSICAL_H
#define QUANTUM_CLASSICAL_H
#include <cstdint>
#include <memory>
#include <vector>

namespace QuantumClassical {
// Immutable unsigned bit-vector expressions; not OpenQASM signed/float arithmetic.
// Register/slice indices are least-significant first. Copies retain their value.
class Bits {
 struct Node;
 std::shared_ptr<const Node> node_;
 explicit Bits(std::shared_ptr<const Node> node):node_(node) {}
public:
 enum class Binary { And, Or, Xor, ShiftLeft, ShiftRight, Equal, NotEqual, Less, LessEqual, Greater, GreaterEqual };
 enum class Direction { Left, Right };
 enum class Distance { Unsigned, Signed };
 Bits(const Bits &)=default;
 Bits &operator=(const Bits &)=default;
 static Bits constant(unsigned width,std::uint64_t value);
 static Bits read(const std::vector<unsigned> &indices);
 static Bits complement(const Bits &operand);
 static Bits binary(Binary operation,const Bits &left,const Bits &right);
 // Population count is an unsigned 64-bit internal value (0..64).
 static Bits populationCount(const Bits &operand);
 // Signed distances use the declared two's-complement width, including bit 63.
 static Bits rotate(Direction direction,const Bits &operand,const Bits &distance,Distance interpretation);
 unsigned width() const;
 // Bounds: widths 1..64, 512 expanded nodes and 32 node levels.
 // Rejects records or references outside the supplied 0..64-bit register.
 std::uint64_t evaluate(std::uint64_t record,unsigned registerBits) const;
};
// Evaluate the full RHS against the old record, then write distinct targets.
// Overlapping source/destination slices therefore have copy semantics.
std::uint64_t assign(std::uint64_t record,unsigned registerBits,
 const std::vector<unsigned> &targets,const Bits &expression);
}
#endif
