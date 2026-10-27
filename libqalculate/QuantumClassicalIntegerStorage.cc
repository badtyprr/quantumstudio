// GPL-2.0-or-later; see COPYING.
#include "QuantumClassicalIntegerStorage.h"
#include <stdexcept>
namespace QuantumClassical {
RuntimeStorage::RuntimeStorage(const std::vector<IntegerType> &types,const std::vector<NumericType> &numericTypes):numeric_(numericTypes) {
 slots_.reserve(types.size());
 for(const auto &type:types)slots_.emplace_back(type);
}
IntegerType IntegerStorage::type(std::size_t index) const {return slots_.at(index).type;}
bool IntegerStorage::initialized(std::size_t index) const {return slots_.at(index).initialized;}
TypedInteger IntegerStorage::read(std::size_t index) const {
 const auto &slot=slots_.at(index);
 if(!slot.initialized)throw std::domain_error("Integer variable read before initialization");
 return TypedInteger::fromBits(slot.type,slot.bits);
}
void IntegerStorage::write(std::size_t index,const TypedInteger &value) {
 auto &slot=slots_.at(index);auto converted=value.cast(slot.type);
 slot.bits=converted.value().bits();slot.initialized=true;
}
void IntegerStorage::clear(std::size_t index) {
 auto &slot=slots_.at(index);slot.bits=0;slot.initialized=false;
}
}
