// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_CLASSICAL_INTEGER_H
#define QUANTUM_CLASSICAL_INTEGER_H
#include <cstdint>
namespace QuantumClassical {
// Fixed-width integer values. Parsing, implicit promotion and register storage
// belong to the expression layer; operations here require matching types.
class Integer {
public:
 enum class Signedness { Signed, Unsigned };
 enum class Operation { Add, Subtract, Multiply, Divide, Remainder };
 static Integer fromBits(Signedness sign,unsigned width,std::uint64_t bits);
 Signedness signedness() const {return sign_;}
 unsigned width() const {return width_;}
 std::uint64_t bits() const {return bits_;}
 bool negative() const;
 // Explicit casts preserve low bits, sign-extending a negative source when
 // widening. This is a deliberate policy for narrowing integer conversions.
 Integer cast(Signedness sign,unsigned width) const;
 Integer binary(Operation operation,const Integer &right) const;
 Integer power(std::uint64_t exponent) const;
 int compare(const Integer &right) const;
private:
 Signedness sign_;unsigned width_;std::uint64_t bits_;
 Integer(Signedness sign,unsigned width,std::uint64_t bits):sign_(sign),width_(width),bits_(bits) {}
 void sameType(const Integer &right) const;
 std::int64_t signedValue() const;
 std::uint64_t magnitude() const;
 Integer signedMagnitude(bool negative,std::uint64_t magnitude) const;
};
}
#endif
