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
 static int Main(string[] args){try {
  Check(Format(Parse("rotl(c, -1)",3))=="rotl_signed(read(0,1,2), -1)");
  Check(Format(Parse("rotl_signed(c, 1)",3))=="rotl_signed(read(0,1,2), 1)");
  Check(Format(Parse("popcount(c) == 1",1))=="(popcount(read(0,1,2)) == 1)");
  Check(Format(Parse("1 == popcount(c)",1))=="(1 == popcount(read(0,1,2)))");
  Check(Parse("popcount(c)",64).Kind=="PopulationCount");
  foreach(string text in new[]{"popcount(c) == 2","popcount(read(63)) != 0","popcount(\"111\") == popcount(7)"})Roundtrip(Parse(text,1),1);
  foreach(string text in new[]{"rotl(c, 1)","rotr(c, -1)","rotl(c, -9223372036854775808)","rotr(c, 18446744073709551615)","rotl_signed(c, c)","rotr_signed(c, 1)","rotl(c, popcount(c))"})Roundtrip(Parse(text,3),3);
  var signedRotation=Parse("rotl(c, -1)",3);Check(signedRotation.DistanceInterpretation=="Signed" && signedRotation.Right.Width==64 && signedRotation.Right.Value==UInt64.MaxValue.ToString());
  signedRotation=Parse("rotl_signed(c, 1)",3);Check(signedRotation.Right.Width==64 && signedRotation.Right.Value=="1");
  var imported=new N{Kind="Rotate",RotationDirection="Right",DistanceInterpretation="Signed",Left=new N{Kind="Read",Bits=new[]{0,1,2}},Right=new N{Kind="Constant",Width=8,Value="255"}};Roundtrip(imported,3);
  foreach(string bad in new[]{"popcount()","popcount(c, 1)","rotl(c)","rotr(c, 1, 2)","rotl(c, -9223372036854775809)","rotl(c, --1)","rotr(c, -c)","rotl(c, -1 << 1)"})Reject(()=>Parse(bad,3));
  Reject(()=>Parse("popcount(c)",3));
  Check(Format(Parse("c[0] ^ c[1] & c[2]",1))=="(read(0) ^ (read(1) & read(2)))");
  Check(Format(Parse("c == 1 || c == 2",1))=="((read(0,1,2) == \"001\") || (read(0,1,2) == \"010\"))");
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
  foreach(string text in new[]{"int[3](c) < 0","uint[3](c) > 3","6 / int[3](c) == 3","int[3](c) + 2 * 3 == 7","int[3](c) - 1 >= -2","-int[3](c) != 0","int[3](255) < 0","int(-9223372036854775808) == -9223372036854775808","uint(18446744073709551615) == 18446744073709551615","int[3](c) % 2 == 1","int[3](c) < 0 || uint[3](c) == 0","!(int[3](c) < 0)","int[3](\"111\") < 0"}) {
   var typed=Parse(text,1);Check(ClassicalExpressionText.RequiredVersion(typed)==4);Roundtrip(typed,1);
  }
  Check(Format(Parse("int[3](c) + 2 * 3 == 7",1))=="((int[3](read(0,1,2)) + (int(2) * int(3))) == int(7))");
  foreach(string bad in new[]{"int[0](c) < 0","int[65](c) < 0","int[8](c) < 0","int[3](c) + c == 1","int[3](c) & int[3](c)","int[3](c)","-9223372036854775809 == 0","int[3](popcount(c)) == 0","int[3](\"11\") == 0"})Reject(()=>Parse(bad,1));
  var typedLeaf=new N{Kind="IntegerConstant",Signedness="Signed",Width=0,Value="0"};
  var typedDeep=typedLeaf;for(int k=0;k<30;k++)typedDeep=new N{Kind="IntegerCast",Signedness="Signed",Width=0,Left=typedDeep};
  Roundtrip(new N{Kind="IntegerCompare",Operator="Equal",Left=typedDeep,Right=typedLeaf},1);
  var typedBroad=typedLeaf;for(int k=0;k<7;k++)typedBroad=new N{Kind="IntegerBinary",Operator="Add",Left=typedBroad,Right=typedBroad};
  Roundtrip(new N{Kind="Complement",Left=new N{Kind="IntegerCompare",Operator="Equal",Left=typedBroad,Right=typedBroad}},1);
  Check(ClassicalExpressionText.RequiredVersion(Parse("c == 1",1))==3);
  foreach(string text in new[]{"int[3](c) != 0 && 6 / int[3](c) == 3","int[3](c) == 0 || 6 / int[3](c) == 3","true || false && true"}) {
   var node=Parse(text,1);Check(node.Kind=="Logical");Roundtrip(node,1);
   var d=Context();d.Version=4;d.OutputBits=new[]{3};d.Steps=new[]{new ClassicalCircuit.Step{Kind="Assign",Wires=new[]{3},ClassicalValue=node}};
   var saved=ClassicalCircuit.From(d);var reopened=ClassicalCircuit.Load(saved.Serialize());Check(reopened.Serialize()==saved.Serialize());
   Check(Format(reopened.Snapshot().Steps[0].ClassicalValue)==Format(node));
   foreach(int oldVersion in new[]{2,3}){d.Version=oldVersion;Reject(()=>ClassicalCircuit.From(d));}d.Version=4;
   foreach(string badOp in new[]{"Xor","Equal","1"}){node.Operator=badOp;Reject(()=>ClassicalCircuit.From(d));}node.Operator=text.Contains("&&") && !text.StartsWith("true") ? "And" : "Or";
   if(args.Length>0)foreach(bool exact in new[]{true,false}) {
    var steps=reopened.SamplingGates();byte[] request=exact ? NumericalSampling.RequestExact(0,64,new[]{3},steps) : NumericalSampling.RequestClassical(0,64,10000,1731,new[]{3},steps);
    string result=NumericalSampling.RunRequest(args[0],exact ? "--exact-circuit" : "--sample",request,System.Threading.CancellationToken.None,x=>x).GetAwaiter().GetResult();
    var root=new System.Web.Script.Serialization.JavaScriptSerializer().Deserialize<System.Collections.Generic.Dictionary<string,object>>(result);
    var values=(System.Collections.Generic.Dictionary<string,object>)root[exact ? "probabilities" : "counts"];
    string want=text.StartsWith("int[3](c) !=") ? "0" : "1";Check(values.Count==1 && Convert.ToString(values[want])==(exact ? "1" : "10000"));
   }
  }
  foreach(string text in new[]{"bit[3](int[3](c))","bit[3](uint[3](-1))","~bit[3](int[3](c))","bit[3](int[3](int[3](c)+1))","bit[3](uint[3](255)) & c"})Roundtrip(Parse(text,3),3);
  foreach(string bad in new[]{"bit[3](c)","bit[3](int(c))","bit[2](int[3](c))","bit[3](int[3](c)+1)","bit(int[3](c))","bit[0](int[3](c))","bit[65](int[3](c))","bit[3](1)","bit[3](int[3](c)) + 1"})Reject(()=>Parse(bad,3));
  Roundtrip(Parse("bit[1](uint[1](1)) && true",1),1);
  Check(ClassicalExpressionText.RequiredVersion(Parse("bit[3](int[3](c))",3))==4);
  var castNode=Parse("bit[3](int[3](int[3](c)+1))",3);var castDocument=Context();castDocument.Version=4;
  castDocument.Steps=new[]{new ClassicalCircuit.Step{Kind="Assign",Wires=new[]{0,1,2},ClassicalValue=castNode}};
  var castSaved=ClassicalCircuit.From(castDocument);var castOpened=ClassicalCircuit.Load(castSaved.Serialize());
  Check(Format(castOpened.Snapshot().Steps[0].ClassicalValue)==Format(castNode));
  if(args.Length>0)foreach(bool exact in new[]{true,false}) {
   byte[] request=exact ? NumericalSampling.RequestExact(0,64,new[]{2,1,0},castOpened.SamplingGates()) : NumericalSampling.RequestClassical(0,64,10000,1731,new[]{2,1,0},castOpened.SamplingGates());
   string result=NumericalSampling.RunRequest(args[0],exact ? "--exact-circuit" : "--sample",request,System.Threading.CancellationToken.None,x=>x).GetAwaiter().GetResult();
   var root=new System.Web.Script.Serialization.JavaScriptSerializer().Deserialize<System.Collections.Generic.Dictionary<string,object>>(result);
   var values=(System.Collections.Generic.Dictionary<string,object>)root[exact ? "probabilities" : "counts"];
   Check(values.Count==1 && Convert.ToString(values["001"])==(exact ? "1" : "10000"));
  }
  foreach(string name in new[]{"int","uint","bit"}) {
   var named=Context();named.Registers[0].Name=name;
   Check(Format(ClassicalExpressionText.Parse(name+"[0:1]",named,2))=="read(0,1)");
   Check(Format(ClassicalExpressionText.Parse(name+"[1]",named,1))=="read(1)");
   Check(Format(ClassicalExpressionText.Parse(name,named,3))=="read(0,1,2)");
  }
  Console.WriteLine("PASS: "+checks+" classical expression text checks.");return 0;
 }catch(Exception e){Console.Error.WriteLine(e);return 1;}}
}
