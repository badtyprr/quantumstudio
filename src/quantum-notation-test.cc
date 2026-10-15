// GPL-2.0-or-later; see COPYING.
#include "QuantumNotation.h"
#include <iostream>
#include <stdexcept>
#include <string>
static unsigned checks=0;
static void equal(const std::string &input,const std::string &expected) {
 auto actual=translateQuantum(input);
 if(actual!=expected)throw std::runtime_error("Translation mismatch: "+input.substr(0,100)+" -> "+actual);
 ++checks;
}
static void rejects(const std::string &input) {
 try{translateQuantum(input);}catch(const std::runtime_error &){++checks;return;}
 throw std::runtime_error("Accepted invalid notation: "+input.substr(0,100));
}
static std::string bits(unsigned value,unsigned width) {
 std::string result(width,'0');for(unsigned k=0;k<width;++k)if(value&(1U<<k))result[width-k-1]='1';return result;
}
static std::string basis(unsigned index,unsigned dimension) {
 std::string result="matrix("+std::to_string(dimension)+",1,[";
 for(unsigned j=0;j<dimension;++j){if(j)result+=',';result+=j==index ? '1' : '0';}
 return result+"])";
}
int main(){try {
 equal("|0⊕a_0>_2","qbasis(qindexxor(0,\"a_0\"),2)");
 equal("|2⊕3>_4 ⊕ |0>","qdirectsum(qbasis(qindexxor(2,3),4),matrix(2,1,[1,0]))");
 equal("1+2*3","(1+qmul(2,3))");
 equal("<0|1>","qmul(qdag(matrix(2,1,[1,0])),matrix(2,1,[0,1]))");
 equal("|0><1|","qadjacent(matrix(2,1,[1,0]),qdag(matrix(2,1,[0,1])))");
 equal("H ⊗ I","qtensor(([1,1;1,-1]/sqrt(2)),[1,0;0,1])");
 equal("X†","qdag([0,1;1,0])");equal("A<=B","qcompare(A,B,2)");
 equal("spin.x(1)","qpauliword(2,2,0,0)");
 equal("[1,0;0,1]","[1,0;0,1]");
 equal("|⟨101|(H⊗H⊗H)|000⟩|^2",translateQuantum("abs(<101|(H@H@H)|000>)^2"));
 equal("|<0|1>|^2","qpower(abs(qmul(qdag(matrix(2,1,[1,0])),matrix(2,1,[0,1]))),2)");
 equal(" | <0|H|0> | ",translateQuantum("abs(<0|H|0>)"));
 equal("|<00|H@H|0>|0>|^2",translateQuantum("abs(<00|H@H|0>|0>)^2"));
 equal("|<0|H|0>|^2+|<1|H|0>|^2",translateQuantum("abs(<0|H|0>)^2+abs(<1|H|0>)^2"));
 equal("|<0|H|0>|^2 > 0",translateQuantum("abs(<0|H|0>)^2 > 0"));
 rejects("|<0|H|0>");rejects("|<0|H|0>| |<1|H|1>");
 for(unsigned width=1;width<=10;++width)for(unsigned trial=0;trial<8;++trial) {
  unsigned dimension=1U<<width,index=(trial*73+width)%dimension,other=(trial*19+3)%dimension;
  std::string label=bits(index,width);
  equal("|"+label+">",basis(index,dimension));
  equal("|"+label+"⟩",basis(index,dimension));
  equal("\\ket{"+label+"}",basis(index,dimension));
  equal("|"+label+"⊕"+bits(other,width)+">",basis(index^other,dimension));
 }
 for(const auto &input:{"","(","|2>","|01⊕1>","spin.x(9)","spin.x(-1)","qbasis(1)","X^^2","[1,2","\\unknown{X}"})rejects(input);
 std::string expanded="1";
 for(unsigned k=0;k<12;++k)expanded="XPowGate("+expanded+")";
 rejects(expanded);
 expanded="1";for(unsigned k=0;k<14;++k)expanded="Rx("+expanded+")";
 rejects(expanded);
 rejects(std::string(32769,' '));
 rejects(std::string(300,'(')+"1"+std::string(300,')'));
 std::string many="1";for(unsigned i=0;i<600;++i)many+="+1";rejects(many);
 for(const auto &prefix:{std::string("quantum:"),std::string(" \tquantum:"),std::string("\xef\xbb\xbf")+"quantum:",std::string("\xc2\xa0")+"quantum:"}) {
  if(quantumPrefixLength(prefix+"X")!=prefix.size())throw std::runtime_error("Incorrect quantum prefix offset");
  ++checks;
 }
 for(const auto &input:{"Quantum:X","xquantum:X","quantum X",""}) {
  if(quantumPrefixLength(input)!=0)throw std::runtime_error("False quantum prefix");
  ++checks;
 }
 std::string nestedSums;
 for(unsigned k=0;k<300;++k)nestedSums+="qtexsum(0,1,k) ";
 rejects(nestedSums+"1");
 std::cout<<"PASS: "<<checks<<" notation checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
