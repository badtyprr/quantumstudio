using System;
using System.Collections.Generic;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using E=ClassicalExpression;
using I=ClassicalIntegerExpression;
using T=ClassicalIntegerType;
using G=NumericalSampling.Gate;
using O=NumericalSampling.Operation;

static class ClassicalExpressionTests {
 static int checks;
 static void Check(bool value){++checks;if(!value)throw new Exception("Classical adapter check failed: "+checks);}
 static void Reject(Action action){bool rejected=false;try{action();}catch(ArgumentException){rejected=true;}Check(rejected);}
 static G Assign(int[] targets,E value){return new G{Kind=O.Assign,Wires=targets,ClassicalExpression=value};}
 static G Branch(E condition,IList<G> yes,IList<G> no=null){return new G{Kind=O.ExpressionBranch,ClassicalExpression=condition,WhenTrue=yes,WhenFalse=no??new G[0]};}
 static byte[] Request(bool exact,int q,int bits,int[] output,IList<G> steps,IList<T> types=null){return exact ? NumericalSampling.RequestExact(q,bits,output,steps,types) : NumericalSampling.RequestClassical(q,bits,10000,1731,output,steps,types);}
 static string Encode(E value,int bits){var text=new StringBuilder();value.Write(v=>text.Append(v).Append('\n'),bits);return text.ToString();}
 static Dictionary<string,object> Evaluate(string worker,bool exact,int q,int bits,int[] output,IList<G> steps,IList<T> types=null) {
  string text=NumericalSampling.RunRequest(worker,exact ? "--exact-circuit" : "--sample",Request(exact,q,bits,output,steps,types),CancellationToken.None,s=>s).GetAwaiter().GetResult();
  var root=new JavaScriptSerializer().Deserialize<Dictionary<string,object>>(text);
  return (Dictionary<string,object>)root[exact ? "probabilities" : "counts"];
 }
 static void TerminationChecks(string worker) {
  var yes=E.Constant(1,1);var no=E.Constant(1,0);var end=new G{Kind=O.End};
  Func<IList<G>,G> loop=body=>new G{Kind=O.While,ClassicalExpression=yes,WhenTrue=body};
  foreach(bool exact in new[]{false,true}) {
   string payload=Encoding.UTF8.GetString(Request(exact,0,1,new[]{0},new[]{end}));
   Check(payload==(exact ? "QEXACT8\n0\n1\n0\n1000000\n1\n0\n1\n14\n" : "QSAMPLE9\n0\n10000\n1731\n1\n0\n1000000\n1\n0\n1\n14\n"));
   foreach(Action<G> corrupt in new Action<G>[] {
    g=>g.Wires=new[]{0},g=>g.Expression="X",g=>g.Mask=1,g=>g.Value=1,
    g=>g.ClassicalBit=0,g=>g.WhenTrue=new G[0],g=>g.WhenFalse=new G[0],
    g=>g.ClassicalExpression=yes,g=>g.VariableSlot=0,g=>g.IntegerExpression=I.Constant(T.Create(T.Sign.Unsigned,1),0)
   }) {var invalid=new G{Kind=O.End};corrupt(invalid);Reject(()=>Request(exact,1,1,new[]{0},new[]{invalid}));}
   Reject(()=>Request(exact,0,1,new[]{0},new[]{end,Assign(new[]{1},yes)}));
   Reject(()=>Request(exact,0,1,new[]{0},new[]{end,new G{Kind=O.Break}}));
   if(worker==null)continue;
   foreach(var program in new IList<G>[] {
    new[]{Assign(new[]{0},yes),end,Assign(new[]{0},no)},
    new[]{loop(new[]{loop(new[]{Assign(new[]{0},yes),Branch(yes,new[]{end})})}),Assign(new[]{0},no)}
   }) {
    var result=Evaluate(worker,exact,0,1,new[]{0},program);
    Check(result.Count==1 && Convert.ToString(result["1"])==(exact ? "1" : "10000"));
   }
   byte[] zeroBudget=exact ? NumericalSampling.RequestExact(0,1,new[]{0},new[]{end},null,0) : NumericalSampling.RequestClassical(0,1,1,0,new[]{0},new[]{end},null,0);
   Check(NumericalSampling.RunRequest(worker,exact ? "--exact-circuit" : "--sample",zeroBudget,CancellationToken.None,x=>x).GetAwaiter().GetResult().Length>0);
  }
  Reject(()=>NumericalSampling.Request(1,1,0,new[]{0},new[]{end}));
 }
 static void TransferChecks(string worker) {
  Func<E,IList<G>,G> loop=(condition,body)=>new G{Kind=O.While,ClassicalExpression=condition,WhenTrue=body};
  var yes=E.Constant(1,1);var no=E.Constant(1,0);
  foreach(bool exact in new[]{false,true}) foreach(O kind in new[]{O.Break,O.Continue}) {
   var transfer=new G{Kind=kind};
   Reject(()=>Request(exact,0,1,new[]{0},new[]{transfer}));
   Reject(()=>Request(exact,0,1,new[]{0},new[]{Branch(no,new[]{transfer})}));
   var steps=new[]{loop(no,new[]{transfer})};
   string payload=Encoding.UTF8.GetString(Request(exact,0,1,new[]{0},steps));
   Check(payload.StartsWith(exact ? "QEXACT7\n" : "QSAMPLE8\n"));
   Check(payload.EndsWith("1\n"+((int)kind)+"\n"));
   foreach(Action<G> corrupt in new Action<G>[] {
    g=>g.Wires=new[]{0},g=>g.Expression="X",g=>g.Mask=1,g=>g.Value=1,
    g=>g.ClassicalBit=0,g=>g.WhenTrue=new G[0],g=>g.WhenFalse=new G[0],
    g=>g.ClassicalExpression=yes,g=>g.VariableSlot=0,g=>g.IntegerExpression=I.Constant(T.Create(T.Sign.Unsigned,1),0)
   }) {var invalid=new G{Kind=kind};corrupt(invalid);Reject(()=>Request(exact,1,1,new[]{0},new[]{loop(no,new[]{invalid})}));}
   Reject(()=>NumericalSampling.Request(1,1,0,new[]{0},steps));
   if(worker==null)continue;
   // Both transfers skip the suffix. Continue must recheck the cleared condition.
   var once=new[]{Assign(new[]{0},yes),loop(E.Read(0),new[]{Assign(new[]{0},no),Branch(yes,new[]{transfer}),Assign(new[]{0},yes)})};
   var result=Evaluate(worker,exact,0,1,new[]{0},once);
   Check(result.Count==1 && Convert.ToString(result["0"])==(exact ? "1" : "10000"));
   foreach(int budget in new[]{1,2}) {
    byte[] bounded=exact ? NumericalSampling.RequestExact(0,1,new[]{0},once,null,budget) : NumericalSampling.RequestClassical(0,1,10,7,new[]{0},once,null,budget);
    bool failed=false;try{NumericalSampling.RunRequest(worker,exact ? "--exact-circuit" : "--sample",bounded,CancellationToken.None,x=>x).GetAwaiter().GetResult();}catch(InvalidOperationException e){failed=e.Message.Contains("loop condition budget");}
    Check(failed==(kind==O.Continue && budget==1));
   }
  }
  if(worker!=null)foreach(bool exact in new[]{false,true}) {
   // An inner break must leave the rest of the outer body executable.
   var nested=new[]{loop(yes,new[]{loop(yes,new[]{new G{Kind=O.Break}}),Assign(new[]{0},yes),new G{Kind=O.Break}})};
   var result=Evaluate(worker,exact,0,1,new[]{0},nested);
   Check(result.Count==1 && Convert.ToString(result["1"])==(exact ? "1" : "10000"));
  }
 }
 static void LoopChecks(string worker) {
  Func<E,IList<G>,G> loop=(condition,body)=>new G{Kind=O.While,ClassicalExpression=condition,WhenTrue=body};
  var no=E.Constant(1,0);var yes=E.Constant(1,1);
  var steps=new[]{Assign(new[]{0},yes),loop(E.Read(0),new[]{Assign(new[]{0},no)})};
  foreach(bool exact in new[]{false,true}) {
   string payload=Encoding.UTF8.GetString(Request(exact,0,1,new[]{0},steps));
   Check(payload.StartsWith(exact ? "QEXACT6\n0\n1\n0\n1000000\n" : "QSAMPLE7\n0\n10000\n1731\n1\n0\n1000000\n"));
   Reject(()=>Request(exact,0,1,new[]{0},new[]{loop(E.Constant(2,0),new G[0])}));
   Reject(()=>Request(exact,0,1,new[]{0},new[]{loop(no,null)}));
   var invalid=loop(no,new G[0]);invalid.WhenFalse=new G[0];Reject(()=>Request(exact,0,1,new[]{0},new[]{invalid}));
   invalid=loop(no,new G[0]);invalid.Wires=new[]{0};Reject(()=>Request(exact,1,1,new[]{0},new[]{invalid}));
   invalid=loop(no,new G[0]);invalid.Mask=1;Reject(()=>Request(exact,0,1,new[]{0},new[]{invalid}));
   Reject(()=>Request(exact,0,1,new[]{0},new[]{loop(no,new[]{Assign(new[]{1},yes)})}));
   var body=new G[0];for(int k=0;k<32;k++)body=new[]{loop(no,body)};
   Check(Request(exact,0,1,new[]{0},body).Length>0);
   Reject(()=>Request(exact,0,1,new[]{0},new[]{loop(no,body)}));
   var type=T.Create(T.Sign.Unsigned,1);var types=new[]{type};
   var withSlot=new[]{new G{Kind=O.StoreInteger,VariableSlot=0,IntegerExpression=I.FromBits(type,yes)},
    loop(E.FromInteger(I.Variable(type,0)),new[]{new G{Kind=O.StoreInteger,VariableSlot=0,IntegerExpression=I.FromBits(type,no)},Assign(new[]{0},yes)})};
   Check(Encoding.UTF8.GetString(Request(exact,0,1,new[]{0},withSlot,types)).Contains("1\n1\n1\n1000000\n"));
   if(worker!=null) {
    var result=Evaluate(worker,exact,0,1,new[]{0},steps);Check(result.Count==1 && Convert.ToString(result["0"])==(exact ? "1" : "10000"));
    result=Evaluate(worker,exact,0,1,new[]{0},withSlot,types);Check(result.Count==1 && Convert.ToString(result["1"])==(exact ? "1" : "10000"));
    byte[] bounded=exact ? NumericalSampling.RequestExact(0,1,new[]{0},steps,null,1) : NumericalSampling.RequestClassical(0,1,10,7,new[]{0},steps,null,1);
    bool failed=false;try{NumericalSampling.RunRequest(worker,exact ? "--exact-circuit" : "--sample",bounded,CancellationToken.None,x=>x).GetAwaiter().GetResult();}catch(InvalidOperationException e){failed=e.Message.Contains("loop condition budget");}Check(failed);
   }
  }
  Reject(()=>NumericalSampling.Request(1,1,0,new[]{0},new[]{loop(no,new G[0])}));
  Reject(()=>NumericalSampling.RequestClassical(0,1,1,0,new[]{0},steps,null,-1));
  Reject(()=>NumericalSampling.RequestExact(0,1,new[]{0},steps,null,1000001));
  Check(Encoding.UTF8.GetString(NumericalSampling.RequestExact(0,0,new int[0],new G[0],null,0))=="QEXACT6\n0\n0\n0\n0\n0\n0\n");
  if(worker!=null) {
   bool failed=false;try{NumericalSampling.RunClassical(worker,0,1,10,7,new[]{0},new[]{loop(no,new G[0])},CancellationToken.None,null,0).GetAwaiter().GetResult();}catch(InvalidOperationException e){failed=e.Message.Contains("loop condition budget");}Check(failed);
   var result=NumericalSampling.RunClassical(worker,0,1,10,7,new[]{0},steps,CancellationToken.None,null,2).GetAwaiter().GetResult();Check(result.counts["0"]==10);
  }
 }
 static void ComputedBitsChecks(string worker) {
  var u1=T.Create(T.Sign.Unsigned,1);var s8=T.Create(T.Sign.Signed,8);
  var truth=I.FromBits(u1,E.Constant(1,1));var result=E.FromInteger(truth);
  Check(truth.UsesBitExpressionProtocol && result.UsesBitExpressionProtocol);
  Reject(()=>I.FromBits(null,E.Constant(1,1)));Reject(()=>I.FromBits(u1,null));
  Reject(()=>I.FromBits(s8,E.Constant(1,1)));
  Reject(()=>Encode(E.FromInteger(I.FromBits(u1,E.Read(1))),1));
  var deep=E.Constant(1,0);for(int k=0;k<15;k++)deep=E.FromInteger(I.FromBits(u1,deep));
  var limit=I.FromBits(u1,deep);Check(limit.Depth==32);
  Reject(()=>E.FromInteger(limit));
  var broad=E.Constant(1,0);for(int k=0;k<8;k++)broad=E.Binary(E.Operator.Or,broad,broad);
  var wide=I.FromBits(u1,broad);Check(wide.Count==512);Reject(()=>I.Cast(u1,wide));
  foreach(bool exact in new[]{true,false}) {
   var plain=new[]{Assign(new[]{0},result)};
   Check(Encoding.UTF8.GetString(Request(exact,0,1,new[]{0},plain)).StartsWith(exact ? "QEXACT5\n0\n1\n0\n" : "QSAMPLE6\n0\n10000\n1731\n1\n0\n"));
   var types=new[]{u1};var v=I.Variable(u1,0);
   var store=new G{Kind=O.StoreInteger,VariableSlot=0,IntegerExpression=truth};
   var nested=new[]{Branch(E.Constant(1,1),new[]{store,Assign(new[]{0},E.FromInteger(v))})};
   Check(Encoding.UTF8.GetString(Request(exact,0,1,new[]{0},nested,types)).StartsWith(exact ? "QEXACT5\n" : "QSAMPLE6\n"));
   var invalid=I.FromBits(u1,E.IntegerCompare(E.Operator.Equal,I.Variable(s8,0),I.Constant(s8,0)));
   Reject(()=>Request(exact,0,1,new[]{0},new[]{new G{Kind=O.StoreInteger,VariableSlot=0,IntegerExpression=invalid}},types));
   var lazy=I.FromBits(u1,E.Logical(E.Operator.And,E.Constant(1,0),E.IntegerCompare(E.Operator.Equal,v,I.Constant(u1,0))));
   var guarded=new[]{new G{Kind=O.StoreInteger,VariableSlot=0,IntegerExpression=lazy},Assign(new[]{0},E.FromInteger(v))};
   var negative=E.IntegerCompare(E.Operator.Less,I.FromBits(s8,E.Complement(E.Constant(8,0))),I.Constant(s8,0));
   if(worker==null)continue;
   foreach(var program in new[]{plain,nested,new[]{Assign(new[]{0},negative)}}) {
    var values=Evaluate(worker,exact,0,1,new[]{0},program,Object.ReferenceEquals(program,nested) ? types : null);
    Check(values.Count==1 && Convert.ToString(values["1"])==(exact ? "1" : "10000"));
   }
   var zero=Evaluate(worker,exact,0,1,new[]{0},guarded,types);
   Check(zero.Count==1 && Convert.ToString(zero["0"])==(exact ? "1" : "10000"));
  }
 }
 static void VariableChecks(string worker) {
  var type=T.Create(T.Sign.Signed,8);var types=new[]{type};var value=I.Variable(type,0);
  var three=I.Constant(type,3);var positive=E.IntegerCompare(E.Operator.Greater,value,I.Constant(type,0));
  var store=new G {Kind=O.StoreInteger,VariableSlot=0,IntegerExpression=three};
  var clear=new G {Kind=O.ClearInteger,VariableSlot=0};
  Reject(()=>I.Variable(type,-1));Reject(()=>I.Variable(type,4096));Reject(()=>I.Variable(null,0));
  Reject(()=>Encode(positive,0));
  foreach(bool exact in new[]{true,false}) {
   var steps=new[]{store,Branch(positive,new[]{Assign(new[]{0},E.Constant(1,1))})};
   string encoded=Encoding.UTF8.GetString(Request(exact,0,1,new[]{0},steps,types));
   Check(encoded.StartsWith(exact ? "QEXACT4\n0\n1\n1\n0\n8\n" : "QSAMPLE5\n0\n10000\n1731\n1\n1\n0\n8\n"));
   Reject(()=>Request(exact,0,1,new[]{0},steps));
   Reject(()=>Request(exact,0,1,new[]{0},steps,new[]{T.Create(T.Sign.Unsigned,8)}));
   Reject(()=>Request(exact,0,1,new[]{0},steps,new T[0]));
   Reject(()=>Request(exact,0,1,new[]{0},steps,new T[]{null}));
   Reject(()=>Request(exact,0,0,new int[0],new G[0],new T[4097]));
   foreach(var bad in new[]{new G {Kind=O.StoreInteger,VariableSlot=0},new G {Kind=O.ClearInteger,VariableSlot=0,IntegerExpression=three},
     new G {Kind=O.StoreInteger,VariableSlot=1,IntegerExpression=three},new G {Kind=O.StoreInteger,VariableSlot=0,IntegerExpression=three,Expression="X"},
     new G {Kind=O.StoreInteger,VariableSlot=0,IntegerExpression=three,Wires=new[]{0}},new G {Kind=O.StoreInteger,VariableSlot=0,IntegerExpression=three,Mask=1},
     new G {Kind=O.Gate,Expression="X",Wires=new[]{0},VariableSlot=0},new G {Kind=O.ClearInteger,VariableSlot=0,ClassicalExpression=E.Constant(1,0)}})
    Reject(()=>Request(exact,1,1,new[]{0},new[]{bad},types));
   var invalid=E.IntegerCompare(E.Operator.Equal,I.Variable(type,1),three);
   Reject(()=>Request(exact,0,1,new[]{0},new[]{Branch(E.Constant(1,0),new[]{Branch(invalid,new G[0])})},types));
   if(worker==null)continue;
   var result=Evaluate(worker,exact,0,1,new[]{0},steps,types);Check(result.Count==1 && Convert.ToString(result["1"])==(exact ? "1" : "10000"));
   result=Evaluate(worker,exact,0,1,new[]{0},new[]{store,clear,new G {Kind=O.StoreInteger,VariableSlot=0,IntegerExpression=I.Constant(type,0)},Branch(positive,new[]{Assign(new[]{0},E.Constant(1,1))})},types);
   Check(result.Count==1 && Convert.ToString(result["0"])==(exact ? "1" : "10000"));
   var measured=I.Read(T.Create(T.Sign.Unsigned,1),0);
   result=Evaluate(worker,exact,1,1,new[]{0},new[]{new G {Expression="H",Wires=new[]{0}},new G {Kind=O.Measure,Wires=new[]{0},ClassicalBit=0},
    new G {Kind=O.StoreInteger,VariableSlot=0,IntegerExpression=measured},Assign(new[]{0},E.Constant(1,0)),Branch(positive,new[]{Assign(new[]{0},E.Constant(1,1))})},types);
   Check(result.Count==2);foreach(string label in new[]{"0","1"})Check(exact ? Convert.ToString(result[label])=="0.5" : Math.Abs(Convert.ToInt32(result[label])-5000)<400);
  }
 }
 static void PowerChecks(string worker) {
  var machine=T.Create(T.Sign.Signed);var byteType=T.Create(T.Sign.Signed,8);
  var two=I.Constant(machine,2);var three=I.Constant(machine,3);
  var power=I.Binary(I.Operator.Power,two,three);
  var equal=E.IntegerCompare(E.Operator.Equal,power,I.Constant(machine,8));
  Check(Encode(equal,0)=="6\n0\n3\n5\n0\n0\n0\n2\n0\n0\n0\n3\n0\n0\n0\n8\n");
  Check(equal.UsesTypedProtocol && power.Type.DeclaredWidth==0);
  Reject(()=>I.Binary(I.Operator.Power,null,three));Reject(()=>I.Binary(I.Operator.Power,two,null));
  var read=I.Read(byteType,0,1,2,3,4,5,6,7);
  var runtime=I.Binary(I.Operator.Power,two,read);
  var condition=E.IntegerCompare(E.Operator.Equal,runtime,I.Constant(machine,8));
  Reject(()=>Encode(condition,7));
  foreach(bool exact in new[]{true,false}) {
   var steps=new[]{Assign(new[]{0,1,2,3,4,5,6,7},E.Constant(8,3)),Assign(new[]{8},condition)};
   Check(Encoding.UTF8.GetString(Request(exact,0,9,new[]{8},steps)).StartsWith(exact ? "QEXACT3\n" : "QSAMPLE4\n"));
   if(worker==null)continue;
   var result=Evaluate(worker,exact,0,9,new[]{8},steps);
   Check(result.Count==1 && Convert.ToString(result["1"])==(exact ? "1" : "10000"));
   var nested=I.Binary(I.Operator.Power,two,I.Binary(I.Operator.Power,three,two));
   result=Evaluate(worker,exact,0,1,new[]{0},new[]{Assign(new[]{0},E.IntegerCompare(E.Operator.Equal,nested,I.Constant(machine,512)))});
   Check(result.Count==1 && Convert.ToString(result["1"])==(exact ? "1" : "10000"));
   foreach(ulong bad in new ulong[]{63,255}) {
    var prefix=Assign(new[]{0,1,2,3,4,5,6,7},E.Constant(8,bad));
    bool failed=false;try{Evaluate(worker,exact,0,9,new[]{8},new[]{prefix,Assign(new[]{8},condition)});}catch(InvalidOperationException){failed=true;}Check(failed);
    result=Evaluate(worker,exact,0,9,new[]{8},new[]{prefix,Branch(E.Constant(1,0),new[]{Assign(new[]{8},condition)})});
    Check(result.Count==1 && Convert.ToString(result["0"])==(exact ? "1" : "10000"));
   }
  }
 }
 static void IntegerBitChecks(string worker) {
  var sized=T.Create(T.Sign.Signed,3);var machine=T.Create(T.Sign.Signed);
  var value=E.FromInteger(I.Constant(sized,7));
  Check(value.Width==3 && value.UsesTypedProtocol && E.Complement(value).UsesTypedProtocol);
  Check(Encode(value,0)=="8\n0\n0\n3\n7\n");
  Reject(()=>E.FromInteger(null));Reject(()=>E.FromInteger(I.Constant(machine,1)));
  Reject(()=>E.FromInteger(I.Constant(T.Create(T.Sign.Unsigned),1)));
  var read=I.Read(sized,0,1,2);Reject(()=>Encode(E.FromInteger(read),2));
  var one=I.Constant(machine,1);var increment=E.FromInteger(I.Cast(sized,I.Binary(I.Operator.Add,read,one)));
  var deep=I.Constant(sized,0);for(int k=1;k<31;k++)deep=I.Cast(sized,deep);
  Check(Encode(E.FromInteger(deep),0).Length>32);Reject(()=>E.Complement(E.FromInteger(deep)));Reject(()=>E.FromInteger(I.Cast(sized,deep)));
  var broad=one;for(int k=0;k<8;k++)broad=I.Binary(I.Operator.Add,broad,broad);
  Reject(()=>E.FromInteger(I.Cast(sized,broad)));
  foreach(bool exact in new[]{true,false}) {
   var steps=new[]{Assign(new[]{0,1,2},E.Constant(3,3)),Assign(new[]{1,2,3},increment)};
   Check(Encoding.UTF8.GetString(Request(exact,0,4,new[]{3,2,1,0},steps)).StartsWith(exact ? "QEXACT3\n" : "QSAMPLE4\n"));
   Check(Encoding.UTF8.GetString(Request(exact,0,3,new[]{0},new[]{Branch(E.Constant(1,0),new[]{Assign(new[]{0,1,2},E.Complement(value))})})).StartsWith(exact ? "QEXACT3\n" : "QSAMPLE4\n"));
   Reject(()=>Request(exact,0,3,new[]{0},new[]{Assign(new[]{0},value)}));
   Reject(()=>Request(exact,0,3,new[]{0},new[]{Branch(E.Constant(1,0),new[]{Assign(new[]{0},E.FromInteger(I.Read(T.Create(T.Sign.Signed,1),3)))})}));
   if(worker==null)continue;
   var result=Evaluate(worker,exact,0,4,new[]{3,2,1,0},steps);Check(result.Count==1 && Convert.ToString(result["1001"])==(exact ? "1" : "10000"));
   foreach(var sign in new[]{T.Sign.Signed,T.Sign.Unsigned})foreach(int width in new[]{1,3,8,63,64}) {
    var targets=new int[width];for(int k=0;k<width;k++)targets[k]=k;
    var high=E.FromInteger(I.Constant(T.Create(sign,width),1UL<<(width-1)));
    result=Evaluate(worker,exact,0,width,targets,new[]{Assign(targets,high)});
    Check(result.Count==1 && Convert.ToString(result[new string('0',width-1)+"1"])==(exact ? "1" : "10000"));
   }
  }
 }
 static void LogicalChecks(string worker) {
  var zero=E.Constant(1,0);var one=E.Constant(1,1);
  var value=E.Logical(E.Operator.And,zero,one);
  Check(value.Width==1 && value.UsesTypedProtocol && E.Complement(value).UsesTypedProtocol);
  Check(Encode(value,0)=="7\n0\n0\n1\n0\n0\n1\n1\n");
  Reject(()=>E.Logical(E.Operator.And,null,one));Reject(()=>E.Logical(E.Operator.Or,zero,null));
  Reject(()=>E.Logical(E.Operator.Xor,zero,one));Reject(()=>E.Logical((E.Operator)99,zero,one));
  Reject(()=>E.Logical(E.Operator.And,E.Constant(2,0),one));Reject(()=>E.Logical(E.Operator.Or,one,E.Constant(2,0)));
  Reject(()=>Encode(E.Logical(E.Operator.And,zero,E.Read(1)),1));
  var deep=zero;for(int k=1;k<32;k++)deep=E.Logical(E.Operator.And,zero,deep);
  Check(Encode(deep,0).Length>32);Reject(()=>E.Logical(E.Operator.And,zero,deep));
  var broad=one;for(int k=0;k<8;k++)broad=E.Logical(E.Operator.Or,broad,broad);
  Check(Encode(E.Complement(broad),0).Length>512);Reject(()=>E.Complement(E.Complement(broad)));
  var machine=T.Create(T.Sign.Signed);
  var quotient=I.Binary(I.Operator.Divide,I.Constant(machine,6),I.Read(T.Create(T.Sign.Signed,1),0));
  var condition=E.IntegerCompare(E.Operator.Equal,quotient,I.Constant(machine,3));
  foreach(bool exact in new[]{true,false}) {
   Check(Encoding.UTF8.GetString(Request(exact,0,1,new[]{0},new[]{Assign(new[]{0},value)})).StartsWith(exact ? "QEXACT3\n" : "QSAMPLE4\n"));
   Check(Encoding.UTF8.GetString(Request(exact,0,1,new[]{0},new[]{Branch(zero,new[]{Assign(new[]{0},value)})})).StartsWith(exact ? "QEXACT3\n" : "QSAMPLE4\n"));
   Reject(()=>Request(exact,0,1,new[]{0},new[]{Assign(new[]{0},E.Logical(E.Operator.And,zero,E.Read(1)))}));
   if(worker==null)continue;
   foreach(var op in new[]{E.Operator.And,E.Operator.Or})for(int a=0;a<2;a++)for(int b=0;b<2;b++) {
    int want=op==E.Operator.And ? a&b : a|b;
    var result=Evaluate(worker,exact,0,1,new[]{0},new[]{Assign(new[]{0},E.Logical(op,E.Constant(1,(ulong)a),E.Constant(1,(ulong)b)))});
    Check(result.Count==1 && Convert.ToString(result[want.ToString()])==(exact ? "1" : "10000"));
   }
   foreach(var op in new[]{E.Operator.And,E.Operator.Or}) {
    int want=op==E.Operator.And ? 0 : 1;
    var result=Evaluate(worker,exact,0,1,new[]{0},new[]{Assign(new[]{0},E.Logical(op,E.Constant(1,(ulong)want),condition))});
    Check(result.Count==1 && Convert.ToString(result[want.ToString()])==(exact ? "1" : "10000"));
   }
  }
 }
 static void IntegerChecks(string worker) {
  var machine=T.Create(T.Sign.Signed);var s8=T.Create(T.Sign.Signed,8);var u8=T.Create(T.Sign.Unsigned,8);
  Check(machine.Width==64 && machine.DeclaredWidth==0 && T.Create(T.Sign.Signed,64).DeclaredWidth==64);
  var bits=new[]{0,1,2,3,4,5,6,7};var read=I.Read(s8,bits);bits[0]=63;var copy=read.Indices;copy[0]=62;Check(read.Indices[0]==0);
  var zero=I.Constant(machine,0);var negative=E.IntegerCompare(E.Operator.Less,read,zero);
  Check(negative.Width==1 && negative.UsesTypedProtocol && E.Complement(negative).UsesTypedProtocol);
  Check(Encode(negative,8)=="6\n2\n1\n0\n8\n0\n1\n2\n3\n4\n5\n6\n7\n0\n0\n0\n0\n");
  Reject(()=>T.Create((T.Sign)99));Reject(()=>T.Create(T.Sign.Signed,-1));Reject(()=>T.Create(T.Sign.Signed,65));
  Reject(()=>I.Read(s8,0));Reject(()=>I.Read(T.Create(T.Sign.Signed,1),64));Reject(()=>I.Constant(s8,256));
  Reject(()=>I.Cast(machine,null));Reject(()=>I.Binary((I.Operator)99,zero,zero));Reject(()=>E.IntegerCompare(E.Operator.And,zero,zero));
  Reject(()=>Encode(negative,7));Reject(()=>Encode(E.Complement(negative),7));
  var deep=zero;for(int k=1;k<32;k++)deep=I.Cast(machine,deep);Reject(()=>I.Cast(machine,deep));Reject(()=>E.IntegerCompare(E.Operator.Equal,deep,zero));
  var broad=zero;for(int k=0;k<8;k++)broad=I.Binary(I.Operator.Add,broad,broad);Reject(()=>E.IntegerCompare(E.Operator.Equal,broad,zero));
  var quotient=I.Binary(I.Operator.Divide,I.Constant(machine,6),read);
  var condition=E.IntegerCompare(E.Operator.Equal,quotient,I.Constant(machine,3));
  var initialize=Assign(new[]{0,1,2,3,4,5,6,7},E.Constant(8,255));var output=Assign(new[]{8},E.Constant(1,1));
  foreach(bool exact in new[]{true,false}) {
   var steps=new[]{initialize,Branch(negative,new[]{output})};
   Check(Encoding.UTF8.GetString(Request(exact,0,9,new[]{8},steps)).StartsWith(exact ? "QEXACT3\n" : "QSAMPLE4\n"));
   Check(Encoding.UTF8.GetString(Request(exact,0,9,new[]{8},new[]{Branch(E.Constant(1,0),new[]{Branch(condition,new[]{output})})})).StartsWith(exact ? "QEXACT3\n" : "QSAMPLE4\n"));
   Reject(()=>Request(exact,0,7,new int[0],new[]{Branch(E.Constant(1,0),new[]{Branch(negative,new G[0])})}));
   if(worker!=null) {
    var result=Evaluate(worker,exact,0,9,new[]{8},steps);Check(result.Count==1 && Convert.ToString(result["1"])==(exact ? "1" : "10000"));
    result=Evaluate(worker,exact,0,9,new[]{8},new[]{Assign(new[]{0,1,2,3,4,5,6,7},E.Constant(8,2)),Branch(condition,new[]{output})});Check(result.Count==1 && Convert.ToString(result["1"])==(exact ? "1" : "10000"));
    result=Evaluate(worker,exact,0,9,new[]{8},new[]{Branch(E.Constant(1,0),new[]{Branch(condition,new[]{output})})});Check(result.Count==1 && Convert.ToString(result["0"])==(exact ? "1" : "10000"));
    var cast=I.Cast(u8,read);result=Evaluate(worker,exact,0,9,new[]{8},new[]{initialize,Assign(new[]{8},E.IntegerCompare(E.Operator.Greater,cast,zero))});Check(result.Count==1 && Convert.ToString(result["1"])==(exact ? "1" : "10000"));
   }
  }
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
  IntegerChecks(args.Length>0 ? args[0] : null);
  LogicalChecks(args.Length>0 ? args[0] : null);
  IntegerBitChecks(args.Length>0 ? args[0] : null);
  PowerChecks(args.Length>0 ? args[0] : null);
  ComputedBitsChecks(args.Length>0 ? args[0] : null);
  LoopChecks(args.Length>0 ? args[0] : null);
  TransferChecks(args.Length>0 ? args[0] : null);
  TerminationChecks(args.Length>0 ? args[0] : null);
  VariableChecks(args.Length>0 ? args[0] : null);
  Console.WriteLine("PASS: "+checks+" classical expression adapter checks.");return 0;
 }catch(Exception e){Console.Error.WriteLine(e);return 1;}}
}
