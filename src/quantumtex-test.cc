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
  equal(R"(\sin x)","sin x");
  equal(R"(\cos (x))","cos (x)");
  equal(R"(\sin^{-1}(1/2))","asin(1/2)");
  equal(R"(\sin^{- 1}(1/2))","asin(1/2)");
  equal(R"(\cos^{-\!1}(1/2))","acos(1/2)");
  equal(R"(\tan^{ -\,1 }{1})","atan(1)");
  equal(R"(\cos^{-1}\biggl(1/2\biggr))","acos(1/2)");
  equal(R"(\tan^{-1}{1})","atan(1)");
  equal(R"(\sin^2\left(pi/6\right))","(sin(pi/6))^(2)");
  equal(R"(\cos^{2+2}{x})","(cos(x))^(2+2)");
  equal(R"(\sin^{-2}(x))","(sin(x))^(-2)");
  equal(R"(\arcsin(x)+\arccos(x)+\arctan(x))","asin(x)+acos(x)+atan(x)");
  for(const char *s:{R"(\sin^{}(x))",R"(\sin^2())",R"(\sin^2)",R"(\sin^2 x)",R"(\sin^2(x)"})rejects(s);
  rejects(R"(\{0,\ldots,\ldots\})");
  equal(R"(\{0,\ldots,n-1\})","unique(qindexrange(0,n-1))");
  equal(R"(\{0,\cdots,3\})","unique(qindexrange(0,3))");
  equal(R"(\{0,...,3\})","unique(qindexrange(0,3))");
  rejects(R"(\{0,\ldots\})");
  rejects(R"(\{0,1,\ldots,3\})");

  equal(R"(\{\})","unique(vector())");
  equal(R"(\{"a:b",'c:d'\})",R"(unique(vector("a:b",'c:d')))");
  rejects(R"(\{0,1)");
  rejects(R"(\})");

  equal(R"(\{0,1,0\})","unique(vector(0,1,0))");
  equal(R"(\{k\in\{0,1\}:k>0\})","unique(select(unique(vector(0,1)),k>0,k))");
  equal(R"(\left\{k\in S_0\mid k\geq0\right\})","unique(select(S_0,k>=0,k))");
  rejects(R"(\{k\in S_0:\})");
  rejects(R"(\{k+1\in S_0:k>0\})");
  rejects(R"(\{k\in S_0:k>0:k<2\})");

  rejects(R"(\sum_{k\in\{0,1}{k})");
  rejects(R"(\prod_{k\in\{0,1\}}{k})");
  equal(R"(\sum_{k\in\{0,2,5\}}{k^2})","sumset(k^2,unique(vector(0,2,5)),k)");
  equal(R"(\sum_{k\in S_0} k+1)","qtexsumset( S_0,k) k+1");
  rejects(R"(\sum^{2}_{k\in S_0}{k})");
  rejects(R"(\sum_{k\in}{k})");

  equal(R"(\tilde{\rho})"," ρ_tilde ");
  equal(R"(\widetilde{x})"," x_tilde ");
  equal(R"(\tilde{\rho}_0)"," ρ_tilde_0");
  rejects(R"(\tilde{})");
  rejects(R"(\tilde{x+y})");
  equal(R"(\begin{cases}1 & x=0\\2 & \text{otherwise}\end{cases})","(if(x=0,1,2))");
  equal(R"(\begin{cases}|0> & \text{if $1=1$}\\[1mm]|1> & \text{if }1=0\end{cases})","(if(1=1,|0>,if(1=0,|1>,undefined)))");
  equal(R"(\begin{cases}1 & 1\\\end{cases})","(if(1,1,undefined))");
  rejects(R"(\begin{cases}\end{cases})");
  rejects(R"(\begin{cases}1\end{cases})");
  rejects(R"(\begin{cases}1 & \end{cases})");
  rejects(R"(\begin{cases}1 & 1 & 2\end{cases})");
  rejects(R"(\begin{cases}1 & \text{otherwise}\\2 & 1\end{cases})");
  rejects(R"(\begin{cases}1 & \text{perhaps}\end{cases})");
  rejects(R"(\begin{cases}1 & 1\end{matrix})");
  std::string tooMany=R"(\begin{cases})";
  for(int j=0;j<65;++j)tooMany+=R"(1 & 1\\)";
  rejects(tooMany+R"(\end{cases})");
  rejects(R"(\begin{cases}1 & 1\\\\2 & 0\end{cases})");
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
  equal(R"(\sum_{k=0}^{2} k+1)","qtexsum(0,2,k) k+1");
  equal(R"(\prod^{2}_{k=0}{k})","product(k,0,2,k)");
  equal(R"(\bigotimes_{k=0}^{2}{X})","tensorproduct(X,0,2,k)");
  equal(R"(\bigoplus_{k=0}^{2}{X})","blocksum(X,0,2,k)");
  equal("∑_{k=0}^{2}{k}","sum(k,0,2,k)");
  equal(R"(\begin{pmatrix}1&2\\[1mm]3&4\end{pmatrix})","[1,2;3,4]");
  equal(R"(\begin{bmatrix}1\\[-.5 em]2\\[+2pt]3\end{bmatrix})","[1;2;3]");
  equal(R"(\mathrm{QFT}_{16})"," qfourier(16)");
  equal("QFT₁₆","qfourier(16)");
  equal("myQFT_4","myQFT_4");
  equal("\"QFT_4\"","\"QFT_4\"");
  equal("'QFT₄'","'QFT₄'");
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
      R"(\begin{matrix}1\\[2]2\end{matrix})",
      R"(\begin{matrix}1\\[mm]2\end{matrix})",
      R"(\begin{matrix}1\\[1mm+2]2\end{matrix})",
      R"(\begin{matrix}1\\[1mm2\end{matrix})",
      R"(\begin{matrix}1\\[\foo]2\end{matrix})"})rejects(input);
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
