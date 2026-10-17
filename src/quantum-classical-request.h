// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_CLASSICAL_REQUEST_H
#define QUANTUM_CLASSICAL_REQUEST_H
#include <libqalculate/QuantumClassical.h>
#include <limits>
#include <stdexcept>

// Shared prefix-tree decoder. Reader supplies bounded, LF-terminated integers.
// Bound recursion before descending, not after constructing an oversized tree.
namespace QuantumClassicalRequest {
template<class Reader>
QuantumClassical::Bits node(Reader &reader,unsigned depth,unsigned &count) {
 using Bits=QuantumClassical::Bits;
 if(depth>=32 || ++count>512)throw std::length_error("Classical expression exceeds 32 levels or 512 nodes.");
 unsigned kind=static_cast<unsigned>(reader.integer(5));
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
 if(kind==2)return Bits::complement(node(reader,depth+1,count));
 if(kind==4)return Bits::populationCount(node(reader,depth+1,count));
 if(kind==5) {
  const auto direction=reader.integer(1)==0 ? Bits::Direction::Left : Bits::Direction::Right;
  const auto interpretation=reader.integer(1)==0 ? Bits::Distance::Unsigned : Bits::Distance::Signed;
  auto value=node(reader,depth+1,count);auto distance=node(reader,depth+1,count);
  return Bits::rotate(direction,value,distance,interpretation);
 }
 // Explicit wire mapping remains stable if the C++ enum is reordered.
 const Bits::Binary operations[]={Bits::Binary::And,Bits::Binary::Or,Bits::Binary::Xor,
  Bits::Binary::ShiftLeft,Bits::Binary::ShiftRight,Bits::Binary::Equal,Bits::Binary::NotEqual,
  Bits::Binary::Less,Bits::Binary::LessEqual,Bits::Binary::Greater,Bits::Binary::GreaterEqual};
 unsigned operation=static_cast<unsigned>(reader.integer(10));
 auto left=node(reader,depth+1,count);
 auto right=node(reader,depth+1,count);
 return Bits::binary(operations[operation],left,right);
}
template<class Reader>
QuantumClassical::Bits read(Reader &reader,unsigned bits) {
 unsigned count=0;auto expression=node(reader,0,count);
 expression.evaluate(0,bits); // Validate even references in untaken branches.
 return expression;
}
}
#endif
