// GPL-2.0-or-later; see COPYING.
using System;
using System.Web.Script.Serialization;
static class ClassicalRealExpressionTextTests {
 static int checks;
 static void Check(bool value){checks++;if(!value)throw new Exception("Angle text check "+checks+" failed.");}
 static void Main() {
  var context=new ClassicalCircuit.Document{Version=11,LoopConditionBudget=1000000,Registers=new[]{new ClassicalCircuit.Register{Name="c",Size=1}},Variables=new[]{new ClassicalCircuit.Variable{Name="n",Signedness="Signed",Width=0}}};
  var json=new JavaScriptSerializer();
  foreach(string source in new[]{"pi*n/2","π * uint[1](c)","float(n/2)","1e-9 + .5","-n","-0.0","1-(2-3)","1/2/3","float(int[8](-1))"}) {
   var value=ClassicalRealExpressionText.Parse(source,context);
   string formatted=ClassicalRealExpressionText.Format(value,context);
   Check(json.Serialize(value)==json.Serialize(ClassicalRealExpressionText.Parse(formatted,context)));
  }
  Check(ClassicalRealExpressionText.Parse("n/2",context).Kind=="Binary");
  Check(ClassicalRealExpressionText.Parse("float(n/2)",context).IntegerValue.Kind=="IntegerBinary");
  Check(ClassicalRealExpressionText.Parse("-0.0",context).ValueBits=="9223372036854775808");
  foreach(string source in new[]{"","NaN","Infinity","1e999","c","unknown","arccosh(n)","float(c)","1+","(1","1)","1**2","float(n","uint[0](c)"}) {
   bool rejected=false;try{ClassicalRealExpressionText.Parse(source,context);}catch(ArgumentException){rejected=true;}catch(OverflowException){rejected=true;}
   Check(rejected);
  }
  var deep=ClassicalRealExpressionText.Parse("1",context);
  for(int i=1;i<32;i++)deep=new ClassicalCircuit.RealNode{Kind="Binary",Operator="Add",Left=deep,Right=new ClassicalCircuit.RealNode{Kind="Constant",ValueBits="0"}};
  Check(json.Serialize(deep)==json.Serialize(ClassicalRealExpressionText.Parse(ClassicalRealExpressionText.Format(deep,context),context)));
  context.Version=13;context.Registers[0].Size=8;context.NumericVariables=new[]{new ClassicalCircuit.NumericVariable{Name="f",NumericKind="Float",Width=32},new ClassicalCircuit.NumericVariable{Name="a",NumericKind="Angle",Width=8}};
  foreach(string source in new[]{"f+1","sin(f)","sqrt(float[32](9.0))","float[32](n/2)","float[64](f)","mod(f,2.0)","f**2.0","angle[8](\"10000000\")","a+angle[8](pi)","-a","~a","a / uint[8](2)","a << uint[8](1)","float[32](-0.0)","angle(1.0)"}) {
   var node=ClassicalRealExpressionText.Parse(source,context);
   string formatted=ClassicalRealExpressionText.Format(node,context);
   var again=ClassicalRealExpressionText.Parse(formatted,context);
   Check(ClassicalRealExpressionText.Format(again,context)==formatted);
  }
  foreach(string source in new[]{"f > 0","bool(f)","a == angle[8](pi)","f>0 && a!=angle[8](0.0)","int[8](f)==n","compare(f,1.0)>0"}) {
   var node=ClassicalExpressionText.Parse(source,context,1);var text=ClassicalExpressionText.Format(node,context);
   Check(ClassicalExpressionText.RequiredVersion(ClassicalExpressionText.Parse(text,context,1))==13);
  }
  foreach(string source in new[]{"int[8](f)","anglebits(a)","a / angle[8](pi)","compare(f,1.0)","int[8](f>0)","int(bool(f))"}) {
   var node=ClassicalExpressionText.ParseInteger(source,context);var text=ClassicalExpressionText.Format(node,context);
   Check(ClassicalExpressionText.RequiredVersion(ClassicalExpressionText.ParseInteger(text,context))==13);
  }
  var bitCast=ClassicalExpressionText.Parse("bit[8](a)",context,8);
  Check(ClassicalExpressionText.Parse(ClassicalExpressionText.Format(bitCast,context),context,8).Kind=="IntegerBits");
  foreach(string source in new[]{"float[16](f)","float[32](a)","a + f","a / uint[7](2)","~f","log(a)","angle[0](0.0)","angle[8](\"1\")"}) {
   bool rejected=false;try{ClassicalRealExpressionText.Parse(source,context);}catch(ArgumentException){rejected=true;}catch(System.IO.InvalidDataException){rejected=true;}Check(rejected);
  }
  foreach(string name in new[]{"two words","pi","sqrt","numeric"}) {
   context.NumericVariables[0].Name=name;
   var node=new ClassicalCircuit.RealNode{Kind="Variable",NumericKind="Float",Width=32,Slot=0};
   var text=ClassicalRealExpressionText.Format(node,context);
   Check(text=="numeric(0)");Check(ClassicalRealExpressionText.Parse(text,context).Slot==0);
  }
  Console.WriteLine("PASS: "+checks+" real angle text checks.");
 }
}
