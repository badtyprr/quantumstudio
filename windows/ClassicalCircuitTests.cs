// GPL-2.0-or-later; see COPYING.
using System;
using System.IO;
using System.Text;
class ClassicalCircuitTests {
 static int checks;
 static void Numerics(string worker) {
  var value=new ClassicalCircuit.RealNode{Kind="Variable",NumericKind="Angle",Width=8,Slot=0};
  var doc=new ClassicalCircuit.Document{Version=13,Qubits=1,LoopConditionBudget=1000,
   Registers=new[]{new ClassicalCircuit.Register{Name="c",Size=1}},Variables=new ClassicalCircuit.Variable[0],
   NumericVariables=new[]{new ClassicalCircuit.NumericVariable{Name="theta",NumericKind="Angle",Width=8}},OutputBits=new[]{0},
   Steps=new[]{new ClassicalCircuit.Step{Kind="StoreNumeric",VariableSlot=0,NumericValue=new ClassicalCircuit.RealNode{Kind="TypedConstant",NumericKind="Angle",Width=8,ValueBits="128"}},
    new ClassicalCircuit.Step{Kind="Rotation",Axis="Y",Angle=value,Wires=new[]{0}},new ClassicalCircuit.Step{Kind="Measure",Wires=new[]{0},ClassicalBit=0}}};
  var circuit=ClassicalCircuit.From(doc);string saved=circuit.Serialize();
  for(int i=0;i<3;i++){circuit=ClassicalCircuit.Load(saved);Check(circuit.Serialize()==saved);}
  Check(circuit.NumericTypes[0].Width==8);
  var copy=circuit.Snapshot();copy.NumericVariables[0].Width=7;Check(circuit.Serialize()==saved);
  foreach(bool exact in new[]{true,false}) {
   var request=exact ? NumericalSampling.RequestExact(1,1,new[]{0},circuit.SamplingGates(),circuit.VariableTypes,circuit.LoopConditionBudget,circuit.NumericTypes) :
    NumericalSampling.RequestClassical(1,1,100,1,new[]{0},circuit.SamplingGates(),circuit.VariableTypes,circuit.LoopConditionBudget,circuit.NumericTypes);
   Check(Encoding.UTF8.GetString(request).StartsWith(exact ? "QEXACT12\n" : "QSAMPLE13\n"));
   if(worker!=null){string result=NumericalSampling.RunRequest(worker,exact ? "--exact-circuit" : "--sample",request,System.Threading.CancellationToken.None,t=>t).GetAwaiter().GetResult();Check(result.Contains(exact ? "\"1\":\"1\"" : "\"1\":100"));}
  }
  for(int version=2;version<13;version++){copy=circuit.Snapshot();copy.Version=version;Reject(()=>ClassicalCircuit.From(copy));}
  foreach(Action<ClassicalCircuit.Document> corrupt in new Action<ClassicalCircuit.Document>[] {
   d=>d.NumericVariables=null,d=>d.NumericVariables[0].NumericKind="0",d=>d.NumericVariables[0].Width=0,d=>d.NumericVariables[0].Width=65,
   d=>d.NumericVariables[0].Name="c",d=>d.NumericVariables[0].NumericKind="Float",d=>d.Steps[0].VariableSlot=1,
   d=>d.Steps[0].NumericValue=null,d=>d.Steps[0].NumericValue.ValueBits="256",d=>d.Steps[0].NumericValue.ValueBits="-1",
   d=>d.Steps[0].NumericValue.Left=value,d=>d.Steps[0].Kind="ClearNumeric",d=>d.Steps[1].Angle.Width=7,
   d=>d.Steps[1].Angle.Slot=1,d=>d.Steps[1].NumericValue=value,d=>d.Steps[0].IntegerValue=new ClassicalCircuit.ExpressionNode{Kind="IntegerConstant",Width=0,Signedness="Signed",Value="0"}
  }){copy=circuit.Snapshot();corrupt(copy);Reject(()=>ClassicalCircuit.From(copy));}
  Reject(()=>ClassicalCircuit.Load(saved.Replace("\"NumericKind\":\"Angle\"","\"NumericKind\":1")));
  Reject(()=>ClassicalCircuit.Load(saved.Replace("\"NumericValue\":{","\"NumericValue\":{\"Unknown\":null,")));
  var f=ClassicalRealExpression.TypedConstant(ClassicalNumericType.Create(ClassicalNumericType.NumericKind.Float,32),0);
  var cross=ClassicalIntegerExpression.FromNumeric(ClassicalIntegerType.Create(ClassicalIntegerType.Sign.Signed),f);
  var gates=new[]{new NumericalSampling.Gate{Kind=NumericalSampling.Operation.Assign,Wires=new[]{0},ClassicalExpression=ClassicalExpression.IntegerCompare(ClassicalExpression.Operator.Equal,cross,ClassicalIntegerExpression.Constant(cross.Type,0))}};
  Check(Encoding.UTF8.GetString(NumericalSampling.RequestExact(0,1,new[]{0},gates)).StartsWith("QEXACT12\n"));
  for(int i=0;i<14;i++)f=ClassicalRealExpression.FromInteger(ClassicalIntegerExpression.FromNumeric(cross.Type,f));
  Reject(()=>ClassicalRealExpression.FromInteger(ClassicalIntegerExpression.FromNumeric(cross.Type,ClassicalRealExpression.FromInteger(ClassicalIntegerExpression.FromNumeric(cross.Type,f)))));
 }
 static void ParameterGates() {
  var doc=new ClassicalCircuit.Document{Version=12,Qubits=3,LoopConditionBudget=1000,Registers=new ClassicalCircuit.Register[0],Variables=new ClassicalCircuit.Variable[0],OutputBits=new int[0],
   Steps=new[]{new ClassicalCircuit.Step{Kind="ParameterGate",Wires=new[]{2,0,1},ParameterGate=new ClassicalCircuit.ParameterGateNode{Gate="U3",Controls=2,ControlState="1",
    Parameters=new[]{new ClassicalCircuit.RealNode{Kind="Constant",ValueBits="0"},new ClassicalCircuit.RealNode{Kind="Constant",ValueBits="4607182418800017408"},new ClassicalCircuit.RealNode{Kind="Constant",ValueBits="4611686018427387904"}},
    Power=new ClassicalCircuit.ExpressionNode{Kind="IntegerConstant",Signedness="Signed",Width=0,Value="1"}}}}};
  var circuit=ClassicalCircuit.From(doc);string saved=circuit.Serialize();
  Check(ClassicalCircuit.Load(saved).Serialize()==saved);
  Check(circuit.SamplingGates()[0].ParameterGate.ControlState==1);
  foreach(bool exact in new[]{true,false}) {
   var payload=exact ? NumericalSampling.RequestExact(3,0,new int[0],circuit.SamplingGates(),circuit.VariableTypes,circuit.LoopConditionBudget) : NumericalSampling.RequestClassical(3,0,10,1,new int[0],circuit.SamplingGates(),circuit.VariableTypes,circuit.LoopConditionBudget);
   Check(Encoding.UTF8.GetString(payload).StartsWith(exact ? "QEXACT11\n" : "QSAMPLE12\n"));
  }
  for(int version=2;version<12;version++){var copy=circuit.Snapshot();copy.Version=version;Reject(()=>ClassicalCircuit.From(copy));}
  foreach(Action<ClassicalCircuit.Step> corrupt in new Action<ClassicalCircuit.Step>[] {
   s=>s.ParameterGate=null,s=>s.ParameterGate.Gate="6",s=>s.ParameterGate.Gate="Unknown",s=>s.ParameterGate.Controls=-1,
   s=>s.ParameterGate.Controls=3,s=>s.ParameterGate.ControlState="4",s=>s.ParameterGate.ControlState="-1",
   s=>s.ParameterGate.Parameters=null,s=>s.ParameterGate.Parameters=new ClassicalCircuit.RealNode[0],
   s=>s.ParameterGate.Parameters[1]=null,s=>s.ParameterGate.Power=null,
   s=>s.Wires=new[]{0,0,1},s=>s.Wires=new[]{0,1},s=>s.Expression="H",s=>s.Axis="X",s=>s.Kind="Gate",
   s=>s.ParameterGate.Parameters[2].ValueBits="9218868437227405312"
  }){var copy=circuit.Snapshot();corrupt(copy.Steps[0]);Reject(()=>ClassicalCircuit.From(copy));}
  Reject(()=>ClassicalCircuit.Load(saved.Replace("\"ControlState\":\"1\"","\"ControlState\":1")));
  Reject(()=>ClassicalCircuit.Load(saved.Replace("\"ParameterGate\":{","\"ParameterGate\":{\"Unexpected\":0,")));
 }
 static void Rotations(string worker) {
  var angle=new ClassicalCircuit.RealNode{Kind="Constant",ValueBits="13830554455654793216"};
  var doc=new ClassicalCircuit.Document{Version=11,LoopConditionBudget=1000,Qubits=1,
   Registers=new[]{new ClassicalCircuit.Register{Name="c",Size=1}},Variables=new ClassicalCircuit.Variable[0],OutputBits=new[]{0},
   Steps=new[]{new ClassicalCircuit.Step{Kind="Rotation",Axis="Y",Angle=angle,Wires=new[]{0}}}};
  var circuit=ClassicalCircuit.From(doc);string saved=circuit.Serialize();
  for(int n=0;n<3;++n){circuit=ClassicalCircuit.Load(saved);Check(circuit.Serialize()==saved);Check(circuit.SamplingGates()[0].Angle.Value==-1);}
  var copy=circuit.Snapshot();copy.Steps[0].Angle.ValueBits="0";Check(circuit.Serialize()==saved);
  foreach(bool exact in new[]{true,false}) {
   var bytes=exact ? NumericalSampling.RequestExact(1,1,new[]{0},circuit.SamplingGates(),circuit.VariableTypes,circuit.LoopConditionBudget) :
    NumericalSampling.RequestClassical(1,1,100,1,new[]{0},circuit.SamplingGates(),circuit.VariableTypes,circuit.LoopConditionBudget);
   Check(Encoding.UTF8.GetString(bytes).EndsWith("16\n0\n1\n0\n13830554455654793216\n"));
  }
  for(int version=2;version<11;++version){copy=circuit.Snapshot();copy.Version=version;Reject(()=>ClassicalCircuit.From(copy));}
  foreach(Action<ClassicalCircuit.Step> corrupt in new Action<ClassicalCircuit.Step>[] {
   s=>s.Axis=null,s=>s.Axis="1",s=>s.Axis="y",s=>s.Angle=null,s=>s.Kind="Gate",s=>s.Expression="X",
   s=>s.Angle.ValueBits="NaN",s=>s.Angle.ValueBits="-1",s=>s.Angle.ValueBits="9218868437227405312",
   s=>s.Angle.Operator="Add",s=>s.Angle.Left=angle,s=>s.Angle.Kind="Unknown",
   s=>s.Angle=new ClassicalCircuit.RealNode{Kind="Integer",IntegerValue=new ClassicalCircuit.ExpressionNode{Kind="IntegerVariable",Signedness="Signed",Width=0,Slot=0}}
  }) {copy=circuit.Snapshot();corrupt(copy.Steps[0]);Reject(()=>ClassicalCircuit.From(copy));}
  copy=circuit.Snapshot();copy.Steps[0].Angle=new ClassicalCircuit.RealNode{Kind="Binary",Operator="Multiply",Left=angle,
   Right=new ClassicalCircuit.RealNode{Kind="Integer",IntegerValue=new ClassicalCircuit.ExpressionNode{Kind="IntegerRead",Signedness="Unsigned",Width=1,Bits=new[]{0}}}};
  var feedback=ClassicalCircuit.From(copy);Check(ClassicalCircuit.Load(feedback.Serialize()).Serialize()==feedback.Serialize());
  Check(feedback.SamplingGates()[0].Angle.Right.Integer.Indices[0]==0);
  Reject(()=>ClassicalCircuit.Load(saved.Replace("\"ValueBits\":\"13830554455654793216\"","\"ValueBits\":1")));
  Reject(()=>ClassicalCircuit.Load(saved.Replace("\"ValueBits\":","\"Unexpected\":0,\"ValueBits\":")));
  if(worker!=null)foreach(bool exact in new[]{true,false}) {
   copy=circuit.Snapshot();copy.Steps[0].Angle.ValueBits="0";
   copy.Steps=new[]{copy.Steps[0],new ClassicalCircuit.Step{Kind="Measure",Wires=new[]{0},ClassicalBit=0}};
   var loaded=ClassicalCircuit.Load(ClassicalCircuit.From(copy).Serialize());
   var payload=exact ? NumericalSampling.RequestExact(1,1,new[]{0},loaded.SamplingGates(),loaded.VariableTypes,loaded.LoopConditionBudget) :
    NumericalSampling.RequestClassical(1,1,100,1,new[]{0},loaded.SamplingGates(),loaded.VariableTypes,loaded.LoopConditionBudget);
   string result=NumericalSampling.RunRequest(worker,exact ? "--exact-circuit" : "--sample",payload,System.Threading.CancellationToken.None,s=>s).GetAwaiter().GetResult();
   Check(result.Contains(exact ? "\"0\":\"1\"" : "\"0\":100"));
  }
 }
 static void Ranges(string worker) {
  Func<ulong,ClassicalCircuit.ExpressionNode> literal=n=>new ClassicalCircuit.ExpressionNode{Kind="IntegerConstant",Signedness="Signed",Width=0,Value=n.ToString(System.Globalization.CultureInfo.InvariantCulture)};
  Func<int,ClassicalCircuit.ExpressionNode> variable=n=>new ClassicalCircuit.ExpressionNode{Kind="IntegerVariable",Signedness="Signed",Width=0,Slot=n};
  var range=new ClassicalCircuit.Step{Kind="ForRange",VariableSlot=0,Range=new ClassicalCircuit.RangeNode{Start=literal(0),Stop=literal(2),Step=literal(1)},WhenTrue=new[]{new ClassicalCircuit.Step{Kind="StoreInteger",VariableSlot=1,IntegerValue=new ClassicalCircuit.ExpressionNode{Kind="IntegerBinary",Operator="Add",Left=variable(1),Right=variable(0)}}}};
  var doc=new ClassicalCircuit.Document{Version=10,LoopConditionBudget=4,Qubits=0,Registers=new[]{new ClassicalCircuit.Register{Name="c",Size=1}},Variables=new[]{new ClassicalCircuit.Variable{Name="i",Signedness="Signed",Width=0},new ClassicalCircuit.Variable{Name="sum",Signedness="Signed",Width=0}},OutputBits=new[]{0},Steps=new[]{new ClassicalCircuit.Step{Kind="StoreInteger",VariableSlot=1,IntegerValue=literal(0)},range,new ClassicalCircuit.Step{Kind="Assign",Wires=new[]{0},ClassicalValue=new ClassicalCircuit.ExpressionNode{Kind="IntegerCompare",Operator="Equal",Left=variable(1),Right=literal(3)}}}};
  var circuit=ClassicalCircuit.From(doc);var saved=circuit.Serialize();
  for(int n=0;n<3;n++){circuit=ClassicalCircuit.Load(saved);Check(circuit.Serialize()==saved);Check(circuit.Snapshot().Version==10);}
  var copy=circuit.Snapshot();copy.Steps[1].Range.Start.Value="99";copy.Steps[1].WhenTrue[0].IntegerValue.Left.Slot=0;Check(circuit.Serialize()==saved);
  for(int version=2;version<=9;version++){copy=circuit.Snapshot();copy.Version=version;Reject(()=>ClassicalCircuit.From(copy));}
  copy=circuit.Snapshot();copy.Version=13;Reject(()=>ClassicalCircuit.From(copy));
  copy=circuit.Snapshot();copy.Variables=null;Reject(()=>ClassicalCircuit.From(copy));
  copy=circuit.Snapshot();copy.LoopConditionBudget=null;Reject(()=>ClassicalCircuit.From(copy));
  foreach(Action<ClassicalCircuit.Step> corrupt in new Action<ClassicalCircuit.Step>[] {
   s=>s.Range=null,s=>s.Range.Start=null,s=>s.Range.Stop=null,s=>s.Range.Step=null,
   s=>s.VariableSlot=null,s=>s.VariableSlot=-1,s=>s.VariableSlot=2,s=>s.WhenTrue=null,
   s=>s.WhenFalse=new ClassicalCircuit.Step[0],s=>s.Expression="X",s=>s.Wires=new[]{0},
   s=>s.ClassicalBit=0,s=>s.Mask="0",s=>s.Value="0",s=>s.IntegerValue=literal(0),
   s=>s.ClassicalValue=new ClassicalCircuit.ExpressionNode{Kind="Constant",Width=1,Value="0"},
   s=>s.Range.Start=variable(2),s=>s.Range.Step.Kind="Constant",s=>s.Kind="ClearInteger"
  }){copy=circuit.Snapshot();corrupt(copy.Steps[1]);Reject(()=>ClassicalCircuit.From(copy));}
  var unknown=saved.Replace("\"Range\":{","\"Range\":{\"Unexpected\":0,");Check(unknown!=saved);Reject(()=>ClassicalCircuit.Load(unknown));
  copy=circuit.Snapshot();copy.Steps[0].Range=copy.Steps[1].Range;Reject(()=>ClassicalCircuit.From(copy));
  // A zero step is a runtime failure, so unreachable ranges can still be saved.
  copy=circuit.Snapshot();copy.Steps[1].Range.Step.Value="0";Check(ClassicalCircuit.From(copy).Snapshot().Steps[1].Range.Step.Value=="0");
  if(worker==null)return;
  foreach(bool exact in new[]{false,true}) {
   byte[] request=exact ? NumericalSampling.RequestExact(0,1,new[]{0},circuit.SamplingGates(),circuit.VariableTypes,circuit.LoopConditionBudget) : NumericalSampling.RequestClassical(0,1,10,1,new[]{0},circuit.SamplingGates(),circuit.VariableTypes,circuit.LoopConditionBudget);
   Check(Encoding.UTF8.GetString(request).StartsWith(exact ? "QEXACT9\n" : "QSAMPLE10\n"));
   string result=NumericalSampling.RunRequest(worker,exact ? "--exact-circuit" : "--sample",request,System.Threading.CancellationToken.None,text=>text).GetAwaiter().GetResult();
   Check(result.Contains(exact ? "\"1\":\"1\"" : "\"1\":10"));
  }
 }
 static void Termination(string worker) {
  var yes=new ClassicalCircuit.ExpressionNode{Kind="Constant",Width=1,Value="1"};
  var doc=new ClassicalCircuit.Document{Version=9,LoopConditionBudget=0,Qubits=0,Registers=new[]{new ClassicalCircuit.Register{Name="c",Size=1}},Variables=new ClassicalCircuit.Variable[0],OutputBits=new[]{0},Steps=new[]{new ClassicalCircuit.Step{Kind="End"},new ClassicalCircuit.Step{Kind="Assign",Wires=new[]{0},ClassicalValue=yes}}};
  var circuit=ClassicalCircuit.From(doc);string saved=circuit.Serialize();
  Check(ClassicalCircuit.Load(saved).Serialize()==saved);
  var copy=circuit.Snapshot();copy.Steps[0].Kind="Break";Check(circuit.Serialize()==saved);
  for(int version=2;version<=8;version++) {copy=circuit.Snapshot();copy.Version=version;Reject(()=>ClassicalCircuit.From(copy));}
  copy=circuit.Snapshot();copy.Variables=null;Reject(()=>ClassicalCircuit.From(copy));
  copy=circuit.Snapshot();copy.LoopConditionBudget=null;Reject(()=>ClassicalCircuit.From(copy));
  foreach(Action<ClassicalCircuit.Step> corrupt in new Action<ClassicalCircuit.Step>[] {
   s=>s.Expression="X",s=>s.Wires=new[]{0},s=>s.ClassicalBit=0,s=>s.Mask="0",s=>s.Value="0",s=>s.ClassicalValue=yes,
   s=>s.VariableSlot=0,s=>s.IntegerValue=new ClassicalCircuit.ExpressionNode{Kind="IntegerConstant",Signedness="Unsigned",Width=1,Value="0"},
   s=>s.WhenTrue=new ClassicalCircuit.Step[0],s=>s.WhenFalse=new ClassicalCircuit.Step[0]
  }) {copy=circuit.Snapshot();corrupt(copy.Steps[0]);Reject(()=>ClassicalCircuit.From(copy));}
  copy=circuit.Snapshot();copy.Steps[1].Wires=new[]{1};Reject(()=>ClassicalCircuit.From(copy));
  foreach(bool nested in new[]{false,true}) {
   copy=circuit.Snapshot();
   if(nested) {copy.LoopConditionBudget=1;copy.Steps=new[]{new ClassicalCircuit.Step{Kind="While",ClassicalValue=yes,WhenTrue=copy.Steps},copy.Steps[1]};}
   var reopened=ClassicalCircuit.Load(ClassicalCircuit.From(copy).Serialize());
   Check(reopened.Snapshot().Version==9);
   if(worker==null)continue;
   foreach(bool exact in new[]{true,false}) {
    byte[] request=exact ? NumericalSampling.RequestExact(0,1,new[]{0},reopened.SamplingGates(),reopened.VariableTypes,reopened.LoopConditionBudget) : NumericalSampling.RequestClassical(0,1,10,1,new[]{0},reopened.SamplingGates(),reopened.VariableTypes,reopened.LoopConditionBudget);
    Check(Encoding.UTF8.GetString(request).StartsWith(exact ? "QEXACT8\n" : "QSAMPLE9\n"));
    string result=NumericalSampling.RunRequest(worker,exact ? "--exact-circuit" : "--sample",request,System.Threading.CancellationToken.None,text=>text).GetAwaiter().GetResult();
    var root=new System.Web.Script.Serialization.JavaScriptSerializer().Deserialize<System.Collections.Generic.Dictionary<string,object>>(result);
    var values=(System.Collections.Generic.Dictionary<string,object>)root[exact ? "probabilities" : "counts"];
    Check(values.Count==1 && Convert.ToString(values["0"])==(exact ? "1" : "10"));
   }
  }
 }
 static void Transfers(string worker) {
  var yes=new ClassicalCircuit.ExpressionNode{Kind="Constant",Width=1,Value="1"};
  var no=new ClassicalCircuit.ExpressionNode{Kind="Constant",Width=1,Value="0"};
  foreach(string kind in new[]{"Break","Continue"}) {
   var doc=new ClassicalCircuit.Document{Version=8,LoopConditionBudget=2,Qubits=0,Registers=new[]{new ClassicalCircuit.Register{Name="c",Size=1}},Variables=new ClassicalCircuit.Variable[0],OutputBits=new[]{0},Steps=new[]{
    new ClassicalCircuit.Step{Kind="Assign",Wires=new[]{0},ClassicalValue=yes},
    new ClassicalCircuit.Step{Kind="While",ClassicalValue=new ClassicalCircuit.ExpressionNode{Kind="Read",Bits=new[]{0}},WhenTrue=new[]{
     new ClassicalCircuit.Step{Kind="Assign",Wires=new[]{0},ClassicalValue=no},new ClassicalCircuit.Step{Kind=kind},new ClassicalCircuit.Step{Kind="Assign",Wires=new[]{0},ClassicalValue=yes}}}}};
   var circuit=ClassicalCircuit.From(doc);string saved=circuit.Serialize();
   Check(ClassicalCircuit.Load(saved).Serialize()==saved);
   var copy=circuit.Snapshot();copy.Steps[1].WhenTrue[1].Kind="Reset";Check(circuit.Serialize()==saved);
   foreach(int version in new[]{2,3,4,5,6,7}) {copy=circuit.Snapshot();copy.Version=version;Reject(()=>ClassicalCircuit.From(copy));}
   copy=circuit.Snapshot();copy.LoopConditionBudget=null;Reject(()=>ClassicalCircuit.From(copy));
   copy=circuit.Snapshot();copy.Variables=null;Reject(()=>ClassicalCircuit.From(copy));
   foreach(int budget in new[]{-1,1000001}) {copy=circuit.Snapshot();copy.LoopConditionBudget=budget;Reject(()=>ClassicalCircuit.From(copy));}
   foreach(Action<ClassicalCircuit.Step> corrupt in new Action<ClassicalCircuit.Step>[] {
    s=>s.Expression="X",s=>s.Wires=new[]{0},s=>s.ClassicalBit=0,s=>s.Mask="0",s=>s.Value="0",s=>s.ClassicalValue=yes,
    s=>s.VariableSlot=0,s=>s.IntegerValue=new ClassicalCircuit.ExpressionNode{Kind="IntegerConstant",Signedness="Unsigned",Width=1,Value="0"},
    s=>s.WhenTrue=new ClassicalCircuit.Step[0],s=>s.WhenFalse=new ClassicalCircuit.Step[0]
   }) {copy=circuit.Snapshot();corrupt(copy.Steps[1].WhenTrue[1]);Reject(()=>ClassicalCircuit.From(copy));}
   copy=circuit.Snapshot();copy.Steps=new[]{new ClassicalCircuit.Step{Kind=kind}};Reject(()=>ClassicalCircuit.From(copy));
   copy=circuit.Snapshot();copy.Steps=new[]{new ClassicalCircuit.Step{Kind="ExpressionBranch",ClassicalValue=no,WhenTrue=new[]{new ClassicalCircuit.Step{Kind=kind}},WhenFalse=new ClassicalCircuit.Step[0]}};Reject(()=>ClassicalCircuit.From(copy));
   if(worker!=null)foreach(bool exact in new[]{true,false}) {
    var opened=ClassicalCircuit.Load(saved);
    byte[] request=exact ? NumericalSampling.RequestExact(0,1,new[]{0},opened.SamplingGates(),opened.VariableTypes,opened.LoopConditionBudget) : NumericalSampling.RequestClassical(0,1,10,1,new[]{0},opened.SamplingGates(),opened.VariableTypes,opened.LoopConditionBudget);
    Check(Encoding.UTF8.GetString(request).StartsWith(exact ? "QEXACT7\n" : "QSAMPLE8\n"));
    string result=NumericalSampling.RunRequest(worker,exact ? "--exact-circuit" : "--sample",request,System.Threading.CancellationToken.None,text=>text).GetAwaiter().GetResult();
    var root=new System.Web.Script.Serialization.JavaScriptSerializer().Deserialize<System.Collections.Generic.Dictionary<string,object>>(result);
    var values=(System.Collections.Generic.Dictionary<string,object>)root[exact ? "probabilities" : "counts"];
    Check(values.Count==1 && Convert.ToString(values["0"])==(exact ? "1" : "10"));
   }
  }
 }
 static void Check(bool ok) {if(!ok)throw new Exception("Check failed: "+checks);checks++;}
 static void Reject(Action action) {try {action();}catch(ArgumentException){checks++;return;}catch(InvalidDataException){checks++;return;}throw new Exception("Invalid circuit accepted: "+checks);}
 static void Loops(string worker) {
  var yes=new ClassicalCircuit.ExpressionNode{Kind="Constant",Width=1,Value="1"};
  var no=new ClassicalCircuit.ExpressionNode{Kind="Constant",Width=1,Value="0"};
  var doc=new ClassicalCircuit.Document{Version=7,LoopConditionBudget=2,Qubits=0,Registers=new[]{new ClassicalCircuit.Register{Name="c",Size=1}},Variables=new ClassicalCircuit.Variable[0],OutputBits=new[]{0},Steps=new[]{
   new ClassicalCircuit.Step{Kind="Assign",Wires=new[]{0},ClassicalValue=yes},
   new ClassicalCircuit.Step{Kind="While",ClassicalValue=new ClassicalCircuit.ExpressionNode{Kind="Read",Bits=new[]{0}},WhenTrue=new[]{new ClassicalCircuit.Step{Kind="Assign",Wires=new[]{0},ClassicalValue=no}}}}};
  var circuit=ClassicalCircuit.From(doc);string saved=circuit.Serialize();
  foreach(string transfer in new[]{"Break","Continue"}) {
   var invalid=circuit.Snapshot();invalid.Steps[1].WhenTrue=new[]{new ClassicalCircuit.Step{Kind=transfer}};
   Reject(()=>ClassicalCircuit.From(invalid));
   Reject(()=>ClassicalCircuit.Load(new System.Web.Script.Serialization.JavaScriptSerializer().Serialize(invalid)));
  }
  Check(circuit.LoopConditionBudget==2 && ClassicalCircuit.Load(saved).Serialize()==saved);
  Check(circuit.Snapshot().Steps[1].WhenFalse==null);
  var copy=circuit.Snapshot();copy.LoopConditionBudget=0;copy.Steps[1].WhenTrue[0].ClassicalValue.Value="1";
  Check(circuit.LoopConditionBudget==2 && circuit.Serialize()==saved);
  foreach(int version in new[]{2,3,4,5,6}) {var bad=circuit.Snapshot();bad.Version=version;Reject(()=>ClassicalCircuit.From(bad));bad.LoopConditionBudget=null;Reject(()=>ClassicalCircuit.From(bad));}
  foreach(int budget in new[]{-1,1000001}){var bad=circuit.Snapshot();bad.LoopConditionBudget=budget;Reject(()=>ClassicalCircuit.From(bad));}
  copy=circuit.Snapshot();copy.LoopConditionBudget=null;Reject(()=>ClassicalCircuit.From(copy));
  copy=circuit.Snapshot();copy.Variables=null;Reject(()=>ClassicalCircuit.From(copy));
  copy=circuit.Snapshot();copy.Steps[1].WhenFalse=new ClassicalCircuit.Step[0];Reject(()=>ClassicalCircuit.From(copy));
  copy=circuit.Snapshot();copy.Steps[1].WhenTrue=null;Reject(()=>ClassicalCircuit.From(copy));
  copy=circuit.Snapshot();copy.Steps[1].ClassicalValue=yes;copy.Steps[1].ClassicalValue.Width=2;Reject(()=>ClassicalCircuit.From(copy));
  copy=circuit.Snapshot();copy.Steps[1].WhenTrue[0].Wires=new[]{1};Reject(()=>ClassicalCircuit.From(copy));
  Reject(()=>ClassicalCircuit.Load(saved.Replace("\"LoopConditionBudget\":2","\"LoopConditionBudget\":\"2\"")));
  foreach(int budget in new[]{0,1000000}){copy=circuit.Snapshot();copy.LoopConditionBudget=budget;Check(ClassicalCircuit.From(copy).LoopConditionBudget==budget);}
  if(worker!=null)foreach(bool exact in new[]{true,false}) {
   var opened=ClassicalCircuit.Load(saved);
   byte[] request=exact ? NumericalSampling.RequestExact(0,1,new[]{0},opened.SamplingGates(),opened.VariableTypes,opened.LoopConditionBudget) : NumericalSampling.RequestClassical(0,1,10,1,new[]{0},opened.SamplingGates(),opened.VariableTypes,opened.LoopConditionBudget);
   string result=NumericalSampling.RunRequest(worker,exact ? "--exact-circuit" : "--sample",request,System.Threading.CancellationToken.None,text=>text).GetAwaiter().GetResult();
   var root=new System.Web.Script.Serialization.JavaScriptSerializer().Deserialize<System.Collections.Generic.Dictionary<string,object>>(result);
   var values=(System.Collections.Generic.Dictionary<string,object>)root[exact ? "probabilities" : "counts"];
   Check(values.Count==1 && Convert.ToString(values["0"])==(exact ? "1" : "10"));
  }
 }
 static void Variables(string worker) {
  var constant=new ClassicalCircuit.ExpressionNode {Kind="IntegerConstant",Signedness="Signed",Width=8,Value="3"};
  var variable=new ClassicalCircuit.ExpressionNode {Kind="IntegerVariable",Signedness="Signed",Width=8,Slot=0};
  var doc=new ClassicalCircuit.Document {Version=5,Qubits=0,Registers=new[]{new ClassicalCircuit.Register {Name="flag",Size=1}},OutputBits=new[]{0},
   Variables=new[]{new ClassicalCircuit.Variable {Name="counter",Signedness="Signed",Width=8}},Steps=new[]{
    new ClassicalCircuit.Step {Kind="StoreInteger",VariableSlot=0,IntegerValue=constant},
    new ClassicalCircuit.Step {Kind="Assign",Wires=new[]{0},ClassicalValue=new ClassicalCircuit.ExpressionNode {Kind="IntegerCompare",Operator="Equal",Left=variable,Right=constant}}}};
  var circuit=ClassicalCircuit.From(doc);string saved=circuit.Serialize();
  Check(ClassicalCircuit.Load(saved).Serialize()==saved);
  Check(circuit.VariableTypes.Length==1 && circuit.VariableTypes[0].DeclaredWidth==8);
  var snapshot=circuit.Snapshot();snapshot.Variables[0].Name="changed";snapshot.Steps[0].IntegerValue.Value="0";
  Check(circuit.Serialize()==saved && circuit.Snapshot().Variables[0].Name=="counter");
  var types=circuit.VariableTypes;types[0]=ClassicalIntegerType.Create(ClassicalIntegerType.Sign.Unsigned);
  Check(circuit.VariableTypes[0].Signedness==ClassicalIntegerType.Sign.Signed);
  Check(Encoding.UTF8.GetString(NumericalSampling.RequestExact(0,1,new[]{0},circuit.SamplingGates(),circuit.VariableTypes)).StartsWith("QEXACT4\n"));
  Check(Encoding.UTF8.GetString(NumericalSampling.RequestClassical(0,1,10,1,new[]{0},circuit.SamplingGates(),circuit.VariableTypes)).StartsWith("QSAMPLE5\n"));
  foreach(int version in new[]{2,3,4}){var invalid=circuit.Snapshot();invalid.Version=version;Reject(()=>ClassicalCircuit.From(invalid));}
  if(worker!=null)foreach(bool exact in new[]{true,false}) {
   var reopened=ClassicalCircuit.Load(saved);
   byte[] request=exact ? NumericalSampling.RequestExact(0,1,new[]{0},reopened.SamplingGates(),reopened.VariableTypes) : NumericalSampling.RequestClassical(0,1,10,1,new[]{0},reopened.SamplingGates(),reopened.VariableTypes);
   string result=NumericalSampling.RunRequest(worker,exact ? "--exact-circuit" : "--sample",request,System.Threading.CancellationToken.None,text=>text).GetAwaiter().GetResult();
   var root=new System.Web.Script.Serialization.JavaScriptSerializer().Deserialize<System.Collections.Generic.Dictionary<string,object>>(result);
   var values=(System.Collections.Generic.Dictionary<string,object>)root[exact ? "probabilities" : "counts"];
   Check(values.Count==1 && Convert.ToString(values["1"])==(exact ? "1" : "10"));
  }
  var bad=circuit.Snapshot();bad.Variables=null;Reject(()=>ClassicalCircuit.From(bad));
  bad=circuit.Snapshot();bad.Variables[0].Name="flag";Reject(()=>ClassicalCircuit.From(bad));
  bad=circuit.Snapshot();bad.Variables[0].Width=65;Reject(()=>ClassicalCircuit.From(bad));
  bad=circuit.Snapshot();bad.Variables[0].Signedness="0";Reject(()=>ClassicalCircuit.From(bad));
  bad=circuit.Snapshot();bad.Steps[0].VariableSlot=1;Reject(()=>ClassicalCircuit.From(bad));
  bad=circuit.Snapshot();bad.Steps[1].ClassicalValue.Left.Signedness="Unsigned";Reject(()=>ClassicalCircuit.From(bad));
  bad=circuit.Snapshot();bad.Steps[1].VariableSlot=0;Reject(()=>ClassicalCircuit.From(bad));
  bad=circuit.Snapshot();bad.Steps[0].Kind="ClearInteger";Reject(()=>ClassicalCircuit.From(bad));
  bad.Steps[0].IntegerValue=null;Check(ClassicalCircuit.From(bad).Snapshot().Steps[0].Kind=="ClearInteger");
 }
 static ClassicalCircuit.Step Measure(int bit) {return new ClassicalCircuit.Step {Kind="Measure",Wires=new[]{0},ClassicalBit=bit};}
 static ClassicalCircuit.Document Program() {return new ClassicalCircuit.Document {Version=2,Qubits=1,Registers=new[]{new ClassicalCircuit.Register {Name="flag",Size=1},new ClassicalCircuit.Register {Name="record",Size=63}},OutputBits=new[]{63,0},Steps=new[]{Measure(63),new ClassicalCircuit.Step {Kind="Branch",Mask="9223372036854775808",Value="9223372036854775808",WhenTrue=new[]{Measure(0)},WhenFalse=new ClassicalCircuit.Step[0]}}};}
 static ClassicalCircuit.ExpressionNode Constant(int width,string value) {return new ClassicalCircuit.ExpressionNode {Kind="Constant",Width=width,Value=value};}
 static ClassicalCircuit.Document Expressions() {
  var result=Program();result.Version=3;
  result.Steps=new[]{new ClassicalCircuit.Step {Kind="Assign",Wires=new[]{63},ClassicalValue=Constant(1,"1")},
   new ClassicalCircuit.Step {Kind="ExpressionBranch",ClassicalValue=new ClassicalCircuit.ExpressionNode {Kind="Read",Bits=new[]{63}},WhenTrue=new[]{Measure(0)},WhenFalse=new ClassicalCircuit.Step[0]}};
  return result;
 }
 static ClassicalCircuit.Document TypedProgram() {
  return new ClassicalCircuit.Document {Version=4,Qubits=0,Registers=new[]{new ClassicalCircuit.Register{Name="c",Size=9}},OutputBits=new[]{8},Steps=new[]{
   new ClassicalCircuit.Step{Kind="Assign",Wires=new[]{0,1,2,3,4,5,6,7},ClassicalValue=Constant(8,"255")},
   new ClassicalCircuit.Step{Kind="Assign",Wires=new[]{8},ClassicalValue=new ClassicalCircuit.ExpressionNode{Kind="IntegerCompare",Operator="Less",
    Left=new ClassicalCircuit.ExpressionNode{Kind="IntegerRead",Signedness="Signed",Width=8,Bits=new[]{0,1,2,3,4,5,6,7}},
    Right=new ClassicalCircuit.ExpressionNode{Kind="IntegerConstant",Signedness="Signed",Width=0,Value="0"}}}}};
 }
 static void ImportedCanonicalChecks() {
  // Run first: serializer caches differ before any DTO has been constructed.
  var imported=ClassicalCircuit.Load(@"{""Version"":4,""Qubits"":0,""Registers"":[{""Name"":""c"",""Size"":8},{""Name"":""r"",""Size"":1}],""OutputBits"":[8],""Steps"":[{""Kind"":""Assign"",""Wires"":[0,1,2,3,4,5,6,7],""ClassicalValue"":{""Kind"":""Constant"",""Width"":8,""Value"":""255""}},{""Kind"":""ExpressionBranch"",""ClassicalValue"":{""Kind"":""IntegerCompare"",""Operator"":""Less"",""Left"":{""Kind"":""IntegerRead"",""Signedness"":""Signed"",""Width"":8,""Bits"":[0,1,2,3,4,5,6,7]},""Right"":{""Kind"":""IntegerConstant"",""Signedness"":""Signed"",""Width"":0,""Value"":""0""}},""WhenTrue"":[{""Kind"":""Assign"",""Wires"":[8],""ClassicalValue"":{""Kind"":""Constant"",""Width"":1,""Value"":""1""}}],""WhenFalse"":[]}]}");
  var canonical=imported.Serialize();
  for(int round=0;round<3;round++) {
   var reopened=ClassicalCircuit.Load(canonical);Check(reopened.Serialize()==canonical);
   Check(Convert.ToBase64String(NumericalSampling.RequestExact(imported.Qubits,imported.ClassicalBits,imported.OutputBits,imported.SamplingGates()))==Convert.ToBase64String(NumericalSampling.RequestExact(reopened.Qubits,reopened.ClassicalBits,reopened.OutputBits,reopened.SamplingGates())));
  }
 }
 static void TypedChecks() {
  var original=ClassicalCircuit.From(TypedProgram());var restored=ClassicalCircuit.Load(original.Serialize());
  Check(restored.Serialize()==original.Serialize());Check(restored.Snapshot().Version==4);
  Check(restored.Snapshot().Steps[1].ClassicalValue.Left.Signedness=="Signed");
  Check(restored.SamplingGates()[1].ClassicalExpression.IntegerRight.Type.DeclaredWidth==0);
  Check(Convert.ToBase64String(NumericalSampling.RequestExact(0,9,new[]{8},original.SamplingGates()))==Convert.ToBase64String(NumericalSampling.RequestExact(0,9,new[]{8},restored.SamplingGates())));
  Check(Convert.ToBase64String(NumericalSampling.RequestClassical(0,9,10000,1731,new[]{8},original.SamplingGates()))==Convert.ToBase64String(NumericalSampling.RequestClassical(0,9,10000,1731,new[]{8},restored.SamplingGates())));
  var copy=restored.Snapshot();copy.Steps[1].ClassicalValue.Left.Bits[0]=63;Check(restored.Snapshot().Steps[1].ClassicalValue.Left.Bits[0]==0);
  foreach(int width in new[]{0,64}) {var d=TypedProgram();d.Steps[1].ClassicalValue.Right.Width=width;var c=ClassicalCircuit.Load(ClassicalCircuit.From(d).Serialize());Check(c.SamplingGates()[1].ClassicalExpression.IntegerRight.Type.DeclaredWidth==width);}
  foreach(var mutate in new Action<ClassicalCircuit.Document>[] {
   d=>d.Version=3,d=>d.Version=2,d=>d.Steps[1].ClassicalValue.Operator="And",d=>d.Steps[1].ClassicalValue.Operator="7",
   d=>d.Steps[1].ClassicalValue.Left.Signedness=null,d=>d.Steps[1].ClassicalValue.Left.Signedness="0",d=>d.Steps[1].ClassicalValue.Left.Signedness="signed",
   d=>d.Steps[1].ClassicalValue.Left.Width=null,d=>d.Steps[1].ClassicalValue.Left.Width=65,d=>d.Steps[1].ClassicalValue.Left.Width=-1,
   d=>d.Steps[1].ClassicalValue.Left.Bits[7]=10,d=>d.Steps[1].ClassicalValue.Left.Bits=new[]{0},d=>d.Steps[1].ClassicalValue.Left.Kind="Read",
   d=>d.Steps[1].ClassicalValue.Right.Kind="Constant",d=>d.Steps[1].ClassicalValue.Right.Value="-1",
   d=>d.Steps[1].ClassicalValue.Signedness="Signed",d=>d.Steps[1].ClassicalValue.Left.Value="0"}) {
   var bad=TypedProgram();mutate(bad);Reject(()=>ClassicalCircuit.From(bad));Check(original.Serialize()==restored.Serialize());
  }
  Reject(()=>ClassicalCircuit.Load(original.Serialize().Replace("\"Signedness\":\"Signed\"","\"Signedness\":0")));
  Reject(()=>ClassicalCircuit.Load(original.Serialize().Replace("\"Width\":8","\"Width\":8.5")));
  var arithmetic=TypedProgram();arithmetic.Steps[1].ClassicalValue.Left=new ClassicalCircuit.ExpressionNode{Kind="IntegerBinary",Operator="Divide",Left=new ClassicalCircuit.ExpressionNode{Kind="IntegerConstant",Signedness="Signed",Width=0,Value="6"},Right=arithmetic.Steps[1].ClassicalValue.Left};
  var stored=ClassicalCircuit.From(arithmetic);Check(ClassicalCircuit.Load(stored.Serialize()).SamplingGates()[1].ClassicalExpression.IntegerLeft.Operation==ClassicalIntegerExpression.Operator.Divide);
  var limit=TypedProgram();var leaf=limit.Steps[1].ClassicalValue.Right;
  var deepInteger=leaf;for(int i=0;i<30;i++)deepInteger=new ClassicalCircuit.ExpressionNode{Kind="IntegerCast",Signedness="Signed",Width=0,Left=deepInteger};
  limit.Steps[1].ClassicalValue.Left=deepInteger;Check(ClassicalCircuit.From(limit).Snapshot().Version==4);
  limit.Steps[1].ClassicalValue.Left=new ClassicalCircuit.ExpressionNode{Kind="IntegerCast",Signedness="Signed",Width=0,Left=deepInteger};Reject(()=>ClassicalCircuit.From(limit));
  var half=leaf;for(int i=0;i<7;i++)half=new ClassicalCircuit.ExpressionNode{Kind="IntegerBinary",Operator="Add",Left=half,Right=half};
  limit=TypedProgram();limit.Steps[1].ClassicalValue=new ClassicalCircuit.ExpressionNode{Kind="Complement",Left=new ClassicalCircuit.ExpressionNode{Kind="IntegerCompare",Operator="Equal",Left=half,Right=half}};
  Check(ClassicalCircuit.From(limit).Snapshot().Version==4);
  limit.Steps[1].ClassicalValue=new ClassicalCircuit.ExpressionNode{Kind="Complement",Left=limit.Steps[1].ClassicalValue};Reject(()=>ClassicalCircuit.From(limit));
  var cast=TypedProgram();cast.Steps[1].ClassicalValue.Left=new ClassicalCircuit.ExpressionNode{Kind="IntegerCast",Signedness="Unsigned",Width=8,Left=cast.Steps[1].ClassicalValue.Left};
  Check(ClassicalCircuit.From(cast).SamplingGates()[1].ClassicalExpression.IntegerLeft.Type.Signedness==ClassicalIntegerType.Sign.Unsigned);
  for(int version=2;version<=3;version++){var legacy=version==2 ? Program() : Expressions();Check(!ClassicalCircuit.From(legacy).Serialize().Contains("Signedness"));}
 }
 static ClassicalCircuit.Document BitCastProgram() {
  var result=TypedProgram();result.Steps[1].Wires=new[]{0,1,2,3,4,5,6,7};
  result.Steps[1].ClassicalValue=new ClassicalCircuit.ExpressionNode{Kind="IntegerBits",Left=result.Steps[1].ClassicalValue.Left};
  return result;
 }
 static void BitCastChecks() {
  var original=ClassicalCircuit.From(BitCastProgram());var restored=ClassicalCircuit.Load(original.Serialize());
  Check(original.Serialize()==restored.Serialize());Check(restored.SamplingGates()[1].ClassicalExpression.Width==8);
  Check(restored.SamplingGates()[1].ClassicalExpression.Kind==ClassicalExpression.NodeKind.IntegerBits);
  Check(restored.SamplingGates()[1].ClassicalExpression.UsesTypedProtocol);
  Check(Convert.ToBase64String(NumericalSampling.RequestExact(0,9,new[]{8},original.SamplingGates()))==Convert.ToBase64String(NumericalSampling.RequestExact(0,9,new[]{8},restored.SamplingGates())));
  Check(Convert.ToBase64String(NumericalSampling.RequestClassical(0,9,10000,1731,new[]{8},original.SamplingGates()))==Convert.ToBase64String(NumericalSampling.RequestClassical(0,9,10000,1731,new[]{8},restored.SamplingGates())));
  var snapshot=restored.Snapshot();snapshot.Steps[1].ClassicalValue.Left.Bits[0]=63;Check(restored.Snapshot().Steps[1].ClassicalValue.Left.Bits[0]==0);
  foreach(var mutate in new Action<ClassicalCircuit.Document>[] {
   d=>d.Version=3,d=>d.Version=2,d=>d.Steps[1].ClassicalValue.Left=null,
   d=>d.Steps[1].ClassicalValue.Width=8,d=>d.Steps[1].ClassicalValue.Operator="Add",
   d=>d.Steps[1].ClassicalValue.Right=Constant(1,"0"),d=>d.Steps[1].ClassicalValue.Signedness="Signed",
   d=>d.Steps[1].ClassicalValue.Left=Constant(8,"255"),d=>d.Steps[1].ClassicalValue.Left.Width=0,
   d=>d.Steps[1].ClassicalValue.Left.Bits[0]=9,d=>d.Steps[1].Wires=new[]{0},
   d=>d.Steps[1].ClassicalValue.Left=new ClassicalCircuit.ExpressionNode{Kind="IntegerConstant",Width=0,Signedness="Signed",Value="1"}}) {
   var bad=BitCastProgram();mutate(bad);Reject(()=>ClassicalCircuit.From(bad));Check(original.Serialize()==restored.Serialize());
  }
  var nested=BitCastProgram();nested.Steps[1].ClassicalValue=new ClassicalCircuit.ExpressionNode{Kind="Complement",Left=nested.Steps[1].ClassicalValue};
  Check(ClassicalCircuit.From(nested).SamplingGates()[1].ClassicalExpression.UsesTypedProtocol);
  var limit=BitCastProgram();var child=limit.Steps[1].ClassicalValue.Left;
  for(int k=1;k<31;k++)child=new ClassicalCircuit.ExpressionNode{Kind="IntegerCast",Signedness="Signed",Width=8,Left=child};
  limit.Steps[1].ClassicalValue.Left=child;Check(ClassicalCircuit.From(limit).Snapshot().Version==4);
  limit.Steps[1].ClassicalValue.Left=new ClassicalCircuit.ExpressionNode{Kind="IntegerCast",Signedness="Signed",Width=8,Left=child};Reject(()=>ClassicalCircuit.From(limit));
 }
 static void Main(string[] args) {
  if(args.Length>0 && args[0]=="--legacy-cold") {
   // The first load in this process must exercise legacy expression metadata.
   var source=@"{""Version"":3,""Qubits"":0,""Registers"":[{""Name"":""r"",""Size"":1}],""OutputBits"":[0],""Steps"":[{""Kind"":""Assign"",""Wires"":[0],""ClassicalValue"":{""Kind"":""Binary"",""Operator"":""NotEqual"",""Left"":{""Kind"":""Constant"",""Width"":2,""Value"":""2""},""Right"":{""Kind"":""Constant"",""Width"":2,""Value"":""0""}}}]}";
   var initial=ClassicalCircuit.Load(source);var saved=initial.Serialize();
   for(int n=0;n<3;n++) {
    var opened=ClassicalCircuit.Load(saved);Check(opened.Serialize()==saved);
    Check(Convert.ToBase64String(NumericalSampling.RequestExact(0,1,new[]{0},initial.SamplingGates()))==Convert.ToBase64String(NumericalSampling.RequestExact(0,1,new[]{0},opened.SamplingGates())));
   }
   Check(!saved.Contains("Signedness") && !saved.Contains("LoopConditionBudget"));
   Console.WriteLine("PASS: "+checks+" cold legacy circuit checks.");return;
  }
  Rotations(args.Length>0 ? args[0] : null);
  ParameterGates();
  ImportedCanonicalChecks();
  var draft=Program();var circuit=ClassicalCircuit.From(draft);var text=circuit.Serialize();
  Check(circuit.ClassicalBits==64 && circuit.Qubits==1);
  Check(ClassicalCircuit.Load(text).Serialize()==text);
  Check(circuit.Snapshot().Registers[1].Name=="record");
  Check(circuit.SamplingGates()[1].Mask==1UL<<63);
  Check(circuit.SamplingGates()[1].WhenTrue[0].ClassicalBit==0);
  draft.Registers[0].Name="changed";draft.Steps[0].Wires[0]=7;
  var snapshot=circuit.Snapshot();snapshot.Steps[1].WhenTrue[0].ClassicalBit=8;
  var gates=circuit.SamplingGates();gates[0].Wires[0]=8;gates[1].WhenTrue.Clear();
  var output=circuit.OutputBits;output[0]=9;
  Check(circuit.Serialize()==text && circuit.SamplingGates()[0].Wires[0]==0 && circuit.SamplingGates()[1].WhenTrue.Count==1 && circuit.OutputBits[0]==63);
  foreach(var mutate in new Action<ClassicalCircuit.Document>[] {
   d=>d.Version=1,d=>d.Qubits=26,d=>d.Registers[1].Name="flag",d=>d.Registers[0].Name=" flag",
   d=>d.Registers[0].Size=0,d=>d.Registers[1].Size=64,d=>d.OutputBits=new[]{64},
   d=>d.Steps[0].ClassicalBit=null,d=>d.Steps[0].ClassicalBit=64,d=>d.Steps[0].Expression="X",
   d=>d.Steps[0].Kind="0",d=>d.Steps[0].Mask="0",d=>d.Steps[1].Value="18446744073709551616",
   d=>d.Steps[1].Mask="-1",d=>d.Steps[1].WhenFalse=null,d=>d.Steps[1].WhenFalse=new[]{Measure(64)}
  }) {var bad=Program();mutate(bad);Reject(()=>ClassicalCircuit.From(bad));}
  Reject(()=>ClassicalCircuit.Load(text.Replace("\"Version\":2","\"Version\":\"2\"")));
  Reject(()=>ClassicalCircuit.Load(text.Replace("\"Qubits\":1","\"Qubits\":1.0")));
  Reject(()=>ClassicalCircuit.Load(text.Replace("\"Name\":\"flag\"","\"Name\":\"flag\",\"Unknown\":0")));
  Reject(()=>ClassicalCircuit.Load(text.Replace("\"Kind\":\"Measure\"","\"Kind\":\"Measure\",\"Unknown\":0")));
  var many=Program();many.Steps=new ClassicalCircuit.Step[512];for(int i=0;i<512;i++)many.Steps[i]=Measure(0);
  Check(ClassicalCircuit.From(many).SamplingGates().Count==512);
  many.Steps=new ClassicalCircuit.Step[513];for(int i=0;i<513;i++)many.Steps[i]=Measure(0);
  Reject(()=>ClassicalCircuit.From(many));
  var empty=Program();empty.Registers=new ClassicalCircuit.Register[0];empty.OutputBits=new int[0];empty.Steps=new ClassicalCircuit.Step[0];
  Check(ClassicalCircuit.From(empty).ClassicalBits==0);
  var nested=Program();var body=new[]{Measure(0)};
  for(int depth=0;depth<32;depth++)body=new[]{new ClassicalCircuit.Step {Kind="Branch",Mask="1",Value="1",WhenTrue=body,WhenFalse=new ClassicalCircuit.Step[0]}};
  nested.Steps=body;Check(ClassicalCircuit.From(nested).SamplingGates().Count==1);
  nested.Steps=new[]{new ClassicalCircuit.Step {Kind="Branch",Mask="1",Value="1",WhenTrue=body,WhenFalse=new ClassicalCircuit.Step[0]}};
  Reject(()=>ClassicalCircuit.From(nested));
  Reject(()=>ClassicalCircuit.Load(new string(' ',262145)));
  var expressionDraft=Expressions();var expressionCircuit=ClassicalCircuit.From(expressionDraft);string expressionText=expressionCircuit.Serialize();
  Check(ClassicalCircuit.Load(expressionText).Serialize()==expressionText);
  var wide=Expressions();var allBits=new int[64];for(int bit=0;bit<64;bit++)allBits[bit]=bit;
  wide.Steps=new[]{new ClassicalCircuit.Step {Kind="Assign",Wires=allBits,ClassicalValue=Constant(64,"18446744073709551615")}};
  Check(ClassicalCircuit.Load(ClassicalCircuit.From(wide).Serialize()).SamplingGates()[0].ClassicalExpression.Value==UInt64.MaxValue);
  Check(Encoding.UTF8.GetString(NumericalSampling.RequestExact(1,64,new[]{63,0},expressionCircuit.SamplingGates())).StartsWith("QEXACT2\n"));
  Check(Encoding.UTF8.GetString(NumericalSampling.RequestClassical(1,64,1,0,new[]{63,0},expressionCircuit.SamplingGates())).StartsWith("QSAMPLE3\n"));
  expressionDraft.Steps[0].ClassicalValue.Value="0";expressionCircuit.Snapshot().Steps[1].ClassicalValue.Bits[0]=0;
  Check(expressionCircuit.Snapshot().Steps[0].ClassicalValue.Value=="1" && expressionCircuit.SamplingGates()[1].ClassicalExpression.Indices[0]==63);
  foreach(var mutate in new Action<ClassicalCircuit.Document>[] {
   d=>d.Version=2,d=>d.Version=5,d=>d.Steps[0].ClassicalValue=null,
   d=>d.Steps[0].ClassicalValue.Width=null,d=>d.Steps[0].ClassicalValue.Width=0,d=>d.Steps[0].ClassicalValue.Value="2",
   d=>d.Steps[0].ClassicalValue.Value="18446744073709551616",d=>d.Steps[0].ClassicalValue.Value="-1",
   d=>d.Steps[0].ClassicalValue.Value=" 1",d=>d.Steps[0].ClassicalValue.Bits=new[]{0},
   d=>d.Steps[0].Kind="Reset",d=>d.Steps[0].Mask="0",d=>d.Steps[0].Expression="X",
   d=>d.Steps[1].ClassicalValue.Bits=new[]{64},d=>d.Steps[1].ClassicalValue.Bits=new[]{0,1},
   d=>d.Steps[1].ClassicalValue.Kind="Unknown",d=>d.Steps[1].ClassicalValue.Left=Constant(1,"0")
  }) {var bad=Expressions();mutate(bad);Reject(()=>ClassicalCircuit.From(bad));}
  Reject(()=>ClassicalCircuit.Load(expressionText.Replace("\"Width\":1","\"Width\":1.0")));
  Reject(()=>ClassicalCircuit.Load(expressionText.Replace("\"Value\":\"1\"","\"Value\":1")));
  Reject(()=>ClassicalCircuit.Load(expressionText.Replace("\"Kind\":\"Read\"","\"Kind\":\"Read\",\"Unknown\":null")));
  var expr=Constant(1,"0");for(int k=1;k<32;k++)expr=new ClassicalCircuit.ExpressionNode {Kind="Complement",Left=expr};
  var bounded=Expressions();bounded.Steps[0].ClassicalValue=expr;Check(ClassicalCircuit.From(bounded).SamplingGates()[0].ClassicalExpression.Width==1);
  bounded.Steps[0].ClassicalValue=new ClassicalCircuit.ExpressionNode {Kind="Complement",Left=expr};Reject(()=>ClassicalCircuit.From(bounded));
  expr=Constant(1,"1");for(int k=0;k<8;k++)expr=new ClassicalCircuit.ExpressionNode {Kind="Binary",Operator="Xor",Left=expr,Right=expr};
  bounded.Steps[0].ClassicalValue=new ClassicalCircuit.ExpressionNode {Kind="Complement",Left=expr};Check(ClassicalCircuit.From(bounded).SamplingGates()[0].ClassicalExpression.Width==1);
  bounded.Steps[0].ClassicalValue=new ClassicalCircuit.ExpressionNode {Kind="Binary",Operator="Xor",Left=expr,Right=Constant(1,"1")};Reject(()=>ClassicalCircuit.From(bounded));
  foreach(string op in new[]{"0","XOR","Unknown"}) {bounded.Steps[0].ClassicalValue=new ClassicalCircuit.ExpressionNode {Kind="Binary",Operator=op,Left=Constant(1,"0"),Right=Constant(1,"1")};Reject(()=>ClassicalCircuit.From(bounded));}
  foreach(string direction in new[]{"Left","Right"})foreach(string signedness in new[]{"Unsigned","Signed"}) {
   var rotated=Expressions();rotated.Steps=new[]{new ClassicalCircuit.Step {Kind="Assign",Wires=allBits,ClassicalValue=new ClassicalCircuit.ExpressionNode {Kind="Rotate",RotationDirection=direction,DistanceInterpretation=signedness,Left=Constant(64,"1"),Right=Constant(8,"255")}}};
   var rotation=ClassicalCircuit.From(rotated);var loaded=ClassicalCircuit.Load(rotation.Serialize());
   Check(loaded.Serialize()==rotation.Serialize());
   var node=loaded.SamplingGates()[0].ClassicalExpression;
   Check(node.Width==64 && node.RotationDirection.ToString()==direction && node.DistanceInterpretation.ToString()==signedness && node.Right.Width==8);
   foreach(var mutate in new Action<ClassicalCircuit.ExpressionNode>[] {n=>n.RotationDirection=null,n=>n.RotationDirection="0",n=>n.RotationDirection="left",n=>n.DistanceInterpretation="Unknown",n=>n.DistanceInterpretation=null,n=>n.Left=null,n=>n.Right=null,n=>n.Width=64,n=>n.Operator="And"}) {
    var bad=loaded.Snapshot();mutate(bad.Steps[0].ClassicalValue);Reject(()=>ClassicalCircuit.From(bad));
   }
  }
  wide.Steps[0].ClassicalValue=new ClassicalCircuit.ExpressionNode {Kind="PopulationCount",Left=Constant(64,"18446744073709551615")};
  var counted=ClassicalCircuit.From(wide);Check(ClassicalCircuit.Load(counted.Serialize()).SamplingGates()[0].ClassicalExpression.Width==64);
  wide.Steps[0].ClassicalValue.Right=Constant(1,"0");Reject(()=>ClassicalCircuit.From(wide));wide.Steps[0].ClassicalValue.Right=null;
  wide.Steps[0].ClassicalValue.RotationDirection="Left";Reject(()=>ClassicalCircuit.From(wide));
  Numerics(args.Length==0 ? null : args[0]);
  TypedChecks();
  BitCastChecks();
  Variables(args.Length==0 ? null : args[0]);
  Loops(args.Length==0 ? null : args[0]);
  Transfers(args.Length==0 ? null : args[0]);
  Termination(args.Length==0 ? null : args[0]);
  Ranges(args.Length==0 ? null : args[0]);
  Console.WriteLine("PASS: "+checks+" classical circuit storage checks.");
 }
}
