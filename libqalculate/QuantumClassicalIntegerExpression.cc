// GPL-2.0-or-later; see COPYING.
#include "QuantumClassicalIntegerExpression.h"
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
  case Integer::Operation::Divide:case Integer::Operation::Remainder:return;
 }
 throw std::invalid_argument("Unknown runtime integer operation");
}
}
struct IntegerExpression::Node {
 enum class Kind { Constant, Read, Cast, Binary };
 Kind kind;IntegerType type;Integer::Operation operation=Integer::Operation::Add;
 std::uint64_t value=0,references=0;unsigned depth=1,count=1;
 std::vector<unsigned> indices;std::shared_ptr<const Node> left,right;
 Node(Kind kind,IntegerType type):kind(kind),type(type) {}
 void bound() {
  depth=1+std::max(left ? left->depth : 0,right ? right->depth : 0);
  count=1+(left ? left->count : 0)+(right ? right->count : 0);
  references=(left ? left->references : 0)|(right ? right->references : 0);
  if(depth>32 || count>512)throw std::length_error("Integer expression exceeds 32 levels or 512 expanded nodes");
 }
 TypedInteger evaluate(std::uint64_t record) const {
  if(kind==Kind::Constant)return TypedInteger::fromBits(type,value);
  if(kind==Kind::Read) {
   std::uint64_t bits=0;
   for(unsigned k=0;k<indices.size();++k)bits|=((record>>indices[k])&1)<<k;
   return TypedInteger::fromBits(type,bits);
  }
  auto a=left->evaluate(record);
  if(kind==Kind::Cast)return a.cast(type);
  return a.binary(operation,right->evaluate(record));
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
IntegerExpression IntegerExpression::binary(Integer::Operation operation,const IntegerExpression &left,const IntegerExpression &right) {
 checkOperation(operation);
 auto n=std::make_shared<Node>(Node::Kind::Binary,IntegerType::common(left.type(),right.type()));
 n->operation=operation;n->left=left.node_;n->right=right.node_;n->bound();return IntegerExpression(n);
}
const IntegerType &IntegerExpression::type() const {return node_->type;}
void IntegerExpression::validate(unsigned registerBits) const {
 if(node_->references&~recordMask(registerBits))throw std::out_of_range("Integer expression references exceed the register");
}
TypedInteger IntegerExpression::evaluate(std::uint64_t record,unsigned registerBits) const {
 validate(registerBits);
 if(record&~recordMask(registerBits))throw std::out_of_range("Integer runtime record exceeds the register");
 return node_->evaluate(record);
}
}
