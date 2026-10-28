// GPL-2.0-or-later; see COPYING.
#include "QuantumClassicalRealExpression.h"
#include "QuantumClassicalIntegerStorage.h"
#include "QuantumClassical.h"
#include <algorithm>
#include <stdexcept>
namespace QuantumClassical {
namespace {
void bounds(unsigned depth,unsigned count){if(depth>32 || count>512)throw std::length_error("Real expression exceeds 32 levels or 512 expanded nodes");}
bool angle(NumericType type){return type.kind()==NumericType::Kind::Angle;}
}
struct RealExpression::Node {
 enum class Kind { Constant, Integer, Binary, Variable, Cast, Bits, Function, Scale, ArrayElement };
 Kind kind;NumericType type;std::uint64_t value=0,references=0;std::size_t slot=0;
 Operation operation=Operation::Add;NumericValue::Function function=NumericValue::Function::Negate;NumericValue::Scaling scaling=NumericValue::Scaling::Multiply;
 unsigned depth=1,count=1;
 std::shared_ptr<const IntegerExpression> integer;
 std::shared_ptr<const QuantumClassical::Bits> bits;
 std::shared_ptr<const Node> left,right;
 std::shared_ptr<const ArraySelection> selection;
 Node(Kind kind,NumericType type):kind(kind),type(type) {}
 void bound() {
  depth=1+std::max(left ? left->depth : 0,right ? right->depth : 0);count=1+(left ? left->count : 0)+(right ? right->count : 0);
  references=(left ? left->references : 0)|(right ? right->references : 0);
  if(integer){depth=std::max(depth,1+integer->depth());count+=integer->count();references|=integer->references();}
  if(bits){depth=std::max(depth,1+bits->depth());count+=bits->count();references|=bits->references();}
  if(selection){depth=std::max(depth,1+selection->depth());count+=selection->count();references|=selection->references();}
  bounds(depth,count);
 }
 void validate(unsigned registerBits,const IntegerStorage &storage) const {
  if(selection) {
   selection->validate(registerBits,storage);
   if(storage.array(selection->array()).numericType()!=type)throw std::invalid_argument("Numeric array read type does not match its declaration");
  }
  if(integer)integer->validate(registerBits,storage);
  if(bits)bits->validate(registerBits,storage);
  if(kind==Kind::Variable && storage.numeric().type(slot)!=type)throw std::invalid_argument("Numeric variable type does not match its declaration");
  if(left)left->validate(registerBits,storage);if(right)right->validate(registerBits,storage);
 }
 NumericValue evaluate(std::uint64_t record,unsigned registerBits,const IntegerStorage &storage) const {
  if(selection)return storage.numeric().read(selection->evaluate(record,registerBits,storage));
  if(kind==Kind::Constant)return NumericValue::fromBits(type,value);
  if(kind==Kind::Variable)return storage.numeric().read(slot);
  if(kind==Kind::Integer)return NumericValue::fromInteger(integer->evaluate(record,registerBits,storage),type.width());
  if(kind==Kind::Bits)return NumericValue::fromBits(type,bits->evaluate(record,registerBits,storage));
  const auto a=left->evaluate(record,registerBits,storage);
  if(kind==Kind::Cast)return a.cast(type);
  if(kind==Kind::Function)return a.function(function);
  if(kind==Kind::Scale)return a.scale(scaling,integer->evaluate(record,registerBits,storage));
  const auto b=right->evaluate(record,registerBits,storage);return a.binary(operation,b);
 }
};
RealExpression RealExpression::constant(double value){return constant(NumericValue::floating(value));}
RealExpression RealExpression::constant(const NumericValue &value){auto n=std::make_shared<Node>(Node::Kind::Constant,value.type());n->value=value.bits();return RealExpression(n);}
RealExpression RealExpression::fromInteger(const IntegerExpression &value,unsigned width) {
 auto n=std::make_shared<Node>(Node::Kind::Integer,NumericType::floating(width));n->integer=std::make_shared<const IntegerExpression>(value);n->bound();return RealExpression(n);
}
RealExpression RealExpression::variable(NumericType type,std::size_t slot){auto n=std::make_shared<Node>(Node::Kind::Variable,type);n->slot=slot;return RealExpression(n);}
RealExpression RealExpression::arrayElement(NumericType type,const ArraySelection &selection) {
 auto n=std::make_shared<Node>(Node::Kind::ArrayElement,type);n->selection=std::make_shared<const ArraySelection>(selection);n->bound();return RealExpression(n);
}
RealExpression RealExpression::cast(NumericType type,const RealExpression &value) {
 if(angle(value.type()) && !angle(type))throw std::invalid_argument("Angles cannot be cast to float");
 auto n=std::make_shared<Node>(Node::Kind::Cast,type);n->left=value.node_;n->bound();return RealExpression(n);
}
RealExpression RealExpression::fromBits(unsigned width,const Bits &value) {
 if(width!=value.width())throw std::invalid_argument("Bit-to-angle casts require matching widths");
 auto n=std::make_shared<Node>(Node::Kind::Bits,NumericType::angle(width));n->bits=std::make_shared<const Bits>(value);n->bound();return RealExpression(n);
}
RealExpression RealExpression::function(NumericValue::Function function,const RealExpression &value) {
 NumericType type=value.type();
 switch(function) {
  case NumericValue::Function::Sin:case NumericValue::Function::Cos:case NumericValue::Function::Tan:
   if(angle(type))type=NumericType::floating();break;
  case NumericValue::Function::Negate:break;
  case NumericValue::Function::Complement:if(!angle(type))throw std::invalid_argument("Bitwise complement requires an angle");break;
  case NumericValue::Function::Arcsin:case NumericValue::Function::Arccos:case NumericValue::Function::Arctan:
  case NumericValue::Function::Exp:case NumericValue::Function::Log:case NumericValue::Function::Sqrt:
  case NumericValue::Function::Floor:case NumericValue::Function::Ceiling:
   if(angle(type))throw std::invalid_argument("Only trigonometric functions accept angles");break;
  default:throw std::invalid_argument("Unknown numeric function");
 }
 auto n=std::make_shared<Node>(Node::Kind::Function,type);n->function=function;n->left=value.node_;n->bound();return RealExpression(n);
}
RealExpression RealExpression::scale(NumericValue::Scaling operation,const RealExpression &value,const IntegerExpression &integer) {
 if(!angle(value.type()) || integer.type().signedness()!=Integer::Signedness::Unsigned)throw std::invalid_argument("Angle scaling requires an unsigned integer");
 switch(operation){case NumericValue::Scaling::Multiply:case NumericValue::Scaling::Divide:
  if(integer.type().width()!=value.type().width())throw std::invalid_argument("Angle scaling requires equal widths");break;
  case NumericValue::Scaling::ShiftLeft:case NumericValue::Scaling::ShiftRight:break;
  default:throw std::invalid_argument("Unknown angle scaling operation");}
 auto n=std::make_shared<Node>(Node::Kind::Scale,value.type());n->scaling=operation;n->left=value.node_;n->integer=std::make_shared<const IntegerExpression>(integer);n->bound();return RealExpression(n);
}
RealExpression RealExpression::binary(Operation operation,const RealExpression &left,const RealExpression &right) {
 auto type=NumericType::floating(std::max(left.type().width(),right.type().width())==32 ? 32 : 64);
 if(angle(left.type()) || angle(right.type())) {
  if(left.type()!=right.type())throw std::invalid_argument("Angle operands must have the same width");type=left.type();
  switch(operation){case Operation::Add:case Operation::Subtract:case Operation::And:case Operation::Or:case Operation::Xor:break;default:throw std::invalid_argument("Unsupported operation between angles");}
 } else {
  switch(operation){case Operation::Add:case Operation::Subtract:case Operation::Multiply:case Operation::Divide:case Operation::Power:case Operation::Mod:break;default:throw std::invalid_argument("Unsupported floating-point operation");}
 }
 auto n=std::make_shared<Node>(Node::Kind::Binary,type);n->operation=operation;n->left=left.node_;n->right=right.node_;n->bound();return RealExpression(n);
}
NumericType RealExpression::type() const{return node_->type;}
unsigned RealExpression::depth() const{return node_->depth;}
unsigned RealExpression::count() const{return node_->count;}
std::uint64_t RealExpression::references() const{return node_->references;}
void RealExpression::validate(unsigned bits,const IntegerStorage &storage) const {
 if(bits>64)throw std::out_of_range("Real expression register exceeds 64 bits");node_->validate(bits,storage);
}
NumericValue RealExpression::evaluateTyped(std::uint64_t record,unsigned bits,const IntegerStorage &storage) const {
 validate(bits,storage);if(bits<64 && (record>>bits))throw std::out_of_range("Real runtime record exceeds the register");return node_->evaluate(record,bits,storage);
}
double RealExpression::evaluate(std::uint64_t record,unsigned bits,const IntegerStorage &storage) const{return evaluateTyped(record,bits,storage).radians();}
}
