param([string]$Distribution = (Join-Path (Split-Path $PSScriptRoot -Parent) 'dist\QuantumStudio'))
$ErrorActionPreference = 'Stop'
function Evaluate([string]$expression, [string]$arguments = "") {
    $info = [Diagnostics.ProcessStartInfo]::new((Join-Path $Distribution 'quantum-worker.exe'))
    $info.Arguments = $arguments
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardInput = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $info.StandardOutputEncoding = [Text.Encoding]::UTF8
    $info.StandardErrorEncoding = [Text.Encoding]::UTF8
    $info.EnvironmentVariables['QALCULATE_DEFINITIONS_DIR'] = Join-Path $Distribution 'data'
    $process = [Diagnostics.Process]::Start($info)
    $outTask = $process.StandardOutput.ReadToEndAsync()
    $errTask = $process.StandardError.ReadToEndAsync()
    $bytes = [Text.Encoding]::UTF8.GetBytes($expression)
    $process.StandardInput.BaseStream.Write($bytes, 0, $bytes.Length)
    $process.StandardInput.Close()
    if (!$process.WaitForExit(20000)) { $process.Kill(); throw "Timeout: $expression" }
    $result = @{ Code = $process.ExitCode; Text = $outTask.Result.Trim(); Error = $errTask.Result.Trim() }
    $process.Dispose()
    return $result
}
$cases = @(
    @('quantum:css_encoder([],[1,1,0;0,1,1])(I/2)css_encoder([],[1,1,0;0,1,1])†==stabilizer_projector(<ZZI,IZZ>)/2','1'),
    @('quantum:norm(css_encoder([],[1,1,0;0,1,1])†stabilizer_correction(<ZZI,IZZ>,[1,1])pauli(IXI)css_encoder([],[1,1,0;0,1,1])|i>-|i>)','0'),
    @('quantum:norm(css_encoder([],[1,1,0;0,1,1])|i>-(|000>+i|111>)/sqrt(2))','0'),
    @('quantum:css_encoder([1,1,1,1],[1,1,1,1])†css_encoder([1,1,1,1],[1,1,1,1])==identity(4)','1'),
    @('quantum:css_encoder([0,0,0],[])==identity(8)','1'),
    @('quantum:norm(css_encoder([1,1],[1,1])-|Phi+>)','0'),
    @('quantum:stabilizer_parameters(css_generators([1,1,1,1],[1,1,1,1]))','[4  2  2]'),
    @('quantum:stabilizer_dimension(css_generators([],[1,1,0;0,1,1]))','2'),
    @('quantum:norm(css_state([1,1],[1,1],0)-|Phi+>)','0'),
    @('quantum:norm(css_state([1,1;1,1],[1,1],0)-|Phi+>)','0'),
    @('quantum:stabilizer_syndrome(css_generators([1,1],[1,1]),pauli(XI))','[0  1]'),
    @("quantum:norm(Pauli('-1jXYZ')|000>-|110>)",'0'),
    @('quantum:pauli(+1jYY)==iY@Y','1'),
    @('quantum:pauli(-1YY)==-Y@Y','1'),
    @('quantum:stabilizer_dimension(<-1XX,ZZ,1YY>)','1'),
    @('quantum:stabilizer_correction(<XXII,ZZII,IIXX,IIZZ>,[1,1,1,1])==pauli(IYIY)','1'),
    @('quantum:norm(vec(stabilizer_correction(<ZZI,IZZ>,[1,1])-pauli(IXI)))','0'),
    @('quantum:norm(vec(stabilizer_correction(<XX,ZZ>,[1,1])-pauli(IY)))','0'),
    @('quantum:norm(vec(stabilizer_correction(<Z>,1)-X))','0'),
    @('quantum:norm(vec(stabilizer_correction(<XX,ZZ>,[0,0])-identity(4)))','0'),
    @('quantum:fidelity(stabilizer_correction(<ZZI,IZZ>,[1,1])pauli(IXI)(|000>+i|111>),|000>+i|111>)','1.00000000000'),
    @('quantum:stabilizer_distance(<ZZI,IZZ>)','1'),
    @('quantum:stabilizer_parameters(<XXXX,ZZZZ>)','[4  2  2]'),
    @('quantum:stabilizer_parameters(<XZZXI,IXZZX,XIXZZ,ZXIXZ>)','[5  1  3]'),
    @('quantum:stabilizer_parameters(<ZZZZIII,ZZIIZZI,ZIZIZIZ,XXXXIII,XXIIXXI,XIXIXIX>)','[7  1  3]'),
    @('quantum:stabilizer_distance(<-XXXX,ZZZZ,-YYYY>)','2'),
    @('quantum:stabilizer_dimension(⟨XX,ZZ⟩)','1'),
    @('quantum:stabilizer_dimension(<ZZI,IZZ>)','2'),
    @('quantum:stabilizer_dimension(\left\langle XX,ZZ,-YY\right\rangle)','1'),
    @('quantum:norm(vec(stabilizer_projector(⟨X⊗X,Z⊗Z⟩)-density(|Phi+>)))','0'),
    @('quantum:stabilizer_syndrome(⟨ZZI,IZZ⟩,pauli(IXI))','[1  1]'),
    @('quantum:stabilizer_dimension(<ZZ>)>1','1'),
    @('quantum:stabilizer_dimension(vector(X@X,Z@Z))','1'),
    @('quantum:stabilizer_dimension(vector(Z@Z@I,I@Z@Z))','2'),
    @('quantum:stabilizer_dimension(vector(X@X,Z@Z,-Y@Y))','1'),
    @('quantum:norm(vec(stabilizer_projector(vector(X@X,Z@Z))-density(|Phi+>)))','0'),
    @('quantum:stabilizer_syndrome(vector(Z@Z@I,I@Z@Z),I@X@I)','[1  1]'),
    @('quantum:stabilizer_syndrome(vector(Z),iX)','1'),
    @('quantum:\expval{Y}{i}','1'),
    @('quantum:\ev*{X}{+}','1'),
    @('quantum:\expectationvalue**{Z}{1}','−1'),
    @('quantum:\matrixel{0}{X}{1}','1'),
    @('quantum:\mel**{i}{Y}{i}','1'),
    @('quantum:\matrixelement*{1,1}{CNOT}{1,0}','1'),
    @('quantum:\ip{i}','1'),
    @('quantum:\braket*{i}{-i}','0'),
    @('quantum:\bra*{i}Y\ket*{i}','1'),
    @('quantum:norm(vec(\dyad{i}-density(|i>)))','0'),
    @('quantum:norm(vec(\op*{0}{1}^2))','0'),
    @('quantum:norm(vec(\ketbra{0}{1}†-|1><0|))','0'),
    @('quantum:\expval{Z}{1}^2','1'),

    @(('quantum:' + ('(' * 80) + '1' + (')' * 80)), '1'),
    @('quantum:norm(vec(linear_gate([1,0;1,1])-CNOT))','0'),
    @('quantum:norm(vec(linear_gate([0,1;1,0])-SWAP))','0'),
    @('quantum:norm(linear_gate([1,0;1,1])|+0>-|Phi+>)','0'),
    @('quantum:norm(vec(linear_gate(1)-I))','0'),
    @('quantum:tr(linear_gate(identity(9)))','512'),
    @('quantum:gf2_rank(gf2_mul(identity(128),identity(128)))','128'),
    @('quantum:gf2_mul([1,1],[1;1])','0'),
    @('quantum:norm(vec(gf2_mul([1,1;0,1],[1,1;0,1])-I))','0'),
    @('quantum:norm(vec(linear_gate(gf2_mul([1,0;1,1],[0,1;1,0]))-CNOT*SWAP))','0'),
    @('quantum:norm(vec(linear_gate(gf2_inverse([1,1,0;0,1,1;0,0,1]))-linear_gate([1,1,0;0,1,1;0,0,1])†))','0'),

    @('quantum:gf2_inverse(1)','1'),
    @('quantum:norm(vec(gf2_inverse([1,1;0,1])-[1,1;0,1]))','0'),
    @('quantum:norm(vec(gf2_inverse([0,1;1,0])-[0,1;1,0]))','0'),
    @('quantum:norm(vec(gf2_inverse([1,1,0;0,1,1;0,0,1])-[1,1,1;0,1,1;0,0,1]))','0'),
    @('quantum:gf2_rank(gf2_inverse(identity(128)))','128'),

    @('quantum:gf2_rank([1,1,0;1,0,1;0,1,1])','2'),
    @('quantum:gf2_nullspace([0,1,0;1,0,1])','[1; 0; 1]'),
    @('quantum:gf2_nullspace([1,1,0;1,0,1;0,1,1])','[1; 1; 1]'),
    @('quantum:norm(vec(gf2_rref([0,1,0;1,0,1])-[1,0,1;0,1,0]))','0'),
    @('quantum:gf2_rank(1)','1'),
    @('quantum:gf2_rank(0)','0'),
    @('quantum:norm(vec(gf2_nullspace(0*I)-I))','0'),
    @('quantum:gf2_rank([1,1,1])','1'),
    @('quantum:gf2_rank([1;1;1])','1'),
    @('quantum:gf2_nullspace(I)','[]'),
    @('quantum:gf2_rank(identity(128))','128'),

    @('quantum:(0!=0)!=(1!=0)','1'),
    @('quantum:(0=0)!=(1=0)','1'),
    @('quantum:(0=0)=(1=0)','0'),
    @('quantum:(0=0)>(1=0)','1'),
    @('quantum:(0=0)<(1=0)','0'),
    @('quantum:(0=0)>=(1=0)','1'),
    @('quantum:(0=0)<=(1=0)','0'),
    @('quantum:0<=(2>1)<2','1'),
    @('quantum:(2>1)=(3>2)=(4>3)','1'),
    @('quantum:((1=1)=(2=2))!=0','1'),
    @('quantum:norm(vec(phase_function((x=1)!=(x=2),2,x)-(Z@Z)))','0'),
    @('quantum:norm(vec(oracle_function((x=1)=(x=2),2,1,x)-oracle([1,0,0,1],1)))','0'),

    @('quantum:0 xor 0','0'),
    @('quantum:0 xor 1','1'),
    @('quantum:1 xor 0','1'),
    @('quantum:1 xor 1','0'),
    @('quantum:2 xor -3','0'),
    @('quantum:0 ⊻ 2','1'),
    @('quantum:1 \veebar 1','0'),
    @('quantum:1 xor 1 and 0','1'),
    @('quantum:1 or 1 xor 1','1'),
    @('quantum:1 xor 1 xor 1','1'),
    @('quantum:not 1 xor 1','1'),
    @('quantum:1=1 xor 2=3','1'),
    @('quantum:xor(5,6)','3'),
    @('quantum:2*xor(5,6)','6'),
    @('quantum:norm(vec(phase_function(x>=2 xor x mod 2,2,x)-(Z @ Z)))','0'),
    @('quantum:norm(vec(oracle_function(x>=2 xor x mod 2,2,1,x)-oracle([0,1,1,0],1)))','0'),
    @('quantum:norm((H@H)phase_function(x>=2 xor x mod 2,2,x)|++>-|11>)','0'),

    @('quantum:not 0','1'),
    @('quantum:not 1','0'),
    @('quantum:not not 2','1'),
    @('quantum:1 or 0 and 0','1'),
    @('quantum:(1 or 0) and 0','0'),
    @('quantum:not 2=3','1'),
    @('quantum:not 2=2 or 1=1 and 0=1','0'),
    @('quantum:1+(not 0)','2'),
    @('quantum:norm((2<3 and not 0)|0>-|0>)','0'),
    @('quantum:norm(vec(phase_function(x=1 or x=3,2,x)-(I @ Z)))','0'),
    @('quantum:norm(vec(phase_function(x>=1 and x<=2,2,x)-phaseoracle(2,[1,2])))','0'),
    @('quantum:norm(vec(phase_function(not x=3,2,x)+CZ))','0'),
    @('quantum:norm(vec(oracle_function(x<2 and not x=0,2,1,x)-oracle([0,1,0,0],1)))','0'),
    @('quantum:norm(vec(phase_function(\neg(x=1 \lor x=3),2,x)+(I @ Z)))','0'),

    @('quantum:2=2','1'),
    @('quantum:2==3','0'),
    @('quantum:2!=3','1'),
    @('quantum:1<2','1'),
    @('quantum:vector(1<2,|0>)','(1, [1; 0])'),
    @('quantum:vector(2<1,|0>)','(0, [1; 0])'),
    @('quantum:vector(1<2,3<4,|0>)','(1, 1, [1; 0])'),
    @('quantum:vector(1<2,<0|)','(1, [1  0])'),
    @('quantum:norm(vec(2<0,1|-2*<01|))','0'),
    @('quantum:1>2','0'),
    @('quantum:2<=2','1'),
    @('quantum:3>=2','1'),
    @('quantum:1≤2','1'),
    @('quantum:3≥4','0'),
    @('quantum:2≠3','1'),
    @('quantum:2\leq3','1'),
    @('quantum:3\geq3','1'),
    @('quantum:2\neq2','0'),
    @('quantum:0<=2<3','1'),
    @('quantum:0<=3<3','0'),
    @('quantum:3>2>=1','1'),
    @('quantum:1+2=3','1'),
    @('quantum:1=2+1','0'),
    @('quantum:norm(vec(phase_function(x=3,2,x)-CZ))','0'),
    @('quantum:norm(vec(phase_function(1<=x<3,2,x)-phaseoracle(2,[1,2])))','0'),
    @('quantum:norm(vec(oracle_function(x>1,2,1,x)-oracle([0,0,1,1],1)))','0'),
    @('quantum:norm(diffusion(2)phase_function(x==3,2,x)|++>-|11>)','0'),
    @('quantum:<0|X|1>','1'),
    @('quantum:<0|<1|01>','1'),
    @('quantum:norm(vec(|0><0|+|1><1|-I))','0'),
    @('quantum:sum(k=2,0,3,k)','1'),

    @('quantum:norm(vec(phase_function(x,1,x)-Z))','0'),
    @('quantum:norm(vec(phase_function(0,3,x)-identity(8)))','0'),
    @('quantum:norm(vec(phase_function(1,2,x)+identity(4)))','0'),
    @('quantum:norm(vec(phase_function(floor(x/3),2,x)-CZ))','0'),
    @('quantum:norm(diffusion(2)phase_function(floor(x/3),2,x)|++>-|11>)','0'),
    @('quantum:norm((H @ H @ H)phase_function(bitdot("101",bits(x,3)),3,x)|+++>-|101>)','0'),
    @('quantum:norm(vec(blocksum(phase_function(x,1,x),0,1,x)-(Z # Z)))','0'),
    @('quantum:norm(vec(blocksum(phase_function(mod(x+k,2),1,x),0,1,k)-(Z # (-Z))))','0'),
    @('quantum:norm(vec(oracle_function((tr(phase_function(x,1,x))+2)/2,1,1,x)-(I @ X)))','0'),
    @('quantum:tr(phase_function(0,9,x))','512'),

    @('quantum:norm(vec(oracle_function(x,1,1,x)-CNOT))','0'),
    @('quantum:norm(vec(oracle_function(1-x,1,1,x)-oracle([1,0],1)))','0'),
    @('quantum:norm(vec(oracle_function(mod(x*x+1,4),2,2,x)-oracle([1,2,1,2],2)))','0'),
    @('quantum:norm((H @ H @ H @ I)oracle_function(bitdot("101",bits(x,3)),3,1,x)(H @ H @ H @ I)|000,->-|101,->)','0'),
    @('quantum:norm(vec(blocksum(oracle_function(x,1,1,x),0,1,x)-(CNOT # CNOT)))','0'),
    @('quantum:norm(vec(blocksum(oracle_function(mod(x+k,2),1,1,x),0,1,k)-(CNOT # oracle([1,0],1))))','0'),
    @('quantum:tr(oracle_function(0,8,1,x))','512'),
    @('quantum:norm(vec(oracle_function(mod(x+1,4),2,2,x)^2-identity(16)))','0'),

    @('quantum:bits(5,4)','[0  1  0  1]'),
    @('quantum:bitvalue("00101")','5'),
    @('quantum:bitvalue([0;1;0;1])','5'),
    @('quantum:bitvalue(bits(2^100+13,128))-(2^100+13)','0'),
    @('quantum:bitvalue(bits(2^1024-1,1024))-(2^1024-1)','0'),
    @('quantum:bitvalue(bitxor(bits(5,4),bits(6,4)))','3'),
    @('quantum:norm(|bitvalue("101")>_8-|101>)','0'),
    @('quantum:bits(0,1)','0'),
    @('quantum:bitvalue(1)','1'),
    @('quantum:<101|H @ H @ H|011>-(-1)^bitdot(bits(5,3),bits(3,3))/sqrt(8)','0'),

    @('quantum:bitxor("101","110")','[0  1  1]'),
    @('quantum:binaryxor([0;0;1],[1,0,1])','[1  0  0]'),
    @('quantum:bitxor("0","1")','1'),
    @('quantum:bitxor("000","000")','[0  0  0]'),
    @('quantum:bitdot(bitxor("001","101"),"100")','1'),
    @('quantum:norm((bitxor(bitxor("001","101"),"101")-[0,0,1])†)','0'),
    @('quantum:norm((bitxor("101","110")-bitxor("110","101"))†)','0'),
    @('quantum:bitdot(bitxor("101","110"),"011")','0'),
    @('quantum:xor(5,6)','3'),

    @('quantum:bitdot("101","110")','1'),
    @('quantum:bitdot("111","110")','0'),
    @('quantum:binarydot([1,0,1],[1,1,0])','1'),
    @('quantum:bitdot([1;0;1],[1,1,0])','1'),
    @('quantum:bitdot("001",[0;0;1])','1'),
    @('quantum:bitdot("0","1")','0'),
    @('quantum:bitdot(1,1)','1'),
    @('quantum:(-1)^bitdot("101","100")','−1'),
    @('quantum:sum((-1)^bitdot([1,0,1],[k,0,0]),0,1,k)','0'),
    @('quantum:bitdot([1-1,2/2],[0,1])','1'),

    @('quantum:norm(|0,1>-|01>)','0'),
    @('quantum:norm(|00,1>-|001>)','0'),
    @('quantum:norm(|+,i>-(|+>@|i>))','0'),
    @('quantum:norm(|Phi+,1>-(|Phi+>@|1>))','0'),
    @('quantum:norm(|0^2,1>-|001>)','0'),
    @('quantum:<0,1|0,1>','1'),
    @('quantum:<i,-|i,->','1'),
    @('quantum:<i,-|-i,->','0'),
    @('quantum:<1,1|CNOT|+,0>-1/sqrt(2)','0'),
    @('quantum:norm(CNOT|+,0>-|Phi+>)','0'),
    @('quantum:norm(vec(|0,1><1,0|-|01><10|))','0'),
    @('quantum:norm(<i,-|†-|i,->)','0'),
    @('quantum:norm(\ket{0,1}-|01>)','0'),
    @('quantum:\braket{i,-|i,-}','1'),
    @('quantum:norm(|mod(5,3)>_3-|2>_3)','0'),
    @('quantum:<mod(5,3)|_3 mod(8,3)>_3','1'),
    @('quantum:norm(|0,1>|1>-|011>)','0'),
    @('quantum:<0,1|<1|011>','1'),
    @('quantum:norm(| 0 , 1 , 0 >-|010>)','0'),

    @('quantum:<0|<1|CNOT|0>|1>','1'),
    @('quantum:<1|<1|CNOT|+>|0>-1/sqrt(2)','0'),
    @('quantum:<1|<0|CNOT|+>|0>','0'),
    @('quantum:<i|<-|i>|->','1'),
    @('quantum:<i|<-|I @ I|i>|->','1'),
    @('quantum:<0|<1|0>|1>','1'),
    @('quantum:<0|<1|01>','1'),
    @('quantum:<0|<1| |0>|1>','1'),
    @('quantum:<2|_3<1|identity(6)|2>_3|1>','1'),
    @('quantum:<2|_3<1|2>_3|1>','1'),
    @('quantum:<0|<1|1>|0>','0'),
    @('quantum:<0|<1|<0|010>','1'),
    @('quantum:norm((<0|<1|)†-|01>)','0'),
    @('quantum:<0|<1|†','0'),
    @('quantum:<i|<i|†','1'),
    @('quantum:<0|0>|1>-|1>','[0; 0]'),
    @('quantum:\bra{1}\bra{1}CNOT\ket{+}\ket{0}-1/sqrt(2)','0'),

    @('quantum:<00|CNOT|+>|0>-1/sqrt(2)','0'),
    @('quantum:<11|CNOT|+>|0>-1/sqrt(2)','0'),
    @('quantum:<01|CNOT|1>|0>','0'),
    @('quantum:<11|CNOT|1>|0>','1'),
    @('quantum:<00|CNOT|+>|0>^2','0.5'),
    @('quantum:<00|CNOT|+>|0>+<11|CNOT|+>|0>-sqrt(2)','0'),
    @('quantum:<11|I @ Y|1>|0>-i','0'),
    @('quantum:<101|identity(8)|1>|0>|1>','1'),
    @('quantum:<5|_6 identity(6)|2>_3|1>','1'),
    @('quantum:\bra{11}CNOT\ket{+}\ket{0}-1/sqrt(2)','0'),
    @('quantum:<00|CNOT+identity(4)|+>|0>-sqrt(2)','0'),

    @('quantum:norm(vec(logm(I)))','0'),
    @('quantum:norm(vec(logm(X)-i*pi*(I-X)/2))','0'),
    @('quantum:norm(vec(logm(Y)-i*pi*(I-Y)/2))','0'),
    @('quantum:norm(vec(logm(H)-i*pi*(I-H)/2))','0'),
    @('quantum:norm(vec(logm(SWAP)-i*pi*(identity(4)-SWAP)/2))','0'),
    @('quantum:norm(vec(logm(CNOT)-density(|1>) @ logm(X)))','0'),
    @('quantum:norm(vec(logm(Z)-[0,0;0,i*pi]))','0'),
    @('quantum:norm(vec(logm(S)-[0,0;0,i*pi/2]))','0'),
    @('quantum:norm(vec(logm(-I)-i*pi*I))','0'),
    @('quantum:norm(vec(logm([2,0;0,3])-[ln(2),0;0,ln(3)]))','0'),
    @('quantum:norm(vec(logm([x,0;0,y])-[ln(x),0;0,ln(y)]))','0'),
    @('quantum:norm(vec(logm(X)†+logm(X)))','0'),
    @('quantum:norm(vec(expm(logm(X))-X))','0'),
    @('quantum:norm(evolution(i*logm(X),1)|0>-|1>)','0'),
    @('quantum:norm(vec(logm(expm(2*pi*i*I))))','0'),
    @('quantum:norm(vec(expm(logm([0,2;1/2,0]))-[0,2;1/2,0]))','0'),
    @('quantum:tr(logm(2*identity(64)))-64ln(2)','0'),
    @('quantum:norm(vec(Y^∗+Y))','0'),
    @('quantum:norm(vec(X×Y⊗Z-(X*Y) @ Z))','0'),
    @('quantum:√9×4','12'),
    @('quantum:√(9×4)','6'),
    @('quantum:⟪(X⋅Y)|(X⋅Y)⟫','2'),
    @('quantum:norm(vec(\frac{X×Y}{2}-iZ/2))','0'),
    @('quantum:norm(vec(√X-SX))','0'),
    @('quantum:norm(vec(√SWAP-sqrt(SWAP)))','0'),
    @('quantum:norm(vec((∛X)^3-X))','0'),
    @('quantum:norm(vec((∜X)^4-X))','0'),
    @('quantum:√√16','2'),
    @('quantum:norm(vec(H√X-H*SX))','0'),
    @('quantum:norm(vec(√X†-sqrt(X†)))','0'),
    @('quantum:norm(vec((√X)†-SXdg))','0'),
    @('quantum:norm(vec(√X²-I))','0'),
    @('quantum:norm(vec((√X)²-X))','0'),
    @('quantum:norm(√X|0>-(1+i)/2*|0>-(1-i)/2*|1>)','0'),
    @('quantum:norm(vec(√(X @ X)-sqrt(X @ X)))','0'),
    @('quantum:norm(vec(√[0,1;1,0]-SX))','0'),
    @('quantum:2√9+∛8+∜16','10'),
    @('quantum:√9*4','12'),
    @('quantum:√(9*4)','6'),
    @('quantum:√-1','i'),
    @('quantum:∛(-8)-(1+i*sqrt(3))','0'),
    @('quantum:√(-1)^2','1'),
    @('quantum:(√(-1))^2','−1'),
    @('quantum:√π-sqrt(pi)','0'),
    @('quantum:⟪(√X)|(√X)⟫','2'),
    @('quantum:<0|√X|0>-(1+i)/2','0'),
    @('quantum:norm(vec(X^(1/2)-SX))','0'),
    @('quantum:norm(vec(sqrt(X)-SX))','0'),
    @('quantum:norm(vec(\sqrt{X}-SX))','0'),
    @('quantum:norm(vec((\sqrt[3]{X})^3-X))','0'),
    @('quantum:norm(vec(Z^(1/2)-S))','0'),
    @('quantum:norm(vec(S^(1/2)-T))','0'),
    @('quantum:norm(vec(X^(-1/2)-SXdg))','0'),
    @('quantum:norm(vec(Y^(1/2)*Y^(1/2)-Y))','0'),
    @('quantum:norm(vec(H^(1/2)*H^(1/2)-H))','0'),
    @('quantum:norm(vec(CNOT^(1/2)-controlled(SX)))','0'),
    @('quantum:norm(vec(SWAP^(1/2)-[1,0,0,0;0,(1+i)/2,(1-i)/2,0;0,(1-i)/2,(1+i)/2,0;0,0,0,1]))','0'),
    @('quantum:norm(vec(sqrt(ECR)^2-ECR))','0'),
    @('quantum:norm(vec(X^(1/2)^2-X^(1/4)))','0'),
    @('quantum:norm(vec((X^(1/3))^3-X))','0'),
    @('quantum:norm(vec([4,0;0,9]^(1/2)-[2,0;0,3]))','0'),
    @('quantum:norm(vec([1,0;0,-1]^t-((1+(-1)^t)/2*I+(1-(-1)^t)/2*Z)))','0'),
    @('quantum:sqrt(9)','3'),
    @('quantum:norm(vec(sqrt([0,2;1/2,0])^2-[0,2;1/2,0]))','0'),
    @('quantum:norm(vec(ECR-(X @ I-Y @ X)/sqrt(2)))','0'),
    @('quantum:norm(vec(ECR† ECR-identity(4)))','0'),
    @('quantum:norm(vec(ECR-ECR†))','0'),
    @('quantum:norm(vec(ECR^2-identity(4)))','0'),
    @('quantum:norm(ECR |00>-(|10>-i|11>)/sqrt(2))','0'),
    @('quantum:norm(ECR |01>-(-i|10>+|11>)/sqrt(2))','0'),
    @('quantum:norm(ECR |10>-(|00>+i|01>)/sqrt(2))','0'),
    @('quantum:norm(ECR |11>-(i|00>+|01>)/sqrt(2))','0'),
    @('quantum:norm(vec(ECR-exp(-i*pi/4)*(X @ I)*CNOT*(S @ SX)))','0'),
    @('quantum:norm(apply(ECR,|000>,[2,0])-(|001>-i|101>)/sqrt(2))','0'),
    @('quantum:norm(controlled(ECR)|000>-|000>)','0'),
    @('quantum:norm(controlled(ECR)|100>-(|110>-i|111>)/sqrt(2))','0'),
    @('quantum:norm(|(pauli("X Y"))>>-vec(pauli("X Y")))','0'),
    @('quantum:norm(vec(Pauli(X Y)-X @ Y))','0'),
    @('quantum:norm(|(X+iY)>>-vec(X+iY))','0'),
    @('quantum:<<(X+iY)|(X+iY)>>','4'),
    @('quantum:<<(X Y)|(X Y)>>','2'),
    @('quantum:norm(|(X Y)>>-vec(X*Y))','0'),
    @('quantum:<<(X+iY)|Y>>+2i','0'),
    @('quantum:<<Y|(X+iY)>>-2i','0'),
    @('quantum:norm(|(density(|i>))>>-vec(density(|i>)))','0'),
    @('quantum:<<(density(|i>))|(density(|i>))>>','1'),
    @('quantum:<<(X+iY)|superop(vector(S))|(X+iY)>>+4i','0'),
    @('quantum:norm(vec(|(X)>><<(Y)|-vec(X)*dagger(vec(Y))))','0'),
    @('quantum:norm(|(unvec(|(X+iY)>>,2))>>-vec(X+iY))','0'),
    @('quantum:norm(|([1,i,2;3,4,5])>>-vec([1,i,2;3,4,5]))','0'),
    @('quantum:⟪(X+iY)|(X+iY)⟫','4'),
    @('quantum:\langle\langle(X+iY)|(X+iY)\rangle\rangle','4'),
    @('quantum:norm(vec(lindblad_dissipator(destroy(2))-[0,0,0,1;0,-1/2,0,0;0,0,-1/2,0;0,0,0,-1]))','0'),
    @('quantum:norm(lindblad_dissipator(destroy(2))vec(density(|0>)))','0'),
    @('quantum:norm(lindblad_dissipator(destroy(2))vec(density(|1>))-vec(Z))','0'),
    @('quantum:norm(vec(lindblad_dissipator(i*destroy(2))-lindblad_dissipator(destroy(2))))','0'),
    @('quantum:norm(vec(lindblad_dissipator(2*destroy(2))-4*lindblad_dissipator(destroy(2))))','0'),
    @('quantum:norm(vec(lindblad_dissipator(I)))','0'),
    @('quantum:norm(vec(liouvillian(Y/2)+i*(spre(Y/2)-spost(Y/2))))','0'),
    @('quantum:norm(vec(liouvillian(X,vector(Z,destroy(2)))-liouvillian(X)-lindblad_dissipator(Z)-lindblad_dissipator(destroy(2))))','0'),
    @('quantum:norm(vec(liouvillian(0I,vector(destroy(2)))-lindblad_dissipator(destroy(2))))','0'),
    @('quantum:norm(vec(liouvillian(X,vector())-liouvillian(X)))','0'),
    @('quantum:tr(unvec(liouvillian(Y,vector([1,i;2,3]))vec([1,2;3i,4]),2))','0'),
    @('quantum:norm(liouvillian(identity(16))vec(identity(16)))','0'),
    @('quantum:norm(lindblad_dissipator(identity(16))vec(identity(16)))','0'),
    @('quantum:norm(liouvillian(numberop(3))vec(identity(3)))','0'),
    @('quantum:norm(spre(Y)vec(S)-vec(Y*S))','0'),
    @('quantum:norm(spost(Y)vec(S)-vec(S*Y))','0'),
    @('quantum:norm(sprepost(Y,S)vec(X)-vec(Y*X*S))','0'),
    @('quantum:norm(vec(sprepost(S,S†)-superop(vector(S))))','0'),
    @('quantum:norm(vec(sprepost(Y,S)-spre(Y)*spost(S)))','0'),
    @('quantum:norm((spre(Y)-spost(Y))vec(X)-vec(comm(Y,X)))','0'),
    @('quantum:norm(sprepost([1,i,2;3,4,5],[1,2;3i,4;5,6;7,8])*vec([1,i,2,3;4,5,6,7;8,9,10,11])-vec([1,i,2;3,4,5]*[1,i,2,3;4,5,6,7;8,9,10,11]*[1,2;3i,4;5,6;7,8]))','0'),
    @('quantum:norm(sprepost(CNOT,SWAP)vec(identity(4))-vec(CNOT*SWAP))','0'),
    @('quantum:norm(spre(identity(16))vec(identity(16))-vec(identity(16)))','0'),
    @('quantum:norm(spost(identity(16))vec(identity(16))-vec(identity(16)))','0'),
    @('quantum:norm(spre(identity(3))vec(identity(3))-vec(identity(3)))','0'),
    @('quantum:norm(vec(R(pi/3,0)-Rx(pi/3)))','0'),
    @('quantum:norm(vec(R(pi/3,pi/2)-Ry(pi/3)))','0'),
    @('quantum:norm(vec(R(pi/3,pi)-Rx(-pi/3)))','0'),
    @('quantum:norm(vec(R(pi/3,pi/4)-Rz(pi/4)*Rx(pi/3)*Rz(-pi/4)))','0'),
    @('quantum:norm(vec(R(pi/3,pi/4)†-R(-pi/3,pi/4)))','0'),
    @('quantum:norm(vec(R(2pi,pi/4)+I))','0'),
    @('quantum:norm(vec(R(0,pi/4)-I))','0'),
    @('quantum:norm(vec(R(pi/3,pi/4)-expm(-i*pi/6*(X+Y)/sqrt(2))))','0'),
    @('quantum:norm(controlled(R(pi,pi/2))|10>-|11>)','0'),
    @('quantum:norm(vec(apply(R(pi/2,pi/2),density(|0>),0)-density(|+>)))','0'),
    @('quantum:norm(C(X,1,"0")|00>-|01>)','0'),
    @('quantum:norm(controlled(X,1+1,"01")|010>-|011>)','0'),
    @('quantum:norm(controlled(SWAP,2,"10")|1001>-|1010>)','0'),
    @('quantum:norm(apply(controlled(X,2,"10"),|0010>,[2,0,3])-|0011>)','0'),
    @('quantum:norm(controlled(X,8,"00000001")basis(2,512)-basis(3,512))','0'),
    @('quantum:norm(vec(chi(vector(I))-2density(basis(0,4))))','0'),
    @('quantum:norm(vec(Chi(vector(X))-2density(basis(1,4))))','0'),
    @('quantum:norm(vec(χ(vector(Y))-2density(basis(2,4))))','0'),
    @('quantum:norm(vec(\chi(vector(Z))-2density(basis(3,4))))','0'),
    @('quantum:norm(vec(chi(vector(H))-[0,0,0,0;0,1,0,1;0,0,0,0;0,1,0,1]))','0'),
    @('quantum:norm(vec(chi(vector(S))-[1,0,0,i;0,0,0,0;0,0,0,0;-i,0,0,1]))','0'),
    @('quantum:norm(vec(chi(amplitude_damping(3/4))-[9,0,0,3;0,3,-3i,0;0,3i,3,0;3,0,0,1]/8))','0'),
    @('quantum:norm(vec(chi(depolarizing(1))-identity(4)/2))','0'),
    @('quantum:norm(vec(chi(vector(X @ S))-chi(vector(X)) @ chi(vector(S))))','0'),
    @('quantum:norm(vec(chi(vector(i*S))-chi(vector(S))))','0'),
    @('quantum:norm(vec(chi(vector(2I))-8density(basis(0,4))))','0'),
    @('quantum:norm(vec(chi(vector((I+X)/2,(I-X)/2))-chi(vector(I/sqrt(2),X/sqrt(2)))))','0'),
    @('quantum:tr(chi(vector(identity(16))))','16'),
    @('quantum:bloch(|00>,[0])','[0; 0; 1]'),
    @('quantum:bloch(|+1>,0)','[1; 0; 0]'),
    @('quantum:bloch(|+1>,1)','[0; 0; −1]'),
    @('quantum:bloch((|00>+|11>)/sqrt(2),0)','[0; 0; 0]'),
    @('quantum:bloch((|00>+i|11>)/sqrt(2),1)','[0; 0; 0]'),
    @('quantum:bloch(|0> @ |i> @ |+>,1)','[0; 1; 0]'),
    @('quantum:bloch(3i*(|0> @ |i> @ |+>),2)','[1; 0; 0]'),
    @('quantum:bloch(density(|0> @ |i> @ |+>),1)','[0; 1; 0]'),
    @('quantum:norm(bloch(channel(density((|00>+|11>)/sqrt(2)),amplitude_damping(3/4),1),1)-[0;0;3/4])','0'),
    @('quantum:bloch(|0000000001>,9)','[0; 0; −1]'),
    @('quantum:bloch(|0000000001>,0)','[0; 0; 1]'),
    @('quantum:bloch(identity(128),6)','[0; 0; 0]'),
    @('quantum:bloch(|i>,0)','[0; 1; 0]'),
    @('quantum:bloch(|0>)','[0; 0; 1]'),
    @('quantum:bloch(|1>)','[0; 0; −1]'),
    @('quantum:bloch(|+>)','[1; 0; 0]'),
    @('quantum:bloch(|->)','[−1; 0; 0]'),
    @('quantum:bloch(|i>)','[0; 1; 0]'),
    @('quantum:bloch(|-i>)','[0; −1; 0]'),
    @('quantum:bloch(3i|i>)','[0; 1; 0]'),
    @('quantum:bloch(3I)','[0; 0; 0]'),
    @('quantum:bloch([3/4,0;0,1/4])','[0; 0; 0.5]'),
    @('quantum:bloch(Ry(pi/2)|0>)','[1; 0; 0]'),
    @('quantum:bloch(Rx(pi/2)|0>)','[0; −1; 0]'),
    @('quantum:bloch(ptrace(density((|00>+|11>)/sqrt(2)),0))','[0; 0; 0]'),
    @('quantum:norm(bloch(density((|0>+(1+i)|1>)/sqrt(3)))-[2/3;2/3;-1/3])','0'),
    @('quantum:norm(vec(superop(thermal_relaxation(1,2,ln(4)))-superop(amplitude_damping(3/4))))','0'),
    @('quantum:norm(vec(channel(density(|i>),thermal_relaxation(1,1,ln(2),1/4))-[5/8,-i/4;i/4,3/8]))','0'),
    @('quantum:norm(vec(superop(thermal_relaxation(infinity,1,ln(2)))-superop(phase_damping(3/4))))','0'),
    @('quantum:norm(vec(superop(thermal_relaxation(infinity,infinity,10,1/4))-identity(4)))','0'),
    @('quantum:norm(vec(superop(thermal_relaxation(1,1,0,1/4))-identity(4)))','0'),
    @('quantum:norm(vec(channel([3/4,0;0,1/4],thermal_relaxation(1,1,ln(2),1/4))-[3/4,0;0,1/4]))','0'),
    @('quantum:norm(vec(ptm(thermal_relaxation(1,1,ln(4),1/4))-ptm(thermal_relaxation(1,1,ln(2),1/4))^2))','0'),
    @('quantum:norm(vec(ptrace(choi(thermal_relaxation(1,1,ln(2))),1)-I))','0'),
    @('quantum:expect(Z,channel(density(|0>),thermal_relaxation(1,2,ln(2),1)))','0'),
    @('quantum:norm(paulivec(Y)-sqrt(2)basis(2,4))','0'),
    @('quantum:norm(paulivec([1,i;2,3])-[4;2+i;-1-2i;-2]/sqrt(2))','0'),
    @('quantum:norm(paulivec(X @ Y)-2basis(6,16))','0'),
    @('quantum:norm(paulivec(pauli("YIXZ"))-4basis(135,256))','0'),
    @('quantum:norm(vec(unpaulivec(paulivec([1,i;2,3]))-[1,i;2,3]))','0'),
    @('quantum:norm(vec(unpaulivec(paulivec(CNOT))-CNOT))','0'),
    @('quantum:norm(vec(unpaulivec(paulivec(identity(16)))-identity(16)))','0'),
    @('quantum:norm(paulivec(unpaulivec([1;i;2;-3]))-[1;i;2;-3])','0'),
    @('quantum:norm(paulivec(density((|00>+|11>)/sqrt(2)))-(basis(0,16)+basis(5,16)-basis(10,16)+basis(15,16))/2)','0'),
    @('quantum:norm(vec(unpaulivec(ptm(amplitude_damping(3/4))paulivec(density(|i>)))-channel(density(|i>),amplitude_damping(3/4))))','0'),
    @('quantum:norm(vec(unpaulivec(ptm(vector(CNOT))paulivec(density(|+0>)))-density((|00>+|11>)/sqrt(2))))','0'),
    @('quantum:norm(paulivec([1,i;2,3]))^2-tr([1,i;2,3]†[1,i;2,3])','0'),
    @('quantum:norm(paulivec(0I))','0'),
    @('quantum:norm(vec(unpaulivec(0|00>)))','0'),
    @('quantum:norm(vec(ptm(vector(I))-identity(4)))','0'),
    @('quantum:norm(vec(PTM(vector(S))-[1,0,0,0;0,0,-1,0;0,1,0,0;0,0,0,1]))','0'),
    @('quantum:norm(vec(ptm(vector(H))-[1,0,0,0;0,0,0,1;0,0,-1,0;0,1,0,0]))','0'),
    @('quantum:norm(vec(ptm(amplitude_damping(3/4))-[1,0,0,0;0,1/2,0,0;0,0,1/2,0;3/4,0,0,1/4]))','0'),
    @('quantum:norm(vec(ptm(amplitude_damping(3/4,1/4))-[1,0,0,0;0,1/2,0,0;0,0,1/2,0;3/8,0,0,1/4]))','0'),
    @('quantum:norm(vec(ptm(phase_damping(3/4))-[1,0,0,0;0,1/2,0,0;0,0,1/2,0;0,0,0,1]))','0'),
    @('quantum:norm(vec(ptm(depolarizing(4/3))-[1,0,0,0;0,-1/3,0,0;0,0,-1/3,0;0,0,0,-1/3]))','0'),
    @('quantum:norm(vec(ptm(vector(S*H))-ptm(vector(S))*ptm(vector(H))))','0'),
    @('quantum:norm(vec(ptm(vector(X @ S))-ptm(vector(X)) @ ptm(vector(S))))','0'),
    @('quantum:norm(ptm(vector(CNOT))basis(4,16)-basis(5,16))','0'),
    @('quantum:norm(ptm(vector(CNOT))basis(3,16)-basis(15,16))','0'),
    @('quantum:norm(ptm(vector(CNOT))basis(7,16)+basis(10,16))','0'),
    @('quantum:norm(ptm(vector(X @ I @ S))basis(41,64)+basis(42,64))','0'),
    @('quantum:tr(ptm(vector(identity(16))))','256'),
    @('quantum:norm(vec(ptm(vector(2I))-4identity(4)))','0'),
    @('quantum:tr((channel(density(|i>),amplitude_damping(3/4,1/4))-[11/16,-i/4;i/4,5/16])^2)','0'),
    @('quantum:tr((channel(density(|i>),phase_amplitude_damping(1/4,1/2,1/4))-[9/16,-i/4;i/4,7/16])^2)','0'),
    @('quantum:tr((channel([3/4,0;0,1/4],amplitude_damping(2/3,1/4))-[3/4,0;0,1/4])^2)','0'),
    @('quantum:tr((channel([3/4,0;0,1/4],phase_amplitude_damping(1/3,1/2,1/4))-[3/4,0;0,1/4])^2)','0'),
    @('quantum:tr((channel(density(|i>),amplitude_damping(1,1/4))-[3/4,0;0,1/4])^2)','0'),
    @('quantum:tr((channel(density(|i>),amplitude_damping(0,1/4))-density(|i>))^2)','0'),
    @('quantum:tr((channel(density(|i>),phase_amplitude_damping(0,0,1/4))-density(|i>))^2)','0'),
    @('quantum:tr((channel(density(|i>),phase_amplitude_damping(0,1,1/4))-I/2)^2)','0'),
    @('quantum:tr((channel(density(|i>),phase_amplitude_damping(1/4,3/4,1/4))-[9/16,0;0,7/16])^2)','0'),
    @('quantum:tr((channel(density(|0>),amplitude_damping(1,1))-density(|1>))^2)','0'),
    @('quantum:norm(vec(superop(amplitude_damping(2/3,0))-superop(amplitude_damping(2/3))))','0'),
    @('quantum:norm(vec(superop(phase_amplitude_damping(2/3,0,0))-superop(amplitude_damping(2/3))))','0'),
    @('quantum:norm(vec(superop(phase_amplitude_damping(0,2/3))-superop(phase_damping(2/3))))','0'),
    @('quantum:tr((ptrace(choi(amplitude_damping(2/3,1/4)),1)-I)^2)','0'),
    @('quantum:tr((ptrace(choi(phase_amplitude_damping(1/3,1/2,1/4)),1)-I)^2)','0'),
    @('quantum:tr((channel(density((|00>+|11>)/sqrt(2)),amplitude_damping(1,1/2),1)-identity(4)/4)^2)','0'),
    @('quantum:tr((channel(density(|i>),phase_amplitude_damping(1/4,1/2,1/4))-channel(channel(density(|i>),amplitude_damping(1/4,1/4)),phase_damping(2/3)))^2)','0'),
    @('quantum:tr((channel(density(|1>),amplitude_damping(3/4))-[3/4,0;0,1/4])^2)','0'),
    @('quantum:tr((channel(density(|i>),amplitude_damping(3/4))-[7/8,-i/4;i/4,1/8])^2)','0'),
    @('quantum:tr((channel(density(|i>),phase_damping(3/4))-[1/2,-i/4;i/4,1/2])^2)','0'),
    @('quantum:tr((channel(density(|i>),depolarizing(1/2))-[1/2,-i/4;i/4,1/2])^2)','0'),
    @('quantum:tr((channel(density(|1>),depolarizing(4/3))-[2/3,0;0,1/3])^2)','0'),
    @('quantum:tr((channel(density((|00>+|11>)/sqrt(2)),amplitude_damping(3/4),1)-[1/2,0,0,1/4;0,0,0,0;0,0,3/8,0;1/4,0,0,1/8])^2)','0'),
    @('quantum:tr((channel(density((|00>+|11>)/sqrt(2)),depolarizing(1),0)-identity(4)/4)^2)','0'),
    @('quantum:tr((ptrace(choi(amplitude_damping(2/3)),1)-I)^2)','0'),
    @('quantum:tr((ptrace(choi(phase_damping(2/3)),1)-I)^2)','0'),
    @('quantum:tr((ptrace(choi(depolarizing(2/3)),1)-I)^2)','0'),
    @('quantum:norm(superop(amplitude_damping(3/4))vec(density(|i>))-vec([7/8,-i/4;i/4,1/8]))','0'),
    @('quantum:tr((channel(density(|i>),amplitude_damping(0))-density(|i>))^2)','0'),
    @('quantum:tr((channel(density(|i>),phase_damping(0))-density(|i>))^2)','0'),
    @('quantum:tr((channel(density(|i>),depolarizing(0))-density(|i>))^2)','0'),
    @('quantum:tr((channel(density(|i>),amplitude_damping(1))-density(|0>))^2)','0'),
    @('quantum:tr((channel(density(|i>),phase_damping(1))-I/2)^2)','0'),
    @('quantum:tr((channel(density(|i>),depolarizing(1))-I/2)^2)','0'),
    @('quantum:purity(3|i>)','1'),
    @('quantum:purity(density((|00>+|11>)/sqrt(2)))','1'),
    @('quantum:purity(ptrace(density((|00>+|11>)/sqrt(2)),1))','0.5'),
    @('quantum:purity(3I)','0.5'),
    @('quantum:3purity(identity(3))','1'),
    @('quantum:purity([1/4,0;0,3/4])','0.625'),
    @('quantum:variance(Z,|0>)','0'),
    @('quantum:variance(Z,3|+>)','1'),
    @('quantum:variance(Y,|i>)','0'),
    @('quantum:variance(Y,|0>)','1'),
    @('quantum:variance(3I+2Z,3I)','4'),
    @('quantum:variance(Z,[1/4,0;0,3/4])','0.75'),
    @('quantum:variance([1,i;-i,3],|0>)','1'),
    @('quantum:variance(pauli("ZZ"),(|00>+|11>)/sqrt(2))','0'),
    @('quantum:norm(U(pi/2,0,pi)|0>-H|0>)','0'),
    @('quantum:norm(U3(pi/2,0,pi)|1>-H|1>)','0'),
    @('quantum:norm(U2(0,pi)|1>-H|1>)','0'),
    @('quantum:norm(U1(pi/2)|1>-S|1>)','0'),
    @('quantum:norm(U_{3}(pi,0,pi)|0>-X|0>)','0'),
    @('quantum:norm(U_1(pi/4)|1>-T|1>)','0'),
    @('quantum:norm(U3(pi/3,0,0)|0>-Ry(pi/3)|0>)','0'),
    @('quantum:norm(U(pi/3,pi/2,pi/2)|1>-i Rz(pi/2) Ry(pi/3) Rz(pi/2)|1>)','0'),
    @('quantum:norm(controlled(U(0,pi,pi)) (|00>+|10>)/sqrt(2)-(|00>+|10>)/sqrt(2))','0'),
    @('quantum:tr(U3(pi/3,pi/2,pi/2)†U3(pi/3,pi/2,pi/2))','2'),
    @('quantum:norm(pauli("XYZ")|000>-i|110>)','0'),
    @('quantum:norm(pauli(XYZ)|001>+i|111>)','0'),
    @('quantum:norm(Pauli("-iXYZ")|000>-|110>)','0'),
    @('quantum:norm(pauli("iY")|0>+|1>)','0'),
    @('quantum:norm(pauli("-X")|0>+|1>)','0'),
    @('quantum:norm(pauli("+X")|0>-|1>)','0'),
    @('quantum:tr(pauli("XYZ")†pauli("XYZ"))','8'),
    @('quantum:expect(pauli("XX")+pauli("YY")+pauli("ZZ"),(|01>-|10>)/sqrt(2))','−3'),
    @('quantum:norm(evolution(pauli("XX"),pi/2)|00>+i|11>)','0'),
    @('quantum:norm(pauli("I X")|00>-|01>)','0'),
    @('quantum:norm(pauli("-iX")†|0>-i|1>)','0'),
    @('quantum:norm(shift(3)basis(2,3)-basis(0,3))','0'),
    @('quantum:norm(shift(5)basis(3,5)-basis(4,5))','0'),
    @('quantum:norm(clock(3)basis(1,3)-exp(2pi i/3)basis(1,3))','0'),
    @('quantum:norm(clock(3)shift(3)basis(0,3)-exp(2pi i/3)shift(3)clock(3)basis(0,3))','0'),
    @('quantum:norm(shift(2)|0>-X|0>)','0'),
    @('quantum:norm(clock(2)|1>-Z|1>)','0'),
    @('quantum:norm(fourier(2)|0>-H|0>)','0'),
    @('quantum:norm(fourier(4)|01>-QFT(2)|01>)','0'),
    @('quantum:norm(fourier(3)basis(0,3)-(basis(0,3)+basis(1,3)+basis(2,3))/sqrt(3))','0'),
    @('quantum:tr(fourier(3)†fourier(3))','3'),
    @('quantum:norm(fourier(3)shift(3)fourier(3)†basis(1,3)-clock(3)basis(1,3))','0'),
    @('quantum:tr(shift(3)^3)','3'),
    @('quantum:tr(clock(3)^3)','3'),
    @('quantum:ptrace(density(|1> ⊗ basis(2,3)),0,[2,3])','[0 0 0;0 0 0;0 0 1]'),
    @('quantum:ptrace(density(|1> ⊗ basis(2,3)),1,[2,3])','[0 0;0 1]'),
    @('quantum:3ptrace(density((basis(0,9)+basis(4,9)+basis(8,9))/sqrt(3)),1,[3,3])','[1 0 0;0 1 0;0 0 1]'),
    @('quantum:ptrace(density(basis(5,6)),[0,1],[2,3])','1'),
    @('quantum:ptrace(density(basis(5,6)),[1,0],[2,3])','1'),
    @('quantum:ptrace(density(basis(5,6)),1,[2,1,3])','[0 0 0 0 0 0;0 0 0 0 0 0;0 0 0 0 0 0;0 0 0 0 0 0;0 0 0 0 0 0;0 0 0 0 0 1]'),
    @('quantum:dagger(basis(2,6)) ptranspose(basis(0,6) dagger(basis(5,6)),1,[2,3]) basis(3,6)','1'),
    @('quantum:dagger(basis(3,6)) ptranspose(basis(0,6) dagger(basis(5,6)),0,[2,3]) basis(2,6)','1'),
    @('quantum:dagger(basis(5,6)) ptranspose(basis(0,6) dagger(basis(5,6)),[0,1],[2,3]) basis(0,6)','1'),
    @('quantum:dagger(basis(0,6)) ptranspose(ptranspose(basis(0,6) dagger(basis(5,6)),1,[2,3]),1,[2,3]) basis(5,6)','1'),
    @('quantum:ptrace(density(|01>),0,[2,2])','[0 0;0 1]'),
    @('quantum:probs(|+> ⊗ |0>,0)','[0.5;0.5]'),
    @('quantum:probs(|+> ⊗ |0>,1)','[1;0]'),
    @('quantum:probs(|+> ⊗ |0>,[1,0])','[0.5;0.5;0;0]'),
    @('quantum:probs((|000>+|111>)/sqrt(2),[2,0])','[0.5;0;0;0.5]'),
    @('quantum:probs(|100>,[2,0])','[0;1;0;0]'),
    @('quantum:probs(3|100>,[0,2])','[0;0;1;0]'),
    @('quantum:probs(density(|+> ⊗ |0>),[1,0])','[0.5;0.5;0;0]'),
    @('quantum:probs(3density(|100>),[0,2])','[0;0;1;0]'),
    @('quantum:probs(identity(8)/8,[2,0])','[0.25;0.25;0.25;0.25]'),
    @('quantum:norm(R_{XX}(pi/2)|00>-(|00>-i|11>)/sqrt(2))','0'),
    @('quantum:norm(R_x(pi)|0>+i|1>)','0'),
    @('quantum:norm(R_{y}(pi)|0>-|1>)','0'),
    @('quantum:norm(R_{ZZ}(pi)|01>-i|01>)','0'),
    @('quantum:norm(C^2(X)|110>-|111>)','0'),
    @('quantum:norm(C^{2}(X)|110>-|111>)','0'),
    @('quantum:norm(C^{1+1}(X)|010>-|010>)','0'),
    @('quantum:norm(C^1(R_x(pi))|10>+i|11>)','0'),
    @('quantum:tr(C^2(X)† C^2(X))','8'),
    @('quantum:channel(density(|11>),vector([1,0;0,0],[0,1;0,0]),1)','[0 0 0 0;0 0 0 0;0 0 1 0;0 0 0 0]'),
    @('quantum:channel(density((|00>+|11>)/sqrt(2)),vector([1,0;0,0],[0,1;0,0]),1)','[0.5 0 0 0;0 0 0 0;0 0 0.5 0;0 0 0 0]'),
    @('quantum:channel(density(|1>),vector([1,0;0,sqrt(3)/2],[0,1/2;0,0]),0)','[0.25 0;0 0.75]'),
    @('quantum:channel(density((|00>+|11>)/sqrt(2)),vector(I/sqrt(2),Z/sqrt(2)),0)','[0.5 0 0 0;0 0 0 0;0 0 0 0;0 0 0 0.5]'),
    @('quantum:tr(channel(density(|100>),vector(CNOT),[0,2])*density(|101>))','1'),
    @('quantum:tr(channel(density(|001>),vector(CNOT),[2,0])*density(|101>))','1'),
    @('quantum:channel(density(|+>),vector(S),0)','[0.5 −0.5i;0.5i 0.5]'),
    @('quantum:tr(channel(I/2,vector(density(|0>)),0))','0.5'),
    @('quantum:apply(S,density(|+>),0)','[0.5 −0.5i; 0.5i 0.5]'),
    @('quantum:apply(H,I/2,0)','[0.5 0; 0 0.5]'),
    @('quantum:apply(X,density(|00>),1)','[0 0 0 0;0 1 0 0;0 0 0 0;0 0 0 0]'),
    @('quantum:tr(apply(CNOT,density((|00>+|11>)/sqrt(2)),[1,0])*density((|00>+|01>)/sqrt(2)))','1'),
    @('quantum:tr(apply(CNOT,density(|100>),[0,2])*density(|101>))','1'),
    @('quantum:tr(apply(S,density((|00>+|11>)/sqrt(2)),1)*density((|00>+i|11>)/sqrt(2)))','1'),
    @('quantum:tr(apply(density(|0>),I/2,0))','0.5'),
    @('quantum:apply(S,[1,i;2,3],0)','[1 1;2i 3]'),
    @('quantum:norm(controlled(X,2)|110>-|111>)','0'),
    @('quantum:norm(controlled(X,2,1)|010>-|011>)','0'),
    @('quantum:norm(controlled(X,2,1)|110>-|110>)','0'),
    @('quantum:norm(controlled(X,1,0)|00>-|01>)','0'),
    @('quantum:norm(C(X)|10>-|11>)','0'),
    @('quantum:norm(controlled(SWAP,2,2)|1001>-|1010>)','0'),
    @('quantum:norm(apply(controlled(X,2,1),|0010>,[2,0,3])-|0010>)','0'),
    @('quantum:norm(apply(controlled(X,2,2),|0010>,[2,0,3])-|0011>)','0'),
    @('quantum:norm(CY|10>-i|11>)','0'),
    @('quantum:reset(|i>)','[1 0; 0 0]'),
    @('quantum:dephase(|i>)','[0.5 0; 0 0.5]'),
    @('quantum:|2⟩_3','[0; 0; 1]'),
    @('quantum:tr(choi(vector(I)))','2'),
    @('quantum:tr((choi(vector(I))-density(|I>>))^2)','0'),
    @('quantum:norm(superop(vector(S))vec(density(|+>))-vec(channel(density(|+>),vector(S))))','0'),
    @('quantum:norm(superop(vector([1,0;0,sqrt(3)/2],[0,1/2;0,0]))vec(density(|i>))-vec(channel(density(|i>),vector([1,0;0,sqrt(3)/2],[0,1/2;0,0]))))','0'),
    @('quantum:tr((ptrace(choi(vector([1,0;0,sqrt(3)/2],[0,1/2;0,0])),1)-I)^2)','0'),
    @('quantum:tr((ptrace(choi(vector([1,0;0,1;0,0])),1,[2,3])-I)^2)','0'),
    @('quantum:norm(superop(vector([1,0;0,1;0,0]))vec(density(|i>))-vec([1,0;0,1;0,0]density(|i>)[1,0;0,1;0,0]†))','0'),
    @('quantum:superop(vector([1,0],[0,1]))vec(density(|i>))','1'),
    @('quantum:tr((choi(vector(I/sqrt(2),i I/sqrt(2)))-choi(vector(I)))^2)','0'),
    @('quantum:norm((superop(vector(X))superop(vector(S))-superop(vector(X S)))vec(density(|+>)))','0'),
    @('quantum:vec([1,2,3;4,5,6])','[1; 4; 2; 5; 3; 6]'),
    @('quantum:unvec(vec([1,2,3;4,5,6]),2)','[1 2 3; 4 5 6]'),
    @('quantum:vec([1,2,3])','[1; 2; 3]'),
    @('quantum:|Y⟩⟩','[0; i; −i; 0]'),
    @('quantum:⟪Y|Y⟫','2'),
    @('quantum:<<X|Y>>','0'),
    @('quantum:<<Y| |Y>>','2'),
    @('quantum:norm(|Y>>-vec(Y))','0'),
    @('quantum:tr(unvec(|Y>>,2)Y)','2'),
    @('quantum:\langle\langle Y|Y\rangle\rangle','2'),
    @('quantum:vec([1,i;2,3])†vec([1,i;2,3])','15'),
    @('quantum:norm(vec(Y [1,i;2,3] S)-(S^T @ Y)vec([1,i;2,3]))','0'),
    @('quantum:norm(vec(S density(|+>) S†)-(S^* @ S)vec(density(|+>)))','0'),
    @('quantum:norm(permute(|i> @ |+>,[1,0])-SWAP(|i> @ |+>))','0'),
    @('quantum:norm(permute(|+> @ |2>_3,[1,0],[2,3])-(|2>_3 @ |+>))','0'),
    @('quantum:norm(permute(permute(|+> @ |2>_3,[1,0],[2,3]),[1,0],[3,2])-(|+> @ |2>_3))','0'),
    @('quantum:permute(<01|,[1,0])|10>','1'),
    @('quantum:tr((permute(X @ Y,[1,0])-Y @ X)^2)','0'),
    @('quantum:norm(permute(|i> @ |+> @ |->,[1,2,0])-(|+> @ |-> @ |i>))','0'),
    @('quantum:tr((permute(density((|0> @ |1>_3+i|1> @ |2>_3)/sqrt(2)),[1,0],[2,3])-density((|1>_3 @ |0>+i|2>_3 @ |1>)/sqrt(2)))^2)','0'),
    @('quantum:norm(permute(|10>,[2,0,1],[2,1,2])-|01>)','0'),
    @('quantum:tr((SUM(2)-CNOT)^2)','0'),
    @('quantum:norm(SUM(3)†(|2>_3 @ |1>_3)-(|2>_3 @ |2>_3))','0'),
    @('quantum:norm(CADD(2,3)(|1> @ |2>_3)-(|1> @ |0>_3))','0'),
    @('quantum:norm(SUM(3,2)(|2>_3 @ |1>)-(|2>_3 @ |1>))','0'),
    @('quantum:tr(SUM(3)^3)','9'),
    @('quantum:norm(\operatorname{SUM}_{3}(|2>_3 @ |2>_3)-(|2>_3 @ |1>_3))','0'),
    @('quantum:3purity(ptrace(density(SUM(3)(fourier(3) @ identity(3))(|0>_3 @ |0>_3)),0,[3,3]))','1'),
    @('quantum:<2|2>_3','1'),
    @('quantum:<1|2>_{3}','0'),
    @('quantum:<0|_3 shift(3)|2>_3','1'),
    @('quantum:norm(shift(3)|2>_3-|0>_3)','0'),
    @('quantum:norm(|10>_16-basis(10,16))','0'),
    @('quantum:norm(|10>-basis(2,4))','0'),
    @('quantum:tr(|2>_3 <2|_3)','1'),
    @('quantum:\braket{2|2}_{3}','1'),
    @('quantum:norm(\ket{2}_{3}-basis(2,3))','0'),
    @('quantum:norm(|1023>_1024)','1'),
    @('quantum:ptrace(density(|1> @ |2>_3),0,[2,3])','[0 0 0; 0 0 0; 0 0 1]'),
    @('quantum:norm(CP(pi)|11>+|11>)','0'),
    @('quantum:norm(CRx(pi)|10>+i|11>)','0'),
    @('quantum:norm(CRy(pi)|10>-|11>)','0'),
    @('quantum:norm(CRz(pi)|10>+i|10>)','0'),
    @('quantum:norm(CR_{z}(pi)|11>-i|11>)','0'),
    @('quantum:norm(CRX(pi)|10>+i|11>)','0'),
    @('quantum:expect(X @ I,CP(pi)(|00>+|10>)/sqrt(2))','1'),
    @('quantum:expect(X @ I,CRz(pi)(|00>+|10>)/sqrt(2))','0'),
    @('quantum:feedforward(|+>,0,1,X,0)','[1 0; 0 0]'),
    @('quantum:feedforward(|+>,0,0,X,0)','[0 0; 0 1]'),
    @('quantum:probs(feedforward((|00>+|11>)/sqrt(2),0,1,X,1))','[0.5; 0; 0.5; 0]'),
    @('quantum:purity(feedforward((|00>+|11>)/sqrt(2),0,1,X,1))','0.5'),
    @('quantum:tr(feedforward(|100>,[2,0],1,X,1)*density(|110>))','1'),
    @('quantum:tr(feedforward(|100>,[0,2],1,X,1)*density(|100>))','1'),
    @('quantum:tr(feedforward(3I,0,1,X,0))','6'),
    @('quantum:feedforward(|0>,0,1,X,0)','[1 0; 0 0]'),
    @('quantum:expect(Y,ptrace(feedforward(feedforward(apply(H,apply(CNOT,|i> @ (|00>+|11>)/sqrt(2),[0,1]),0),1,1,X,2),0,1,Z,2),[0,1]))','1'),
    @('quantum:expect(X,ptrace(feedforward(feedforward(apply(H,apply(CNOT,|-> @ (|00>+|11>)/sqrt(2),[0,1]),0),1,1,X,2),0,1,Z,2),[0,1]))','−1'),
    @('quantum:<-|->','1'),
    @('quantum:norm(H|->-|1>)','0'),
    @('1 m -> cm','100 cm'),
    @('quantum:purity(dephase(|+> @ |+> @ |+>,[2,0]))','0.25'),
    @('quantum:expect(X @ I,dephase(|+> @ |+>,1))','1'),
    @('quantum:expect(I @ X,dephase(|+> @ |+>,1))','0'),
    @('quantum:tr(dephase(3I,0))','6'),
    @('quantum:tr((dephase(|i>)-channel(density(|i>),vector(I/sqrt(2),Z/sqrt(2))))^2)','0'),
    @('quantum:purity(reset((|00>+|11>)/sqrt(2),0))','0.5'),
    @('quantum:probs(reset((|00>+|11>)/sqrt(2),0))','[0.5; 0.5; 0; 0]'),
    @('quantum:probs(reset((|00>+|11>)/sqrt(2),1))','[0.5; 0; 0.5; 0]'),
    @('quantum:tr(reset(3I,0))','6'),
    @('quantum:probs(reset(|111>,[2,0]))','[0; 0; 1; 0; 0; 0; 0; 0]'),
    @('quantum:tr((reset(|+>,0)-channel(density(|+>),vector([1,0;0,0],[0,1;0,0])))^2)','0'),
    @('quantum:norm(SX|0>-((1+i)|0>+(1-i)|1>)/2)','0'),
    @('quantum:norm(SX^2|1>-X|1>)','0'),
    @('quantum:tr(SXdg SX)','2'),
    @('quantum:norm(SX†|0>-SXdg|0>)','0'),
    @('quantum:norm(Sdg|1>-S†|1>)','0'),
    @('quantum:norm(Tdg|1>-T†|1>)','0'),
    @('quantum:norm(controlled(SX)^2|10>-CNOT|10>)','0'),
    @('quantum:norm(CH|10>-(|10>+|11>)/sqrt(2))','0'),
    @('quantum:norm(CCZ|111>+|111>)','0'),
    @('quantum:norm(Rxx(pi)|00>+i|11>)','0'),
    @('quantum:norm(Ryy(pi)|00>-i|11>)','0'),
    @('quantum:norm(Rzz(pi)|01>-i|01>)','0'),
    @('quantum:norm(Rzx(pi)|10>-i|11>)','0'),
    @('quantum:norm(Rxx(pi/2)|00>-(|00>-i|11>)/sqrt(2))','0'),
    @('quantum:norm(Rxx(0)|00>-|00>)','0'),
    @('quantum:tr(Ryy(pi/3)† Ryy(pi/3))','4'),
    @('quantum:<0|0>', '1'),
    @('quantum:<0|1>', '0'),
    @('quantum:⟨i|Y|i⟩', '1'),
    @('quantum:⟨i|-i⟩', '0'),
    @('quantum:norm(CNOT (H ⊗ I) |00⟩ - (|00⟩+|11⟩)/sqrt(2))', '0'),
    @('quantum:tr(H† H)', '2'),
    @('quantum:tr(S† S)', '2'),
    @('quantum:tr(T† T)', '2'),
    @('quantum:norm(Rx(pi) |0> + i |1>)', '0'),
    @('quantum:norm(Ry(pi) |0> - |1>)', '0'),
    @('quantum:norm(Rz(pi) |0> + i |0>)', '0'),
    @('quantum:norm(P(pi) |1> + |1>)', '0'),
    @('quantum:ptrace(density((|00⟩+|11⟩)/sqrt(2)),1)', '[0.5  0; 0  0.5]'),
    @('quantum:ptrace(density(|01⟩),0)', '[0  0; 0  1]'),
    @('quantum:ptrace(density(|01⟩),1)', '[1  0; 0  0]'),
    @('quantum:expect(Z,|0>)', '1'),
    @('quantum:expect(X,|+>)', '1'),
    @('quantum:norm(normalize(|0>+|1>))', '1'),
    @('quantum:tr(density(|i>))', '1'),
    @('quantum:comm(X,Y)/(2i)', '[1  0; 0  −1]'),
    @('quantum:anticomm(X,Y)', '[0  0; 0  0]'),
    @('quantum:tr(X ⊕ I)', '2'),
    @('quantum:norm(controlled(X) |10> - |11>)', '0'),
    @('quantum:norm(SWAP |01> - |10>)', '0'),
    @('quantum:norm(CCX |110> - |111>)', '0'),
    @('quantum:norm(CSWAP |101> - |110>)', '0'),
    @('quantum:channel(density(|0>),vector(X))', '[0  0; 0  1]'),
    @('quantum:channel(density(|0>),vector(X/sqrt(2),Z/sqrt(2)))', '[0.5  0; 0  0.5]'),
    @('quantum:norm((H^⊗2) |00> - (|00>+|01>+|10>+|11>)/2)', '0'),
    @('quantum:probs(CNOT (H ⊗ I) |00>)', '[0.5; 0; 0; 0.5]'),
    @('quantum:norm(QFT(2) |00> - (|00>+|01>+|10>+|11>)/2)', '0'),
    @('quantum:tr(QFT(2)† QFT(2))', '4'),
    @('quantum:H^⊗0', '1'),
    @('quantum:norm(apply(X,|000>,2)-|001>)', '0'),
    @('quantum:norm(apply(CNOT,|100>,[0,2])-|101>)', '0'),
    @('quantum:norm(apply(CNOT,|001>,[2,0])-|101>)', '0'),
    @('quantum:probs((2 density(|+>⊗|+>)-(I⊗I)) CZ (H⊗H)|00>)', '[0; 0; 0; 1]'),
    @('quantum:\langle 0\vert 0\rangle', '1'),
    @('quantum:\norm{\frac{\ket{0}+\ket{1}}{\sqrt{2}}}', '1'),
    @('quantum:\braket{i|Y|i}', '1'),
    @('quantum:\braket{0}{1}', '0'),
    @('quantum:\operatorname{Tr}(\outerproduct{i}{i})', '1'),
    @('quantum:\norm{\begin{bmatrix}0 & 1 \\ 1 & 0\end{bmatrix}\ket{0}-\ket{1}}', '0'),
    @('quantum:\begin{vmatrix}1 & 2 \\ 3 & 4\end{vmatrix}', '−2'),
    @('quantum:\operatorname{Tr}(H^{\dagger}H)', '2'),
    @('quantum:tr(H ^ { \dagger }H)', '2'),
    @('quantum:norm(|0>|1>-|01>)', '0'),
    @('quantum:norm(|0>|1>|0>-|010>)', '0'),
    @('quantum:norm(CNOT|0>|1>-|01>)', '0'),
    @('quantum:norm(CNOT|1>|0>-|11>)', '0'),
    @('quantum:norm(CNOT|+>|0>-|Φ+>)', '0'),
    @('quantum:norm(-|0>|1>+|01>)', '0'),
    @('quantum:norm(|i>|->-(|i>@|->))', '0'),
    @('quantum:norm(|2>_3|1>-basis(5,6))', '0'),
    @('quantum:norm(\ket{0}\ket{1}-|01>)', '0'),
    @('quantum:norm(|Φ+>|1>-(|001>+|111>)/sqrt(2))', '0'),
    @('quantum:(<0|<1|)(|0>|1>)', '1'),
    @('quantum:(<i|<-|)(|i>|->)', '1'),
    @('quantum:norm(vec(|0>|1><0|<1|-density(|01>)))', '0'),
    @('quantum:<0|1>', '0'),
    @('quantum:<i|i>', '1'),
    @('quantum:norm(vec(|0><1|-[0,1;0,0]))', '0'),
    @('quantum:|0>†|0>', '1'),
    @('quantum:(<0|†)†|0>', '1'),
    @('quantum:norm(vec(X Y-iZ))', '0'),
    @('quantum:norm(vec([1,0;0,1][0,1;1,0]-X))', '0'),
    @('quantum:norm(|Φ+>-(|00>+|11>)/sqrt(2))', '0'),
    @('quantum:norm(\ket{\Phi^{-}}-(|00>-|11>)/sqrt(2))', '0'),
    @('quantum:norm(|Ψ⁺>-(|01>+|10>)/sqrt(2))', '0'),
    @('quantum:norm(\ket{\Psi_{-}}-(|01>-|10>)/sqrt(2))', '0'),
    @('quantum:<Φ⁺|Φ⁻>', '0'),
    @('quantum:<Psi^-|Ψ⁻>', '1'),
    @('quantum:norm(SWAP|Ψ->+|Ψ->)', '0'),
    @('quantum:norm(vec(ptrace(density(|Φ+>),0)-I/2))', '0'),
    @('quantum:norm(vec(density(|Φ+>)+density(|Φ->)+density(|Ψ+>)+density(|Ψ->)-identity(4)))', '0'),
    @('quantum:norm(|0²>-|00>)','0'),
    @('quantum:norm(|0^3>-|000>)', '0'),
    @('quantum:norm(|1^3>-|111>)', '0'),
    @('quantum:norm(\ket{0^{3}}-|000>)', '0'),
    @('quantum:norm(|1³⟩-|111>)', '0'),
    @('quantum:<0^3|0^3>', '1'),
    @('quantum:<0^3|1^3>', '0'),
    @('quantum:<1^{3}|X^{\otimes 3}|0^{3}>', '1'),
    @('quantum:\sum_{n=1}^{4}{<0^n|0^n>}', '4'),
    @('quantum:norm(|0^(1+2)>-|000>)', '0'),
    @('quantum:norm(| 1 ^ (2+1) >-|111>)', '0'),
    @('quantum:|0^0>', '1'),
    @('quantum:|1^0>', '1'),
    @('quantum:norm(|1^3>_8-basis(1,8))', '0'),
    @('quantum:norm(|0^3>_8-basis(0,8))', '0'),
    @('quantum:norm(|1^10>-basis(1023,1024))', '0'),
    @('quantum:norm(\bigotimes_{k=1}^{3}{|0^k>}-|000000>)', '0'),
    @('quantum:17 mod 5', '2'),
    @('quantum:17\bmod 5', '2'),
    @('quantum:17\mod 5', '2'),
    @('quantum:17\mathrm{mod}5', '2'),
    @('quantum:-17 mod 5', '3'),
    @('quantum:2+7 mod 3', '3'),
    @('quantum:(2+7) mod 3', '0'),
    @('quantum:2*7 mod 5', '4'),
    @('quantum:17 mod 5 * 2', '4'),
    @('quantum:norm(|2*7\bmod 15>_{15}-|14>_15)', '0'),
    @('quantum:<2*7 mod 15|14>_15', '1'),
    @('quantum:<14|2*7 mod 15>_15', '1'),
    @('quantum:norm(vec(\sum_{k=0}^{14}{|2*k\bmod 15>_16<k|_16}+|15>_16<15|_16-modmul(2,15)))', '0'),
    @('quantum:norm(\sum_{k=0}^{3}{|2^k\bmod 15>_15}/2-(|1>_15+|2>_15+|4>_15+|8>_15)/2)', '0'),
    @('quantum:17%5', '2'),
    @('quantum:mod(17,5)', '2'),
    @('quantum:2mod(17,5)', '4'),
    @('quantum:norm(|7>_{2^3}-|111>)', '0'),
    @('quantum:norm(|7>_(2^3)-basis(7,8))', '0'),
    @('quantum:<7|_{2^3}|7>_{4+4}', '1'),
    @('quantum:<7|_{2^3}7>_{4+4}', '1'),
    @('quantum:\sum_{n=1}^{3}{<0|_{2^n}0>_{2^n}}', '3'),
    @('quantum:norm(\sum_{k=0}^{7}{\ket{k}_{2^3}}/sqrt(8)-H^{\otimes 3}|000>)', '0'),
    @('quantum:norm(\bigotimes_{k=2}^{4}{|k-1>_{k}}-(|1>_2@|2>_3@|3>_4))', '0'),
    @('quantum:norm(vec(\sum_{k=0}^{3}{|k>_{2^2}<k|_{2^2}}-identity(4)))', '0'),
    @('quantum:norm(|10>_{2^4}-basis(10,16))', '0'),
    @('quantum:norm(|1>_{3+1}-|01>)', '0'),
    @('quantum:<0|_{2^2}identity(4)|0>_{2+2}', '1'),
    @('quantum:<1+1|mod(5,3)>_3', '1'),
    @('quantum:norm(|1+1>_3-|2>_3)', '0'),
    @('quantum:norm(\sum_{k=0}^{3}{\ket{k}_4}/2-H^{\otimes 2}|00>)', '0'),
    @('quantum:norm(\bigotimes_{k=0}^{2}{\ket{k}_3}-(|0>_3@|1>_3@|2>_3))', '0'),
    @('quantum:\sum_{k=0}^{3}{<k|k>_4}', '4'),
    @('quantum:norm(vec(\sum_{k=0}^{2}{|k>_3<k|_3}-identity(3)))', '0'),
    @('quantum:norm(\sum_{k=0}^{3}{exp(2*pi*i*k/4)|k>_4}/2-QFT(2)|01>)', '0'),
    @('quantum:<1+1|_3|2>_3', '1'),
    @('quantum:<mod(5,3)|_3|2>_3', '1'),
    @('quantum:norm(|mod(5,3)>_3-|2>_3)', '0'),
    @('quantum:norm(|001>-basis(1,8))', '0'),
    @('quantum:norm(|001>_3-basis(1,3))', '0'),
    @('quantum:∑_{k=0}^{3}{k^2}', '14'),
    @('quantum:∏_{k=1}^{4}{k}', '24'),
    @('quantum:norm((⨂_{k=0}^{2}{basis(k,3)})-(|0>_3@|1>_3@|2>_3))', '0'),
    @('quantum:norm(vec((⨁^{1}_{k=0}{X^k})-CNOT))', '0'),
    @('quantum:tr(⨁\limits_{k=0}^{1}{X^k})', '2'),
    @('quantum:∑_{k=1}^{2}{∏_{j=1}^{k}{j}}', '3'),
    @('quantum:norm(vec((\bigoplus_{k=0}^{1}{X^k})-CNOT))', '0'),
    @('quantum:norm(vec(blocksum(P(k*pi/2),0,1,k)-controlled(S)))', '0'),
    @('quantum:norm(vec(blocksum(k,-1,1,k)-[-1,0,0;0,0,0;0,0,1]))', '0'),
    @('quantum:norm(vec(blocksum(blocksum(k,0,1,k),0,1,k)-[0,0,0,0;0,1,0,0;0,0,0,0;0,0,0,1]))', '0'),
    @('quantum:tr(blocksum(X,5,5,k)*X)', '2'),
    @('quantum:blocksum(3,0,0,k)', '3'),
    @('quantum:tr(blocksum(identity(k),1,3,k))', '6'),
    @('quantum:norm(vec(blocksum(tensorproduct(X,0,k,j),0,1,k)-(X # (X@X))))', '0'),
    @('quantum:norm((\bigotimes_{k=0}^{2}{basis(k,3)})-(|0>_3@|1>_3@|2>_3))', '0'),
    @('quantum:tr((\bigotimes_{k=1}^{2}{Rz(k*pi)})-(Rz(pi)@Rz(2*pi)))', '0'),
    @('quantum:norm(tensorproduct(Ry(k*pi),0,2,k)|000>+|010>)', '0'),
    @('quantum:(\bigotimes_{k=1}^{2}{<i|})|11>', '−0.5'),
    @('quantum:norm(tensorproduct(basis(k+1,3),-1,1,k)-(|0>_3@|1>_3@|2>_3))', '0'),
    @('quantum:tensorproduct(<0|,0,2,k)|000>', '1'),
    @('quantum:tr(tensorproduct(X,3,3,k)X)', '2'),
    @('quantum:norm(tensorproduct(tensorproduct(basis(k,2),0,1,k),0,1,k)-|0101>)', '0'),
    @('quantum:norm(tensorproduct(tensorproduct(basis(j,2),0,k,j),0,1,k)-|001>)', '0'),
    @('quantum:tr(Y^{ \ast }Y)', '−2'),
    @('quantum:tr(Y^{ T }Y)', '−2'),
    @('quantum:tr(Y^{ \top }Y)', '−2'),
    @('quantum:norm(H ^ { \otimes 2 }|00>-(|00>+|01>+|10>+|11>)/2)', '0'),
    @('quantum:<0|^{\otimes 2}|00>', '1'),
    @('quantum:<i|^{ \otimes 2 }|11>', '−0.5'),
    @('quantum:<0|^{\otimes 3}|000>', '1'),
    @('quantum:<0|^{\otimes 0}', '1'),
    @('quantum:tensorpow(<1|,2)|11>', '1'),
    @('quantum:<00|(|0> ^ { \otimes 2 })', '1'),
    @('quantum:tr(X ^ { 2 })', '2'),
    @('quantum:\norm{H^{\otimes 2}\ket{00}-\frac{\ket{00}+\ket{01}+\ket{10}+\ket{11}}{2}}', '0'),
    @('quantum:\norm{\sigma_{x}\ket{0}-\ket{1}}', '0'),
    @('quantum:\sqrt[3]{8}', '2'),
    @('quantum:\left\lVert |0> \right\rVert', '1'),
    @('quantum:‖|0>+|1>‖^2', '2'),
    @('quantum:$\braket{0|0}$', '1'),
    @('quantum:\[\braket{0|0}\]', '1'),
    @('quantum:\operatorname{Tr}_{0,2}(density(|101>))', '[1  0; 0  0]'),
    @('quantum:Tr_{0,1}(density((|00>+|11>)/sqrt(2)))', '1'),
    @('quantum:ptrace(density(|101>),[2,0])', '[1  0; 0  0]'),
    @('quantum:\sum_{k=0}^{3}{k^2}', '14'),
    @('quantum:\prod_{k=1}^{4}{k}', '24'),
    @('quantum:\sum^{3}_{k=0}{exp(2*pi*i*k/4)}', '0'),
    @('quantum:\norm{\frac{1}{2}\sum_{k=0}^{3}{basis(k,4)}}', '1'),
    @('quantum:\operatorname{Tr}(\sum_{k=0}^{3}{density(basis(k,4))})', '4'),
    @('quantum:basis(2,3)', '[0; 0; 1]'),
    @('quantum:\frac12+\frac1{2}', '1'),
    @('quantum:\norm{\frac{\ket0+\ket1}{\sqrt2}}', '1'),
    @('quantum:\sum_{k=0}^3{k^2}', '14'),
    @('quantum:\sum_{t=0}^3{t^2}', '14'),
    @('quantum:\norm{(\prod_{k=0}^1{Rz(pi*k) H})|0>+i|1>}', '0'),
    @('quantum:norm(exp(-i*pi*X/2)|0>+i|1>)', '0'),
    @('quantum:norm(e^(-i*pi*X/2)|0>+i|1>)', '0'),
    @('quantum:norm(evolution(X,pi/2)|0>+i|1>)', '0'),
    @('quantum:norm(exp(-i*pi*(X⊗Z)/2)|00>+i|10>)', '0'),
    @('quantum:tr(exp(0*(I⊗I)))', '4'),
    @('quantum:exp([0,1;0,0])', '[1  1; 0  1]'),
    @('quantum:exp([2,1;0,2])/exp(2)', '[1  1; 0  1]'),
    @('quantum:floor(norm(exp([0,1,0;0,0,1;0,0,0])basis(2,3)-basis(2,3)-basis(1,3)-basis(0,3)/2)*1e20)', '0'),
    @('quantum:floor(abs(element(exp([0,1,0;0,0,1;1,0,0]),1,1)-(exp(1)+2*exp(-1/2)*cos(sqrt(3)/2))/3)*1e20)', '0'),
    @('quantum:floor(norm((exp([0,1,0;0,0,1;1,0,0])exp([0,-1,0;0,0,-1;-1,0,0])-identity(3))basis(0,3))*1e20)', '0'),
    @('quantum:probs(I/2)', '[0.5; 0.5]'),
    @('quantum:expect(Z,I/2)', '0'),
    @('quantum:born(density(|+>),I/2)', '0.5'),
    @('quantum:born(density(|0>),2|+>)', '0.5'),
    @('quantum:postselect(density(|0>)⊗I,(|00>+|11>)/sqrt(2))', '[1; 0; 0; 0]'),
    @('quantum:postselect(density(|+>),I/2)', '[0.5  0.5; 0.5  0.5]'),
    @('quantum:det(ptranspose(density((|00>+|11>)/sqrt(2)),1))', '−0.0625'),
    @('quantum:det(density((|00>+|11>)/sqrt(2))^{T_1})', '−0.0625'),
    @('quantum:norm((ptranspose(Y⊗X,[0,1])-(Y⊗X)^T)|00>)', '0'),
    @('quantum:norm((Y^T+Y)|0>)', '0'),
    @('quantum:norm((Y^{\top}+Y)|0>)', '0'),
    @('quantum:norm((Y^{*}+Y)|0>)', '0'),
    @('quantum:norm((Y^*+Y)|0>)', '0'),
    @('quantum:norm((conjugate(Y)+Y)|0>)', '0'),
    @('quantum:floor(norm(expm([0,-pi/2,0;pi/2,0,0;0,0,0])basis(0,3)-basis(1,3))*1e20)', '0'),
    @('quantum:floor(norm(expm([0,-128*pi,0;128*pi,0,0;0,0,0])basis(0,3)-basis(0,3))*1e18)', '0'),
    @('quantum:1e-3', '0.001'),
    @('2+3*4', '14'),
    @('det([1,2;3,4])', '−2'),
    @('adj([1,2;3,4])', '[4  −2; −3  1]')
)
$bundledExamples = Get-Content (Join-Path $PSScriptRoot 'examples.json') -Raw | ConvertFrom-Json
for ($control = 0; $control -lt 3; $control++) {
    for ($target = 0; $target -lt 3; $target++) {
        $cases += ,@(('quantum:norm(SUM(3)basis({0},9)-basis({1},9))' -f (3*$control+$target),(3*$control+(($target+$control)%3))), '0')
    }
}
foreach ($basis in @('|00>','|01>','|10>','|11>')) {
    $cases += ,@(('quantum:norm(apply(SWAP,apply(H,apply(CP(pi/2),apply(H,' + $basis + ',0),[1,0]),1),[0,1])-QFT(2)' + $basis + ')'), '0')
}
foreach ($example in $bundledExamples) { $cases += ,@(('quantum:' + $example.expression), $example.expected) }
foreach ($state in @('|0>','|1>','|+>','|->','|i>','|-i>','(3|0>+4i|1>)/5')) {
    $teleported = 'ptrace(feedforward(feedforward(apply(H,apply(CNOT,({0}) @ (|00>+|11>)/sqrt(2),[0,1]),0),1,1,X,2),0,1,Z,2),[0,1])' -f $state
    $cases += ,@(('quantum:tr((' + $teleported + '-density(' + $state + '))^2)'), '0')
}
$cases += ,@('quantum:tr((ptrace(feedforward(feedforward(apply(H,apply(CNOT,(I/2) @ density((|00>+|11>)/sqrt(2)),[0,1]),0),1,1,X,2),0,1,Z,2),[0,1])-I/2)^2)', '0')
$failures = 0
foreach ($state in @('|00>', '|01>', '|10>', '|11>')) {
    $cases += ,@(('quantum:norm((iSWAP-CZ (S @ S) SWAP)' + $state + ')'), '0')
    $cases += ,@(('quantum:norm((fSim(-pi/2,0)-iSWAP)' + $state + ')'), '0')
    $cases += ,@(('quantum:norm((fSim(0,pi/3)-CP(-pi/3))' + $state + ')'), '0')
}
$cases += ,@('quantum:norm(iSWAP|01>-i|10>)', '0')
$cases += ,@('quantum:tr((ISWAP^2-Z @ Z)^2)', '0')
$cases += ,@('quantum:tr(fSim(pi/3,pi/4)†fSim(pi/3,pi/4))', '4')
foreach ($check in @(
 @('norm(vec(reflection(|0>)+Z))','0'),
 @('norm(vec(reflection(|1>)-Z))','0'),
 @('norm(vec(reflection(|+>)+X))','0'),
 @('norm(vec(reflection(|i>)+Y))','0'),
 @('norm(vec(reflection(3i|+>)-reflection(|+>)))','0'),
 @('norm(vec(reflection(|0>+2i|1>)^2-I))','0'),
 @('norm(vec(reflection(|0>+2i|1>)†-reflection(|0>+2i|1>)))','0'),
 @('norm(reflection(|0>+2i|1>)(|0>+2i|1>)+|0>+2i|1>)','0'),
 @('norm(vec(reflection(|++>)+diffusion(2)))','0'),
 @('norm(-reflection(|++>)reflection(|11>)|++>-|11>)','0'),
 @('norm(vec(controlled(reflection(|1>))-CZ))','0'),
 @('norm(vec(phase_reflection(|1>,pi/3)-P(pi/3)))','0'),
 @('norm(vec(phase_reflection(|i>,pi)-reflection(|i>)))','0'),
 @('norm(vec(phase_reflection(|i>,0)-I))','0'),
 @('norm(vec(phase_reflection(|i>,pi/3)†phase_reflection(|i>,pi/3)-I))','0'),
 @('norm(vec(phase_reflection(|i>,-pi/3)-phase_reflection(|i>,pi/3)†))','0'),
 @('norm(vec(phase_reflection(|i>,pi/3)phase_reflection(|i>,pi/6)-phase_reflection(|i>,pi/2)))','0'),
 @('norm(phase_reflection(|0>,pi/3)|1>-|1>)','0'),
 @('norm(phase_reflection(|i>,pi/2)|i>-i|i>)','0'),
 @('norm(vec(reflection(|1>_3)-[1,0,0;0,-1,0;0,0,1]))','0'),
 @('tr(reflection(basis(0,64)))','62'),
 @('norm(vec(reflection(1e200*|i>)-reflection(|i>)))','0'),
 @('norm(vec(reflection(1e-200*|i>)-reflection(|i>)))','0'),
 @('norm(vec(reflection(1e1000*|i>)-reflection(|i>)))','0'),
 @('norm(vec(reflection(1e-1000*|i>)-reflection(|i>)))','0')
)) { $cases += ,@(('quantum:'+$check[0]),$check[1]) }

