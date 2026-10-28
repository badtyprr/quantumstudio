// GPL-2.0-or-later; see COPYING.
#include "QuantumClassicalArray.h"
#include "QuantumClassicalIntegerStorage.h"
#include <algorithm>
#include <stdexcept>
namespace QuantumClassical {
ArrayDeclaration::ArrayDeclaration(bool numeric,std::size_t base,const std::vector<unsigned> &dimensions,
 IntegerType integerType,NumericType numericType):numeric_(numeric),base_(base),size_(1),dimensions_(dimensions),integerType_(integerType),numericType_(numericType) {
 if(base>4096 || dimensions.empty() || dimensions.size()>7)throw std::invalid_argument("Arrays require a bounded allocation and one to seven dimensions");
 for(unsigned dimension:dimensions)if(dimension>4096)throw std::length_error("Array dimensions must be at most 4096");
 // A zero axis has no elements, including when an earlier partial product
 // exceeds the storage bound. No dummy readable element is allocated.
 if(std::find(dimensions.begin(),dimensions.end(),0)!=dimensions.end())size_=0;
 else for(unsigned dimension:dimensions){if(size_>4096/dimension)throw std::length_error("Runtime arrays exceed 4096 elements");size_*=dimension;}
 if(size_>4096-base_)throw std::length_error("Array allocation exceeds the scalar slot limit");
}
ArrayDeclaration ArrayDeclaration::integers(IntegerType type,std::size_t base,const std::vector<unsigned> &dimensions) {
 return {false,base,dimensions,type,NumericType::floating()};
}
ArrayDeclaration ArrayDeclaration::numerics(NumericType type,std::size_t base,const std::vector<unsigned> &dimensions) {
 return {true,base,dimensions,IntegerType::machine(Integer::Signedness::Signed),type};
}
IntegerType ArrayDeclaration::integerType() const {if(numeric_)throw std::invalid_argument("Expected an integer array");return integerType_;}
NumericType ArrayDeclaration::numericType() const {if(!numeric_)throw std::invalid_argument("Expected a numeric array");return numericType_;}
void ArrayDeclaration::validate(const IntegerStorage &storage) const {
 const auto available=numeric_ ? storage.numeric().size() : storage.size();
 if(base_>available || size_>available-base_)throw std::out_of_range("Array backing allocation is outside runtime storage");
 for(std::size_t k=0;k<size_;++k) {
  if(numeric_ ? storage.numeric().type(base_+k)!=numericType_ : storage.type(base_+k)!=integerType_)
   throw std::invalid_argument("Array element types must match their backing slots");
 }
}
ArraySelection::ArraySelection(std::size_t array,const std::vector<IntegerExpression> &indices,const std::string &source):array_(array),indices_(indices),source_(source) {
 if(array>=4096 || indices.empty() || indices.size()>7)throw std::invalid_argument("Array selection requires one to seven indices");
 if(source.size()>512 || source.find('\0')!=std::string::npos)throw std::invalid_argument("Array source context exceeds its bounds");
 for(const auto &index:indices_) {depth_=std::max(depth_,1+index.depth());count_+=index.count();references_|=index.references();}
 if(depth_>32 || count_>512)throw std::length_error("Array selection exceeds 32 levels or 512 expression nodes");
}
std::string ArraySelection::diagnostic(const std::string &message) const {return source_.empty() ? message : source_+": "+message;}
void ArraySelection::validate(unsigned bits,const IntegerStorage &storage) const {
 const auto &array=storage.array(array_);
 if(indices_.size()!=array.dimensions().size())throw std::invalid_argument(diagnostic("Array index rank does not match its shape"));
 for(const auto &index:indices_)index.validate(bits,storage);
}
std::size_t ArraySelection::evaluate(std::uint64_t record,unsigned bits,const IntegerStorage &storage) const {
 validate(bits,storage);const auto &array=storage.array(array_);std::size_t offset=0;
 for(std::size_t axis=0;axis<indices_.size();++axis) {
  const auto value=[&]{try{return indices_[axis].evaluate(record,bits,storage).value();}
   catch(const std::exception &error){throw std::domain_error(diagnostic(std::string("Array index: ")+error.what()));}}();
  const auto dimension=array.dimensions()[axis];std::uint64_t index=value.bits();
  if(value.negative()) {
   const auto extended=value.cast(Integer::Signedness::Signed,64).bits();const auto magnitude=~extended+std::uint64_t(1);
   if(magnitude>dimension)throw std::out_of_range(diagnostic("Array index is outside dimension "+std::to_string(axis)));
   index=dimension-magnitude;
  }
  if(index>=dimension)throw std::out_of_range(diagnostic("Array index is outside dimension "+std::to_string(axis)));
  offset=offset*dimension+static_cast<std::size_t>(index);
 }
 return array.base()+offset;
}
}
