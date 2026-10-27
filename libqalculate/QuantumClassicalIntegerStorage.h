// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_CLASSICAL_INTEGER_STORAGE_H
#define QUANTUM_CLASSICAL_INTEGER_STORAGE_H
#include "QuantumClassicalIntegerType.h"
#include "QuantumClassicalNumeric.h"
#include <vector>
#include <cstddef>
namespace QuantumClassical {
// Runtime variable slots have a fixed declared type and an explicit undefined
// state. Copying storage creates an independent branch/trajectory snapshot.
// Name resolution and lexical scope belong to the program layer.
class RuntimeStorage {
 struct Slot {
  IntegerType type;std::uint64_t bits=0;bool initialized=false;
  explicit Slot(IntegerType declared):type(declared) {}
 };
 std::vector<Slot> slots_;
 NumericStorage numeric_;
public:
 explicit RuntimeStorage(const std::vector<IntegerType> &types,const std::vector<NumericType> &numericTypes={});
 std::size_t size() const {return slots_.size();}
 std::size_t totalSize() const {return size()+numeric_.size();}
 const NumericStorage &numeric() const {return numeric_;}
 NumericStorage &numeric() {return numeric_;}
 IntegerType type(std::size_t index) const;
 bool initialized(std::size_t index) const;
 TypedInteger read(std::size_t index) const;
 // Evaluate RHS before calling write. Conversion completes before mutation.
 void write(std::size_t index,const TypedInteger &value);
 void clear(std::size_t index);
};
// Preserve the existing native integer-expression interface while sharing one
// copyable activation snapshot with the separately typed numeric slot table.
using IntegerStorage=RuntimeStorage;
}
#endif
