// GPL-2.0-or-later; see COPYING.
#include "QuantumClassical.h"
#include "QuantumClassicalIntegerExpression.h"
#include <algorithm>
#include <stdexcept>

namespace QuantumClassical {
namespace {
std::uint64_t mask(unsigned width) {
 if(width>64)throw std::out_of_range("Classical bit width exceeds 64");
 return width==64 ? ~std::uint64_t(0) : (std::uint64_t(1)<<width)-1;
}
}
struct Bits::Node {
 enum class Kind { Constant, Read, Complement, Binary, PopulationCount, Rotate, IntegerCompare, Logical, IntegerBits };
 Kind kind;Binary operation=Binary::And;
 Direction direction=Direction::Left;Distance interpretation=Distance::Unsigned;
 unsigned width,depth=1,count=1;std::uint64_t value=0,references=0;
 std::shared_ptr<const IntegerExpression> integerLeft,integerRight;
 std::vector<unsigned> indices;std::shared_ptr<const Node> left,right;
 explicit Node(Kind k,unsigned w):kind(k),width(w) {
  if(!w || w>64)throw std::out_of_range("Classical expressions require 1..64 bits");
 }
 void bound() {
  depth=1+std::max(left ? left->depth : 0,right ? right->depth : 0);
  count=1+(left ? left->count : 0)+(right ? right->count : 0);
  references=(left ? left->references : 0)|(right ? right->references : 0);
  if(depth>32 || count>512)throw std::length_error("Classical expression exceeds 32 levels or 512 expanded nodes");
 }
 void validateVariables(unsigned registerBits,const IntegerStorage *storage) const {
  for(const auto &integer:{integerLeft,integerRight})if(integer) {
   if(storage)integer->validate(registerBits,*storage);else integer->validate(registerBits);
  }
  if(left)left->validateVariables(registerBits,storage);
  if(right)right->validateVariables(registerBits,storage);
 }
 std::uint64_t evaluate(std::uint64_t record,const IntegerStorage *storage) const {
  auto integerValue=[&](const IntegerExpression &integer) {
   return storage ? integer.evaluate(record,64,*storage) : integer.evaluate(record,64);
  };
  if(kind==Kind::Constant)return value;
  if(kind==Kind::IntegerBits)return integerValue(*integerLeft).value().bits();
  if(kind==Kind::Read) {
   std::uint64_t result=0;
   for(unsigned k=0;k<indices.size();++k)result|=((record>>indices[k])&1)<<k;
   return result;
  }
  if(kind==Kind::IntegerCompare) {
   const int comparison=integerValue(*integerLeft).compare(integerValue(*integerRight));
   switch(operation) {
    case Binary::Equal:return comparison==0;case Binary::NotEqual:return comparison!=0;
    case Binary::Less:return comparison<0;case Binary::LessEqual:return comparison<=0;
    case Binary::Greater:return comparison>0;case Binary::GreaterEqual:return comparison>=0;
    default:throw std::logic_error("Invalid integer comparison");
   }
  }
  auto a=left->evaluate(record,storage);
  if(kind==Kind::Complement)return (~a)&mask(width);
  if(kind==Kind::PopulationCount) {
   std::uint64_t result=0;for(;a;a&=a-1)++result;return result;
  }
  if(kind==Kind::Logical && ((operation==Binary::And && !a) || (operation==Binary::Or && a)))return a;
  auto b=right->evaluate(record,storage);
  if(kind==Kind::Rotate) {
   bool leftward=direction==Direction::Left;
   if(interpretation==Distance::Signed && (b&(std::uint64_t(1)<<(right->width-1)))) {
    b=(~b+1)&mask(right->width);leftward=!leftward;
   }
   const unsigned distance=static_cast<unsigned>(b%width);
   if(!distance)return a; // In particular, never shift a 64-bit value by 64.
   return (leftward ? (a<<distance)|(a>>(width-distance)) : (a>>distance)|(a<<(width-distance)))&mask(width);
  }
  switch(operation) {
   case Binary::And:return a&b;
   case Binary::Or:return a|b;
   case Binary::Xor:return a^b;
   case Binary::ShiftLeft:return b>=width ? 0 : (a<<b)&mask(width);
   case Binary::ShiftRight:return b>=width ? 0 : a>>b;
   case Binary::Equal:return a==b;
   case Binary::NotEqual:return a!=b;
   case Binary::Less:return a<b;
   case Binary::LessEqual:return a<=b;
   case Binary::Greater:return a>b;
   case Binary::GreaterEqual:return a>=b;
  }
  throw std::logic_error("Invalid classical operation");
 }
};
Bits Bits::constant(unsigned width,std::uint64_t value) {
 auto node=std::make_shared<Node>(Node::Kind::Constant,width);
 if(value&~mask(width))throw std::out_of_range("Classical constant does not fit its width");
 node->value=value;return Bits(node);
}
Bits Bits::read(const std::vector<unsigned> &indices) {
 if(indices.empty() || indices.size()>64)throw std::out_of_range("Classical reads require 1..64 indices");
 auto node=std::make_shared<Node>(Node::Kind::Read,static_cast<unsigned>(indices.size()));
 for(unsigned bit:indices) {
  if(bit>=64)throw std::out_of_range("Classical read index exceeds 63");
  node->references|=std::uint64_t(1)<<bit;
 }
 node->indices=indices;return Bits(node);
}
Bits Bits::complement(const Bits &operand) {
 auto node=std::make_shared<Node>(Node::Kind::Complement,operand.width());
 node->left=operand.node_;node->bound();return Bits(node);
}
Bits Bits::binary(Binary operation,const Bits &left,const Bits &right) {
 unsigned width=left.width();
 switch(operation) {
  case Binary::ShiftLeft:case Binary::ShiftRight:break;
  case Binary::And:case Binary::Or:case Binary::Xor:
  case Binary::Equal:case Binary::NotEqual:case Binary::Less:case Binary::LessEqual:case Binary::Greater:case Binary::GreaterEqual:
   if(width!=right.width())throw std::invalid_argument("Classical operands require equal widths");
   if(operation!=Binary::And && operation!=Binary::Or && operation!=Binary::Xor)width=1;
   break;
  default:throw std::invalid_argument("Unknown classical binary operation");
 }
 auto node=std::make_shared<Node>(Node::Kind::Binary,width);node->operation=operation;
 node->left=left.node_;node->right=right.node_;node->bound();return Bits(node);
}
Bits Bits::logical(Binary operation,const Bits &left,const Bits &right) {
 if(operation!=Binary::And && operation!=Binary::Or)throw std::invalid_argument("Logical expressions require And or Or");
 if(left.width()!=1 || right.width()!=1)throw std::invalid_argument("Logical operands require one bit");
 auto node=std::make_shared<Node>(Node::Kind::Logical,1);node->operation=operation;
 node->left=left.node_;node->right=right.node_;node->bound();return Bits(node);
}
Bits Bits::integerCompare(Binary operation,const IntegerExpression &left,const IntegerExpression &right) {
 switch(operation) {
  case Binary::Equal:case Binary::NotEqual:case Binary::Less:case Binary::LessEqual:
  case Binary::Greater:case Binary::GreaterEqual:break;
  default:throw std::invalid_argument("Integer conditions require a comparison operation");
 }
 auto node=std::make_shared<Node>(Node::Kind::IntegerCompare,1);node->operation=operation;
 node->depth=1+std::max(left.depth(),right.depth());node->count=1+left.count()+right.count();
 node->references=left.references()|right.references();
 if(node->depth>32 || node->count>512)throw std::length_error("Classical expression exceeds 32 levels or 512 expanded nodes");
 node->integerLeft=std::make_shared<const IntegerExpression>(left);
 node->integerRight=std::make_shared<const IntegerExpression>(right);return Bits(node);
}
Bits Bits::fromInteger(const IntegerExpression &operand) {
 if(!operand.type().explicitWidth())throw std::invalid_argument("Bit casts require an explicitly sized integer");
 auto node=std::make_shared<Node>(Node::Kind::IntegerBits,operand.type().width());
 node->depth=1+operand.depth();node->count=1+operand.count();node->references=operand.references();
 if(node->depth>32 || node->count>512)throw std::length_error("Classical expression exceeds 32 levels or 512 expanded nodes");
 node->integerLeft=std::make_shared<const IntegerExpression>(operand);return Bits(node);
}
Bits Bits::populationCount(const Bits &operand) {
 auto node=std::make_shared<Node>(Node::Kind::PopulationCount,64);
 node->left=operand.node_;node->bound();return Bits(node);
}
Bits Bits::rotate(Direction direction,const Bits &operand,const Bits &distance,Distance interpretation) {
 if(direction!=Direction::Left && direction!=Direction::Right)throw std::invalid_argument("Unknown classical rotation direction");
 if(interpretation!=Distance::Unsigned && interpretation!=Distance::Signed)throw std::invalid_argument("Unknown classical distance interpretation");
 auto node=std::make_shared<Node>(Node::Kind::Rotate,operand.width());
 node->direction=direction;node->interpretation=interpretation;
 node->left=operand.node_;node->right=distance.node_;node->bound();return Bits(node);
}
unsigned Bits::width() const {return node_->width;}
void Bits::validateContext(unsigned registerBits,const IntegerStorage *storage) const {
 if(node_->references&~mask(registerBits))throw std::out_of_range("Classical record or expression exceeds its register");
 node_->validateVariables(registerBits,storage);
}
void Bits::validate(unsigned registerBits) const {validateContext(registerBits,nullptr);}
void Bits::validate(unsigned registerBits,const IntegerStorage &storage) const {validateContext(registerBits,&storage);}
std::uint64_t Bits::evaluate(std::uint64_t record,unsigned registerBits) const {
 validate(registerBits);
 if(record&~mask(registerBits))throw std::out_of_range("Classical record or expression exceeds its register");
 return node_->evaluate(record,nullptr);
}
std::uint64_t Bits::evaluate(std::uint64_t record,unsigned registerBits,const IntegerStorage &storage) const {
 validate(registerBits,storage);
 if(record&~mask(registerBits))throw std::out_of_range("Classical record or expression exceeds its register");
 return node_->evaluate(record,&storage);
}
namespace {
std::uint64_t assignmentTargets(unsigned registerBits,const std::vector<unsigned> &targets,const Bits &expression) {
 if(targets.size()!=expression.width())throw std::invalid_argument("Assignment width must match its targets");
 auto allowed=mask(registerBits);std::uint64_t seen=0;
 for(unsigned target:targets) {
  if(target>=registerBits)throw std::out_of_range("Assignment target is outside its register");
  auto flag=std::uint64_t(1)<<target;
  if(seen&flag)throw std::invalid_argument("Assignment targets must be distinct");
  seen|=flag;
 }
 (void)allowed;
 return seen;
}
}
void validateAssignment(unsigned registerBits,const std::vector<unsigned> &targets,const Bits &expression) {
 assignmentTargets(registerBits,targets,expression);
 expression.validate(registerBits);
}
void validateAssignment(unsigned registerBits,const std::vector<unsigned> &targets,const Bits &expression,const IntegerStorage &storage) {
 assignmentTargets(registerBits,targets,expression);
 expression.validate(registerBits,storage);
}
std::uint64_t assign(std::uint64_t record,unsigned registerBits,const std::vector<unsigned> &targets,const Bits &expression) {
 const auto seen=assignmentTargets(registerBits,targets,expression);
 const auto value=expression.evaluate(record,registerBits);
 auto result=record&~seen;
 for(unsigned k=0;k<targets.size();++k)result|=((value>>k)&1)<<targets[k];
 return result;
}
std::uint64_t assign(std::uint64_t record,unsigned registerBits,const std::vector<unsigned> &targets,const Bits &expression,const IntegerStorage &storage) {
 const auto seen=assignmentTargets(registerBits,targets,expression);
 const auto value=expression.evaluate(record,registerBits,storage);
 auto result=record&~seen;
 for(unsigned k=0;k<targets.size();++k)result|=((value>>k)&1)<<targets[k];
 return result;
}
}
