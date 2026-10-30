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

// A reference view never reads its elements. Runtime geometry is evaluated
// against the copied scalar frame; nested views preserve access permissions.
class ArrayViewAxis {
 friend class ArrayView;
 bool scalar_;
 std::shared_ptr<const IntegerExpression> start_,stop_,step_;
 ArrayViewAxis(bool scalar,const IntegerExpression *start,const IntegerExpression *stop,const IntegerExpression *step);
public:
 static ArrayViewAxis scalar(const IntegerExpression &index);
 static ArrayViewAxis range(const IntegerExpression *start=nullptr,const IntegerExpression *stop=nullptr,const IntegerExpression *step=nullptr);
};
struct ResolvedArrayView {
 bool numeric,writable;
 std::vector<unsigned> dimensions;
 // Absolute slots in the selected scalar table, in logical row-major order.
 std::vector<std::size_t> slots;
};
class ArrayView {
 std::size_t array_;
 std::shared_ptr<const ArrayView> parent_;
 std::vector<ArrayViewAxis> axes_;
 bool writable_;
 unsigned depth_=1,count_=1;std::uint64_t references_=0;
 void measure();
public:
 ArrayView(std::size_t array,const std::vector<ArrayViewAxis> &axes,bool writable);
 ArrayView(const ArrayView &parent,const std::vector<ArrayViewAxis> &axes,bool writable);
 unsigned rank() const;
 unsigned depth() const {return depth_;}
 unsigned count() const {return count_;}
 std::uint64_t references() const {return references_;}
 bool writable() const {return writable_;}
 std::size_t array() const {return array_;}
 void validate(unsigned bits,const IntegerStorage &storage) const;
 ResolvedArrayView evaluate(std::uint64_t record,unsigned bits,const IntegerStorage &storage) const;
 // Only pairs of mutable references conflict; readonly overlap is permitted.
 static void validateBindings(const std::vector<ResolvedArrayView> &views);
};

// A rank-aware element address. Validation never reads undefined elements.
// Evaluation checks each axis before calculating the row-major scalar slot.
class ArraySelection {
 std::size_t array_;
 std::vector<IntegerExpression> indices_;
 std::shared_ptr<const ArrayView> view_;
 std::string source_;
 unsigned depth_=1,count_=1;std::uint64_t references_=0;
 void measure();
 std::string diagnostic(const std::string &message) const;
 std::size_t evaluateAddress(std::uint64_t record,unsigned bits,const IntegerStorage &storage,bool prefix) const;
public:
 ArraySelection(std::size_t array,const std::vector<IntegerExpression> &indices,const std::string &source="");
 ArraySelection(const ArrayView &view,const std::vector<IntegerExpression> &indices,const std::string &source="");
 bool writable() const {return !view_ || view_->writable();}
 void validateWrite(unsigned bits,const IntegerStorage &storage) const;
 std::size_t array() const {return array_;}
 unsigned depth() const {return depth_;}
 unsigned count() const {return count_;}
 std::uint64_t references() const {return references_;}
 void validate(unsigned bits,const IntegerStorage &storage) const;
 void validatePrefix(unsigned bits,const IntegerStorage &storage) const;
 void checkPrefix(std::uint64_t record,unsigned bits,const IntegerStorage &storage) const;
 std::size_t evaluate(std::uint64_t record,unsigned bits,const IntegerStorage &storage) const;
};
}
#endif
