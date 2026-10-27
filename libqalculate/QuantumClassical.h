// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_CLASSICAL_H
#define QUANTUM_CLASSICAL_H
#include <cstdint>
#include <memory>
#include <vector>

namespace QuantumClassical {
class IntegerExpression;
class RuntimeStorage;
using IntegerStorage=RuntimeStorage;
// Immutable unsigned bit-vector expressions; not OpenQASM signed/float arithmetic.
// Register/slice indices are least-significant first. Copies retain their value.
class Bits {
 friend class IntegerExpression;
 friend class RealExpression;
 unsigned depth() const;
 unsigned count() const;
 std::uint64_t references() const;
 void validateContext(unsigned registerBits,const IntegerStorage *storage) const;
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
 // One-bit And/Or with left-to-right short circuit; both branches are validated.
 static Bits logical(Binary operation,const Bits &left,const Bits &right);
 // Population count is an unsigned 64-bit internal value (0..64).
 // Compare typed runtime integers, producing one bit for assignments/branches.
 // Only the six comparison Binary values are accepted.
 static Bits integerCompare(Binary operation,const IntegerExpression &left,const IntegerExpression &right);
 // Reinterpret an explicitly sized integer without changing its width or bits.
 // Cast arithmetic results to a sized integer first; machine types are distinct.
 static Bits fromInteger(const IntegerExpression &operand);
 static Bits populationCount(const Bits &operand);
 // Signed distances use the declared two's-complement width, including bit 63.
 static Bits rotate(Direction direction,const Bits &operand,const Bits &distance,Distance interpretation);
 unsigned width() const;
 // Bounds: widths 1..64, 512 expanded nodes and 32 node levels.
 // Rejects records or references outside the supplied 0..64-bit register.
 // Check register references without evaluating a fabricated runtime value.
 void validate(unsigned registerBits) const;
 void validate(unsigned registerBits,const IntegerStorage &storage) const;
 std::uint64_t evaluate(std::uint64_t record,unsigned registerBits) const;
 std::uint64_t evaluate(std::uint64_t record,unsigned registerBits,const IntegerStorage &storage) const;
};
// Validate target width, distinctness and references without evaluating the RHS.
void validateAssignment(unsigned registerBits,const std::vector<unsigned> &targets,const Bits &expression);
void validateAssignment(unsigned registerBits,const std::vector<unsigned> &targets,const Bits &expression,const IntegerStorage &storage);
// Evaluate the full RHS against the old record, then write distinct targets.
// Overlapping source/destination slices therefore have copy semantics.
std::uint64_t assign(std::uint64_t record,unsigned registerBits,
 const std::vector<unsigned> &targets,const Bits &expression);
std::uint64_t assign(std::uint64_t record,unsigned registerBits,
 const std::vector<unsigned> &targets,const Bits &expression,const IntegerStorage &storage);
}
#endif
