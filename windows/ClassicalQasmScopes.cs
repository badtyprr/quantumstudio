// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.IO;
using G=NumericalSampling.Gate;
using O=NumericalSampling.Operation;

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
 readonly Scope root;
 static InvalidDataException Unsupported(int slot) {
  return new InvalidDataException("OpenQASM export cannot reconstruct integer lifetime for v"+slot+". Save the circuit document to preserve it.");
 }
 public ClassicalQasmScopes(IList<G> steps,int variables) {
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
    for(int i=0;i<clear.Index && entry;i++)entry=clear.Scope.Body[i].Kind==O.ClearInteger;
    if(entry)continue;
    int next=clear.Index+1;
    while(next<clear.Scope.Body.Count && clear.Scope.Body[next].Kind==O.ClearInteger)next++;
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
 static bool BeforeTransfer(Site site,int slot) {
  for(int i=site.Index-1;i>=0 && site.Scope.Body[i].Kind==O.ClearInteger;i--)
   if(site.Scope.Body[i].VariableSlot==slot)return true;
  return false;
 }
 static bool TailClear(Scope scope,int slot) {
  int i=scope.Body.Count-1;
  if(i>=0 && (scope.Body[i].Kind==O.End || scope.Body[i].Kind==O.Break || scope.Body[i].Kind==O.Continue))i--;
  for(;i>=0 && scope.Body[i].Kind==O.ClearInteger;i--)if(scope.Body[i].VariableSlot==slot)return true;
  return false;
 }
 void Integer(ClassicalIntegerExpression expression,Scope scope) {
  if(expression==null)return;
  if(expression.Kind==ClassicalIntegerExpression.NodeKind.Variable)uses[expression.Slot].Add(scope);
  Integer(expression.Left,scope);Integer(expression.Right,scope);Bits(expression.BitOperand,scope);
 }
 void Bits(ClassicalExpression expression,Scope scope) {
  if(expression==null)return;
  Bits(expression.Left,scope);Bits(expression.Right,scope);
  Integer(expression.IntegerLeft,scope);Integer(expression.IntegerRight,scope);
 }
 void Real(ClassicalRealExpression expression,Scope scope) {
  if(expression==null)return;
  Integer(expression.Integer,scope);Real(expression.Left,scope);Real(expression.Right,scope);
 }
 Scope Scan(IList<G> body,Scope parent,bool loop) {
  var scope=new Scope{Body=body,Parent=parent};scope.Loop=loop ? scope : parent==null ? null : parent.Loop;
  scopes.Add(body,scope);
  for(int i=0;i<body.Count;i++) {
   var gate=body[i];var site=new Site{Scope=scope,Index=i,Gate=gate};
   Bits(gate.ClassicalExpression,scope);Integer(gate.IntegerExpression,scope);Real(gate.Angle,scope);
   if(gate.Kind==O.StoreInteger)uses[gate.VariableSlot.Value].Add(scope);
   if(gate.Kind==O.ClearInteger)clears[gate.VariableSlot.Value].Add(site);
   if(gate.Kind==O.Break || gate.Kind==O.Continue || gate.Kind==O.End)transfers.Add(site);
   if(gate.Kind==O.ForRange) {
    Integer(gate.Range.Start,scope);Integer(gate.Range.Stop,scope);Integer(gate.Range.Step,scope);
    var child=Scan(gate.WhenTrue,scope,true);int slot=gate.VariableSlot.Value;
    if(ranges.ContainsKey(slot))throw Unsupported(slot);
    ranges.Add(slot,child);
   } else if(gate.Kind==O.While)Scan(gate.WhenTrue,scope,true);
   else if(gate.Kind==O.Branch || gate.Kind==O.ExpressionBranch) {
    Scan(gate.WhenTrue,scope,false);
    if(gate.WhenFalse!=null)Scan(gate.WhenFalse,scope,false);
   }
  }
  return scope;
 }
}
