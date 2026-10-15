// Quantum notation extension. GPL-2.0-or-later; see COPYING.
#include "QuantumNotation.h"
#include "QuantumTeX.h"
#include <stdexcept>
#include <cctype>
#include <cmath>
#include <map>
#include <algorithm>
#include <vector>
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
 if(!dimension && s.find('#')!=std::string::npos) {
  // In a computational basis label, oplus combines equal-width bit strings.
  // Outside labels the same token remains the matrix direct sum.
  std::string bits;size_t start=0;
  while(true) {
   size_t end=s.find('#',start);
   std::string part=s.substr(start,end==std::string::npos ? end : end-start);
   if(part.empty() || part.size()>10 || part.find_first_not_of("01")!=std::string::npos)
    throw std::runtime_error("XOR basis labels require literal binary strings of 1 to 10 bits.");
   if(bits.empty())bits=part;
   else {
    if(bits.size()!=part.size())throw std::runtime_error("XOR basis labels require equal-width binary strings.");
    for(size_t j=0;j<bits.size();++j)bits[j]=bits[j]==part[j] ? '0' : '1';
   }
   if(end==std::string::npos)break;
   start=end+1;
  }
  s=bits;
 }
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
 static void checkSize(const std::string &value) {
  if(value.size()>131072)throw std::runtime_error("Expanded quantum expression exceeds 131072 bytes.");
 }
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
    state=state.empty() ? factor : "qtensor("+state+","+factor+")";checkSize(state);
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
  else if(take('|')) {
   ws();
   if(p<s.size() && s[p]=='<') {
    // A leading bra inside bars denotes the magnitude of a Dirac scalar,
    // e.g. |<a|U|b>|. Its closing bar follows the ket's closing bracket.
    size_t closing=std::string::npos;int nesting=0;
    for(size_t k=p;k<s.size();++k) {
     if(s[k]=='(' || s[k]=='[')++nesting;
     else if(s[k]==')' || s[k]==']') {if(nesting==0)break;--nesting;}
     else if(s[k]=='>' && nesting==0) {
      size_t next=k+1;while(next<s.size() && std::isspace((unsigned char)s[next]))++next;
      if(next<s.size() && s[next]=='|') {closing=next;break;}
     }
    }
    if(closing==std::string::npos)throw std::runtime_error("Unclosed magnitude of a Dirac expression; use |<a|U|b>|.");
    s[closing]=')';std::string value=expression();ws();
    if(p!=closing)throw std::runtime_error("Invalid Dirac expression inside magnitude bars.");
    s[closing]='|';p=closing+1;a="abs("+value+")";
   } else {
    size_t b=p;p=labelEnd('>',p);
    if(p==std::string::npos)throw std::runtime_error("Unclosed ket; use |0> or |0⟩.");
    std::string label=s.substr(b,p-b);++p;
    a=take('>') ? operatorState(label) : basisState(label,dimensionSuffix());kind=1;
   }
  }
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
     if(take(','))population=expression();
     need(')');
     a="qcombineddamping("+amplitude+","+phase+","+population+")";
    } else if(name=="qthermalrelaxation") {
     std::string t1=expression();need(',');std::string t2=expression();need(',');std::string time=expression(),population="0";
     if(take(','))population=expression();
     need(')');
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
     if(take(','))bits=expression();
     need(')');
     a="qoracle("+table+","+bits+")";
    } else if(name=="qsumgate") {
     std::string control=expression(), target=control;
     if(take(',')) target=expression();
     need(')');
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
     if(take(','))beta="("+expression()+")";
     need(')');
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
  --depth;diracKind=kind;checkSize(a);return a;
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
  diracKind=kind;checkSize(a);return a;
 }
 std::string unary() {
  if(++depth>256)throw std::runtime_error("Quantum expression nesting exceeds 256.");
  std::string a;ws();unsigned root=radical();
  if(root) {p+=3;a="qpower("+unary()+",1/"+std::to_string(root)+")";diracKind=0;}
  else if(take('+'))a=unary();
  else if(take('-'))a="(-"+unary()+")";
  else a=power();
  --depth;checkSize(a);return a;
 }
 std::string diracFactor() {
  auto a=unary();int kind=diracKind;
  while(kind) {
   ws();if(p==s.size() || s[p]!=(kind==1 ? '|' : '<'))break;
   auto b=unary();
   if(diracKind==kind)a="qtensor("+a+","+b+")";
   else {a="qmul("+a+","+b+")";kind=0;}
  }
  diracKind=kind;checkSize(a);return a;
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
   checkSize(a);
  } return a;
 }
 std::string additive() {
  auto a=product();
  while(true) {
   if(take('+')) {auto b=product();a=spinContext ? "qspinadd("+a+","+b+")" : "("+a+"+"+b+")";}
   else if(take('-')) {auto b=product();a=spinContext ? "qspinadd("+a+",(-"+b+"))" : "("+a+"-"+b+")";}
   else break;
   checkSize(a);
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
   result=result.empty() ? clause : "("+result+"&&"+clause+")";checkSize(result);left=right;
  }
  return result.empty() ? left : result;
 }
 std::string logicalNot() {
  size_t count=0;
  while(takeWord("not"))if(++count>128)throw std::runtime_error("Too many nested logical negations.");
  std::string result=comparison();
  for(size_t k=0;k<count;++k) {result="!("+result+")";checkSize(result);}
  return result;
 }
 std::string logicalAnd() {
  std::string result=logicalNot();
  while(takeWord("and")) {result="("+result+"&&"+logicalNot()+")";checkSize(result);}
  return result;
 }
 std::string logicalXor() {
  std::string result=logicalAnd();
  while(takeWord("xor")) {result="lxor("+result+","+logicalAnd()+")";checkSize(result);}
  return result;
 }
 std::string expression() {
  std::string result=logicalXor();
  while(takeWord("or")) {result="("+result+"||"+logicalXor()+")";checkSize(result);}
  return result;
 }
 public:
 explicit Parser(std::string text,bool spin=false):spinContext(spin),s(text) {}
 std::string run() { auto out=expression(); ws(); if(p!=s.size()) throw std::runtime_error("Unexpected notation at byte "+std::to_string(p+1)); checkSize(out);return out; }
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
