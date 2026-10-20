// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_CLASSICAL_REQUEST_H
#define QUANTUM_CLASSICAL_REQUEST_H
#include <libqalculate/QuantumClassical.h>
#include <libqalculate/QuantumClassicalIntegerExpression.h>
#include <libqalculate/QuantumClassicalIntegerStorage.h>
#include <libqalculate/QuantumClassicalRangeExpression.h>
#include <libqalculate/QuantumRuntimeRotation.h>
#include <cstring>
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
QuantumClassical::Bits node(Reader &,unsigned,unsigned &,bool,bool=false,bool=false);

template<class Reader>
QuantumClassical::IntegerExpression integerNode(Reader &reader,unsigned depth,unsigned &count,bool variables=false,bool bitExpressions=false) {
 using namespace QuantumClassical;
 if(depth>=32 || ++count>512)throw std::length_error("Classical expression exceeds 32 levels or 512 nodes.");
 const auto kind=reader.integer(bitExpressions ? 5 : variables ? 4 : 3);
 if(kind==3) {
  const Integer::Operation operations[]={Integer::Operation::Add,Integer::Operation::Subtract,
   Integer::Operation::Multiply,Integer::Operation::Divide,Integer::Operation::Remainder,Integer::Operation::Power};
  const auto operation=operations[reader.integer(5)];
  auto left=integerNode(reader,depth+1,count,variables,bitExpressions);auto right=integerNode(reader,depth+1,count,variables,bitExpressions);
  return IntegerExpression::binary(operation,left,right);
 }
 auto type=integerType(reader);
 if(kind==5)return IntegerExpression::fromBits(type,node(reader,depth+1,count,true,variables,bitExpressions));
 if(kind==4)return IntegerExpression::variable(type,static_cast<std::size_t>(reader.integer(4095)));
 if(kind==0)return IntegerExpression::constant(TypedInteger::fromBits(type,reader.integer(std::numeric_limits<std::uint64_t>::max())));
 if(kind==2)return IntegerExpression::cast(type,integerNode(reader,depth+1,count,variables,bitExpressions));
 std::vector<unsigned> indices;
 for(unsigned k=0;k<type.width();++k)indices.push_back(static_cast<unsigned>(reader.integer(63)));
 return IntegerExpression::read(type,indices);
}
template<class Reader>
QuantumClassical::Bits node(Reader &reader,unsigned depth,unsigned &count,bool typed,bool variables,bool bitExpressions) {
 using Bits=QuantumClassical::Bits;
 if(depth>=32 || ++count>512)throw std::length_error("Classical expression exceeds 32 levels or 512 nodes.");
 unsigned kind=static_cast<unsigned>(reader.integer(typed ? 8 : 5));
 if(kind==8)return Bits::fromInteger(integerNode(reader,depth+1,count,variables,bitExpressions));
 if(kind==7) {
  const auto operation=reader.integer(1)==0 ? Bits::Binary::And : Bits::Binary::Or;
  auto left=node(reader,depth+1,count,typed,variables,bitExpressions);auto right=node(reader,depth+1,count,typed,variables,bitExpressions);
  return Bits::logical(operation,left,right);
 }
 if(kind==6) {
  const Bits::Binary comparisons[]={Bits::Binary::Equal,Bits::Binary::NotEqual,Bits::Binary::Less,
   Bits::Binary::LessEqual,Bits::Binary::Greater,Bits::Binary::GreaterEqual};
  const auto operation=comparisons[reader.integer(5)];
  auto left=integerNode(reader,depth+1,count,variables,bitExpressions);auto right=integerNode(reader,depth+1,count,variables,bitExpressions);
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
 if(kind==2)return Bits::complement(node(reader,depth+1,count,typed,variables,bitExpressions));
 if(kind==4)return Bits::populationCount(node(reader,depth+1,count,typed,variables,bitExpressions));
 if(kind==5) {
  const auto direction=reader.integer(1)==0 ? Bits::Direction::Left : Bits::Direction::Right;
  const auto interpretation=reader.integer(1)==0 ? Bits::Distance::Unsigned : Bits::Distance::Signed;
  auto value=node(reader,depth+1,count,typed,variables,bitExpressions);auto distance=node(reader,depth+1,count,typed,variables,bitExpressions);
  return Bits::rotate(direction,value,distance,interpretation);
 }
 // Explicit wire mapping remains stable if the C++ enum is reordered.
 const Bits::Binary operations[]={Bits::Binary::And,Bits::Binary::Or,Bits::Binary::Xor,
  Bits::Binary::ShiftLeft,Bits::Binary::ShiftRight,Bits::Binary::Equal,Bits::Binary::NotEqual,
  Bits::Binary::Less,Bits::Binary::LessEqual,Bits::Binary::Greater,Bits::Binary::GreaterEqual};
 unsigned operation=static_cast<unsigned>(reader.integer(10));
 auto left=node(reader,depth+1,count,typed,variables,bitExpressions);
 auto right=node(reader,depth+1,count,typed,variables,bitExpressions);
 return Bits::binary(operations[operation],left,right);
}
template<class Reader>
QuantumClassical::Bits read(Reader &reader,unsigned bits,bool typed=false,const QuantumClassical::IntegerStorage *variables=nullptr,bool bitExpressions=false) {
 unsigned count=0;auto expression=node(reader,0,count,typed,variables!=nullptr,bitExpressions);
 if(variables)expression.validate(bits,*variables);else expression.validate(bits);
 return expression;
}
template<class Reader>
QuantumClassical::RangeExpression range(Reader &reader,unsigned bits,const QuantumClassical::IntegerStorage &variables) {
 unsigned count=0;auto start=integerNode(reader,0,count,true,true);
 count=0;auto stop=integerNode(reader,0,count,true,true);
 count=0;auto step=integerNode(reader,0,count,true,true);
 QuantumClassical::RangeExpression result(start,stop,step);
 result.validate(bits,variables);return result;
}

// Constants travel as unsigned IEEE-754 bit patterns, avoiding locale-dependent
// decimal parsing and preserving the binary64 value across both backends.
template<class Reader>
QuantumClassical::RealExpression realNode(Reader &reader,unsigned depth,unsigned &count) {
 using R=QuantumClassical::RealExpression;
 if(depth>=32 || ++count>512)throw std::length_error("Real expression exceeds 32 levels or 512 nodes.");
 const auto kind=reader.integer(2);
 if(kind==0) {
  static_assert(sizeof(double)==sizeof(std::uint64_t),"Binary64 protocol requires 64-bit double");
  const std::uint64_t raw=reader.integer(std::numeric_limits<std::uint64_t>::max());
  double value;std::memcpy(&value,&raw,sizeof(value));return R::constant(value);
 }
 if(kind==1)return R::fromInteger(integerNode(reader,depth+1,count,true,true));
 const R::Operation operations[]={R::Operation::Add,R::Operation::Subtract,R::Operation::Multiply,R::Operation::Divide};
 const auto operation=operations[reader.integer(3)];
 auto left=realNode(reader,depth+1,count);auto right=realNode(reader,depth+1,count);
 return R::binary(operation,left,right);
}
template<class Reader>
QuantumNumerics::RuntimeRotation rotation(Reader &reader,unsigned bits,const QuantumClassical::IntegerStorage &variables) {
 using Rotation=QuantumNumerics::RuntimeRotation;
 const Rotation::Axis axes[]={Rotation::Axis::X,Rotation::Axis::Y,Rotation::Axis::Z};
 const auto axis=axes[reader.integer(2)];unsigned count=0;
 Rotation result(axis,realNode(reader,0,count));result.validate(bits,variables);return result;
}
}
#endif
