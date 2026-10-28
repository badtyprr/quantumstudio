// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_CLASSICAL_ARRAY_H
#define QUANTUM_CLASSICAL_ARRAY_H
#include "QuantumClassicalIntegerExpression.h"
#include "QuantumClassicalNumeric.h"
#include <string>
namespace QuantumClassical {
// Immutable allocation metadata. Elements use the existing copied scalar slots;
// shape and bounds never depend on the values stored in those elements.
class ArrayDeclaration {
 bool numeric_;std::size_t base_,size_;
 std::vector<unsigned> dimensions_;
 IntegerType integerType_;NumericType numericType_;
 ArrayDeclaration(bool numeric,std::size_t base,const std::vector<unsigned> &dimensions,
                  IntegerType integerType,NumericType numericType);
public:
 static ArrayDeclaration integers(IntegerType type,std::size_t base,const std::vector<unsigned> &dimensions);
 static ArrayDeclaration numerics(NumericType type,std::size_t base,const std::vector<unsigned> &dimensions);
 bool numeric() const {return numeric_;}
 std::size_t base() const {return base_;}
 std::size_t size() const {return size_;}
 const std::vector<unsigned> &dimensions() const {return dimensions_;}
 IntegerType integerType() const;
 NumericType numericType() const;
 void validate(const IntegerStorage &storage) const;
};

// A rank-aware element address. Validation never reads undefined elements.
// Evaluation checks each axis before calculating the row-major scalar slot.
class ArraySelection {
 std::size_t array_;
 std::vector<IntegerExpression> indices_;
 std::string source_;
 unsigned depth_=1,count_=1;std::uint64_t references_=0;
 std::string diagnostic(const std::string &message) const;
public:
 ArraySelection(std::size_t array,const std::vector<IntegerExpression> &indices,const std::string &source="");
 std::size_t array() const {return array_;}
 unsigned depth() const {return depth_;}
 unsigned count() const {return count_;}
 std::uint64_t references() const {return references_;}
 void validate(unsigned bits,const IntegerStorage &storage) const;
 std::size_t evaluate(std::uint64_t record,unsigned bits,const IntegerStorage &storage) const;
};
}
#endif
