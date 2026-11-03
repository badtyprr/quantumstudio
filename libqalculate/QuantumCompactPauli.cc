// GPL-2.0-or-later; see COPYING.
#include "QuantumCompactPauli.h"
#include "Calculator.h"
#include "Function.h"
#include <cstdint>
#include <functional>
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
 bool logical(const Pauli &p) const {
  for(const auto &g:generators)if(!commutes(p,g))return false;
  Word word=p.x|(p.z<<n);
  for(unsigned k=2*n;k-->0;)if(word&(Word(1)<<k))word^=basis[k].x|(basis[k].z<<n);
  return word!=0;
 }
 unsigned distance(unsigned bound) const {
  if(rank==n)throw std::invalid_argument("Compact code distance requires at least one logical qubit.");
  // Enumerate supports in weight order, and all three nonidentity letters on
  // each support. A found witness proves the exact minimum, not an upper bound.
  std::function<bool(unsigned,unsigned,Pauli)> search;
  search=[&](unsigned next,unsigned left,Pauli p) {
   if(CALCULATOR->aborted())throw std::runtime_error("Compact distance calculation cancelled.");
   if(!left)return logical(p);
   for(unsigned q=next;q+left<=n;++q)for(unsigned letter=1;letter<=3;++letter) {
    Pauli candidate=p;Word bit=Word(1)<<q;
    if(letter&1)candidate.x|=bit;
    if(letter&2)candidate.z|=bit;
    if(search(q+1,left-1,candidate))return true;
   }
   return false;
  };
  for(unsigned weight=1;weight<=bound;++weight)if(search(0,weight,Pauli{n,0,0,0}))return weight;
  throw std::invalid_argument("No logical Pauli found within the requested weight bound; distance is not determined.");
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
    unsigned bound=integer(args[1],3);
    if(!bound)throw std::invalid_argument("Compact distance search requires a weight bound from 1 to 3.");
    out=MathStructure(int(group.distance(bound)));
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
 for(const auto &entry:{std::pair<const char *,int>("qcompactpauli",4),{"qcompactmultiply",2},{"qcompactcommutes",2},{"qcompactrank",1},{"qcompactdimension",1},{"qcompactdistance",2},{"qcompactsyndrome",2}})
  calculator.addFunction(new CompactFunction(entry.first,entry.second));
}
