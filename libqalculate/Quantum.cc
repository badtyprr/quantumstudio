// Quantum notation extension. GPL-2.0-or-later; see COPYING.
#include "Quantum.h"
#include "QuantumTeX.h"
#include "QuantumMatrix.h"
#include "Calculator.h"
#include "Function.h"
#include "MathStructure.h"
#include "Variable.h"
#include <stdexcept>
#include <cctype>
#include <cmath>
#include <map>
#include <algorithm>

namespace {
size_t quantumSpaceLength(const std::string &s,size_t p) {
 if(p>=s.size())return 0;
 unsigned char c=s[p];if(c==' ' || (c>=9 && c<=13))return 1;
 if(c<128)return 0;
 for(const char *space:{"\xc2\x85","\xc2\xa0","\xe1\x9a\x80","\xe2\x80\x80","\xe2\x80\x81","\xe2\x80\x82","\xe2\x80\x83","\xe2\x80\x84","\xe2\x80\x85","\xe2\x80\x86","\xe2\x80\x87","\xe2\x80\x88","\xe2\x80\x89","\xe2\x80\x8a","\xe2\x80\xa8","\xe2\x80\xa9","\xe2\x80\xaf","\xe2\x81\x9f","\xe3\x80\x80"}) {
  std::string token(space);if(s.compare(p,token.size(),token)==0)return token.size();
 }
 return 0;
}
std::string quantumWhitespace(const std::string &s) {
 std::string out;bool quoted=false;
 for(size_t p=s.compare(0,3,"\xef\xbb\xbf")==0 ? 3 : 0;p<s.size();) {
  if(s[p]=='"')quoted=!quoted;
  size_t length=quoted ? 0 : quantumSpaceLength(s,p);
  if(length){out+=' ';p+=length;}else out+=s[p++];
 }
 return out;
}
void replaceAll(std::string &s, const std::string &a, const std::string &b) {
 size_t p = 0; while((p = s.find(a, p)) != std::string::npos) { s.replace(p, a.size(), b); p += b.size(); }
}
std::string labelText(std::string s) {
 s.erase(std::remove_if(s.begin(),s.end(),[](unsigned char c) { return std::isspace(c); }),s.end()); return s;
}
std::string binaryNumeral(const std::string &text) {
 std::string integer="0";size_t digits=0,fraction=0;bool point=false;
 for(char c:text) {
  if(c=='.' && !point) {point=true;continue;}
  if(c!='0' && c!='1')throw std::runtime_error("A base-two numeral may contain only binary digits and one radix point.");
  if(++digits>1024)throw std::runtime_error("Binary numerals support at most 1024 digits.");
  if(point)++fraction;
  int carry=c-'0';
  for(size_t j=integer.size();j>0;--j) {int value=2*(integer[j-1]-'0')+carry;integer[j-1]=char('0'+value%10);carry=value/10;}
  if(carry)integer.insert(integer.begin(),char('0'+carry));
 }
 if(!digits)throw std::runtime_error("A binary numeral requires at least one digit.");
 return "("+integer+"/2^"+std::to_string(fraction)+")";
}
std::string unicodeArithmetic(const std::string &input) {
 static const std::map<std::string,char> symbols={{"×",'*'},{"⋅",'*'},{"·",'*'},{"∙",'*'},{"∗",'*'},{"÷",'/'},{"∕",'/'},{"⁄",'/'}};
 std::string out;bool quoted=false;
 for(size_t p=0;p<input.size();) {
  if(input[p]=='"'){quoted=!quoted;out+=input[p++];continue;}
  bool matched=false;
  if(!quoted)for(const auto &symbol:symbols)if(input.compare(p,symbol.first.size(),symbol.first)==0) {
   out+=symbol.second;p+=symbol.first.size();matched=true;break;
  }
  if(!matched)out+=input[p++];
 }
 return out;
}
bool bellSuffix(const std::string &text) {
 for(const std::string &name:{std::string("Φ"),std::string("φ"),std::string("ϕ"),std::string("Ψ"),std::string("ψ"),std::string("Phi"),std::string("phi"),std::string("Psi"),std::string("psi")})
  if(text.size()>=name.size() && text.compare(text.size()-name.size(),name.size(),name)==0)return true;
 return false;
}
std::string bellState(const std::string &label) {
 std::string value=labelText(label);bool negative=false;size_t mark=std::string::npos;
 for(const std::string &suffix:{std::string("^(+)"),std::string("^(-)"),std::string("^+"),std::string("^-"),std::string("_+"),std::string("_-"),std::string("+"),std::string("-")}) {
  if(value.size()>suffix.size() && value.compare(value.size()-suffix.size(),suffix.size(),suffix)==0) {mark=value.size()-suffix.size();negative=suffix.find('-')!=std::string::npos;break;}
 }
 if(mark==std::string::npos)return "";
 std::string name=value.substr(0,mark);
 bool phi=name=="Φ" || name=="φ" || name=="ϕ" || name=="Phi" || name=="phi";
 bool psi=name=="Ψ" || name=="ψ" || name=="Psi" || name=="psi";
 if(!phi && !psi)return "";
 return std::string("(matrix(4,1,[")+(phi ? "1,0,0," : "0,1,")+(negative ? "-1" : "1")+(phi ? "])/sqrt(2))" : ",0])/sqrt(2))");
}
std::string unicodePowers(const std::string &input) {
 static const std::map<std::string,char> digits={{"⁰",'0'},{"¹",'1'},{"²",'2'},{"³",'3'},{"⁴",'4'},{"⁵",'5'},{"⁶",'6'},{"⁷",'7'},{"⁸",'8'},{"⁹",'9'},{"⁺",'+'},{"⁻",'-'}};
 std::string result;bool quoted=false;
 for(size_t p=0;p<input.size();) {
  if(input[p]=='"') {quoted=!quoted;result+=input[p++];continue;}
  std::string exponent;
  if(!quoted)while(p<input.size()) {
   bool found=false;
   for(const auto &digit:digits)if(input.compare(p,digit.first.size(),digit.first)==0) {
    exponent+=digit.second;p+=digit.first.size();found=true;break;
   }
   if(!found)break;
  }
  if(exponent.empty()) {result+=input[p++];continue;}
  if((exponent=="+" || exponent=="-") && bellSuffix(result)) {result+="^("+exponent+")";continue;}
  size_t start=(exponent[0]=='+' || exponent[0]=='-') ? 1 : 0;
  if(start==exponent.size() || exponent.find_first_not_of("0123456789",start)!=std::string::npos)throw std::runtime_error("Unicode superscripts require an optionally signed integer exponent.");
  result+="^("+exponent+")";
 }
 return result;
}
std::string ket(const std::string &label, size_t dimension=0) {
 std::string s=labelText(label);
 if(dimension) {
  if(s.empty() || s.find_first_not_of("0123456789")!=std::string::npos) throw std::runtime_error("Dimension-qualified kets require a decimal basis index.");
  size_t index=0; for(char c:s) {index=index*10+c-'0'; if(index>=dimension) throw std::runtime_error("Basis index must be smaller than its explicit dimension.");}
  return "qbasis("+std::to_string(index)+","+std::to_string(dimension)+")";
 }
 std::string bell=bellState(s);if(!bell.empty())return bell;
 if(s.find("±")!=std::string::npos)throw std::runtime_error("Choose one state sign, + or -, rather than an ambiguous plus/minus label.");
 if(s == "+") return "(matrix(2,1,[1,1])/sqrt(2))";
 if(s == "-") return "(matrix(2,1,[1,-1])/sqrt(2))";
 if(s == "i" || s == "+i") return "(matrix(2,1,[1,i])/sqrt(2))";
 if(s == "-i") return "(matrix(2,1,[1,-i])/sqrt(2))";
 if(s.find("↑")!=std::string::npos || s.find("↓")!=std::string::npos) {
  replaceAll(s,"↑","0");replaceAll(s,"↓","1");
  if(s.find_first_not_of("01+-")!=std::string::npos)throw std::runtime_error("Spin-arrow product kets contain only arrows, binary digits, or +/- qubit labels.");
 }
 if(!s.empty() && s.find_first_not_of("01") == std::string::npos) {
  if(s.size() > 10) throw std::runtime_error("Basis kets are limited to 10 qubits.");
  size_t n = size_t(1) << s.size(), k = 0;
  for(char c : s) k = k * 2 + c - '0';
  std::string out = "matrix(" + std::to_string(n) + ",1,[";
  for(size_t j = 0; j < n; ++j) { if(j) out += ','; out += j == k ? '1' : '0'; }
  return out + "])";
 }
 if(s.size()>1 && s.find_first_not_of("01+-")==std::string::npos) {
  if(s.size()>10)throw std::runtime_error("Product kets are limited to 10 qubits.");
  std::string product=ket(s.substr(0,1));
  for(size_t k=1;k<s.size();++k)product="qtensor("+product+","+ket(s.substr(k,1))+")";
  return product;
 }
 if(s.empty()) throw std::runtime_error("Empty ket label.");
 if(s.find_first_not_of("0123456789")==std::string::npos) throw std::runtime_error("Nonbinary numeric kets require an explicit dimension, such as |2>_3 or basis(2,3).");
 for(unsigned char c : s) if(c < 128 && !std::isalnum(c) && c != '_') throw std::runtime_error("Use a basis label or a named column vector inside a ket.");
 return "(" + s + ")";
}
// Shared by registration and strict quantum-call validation.
const std::map<std::string,int> quantumSignatures = {
 {"qamplitudedamping",1},
 {"qgeneralizeddamping",2},
 {"qcombineddamping",3},
 {"qthermalrelaxation",4},
 {"qphasedamping",1},
 {"qdepolarizing",1},
 {"qanticomm",2},
 {"qapply",3},
 {"qbasis",2},
 {"qcompare",3},
 {"qbitdot",2},
 {"qbitxor",2},
 {"qbits",2},
 {"qgf2rref",1},
 {"qgf2rank",1},
 {"qgf2mul",2},
 {"qlineargate",1},
 {"qgf2inverse",1},
 {"qgf2nullspace",1},
 {"qstabilizerprojector",1},
 {"qstabilizerdimension",1},
 {"qstabilizerdistance",1},
 {"qstabilizerparameters",1},
 {"qstabilizersyndrome",2},
 {"qstabilizercorrection",2},
 {"qcssgenerators",2},
 {"qcssstate",3},
 {"qcssencoder",2},
 {"qbitvalue",1},
 {"qbloch",1},
 {"qblochsub",2},
 {"qborn",2},
 {"qchannel",2},
 {"qchoi",1},
 {"qchi",1},
 {"qspre",1},
 {"qspost",1},
 {"qsprepost",2},
 {"qlindblad",1},
 {"qliouvillian",2},
 {"qliouvillianclosed",1},
 {"qclock",1},
 {"qcomm",2},
 {"qconj",1},
 {"qcontrol",3},
 {"qcontrolpattern",4},
 {"qcontrolled",1},
 {"qcreate",1},
 {"qdag",1},
 {"qdensity",1},
 {"qdephase",2},
 {"qdephaseall",1},
 {"qdestroy",1},
 {"qdiffusion",1},
 {"qreflection",1},
 {"qphasereflection",2},
 {"qdirectsum",2},
 {"qevolution",2},
 {"qentropy",1},
 {"qschmidt",2},
 {"qschmidtdim",3},
 {"qnegativity",2},
 {"qnegativitydim",3},
 {"qlognegativity",2},
 {"qlognegativitydim",3},
 {"qentropybase",2},
 {"qexp",1},
 {"qexpect",2},
 {"qfcreate",2},
 {"qfdestroy",2},
 {"qfeedforward",5},
 {"qfidelity",2},
 {"qrootfidelity",2},
 {"qhellingerfidelity",2},
 {"qhellingerdistance",2},
 {"qfourier",1},
 {"qft",1},
 {"qindexedchannel",3},
 {"qjx",1},
 {"qjy",1},
 {"qjz",1},
 {"qjplus",1},
 {"qjminus",1},
 {"qmodmul",2},
 {"qmul",2},
 {"qspinadd",2},
 {"qnorm",1},
 {"qschatten",2},
 {"qtracenorm",1},
 {"qspectralnorm",1},
 {"qfrobeniusnorm",1},
 {"qnormalize",1},
 {"qnumberop",1},
 {"qoracle",2},
 {"qoraclefunction",4},
 {"qpermute",2},
 {"qpermutedim",3},
 {"qphaseoracle",2},
 {"qphasefunction",3},
 {"qpostselect",2},
 {"qpower",2},
 {"qlogm",1},
 {"qsqrt",1},
 {"qprobs",1},
 {"qprobsub",2},
 {"qptrace",2},
 {"qptracedim",3},
 {"qptm",1},
 {"qpaulivec",1},
 {"qpauliword",4},
 {"qunpaulivec",1},
 {"qptranspose",2},
 {"qptransposedim",3},
 {"qpurity",1},
 {"qreset",2},
 {"qresetall",1},
 {"qshift",1},
 {"qsinhc",1},
 {"qsumgate",2},
 {"qsuperop",1},
 {"qtensor",2},
 {"qtensorpow",2},
 {"qtensorproduct",4},
 {"qblocksum",4},
 {"qtrace",1},
 {"qtracedistance",2},
 {"qtranspose",1},
 {"qunvec",2},
 {"qvariance",2},
 {"qvec",1},
};
const std::map<std::string, std::string> gates = {
 {"I","[1,0;0,1]"}, {"X","[0,1;1,0]"}, {"Y","[0,-i;i,0]"}, {"Z","[1,0;0,-1]"},
 {"H","([1,1;1,-1]/sqrt(2))"}, {"S","[1,0;0,i]"}, {"T","[1,0;0,exp(i*pi/4)]"},
 {"Sdg","[1,0;0,-i]"}, {"Tdg","[1,0;0,exp(-i*pi/4)]"},
 {"SX","([1+i,1-i;1-i,1+i]/2)"}, {"SXdg","([1-i,1+i;1+i,1-i]/2)"},
 {"CNOT","[1,0,0,0;0,1,0,0;0,0,0,1;0,0,1,0]"}, {"CX","[1,0,0,0;0,1,0,0;0,0,0,1;0,0,1,0]"},
 {"CZ","[1,0,0,0;0,1,0,0;0,0,1,0;0,0,0,-1]"}, {"SWAP","[1,0,0,0;0,0,1,0;0,1,0,0;0,0,0,1]"},
 {"iSWAP","[1,0,0,0;0,0,i,0;0,i,0,0;0,0,0,1]"}, {"ISWAP","[1,0,0,0;0,0,i,0;0,i,0,0;0,0,0,1]"},
 {"FSWAP","[1,0,0,0;0,0,1,0;0,1,0,0;0,0,0,-1]"},
 {"ECR","[0,0,1,i;0,0,i,1;1,-i,0,0;-i,1,0,0]/sqrt(2)"},
 {"CCX","qcontrolled(qcontrolled([0,1;1,0]))"}, {"Toffoli","qcontrolled(qcontrolled([0,1;1,0]))"},
 {"CSWAP","qcontrolled([1,0,0,0;0,0,1,0;0,1,0,0;0,0,0,1])"},
 {"CY","qcontrolled([0,-i;i,0])"}, {"CH","qcontrolled([1,1;1,-1]/sqrt(2))"},
 {"CCZ","qcontrolled(qcontrolled([1,0;0,-1]))"}
};
std::string operatorVector(const std::string &label) {
 std::string name=labelText(label);
 if(name.empty() || (name[0]>='0' && name[0]<='9')) throw std::runtime_error("Double kets require an operator name; use vec(expression) for a general matrix.");
 for(unsigned char c:name) if(c<128 && !std::isalnum(c) && c!='_') throw std::runtime_error("Double kets require an operator name; use vec(expression) for a general matrix.");
 auto gate=gates.find(name); return "qvec("+(gate==gates.end() ? name : gate->second)+")";
}
std::string pauliLabelExpression(const std::string &label) {
 unsigned phase=0;size_t first=0,x=0,z=0;
 if(first<label.size() && (label[first]=='+' || label[first]=='-')) {if(label[first]=='-')phase=2;++first;}
 if(first<label.size() && label[first]=='1')++first;
 if(first<label.size() && (label[first]=='i' || label[first]=='j')) {++phase;++first;}
 if(label.size()-first<1 || label.size()-first>9 || label.find_first_not_of("IXYZ",first)!=std::string::npos)throw std::runtime_error("Pauli labels require 1 to 9 letters I, X, Y, Z, with an optional sign, 1, and i/j phase prefix.");
 for(size_t k=first;k<label.size();++k) {
  x=(x<<1)|(label[k]=='X' || label[k]=='Y');z=(z<<1)|(label[k]=='Z' || label[k]=='Y');
  if(label[k]=='Y')phase+=3; // Y = -i ZX; row-based sparse matrix convention.
 }
 return "qpauliword("+std::to_string(label.size()-first)+","+std::to_string(x)+","+std::to_string(z)+","+std::to_string(phase%4)+")";
}
class Parser {
 bool spinContext=false;
 int diracKind=0; // 1: a ket, 2: a bra; zero: another expression.
 std::string s; size_t p = 0; unsigned depth = 0, nodes = 0;
 void ws() { while(p < s.size() && std::isspace((unsigned char)s[p])) ++p; }
 bool take(char c) { ws(); if(p < s.size() && s[p] == c) { ++p; return true; } return false; }
 bool word(const std::string &token) {
  ws();if(s.compare(p,token.size(),token)!=0)return false;
  size_t end=p+token.size();
  return end==s.size() || (!std::isalnum((unsigned char)s[end]) && s[end]!='_' && (unsigned char)s[end]<128);
 }
 bool takeWord(const std::string &token) {if(!word(token))return false;p+=token.size();return true;}
 unsigned radical() const {
  if(s.compare(p,3,"√")==0)return 2;
  if(s.compare(p,3,"∛")==0)return 3;
  if(s.compare(p,3,"∜")==0)return 4;
  return 0;
 }
 void need(char c) { if(!take(c)) throw std::runtime_error(std::string("Expected '") + c + "' at byte " + std::to_string(p + 1)); }
 bool startsAtom() { ws(); if(p == s.size() || word("and") || word("or") || word("xor") || word("not")) return false; unsigned char c=s[p]; return c=='(' || c=='[' || c=='|' || (c=='<' && startsBra()) || std::isalnum(c) || c=='_' || c>=128; }
 bool startsBra() {
  size_t end=labelEnd('|',p+1);
  if(end==std::string::npos)return false;
  int nesting=0;
  for(size_t k=p+1+(s[p+1]=='<' ? 1 : 0);k<end;++k) {
   if(s[k]=='(' || s[k]=='[')++nesting;
   else if(s[k]==')' || s[k]==']')--nesting;
   else if(nesting==0 && (s[k]=='<' || s[k]=='>'))return false;
  }
  size_t last=s.find_last_not_of(" \t\r\n",end-1);
  // A function argument ending in a comma cannot be a complete bra label.
  return last!=std::string::npos && last>p && s[last]!=',';
 }
 size_t labelEnd(char delimiter,size_t start) {
  int nesting=0;bool quoted=false;
  for(size_t k=start;k<s.size();++k) {
   char c=s[k];if(c=='"'){quoted=!quoted;continue;}if(quoted)continue;
   if(nesting==0 && c==delimiter)return k;
   if(c=='(' || c=='[')++nesting;
   else if(c==')' || c==']'){if(nesting==0)return std::string::npos;--nesting;}
   else if(nesting==0 && c==';')return std::string::npos;
  }
  return std::string::npos;
 }
 std::string operatorState(const std::string &label) {
  size_t begin=0,end=label.size();
  while(begin<end && std::isspace((unsigned char)label[begin]))++begin;
  while(end>begin && std::isspace((unsigned char)label[end-1]))--end;
  std::string name=label.substr(begin,end-begin);
  if(name.size()>2 && name.front()=='(' && name.back()==')') {
   // Reuse this parser's depth/node budget for grouped operator expressions.
   std::string outer=s;size_t outerPosition=p;s=name;p=0;
   std::string value=expression();ws();
   if(p!=s.size())throw std::runtime_error("Invalid grouped operator inside double brackets.");
   s=outer;p=outerPosition;return "qvec("+value+")";
  }
  return operatorVector(label);
 }
 size_t repeatedRegister(const std::string &label) {
  size_t first=label.find_first_not_of(" \t\r\n");
  if(first==std::string::npos || (label[first]!='0' && label[first]!='1'))return std::string::npos;
  size_t mark=label.find_first_not_of(" \t\r\n",first+1);
  return mark!=std::string::npos && label[mark]=='^' ? mark : std::string::npos;
 }
 std::string basisState(const std::string &label,const std::string &dimension="") {
  // Commas at the top level separate registers. Commas inside a computed
  // basis index, such as mod(k,3), remain ordinary function arguments.
  std::vector<std::string> registers;size_t start=0;int nesting=0;
  for(size_t k=0;k<label.size();++k) {
   if(label[k]=='(' || label[k]=='[')++nesting;
   else if(label[k]==')' || label[k]==']')--nesting;
   else if(label[k]==',' && nesting==0) {registers.push_back(label.substr(start,k-start));start=k+1;}
  }
  if(!registers.empty()) {
   if(!dimension.empty())throw std::runtime_error("A comma-separated register label cannot have one overall basis dimension; use separately dimensioned adjacent kets or bras.");
   registers.push_back(label.substr(start));std::string state;
   for(const auto &part:registers) {
    if(++nodes>512)throw std::runtime_error("Quantum expression is too complex.");
    if(labelText(part).empty())throw std::runtime_error("Empty register in a comma-separated state label.");
    std::string factor=basisState(part);
    state=state.empty() ? factor : "qtensor("+state+","+factor+")";
   }
   return state;
  }
  if(dimension.empty()) {
   size_t mark=repeatedRegister(label);
   if(mark==std::string::npos)return ket(label);
   std::string outer=s;size_t outerPosition=p;s=label.substr(mark+1);p=0;
   std::string count=unary();ws();
   if(p!=s.size())throw std::runtime_error("Group a compound repeated-register count, for example |0^(n+1)>.");
   s=outer;p=outerPosition;
   char bit=label[label.find_first_not_of(" \t\r\n")];
   return "qtensorpow("+ket(std::string(1,bit))+","+count+")";
  }
  // Explicit dimensions disambiguate evaluated decimal indices from binary
  // strings and named states. Reuse the parser's depth and node limits.
  std::string outer=s;size_t outerPosition=p;s=label;p=0;
  std::string index=expression();ws();
  if(p!=s.size())throw std::runtime_error("Invalid expression in a dimension-qualified basis label.");
  s=outer;p=outerPosition;
  return "qbasis("+index+","+dimension+")";
 }
 std::string dimensionSuffix() {
  if(!take('_')) return "";
  if(take('(')) {std::string dimension=expression();need(')');return dimension;}
  ws();size_t start=p;
  while(p<s.size() && s[p]>='0' && s[p]<='9')++p;
  if(p==start || (p<s.size() && (s[p]=='.' || std::isalnum((unsigned char)s[p]))))throw std::runtime_error("Put a basis dimension expression in braces or parentheses.");
  return s.substr(start,p-start);
 }
 std::string binaryArgument() {
  if(!take('"'))return expression();
  std::string bits;
  while(p<s.size() && s[p]!='"') {
   if(s[p]!='0' && s[p]!='1')throw std::runtime_error("A binary string contains only 0 and 1.");
   bits+=s[p++];
  }
  need('"');
  if(bits.empty() || bits.size()>1024)throw std::runtime_error("Binary strings must contain 1 to 1024 bits.");
  std::string value="vector(";
  for(size_t j=0;j<bits.size();++j) {if(j)value+=',';value+=bits[j];}
  return value+")";
 }
 std::string atom() {
  if(++depth > 256 || ++nodes > 512) throw std::runtime_error("Quantum expression exceeds the nesting or complexity limit.");
  ws(); std::string a;int kind=0;
  if(take('(')) { a="("+expression()+")"; need(')'); }
  else if(take('[')) {
   if(take(']'))a="vector()";
   else {
    a="["; a+=expression();
    while(true) { if(take(',')) a+=","+expression(); else if(take(';')) a+=";"+expression(); else break; }
    need(']'); a+="]";
   }
  }
  else if(take('|')) { size_t b=p; p=labelEnd('>',p); if(p==std::string::npos) throw std::runtime_error("Unclosed ket; use |0> or |0⟩."); std::string label=s.substr(b,p-b); ++p; a=take('>') ? operatorState(label) : basisState(label,dimensionSuffix());kind=1; }
  else if(take('<')) {
   bool vectorized=take('<');
   size_t b=p; p=labelEnd('|',p); if(p==std::string::npos) throw std::runtime_error("Unclosed bra.");
   std::string left=s.substr(b,p-b); ++p; std::string dimension=vectorized ? "" : dimensionSuffix(); bool compact=false;
   // Collect bare adjacent output registers before recognizing a contraction.
   // Leave a following bra with a postfix operation to the ordinary parser.
   std::string leftRegister;
   if(!vectorized) {
    while(true) {
     ws();size_t saved=p;
     if(p+1>=s.size() || s[p]!='<' || s[p+1]=='<')break;
     size_t nextStart=++p, nextEnd=labelEnd('|',p);
     if(nextEnd==std::string::npos)throw std::runtime_error("Unclosed adjacent bra.");
     std::string nextLabel=s.substr(nextStart,nextEnd-nextStart);p=nextEnd+1;
     std::string nextDimension=dimensionSuffix();ws();
     if(p<s.size() && std::string("~`?^").find(s[p])!=std::string::npos) {p=saved;break;}
     if(++nodes>512)throw std::runtime_error("Quantum expression is too complex.");
     if(leftRegister.empty())leftRegister=basisState(left,dimension);
     leftRegister="qtensor("+leftRegister+","+basisState(nextLabel,nextDimension)+")";
    }
   }
   // Compact inner product <a|b> and matrix element <a|U|b>.
   size_t end=labelEnd('>',p), bar=labelEnd('|',p);
   if(end!=std::string::npos && (bar==std::string::npos || end<bar)) {
    std::string rawLabel=s.substr(p,end-p), label=labelText(rawLabel); bool valid=!label.empty();
    if(label!="+" && label!="-" && label!="+i" && label!="-i") for(unsigned char c:label) if(c<128 && !std::isalnum(c) && c!='_' && c!='+' && c!='-' && c!=',') valid=false;
    size_t suffix=end+1;while(suffix<s.size() && std::isspace((unsigned char)s[suffix]))++suffix;
    if(!vectorized && (!dimension.empty() || (suffix<s.size() && s[suffix]=='_')))valid=!label.empty();
    if(!vectorized && repeatedRegister(rawLabel)!=std::string::npos)valid=true;
    if(!vectorized && !bellState(rawLabel).empty())valid=true;
    if(vectorized && label.size()>2 && label.front()=='(' && label.back()==')')valid=true;
    if(valid) {
     p=end+1;
     if(vectorized) {need('>'); a="qmul(qdag("+operatorState(left)+"),"+operatorState(rawLabel)+")";compact=true;}
     else {
     std::string rightDimension=dimensionSuffix();
     if(leftRegister.empty()) {
      if(dimension.empty())dimension=rightDimension;
      if(rightDimension.empty())rightDimension=dimension;
     }
     std::string rightRegister=basisState(rawLabel,rightDimension);
     if(!leftRegister.empty()) {
      while(take('|')) {
       if(++nodes>512)throw std::runtime_error("Quantum expression is too complex.");
       size_t nextStart=p;p=labelEnd('>',p);
       if(p==std::string::npos)throw std::runtime_error("Unclosed adjacent ket in inner product.");
       std::string nextLabel=s.substr(nextStart,p-nextStart);++p;
       std::string nextState=take('>') ? operatorState(nextLabel) : basisState(nextLabel,dimensionSuffix());
       rightRegister="qtensor("+rightRegister+","+nextState+")";
      }
     }
     a="qmul(qdag("+(leftRegister.empty() ? basisState(left,dimension) : leftRegister)+"),"+rightRegister+")"; compact=true;
     }
    }
   }
   if(!compact) {
    a="qdag("+(vectorized ? operatorState(left) : leftRegister.empty() ? basisState(left,dimension) : leftRegister)+")";kind=2;
    // A complete bra/operator/ket expression scopes the operator between its
    // bars. Respect nested function/matrix arguments and quoted Pauli labels.
    size_t start=p, closing=std::string::npos;int nesting=0;bool quoted=false;
    for(size_t k=p;k<s.size();++k) {
     char c=s[k];
     if(c=='"') {quoted=!quoted;continue;}
     if(quoted)continue;
     if(c=='(' || c=='[')++nesting;
     else if(c==')' || c==']') {if(nesting==0)break;--nesting;}
     else if(nesting==0) {
      if(c=='|' && k>start) {closing=k;break;}
      if(c=='<' || c=='>' || c==',' || c==';')break;
     }
    }
    std::string body=closing==std::string::npos ? "" : labelText(s.substr(start,closing-start));
    if(!body.empty() && body!="+" && body!="-" && std::string("*/@#~`?^").find(body[0])==std::string::npos) {
     // Use this parser (and its shared nesting/node budget), with a temporary
     // terminator, instead of recursively creating an unrestricted parser.
     s[closing]=')';std::string op=expression();
     if(p!=closing)throw std::runtime_error("Invalid operator inside a matrix element.");
     s[closing]='|';p=closing+1;
     size_t rightStart=p;p=labelEnd('>',p);
     if(p==std::string::npos)throw std::runtime_error("Unclosed ket in matrix element.");
     std::string right=s.substr(rightStart,p-rightStart);++p;
     std::string state;
     if(vectorized) {need('>');state=operatorState(right);}
     else state=basisState(right,dimensionSuffix());
     // Adjacent input registers belong to the same matrix element. Build
     // their tensor product before contracting it with the operator and bra.
     while(take('|')) {
      if(++nodes>512)throw std::runtime_error("Quantum expression is too complex.");
      size_t nextStart=p;p=labelEnd('>',p);
      if(p==std::string::npos)throw std::runtime_error("Unclosed adjacent ket in matrix element.");
      std::string nextLabel=s.substr(nextStart,p-nextStart);++p;
      std::string nextState=take('>') ? operatorState(nextLabel) : basisState(nextLabel,dimensionSuffix());
      state="qtensor("+state+","+nextState+")";
     }
     a="qmul(qmul("+a+","+op+"),"+state+")";kind=0;
    }
   }
  }
  else {
   ws(); size_t b=p;
   bool numericToken=p<s.size() && (std::isdigit((unsigned char)s[p]) || s[p]=='.');
   if(numericToken) {
    while(p<s.size() && (std::isdigit((unsigned char)s[p]) || s[p]=='.')) ++p;
    if(p<s.size() && (s[p]=='e' || s[p]=='E')) {
     size_t exponent=p++; if(p<s.size() && (s[p]=='+' || s[p]=='-')) ++p;
     size_t digits=p; while(p<s.size() && std::isdigit((unsigned char)s[p])) ++p;
     if(p==digits) p=exponent;
    }
   } else {
    while(p<s.size() && !radical() && (std::isalnum((unsigned char)s[p]) || (unsigned char)s[p]>=128 || s[p]=='_')) ++p;
   }
   if(b==p) throw std::runtime_error("Expected a quantum expression at byte "+std::to_string(p+1));
   a=s.substr(b,p-b); ws();
   if(numericToken && p<s.size() && (s[p]=='_' || s.compare(p,std::string("₂").size(),"₂")==0)) {
    if(s[p]=='_') {
     ++p;size_t start=p;while(p<s.size() && std::isdigit((unsigned char)s[p]))++p;
     if(s.substr(start,p-start)!="2")throw std::runtime_error("Numeric radix subscripts currently require base 2.");
    } else p+=std::string("₂").size();
    a=binaryNumeral(a);ws();
    if(p<s.size() && (s[p]=='_' || s.compare(p,std::string("₂").size(),"₂")==0))throw std::runtime_error("A binary numeral cannot have a second radix subscript.");
   }
   if(a=="and" || a=="or" || a=="not" || (a=="xor" && (p==s.size() || s[p]!='(')))throw std::runtime_error("Expected an operand; group a logical predicate when using it in arithmetic.");
   // A scalar prefix is its own token so powers/daggers bind to the gate:
   // iY^2 means i*(Y^2), while (iY)^2 squares the entire product.
   // Match complete gate names first, notably iSWAP.
   if(a.size()>1 && a[0]=='i' && gates.find(a)==gates.end() && gates.find(a.substr(1))!=gates.end()) {p=b+1;a="i";}
   if(a.compare(0,4,"SUM_")==0) {
    std::string dimension=a.substr(4);
    if(dimension.empty() || dimension.find_first_not_of("0123456789")!=std::string::npos) throw std::runtime_error("SUM subscripts require an integer dimension; use SUM(d) for an expression.");
    a="qsumgate("+dimension+","+dimension+")";
   }
   else if(gates.find(a)!=gates.end()) { a=gates.at(a); }
   else if(take('(')) {
    std::string publicName=a, name=a; if(name=="dagger" || name=="adjoint") name="qdag";
    if(name=="J_x" || name=="Jₓ") name="Jx";
    if(name=="J_y") name="Jy";
    if(name=="J_z") name="Jz";
    if(name=="J₊") name="Jplus";
    if(name=="J₋") name="Jminus";
    if(name=="CRX" || name=="CR_x" || name=="CR_{x}") name="CRx";
    if(name=="CRY" || name=="CR_y" || name=="CR_{y}") name="CRy";
    if(name=="CRZ" || name=="CR_z" || name=="CR_{z}") name="CRz";
    if(name=="U_1" || name=="U_2" || name=="U_3") name="U"+name.substr(2);
    // Textbook subscripts and API-style names denote the same rotations.
    if(name.size()>=3 && name.substr(0,2)=="R_") {
     std::string axes=name.substr(2);
     for(char &axis:axes) axis=std::tolower((unsigned char)axis);
     if(axes=="x" || axes=="y" || axes=="z" || axes=="xx" || axes=="yy" || axes=="zz" || axes=="zx") name="R"+axes;
    }
    if(name=="tr" || name=="Tr" || name=="trace") name="qtrace";
    if(name=="tensor") name="qtensor";
    if(name=="bitdot" || name=="binarydot")name="qbitdot";
    if(name=="bitxor" || name=="binaryxor")name="qbitxor";
    if(name=="bits")name="qbits";
    if(name=="gf2_rref")name="qgf2rref";
    if(name=="gf2_rank")name="qgf2rank";
    if(name=="gf2_mul")name="qgf2mul";
    if(name=="linear_gate")name="qlineargate";
    if(name=="gf2_inverse")name="qgf2inverse";
    if(name=="gf2_nullspace")name="qgf2nullspace";
    if(name=="stabilizer_projector")name="qstabilizerprojector";
    if(name=="stabilizer_dimension")name="qstabilizerdimension";
    if(name=="stabilizer_distance")name="qstabilizerdistance";
    if(name=="stabilizer_parameters")name="qstabilizerparameters";
    if(name=="stabilizer_syndrome")name="qstabilizersyndrome";
    if(name=="stabilizer_correction")name="qstabilizercorrection";
    if(name=="css_generators")name="qcssgenerators";
    if(name=="css_state")name="qcssstate";
    if(name=="css_encoder")name="qcssencoder";
    if(name=="bitvalue")name="qbitvalue";
    if(name=="density") name="qdensity";
    if(name=="bloch") name="qbloch";
    if(name=="ptrace") name="qptrace";
    if(name=="permute") name="qpermute";
    if(name=="vec") name="qvec";
    if(name=="spre") name="qspre";
    if(name=="spost") name="qspost";
    if(name=="sprepost") name="qsprepost";
    if(name=="lindblad_dissipator") name="qlindblad";
    if(name=="liouvillian") name="qliouvillian";
    if(name=="paulivec") name="qpaulivec";
    if(name=="unpaulivec") name="qunpaulivec";
    if(name=="unvec") name="qunvec";
    if(name=="superop") name="qsuperop";
    if(name=="ptm" || name=="PTM") name="qptm";
    if(name=="choi") name="qchoi";
    if(name=="chi" || name=="Chi" || name=="χ") name="qchi";
    if(name=="comm") name="qcomm";
    if(name=="anticomm") name="qanticomm";
    if(name=="controlled" || name=="C") name="qcontrolled";
    if(name=="directsum") name="qdirectsum";
    if(name=="normalize") name="qnormalize";
    if(name=="norm") name="qnorm";
    if(name=="schatten") name="qschatten";
    if(name=="tracenorm") name="qtracenorm";
    if(name=="spectralnorm") name="qspectralnorm";
    if(name=="frobeniusnorm") name="qfrobeniusnorm";
    if(name=="expect") name="qexpect";
    if(name=="purity") name="qpurity";
    if(name=="entropy") name="qentropy";
    if(name=="schmidt_coeffs") name="qschmidt";
    if(name=="sqrt") name="qsqrt";
    if(name=="negativity") name="qnegativity";
    if(name=="lognegativity") name="qlognegativity";
    if(name=="tracedistance" || name=="tracedist") name="qtracedistance";
    if(name=="fidelity") name="qfidelity";
    if(name=="root_fidelity" || name=="rootfidelity") name="qrootfidelity";
    if(name=="hellinger_fidelity") name="qhellingerfidelity";
    if(name=="hellinger_distance") name="qhellingerdistance";
    if(name=="variance") name="qvariance";
    if(name=="channel") name="qchannel";
    if(name=="amplitude_damping") name="qamplitudedamping";
    if(name=="phase_amplitude_damping") name="qcombineddamping";
    if(name=="thermal_relaxation") name="qthermalrelaxation";
    if(name=="phase_damping") name="qphasedamping";
    if(name=="depolarizing") name="qdepolarizing";
    if(name=="reset") name="qreset";
    if(name=="dephase") name="qdephase";
    if(name=="feedforward") name="qfeedforward";
    if(name=="tensorpow") name="qtensorpow";
    if(name=="tensorproduct") name="qtensorproduct";
    if(name=="blocksum") name="qblocksum";
    if(name=="probs") name="qprobs";
    if(name=="QFT") name="qft";
    if(name=="phaseoracle") name="qphaseoracle";
    if(name=="phase_function")name="qphasefunction";
    if(name=="oracle") name="qoracle";
    if(name=="oracle_function")name="qoraclefunction";
    if(name=="modmul") name="qmodmul";
    if(name=="destroy" || name=="annihilation") name="qdestroy";
    if(name=="create" || name=="creation") name="qcreate";
    if(name=="numberop") name="qnumberop";
    if(name=="fdestroy") name="qfdestroy";
    if(name=="fcreate") name="qfcreate";
    if(name=="Jx") name="qjx";
    if(name=="Jy") name="qjy";
    if(name=="Jz") name="qjz";
    if(name=="Jplus") name="qjplus";
    if(name=="Jminus") name="qjminus";
    if(name=="diffusion") name="qdiffusion";
    if(name=="reflection") name="qreflection";
    if(name=="phase_reflection") name="qphasereflection";
    if(name=="shift") name="qshift";
    if(name=="clock") name="qclock";
    if(name=="fourier") name="qfourier";
    if(name=="SUM" || name=="CADD") name="qsumgate";
    if(name=="apply") name="qapply";
    if(name=="basis") name="qbasis";
    if(name=="exp" || name=="expm") name="qexp";
    if(name=="logm") name="qlogm";
    if(name=="sinhc") name="qsinhc";
    if(name=="evolution") name="qevolution";
    if(name=="born") name="qborn";
    if(name=="postselect") name="qpostselect";
    if(name=="ptranspose") name="qptranspose";
    if(name=="transpose") name="qtranspose";
    if(name=="conjugate") name="qconj";
    if((name=="qstabilizerprojector" || name=="qstabilizerdimension" || name=="qstabilizersyndrome" || name=="qstabilizerdistance" || name=="qstabilizerparameters" || name=="qstabilizercorrection") && take('<')) {
     // In this argument position angle brackets denote a generated Pauli
     // group, not a bra. Compact adjacent letters are tensor factors here.
     std::string generators="vector(";size_t count=0;
     do {
      ws();size_t begin=p;while(p<s.size() && s[p]!=',' && s[p]!='>')++p;
      if(p==s.size())throw std::runtime_error("Unclosed stabilizer generator group.");
      std::string label;
      bool separator=false;
      for(size_t k=begin;k<p;++k) {
       unsigned char c=s[k];if(std::isspace(c))continue;
       if(c=='@') {
        if(label.empty() || separator || std::string("IXYZ").find(label.back())==std::string::npos)throw std::runtime_error("A tensor separator must occur between Pauli factors.");
        separator=true;continue;
       }
       if(separator && std::string("IXYZ").find(c)==std::string::npos)throw std::runtime_error("Expected a Pauli factor after the tensor separator.");
       label+=c;separator=false;
      }
      if(separator)throw std::runtime_error("A tensor separator requires a following Pauli factor.");
      if(++count>32)throw std::runtime_error("Stabilizer groups support at most 32 generators.");
      if(count>1)generators+=",";
      generators+=pauliLabelExpression(label);
     } while(take(','));
     need('>');generators+=")";a=name+"("+generators;
     if(name=="qstabilizersyndrome" || name=="qstabilizercorrection") {need(',');a+=","+expression();}
     need(')');a+=")";
    } else if(name=="pauli" || name=="Pauli") {
     ws(); char quote=take('"') ? '"' : take('\'') ? '\'' : 0; size_t begin=p;
     while(p<s.size() && s[p]!=(quote ? quote : ')')) ++p;
     if(p==s.size()) throw std::runtime_error("Unclosed Pauli label.");
     std::string label=labelText(s.substr(begin,p-begin)); if(quote) ++p; need(')');
     a=pauliLabelExpression(label);
    } else if(name=="qschmidt" || name=="qptrace" || name=="qptranspose" || name=="qpermute" || name=="qnegativity" || name=="qlognegativity") {
     std::string state=expression(); need(','); std::string indices=expression();
     if(take(',')) { std::string dimensions=expression(); a=name+"dim("+state+","+indices+","+dimensions+")"; }
     else a=name+"("+state+","+indices+")";
     need(')');
    } else if(name=="qnorm") {
     std::string operand=expression();
     if(take(','))a="qschatten("+operand+","+expression()+")";else a="qnorm("+operand+")";
     need(')');
    } else if(name=="qentropy") {
     std::string state=expression();
     if(take(',')) {std::string base=expression();a="qentropybase("+state+","+base+")";}
     else a="qentropy("+state+")";
     need(')');
    } else if(name=="qprobs") {
     std::string state=expression();
     if(take(',')) { std::string indices=expression(); a="qprobsub("+state+","+indices+")"; }
     else a="qprobs("+state+")";
     need(')');
    } else if(name=="qreset" || name=="qdephase") {
     std::string state=expression();
     if(take(',')) { std::string indices=expression(); a=name+"("+state+","+indices+")"; }
     else a=name+"all("+state+")";
     need(')');
    } else if(name=="qbloch") {
     std::string state=expression();
     if(take(',')) {std::string wire=expression();a="qblochsub("+state+","+wire+")";}
     else a="qbloch("+state+")";
     need(')');
    } else if(name=="qbitvalue") {
     a="qbitvalue("+binaryArgument()+")";need(')');
    } else if(name=="qbitdot" || name=="qbitxor") {
     std::string left=binaryArgument();need(',');std::string right=binaryArgument();need(')');
     a=name+"("+left+","+right+")";
    } else if(name=="qamplitudedamping") {
     std::string damping=expression();
     if(take(',')) {std::string population=expression();a="qgeneralizeddamping("+damping+","+population+")";}
     else a="qamplitudedamping("+damping+")";
     need(')');
    } else if(name=="qcombineddamping") {
     std::string amplitude=expression();need(',');std::string phase=expression(),population="0";
     if(take(','))population=expression();need(')');
     a="qcombineddamping("+amplitude+","+phase+","+population+")";
    } else if(name=="qthermalrelaxation") {
     std::string t1=expression();need(',');std::string t2=expression();need(',');std::string time=expression(),population="0";
     if(take(','))population=expression();need(')');
     a="qthermalrelaxation("+t1+","+t2+","+time+","+population+")";
    } else if(name=="qchannel") {
     std::string state=expression(); need(','); std::string operators=expression();
     if(take(',')) { std::string indices=expression(); a="qindexedchannel("+state+","+operators+","+indices+")"; }
     else a="qchannel("+state+","+operators+")";
     need(')');
    } else if(name=="qfdestroy" || name=="qfcreate") {
     std::string modes=expression();need(',');std::string site=expression();need(')');a=name+"("+modes+","+site+")";
    } else if(name=="qdestroy" || name=="qcreate" || name=="qnumberop") {
     std::string dimension=expression();need(')');a=name+"("+dimension+")";
    } else if(name=="qoracle") {
     std::string table=expression(), bits="1";
     if(take(','))bits=expression(); need(')');
     a="qoracle("+table+","+bits+")";
    } else if(name=="qsumgate") {
     std::string control=expression(), target=control;
     if(take(',')) target=expression(); need(')');
     a="qsumgate("+control+","+target+")";
    } else if(name=="qliouvillian") {
     std::string hamiltonian=expression();
     if(take(','))a="qliouvillian("+hamiltonian+","+expression()+")";
     else a="qliouvillianclosed("+hamiltonian+")";
     need(')');
    } else if(name=="qcontrolled") {
     std::string gate=expression(), count="1", state;
     size_t patternLength=0;
     if(take(',')) count=expression();
     if(take(',')) {
      if(take('"')) {
       size_t value=0;
       while(p<s.size() && s[p]!='"') {
        if((s[p]!='0' && s[p]!='1') || patternLength>=8) throw std::runtime_error("Control patterns require one to eight binary digits.");
        value=value*2+(s[p++]-'0');++patternLength;
       }
       need('"');
       if(!patternLength) throw std::runtime_error("Control patterns cannot be empty.");
       state=std::to_string(value);
      } else state=expression();
     }
     need(')');
     if(state.empty()) state="(2^("+count+")-1)";
     a=patternLength ? "qcontrolpattern("+gate+","+count+","+state+","+std::to_string(patternLength)+")" : "qcontrol("+gate+","+count+","+state+")";
    } else if(name=="XPowGate" || name=="ZPowGate" || name=="CZPowGate") {
     // Cirq's eigenvalue-power convention includes a phase relative to Rx/Rz.
     std::string exponent="1", shift="0";bool haveExponent=false,haveShift=false,named=false;
     if(!take(')')) {
      do {
       ws();size_t begin=p;
       while(p<s.size() && (std::isalpha((unsigned char)s[p]) || s[p]=='_'))++p;
       std::string key=s.substr(begin,p-begin);ws();
       bool keyword=p<s.size() && s[p]=='=' && (p+1==s.size() || s[p+1]!='=');
       if(keyword) {++p;named=true;}
       else {p=begin;if(named)throw std::runtime_error("Positional power-gate arguments must precede named arguments.");key=haveExponent ? "global_shift" : "exponent";}
       if(key=="exponent") {if(haveExponent)throw std::runtime_error("Duplicate exponent.");exponent=expression();haveExponent=true;}
       else if(key=="global_shift") {if(haveShift)throw std::runtime_error("Duplicate global_shift.");shift=expression();haveShift=true;}
       else throw std::runtime_error("Power gates accept exponent and global_shift only; qubit dimension is two.");
      } while(take(','));
      need(')');
     }
     std::string phase="exp(i*pi*("+exponent+")*("+shift+"))", eigen="exp(i*pi*("+exponent+"))";
     if(name=="ZPowGate")a=phase+"*[1,0;0,"+eigen+"]";
     else if(name=="CZPowGate")a=phase+"*[1,0,0,0;0,1,0,0;0,0,1,0;0,0,0,"+eigen+"]";
     else a=phase+"/2*[(1+"+eigen+"),(1-"+eigen+");(1-"+eigen+"),(1+"+eigen+")]";
     a="("+a+")";
    } else if(name=="Rxx" || name=="Ryy" || name=="Rzz" || name=="Rzx") {
     std::string theta=expression(); need(')');
     std::string first(1,std::toupper(name[1])), second(1,std::toupper(name[2]));
     a="qexp((-i*("+theta+")/2)*qtensor("+gates.at(first)+","+gates.at(second)+"))";
    } else if(name=="R") {
     std::string theta="("+expression()+")";need(',');
     std::string phi="("+expression()+")";need(')');
     std::string co="cos("+theta+"/2)", si="sin("+theta+"/2)";
     a="["+co+",-i*exp(-i*"+phi+")*"+si+";-i*exp(i*"+phi+")*"+si+","+co+"]";
    } else if(name=="XXPlusYY" || name=="XXMinusYY") {
     std::string theta="("+expression()+")", beta="0";
     if(take(','))beta="("+expression()+")";need(')');
     std::string co="cos("+theta+"/2)", si="-i*sin("+theta+"/2)";
     std::string positive=si+"*exp(i*"+beta+")", negative=si+"*exp(-i*"+beta+")";
     // First operand is the most significant bit; preserve physical wire order.
     if(name=="XXPlusYY")a="[1,0,0,0;0,"+co+","+positive+",0;0,"+negative+","+co+",0;0,0,0,1]";
     else a="["+co+",0,0,"+negative+";0,1,0,0;0,0,1,0;"+positive+",0,0,"+co+"]";
    } else if(name=="fSim" || name=="FSim") {
     std::string theta="("+expression()+")"; need(',');
     std::string phi="("+expression()+")"; need(')');
     std::string co="cos("+theta+")", si="-i*sin("+theta+")";
     a="[1,0,0,0;0,"+co+","+si+",0;0,"+si+","+co+",0;0,0,0,exp(-i*"+phi+")]";
    } else if(name=="U" || name=="U3" || name=="U2" || name=="U1") {
     std::string theta="0", phi="0", lambda;
     if(name=="U" || name=="U3") {theta="("+expression()+")"; need(',');}
     else if(name=="U2") theta="(pi/2)";
     if(name!="U1") {phi="("+expression()+")"; need(',');}
     lambda="("+expression()+")"; need(')');
     std::string co="cos("+theta+"/2)", si="sin("+theta+"/2)";
     a="["+co+",-exp(i*"+lambda+")*"+si+";exp(i*"+phi+")*"+si+",exp(i*("+phi+"+"+lambda+"))*"+co+"]";
    } else if(name=="Rx" || name=="Ry" || name=="Rz" || name=="P" || name=="CRx" || name=="CRy" || name=="CRz" || name=="CP") {
     bool controlled=name[0]=='C'; if(controlled) name=name.substr(1);
     std::string theta="("+expression()+")"; need(')');
     std::string co="cos("+theta+"/2)", si="sin("+theta+"/2)";
     if(name=="Rx") a="["+co+",-i*"+si+";-i*"+si+","+co+"]";
     if(name=="Ry") a="["+co+",-"+si+";"+si+","+co+"]";
     if(name=="Rz") a="[exp(-i*"+theta+"/2),0;0,exp(i*"+theta+"/2)]";
     if(name=="P") a="[1,0;0,exp(i*"+theta+")]";
     if(controlled) a="qcontrolled("+a+")";
    } else {
    a=name+"("; unsigned count=0;
    if(!take(')')) { a+=expression(); ++count; while(take(',')) {a+=","+expression();++count;} need(')'); } a+=")";
    auto signature=quantumSignatures.find(name);
    if(signature!=quantumSignatures.end() && count!=(unsigned)signature->second) throw std::runtime_error("Quantum function "+publicName+" requires exactly "+std::to_string(signature->second)+" arguments.");
    }
   } else { auto it=gates.find(a); if(it!=gates.end()) a=it->second; }
  }
  while(true) {
   if(take('~')) {a="qdag("+a+")";if(kind)kind=3-kind;}
   else if(take('`')) {a="qtranspose("+a+")";if(kind)kind=3-kind;}
   else if(take('?')) a="qconj("+a+")";
   else break;
  }
  --depth;diracKind=kind;return a;
 }
 std::string power() {
  auto a=atom();int kind=diracKind;
  if(take('^')) {
   kind=0;
   if(a=="C") {
    std::string controls;
    if(take('(')) { controls=expression(); need(')'); }
    else { ws(); size_t start=p; while(p<s.size() && std::isdigit((unsigned char)s[p])) ++p; controls=s.substr(start,p-start); }
    if(controls.empty()) throw std::runtime_error("C^n(U) requires an integer control count or a grouped count expression.");
    need('('); std::string gate=expression(); need(')');
    a="qcontrol("+gate+","+controls+",(2^("+controls+")-1))";
    while(take('~')) a="qdag("+a+")";
   }
   else if(take('@')) a="qtensorpow("+a+","+unary()+")";
   else if(take('%')) {
    need('('); std::string indices=expression(); while(take(',')) indices+=","+expression(); need(')');
    a="qptranspose("+a+",vector("+indices+"))";
   }
   else if(take('`') || take('T')) a="qtranspose("+a+")";
   else if(take('*')) a="qconj("+a+")";
   else if(a=="e") a="qexp("+unary()+")";
   else a="qpower("+a+","+unary()+")";
  }
  diracKind=kind;return a;
 }
 std::string unary() {
  if(++depth>256)throw std::runtime_error("Quantum expression nesting exceeds 256.");
  std::string a;ws();unsigned root=radical();
  if(root) {p+=3;a="qpower("+unary()+",1/"+std::to_string(root)+")";diracKind=0;}
  else if(take('+'))a=unary();
  else if(take('-'))a="(-"+unary()+")";
  else a=power();
  --depth;return a;
 }
 std::string diracFactor() {
  auto a=unary();int kind=diracKind;
  while(kind) {
   ws();if(p==s.size() || s[p]!=(kind==1 ? '|' : '<'))break;
   auto b=unary();
   if(diracKind==kind)a="qtensor("+a+","+b+")";
   else {a="qmul("+a+","+b+")";kind=0;}
  }
  diracKind=kind;return a;
 }
 bool moduloWord() {
  ws();if(s.compare(p,3,"mod")!=0 || (p>0 && !std::isspace((unsigned char)s[p-1])))return false;
  size_t end=p+3;
  if(end<s.size() && (std::isalnum((unsigned char)s[end]) || s[end]=='_' || (unsigned char)s[end]>=128))return false;
  p=end;return true;
 }
 std::string product() {
  auto a=diracFactor();
  while(true) {
   if(take('%') || moduloWord()) a="mod("+a+","+diracFactor()+")";
   else if(take('*')) a="qmul("+a+","+diracFactor()+")";
   else if(take('/')) a="("+a+"/("+diracFactor()+"))";
   else if(take('@')) a="qtensor("+a+","+diracFactor()+")";
   else if(take('#')) a="qdirectsum("+a+","+diracFactor()+")";
   else if(startsAtom()) a="qmul("+a+","+diracFactor()+")";
   else break;
  } return a;
 }
 std::string additive() {
  auto a=product();
  while(true) {
   if(take('+')) {auto b=product();a=spinContext ? "qspinadd("+a+","+b+")" : "("+a+"+"+b+")";}
   else if(take('-')) {auto b=product();a=spinContext ? "qspinadd("+a+",(-"+b+"))" : "("+a+"-"+b+")";}
   else break;
  }
  return a;
 }
 std::string comparison() {
  std::string left=additive(),result;
  while(true) {
   ws();std::string relation;
   for(const char *token:{"<=",">=","!=","==","=","<",">"}) {
    std::string candidate(token);
    if(s.compare(p,candidate.size(),candidate)==0) {relation=candidate;p+=candidate.size();break;}
   }
   if(relation.empty())break;
   int kind=relation=="<" ? 0 : relation==">" ? 1 : relation=="<=" ? 2 : relation==">=" ? 3 : relation=="!=" ? 5 : 4;
   std::string right=additive(),clause="qcompare("+left+","+right+","+std::to_string(kind)+")";
   result=result.empty() ? clause : "("+result+"&&"+clause+")";left=right;
  }
  return result.empty() ? left : result;
 }
 std::string logicalNot() {
  size_t count=0;
  while(takeWord("not"))if(++count>128)throw std::runtime_error("Too many nested logical negations.");
  std::string result=comparison();
  for(size_t k=0;k<count;++k)result="!("+result+")";
  return result;
 }
 std::string logicalAnd() {
  std::string result=logicalNot();
  while(takeWord("and"))result="("+result+"&&"+logicalNot()+")";
  return result;
 }
 std::string logicalXor() {
  std::string result=logicalAnd();
  while(takeWord("xor"))result="lxor("+result+","+logicalAnd()+")";
  return result;
 }
 std::string expression() {
  std::string result=logicalXor();
  while(takeWord("or"))result="("+result+"||"+logicalXor()+")";
  return result;
 }
 public:
 explicit Parser(std::string text,bool spin=false):spinContext(spin),s(text) {}
 std::string run() { auto out=expression(); ws(); if(p!=s.size()) throw std::runtime_error("Unexpected notation at byte "+std::to_string(p+1)); return out; }
};

const MathStructure &element(const MathStructure &m, size_t r, size_t c) { return *m.getElement(r+1,c+1); }
MathStructure &element(MathStructure &m, size_t r, size_t c) { return *m.getElement(r+1,c+1); }
MathStructure dagger(const MathStructure &a, const EvaluationOptions &eo) {
 MathStructure out=a;
 if(out.isMatrix()) {
  out.transposeMatrix();
  for(size_t r=0;r<out.rows();++r) for(size_t c=0;c<out.columns();++c) {
   MathStructure v=element(out,r,c); element(out,r,c).set(CALCULATOR->getFunction("conj"), &v, NULL); element(out,r,c).eval(eo);
  }
 } else { out.set(CALCULATOR->getFunction("conj"), &a, NULL); out.eval(eo); }
 return out;
}
MathStructure multiply(MathStructure a, const MathStructure &b, const EvaluationOptions &eo) {
 a*=b; a.eval(eo);
 if(a.isMatrix() && a.rows()==1 && a.columns()==1) { MathStructure scalar=element(a,0,0); return scalar; }
 return a;
}
MathStructure trace(const MathStructure &matrix,const EvaluationOptions &eo) {
 MathStructure value;
 for(size_t r=0;r<matrix.rows();++r) value+=element(matrix,r,r);
 value.eval(eo); return value;
}
bool zeroMatrix(MathStructure matrix,const EvaluationOptions &eo) {
 matrix.eval(eo);
 if(!matrix.isMatrix()) return matrix.isZero();
 for(size_t r=0;r<matrix.rows();++r) for(size_t c=0;c<matrix.columns();++c) if(!element(matrix,r,c).isZero()) return false;
 return true;
}
MathStructure twoSidedSuperoperator(const MathStructure &left,MathStructure right,const EvaluationOptions &eo) {
 right.transposeMatrix();MathStructure result;
 result.set(CALCULATOR->getFunction("qtensor"),&right,&left,NULL);result.eval(eo);return result;
}
MathStructure dissipator(const MathStructure &collapse,const EvaluationOptions &eo) {
 MathStructure adjoint=dagger(collapse,eo), product=multiply(adjoint,collapse,eo), identity;
 identity.setToIdentityMatrix(collapse.rows());
 MathStructure result=twoSidedSuperoperator(collapse,adjoint,eo);
 MathStructure loss=twoSidedSuperoperator(product,identity,eo);loss+=twoSidedSuperoperator(identity,product,eo);
 loss/=2;result-=loss;result.eval(eo);return result;
}
void pauliBasis(size_t d,std::vector<std::vector<size_t>> &locations,std::vector<std::vector<Number>> &phases) {
 locations.assign(d*d,std::vector<size_t>(d));phases.assign(d*d,std::vector<Number>(d));
 for(size_t p=0;p<d*d;++p)for(size_t c=0;c<d;++c) {
  size_t digits=p,row=c,bit=1;int phase=0;
  while(bit<d) {
   unsigned axis=digits%4;digits/=4;
   if(axis==1 || axis==2)row^=bit;
   if(axis==2)phase+=(c & bit) ? 3 : 1;
   if(axis==3 && (c & bit))phase+=2;
   bit<<=1;
  }
  locations[p][c]=row+d*c;
  Number factor;
  if(phase%2)factor.setImaginaryPart(phase%4==1 ? 1 : -1);
  else factor=phase%4==0 ? 1 : -1;
  phases[p][c]=factor;
 }
}
unsigned binaryParity(size_t value) {unsigned parity=0;while(value){parity^=1;value&=value-1;}return parity;}
struct SignedPauli {size_t x=0,z=0,d=0;unsigned phase=0;};
Number pauliPhase(unsigned phase) {
 Number value;
 if(phase%2)value.setImaginaryPart(phase%4==1 ? 1 : -1);
 else value=phase%4==0 ? 1 : -1;
 return value;
}
bool readSignedPauli(const MathStructure &matrix,SignedPauli &out,bool hermitian) {
 if(!matrix.isMatrix() || matrix.rows()!=matrix.columns() || matrix.rows()<2 || matrix.rows()>512 || (matrix.rows()&(matrix.rows()-1)))return false;
 out=SignedPauli();out.d=matrix.rows();bool found=false;
 for(size_t c=0;c<out.d;++c) {
  const MathStructure &v=element(matrix,0,c);if(!v.isNumber())return false;
  if(!v.number().isZero()) {if(found)return false;found=true;out.x=c;bool unit=false;for(unsigned p=0;p<4;++p)if(v.number().equals(pauliPhase(p))){out.phase=p;unit=true;break;}if(!unit)return false;}
 }
 if(!found)return false;
 for(size_t bit=1;bit<out.d;bit<<=1) {
  const MathStructure &v=element(matrix,bit,bit^out.x);if(!v.isNumber())return false;
  if(v.number().equals(pauliPhase(out.phase+2)))out.z|=bit;
  else if(!v.number().equals(pauliPhase(out.phase)))return false;
 }
 for(size_t r=0;r<out.d;++r) {
  if(CALCULATOR->aborted())return false;
  Number expected=pauliPhase(out.phase+2*binaryParity(r&out.z));
  for(size_t c=0;c<out.d;++c) {const MathStructure &v=element(matrix,r,c);if(!v.isNumber() || (c==(r^out.x) ? !v.number().equals(expected) : !v.number().isZero()))return false;}
 }
 return !hermitian || (out.phase+binaryParity(out.x&out.z))%2==0;
}
SignedPauli multiplyPauli(const SignedPauli &a,const SignedPauli &b) {
 SignedPauli result;result.d=a.d;result.x=a.x^b.x;result.z=a.z^b.z;result.phase=(a.phase+b.phase+2*binaryParity(a.x&b.z))%4;return result;
}
bool stabilizerGenerators(const MathStructure &input,std::vector<SignedPauli> &generators,size_t &rank) {
 std::vector<MathStructure> matrices;
 if(input.isMatrix() && input.rows()>0 && input.columns()>0 && element(input,0,0).isNumber())matrices.push_back(input);
 else if(input.isVector() && input.size()>0 && input.size()<=32)for(size_t k=0;k<input.size();++k)matrices.push_back(input[k]);
 else {CALCULATOR->error(true,"Stabilizers require one Pauli matrix or a nonempty vector of at most 32 Pauli matrices.",NULL);return false;}
 for(const auto &matrix:matrices) {
  SignedPauli p;if(!readSignedPauli(matrix,p,true) || (!generators.empty() && p.d!=generators[0].d)) {CALCULATOR->error(true,"Stabilizer generators must be Hermitian signed Pauli matrices on the same 1 to 9 qubits.",NULL);return false;}
  for(const auto &previous:generators)if(binaryParity((p.x&previous.z)^(p.z&previous.x))) {CALCULATOR->error(true,"Stabilizer generators must commute.",NULL);return false;}
  generators.push_back(p);
 }
 size_t bits=0;while((size_t(1)<<bits)<generators[0].d)++bits;
 std::vector<SignedPauli> basis(2*bits);std::vector<bool> present(2*bits,false);rank=0;
 for(auto p:generators) {
  for(size_t column=2*bits;column-->0;) {
   size_t word=p.x|(p.z<<bits);if(!(word&(size_t(1)<<column)))continue;
   if(present[column])p=multiplyPauli(p,basis[column]);
   else {basis[column]=p;present[column]=true;++rank;break;}
  }
  if(!p.x && !p.z && p.phase) {CALCULATOR->error(true,"The generators contain -I in their group and have no common +1 eigenspace.",NULL);return false;}
 }
 return true;
}
bool noiseParameter(const MathStructure &a,const Number &upper,const EvaluationOptions &eo) {
 MathStructure parameter=a;EvaluationOptions numeric=eo;numeric.approximation=APPROXIMATION_APPROXIMATE;parameter.eval(numeric);
 if(!parameter.isNumber() || parameter.number().isComplex() || parameter.number().isUndefined() || parameter.number().isInfinite(false)) {
  CALCULATOR->error(true,"Noise parameters must be finite real numbers.",NULL);return false;
 }
 Number value=parameter.number();
 if((a.isNumber() && (a.number()<0 || a.number()>upper)) || (value.isInterval() && !value.intervalToPrecision(12)) || value<0 || value>upper) {
  CALCULATOR->error(true,"Damping parameters and equilibrium populations must be in [0,1], with amplitude+phase <= 1; depolarizing lambda must be in [0,4/3], without broad uncertainty.",NULL);return false;
 }
 return true;
}
// Substitute a free index without capturing a nested finite-product/sum index.
void replaceQuantumIndex(MathStructure &value,const MathStructure &index,const MathStructure &replacement) {
 if(value.equals(index)) {value=replacement;return;}
 int bound=-1;
 if(value.isFunction() && value.size()==4) {
  const std::string &name=value.function()->referenceName();
  if((name=="qtensorproduct" || name=="qblocksum" || name=="qoraclefunction" || name=="sum" || name=="product") && value[3].equals(index))bound=3;
 }
 if(value.isFunction() && value.size()==3 && value.function()->referenceName()=="qphasefunction" && value[2].equals(index))bound=2;
 for(size_t k=0;k<value.size();++k) {
  if(bound>=0 && (k==0 || k==size_t(bound)))continue;
  replaceQuantumIndex(value[k],index,replacement);
 }
 value.childrenUpdated();
}
bool binaryMatrix(const MathStructure &a,std::vector<std::vector<unsigned char>> &matrix) {
 size_t rows=a.isMatrix() ? a.rows() : 1, columns=a.isMatrix() ? a.columns() : a.isVector() ? a.size() : 1;
 if(rows==0 || columns==0 || rows>128 || columns>128) {CALCULATOR->error(true,"GF(2) operations require a nonempty matrix with at most 128 rows and columns.",NULL);return false;}
 matrix.assign(rows,std::vector<unsigned char>(columns));
 for(size_t r=0;r<rows;++r)for(size_t c=0;c<columns;++c) {
  const MathStructure &value=a.isMatrix() ? element(a,r,c) : a.isVector() ? a[c] : a;
  if(!value.isNumber() || (!value.number().isZero() && !value.number().isOne())) {CALCULATOR->error(true,"GF(2) matrix entries must be 0 or 1.",NULL);return false;}
  matrix[r][c]=value.number().isOne() ? 1 : 0;
 }
 return true;
}
// Hermitian Loewner order via exact Schur complements. A zero diagonal in a
// PSD matrix must have a zero row; testing this also handles singular matrices
// without a numerical eigenvalue tolerance or division by a zero pivot.
bool quantumMatrixOrder(MathStructure &out,MathStructure left,MathStructure right,int kind,const EvaluationOptions &eo) {
 if(!CALCULATOR->getFunction("conj")) {CALCULATOR->error(true,"Load global functions before comparing quantum matrices.",NULL);return false;}
 EvaluationOptions exact=eo;exact.approximation=APPROXIMATION_EXACT;
 left.eval(exact);right.eval(exact);
 size_t n=left.isMatrix() ? left.rows() : right.isMatrix() ? right.rows() : 0;
 if(n==0 || n>64) {CALCULATOR->error(true,"Matrix order requires square matrices of matching dimension, at most 64.",NULL);return false;}
 for(MathStructure *value:{&left,&right}) {
  if(!value->isVector() && value->representsScalar()) {
   MathStructure scalar=*value;value->clearMatrix();value->resizeMatrix(n,n,m_zero);
   for(size_t r=0;r<n;++r)element(*value,r,r)=scalar;
  }
  if(!value->isMatrix() || value->rows()!=n || value->columns()!=n) {CALCULATOR->error(true,"Matrix order requires square matrices of matching dimension; scalars mean scalar times identity.",NULL);return false;}
  for(size_t r=0;r<n;++r)for(size_t c=0;c<n;++c) {
   MathStructure other=element(*value,c,r),conjugated;
   conjugated.set(CALCULATOR->getFunction("conj"),&other,NULL);
   MathStructure difference=element(*value,r,c);difference-=conjugated;difference.eval(exact);
   if(!difference.isZero()) {CALCULATOR->error(true,"Matrix order requires provably Hermitian operands with finite entries.",NULL);return false;}
  }
 }
 MathStructure matrix;matrix.clearMatrix();matrix.resizeMatrix(n,n,m_zero);
 for(size_t r=0;r<n;++r)for(size_t c=0;c<n;++c) {
  element(matrix,r,c)=(kind==0 || kind==2) ? element(right,r,c) : element(left,r,c);
  element(matrix,r,c)-=(kind==0 || kind==2) ? element(left,r,c) : element(right,r,c);
  element(matrix,r,c).eval(exact);
 }
 bool strict=kind<2;
 for(size_t k=0;k<n;++k) {
  if(CALCULATOR->aborted())return false;
  MathStructure pivot=element(matrix,k,k);pivot.eval(exact);
  if(pivot.representsNegative()) {out=0;return true;}
  if(pivot.isZero()) {
   if(strict) {out=0;return true;}
   for(size_t r=k+1;r<n;++r) {
    const MathStructure &value=element(matrix,k,r);
    if(value.isZero())continue;
    if(value.representsNonZero()) {out=0;return true;}
    CALCULATOR->error(true,"Matrix order cannot determine whether an off-diagonal entry is zero.",NULL);return false;
   }
   continue;
  }
  if(!pivot.representsPositive()) {CALCULATOR->error(true,"Matrix order cannot determine a pivot sign; supply concrete values without unresolved uncertainty.",NULL);return false;}
  for(size_t r=k+1;r<n;++r)for(size_t c=k+1;c<n;++c) {
   MathStructure term=element(matrix,r,k);term*=element(matrix,k,c);term/=pivot;
   element(matrix,r,c)-=term;element(matrix,r,c).eval(exact);
  }
 }
 out=1;return true;
}
class QuantumFunction: public MathFunction {
 std::string op;
 public:
 QuantumFunction(std::string name,int n):MathFunction(name,n),op(name) {}
 ExpressionItem *copy() const { return new QuantumFunction(*this); }
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  if((op=="qdag" || op=="qconj" || op=="qdensity" || op=="qnorm" || op=="qnormalize" || op=="qprobs" || op=="qexpect" || op=="qchannel" || op=="qborn" || op=="qpostselect" || op=="qevolution") && !CALCULATOR->getFunction("conj")) {
   CALCULATOR->error(true,"Load the global function definitions before using quantum conjugation.",NULL); return 0;
  }
  if(op=="qphasefunction") {
   if((!raw[2].isSymbolic() && !raw[2].isVariable()) || (raw[2].isVariable() && raw[2].variable()->isKnown())) {CALCULATOR->error(true,"A phase function index must be a symbolic variable.",NULL);return 0;}
   MathStructure width=raw[1];width.eval(eo);
   if(!width.isNumber() || !width.number().isInteger() || width.number()<1 || width.number()>9) {CALCULATOR->error(true,"Phase functions require an integer width from 1 to 9 qubits.",NULL);return 0;}
   int count=1<<width.number().intValue();
   out.clearMatrix();out.resizeMatrix(count,count,m_zero);
   for(int x=0;x<count;++x) {
    if(CALCULATOR->aborted())return 0;
    MathStructure value=raw[0],index(x);replaceQuantumIndex(value,raw[2],index);value.eval(eo);
    if(!value.isNumber() || (!value.number().isZero() && !value.number().isOne())) {CALCULATOR->error(true,"A phase function must evaluate to 0 or 1 at every input index.",NULL);return 0;}
    element(out,x,x)=MathStructure(value.number().isOne() ? -1 : 1);
   }
   return 1;
  }
  if(op=="qoraclefunction") {
   if((!raw[3].isSymbolic() && !raw[3].isVariable()) || (raw[3].isVariable() && raw[3].variable()->isKnown())) {CALCULATOR->error(true,"An oracle function index must be a symbolic variable.",NULL);return 0;}
   MathStructure inputBits=raw[1],outputBits=raw[2];inputBits.eval(eo);outputBits.eval(eo);
   if(!inputBits.isNumber() || !outputBits.isNumber() || !inputBits.number().isInteger() || !outputBits.number().isInteger() || inputBits.number()<1 || outputBits.number()<1 || inputBits.number()>8 || outputBits.number()>8 || inputBits.number()+outputBits.number()>9) {CALCULATOR->error(true,"Oracle register widths must be positive integers with at most 9 total qubits.",NULL);return 0;}
   int count=1<<inputBits.number().intValue(),outputs=1<<outputBits.number().intValue();
   MathStructure table;table.clearVector();
   for(int x=0;x<count;++x) {
    if(CALCULATOR->aborted())return 0;
    MathStructure value=raw[0],index(x);replaceQuantumIndex(value,raw[3],index);value.eval(eo);
    if(!value.isNumber() || !value.number().isInteger() || value.number()<0 || value.number()>=Number(outputs)) {CALCULATOR->error(true,"Each oracle function value must be an integer from 0 to 2^m-1.",NULL);return 0;}
    table.addChild(value);
   }
   MathStructure parameters;parameters.clearVector();parameters.addChild(table);parameters.addChild(outputBits);
   QuantumFunction oracle("qoracle",2);return oracle.calculate(out,parameters,eo);
  }
  if(op=="qtensorproduct" || op=="qblocksum") {
   if((!raw[3].isSymbolic() && !raw[3].isVariable()) || (raw[3].isVariable() && raw[3].variable()->isKnown())) {CALCULATOR->error(true,"An indexed operation index must be a symbolic variable.",NULL);return 0;}
   MathStructure first=raw[1],last=raw[2];first.eval(eo);last.eval(eo);
   if(!first.isNumber() || !last.isNumber() || !first.number().isInteger() || !last.number().isInteger() || first.number() < -1000000 || last.number()>1000000 || last.number()<first.number()) {
    CALCULATOR->error(true,"Indexed operations require ascending integer bounds within -1000000 to 1000000.",NULL);return 0;
   }
   Number span=last.number();span-=first.number();
   if(span>31) {CALCULATOR->error(true,"Indexed operations support at most 32 terms.",NULL);return 0;}
   out.setToIdentityMatrix(1);
   for(int k=first.number().intValue();k<=last.number().intValue();++k) {
    if(CALCULATOR->aborted())return 0;
    MathStructure factor=raw[0],index(k);replaceQuantumIndex(factor,raw[3],index);factor.eval(eo);
    if(op=="qblocksum") {
     // Scalar blocks denote one-dimensional linear maps, not state labels.
     if(factor.representsScalar()) {
      MathStructure scalar=factor;factor.clearMatrix();factor.resizeMatrix(1,1,m_zero);element(factor,0,0)=scalar;
     }
     if(factor.isVector() && !factor.isMatrix() && factor.size()>0 && factor.size()<=1024) {
      bool flat=true;for(size_t c=0;c<factor.size();++c)if(factor[c].isVector())flat=false;
      if(flat) {MathStructure row=factor;factor.clearMatrix();factor.resizeMatrix(1,row.size(),m_zero);for(size_t c=0;c<row.size();++c)element(factor,0,c)=row[c];}
     }
     if(!factor.isMatrix()) {CALCULATOR->error(true,"Block sums require matrix or scalar blocks.",NULL);return 0;}
     if(factor.rows()>1024 || factor.columns()>1024 || factor.rows()*factor.columns()>262144) {CALCULATOR->error(true,"Block sum matrix allocation limit exceeded.",NULL);return 0;}
     if(k==first.number().intValue()) {out=factor;continue;}
     // Evaluation can collapse a 1x1 matrix to its scalar entry.
     if(!out.isVector()) {MathStructure scalar=out;out.clearMatrix();out.resizeMatrix(1,1,m_zero);element(out,0,0)=scalar;}
     // Build directly so a one-row rectangular block keeps its matrix shape.
     size_t rows=out.rows()+factor.rows(),cols=out.columns()+factor.columns();
     if(rows>1024 || cols>1024 || rows*cols>262144) {CALCULATOR->error(true,"Block sum matrix allocation limit exceeded.",NULL);return 0;}
     MathStructure previous=out;out.clearMatrix();out.resizeMatrix(rows,cols,m_zero);
     for(size_t r=0;r<previous.rows();++r)for(size_t c=0;c<previous.columns();++c)element(out,r,c)=element(previous,r,c);
     for(size_t r=0;r<factor.rows();++r)for(size_t c=0;c<factor.columns();++c)element(out,r+previous.rows(),c+previous.columns())=element(factor,r,c);
    } else {
     MathStructure previous=out;out.set(CALCULATOR->getFunction("qtensor"),&previous,&factor,NULL);out.eval(eo);
    }
    if(!out.isMatrix() && !out.isVector())return 0;
   }
   return 1;
  }
  MathStructure args=raw;
  for(size_t j=0;j<args.size();++j) args[j].eval(eo);
  // libqalculate simplifies a one-row matrix (a bra) to a flat vector.
  if(op=="qpermute" || op=="qpermutedim" || op=="qvec" || op=="qtensor" || op=="qtensorpow" || op=="qdag" || op=="qtranspose") for(size_t j=0;j<(op=="qtensor" ? 2U : 1U);++j) {
   if(!args[j].isVector() || args[j].isMatrix())continue;
   bool flat=true; for(size_t k=0;k<args[j].size();++k) if(args[j][k].isVector()) flat=false;
   if(flat && args[j].size()>0 && args[j].size()<=1024) {
    MathStructure row; row.clearMatrix(); row.resizeMatrix(1,args[j].size(),m_zero);
    for(size_t k=0;k<args[j].size();++k) element(row,0,k)=args[j][k];
    args[j]=row;
   }
  }
  if(op=="qcompare") {
   if(!args[2].isNumber() || !args[2].number().isInteger() || args[2].number()<0 || args[2].number()>5) {
    CALCULATOR->error(true,"Invalid quantum comparison kind.",NULL);return 0;
   }
   static const ComparisonType kinds[]={COMPARISON_LESS,COMPARISON_GREATER,COMPARISON_EQUALS_LESS,COMPARISON_EQUALS_GREATER,COMPARISON_EQUALS,COMPARISON_NOT_EQUALS};
   if(args[2].number()<4 && (args[0].containsType(STRUCT_VECTOR,true)>0 || args[1].containsType(STRUCT_VECTOR,true)>0))
    return quantumMatrixOrder(out,raw[0],raw[1],args[2].number().intValue(),eo) ? 1 : 0;
   out=args[0];out.transform(kinds[args[2].number().intValue()],args[1]);out.eval(eo);return 1;
  }
  if(op=="qchannel" && (args[0].representsScalar() || (args[0].isVector() && args[0].size()==1 && !args[0][0].isVector()))) {
   MathStructure value=args[0].isVector() ? args[0][0] : args[0];
   args[0].clearMatrix();args[0].resizeMatrix(1,1,m_zero);element(args[0],0,0)=value;
  }
  const MathStructure &a=args[0];
  if(op=="qspinadd") {
   const MathStructure &b=args[1];
   if(a.isVector()!=b.isVector()) {
    const MathStructure &matrix=a.isVector() ? a : b, &scalar=a.isVector() ? b : a;
    if(!matrix.isMatrix() || matrix.rows()!=matrix.columns() || matrix.rows()>512 || !scalar.representsScalar()) {
     CALCULATOR->error(true,"In a spin expression scalar offsets require a square operator (at most 512 rows).",NULL);return 0;
    }
    out=matrix;for(size_t k=0;k<matrix.rows();++k)element(out,k,k)+=scalar;out.eval(eo);return 1;
   }
   if(a.isVector() && (a.isMatrix()!=b.isMatrix() || (a.isMatrix() ? (a.rows()!=b.rows() || a.columns()!=b.columns()) : a.size()!=b.size()))) {
    CALCULATOR->error(true,"Spin-expression addition requires matching matrix or vector dimensions.",NULL);return 0;
   }
   out=a;out+=b;out.eval(eo);return 1;
  }
  if(op=="qhellingerfidelity" || op=="qhellingerdistance") {
   std::vector<MathStructure> weights[2];MathStructure totals[2]={m_zero,m_zero};
   EvaluationOptions numeric=eo;numeric.approximation=APPROXIMATION_APPROXIMATE;
   for(size_t side=0;side<2;++side) {
    const MathStructure &v=args[side];
    if(v.isMatrix()) {
     if(v.rows()!=1 && v.columns()!=1) {CALCULATOR->error(true,"Hellinger measures require aligned vectors, not general matrices.",NULL);return 0;}
     size_t count=v.rows()*v.columns();
     if(count>1024) {CALCULATOR->error(true,"Hellinger vectors support at most 1024 outcomes.",NULL);return 0;}
     for(size_t j=0;j<count;++j)weights[side].push_back(element(v,v.rows()==1 ? 0 : j,v.rows()==1 ? j : 0));
    } else if(v.isVector()) {
     if(v.size()==0 || v.size()>1024) {CALCULATOR->error(true,"Hellinger vectors require 1 to 1024 outcomes.",NULL);return 0;}
     for(size_t j=0;j<v.size();++j)weights[side].push_back(v[j]);
    } else weights[side].push_back(v);
    for(const auto &weight:weights[side]) {
     MathStructure check=weight;check.eval(numeric);
     if(!check.isNumber() || check.number().isComplex() || check.number().isUndefined() || check.number().isInfinite(false) || !check.number().isNonNegative()) {
      CALCULATOR->error(true,"Hellinger weights must be finite nonnegative real numbers.",NULL);return 0;
     }
     Number value=check.number();
     if(value.isInterval() && !value.intervalToPrecision(12)) {CALCULATOR->error(true,"Hellinger weights cannot have broad uncertainty.",NULL);return 0;}
     totals[side]+=weight;
    }
    totals[side].eval(eo);
    MathStructure check=totals[side];check.eval(numeric);
    if(!check.isNumber() || !check.number().isPositive()) {CALCULATOR->error(true,"Each Hellinger distribution must have positive total weight.",NULL);return 0;}
   }
   if(weights[0].size()!=weights[1].size()) {CALCULATOR->error(true,"Hellinger vectors must have the same outcome order and length; pad missing outcomes with zero.",NULL);return 0;}
   out=m_zero;
   for(size_t j=0;j<weights[0].size();++j) {
    if(CALCULATOR->aborted())return 0;
    if(op=="qhellingerdistance") {
     MathStructure left=weights[0][j],right=weights[1][j];left*=totals[1];right*=totals[0];left.eval(eo);right.eval(eo);
     if(left.equals(right))continue;
    }
    MathStructure p=weights[0][j],q=weights[1][j];p/=totals[0];q/=totals[1];
    if(op=="qhellingerdistance" && p.equals(q))continue;
    if(op=="qhellingerfidelity") {p*=q;p.raise(Number(1,2));}
    else {p.raise(Number(1,2));q.raise(Number(1,2));p-=q;p.raise(2);p/=2;}
    p.eval(eo);out+=p;
   }
   out.eval(eo);out.raise(op=="qhellingerfidelity" ? Number(2) : Number(1,2));out.eval(eo);return 1;
  }
  if(op=="qcssgenerators" || op=="qcssstate" || op=="qcssencoder") {
   std::vector<std::vector<unsigned char>> checks[2];
   for(size_t kind=0;kind<2;++kind) {
    if(args[kind].isVector() && args[kind].size()==0)continue;
    if(!binaryMatrix(args[kind],checks[kind]))return 0;
   }
   size_t count=checks[0].size()+checks[1].size();
   if(count==0 || count>32) {CALCULATOR->error(true,"CSS construction requires 1 to 32 total check rows; either X or Z checks may be empty, but not both.",NULL);return 0;}
   size_t n=checks[0].empty() ? checks[1][0].size() : checks[0][0].size();
   if(n<1 || n>9 || (!checks[0].empty() && !checks[1].empty() && checks[1][0].size()!=n)) {CALCULATOR->error(true,"CSS check matrices must have the same 1 to 9 columns, one per qubit.",NULL);return 0;}
   for(const auto &x:checks[0])for(const auto &z:checks[1]) {
    unsigned parity=0;for(size_t j=0;j<n;++j)parity^=x[j]&z[j];
    if(parity) {CALCULATOR->error(true,"CSS checks must satisfy Hx Hz^T = 0 over GF(2), so every X check commutes with every Z check.",NULL);return 0;}
   }
   size_t d=size_t(1)<<n;
   if(op=="qcssstate" || op=="qcssencoder") {
    size_t u=0;
    if(op=="qcssstate") {
     if(!args[2].isNumber() || !args[2].number().isInteger() || args[2].number()<0 || args[2].number()>=Number(d)) {CALCULATOR->error(true,"A CSS coset representative must be an integer basis index from 0 to 2^n-1.",NULL);return 0;}
     u=args[2].number().intValue();
    }
    for(const auto &row:checks[1]) {
     size_t mask=0;for(auto bit:row)mask=(mask<<1)|bit;
     if(binaryParity(u&mask)) {CALCULATOR->error(true,"The CSS coset representative must satisfy every Z parity check.",NULL);return 0;}
    }
    std::vector<size_t> span(1,0);std::vector<bool> present(d,false);present[0]=true;
    for(const auto &row:checks[0]) {
     if(CALCULATOR->aborted())return 0;
     size_t mask=0;for(auto bit:row)mask=(mask<<1)|bit;
     size_t old_size=span.size();for(size_t j=0;j<old_size;++j) {
      size_t word=span[j]^mask;if(!present[word]) {present[word]=true;span.push_back(word);}
     }
    }
    MathStructure amplitude{Number(span.size())};amplitude.raise(Number(-1,2));amplitude.eval(eo);
    if(op=="qcssencoder") {
     std::vector<size_t> logical,closure=span;
     // Canonical quotient basis: greedily extend the X row space using
     // ascending integer words in ker(Hz). Earlier words label lower bits.
     for(size_t candidate=1;candidate<d;++candidate) {
      if(CALCULATOR->aborted())return 0;
      if(present[candidate])continue;
      bool allowed=true;
      for(const auto &row:checks[1]) {
       size_t mask=0;for(auto bit:row)mask=(mask<<1)|bit;
       if(binaryParity(candidate&mask)) {allowed=false;break;}
      }
      if(!allowed)continue;
      logical.push_back(candidate);size_t old_size=closure.size();
      for(size_t j=0;j<old_size;++j) {size_t word=closure[j]^candidate;present[word]=true;closure.push_back(word);}
     }
     size_t columns=size_t(1)<<logical.size();out.clearMatrix();out.resizeMatrix(d,columns,m_zero);
     for(size_t column=0;column<columns;++column) {
      size_t representative=0;for(size_t j=0;j<logical.size();++j)if(column&(size_t(1)<<j))representative^=logical[j];
      for(size_t word:span)element(out,representative^word,column)=amplitude;
     }
     return 1;
    }
    out.clearMatrix();out.resizeMatrix(d,1,m_zero);
    for(size_t word:span)element(out,u^word,0)=amplitude;
    return 1;
   }
   out.clearVector();
   for(size_t kind=0;kind<2;++kind)for(const auto &row:checks[kind]) {
    if(CALCULATOR->aborted())return 0;
    size_t mask=0;for(auto bit:row)mask=(mask<<1)|bit;
    MathStructure generator;generator.clearMatrix();generator.resizeMatrix(d,d,m_zero);
    for(size_t r=0;r<d;++r) {
     if(kind==0)element(generator,r,r^mask)=m_one;
     else element(generator,r,r)=MathStructure(binaryParity(r&mask) ? -1 : 1);
    }
    out.addChild(generator);
   }
   return 1;
  }
  if(op=="qpauliword") {
   for(size_t j=0;j<4;++j)if(!args[j].isNumber() || !args[j].number().isInteger() || args[j].number()<0 || args[j].number()>511) {
    CALCULATOR->error(true,"Invalid binary Pauli word parameters.",NULL);return 0;
   }
   size_t n=a.number().intValue(),x=args[1].number().intValue(),z=args[2].number().intValue();unsigned phase=args[3].number().intValue();
   if(n<1 || n>9 || phase>3 || x>=(size_t(1)<<n) || z>=(size_t(1)<<n)) {CALCULATOR->error(true,"Binary Pauli words require 1 to 9 qubits, bounded bit masks and a phase from 0 to 3.",NULL);return 0;}
   size_t d=size_t(1)<<n;out.clearMatrix();out.resizeMatrix(d,d,m_zero);
   for(size_t r=0;r<d;++r) {
    if(CALCULATOR->aborted())return 0;
    element(out,r,r^x)=MathStructure(pauliPhase(phase+2*binaryParity(r&z)));
   }
   return 1;
  }
  if(op=="qstabilizerprojector" || op=="qstabilizerdimension" || op=="qstabilizersyndrome" || op=="qstabilizerdistance" || op=="qstabilizerparameters" || op=="qstabilizercorrection") {
   std::vector<SignedPauli> generators;size_t rank=0;if(!stabilizerGenerators(a,generators,rank))return 0;
   size_t d=generators[0].d;
   if(op=="qstabilizerdimension") {out=MathStructure((int)(d>>rank));return 1;}
   if(op=="qstabilizercorrection") {
    const MathStructure &syndrome=args[1];std::vector<unsigned> bits;
    if(syndrome.isNumber() && generators.size()==1) {
     if(syndrome.number().equals(0))bits.push_back(0);
     else if(syndrome.number().equals(1))bits.push_back(1);
    } else if(syndrome.isVector() && syndrome.size()==generators.size()) {
     for(size_t j=0;j<syndrome.size();++j) {
      if(!syndrome[j].isNumber())break;
      if(syndrome[j].number().equals(0))bits.push_back(0);
      else if(syndrome[j].number().equals(1))bits.push_back(1);
      else break;
     }
    }
    if(bits.size()!=generators.size()) {CALCULATOR->error(true,"A correction syndrome requires one exact 0 or 1 per generator, in generator order (a scalar for one generator).",NULL);return 0;}
    size_t n=0;while((size_t(1)<<n)<d)++n;
    size_t best=d*d,best_weight=n+1;
    // Ties use increasing x|(z<<n); enumerate all candidates to prove minimum weight.
    for(size_t word=0;word<d*d && best_weight>0;++word) {
     if(CALCULATOR->aborted())return 0;
     size_t x=word&(d-1),z=word>>n,support=x|z,weight=0;
     while(support) {support&=support-1;++weight;}
     if(weight>=best_weight)continue;
     bool matches=true;
     for(size_t j=0;j<generators.size();++j)if(binaryParity((x&generators[j].z)^(z&generators[j].x))!=bits[j]) {matches=false;break;}
     if(matches) {best=word;best_weight=weight;}
    }
    if(best==d*d) {CALCULATOR->error(true,"The syndrome is inconsistent with the stabilizer generators (including redundant or identity checks).",NULL);return 0;}
    size_t x=best&(d-1),z=best>>n,ys=x&z;unsigned phase=0;
    while(ys) {ys&=ys-1;phase+=3;}
    out.clearMatrix();out.resizeMatrix(d,d,m_zero);
    for(size_t r=0;r<d;++r)element(out,r,r^x)=MathStructure(pauliPhase(phase+2*binaryParity(r&z)));
    return 1;
   }
   if(op=="qstabilizerdistance" || op=="qstabilizerparameters") {
    size_t n=0;while((size_t(1)<<n)<d)++n;
    if(rank==n) {CALCULATOR->error(true,"Logical code distance requires at least one encoded qubit (k > 0); stabilizer-state distance conventions are not used.",NULL);return 0;}
    // Ignore phases for membership: any scalar multiple of a stabilizer acts trivially.
    std::vector<size_t> basis(2*n,0);
    for(const auto &p:generators) {
     size_t word=p.x|(p.z<<n);
     for(size_t bit=2*n;bit-->0;)if(word&(size_t(1)<<bit)) {
      if(basis[bit])word^=basis[bit];else {basis[bit]=word;break;}
     }
    }
    size_t distance=n+1;
    for(size_t word=1;word<d*d && distance>1;++word) {
     if(CALCULATOR->aborted())return 0;
     size_t x=word&(d-1),z=word>>n,support=x|z,weight=0;
     while(support) {support&=support-1;++weight;}
     if(weight>=distance)continue;
     bool commutes=true;for(const auto &p:generators)if(binaryParity((x&p.z)^(z&p.x))) {commutes=false;break;}
     if(!commutes)continue;
     size_t remainder=word;
     for(size_t bit=2*n;bit-->0;)if(remainder&(size_t(1)<<bit))remainder^=basis[bit];
     if(remainder)distance=weight;
    }
    if(distance>n)return 0;
    if(op=="qstabilizerdistance")out=MathStructure((int)distance);
    else {out.clearVector();out.addChild(MathStructure((int)n));out.addChild(MathStructure((int)(n-rank)));out.addChild(MathStructure((int)distance));}
    return 1;
   }
   if(op=="qstabilizersyndrome") {
    SignedPauli error;if(!readSignedPauli(args[1],error,false) || error.d!=d) {CALCULATOR->error(true,"The error must be a Pauli matrix on the same qubits as the stabilizers.",NULL);return 0;}
    out.clearVector();for(const auto &p:generators)out.addChild(MathStructure((int)binaryParity((p.x&error.z)^(p.z&error.x))));return 1;
   }
   std::vector<Number> values(d*d);for(size_t r=0;r<d;++r)values[r*d+r]=1;
   for(const auto &p:generators) {
    std::vector<Number> previous=values;
    for(size_t r=0;r<d;++r) {
     if(CALCULATOR->aborted())return 0;
     Number phase=pauliPhase(p.phase+2*binaryParity(r&p.z));
     for(size_t c=0;c<d;++c) {Number term=previous[(r^p.x)*d+c];term*=phase;values[r*d+c]+=term;values[r*d+c]/=2;}
    }
   }
   out.clearMatrix();out.resizeMatrix(d,d,m_zero);for(size_t r=0;r<d;++r)for(size_t c=0;c<d;++c)element(out,r,c)=MathStructure(values[r*d+c]);return 1;
  }
  if(op=="qgf2mul") {
   std::vector<std::vector<unsigned char>> left,right;
   if(!binaryMatrix(a,left) || !binaryMatrix(args[1],right))return 0;
   if(left[0].size()!=right.size()) {CALCULATOR->error(true,"GF(2) matrix multiplication requires matching inner dimensions.",NULL);return 0;}
   out.clearMatrix();out.resizeMatrix(left.size(),right[0].size(),m_zero);
   for(size_t r=0;r<left.size();++r) {
    if(CALCULATOR->aborted())return 0;
    for(size_t c=0;c<right[0].size();++c) {
     unsigned char parity=0;for(size_t k=0;k<right.size();++k)parity^=left[r][k]&right[k][c];
     if(parity)element(out,r,c)=m_one;
    }
   }
   return 1;
  }
  if(op=="qgf2rref" || op=="qgf2rank" || op=="qgf2nullspace" || op=="qgf2inverse" || op=="qlineargate") {
   std::vector<std::vector<unsigned char>> reduced;
   if(!binaryMatrix(a,reduced))return 0;
   size_t rows=reduced.size(),columns=reduced[0].size();
   bool inverse=op=="qgf2inverse",linear=op=="qlineargate";
   if((inverse || linear) && rows!=columns) {CALCULATOR->error(true,"GF(2) inversion and linear gates require square matrices.",NULL);return 0;}
   if(linear && columns>9) {CALCULATOR->error(true,"Linear gates support 1 to 9 qubits.",NULL);return 0;}
   std::vector<std::vector<unsigned char>> original;if(linear)original=reduced;
   size_t width=inverse ? 2*columns : columns;
   if(inverse)for(size_t r=0;r<rows;++r) {reduced[r].resize(width,0);reduced[r][columns+r]=1;}
   std::vector<size_t> pivots;
   for(size_t c=0;c<columns && pivots.size()<rows;++c) {
    if(CALCULATOR->aborted())return 0;
    size_t rank=pivots.size(),selected=rank;
    while(selected<rows && !reduced[selected][c])++selected;
    if(selected==rows)continue;
    std::swap(reduced[rank],reduced[selected]);
    for(size_t r=0;r<rows;++r)if(r!=rank && reduced[r][c])for(size_t k=c;k<width;++k)reduced[r][k]^=reduced[rank][k];
    pivots.push_back(c);
   }
   if(linear) {
    if(pivots.size()!=columns) {CALCULATOR->error(true,"A linear quantum gate requires an invertible binary map.",NULL);return 0;}
    size_t dimension=size_t(1)<<columns;
    out.clearMatrix();out.resizeMatrix(dimension,dimension,m_zero);
    for(size_t x=0;x<dimension;++x) {
     if(CALCULATOR->aborted())return 0;
     size_t y=0;
     for(size_t r=0;r<rows;++r) {
      unsigned char parity=0;for(size_t c=0;c<columns;++c)parity^=original[r][c]&((x>>(columns-1-c))&1);
      y=(y<<1)|parity;
     }
     element(out,y,x)=m_one;
    }
    return 1;
   }
   if(inverse) {
    if(pivots.size()!=columns) {CALCULATOR->error(true,"The matrix is singular over GF(2).",NULL);return 0;}
    out.clearMatrix();out.resizeMatrix(rows,columns,m_zero);
    for(size_t r=0;r<rows;++r)for(size_t c=0;c<columns;++c)if(reduced[r][columns+c])element(out,r,c)=m_one;
    return 1;
   }
   if(op=="qgf2rank") {out=MathStructure((int)pivots.size());return 1;}
   if(op=="qgf2rref") {
    out.clearMatrix();out.resizeMatrix(rows,columns,m_zero);
    for(size_t r=0;r<rows;++r)for(size_t c=0;c<columns;++c)if(reduced[r][c])element(out,r,c)=m_one;
    return 1;
   }
   size_t nullity=columns-pivots.size();
   // No basis vectors means the kernel contains only zero. Qalculate has no
   // zero-column matrix representation, so expose an empty vector in this case.
   if(!nullity) {out.clearVector();return 1;}
   out.clearMatrix();out.resizeMatrix(columns,nullity,m_zero);
   size_t pivotIndex=0,basisColumn=0;
   for(size_t free=0;free<columns;++free) {
    if(pivotIndex<pivots.size() && pivots[pivotIndex]==free) {++pivotIndex;continue;}
    element(out,free,basisColumn)=m_one;
    for(size_t r=0;r<pivots.size();++r)if(reduced[r][free])element(out,pivots[r],basisColumn)=m_one;
    ++basisColumn;
   }
   return 1;
  }
  if(op=="qbits") {
   const MathStructure &width=args[1];
   if(!a.isNumber() || !a.number().isInteger() || a.number().isNegative() || !width.isNumber() || !width.number().isInteger() || width.number()<1 || width.number()>1024) {CALCULATOR->error(true,"bits(value,width) requires a nonnegative integer and a width from 1 to 1024.",NULL);return 0;}
   Number limit(1);limit.shiftLeft(width.number());
   if(a.number()>=limit) {CALCULATOR->error(true,"The integer does not fit in the requested binary width.",NULL);return 0;}
   out.clearVector();
   for(int k=width.number().intValue();k>0;--k)out.addChild(a.number().bitGet(k) ? m_one : m_zero);
   return 1;
  }
  if(op=="qbitdot" || op=="qbitxor" || op=="qbitvalue") {
   std::vector<MathStructure> bits[2];
   for(size_t j=0;j<(op=="qbitvalue" ? 1U : 2U);++j) {
    const MathStructure &value=args[j];
    if(value.isMatrix()) {
     if(value.rows()!=1 && value.columns()!=1) {CALCULATOR->error(true,"Binary bit operations require vectors, not multi-row matrices.",NULL);return 0;}
     if(value.rows()*value.columns()>1024) {CALCULATOR->error(true,"Binary bit operations support at most 1024 bits.",NULL);return 0;}
     for(size_t r=0;r<value.rows();++r)for(size_t c=0;c<value.columns();++c)bits[j].push_back(*value.getElement(r+1,c+1));
    } else if(value.isVector()) {
     if(value.size()>1024) {CALCULATOR->error(true,"Binary bit operations support at most 1024 bits.",NULL);return 0;}
     for(size_t k=0;k<value.size();++k)bits[j].push_back(value[k]);
    } else bits[j].push_back(value);
    if(bits[j].empty()) {CALCULATOR->error(true,"Binary bit operations require nonempty bit vectors.",NULL);return 0;}
    for(const auto &bit:bits[j])if(!bit.isNumber() || (!bit.number().isZero() && !bit.number().isOne())) {CALCULATOR->error(true,"Binary bit operations require each entry to be 0 or 1.",NULL);return 0;}
   }
   if(op=="qbitvalue") {
    Number value(0);
    for(const auto &bit:bits[0]) {value.multiply(2);if(bit.number().isOne())value.add(1);}
    out=MathStructure(value);return 1;
   }
   if(bits[0].size()!=bits[1].size()) {CALCULATOR->error(true,"Binary bit operations require equally long bit vectors.",NULL);return 0;}
   if(op=="qbitxor") {
    out.clearVector();
    for(size_t k=0;k<bits[0].size();++k)out.addChild(bits[0][k].number().isOne()!=bits[1][k].number().isOne() ? m_one : m_zero);
    return 1;
   }
   bool parity=false;
   for(size_t k=0;k<bits[0].size();++k)if(bits[0][k].number().isOne() && bits[1][k].number().isOne())parity=!parity;
   out=parity ? m_one : m_zero;return 1;
  }
  if(op=="qblochsub") {
   size_t n=a.rows(),bits=0;while((size_t(1)<<bits)<n && bits<11)++bits;
   if(!a.isMatrix() || n<2 || n>1024 || n!=(size_t(1)<<bits) || (a.columns()!=1 && a.columns()!=n) || a.rows()*a.columns()>262144 || !args[1].isNumber() || !args[1].number().isInteger() || args[1].number()<0 || args[1].number()>=Number(bits)) {
    CALCULATOR->error(true,"bloch(state,wire) requires a qubit ket/density matrix with at most 262144 entries and a zero-based wire index; wire 0 is leftmost.",NULL);return 0;
   }
   if(!CALCULATOR->getFunction("conj")) {CALCULATOR->error(true,"Load global functions before calculating Bloch coordinates.",NULL);return 0;}
   size_t mask=size_t(1)<<(bits-1-args[1].number().intValue());
   MathStructure reduced;reduced.clearMatrix();reduced.resizeMatrix(2,2,m_zero);
   MathStructure adjoint;if(a.columns()==1)adjoint=dagger(a,eo);
   for(size_t base=0;base<n;++base) {
    if(CALCULATOR->aborted())return 0;
    if(base & mask)continue;
    for(size_t r=0;r<2;++r)for(size_t c=0;c<2;++c) {
     size_t row=base|(r ? mask : 0),column=base|(c ? mask : 0);
     if(a.columns()==1) {MathStructure term=element(a,row,0);term*=element(adjoint,0,column);element(reduced,r,c)+=term;}
     else element(reduced,r,c)+=element(a,row,column);
    }
   }
   reduced.eval(eo);MathStructure parameters;parameters.clearVector();parameters.addChild(reduced);
   QuantumFunction single("qbloch",1);return single.calculate(out,parameters,eo);
  }
  if(op=="qbloch") {
   if(!a.isMatrix() || a.rows()!=2 || (a.columns()!=1 && a.columns()!=2)) {
    CALCULATOR->error(true,"bloch requires a two-component ket or a 2-by-2 density matrix.",NULL);return 0;
   }
   if(!CALCULATOR->getFunction("conj")) {CALCULATOR->error(true,"Load global functions before calculating Bloch coordinates.",NULL);return 0;}
   MathStructure checked;
   if(!quantumEntropy(checked,a,eo))return 0;
   MathStructure rho=a.columns()==1 ? multiply(a,dagger(a,eo),eo) : a;
   MathStructure difference=rho;difference-=dagger(rho,eo);
   if(!rho.isApproximate() && !zeroMatrix(difference,eo)) {CALCULATOR->error(true,"bloch requires a Hermitian density matrix.",NULL);return 0;}
   // Numeric validation above permits rounding-sized Hermiticity residuals.
   // Use the Hermitian part rather than rejecting floating-point states.
   rho+=dagger(rho,eo);rho*=Number(1,2);rho.eval(eo);
   MathStructure weight=trace(rho,eo);
   if(weight.isNumber())weight=weight.number().realPart();
   out.clearMatrix();out.resizeMatrix(3,1,m_zero);
   element(out,0,0)=element(rho,0,1);element(out,0,0)+=element(rho,1,0);
   element(out,1,0)=element(rho,0,1);element(out,1,0)-=element(rho,1,0);
   Number imaginary;imaginary.setImaginaryPart(1);element(out,1,0)*=imaginary;
   element(out,2,0)=element(rho,0,0);element(out,2,0)-=element(rho,1,1);
   out/=weight;out.eval(eo);
   for(size_t k=0;k<3;++k)if(element(out,k,0).isNumber())element(out,k,0)=element(out,k,0).number().realPart();
   return 1;
  }
  if(op=="qthermalrelaxation") {
   Number times[3];EvaluationOptions numeric=eo;numeric.approximation=APPROXIMATION_APPROXIMATE;
   for(size_t k=0;k<3;++k) {
    MathStructure parameter=args[k];parameter.eval(numeric);
    if(!parameter.isNumber() || parameter.number().isComplex() || parameter.number().isUndefined()) {
     CALCULATOR->error(true,"Relaxation times must be real numbers in consistent time units.",NULL);return 0;
    }
    times[k]=parameter.number();
    if((times[k].isInterval() && !times[k].intervalToPrecision(12)) || (k<2 ? !times[k].isPositive() : times[k].isInfinite(false) || times[k]<0)) {
     CALCULATOR->error(true,"T1 and T2 must be positive (or infinity); elapsed time must be finite and nonnegative, without broad uncertainty.",NULL);return 0;
    }
   }
   Number twiceT1=times[0];twiceT1*=2;
   bool invalid=times[1]>twiceT1;
   if(a.isNumber() && args[1].isNumber()) {Number exactTwice=a.number();exactTwice*=2;invalid=invalid || args[1].number()>exactTwice;}
   if(invalid) {CALCULATOR->error(true,"Physical thermal relaxation requires T2 <= 2*T1.",NULL);return 0;}
   if(!noiseParameter(args[3],Number(1),eo))return 0;
   auto decay=[&](size_t index,int multiplier) {
    if(times[index].isPlusInfinity() || args[2].isZero())return MathStructure(1);
    MathStructure exponent=args[2];exponent*=Number(-multiplier);exponent/=args[index];exponent.eval(eo);
    MathStructure result;result.set(CALCULATOR->getFunction("exp"),&exponent,NULL);result.eval(eo);return result;
   };
   if(!CALCULATOR->getFunction("exp")) {CALCULATOR->error(true,"Load global functions before constructing thermal relaxation.",NULL);return 0;}
   MathStructure populationDecay=decay(0,1),coherenceSquared=decay(1,2);
   MathStructure amplitude(1);amplitude-=populationDecay;amplitude.eval(eo);
   MathStructure phase=populationDecay;phase-=coherenceSquared;phase.eval(eo);
   MathStructure parameters;parameters.clearVector();parameters.addChild(amplitude);parameters.addChild(phase);parameters.addChild(args[3]);
   QuantumFunction combined("qcombineddamping",3);return combined.calculate(out,parameters,eo);
  }
  if(op=="qgeneralizeddamping" || op=="qcombineddamping") {
   MathStructure phase=op=="qcombineddamping" ? args[1] : MathStructure(0);
   const MathStructure &population=args[op=="qcombineddamping" ? 2 : 1];
   MathStructure total=a;total+=phase;total.eval(eo);
   if(!noiseParameter(a,Number(1),eo) || !noiseParameter(phase,Number(1),eo) || !noiseParameter(population,Number(1),eo) || !noiseParameter(total,Number(1),eo))return 0;
   auto squareRoot=[&eo](MathStructure value) {value.raise(Number(1,2));value.eval(eo);return value;};
   MathStructure remaining(1);remaining-=total;remaining.eval(eo);
   MathStructure coherence=squareRoot(remaining),relaxation=squareRoot(a),dephasing=squareRoot(phase);
   MathStructure zero;zero.clearMatrix();zero.resizeMatrix(2,2,m_zero);out.clearVector();
   for(size_t excited=0;excited<2;++excited) {
    MathStructure weight=population;
    if(!excited) {weight=1;weight-=population;weight.eval(eo);}
    weight=squareRoot(weight);
    MathStructure k=zero;element(k,excited,excited)=m_one;element(k,1-excited,1-excited)=coherence;
    k*=weight;k.eval(eo);out.addChild(k);
    k=zero;element(k,excited,1-excited)=relaxation;k*=weight;k.eval(eo);out.addChild(k);
    if(op=="qcombineddamping") {
     k=zero;element(k,1-excited,1-excited)=dephasing;k*=weight;k.eval(eo);out.addChild(k);
    }
   }
   return 1;
  }
  if(op=="qamplitudedamping" || op=="qphasedamping" || op=="qdepolarizing") {
   Number upper=op=="qdepolarizing" ? Number(4,3) : Number(1);
   if(!noiseParameter(a,upper,eo))return 0;
   auto squareRoot=[&eo](MathStructure value) {value.raise(Number(1,2));value.eval(eo);return value;};
   MathStructure zero;zero.clearMatrix();zero.resizeMatrix(2,2,m_zero);
   out.clearVector();
   if(op=="qdepolarizing") {
    MathStructure weight=a;weight*=Number(1,4);weight.eval(eo);
    MathStructure identityWeight(1);identityWeight-=weight*Number(3);identityWeight.eval(eo);
    MathStructure k=zero,root=squareRoot(identityWeight);element(k,0,0)=root;element(k,1,1)=root;out.addChild(k);
    root=squareRoot(weight);k=zero;element(k,0,1)=root;element(k,1,0)=root;out.addChild(k);
    Number imaginary;imaginary.setImaginaryPart(1);MathStructure imaginaryRoot=root;imaginaryRoot*=imaginary;imaginaryRoot.eval(eo);
    k=zero;element(k,1,0)=imaginaryRoot;imaginaryRoot*=Number(-1);imaginaryRoot.eval(eo);element(k,0,1)=imaginaryRoot;out.addChild(k);
    k=zero;element(k,0,0)=root;root*=Number(-1);root.eval(eo);element(k,1,1)=root;out.addChild(k);
   } else {
    MathStructure remaining(1);remaining-=a;remaining.eval(eo);
    MathStructure k=zero;element(k,0,0)=m_one;element(k,1,1)=squareRoot(remaining);out.addChild(k);
    k=zero;element(k,op=="qamplitudedamping" ? 0 : 1,1)=squareRoot(a);out.addChild(k);
   }
   return 1;
  }
  if(op=="qlogm")return quantumMatrixLog(out,a,eo) ? 1 : 0;
  if(op=="qpower" || op=="qsqrt") {
   MathStructure exponent=op=="qsqrt" ? MathStructure(Number(1,2)) : args[1];
   if(!a.isMatrix() && a.containsType(STRUCT_VECTOR,true)>0 && !(exponent.isNumber() && exponent.number().isInteger())) {
    CALCULATOR->error(true,"Fractional matrix powers require a resolved square matrix, without broad matrix uncertainty.",NULL);return 0;
   }
   if(a.isMatrix() && exponent.isZero()) {
    if(a.rows()!=a.columns()) {CALCULATOR->error(true,"A zero matrix power requires a square matrix.",NULL);return 0;}
    out.clearMatrix();out.resizeMatrix(a.rows(),a.columns(),m_zero);
    for(size_t k=0;k<a.rows();++k)element(out,k,k)=m_one;
   } else if(a.isMatrix() && !(exponent.isNumber() && exponent.number().isInteger())) {
    return quantumMatrixPower(out,a,exponent,eo) ? 1 : 0;
   } else {out=a;out.raise(exponent);out.eval(eo);}
   return 1;
  }
  if(op=="qschmidt" || op=="qschmidtdim")return quantumSchmidt(out,a,args[1],op=="qschmidtdim" ? &args[2] : NULL,eo) ? 1 : 0;
  if(op=="qschatten" || op=="qtracenorm" || op=="qspectralnorm" || op=="qfrobeniusnorm") {
   MathStructure order=op=="qschatten" ? args[1] : MathStructure(op=="qfrobeniusnorm" ? 2 : 1);
   if(op=="qspectralnorm")order=CALCULATOR->calculate("infinity",eo);
   return quantumSchattenNorm(out,a,order,eo) ? 1 : 0;
  }
  if(op=="qreflection" || op=="qphasereflection") {
   if(!CALCULATOR->getFunction("conj") || !a.isMatrix() || a.columns()!=1 || a.rows()<2 || a.rows()>512) {
    CALCULATOR->error(true,"State reflections require global functions and a nonzero column ket with 2 to 512 amplitudes.",NULL);return 0;
   }
   EvaluationOptions stateNumeric=eo;stateNumeric.approximation=APPROXIMATION_APPROXIMATE;
   for(size_t k=0;k<a.rows();++k) {
    if(CALCULATOR->aborted())return 0;
    MathStructure value=element(a,k,0);value.eval(stateNumeric);
    if(!value.isNumber() || value.number().isUndefined() || value.number().isInfinite(false)) {
     CALCULATOR->error(true,"State reflections require finite numeric amplitudes.",NULL);return 0;
    }
    Number re=value.number().realPart(),im=value.number().imaginaryPart();
    if((re.isInterval() && !re.intervalToPrecision(12)) || (im.isInterval() && !im.intervalToPrecision(12))) {
     CALCULATOR->error(true,"State reflections do not accept broad amplitude uncertainty.",NULL);return 0;
    }
   }
   MathStructure factor(-2);
   if(op=="qphasereflection") {
    EvaluationOptions numeric=eo;numeric.approximation=APPROXIMATION_APPROXIMATE;
    MathStructure angle=args[1];angle.eval(numeric);
    if(!angle.isNumber() || angle.number().isComplex() || angle.number().isUndefined() || angle.number().isInfinite(false)) {
     CALCULATOR->error(true,"A phase reflection requires a finite real angle in radians.",NULL);return 0;
    }
    Number check=angle.number();if(check.isInterval() && !check.intervalToPrecision(12)) {
     CALCULATOR->error(true,"A phase reflection angle cannot have broad uncertainty.",NULL);return 0;
    }
    if(!CALCULATOR->getFunction("cos") || !CALCULATOR->getFunction("sin"))return 0;
    // Euler's form retains familiar exact trigonometric values, including
    // pi/6, instead of leaving fractional powers of -1 in compositions.
    Number imaginary;imaginary.setImaginaryPart(1);
    MathStructure sine(CALCULATOR->getFunction("sin"),&args[1],NULL);sine.eval(eo);sine*=imaginary;
    factor.set(CALCULATOR->getFunction("cos"),&args[1],NULL);factor.eval(eo);factor+=sine;factor-=m_one;factor.eval(eo);
   }
   MathStructure bra=dagger(a,eo),weight=multiply(bra,a,eo);
   if(weight.isZero()) {CALCULATOR->error(true,"Cannot reflect in a zero state.",NULL);return 0;}
   out=multiply(a,bra,eo);out/=weight;out*=factor;out.eval(eo);
   for(size_t k=0;k<a.rows();++k)element(out,k,k)+=m_one;
   out.eval(eo);return 1;
  }
  if(op=="qentropy")return quantumEntropy(out,a,eo) ? 1 : 0;
  if(op=="qnegativity" || op=="qnegativitydim" || op=="qlognegativity" || op=="qlognegativitydim") {
   if(!CALCULATOR->getFunction("conj") || !a.isMatrix() || a.rows()<2 || a.rows()>64 || (a.columns()!=1 && a.columns()!=a.rows())) {
    CALCULATOR->error(true,"Negativity requires global functions and a ket or density matrix of dimension 2 to 64.",NULL);return 0;
   }
   MathStructure validation;if(!quantumEntropy(validation,a,eo))return 0;
   MathStructure rho;
   if(a.columns()==1)rho=multiply(a,dagger(a,eo),eo);
   else {rho=a;rho+=dagger(a,eo);rho/=2;rho.eval(eo);}
   rho/=trace(rho,eo);rho.eval(eo);
   MathStructure transposed;bool dimensions=op=="qnegativitydim" || op=="qlognegativitydim";
   if(dimensions)transposed.set(CALCULATOR->getFunction("qptransposedim"),&rho,&args[1],&args[2],NULL);
   else transposed.set(CALCULATOR->getFunction("qptranspose"),&rho,&args[1],NULL);
   transposed.eval(eo);
   return quantumNegativity(out,transposed,eo,op=="qlognegativity" || op=="qlognegativitydim") ? 1 : 0;
  }
  if(op=="qtracedistance")return quantumTraceDistance(out,a,args[1],eo) ? 1 : 0;
  if(op=="qfidelity")return quantumTraceDistance(out,a,args[1],eo,true) ? 1 : 0;
  if(op=="qrootfidelity") {
   if(!quantumTraceDistance(out,a,args[1],eo,true))return 0;
   Number value;value.setFloat(std::sqrt(out.number().floatValue()));
   value.setApproximate(true);value.setPrecision(12);out=value;return 1;
  }
  if(op=="qentropybase") {
   MathStructure base=args[1];EvaluationOptions numeric=eo;numeric.approximation=APPROXIMATION_APPROXIMATE;base.eval(numeric);
   if(!base.isNumber() || base.number().isComplex() || base.number().isUndefined() || base.number().isInfinite(false) || base.number()<=1) {
    CALCULATOR->error(true,"Entropy logarithm base must be a finite real number greater than one.",NULL);return 0;
   }
   Number logarithm=base.number();
   if((logarithm.isInterval() && !logarithm.intervalToPrecision(12)) || !logarithm.log(Number(2)) || !logarithm.isPositive()) {
    CALCULATOR->error(true,"Entropy logarithm base must have a well-defined positive logarithm without broad uncertainty.",NULL);return 0;
   }
   if(!quantumEntropy(out,a,eo))return 0;
   if(!out.isZero()) {
    out/=logarithm;out.eval(eo);
    if(out.isNumber()) {Number result=out.number();result.intervalToMidValue();result.setApproximate(true);result.setPrecision(12);out=result;}
   }
   return 1;
  }
  if(op=="qpaulivec" || op=="qunpaulivec") {
   size_t d=a.rows();bool inverse=op=="qunpaulivec";
   if(inverse) {d=2;while(d*d<a.rows() && d<16)d*=2;}
   if(!a.isMatrix() || d<2 || d>16 || (d & (d-1)) || (inverse ? a.columns()!=1 || a.rows()!=d*d : a.columns()!=d)) {
    CALCULATOR->error(true,"paulivec requires a square one-to-four-qubit operator; unpaulivec requires a column with 4, 16, 64, or 256 Pauli coordinates.",NULL);return 0;
   }
   std::vector<std::vector<size_t>> locations;std::vector<std::vector<Number>> phases;pauliBasis(d,locations,phases);
   MathStructure scale{Number(d)};scale.raise(Number(1,2));scale.eval(eo);
   out.clearMatrix();out.resizeMatrix(inverse ? d : d*d,inverse ? d : 1,m_zero);
   for(size_t p=0;p<d*d;++p) {
    if(CALCULATOR->aborted())return 0;
    for(size_t c=0;c<d;++c) {
     size_t r=locations[p][c]%d;Number factor=phases[p][c];
     if(!inverse && factor.isComplex())factor.negate();
     MathStructure term=inverse ? element(a,p,0) : element(a,r,c);if(term.isZero())continue;
     term*=factor;
     if(inverse)element(out,r,c)+=term;else element(out,p,0)+=term;
    }
   }
   out/=scale;out.eval(eo);return 1;
  }
  if(op=="qvec") {
   if(!a.isMatrix() || a.rows()*a.columns()>1024) { CALCULATOR->error(true,"vec requires a matrix with at most 1024 entries.",NULL); return 0; }
   out.clearMatrix(); out.resizeMatrix(a.rows()*a.columns(),1,m_zero);
   for(size_t c=0;c<a.columns();++c) for(size_t r=0;r<a.rows();++r) element(out,c*a.rows()+r,0)=element(a,r,c);
   return 1;
  }
  if(op=="qlindblad" || op=="qliouvillian" || op=="qliouvillianclosed") {
   if(!CALCULATOR->getFunction("conj")) {CALCULATOR->error(true,"Load global functions before constructing a Lindblad generator.",NULL);return 0;}
   if(!a.isMatrix() || a.rows()!=a.columns() || a.rows()<2 || a.rows()>16) {
    CALCULATOR->error(true,"Lindblad generators require square operators of dimension 2 to 16.",NULL);return 0;
   }
   if(op=="qlindblad") {out=dissipator(a,eo);return 1;}
   MathStructure difference=a;difference-=dagger(a,eo);
   if(!zeroMatrix(difference,eo)) {CALCULATOR->error(true,"liouvillian requires a Hermitian Hamiltonian.",NULL);return 0;}
   MathStructure identity;identity.setToIdentityMatrix(a.rows());
   out=twoSidedSuperoperator(a,identity,eo);out-=twoSidedSuperoperator(identity,a,eo);
   Number minusI;minusI.setImaginaryPart(-1);out*=minusI;
   if(op=="qliouvillian") {
    const MathStructure &collapses=args[1];
    if(!collapses.isVector() || collapses.size()>256) {CALCULATOR->error(true,"Collapse operators must be a list of at most 256 matrices; use vector(C0,C1,...).",NULL);return 0;}
    for(size_t j=0;j<collapses.size();++j) {
     if(CALCULATOR->aborted())return 0;
     const MathStructure &collapse=collapses[j];
     if(!collapse.isMatrix() || collapse.rows()!=a.rows() || collapse.columns()!=a.columns()) {CALCULATOR->error(true,"Collapse operators must match the Hamiltonian dimensions.",NULL);return 0;}
     out+=dissipator(collapse,eo);
    }
   }
   out.eval(eo);return 1;
  }
  if(op=="qspre" || op=="qspost" || op=="qsprepost") {
   if(!a.isMatrix() || a.rows()>16 || a.columns()>16 || (op!="qsprepost" && a.rows()!=a.columns())) {
    CALCULATOR->error(true,"Left/right superoperators require matrices with at most 16 rows and columns; spre and spost require square matrices.",NULL);return 0;
   }
   MathStructure left=a,right;
   if(op=="qsprepost") {
    right=args[1];
    if(!right.isMatrix() || right.rows()>16 || right.columns()>16) {
     CALCULATOR->error(true,"sprepost requires two matrices with at most 16 rows and columns each.",NULL);return 0;
    }
   } else if(op=="qspre")right.setToIdentityMatrix(a.rows());
   else {right=a;left.setToIdentityMatrix(a.rows());}
   // Column stacking: vec(A X B) = (B^T tensor A) vec(X).
   // This is a transpose, never an adjoint, even for complex B.
   right.transposeMatrix();
   out.set(CALCULATOR->getFunction("qtensor"),&right,&left,NULL);out.eval(eo);return 1;
  }
  if(op=="qunvec") {
   if(!a.isMatrix() || a.columns()!=1 || a.rows()>1024 || !args[1].isNumber() || !args[1].number().isInteger() || args[1].number()<1 || args[1].number()>1024) { CALCULATOR->error(true,"unvec requires a column vector of at most 1024 entries and a positive integer row count.",NULL); return 0; }
   size_t rows=args[1].number().intValue();
   if(a.rows()%rows!=0) { CALCULATOR->error(true,"unvec row count must divide the vector length.",NULL); return 0; }
   size_t columns=a.rows()/rows; out.clearMatrix(); out.resizeMatrix(rows,columns,m_zero);
   for(size_t c=0;c<columns;++c) for(size_t r=0;r<rows;++r) element(out,r,c)=element(a,c*rows+r,0);
   return 1;
  }
  if(op=="qsinhc") {
   if(a.isZero()) { out=1; return 1; }
   if(!a.isNumber() && !a.representsNonZero()) return 0;
   auto function=CALCULATOR->getFunction("sinh"); if(!function) return 0;
   out.set(function,&a,NULL); out/=a; out.eval(eo); return 1;
  }
  if(op=="qexp" || op=="qevolution") {
   MathStructure exponent=a;
   if(op=="qevolution") {
    if(!a.isMatrix() || a.rows()!=a.columns() || args[1].isVector()) { CALCULATOR->error(true,"evolution(H,t) requires a square Hamiltonian and a scalar time (hbar=1).",NULL); return 0; }
    MathStructure difference=a; difference-=dagger(a,eo);
    if(!zeroMatrix(difference,eo) || (args[1].isNumber() && args[1].number().isComplex())) { CALCULATOR->error(true,"evolution requires a Hermitian Hamiltonian and real time; use expm for a general matrix exponential.",NULL); return 0; }
    exponent*=args[1]; Number minusI; minusI.setImaginaryPart(-1); exponent*=minusI; exponent.eval(eo);
   }
   if(exponent.isMatrix()) return quantumMatrixExp(out,exponent,eo) ? 1 : 0;
   if(exponent.isVector()) { CALCULATOR->error(true,"A matrix exponential requires a square matrix.",NULL); return 0; }
   auto function=CALCULATOR->getFunction("exp"); if(!function) return 0;
   out.set(function,&exponent,NULL); out.eval(eo); return 1;
  }
  if(op=="qbasis") {
   const MathStructure &dimension=args[1];
   if(!a.isNumber() || !a.number().isInteger() || a.number()<0 || !dimension.isNumber() || !dimension.number().isInteger() || dimension.number()<2 || dimension.number()>1024 || a.number()>=dimension.number()) {
    CALCULATOR->error(true,"basis(index,dimension) requires an integer dimension from 2 to 1024 and a zero-based index in range.",NULL); return 0;
   }
   out.clearMatrix(); out.resizeMatrix(dimension.number().intValue(),1,m_zero); element(out,a.number().intValue(),0)=m_one; return 1;
  }
  if(op=="qjx" || op=="qjy" || op=="qjz" || op=="qjplus" || op=="qjminus") {
   Number twiceSpin;
   if(a.isNumber()) {twiceSpin=a.number();twiceSpin*=2;}
   if(!a.isNumber() || !twiceSpin.isInteger() || twiceSpin<1 || twiceSpin>63) {
    CALCULATOR->error(true,"Spin operators require integer or half-integer j from 1/2 to 63/2, with hbar=1 and basis m=j,j-1,...,-j.",NULL);return 0;
   }
   int twice=twiceSpin.intValue(), dimension=twice+1;
   out.clearMatrix();out.resizeMatrix(dimension,dimension,m_zero);
   if(op=="qjz") {
    for(int k=0;k<dimension;++k)element(out,k,k)=MathStructure(Number(twice-2*k,2));
   } else {
    for(int k=1;k<dimension;++k) {
     MathStructure value(k*(twice-k+1));value.raise(Number(1,2));
     if(op=="qjx" || op=="qjy")value*=Number(1,2);
     value.eval(eo);
     if(op=="qjy") {
      Number imaginary;imaginary.setImaginaryPart(1);value*=imaginary;value.eval(eo);
      element(out,k,k-1)=value;value*=Number(-1);value.eval(eo);element(out,k-1,k)=value;
     } else {
      if(op!="qjminus")element(out,k-1,k)=value;
      if(op!="qjplus")element(out,k,k-1)=value;
     }
    }
   }
   return 1;
  }
  if(op=="qfdestroy" || op=="qfcreate") {
   const MathStructure &site=args[1];
   if(!a.isNumber() || !a.number().isInteger() || a.number()<1 || a.number()>9 || !site.isNumber() || !site.number().isInteger() || site.number()<0 || site.number()>=a.number()) {
    CALCULATOR->error(true,"Fermionic operators require 1 to 9 modes and an integer site from 0 to modes-1 (leftmost is 0).",NULL);return 0;
   }
   size_t modes=a.number().intValue(), index=site.number().intValue(), dimension=size_t(1)<<modes, bit=size_t(1)<<(modes-1-index);
   out.clearMatrix();out.resizeMatrix(dimension,dimension,m_zero);
   for(size_t column=0;column<dimension;++column) {
    if(CALCULATOR->aborted())return 0;
    bool occupied=(column & bit)!=0;
    if(occupied!=(op=="qfdestroy"))continue;
    size_t prefix=column>>(modes-index);bool odd=false;
    while(prefix) {odd=!odd;prefix&=prefix-1;}
    element(out,column^bit,column)=odd ? MathStructure(-1) : m_one;
   }
   return 1;
  }
  if(op=="qdestroy" || op=="qcreate" || op=="qnumberop") {
   if(!a.isNumber() || !a.number().isInteger() || a.number()<2 || a.number()>512) {
    CALCULATOR->error(true,"Bosonic operators require an integer truncation dimension from 2 to 512.",NULL);return 0;
   }
   size_t dimension=a.number().intValue();out.clearMatrix();out.resizeMatrix(dimension,dimension,m_zero);
   for(size_t k=1;k<dimension;++k) {
    if(CALCULATOR->aborted())return 0;
    MathStructure value((int)k);
    if(op=="qnumberop")element(out,k,k)=value;
    else {
     value.raise(Number(1,2));value.eval(eo);
     element(out,op=="qdestroy" ? k-1 : k,op=="qdestroy" ? k : k-1)=value;
    }
   }
   return 1;
  }
  if(op=="qmodmul") {
   const MathStructure &modulus=args[1];
   if(!a.isNumber() || !a.number().isInteger() || !modulus.isNumber() || !modulus.number().isInteger() || modulus.number()<2 || modulus.number()>512 || a.number()<1 || a.number()>=modulus.number()) {
    CALCULATOR->error(true,"modmul(a,N) requires integer N from 2 to 512 and an integer multiplier 1 <= a < N.",NULL);return 0;
   }
   size_t multiplier=a.number().intValue(), mod=modulus.number().intValue(), u=multiplier, v=mod;
   while(v) {size_t remainder=u%v;u=v;v=remainder;}
   if(u!=1) {CALCULATOR->error(true,"A reversible modular multiplier requires gcd(a,N)=1.",NULL);return 0;}
   size_t dimension=1;while(dimension<mod)dimension*=2;
   out.clearMatrix();out.resizeMatrix(dimension,dimension,m_zero);
   for(size_t x=0;x<dimension;++x) {
    if(CALCULATOR->aborted())return 0;
    element(out,x<mod ? multiplier*x%mod : x,x)=m_one;
   }
   return 1;
  }
  if(op=="qoracle") {
   const MathStructure &bits=args[1];
   if(!a.isVector() || a.isMatrix() || a.size()<2 || a.size()>256 || (a.size() & (a.size()-1)) || !bits.isNumber() || !bits.number().isInteger() || bits.number()<1 || bits.number()>8) {
    CALCULATOR->error(true,"oracle requires a flat truth table of power-of-two length 2 to 256 and an output-qubit count from 1 to 8.",NULL); return 0;
   }
   size_t outputs=size_t(1)<<bits.number().intValue(), n=a.size()*outputs;
   if(n>512) {CALCULATOR->error(true,"Oracle input and output registers together must not exceed 9 qubits.",NULL);return 0;}
   std::vector<size_t> values;
   for(size_t x=0;x<a.size();++x) {
    if(!a[x].isNumber() || !a[x].number().isInteger() || a[x].number()<0 || a[x].number()>=Number(outputs)) {CALCULATOR->error(true,"Oracle table entries must be integer output values from 0 to 2^m-1.",NULL);return 0;}
    values.push_back(a[x].number().intValue());
   }
   out.clearMatrix();out.resizeMatrix(n,n,m_zero);
   for(size_t x=0;x<a.size();++x) {
    if(CALCULATOR->aborted())return 0;
    for(size_t y=0;y<outputs;++y)element(out,x*outputs+(y^values[x]),x*outputs+y)=m_one;
   }
   return 1;
  }
  if(op=="qphaseoracle" || op=="qdiffusion") {
   if(!a.isNumber() || !a.number().isInteger() || a.number()<1 || a.number()>9) {
    CALCULATOR->error(true,"phaseoracle and diffusion require an integer qubit count from 1 to 9.",NULL); return 0;
   }
   size_t n=size_t(1)<<a.number().intValue();
   std::vector<bool> marked(n,false);
   if(op=="qphaseoracle") {
    const MathStructure &indices=args[1]; size_t count=indices.isVector() ? indices.size() : 1;
    if(count==0 || count>n) {CALCULATOR->error(true,"A phase oracle requires 1 to 2^n distinct marked indices.",NULL);return 0;}
    for(size_t k=0;k<count;++k) {
     const MathStructure &index=indices.isVector() ? indices[k] : indices;
     if(!index.isNumber() || !index.number().isInteger() || index.number()<0 || index.number()>=Number(n)) {CALCULATOR->error(true,"Marked indices must be integers from 0 to 2^n-1; the leftmost bit is most significant.",NULL);return 0;}
     size_t value=index.number().intValue();
     if(marked[value]) {CALCULATOR->error(true,"Marked phase-oracle indices must be distinct.",NULL);return 0;}
     marked[value]=true;
    }
   }
   MathStructure entry(2); entry/=Number(n); entry.eval(eo);
   out.clearMatrix(); out.resizeMatrix(n,n,op=="qdiffusion" ? entry : m_zero);
   for(size_t r=0;r<n;++r) {
    if(CALCULATOR->aborted())return 0;
    if(op=="qdiffusion")element(out,r,r)-=m_one;
    else element(out,r,r)=marked[r] ? MathStructure(-1) : m_one;
   }
   return 1;
  }
  if(op=="qsumgate") {
   const MathStructure &target=args[1];
   if(!a.isNumber() || !a.number().isInteger() || a.number()<2 || a.number()>64 || !target.isNumber() || !target.number().isInteger() || target.number()<2 || target.number()>64) {
    CALCULATOR->error(true,"SUM requires one or two integer qudit dimensions from 2 to 64.",NULL); return 0;
   }
   size_t dc=a.number().intValue(), dt=target.number().intValue(), n=dc*dt;
   if(n>512) { CALCULATOR->error(true,"SUM gate dimension product must not exceed 512.",NULL); return 0; }
   out.clearMatrix(); out.resizeMatrix(n,n,m_zero);
   for(size_t control=0;control<dc;++control) {
    if(CALCULATOR->aborted()) return 0;
    for(size_t value=0;value<dt;++value) element(out,control*dt+(value+control)%dt,control*dt+value)=m_one;
   }
   return 1;
  }
  if(op=="qft" || op=="qfourier" || op=="qshift" || op=="qclock") {
   bool qubits=op=="qft";
   if(!a.isNumber() || !a.number().isInteger() || a.number()<(qubits ? 1 : 2) || a.number()>(qubits ? 6 : 64)) { CALCULATOR->error(true,"QFT requires 1 to 6 qubits; shift, clock, and fourier require an integer dimension from 2 to 64.",NULL); return 0; }
   size_t n=qubits ? size_t(1)<<a.number().intValue() : a.number().intValue(); out.clearMatrix(); out.resizeMatrix(n,n,m_zero);
   if(op=="qshift") { for(size_t c=0;c<n;++c) element(out,(c+1)%n,c)=m_one; return 1; }
   if(op=="qclock") {
    for(size_t r=0;r<n;++r) {
     if(CALCULATOR->aborted()) return 0;
     element(out,r,r)=CALCULATOR->calculate("exp(2*pi*i*"+std::to_string(r)+"/"+std::to_string(n)+")",eo);
    } return 1;
   }
   for(size_t r=0;r<n;++r) for(size_t c=0;c<n;++c) {
    if(CALCULATOR->aborted()) return 0;
    element(out,r,c)=CALCULATOR->calculate("exp(2*pi*i*"+std::to_string((r*c)%n)+"/"+std::to_string(n)+")/sqrt("+std::to_string(n)+")",eo);
   } return 1;
  }
  if(op=="qdag") { out=dagger(a,eo); return 1; }
  if(op=="qconj") { out=dagger(a,eo); if(a.isMatrix()) out.transposeMatrix(); return 1; }
  if(op=="qtranspose") { out=a; if(a.isMatrix()) out.transposeMatrix(); else if(a.isVector()) { CALCULATOR->error(true,"Transpose requires a matrix or scalar.",NULL); return 0; } return 1; }
  if(op=="qapply") {
   const MathStructure &state=args[1];
   if(!a.isMatrix() || a.rows()!=a.columns() || !state.isMatrix() || (state.columns()!=1 && state.columns()!=state.rows()) || state.rows()>1024 || state.rows()*state.columns()>262144) { CALCULATOR->error(true,"apply requires a square gate and a column ket or square density matrix (at most 1024 rows and 262144 elements).",NULL); return 0; }
   if(state.columns()!=1 && !CALCULATOR->getFunction("conj")) { CALCULATOR->error(true,"Load global function definitions before applying a gate to a density matrix.",NULL); return 0; }
   size_t n=state.rows(), dim=a.rows(), bits=0, gatebits=0;
   while((size_t(1)<<bits)<n) ++bits;
   while((size_t(1)<<gatebits)<dim) ++gatebits;
   if(n!=(size_t(1)<<bits) || dim!=(size_t(1)<<gatebits) || gatebits>bits) { CALCULATOR->error(true,"apply requires power-of-two gate and state dimensions.",NULL); return 0; }
   std::vector<size_t> targets; size_t mask=0;
   size_t count=args[2].isVector() ? args[2].size() : 1;
   if(count!=gatebits) { CALCULATOR->error(true,"One target index is required for each gate qubit.",NULL); return 0; }
   for(size_t k=0;k<count;++k) {
    const MathStructure &target=args[2].isVector() ? args[2][k] : args[2];
    if(!target.isNumber() || !target.number().isInteger() || target.number()<0 || target.number()>=Number(bits)) { CALCULATOR->error(true,"Target qubit index is out of range (leftmost is 0).",NULL); return 0; }
    size_t bit=size_t(1)<<(bits-1-target.number().intValue());
    if(mask & bit) { CALCULATOR->error(true,"Target qubit indices must be unique.",NULL); return 0; }
    mask|=bit; targets.push_back(bit);
   }
   auto leftApply=[&](const MathStructure &input,MathStructure &output) {
   output.clearMatrix(); output.resizeMatrix(n,input.columns(),m_zero);
   for(size_t j=0;j<n;++j) {
    if(CALCULATOR->aborted()) return 0;
    size_t column=0; for(size_t bit:targets) column=(column<<1) | ((j & bit) ? 1 : 0);
    for(size_t r=0;r<dim;++r) {
     if(element(a,r,column).isZero()) continue;
     size_t index=j & ~mask;
     for(size_t k=0;k<count;++k) if(r & (size_t(1)<<(count-1-k))) index|=targets[k];
     for(size_t c=0;c<input.columns();++c) {
      if(element(input,j,c).isZero()) continue;
      MathStructure term=element(a,r,column); term*=element(input,j,c); element(output,index,c)+=term;
     }
    }
   } return 1;
   };
   if(!leftApply(state,out)) return 0;
   // (U (U rho)-dagger)-dagger = U rho U-dagger. No full-system gate needed.
   if(state.columns()!=1) {
    MathStructure adjoint=dagger(out,eo), second;
    if(!leftApply(adjoint,second)) return 0;
    out=dagger(second,eo);
   }
   return 1;
  }
  if(op=="qsuperop" || op=="qchoi" || op=="qptm" || op=="qchi") {
   if(!CALCULATOR->getFunction("conj")) { CALCULATOR->error(true,"Load global functions before converting a quantum channel.",NULL); return 0; }
   if(!a.isVector() || a.size()==0 || a.size()>256) { CALCULATOR->error(true,"Channel conversion requires a list of 1 to 256 Kraus matrices; use vector(K0,K1,...).",NULL); return 0; }
   std::vector<MathStructure> operators; size_t input=0, output=0;
   for(size_t k=0;k<a.size();++k) {
    MathStructure matrix=a[k];
    if(matrix.isVector() && !matrix.isMatrix()) {
     bool flat=true; for(size_t j=0;j<matrix.size();++j) if(matrix[j].isVector()) flat=false;
     if(flat && matrix.size()>0 && matrix.size()<=32) {
      MathStructure row; row.clearMatrix(); row.resizeMatrix(1,matrix.size(),m_zero);
      for(size_t j=0;j<matrix.size();++j) element(row,0,j)=matrix[j]; matrix=row;
     }
    }
    if(!matrix.isMatrix() || matrix.rows()>32 || matrix.columns()>32 || matrix.rows()*matrix.columns()>512) { CALCULATOR->error(true,"Kraus matrices require at most 32 rows, 32 columns, and 512 entries each.",NULL); return 0; }
    if(k==0) {input=matrix.columns();output=matrix.rows();}
    else if(matrix.rows()!=output || matrix.columns()!=input) { CALCULATOR->error(true,"All Kraus matrices must have matching input and output dimensions.",NULL); return 0; }
    operators.push_back(matrix);
   }
   if((op=="qptm" || op=="qchi") && (input!=output || input<2 || (input & (input-1)))) {
    CALCULATOR->error(true,"Pauli channel representations require square Kraus matrices for one to four qubits.",NULL);return 0;
   }
   bool choiBasis=op=="qchoi" || op=="qchi";
   size_t rows=choiBasis ? input*output : output*output;
   size_t columns=choiBasis ? rows : input*input;
   out.clearMatrix(); out.resizeMatrix(rows,columns,m_zero);
   for(const auto &matrix:operators) {
    MathStructure conjugated=matrix;
    for(size_t r=0;r<output;++r)for(size_t c=0;c<input;++c) {
     MathStructure value=element(matrix,r,c);
     element(conjugated,r,c).set(CALCULATOR->getFunction("conj"),&value,NULL);
     element(conjugated,r,c).eval(eo);
    }
    for(size_t r=0;r<output;++r) {
     if(CALCULATOR->aborted()) return 0;
     for(size_t i=0;i<input;++i) {
      if(element(matrix,r,i).isZero()) continue;
      for(size_t s=0;s<output;++s) for(size_t j=0;j<input;++j) {
       if(element(conjugated,s,j).isZero()) continue;
       MathStructure term=element(matrix,r,i); term*=element(conjugated,s,j);
       size_t row=choiBasis ? r+output*i : r+output*s;
       size_t column=choiBasis ? s+output*j : i+input*j;
       element(out,row,column)+=term;
      }
     }
    }
   }
   if(op=="qptm" || op=="qchi") {
    out.eval(eo);
    // Columns of the unnormalized Pauli change-of-basis matrix have d
    // nonzero entries. Exploit that sparsity instead of multiplying dense
    // d^2-by-d^2 matrices. Basis order is II, IX, IY, IZ, XI, ... .
    size_t d=input, count=d*d;
    std::vector<std::vector<size_t>> locations;std::vector<std::vector<Number>> phases;pauliBasis(d,locations,phases);
    MathStructure transformed;transformed.clearMatrix();transformed.resizeMatrix(count,count,m_zero);
    for(size_t column=0;column<count;++column) {
     if(CALCULATOR->aborted())return 0;
     std::vector<MathStructure> intermediate(count);
     for(size_t r=0;r<count;++r)for(size_t c=0;c<d;++c) {
      const MathStructure &entry=element(out,r,locations[column][c]);if(entry.isZero())continue;
      MathStructure term=entry;term*=phases[column][c];intermediate[r]+=term;
     }
     for(auto &entry:intermediate)entry.eval(eo);
     for(size_t row=0;row<count;++row) {
      MathStructure result;
      for(size_t c=0;c<d;++c) {
       MathStructure term=intermediate[locations[row][c]];if(term.isZero())continue;
       Number factor=phases[row][c];if(factor.isComplex())factor.negate();
       term*=factor;result+=term;
      }
      result/=Number(d);result.eval(eo);element(transformed,row,column)=result;
     }
    }
    out=transformed;
   }
   return 1;
  }
  if(op=="qmul") {
   if(a.isMatrix() && args[1].isMatrix() && a.columns()!=args[1].rows()) { CALCULATOR->error(true,"Quantum matrix dimensions do not match.",NULL); return 0; }
   out=multiply(a,args[1],eo); return 1;
  }
  if(!a.isMatrix()) { CALCULATOR->error(true,"Quantum operation requires a matrix (kets are column matrices).",NULL); return 0; }
  if(op=="qtensorpow") {
   if(!args[1].isNumber() || !args[1].number().isInteger() || args[1].number()<0 || args[1].number()>10) { CALCULATOR->error(true,"Tensor power requires an integer exponent from 0 to 10.",NULL); return 0; }
   int count=args[1].number().intValue(); out.setToIdentityMatrix(1);
   for(int k=0;k<count;++k) {
    MathStructure previous=out; out.set(CALCULATOR->getFunction("qtensor"), &previous, &a, NULL); out.eval(eo);
    // A tensor product of bras simplifies to a flat row vector.
    if(!out.isMatrix() && !out.isVector()) return 0;
   } return 1;
  }
  if(op=="qprobsub") {
   size_t n=a.rows(), bits=0, mask=0;
   while(bits<11 && (size_t(1)<<bits)<n) ++bits;
   if(n<2 || n>1024 || n!=(size_t(1)<<bits)) { CALCULATOR->error(true,"Selected probabilities require a qubit state with 2 to 1024 rows.",NULL); return 0; }
   size_t count=args[1].isVector() ? args[1].size() : 1;
   if(count==0 || count>bits) { CALCULATOR->error(true,"Select between one and all qubits for probabilities.",NULL); return 0; }
   std::vector<size_t> selected;
   for(size_t k=0;k<count;++k) {
    const MathStructure &index=args[1].isVector() ? args[1][k] : args[1];
    if(!index.isNumber() || !index.number().isInteger() || index.number()<0 || index.number()>=Number(bits)) { CALCULATOR->error(true,"Probability indices must be integers in range (leftmost qubit is 0).",NULL); return 0; }
    size_t bit=size_t(1)<<(bits-1-index.number().intValue());
    if(mask & bit) { CALCULATOR->error(true,"Probability indices must be unique.",NULL); return 0; }
    mask|=bit; selected.push_back(bit);
   }
   MathStructure parameters, probabilities; parameters.clearVector(); parameters.addChild(a);
   QuantumFunction full("qprobs",1);
   if(!full.calculate(probabilities,parameters,eo)) return 0;
   out.clearMatrix(); out.resizeMatrix(size_t(1)<<count,1,m_zero);
   for(size_t j=0;j<n;++j) {
    if(CALCULATOR->aborted()) return 0;
    size_t outcome=0; for(size_t bit:selected) outcome=(outcome<<1) | ((j & bit) ? 1 : 0);
    element(out,outcome,0)+=element(probabilities,j,0);
   }
   return 1;
  }
  if(op=="qprobs") {
   bool ket=a.columns()==1;
   if(!ket && a.rows()!=a.columns()) { CALCULATOR->error(true,"probs requires a column ket or a square density matrix.",NULL); return 0; }
   MathStructure norm=ket ? multiply(dagger(a,eo),a,eo) : trace(a,eo);
   if(norm.isZero()) { CALCULATOR->error(true,"A zero-norm/zero-trace state has no normalized measurement distribution.",NULL); return 0; }
   MathStructure bra; if(ket) bra=dagger(a,eo);
   out.clearMatrix(); out.resizeMatrix(a.rows(),1,m_zero);
   for(size_t r=0;r<a.rows();++r) {
    element(out,r,0)=ket ? element(a,r,0) : element(a,r,r);
    if(ket) element(out,r,0)*=element(bra,0,r);
    element(out,r,0)/=norm;
   }
   return 1;
  }
  if(op=="qpurity") {
   bool ket=a.columns()==1;
   if((!ket && a.rows()!=a.columns()) || a.rows()>1024 || a.rows()*a.columns()>262144) { CALCULATOR->error(true,"purity requires a ket or square density matrix, with at most 1024 rows and 262144 elements.",NULL); return 0; }
   if(!CALCULATOR->getFunction("conj")) { CALCULATOR->error(true,"Load global definitions before evaluating state purity.",NULL); return 0; }
   MathStructure normalization=ket ? multiply(dagger(a,eo),a,eo) : trace(a,eo);
   if(normalization.isZero()) { CALCULATOR->error(true,"Purity requires nonzero state norm or trace.",NULL); return 0; }
   if(ket) {out=1; return 1;}
   out.clear();
   for(size_t r=0;r<a.rows();++r) {
    if(CALCULATOR->aborted()) return 0;
    for(size_t c=0;c<a.columns();++c) {MathStructure term=element(a,r,c); term*=element(a,c,r); out+=term;}
   }
   normalization.raise(2); out/=normalization; return 1;
  }
  if(op=="qnorm" || op=="qnormalize") {
   if(a.columns()!=1) { CALCULATOR->error(true,"norm and normalize require a column ket.",NULL); return 0; }
   MathStructure norm=multiply(dagger(a,eo),a,eo);
   if(norm.isZero() && op=="qnormalize") { CALCULATOR->error(true,"Cannot normalize the zero ket.",NULL); return 0; }
   norm.raise(Number(1,2)); norm.eval(eo);
   out= op=="qnorm" ? norm : a; if(op=="qnormalize") out/=norm; return 1;
  }
  if(op=="qexpect" || op=="qborn" || op=="qpostselect" || op=="qvariance") {
   const MathStructure &state=args[1];
   bool ket=state.isMatrix() && state.columns()==1;
   if(!state.isMatrix() || (!ket && state.rows()!=state.columns()) || a.rows()!=a.columns() || a.columns()!=state.rows()) { CALCULATOR->error(true,"Measurement requires a square operator and a compatible ket or density matrix.",NULL); return 0; }
   if(op=="qvariance") {
    if(!CALCULATOR->getFunction("conj")) { CALCULATOR->error(true,"Load global definitions before evaluating variance.",NULL); return 0; }
    MathStructure difference=a; difference-=dagger(a,eo);
    if(!zeroMatrix(difference,eo)) { CALCULATOR->error(true,"variance requires a Hermitian observable.",NULL); return 0; }
    MathStructure normalization=ket ? multiply(dagger(state,eo),state,eo) : trace(state,eo);
    if(normalization.isZero()) { CALCULATOR->error(true,"Variance requires nonzero state norm or trace.",NULL); return 0; }
    MathStructure first=ket ? multiply(dagger(state,eo),multiply(a,state,eo),eo) : trace(multiply(a,state,eo),eo);
    MathStructure square=multiply(a,a,eo);
    out=ket ? multiply(dagger(state,eo),multiply(square,state,eo),eo) : trace(multiply(square,state,eo),eo);
    out/=normalization; first/=normalization; first.raise(2); out-=first; return 1;
   }
   if(op=="qpostselect") {
    MathStructure difference=a; difference-=dagger(a,eo);
    MathStructure squared=multiply(a,a,eo); squared-=a;
    if(!zeroMatrix(difference,eo) || !zeroMatrix(squared,eo)) { CALCULATOR->error(true,"postselect requires a Hermitian projector P with P^2=P.",NULL); return 0; }
    out=multiply(a,state,eo);
    if(!ket) out=multiply(out,a,eo);
    MathStructure probability=ket ? multiply(dagger(out,eo),out,eo) : trace(out,eo);
    if(probability.isZero()) { CALCULATOR->error(true,"Cannot postselect an outcome with zero probability.",NULL); return 0; }
    if(ket) { probability.raise(Number(1,2)); probability.eval(eo); }
    out/=probability; return 1;
   }
   out=ket ? multiply(dagger(state,eo),multiply(a,state,eo),eo) : trace(multiply(a,state,eo),eo);
   if(op=="qborn") {
    MathStructure normalization=ket ? multiply(dagger(state,eo),state,eo) : trace(state,eo);
    if(normalization.isZero()) { CALCULATOR->error(true,"The Born expression requires nonzero norm or trace.",NULL); return 0; }
    out/=normalization;
   }
   return 1;
  }
  if(op=="qreset" || op=="qresetall" || op=="qdephase" || op=="qdephaseall") {
   bool dephase=op=="qdephase" || op=="qdephaseall";
   if(!a.isMatrix() || a.rows()<2 || a.rows()>512 || (a.columns()!=1 && a.columns()!=a.rows())) {
    CALCULATOR->error(true,"Reset and dephasing require a qubit ket or square density matrix with 2 to 512 rows.",NULL); return 0;
   }
   size_t n=a.rows(), bits=0, mask=0; while((size_t(1)<<bits)<n) ++bits;
   if(n!=(size_t(1)<<bits)) { CALCULATOR->error(true,"Reset and dephasing require a power-of-two state dimension.",NULL); return 0; }
   if(op=="qresetall" || op=="qdephaseall") mask=n-1;
   else {
    size_t count=args[1].isVector() ? args[1].size() : 1;
    for(size_t k=0;k<count;++k) {
     const MathStructure &index=args[1].isVector() ? args[1][k] : args[1];
     if(!index.isNumber() || !index.number().isInteger() || index.number()<0 || index.number()>=Number(bits)) {
      CALCULATOR->error(true,"Channel indices must be integers inside the register (leftmost is 0).",NULL); return 0;
     }
     size_t bit=size_t(1)<<(bits-1-index.number().intValue());
     if(mask & bit) { CALCULATOR->error(true,"Channel indices must be unique.",NULL); return 0; } mask|=bit;
    }
   }
   MathStructure state=a;
   if(a.columns()==1) {
    if(!CALCULATOR->getFunction("conj")) { CALCULATOR->error(true,"Load global functions before converting a ket to a density matrix.",NULL); return 0; }
    state=multiply(a,dagger(a,eo),eo);
   }
   out.clearMatrix(); out.resizeMatrix(n,n,m_zero);
   // Retain matching outcome blocks. Reset additionally maps those outcomes to zero.
   for(size_t r=0;r<n;++r) {
    if(CALCULATOR->aborted()) return 0;
    for(size_t c=0;c<n;++c) if((r & mask)==(c & mask)) element(out,dephase ? r : r & ~mask,dephase ? c : c & ~mask)+=element(state,r,c);
   }
   return 1;
  }
  if(op=="qfeedforward") {
   // Sum every measured branch, replacing only the requested outcome by U rho U†.
   QuantumFunction dephase("qdephase",2), apply("qapply",3);
   MathStructure parameters; parameters.clearVector(); parameters.addChild(a); parameters.addChild(args[1]);
   if(!dephase.calculate(out,parameters,eo)) return 0;
   size_t count=args[1].isVector() ? args[1].size() : 1;
   if(!args[2].isNumber() || !args[2].number().isInteger() || args[2].number()<0 || args[2].number()>=Number(size_t(1)<<count)) {
    CALCULATOR->error(true,"Feedforward outcome must be an integer from zero to 2^k-1 for k measured qubits.",NULL); return 0;
   }
   size_t n=out.rows(), bits=0, mask=0, pattern=0, outcome=args[2].number().intValue();
   while((size_t(1)<<bits)<n) ++bits;
   for(size_t k=0;k<count;++k) {
    const MathStructure &index=args[1].isVector() ? args[1][k] : args[1];
    size_t bit=size_t(1)<<(bits-1-index.number().intValue()); mask|=bit;
    if(outcome & (size_t(1)<<(count-1-k))) pattern|=bit;
   }
   MathStructure selected; selected.clearMatrix(); selected.resizeMatrix(n,n,m_zero);
   for(size_t r=0;r<n;++r) {
    if(CALCULATOR->aborted()) return 0;
    if((r & mask)!=pattern) continue;
    for(size_t c=0;c<n;++c) if((c & mask)==pattern) {
     element(selected,r,c)=element(out,r,c); element(out,r,c)=m_zero;
    }
   }
   parameters.clearVector(); parameters.addChild(args[3]); parameters.addChild(selected); parameters.addChild(args[4]);
   MathStructure corrected; if(!apply.calculate(corrected,parameters,eo)) return 0;
   out+=corrected; return 1;
  }
  if(op=="qindexedchannel") {
   if(a.rows()!=a.columns() || a.rows()>512 || !args[1].isVector() || args[1].size()==0 || args[1].size()>256) { CALCULATOR->error(true,"Indexed channel requires a square density matrix of at most 512 rows and 1 to 256 Kraus matrices.",NULL); return 0; }
   QuantumFunction apply("qapply",3);
   out.clearMatrix(); out.resizeMatrix(a.rows(),a.columns(),m_zero);
   for(size_t k=0;k<args[1].size();++k) {
    if(CALCULATOR->aborted()) return 0;
    MathStructure parameters, branch; parameters.clearVector();
    parameters.addChild(args[1][k]); parameters.addChild(a); parameters.addChild(args[2]);
    if(!apply.calculate(branch,parameters,eo)) return 0;
    out+=branch;
   }
   return 1;
  }
  if(op=="qchannel") {
   if(a.rows()!=a.columns() || a.rows()>512 || !args[1].isVector() || args[1].size()==0 || args[1].size()>256) { CALCULATOR->error(true,"channel requires a square density matrix of at most 512 rows and 1 to 256 Kraus matrices.",NULL); return 0; }
   size_t output=0;
   for(size_t k=0;k<args[1].size();++k) {
    if(CALCULATOR->aborted()) return 0;
    MathStructure v=args[1][k];
    if(a.rows()==1 && v.representsScalar()) {
     MathStructure value=v;v.clearMatrix();v.resizeMatrix(1,1,m_zero);element(v,0,0)=value;
    }
    if(v.isVector() && !v.isMatrix() && v.size()==a.rows()) {
     bool flat=true; for(size_t j=0;j<v.size();++j) if(v[j].isVector())flat=false;
     if(flat) {
      MathStructure row;row.clearMatrix();row.resizeMatrix(1,v.size(),m_zero);
      for(size_t j=0;j<v.size();++j)element(row,0,j)=v[j];
      v=row;
     }
    }
    if(!v.isMatrix() || v.columns()!=a.rows() || v.rows()==0 || v.rows()>512 || (k && v.rows()!=output)) { CALCULATOR->error(true,"Kraus matrices must have one column per input dimension and a common output dimension of 1 to 512.",NULL); return 0; }
    if(k==0) {output=v.rows();out.clearMatrix();out.resizeMatrix(output,output,m_zero);}
    MathStructure term=multiply(multiply(v,a,eo),dagger(v,eo),eo);
    if(output==1 && !term.isMatrix())element(out,0,0)+=term;
    else out+=term;
   } return 1;
  }
  if(op=="qdensity") {
   if(a.columns()!=1 || a.rows()>512) { CALCULATOR->error(true,"density requires a column ket with at most 512 entries.",NULL); return 0; }
   out=multiply(a,dagger(a,eo),eo); return 1;
  }
  if(op=="qtrace") {
   if(a.rows()!=a.columns()) { CALCULATOR->error(true,"Trace requires a square matrix.",NULL); return 0; }
   out.clear(); for(size_t r=0;r<a.rows();++r) out+=element(a,r,r); return 1;
  }
  if(op=="qcontrol" || op=="qcontrolpattern") {
   const MathStructure &count=args[1], &state=args[2];
   if(!count.isNumber() || !count.number().isInteger() || count.number()<1 || count.number()>8) {
    CALCULATOR->error(true,"Controlled gates require an integer control count from 1 to 8.",NULL); return 0;
   }
   size_t blocks=size_t(1)<<count.number().intValue(), n=a.rows();
   if(op=="qcontrolpattern" && args[3]!=count) {
    CALCULATOR->error(true,"The control pattern length must equal the number of controls.",NULL);return 0;
   }
   if(n!=a.columns() || n<2 || (n & (n-1)) || n>512/blocks) {
    CALCULATOR->error(true,"Controlled gates require a square qubit operator and at most 512 total dimensions.",NULL); return 0;
   }
   if(!state.isNumber() || !state.number().isInteger() || state.number()<0 || state.number()>=Number(blocks)) {
    CALCULATOR->error(true,"Control state must be an integer from 0 to 2^controls-1; the leftmost control is the most significant bit.",NULL); return 0;
   }
   size_t offset=n*state.number().intValue();
   out.setToIdentityMatrix(n*blocks);
   for(size_t r=0;r<n;++r) for(size_t c=0;c<n;++c) element(out,offset+r,offset+c)=element(a,r,c);
   return 1;
  }
  if(op=="qcontrolled") {
   size_t n=a.rows(); if(n!=a.columns() || n>256) { CALCULATOR->error(true,"Controlled gates require a square matrix of dimension at most 256.",NULL); return 0; }
   out.setToIdentityMatrix(n*2); for(size_t r=0;r<n;++r) for(size_t c=0;c<n;++c) element(out,r+n,c+n)=element(a,r,c); return 1;
  }
  if(op=="qpermute" || op=="qpermutedim") {
   if(!a.isMatrix() || (a.rows()!=1 && a.columns()!=1 && a.rows()!=a.columns()) || a.rows()*a.columns()>262144) {
    CALCULATOR->error(true,"permute requires a ket, bra, or square matrix with at most 262144 elements.",NULL); return 0;
   }
   size_t n=std::max(a.rows(),a.columns());
   if(n>1024) { CALCULATOR->error(true,"Permutation dimension must not exceed 1024.",NULL); return 0; }
   std::vector<size_t> dimensions;
   if(op=="qpermutedim") {
    if(!args[2].isVector() || args[2].size()==0 || args[2].size()>32) { CALCULATOR->error(true,"Permutation dimensions require a list of 1 to 32 factors.",NULL); return 0; }
    size_t product=1;
    for(size_t k=0;k<args[2].size();++k) {
     const MathStructure &d=args[2][k];
     if(!d.isNumber() || !d.number().isInteger() || d.number()<1 || d.number()>1024) { CALCULATOR->error(true,"Subsystem dimensions must be integers from 1 to 1024.",NULL); return 0; }
     size_t dimension=d.number().intValue();
     if(product>1024/dimension) { CALCULATOR->error(true,"Permutation dimension product exceeds 1024.",NULL); return 0; }
     product*=dimension; dimensions.push_back(dimension);
    }
    if(product!=n) { CALCULATOR->error(true,"Permutation dimensions must multiply to the state or operator dimension.",NULL); return 0; }
   } else {
    size_t product=1; while(product<n) {dimensions.push_back(2);product*=2;}
    if(product!=n) { CALCULATOR->error(true,"Non-qubit permutations require explicit subsystem dimensions.",NULL); return 0; }
   }
   const MathStructure &order=args[1];
   if(!order.isVector() || order.size()!=dimensions.size()) { CALCULATOR->error(true,"Permutation order must list every subsystem exactly once.",NULL); return 0; }
   std::vector<size_t> permutation; std::vector<bool> seen(dimensions.size(),false);
   for(size_t k=0;k<order.size();++k) {
    if(!order[k].isNumber() || !order[k].number().isInteger() || order[k].number()<0 || order[k].number()>=Number(dimensions.size())) { CALCULATOR->error(true,"Permutation index is out of range.",NULL); return 0; }
    size_t index=order[k].number().intValue();
    if(seen[index]) { CALCULATOR->error(true,"Permutation indices must be unique.",NULL); return 0; }
    seen[index]=true; permutation.push_back(index);
   }
   std::vector<size_t> mapping(n), digits(dimensions.size());
   for(size_t old=0;old<n;++old) {
    size_t value=old, dest=0;
    for(size_t k=dimensions.size();k>0;--k) {digits[k-1]=value%dimensions[k-1];value/=dimensions[k-1];}
    for(size_t index:permutation) dest=dest*dimensions[index]+digits[index];
    mapping[old]=dest;
   }
   out.clearMatrix(); out.resizeMatrix(a.rows(),a.columns(),m_zero);
   for(size_t r=0;r<a.rows();++r) {
    if(CALCULATOR->aborted()) return 0;
    for(size_t c=0;c<a.columns();++c) element(out,a.rows()==1 ? 0 : mapping[r],a.columns()==1 ? 0 : mapping[c])=element(a,r,c);
   }
   return 1;
  }
  if(op=="qptracedim" || op=="qptransposedim") {
   size_t n=a.rows(); const MathStructure &dims=args[2];
   if(n!=a.columns() || n>512 || !dims.isVector() || dims.size()==0 || dims.size()>32) { CALCULATOR->error(true,"Explicit subsystem dimensions require a square matrix of at most 512 rows and a list of 1 to 32 dimensions.",NULL); return 0; }
   std::vector<size_t> dimensions, strides(dims.size()); size_t total=1;
   for(size_t k=0;k<dims.size();++k) {
    if(!dims[k].isNumber() || !dims[k].number().isInteger() || dims[k].number()<1 || dims[k].number()>512) { CALCULATOR->error(true,"Subsystem dimensions must be integers from 1 to 512.",NULL); return 0; }
    size_t dimension=dims[k].number().intValue();
    if(total>512/dimension) { CALCULATOR->error(true,"Subsystem dimension product exceeds 512.",NULL); return 0; }
    total*=dimension; dimensions.push_back(dimension);
   }
   if(total!=n) { CALCULATOR->error(true,"Subsystem dimension product must equal the matrix dimension.",NULL); return 0; }
   size_t stride=1; for(size_t k=dimensions.size();k>0;--k) {strides[k-1]=stride; stride*=dimensions[k-1];}
   std::vector<bool> selected(dimensions.size(),false);
   size_t count=args[1].isVector() ? args[1].size() : 1;
   for(size_t k=0;k<count;++k) {
    const MathStructure &index=args[1].isVector() ? args[1][k] : args[1];
    if(!index.isNumber() || !index.number().isInteger() || index.number()<0 || index.number()>=Number(dimensions.size())) { CALCULATOR->error(true,"Subsystem index is out of range (leftmost is 0).",NULL); return 0; }
    size_t which=index.number().intValue();
    if(selected[which]) { CALCULATOR->error(true,"Subsystem indices must be unique.",NULL); return 0; }
    selected[which]=true;
   }
   size_t remaining=1; for(size_t k=0;k<dimensions.size();++k) if(!selected[k]) remaining*=dimensions[k];
   std::vector<size_t> kept(n,0), removed(n,0);
   for(size_t j=0;j<n;++j) for(size_t k=0;k<dimensions.size();++k) {
    size_t digit=(j/strides[k])%dimensions[k];
    if(selected[k]) removed[j]+=digit*strides[k]; else kept[j]=kept[j]*dimensions[k]+digit;
   }
   bool transpose=op=="qptransposedim";
   out.clearMatrix(); out.resizeMatrix(transpose ? n : remaining,transpose ? n : remaining,m_zero);
   for(size_t r=0;r<n;++r) {
    if(CALCULATOR->aborted()) return 0;
    for(size_t c=0;c<n;++c) {
     if(transpose) element(out,r-removed[r]+removed[c],c-removed[c]+removed[r])=element(a,r,c);
     else if(removed[r]==removed[c]) element(out,kept[r],kept[c])+=element(a,r,c);
    }
   }
   if(!transpose && remaining==1) { MathStructure scalar=element(out,0,0); out=scalar; }
   return 1;
  }
  if(op=="qptrace" || op=="qptranspose") {
   size_t n=a.rows(), bits=0;
   while((size_t(1)<<bits)<n && bits<11) ++bits;
   if(n!=a.columns() || n!=(size_t(1)<<bits) || bits>10) { CALCULATOR->error(true,"Partial trace/transpose requires a qubit matrix of at most 10 qubits.",NULL); return 0; }
   size_t count=args[1].isVector() ? args[1].size() : 1, mask=0;
   for(size_t k=0;k<count;++k) {
    const MathStructure &index=args[1].isVector() ? args[1][k] : args[1];
    if(!index.isNumber() || !index.number().isInteger() || index.number()<0 || index.number()>=Number(bits)) { CALCULATOR->error(true,"Partial trace indices must be integers in range (leftmost subsystem is 0).",NULL); return 0; }
    size_t bit=size_t(1)<<(bits-1-index.number().intValue());
    if(mask & bit) { CALCULATOR->error(true,"Partial trace subsystem indices must be unique.",NULL); return 0; }
    mask|=bit;
   }
   if(op=="qptranspose") {
    out.clearMatrix(); out.resizeMatrix(n,n,m_zero);
    for(size_t r=0;r<n;++r) {
     if(CALCULATOR->aborted()) return 0;
     for(size_t c=0;c<n;++c) element(out,(r & ~mask)|(c & mask),(c & ~mask)|(r & mask))=element(a,r,c);
    } return 1;
   }
   size_t remaining=n>>count;
   std::vector<size_t> compressed(n,0);
   for(size_t i=0;i<n;++i) for(size_t bit=n>>1;bit;bit>>=1) if(!(bit & mask)) compressed[i]=(compressed[i]<<1) | ((i & bit) ? 1 : 0);
   out.clearMatrix(); out.resizeMatrix(remaining,remaining,m_zero);
   for(size_t r=0;r<n;++r) {
    if(CALCULATOR->aborted()) return 0;
    for(size_t c=0;c<n;++c) if((r & mask)==(c & mask)) element(out,compressed[r],compressed[c])+=element(a,r,c);
   } return 1;
  }
  const MathStructure &b=args[1]; if(!b.isMatrix()) { CALCULATOR->error(true,"Quantum operation requires two matrices.",NULL); return 0; }
  if(op=="qcomm" || op=="qanticomm") {
   if(a.rows()!=a.columns() || b.rows()!=b.columns() || a.rows()!=b.rows()) { CALCULATOR->error(true,"Commutators require square matrices of the same dimension.",NULL); return 0; }
   out=multiply(a,b,eo); auto reverse=multiply(b,a,eo); if(op=="qcomm") out-=reverse; else out+=reverse; return 1;
  }
  size_t rows=op=="qtensor" ? a.rows()*b.rows() : a.rows()+b.rows();
  size_t cols=op=="qtensor" ? a.columns()*b.columns() : a.columns()+b.columns();
  if(rows>1024 || cols>1024 || rows*cols>262144) { CALCULATOR->error(true,"Quantum matrix allocation limit exceeded (262144 elements).",NULL); return 0; }
  out.clearMatrix(); out.resizeMatrix(rows,cols,m_zero);
  for(size_t r=0;r<a.rows();++r) for(size_t c=0;c<a.columns();++c) {
   if(CALCULATOR->aborted()) return 0;
   if(op=="qdirectsum") element(out,r,c)=element(a,r,c);
   else for(size_t j=0;j<b.rows();++j) for(size_t k=0;k<b.columns();++k) { element(out,r*b.rows()+j,c*b.columns()+k)=element(a,r,c); element(out,r*b.rows()+j,c*b.columns()+k)*=element(b,j,k); }
  }
  if(op=="qdirectsum") for(size_t r=0;r<b.rows();++r) for(size_t c=0;c<b.columns();++c) element(out,r+a.rows(),c+a.columns())=element(b,r,c);
  return 1;
 }
};
}
size_t quantumPrefixLength(const std::string &expression) {
 size_t p=expression.compare(0,3,"\xef\xbb\xbf")==0 ? 3 : 0;
 while(size_t length=quantumSpaceLength(expression,p))p+=length;
 return expression.compare(p,8,"quantum:")==0 ? p+8 : 0;
}
// Expand indexed Pauli factors on a shared full register before normal parsing.
// CUDA-Q index zero is the least significant tensor factor.
std::string expandIndexedSpin(const std::string &input,bool &found) {
 struct Factor {size_t begin,end,index;char axis;};std::vector<Factor> factors;size_t width=0;char quote=0;
 for(size_t p=0;p<input.size();) {
  if(input[p]=='"' || input[p]=='\'') {if(quote==input[p])quote=0;else if(!quote)quote=input[p];++p;continue;}
  if(quote) {++p;continue;}
  std::string prefix;
  bool boundary=p==0 || (!std::isalnum((unsigned char)input[p-1]) && input[p-1]!='_' && input[p-1]!='.' && input[p-1]!=':');
  if(boundary)for(const char *candidate:{"cudaq::spin_op::","cudaq::spin::","cudaq.spin.","spin."}) {
   std::string value(candidate);if(input.compare(p,value.size(),value)==0) {prefix=value;break;}
  }
  if(prefix.empty()) {++p;continue;}
  size_t begin=p;p+=prefix.size();
  if(p==input.size() || std::string("ixyz").find(input[p])==std::string::npos)throw std::runtime_error("Indexed spin expressions support i, x, y and z factors.");
  char axis=input[p++];while(p<input.size() && std::isspace((unsigned char)input[p]))++p;
  if(p==input.size() || input[p++]!='(')throw std::runtime_error("A spin factor requires a literal qubit index in parentheses.");
  while(p<input.size() && std::isspace((unsigned char)input[p]))++p;
  size_t start=p,index=0;
  while(p<input.size() && std::isdigit((unsigned char)input[p])) {index=index*10+input[p++]-'0';if(index>8)throw std::runtime_error("Spin expressions support qubit indices 0 to 8.");}
  if(p==start)throw std::runtime_error("Spin indices must be nonnegative integer literals.");
  while(p<input.size() && std::isspace((unsigned char)input[p]))++p;
  if(p==input.size() || input[p++]!=')')throw std::runtime_error("Spin indices must be nonnegative integer literals.");
  factors.push_back({begin,p,index,axis});width=std::max(width,index+1);
 }
 found=!factors.empty();if(!found)return input;
 std::string result;size_t position=0;
 for(const auto &factor:factors) {
  result+=input.substr(position,factor.begin-position);
  std::string label(width,'I');label[width-1-factor.index]=char(std::toupper(factor.axis));
  result+=pauliLabelExpression(label);position=factor.end;
 }
 result+=input.substr(position);return result;
}
std::string translateQuantum(const std::string &expression) {
 if(expression.size()>32768) throw std::runtime_error("Quantum input exceeds 32768 bytes.");
 std::string s=unicodeArithmetic(quantumWhitespace(expression));
 for(const auto &pair : std::map<std::string,std::string>{{"⟪","<<"},{"⟫",">>"},{"⟨","<"},{"⟩",">"},{"∣","|"},{"⊗","@"},{"⊕","#"},{"†","~"},{"−","-"},{"π","pi"},{"σ_x","X"},{"σ_y","Y"},{"σ_z","Z"}}) replaceAll(s,pair.first,pair.second);
 for(const auto &pair : std::map<std::string,std::string>{{"≤","<="},{"≥",">="},{"≼","<="},{"≽",">="},{"⪯","<="},{"⪰",">="},{"≺","<"},{"≻",">"},{"≠","!="},{"∧"," and "},{"∨"," or "},{"¬"," not "},{"⊻"," xor "}})replaceAll(s,pair.first,pair.second);
 s=quantumTeX(s);
 for(const auto &pair : std::map<std::string,std::string>{{"σ_x","X"},{"σ_y","Y"},{"σ_z","Z"}}) replaceAll(s,pair.first,pair.second);
 replaceAll(s,"^{~}","~"); replaceAll(s,"^~","~");
 bool spin=false;s=expandIndexedSpin(unicodePowers(s),spin);
 return Parser(s,spin).run();
}
void registerQuantumFunctions(Calculator &c) {
 for(const auto &signature : quantumSignatures) c.addFunction(new QuantumFunction(signature.first,signature.second));
}
