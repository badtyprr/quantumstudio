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
  equal(R"($\Pi_k$)","Π_k");
  equal(R"($\Pi_{k+1}$)","Π_{k+1}");
  equal(R"($\mathsf{X}$)","\"X\"");
  equal(R"($(\mathsf{X},\mathsf{Y})$)","tuple(\"X\",\"Y\")");
  equal(R"(\mathsf{X}\ket{0})",quantumTeX(R"(\mathrm{X}\ket{0})"));
  equal(R"(\operatorname{Pr}(\text{outcome is 1}))","qeventprob(\"measurement probabilities\",1)");
  equal(R"(\operatorname{Pr}(\text{outcome is $0$}))","qeventprob(\"measurement probabilities\",0)");
  equal(R"(\operatorname{Pr}(\text{outcome is $k$}))","qeventprob(\"measurement probabilities\",\"k\")");
  equal(R"(\operatorname{Pr}(\mathsf{X}=0))","qeventprob(\"X\",0)");
  equal(R"($8,9,\ldots,11$)","qindexsequence(8,11)");
  rejects(R"($8,10,\ldots,12$)");
  rejects(R"($8,9,\ldots,7$)");
  equal(R"(\{\mathrm{ready},\mathrm{off}\})","qset(vector(qoutcome(\"ready\"),qoutcome(\"off\")))");
  equal(R"(M_n \,\cdots\, M_1)","qcomposemaps(qindexedentries(\"M_\",1,n,vector()))");
  rejects(R"(M_n \,\cdots\, K_1)");
  equal(R"(\vert\text{heads}\rangle)","|heads>");
  equal(R"(\ket{\text{tails}})","|tails>");
  equal(R"(\langle\text{heads}\vert)","<heads|");
  equal(R"(\{\text{heads},\text{tails}\})","qset(vector(qoutcome(\"heads\"),qoutcome(\"tails\")))");
  rejects(R"(\text{heads})");
  rejects(R"(|\text{and then}\rangle)");
  equal(R"(\mathbb{Z}_N)","qresidues(N)");
  equal(R"(\mathbb{Z}_{21}^{\ast})","qunitsmod(21)");
  equal(R"($5.333 \cdots$)","(5+3/9)");
  equal(R"($-0.777\ldots$)","-(0+7/9)");
  rejects(R"($1.234\cdots$)");
  equal("$$1 +\n  % skip the unused expression {\n2$$",quantumTeX("$$1 +\n\n2$$"));
  equal(R"(\gcd(a,N))","integergcd(a,N)");
  equal(R"($\vert\phi_0\rangle,\ldots,\vert\phi_3\rangle$)",R"(qindexedketlist("φ_",0,3,vector()))");
  equal(R"(\vert 0\rangle,\ldots,\vert N - 1\rangle)","qbasiskets(N)");
  equal(R"(\vert 00\rangle,\ldots,\vert 11\rangle)","qbasiskets(2^2)");
  equal(R"($\{\vert 0\rangle,\ldots,\vert 14\rangle\}$)","qbasisketset((14)+1)");
  equal(R"($\{\vert 0\rangle,\ldots,\vert N-1\rangle\}$)","qbasisketset(N)");
  equal(R"($\{\vert 00\rangle,\ldots,\vert 11\rangle\}$)","qbasisketset(2^2)");
  rejects(R"(\vert 0\rangle,\ldots,\vert 11\rangle)");
  equal(R"(1 + r + r^2 + \cdots + r^{n-1})","qgeometricsum(r,(n-1)+1)");
  rejects(R"(1 + r + s^2 + \cdots + r^{n-1})");
  rejects(R"(1 + r + r^2 + \cdots + s^{n-1})");
  equal("x ∈ {0,1}",quantumTeX(R"(x ∈ \{0,1\})"));
  equal("x ∉ {1/4}",quantumTeX(R"(x ∉ \{1/4\})"));
  rejects("x ∈ {0,1");
  equal(R"($\{\vert\phi_0\rangle,\ldots,\vert\phi_{N-1}\rangle\}$)",R"(qindexedketset("φ_",0,N-1,vector()))");
  equal(R"($\{|a_2>,\ldots,|a_{n + 10}>\}$)",R"(qindexedketset("a_",2,n+10,vector()))");
  equal(R"($\{C_1,C_2,C_3,\ldots\}$)",R"(qindexedfamily("C_",1))");
  equal(R"($\{C_1,C_2,\ldots,\}$)",R"(qindexedfamily("C_",1))");
  equal(R"($\{A_{99},A_{100},\dots\}$)",R"(qindexedfamily("A_",99))");
  rejects(R"($\{C_1,D_2,\ldots\}$)");rejects(R"($\{C_1,C_3,\ldots\}$)");
  equal(R"($2\hspace{1mm}+3$)",quantumTeX("$2 +3$"));
  equal(R"($a\hspace{ -.25 em }b$)",quantumTeX("$a b$"));
  rejects(R"($2\hspace{1mm+9}+3$)");rejects(R"($2\hspace{3cats}+3$)");
  rejects(R"($2\hspace{mm}+3$)");rejects(R"($2\hspace 1mm+3$)");
  equal(R"($N^K\hspace{1mm} (\text{mod }M)$)",quantumTeX("$N^K pmod (M)$"));
  equal(R"($N^K(\text{mod }M+1)$)",quantumTeX("$N^K pmod (M+1)$"));
  rejects(R"($N^K(\text{mod })$)");rejects(R"($N^K(\text{model}M)$)");
  equal(R"($\log_{2}\left(16\right)$)","log2(16)");
  equal(R"($\log_{10}{100}$)","log(100,10)");
  equal(R"($\log_2 16$)","log2(16)");
  equal(R"($\log_2 .5$)","log2(.5)");
  rejects(R"($\log_{}(8)$)");rejects(R"($\log_2()$)");
  equal("$$x.$$","x");equal(R"(\[\ket{0}.\])","|0>");
  equal("$$1.5$$","1.5");equal("$$1.$$","1.");
  equal(R"($$\left\|x\right\|^2.$$)",quantumTeX(R"($$\left\|x\right\|^2$$)"));
  equal("$$x^{2.}$$","x^(2.)");equal("$$x^2.5$$","x^2.5");
  equal(R"($$x=2\tag{1}$$)","x=2");
  equal(R"($$x=2\tag*{A.1}$$)","x=2");
  equal(R"(\begin{aligned}x &= 2\tag{1}\\y &= 3\tag{2}\end{aligned})",
        quantumTeX(R"(\begin{aligned}x &= 2\\y &= 3\end{aligned})"));
  rejects(R"($$x\tag{1}+2$$)");rejects(R"($$x\tag{}$$)");
  rejects(R"($$x\tag{1}\tag{2}$$)");rejects(R"($$\tag{1}$$)");
  equal(R"($s = s_{n-1} \cdots s_0$)",R"(s=qregisterword("s_",(n-1),(0),vector()))");
  rejects(R"($s = s_{n-1} \cdotss_0$)");
  rejects(R"($s = s_{n-1} \cdots t_0$)");
  equal("$$x..$$","x..");equal("$$x+.$$","x+.");
  equal("$$\"x.\"$$","\"x.\"");equal("x.","x.");
  equal(R"(\begin{aligned}x &= y.\end{aligned})",quantumTeX(R"(\begin{aligned}x &= y\end{aligned})"));
  equal("$$x,$$","x");equal("$$1.25,$$","1.25");
  equal(R"(\[\frac{1}{2},\])",quantumTeX(R"(\frac{1}{2})"));
  equal(R"($$\begin{pmatrix}1&2\\3&4\end{pmatrix},$$)",quantumTeX(R"(\begin{pmatrix}1&2\\3&4\end{pmatrix})"));
  equal("$$x+,$$","x+,");equal("$$x,,$$","x,,");equal("x,","x,");
  const std::string hadamardFamily=R"(\bigl(H \vert x_{n-1} \rangle \bigr) \otimes \cdots \otimes \bigl(H \vert x_{0} \rangle \bigr))";
  equal(hadamardFamily,"(tensorpow(H,n)*|x_(n-1) ... x_0>)");
  equal("replace("+hadamardFamily+",n,2)","replace((tensorpow(H,n)*|x_(n-1) ... x_0>),n,2)");
  equal(R"((H \vert b_{m-1}\rangle)\otimes\cdots\otimes(H \vert b_0\rangle))","(tensorpow(H,m)*|b_(m-1) ... b_0>)");
  equal(R"((H \vert x_0\rangle)\otimes\cdots\otimes(H \vert x_0\rangle))","(tensorpow(H,1)*|x_(0) ... x_0>)");
  equal("\""+hadamardFamily+"\"","\""+hadamardFamily+"\"");
  equal(R"((H \vert x_{10}\rangle)\otimes\cdots\otimes(H \vert x_0\rangle))",
        "qtexgrouptensorseries(10,0,qseriesindex,-1,H | x_qseriesindex>)");
  equal(R"((H \vert x_{n+1}\rangle)\otimes\cdots\otimes(H \vert x_0\rangle))",
        "qtexgrouptensorseries(n+1,0,qseriesindex,-1,H | x_qseriesindex>)");
  for(const char *input:{
   R"((H \vert x_{n-1}\rangle)\otimes\cdots\otimes(X \vert x_0\rangle))",
   R"((H \vert x_{n-1}\rangle)\otimes\cdots\otimes(H \vert y_0\rangle))",
   R"((H \vert x_{n-1}\rangle)\otimes\cdots\otimes(H \vert x_1\rangle))",
   R"((H \vertx_{n-1}\rangle)\otimes\cdots\otimes(H \vert x_0\rangle))"
  })rejects(input);
  equal(R"(x_{n-1}y_{n-1} + \cdots + x_0 y_0)","qscalarproductsum(\"x_\",\"y_\",\"n\",vector())");
  equal(R"(replace(u_{m-1}v_{m-1}+\cdots+u_0 v_0,m,2))","replace(qscalarproductsum(\"u_\",\"v_\",\"m\",vector()),m,2)");
  equal(R"(x_0y_0+\cdots+x_0y_0)","qscalarproductsum(\"x_\",\"y_\",1,vector())");
  equal(R"("x_{n-1}y_{n-1} + \cdots + x_0 y_0")",R"("x_{n-1}y_{n-1} + \cdots + x_0 y_0")");
  for(const char *input:{R"(-x_{n-1}y_{n-1}+\cdots+x_0y_0)",R"(x_{n-1}y_{m-1}+\cdots+x_0y_0)",R"(x_{n-1}y_{n-1}+\cdots+x_0z_0)",R"(x_{n-1}y_{n-1}+\cdots+x_0y_0+1)"})rejects(input);
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
  equal(R"(\begin{aligned}a=b & \qquad c=d\\e=f & \qquad g=h\end{aligned})","vector((a=b),(c=d),(e=f),(g=h))");
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
  equal("<0|+A_{i+j}","<0|+A_{i+j}");
  equal("<0|+A_i+j","<0|+A_i+j");
  equal("x_{n-1}","x_{n-1}");
  equal("x_n-1","x_n-1");
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
  equal(R"(\{0,2\}^{2})","qcartesianpower(vector(0,2),2)");
  equal(R"(\{0,\ldots,3\}^{2})","qcartesianpower(qindexrange(0,3),2)");
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
  equal(R"(\{0,\ldots,n-1\})","qindexrange(0,n-1)");
  equal(R"(\{0,\cdots,3\})","qindexrange(0,3)");
  equal(R"(\{0,...,3\})","qindexrange(0,3)");
  rejects(R"(\{0,\ldots\})");
  equal(R"(\{0,1,\ldots,3\})","qindexrange(0,3)");
  rejects(R"(\{0,2,\ldots,3\})");
  rejects(R"(\{8,9,10,\ldots,7\})");

  equal(R"(\{\})","qset(vector())");
  equal(R"(\{"a:b",'c:d'\})",R"(qset(vector("a:b",'c:d')))");
  rejects(R"(\{0,1)");
  rejects(R"(\})");

  equal(R"(\{0,1,0\})","qset(vector(0,1,0))");
  equal(R"(\{k\in\{0,1\}:k>0\})","qsetfilter(k>0,qset(vector(0,1)),k)");
  equal(R"(\left\{k\in S_0\mid k\geq0\right\})","qsetfilter(k>=0,S_0,k)");
  rejects(R"(\{k\in S_0:\})");
  rejects(R"(\{k+1\in S_0:k>0\})");
  rejects(R"(\{k\in S_0:k>0:k<2\})");

  rejects(R"(\sum_{k\in\{0,1}{k})");
  rejects(R"(\prod_{k\in\{0,1\}}{k})");
  equal(R"(\sum_{k\in\{0,2,5\}}{k^2})","qtexgroupsumset(qset(vector(0,2,5)),k,k^2)");
  equal(R"(\sum_{k\in S_0} k+1)","qtexsumset( S_0,k) k+1");
  rejects(R"(\sum^{2}_{k\in S_0}{k})");
  rejects(R"(\sum_{k\in}{k})");

  equal(R"(\tilde{\rho})"," ρ_tilde ");
  equal(R"(\widetilde{x})"," x_tilde ");
  equal(R"(\tilde{\rho}_0)"," ρ_tilde_0");
  rejects(R"(\tilde{})");
  rejects(R"(\tilde{x+y})");
  equal(R"(a=1\text{and}b=2)","a=1 and b=2");
  equal(R"(a=1\text{ or }b=2)","a=1 or b=2");
  rejects(R"(a=1\text{and then}b=2)");
  equal(R"(\begin{cases}1 & x=0\\2 & \text{otherwise}\end{cases})","(if(x=0,1,2))");
  equal(R"(\begin{cases}1 & y=z\\0 & y\neq z,\end{cases})",
        quantumTeX(R"(\begin{cases}1 & y=z\\0 & y\neq z\end{cases})"));
  equal(R"(0.b = \begin{cases}0 & b=0\\1/2 & b=1\end{cases})",
        "(qbitvalue(qbitlabel(b,1))/2)=(if(b=0,0,if(b=1,1/2,undefined)))");
  equal(R"(0.25 = \begin{cases}1 & x=0\end{cases})","0.25 = (if(x=0,1,undefined))");
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
  equal(R"(\sum_{a,b=0}^{2}{a+b})","qtexgroupsum(0,2,[a,b],a+b)");
  equal(R"(\sum_{a,b\in S} ab+1)","qtexsumset( S,[a,b]) ab+1");
  rejects(R"(\sum_{a,a=0}^{2}{a})");
  rejects(R"(\sum_{a,,b=0}^{2}{b})");
  equal(R"(\sum_{a,b=0}^{a}{b})","qtexgroupsum(0,a,[a,b],b)");
  equal(R"(\sum_{k=0}^{2}{k})","qtexgroupsum(0,2,k,k)");
  equal(R"(\sum_{a_0=0}^{2}{a_0})","qtexgroupsum(0,2,a_0,a_0)");
  equal(R"(\sum_{a_{10}=0}^{2}{a_{10}})","qtexgroupsum(0,2,a_10,a_10)");
  equal(R"(\sum_{k=0}^{2} k+1)","qtexsum(0,2,k) k+1");
  equal(R"(\prod^{2}_{k=0}{k})","qtexgroupprod(0,2,k,k)");
  equal(R"(\bigotimes_{k=0}^{2}{X})","qtexgroupbigotimes(0,2,k,X)");
  equal(R"(\bigoplus_{k=0}^{2}{X})","qtexgroupbigoplus(0,2,k,X)");
  equal("∑_{k=0}^{2}{k}","qtexgroupsum(0,2,k,k)");
  equal(R"(\begin{pmatrix}1&2\\3&4\\[2mm]\end{pmatrix})","[1,2;3,4]");
  equal(R"(\begin{bmatrix}a_0\\\vdots\\a_n\\\end{bmatrix})",quantumTeX(R"(\begin{bmatrix}a_0\\\vdots\\a_n\end{bmatrix})"));
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
  equal(R"(\begin{pmatrix}s_{n-1}\\\vdots\\s_0\end{pmatrix})", "qdescendingcolumn(\"s_\",(n-1),0)");
  equal("[s_5; ⋮; s_2; s_1; s_0]", "qdescendingcolumn(\"s_\",(5),2)");
  for(const auto &bad:{"[s_5; ⋮; s_2; s_0]","[s_5; ⋮; s_1; t_0]","[s_5; ⋮; ⋮; s_0]"})rejects(bad);
  equal("[alpha_0; alpha_1; ⋮; alpha_(n-1)]", "qindexedcolumn(\"alpha_\",(n-1),1)");
  equal("[α_0; ⋮; α_{n-1}]", "qindexedcolumn(\"α_\",(n-1),0)");
  equal(R"(\begin{pmatrix}\alpha_0\\\alpha_1\\\vdots\\\alpha_{n-1}\end{pmatrix})", "qindexedcolumn(\"α_\",(n-1),1)");
  equal(R"(\begin{bmatrix}a_0\\\vdots\\a_3\end{bmatrix})", "qindexedcolumn(\"a_\",(3),0)");
  equal("[a_1; ⋮; a_n]", "qonebasedcolumn(\"a_\",(n),1)");
  for(const auto &input:{"[a_2; ⋮; a_n]", "[a_0; a_2; ⋮; a_n]", "[a_0; ⋮; b_n]", "[a_0; ⋮; a_n-1]", "[a_0; ⋮; a_1; a_n]", "[a_0; ⋮; a_(n,2)]",
    R"(\begin{pmatrix}\alpha_0\\\vdots\\\alpha_n-1\end{pmatrix})"})rejects(input);
  equal("[[a_0; ⋮; a_n]]", "[qindexedcolumn(\"a_\",(n),0)]");
  equal("[\"⋮\"]", "[\"⋮\"]");
  equal("[a_0; ⋮; a_(n/2+1)]", "qindexedcolumn(\"a_\",(n/2+1),0)");
  rejects("[ _0; ⋮; a_n]");
  equal(R"(\begin{pmatrix}\alpha_0\\[1.5mm]\alpha_1\\[-.5 em]\vdots\\[+2pt]\alpha_{n-1}\end{pmatrix})", "qindexedcolumn(\"α_\",(n-1),1)");
  rejects(R"(\begin{pmatrix}a_0\\[n mm]\vdots\\a_n\end{pmatrix})");
  equal("[a_(0,0), ⋯, a_(0,n-1); ⋮, ⋱, ⋮; a_(m-1,0), ⋯, a_(m-1,n-1)]", "qindexedmatrix(\"a_\",(m-1),(n-1),0,0)");
  equal(R"(\begin{pmatrix}\alpha_{0,0}&\alpha_{0,1}&\cdots&\alpha_{0,n-1}\\[1.5mm]\alpha_{1,0}&\alpha_{1,1}&\cdots&\alpha_{1,n-1}\\[1.5mm]\vdots&\vdots&\ddots&\vdots\\[1.5mm]\alpha_{n-1,0}&\alpha_{n-1,1}&\cdots&\alpha_{n-1,n-1}\end{pmatrix})", "qindexedmatrix(\"α_\",(n-1),(n-1),1,1)");
  rejects("[a_(0,0), ⋯, a_(0,n); ⋮, ⋱, ⋮; a_(m,1), ⋯, a_(m,n)]");
  rejects("[a_(0,0), ⋯, a_(0,n); ⋮, ⋱, ⋮; a_(m,0), ⋯, b_(m,n)]");
  rejects("[a_(0,0), ⋯, a_(0,n); ⋮, ⋱, ⋯; a_(m,0), ⋯, a_(m,n)]");
  rejects("[a_(0,0), ⋯, a_(0,n); ⋮, ⋱, ⋮; a_(m,0), ⋯, a_(m,n+1)]");
  equal("[\"⋱\"]", "[\"⋱\"]");
  equal("[a_(0,0), ⋯, a_(0,n n); ⋮, ⋱, ⋮; a_(m,0), ⋯, a_(m,n n)]", "qindexedmatrix(\"a_\",(m),(n n),0,0)");
  equal("a_(0,1)", "qindexedcoefficient(\"a_\",(0),(1))");
  equal(R"(\alpha_{k,l+1})", "qindexedcoefficient(\"α_\",(k),(l+1))");
  equal(R"(\begin{pmatrix}a_{0,0}&a_{0,1}\\a_{1,0}&a_{1,1}\end{pmatrix})", "[qindexedcoefficient(\"a_\",(0),(0)),qindexedcoefficient(\"a_\",(0),(1));qindexedcoefficient(\"a_\",(1),(0)),qindexedcoefficient(\"a_\",(1),(1))]");
  rejects("a_(0,1,2)");rejects("a_(0,)");
  equal("2a_(0,1)", "2qindexedcoefficient(\"a_\",(0),(1))");
  equal(R"(\begin{array}{lr}N & \text{Success probability}\\ \hline 2 & 0.50\\4 & 1.00\end{array})",
        "matrix(3,2,vector(\"N\",\"Success probability\",2,0.50,4,1.00))");
  equal(R"(\begin{array}{c|r}a & f(a)\\\hline 0 & 1\end{array}\qquad \begin{array}{c}b\\\hline 0\end{array})",
        "vector(matrix(2,2,vector(\"a\",\"f(a)\",0,1)),matrix(2,1,vector(\"b\",0)))");
  rejects(R"(\begin{array}{|}a\\\hline 0\end{array})");
  equal(R"(\begin{array}{c|c}+ & 0\\\hline 0 & 0\end{array}\qquad\begin{array}{c|c}\cdot & 0\\\hline 0 & 0\end{array})",
        "vector(matrix(2,2,vector(\"+\",\"0\",0,0)),matrix(2,2,vector(\"·\",\"0\",0,0)))");
  rejects(R"(\begin{array}{cc}a & \cdot\\\hline 0 & 0\end{array})");
  rejects(R"(\begin{array}{cc}N & p(N,1)\\ \hline 2\end{array})");
  rejects(R"(\begin{array}{cc}N & p(N,1)\\ \hline 2 & 1.2.3\end{array})");
  rejects(R"(\begin{array}{c}N\\ 2\end{array})");
  equal(R"(Z_{\mathrm{OR}})","Z_OR");
  equal(R"(U_{ f })","U_f");
  // A rejected call must not affect a subsequent independent translation.
  equal(R"(\ket{1})","|1>");
  std::cout<<"PASS: "<<checks<<" TeX translation and rejection checks\n";
  return 0;
 } catch(const std::exception &error) {
  std::cerr<<error.what()<<'\n';return 1;
 }
}
