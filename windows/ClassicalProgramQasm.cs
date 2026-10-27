// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;

// Build the complete text before any caller opens an output file.
// The validated circuit model, not editable display text, drives statements.
sealed class ClassicalProgramQasm {
 readonly ClassicalCircuit circuit;
 readonly ClassicalQasmStorage storage;
 readonly ClassicalExpressionQasm expressions;
 readonly ClassicalIntegerType[] variables;
 ClassicalQasmScopes scopes;
 static readonly HashSet<string> Gates=new HashSet<string>(
  ("H X Y Z S T Sdg Tdg SX SXdg Rx Ry Rz P CNOT CZ SWAP CCX CY CH CCZ CSWAP "+
   "CP CRx CRy CRz Rxx Ryy Rzz Rzx R U3 fSim ECR FSWAP iSWAP XXPlusYY XXMinusYY").Split(' '));
 static string Number(int value){return value.ToString(CultureInfo.InvariantCulture);}
 static string Type(ClassicalIntegerType value) {
  return (value.Signedness==ClassicalIntegerType.Sign.Signed ? "int[" : "uint[")+Number(value.Width)+"]";
 }
 ClassicalProgramQasm(ClassicalCircuit value) {
  circuit=value;variables=value.VariableTypes??new ClassicalIntegerType[0];
  storage=new ClassicalQasmStorage(value.ClassicalBits,value.OutputBits);
  expressions=new ClassicalExpressionQasm(value.ClassicalBits,variables,storage);
  if(storage.BitCount>0 && variables.Length>=4096)
   throw new InvalidDataException("OpenQASM export needs one assignment temporary within the 4096-variable limit.");
 }
 public static string Export(ClassicalCircuit value) {
  if(value==null)throw new ArgumentNullException("value");
  return new ClassicalProgramQasm(value).Build(true);
 }
 string Build(bool recoverLifetimes=false) {
  var steps=circuit.SamplingGates();
  try {scopes=new ClassicalQasmScopes(steps,variables.Length);}
  catch(InvalidDataException) {
   if(!recoverLifetimes)throw;
   return new ClassicalProgramQasm(ClassicalQasmLifetimes.Prepare(circuit)).Build();
  }
  var prefix=new StringBuilder("OPENQASM 3.0;\ninclude \"stdgates.inc\";\n");
  if(circuit.Qubits>0)prefix.Append("qubit["+Number(circuit.Qubits)+"] q;\nreset q;\n");
  var body=new StringBuilder();
  // QuantumStudio starts bits at zero. OpenQASM declarations alone do not
  // promise that value. Integer variables deliberately remain undefined.
  for(int i=0;i<storage.BitCount;i++)body.Append(storage.Bit(i)+" = 0;\n");
  Statements(body,steps);
  prefix.Append(storage.ProgramBody(body.ToString()));
  string source=prefix.ToString();
  if(Encoding.UTF8.GetByteCount(source)>262144)
   throw new InvalidDataException("Exported OpenQASM exceeds the compiler's 256 KB limit.");
  return source;
 }
 string Condition(ClassicalExpression expression){return "("+expressions.Bits(expression)+") != \"0\"";}
 string MaskCondition(ulong mask,ulong value) {
  if(mask==0)return "true";
  var terms=new List<string>();
  for(int bit=0;bit<storage.BitCount;bit++)if((mask&(1UL<<bit))!=0)
   terms.Add(storage.Bit(bit)+" == "+(((value>>bit)&1)==0 ? "0" : "1"));
  return String.Join(" && ",terms);
 }
 void Gate(StringBuilder text,NumericalSampling.Gate gate) {
  string expression=gate.Expression.Trim();
  if(expression=="I" && gate.Wires.Length==1)return;
  // Only recognized named gates reach the shared serializer. Matrix-valued
  // calculator expressions require a separate decomposition, never a guess.
  var match=Regex.Match(expression,@"\A([A-Za-z][A-Za-z0-9]*)(?:\((.*)\))?\z");
  string name=match.Success ? match.Groups[1].Value : "";
  if(!Gates.Contains(name))
   throw new InvalidDataException("OpenQASM export cannot decompose gate expression: "+expression);
  bool parameterized=QasmGateSerializer.NeedsAngle(name);
  if(match.Groups[2].Success!=parameterized || gate.Wires.Length!=QasmGateSerializer.WireCount(name))
   throw new InvalidDataException("Gate parameters or wire count do not match "+name+".");
  string angle=parameterized ? match.Groups[2].Value : "";
  if(parameterized)QasmGateSerializer.GateAngles(name,angle);
  int unused=0;QasmGateSerializer.Append(text,name,angle,gate.Wires,ref unused);
  if(unused!=0)throw new InvalidDataException("Gate export unexpectedly allocated measurement storage.");
 }
 void Block(StringBuilder text,string condition,IList<NumericalSampling.Gate> yes,IList<NumericalSampling.Gate> no) {
  text.Append("if ("+condition+") {\n");Statements(text,yes);text.Append("}\n");
  if(no!=null && no.Count>0){text.Append("else {\n");Statements(text,no);text.Append("}\n");}
 }
 void ParameterGate(StringBuilder text,NumericalSampling.Gate step) {
  var gate=step.ParameterGate;
  var modifiers=new StringBuilder();
  for(int i=0;i<gate.Controls;i++)modifiers.Append(((gate.ControlState>>(gate.Controls-1-i))&1)==0 ? "negctrl @ " : "ctrl @ ");
  modifiers.Append("pow("+expressions.Integer(gate.Power)+") @ ");
  var parameters=new List<string>();foreach(var value in gate.Parameters)parameters.Add(expressions.Real(value));
  var targets=new List<string>();foreach(int wire in step.Wires)targets.Add("q["+Number(wire)+"]");
  string suffix=targets.Count==0 ? ";\n" : " "+String.Join(", ",targets)+";\n";
  string name=gate.Kind==NumericalSampling.ParameterGateKind.Phase ? "p" :
   gate.Kind==NumericalSampling.ParameterGateKind.GlobalPhase ? "gphase" :
   gate.Kind==NumericalSampling.ParameterGateKind.U3 || gate.Kind==NumericalSampling.ParameterGateKind.PublishedU ? "u3" : "r"+gate.Kind.ToString().ToLowerInvariant();
  // Explicit phase makes the chosen U convention independent of the importer setting.
  if(gate.Kind==NumericalSampling.ParameterGateKind.PublishedU) {
   var controls=targets.GetRange(0,gate.Controls);
   text.Append(modifiers+"gphase(("+parameters[0]+") / 2.0)"+(controls.Count==0 ? ";\n" : " "+String.Join(", ",controls)+";\n"));
  }
  text.Append(modifiers+name+"("+String.Join(", ",parameters)+")"+suffix);
 }
 void Statements(StringBuilder text,IList<NumericalSampling.Gate> gates) {
  foreach(int slot in scopes.Declarations(gates))text.Append(Type(variables[slot])+" v"+Number(slot)+";\n");
  foreach(var gate in gates) {
   switch(gate.Kind) {
    case NumericalSampling.Operation.Gate:Gate(text,gate);break;
    case NumericalSampling.Operation.ParameterGate:ParameterGate(text,gate);break;
    case NumericalSampling.Operation.Rotation:
     text.Append("r"+gate.Axis.Value.ToString().ToLowerInvariant()+"("+expressions.Real(gate.Angle)+") q["+Number(gate.Wires[0])+"];\n");break;
    case NumericalSampling.Operation.Measure:
     text.Append(storage.Bit(gate.ClassicalBit.Value)+" = measure q["+Number(gate.Wires[0])+"];\n");break;
    case NumericalSampling.Operation.Reset:
     text.Append("reset q["+Number(gate.Wires[0])+"];\n");break;
    case NumericalSampling.Operation.Conditional:
     text.Append("if ("+MaskCondition(gate.Mask,gate.Value)+") {\n");Gate(text,gate);text.Append("}\n");break;
    case NumericalSampling.Operation.Branch:
     Block(text,MaskCondition(gate.Mask,gate.Value),gate.WhenTrue,gate.WhenFalse);break;
    case NumericalSampling.Operation.ExpressionBranch:
     Block(text,Condition(gate.ClassicalExpression),gate.WhenTrue,gate.WhenFalse);break;
    case NumericalSampling.Operation.Assign:
     text.Append(storage.Assign(gate.Wires,gate.ClassicalExpression,variables));break;
    case NumericalSampling.Operation.StoreInteger:
     int slot=gate.VariableSlot.Value;
     text.Append("v"+Number(slot)+" = "+Type(variables[slot])+"("+expressions.Integer(gate.IntegerExpression)+");\n");break;
    case NumericalSampling.Operation.While:
     if(circuit.LoopConditionBudget!=1000000)
      throw new InvalidDataException("OpenQASM export requires the standard 1000000-condition loop budget.");
     text.Append("while ("+Condition(gate.ClassicalExpression)+") {\n");Statements(text,gate.WhenTrue);text.Append("}\n");break;
    case NumericalSampling.Operation.Break:text.Append("break;\n");break;
    case NumericalSampling.Operation.Continue:text.Append("continue;\n");break;
    case NumericalSampling.Operation.End:text.Append("end;\n");break;
    case NumericalSampling.Operation.ClearInteger:break; // Proven lexical exit.
    case NumericalSampling.Operation.ForRange:
     if(circuit.LoopConditionBudget!=1000000)
      throw new InvalidDataException("OpenQASM export requires the standard 1000000-condition loop budget.");
     int iterator=gate.VariableSlot.Value;
     text.Append("for "+Type(variables[iterator])+" v"+Number(iterator)+" in ["+
      expressions.Integer(gate.Range.Start)+":"+expressions.Integer(gate.Range.Step)+":"+expressions.Integer(gate.Range.Stop)+"] {\n");
     Statements(text,gate.WhenTrue);text.Append("}\n");break;
    case NumericalSampling.Operation.Channel:
    case NumericalSampling.Operation.Readout:
     throw new InvalidDataException("OpenQASM export does not support "+gate.Kind+" noise operations.");
    default:throw new InvalidDataException("Unsupported OpenQASM statement: "+gate.Kind);
   }
  }
 }
}
