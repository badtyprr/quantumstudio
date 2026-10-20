// GPL-2.0-or-later; see COPYING.
#include "QuantumNotation.h"
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include <utility>
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
 for(const std::string &input:{"|x_(n-1) ... x_0>","|x_(n-1) ⋯ x_0>","|x_(n-1) … x_0>"})
  equal(input,translateQuantum("qregisterfamily(\"x_\",n-1,0,vector())"));
 equal("|x_{n-1} ... x_1 x_0>",translateQuantum("qregisterfamily(\"x_\",n-1,0,vector(1,x_1))"));
 for(const std::string &input:{R"(\vert x_{n-1}\cdots x_1 x_0\rangle)",R"(\ket{x_{n-1}\ldots x_1 x_0})",R"(|x_{n-1}\dots x_1 x_0>)"})
  equal(input,translateQuantum("|x_(n-1) ... x_1 x_0>"));
 equal(R"(\bra{x_{n-1}\cdots x_0})",translateQuantum("<x_(n-1) ... x_0|"));
 rejects(R"(x_3\cdots x_0)");
 equal("<x_(n-1) ... x_0|",translateQuantum("qdag(qregisterfamily(\"x_\",n-1,0,vector()))"));
 for(const std::string &input:{"|x_3 ... y_0>","|x_3 ... x_2 x_0>","|x_3 ...>","|... x_0>","|x_3 ... x_1 ... x_0>","|x_3 ... x_0>_2"})rejects(input);
 equal("|GHZ>","(matrix(8,1,[1,0,0,0,0,0,0,1])/sqrt(2))");
 equal("<GHZ|","qdag((matrix(8,1,[1,0,0,0,0,0,0,1])/sqrt(2)))");
 equal("2^Tr(A)","qpower(2,qtrace(A))");
 equal("2^Tr(I)","qpower(2,qtrace([1,0;0,1]))");
 equal("A^T","qtranspose(A)");
 equal("A^T*B","qmul(qtranspose(A),B)");
 equal("|psi_{pi/8}>","qstatecall(\"psi\",(pi/(8)))");
 equal("|psi_(2)>","qnamedket(\"psi_2\")");
 equal("|psi(pi/8)>","qstatecall(\"psi\",(pi/(8)))");
 equal("<psi(0)|psi(1)>","qmul(qdag(qstatecall(\"psi\",0)),qstatecall(\"psi\",1))");
 rejects("|psi()>");equal("|psi(1,2)>","qstatecalls(\"psi\",vector(1,2))");
 const std::string zero=basis(0,2), one=basis(1,2);
 for(const std::string sign:{"+","-"}) {
  equal("0.5*|0><0|"+sign+"0.5*|1><1|",(sign=="+" ? "qadd(" : "qsub(")+std::string("qadjacent(qmul(0.5,")+zero+"),qdag("+zero+")),qadjacent(qmul(0.5,"+one+"),qdag("+one+")))");
 }
 equal("<0|-X|0>","qmul(qmul(qdag("+zero+"),(-[0,1;1,0])),"+zero+")");
 equal("<0|X^*|1>","qmul(qmul(qdag("+zero+"),qconj([0,1;1,0])),"+one+")");
 equal("GHz","qfrequency(\"GHz\")");
 equal("Hz","qfrequency(\"Hz\")");
 equal("'GHz'","'GHz'");
 equal("rad","1");
 equal("deg","(pi/180)");
 equal("'rad'","'rad'");
 equal("\"deg\"","\"deg\"");
 for(const std::string literal:{"'N'","\"high\"","'α'","'π⊗σ_x²'","\"a'⊗b\"","'a\"⊗b'","'a b'"})equal(literal,literal);
 equal("['α';'β']","['α';'β']");
 equal("qfourier('N')","qfourier('N')");
 equal("|'a|b'|","qbars('a|b')");
 rejects("'unfinished");
 rejects("\"unfinished");
 equal("1 <= |x|","qcompare(1,qbars(x),2)");
 equal("1 ≤ |x|","qcompare(1,qbars(x),2)");
 equal("|x| <= 2|y|","qcompare(qbars(x),qadjacent(2,qbars(y)),2)");
 for(const std::string letter:{"α","β","γ","δ","Σ","Π","ρ","ϕ","Ω"})equal(letter,"\""+letter+"\"");
 equal(R"(\alpha\beta)","(\"α\"*\"β\")");
 equal("δ(1)","δ(1)");
 equal("pi","pi");

 equal("θ","\"θ\"");
 equal(R"(\theta)","\"θ\"");
 equal("θ(0)","θ(0)");
 equal(R"(\pi\theta)","(pi*\"θ\")");
 equal("θθ","(\"θ\"*\"θ\")");
 for(const std::string dimension:{"N","n","registerdim","d_0","δ"}) {
  equal("|x>_"+dimension,translateQuantum("|x>_{"+dimension+"}"));
  equal("<x|_"+dimension,translateQuantum("<x|_{"+dimension+"}"));
  equal("|x>_"+dimension+"^2",translateQuantum("|x>_{"+dimension+"}^2"));
  equal("|x>_"+dimension+"†",translateQuantum("|x>_{"+dimension+"}†"));
  equal("<x|_"+dimension+"|y>_"+dimension,translateQuantum("<x|_{"+dimension+"}|y>_{"+dimension+"}"));
 }
 equal(R"(\ket{x}_\alpha)",translateQuantum(R"(\ket{x}_{\alpha})"));
 equal("QFT_N|x>_N",translateQuantum("QFT_N|x>_{N}"));
 equal("|x>_N H",translateQuantum("|x>_{N} H"));
 for(const char *input:{"|x>_","|x>_-N","|x>_2.5","|x>_2N"})rejects(input);

 for(const char *input:{R"(|\{0\}∪|)",R"(|\{0\}∩\{1\})",R"(|\{0\}∪(\{1\}|))"})rejects(input);
 for(const char *input:{"cardinality()","cardinality([1],2)",R"(|\{0,1\})",R"(|\{0,1\}> )"})rejects(input);
 equal(R"(\tilde{\rho})","\"ρ_tilde\"");
 equal(R"(\widetilde{x}_0)","\"x_tilde_0\"");
 equal(R"(\tilde{X})","\"X_tilde\"");
 for(const auto &body:{"X","(density(|0>)-density(|+>))","|0><0|","<0||1>","|0>","(||X||_1)"})
  equal("||"+std::string(body)+"||_1",translateQuantum("norm("+std::string(body)+",1)"));
 equal("||X||_1^2",translateQuantum("norm(X,1)^2"));
 equal("||X||^2_1",translateQuantum("norm(X,1)^2"));
 equal("||X||_{F}",translateQuantum("norm(X,2)"));
 equal("||X||_{infinity}",translateQuantum("norm(X,infinity)"));
 equal("||X||_{3/2}",translateQuantum("norm(X,3/2)"));
 equal("||X||_1+||Y||_1",translateQuantum("norm(X,1)+norm(Y,1)"));
 equal("|||0>||",translateQuantum("norm(|0>)"));
 equal("<0||0>","qadjacent(qdag(matrix(2,1,[1,0])),matrix(2,1,[1,0]))");
 rejects("||X");rejects("||X||_");
 equal("5⊕6","qoplus(5,6)");
 for(const std::string &gate:{"XPowGate","ZPowGate","CZPowGate"}) {
  equal("cirq."+gate+"(exponent=3/10,global_shift=-1/2)",translateQuantum(gate+"(exponent=3/10,global_shift=-1/2)"));
  equal("cirq . "+gate+"()",translateQuantum(gate+"()"));
 }
 for(const auto &input:{"cirq.XPowGate","cirq.Unknown(1)","cirq.XPowGateExtra(1)","othercirq.XPowGate(1)","cirq..XPowGate(1)","cirq.XPowGate(dimension=3)","cirq.XPowGate(exponent=1,exponent=2)"})rejects(input);

 equal("|0⊕a_0>_2","qbasis(qoplus(0,\"a_0\"),2)");
 equal("|2⊕3>_4 ⊕ |0>","qoplus(qbasis(qoplus(2,3),4),matrix(2,1,[1,0]))");
 equal("1+2*3","qadd(1,qmul(2,3))");
 equal("1-2*3","qsub(1,qmul(2,3))");
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
 rejects(std::string(1,'\x1e')+"p_k");
 rejects(std::string(1,'\x1f')+"p_k");
 std::string repeatedIndex="p";for(unsigned k=0;k<129;++k)repeatedIndex+="_k";
 rejects("sum("+repeatedIndex+",0,1,k)");
 rejects(std::string(300,'(')+"1"+std::string(300,')'));
 std::string many="1";for(unsigned i=0;i<600;++i)many+="+1";rejects(many);
 std::string excessiveSequence="sequence([";
 for(unsigned i=0;i<4200;++i){if(i)excessiveSequence+=",";excessiveSequence+="x";}
 rejects(excessiveSequence+"],|0>,x)");
 rejects("sequence(["+std::string(300,'(')+"x"+std::string(300,')')+"],|0>,x)");
 for(const auto &prefix:{std::string("quantum:"),std::string(" \tquantum:"),std::string("\xef\xbb\xbf")+"quantum:",std::string("\xc2\xa0")+"quantum:"}) {
  if(quantumPrefixLength(prefix+"X")!=prefix.size())throw std::runtime_error("Incorrect quantum prefix offset");
  ++checks;
 }
 for(const auto &input:{"Quantum:X","xquantum:X","quantum X",""}) {
  if(quantumPrefixLength(input)!=0)throw std::runtime_error("False quantum prefix");
  ++checks;
 }
 rejects(std::string("1+")+char(0x1c)+"i");
 rejects(std::string("1+")+char(0x1d)+"i");
 rejects(std::string("1+")+char(0x1b)+"i");

 // Compact products bind to the surrounding mathematical sum indices.
 for(const auto &pair:std::vector<std::pair<std::string,std::string>>{
  {R"(\sum_{x=0}^{1}\sum_{y=0}^{1} xy)",R"(\sum_{x=0}^{1}\sum_{y=0}^{1} x*y)"},
  {R"(\sum_{x=0}^{1}{\sum_{y=0}^{1}{xy}})",R"(\sum_{x=0}^{1}{\sum_{y=0}^{1}{x*y}})"},
  {"∑_{x=0}^{1}{∑_{y=0}^{1}{xy}}","∑_{x=0}^{1}{∑_{y=0}^{1}{x*y}}"},
  {R"(\sum_{x=0}^{2}{xxx})",R"(\sum_{x=0}^{2}{x*x*x})"},
  {R"(\sum_{p=0}^{1}{\sum_{i=0}^{1}{pi}})",R"(sum(sum(pi,0,1,i),0,1,p))"},
  {R"(\sum_{i=0}^{2}{ii})",R"(\sum_{i=0}^{2}{i*i})"},
  {R"(\sum_{x=0}^{1}{xy})",R"(sum(xy,0,1,x))"},
  {R"(\sum_{x=0}^{1}{\sum_{y=0}^{1}{"xy"}})",R"(sum(sum("xy",0,1,y),0,1,x))"},
  {R"(\sum_{xy=0}^{2}{xy})",R"(sum(xy,0,2,xy))"},
  {R"(\sum_{x=0}^{1}{xx}+xx)",R"(sum(x*x,0,1,x)+xx)"}
 })equal(pair.first,translateQuantum(pair.second));
 rejects("qtexgroupsum(0,1,x,"+std::string(600,'x')+")");
 equal("qtexgroupsum(0,1,x,"+std::string(600,'x')+"z)",translateQuantum("sum("+std::string(600,'x')+"z,0,1,x)"));
 std::string nestedSums;
 for(unsigned k=0;k<300;++k)nestedSums+="qtexsum(0,1,k) ";
 rejects(nestedSums+"1");
 std::cout<<"PASS: "<<checks<<" notation checks\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