foreach ($gate in @('XXPlusYY','XXMinusYY')) {
 foreach ($state in @('|00>','|01>','|10>','|11>')) {
  $cases += ,@("quantum:norm(($gate(0,pi/3)-identity(4))$state)",'0')
  $cases += ,@("quantum:norm(($gate(pi/3,pi/4)†*$gate(pi/3,pi/4)-identity(4))$state)",'0')
  $cases += ,@("quantum:norm(($gate(-pi/3,pi/4)-$gate(pi/3,pi/4)†)$state)",'0')
  $cases += ,@("quantum:norm(($gate(pi/3)-$gate(pi/3,0))$state)",'0')
 }
}
$cases += ,@('quantum:norm(XXPlusYY(pi,pi/2)|01>+|10>)','0')
$cases += ,@('quantum:norm(XXPlusYY(pi,pi/2)|10>-|01>)','0')
$cases += ,@('quantum:norm(XXMinusYY(pi,pi/2)|00>-|11>)','0')
$cases += ,@('quantum:norm(XXMinusYY(pi,pi/2)|11>+|00>)','0')
$cases += ,@('quantum:norm(vec(XXPlusYY(pi/3,pi/4)-(Rz(-pi/4)@I)*Rxx(pi/6)*Ryy(pi/6)*(Rz(pi/4)@I)))','0')
$cases += ,@('quantum:norm(vec(XXMinusYY(pi/3,pi/4)-(I@Rz(pi/4))*Rxx(pi/6)*Ryy(-pi/6)*(I@Rz(-pi/4))))','0')

