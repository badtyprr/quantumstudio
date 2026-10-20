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
  foreach(string source in new[]{"","NaN","Infinity","1e999","c","unknown","sin(n)","float(c)","1+","(1","1)","1**2","float(n","uint[0](c)"}) {
   bool rejected=false;try{ClassicalRealExpressionText.Parse(source,context);}catch(ArgumentException){rejected=true;}catch(OverflowException){rejected=true;}
   Check(rejected);
  }
  var deep=ClassicalRealExpressionText.Parse("1",context);
  for(int i=1;i<32;i++)deep=new ClassicalCircuit.RealNode{Kind="Binary",Operator="Add",Left=deep,Right=new ClassicalCircuit.RealNode{Kind="Constant",ValueBits="0"}};
  Check(json.Serialize(deep)==json.Serialize(ClassicalRealExpressionText.Parse(ClassicalRealExpressionText.Format(deep,context),context)));
  Console.WriteLine("PASS: "+checks+" real angle text checks.");
 }
}
