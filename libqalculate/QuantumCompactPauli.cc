// GPL-2.0-or-later; see COPYING.
#include "QuantumCompactPauli.h"
#include "QuantumBinary.h"
#include "QuantumIndexed.h"
#include "Calculator.h"
#include "Function.h"
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using Word = std::uint64_t;
unsigned parity(Word x) { unsigned p=0; while(x) {p^=1;x&=x-1;} return p; }
// P = i^phase Z^z X^x, matching qpauliword's row convention.
// The public value is an exact four-integer vector [n,x,z,phase].
struct Pauli { unsigned n; Word x,z; unsigned phase; };
unsigned integer(const MathStructure &v,unsigned maximum) {
 if(!v.isNumber() || v.number().isApproximate() || !v.number().isInteger() || v.number()<0 || v.number()>maximum)
  throw std::invalid_argument("Compact Pauli fields must be exact nonnegative bounded integers.");
 return v.number().uintValue();
}
Pauli read(const MathStructure &v) {
 if(!v.isVector() || v.size()!=4)throw std::invalid_argument("A compact Pauli requires [qubits,x,z,phase].");
 unsigned n=integer(v[0],25);
 if(!n)throw std::invalid_argument("Compact Paulis require 1 to 25 qubits.");
 unsigned limit=(1u<<n)-1;
 return {n,integer(v[1],limit),integer(v[2],limit),integer(v[3],3)};
}
MathStructure value(const Pauli &p) {
 MathStructure out;out.clearVector();
 for(unsigned v:{p.n,unsigned(p.x),unsigned(p.z),p.phase})out.addChild(MathStructure(int(v)));
 return out;
}
void sameSize(const Pauli &a,const Pauli &b) {
 if(a.n!=b.n)throw std::invalid_argument("Compact Paulis must have the same qubit count.");
}
bool commutes(const Pauli &a,const Pauli &b) {return !parity((a.x&b.z)^(a.z&b.x));}
Pauli product(const Pauli &a,const Pauli &b) {
 return {a.n,a.x^b.x,a.z^b.z,(a.phase+b.phase+2*parity(a.x&b.z))%4};
}
// A support contributes at most two binary columns per qubit. Descendants
// append after the current rank, so siblings can reuse the same scratch space.
struct BinaryColumns {
 Word pivots[50]; // Two Pauli axes for each of the 25 compact qubits.
 unsigned append(unsigned rank, Word column) {
  for(unsigned i=0;i<rank;++i) {
   const Word reduced=column^pivots[i];
   if(reduced<column)column=reduced;
  }
  if(!column)return rank;
  pivots[rank]=column;
  return rank+1;
 }
};

struct DistanceSearch {
 struct Column { Word syndrome, remainder; };
 std::vector<Column> columns; // X, Z for each qubit in order
 BinaryColumns syndromes, remainders;

 bool containsLogical(unsigned next, unsigned left, unsigned syndromeRank, unsigned remainderRank) {
  if(CALCULATOR->aborted())throw std::runtime_error("Compact Pauli search cancelled.");
  const unsigned qubits=columns.size()/2;
  for(unsigned q=next;q+left<=qubits;++q) {
   unsigned sr=syndromeRank, rr=remainderRank;
   for(unsigned j=2*q;j<2*q+2;++j) {
    sr=syndromes.append(sr,columns[j].syndrome);
    rr=remainders.append(rr,columns[j].remainder);
   }
   // The zero-remainder kernel is the stabilizer subspace on this support.
   // The zero-syndrome kernel also includes logical operators. Rank-nullity
   // detects a logical operator exactly when the second kernel is larger.
   if(rr>sr || (left>1 && containsLogical(q+1,left-1,sr,rr)))return true;
  }
  return false;
 }
};

