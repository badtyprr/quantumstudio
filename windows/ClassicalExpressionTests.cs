using System;
using System.Collections.Generic;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using E=ClassicalExpression;
using G=NumericalSampling.Gate;
using O=NumericalSampling.Operation;

static class ClassicalExpressionTests {
 static int checks;
 static void Check(bool value){++checks;if(!value)throw new Exception("Classical adapter check failed: "+checks);}
 static void Reject(Action action){bool rejected=false;try{action();}catch(ArgumentException){rejected=true;}Check(rejected);}
 static G Assign(int[] targets,E value){return new G{Kind=O.Assign,Wires=targets,ClassicalExpression=value};}
 static G Branch(E condition,IList<G> yes,IList<G> no=null){return new G{Kind=O.ExpressionBranch,ClassicalExpression=condition,WhenTrue=yes,WhenFalse=no??new G[0]};}
 static byte[] Request(bool exact,int q,int bits,int[] output,IList<G> steps){return exact ? NumericalSampling.RequestExact(q,bits,output,steps) : NumericalSampling.RequestClassical(q,bits,10000,1731,output,steps);}
 static string Encode(E value,int bits){var text=new StringBuilder();value.Write(v=>text.Append(v).Append('\n'),bits);return text.ToString();}
 static Dictionary<string,object> Evaluate(string worker,bool exact,int q,int bits,int[] output,IList<G> steps) {
  string text=NumericalSampling.RunRequest(worker,exact ? "--exact-circuit" : "--sample",Request(exact,q,bits,output,steps),CancellationToken.None,s=>s).GetAwaiter().GetResult();
  var root=new JavaScriptSerializer().Deserialize<Dictionary<string,object>>(text);
  return (Dictionary<string,object>)root[exact ? "probabilities" : "counts"];
 }
 static int Main(string[] args){try {
  var countValue=E.PopulationCount(E.Constant(64,UInt64.MaxValue));Check(countValue.Width==64);
  Check(Encode(countValue,0)=="4\n0\n64\n18446744073709551615\n");
  var rotatedValue=E.Rotate(E.Direction.Left,E.Constant(4,9),E.Constant(8,255),E.Distance.Signed);Check(rotatedValue.Width==4);
  Check(Encode(rotatedValue,0)=="5\n0\n1\n0\n4\n9\n0\n8\n255\n");
  Reject(()=>E.PopulationCount(null));
  Reject(()=>E.Rotate((E.Direction)2,E.Constant(1,1),E.Constant(1,0),E.Distance.Signed));
  Reject(()=>E.Rotate(E.Direction.Left,E.Constant(1,1),E.Constant(1,0),(E.Distance)2));
  Reject(()=>E.Rotate(E.Direction.Left,null,E.Constant(1,0),E.Distance.Unsigned));
  Reject(()=>E.Rotate(E.Direction.Left,E.Constant(1,1),null,E.Distance.Unsigned));
  Reject(()=>Encode(E.PopulationCount(E.Read(1)),1));
  Reject(()=>Encode(E.Rotate(E.Direction.Right,E.Constant(1,1),E.Read(1),E.Distance.Signed),1));
  var indices=new[]{0,1};var read=E.Read(indices);indices[0]=63;var exported=read.Indices;exported[0]=62;
  Check(Encode(read,2)=="1\n2\n0\n1\n");
  Check(Encode(E.Constant(64,UInt64.MaxValue),0)=="0\n64\n18446744073709551615\n");
  Check(Encode(E.Complement(E.Read(0)),1)=="2\n1\n1\n0\n");
  Check(Encode(E.Binary(E.Operator.Xor,E.Read(0),E.Read(1)),2)=="3\n2\n1\n1\n0\n1\n1\n1\n");
  foreach(E.Operator op in Enum.GetValues(typeof(E.Operator)))Check(E.Binary(op,E.Constant(3,5),E.Constant(3,2)).Width==((int)op>=5 ? 1 : 3));
  Reject(()=>E.Constant(0,0));Reject(()=>E.Constant(65,0));Reject(()=>E.Constant(1,2));Reject(()=>E.Read());Reject(()=>E.Read(64));Reject(()=>E.Read(-1));
  Reject(()=>E.Complement(null));Reject(()=>E.Binary((E.Operator)99,E.Constant(1,0),E.Constant(1,0)));
  Reject(()=>E.Binary(E.Operator.And,E.Constant(1,0),E.Constant(2,0)));
  Reject(()=>Encode(E.Read(1),1));Reject(()=>Encode(E.Read(0),0));Reject(()=>Encode(E.Constant(1,0),65));
  var deep=E.Constant(1,0);for(int k=1;k<32;k++)deep=E.Complement(deep);Check(Encode(deep,0).Length>32);Reject(()=>E.Complement(deep));
  var broad=E.Constant(1,1);for(int k=0;k<8;k++)broad=E.Binary(E.Operator.Or,broad,broad);Check(Encode(broad,0).Length>512);Reject(()=>E.Binary(E.Operator.Or,broad,broad));
  Reject(()=>E.PopulationCount(deep));Reject(()=>E.Rotate(E.Direction.Left,deep,E.Constant(1,0),E.Distance.Unsigned));
  var overlap=new[]{Assign(new[]{0},E.Constant(1,1)),Assign(new[]{1,2},E.Read(0,1))};
  foreach(bool exact in new[]{true,false}) {
   string encoded=Encoding.UTF8.GetString(Request(exact,0,3,new[]{2,1,0},overlap));Check(encoded.StartsWith(exact ? "QEXACT2\n" : "QSAMPLE3\n"));
   Check(encoded.EndsWith("7\n2\n1\n2\n1\n2\n0\n1\n"));
   string legacy=Encoding.UTF8.GetString(Request(exact,0,0,new int[0],new G[0]));Check(legacy.StartsWith(exact ? "QEXACT1\n" : "QSAMPLE2\n"));
   foreach(var bad in new[]{Assign(new[]{0,0},E.Constant(2,0)),Assign(new[]{1},E.Constant(1,0)),Assign(new[]{0},E.Constant(2,0)),Assign(new[]{0},E.Read(1)),Assign(new[]{0},null),Branch(E.Constant(2,0),new G[0]),Branch(E.Constant(1,0),new[]{Assign(new[]{1},E.Constant(1,0))}),new G{Kind=O.Gate,ClassicalExpression=E.Constant(1,0)}})
    Reject(()=>Request(exact,0,1,new[]{0},new[]{bad}));
   var ambiguous=Assign(new[]{0},E.Constant(1,0));ambiguous.Mask=1;Reject(()=>Request(exact,0,1,new[]{0},new[]{ambiguous}));
   ambiguous=Assign(new[]{0},E.Constant(1,0));ambiguous.Expression="X";Reject(()=>Request(exact,0,1,new[]{0},new[]{ambiguous}));
   var nested=Branch(E.Read(0),overlap);Check(Encoding.UTF8.GetString(Request(exact,0,3,new[]{0},new[]{nested})).StartsWith(exact ? "QEXACT2\n" : "QSAMPLE3\n"));
   if(args.Length>0) {
    var targets=new int[64];for(int k=0;k<64;k++)targets[k]=k;
    var countResult=Evaluate(args[0],exact,0,64,new[]{6,5,4,3,2,1,0},new[]{Assign(targets,countValue)});
    Check(countResult.Count==1 && Convert.ToString(countResult["1000000"])==(exact ? "1" : "10000"));
    var rotationResult=Evaluate(args[0],exact,0,4,new[]{3,2,1,0},new[]{Assign(new[]{0,1,2,3},rotatedValue)});
    Check(rotationResult.Count==1 && Convert.ToString(rotationResult["1100"])==(exact ? "1" : "10000"));
    var result=Evaluate(args[0],exact,0,3,new[]{2,1,0},overlap);Check(result.Count==1 && Convert.ToString(result["011"])==(exact ? "1" : "10000"));
    result=Evaluate(args[0],exact,0,64,new[]{63},new[]{Assign(new[]{63},E.Constant(1,1))});Check(result.Count==1 && Convert.ToString(result["1"])==(exact ? "1" : "10000"));
    var parity=new[]{new G{Expression="H",Wires=new[]{0}},new G{Expression="H",Wires=new[]{1}},new G{Kind=O.Measure,Wires=new[]{0},ClassicalBit=0},new G{Kind=O.Measure,Wires=new[]{1},ClassicalBit=1},Branch(E.Binary(E.Operator.Xor,E.Read(0),E.Read(1)),new[]{new G{Expression="X",Wires=new[]{2}}}),new G{Kind=O.Measure,Wires=new[]{2},ClassicalBit=2}};
    result=Evaluate(args[0],exact,3,3,new[]{2,1,0},parity);Check(result.Count==4);
    foreach(string label in new[]{"000","011","101","110"})Check(exact ? Convert.ToString(result[label])=="0.25" : Math.Abs(Convert.ToInt32(result[label])-2500)<400);
   }
  }
  Reject(()=>NumericalSampling.Request(1,1,0,new[]{0},new[]{Assign(new[]{0},E.Constant(1,1))}));
  Console.WriteLine("PASS: "+checks+" classical expression adapter checks.");return 0;
 }catch(Exception e){Console.Error.WriteLine(e);return 1;}}
}
