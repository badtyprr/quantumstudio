// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using System.Web.Script.Serialization;

// Version 2 stores saved records; version 3 adds bit expressions; version 4 adds typed integer conditions.
// The editor receives copies; a validated program cannot change underneath a run.
sealed class ClassicalCircuit {
 public sealed class Register {public string Name {get;set;}public int Size {get;set;}}
 public sealed class ExpressionNode {
  public string Signedness {get;set;}
  public string Kind {get;set;}public int? Width {get;set;}public string Value {get;set;}
  public int[] Bits {get;set;}public string Operator {get;set;}
  public string RotationDirection {get;set;}public string DistanceInterpretation {get;set;}
  public ExpressionNode Left {get;set;}public ExpressionNode Right {get;set;}
 }
 public sealed class Step {
  public string Kind {get;set;}public string Expression {get;set;}public int[] Wires {get;set;}
  public int? ClassicalBit {get;set;}public string Mask {get;set;}public string Value {get;set;}
  public Step[] WhenTrue {get;set;}public Step[] WhenFalse {get;set;}
  public ExpressionNode ClassicalValue {get;set;}
 }
 public sealed class Document {
  public int Version {get;set;}public int Qubits {get;set;}public Register[] Registers {get;set;}
  public int[] OutputBits {get;set;}public Step[] Steps {get;set;}
 }
 const int MaxBytes=262144;
 readonly Document document;readonly string json;readonly int classicalBits;
 static JavaScriptSerializer Serializer() {return new JavaScriptSerializer {MaxJsonLength=MaxBytes,RecursionLimit=128};}
 ClassicalCircuit(Document value,string text,int bits) {document=value;json=text;classicalBits=bits;}
 public int Qubits {get{return document.Qubits;}}
 public int ClassicalBits {get{return classicalBits;}}
 public int[] OutputBits {get{return (int[])document.OutputBits.Clone();}}
 public string Serialize() {return json;}
 public Document Snapshot() {return Serializer().Deserialize<Document>(json);}
 public static ClassicalCircuit From(Document value) {return Load(Serializer().Serialize(value));}
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
 static void ExpressionFields(object value,int depth,ref int count,int version,bool integer=false) {
  if(depth>=32 || ++count>512)throw Invalid("Classical expressions allow 32 levels and 512 nodes.");
  var fields=Fields(value,"Kind,Width,Value,Bits,Operator,Left,Right,RotationDirection,DistanceInterpretation,Signedness");
  var kind=Required(fields,"Kind") as string;string permitted;
  if(integer) {
   if(version!=4)throw Invalid("Typed integer expressions require circuit version 4.");
   if(kind=="IntegerConstant" || kind=="IntegerRead" || kind=="IntegerCast") {
    if(!(Required(fields,"Signedness") is string))throw Invalid("Integer signedness must be a name.");
    Integer(Required(fields,"Width"));
    permitted="Kind,Signedness,Width,"+(kind=="IntegerConstant" ? "Value" : kind=="IntegerRead" ? "Bits" : "Left");
    if(kind=="IntegerConstant" && !(Required(fields,"Value") is string))throw Invalid("Integer values must be raw unsigned decimal text.");
    if(kind=="IntegerRead")IntegerArray(Required(fields,"Bits"));
    if(kind=="IntegerCast")ExpressionFields(Required(fields,"Left"),depth+1,ref count,version,true);
   } else if(kind=="IntegerBinary") {
    permitted="Kind,Operator,Left,Right";if(!(Required(fields,"Operator") is string))throw Invalid("An integer operator must be a name.");
    ExpressionFields(Required(fields,"Left"),depth+1,ref count,version,true);ExpressionFields(Required(fields,"Right"),depth+1,ref count,version,true);
   } else throw Invalid("Expected a typed integer expression.");
  }
  else if(kind=="IntegerBits") {
   if(version!=4)throw Invalid("Integer bit casts require circuit version 4.");
   permitted="Kind,Left";ExpressionFields(Required(fields,"Left"),depth+1,ref count,version,true);
  }
  else if(kind=="IntegerCompare") {
   if(version!=4)throw Invalid("Typed integer conditions require circuit version 4.");
   permitted="Kind,Operator,Left,Right";if(!(Required(fields,"Operator") is string))throw Invalid("A comparison must be a name.");
   ExpressionFields(Required(fields,"Left"),depth+1,ref count,version,true);ExpressionFields(Required(fields,"Right"),depth+1,ref count,version,true);
  }
  else if(kind=="Constant") {permitted="Kind,Width,Value";Integer(Required(fields,"Width"));if(!(Required(fields,"Value") is string))throw Invalid("A constant value must be unsigned decimal text.");}
  else if(kind=="Read") {permitted="Kind,Bits";IntegerArray(Required(fields,"Bits"));}
  else if(kind=="Complement" || kind=="PopulationCount") {permitted="Kind,Left";ExpressionFields(Required(fields,"Left"),depth+1,ref count,version);}
  else if(kind=="Binary" || kind=="Logical") {if(kind=="Logical" && version!=4)throw Invalid("Logical conditions require circuit version 4.");permitted="Kind,Operator,Left,Right";if(!(Required(fields,"Operator") is string))throw Invalid("A classical operator must be a name.");ExpressionFields(Required(fields,"Left"),depth+1,ref count,version);ExpressionFields(Required(fields,"Right"),depth+1,ref count,version);}
  else if(kind=="Rotate") {
   permitted="Kind,RotationDirection,DistanceInterpretation,Left,Right";
   if(!(Required(fields,"RotationDirection") is string) || !(Required(fields,"DistanceInterpretation") is string))throw Invalid("Rotation direction and distance interpretation must be names.");
   ExpressionFields(Required(fields,"Left"),depth+1,ref count,version);ExpressionFields(Required(fields,"Right"),depth+1,ref count,version);
  }
  else throw Invalid("Unknown classical expression kind.");
  var allowed=new HashSet<string>(permitted.Split(','),StringComparer.Ordinal);
  foreach(var field in fields)if(field.Value!=null && !allowed.Contains(field.Key))throw Invalid("Unexpected field for classical expression: "+field.Key);
 }
 static ClassicalIntegerExpression ConvertInteger(ExpressionNode node) {
  if(node.Kind=="IntegerBinary") {
   ClassicalIntegerExpression.Operator op;
   if(!Enum.TryParse(node.Operator,out op) || op.ToString()!=node.Operator || !Enum.IsDefined(typeof(ClassicalIntegerExpression.Operator),op))throw Invalid("Unknown integer operator.");
   return ClassicalIntegerExpression.Binary(op,ConvertInteger(node.Left),ConvertInteger(node.Right));
  }
  ClassicalIntegerType.Sign sign;
  if(!Enum.TryParse(node.Signedness,out sign) || sign.ToString()!=node.Signedness || !Enum.IsDefined(typeof(ClassicalIntegerType.Sign),sign))throw Invalid("Unknown integer signedness.");
  var type=ClassicalIntegerType.Create(sign,node.Width.Value);
  if(node.Kind=="IntegerConstant")return ClassicalIntegerExpression.Constant(type,Condition(node.Value));
  if(node.Kind=="IntegerRead")return ClassicalIntegerExpression.Read(type,node.Bits);
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
 static void StepFields(object value,int depth,ref int count,int version) {
  foreach(object item in ArrayValue(value)) {
   if(++count>512 || depth>32)throw Invalid("Use at most 512 steps and 32 nested branches.");
   var fields=Fields(item,"Kind,Expression,Wires,ClassicalBit,Mask,Value,WhenTrue,WhenFalse,ClassicalValue");
   if(!(Required(fields,"Kind") is string))throw Invalid("A step kind must be a name.");
   foreach(string name in new[]{"Expression","Mask","Value"})if(fields.ContainsKey(name) && fields[name]!=null && !(fields[name] is string))throw Invalid(name+" must be text.");
   if(fields.ContainsKey("Wires") && fields["Wires"]!=null)IntegerArray(fields["Wires"]);
   if(fields.ContainsKey("ClassicalBit") && fields["ClassicalBit"]!=null)Integer(fields["ClassicalBit"]);
   if(fields.ContainsKey("ClassicalValue") && fields["ClassicalValue"]!=null) {
    if(version<3)throw Invalid("Classical expressions require circuit version 3 or 4.");
    int nodes=0;ExpressionFields(fields["ClassicalValue"],0,ref nodes,version);
   }
   foreach(string name in new[]{"WhenTrue","WhenFalse"})if(fields.ContainsKey(name) && fields[name]!=null)StepFields(fields[name],depth+1,ref count,version);
  }
 }
 public static ClassicalCircuit Load(string text) {
  if(text==null || text.Length>MaxBytes || Encoding.UTF8.GetByteCount(text)>MaxBytes)throw Invalid("Circuit data exceeds 256 KiB.");
  var serializer=Serializer();var root=Fields(serializer.DeserializeObject(text),"Version,Qubits,Registers,OutputBits,Steps");
  Integer(Required(root,"Version"));Integer(Required(root,"Qubits"));IntegerArray(Required(root,"OutputBits"));
  foreach(object item in ArrayValue(Required(root,"Registers"))) {
   var fields=Fields(item,"Name,Size");if(!(Required(fields,"Name") is string))throw Invalid("A register name must be text.");Integer(Required(fields,"Size"));
  }
  int version=(int)root["Version"];
  if(version!=2 && version!=3 && version!=4)throw Invalid("Expected a version 2, 3 or 4 classical circuit.");
  int count=0;StepFields(Required(root,"Steps"),0,ref count,version);
  var value=serializer.ConvertToType<Document>(root);
  var names=new HashSet<string>(StringComparer.Ordinal);int bits=0;
  foreach(var register in value.Registers) {
   if(String.IsNullOrWhiteSpace(register.Name) || register.Name.Length>64 || register.Name!=register.Name.Trim() || !names.Add(register.Name))throw Invalid("Register names must be distinct, nonempty and at most 64 characters.");
   foreach(char c in register.Name)if(Char.IsControl(c))throw Invalid("Register names cannot contain control characters.");
   if(register.Size<1 || register.Size>64-bits)throw Invalid("Registers must contain 1–64 bits, with at most 64 bits total.");
   bits+=register.Size;
  }
  var gates=ConvertSteps(value.Steps,version);
  // Reuse the worker adapter's bounds, destinations, masks and payload checks.
  NumericalSampling.RequestClassical(value.Qubits,bits,1,0,value.OutputBits,gates);
  var canonicalObject=serializer.DeserializeObject(serializer.Serialize(value));
  string canonical=serializer.Serialize(CanonicalFields(canonicalObject));
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
   foreach(var field in ordered)if(field.Key!="Signedness")result.Add(field.Key,CanonicalFields(field.Value));
   object sign;if(fields.TryGetValue("Signedness",out sign) && sign!=null)result.Add("Signedness",sign);
   return result;
  }
  var array=value as object[];
  if(array!=null){var result=new object[array.Length];for(int i=0;i<array.Length;i++)result[i]=CanonicalFields(array[i]);return result;}
  return value;
 }
 static ulong Condition(string text) {
  ulong result;if(text==null || !UInt64.TryParse(text,NumberStyles.None,CultureInfo.InvariantCulture,out result))throw Invalid("A condition mask and value must be unsigned decimal strings.");return result;
 }
 static List<NumericalSampling.Gate> ConvertSteps(Step[] steps,int version) {
  var result=new List<NumericalSampling.Gate>();
  foreach(var step in steps) {
   NumericalSampling.Operation kind;
   if(!Enum.TryParse(step.Kind,out kind) || kind.ToString()!=step.Kind || !Enum.IsDefined(typeof(NumericalSampling.Operation),kind))throw Invalid("Unknown operation kind.");
   bool expression=kind==NumericalSampling.Operation.Assign || kind==NumericalSampling.Operation.ExpressionBranch;
   if(expression && version<3)throw Invalid("Classical expressions require circuit version 3 or 4.");
   if(!expression && step.ClassicalValue!=null)throw Invalid("Only assignments and expression branches have classical expressions.");
   bool condition=kind==NumericalSampling.Operation.Conditional || kind==NumericalSampling.Operation.Branch;
   if(!condition && (step.Mask!=null || step.Value!=null))throw Invalid("Only conditions have a mask and value.");
   if((kind==NumericalSampling.Operation.Measure || kind==NumericalSampling.Operation.Reset) && !String.IsNullOrEmpty(step.Expression))throw Invalid("Measurement and reset cannot contain matrix expressions.");
   var gate=new NumericalSampling.Gate {Kind=kind,Expression=step.Expression,Wires=step.Wires==null ? null : (int[])step.Wires.Clone(),ClassicalBit=step.ClassicalBit};
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