struct Stabilizers {
 std::vector<Pauli> generators,basis;
 unsigned n=0,rank=0;
 explicit Stabilizers(const MathStructure &input) {
  if(!input.isVector() || input.size()==0 || input.size()>64)
   throw std::invalid_argument("Compact stabilizers require 1 to 64 compact Pauli generators.");
  for(size_t j=0;j<input.size();++j) {
   Pauli p=read(input[j]);
   if(generators.empty()) {n=p.n;basis.resize(2*n,Pauli{n,0,0,0});}
   else sameSize(p,generators[0]);
   if((p.phase+parity(p.x&p.z))%2)throw std::invalid_argument("Compact stabilizer generators must be Hermitian.");
   for(const auto &g:generators)if(!commutes(p,g))throw std::invalid_argument("Compact stabilizer generators must commute.");
   generators.push_back(p);
   for(unsigned k=2*n;k-->0;)if((p.x|(p.z<<n))&(Word(1)<<k)) {
    if(basis[k].x || basis[k].z)p=product(p,basis[k]);
    else {basis[k]=p;++rank;break;}
   }
   if(!p.x && !p.z && p.phase)throw std::invalid_argument("Compact generators contain -I and have no common +1 eigenspace.");
  }
 }
 template<class Predicate>
 bool search(unsigned next, unsigned left, Pauli p, const Predicate &accept) const {
  if(CALCULATOR->aborted())throw std::runtime_error("Compact Pauli search cancelled.");
  if(!left)return accept(p);
  for(unsigned q=next;q+left<=n;++q)for(unsigned letter=1;letter<=3;++letter) {
   Pauli candidate=p;
   const Word bit=Word(1)<<q;
   if(letter&1)candidate.x|=bit;
   if(letter&2)candidate.z|=bit;
   // Each Y is -i ZX in the public representation.
   if(letter==3)candidate.phase=(candidate.phase+3)%4;
   if(search(q+1,left-1,candidate,accept))return true;
  }
  return false;
 }
 unsigned distance(unsigned bound) const {
  if(rank==n)throw std::invalid_argument("Compact code distance requires at least one logical qubit.");
  DistanceSearch search;
  for(unsigned q=0;q<n;++q)for(unsigned axis=0;axis<2;++axis) {
   const Word bit=Word(1)<<q;
   Pauli single{n,axis==0 ? bit : 0,axis==1 ? bit : 0,0};
   Word syndrome=0;
   for(size_t j=0;j<generators.size();++j)
    if(!commutes(single,generators[j]))syndrome|=Word(1)<<j;
   Word remainder=single.x|(single.z<<n);
   for(unsigned k=2*n;k-->0;)
    if(remainder&(Word(1)<<k))remainder^=basis[k].x|(basis[k].z<<n);
   search.columns.push_back({syndrome,remainder});
  }
  for(unsigned weight=1;weight<=bound && weight<=n;++weight)
   if(search.containsLogical(0,weight,0,0))return weight;
  throw std::invalid_argument("No logical Pauli found within the requested weight bound; distance is not determined.");
 }
 Pauli correction(const MathStructure &bits, unsigned bound) const {
  if(!bits.isVector() || bits.size()!=generators.size())
   throw std::invalid_argument("Supply one syndrome bit per compact generator.");
  Word target=0;
  for(size_t j=0;j<bits.size();++j)target|=Word(integer(bits[j],1))<<j;
  Pauli result{n,0,0,0};
  auto matches=[&](const Pauli &p) {
   for(size_t j=0;j<generators.size();++j) {
    const bool bit=!commutes(p,generators[j]);
    if(bit!=bool((target>>j)&1))return false;
   }
   result=p;
   return true;
  };
  for(unsigned weight=0;weight<=bound;++weight)
   if(search(0,weight,Pauli{n,0,0,0},matches))return result;
  throw std::invalid_argument("No compact Pauli correction matches the syndrome within the requested weight bound.");
 }

};
class CompactFunction:public MathFunction {
 std::string op;
public:
 CompactFunction(const char *name,int count):MathFunction(name,count),op(name) {}
 ExpressionItem *copy() const {return new CompactFunction(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  try {
   MathStructure args=raw;for(size_t j=0;j<args.size();++j)args[j].eval(eo);
   if(op=="qcompactpauli") {
    MathStructure fields;fields.clearVector();
    for(size_t j=0;j<4;++j)fields.addChild(args[j]);
    out=value(read(fields));return 1;
   }
   if(op=="qcompactmultiply" || op=="qcompactcommutes") {
    Pauli a=read(args[0]),b=read(args[1]);sameSize(a,b);
    out=op=="qcompactmultiply" ? value(product(a,b)) : MathStructure(int(commutes(a,b)));return 1;
   }
   Stabilizers group(args[0]);
   if(op=="qcompactrank")out=MathStructure(int(group.rank));
   else if(op=="qcompactdimension")out=MathStructure(int(1u<<(group.n-group.rank)));
   else if(op=="qcompactdistance") {
    unsigned bound=integer(args[1],25);
    if(!bound)throw std::invalid_argument("Compact distance search requires a weight bound from 1 to 25.");
    out=MathStructure(int(group.distance(bound)));
   } else if(op=="qcompactcorrection") {
    MathStructure syndrome=args[1];
    if(isQuantumBitLabel(syndrome) && syndrome.size()==2) {
     MathStructure index=syndrome[0], width=syndrome[1];
     if(validateQuantumBitLabel(index,width,eo)!=QuantumBitLabelState::Concrete ||
        index.number().isApproximate() || width.number().isApproximate() ||
        width.number()!=Number(group.generators.size()))
      throw std::invalid_argument("Supply a concrete syndrome word with one exact bit per compact generator.");
     syndrome.clearVector();
     for(size_t bit=group.generators.size();bit>0;--bit)
      syndrome.addChild(MathStructure(index.number().bitGet(bit)));
    }
    out=value(group.correction(syndrome,integer(args[2],3)));
   } else {
    Pauli error=read(args[1]);sameSize(error,group.generators[0]);out.clearVector();
    for(const auto &g:group.generators)out.addChild(MathStructure(int(!commutes(g,error))));
   }
   return 1;
  } catch(const std::exception &e) {CALCULATOR->error(true,"%s",e.what(),NULL);return 0;}
 }
};
}
void registerQuantumCompactPauli(Calculator &calculator) {
 for(const auto &entry:{std::pair<const char *,int>("qcompactpauli",4),{"qcompactmultiply",2},{"qcompactcommutes",2},{"qcompactrank",1},{"qcompactdimension",1},{"qcompactdistance",2},{"qcompactsyndrome",2},{"qcompactcorrection",3}})
  calculator.addFunction(new CompactFunction(entry.first,entry.second));
}
