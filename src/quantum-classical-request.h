// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_CLASSICAL_REQUEST_H
#define QUANTUM_CLASSICAL_REQUEST_H
#include <libqalculate/QuantumClassical.h>
#include <libqalculate/QuantumClassicalIntegerExpression.h>
#include <libqalculate/QuantumClassicalIntegerStorage.h>
#include <libqalculate/QuantumClassicalRangeExpression.h>
#include <libqalculate/QuantumRuntimeRotation.h>
#include <libqalculate/QuantumRuntimeGate.h>
#include <libqalculate/QuantumWireSelection.h>
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
QuantumClassical::Bits node(Reader &,unsigned,unsigned &,bool,bool=false,bool=false,bool=false);

template<class Reader>
QuantumClassical::RealExpression realNode(Reader &,unsigned,unsigned &,bool=false);

template<class Reader>
QuantumClassical::NumericType numericType(Reader &reader) {
 const auto kind=reader.integer(1);const unsigned width=static_cast<unsigned>(reader.integer(64));
 return kind==0 ? QuantumClassical::NumericType::floating(width) : QuantumClassical::NumericType::angle(width);
}

template<class Reader>
QuantumClassical::IntegerExpression integerNode(Reader &reader,unsigned depth,unsigned &count,bool variables=false,bool bitExpressions=false,bool numeric=false) {
 using namespace QuantumClassical;
 if(depth>=32 || ++count>512)throw std::length_error("Classical expression exceeds 32 levels or 512 nodes.");
 const auto kind=reader.integer(numeric ? 9 : bitExpressions ? 5 : variables ? 4 : 3);
 if(kind>=6) {
  if(kind==6){auto type=integerType(reader);return IntegerExpression::fromNumeric(type,realNode(reader,depth+1,count,true));}
  auto left=realNode(reader,depth+1,count,true);
  if(kind==8)return IntegerExpression::angleBits(left);
  auto right=realNode(reader,depth+1,count,true);
  return kind==7 ? IntegerExpression::angleRatio(left,right) : IntegerExpression::numericCompare(left,right);
 }
 if(kind==3) {
  const Integer::Operation operations[]={Integer::Operation::Add,Integer::Operation::Subtract,
   Integer::Operation::Multiply,Integer::Operation::Divide,Integer::Operation::Remainder,Integer::Operation::Power};
  const auto operation=operations[reader.integer(5)];
  auto left=integerNode(reader,depth+1,count,variables,bitExpressions,numeric);auto right=integerNode(reader,depth+1,count,variables,bitExpressions,numeric);
  return IntegerExpression::binary(operation,left,right);
 }
 auto type=integerType(reader);
 if(kind==5)return IntegerExpression::fromBits(type,node(reader,depth+1,count,true,variables,bitExpressions,numeric));
 if(kind==4)return IntegerExpression::variable(type,static_cast<std::size_t>(reader.integer(4095)));
 if(kind==0)return IntegerExpression::constant(TypedInteger::fromBits(type,reader.integer(std::numeric_limits<std::uint64_t>::max())));
 if(kind==2)return IntegerExpression::cast(type,integerNode(reader,depth+1,count,variables,bitExpressions,numeric));
 std::vector<unsigned> indices;
 for(unsigned k=0;k<type.width();++k)indices.push_back(static_cast<unsigned>(reader.integer(63)));
 return IntegerExpression::read(type,indices);
}
template<class Reader>
QuantumClassical::WireSelection wireSelection(Reader &reader,unsigned qubits,unsigned bits,const QuantumClassical::IntegerStorage &storage) {
 const auto source=reader.expression();
 if(source.size()>512)throw std::length_error("Wire source context exceeds 512 bytes");
 const auto count=reader.integer(3);std::vector<QuantumClassical::WireSelection::Target> targets;
 for(unsigned k=0;k<count;++k) {
  const auto size=reader.integer(25);std::vector<unsigned> mapping;
  if(!qubits)throw std::out_of_range("A runtime wire requires a quantum register");
  for(unsigned j=0;j<size;++j)mapping.push_back(static_cast<unsigned>(reader.integer(qubits-1)));
  unsigned nodes=0;auto index=integerNode(reader,0,nodes,true,true,true);
  targets.push_back({mapping,index});
 }
 QuantumClassical::WireSelection result(targets,source);result.validate(qubits,bits,storage);return result;
}

