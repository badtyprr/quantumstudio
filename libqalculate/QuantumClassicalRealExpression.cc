// GPL-2.0-or-later; see COPYING.
#include "QuantumClassicalRealExpression.h"
#include "QuantumClassicalIntegerStorage.h"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
namespace QuantumClassical {
namespace {
static_assert(std::numeric_limits<double>::is_iec559 &&
 std::numeric_limits<double>::digits==53 && std::numeric_limits<double>::max_exponent==1024,
 "Runtime real expressions require IEEE 754 binary64 double");
double finite(double value) {
 if(!std::isfinite(value))throw std::domain_error("Runtime real expression must be finite");
 return value;
}
void bounds(unsigned depth,unsigned count) {
 if(depth>32 || count>512)throw std::length_error("Real expression exceeds 32 levels or 512 expanded nodes");
}
}
struct RealExpression::Node {
 enum class Kind { Constant, Integer, Binary };
 Kind kind;double value=0;Operation operation=Operation::Add;
 unsigned depth=1,count=1;
 std::shared_ptr<const IntegerExpression> integer;
 std::shared_ptr<const Node> left,right;
 explicit Node(Kind kind):kind(kind) {}
 void validate(unsigned bits,const IntegerStorage &storage) const {
  if(integer)integer->validate(bits,storage);
  if(left)left->validate(bits,storage);
  if(right)right->validate(bits,storage);
 }
 double evaluate(std::uint64_t record,unsigned bits,const IntegerStorage &storage) const {
  if(kind==Kind::Constant)return value;
  if(kind==Kind::Integer) {
   const auto n=integer->evaluate(record,bits,storage).value();
   // Convert magnitude without signed casts or negating INT64_MIN.
   const auto raw=n.bits();
   const auto mask=n.width()==64 ? ~std::uint64_t(0) : (std::uint64_t(1)<<n.width())-1;
   return n.negative() ? -static_cast<double>(((~raw)&mask)+1) : static_cast<double>(raw);
  }
  const double a=left->evaluate(record,bits,storage),b=right->evaluate(record,bits,storage);
  switch(operation) {
   case Operation::Add:return finite(a+b);
   case Operation::Subtract:return finite(a-b);
   case Operation::Multiply:return finite(a*b);
   case Operation::Divide:
    if(b==0)throw std::domain_error("Runtime real division by zero");
    return finite(a/b);
  }
  throw std::invalid_argument("Unknown runtime real operation");
 }
};
RealExpression RealExpression::constant(double value) {
 auto n=std::make_shared<Node>(Node::Kind::Constant);n->value=finite(value);return RealExpression(n);
}
RealExpression RealExpression::fromInteger(const IntegerExpression &value) {
 auto n=std::make_shared<Node>(Node::Kind::Integer);
 n->depth=1+value.depth();n->count=1+value.count();bounds(n->depth,n->count);
 n->integer=std::make_shared<const IntegerExpression>(value);return RealExpression(n);
}
RealExpression RealExpression::binary(Operation operation,const RealExpression &left,const RealExpression &right) {
 switch(operation) {
  case Operation::Add:case Operation::Subtract:case Operation::Multiply:case Operation::Divide:break;
  default:throw std::invalid_argument("Unknown runtime real operation");
 }
 auto n=std::make_shared<Node>(Node::Kind::Binary);
 n->operation=operation;n->left=left.node_;n->right=right.node_;
 n->depth=1+std::max(n->left->depth,n->right->depth);n->count=1+n->left->count+n->right->count;
 bounds(n->depth,n->count);return RealExpression(n);
}
void RealExpression::validate(unsigned bits,const IntegerStorage &storage) const {
 if(bits>64)throw std::out_of_range("Real expression register exceeds 64 bits");
 node_->validate(bits,storage);
}
double RealExpression::evaluate(std::uint64_t record,unsigned bits,const IntegerStorage &storage) const {
 validate(bits,storage);
 if(bits<64 && (record>>bits))throw std::out_of_range("Real runtime record exceeds the register");
 return node_->evaluate(record,bits,storage);
}
}
