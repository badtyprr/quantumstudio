// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_CLASSICAL_NUMERIC_H
#define QUANTUM_CLASSICAL_NUMERIC_H
#include "QuantumClassicalIntegerType.h"
#include <vector>
#include <cstddef>
#include <string>
namespace QuantumClassical {
class NumericType {
public:
 enum class Kind { Float, Angle };
 static NumericType floating(unsigned width=64);
 static NumericType angle(unsigned width);
 Kind kind() const {return kind_;}
 unsigned width() const {return width_;}
 bool operator==(NumericType other) const {return kind_==other.kind_ && width_==other.width_;}
 bool operator!=(NumericType other) const {return !(*this==other);}
private:
 Kind kind_;unsigned width_;
 NumericType(Kind kind,unsigned width):kind_(kind),width_(width) {}
};
// A finite IEEE float or a modular angle bit pattern. Angles never become
// unconstrained floating slots: only gate/trigonometric consumption uses radians.
class NumericValue {
 NumericType type_;std::uint64_t bits_;
 NumericValue(NumericType type,std::uint64_t bits):type_(type),bits_(bits) {}
public:
 enum class Operation { Add, Subtract, Multiply, Divide, Power, Mod, And, Or, Xor };
 enum class Function { Negate, Sin, Cos, Tan, Arcsin, Arccos, Arctan, Exp, Log, Sqrt, Floor, Ceiling, Complement };
 enum class Scaling { Multiply, Divide, ShiftLeft, ShiftRight };
 static NumericValue fromBits(NumericType type,std::uint64_t bits);
 static NumericValue floating(double value,unsigned width=64);
 static NumericValue fromInteger(const TypedInteger &value,unsigned width=64);
 NumericType type() const {return type_;}
 std::uint64_t bits() const {return bits_;}
 bool truth() const;
 double radians() const;
 std::string exactRadians() const;
 double floatingValue() const;
 NumericValue cast(NumericType target) const;
 TypedInteger integerCast(IntegerType target) const;
 NumericValue binary(Operation operation,const NumericValue &right) const;
 NumericValue function(Function function) const;
 NumericValue scale(Scaling operation,const TypedInteger &right) const;
 TypedInteger ratio(const NumericValue &right) const;
 int compare(const NumericValue &right) const;
};
class NumericStorage {
 struct Slot {NumericType type;std::uint64_t bits=0;bool initialized=false;explicit Slot(NumericType type):type(type) {}};
 std::vector<Slot> slots_;
public:
 explicit NumericStorage(const std::vector<NumericType> &types={});
 std::size_t size() const {return slots_.size();}
 NumericType type(std::size_t index) const;
 bool initialized(std::size_t index) const;
 NumericValue read(std::size_t index) const;
 void write(std::size_t index,const NumericValue &value);
 void clear(std::size_t index);
};
}
#endif