template<class Reader>
QuantumClassical::Bits node(Reader &reader,unsigned depth,unsigned &count,bool typed,bool variables,bool bitExpressions,bool numeric) {
 using Bits=QuantumClassical::Bits;
 if(depth>=32 || ++count>512)throw std::length_error("Classical expression exceeds 32 levels or 512 nodes.");
 unsigned kind=static_cast<unsigned>(reader.integer(typed ? 8 : 5));
 if(kind==8)return Bits::fromInteger(integerNode(reader,depth+1,count,variables,bitExpressions,numeric));
 if(kind==7) {
  const auto operation=reader.integer(1)==0 ? Bits::Binary::And : Bits::Binary::Or;
  auto left=node(reader,depth+1,count,typed,variables,bitExpressions,numeric);auto right=node(reader,depth+1,count,typed,variables,bitExpressions,numeric);
  return Bits::logical(operation,left,right);
 }
 if(kind==6) {
  const Bits::Binary comparisons[]={Bits::Binary::Equal,Bits::Binary::NotEqual,Bits::Binary::Less,
   Bits::Binary::LessEqual,Bits::Binary::Greater,Bits::Binary::GreaterEqual};
  const auto operation=comparisons[reader.integer(5)];
  auto left=integerNode(reader,depth+1,count,variables,bitExpressions,numeric);auto right=integerNode(reader,depth+1,count,variables,bitExpressions,numeric);
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
 if(kind==2)return Bits::complement(node(reader,depth+1,count,typed,variables,bitExpressions,numeric));
 if(kind==4)return Bits::populationCount(node(reader,depth+1,count,typed,variables,bitExpressions,numeric));
 if(kind==5) {
  const auto direction=reader.integer(1)==0 ? Bits::Direction::Left : Bits::Direction::Right;
  const auto interpretation=reader.integer(1)==0 ? Bits::Distance::Unsigned : Bits::Distance::Signed;
  auto value=node(reader,depth+1,count,typed,variables,bitExpressions,numeric);auto distance=node(reader,depth+1,count,typed,variables,bitExpressions,numeric);
  return Bits::rotate(direction,value,distance,interpretation);
 }
 // Explicit wire mapping remains stable if the C++ enum is reordered.
 const Bits::Binary operations[]={Bits::Binary::And,Bits::Binary::Or,Bits::Binary::Xor,
  Bits::Binary::ShiftLeft,Bits::Binary::ShiftRight,Bits::Binary::Equal,Bits::Binary::NotEqual,
  Bits::Binary::Less,Bits::Binary::LessEqual,Bits::Binary::Greater,Bits::Binary::GreaterEqual};
 unsigned operation=static_cast<unsigned>(reader.integer(10));
 auto left=node(reader,depth+1,count,typed,variables,bitExpressions,numeric);
 auto right=node(reader,depth+1,count,typed,variables,bitExpressions,numeric);
 return Bits::binary(operations[operation],left,right);
}
template<class Reader>
QuantumClassical::Bits read(Reader &reader,unsigned bits,bool typed=false,const QuantumClassical::IntegerStorage *variables=nullptr,bool bitExpressions=false,bool numeric=false) {
 unsigned count=0;auto expression=node(reader,0,count,typed,variables!=nullptr,bitExpressions,numeric);
 if(variables)expression.validate(bits,*variables);else expression.validate(bits);
 return expression;
}
template<class Reader>
QuantumClassical::RangeExpression range(Reader &reader,unsigned bits,const QuantumClassical::IntegerStorage &variables,bool numeric=false) {
 unsigned count=0;auto start=integerNode(reader,0,count,true,true,numeric);
 count=0;auto stop=integerNode(reader,0,count,true,true,numeric);
 count=0;auto step=integerNode(reader,0,count,true,true,numeric);
 QuantumClassical::RangeExpression result(start,stop,step);
 result.validate(bits,variables);return result;
}

// Constants travel as unsigned IEEE-754 bit patterns, avoiding locale-dependent
// decimal parsing and preserving the binary64 value across both backends.
template<class Reader>
QuantumClassical::RealExpression realNode(Reader &reader,unsigned depth,unsigned &count,bool numeric) {
 using R=QuantumClassical::RealExpression;
 if(depth>=32 || ++count>512)throw std::length_error("Real expression exceeds 32 levels or 512 nodes.");
 const auto kind=reader.integer(numeric ? 9 : 2);
 if(kind>=3) {
  if(kind==3 || kind==4 || kind==5) {
   const auto type=numericType(reader);
   if(kind==3)return R::constant(QuantumClassical::NumericValue::fromBits(type,reader.integer(std::numeric_limits<std::uint64_t>::max())));
   if(kind==4)return R::variable(type,static_cast<std::size_t>(reader.integer(4095)));
   return R::cast(type,realNode(reader,depth+1,count,true));
  }
  if(kind==6) {
   using F=QuantumClassical::NumericValue::Function;
   const F functions[]={F::Negate,F::Sin,F::Cos,F::Tan,F::Arcsin,F::Arccos,F::Arctan,F::Exp,F::Log,F::Sqrt,F::Floor,F::Ceiling,F::Complement};
   const auto function=functions[reader.integer(12)];return R::function(function,realNode(reader,depth+1,count,true));
  }
  if(kind==7) {
   using S=QuantumClassical::NumericValue::Scaling;const S operations[]={S::Multiply,S::Divide,S::ShiftLeft,S::ShiftRight};
   const auto operation=operations[reader.integer(3)];auto angle=realNode(reader,depth+1,count,true);
   return R::scale(operation,angle,integerNode(reader,depth+1,count,true,true,true));
  }
  const unsigned width=static_cast<unsigned>(reader.integer(64));
  if(kind==8)return R::fromBits(width,node(reader,depth+1,count,true,true,true,true));
  return R::fromInteger(integerNode(reader,depth+1,count,true,true,true),width);
 }
 if(kind==0) {
  static_assert(sizeof(double)==sizeof(std::uint64_t),"Binary64 protocol requires 64-bit double");
  const std::uint64_t raw=reader.integer(std::numeric_limits<std::uint64_t>::max());
  double value;std::memcpy(&value,&raw,sizeof(value));return R::constant(value);
 }
 if(kind==1)return R::fromInteger(integerNode(reader,depth+1,count,true,true,numeric));
 const R::Operation operations[]={R::Operation::Add,R::Operation::Subtract,R::Operation::Multiply,R::Operation::Divide,R::Operation::Power,R::Operation::Mod,R::Operation::And,R::Operation::Or,R::Operation::Xor};
 const auto operation=operations[reader.integer(numeric ? 8 : 3)];
 auto left=realNode(reader,depth+1,count,numeric);auto right=realNode(reader,depth+1,count,numeric);
 return R::binary(operation,left,right);
}
template<class Reader>
QuantumNumerics::RuntimeRotation rotation(Reader &reader,unsigned bits,const QuantumClassical::IntegerStorage &variables,bool numeric=false) {
 using Rotation=QuantumNumerics::RuntimeRotation;
 const Rotation::Axis axes[]={Rotation::Axis::X,Rotation::Axis::Y,Rotation::Axis::Z};
 const auto axis=axes[reader.integer(2)];unsigned count=0;
 Rotation result(axis,realNode(reader,0,count,numeric));result.validate(bits,variables);return result;
}
template<class Reader>
QuantumNumerics::RuntimeGate parameterGate(Reader &reader,unsigned bits,const QuantumClassical::IntegerStorage &variables,bool numeric=false) {
 using G=QuantumNumerics::RuntimeGate;
 const G::Kind kinds[]={G::Kind::X,G::Kind::Y,G::Kind::Z,G::Kind::Phase,G::Kind::GlobalPhase,G::Kind::U3,G::Kind::PublishedU};
 const auto kind=kinds[reader.integer(6)];
 const unsigned controls=static_cast<unsigned>(reader.integer(3));
 const auto state=reader.integer(7);const auto size=reader.integer(3);
 std::vector<QuantumClassical::RealExpression> parameters;
 for(unsigned k=0;k<size;++k) {unsigned count=0;parameters.push_back(realNode(reader,0,count,numeric));}
 unsigned count=0;auto power=integerNode(reader,0,count,true,true,numeric);
 G gate(kind,parameters,controls,state,power);gate.validate(bits,variables);return gate;
}
}
#endif
