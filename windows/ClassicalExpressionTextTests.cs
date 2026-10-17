using System;
using System.Text;
using N=ClassicalCircuit.ExpressionNode;
static class ClassicalExpressionTextTests {
 static int checks;
 static void Check(bool value){checks++;if(!value)throw new Exception("Expression text check "+checks+" failed.");}
 static void Reject(Action action){bool caught=false;try{action();}catch(ArgumentException){caught=true;}catch(System.IO.InvalidDataException){caught=true;}Check(caught);}
 static ClassicalCircuit.Document Context(){return new ClassicalCircuit.Document{Version=3,Qubits=0,Registers=new[]{new ClassicalCircuit.Register{Name="c",Size=3},new ClassicalCircuit.Register{Name="rest",Size=61}},OutputBits=new int[0],Steps=new ClassicalCircuit.Step[0]};}
 static N Parse(string text,int width){return ClassicalExpressionText.Parse(text,Context(),width);}
 static string Format(N n){return ClassicalExpressionText.Format(n);}
 static void Roundtrip(N n,int width){string text=Format(n);Check(Format(Parse(text,width))==text);}
 static int Main(){try {
  Check(Format(Parse("c[0] ^ c[1] & c[2]",1))=="(read(0) ^ (read(1) & read(2)))");
  Check(Format(Parse("c == 1 || c == 2",1))=="((read(0,1,2) == \"001\") | (read(0,1,2) == \"010\"))");
  Check(Format(Parse("3 == 7",1))=="(\"011\" == \"111\")");
  Check(Format(Parse("rest[60]",1))=="read(63)");
  Check(Format(Parse("c[1:2]",2))=="read(1,2)");
  Check(Format(Parse("read(2,0,2)",3))=="read(2,0,2)");
  Check(Format(Parse("7",3))=="\"111\"");
  Check(Format(Parse("c << 64",3))=="(read(0,1,2) << \"1000000\")");
  foreach(string op in new[]{"&","|","^","<<",">>","==","!=","<",">","<=",">="})Roundtrip(Parse("c "+op+" 1",op=="&" || op=="|" || op=="^" || op=="<<" || op==">>" ? 3 : 1),op=="&" || op=="|" || op=="^" || op=="<<" || op==">>" ? 3 : 1);
  foreach(string text in new[]{"true && !false","~c[0]","(c[0] | c[1]) & c[2]","c[0] != c[1]","read(63)","0"})Roundtrip(Parse(text,1),1);
  Roundtrip(Parse(UInt64.MaxValue.ToString(),64),64);
  foreach(string bad in new[]{"","unknown","c[3]","rest[61]","read(64)","read()","c[-1]","c[2:0]","read(0,,1)","18446744073709551616","-1","c + 1","c &", "c[0] trailing", "\"\"", "\"102\"",new string('(',130)+"0"+new string(')',130),new string(' ',65537)})Reject(()=>Parse(bad,1));
  Reject(()=>Parse("c & rest",3));Reject(()=>Parse("c && true",1));Reject(()=>Parse("!c",1));Reject(()=>Parse("8",3));Reject(()=>Parse("\"01\"",1));
  Reject(()=>Parse("\"01 \"",2));
  var deep=new N{Kind="Read",Bits=new[]{0}};for(int k=1;k<32;k++)deep=new N{Kind="Complement",Left=deep};Roundtrip(deep,1);
  Reject(()=>Parse("~("+Format(deep)+")",1));
  var broad=new N{Kind="Read",Bits=new[]{0}};for(int k=0;k<8;k++)broad=new N{Kind="Binary",Operator="Or",Left=broad,Right=broad};Roundtrip(new N{Kind="Complement",Left=broad},1);
  Reject(()=>Parse("("+Format(broad)+" | read(0))",1));
  var parsed=Parse("c ^ 1",3);var document=Context();document.Steps=new[]{new ClassicalCircuit.Step{Kind="Assign",Wires=new[]{0,1,2},ClassicalValue=parsed}};
  var circuit=ClassicalCircuit.From(document);Check(Encoding.UTF8.GetString(NumericalSampling.RequestExact(0,64,new[]{2,1,0},circuit.SamplingGates())).StartsWith("QEXACT2\n"));
  Console.WriteLine("PASS: "+checks+" classical expression text checks.");return 0;
 }catch(Exception e){Console.Error.WriteLine(e);return 1;}}
}
