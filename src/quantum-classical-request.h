// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_CLASSICAL_REQUEST_H
#define QUANTUM_CLASSICAL_REQUEST_H
#include <libqalculate/QuantumClassical.h>
#include <libqalculate/QuantumClassicalIntegerExpression.h>
#include <limits>
#include <stdexcept>

// Shared prefix-tree decoder. Reader supplies bounded, LF-terminated integers.
// Bound recursion before descending, not after constructing an oversized tree.
namespace QuantumClassicalRequest {
template<class Reader>
QuantumClassical::IntegerType integerType(Reader &reader) {
 using namespace QuantumClassical;
 const auto sign=reader.integer(1)==0 ? Integer::Signedness::Signed : Integer::Signedness::Unsigned;
 const unsigned width=static_cast<unsigned>(reader.integer(64));
 return width ? IntegerType::sized(sign,width) : IntegerType::machine(sign);
}
template<class Reader>
QuantumClassical::IntegerExpression integerNode(Reader &reader,unsigned depth,unsigned &count) {
 using namespace QuantumClassical;
 if(depth>=32 || ++count>512)throw std::length_error("Classical expression exceeds 32 levels or 512 nodes.");
 const auto kind=reader.integer(3);
 if(kind==3) {
  const Integer::Operation operations[]={Integer::Operation::Add,Integer::Operation::Subtract,
   Integer::Operation::Multiply,Integer::Operation::Divide,Integer::Operation::Remainder};
  const auto operation=operations[reader.integer(4)];
  auto left=integerNode(reader,depth+1,count);auto right=integerNode(reader,depth+1,count);
  return IntegerExpression::binary(operation,left,right);
 }
 auto type=integerType(reader);
 if(kind==0)return IntegerExpression::constant(TypedInteger::fromBits(type,reader.integer(std::numeric_limits<std::uint64_t>::max())));
 if(kind==2)return IntegerExpression::cast(type,integerNode(reader,depth+1,count));
 std::vector<unsigned> indices;
 for(unsigned k=0;k<type.width();++k)indices.push_back(static_cast<unsigned>(reader.integer(63)));
 return IntegerExpression::read(type,indices);
}
template<class Reader>
QuantumClassical::Bits node(Reader &reader,unsigned depth,unsigned &count,bool typed) {
 using Bits=QuantumClassical::Bits;
 if(depth>=32 || ++count>512)throw std::length_error("Classical expression exceeds 32 levels or 512 nodes.");
 unsigned kind=static_cast<unsigned>(reader.integer(typed ? 8 : 5));
 if(kind==8)return Bits::fromInteger(integerNode(reader,depth+1,count));
 if(kind==7) {
  const auto operation=reader.integer(1)==0 ? Bits::Binary::And : Bits::Binary::Or;
  auto left=node(reader,depth+1,count,typed);auto right=node(reader,depth+1,count,typed);
  return Bits::logical(operation,left,right);
 }
 if(kind==6) {
  const Bits::Binary comparisons[]={Bits::Binary::Equal,Bits::Binary::NotEqual,Bits::Binary::Less,
   Bits::Binary::LessEqual,Bits::Binary::Greater,Bits::Binary::GreaterEqual};
  const auto operation=comparisons[reader.integer(5)];
  auto left=integerNode(reader,depth+1,count);auto right=integerNode(reader,depth+1,count);
  return Bits::integerCompare(operation,left,right);
 }
 if(kind==0) {
  unsigned width=static_cast<unsigned>(reader.integer(64));
  auto value=reader.integer(std::numeric_limits<std::uint64_t>::max());
  return Bits::constant(width,value);
 }
 if(kind==1) {
  unsigned size=static_cast<unsigned>(reader.integer(64));std::vector<unsigned> indices;
  for(unsigned k=0;k<size;++k)indices.push_back(static_cast<unsigned>(reader.integer(63)));
  return Bits::read(indices);
 }
 if(kind==2)return Bits::complement(node(reader,depth+1,count,typed));
 if(kind==4)return Bits::populationCount(node(reader,depth+1,count,typed));
 if(kind==5) {
  const auto direction=reader.integer(1)==0 ? Bits::Direction::Left : Bits::Direction::Right;
  const auto interpretation=reader.integer(1)==0 ? Bits::Distance::Unsigned : Bits::Distance::Signed;
  auto value=node(reader,depth+1,count,typed);auto distance=node(reader,depth+1,count,typed);
  return Bits::rotate(direction,value,distance,interpretation);
 }
 // Explicit wire mapping remains stable if the C++ enum is reordered.
 const Bits::Binary operations[]={Bits::Binary::And,Bits::Binary::Or,Bits::Binary::Xor,
  Bits::Binary::ShiftLeft,Bits::Binary::ShiftRight,Bits::Binary::Equal,Bits::Binary::NotEqual,
  Bits::Binary::Less,Bits::Binary::LessEqual,Bits::Binary::Greater,Bits::Binary::GreaterEqual};
 unsigned operation=static_cast<unsigned>(reader.integer(10));
 auto left=node(reader,depth+1,count,typed);
 auto right=node(reader,depth+1,count,typed);
 return Bits::binary(operations[operation],left,right);
}
template<class Reader>
QuantumClassical::Bits read(Reader &reader,unsigned bits,bool typed=false) {
 unsigned count=0;auto expression=node(reader,0,count,typed);
 expression.validate(bits); // Validate even references in untaken branches.
 return expression;
}
}
#endif
