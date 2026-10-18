// GPL-2.0-or-later; see COPYING.
#include "QuantumClassicalIntegerExpression.h"
#include "QuantumClassicalIntegerStorage.h"
#include "QuantumClassical.h"
#include <algorithm>
#include <stdexcept>
namespace QuantumClassical {
namespace {
std::uint64_t recordMask(unsigned bits) {
 if(bits>64)throw std::out_of_range("Integer expression register exceeds 64 bits");
 return bits==64 ? ~std::uint64_t(0) : (std::uint64_t(1)<<bits)-1;
}
void checkOperation(Integer::Operation operation) {
 switch(operation) {
  case Integer::Operation::Add:case Integer::Operation::Subtract:case Integer::Operation::Multiply:
  case Integer::Operation::Divide:case Integer::Operation::Remainder:case Integer::Operation::Power:return;
 }
 throw std::invalid_argument("Unknown runtime integer operation");
}
}
struct IntegerExpression::Node {
 enum class Kind { Constant, Read, Cast, Binary, Variable, BitExpression };
 Kind kind;IntegerType type;Integer::Operation operation=Integer::Operation::Add;
 std::uint64_t value=0,references=0;unsigned depth=1,count=1;
 std::vector<unsigned> indices;std::shared_ptr<const Node> left,right;
 std::size_t slot=0;
 std::shared_ptr<const Bits> bits;
 Node(Kind kind,IntegerType type):kind(kind),type(type) {}
 void bound() {
  depth=1+std::max(left ? left->depth : 0,right ? right->depth : 0);
  count=1+(left ? left->count : 0)+(right ? right->count : 0);
  references=(left ? left->references : 0)|(right ? right->references : 0);
  if(depth>32 || count>512)throw std::length_error("Integer expression exceeds 32 levels or 512 expanded nodes");
 }
 void validateVariables(const IntegerStorage *storage) const {
  if(bits) {
   if(storage)bits->validate(64,*storage);else bits->validate(64);
  }
  if(kind==Kind::Variable) {
   if(!storage)throw std::invalid_argument("Integer variable requires runtime storage");
   if(storage->type(slot)!=type)throw std::invalid_argument("Integer variable type does not match its declaration");
  }
  if(left)left->validateVariables(storage);
  if(right)right->validateVariables(storage);
 }
 TypedInteger evaluate(std::uint64_t record,const IntegerStorage *storage) const {
  if(kind==Kind::BitExpression)return TypedInteger::fromBits(type,
   storage ? bits->evaluate(record,64,*storage) : bits->evaluate(record,64));
  if(kind==Kind::Variable) {
   if(!storage)throw std::invalid_argument("Integer variable requires runtime storage");
   return storage->read(slot);
  }
  if(kind==Kind::Constant)return TypedInteger::fromBits(type,value);
  if(kind==Kind::Read) {
   std::uint64_t bits=0;
   for(unsigned k=0;k<indices.size();++k)bits|=((record>>indices[k])&1)<<k;
   return TypedInteger::fromBits(type,bits);
  }
  auto a=left->evaluate(record,storage);
  if(kind==Kind::Cast)return a.cast(type);
  return a.binary(operation,right->evaluate(record,storage));
 }
};
IntegerExpression IntegerExpression::constant(const TypedInteger &value) {
 auto n=std::make_shared<Node>(Node::Kind::Constant,value.type());n->value=value.value().bits();return IntegerExpression(n);
}
IntegerExpression IntegerExpression::read(IntegerType type,const std::vector<unsigned> &indices) {
 if(indices.size()!=type.width())throw std::invalid_argument("Integer read width must match its declared type");
 auto n=std::make_shared<Node>(Node::Kind::Read,type);
 for(unsigned bit:indices) {
  if(bit>=64)throw std::out_of_range("Integer read index exceeds 63");
  n->references|=std::uint64_t(1)<<bit;
 }
 n->indices=indices;return IntegerExpression(n);
}
IntegerExpression IntegerExpression::cast(IntegerType type,const IntegerExpression &operand) {
 auto n=std::make_shared<Node>(Node::Kind::Cast,type);n->left=operand.node_;n->bound();return IntegerExpression(n);
}
IntegerExpression IntegerExpression::fromBits(IntegerType type,const Bits &operand) {
 if(type.width()!=operand.width())throw std::invalid_argument("Bit expression width must match its integer type");
 auto n=std::make_shared<Node>(Node::Kind::BitExpression,type);
 n->depth=1+operand.depth();n->count=1+operand.count();n->references=operand.references();
 if(n->depth>32 || n->count>512)throw std::length_error("Integer expression exceeds 32 levels or 512 expanded nodes");
 n->bits=std::make_shared<const Bits>(operand);return IntegerExpression(n);
}
IntegerExpression IntegerExpression::variable(IntegerType type,std::size_t index) {
 auto n=std::make_shared<Node>(Node::Kind::Variable,type);n->slot=index;return IntegerExpression(n);
}
IntegerExpression IntegerExpression::binary(Integer::Operation operation,const IntegerExpression &left,const IntegerExpression &right) {
 checkOperation(operation);
 auto n=std::make_shared<Node>(Node::Kind::Binary,IntegerType::common(left.type(),right.type()));
 n->operation=operation;n->left=left.node_;n->right=right.node_;n->bound();return IntegerExpression(n);
}
unsigned IntegerExpression::depth() const {return node_->depth;}
unsigned IntegerExpression::count() const {return node_->count;}
std::uint64_t IntegerExpression::references() const {return node_->references;}
const IntegerType &IntegerExpression::type() const {return node_->type;}
void IntegerExpression::validateContext(unsigned registerBits,const IntegerStorage *storage) const {
 if(node_->references&~recordMask(registerBits))throw std::out_of_range("Integer expression references exceed the register");
 node_->validateVariables(storage);
}
void IntegerExpression::validate(unsigned registerBits) const {validateContext(registerBits,nullptr);}
void IntegerExpression::validate(unsigned registerBits,const IntegerStorage &storage) const {validateContext(registerBits,&storage);}
TypedInteger IntegerExpression::evaluate(std::uint64_t record,unsigned registerBits) const {
 validate(registerBits);
 if(record&~recordMask(registerBits))throw std::out_of_range("Integer runtime record exceeds the register");
 return node_->evaluate(record,nullptr);
}
TypedInteger IntegerExpression::evaluate(std::uint64_t record,unsigned registerBits,const IntegerStorage &storage) const {
 validate(registerBits,storage);
 if(record&~recordMask(registerBits))throw std::out_of_range("Integer runtime record exceeds the register");
 return node_->evaluate(record,&storage);
}
}
