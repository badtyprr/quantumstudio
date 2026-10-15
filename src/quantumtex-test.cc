// GPL-2.0-or-later; see COPYING.
#include "QuantumTeX.h"
#include <iostream>
#include <stdexcept>
#include <string>

static unsigned checks=0;
static void equal(const std::string &input,const std::string &expected) {
 const auto actual=quantumTeX(input);
 if(actual!=expected)throw std::runtime_error("Unexpected translation of "+input+": "+actual+"; expected "+expected);
 ++checks;
}
static void rejects(const std::string &input) {
 try {quantumTeX(input);}
 catch(const std::runtime_error &) {++checks;return;}
 throw std::runtime_error("Accepted invalid or oversized input: "+input.substr(0,100));
}
int main() {
 try {
  equal("",""); equal(" \n\t",""); equal("x+y","x+y");
  equal(R"(\frac{1}{\sqrt{2}})","((1)/(sqrt(2)))");
  equal(R"(\frac12)","((1)/(2))");
  equal(R"(\sqrt[3]{x})","((x)^(1/(3)))");
  equal(R"(\ket{01})","|01>"); equal(R"(\bra{01})","<01|");
  equal(R"(\braket{0}{1})","<0|1>");
  equal(R"(\braket{0})","<0|0>");
  equal(R"(\ketbra{0}{1})","(|0><1|)");
  equal(R"(\expval{X}{+})","(<+|(X)|+>)");
  equal(R"(\mel{0}{X}{1})","(<0|(X)|1>)");
  equal(R"(\ket{001\oplus 101})","|001# 101>");
  equal(R"(X^{\dagger})","X~");
  equal(R"(X^{\otimes 2})","X^@( 2)");
  equal(R"(A^{T})","A`"); equal(R"(A^{*})","A?");
  equal(R"(\begin{bmatrix}1&0\\0&1\end{bmatrix})","[1,0;0,1]");
  equal(R"(\begin{vmatrix}a&b\\c&d\end{vmatrix})","det([a,b;c,d])");
  equal(R"(\norm{X}_1)","norm(X,1)");
  equal(R"(\norm{X}^{2}_F)","norm(X,2)^(2)");
  equal(R"(\lVert X\rVert_2)","norm( X,2)");
  equal(R"(\sum_{k=0}^{2}{k})","sum(k,0,2,k)");
  equal(R"(\sum_{a_0=0}^{2}{a_0})","sum(a_0,0,2,a_0)");
  equal(R"(\sum_{a_{10}=0}^{2}{a_{10}})","sum(a_10,0,2,a_10)");
  equal(R"(\prod^{2}_{k=0}{k})","product(k,0,2,k)");
  equal(R"(\bigotimes_{k=0}^{2}{X})","tensorproduct(X,0,2,k)");
  equal(R"(\bigoplus_{k=0}^{2}{X})","blocksum(X,0,2,k)");
  equal("∑_{k=0}^{2}{k}","sum(k,0,2,k)");
  equal(R"(\Tr_{1}{X})","ptrace(X,vector(1))");
  equal(R"(\hat{X+Y}^{2})","(X+Y)^(2)");
  equal(R"(\preceq)","<="); equal(R"(\succeq)",">=");
  equal("$x+y$","x+y"); equal("$$x+y$$","x+y");
  equal(R"(\(x+y\))","x+y"); equal(R"(\[x+y\])","x+y");
  for(const auto &input:{R"(\unknown{x})",R"(\)",R"(\frac{1})",R"(\sqrt)",
      "{x", "x}", "(x", "x)", "[x", "x]", "a&b",
      R"(\begin{matrix}1\end{bmatrix})",R"(\begin{matrix}1)",
      R"(\begin{document}x\end{document})",R"(\rVert)",R"(\lVert X)",
      R"(\norm{X}_{})",R"(\begin{Vmatrix}1\end{Vmatrix})",
      R"(\expval{X})",R"(\ket**{0})",R"(\sum_{k=0}{k})",
      R"(\sum_{0}^{2}{k})",R"(\sum_{k=0}_{k=1}{k})",
      R"(\begin{matrix}1\\[2pt]2\end{matrix})"})rejects(input);
  equal(std::string(127,'(')+"x"+std::string(127,')'),std::string(127,'(')+"x"+std::string(127,')'));
  rejects(std::string(128,'(')+"x"+std::string(128,')'));
  equal(std::string(131072,'x'),std::string(131072,'x'));
  rejects(std::string(131073,'x'));
  std::string expansion="0";
  for(unsigned i=0;i<20;++i)expansion="\\ketbra{"+expansion+"}";
  rejects(expansion);
  // A rejected call must not affect a subsequent independent translation.
  equal(R"(\ket{1})","|1>");
  std::cout<<"PASS: "<<checks<<" TeX translation and rejection checks\n";
  return 0;
 } catch(const std::exception &error) {
  std::cerr<<error.what()<<'\n';return 1;
 }
}
