// GPL-2.0-or-later; see COPYING.
#include "QuantumClassicalIntegerStorage.h"
#include <stdexcept>
namespace QuantumClassical {
RuntimeStorage::RuntimeStorage(const std::vector<IntegerType> &types,const std::vector<NumericType> &numericTypes,const std::vector<ArrayDeclaration> &arrays):numeric_(numericTypes),arrays_(std::make_shared<const std::vector<ArrayDeclaration>>(arrays)) {
 if(types.size()+numericTypes.size()>4096 || arrays.size()>4096)throw std::length_error("Runtime storage exceeds 4096 slots or arrays");
 slots_.reserve(types.size());
 for(const auto &type:types)slots_.emplace_back(type);
 for(std::size_t k=0;k<arrays.size();++k) {
  arrays[k].validate(*this);
  for(std::size_t j=0;j<k;++j)if(arrays[k].numeric()==arrays[j].numeric() && arrays[k].size() && arrays[j].size() &&
    arrays[k].base()<arrays[j].base()+arrays[j].size() && arrays[j].base()<arrays[k].base()+arrays[k].size())
   throw std::invalid_argument("Array backing allocations must not overlap");
 }
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
