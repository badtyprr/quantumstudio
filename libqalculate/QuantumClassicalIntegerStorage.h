// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_CLASSICAL_INTEGER_STORAGE_H
#define QUANTUM_CLASSICAL_INTEGER_STORAGE_H
#include "QuantumClassicalIntegerType.h"
#include <vector>
#include <cstddef>
namespace QuantumClassical {
// Runtime variable slots have a fixed declared type and an explicit undefined
// state. Copying storage creates an independent branch/trajectory snapshot.
// Name resolution and lexical scope belong to the program layer.
class IntegerStorage {
 struct Slot {
  IntegerType type;std::uint64_t bits=0;bool initialized=false;
  explicit Slot(IntegerType declared):type(declared) {}
 };
 std::vector<Slot> slots_;
public:
 explicit IntegerStorage(const std::vector<IntegerType> &types);
 std::size_t size() const {return slots_.size();}
 IntegerType type(std::size_t index) const;
 bool initialized(std::size_t index) const;
 TypedInteger read(std::size_t index) const;
 // Evaluate RHS before calling write. Conversion completes before mutation.
 void write(std::size_t index,const TypedInteger &value);
 void clear(std::size_t index);
};
}
#endif
