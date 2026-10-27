// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.IO;
using G=NumericalSampling.Gate;
using O=NumericalSampling.Operation;

// Flattened subroutine activations can reuse a slot in disjoint lexical
// lifetimes. Recover only paired, non-crossing intervals containing every
// reference to that slot. Work on a snapshot so export never edits the circuit.
static class ClassicalQasmLifetimes {
 sealed class Interval {
  public ClassicalCircuit.Step[] Body;
  public int Start,End;
 }
 static void Expression(ClassicalCircuit.ExpressionNode node,Action<ClassicalCircuit.ExpressionNode> visit,Action<ClassicalCircuit.RealNode> numeric) {
  if(node==null)return;
  visit(node);Expression(node.Left,visit,numeric);Expression(node.Right,visit,numeric);Real(node.RealLeft,visit,numeric);Real(node.RealRight,visit,numeric);
 }
 static void Real(ClassicalCircuit.RealNode node,Action<ClassicalCircuit.ExpressionNode> visit,Action<ClassicalCircuit.RealNode> numeric) {
  if(node==null)return;
  if(numeric!=null)numeric(node);Expression(node.IntegerValue,visit,numeric);Expression(node.BitValue,visit,numeric);Real(node.Left,visit,numeric);Real(node.Right,visit,numeric);
 }
 static void Visit(ClassicalCircuit.Step step,Action<ClassicalCircuit.Step> instruction,Action<ClassicalCircuit.ExpressionNode> expression,Action<ClassicalCircuit.RealNode> numeric=null,int depth=0) {
  // Recovery adds blocks before the final model validation. Bound each walk
  // too, so intermediate trees cannot exhaust the stack while being rebuilt.
  if(depth>=32)throw new InvalidDataException("OpenQASM export local lifetimes exceed 32 levels of nesting.");
  instruction(step);Expression(step.ClassicalValue,expression,numeric);Expression(step.IntegerValue,expression,numeric);Real(step.Angle,expression,numeric);Real(step.NumericValue,expression,numeric);
  if(step.ParameterGate!=null){foreach(var angle in step.ParameterGate.Parameters)Real(angle,expression,numeric);Expression(step.ParameterGate.Power,expression,numeric);}
  if(step.Range!=null){Expression(step.Range.Start,expression,numeric);Expression(step.Range.Stop,expression,numeric);Expression(step.Range.Step,expression,numeric);}
  if(step.WhenTrue!=null)foreach(var child in step.WhenTrue)Visit(child,instruction,expression,numeric,depth+1);
  if(step.WhenFalse!=null)foreach(var child in step.WhenFalse)Visit(child,instruction,expression,numeric,depth+1);
 }
 static bool SlotOperation(ClassicalCircuit.Step step,bool numeric){return numeric ? step.Kind=="StoreNumeric" || step.Kind=="ClearNumeric" : step.Kind=="StoreInteger" || step.Kind=="ClearInteger" || step.Kind=="ForRange";}
 static int References(ClassicalCircuit.Step step,int slot,bool numeric) {
  int count=0;
  Visit(step,s=>{if(SlotOperation(s,numeric) && s.VariableSlot==slot)count++;},e=>{if(!numeric && e.Kind=="IntegerVariable" && e.Slot==slot)count++;},e=>{if(numeric && e.Kind=="Variable" && e.Slot==slot)count++;});
  return count;
 }
 static void Find(ClassicalCircuit.Step[] body,int slot,List<Interval> intervals,bool numeric) {
  if(body==null)return;
  for(int i=0;i<body.Length;i++) {
   if(body[i].Kind==(numeric ? "ClearNumeric" : "ClearInteger") && body[i].VariableSlot==slot) {
    int end=i+1;
    while(end<body.Length && !(body[end].Kind==(numeric ? "ClearNumeric" : "ClearInteger") && body[end].VariableSlot==slot))end++;
    if(end<body.Length){intervals.Add(new Interval{Body=body,Start=i,End=end});i=end;continue;}
   }
   Find(body[i].WhenTrue,slot,intervals,numeric);Find(body[i].WhenFalse,slot,intervals,numeric);
  }
 }
 static ClassicalCircuit.Step[] Wrap(ClassicalCircuit.Step[] body,Dictionary<ClassicalCircuit.Step,ClassicalCircuit.Step> starts,Dictionary<ClassicalCircuit.Step,int> lengths) {
  if(body==null)return null;
  var result=new List<ClassicalCircuit.Step>();
  for(int i=0;i<body.Length;i++) {
   ClassicalCircuit.Step wrapper;
   if(starts.TryGetValue(body[i],out wrapper)){result.Add(wrapper);i+=lengths[body[i]]-1;}
   else {
    body[i].WhenTrue=Wrap(body[i].WhenTrue,starts,lengths);
    body[i].WhenFalse=Wrap(body[i].WhenFalse,starts,lengths);result.Add(body[i]);
   }
  }
  return result.ToArray();
 }
 public static ClassicalCircuit Prepare(ClassicalCircuit circuit){return PrepareKind(PrepareKind(circuit,false),true);}
 static ClassicalCircuit PrepareKind(ClassicalCircuit circuit,bool numeric) {
  var document=circuit.Snapshot();
  var variables=new List<ClassicalCircuit.Variable>(document.Variables??new ClassicalCircuit.Variable[0]);
  var numericVariables=new List<ClassicalCircuit.NumericVariable>(document.NumericVariables??new ClassicalCircuit.NumericVariable[0]);
  int originalCount=numeric ? numericVariables.Count : variables.Count;if(originalCount==0)return circuit;
  bool changed=false;
  for(int slot=0;slot<originalCount;slot++) {
   int total=0;bool range=false;
   foreach(var step in document.Steps) {
    total+=References(step,slot,numeric);
    Visit(step,s=>{if(!numeric && s.Kind=="ForRange" && s.VariableSlot==slot)range=true;},e=>{});
   }
   if(range || total==0)continue;
   var intervals=new List<Interval>();Find(document.Steps,slot,intervals,numeric);
   int covered=0;
   foreach(var interval in intervals)for(int i=interval.Start;i<=interval.End;i++)covered+=References(interval.Body[i],slot,numeric);
   if(covered!=total || intervals.Count==0)continue;
   var starts=new Dictionary<ClassicalCircuit.Step,ClassicalCircuit.Step>();
   var lengths=new Dictionary<ClassicalCircuit.Step,int>();
   for(int index=0;index<intervals.Count;index++) {
    var interval=intervals[index];int target=slot;
    if(index>0) {
     if(variables.Count+numericVariables.Count>=4096)throw new InvalidDataException("OpenQASM export exceeds the 4096-variable limit while separating local lifetimes.");
     if(numeric){target=numericVariables.Count;var type=document.NumericVariables[slot];numericVariables.Add(new ClassicalCircuit.NumericVariable{Name="export_numeric_local_"+target,NumericKind=type.NumericKind,Width=type.Width});}
     else {target=variables.Count;var type=document.Variables[slot];variables.Add(new ClassicalCircuit.Variable{Name="export_local_"+target,Signedness=type.Signedness,Width=type.Width});}
    }
    var body=new ClassicalCircuit.Step[interval.End-interval.Start+1];
    Array.Copy(interval.Body,interval.Start,body,0,body.Length);
    if(target!=slot)foreach(var step in body)Visit(step,s=>{if(SlotOperation(s,numeric) && s.VariableSlot==slot)s.VariableSlot=target;},e=>{if(!numeric && e.Kind=="IntegerVariable" && e.Slot==slot)e.Slot=target;},e=>{if(numeric && e.Kind=="Variable" && e.Slot==slot)e.Slot=target;});
    starts.Add(body[0],new ClassicalCircuit.Step{Kind="Branch",Mask="0",Value="0",WhenTrue=body,WhenFalse=new ClassicalCircuit.Step[0]});
    lengths.Add(body[0],body.Length);
   }
   document.Steps=Wrap(document.Steps,starts,lengths);changed=true;
  }
  if(!changed)return circuit;
  document.Variables=variables.ToArray();if(numeric)document.NumericVariables=numericVariables.ToArray();
  return ClassicalCircuit.From(document);
 }
}