$cases += ,@('quantum:norm(FSim(pi/2,0)|10>+i|01>)', '0')
$cases += ,@('quantum:norm(diffusion(2)phaseoracle(2,3)(H @ H)|00>-|11>)', '0')
$cases += ,@('quantum:born(density(|101>),(diffusion(3)phaseoracle(3,5))^2 H^⊗3 |000>)', '0.9453125')
$cases += ,@('quantum:born(density(|001>)+density(|110>),diffusion(3)phaseoracle(3,[1,6])H^⊗3 |000>)', '1')
$cases += ,@('quantum:tr((diffusion(3)^2-identity(8))^2)', '0')
$cases += ,@('quantum:tr((phaseoracle(3,[0,2,7])^2-identity(8))^2)', '0')
$cases += ,@('quantum:norm(diffusion(2)(|00>-|01>)+(|00>-|01>))', '0')
$cases += ,@('quantum:norm(diffusion(2)(|+> @ |+>)-(|+> @ |+>))', '0')
$cases += ,@('quantum:tr((phaseoracle(2,3)-CZ)^2)', '0')
$cases += ,@('quantum:tr((phaseoracle(1,1)-Z)^2)', '0')
$cases += ,@('quantum:tr((diffusion(1)-X)^2)', '0')
$cases += ,@('quantum:tr(phaseoracle(2,[0,1,2,3]))', '−4')
$cases += ,@('quantum:norm(apply(phaseoracle(2,2),|100>,[0,2])+|100>)', '0')
$truthTable = @(2,2,1,0)
for ($x=0; $x -lt 4; $x++) {
    for ($y=0; $y -lt 4; $y++) {
        $inputIndex=4*$x+$y
        $outputIndex=4*$x+($y -bxor $truthTable[$x])
        $cases += ,@("quantum:norm(oracle([2,2,1,0],2)basis($inputIndex,16)-basis($outputIndex,16))", '0')
    }
}
$cases += ,@('quantum:tr((oracle([0,1])-CNOT)^2)', '0')
$cases += ,@('quantum:tr((oracle([0,0,0,1])-CCX)^2)', '0')
$cases += ,@('quantum:norm(oracle([2,1],2)|011>-|001>)', '0')
$cases += ,@('quantum:tr((oracle([2,2,1,0],2)^2-identity(16))^2)', '0')
$cases += ,@('quantum:norm(oracle([0,1,1,0])(|+> @ |+> @ |->)-(phaseoracle(2,[1,2])(|+> @ |+>)) @ |->)', '0')
$cases += ,@('quantum:probs((H @ H @ I)oracle([0,1,1,0])(H @ H @ I)(|00> @ |->),[0,1])', '[0; 0; 0; 1]')
$cases += ,@('quantum:probs((H @ H @ I)oracle([1,1,1,1])(H @ H @ I)(|00> @ |->),[0,1])', '[1; 0; 0; 0]')
$cases += ,@('quantum:norm(apply(oracle([0,1]),|001>,[2,0])-|101>)', '0')
for ($x=0; $x -lt 8; $x++) {
    $mapped=if($x -lt 5) { (2*$x)%5 } else { $x }
    $cases += ,@("quantum:norm(modmul(2,5)basis($x,8)-basis($mapped,8))", '0')
}
$cases += ,@('quantum:tr((modmul(2,15)^4-identity(16))^2)', '0')
$cases += ,@('quantum:tr((modmul(2,15)†-modmul(8,15))^2)', '0')
$cases += ,@('quantum:tr((modmul(1,5)-identity(8))^2)', '0')
$cases += ,@('quantum:tr((modmul(3,8)^2-identity(8))^2)', '0')
$cases += ,@('quantum:norm(controlled(modmul(2,5))|1001>-|1010>)', '0')
$cases += ,@('quantum:norm(controlled(modmul(2,5))|0001>-|0001>)', '0')
$qpe='apply(QFT(2)†,apply(controlled(modmul(2,15)),apply(controlled(modmul(2,15)^2),(|+> @ |+> @ (|0001>-i|0010>-|0100>+i|1000>)/2),[0,2,3,4,5]),[1,2,3,4,5]),[0,1])'
$cases += ,@(('quantum:probs('+$qpe+',[0,1])'), '[0; 1; 0; 0]')
for ($n=0; $n -lt 5; $n++) {
    $cases += ,@("quantum:expect(numberop(5),basis($n,5))", "$n")
    if ($n -gt 0) { $previous=$n-1; $cases += ,@("quantum:norm(destroy(5)basis($n,5)-sqrt($n)basis($previous,5))", '0') }
    if ($n -lt 4) { $next=$n+1; $cases += ,@("quantum:norm(create(5)basis($n,5)-sqrt($next)basis($next,5))", '0') }
}
$cases += ,@('quantum:norm(annihilation(5)|0>_5)', '0')
$cases += ,@('quantum:norm(creation(5)|4>_5)', '0')
$cases += ,@('quantum:tr((create(5)-destroy(5)†)^2)', '0')
$cases += ,@('quantum:tr((create(5)destroy(5)-numberop(5))^2)', '0')
$cases += ,@('quantum:tr((comm(destroy(5),create(5))-identity(5)+5density(|4>_5))^2)', '0')
$cases += ,@('quantum:tr((comm(numberop(5),destroy(5))+destroy(5))†(comm(numberop(5),destroy(5))+destroy(5)))', '0')
$cases += ,@('quantum:expect(comm(destroy(5),create(5)),|4>_5)', '−4')
$cases += ,@('quantum:expect(numberop(5),(|1>_5+i|3>_5)/sqrt(2))', '2')
for ($j=0; $j -lt 3; $j++) {
    for ($k=0; $k -lt 3; $k++) {
        $delta=if($j -eq $k) {'identity(8)'} else {'0identity(8)'}
        $car="(anticomm(fdestroy(3,$j),fcreate(3,$k))-$delta)"
        $cars="anticomm(fdestroy(3,$j),fdestroy(3,$k))"
        $cases += ,@("quantum:tr(${car}†${car})", '0')
        $cases += ,@("quantum:tr(($cars)†($cars))", '0')
    }
    $difference="(fcreate(3,$j)-fdestroy(3,$j)†)"
    $cases += ,@("quantum:tr(${difference}†${difference})", '0')
}
$cases += ,@('quantum:norm(fdestroy(3,1)|110>+|100>)', '0')
$cases += ,@('quantum:norm(fcreate(3,2)|110>-|111>)', '0')
$cases += ,@('quantum:norm(fcreate(3,1)|110>)', '0')
$cases += ,@('quantum:norm(fdestroy(3,1)|100>)', '0')
$cases += ,@('quantum:tr((fdestroy(3,1)-Z @ destroy(2) @ I)†(fdestroy(3,1)-Z @ destroy(2) @ I))', '0')
$cases += ,@('quantum:expect(fcreate(3,0)fdestroy(3,0)+fcreate(3,1)fdestroy(3,1)+fcreate(3,2)fdestroy(3,2),|101>)', '2')
foreach ($state in @('|00>','|01>','|10>','|11>')) {
    $cases += ,@(('quantum:norm((FSWAP-CZ SWAP)'+$state+')'), '0')
}
$cases += ,@('quantum:norm(FSWAP|11>+|11>)', '0')
$cases += ,@('quantum:tr((FSWAP^2-identity(4))^2)', '0')
$cases += ,@('quantum:tr((FSWAP fdestroy(2,0) FSWAP-fdestroy(2,1))†(FSWAP fdestroy(2,0) FSWAP-fdestroy(2,1)))', '0')
$cases += ,@('quantum:tr(((I @ FSWAP) fcreate(3,1) (I @ FSWAP)-fcreate(3,2))†((I @ FSWAP) fcreate(3,1) (I @ FSWAP)-fcreate(3,2)))', '0')
$cases += ,@('quantum:\bra{1}\hat{X}\ket{0}', '1')
$cases += ,@('quantum:\bra{1}\hat X\ket{0}', '1')
$cases += ,@('quantum:\bra{i}\hat{\sigma}_{y}\ket{i}', '1')
$cases += ,@('quantum:\bra{0}\hat{\sigma_{z}}\ket{0}', '1')
$cases += ,@('quantum:tr(\widehat{X+Y}^{2})', '4')
$cases += ,@('quantum:tr(\widehat{X+i*Y}^{\dagger}\widehat{X+i*Y})', '4')
$cases += ,@('quantum:norm(\hat{\operatorname{destroy}}(3)|2>_3-sqrt(2)|1>_3)', '0')
$cases += ,@('quantum:tr(\hat{\hat{X}}\hat{X})', '2')
$cases += ,@('quantum:norm(iY|0>+|1>)', '0')
$cases += ,@('quantum:norm(-iY|0>-|1>)', '0')
$cases += ,@('quantum:norm(2iX|0>-2i|1>)', '0')
$cases += ,@('quantum:tr(iY^2)', '2i')
$cases += ,@('quantum:tr((iY)^2)', '−2')
$cases += ,@('quantum:norm(iY†|0>+|1>)', '0')
$cases += ,@('quantum:norm((iY)†|0>-|1>)', '0')
$cases += ,@('quantum:norm(iSdg|1>-|1>)', '0')
$cases += ,@('quantum:norm(iSWAP|11>-|11>)', '0')
$cases += ,@('quantum:norm(iiSWAP|11>-i|11>)', '0')
$cases += ,@('quantum:tr(\widehat{X+iY}^{\dagger}\widehat{X+iY})', '4')
$cases += ,@('quantum:\bra{0}\mathbf{X}\mathbf{Y}\ket{0}', 'i')
$cases += ,@('quantum:norm(\mathbb{1}\mathbf{X}|0>-|1>)', '0')
$cases += ,@('quantum:norm(\mathrm{R}_{x}(pi)|0>+i|1>)', '0')
$cases += ,@('quantum:tr(\operatorname{Tr}_{0}(density((|00>+|11>)/sqrt(2))))', '1')
$cases += ,@('quantum:\mathsf{X}\mathcal{Y}|0>', '[i; 0]')
foreach ($spinCase in @(@('1/2',2),@('1',3),@('3/2',4),@('2',5),@('5/2',6))) {
    $spin = $spinCase[0]; $dim = $spinCase[1]
    foreach ($difference in @("comm(Jx($spin),Jy($spin))-i*Jz($spin)", "comm(Jy($spin),Jz($spin))-i*Jx($spin)", "comm(Jz($spin),Jx($spin))-i*Jy($spin)", "Jplus($spin)†-Jminus($spin)", "Jx($spin)^2+Jy($spin)^2+Jz($spin)^2-($spin)*(($spin)+1)*identity($dim)", "Jplus($spin)-Jx($spin)-i*Jy($spin)")) {
        $cases += ,@("quantum:tr(($difference)†($difference))", '0')
    }
    $cases += ,@("quantum:norm(Jplus($spin)basis(0,$dim))", '0')
    $cases += ,@("quantum:norm(Jminus($spin)basis($($dim-1),$dim))", '0')
    for ($k=1; $k -lt $dim; $k++) {
        $cases += ,@("quantum:norm(Jplus($spin)basis($k,$dim)-sqrt($k*($dim-$k))*basis($($k-1),$dim))", '0')
    }
}
foreach ($pair in @(@('Jx','X'),@('Jy','Y'),@('Jz','Z'))) {
    $difference = "$($pair[0])(1/2)-$($pair[1])/2"
    $cases += ,@("quantum:tr(($difference)†($difference))", '0')
}
$cases += ,@('quantum:tr(Jz(63/2))', '0')
foreach ($spinAlias in @(@('J_x','Jx'),@('J_{x}','Jx'),@('Jₓ','Jx'),@('J_y','Jy'),@('J_{z}','Jz'),@('J_+','Jplus'),@('J_{+}','Jplus'),@('J₊','Jplus'),@('J_-','Jminus'),@('J_{-}','Jminus'),@('J₋','Jminus'),@('\hat{J}_{+}','Jplus'),@('\widehat{J}_{-}','Jminus'),@('\mathrm{J}_{x}','Jx'),@('J_{ + }','Jplus'))) {
    $difference = "$($spinAlias[0])(3/2)-$($spinAlias[1])(3/2)"
    $cases += ,@("quantum:tr(($difference)†($difference))", '0')
}
$cases += ,@('quantum:norm(J_{+}(1)basis(1,3)-sqrt(2)*basis(0,3))', '0')
$cases += ,@('quantum:tr((J_x(1)+J_y(1)-Jx(1)-Jy(1))^2)', '0')
$cases += ,@('quantum:tr((J_+(1)†-J_-(1))^2)', '0')
$guideText = Get-Content (Join-Path $PSScriptRoot 'Notation-guide.html') -Raw -Encoding UTF8
foreach ($powerCase in @(@('X²','I'),@('Y³','Y'),@('Z⁰','I'),@('H⁻¹','H'),@('S⁻²','Z'),@('T⁴','Z'),@('X¹²','I'),@('X⁺²','I'),@('SX²','X'),@('iY²','i*I'),@('(iY)²','-I'),@('(X+Z)²','2I'))) {
    $difference="($($powerCase[0])-($($powerCase[1])))"
    $cases += ,@("quantum:tr(${difference}†$difference)", '0')
}
$cases += ,@('quantum:2³', '8')
$cases += ,@('quantum:⟨0|X²|0⟩', '1')
$cases += ,@('quantum:norm(Rz(pi)⁻¹|0>-i|0>)', '0')
$cases += ,@('quantum:tr(density(|+>)²)', '1')
$cases += ,@('quantum:norm(H⁻¹H|0>-|0>)', '0')
$cases += ,@('quantum:tr(CNOT^0)', '4')
$cases += ,@('quantum:2^0', '1')
$cases += ,@('quantum:entropy(|+>)', '0')
$cases += ,@('quantum:entropy((|00>+|11>)/sqrt(2))', '0')
$cases += ,@('quantum:entropy(3|i>)', '0')
$cases += ,@('quantum:entropy(|+>,e)', '0')
$cases += ,@('quantum:<+-|X @ X|+->', '−1')
$cases += ,@('quantum:<0|X+Z|0>', '1')
$cases += ,@('quantum:<0|2Z-X|0>+3', '5')
$cases += ,@('quantum:2<0|X+Z|0>', '2')
$cases += ,@('quantum:<00|H @ H|00>', '0.5')
$cases += ,@('quantum:<0|density(|0>)+density(|1>)|0>', '1')
$cases += ,@('quantum:<0|[1,2;3,4]|1>', '2')
$cases += ,@('quantum:<00|pauli("ZZ")+X @ X|00>', '1')
$cases += ,@('quantum:<0|X|1>+<1|Y|0>', '1 + i')
$cases += ,@('quantum:\braket{+-|X \otimes X|+-}', '−1')
$cases += ,@('quantum:<0| * X |1>', '1')
$cases += ,@('quantum:(<0| @ <1|)|01>', '1')
$cases += ,@('quantum:norm((<i| @ <-|)†-(|i> @ |->))', '0')
$cases += ,@('quantum:norm(<i|†-|i>)', '0')
$cases += ,@('quantum:norm(transpose(<i|)-|-i>)', '0')
$cases += ,@('quantum:norm(dagger(dagger(|i>))-|i>)', '0')
$cases += ,@('quantum:norm((|0> @ <1|)|1>-|0>)', '0')
$cases += ,@('quantum:(<0| @ <1| @ <+|)|01+>', '1')
$cases += ,@('quantum:expect(Z,|0>)+<0|X+Z|0>', '2')
$cases += ,@('quantum:<<I|identity(4)+identity(4)|I>>', '4')
for ($basisIndex=0; $basisIndex -lt 8; $basisIndex++) {
    $bits=[Convert]::ToString($basisIndex,2).PadLeft(3,'0')
    $signs=$bits.Replace('0','+').Replace('1','-')
    $cases += ,@("quantum:norm(|$signs>-H^⊗3 |$bits>)", '0')
    for ($other=0; $other -lt 8; $other++) {
        $otherSigns=[Convert]::ToString($other,2).PadLeft(3,'0').Replace('0','+').Replace('1','-')
        $overlap=if($basisIndex -eq $other){'1'}else{'0'}
        $cases += ,@("quantum:<$signs|$otherSigns>", $overlap)
    }
}
$cases += ,@('quantum:norm(|0+>-|0> @ |+>)', '0')
$cases += ,@('quantum:norm(|+↓->-|+> @ |1> @ |->)', '0')
$cases += ,@('quantum:norm(\ket{+-}-\ket{+} \otimes \ket{-})', '0')
$cases += ,@('quantum:tr(|+-><+−|)', '1')
$cases += ,@('quantum:<+-|(X @ X)|+->', '−1')
$cases += ,@('quantum:norm(|+i>-|i>)', '0')
$cases += ,@('quantum:norm(|-i>-(|0>-i|1>)/sqrt(2))', '0')
for ($basisIndex=0; $basisIndex -lt 8; $basisIndex++) {
    $bits=[Convert]::ToString($basisIndex,2).PadLeft(3,'0')
    $arrows=$bits.Replace('0','↑').Replace('1','↓')
    $texArrows=$bits.Replace('0','\uparrow ').Replace('1','\downarrow ')
    $cases += ,@("quantum:norm(|$arrows> - |$bits>)", '0')
    $cases += ,@("quantum:<$arrows|$bits>", '1')
    $cases += ,@("quantum:norm(\ket{$texArrows}-|$bits>)", '0')
}
$cases += ,@('quantum:<↑|↓>', '0')
$cases += ,@('quantum:<↑|Jz(1/2)|↑>', '0.5')
$cases += ,@('quantum:<↓|Jz(1/2)|↓>', '−0.5')
$cases += ,@('quantum:norm(J_+(1/2)|↓>-|↑>)', '0')
$cases += ,@('quantum:norm(J_-(1/2)|↑>-|↓>)', '0')
$cases += ,@('quantum:norm(|↑1↓>-|011>)', '0')
$cases += ,@('quantum:norm((|↑><↓|-(X+i*Y)/2)|↓>)', '0')
$cases += ,@('quantum:\braket{\uparrow|\downarrow}', '0')
$cases += ,@('quantum:norm((\ketbra{\uparrow}{\downarrow}-Jplus(1/2))|↓>)', '0')
for ($syndrome=0; $syndrome -lt 4; $syndrome++) {
    for ($observed=0; $observed -lt 4; $observed++) {
        $bits = [Convert]::ToString($observed,2).PadLeft(2,'0')
        $reversed = [string]$bits[1] + [string]$bits[0]
        $target = if ($syndrome -eq $observed) { '1' } else { '0' }
        $cases += ,@("quantum:tr((feedforward(|0$reversed>,[2,1],$syndrome,X,0)-density(|$target$reversed>))^2)", '0')
        $phase = if ($syndrome -eq $observed) { '-' } else { '+' }
        $cases += ,@("quantum:tr((feedforward(|+> @ |$reversed>,[2,1],$syndrome,Z,0)-density(|$phase> @ |$reversed>))^2)", '0')
    }
}
$guideCode = @([regex]::Matches($guideText,'<code>(.*?)</code>','Singleline') | ForEach-Object { [Net.WebUtility]::HtmlDecode($_.Groups[1].Value) })
$guideFraction = @($guideCode | Where-Object { $_.StartsWith('\frac{') })
$guideMatrix = @($guideCode | Where-Object { $_.StartsWith('\begin{bmatrix}') })
if ($guideFraction.Count -ne 1 -or $guideMatrix.Count -ne 1) { throw 'Missing or incorrectly escaped TeX examples in the offline guide.' }
$cases += ,@(('quantum:norm(('+ $guideFraction[0] + ')-|+>)'), '0')
$cases += ,@(('quantum:tr((('+ $guideMatrix[0] + ')-X)^2)'), '0')
$spacePoints=@(9,10,11,12,13,32,0x85,0xa0,0x1680)+(0x2000..0x200a)+@(0x2028,0x2029,0x202f,0x205f,0x3000)
foreach($point in $spacePoints) {
    $space=[char]$point
    $cases += ,@("${space}quantum:norm(|->)",'1')
    $cases += ,@("quantum:<0|X${space}X|0>",'1')
}
$cases += ,@(([char]0xfeff+" `tquantum:norm(|->)"),'1')
$cases += ,@(('quantum:'+ [char]0xfeff +'norm(|->)'),'1')
$cases += ,@("`r`n quantum:norm(`r`n H |-> `r`n)",'1')
$cases += ,@(" `t1 m to cm",'100 cm')
$cases += ,@(" `t1 m -> cm",'100 cm')
for($mask=0;$mask -lt 4;$mask++) {
    $pattern=[Convert]::ToString($mask,2).PadLeft(2,'0')
    for($basis=0;$basis -lt 8;$basis++) {
        $target=if([int][Math]::Floor($basis/2) -eq $mask){$basis -bxor 1}else{$basis}
        $cases += ,@(('quantum:norm(controlled(X,2,"'+$pattern+'")basis('+$basis+',8)-basis('+$target+',8))'),'0')
    }
}
foreach ($symbol in @('×','⋅','·','∙','∗')) {
    $cases += ,@("quantum:norm(vec(X${symbol}Y-iZ))",'0')
    $cases += ,@("quantum:norm(vec(Y${symbol}X+iZ))",'0')
    $cases += ,@("quantum:norm(vec(2${symbol}X-2X))",'0')
    $cases += ,@("quantum:<0|X${symbol}X|0>",'1')
    $cases += ,@("quantum:norm(vec(|0>${symbol}<1|-[0,1;0,0]))",'0')
}
foreach ($symbol in @('÷','∕','⁄')) {
    $cases += ,@("quantum:norm(vec(X${symbol}2-X/2))",'0')
    $cases += ,@("quantum:norm(Rx(pi${symbol}2)|0>-(|0>-i|1>)/sqrt(2))",'0')
    $cases += ,@("quantum:norm((|00>+|11>)${symbol}√2)",'1')
    $cases += ,@("quantum:8${symbol}2${symbol}2",'2')
}
foreach ($case in $cases) {
    $result = Evaluate $case[0]
    if ($result.Code -ne 0 -or ($result.Text -replace '\s+', '') -ne ($case[1] -replace '\s+', '')) {
        Write-Output "FAIL $($case[0]): expected $($case[1]); got $($result.Text) [$($result.Code)] $($result.Error)"
        $failures++
    } else { Write-Output "PASS $($case[0])" }
}
$invalid = @(
    'quantum:css_encoder([],[])',
    'quantum:css_encoder([1,0],[1,0])',
    'quantum:css_encoder([1,2],[])',
    'quantum:css_encoder([1,1],[1])',
    'quantum:css_generators([],[])',
    'quantum:css_generators([1,1],[1])',
    'quantum:css_generators([1,0],[1,1])',
    'quantum:css_generators([1,2],[])',
    'quantum:css_state([1,1],[1,1],1)',
    'quantum:css_state([1,1],[],4)',
    'quantum:pauli(11X)',
    'quantum:pauli(ijX)',
    'quantum:pauli(j)',
    'quantum:qpauliword(10,0,0,0)',
    'quantum:qpauliword(1,2,0,0)',
    'quantum:qpauliword(1,0,0,4)',
    'quantum:stabilizer_correction(<Z,Z>,[1,0])',
    'quantum:stabilizer_correction(<I>,1)',
    'quantum:stabilizer_correction(<Z>,1/2)',
    'quantum:stabilizer_correction(<XX,ZZ>,[1,2])',
    'quantum:stabilizer_correction(<XX,ZZ>,1)',
    'quantum:stabilizer_distance(<Z>)',
    'quantum:stabilizer_parameters(<XX,ZZ>)',
    'quantum:stabilizer_distance(<X,Z>)',
    'quantum:stabilizer_parameters(<XX,ZZ,YY>)',
    'quantum:stabilizer_projector(<>)',
    'quantum:stabilizer_projector(<X,>)',
    'quantum:stabilizer_projector(<X@@X>)',
    'quantum:stabilizer_projector(<X*X>)',
    'quantum:stabilizer_projector(<XX,ZZ,YY>)',
    'quantum:stabilizer_projector(<X,Z>)',
    'quantum:stabilizer_projector(vector(X,Z))',
    'quantum:stabilizer_projector(vector(X@X,Z@Z,Y@Y))',
    'quantum:stabilizer_projector(vector(iX))',
    'quantum:stabilizer_projector(vector(H))',
    'quantum:stabilizer_projector(vector(-I))',
    'quantum:stabilizer_syndrome(vector(Z),H)',
    'quantum:\expval{X}','quantum:\ev{}{}','quantum:\matrixel{0}{X}','quantum:\mel{0}{}{1}','quantum:\ev***{X}{0}','quantum:\dyad**{0}','quantum:\ip{}','quantum:\ket**{0}','quantum:\expval{X}{0',
    ('quantum:' + ('(' * 129) + '1' + (')' * 129)),
    'quantum:linear_gate(0)','quantum:linear_gate([1,0])','quantum:linear_gate(identity(10))','quantum:linear_gate([1,2;0,1])','quantum:linear_gate([])','quantum:gf2_mul([1,0],I@I)','quantum:gf2_mul(I,[1,-1;0,1])','quantum:gf2_mul([],I)','quantum:gf2_mul(identity(129),identity(129))',
    'quantum:gf2_inverse(0)','quantum:gf2_inverse([1,0,1])','quantum:gf2_inverse([1;0])','quantum:gf2_inverse([])','quantum:gf2_inverse([1,2;0,1])','quantum:gf2_inverse([1,1,0;1,0,1;0,1,1])','quantum:gf2_inverse(identity(129))','quantum:gf2_inverse([1/2,0;0,1])',
    'quantum:gf2_rank([])','quantum:gf2_rref([1,2])','quantum:gf2_nullspace([-1,0])','quantum:gf2_rank([1/2,0])','quantum:gf2_rank([i,0])','quantum:gf2_rank([x,0])','quantum:gf2_rank(identity(129))','quantum:gf2_nullspace()',
    'quantum:xor','quantum:xor 1','quantum:1 xor','quantum:1 xor xor 0','quantum:1+ xor 0','quantum:phase_function(x=1 xor y=3,2,x)','quantum:not','quantum:1 and','quantum:or 1','quantum:1 and or 0','quantum:1 or or 0','quantum:1+not 0','quantum:not and 1','quantum:phase_function(x=1 or y=3,2,x)','quantum:1<','quantum:1>=','quantum:1===2','quantum:1><2','quantum:phase_function(x<y,2,x)','quantum:phase_function(x,1,1)','quantum:phase_function(x,1,pi)','quantum:phase_function(x,1,x+1)','quantum:phase_function(x,0,x)','quantum:phase_function(x,10,x)','quantum:phase_function(x,1/2,x)','quantum:phase_function(x,n,x)','quantum:phase_function(x,2,x)','quantum:phase_function(-1,1,x)','quantum:phase_function(1/2,1,x)','quantum:phase_function(i,1,x)','quantum:phase_function(y,1,x)','quantum:phase_function([0,1],1,x)','quantum:phase_function(x,1)','quantum:phase_function(x,1,x,0)','quantum:oracle_function(x,1,1,1)','quantum:oracle_function(x,1,1,pi)','quantum:oracle_function(x,1,1,x+1)','quantum:oracle_function(x,0,1,x)','quantum:oracle_function(x,1,0,x)','quantum:oracle_function(x,5,5,x)','quantum:oracle_function(x,1/2,1,x)','quantum:oracle_function(x,n,1,x)','quantum:oracle_function(x,2,1,x)','quantum:oracle_function(-1,1,1,x)','quantum:oracle_function(1/2,1,1,x)','quantum:oracle_function(i,1,1,x)','quantum:oracle_function(y,1,1,x)','quantum:oracle_function([0,1],1,1,x)','quantum:oracle_function(x,1,1)','quantum:bits(-1,3)','quantum:bits(8,3)','quantum:bits(1/2,3)','quantum:bits(i,3)','quantum:bits(x,3)','quantum:bits(0,0)','quantum:bits(0,1025)','quantum:bits(0,3/2)','quantum:bits(0,n)','quantum:bits(2^1024,1024)','quantum:bits(1)','quantum:bits(1,2,3)','quantum:bitvalue("")','quantum:bitvalue("102")','quantum:bitvalue([0,2])','quantum:bitvalue(I)','quantum:bitvalue([0,x])','quantum:bitvalue("1","0")','quantum:bitxor("","0")','quantum:bitxor("01","1")','quantum:bitxor("0 1","101")','quantum:bitxor("102","101")','quantum:bitxor([2,0],[0,1])','quantum:bitxor([i,0],[0,1])','quantum:bitxor([x,0],[0,1])','quantum:bitxor(I,I)','quantum:bitxor(2,1)','quantum:bitxor("1")','quantum:bitxor("1","1","1")','quantum:bitdot("","0")','quantum:bitdot("10","1")','quantum:bitdot("1 0","10")','quantum:bitdot("102","101")','quantum:bitdot([1,2],[0,1])','quantum:bitdot([1/2,0],[0,1])','quantum:bitdot([i,0],[0,1])','quantum:bitdot([x,0],[0,1])','quantum:bitdot(I,I)','quantum:bitdot(2,1)','quantum:bitdot("1")','quantum:bitdot("1","1","1")','quantum:bitdot("1,1)','quantum:|0,>','quantum:|,1>','quantum:|0,,1>','quantum:|0,2>','quantum:|0,1>_4','quantum:<0,1|_4 1>_4','quantum:|0;1>','quantum:|0,(1,0)>','quantum:<0,1|0>','quantum:|0,1,0,1,0,1,0,1,0,1,0>','quantum:|0>*|1>','quantum:[1;0][0;1]','quantum:CNOT|0>','quantum:(<0|<1|)|0>', 'quantum:|Φ±>','quantum:|Ψ^2>','quantum:|Phi+>_4','quantum:X⁺', 'quantum:|0^-1>','quantum:|0^11>','quantum:|0^(1/2)>','quantum:|0^n>','quantum:|0^i>','quantum:|0^H>','quantum:|0^>','quantum:|0^2+1>','quantum:<0^2|0^3>', 'quantum:17\bmod','quantum:\bmod 5','quantum:17\pmod{5}','quantum:|17 mod 0>_3','quantum:|17 mod 5>_2', 'quantum:|0>_{1}','quantum:|0>_{2^11}','quantum:|0>_{3/2}','quantum:|0>_{i}','quantum:|0>_{d}','quantum:|4>_{2^2}','quantum:<0|_3 0>_4','quantum:<0|_{2+1}0>_{2^2}','quantum:|0>_{}','quantum:|0>_{[2,3]}', 'quantum:|-1>_3','quantum:|3+1>_3','quantum:|1/2>_3','quantum:|i>_3','quantum:|H>_3','quantum:|k>_3','quantum:|1+>_3','quantum:|[0,1]>_3','quantum:|k+1>', 'quantum:∑','quantum:∑_{k=0}{X}','quantum:∑_{k=0}^{1}X','quantum:∑_{k=0}_{j=1}{X}','quantum:∏','quantum:∏_{k=0}{X}','quantum:∏_{k=0}^{1}X','quantum:∏_{k=0}_{j=1}{X}','quantum:⨂','quantum:⨂_{k=0}{X}','quantum:⨂_{k=0}^{1}X','quantum:⨂_{k=0}_{j=1}{X}','quantum:⨁','quantum:⨁_{k=0}{X}','quantum:⨁_{k=0}^{1}X','quantum:⨁_{k=0}_{j=1}{X}', 'quantum:blocksum(X,1,0,k)','quantum:blocksum(X,0,32,k)','quantum:blocksum(X,0,1/2,k)','quantum:blocksum(X,0,infinity,k)','quantum:blocksum(X,0,1,pi)','quantum:blocksum(X,0,1,2)','quantum:blocksum(X,0,1,k+1)','quantum:blocksum(X,0,1000001,k)', 'quantum:tensorproduct(X,2,1,k)','quantum:tensorproduct(X,0,32,k)','quantum:tensorproduct(X,0,1/2,k)','quantum:tensorproduct(X,0,infinity,k)','quantum:tensorproduct(X,0,1,2)','quantum:tensorproduct(X,0,1,k+1)','quantum:tensorproduct(X,-1000001,0,k)','quantum:tensorproduct(2,0,1,k)','quantum:tensorproduct(X,0,1,pi)', 'quantum:purity(0|0>)', 'quantum:purity(0I)', 'quantum:purity([1,2;3,4;5,6])', 'quantum:variance(X,0|0>)', 'quantum:variance(X,0I)', 'quantum:variance([0,1;0,0],|0>)', 'quantum:variance(CNOT,|0>)', 'quantum:U3(1,2)', 'quantum:U2(1,2,3)', 'quantum:U1()', 'quantum:U(1,2,3,4)', 'quantum:pauli("")', 'quantum:pauli("i")', 'quantum:pauli("H")', 'quantum:pauli("xyz")', 'quantum:pauli("XXXXXXXXXX")', 'quantum:pauli("X",1)', 'quantum:pauli("X)','quantum:shift(1)', 'quantum:clock(65)', 'quantum:fourier(3/2)', 'quantum:shift(-2)', 'quantum:ptrace(I,0,[2,3])', 'quantum:ptrace(I,0,[0,2])', 'quantum:ptrace(I,0,[1/2,4])', 'quantum:ptrace(I,0,[1024])', 'quantum:ptrace(I,2,[1,2])', 'quantum:ptrace(I,[1,1],[1,2])', 'quantum:ptranspose(I,0,2)', 'quantum:probs(|00>,[0,0])', 'quantum:probs(|00>,2)', 'quantum:probs(|00>,-1)', 'quantum:probs(|00>,1/2)', 'quantum:probs(basis(0,3),0)', 'quantum:probs(0|00>,0)', 'quantum:probs(0identity(4),0)', 'quantum:C^0(X)', 'quantum:C^9(X)', 'quantum:C^2 X', 'quantum:C^n(X)', 'quantum:channel(I/2,vector(X),1)', 'quantum:channel(I/2,vector(CNOT),[0,0])', 'quantum:channel(I/2,vector(2),0)', 'quantum:channel(|0>,vector(X),0)', 'quantum:apply(X,[1,2;3,4;5,6],0)', 'quantum:apply(X,identity(3),0)', 'quantum:controlled(X,0)', 'quantum:controlled(X,9)', 'quantum:controlled(X,1,2)',
    'quantum:controlled(X,2,-1)', 'quantum:controlled(X,1/2)', 'quantum:controlled(X,2,1/2)',
    'quantum:controlled(identity(3),1)', 'quantum:controlled(CNOT,8)', 'quantum:controlled(X,1,0,0)','quantum:|0', 'quantum:|00000000000>', 'quantum:H |00>', 'quantum:normalize(0 |0>)',
    'quantum:ptrace(density(|0>),1)', 'quantum:QFT(0)', 'quantum:H^⊗11', 'quantum:probs(0 |0>)', 'quantum:(H', 'quantum:H$',
    'quantum:apply(X,|0>,1)', 'quantum:apply(CNOT,|00>,[0,0])',
    'quantum:ptrace(density(|0>),18446744073709551616)', 'quantum:comm(H,CNOT)',
    'quantum:\frac{1}', 'quantum:\leftover{1}', 'quantum:\begin{bmatrix}1\end{pmatrix}',
    'quantum:\lVert |0>', 'quantum:ptrace(density(|00>),[0,0])', 'quantum:Tr_{2}(density(|00>))',
    'quantum:basis(3,3)', 'quantum:\sum_{k=0}{k}', 'quantum:\sum_{k=0}_{k=2}{k}',
    'quantum:\begin{bmatrix}1\\[2pt]0\end{bmatrix}', 'quantum:expm([1,2,3;4,5,6])',
    'quantum:evolution(|0>,1)', 'quantum:postselect(X,|0>)', 'quantum:postselect(density(|1>),|0>)',
    'quantum:born(X,0|0>)', 'quantum:probs(0I)', 'quantum:expect(X,identity(3))', 'quantum:ptranspose(I,1)',
    'quantum:evolution([0,1;0,0],1)', 'quantum:evolution(X,i)')
