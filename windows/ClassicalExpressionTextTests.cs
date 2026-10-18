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
 static void SignedLiteralChecks() {
  var context=Context();context.Version=5;context.Variables=new ClassicalCircuit.Variable[0];
  var serializer=new System.Web.Script.Serialization.JavaScriptSerializer();
  var samples=new[]{
   new N{Kind="IntegerConstant",Signedness="Signed",Width=0,Value="18446744073709551615"},
   new N{Kind="IntegerConstant",Signedness="Signed",Width=64,Value="9223372036854775808"},
   new N{Kind="IntegerConstant",Signedness="Signed",Width=8,Value="128"},
   new N{Kind="IntegerConstant",Signedness="Signed",Width=3,Value="7"},
   new N{Kind="IntegerConstant",Signedness="Signed",Width=1,Value="1"},
   new N{Kind="IntegerConstant",Signedness="Signed",Width=3,Value="3"},
   new N{Kind="IntegerConstant",Signedness="Unsigned",Width=64,Value="18446744073709551615"}};
  string[] expected={"int(-1)","int[64](-9223372036854775808)","int[8](-128)","int[3](-1)","int[1](-1)","int[3](3)","uint[64](18446744073709551615)"};
  for(int i=0;i<samples.Length;i++) {
   Check(Format(samples[i])==expected[i]);
   Check(serializer.Serialize(ClassicalExpressionText.ParseInteger(expected[i],context))==serializer.Serialize(samples[i]));
   var cast=new N{Kind="IntegerCast",Signedness="Signed",Width=8,Left=samples[i]};
   Check(serializer.Serialize(ClassicalExpressionText.ParseInteger(Format(cast),context))==serializer.Serialize(cast));
  }
  Check(Format(ClassicalExpressionText.ParseInteger("uint[8](-1)",context))=="uint[8](255)");
  Reject(()=>ClassicalExpressionText.ParseInteger("int[8](-9223372036854775809)",context));
 }
 static void BooleanDisplayChecks() {
  var serializer=new System.Web.Script.Serialization.JavaScriptSerializer();
  string[] source={"bool(c)","bool(int[3](c))","bool(popcount(c))","bool(bool(c))","bool(c == 4)","bool(c) && 6 / int[3](c) == 3"};
  foreach(string text in source) {
   N before=Parse(text,1);string shown=Format(before);
   Check(shown.StartsWith("bool(") || shown.StartsWith("(bool("));
   Check(serializer.Serialize(before)==serializer.Serialize(Parse(shown,1)));
  }
  foreach(string text in new[]{"int[3](c) != int[8](0)","int[3](c) != uint(0)","c != 1","c == 0"}) {
   N before=Parse(text,1);string shown=Format(before);
   Check(!shown.StartsWith("bool("));
   Check(serializer.Serialize(before)==serializer.Serialize(Parse(shown,1)));
  }
  var context=Context();context.Version=6;context.Variables=new[]{new ClassicalCircuit.Variable{Name="ready",Signedness="Unsigned",Width=1}};
  N value=ClassicalExpressionText.Parse("bool(ready)",context,1);
  Check(ClassicalExpressionText.Format(value,context)=="bool(ready)");
  Check(serializer.Serialize(value)==serializer.Serialize(ClassicalExpressionText.Parse("bool(ready)",context,1)));
 }
 static void VariableChecks(string worker) {
  var context=Context();context.Version=5;context.Variables=new[]{new ClassicalCircuit.Variable{Name="counter",Signedness="Signed",Width=8}};
  string boundary="counter";for(int depth=1;depth<32;depth++)boundary="int("+boundary+")";
  Check(ClassicalExpressionText.ParseInteger(boundary,context)!=null);
  Reject(()=>ClassicalExpressionText.ParseInteger("int("+boundary+")",context));
  var rhs=ClassicalExpressionText.ParseInteger("counter ** 2 - 1",context);
  Check(ClassicalExpressionText.RequiredVersion(rhs)==5);
  string pretty=ClassicalExpressionText.Format(rhs,context);Check(pretty.Contains("counter"));
  Check(ClassicalExpressionText.Format(ClassicalExpressionText.ParseInteger(pretty,context),context)==pretty);
  string fallback=Format(rhs);Check(fallback.Contains("variable(0)"));
  Check(Format(ClassicalExpressionText.ParseInteger(fallback,context))==fallback);
  var condition=ClassicalExpressionText.Parse("counter == 8",context,1);
  Check(ClassicalExpressionText.RequiredVersion(condition)==5);
  Reject(()=>ClassicalExpressionText.ParseInteger("missing + 1",context));
  Reject(()=>ClassicalExpressionText.ParseInteger("variable(1)",context));
  Reject(()=>ClassicalExpressionText.ParseInteger("variable(4096)",context));
  Reject(()=>ClassicalExpressionText.ParseInteger("counter == 8",context));
  Reject(()=>ClassicalExpressionText.Parse("counter",context,1));
  var initial=ClassicalExpressionText.ParseInteger("3",context);
  context.OutputBits=new[]{0};context.Steps=new[]{new ClassicalCircuit.Step{Kind="StoreInteger",VariableSlot=0,IntegerValue=initial},
   new ClassicalCircuit.Step{Kind="StoreInteger",VariableSlot=0,IntegerValue=rhs},new ClassicalCircuit.Step{Kind="Assign",Wires=new[]{0},ClassicalValue=condition}};
  var circuit=ClassicalCircuit.From(context);var opened=ClassicalCircuit.Load(circuit.Serialize());Check(opened.Serialize()==circuit.Serialize());
  if(worker!=null)foreach(bool exact in new[]{true,false}) {
   byte[] request=exact ? NumericalSampling.RequestExact(0,64,new[]{0},opened.SamplingGates(),opened.VariableTypes) : NumericalSampling.RequestClassical(0,64,10000,1731,new[]{0},opened.SamplingGates(),opened.VariableTypes);
   string result=NumericalSampling.RunRequest(worker,exact ? "--exact-circuit" : "--sample",request,System.Threading.CancellationToken.None,x=>x).GetAwaiter().GetResult();
   var root=new System.Web.Script.Serialization.JavaScriptSerializer().Deserialize<System.Collections.Generic.Dictionary<string,object>>(result);
   var values=(System.Collections.Generic.Dictionary<string,object>)root[exact ? "probabilities" : "counts"];
   Check(values.Count==1 && Convert.ToString(values["1"])==(exact ? "1" : "10000"));
  }
  foreach(string name in new[]{"with space","true","false","int","variable"}) {
   context.Variables[0].Name=name;var node=new N{Kind="IntegerVariable",Signedness="Signed",Width=8,Slot=0};
   string text=ClassicalExpressionText.Format(node,context);Check(ClassicalExpressionText.ParseInteger(text,context).Slot==0);
  }
 }
 static void ComputedCastChecks(string worker) {
  foreach(string text in new[]{"int[3](~c) == -1","uint[3](c ^ \"111\") == 7","uint[1](c == 0) == 1","uint[1](true || int[3](c)/0 == 1) == 1","uint(popcount(c)) == 0","int(uint[3](c | \"100\")) == 4"}) {
   var node=Parse(text,1);Check(ClassicalExpressionText.RequiredVersion(node)==6);Roundtrip(node,1);
   var doc=Context();doc.Version=6;doc.Variables=new ClassicalCircuit.Variable[0];doc.OutputBits=new[]{3};
   doc.Steps=new[]{new ClassicalCircuit.Step{Kind="Assign",Wires=new[]{3},ClassicalValue=node}};
   var saved=ClassicalCircuit.From(doc);var reopened=ClassicalCircuit.Load(saved.Serialize());Check(reopened.Serialize()==saved.Serialize());
   foreach(int version in new[]{2,3,4,5}){var old=reopened.Snapshot();old.Version=version;Reject(()=>ClassicalCircuit.From(old));}
   var missing=reopened.Snapshot();missing.Variables=null;Reject(()=>ClassicalCircuit.From(missing));
   if(worker==null)continue;
   foreach(bool exact in new[]{true,false}) {
    byte[] request=exact ? NumericalSampling.RequestExact(0,64,new[]{3},reopened.SamplingGates(),reopened.VariableTypes) : NumericalSampling.RequestClassical(0,64,10000,1731,new[]{3},reopened.SamplingGates(),reopened.VariableTypes);
    Check(Encoding.UTF8.GetString(request).StartsWith(exact ? "QEXACT5\n" : "QSAMPLE6\n"));
    string result=NumericalSampling.RunRequest(worker,exact ? "--exact-circuit" : "--sample",request,System.Threading.CancellationToken.None,x=>x).GetAwaiter().GetResult();
    var root=new System.Web.Script.Serialization.JavaScriptSerializer().Deserialize<System.Collections.Generic.Dictionary<string,object>>(result);
    var values=(System.Collections.Generic.Dictionary<string,object>)root[exact ? "probabilities" : "counts"];
    Check(values.Count==1 && Convert.ToString(values["1"])==(exact ? "1" : "10000"));
   }
  }
  var context=Context();var cast=ClassicalExpressionText.ParseInteger("uint[3](~c)",context);
  Check(cast.Kind=="IntegerFromBits" && context.Version==3 && context.Variables==null);
  Check(Format(ClassicalExpressionText.ParseInteger(Format(cast),context))==Format(cast));
  foreach(string bad in new[]{"uint[2](~c)","uint[3](c == 0)","uint[1](read(64) == 0)"})Reject(()=>ClassicalExpressionText.ParseInteger(bad,context));
 }
 static void BooleanChecks(string worker) {
  string[] expressions={"bool(c)","bool(int[3](c))","bool(uint[3](c))","bool(popcount(c))","bool(c == 4)","bool(bool(c))","bool(int[3](c) - int[3](c))","bool(~c)","bool(c) && 6 / int[3](c) == 3"};
  int[] initial={0,4,4,4,4,4,4,7,0},expected={0,1,1,1,1,1,0,0,0};
  for(int k=0;k<expressions.Length;k++) {
   var value=Parse(expressions[k],1);Roundtrip(value,1);
   var document=Context();document.Version=ClassicalExpressionText.RequiredVersion(value);
   document.Steps=new[]{new ClassicalCircuit.Step{Kind="Assign",Wires=new[]{0,1,2},ClassicalValue=new N{Kind="Constant",Width=3,Value=initial[k].ToString()}},new ClassicalCircuit.Step{Kind="Assign",Wires=new[]{3},ClassicalValue=value}};
   var stored=ClassicalCircuit.From(document);var reopened=ClassicalCircuit.Load(stored.Serialize());Check(stored.Serialize()==reopened.Serialize());
   if(worker==null)continue;
   foreach(bool exact in new[]{true,false}) {
    byte[] request=exact ? NumericalSampling.RequestExact(0,64,new[]{3},reopened.SamplingGates()) : NumericalSampling.RequestClassical(0,64,10000,1731,new[]{3},reopened.SamplingGates());
    string result=NumericalSampling.RunRequest(worker,exact ? "--exact-circuit" : "--sample",request,System.Threading.CancellationToken.None,x=>x).GetAwaiter().GetResult();
    var root=new System.Web.Script.Serialization.JavaScriptSerializer().Deserialize<System.Collections.Generic.Dictionary<string,object>>(result);
    var values=(System.Collections.Generic.Dictionary<string,object>)root[exact ? "probabilities" : "counts"];
    Check(values.Count==1 && Convert.ToString(values[expected[k].ToString()])==(exact ? "1" : "10000"));
   }
  }
  foreach(string bad in new[]{"bool()","bool(c, 1)","bool(c + 1)","bool(c) trailing"})Reject(()=>Parse(bad,1));
  Check(ClassicalExpressionText.RequiredVersion(Parse("bool(c)",1))==3);
  Check(ClassicalExpressionText.RequiredVersion(Parse("bool(int[3](c))",1))==4);
 }
 static int Main(string[] args){try {
  Check(Format(Parse("rotl(c, -1)",3))=="rotl_signed(read(0,1,2), -1)");
  Check(Format(Parse("rotl_signed(c, 1)",3))=="rotl_signed(read(0,1,2), 1)");
  Check(Format(Parse("popcount(c) == 1",1))=="(popcount(read(0,1,2)) == 1)");
  Check(Format(Parse("1 == popcount(c)",1))=="(1 == popcount(read(0,1,2)))");
  Check(Parse("popcount(c)",64).Kind=="PopulationCount");
  foreach(string text in new[]{"popcount(c) == 2","popcount(read(63)) != 0","popcount(\"111\") == popcount(7)"})Roundtrip(Parse(text,1),1);
  foreach(string text in new[]{"rotl(c, 1)","rotr(c, -1)","rotl(c, -9223372036854775808)","rotr(c, 18446744073709551615)","rotl_signed(c, c)","rotr_signed(c, 1)","rotl(c, popcount(c))"})Roundtrip(Parse(text,3),3);
  foreach(string text in new[]{"int[3](c)**3 == 8","2**3**2 == 512","-2**2 == -4","(-2)**2 == 4","2**-1 == 0","bit[3](int[3](2**3))"})Roundtrip(Parse(text,text.StartsWith("bit") ? 3 : 1),text.StartsWith("bit") ? 3 : 1);
  Check(Parse("2**3**2 == 512",1).Left.Right.Operator=="Power");
  Check(Parse("-2**2 == -4",1).Left.Operator=="Subtract" && Parse("-2**2 == -4",1).Left.Right.Operator=="Power");
  foreach(string bad in new[]{"c**2 == 1","2***3 == 8","2** == 1"})Reject(()=>Parse(bad,1));
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
  Reject(()=>Parse("bool("+Format(deep)+")",1));
  var broad=new N{Kind="Read",Bits=new[]{0}};for(int k=0;k<8;k++)broad=new N{Kind="Binary",Operator="Or",Left=broad,Right=broad};Roundtrip(new N{Kind="Complement",Left=broad},1);
  Reject(()=>Parse("("+Format(broad)+" | read(0))",1));
  Reject(()=>Parse("bool("+Format(broad)+")",1));
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
  foreach(string name in new[]{"int","uint","bit","bool"}) {
   var named=Context();named.Registers[0].Name=name;
   Check(Format(ClassicalExpressionText.Parse(name+"[0:1]",named,2))=="read(0,1)");
   Check(Format(ClassicalExpressionText.Parse(name+"[1]",named,1))=="read(1)");
   Check(Format(ClassicalExpressionText.Parse(name,named,3))=="read(0,1,2)");
  }
  foreach(string text in new[]{"2**3**2 == 512","(2**3)**2 == 64","-2**2 == -4","(-2)**2 == 4","2*3**2 == 18","2**3*2 == 16","int[3](c)**0 == 1","2**int[3](c) == 1","false && 2**-1 == 0","true || 2**63 == 0"}) {
   var node=Parse(text,1);var d=Context();d.Version=4;d.OutputBits=new[]{3};
   d.Steps=new[]{new ClassicalCircuit.Step{Kind="Assign",Wires=new[]{3},ClassicalValue=node}};
   var saved=ClassicalCircuit.From(d);var opened=ClassicalCircuit.Load(saved.Serialize());
   Check(opened.Serialize()==saved.Serialize());Check(Format(opened.Snapshot().Steps[0].ClassicalValue)==Format(node));
   if(args.Length>0)foreach(bool exact in new[]{true,false}) {
    var steps=opened.SamplingGates();byte[] request=exact ? NumericalSampling.RequestExact(0,64,new[]{3},steps) : NumericalSampling.RequestClassical(0,64,10000,1731,new[]{3},steps);
    string result=NumericalSampling.RunRequest(args[0],exact ? "--exact-circuit" : "--sample",request,System.Threading.CancellationToken.None,x=>x).GetAwaiter().GetResult();
    var root=new System.Web.Script.Serialization.JavaScriptSerializer().Deserialize<System.Collections.Generic.Dictionary<string,object>>(result);
    var values=(System.Collections.Generic.Dictionary<string,object>)root[exact ? "probabilities" : "counts"];
    string want=text.StartsWith("false") ? "0" : "1";Check(values.Count==1 && Convert.ToString(values[want])==(exact ? "1" : "10000"));
   }
  }
  BooleanChecks(args.Length>0 ? args[0] : null);
  SignedLiteralChecks();
  BooleanDisplayChecks();
  ComputedCastChecks(args.Length>0 ? args[0] : null);
  VariableChecks(args.Length>0 ? args[0] : null);
  Console.WriteLine("PASS: "+checks+" classical expression text checks.");return 0;
 }catch(Exception e){Console.Error.WriteLine(e);return 1;}}
}