// Recover lexical lifetimes only when the validated instruction tree proves
// them. A clear in the middle of a live scope cannot be replaced by zero.
sealed class ClassicalQasmScopes {
 sealed class Scope {
  public Scope Parent,Loop;
  public IList<G> Body;
  public readonly List<int> Declarations=new List<int>();
 }
 sealed class Site {
  public Scope Scope;
  public int Index;
  public G Gate;
 }
 readonly Dictionary<IList<G>,Scope> scopes=new Dictionary<IList<G>,Scope>();
 readonly Dictionary<int,Scope> ranges=new Dictionary<int,Scope>();
 readonly List<Scope>[] uses;
 readonly List<Site>[] clears;
 readonly List<Site> transfers=new List<Site>();
 readonly Scope root;readonly bool numeric;
 static bool AnyClear(G gate){return gate.Kind==O.ClearInteger || gate.Kind==O.ClearNumeric;}
 bool OwnClear(G gate){return gate.Kind==(numeric ? O.ClearNumeric : O.ClearInteger);}
 static InvalidDataException Unsupported(int slot) {
  return new InvalidDataException("OpenQASM export cannot reconstruct integer lifetime for v"+slot+". Save the circuit document to preserve it.");
 }
 public ClassicalQasmScopes(IList<G> steps,int variables,bool numeric=false) {
  this.numeric=numeric;
  uses=new List<Scope>[variables];clears=new List<Site>[variables];
  for(int i=0;i<variables;i++){uses[i]=new List<Scope>();clears[i]=new List<Site>();}
  root=Scan(steps,null,false);
  for(int slot=0;slot<variables;slot++) {
   Scope owner;
   bool range=ranges.TryGetValue(slot,out owner);
   if(range) {
    foreach(var use in uses[slot])if(!Inside(use,owner))throw Unsupported(slot);
   } else if(clears[slot].Count==0)owner=root;
   else {
    owner=uses[slot].Count==0 ? clears[slot][0].Scope : uses[slot][0];
    foreach(var use in uses[slot])while(!Inside(use,owner))owner=owner.Parent;
    foreach(var clear in clears[slot])while(!Inside(clear.Scope,owner))owner=owner.Parent;
    // Normal completion and every loop transfer must end this lifetime.
    if(!TailClear(owner,slot))throw Unsupported(slot);
    foreach(var transfer in transfers)
     if(Inside(transfer.Scope,owner) && Exits(transfer,owner) && transfer.Gate.Kind!=O.End && !BeforeTransfer(transfer,slot))
      throw Unsupported(slot);
   }
   foreach(var clear in clears[slot]) {
    if(!Inside(clear.Scope,owner))throw Unsupported(slot);
    // The importer emits a clear at lexical entry as well as exit. A new
    // declaration supplies that undefined entry value before any instruction.
    bool entry=clear.Scope==owner;
    for(int i=0;i<clear.Index && entry;i++)entry=AnyClear(clear.Scope.Body[i]);
    if(entry)continue;
    int next=clear.Index+1;
    while(next<clear.Scope.Body.Count && AnyClear(clear.Scope.Body[next]))next++;
    if(next==clear.Scope.Body.Count) {
     if(clear.Scope!=owner)throw Unsupported(slot);
    } else if(next!=clear.Scope.Body.Count-1 || !Exits(new Site{Scope=clear.Scope,Index=next,Gate=clear.Scope.Body[next]},owner))
     throw Unsupported(slot);
   }
   if(!range)owner.Declarations.Add(slot);
  }
 }
 public IList<int> Declarations(IList<G> body){return scopes[body].Declarations;}
 static bool Inside(Scope scope,Scope owner) {
  for(;scope!=null;scope=scope.Parent)if(scope==owner)return true;
  return false;
 }
 static bool Exits(Site site,Scope owner) {
  if(site.Gate.Kind==O.End)return true;
  return (site.Gate.Kind==O.Break || site.Gate.Kind==O.Continue) && Inside(owner,site.Scope.Loop);
 }
 bool BeforeTransfer(Site site,int slot) {
  for(int i=site.Index-1;i>=0 && AnyClear(site.Scope.Body[i]);i--)
   if(OwnClear(site.Scope.Body[i]) && site.Scope.Body[i].VariableSlot==slot)return true;
  return false;
 }
 bool TailClear(Scope scope,int slot) {
  int i=scope.Body.Count-1;
  if(i>=0 && (scope.Body[i].Kind==O.End || scope.Body[i].Kind==O.Break || scope.Body[i].Kind==O.Continue))i--;
  for(;i>=0 && AnyClear(scope.Body[i]);i--)if(OwnClear(scope.Body[i]) && scope.Body[i].VariableSlot==slot)return true;
  return false;
 }
 void Integer(ClassicalIntegerExpression expression,Scope scope) {
  if(expression==null)return;
  if(!numeric && expression.Kind==ClassicalIntegerExpression.NodeKind.Variable)uses[expression.Slot].Add(scope);
  Integer(expression.Left,scope);Integer(expression.Right,scope);Bits(expression.BitOperand,scope);Real(expression.NumericLeft,scope);Real(expression.NumericRight,scope);
 }
 void Bits(ClassicalExpression expression,Scope scope) {
  if(expression==null)return;
  Bits(expression.Left,scope);Bits(expression.Right,scope);
  Integer(expression.IntegerLeft,scope);Integer(expression.IntegerRight,scope);
 }
 void Real(ClassicalRealExpression expression,Scope scope) {
  if(expression==null)return;
  if(numeric && expression.Kind==ClassicalRealExpression.NodeKind.Variable)uses[expression.Slot].Add(scope);
  Integer(expression.Integer,scope);Bits(expression.BitOperand,scope);Real(expression.Left,scope);Real(expression.Right,scope);
 }
 Scope Scan(IList<G> body,Scope parent,bool loop) {
  var scope=new Scope{Body=body,Parent=parent};scope.Loop=loop ? scope : parent==null ? null : parent.Loop;
  scopes.Add(body,scope);
  for(int i=0;i<body.Count;i++) {
   var gate=body[i];var site=new Site{Scope=scope,Index=i,Gate=gate};
   Bits(gate.ClassicalExpression,scope);Integer(gate.IntegerExpression,scope);Real(gate.Angle,scope);Real(gate.NumericExpression,scope);
   if(gate.ParameterGate!=null){foreach(var parameter in gate.ParameterGate.Parameters)Real(parameter,scope);Integer(gate.ParameterGate.Power,scope);}
   if(gate.Kind==(numeric ? O.StoreNumeric : O.StoreInteger))uses[gate.VariableSlot.Value].Add(scope);
   if(OwnClear(gate))clears[gate.VariableSlot.Value].Add(site);
   if(gate.Kind==O.Break || gate.Kind==O.Continue || gate.Kind==O.End)transfers.Add(site);
   if(gate.Kind==O.ForRange) {
    Integer(gate.Range.Start,scope);Integer(gate.Range.Stop,scope);Integer(gate.Range.Step,scope);
    var child=Scan(gate.WhenTrue,scope,true);int slot=gate.VariableSlot.Value;
    if(!numeric){if(ranges.ContainsKey(slot))throw Unsupported(slot);ranges.Add(slot,child);}
   } else if(gate.Kind==O.While)Scan(gate.WhenTrue,scope,true);
   else if(gate.Kind==O.Branch || gate.Kind==O.ExpressionBranch) {
    Scan(gate.WhenTrue,scope,false);
    if(gate.WhenFalse!=null)Scan(gate.WhenFalse,scope,false);
   }
  }
  return scope;
 }
}