$invalid += @('quantum:reset(|00>,[0,0])', 'quantum:reset(|0>,1)', 'quantum:reset(|0>,-1)', 'quantum:reset(|0>,1/2)', 'quantum:reset(basis(0,3),0)', 'quantum:reset(2)', 'quantum:reset([1,2;3,4;5,6],0)')
$invalid += @('quantum:dephase(|00>,[0,0])', 'quantum:dephase(|0>,1)', 'quantum:dephase(|0>,-1)', 'quantum:dephase(|0>,1/2)', 'quantum:dephase(basis(0,3))', 'quantum:dephase(2)')
$invalid += @('quantum:feedforward(|0>,0,2,X,0)', 'quantum:feedforward(|0>,0,-1,X,0)', 'quantum:feedforward(|0>,0,1/2,X,0)', 'quantum:feedforward(|0>,1,0,X,0)', 'quantum:feedforward(|00>,[0,0],0,X,1)', 'quantum:feedforward(|0>,0,1,X,1)', 'quantum:feedforward(|0>,0,1,CNOT,0)', 'quantum:feedforward(|0>,0,1,2,0)')
$invalid += @('quantum:CP()', 'quantum:CRx(1,2)', 'quantum:CRy()', 'quantum:CRz(1,2)')
$invalid += @('quantum:|2>', 'quantum:<2|', 'quantum:|3>_3', 'quantum:|0>_1', 'quantum:|0>_1025', 'quantum:|+>_3', 'quantum:|2>_3.5', 'quantum:|2>_d', 'quantum:<2|2>_2', 'quantum:<2|_3 |2>_4')
$invalid += @('quantum:SUM(1)', 'quantum:SUM(3/2)', 'quantum:SUM(65)', 'quantum:SUM(32)', 'quantum:SUM(2,0)', 'quantum:SUM(2,65)', 'quantum:SUM(2,3,4)', 'quantum:SUM()')
$invalid += @('quantum:permute(|00>,[0,0])', 'quantum:permute(|00>,[0])', 'quantum:permute(|00>,[0,2])', 'quantum:permute(|00>,[-1,1])', 'quantum:permute(|00>,[0,1/2])', 'quantum:permute(|2>_3,[0,1])', 'quantum:permute(|00>,[0,1],[2,3])', 'quantum:permute(|00>,[0,1],[0,4])', 'quantum:permute(|00>,[0,1],[2,2048])', 'quantum:permute(2,[0])', 'quantum:permute([1,2;3,4;5,6],[0,1],[2,3])')
$invalid += @('quantum:vec(2)', 'quantum:vec(identity(33))', 'quantum:unvec(|00>,3)', 'quantum:unvec(|00>,0)', 'quantum:unvec(|00>,1/2)', 'quantum:unvec(X,2)', 'quantum:|0>>', 'quantum:<<Y|Y>', 'quantum:|X+Y>>')
$invalid += @('quantum:choi(vector())', 'quantum:superop(vector())', 'quantum:choi(vector(2))', 'quantum:superop(vector(2))', 'quantum:choi(vector(I,identity(3)))', 'quantum:superop(vector(I,identity(3)))', 'quantum:choi(vector(identity(33)))', 'quantum:superop(vector(identity(23)))')
$invalid += @('quantum:\begin{Vmatrix}1&0\\0&1\end{Vmatrix}', 'quantum:\begin{Vmatrix}1&0\\0&1\end{Vmatrix}^2', 'quantum:\norm{|0>}_{}', 'quantum:\norm{|0>}_{ }', 'quantum:\norm{|0>}^{}', 'quantum:\norm{X}^{2}_{0}')
$invalid += @('quantum:reflection(0|0>)', 'quantum:reflection(I/2)', 'quantum:reflection(<0|)', 'quantum:reflection([x;1])', 'quantum:reflection([infinity;1])', 'quantum:reflection([interval(1,2);1])', 'quantum:reflection(basis(0,1024))', 'quantum:phase_reflection(|0>,i)', 'quantum:phase_reflection(|0>,infinity)', 'quantum:phase_reflection(|0>,interval(0,1))', 'quantum:phase_reflection(|0>,x)', 'quantum:reflection()', 'quantum:reflection(|0>,pi)', 'quantum:phase_reflection(|0>)', 'quantum:phase_reflection(|0>,0,1)')
$invalid += @('quantum:norm(X,0)', 'quantum:norm(X,-1)', 'quantum:norm(X,1/2)', 'quantum:norm(X,i)', 'quantum:norm(X,-infinity)', 'quantum:norm(X,interval(1,2))', 'quantum:tracenorm([x,0;0,1])', 'quantum:tracenorm([infinity,0;0,1])', 'quantum:‖X‖_0', 'quantum:tracenorm(X,1)', 'quantum:schatten(X)')
$invalid += @('quantum:schmidt_coeffs(I/2,0)', 'quantum:schmidt_coeffs(0|00>,0)', 'quantum:schmidt_coeffs(|00>,2)', 'quantum:schmidt_coeffs(|00>,[0,0])', 'quantum:schmidt_coeffs(|00>,-1)', 'quantum:schmidt_coeffs(|00>,1/2)', 'quantum:schmidt_coeffs(|0>_3,0)', 'quantum:schmidt_coeffs(|00>,0,[2,3])', 'quantum:schmidt_coeffs(|00>,0,[0,4])', 'quantum:schmidt_coeffs(|00>,0,[1/2,8])', 'quantum:schmidt_coeffs(|00>,0,2)', 'quantum:schmidt_coeffs(|00>)', 'quantum:schmidt_coeffs(|00>,0,[2,2],0)', 'quantum:schmidt_coeffs([x;0;0;1],0)', 'quantum:schmidt_coeffs([interval(1,2);0;0;1],0)')
$invalid += @('quantum:XXPlusYY()', 'quantum:XXMinusYY()', 'quantum:XXPlusYY(1,2,3)', 'quantum:XXMinusYY(1,2,3)')
$invalid += @('quantum:fSim()', 'quantum:fSim(pi)', 'quantum:fSim(1,2,3)')
$invalid += @('quantum:diffusion(0)', 'quantum:diffusion(10)', 'quantum:diffusion(1/2)', 'quantum:phaseoracle(2,-1)', 'quantum:phaseoracle(2,4)', 'quantum:phaseoracle(2,[1,1])', 'quantum:phaseoracle(2,1/2)', 'quantum:phaseoracle(2,X)', 'quantum:phaseoracle(0,0)', 'quantum:phaseoracle(10,0)')
$invalid += @('quantum:oracle([0,1,0])', 'quantum:oracle([0,2])', 'quantum:oracle([-1,0])', 'quantum:oracle([0,1/2])', 'quantum:oracle(X)', 'quantum:oracle(0)', 'quantum:oracle([0,1],0)', 'quantum:oracle([0,1],9)', 'quantum:oracle([0,1],1/2)', 'quantum:oracle([0,1,2,3],8)', 'quantum:oracle([0,1],1,2)')
$invalid += @('quantum:modmul(2,6)', 'quantum:modmul(0,5)', 'quantum:modmul(5,5)', 'quantum:modmul(-1,5)', 'quantum:modmul(1/2,5)', 'quantum:modmul(1,1)', 'quantum:modmul(2,513)', 'quantum:modmul(1,5/2)', 'quantum:modmul(X,5)')
$invalid += @('quantum:destroy(1)', 'quantum:create(513)', 'quantum:numberop(0)', 'quantum:destroy(3/2)', 'quantum:create(-2)', 'quantum:numberop(X)', 'quantum:destroy(3,1)')
$invalid += @('quantum:fdestroy(0,0)', 'quantum:fcreate(10,0)', 'quantum:fdestroy(3,-1)', 'quantum:fdestroy(3,3)', 'quantum:fcreate(3,1/2)', 'quantum:fdestroy(3/2,0)', 'quantum:fdestroy(3,0,1)', 'quantum:fcreate(3)')
foreach ($spinOp in @('Jx','Jy','Jz','Jplus','Jminus')) {
    foreach ($badSpin in @('0','-1','1/3','32','i','X')) { $invalid += "quantum:${spinOp}($badSpin)" }
    $invalid += "quantum:${spinOp}()"
    $invalid += "quantum:${spinOp}(1,2)"
}
$fixedQuantumCalls = @(
    'dagger(X)', 'density(|0>)', 'trace(I)', 'norm(|0>)', 'normalize(|0>)',
    'vec(X)', 'unvec(|00>,2)', 'superop(vector(I))', 'choi(vector(I))',
    'comm(X,Y)', 'anticomm(X,Y)', 'tensor(X,Y)', 'directsum(X,Y)',
    'expect(X,|+>)', 'purity(|0>)', 'variance(X,|0>)', 'tensorpow(X,2)',
    'QFT(2)', 'shift(3)', 'clock(3)', 'fourier(3)', 'basis(0,2)',
    'expm(X)', 'sinhc(0)', 'evolution(X,1)', 'born(density(|0>),|0>)',
    'postselect(density(|0>),|0>)', 'transpose(X)', 'conjugate(Y)',
    'apply(X,|0>,0)', 'feedforward(|0>,0,1,X,0)', 'phaseoracle(2,1)',
    'diffusion(2)', 'modmul(2,5)'
)
foreach ($call in $fixedQuantumCalls) {
    $invalid += 'quantum:' + $call.Substring(0,$call.Length-1) + ',0)'
    $invalid += 'quantum:' + $call.Substring(0,$call.IndexOf('(')) + '()'
}
$invalid += @('quantum:\hat{}', 'quantum:\hat', 'quantum:\widehat{X+Y', 'quantum:\tilde{X}')
$invalid += @('quantum:J_+()', 'quantum:J_{-}(1,2)', 'quantum:J_{+}(1/3)', 'quantum:J_{+}(1', 'quantum:X_+(1)')
$invalid += @('quantum:|↑>_3', 'quantum:|↑ψ>', 'quantum:|↓2>', 'quantum:|↑↑↑↑↑↑↑↑↑↑↑>', 'quantum:\ket{\Uparrow}')
$invalid += @('quantum:|+++++++++++>', 'quantum:|+2>', 'quantum:|+-> _4', 'quantum:|+i+>')
$invalid += @('quantum:<0|X+|0>', 'quantum:<0|X|0', 'quantum:<0|X @ X|0>', 'quantum:<0|density(|0>)|00>')
$invalid += @('quantum:entropy(0|0>)', 'quantum:entropy(0I)', 'quantum:entropy(-I)', 'quantum:entropy([1,2;2,1])', 'quantum:entropy([1,i;i,1])', 'quantum:entropy([1,1;0,1])', 'quantum:entropy(identity(65))', 'quantum:entropy([1,2;3,4;5,6])', 'quantum:entropy(2)', 'quantum:entropy()', 'quantum:entropy(I,2,3)')
$invalid += @('quantum:entropy(I,1)', 'quantum:entropy(I,0)', 'quantum:entropy(I,-2)', 'quantum:entropy(I,1/2)', 'quantum:entropy(I,i)', 'quantum:entropy(I,X)', 'quantum:entropy(|0>,1)')
$invalid += @('quantum:tracedistance(0|0>,|0>)', 'quantum:tracedistance(I,-I)', 'quantum:tracedistance([1,2;2,1],I)', 'quantum:tracedistance([1,i;i,1],I)', 'quantum:tracedistance(|0>,|00>)', 'quantum:tracedistance(identity(65),identity(65))', 'quantum:tracedistance(I)', 'quantum:tracedistance(I,I,I)', 'quantum:tracedistance(1,I)')
$invalid += @('quantum:fidelity(0|0>,|0>)', 'quantum:fidelity(I,-I)', 'quantum:fidelity([1,2;2,1],I)', 'quantum:fidelity([1,i;i,1],I)', 'quantum:fidelity(|0>,|00>)', 'quantum:fidelity(identity(65),identity(65))', 'quantum:fidelity(I)', 'quantum:fidelity(I,I,I)')
$invalid += @('quantum:X⁻', 'quantum:X²⁻¹', 'quantum:²X', 'quantum:pauli("X²")')
foreach($noise in @('amplitude_damping','phase_damping','depolarizing')) {
    foreach($parameter in @('-1/100','3/2','i','infinity','x','I','interval(0,1)')) { $invalid += "quantum:${noise}($parameter)" }
    $invalid += "quantum:${noise}()"
    $invalid += if($noise -eq 'amplitude_damping'){"quantum:${noise}(0,1,0)"}else{"quantum:${noise}(0,1)"}
}
$invalid += 'quantum:phase_amplitude_damping()','quantum:phase_amplitude_damping(0)','quantum:phase_amplitude_damping(0,0,0,0)','quantum:phase_amplitude_damping(1/2,1/2+1/10^100)','quantum:phase_amplitude_damping(3/4,1/2)'
foreach($parameter in @('-1/100','1001/1000','i','infinity','x','I','interval(0,1)')) {
    $invalid += "quantum:amplitude_damping(1/2,$parameter)","quantum:phase_amplitude_damping($parameter,0)","quantum:phase_amplitude_damping(0,$parameter)","quantum:phase_amplitude_damping(0,0,$parameter)"
}
$invalid += 'quantum:amplitude_damping(1001/1000)','quantum:phase_damping(1001/1000)','quantum:depolarizing(4001/3000)'
$invalid += 'quantum:amplitude_damping(1+1/10^100)','quantum:depolarizing(4/3+1/10^100)'
$invalid += @('quantum:ptm()','quantum:ptm(vector(I),0)','quantum:ptm(I)','quantum:ptm(vector(identity(3)))','quantum:ptm(vector([1,0,0;0,1,0]))','quantum:ptm(vector(I,CNOT))','quantum:ptm(vector(identity(32)))','quantum:ptm(vector(1))')
$invalid += @('quantum:chi()','quantum:chi(vector(I),0)','quantum:chi(I)','quantum:chi(vector(identity(3)))','quantum:chi(vector([1,0,0;0,1,0]))','quantum:chi(vector(I,CNOT))','quantum:chi(vector(identity(32)))','quantum:chi(vector(1))')
$invalid += @('quantum:R()','quantum:R(pi)','quantum:R(pi,0,1)','quantum:R(,0)')
$invalid += @('quantum:logm()','quantum:logm(X,Y)','quantum:logm(2)','quantum:logm(|0>)','quantum:logm(identity(65))','quantum:logm(0I)','quantum:logm(density(|0>))','quantum:logm([1,1;1,1])','quantum:logm([1,1;0,1])','quantum:logm([infinity,0;0,1])','quantum:logm([1,interval(0,1);interval(0,1),1])')
$invalid += @('quantum:sqrt()','quantum:sqrt(X,Y)','quantum:sqrt(|0>)','quantum:sqrt(identity(65))','quantum:sqrt([1,1;0,1])','quantum:sqrt([2,1;0,2])','quantum:(H*S)^(i)','quantum:(H*S)^1000000.5','quantum:(H*S)^interval(1/4,1/2)')
$invalid += @('quantum:√','quantum:∛','quantum:∜','quantum:√()','quantum:√*X','quantum:√(X,Y)','quantum:√|0>','quantum:pauli("X√Y")')
$invalid += 'quantum:' + ('√' * 257) + 'X'
$invalid += @('quantum:sqrt([0,1e200;1e200i,0])','quantum:[1,1;1,1]^(-1/2)','quantum:sqrt([1,interval(0,1);interval(0,1),1])')
foreach ($measure in @('negativity','lognegativity')) {
    foreach ($arguments in @('','I','0|00>,0','-identity(4),0','[1,2;0,0],0','[2,0;0,-1],0','|00>,2','|00>,[0,0]','|00>,-1','|00>,1/2','basis(0,3),0','|00>,0,[2,3]','|0000000>,0','|00>,0,[2,2],0')) {
        $invalid += "quantum:${measure}($arguments)"
    }
}
$invalid += @('quantum:|(X+Y)>','quantum:|(X+Y>>','quantum:<<()|Y>>','quantum:|(1)>>','quantum:|(pauli("X Y"))>>','quantum:<<X|(pauli("X Y"))>>','quantum:<<(pauli("X Y"))|X>>','quantum:|(density(|0>))>','quantum:<<(X)|identity(4)|(Y)>')
$invalid += 'quantum:' + ('|(' * 130) + 'X' + (')>>' * 130)
$invalid += @('quantum:lindblad_dissipator()','quantum:lindblad_dissipator(X,Y)','quantum:lindblad_dissipator(1)','quantum:lindblad_dissipator(|0>)','quantum:lindblad_dissipator(identity(17))','quantum:liouvillian()','quantum:liouvillian(X,vector(Z),1)','quantum:liouvillian([0,1;0,0])','quantum:liouvillian(iX)','quantum:liouvillian(X,Z)','quantum:liouvillian(X,vector(CNOT))','quantum:liouvillian(X,vector(1))','quantum:liouvillian(identity(17))')
$invalid += @('quantum:spre()','quantum:spost()','quantum:spre(X,Y)','quantum:spost(X,Y)','quantum:sprepost(X)','quantum:sprepost(X,Y,Z)','quantum:spre(1)','quantum:spost(|0>)','quantum:spre([1,2,3;4,5,6])','quantum:spre(identity(17))','quantum:spost(identity(17))','quantum:sprepost(X,1)','quantum:sprepost(identity(17),X)','quantum:sprepost(X,identity(17))')
$invalid += @('quantum:controlled(X,2,"1")','quantum:controlled(X,1,"01")','quantum:controlled(X,2,"")','quantum:controlled(X,2,"02")','quantum:controlled(X,2," 01")','quantum:controlled(X,2,"0 1")','quantum:controlled(X,2,"01)','quantum:controlled(X,9,"000000000")','quantum:controlled(X,2,"01",0)','quantum:controlled(X,1/2,"0")')
$invalid += @('quantum:paulivec()','quantum:paulivec(I,2)','quantum:paulivec(identity(3))','quantum:paulivec(identity(32))','quantum:paulivec(|0>)','quantum:paulivec(1)','quantum:unpaulivec(I)','quantum:unpaulivec(|0>)','quantum:unpaulivec([1,2,3,4])','quantum:unpaulivec(basis(0,9))','quantum:unpaulivec(basis(0,1024))','quantum:unpaulivec()','quantum:unpaulivec(|00>,2)')
$invalid += ('quantum:pauli("X'+[char]0xa0+'Y")'),('quantum:pauli("X'+[char]0x2009+'Y")')
$invalid += @('quantum:thermal_relaxation()','quantum:thermal_relaxation(1,1)','quantum:thermal_relaxation(1,1,0,0,0)','quantum:thermal_relaxation(0,1,1)','quantum:thermal_relaxation(1,0,1)','quantum:thermal_relaxation(-1,1,1)','quantum:thermal_relaxation(1,-1,1)','quantum:thermal_relaxation(1,1,-1)','quantum:thermal_relaxation(1,3,1)','quantum:thermal_relaxation(1,2+1/10^100,1)','quantum:thermal_relaxation(1,infinity,1)','quantum:thermal_relaxation(1,1,infinity)','quantum:thermal_relaxation(i,1,1)','quantum:thermal_relaxation(1,x,1)','quantum:thermal_relaxation(1,1,I)','quantum:thermal_relaxation(interval(1,2),1,1)','quantum:thermal_relaxation(1,1,0,-1)','quantum:thermal_relaxation(1,1,0,2)')
$invalid += @('quantum:bloch()','quantum:bloch(|0>,1)','quantum:bloch(0|0>)','quantum:bloch(0I)','quantum:bloch(-I)','quantum:bloch([1,2;2,1])','quantum:bloch([1,i;i,1])','quantum:bloch(|00>)','quantum:bloch(identity(3))','quantum:bloch(x|0>)')
$invalid += @('quantum:bloch(|00>,2)','quantum:bloch(|00>,-1)','quantum:bloch(|00>,1/2)','quantum:bloch(|00>,[0,1])','quantum:bloch(|0>,0,0)','quantum:bloch(identity(3),0)','quantum:bloch([1,2;3,4;5,6;7,8],0)','quantum:bloch(0|00>,0)','quantum:bloch(-identity(4),0)')
foreach ($symbol in @('×','⋅','·','∙','∗','÷','∕','⁄')) {
    $invalid += "quantum:${symbol}X", "quantum:X${symbol}", "quantum:X${symbol}${symbol}Y", ('quantum:pauli("X'+$symbol+'Y")')
}
foreach ($expression in $invalid) {
    $result = Evaluate $expression
    if ($result.Code -ne 2 -or !$result.Error) { Write-Output "FAIL invalid input $expression : $($result.Text) [$($result.Code)] $($result.Error)"; $failures++ }
    else { Write-Output "PASS rejects $expression" }
}
$jsonChecks = @(
    @('quantum:H', 2, 2, $false),
    @('quantum:expm([0,1,0;0,0,1;1,0,0])', 3, 3, $true),
    @('1 m to cm', 0, 0, $false)
)
foreach ($check in $jsonChecks) {
    $result = Evaluate $check[0] '--json'
    $data = $result.Text | ConvertFrom-Json
    if ($result.Code -ne 0 -or $data.rows -ne $check[1] -or $data.columns -ne $check[2] -or $data.approximate -ne $check[3] -or !$data.text -or $data.cells.Count -ne $check[1]) {
        Write-Output "FAIL structured output $($check[0])"; $failures++
    } else { Write-Output "PASS structured output $($check[0])" }
}
$numericChecks = @(
    @('quantum:im(tr(logm(T)))',([Math]::PI/4)),
    @('quantum:norm(vec(ECR-Rzx(-pi/4)*(X @ I)*Rzx(pi/4)))',0.0),
    @('quantum:expect(Y,unvec(expm(liouvillian(0I,vector(destroy(2))))vec(density(|i>)),2))',[Math]::Exp(-0.5)),
    @('quantum:expect(X,unvec(expm(liouvillian(Z/2))vec(density(|+>)),2))',[Math]::Cos(1)),
    @('quantum:expect(Y,channel(density(|i>),thermal_relaxation(20,30,4,1/5)))',[Math]::Exp(-4.0/30)),
    @('quantum:expect(Z,channel(density(|1>),thermal_relaxation(20,30,4,1/5)))',(1-2*(0.2+0.8*[Math]::Exp(-4.0/20)))),
    @('quantum:<0|U(pi/3,0,0)|0>', ([Math]::Sqrt(3)/2)),
    @('quantum:tr(U3(pi/3,pi/4,pi/6)†U3(pi/3,pi/4,pi/6))', 2.0)
)
foreach ($check in $numericChecks) {
    $result = Evaluate $check[0] '--json --approx'
    $data = $result.Text | ConvertFrom-Json
    $number = 0.0
    $parsed = [double]::TryParse($data.text.Replace('−','-'), [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$number)
    if ($result.Code -ne 0 -or !$data.approximate -or !$parsed -or [Math]::Abs($number-$check[1]) -gt 1e-14) {
        Write-Output "FAIL numerical evaluation $($check[0]): $($result.Text)"; $failures++
    } else { Write-Output "PASS numerical evaluation $($check[0])" }
}
$entropyChecks = @(
    @('\lVert X\rVert₁',2.0),
    @('\begin{Vmatrix}3&0\\0&4\end{Vmatrix}_1',7.0),
    @('\begin{Vmatrix}3&0\\0&4\end{Vmatrix}_{\mathrm{F}}',5.0),
    @('\lVert [3,0;0,4]\rVert^{2}_{1}',49.0),
    @('\norm{[3,0;0,4]}_{ F }',5.0),
    @('\Biggl\Vert X\Biggr\Vert_{\infty}',1.0),
    @('tracenorm(X)',2.0),
    @('spectralnorm(H)',1.0),
    @('frobeniusnorm([3,0;0,4])',5.0),
    @('norm([3,0;0,4],1)',7.0),
    @('norm([3,0;0,4],2)',5.0),
    @('norm([3,0;0,4],infinity)',4.0),
    @('schatten([3,0;0,4],3)',[Math]::Pow(91,1.0/3)),
    @('tracenorm([0,2;0,0])',2.0),
    @('spectralnorm([0,2;0,0])',2.0),
    @('tracenorm([1,0,0;0,2,0])',3.0),
    @('tracenorm(3+4i)',5.0),
    @('tracenorm([3,4])',5.0),
    @('spectralnorm(<i|)',1.0),
    @('tracenorm(0I)',0.0),
    @('tracenorm(density(|0>)-density(|+>))',[Math]::Sqrt(2)),
    @('‖X‖₁',2.0),
    @('‖X‖₂',[Math]::Sqrt(2)),
    @('∥X∥_1',2.0),
    @('\lVert X\rVert_1',2.0),
    @('\left\|X\right\|_{\infty}',1.0),
    @('\norm{X}_F',[Math]::Sqrt(2)),
    @('\norm{X}_{\infty}',1.0),
    @('<0|schmidt_coeffs((|00>+|11>)/sqrt(2),0)',[Math]::Sqrt(0.5)),
    @('<1|schmidt_coeffs(3|00>+4i|11>,1)',0.6),
    @('<0|schmidt_coeffs(|+>@|i>,0)',1.0),
    @('<1|schmidt_coeffs(|000>+|111>,[2,0])',[Math]::Sqrt(0.5)),
    @('<0|schmidt_coeffs(|0>_2@|0>_3+|1>_2@|2>_3,0,[2,3])',[Math]::Sqrt(0.5)),
    @('schmidt_coeffs(|00>,[0,1])',1.0),
    @('re(tr(√√X))',(1+[Math]::Sqrt(0.5))),
    @('im(tr(√√X))',[Math]::Sqrt(0.5)),
    @('negativity((|00>+|11>)/sqrt(2),0)',0.5),
    @('lognegativity((|00>+i|11>)/sqrt(2),1)',1.0),
    @('negativity((sqrt(3)|00>+|11>)/2,0)',([Math]::Sqrt(3)/4)),
    @('negativity(|+> @ |i>,0)',0.0), @('negativity(identity(4),0)',0.0),
    @('negativity((density(|00>)+density(|11>))/2,0)',0.0),
    @('negativity(density((|00>+|11>)/sqrt(2))/2+identity(4)/8,0)',0.125),
    @('lognegativity(density((|00>+|11>)/sqrt(2))/2+identity(4)/8,0)',([Math]::Log(1.25,2))),
    @('negativity(density((|00>+|11>)/sqrt(2))/3+identity(4)/6,0)',0.0),
    @('negativity((S @ H)(|00>+|11>)/sqrt(2),0)',0.5),
    @('negativity((|000>+|111>)/sqrt(2),[0,2])',0.5),
    @('negativity((|000>+|111>)/sqrt(2),[0,1,2])',0.0),
    @('negativity((basis(0,9)+basis(4,9)+basis(8,9))/sqrt(3),0,[3,3])',1.0),
    @('lognegativity((basis(0,9)+basis(4,9)+basis(8,9))/sqrt(3),0,[3,3])',([Math]::Log(3,2))),
    @('negativity((basis(0,6)+i*basis(4,6))/sqrt(2),0,[2,3])',0.5),
    @('negativity(1e200*(|00>+|11>),0)',0.5),
    @('negativity((|000000>+|111111>)/sqrt(2),[0,1,2])',0.5),
    @('negativity(|000000>,0)',0.0),
    @('entropy(I/2)',1.0), @('entropy(identity(4)/4)',2.0), @('entropy(7I)',1.0),
    @('entropy(density(|i>))',0.0), @('entropy(ptrace(density((|00>+|11>)/sqrt(2)),0))',1.0),
    @('entropy([3/4,0;0,1/4])',0.8112781244591328),
    @('entropy(QFT(2)[1/2,0,0,0;0,1/4,0,0;0,0,1/8,0;0,0,0,1/8]QFT(2)†)',1.75),
    @('entropy(I/4+density(|i>)/2)',0.8112781244591328),
    @('entropy(identity(64))',6.0), @('entropy(I,2)',1.0),
    @('entropy(I,e)',[Math]::Log(2)), @('entropy(I,10)',[Math]::Log10(2)),
    @('entropy(identity(3),3)',1.0), @('entropy(I,4)',0.5),
    @('tracedistance(|0>,|0>)',0.0), @('tracedistance(|0>,|1>)',1.0),
    @('tracedistance(|0>,|+>)',[Math]::Sqrt(0.5)), @('tracedistance(|i>,|-i>)',1.0),
    @('tracedist(3|i>,density(|i>))',0.0), @('tracedistance(I/2,|i>)',0.5),
    @('tracedistance(I/2,[3/4,0;0,1/4])',0.25),
    @('tracedistance(I/2,I/4+density(|i>)/2)',0.25),
    @('tracedistance([1/2,0,0;0,1/2,0;0,0,0],[0,0,0;0,1/2,0;0,0,1/2])',0.5),
    @('tracedistance(QFT(2)|00>,QFT(2)|01>)',1.0),
    @('tracedistance(dephase(|+>),dephase(|->))',0.0),
    @('tracedistance(|0> @ |i>,|+> @ |i>)',[Math]::Sqrt(0.5)),
    @('fidelity(|0>,|0>)',1.0), @('fidelity(|0>,|1>)',0.0), @('fidelity(|0>,|+>)',0.5),
    @('fidelity(3|i>,density(|i>))',1.0), @('fidelity(|i>,I/2)',0.5),
    @('fidelity(I/2,|i>)',0.5), @('fidelity(I/2,I/2)',1.0),
    @('fidelity([3/4,0;0,1/4],[1/4,0;0,3/4])',0.75),
    @('fidelity((I+Z/2)/2,(I+X/2)/2)',0.875),
    @('fidelity((I+Y/2)/2,(I+Z/2)/2)',0.875),
    @('fidelity(density(|i>),density(|0>))',0.5),
    @('fidelity(density((|00>+i|11>)/sqrt(2)),density((|00>+i|11>)/sqrt(2)))',1.0),
    @('fidelity(dephase(|+>),dephase(|->))',1.0)
)
foreach ($check in $entropyChecks) {
    $result=Evaluate ('quantum:'+$check[0]) '--json'
    $data=$result.Text | ConvertFrom-Json
    $number=0.0
    $parsed=[double]::TryParse($data.text,[Globalization.NumberStyles]::Float,[Globalization.CultureInfo]::InvariantCulture,[ref]$number)
    $tolerance=if($check[0].StartsWith('fidelity(')){5e-7}else{2e-10}
    if($result.Code -ne 0 -or !$data.approximate -or !$parsed -or [Math]::Abs($number-$check[1]) -gt $tolerance) {
        Write-Output "FAIL entropy $($check[0]): $($result.Text) $($result.Error)";$failures++
    } else {Write-Output "PASS entropy $($check[0])"}
}
$chartChecks=@(
    @('quantum:probs((|00>+|11>)/sqrt(2))',@(0.5,0,0,0.5)),
    @('quantum:probs((|0>+sqrt(2)*|1>)/sqrt(3))',@((1.0/3),(2.0/3))),
    @('quantum:probs(H^⊗7 |0000000>)',@()),
    @('quantum:[-1;2]',@()), @('quantum:[1;1]',@())
)
foreach($check in $chartChecks) {
    $result=Evaluate $check[0] '--json --probabilities';$data=$result.Text | ConvertFrom-Json
    $valid=$result.Code -eq 0 -and $data.probabilities.Count -eq $check[1].Count
    if($valid) {for($k=0;$k -lt $check[1].Count;$k++) {if([Math]::Abs($data.probabilities[$k]-$check[1][$k]) -gt 1e-12){$valid=$false}}}
    if(!$valid){Write-Output "FAIL probability chart $($check[0]): $($result.Text)";$failures++}else{Write-Output "PASS probability chart $($check[0])"}
}
$blochChecks=@(@('quantum:bloch(|i>)',@(0,1,0)),@('quantum:bloch(I/2)',@(0,0,0)),@('quantum:bloch(channel(density(|i>),amplitude_damping(3/4)))',@(0,0.5,0.75)),@('quantum:[2;0;0]',@()),@('quantum:[1;0]',@()))
$blochChecks += ,@('quantum:bloch(Ry(pi/3)|0>)',@(([Math]::Sqrt(3)/2),0,0.5),'--approx')
$blochChecks += ,@('quantum:bloch(channel(density(|i>),thermal_relaxation(20,30,4,1/5)))',@(0,[Math]::Exp(-4.0/30),(0.6*(1-[Math]::Exp(-4.0/20)))),'--approx')
foreach($check in $blochChecks) {
    $flags='--json --bloch';if($check.Count -gt 2){$flags+=' '+$check[2]}
    $result=Evaluate $check[0] $flags;$data=$result.Text | ConvertFrom-Json
    $valid=$result.Code -eq 0 -and $data.bloch.Count -eq $check[1].Count
    if($valid){for($k=0;$k -lt $check[1].Count;$k++){if([Math]::Abs($data.bloch[$k]-$check[1][$k]) -gt 1e-12){$valid=$false}}}
    if(!$valid){Write-Output "FAIL Bloch output $($check[0]): $($result.Text)";$failures++}else{Write-Output "PASS Bloch output $($check[0])"}
}
Write-Output "$($cases.Count + $invalid.Count + $jsonChecks.Count + $numericChecks.Count + $entropyChecks.Count + $chartChecks.Count + $blochChecks.Count) checks; $failures failures"
if ($failures) { throw 'Quantum regression checks failed.' }
