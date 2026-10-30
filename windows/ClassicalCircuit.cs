// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using System.Web.Script.Serialization;

// Versions 2-4 store saved bits and expressions; version 5 adds typed variable slots; version 6 adds computed bit casts; version 7 adds loops and their budget; version 8 adds loop transfers; version 9 adds program termination; version 10 adds runtime ranges.
// The editor receives copies; a validated program cannot change underneath a run.
sealed class ClassicalCircuit {
 public sealed class Register {public string Name {get;set;}public int Size {get;set;}}
 public sealed class NumericVariable {public string Name {get;set;}public string NumericKind {get;set;}public int Width {get;set;}}
 public sealed class Variable {public string Name {get;set;}public string Signedness {get;set;}public int Width {get;set;}}
 public sealed class ExpressionNode {
  public ArraySelectionNode Selection {get;set;}
  public RealNode RealLeft {get;set;}public RealNode RealRight {get;set;}
  public int? Slot {get;set;}
  public string Signedness {get;set;}
  public string Kind {get;set;}public int? Width {get;set;}public string Value {get;set;}
  public int[] Bits {get;set;}public string Operator {get;set;}
  public string RotationDirection {get;set;}public string DistanceInterpretation {get;set;}
  public ExpressionNode Left {get;set;}public ExpressionNode Right {get;set;}
 }
 public sealed class WireTargetNode {public int[] Candidates {get;set;}public ExpressionNode Index {get;set;}}
 public sealed class Step {
  public ArraySelectionNode ArrayTarget {get;set;}
  public WireTargetNode[] WireTargets {get;set;}public string WireSource {get;set;}
  public RealNode NumericValue {get;set;}
  public ParameterGateNode ParameterGate {get;set;}
  public string Axis {get;set;}public RealNode Angle {get;set;}
  public string Kind {get;set;}public string Expression {get;set;}public int[] Wires {get;set;}
  public int? ClassicalBit {get;set;}public string Mask {get;set;}public string Value {get;set;}
  public Step[] WhenTrue {get;set;}public Step[] WhenFalse {get;set;}
  public ExpressionNode ClassicalValue {get;set;}
  public int? VariableSlot {get;set;}public ExpressionNode IntegerValue {get;set;}
  public RangeNode Range {get;set;}
 }
 public sealed class RangeNode {public ExpressionNode Start {get;set;}public ExpressionNode Stop {get;set;}public ExpressionNode Step {get;set;}}
 public sealed class ParameterGateNode {
  public string Gate {get;set;}public int Controls {get;set;}public string ControlState {get;set;}
  public RealNode[] Parameters {get;set;}public ExpressionNode Power {get;set;}
 }
 public sealed class RealNode {
  public ArraySelectionNode Selection {get;set;}
  public string NumericKind {get;set;}public int? Width {get;set;}public int? Slot {get;set;}
  public string Function {get;set;}public string Scaling {get;set;}public ExpressionNode BitValue {get;set;}
  public string Kind {get;set;}public string ValueBits {get;set;}public string Operator {get;set;}
  public ExpressionNode IntegerValue {get;set;}public RealNode Left {get;set;}public RealNode Right {get;set;}
 }
 public sealed class ArraySelectionNode {public int Array {get;set;}public ExpressionNode[] Indices {get;set;}public string Source {get;set;}}
 public sealed class ArrayDeclaration {public string Name {get;set;}public int Base {get;set;}public int[] Dimensions {get;set;}public string Signedness {get;set;}public string NumericKind {get;set;}public int Width {get;set;}}
 public sealed class Document {
  public ArrayDeclaration[] Arrays {get;set;}
  public int? LoopConditionBudget {get;set;}
  public int Version {get;set;}public int Qubits {get;set;}public Register[] Registers {get;set;}
  public int[] OutputBits {get;set;}public Step[] Steps {get;set;}
  public Variable[] Variables {get;set;}public NumericVariable[] NumericVariables {get;set;}
 }
 const int MaxBytes=262144;
 readonly Document document;readonly string json;readonly int classicalBits;
 static JavaScriptSerializer Serializer() {return new JavaScriptSerializer {MaxJsonLength=MaxBytes,RecursionLimit=128};}
 ClassicalCircuit(Document value,string text,int bits) {document=value;json=text;classicalBits=bits;}
 public int Qubits {get{return document.Qubits;}}
 public int? LoopConditionBudget {get{return document.LoopConditionBudget;}}
 public int ClassicalBits {get{return classicalBits;}}
 public int[] OutputBits {get{return (int[])document.OutputBits.Clone();}}
 public ClassicalIntegerType[] VariableTypes {get{return Types(document.Variables);}}
 public ClassicalNumericType[] NumericTypes {get{return NumericTypesOf(document.NumericVariables);}}
 public ClassicalArrayAllocation[] ArrayAllocations {get{return Allocations(document.Arrays);}}
 internal RuntimeDeclarations Declarations {get{return new RuntimeDeclarations(VariableTypes??new ClassicalIntegerType[0],NumericTypes??new ClassicalNumericType[0],ArrayAllocations);}}
 public string Serialize() {return json;}
 public Document Snapshot() {return Serializer().Deserialize<Document>(json);}
 public static ClassicalCircuit From(Document value) {return Load(SerializeDocument(value));}
 static string SerializeDocument(Document value) {
  // DTO serialization expands every absent optional field to null. Bound that
  // temporary representation separately; the canonical public document still
  // has the same 256 KiB UTF-8 limit enforced by Load.
  var expanded=Serializer();expanded.MaxJsonLength=MaxBytes*16;
  return expanded.Serialize(CanonicalFields(expanded.DeserializeObject(expanded.Serialize(value))));
 }
 static InvalidDataException Invalid(string message) {return new InvalidDataException(message);}
 static Dictionary<string,object> Fields(object value,string allowed) {
  var fields=value as Dictionary<string,object>;
  if(fields==null)throw Invalid("Expected a circuit object.");
  var names=new HashSet<string>(allowed.Split(','),StringComparer.Ordinal);
  foreach(string name in fields.Keys)if(!names.Contains(name))throw Invalid("Unknown circuit field: "+name);
  return fields;
 }
 static object Required(Dictionary<string,object> fields,string name) {
  object value;if(!fields.TryGetValue(name,out value) || value==null)throw Invalid("Missing circuit field: "+name);return value;
 }
 static object[] ArrayValue(object value) {var array=value as object[];if(array==null)throw Invalid("Expected a circuit array.");return array;}
 static void Integer(object value) {if(!(value is int))throw Invalid("Expected an integer circuit field.");}
 static void IntegerArray(object value) {foreach(object item in ArrayValue(value))Integer(item);}
 static ClassicalArrayAllocation[] Allocations(ArrayDeclaration[] arrays) {
  if(arrays==null)return null;var result=new List<ClassicalArrayAllocation>();
  foreach(var array in arrays)result.Add(new ClassicalArrayAllocation(array.Base,array.Dimensions,
   array.Signedness==null ? null : ClassicalIntegerType.Create(Named<ClassicalIntegerType.Sign>(array.Signedness),array.Width),
   array.NumericKind==null ? null : NumericType(array.NumericKind,array.Width)));
  return result.ToArray();
 }
 static ClassicalArraySelection ConvertSelection(ArraySelectionNode node) {
  var indices=new List<ClassicalIntegerExpression>();foreach(var index in node.Indices)indices.Add(ConvertInteger(index));
  return new ClassicalArraySelection(node.Array,indices,node.Source);
 }
 static void SelectionFields(object value,int depth,ref int count,int version) {
  if(version<15)throw Invalid("Arrays require circuit version 15.");
  if(depth>=32 || ++count>512)throw Invalid("Array selection exceeds expression bounds.");
  var fields=Fields(value,"Array,Indices,Source");Integer(Required(fields,"Array"));
  if(!(Required(fields,"Source") is string))throw Invalid("Array source must be text.");
  var indices=ArrayValue(Required(fields,"Indices"));if(indices.Length<1 || indices.Length>7)throw Invalid("Array selection needs one to seven indices.");
  foreach(var index in indices)ExpressionFields(index,depth+1,ref count,version,true);
 }
 static void ExpressionFields(object value,int depth,ref int count,int version,bool integer=false) {
  if(depth>=32 || ++count>512)throw Invalid("Classical expressions allow 32 levels and 512 nodes.");
  var fields=Fields(value,"Kind,Width,Value,Bits,Operator,Left,Right,RotationDirection,DistanceInterpretation,Signedness,Slot,RealLeft,RealRight,Selection");
  var kind=Required(fields,"Kind") as string;string permitted;
  if(integer) {
   if(version<4)throw Invalid("Typed integer expressions require circuit version 4.");
   if(kind=="IntegerArrayElement" || kind=="IntegerArrayExtent") {
    permitted="Kind,Signedness,Width,Selection";Integer(Required(fields,"Width"));if(!(Required(fields,"Signedness") is string))throw Invalid("Array signedness must be text.");
    SelectionFields(Required(fields,"Selection"),depth+1,ref count,version);
   } else if(kind=="NumericCast" || kind=="AngleRatio" || kind=="AngleBits" || kind=="NumericCompare") {
    if(version<13)throw Invalid("Numeric integer operands require circuit version 13.");
    permitted="Kind,RealLeft";
    if(kind=="NumericCast") {permitted+=",Signedness,Width";Integer(Required(fields,"Width"));if(!(Required(fields,"Signedness") is string))throw Invalid("Integer signedness must be text.");}
    RealFields(Required(fields,"RealLeft"),depth+1,ref count,version);
    if(kind=="AngleRatio" || kind=="NumericCompare"){permitted+=",RealRight";RealFields(Required(fields,"RealRight"),depth+1,ref count,version);}
   } else if(kind=="IntegerConstant" || kind=="IntegerRead" || kind=="IntegerCast" || kind=="IntegerVariable" || kind=="IntegerFromBits") {
    if(!(Required(fields,"Signedness") is string))throw Invalid("Integer signedness must be a name.");
    Integer(Required(fields,"Width"));
    permitted="Kind,Signedness,Width,"+(kind=="IntegerConstant" ? "Value" : kind=="IntegerRead" ? "Bits" : kind=="IntegerVariable" ? "Slot" : "Left");
    if(kind=="IntegerConstant" && !(Required(fields,"Value") is string))throw Invalid("Integer values must be raw unsigned decimal text.");
    if(kind=="IntegerVariable"){if(version<5)throw Invalid("Variables require circuit version 5.");Integer(Required(fields,"Slot"));}
    if(kind=="IntegerRead")IntegerArray(Required(fields,"Bits"));
    if(kind=="IntegerFromBits"){if(version<6)throw Invalid("Computed bit casts require circuit version 6.");ExpressionFields(Required(fields,"Left"),depth+1,ref count,version);}
    if(kind=="IntegerCast")ExpressionFields(Required(fields,"Left"),depth+1,ref count,version,true);
   } else if(kind=="IntegerBinary") {
    permitted="Kind,Operator,Left,Right";if(!(Required(fields,"Operator") is string))throw Invalid("An integer operator must be a name.");
    ExpressionFields(Required(fields,"Left"),depth+1,ref count,version,true);ExpressionFields(Required(fields,"Right"),depth+1,ref count,version,true);
   } else throw Invalid("Expected a typed integer expression.");
  }
  else if(kind=="IntegerBits") {
   if(version<4)throw Invalid("Integer bit casts require circuit version 4.");
   permitted="Kind,Left";ExpressionFields(Required(fields,"Left"),depth+1,ref count,version,true);
  }
  else if(kind=="IntegerCompare") {
   if(version<4)throw Invalid("Typed integer conditions require circuit version 4.");
   permitted="Kind,Operator,Left,Right";if(!(Required(fields,"Operator") is string))throw Invalid("A comparison must be a name.");
   ExpressionFields(Required(fields,"Left"),depth+1,ref count,version,true);ExpressionFields(Required(fields,"Right"),depth+1,ref count,version,true);
  }
  else if(kind=="Constant") {permitted="Kind,Width,Value";Integer(Required(fields,"Width"));if(!(Required(fields,"Value") is string))throw Invalid("A constant value must be unsigned decimal text.");}
  else if(kind=="Read") {permitted="Kind,Bits";IntegerArray(Required(fields,"Bits"));}
  else if(kind=="Complement" || kind=="PopulationCount") {permitted="Kind,Left";ExpressionFields(Required(fields,"Left"),depth+1,ref count,version);}
  else if(kind=="Binary" || kind=="Logical") {if(kind=="Logical" && version<4)throw Invalid("Logical conditions require circuit version 4.");permitted="Kind,Operator,Left,Right";if(!(Required(fields,"Operator") is string))throw Invalid("A classical operator must be a name.");ExpressionFields(Required(fields,"Left"),depth+1,ref count,version);ExpressionFields(Required(fields,"Right"),depth+1,ref count,version);}
  else if(kind=="Rotate") {
   permitted="Kind,RotationDirection,DistanceInterpretation,Left,Right";
   if(!(Required(fields,"RotationDirection") is string) || !(Required(fields,"DistanceInterpretation") is string))throw Invalid("Rotation direction and distance interpretation must be names.");
   ExpressionFields(Required(fields,"Left"),depth+1,ref count,version);ExpressionFields(Required(fields,"Right"),depth+1,ref count,version);
  }
  else throw Invalid("Unknown classical expression kind.");
  var allowed=new HashSet<string>(permitted.Split(','),StringComparer.Ordinal);
  foreach(var field in fields)if(field.Value!=null && !allowed.Contains(field.Key))throw Invalid("Unexpected field for classical expression: "+field.Key);
 }
 internal static void ValidateIntegerExpression(ExpressionNode node,Document context) {
  var definitions=From(new Document {Version=context.Version,LoopConditionBudget=context.LoopConditionBudget,Qubits=0,Registers=context.Registers,Variables=context.Variables,NumericVariables=context.NumericVariables,Arrays=context.Arrays,OutputBits=new int[0],Steps=new Step[0]});
  int nodes=0;ExpressionFields(Serializer().DeserializeObject(Serializer().Serialize(node)),0,ref nodes,Math.Max(4,context.Version),true);
  ConvertInteger(node).Validate(definitions.ClassicalBits,definitions.Declarations);
 }
 static ClassicalIntegerExpression ConvertInteger(ExpressionNode node) {
  if(node.Kind=="AngleRatio")return ClassicalIntegerExpression.AngleRatio(ConvertReal(node.RealLeft),ConvertReal(node.RealRight));
  if(node.Kind=="AngleBits")return ClassicalIntegerExpression.AngleBits(ConvertReal(node.RealLeft));
  if(node.Kind=="NumericCompare")return ClassicalIntegerExpression.NumericCompare(ConvertReal(node.RealLeft),ConvertReal(node.RealRight));
  if(node.Kind=="IntegerBinary") {
   ClassicalIntegerExpression.Operator op;
   if(!Enum.TryParse(node.Operator,out op) || op.ToString()!=node.Operator || !Enum.IsDefined(typeof(ClassicalIntegerExpression.Operator),op))throw Invalid("Unknown integer operator.");
   return ClassicalIntegerExpression.Binary(op,ConvertInteger(node.Left),ConvertInteger(node.Right));
  }
  ClassicalIntegerType.Sign sign;
  if(!Enum.TryParse(node.Signedness,out sign) || sign.ToString()!=node.Signedness || !Enum.IsDefined(typeof(ClassicalIntegerType.Sign),sign))throw Invalid("Unknown integer signedness.");
  var type=ClassicalIntegerType.Create(sign,node.Width.Value);
  if(node.Kind=="IntegerArrayExtent") {if(type.Signedness!=ClassicalIntegerType.Sign.Signed || type.DeclaredWidth!=0)throw Invalid("Array extent requires a machine signed integer.");return ClassicalIntegerExpression.ArrayExtent(ConvertSelection(node.Selection));}
  if(node.Kind=="IntegerArrayElement")return ClassicalIntegerExpression.ArrayElement(type,ConvertSelection(node.Selection));
  if(node.Kind=="NumericCast")return ClassicalIntegerExpression.FromNumeric(type,ConvertReal(node.RealLeft));
  if(node.Kind=="IntegerConstant")return ClassicalIntegerExpression.Constant(type,Condition(node.Value));
  if(node.Kind=="IntegerVariable")return ClassicalIntegerExpression.Variable(type,node.Slot.Value);
  if(node.Kind=="IntegerRead")return ClassicalIntegerExpression.Read(type,node.Bits);
  if(node.Kind=="IntegerFromBits")return ClassicalIntegerExpression.FromBits(type,ConvertExpression(node.Left));
  return ClassicalIntegerExpression.Cast(type,ConvertInteger(node.Left));
 }
 static ClassicalExpression ConvertExpression(ExpressionNode node) {
  if(node==null)throw Invalid("A classical expression is required.");
  if(node.Kind=="IntegerBits")return ClassicalExpression.FromInteger(ConvertInteger(node.Left));
  if(node.Kind=="Constant")return ClassicalExpression.Constant(node.Width.Value,Condition(node.Value));
  if(node.Kind=="Read")return ClassicalExpression.Read(node.Bits);
  if(node.Kind=="Complement")return ClassicalExpression.Complement(ConvertExpression(node.Left));
  if(node.Kind=="PopulationCount")return ClassicalExpression.PopulationCount(ConvertExpression(node.Left));
  if(node.Kind=="Rotate") {
   ClassicalExpression.Direction direction;ClassicalExpression.Distance interpretation;
   if(!Enum.TryParse(node.RotationDirection,out direction) || direction.ToString()!=node.RotationDirection || !Enum.IsDefined(typeof(ClassicalExpression.Direction),direction))throw Invalid("Unknown rotation direction.");
   if(!Enum.TryParse(node.DistanceInterpretation,out interpretation) || interpretation.ToString()!=node.DistanceInterpretation || !Enum.IsDefined(typeof(ClassicalExpression.Distance),interpretation))throw Invalid("Unknown distance interpretation.");
   return ClassicalExpression.Rotate(direction,ConvertExpression(node.Left),ConvertExpression(node.Right),interpretation);
  }
  ClassicalExpression.Operator operation;
  if(!Enum.TryParse(node.Operator,out operation) || operation.ToString()!=node.Operator || !Enum.IsDefined(typeof(ClassicalExpression.Operator),operation))throw Invalid("Unknown classical expression operator.");
  if(node.Kind=="IntegerCompare")return ClassicalExpression.IntegerCompare(operation,ConvertInteger(node.Left),ConvertInteger(node.Right));
  if(node.Kind=="Logical")return ClassicalExpression.Logical(operation,ConvertExpression(node.Left),ConvertExpression(node.Right));
  return ClassicalExpression.Binary(operation,ConvertExpression(node.Left),ConvertExpression(node.Right));
 }
 static void RealFields(object value,int depth,ref int count,int version) {
  if(version<11)throw Invalid("Runtime angles require circuit version 11.");
  if(depth>=32 || ++count>512)throw Invalid("Real expressions allow 32 levels and 512 nodes.");
  var fields=Fields(value,"Kind,ValueBits,Operator,IntegerValue,Left,Right,NumericKind,Width,Slot,Function,Scaling,BitValue,Selection");
  var kind=Required(fields,"Kind") as string;string permitted;
  if(kind=="ArrayElement") {
   permitted="Kind,NumericKind,Width,Selection";Integer(Required(fields,"Width"));if(!(Required(fields,"NumericKind") is string))throw Invalid("Array numeric kind must be text.");
   SelectionFields(Required(fields,"Selection"),depth+1,ref count,version);
  } else if(kind=="TypedConstant" || kind=="Variable" || kind=="Cast" || kind=="Function" || kind=="Scale" || kind=="Bits" || kind=="TypedInteger") {
   if(version<13)throw Invalid("Typed numeric expressions require circuit version 13.");
   permitted="Kind";
   if(kind=="TypedConstant" || kind=="Variable" || kind=="Cast") {
    permitted+=",NumericKind,Width";Integer(Required(fields,"Width"));if(!(Required(fields,"NumericKind") is string))throw Invalid("Numeric kind must be text.");
   }
   if(kind=="TypedConstant"){permitted+=",ValueBits";if(!(Required(fields,"ValueBits") is string))throw Invalid("Numeric bits must be unsigned decimal text.");}
   if(kind=="Variable"){permitted+=",Slot";Integer(Required(fields,"Slot"));}
   if(kind=="Cast" || kind=="Function" || kind=="Scale"){permitted+=",Left";RealFields(Required(fields,"Left"),depth+1,ref count,version);}
   if(kind=="Function" || kind=="Scale"){string field=kind=="Function" ? "Function" : "Scaling";permitted+=","+field;if(!(Required(fields,field) is string))throw Invalid("Numeric operation must be a name.");}
   if(kind=="TypedInteger" || kind=="Bits"){permitted+=",Width";Integer(Required(fields,"Width"));}
   if(kind=="TypedInteger" || kind=="Scale"){permitted+=",IntegerValue";ExpressionFields(Required(fields,"IntegerValue"),depth+1,ref count,version,true);}
   if(kind=="Bits"){permitted+=",BitValue";ExpressionFields(Required(fields,"BitValue"),depth+1,ref count,version);}
  } else if(kind=="Constant") {
   permitted="Kind,ValueBits";
   if(!(Required(fields,"ValueBits") is string))throw Invalid("Real constant bits must be unsigned decimal text.");
  } else if(kind=="Integer") {
   permitted="Kind,IntegerValue";ExpressionFields(Required(fields,"IntegerValue"),depth+1,ref count,version,true);
  } else if(kind=="Binary") {
   permitted="Kind,Operator,Left,Right";
   if(!(Required(fields,"Operator") is string))throw Invalid("A real operator must be a name.");
   if(version<13 && (string)fields["Operator"]!="Add" && (string)fields["Operator"]!="Subtract" && (string)fields["Operator"]!="Multiply" && (string)fields["Operator"]!="Divide")throw Invalid("Numeric operators require version 13.");
   RealFields(Required(fields,"Left"),depth+1,ref count,version);RealFields(Required(fields,"Right"),depth+1,ref count,version);
  } else throw Invalid("Unknown real expression kind.");
  var allowed=new HashSet<string>(permitted.Split(','),StringComparer.Ordinal);
  foreach(var field in fields)if(field.Value!=null && !allowed.Contains(field.Key))throw Invalid("Unexpected real expression field: "+field.Key);
 }
 static T Named<T>(string name) where T:struct {
  T value;if(!Enum.TryParse(name,out value) || value.ToString()!=name || !Enum.IsDefined(typeof(T),value))throw Invalid("Unknown "+typeof(T).Name+".");return value;
 }
 static ClassicalNumericType NumericType(string kind,int width){return ClassicalNumericType.Create(Named<ClassicalNumericType.NumericKind>(kind),width);}
 static ClassicalNumericType[] NumericTypesOf(NumericVariable[] variables) {
  if(variables==null)return null;var types=new ClassicalNumericType[variables.Length];
  for(int i=0;i<types.Length;i++)types[i]=NumericType(variables[i].NumericKind,variables[i].Width);return types;
 }
 static ClassicalRealExpression ConvertReal(RealNode node) {
  if(node.Kind=="ArrayElement")return ClassicalRealExpression.ArrayElement(NumericType(node.NumericKind,node.Width.Value),ConvertSelection(node.Selection));
  if(node.Kind=="TypedConstant")return ClassicalRealExpression.TypedConstant(NumericType(node.NumericKind,node.Width.Value),Condition(node.ValueBits));
  if(node.Kind=="Variable")return ClassicalRealExpression.Variable(NumericType(node.NumericKind,node.Width.Value),node.Slot.Value);
  if(node.Kind=="Cast")return ClassicalRealExpression.Cast(NumericType(node.NumericKind,node.Width.Value),ConvertReal(node.Left));
  if(node.Kind=="Function")return ClassicalRealExpression.Function(Named<ClassicalRealExpression.FunctionKind>(node.Function),ConvertReal(node.Left));
  if(node.Kind=="Scale")return ClassicalRealExpression.Scale(Named<ClassicalRealExpression.Scaling>(node.Scaling),ConvertReal(node.Left),ConvertInteger(node.IntegerValue));
  if(node.Kind=="Bits")return ClassicalRealExpression.FromBits(node.Width.Value,ConvertExpression(node.BitValue));
  if(node.Kind=="TypedInteger")return ClassicalRealExpression.FromInteger(ConvertInteger(node.IntegerValue),node.Width.Value);
  if(node.Kind=="Constant") {
   ulong raw;if(!UInt64.TryParse(node.ValueBits,NumberStyles.None,CultureInfo.InvariantCulture,out raw))throw Invalid("Invalid binary64 constant bits.");
   return ClassicalRealExpression.Constant(BitConverter.Int64BitsToDouble(unchecked((long)raw)));
  }
  if(node.Kind=="Integer")return ClassicalRealExpression.FromInteger(ConvertInteger(node.IntegerValue));
  ClassicalRealExpression.Operator operation;
  if(!Enum.TryParse(node.Operator,out operation) || operation.ToString()!=node.Operator || !Enum.IsDefined(typeof(ClassicalRealExpression.Operator),operation))throw Invalid("Unknown real operator.");
  return ClassicalRealExpression.Binary(operation,ConvertReal(node.Left),ConvertReal(node.Right));
 }
 static void StepFields(object value,int depth,ref int count,int version) {
  foreach(object item in ArrayValue(value)) {
   if(++count>512 || depth>32)throw Invalid("Use at most 512 steps and 32 nested branches.");
   var fields=Fields(item,"Kind,Expression,Wires,ClassicalBit,Mask,Value,WhenTrue,WhenFalse,ClassicalValue,VariableSlot,IntegerValue,Range,Axis,Angle,ParameterGate,NumericValue,WireTargets,WireSource,ArrayTarget");
   if(fields.ContainsKey("ArrayTarget") && fields["ArrayTarget"]!=null){int nodes=0;SelectionFields(fields["ArrayTarget"],0,ref nodes,version);}
   if(fields.ContainsKey("WireTargets") && fields["WireTargets"]!=null) {
    if(version<14)throw Invalid("Runtime wire targets require circuit version 14.");
    var targets=ArrayValue(fields["WireTargets"]);if(targets.Length<1 || targets.Length>3)throw Invalid("Use 1–3 runtime wire targets.");
    if(!(Required(fields,"WireSource") is string))throw Invalid("Runtime wires require source context.");
    foreach(var itemTarget in targets){var target=Fields(itemTarget,"Candidates,Index");IntegerArray(Required(target,"Candidates"));int nodes=0;ExpressionFields(Required(target,"Index"),0,ref nodes,version,true);}
   } else if(fields.ContainsKey("WireSource") && fields["WireSource"]!=null)throw Invalid("Wire source context requires runtime wire targets.");
   if(fields.ContainsKey("ParameterGate") && fields["ParameterGate"]!=null) {
    if(version<12)throw Invalid("Parameterized gates require circuit version 12.");
    var parameter=Fields(fields["ParameterGate"],"Gate,Controls,ControlState,Parameters,Power");
    if(!(Required(parameter,"Gate") is string) || !(Required(parameter,"ControlState") is string))throw Invalid("Runtime gate name and control state must be text.");
    Integer(Required(parameter,"Controls"));
    var angles=ArrayValue(Required(parameter,"Parameters"));if(angles.Length>3)throw Invalid("Runtime gates have at most three parameters.");
    foreach(var angle in angles){int nodes=0;RealFields(angle,0,ref nodes,version);}
    int powerNodes=0;ExpressionFields(Required(parameter,"Power"),0,ref powerNodes,version,true);
   }
   if(fields.ContainsKey("NumericValue") && fields["NumericValue"]!=null){if(version<13)throw Invalid("Numeric stores require version 13.");int nodes=0;RealFields(fields["NumericValue"],0,ref nodes,version);}
   if(fields.ContainsKey("Axis") && fields["Axis"]!=null) {
    if(version<11 || !(fields["Axis"] is string))throw Invalid("Runtime rotation axes require version 11 and a name.");
   }
   if(fields.ContainsKey("Angle") && fields["Angle"]!=null) {int nodes=0;RealFields(fields["Angle"],0,ref nodes,version);}
   if(!(Required(fields,"Kind") is string))throw Invalid("A step kind must be a name.");
   foreach(string name in new[]{"Expression","Mask","Value"})if(fields.ContainsKey(name) && fields[name]!=null && !(fields[name] is string))throw Invalid(name+" must be text.");
   if(fields.ContainsKey("Wires") && fields["Wires"]!=null)IntegerArray(fields["Wires"]);
   if(fields.ContainsKey("ClassicalBit") && fields["ClassicalBit"]!=null)Integer(fields["ClassicalBit"]);
   if(fields.ContainsKey("ClassicalValue") && fields["ClassicalValue"]!=null) {
    if(version<3)throw Invalid("Classical expressions require circuit version 3 or 4.");
    int nodes=0;ExpressionFields(fields["ClassicalValue"],0,ref nodes,version);
   }
   if(fields.ContainsKey("VariableSlot") && fields["VariableSlot"]!=null) {
    if(version<5)throw Invalid("Variables require circuit version 5.");Integer(fields["VariableSlot"]);
   }
   if(fields.ContainsKey("IntegerValue") && fields["IntegerValue"]!=null) {
    if(version<5)throw Invalid("Variables require circuit version 5.");int nodes=0;ExpressionFields(fields["IntegerValue"],0,ref nodes,version,true);
   }
   if(fields.ContainsKey("Range") && fields["Range"]!=null) {
    if(version<10)throw Invalid("Runtime ranges require circuit version 10.");
    var range=Fields(fields["Range"],"Start,Stop,Step");
    foreach(string name in new[]{"Start","Stop","Step"}) {int nodes=0;ExpressionFields(Required(range,name),0,ref nodes,version,true);}
   }
   foreach(string name in new[]{"WhenTrue","WhenFalse"})if(fields.ContainsKey(name) && fields[name]!=null)StepFields(fields[name],depth+1,ref count,version);
  }
 }
 public static ClassicalCircuit Load(string text) {
  if(text==null || text.Length>MaxBytes || Encoding.UTF8.GetByteCount(text)>MaxBytes)throw Invalid("Circuit data exceeds 256 KiB.");
  var serializer=Serializer();var root=Fields(serializer.DeserializeObject(text),"Version,Qubits,Registers,OutputBits,Steps,Variables,LoopConditionBudget,NumericVariables,Arrays");
  Integer(Required(root,"Version"));Integer(Required(root,"Qubits"));IntegerArray(Required(root,"OutputBits"));
  foreach(object item in ArrayValue(Required(root,"Registers"))) {
   var fields=Fields(item,"Name,Size");if(!(Required(fields,"Name") is string))throw Invalid("A register name must be text.");Integer(Required(fields,"Size"));
  }
  int version=(int)root["Version"];
  if(version<2 || version>15)throw Invalid("Expected a version 2 through 15 classical circuit.");
  object loopBudget;
  if(version>=7) {
   loopBudget=Required(root,"LoopConditionBudget");Integer(loopBudget);
   if((int)loopBudget<0 || (int)loopBudget>1000000)throw Invalid("Loop condition budget must be 0–1,000,000.");
  } else if(root.TryGetValue("LoopConditionBudget",out loopBudget) && loopBudget!=null)throw Invalid("Loop budgets require circuit version 7.");
  object declarations;
  if(root.TryGetValue("Variables",out declarations) && declarations!=null) {
   if(version<5)throw Invalid("Variables require circuit version 5.");
   var variables=ArrayValue(declarations);if(variables.Length>4096)throw Invalid("Use at most 4096 variables.");
   foreach(var variable in variables) {
    var fields=Fields(variable,"Name,Signedness,Width");
    if(!(Required(fields,"Name") is string) || !(Required(fields,"Signedness") is string))throw Invalid("Variable names and signedness must be text.");
    Integer(Required(fields,"Width"));
   }
  } else if(version>=5)throw Invalid("Versions 5–11 require a variable declaration array.");
  object numericDeclarations;
  if(root.TryGetValue("NumericVariables",out numericDeclarations) && numericDeclarations!=null) {
   if(version<13)throw Invalid("Numeric variables require version 13.");
   var numeric=ArrayValue(numericDeclarations);if(numeric.Length>4096)throw Invalid("Use at most 4096 numeric slots.");
   foreach(var item in numeric){var fields=Fields(item,"Name,NumericKind,Width");if(!(Required(fields,"Name") is string) || !(Required(fields,"NumericKind") is string))throw Invalid("Numeric names/types must be text.");Integer(Required(fields,"Width"));}
  } else if(version>=13)throw Invalid("Version 13 requires numeric declarations.");
  object arrayDeclarations;
  if(root.TryGetValue("Arrays",out arrayDeclarations) && arrayDeclarations!=null) {
   if(version<15)throw Invalid("Arrays require version 15.");
   var arrays=ArrayValue(arrayDeclarations);if(arrays.Length>4096)throw Invalid("Use at most 4096 arrays.");
   foreach(var item in arrays) {
    var fields=Fields(item,"Name,Base,Dimensions,Signedness,NumericKind,Width");
    if(!(Required(fields,"Name") is string))throw Invalid("Array name must be text.");Integer(Required(fields,"Base"));IntegerArray(Required(fields,"Dimensions"));Integer(Required(fields,"Width"));
    object sign,numeric;bool hasSign=fields.TryGetValue("Signedness",out sign) && sign!=null,hasNumeric=fields.TryGetValue("NumericKind",out numeric) && numeric!=null;
    if(hasSign==hasNumeric || (hasSign && !(sign is string)) || (hasNumeric && !(numeric is string)))throw Invalid("Array requires exactly one element type.");
   }
  } else if(version>=15)throw Invalid("Version 15 requires array declarations.");
  int count=0;StepFields(Required(root,"Steps"),0,ref count,version);
  var value=serializer.ConvertToType<Document>(root);
  var names=new HashSet<string>(StringComparer.Ordinal);int bits=0;
  foreach(var register in value.Registers) {
   if(String.IsNullOrWhiteSpace(register.Name) || register.Name.Length>64 || register.Name!=register.Name.Trim() || !names.Add(register.Name))throw Invalid("Register names must be distinct, nonempty and at most 64 characters.");
   foreach(char c in register.Name)if(Char.IsControl(c))throw Invalid("Register names cannot contain control characters.");
   if(register.Size<1 || register.Size>64-bits)throw Invalid("Registers must contain 1–64 bits, with at most 64 bits total.");
   bits+=register.Size;
  }
  if(value.Variables!=null)foreach(var variable in value.Variables) {
   if(String.IsNullOrWhiteSpace(variable.Name) || variable.Name.Length>64 || variable.Name!=variable.Name.Trim() || !names.Add(variable.Name))throw Invalid("Variable and register names must be distinct and at most 64 characters.");
   foreach(char c in variable.Name)if(Char.IsControl(c))throw Invalid("Variable names cannot contain control characters.");
  }
  if(value.NumericVariables!=null)foreach(var variable in value.NumericVariables) {
   if(String.IsNullOrWhiteSpace(variable.Name) || variable.Name.Length>64 || variable.Name!=variable.Name.Trim() || !names.Add(variable.Name))throw Invalid("Variable and register names must be distinct and at most 64 characters.");
   foreach(char ch in variable.Name)if(Char.IsControl(ch))throw Invalid("Variable names cannot contain control characters.");
  }
  if(value.Arrays!=null)foreach(var array in value.Arrays) {
   if(String.IsNullOrWhiteSpace(array.Name) || array.Name.Length>64 || array.Name!=array.Name.Trim() || !names.Add(array.Name))throw Invalid("Array names must be distinct and at most 64 characters.");
   foreach(char ch in array.Name)if(Char.IsControl(ch))throw Invalid("Array names cannot contain control characters.");
  }
  var types=Types(value.Variables);
  var gates=ConvertSteps(value.Steps,version);
  // Reuse the worker adapter's bounds, destinations, masks and payload checks.
  NumericalSampling.RequestClassical(value.Qubits,bits,1,0,value.OutputBits,gates,types,value.LoopConditionBudget,NumericTypesOf(value.NumericVariables),Allocations(value.Arrays));
  string canonical=SerializeDocument(value);
  if(Encoding.UTF8.GetByteCount(canonical)>MaxBytes)throw Invalid("Canonical circuit data exceeds 256 KiB.");
  return new ClassicalCircuit(value,canonical,bits);
 }
 // JavaScriptSerializer may cache DTO property order differently after reads.
 // Use deterministic ordinal order for every supported circuit version.
 // Keep the added field last, and omit it entirely on legacy expression nodes.
 static object CanonicalFields(object value) {
  var fields=value as Dictionary<string,object>;
  if(fields!=null) {
   var result=new Dictionary<string,object>();
   var ordered=new SortedDictionary<string,object>(fields,StringComparer.Ordinal);
   foreach(var field in ordered)if(field.Key!="Signedness" && !(field.Value==null && (field.Key=="Arrays" || field.Key=="Selection" || field.Key=="ArrayTarget" || field.Key=="WireTargets" || field.Key=="WireSource" || field.Key=="NumericVariables" || field.Key=="NumericValue" || field.Key=="NumericKind" || field.Key=="Function" || field.Key=="Scaling" || field.Key=="BitValue" || field.Key=="RealLeft" || field.Key=="RealRight" || field.Key=="Variables" || field.Key=="Width" || field.Key=="Slot" || field.Key=="VariableSlot" || field.Key=="IntegerValue" || field.Key=="LoopConditionBudget" || field.Key=="Range" || field.Key=="Axis" || field.Key=="Angle")))result.Add(field.Key,CanonicalFields(field.Value));
   object sign;if(fields.TryGetValue("Signedness",out sign) && sign!=null)result.Add("Signedness",sign);
   return result;
  }
  var array=value as object[];
  if(array!=null){var result=new object[array.Length];for(int i=0;i<array.Length;i++)result[i]=CanonicalFields(array[i]);return result;}
  return value;
 }
 static ClassicalIntegerType[] Types(Variable[] variables) {
  if(variables==null)return null;
  var result=new ClassicalIntegerType[variables.Length];
  for(int k=0;k<variables.Length;++k) {
   ClassicalIntegerType.Sign sign;
   if(!Enum.TryParse(variables[k].Signedness,out sign) || sign.ToString()!=variables[k].Signedness || !Enum.IsDefined(typeof(ClassicalIntegerType.Sign),sign))throw Invalid("Unknown variable signedness.");
   result[k]=ClassicalIntegerType.Create(sign,variables[k].Width);
  }
  return result;
 }
 static ulong Condition(string text) {
  ulong result;if(text==null || !UInt64.TryParse(text,NumberStyles.None,CultureInfo.InvariantCulture,out result))throw Invalid("A condition mask and value must be unsigned decimal strings.");return result;
 }
 static List<NumericalSampling.Gate> ConvertSteps(Step[] steps,int version) {
  var result=new List<NumericalSampling.Gate>();
  foreach(var step in steps) {
   NumericalSampling.Operation kind;
   if(!Enum.TryParse(step.Kind,out kind) || kind.ToString()!=step.Kind || !Enum.IsDefined(typeof(NumericalSampling.Operation),kind))throw Invalid("Unknown operation kind.");
   if((kind==NumericalSampling.Operation.Break || kind==NumericalSampling.Operation.Continue) && version<8)throw Invalid("Loop transfers require circuit version 8.");
   if(kind==NumericalSampling.Operation.End && version<9)throw Invalid("Program termination requires circuit version 9.");
   bool range=kind==NumericalSampling.Operation.ForRange;
   if(range && version<10)throw Invalid("Runtime ranges require circuit version 10.");
   if(range!=(step.Range!=null))throw Invalid("Only range loops require a Range object.");
   bool numeric=kind==NumericalSampling.Operation.StoreNumeric || kind==NumericalSampling.Operation.ClearNumeric;
   if(numeric && version<13)throw Invalid("Numeric stores require version 13.");
   if(!numeric && step.NumericValue!=null)throw Invalid("Only numeric stores accept numeric values.");
   bool integer=kind==NumericalSampling.Operation.StoreInteger || kind==NumericalSampling.Operation.ClearInteger;
   if(integer && version<5)throw Invalid("Variables require circuit version 5.");
   if((!integer && step.IntegerValue!=null) || (!integer && !range && !numeric && step.VariableSlot.HasValue))throw Invalid("Only variable operations accept integer values; variables and ranges accept target slots.");
   bool loop=kind==NumericalSampling.Operation.While;
   if(loop && version<7)throw Invalid("Runtime loops require circuit version 7.");
   bool expression=kind==NumericalSampling.Operation.Assign || kind==NumericalSampling.Operation.ExpressionBranch || loop;
   if(expression && version<3)throw Invalid("Classical expressions require circuit version 3 or 4.");
   if(!expression && step.ClassicalValue!=null)throw Invalid("Only assignments and expression branches have classical expressions.");
   bool condition=kind==NumericalSampling.Operation.Conditional || kind==NumericalSampling.Operation.Branch;
   if(!condition && (step.Mask!=null || step.Value!=null))throw Invalid("Only conditions have a mask and value.");
   if((kind==NumericalSampling.Operation.Measure || kind==NumericalSampling.Operation.Reset) && !String.IsNullOrEmpty(step.Expression))throw Invalid("Measurement and reset cannot contain matrix expressions.");
   var gate=new NumericalSampling.Gate {Kind=kind,Expression=step.Expression,Wires=step.Wires==null ? null : (int[])step.Wires.Clone(),ClassicalBit=step.ClassicalBit};
   if(step.ArrayTarget!=null) {
    if(version<15 || (kind!=NumericalSampling.Operation.StoreInteger && kind!=NumericalSampling.Operation.StoreNumeric))throw Invalid("Only version 15 stores accept array targets.");
    gate.ArrayTarget=ConvertSelection(step.ArrayTarget);
   }
   if(step.WireTargets!=null) {
    var targets=new List<NumericalSampling.WireTarget>();
    foreach(var target in step.WireTargets)targets.Add(new NumericalSampling.WireTarget(target.Candidates,ConvertInteger(target.Index)));
    gate.SelectedWires=new NumericalSampling.WireSelection(targets,step.WireSource);
   }
   bool rotation=kind==NumericalSampling.Operation.Rotation;
   if(rotation) {
    if(version<11 || step.Axis==null || step.Angle==null)throw Invalid("Runtime rotations require version 11, an axis and an angle.");
    NumericalSampling.RotationAxis axis;
    if(!Enum.TryParse(step.Axis,out axis) || axis.ToString()!=step.Axis || !Enum.IsDefined(typeof(NumericalSampling.RotationAxis),axis))throw Invalid("Unknown runtime rotation axis.");
    gate.Axis=axis;gate.Angle=ConvertReal(step.Angle);
   } else if(step.Axis!=null || step.Angle!=null)throw Invalid("Only runtime rotations accept an axis and angle.");
   if(kind==NumericalSampling.Operation.ParameterGate) {
    if(version<12 || step.ParameterGate==null)throw Invalid("Parameterized gates require version 12 and a gate value.");
    var value=step.ParameterGate;NumericalSampling.ParameterGateKind gateKind;ulong controlState;
    if(!Enum.TryParse(value.Gate,out gateKind) || gateKind.ToString()!=value.Gate || !Enum.IsDefined(typeof(NumericalSampling.ParameterGateKind),gateKind))throw Invalid("Unknown runtime gate.");
    if(!UInt64.TryParse(value.ControlState,NumberStyles.None,CultureInfo.InvariantCulture,out controlState))throw Invalid("Invalid runtime control state.");
    var parameters=new List<ClassicalRealExpression>();foreach(var parameter in value.Parameters)parameters.Add(ConvertReal(parameter));
    gate.ParameterGate=new NumericalSampling.ParameterizedGate(gateKind,parameters,value.Controls,controlState,ConvertInteger(value.Power));
   } else if(step.ParameterGate!=null)throw Invalid("Only parameterized gates accept a runtime gate value.");
   if(numeric){gate.VariableSlot=step.VariableSlot;if(step.NumericValue!=null)gate.NumericExpression=ConvertReal(step.NumericValue);}
   if(integer){gate.VariableSlot=step.VariableSlot;if(step.IntegerValue!=null)gate.IntegerExpression=ConvertInteger(step.IntegerValue);}
   if(range){gate.VariableSlot=step.VariableSlot;gate.Range=new NumericalSampling.IntegerRange(ConvertInteger(step.Range.Start),ConvertInteger(step.Range.Stop),ConvertInteger(step.Range.Step));}
   if(expression)gate.ClassicalExpression=ConvertExpression(step.ClassicalValue);
   if(condition) {gate.Mask=Condition(step.Mask);gate.Value=Condition(step.Value);}
   if(step.WhenTrue!=null)gate.WhenTrue=ConvertSteps(step.WhenTrue,version);
   if(step.WhenFalse!=null)gate.WhenFalse=ConvertSteps(step.WhenFalse,version);
   result.Add(gate);
  }
  return result;
 }
 public List<NumericalSampling.Gate> SamplingGates() {return ConvertSteps(document.Steps,document.Version);}
}
