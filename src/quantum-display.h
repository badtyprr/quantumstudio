// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_DISPLAY_H
#define QUANTUM_DISPLAY_H
#include "MathStructure.h"
#include "Function.h"
#include "Variable.h"
#include <set>
#include <string>
#include <vector>
#include <utility>
#include <cctype>

// Presentation only. Never feed this text back into evaluation in place of the
// canonical clipboard expression. Unknown forms retain the library's printer.
namespace QuantumDisplay {
enum Kind { Other, Ket, Bra, BraProduct };
struct Fragment {
 std::string text,label;int precedence;Kind kind;
 Fragment(std::string value,int level=100,Kind shape=Other,std::string name=""):
  text(value),label(name),precedence(level),kind(shape) {}
};
class Printer {
 const PrintOptions &options;
 unsigned nodes=0, collected=0;
 bool lostBinding=false;
 std::set<std::string> names;
 std::vector<std::pair<MathStructure,std::string>> bindings;
 bool collect(const MathStructure &value,unsigned depth=0) {
  if(depth>128 || ++collected>2048)return false;
  if(value.isSymbolic()) {
   const std::string name=value.symbol();names.insert(name);
   // A fixed subscript remains free even inside a generated indexed label.
   // Reserve its components so choosing a displayed binder cannot capture it.
   size_t start=0;
   for(size_t end=0;end<=name.size();++end)if(end==name.size() || name[end]=='_') {
    if(end>start)names.insert(name.substr(start,end-start));
    start=end+1;
   }
  }
  if(value.isVariable())names.insert(value.variable()->referenceName());
  for(size_t i=0;i<value.size();++i)if(!collect(value[i],depth+1))return false;
  return true;
 }
 std::string fresh() {
  for(const char *name:{"k","j","l","n","t"})if(names.insert(name).second)return name;
  for(unsigned i=1;;++i){std::string name="k"+std::to_string(i);if(names.insert(name).second)return name;}
 }
 static std::string grouped(const Fragment &value,int precedence) {
  return value.precedence<precedence ? "("+value.text+")" : value.text;
 }
 static bool safeLabel(const std::string &value) {
  if(value.empty())return false;
  for(unsigned char c:value)if(c<128 && !std::isalnum(c) && c!='_' && c!=' ')return false;
  for(const char *special:{"⟨","⟩","↑","↓","±","−","∑"})if(value.find(special)!=std::string::npos)return false;
  return true;
 }
 Fragment fallback(const MathStructure &value) {
  for(const auto &binding:bindings)if(value.contains(binding.first))lostBinding=true;
  int precedence=value.isAddition() ? 20 : value.isMultiplication() ? 40 : value.isPower() ? 80 : 100;
  if(value.isNumber() && value.number().isNegative())precedence=70;
  return Fragment(value.print(options),precedence);
 }
 Fragment render(const MathStructure &value,unsigned depth) {
  if(depth>128 || ++nodes>2048)return fallback(value);
  for(auto i=bindings.rbegin();i!=bindings.rend();++i)if(value.equals(i->first))return Fragment(i->second);
  if(value.isVariable() && !value.variable()->isKnown())return Fragment(value.variable()->referenceName());
  if(value.isSymbolic() && value.symbol().size()==1 && std::isalpha(static_cast<unsigned char>(value.symbol()[0])) && value.symbol()!="i" && value.symbol()!="e")return Fragment(value.symbol());
  if(!value.isFunction())return fallback(value);
  const std::string name=value.function()->referenceName();
  if(name=="qindexedlabel" && value.size()==3) {
   auto part=[&](const MathStructure &v){return v.isSymbolic() ? v.symbol() : render(v,depth+1).text;};
   Fragment index=render(value[1],depth+1);
   return Fragment(part(value[0])+grouped(index,100)+part(value[2]));
  }
  if((name=="qketstate" || name=="qnamedket" || name=="qindexedket") && value.size()==1) {
   std::string label=value[0].isSymbolic() ? value[0].symbol() : render(value[0],depth+1).text;
   bool literalCollision=(value[0].isSymbolic() && label.size()==1) || label.find_first_not_of("0123456789 ")==std::string::npos;
   if(!literalCollision && safeLabel(label))return Fragment("|"+label+"⟩",100,Ket,label);
  }
  if(name=="qpower" && value.size()==2)return Fragment(grouped(render(value[0],depth+1),81)+"^"+grouped(render(value[1],depth+1),81),80);
  if((name=="qsin" || name=="qcos" || name=="qtan" || name=="qasin" || name=="qacos" || name=="qatan") && value.size()==1)
   return Fragment(name.substr(1)+"("+render(value[0],depth+1).text+")");
  if(name=="qfourier" && value.size()==1)return Fragment("QFT_"+grouped(render(value[0],depth+1),100));
  if(name=="qtrace" && value.size()==1)return Fragment("Tr("+render(value[0],depth+1).text+")");
  if(name=="qsum" && value.size()==4) {
   Fragment first=render(value[1],depth+1),last=render(value[2],depth+1);
   std::string index=fresh();bindings.push_back({value[3],index});
   Fragment body=render(value[0],depth+1);bindings.pop_back();
   return Fragment("∑_{"+index+"="+first.text+"}^{"+last.text+"} ("+body.text+")",10);
  }
  if(name=="qdag" && value.size()==1) {
   Fragment child=render(value[0],depth+1);
   if(child.kind==Ket)return Fragment("⟨"+child.label+"|",100,Bra,child.label);
   if(child.kind==Bra)return Fragment("|"+child.label+"⟩",100,Ket,child.label);
   return Fragment(grouped(child,100)+"†",90);
  }
  if((name=="qadd" || name=="qsub" || name=="qmul" || name=="qadjacent" || name=="qtensor") && value.size()==2) {
   Fragment left=render(value[0],depth+1),right=render(value[1],depth+1);
   if(name=="qadd" || name=="qsub")return Fragment(grouped(left,20)+(name=="qadd" ? " + " : " − ")+grouped(right,name=="qsub" ? 21 : 20),20);
   if(name=="qtensor")return Fragment(grouped(left,31)+" ⊗ "+grouped(right,31),30);
   if(left.kind==Bra && right.kind==Ket)return Fragment("⟨"+left.label+"|"+right.label+"⟩");
   if(left.kind==BraProduct && right.kind==Ket)return Fragment(left.text+" "+right.text);
   if(left.kind==Bra)return Fragment(left.text+" "+grouped(right,41),40,BraProduct);
   return Fragment(grouped(left,40)+(right.kind==Ket ? " " : " · ")+grouped(right,40),40);
  }
  return fallback(value);
 }
 public:
 explicit Printer(const PrintOptions &print):options(print) {}
 std::string print(const MathStructure &value) {
  if(value.isMatrix() || value.isNumber())return value.print(options);
  if(!collect(value))return value.print(options);
  std::string text=render(value,0).text;
  return !lostBinding && text.size()<=131072 ? text : value.print(options);
 }
};
inline std::string print(const MathStructure &value,const PrintOptions &options) {return Printer(options).print(value);}
}
#endif
