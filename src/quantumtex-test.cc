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
  equal(R"(\vert{+i}\rangle)","|+i>");
  equal(R"(\langle{-i}\vert)","<-i|");
  equal(R"(\vert{1+2}\vert)","|(1+2)|");
  {
   std::vector<std::string> lines;
   quantumTeX(R"($$\begin{aligned}1&=1\\2&=2\end{aligned}$$)",&lines);
   if(lines!=std::vector<std::string>{"1 =1","2 =2"})throw std::runtime_error("Lost independent alignment metadata");
   ++checks;
   for(const char *input:{R"(2+\begin{aligned}1\\2\end{aligned})",R"((\begin{aligned}1\\2\end{aligned}))",R"(\begin{aligned}1\\2\end{aligned}+\begin{aligned}3\\4\end{aligned})","1+2",""}) {
    quantumTeX(input,&lines);
    if(!lines.empty())throw std::runtime_error("Embedded alignment leaked line metadata");
    ++checks;
   }
  }
  equal(R"(\begin{aligned}1+1&=2\\&=4/2\end{aligned})","(1+1 =2 =4/2)");
  equal(R"(\begin{aligned}1&=1\\2&=3\end{aligned})","vector((1 =1),(2 =3))");
  equal(R"(\begin{aligned}a&=b&c&=d\\&=e&&=f\end{aligned})","vector((a =b =e),(c =d =f))");
  equal(R"(\begin{aligned}[t]1&=1\\[2mm]2&=2\end{aligned})","vector((1 =1),(2 =2))");
  equal(R"(\begin{gathered}1+2\\3+4\end{gathered})","vector((1+2),(3+4))");
  equal(R"(\begin{split}a&=b\\&+c\end{split})","(a =b +c)");
  for(const char *s:{R"(\begin{aligned}\end{aligned})",R"(\begin{aligned}&=2\end{aligned})",R"(\begin{aligned}1&=1\end{gathered})",R"(\begin{gathered}1&=1\end{gathered})",R"(\begin{aligned}[x]1\end{aligned})",R"(\begin{aligned}1&=1\\\\2&=2\end{aligned})"})rejects(s);
  equal(R"(\overline{1+2i})","(conj(1+2i))");
  equal(R"(\overline\beta)","(conj(β))");
  equal(R"(\overline{\overline{1+i}})","(conj((conj(1+i))))");
  equal(R"(\overline{1+i}^2)","(conj(1+i))^2");
  equal(R"(\overline{\begin{pmatrix}1&i\\-i&2\end{pmatrix}})","(conj([1,i;-i,2]))");
  equal(R"(a\overline{b})","a(conj(b))");
  for(const char *s:{R"(\overline{})",R"(\overline)",R"(\overline{1+i)",R"(\ket{\overline{psi}})"})rejects(s);
  equal("|psi_{pi/8}>","|psi_{pi/8}>");
  equal("|psi_{a+b}>","|psi_{a+b}>");
  equal("|psi_a+b>","|psi_a+b>");
  equal(R"(\ket{psi_{a+b}})","|psi_{a+b}>");
  equal("|Phi_{+}>","|Phi_+>");
  rejects("|psi_{}>");
  equal("<0|+A_{i+j}","<0|+A_i+j");
  equal(R"(\ket{\psi_\alpha})","|ψ_α>");
  equal(R"(\braket{psi_{a+b}}{psi_{c+d}})","<psi_{a+b}|psi_{c+d}>");
  equal(R"(\dyad{psi_{a+b}}{psi_{c+d}})","(|psi_{a+b}><psi_{c+d}|)");
  equal(R"(\clubsuit\diamondsuit\heartsuit\spadesuit)","♣♢♡♠");
  equal(R"(\vert\clubsuit\rangle)","|♣>");
  equal(R"(\zeta\eta\iota\kappa\nu\xi\omicron\tau\upsilon)","ζηικνξοτυ");
  equal(R"(\Gamma\Delta\Theta\Lambda\Xi\Pi\Sigma\Upsilon\Omega)","ΓΔΘΛΞΠΣΥΩ");
  equal(R"(\vartheta\varrho\varkappa\varpi\varsigma)","θρκϖς");
  equal(R"(\ket{x}_\alpha)","|x>_(α)");
  equal("<x|_δ","<x|_(δ)");
  equal(R"(x\in S)","x∈ S");
  equal(R"(x\notin S)","x∉ S");
  equal(R"(A\cup B\cap C\setminus D)","A∪ B∩ C∖ D");
  equal("A∪B∩C∖D","A∪ B∩ C∖ D");
  equal(R"(\emptyset)","vector()");
  equal(R"(\varnothing)","vector()");
  equal("∅","vector() ");
  equal("'∪∩∖∅'","'∪∩∖∅'");
  equal(R"(\{0,1\}^{3})","qbitstrings(3)");
  equal(R"(\{1,0\}^{n})","qbitstrings(n)");
  equal(R"(\{0,1,1\}^{2})","qbitstrings(2)");
  rejects(R"(\{0,2\}^{2})");
  rejects(R"(\{0,\ldots,3\}^{2})");
  equal(R"(\Bigl\lfloor\frac{\pi}{4}\sqrt{16}\Bigr\rfloor)","floor(((pi)/(4))sqrt(16))");
  equal(R"(\lfloor-3/2\rfloor^2)","floor(-3/2)^2");
  equal(R"(\lceil\lfloor3/2\rfloor+1/2\rceil)","ceil(floor(3/2)+1/2)");
  equal(R"(\left\lfloor(3/2)\right\rfloor)","floor((3/2))");
  equal("'⌊label⌉'","'⌊label⌉'");
  for(const char *s:{"⌊1⌉","⌈1⌋","⌊⌋","⌈1","1⌉"})rejects(s);
  std::string nestedFloor="1";for(int j=0;j<130;++j)nestedFloor="\\lfloor"+nestedFloor+"\\rfloor";rejects(nestedFloor);
  for(const char *s:{R"(\lfloor\rfloor)",R"(\lceil\rceil)",R"(\lfloor1)",R"(\rfloor)",R"(\rceil)",R"(\lfloor1\rceil)",R"(\lceil1\rfloor)",R"((\lfloor1)\rfloor)",R"(\lfloor(1\rfloor))",R"(\lfloor1\rfloorx)"})rejects(s);
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
  equal("[alpha_0; alpha_1; ⋮; alpha_(n-1)]", "qindexedcolumn(\"alpha_\",(n-1),1)");
  equal("[α_0; ⋮; α_{n-1}]", "qindexedcolumn(\"α_\",(n-1),0)");
  equal(R"(\begin{pmatrix}\alpha_0\\\alpha_1\\\vdots\\\alpha_{n-1}\end{pmatrix})", "qindexedcolumn(\"α_\",(n-1),1)");
  equal(R"(\begin{bmatrix}a_0\\\vdots\\a_3\end{bmatrix})", "qindexedcolumn(\"a_\",(3),0)");
  for(const auto &input:{"[a_1; ⋮; a_n]", "[a_0; a_2; ⋮; a_n]", "[a_0; ⋮; b_n]", "[a_0; ⋮; a_n-1]", "[a_0; ⋮; a_1; a_n]", "[a_0; ⋮; a_(n,2)]",
    R"(\begin{pmatrix}\alpha_0\\\vdots\\\alpha_n-1\end{pmatrix})"})rejects(input);
  equal("[[a_0; ⋮; a_n]]", "[qindexedcolumn(\"a_\",(n),0)]");
  equal("[\"⋮\"]", "[\"⋮\"]");
  equal("[a_0; ⋮; a_(n/2+1)]", "qindexedcolumn(\"a_\",(n/2+1),0)");
  rejects("[ _0; ⋮; a_n]");
  // A rejected call must not affect a subsequent independent translation.
  equal(R"(\ket{1})","|1>");
  std::cout<<"PASS: "<<checks<<" TeX translation and rejection checks\n";
  return 0;
 } catch(const std::exception &error) {
  std::cerr<<error.what()<<'\n';return 1;
 }
}
