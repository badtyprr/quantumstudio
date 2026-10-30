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
ArrayViewAxis::ArrayViewAxis(bool scalar,const IntegerExpression *start,const IntegerExpression *stop,const IntegerExpression *step):scalar_(scalar),
 start_(start?std::make_shared<IntegerExpression>(*start):nullptr),stop_(stop?std::make_shared<IntegerExpression>(*stop):nullptr),step_(step?std::make_shared<IntegerExpression>(*step):nullptr) {}
ArrayViewAxis ArrayViewAxis::scalar(const IntegerExpression &index) {return {true,&index,nullptr,nullptr};}
ArrayViewAxis ArrayViewAxis::range(const IntegerExpression *start,const IntegerExpression *stop,const IntegerExpression *step) {return {false,start,stop,step};}
ArrayView::ArrayView(std::size_t array,const std::vector<ArrayViewAxis> &axes,bool writable):array_(array),axes_(axes),writable_(writable) {measure();}
ArrayView::ArrayView(const ArrayView &parent,const std::vector<ArrayViewAxis> &axes,bool writable):array_(parent.array_),parent_(std::make_shared<ArrayView>(parent)),axes_(axes),writable_(writable) {
 if(writable && !parent.writable_)throw std::invalid_argument("Readonly array references cannot become mutable");
 measure();
}
void ArrayView::measure() {
 if(array_>=4096 || axes_.empty() || axes_.size()>7)throw std::invalid_argument("Array views require one to seven selectors");
 if(parent_) {depth_=1+parent_->depth_;count_+=parent_->count_;references_|=parent_->references_;}
 for(const auto &axis:axes_)for(const auto &expression:{axis.start_,axis.stop_,axis.step_})if(expression) {
  depth_=std::max(depth_,1+expression->depth());count_+=expression->count();references_|=expression->references();
 }
 if(depth_>32 || count_>512)throw std::length_error("Array view exceeds 32 levels or 512 expression nodes");
}
unsigned ArrayView::rank() const {unsigned rank=0;for(const auto &axis:axes_)if(!axis.scalar_)++rank;return rank;}
void ArrayView::validate(unsigned bits,const IntegerStorage &storage) const {
 const auto &allocation=storage.array(array_);
 if(parent_)parent_->validate(bits,storage);
 if(axes_.size()!=(parent_?parent_->rank():allocation.dimensions().size()))throw std::invalid_argument("Array view selector rank does not match its source");
 for(const auto &axis:axes_)for(const auto &expression:{axis.start_,axis.stop_,axis.step_})if(expression)expression->validate(bits,storage);
}
ResolvedArrayView ArrayView::evaluate(std::uint64_t record,unsigned bits,const IntegerStorage &storage) const {
 validate(bits,storage);const auto &allocation=storage.array(array_);
 ResolvedArrayView source{allocation.numeric(),writable_,allocation.dimensions(),{}};
 if(parent_)source=parent_->evaluate(record,bits,storage);
 else for(std::size_t k=0;k<allocation.size();++k)source.slots.push_back(allocation.base()+k);
 ResolvedArrayView result{source.numeric,writable_,{}, {}};
 std::vector<std::vector<unsigned>> positions;
 for(std::size_t axis=0;axis<axes_.size();++axis) {
  const auto &selector=axes_[axis];const auto dimension=source.dimensions[axis];
  auto normalize=[&](const IntegerExpression &expression) {
   const auto value=expression.evaluate(record,bits,storage).value();std::uint64_t index=value.bits();
   if(value.negative()) {
    const auto magnitude=~value.cast(Integer::Signedness::Signed,64).bits()+std::uint64_t(1);
    if(magnitude>dimension)throw std::out_of_range("Array view endpoint is outside its source dimension");
    index=dimension-magnitude;
   }
   if(index>=dimension)throw std::out_of_range("Array view endpoint is outside its source dimension");
   return static_cast<unsigned>(index);
  };
  std::vector<unsigned> selected;
  if(selector.scalar_)selected.push_back(normalize(*selector.start_));
  else {
   // Resolve explicit endpoints even for an empty source. An omitted full
   // range may be empty; it never invents an address or reads a dummy cell.
   unsigned start=selector.start_?normalize(*selector.start_):0;
   bool descending=false;std::uint64_t stride=1;
   if(selector.step_) {
    const auto step=selector.step_->evaluate(record,bits,storage).value();descending=step.negative();
    stride=descending?~step.cast(Integer::Signedness::Signed,64).bits()+std::uint64_t(1):step.bits();
    if(!stride)throw std::invalid_argument("Array view step must not be zero");
   }
   unsigned stop=selector.stop_?normalize(*selector.stop_):0;
   if(dimension) {
    if(!selector.start_)start=descending?dimension-1:0;
    if(!selector.stop_)stop=descending?0:dimension-1;
    if(descending?start>=stop:start<=stop) {
     const auto distance=descending?start-stop:stop-start;
     const auto count=std::uint64_t(distance)/stride+1;
     for(std::uint64_t k=0;k<count;++k)selected.push_back(static_cast<unsigned>(descending?start-k*stride:start+k*stride));
    }
   }
   result.dimensions.push_back(static_cast<unsigned>(selected.size()));
  }
  positions.push_back(std::move(selected));
 }
 // Select from the parent's already bounded logical mapping. Enumerating at
 // most 4096 slots also makes strided overlap exact, without interval guesses.
 for(const auto &axis:positions)if(axis.empty())return result;
 std::vector<std::size_t> offsets{0};
 for(std::size_t axis=0;axis<positions.size();++axis) {
  std::vector<std::size_t> next;
  if(!positions[axis].empty() && offsets.size()>4096/positions[axis].size())throw std::length_error("Array view exceeds 4096 elements");
  for(auto prefix:offsets)for(auto index:positions[axis])next.push_back(prefix*source.dimensions[axis]+index);
  offsets=std::move(next);
 }
 for(auto offset:offsets) {
  if(offset>=source.slots.size())throw std::out_of_range("Array view address is outside its backing allocation");
  result.slots.push_back(source.slots[offset]);
 }
 return result;
}
void ArrayView::validateBindings(const std::vector<ResolvedArrayView> &views) {
 if(views.size()>4096)throw std::length_error("Too many array reference bindings");
 std::vector<bool> integers(4096,false),numerics(4096,false);
 for(const auto &view:views)if(view.writable) {
  auto &seen=view.numeric?numerics:integers;
  for(auto slot:view.slots) {
   if(slot>=seen.size())throw std::out_of_range("Array reference slot exceeds storage bounds");
   if(seen[slot])throw std::invalid_argument("Mutable array reference arguments must not overlap");
   seen[slot]=true;
  }
 }
}
ArrayReferenceCheck::ArrayReferenceCheck(const std::vector<ArrayView> &views,const std::vector<std::vector<unsigned>> &shapes):views_(views),shapes_(shapes) {
 if(views_.empty() || views_.size()>64)throw std::length_error("Array reference preflight requires one to 64 views");
 if(shapes_.empty())shapes_.resize(views_.size());
 if(shapes_.size()!=views_.size())throw std::invalid_argument("Array reference shape list does not match actuals");
 unsigned count=0;
 for(std::size_t k=0;k<views_.size();++k) {
  if(!views_[k].rank())throw std::invalid_argument("Array reference parameters require a retained array dimension");
  count+=views_[k].count();if(count>512)throw std::length_error("Array reference preflight exceeds 512 expression nodes");
  if(!shapes_[k].empty() && shapes_[k].size()!=views_[k].rank())throw std::invalid_argument("Array reference parameter rank does not match its actual");
  for(auto dimension:shapes_[k])if(dimension>4096)throw std::length_error("Array reference dimensions exceed 4096");
 }
}
void ArrayReferenceCheck::validate(unsigned bits,const IntegerStorage &storage) const {
 for(const auto &view:views_)view.validate(bits,storage);
}
void ArrayReferenceCheck::evaluate(std::uint64_t record,unsigned bits,const IntegerStorage &storage) const {
 validate(bits,storage);std::vector<ResolvedArrayView> resolved;
 for(std::size_t k=0;k<views_.size();++k) {
  resolved.push_back(views_[k].evaluate(record,bits,storage));
  if(!shapes_[k].empty() && shapes_[k]!=resolved.back().dimensions)throw std::invalid_argument("Array reference parameter shape does not match its actual");
 }
 ArrayView::validateBindings(resolved);
}
ArrayCopy::ArrayCopy(const ArrayView &destination,const std::vector<ArrayView> &sources):destination_(destination),sources_(sources) {
 if(!destination_.rank() || sources_.empty() || sources_.size()>64)throw std::invalid_argument("Array copy requires an array destination and one to 64 sources");
 if(!destination_.writable())throw std::invalid_argument("Cannot copy into a readonly array reference");
 unsigned count=destination_.count();
 for(const auto &source:sources_) {
  if(source.rank()!=destination_.rank())throw std::invalid_argument("Array copy ranks do not match");
  count+=source.count();if(count>512)throw std::length_error("Array copy exceeds 512 expression nodes");
 }
}
void ArrayCopy::validate(unsigned bits,const IntegerStorage &storage) const {
 destination_.validate(bits,storage);const auto &destination=storage.array(destination_.array());
 for(const auto &source:sources_) {
  source.validate(bits,storage);const auto &array=storage.array(source.array());
  if(array.numeric()!=destination.numeric() || (array.numeric()?array.numericType()!=destination.numericType():array.integerType()!=destination.integerType()))
   throw std::invalid_argument("Array copy element types do not match");
 }
}
void ArrayCopy::execute(std::uint64_t record,unsigned bits,IntegerStorage &storage) const {
 validate(bits,storage);const auto destination=destination_.evaluate(record,bits,storage);
 std::vector<unsigned> shape;std::vector<std::size_t> slots;
 for(const auto &source:sources_) {
  const auto selected=source.evaluate(record,bits,storage);
  if(shape.empty())shape=selected.dimensions;
  else {
   if(!std::equal(shape.begin()+1,shape.end(),selected.dimensions.begin()+1))throw std::invalid_argument("Concatenated array shapes do not match");
   if(selected.dimensions[0]>4096-shape[0])throw std::length_error("Concatenated array dimension exceeds 4096");
   shape[0]+=selected.dimensions[0];
  }
  if(selected.slots.size()>4096-slots.size())throw std::length_error("Array copy exceeds 4096 values");
  slots.insert(slots.end(),selected.slots.begin(),selected.slots.end());
 }
 if(shape!=destination.dimensions)throw std::invalid_argument("Array copy shapes do not match");
 if(destination.numeric) {
  std::vector<NumericValue> values;values.reserve(slots.size());
  for(auto slot:slots)values.push_back(storage.numeric().read(slot));
  for(std::size_t k=0;k<values.size();++k)storage.numeric().write(destination.slots[k],values[k]);
 } else {
  std::vector<TypedInteger> values;values.reserve(slots.size());
  for(auto slot:slots)values.push_back(storage.read(slot));
  for(std::size_t k=0;k<values.size();++k)storage.write(destination.slots[k],values[k]);
 }
}
ArraySelection::ArraySelection(std::size_t array,const std::vector<IntegerExpression> &indices,const std::string &source):array_(array),indices_(indices),source_(source) {measure();}
ArraySelection::ArraySelection(const ArrayView &view,const std::vector<IntegerExpression> &indices,const std::string &source):array_(view.array()),indices_(indices),view_(std::make_shared<ArrayView>(view)),source_(source) {measure();}
void ArraySelection::measure() {
 if(array_>=4096 || (!view_ && indices_.empty()) || indices_.size()>7)throw std::invalid_argument("Array selection requires one to seven indices");
 if(source_.size()>512 || source_.find('\0')!=std::string::npos)throw std::invalid_argument("Array source context exceeds its bounds");
 if(view_){depth_=1+view_->depth();count_+=view_->count();references_|=view_->references();}
 for(const auto &index:indices_) {depth_=std::max(depth_,1+index.depth());count_+=index.count();references_|=index.references();}
 if(depth_>32 || count_>512)throw std::length_error("Array selection exceeds 32 levels or 512 expression nodes");
}
std::string ArraySelection::diagnostic(const std::string &message) const {return source_.empty() ? message : source_+": "+message;}
void ArraySelection::validate(unsigned bits,const IntegerStorage &storage) const {
 const auto &array=storage.array(array_);
 if(view_)view_->validate(bits,storage);
 if(indices_.size()!=(view_?view_->rank():array.dimensions().size()))throw std::invalid_argument(diagnostic("Array index rank does not match its shape"));
 for(const auto &index:indices_)index.validate(bits,storage);
}
void ArraySelection::validateWrite(unsigned bits,const IntegerStorage &storage) const {
 validate(bits,storage);
 if(!writable())throw std::invalid_argument(diagnostic("Cannot write through a readonly array reference"));
}
void ArraySelection::validatePrefix(unsigned bits,const IntegerStorage &storage) const {
 if(view_)view_->validate(bits,storage);
 if(indices_.size()>(view_?view_->rank():storage.array(array_).dimensions().size()))throw std::invalid_argument(diagnostic("Array index prefix exceeds its shape"));
 for(const auto &index:indices_)index.validate(bits,storage);
}
void ArraySelection::checkPrefix(std::uint64_t record,unsigned bits,const IntegerStorage &storage) const {
 evaluateAddress(record,bits,storage,true);
}
std::size_t ArraySelection::evaluate(std::uint64_t record,unsigned bits,const IntegerStorage &storage) const {
 return evaluateAddress(record,bits,storage,false);
}
std::size_t ArraySelection::evaluateAddress(std::uint64_t record,unsigned bits,const IntegerStorage &storage,bool prefix) const {
 if(prefix)validatePrefix(bits,storage);else validate(bits,storage);const auto &array=storage.array(array_);std::size_t offset=0;
 ResolvedArrayView resolved{array.numeric(),true,array.dimensions(),{}};
 if(view_)resolved=view_->evaluate(record,bits,storage);
 for(std::size_t axis=0;axis<indices_.size();++axis) {
  const auto value=[&]{try{return indices_[axis].evaluate(record,bits,storage).value();}
   catch(const std::exception &error){throw std::domain_error(diagnostic(std::string("Array index: ")+error.what()));}}();
  const auto dimension=resolved.dimensions[axis];std::uint64_t index=value.bits();
  if(value.negative()) {
   const auto extended=value.cast(Integer::Signedness::Signed,64).bits();const auto magnitude=~extended+std::uint64_t(1);
   if(magnitude>dimension)throw std::out_of_range(diagnostic("Array index is outside dimension "+std::to_string(axis)));
   index=dimension-magnitude;
  }
  if(index>=dimension)throw std::out_of_range(diagnostic("Array index is outside dimension "+std::to_string(axis)));
  if(!prefix)offset=offset*dimension+static_cast<std::size_t>(index);
 }
 if(view_ && !prefix){if(offset>=resolved.slots.size())throw std::out_of_range(diagnostic("Array view element is outside its shape"));return resolved.slots[offset];}
 return array.base()+offset;
}
}
