// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;

static class NumericalSampling {
 public enum Operation { Gate, Measure, Reset, Conditional, Channel, Readout, Branch, Assign, ExpressionBranch, StoreInteger, ClearInteger, While, Break, Continue, End, ForRange, Rotation, ParameterGate, StoreNumeric, ClearNumeric, CheckArrayReferences=23 }
 public enum RotationAxis { X=0, Y=1, Z=2 }
 public enum ParameterGateKind { X, Y, Z, Phase, GlobalPhase, U3, PublishedU }
 public sealed class ParameterizedGate {
  public ParameterGateKind Kind {get;private set;}
  public int Controls {get;private set;}public ulong ControlState {get;private set;}
  public IList<ClassicalRealExpression> Parameters {get;private set;}
  public ClassicalIntegerExpression Power {get;private set;}
  public int TargetCount {get{return Kind==ParameterGateKind.GlobalPhase ? 0 : 1;}}
  public int WireCount {get{return Controls+TargetCount;}}
  public ParameterizedGate(ParameterGateKind kind,IList<ClassicalRealExpression> parameters,int controls,ulong state,ClassicalIntegerExpression power) {
   if(!Enum.IsDefined(typeof(ParameterGateKind),kind))throw new ArgumentException("Unknown runtime gate.");
   Kind=kind;Controls=controls;ControlState=state;Power=power;
   if(controls<0 || controls>3-TargetCount || state>=(1UL<<controls))throw new ArgumentException("Runtime gate controls exceed three wires or their state.");
   int count=kind==ParameterGateKind.U3 || kind==ParameterGateKind.PublishedU ? 3 : 1;
   if(parameters==null || parameters.Count!=count || power==null)throw new ArgumentException("Incorrect runtime gate parameters or power.");
   var copy=new ClassicalRealExpression[count];
   for(int i=0;i<count;i++){if(parameters[i]==null)throw new ArgumentException("Missing runtime gate parameter.");copy[i]=parameters[i];}
   Parameters=Array.AsReadOnly(copy);
  }
  internal void Validate(int bits,IList<ClassicalIntegerType> variables) {
   foreach(var parameter in Parameters)parameter.Validate(bits,variables);Power.Validate(bits,variables);
  }
  internal void WriteNode(Action<ulong> number) {
   number((ulong)Kind);number((ulong)Controls);number(ControlState);number((ulong)Parameters.Count);
   foreach(var parameter in Parameters)parameter.WriteNode(number);Power.WriteNode(number);
  }
 }
 public sealed class IntegerRange {
  public readonly ClassicalIntegerExpression Start,Stop,Step;
  public IntegerRange(ClassicalIntegerExpression start,ClassicalIntegerExpression stop,ClassicalIntegerExpression step) {
   if(start==null || stop==null || step==null)throw new ArgumentException("A range requires start, stop and step expressions.");
   Start=start;Stop=stop;Step=step;
  }
  internal void Write(Action<ulong> number,int bits,IList<ClassicalIntegerType> variables) {
   foreach(var expression in new[]{Start,Stop,Step}) {expression.Validate(bits,variables);expression.WriteNode(number);}
  }
 }
 public sealed class WireTarget {
  public readonly int[] Candidates;public readonly ClassicalIntegerExpression Index;
  public WireTarget(int[] candidates,ClassicalIntegerExpression index) {
   if(candidates==null || candidates.Length<1 || candidates.Length>25 || index==null)throw new ArgumentException("A wire target requires 1–25 candidates and an integer index.");
   Candidates=(int[])candidates.Clone();Index=index;
  }
 }
 public sealed class WireSelection {
  public readonly IList<WireTarget> Targets;public readonly string Source;
  public WireSelection(IList<WireTarget> targets,string source) {
   if(targets==null || targets.Count<1 || targets.Count>3)throw new ArgumentException("A dynamic operation requires 1–3 wire targets.");
   if(String.IsNullOrWhiteSpace(source) || Encoding.UTF8.GetByteCount(source)>512 || source.IndexOf('\0')>=0)throw new ArgumentException("Wire source context must fit 512 UTF-8 bytes.");
   var copy=new WireTarget[targets.Count];for(int k=0;k<copy.Length;k++){if(targets[k]==null)throw new ArgumentException("Missing wire target.");copy[k]=new WireTarget(targets[k].Candidates,targets[k].Index);}
   Targets=Array.AsReadOnly(copy);Source=source;
  }
  internal void Write(Action<ulong> number,StringBuilder text,int qubits,int bits,IList<ClassicalIntegerType> variables) {
   number((ulong)Encoding.UTF8.GetByteCount(Source));text.Append(Source);number((ulong)Targets.Count);
   foreach(var target in Targets) {
    number((ulong)target.Candidates.Length);
    foreach(int wire in target.Candidates){if(wire<0 || wire>=qubits)throw new ArgumentException("Wire candidate is outside the quantum register.");number((ulong)wire);}
    target.Index.Validate(bits,variables);target.Index.WriteNode(number);
   }
  }
 }
 public sealed class Gate {public ClassicalArrayReferenceCheck ArrayReferences;public ClassicalArraySelection ArrayTarget;public WireSelection SelectedWires;public ClassicalRealExpression NumericExpression;public ParameterizedGate ParameterGate;public RotationAxis? Axis;public ClassicalRealExpression Angle;public string Expression;public int[] Wires;public Operation Kind;public ulong Mask,Value;public ClassicalExpression ClassicalExpression;public int? VariableSlot;public ClassicalIntegerExpression IntegerExpression;public IntegerRange Range;public int? ClassicalBit {get;set;}public IList<Gate> WhenTrue {get;set;}public IList<Gate> WhenFalse {get;set;}}
 static bool UsesNumeric(IList<Gate> gates,int depth=0) {
  if(gates==null)return false;
  if(depth>32)throw new ArgumentException("Circuit nesting exceeds 32 levels.");
  foreach(var gate in gates) {
   if(gate==null)continue;
   if(gate.SelectedWires!=null || gate.Kind==Operation.StoreNumeric || gate.Kind==Operation.ClearNumeric || gate.NumericExpression!=null ||
      (gate.Angle!=null && gate.Angle.UsesNumericProtocol) || (gate.IntegerExpression!=null && gate.IntegerExpression.UsesNumericProtocol) ||
      (gate.ClassicalExpression!=null && gate.ClassicalExpression.UsesNumericProtocol))return true;
   if(gate.ParameterGate!=null) {
    foreach(var parameter in gate.ParameterGate.Parameters)if(parameter.UsesNumericProtocol)return true;
    if(gate.ParameterGate.Power.UsesNumericProtocol)return true;
   }
   if(gate.Range!=null && (gate.Range.Start.UsesNumericProtocol || gate.Range.Stop.UsesNumericProtocol || gate.Range.Step.UsesNumericProtocol))return true;
   if(UsesNumeric(gate.WhenTrue,depth+1) || UsesNumeric(gate.WhenFalse,depth+1))return true;
  }
  return false;
 }
 public sealed class Readout {public string Expression;public int[] Bits;}
 public static bool IsDynamic(IList<Gate> gates) {foreach(var gate in gates)if(gate!=null && gate.Kind!=Operation.Gate)return true;return false;}
 public sealed class Result {
  public int? classical_bits {get;set;} public int qubits {get;set;} public int shots {get;set;} public string seed {get;set;} public int[] wires {get;set;} public Dictionary<string,int> counts {get;set;}
 }
 public static byte[] Request(int qubits,int shots,ulong seed,int[] measured,IList<Gate> gates,IList<Readout> readout=null) {
  return Serialize(qubits,shots,seed,measured,gates,readout,null);
 }
 // Explicit classical outputs preserve saved records: no final measurements are added.
 public static byte[] RequestClassical(int qubits,int classicalBits,int shots,ulong seed,int[] outputBits,IList<Gate> gates,IList<ClassicalIntegerType> variableTypes=null,int? loopBudget=null,IList<ClassicalNumericType> numericTypes=null,IList<ClassicalArrayAllocation> arrays=null) {
  return Serialize(qubits,shots,seed,outputBits,gates,null,classicalBits,false,variableTypes,loopBudget,numericTypes,arrays);
 }
 internal static byte[] RequestExact(int qubits,int classicalBits,int[] outputBits,IList<Gate> gates,IList<ClassicalIntegerType> variableTypes=null,int? loopBudget=null,IList<ClassicalNumericType> numericTypes=null,IList<ClassicalArrayAllocation> arrays=null) {
  return Serialize(qubits,1,0,outputBits,gates,null,classicalBits,true,variableTypes,loopBudget,numericTypes,arrays);
 }
 static byte[] Serialize(int qubits,int shots,ulong seed,int[] measured,IList<Gate> gates,IList<Readout> readout,int? classicalBits,bool exact=false,IList<ClassicalIntegerType> variableTypes=null,int? loopBudget=null,IList<ClassicalNumericType> numericTypes=null,IList<ClassicalArrayAllocation> arrays=null) {
  if(exact && qubits>10)throw new ArgumentException("Exact circuits support at most 10 qubits.");
  int maxSteps=exact ? 512 : 4096;
  if(loopBudget.HasValue && (!classicalBits.HasValue || loopBudget.Value<0 || loopBudget.Value>1000000))throw new ArgumentException("Loop budget requires explicit classical outputs and 0–1,000,000 condition evaluations.");
  IList<ClassicalIntegerType> variables=null;
  if(variableTypes!=null) {
   if(!classicalBits.HasValue || variableTypes.Count>4096)throw new ArgumentException("Variables require explicit classical outputs and at most 4096 slots.");
   variables=new List<ClassicalIntegerType>(variableTypes);
   foreach(var type in variables)if(type==null)throw new ArgumentException("Variable declarations require integer types.");
  }
  bool wireProtocol=false;
  bool arrayProtocol=arrays!=null;
  bool numericProtocol=arrayProtocol || numericTypes!=null || UsesNumeric(gates);
  if(numericProtocol) {
   if(!classicalBits.HasValue)throw new ArgumentException("Numeric expressions require explicit classical outputs.");
   variables=new RuntimeDeclarations(variables ?? new ClassicalIntegerType[0],numericTypes ?? new ClassicalNumericType[0],arrays);
  }
  if(classicalBits.HasValue && (classicalBits.Value<0 || classicalBits.Value>64))throw new ArgumentException("Use 0–64 classical bits.");
  int bits=classicalBits ?? qubits;
  if(qubits<0 || qubits>25 || shots<1 || shots>100000 || gates==null || gates.Count>4096 || measured==null || (readout!=null && readout.Count>4096))
   throw new ArgumentException("Use 0–25 qubits, 1–100,000 shots and at most 4096 gates.");
  bool dynamic=classicalBits.HasValue || IsDynamic(gates) || (readout!=null && readout.Count>0);
  var text=new StringBuilder(exact ? "QEXACT1\n" : dynamic ? "QSAMPLE2\n" : "QSAMPLE1\n");
  Action<ulong> number=value=>text.Append(value.ToString(CultureInfo.InvariantCulture)).Append('\n');
  number((ulong)qubits);if(!exact){number((ulong)shots);number(seed);}if(dynamic)number((ulong)bits);
  int declarationPosition=text.Length;
  if(variables!=null){number((ulong)variables.Count);foreach(var type in variables)type.Write(number);}
  if(numericProtocol) {
   var declarations=(RuntimeDeclarations)variables;number((ulong)declarations.Numeric.Count);
   foreach(var type in declarations.Numeric)type.Write(number);
  }
  if(arrayProtocol){var declarations=(RuntimeDeclarations)variables;number((ulong)declarations.Arrays.Count);foreach(var array in declarations.Arrays)array.Write(number);}
  int budgetPosition=text.Length;
  Action<int[],int,int> wires=delegate(int[] values,int maximum,int registerSize) {
   if(values==null || values.Length>maximum)throw new ArgumentException("Invalid sampling wire list.");
   var seen=new HashSet<int>();number((ulong)values.Length);
   foreach(int wire in values) {
    if(wire<0 || wire>=registerSize || !seen.Add(wire))throw new ArgumentException("Sampling wires must be distinct and inside the register.");
    number((ulong)wire);
   }
  };
  wires(measured,bits,bits);
  int stepCount=gates.Count+(dynamic && !classicalBits.HasValue ? measured.Length : 0)+(readout==null ? 0 : readout.Count);
  if(stepCount>maxSteps)throw new ArgumentException("Circuit exceeds "+maxSteps+" operations including final measurements.");
  number((ulong)stepCount);
  // Final assignment errors must follow final measurements, or those
  // measurements would overwrite the noisy records before returning counts.
  var operations=new List<Gate>(gates);
  if(dynamic && !classicalBits.HasValue)foreach(int wire in measured)operations.Add(new Gate {Kind=Operation.Measure,Wires=new[]{wire}});
  if(readout!=null)foreach(var error in readout) {
   if(error==null || error.Bits==null)throw new ArgumentException("Invalid readout assignment.");
   foreach(int bit in error.Bits)if(Array.IndexOf(measured,bit)<0)throw new ArgumentException("Final readout targets must be measured bits.");
   operations.Add(new Gate {Kind=Operation.Readout,Wires=error.Bits,Expression=error.Expression});
  }
  int total=0;bool expressions=false,typedProtocol=false,bitExpressionProtocol=false,loopProtocol=loopBudget.HasValue || numericProtocol,transferProtocol=false,terminationProtocol=false,rangeProtocol=false,rotationProtocol=false,parameterGateProtocol=false;
  Action<Gate,int,int> write=null;
  write=delegate(Gate gate,int depth,int loopDepth) {
   if(++total>maxSteps)throw new ArgumentException("Circuit exceeds "+maxSteps+" total operations.");
   if(gate==null || !Enum.IsDefined(typeof(Operation),gate.Kind))throw new ArgumentException("Invalid sampling operation.");
   if((gate.Kind==Operation.CheckArrayReferences)!=(gate.ArrayReferences!=null))throw new ArgumentException("Only reference preflight requires array references.");
   if(gate.ArrayTarget!=null && gate.Kind!=Operation.StoreInteger && gate.Kind!=Operation.StoreNumeric)throw new ArgumentException("Only stores accept array targets.");
   if(gate.SelectedWires!=null) {
    if(!classicalBits.HasValue || depth>=32 || ++total>maxSteps)throw new ArgumentException("Runtime wires require explicit outputs and available nesting/step budget.");
    if(gate.Kind!=Operation.Gate && gate.Kind!=Operation.Channel && gate.Kind!=Operation.Measure && gate.Kind!=Operation.Reset && gate.Kind!=Operation.Rotation && gate.Kind!=Operation.ParameterGate)throw new ArgumentException("Only quantum operations accept runtime wire targets; use a surrounding branch for conditions.");
    if(gate.Wires==null || gate.Wires.Length!=gate.SelectedWires.Targets.Count)throw new ArgumentException("Wire target count differs from operation arity.");
    for(int k=0;k<gate.Wires.Length;k++)if(gate.Wires[k]!=k)throw new ArgumentException("Runtime operations require local ordinal wires.");
    wireProtocol=true;number(20);gate.SelectedWires.Write(number,text,qubits,bits,variables);
   }
   if(gate.ClassicalBit.HasValue && (!classicalBits.HasValue || gate.Kind!=Operation.Measure))throw new ArgumentException("A classical destination requires an explicit classical-output measurement.");
   bool range=gate.Kind==Operation.ForRange;rangeProtocol|=range;
   bool loop=gate.Kind==Operation.While || range;loopProtocol|=loop;
   bool branch=gate.Kind==Operation.Branch || gate.Kind==Operation.ExpressionBranch || loop;
   bool expression=gate.Kind==Operation.Assign || gate.Kind==Operation.ExpressionBranch || gate.Kind==Operation.While;
   if(!branch && (gate.WhenTrue!=null || gate.WhenFalse!=null))throw new ArgumentException("Only a branch can contain operation bodies.");
   if(!expression && gate.ClassicalExpression!=null)throw new ArgumentException("Only assignments and expression branches accept classical expressions.");
   bool numeric=gate.Kind==Operation.StoreNumeric || gate.Kind==Operation.ClearNumeric;
   if(!numeric && gate.NumericExpression!=null)throw new ArgumentException("Only numeric stores accept numeric expressions.");
   bool integer=gate.Kind==Operation.StoreInteger || gate.Kind==Operation.ClearInteger;
   if((!integer && gate.IntegerExpression!=null) || (!integer && !range && !numeric && gate.VariableSlot.HasValue))throw new ArgumentException("Only variable operations accept integer expressions; variable operations and ranges accept variable targets.");
   if(range!=(gate.Range!=null))throw new ArgumentException("Only range loops require range expressions.");
   bool parameterGate=gate.Kind==Operation.ParameterGate;
   if(parameterGate!=(gate.ParameterGate!=null))throw new ArgumentException("Only parameterized gates require a runtime gate value.");
   if(parameterGate) {
    if(!classicalBits.HasValue || gate.Axis.HasValue || gate.Angle!=null || gate.Wires==null || gate.Wires.Length!=gate.ParameterGate.WireCount ||
       !String.IsNullOrEmpty(gate.Expression) || gate.Mask!=0 || gate.Value!=0)throw new ArgumentException("Invalid parameterized gate fields.");
    var used=new HashSet<int>();foreach(int wire in gate.Wires)if(wire<0 || wire>=qubits || !used.Add(wire))throw new ArgumentException("Runtime gate wires must be distinct and in range.");
    gate.ParameterGate.Validate(bits,variables);number(17);number((ulong)gate.Wires.Length);foreach(int wire in gate.Wires)number((ulong)wire);gate.ParameterGate.WriteNode(number);
    parameterGateProtocol=true;loopProtocol=true;
    if(text.Length>1100000)throw new ArgumentException("Sampling request is too large.");return;
   }
   bool rotation=gate.Kind==Operation.Rotation;
   if(!rotation && (gate.Axis.HasValue || gate.Angle!=null))throw new ArgumentException("Only runtime rotations accept an axis and angle.");
   if(rotation) {
    if(!classicalBits.HasValue || !gate.Axis.HasValue || !Enum.IsDefined(typeof(RotationAxis),gate.Axis.Value) || gate.Angle==null ||
       gate.Wires==null || gate.Wires.Length!=1 || gate.Wires[0]<0 || gate.Wires[0]>=qubits ||
       !String.IsNullOrEmpty(gate.Expression) || gate.Mask!=0 || gate.Value!=0)
     throw new ArgumentException("Runtime rotations require explicit outputs, one wire, an axis and a real angle.");
    gate.Angle.Validate(bits,variables);number(16);number((ulong)gate.Wires[0]);number((ulong)gate.Axis.Value);gate.Angle.WriteNode(number);
    rotationProtocol=true;loopProtocol=true;
    if(text.Length>1100000)throw new ArgumentException("Sampling request is too large.");
    return;
   }
   if(gate.Kind==Operation.CheckArrayReferences) {
    if(!arrayProtocol || (gate.Wires!=null && gate.Wires.Length!=0) || !String.IsNullOrEmpty(gate.Expression) || gate.Mask!=0 || gate.Value!=0)throw new ArgumentException("Invalid array reference preflight fields.");
    gate.ArrayReferences.Validate(bits,variables);number(23);gate.ArrayReferences.Write(number);
    if(text.Length>1100000)throw new ArgumentException("Sampling request is too large.");return;
   }
   if(range && (!classicalBits.HasValue || variables==null || !gate.VariableSlot.HasValue || gate.VariableSlot.Value<0 || gate.VariableSlot.Value>=variables.Count || gate.Mask!=0 || gate.Value!=0))throw new ArgumentException("Range loops require explicit outputs, a declared binding slot and no condition mask.");
   if(gate.Kind==Operation.Break || gate.Kind==Operation.Continue || gate.Kind==Operation.End) {
    bool end=gate.Kind==Operation.End;
    if(!classicalBits.HasValue)throw new ArgumentException("Control transfers require explicit classical outputs.");
    if(!end && loopDepth==0)throw new ArgumentException("Loop transfers require an enclosing loop.");
    if((gate.Wires!=null && gate.Wires.Length!=0) || !String.IsNullOrEmpty(gate.Expression) || gate.Mask!=0 || gate.Value!=0)
     throw new ArgumentException("Control transfers have no expression, targets or condition fields.");
    terminationProtocol|=end;loopProtocol=true;transferProtocol=true;number((ulong)gate.Kind);return;
   }
   if(gate.ArrayTarget!=null) {
    if(!arrayProtocol || gate.VariableSlot.HasValue || (gate.Wires!=null && gate.Wires.Length!=0) || !String.IsNullOrEmpty(gate.Expression) || gate.Mask!=0 || gate.Value!=0)throw new ArgumentException("Invalid array store fields.");
    if(gate.ArrayTarget.View!=null && !gate.ArrayTarget.View.Writable)throw new ArgumentException("Cannot write through a readonly array reference.");
    var allocation=gate.ArrayTarget.Validate(bits,variables);
    if(numeric) {
     if(allocation.Numeric==null || gate.NumericExpression==null)throw new ArgumentException("Numeric array store needs a numeric array and value.");
     if(gate.NumericExpression.Type.Kind==ClassicalNumericType.NumericKind.Angle && allocation.Numeric.Kind!=ClassicalNumericType.NumericKind.Angle)throw new ArgumentException("Angles cannot be stored in floats.");
     gate.NumericExpression.Validate(bits,variables);number(22);gate.ArrayTarget.Write(number);gate.NumericExpression.WriteNode(number);
    } else {
     if(allocation.Integer==null || gate.IntegerExpression==null)throw new ArgumentException("Integer array store needs an integer array and value.");
     gate.IntegerExpression.Validate(bits,variables);number(21);gate.ArrayTarget.Write(number);gate.IntegerExpression.WriteNode(number);
    }
    if(text.Length>1100000)throw new ArgumentException("Sampling request is too large.");return;
   }
   if(numeric) {
    var declarations=variables as RuntimeDeclarations;
    if(declarations==null || !gate.VariableSlot.HasValue || gate.VariableSlot.Value<0 || gate.VariableSlot.Value>=declarations.Numeric.Count ||
       (gate.Wires!=null && gate.Wires.Length!=0) || !String.IsNullOrEmpty(gate.Expression) || gate.Mask!=0 || gate.Value!=0)
     throw new ArgumentException("Invalid numeric variable operation or slot.");
    if((gate.Kind==Operation.StoreNumeric)!=(gate.NumericExpression!=null))throw new ArgumentException("Only numeric stores require an expression.");
    number((ulong)gate.Kind);number((ulong)gate.VariableSlot.Value);
    if(gate.NumericExpression!=null) {
     var target=declarations.Numeric[gate.VariableSlot.Value];
     if(gate.NumericExpression.Type.Kind==ClassicalNumericType.NumericKind.Angle && target.Kind!=ClassicalNumericType.NumericKind.Angle)throw new ArgumentException("Angles cannot be stored in floats.");
     gate.NumericExpression.Validate(bits,variables);gate.NumericExpression.WriteNode(number);
    }
    if(text.Length>1100000)throw new ArgumentException("Sampling request is too large.");return;
   }
   if(integer) {
    if(variables==null || !gate.VariableSlot.HasValue || gate.VariableSlot.Value<0 || gate.VariableSlot.Value>=variables.Count ||
       (gate.Wires!=null && gate.Wires.Length!=0) || !String.IsNullOrEmpty(gate.Expression) || gate.Mask!=0 || gate.Value!=0)
     throw new ArgumentException("Invalid variable operation fields or slot.");
    if((gate.Kind==Operation.StoreInteger)!=(gate.IntegerExpression!=null))throw new ArgumentException("Only variable stores require an integer expression.");
    number((ulong)gate.Kind);number((ulong)gate.VariableSlot.Value);
    if(gate.IntegerExpression!=null){gate.IntegerExpression.Validate(bits,variables);gate.IntegerExpression.WriteNode(number);bitExpressionProtocol|=gate.IntegerExpression.UsesBitExpressionProtocol;}
    if(text.Length>1100000)throw new ArgumentException("Sampling request is too large.");
    return;
   }
   if(expression) {
    if(!classicalBits.HasValue || gate.ClassicalExpression==null || !String.IsNullOrEmpty(gate.Expression) || gate.Mask!=0 || gate.Value!=0)throw new ArgumentException("Classical expressions require explicit outputs and cannot include matrices or masks.");
    expressions=true;typedProtocol|=gate.ClassicalExpression.UsesTypedProtocol;
    bitExpressionProtocol|=gate.ClassicalExpression.UsesBitExpressionProtocol;
   }
   if(dynamic)number((ulong)gate.Kind);
   if(range) {
    number((ulong)gate.VariableSlot.Value);gate.Range.Write(number,bits,variables);
    if(text.Length>1100000)throw new ArgumentException("Sampling request is too large.");
   }
   if(gate.Kind==Operation.Assign) {
    if(gate.Wires==null || gate.Wires.Length!=gate.ClassicalExpression.Width)throw new ArgumentException("Assignment width must match its targets.");
    wires(gate.Wires,bits,bits);gate.ClassicalExpression.Write(number,bits,variables);
    if(text.Length>1100000)throw new ArgumentException("Sampling request is too large.");
    return;
   }
   if(gate.Kind==Operation.ExpressionBranch || gate.Kind==Operation.While) {
    if(gate.ClassicalExpression.Width!=1)throw new ArgumentException("A branch condition must be one bit.");
    gate.ClassicalExpression.Write(number,bits,variables);
    if(text.Length>1100000)throw new ArgumentException("Sampling request is too large.");
   }
   if(gate.Kind==Operation.Conditional || gate.Kind==Operation.Branch) {
    if(exact && gate.Kind==Operation.Conditional && ++total>maxSteps)throw new ArgumentException("Exact conditional expansion exceeds 512 steps.");
    ulong allowed=bits==64 ? UInt64.MaxValue : (1UL<<bits)-1;
    if((gate.Mask & ~allowed)!=0 || (gate.Value & ~gate.Mask)!=0)throw new ArgumentException("Invalid classical condition.");
    number(gate.Mask);number(gate.Value);
   }
   if(branch) {
    if(!classicalBits.HasValue)throw new ArgumentException("Branches require explicit classical outputs.");
    if(depth>=32)throw new ArgumentException("Sampling branches exceed 32 nesting levels.");
    if(gate.WhenTrue==null || (loop ? gate.WhenFalse!=null : gate.WhenFalse==null) || (gate.Wires!=null && gate.Wires.Length!=0) || !String.IsNullOrEmpty(gate.Expression))throw new ArgumentException("Branches require two bodies; loops require only WhenTrue. Neither accepts matrix or quantum targets.");
    foreach(var body in loop ? new[]{gate.WhenTrue} : new[]{gate.WhenTrue,gate.WhenFalse}) {
     if(body.Count>maxSteps-total)throw new ArgumentException("Circuit exceeds "+maxSteps+" total operations.");
     number((ulong)body.Count);
     foreach(var child in body)write(child,depth+1,loopDepth+(loop ? 1 : 0));
    }
    return;
   }
   if(gate.Kind==Operation.Measure || gate.Kind==Operation.Reset) {
    if(gate.Wires==null || gate.Wires.Length!=1 || gate.Wires[0]<0 || gate.Wires[0]>=qubits)
     throw new ArgumentException("Measurement and reset need one wire inside the register.");
    number((ulong)gate.Wires[0]);
    if(gate.Kind==Operation.Measure) {
     int destination=classicalBits.HasValue ? (gate.ClassicalBit ?? -1) : gate.Wires[0];
     if(destination<0 || destination>=bits)throw new ArgumentException("Measurement needs a destination inside the classical register.");
     number((ulong)destination);
    }
    return;
   }
   if(gate.Wires==null || gate.Wires.Length==0 || String.IsNullOrWhiteSpace(gate.Expression) || gate.Expression.IndexOf('\0')>=0)
    throw new ArgumentException("Each sampling gate needs a matrix expression and target wires.");
   wires(gate.Wires,gate.Kind==Operation.Readout ? 8 : exact ? qubits : 3,gate.Kind==Operation.Readout ? bits : qubits);
   int length=Encoding.UTF8.GetByteCount(gate.Expression);
   if(length>4096)throw new ArgumentException("A sampling gate expression exceeds 4096 UTF-8 bytes.");
   number((ulong)length);text.Append(gate.Expression);
   if(text.Length>1100000)throw new ArgumentException("Sampling request is too large.");
  };
  foreach(var operation in operations)write(operation,0,0);
  if(loopProtocol) {
   string budget=(loopBudget ?? 1000000).ToString(CultureInfo.InvariantCulture)+"\n";
   if(variables==null)text.Insert(declarationPosition,"0\n"+budget);
   else text.Insert(budgetPosition,budget);
   text.Remove(0,exact ? 8 : 9).Insert(0,arrayProtocol ? (exact ? "QEXACT15\n" : "QSAMPLE16\n") : wireProtocol ? (exact ? "QEXACT13\n" : "QSAMPLE14\n") : numericProtocol ? (exact ? "QEXACT12\n" : "QSAMPLE13\n") : parameterGateProtocol ? (exact ? "QEXACT11\n" : "QSAMPLE12\n") : rotationProtocol ? (exact ? "QEXACT10\n" : "QSAMPLE11\n") : rangeProtocol ? (exact ? "QEXACT9\n" : "QSAMPLE10\n") : terminationProtocol ? (exact ? "QEXACT8\n" : "QSAMPLE9\n") : transferProtocol ? (exact ? "QEXACT7\n" : "QSAMPLE8\n") : (exact ? "QEXACT6\n" : "QSAMPLE7\n"));
  }
  else if(bitExpressionProtocol) {
   if(variables==null)text.Insert(declarationPosition,"0\n");
   text.Remove(0,exact ? 8 : 9).Insert(0,exact ? "QEXACT5\n" : "QSAMPLE6\n");
  }
  else if(variables!=null)text.Remove(0,exact ? 8 : 9).Insert(0,exact ? "QEXACT4\n" : "QSAMPLE5\n");
  else if(expressions)text.Remove(0,exact ? 8 : 9).Insert(0,typedProtocol ? (exact ? "QEXACT3\n" : "QSAMPLE4\n") : (exact ? "QEXACT2\n" : "QSAMPLE3\n"));
  byte[] bytes=new UTF8Encoding(false,true).GetBytes(text.ToString());
  if(bytes.Length>1100000)throw new ArgumentException("Sampling request is too large.");
  return bytes;
 }
 public static Result ReadResult(string json,int qubits,int shots,ulong seed,int[] measured,bool dynamic=false) {
  return ValidateResult(json,qubits,shots,seed,measured,dynamic ? (int?)qubits : null);
 }
 public static Result ReadClassicalResult(string json,int qubits,int classicalBits,int shots,ulong seed,int[] outputBits) {
  if(classicalBits<0 || classicalBits>64)throw new ArgumentException("Use 0–64 classical bits.");
  return ValidateResult(json,qubits,shots,seed,outputBits,classicalBits);
 }
 static Result ValidateResult(string json,int qubits,int shots,ulong seed,int[] measured,int? classicalBits) {
  var result=new JavaScriptSerializer {MaxJsonLength=8000000,RecursionLimit=12}.Deserialize<Result>(json);
  if(result==null || result.qubits!=qubits || result.shots!=shots || result.seed!=seed.ToString(CultureInfo.InvariantCulture) ||
     result.wires==null || result.wires.Length!=measured.Length || result.counts==null || result.counts.Count>shots)
   throw new InvalidDataException("The sampler returned an inconsistent response.");
  if(result.classical_bits!=classicalBits)
   throw new InvalidDataException("The sampler returned the wrong classical register.");
  for(int k=0;k<measured.Length;k++)if(result.wires[k]!=measured[k])throw new InvalidDataException("The sampler changed the measurement order.");
  long total=0;
  foreach(var item in result.counts) {
   if(item.Key.Length!=measured.Length || item.Value<=0 || item.Value>shots)throw new InvalidDataException("Invalid sample count.");
   foreach(char bit in item.Key)if(bit!='0' && bit!='1')throw new InvalidDataException("Invalid sampled bit string.");
   total+=item.Value;
  }
  if(total!=shots)throw new InvalidDataException("Sample counts do not sum to the requested shots.");
  return result;
 }
 public static Task<Result> Run(string worker,int qubits,int shots,ulong seed,int[] measured,IList<Gate> gates,CancellationToken cancellation,IList<Readout> readout=null) {
  // Serialize before handing work to another thread, so editor changes cannot alter a run.
  byte[] request=Request(qubits,shots,seed,measured,gates,readout);
  bool dynamic=IsDynamic(gates) || (readout!=null && readout.Count>0);
  int[] order=(int[])measured.Clone();
  return RunSerialized(worker,qubits,shots,seed,order,request,cancellation,dynamic ? (int?)qubits : null);
 }
 public static Task<Result> RunClassical(string worker,int qubits,int classicalBits,int shots,ulong seed,int[] outputBits,IList<Gate> gates,CancellationToken cancellation,IList<ClassicalIntegerType> variableTypes=null,int? loopBudget=null,IList<ClassicalNumericType> numericTypes=null,IList<ClassicalArrayAllocation> arrays=null) {
  byte[] request=RequestClassical(qubits,classicalBits,shots,seed,outputBits,gates,variableTypes,loopBudget,numericTypes,arrays);
  return RunSerialized(worker,qubits,shots,seed,(int[])outputBits.Clone(),request,cancellation,classicalBits);
 }
 static Task<Result> RunSerialized(string worker,int qubits,int shots,ulong seed,int[] order,byte[] request,CancellationToken cancellation,int? classicalBits) {
  return RunRequest(worker,"--sample",request,cancellation,json=>ValidateResult(json,qubits,shots,seed,order,classicalBits));
 }
 internal static Task<T> RunRequest<T>(string worker,string mode,byte[] request,CancellationToken cancellation,Func<string,T> parse) {
  return Task.Run(async delegate {
   cancellation.ThrowIfCancellationRequested();
   using(var process=new Process()) {
    process.StartInfo=new ProcessStartInfo(worker,mode) {UseShellExecute=false,CreateNoWindow=true,RedirectStandardInput=true,RedirectStandardOutput=true,RedirectStandardError=true,StandardOutputEncoding=Encoding.UTF8,StandardErrorEncoding=Encoding.UTF8,WorkingDirectory=Path.GetDirectoryName(worker)};
    process.StartInfo.EnvironmentVariables["QALCULATE_DEFINITIONS_DIR"]=Path.Combine(Path.GetDirectoryName(worker),"data");
    // Closing the last WPF window can end the process before a thread-pool
    // continuation runs. Stop the child synchronously when cancellation fires.
    // Serialize startup with cancellation so closing during Start cannot orphan it.
    var lifetime=new object();bool started=false;
    using(cancellation.Register(delegate {
     lock(lifetime) {
      if(!started)return;
      try {if(!process.HasExited)process.Kill();}
      catch(InvalidOperationException) {} // The child may have exited concurrently.
      catch(System.ComponentModel.Win32Exception) {} // Cleanup below repeats the check.
     }
    })) {
    lock(lifetime) {cancellation.ThrowIfCancellationRequested();process.Start();started=true;}
    var clock=Stopwatch.StartNew();
    try {
     var output=process.StandardOutput.ReadToEndAsync();var error=process.StandardError.ReadToEndAsync();
     await process.StandardInput.BaseStream.WriteAsync(request,0,request.Length,cancellation);process.StandardInput.Close();
     while(!process.WaitForExit(50)) {
      cancellation.ThrowIfCancellationRequested();
      if(clock.Elapsed.TotalMinutes>=5)throw new TimeoutException("Circuit evaluation exceeded five minutes. Reduce the circuit size or shot count.");
     }
     cancellation.ThrowIfCancellationRequested();
     string stdout=await output,stderr=await error;
     if(process.ExitCode!=0)throw new InvalidOperationException(String.IsNullOrWhiteSpace(stderr) ? "Circuit evaluation failed." : stderr.Trim());
     return parse(stdout);
    } catch {cancellation.ThrowIfCancellationRequested();throw;}
    finally {lock(lifetime) {if(!process.HasExited)process.Kill();}process.WaitForExit();}
    }
   }
  });
 }
}
