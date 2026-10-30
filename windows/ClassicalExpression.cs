// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;

// Immutable unsigned expressions shared by exact and sampled request builders.
sealed class ClassicalExpression {
 public enum NodeKind { Constant=0, Read=1, Complement=2, Binary=3, PopulationCount=4, Rotate=5, IntegerCompare=6, Logical=7, IntegerBits=8 }
 public enum Direction { Left=0, Right=1 }
 public enum Distance { Unsigned=0, Signed=1 }
 public Direction RotationDirection {get;private set;}
 public Distance DistanceInterpretation {get;private set;}
 public enum Operator { And=0, Or=1, Xor=2, ShiftLeft=3, ShiftRight=4, Equal=5, NotEqual=6, Less=7, LessEqual=8, Greater=9, GreaterEqual=10 }
 public NodeKind Kind {get;private set;}public Operator Operation {get;private set;}
 public int Width {get;private set;}public ulong Value {get;private set;}
 public ClassicalExpression Left {get;private set;}public ClassicalExpression Right {get;private set;}
 public ClassicalIntegerExpression IntegerLeft {get;private set;}public ClassicalIntegerExpression IntegerRight {get;private set;}
 public bool UsesNumericProtocol {get{return (Left!=null && Left.UsesNumericProtocol)||(Right!=null && Right.UsesNumericProtocol)||(IntegerLeft!=null && IntegerLeft.UsesNumericProtocol)||(IntegerRight!=null && IntegerRight.UsesNumericProtocol);}}
 public bool UsesTypedProtocol {get;private set;}
 public bool UsesBitExpressionProtocol {get;private set;}
 internal int Depth {get{return depth;}}internal int Count {get{return count;}}internal ulong References {get{return references;}}
 readonly int[] indices;readonly ulong references;readonly int depth,count;
 public int[] Indices {get{return indices==null ? null : (int[])indices.Clone();}}
 ClassicalExpression(NodeKind kind,int width,ulong value,int[] bits,Operator operation,ClassicalExpression left,ClassicalExpression right,ClassicalIntegerExpression integerLeft=null,ClassicalIntegerExpression integerRight=null) {
  if(width<1 || width>64)throw new ArgumentException("Classical expressions need 1–64 bits.");
  Kind=kind;Width=width;Value=value;Operation=operation;Left=left;Right=right;
  IntegerLeft=integerLeft;IntegerRight=integerRight;
  UsesBitExpressionProtocol=(left!=null && left.UsesBitExpressionProtocol)||(right!=null && right.UsesBitExpressionProtocol)||(integerLeft!=null && integerLeft.UsesBitExpressionProtocol)||(integerRight!=null && integerRight.UsesBitExpressionProtocol);
  UsesTypedProtocol=kind==NodeKind.Logical || kind==NodeKind.IntegerCompare || kind==NodeKind.IntegerBits || (left!=null && left.UsesTypedProtocol) || (right!=null && right.UsesTypedProtocol);
  depth=1+Math.Max(Math.Max(left==null ? 0 : left.depth,right==null ? 0 : right.depth),Math.Max(integerLeft==null ? 0 : integerLeft.Depth,integerRight==null ? 0 : integerRight.Depth));
  count=1+(left==null ? 0 : left.count)+(right==null ? 0 : right.count)+(integerLeft==null ? 0 : integerLeft.Count)+(integerRight==null ? 0 : integerRight.Count);
  if(depth>32 || count>512)throw new ArgumentException("Classical expressions allow 32 levels and 512 nodes.");
  references=(left==null ? 0 : left.references)|(right==null ? 0 : right.references)|(integerLeft==null ? 0 : integerLeft.References)|(integerRight==null ? 0 : integerRight.References);
  if(bits!=null) {
   indices=(int[])bits.Clone();
   foreach(int bit in indices) {if(bit<0 || bit>=64)throw new ArgumentException("Classical indices must be 0–63.");references|=1UL<<bit;}
  }
 }
 public static ClassicalExpression Constant(int width,ulong value) {
  if(width<1 || width>64 || (width<64 && value>>width!=0))throw new ArgumentException("Constant must fit its bit width.");
  return new ClassicalExpression(NodeKind.Constant,width,value,null,0,null,null);
 }
 public static ClassicalExpression Read(params int[] bits) {
  if(bits==null)throw new ArgumentNullException("bits");
  return new ClassicalExpression(NodeKind.Read,bits.Length,0,bits,0,null,null);
 }
 public static ClassicalExpression Complement(ClassicalExpression operand) {
  if(operand==null)throw new ArgumentNullException("operand");
  return new ClassicalExpression(NodeKind.Complement,operand.Width,0,null,0,operand,null);
 }
 public static ClassicalExpression Binary(Operator operation,ClassicalExpression left,ClassicalExpression right) {
  if(left==null || right==null)throw new ArgumentNullException("operand");
  if(!Enum.IsDefined(typeof(Operator),operation))throw new ArgumentException("Unknown classical operator.");
  bool shift=operation==Operator.ShiftLeft || operation==Operator.ShiftRight;
  if(!shift && left.Width!=right.Width)throw new ArgumentException("Classical operands require equal widths.");
  int width=(int)operation>=(int)Operator.Equal ? 1 : left.Width;
  return new ClassicalExpression(NodeKind.Binary,width,0,null,operation,left,right);
 }
 public static ClassicalExpression Logical(Operator operation,ClassicalExpression left,ClassicalExpression right) {
  if(left==null || right==null)throw new ArgumentNullException("operand");
  if(operation!=Operator.And && operation!=Operator.Or)throw new ArgumentException("Logical conditions require And or Or.");
  if(left.Width!=1 || right.Width!=1)throw new ArgumentException("Logical operands require one bit.");
  return new ClassicalExpression(NodeKind.Logical,1,0,null,operation,left,right);
 }
 public static ClassicalExpression IntegerCompare(Operator operation,ClassicalIntegerExpression left,ClassicalIntegerExpression right) {
  if(left==null || right==null)throw new ArgumentNullException("operand");
  if((int)operation<5 || (int)operation>10)throw new ArgumentException("Integer conditions require a comparison operator.");
  return new ClassicalExpression(NodeKind.IntegerCompare,1,0,null,operation,null,null,left,right);
 }
 public static ClassicalExpression FromInteger(ClassicalIntegerExpression operand) {
  if(operand==null)throw new ArgumentNullException("operand");
  if(operand.Type.DeclaredWidth==0)throw new ArgumentException("Bit casts require an explicitly sized integer.");
  return new ClassicalExpression(NodeKind.IntegerBits,operand.Type.Width,0,null,0,null,null,operand);
 }
 public static ClassicalExpression PopulationCount(ClassicalExpression operand) {
  if(operand==null)throw new ArgumentNullException("operand");
  return new ClassicalExpression(NodeKind.PopulationCount,64,0,null,0,operand,null);
 }
 public static ClassicalExpression Rotate(Direction direction,ClassicalExpression operand,ClassicalExpression distance,Distance interpretation) {
  if(operand==null || distance==null)throw new ArgumentNullException("operand");
  if(!Enum.IsDefined(typeof(Direction),direction) || !Enum.IsDefined(typeof(Distance),interpretation))throw new ArgumentException("Unknown rotation direction or distance interpretation.");
  return new ClassicalExpression(NodeKind.Rotate,operand.Width,0,null,0,operand,distance) {RotationDirection=direction,DistanceInterpretation=interpretation};
 }
 public void Write(Action<ulong> number,int registerBits,IList<ClassicalIntegerType> variables=null) {
  if(number==null)throw new ArgumentNullException("number");
  if(registerBits<0 || registerBits>64)throw new ArgumentException("Use 0–64 classical bits.");
  ulong allowed=registerBits==64 ? UInt64.MaxValue : (1UL<<registerBits)-1;
  if((references & ~allowed)!=0)throw new ArgumentException("Expression reads outside the classical register.");
  ValidateVariables(registerBits,variables);
  WriteNode(number);
 }
 internal void ValidateVariables(int bits,IList<ClassicalIntegerType> variables) {
  if(IntegerLeft!=null)IntegerLeft.Validate(bits,variables);if(IntegerRight!=null)IntegerRight.Validate(bits,variables);
  if(Left!=null)Left.ValidateVariables(bits,variables);if(Right!=null)Right.ValidateVariables(bits,variables);
 }
 internal void WriteNode(Action<ulong> number) {
  number((ulong)Kind);
  if(Kind==NodeKind.IntegerCompare){number((ulong)((int)Operation-5));IntegerLeft.WriteNode(number);IntegerRight.WriteNode(number);}
  else if(Kind==NodeKind.IntegerBits)IntegerLeft.WriteNode(number);
  else if(Kind==NodeKind.Constant){number((ulong)Width);number(Value);}
  else if(Kind==NodeKind.Read){number((ulong)indices.Length);foreach(int bit in indices)number((ulong)bit);}
  else if(Kind==NodeKind.Complement || Kind==NodeKind.PopulationCount)Left.WriteNode(number);
  else if(Kind==NodeKind.Rotate){number((ulong)RotationDirection);number((ulong)DistanceInterpretation);Left.WriteNode(number);Right.WriteNode(number);}
  else {number((ulong)Operation);Left.WriteNode(number);Right.WriteNode(number);}
 }
}

// Semantic type identity is distinct from storage width. Width zero on the wire
// denotes the documented 64-bit machine type, not an explicit int[64].
sealed class ClassicalIntegerType {
 public enum Sign { Signed=0, Unsigned=1 }
 public Sign Signedness {get;private set;}public int DeclaredWidth {get;private set;}
 public int Width {get{return DeclaredWidth==0 ? 64 : DeclaredWidth;}}
 public bool Same(ClassicalIntegerType other){return other!=null && Signedness==other.Signedness && DeclaredWidth==other.DeclaredWidth;}
 ClassicalIntegerType(Sign sign,int width){Signedness=sign;DeclaredWidth=width;}
 public static ClassicalIntegerType Create(Sign sign,int width=0) {
  if(!Enum.IsDefined(typeof(Sign),sign) || width<0 || width>64)throw new ArgumentException("Invalid integer signedness or width.");
  return new ClassicalIntegerType(sign,width);
 }
 internal static ClassicalIntegerType Common(ClassicalIntegerType left,ClassicalIntegerType right) {
  bool unsigned=(left.Signedness==Sign.Unsigned && left.Width==64)||(right.Signedness==Sign.Unsigned && right.Width==64);
  return Create(unsigned ? Sign.Unsigned : Sign.Signed);
 }
 internal void Write(Action<ulong> number){number((ulong)Signedness);number((ulong)DeclaredWidth);}
}
// Typed immutable expressions; only the worker evaluates runtime values.
sealed class ClassicalNumericType {
 public enum NumericKind { Float, Angle }
 public NumericKind Kind {get;private set;}public int Width {get;private set;}
 ClassicalNumericType(NumericKind kind,int width){Kind=kind;Width=width;}
 public static ClassicalNumericType Create(NumericKind kind,int width) {
  if(!Enum.IsDefined(typeof(NumericKind),kind) || (kind==NumericKind.Float ? width!=32 && width!=64 : width<1 || width>64))throw new ArgumentException("Use float32/64 or angle widths 1–64.");
  return new ClassicalNumericType(kind,width);
 }
 public bool Same(ClassicalNumericType other){return other!=null && Kind==other.Kind && Width==other.Width;}
 internal void Write(Action<ulong> number){number((ulong)Kind);number((ulong)Width);}
}
// Immutable array allocation and checked expression metadata shared by the
// document validator and both worker request writers.
sealed class ClassicalArrayAllocation {
 public readonly int Base,Size;
 public readonly IList<int> Dimensions;
 public readonly ClassicalIntegerType Integer;
 public readonly ClassicalNumericType Numeric;
 public ClassicalArrayAllocation(int start,IList<int> dimensions,ClassicalIntegerType integer,ClassicalNumericType numeric) {
  if(start<0 || start>4096 || dimensions==null || dimensions.Count<1 || dimensions.Count>7 || (integer==null)==(numeric==null))throw new ArgumentException("Invalid array declaration.");
  Base=start;Integer=integer;Numeric=numeric;Dimensions=new List<int>(dimensions).AsReadOnly();
  bool empty=false;foreach(int size in Dimensions){if(size<0 || size>4096)throw new ArgumentException("Array dimensions must be 0–4096.");empty|=size==0;}
  int total=empty ? 0 : 1;if(!empty)foreach(int size in Dimensions){if(total>4096/size)throw new ArgumentException("Array allocation exceeds 4096 elements.");total*=size;}
  if(total>4096-start)throw new ArgumentException("Array allocation exceeds its slot budget.");Size=total;
 }
 internal void Validate(RuntimeDeclarations declarations) {
  int available=Numeric==null ? declarations.Count : declarations.Numeric.Count;
  if(Base>available || Size>available-Base)throw new ArgumentException("Array allocation is outside runtime storage.");
  for(int k=Base;k<Base+Size;++k)if(Numeric==null ? !Integer.Same(declarations[k]) : !Numeric.Same(declarations.Numeric[k]))throw new ArgumentException("Array backing types differ from the element type.");
 }
 internal void Write(Action<ulong> number) {
  number(Numeric==null ? 0UL : 1UL);if(Numeric==null)Integer.Write(number);else Numeric.Write(number);
  number((ulong)Base);number((ulong)Dimensions.Count);foreach(int size in Dimensions)number((ulong)size);
 }
}
sealed class ClassicalArraySelection {
 public readonly int Array,Depth,Count;public readonly ulong References;
 public readonly IList<ClassicalIntegerExpression> Indices;public readonly string Source;
 public ClassicalArraySelection(int array,IList<ClassicalIntegerExpression> indices,string source) {
  if(array<0 || array>=4096 || indices==null || indices.Count<1 || indices.Count>7)throw new ArgumentException("Array selection needs one to seven indices.");
  Array=array;Indices=new List<ClassicalIntegerExpression>(indices).AsReadOnly();Source=source??"";
  if(System.Text.Encoding.UTF8.GetByteCount(Source)>512 || Source.IndexOf('\0')>=0)throw new ArgumentException("Invalid array source context.");
  int depth=1,count=1;ulong references=0;foreach(var index in Indices){if(index==null)throw new ArgumentException("Missing array index.");depth=Math.Max(depth,index.Depth+1);count+=index.Count;references|=index.References;}
  if(depth>32 || count>512)throw new ArgumentException("Array selection exceeds expression bounds.");Depth=depth;Count=count;References=references;
 }
 internal ClassicalArrayAllocation Validate(int bits,IList<ClassicalIntegerType> variables,bool prefix=false) {
  var declarations=variables as RuntimeDeclarations;
  if(declarations==null || Array>=declarations.Arrays.Count)throw new ArgumentException("Array selection has no declaration.");
  var allocation=declarations.Arrays[Array];if(prefix ? Indices.Count>allocation.Dimensions.Count : Indices.Count!=allocation.Dimensions.Count)throw new ArgumentException("Array index rank differs from its declaration.");
  foreach(var index in Indices)index.Validate(bits,variables);return allocation;
 }
 internal void Write(Action<ulong> number) {
  number((ulong)Array);number((ulong)Indices.Count);foreach(var index in Indices)index.WriteNode(number);
  byte[] source=System.Text.Encoding.UTF8.GetBytes(Source);number((ulong)source.Length);foreach(byte value in source)number(value);
 }
}
sealed class RuntimeDeclarations : System.Collections.ObjectModel.ReadOnlyCollection<ClassicalIntegerType> {
 public readonly IList<ClassicalNumericType> Numeric;
 public readonly IList<ClassicalArrayAllocation> Arrays;
 public RuntimeDeclarations(IList<ClassicalIntegerType> integers,IList<ClassicalNumericType> numeric,IList<ClassicalArrayAllocation> arrays=null):base(new List<ClassicalIntegerType>(integers)) {
  Numeric=new List<ClassicalNumericType>(numeric).AsReadOnly();
  Arrays=new List<ClassicalArrayAllocation>(arrays??new ClassicalArrayAllocation[0]).AsReadOnly();
  if(Arrays.Count>4096)throw new ArgumentException("Use at most 4096 arrays.");
  if(Count+Numeric.Count>4096)throw new ArgumentException("Use at most 4096 variable slots.");
  foreach(var type in Numeric)if(type==null)throw new ArgumentException("Missing numeric type.");
  for(int k=0;k<Arrays.Count;++k) {
   var a=Arrays[k];if(a==null)throw new ArgumentException("Missing array declaration.");a.Validate(this);
   for(int j=0;j<k;++j){var b=Arrays[j];if((a.Numeric==null)==(b.Numeric==null) && a.Size>0 && b.Size>0 && a.Base<b.Base+b.Size && b.Base<a.Base+a.Size)throw new ArgumentException("Array allocations overlap.");}
  }
 }
}
sealed class ClassicalRealExpression {
 public enum NodeKind { Constant=0, Integer=1, Binary=2, TypedConstant=3, Variable=4, Cast=5, Function=6, Scale=7, Bits=8, TypedInteger=9, ArrayElement=10 }
 public enum Operator { Add=0, Subtract=1, Multiply=2, Divide=3, Power=4, Mod=5, And=6, Or=7, Xor=8 }
 public enum FunctionKind { Negate, Sin, Cos, Tan, Arcsin, Arccos, Arctan, Exp, Log, Sqrt, Floor, Ceiling, Complement }
 public enum Scaling { Multiply, Divide, ShiftLeft, ShiftRight }
 public ClassicalArraySelection Selection {get;private set;}
 public NodeKind Kind {get;private set;}public Operator Operation {get;private set;}
 public ClassicalNumericType Type {get;private set;}public ulong Raw {get;private set;}public int Slot {get;private set;}
 public FunctionKind FunctionCode {get;private set;}public Scaling ScaleCode {get;private set;}
 public double Value {get;private set;}public ClassicalIntegerExpression Integer {get;private set;}
 public ClassicalExpression BitOperand {get;private set;}
 public ClassicalRealExpression Left {get;private set;}public ClassicalRealExpression Right {get;private set;}
 internal int Depth {get;private set;}internal int Count {get;private set;}internal ulong References {get;private set;}
 public bool UsesNumericProtocol {get{return (int)Kind>=3 || (Kind==NodeKind.Binary && (int)Operation>=4) || (Integer!=null && Integer.UsesNumericProtocol) || (Left!=null && Left.UsesNumericProtocol) || (Right!=null && Right.UsesNumericProtocol);}}
 static ClassicalNumericType Float(int width=64){return ClassicalNumericType.Create(ClassicalNumericType.NumericKind.Float,width);}
 static bool Angle(ClassicalNumericType type){return type.Kind==ClassicalNumericType.NumericKind.Angle;}
 ClassicalRealExpression(NodeKind kind,ClassicalNumericType type,ClassicalIntegerExpression integer=null,ClassicalRealExpression left=null,ClassicalRealExpression right=null,ClassicalExpression bits=null) {
  Kind=kind;Type=type;Integer=integer;Left=left;Right=right;BitOperand=bits;
  Depth=1+Math.Max(Math.Max(integer==null ? 0 : integer.Depth,bits==null ? 0 : bits.Depth),Math.Max(left==null ? 0 : left.Depth,right==null ? 0 : right.Depth));
  Count=1+(integer==null ? 0 : integer.Count)+(left==null ? 0 : left.Count)+(right==null ? 0 : right.Count)+(bits==null ? 0 : bits.Count);
  References=(integer==null ? 0 : integer.References)|(left==null ? 0 : left.References)|(right==null ? 0 : right.References)|(bits==null ? 0 : bits.References);
  if(Depth>32 || Count>512)throw new ArgumentException("Real expressions allow 32 levels and 512 nodes.");
 }
 public static ClassicalRealExpression Constant(double value) {
  if(Double.IsNaN(value) || Double.IsInfinity(value))throw new ArgumentException("Real constants must be finite.");
  return new ClassicalRealExpression(NodeKind.Constant,Float()) {Value=value,Raw=unchecked((ulong)BitConverter.DoubleToInt64Bits(value))};
 }
 public static ClassicalRealExpression TypedConstant(ClassicalNumericType type,ulong raw) {
  if(type==null || (type.Width<64 && raw>>type.Width!=0))throw new ArgumentException("Numeric bits exceed their type.");
  if(!Angle(type)) {
   double value=type.Width==64 ? BitConverter.Int64BitsToDouble(unchecked((long)raw)) : BitConverter.ToSingle(BitConverter.GetBytes((uint)raw),0);
   if(Double.IsNaN(value) || Double.IsInfinity(value))throw new ArgumentException("Numeric constants must be finite.");
  }
  return new ClassicalRealExpression(NodeKind.TypedConstant,type) {Raw=raw};
 }
 public static ClassicalRealExpression ArrayElement(ClassicalNumericType type,ClassicalArraySelection selection) {
  if(type==null || selection==null)throw new ArgumentNullException("array type or selection");
  var result=new ClassicalRealExpression(NodeKind.ArrayElement,type);result.Selection=selection;result.Depth=1+selection.Depth;result.Count=1+selection.Count;result.References=selection.References;
  if(result.Depth>32 || result.Count>512)throw new ArgumentException("Array expression exceeds its bounds.");return result;
 }
 public static ClassicalRealExpression Variable(ClassicalNumericType type,int slot) {
  if(type==null || slot<0 || slot>=4096)throw new ArgumentException("Invalid numeric variable.");
  return new ClassicalRealExpression(NodeKind.Variable,type) {Slot=slot};
 }
 public static ClassicalRealExpression FromInteger(ClassicalIntegerExpression value) {
  if(value==null)throw new ArgumentNullException("value");return new ClassicalRealExpression(NodeKind.Integer,Float(),value);
 }
 public static ClassicalRealExpression FromInteger(ClassicalIntegerExpression value,int width) {
  if(value==null)throw new ArgumentNullException("value");return new ClassicalRealExpression(NodeKind.TypedInteger,Float(width),value);
 }
 public static ClassicalRealExpression Cast(ClassicalNumericType type,ClassicalRealExpression value) {
  if(type==null || value==null)throw new ArgumentNullException("type or operand");
  if(Angle(value.Type) && !Angle(type))throw new ArgumentException("Angles cannot be cast to float.");
  return new ClassicalRealExpression(NodeKind.Cast,type,null,value);
 }
 public static ClassicalRealExpression FromBits(int width,ClassicalExpression value) {
  if(value==null || value.Width!=width)throw new ArgumentException("Bit-to-angle casts require matching widths.");
  return new ClassicalRealExpression(NodeKind.Bits,ClassicalNumericType.Create(ClassicalNumericType.NumericKind.Angle,width),null,null,null,value);
 }
 public static ClassicalRealExpression Function(FunctionKind function,ClassicalRealExpression value) {
  if(value==null || !Enum.IsDefined(typeof(FunctionKind),function))throw new ArgumentException("Invalid numeric function.");
  bool trig=function==FunctionKind.Sin || function==FunctionKind.Cos || function==FunctionKind.Tan;
  if(Angle(value.Type) && !trig && function!=FunctionKind.Negate && function!=FunctionKind.Complement)throw new ArgumentException("Only trigonometric functions accept angles.");
  if(!Angle(value.Type) && function==FunctionKind.Complement)throw new ArgumentException("Complement requires an angle.");
  return new ClassicalRealExpression(NodeKind.Function,trig && Angle(value.Type) ? Float() : value.Type,null,value) {FunctionCode=function};
 }
 public static ClassicalRealExpression Scale(Scaling operation,ClassicalRealExpression value,ClassicalIntegerExpression integer) {
  if(value==null || integer==null || !Enum.IsDefined(typeof(Scaling),operation) || !Angle(value.Type) || integer.Type.Signedness!=ClassicalIntegerType.Sign.Unsigned)throw new ArgumentException("Angle scaling requires an unsigned integer.");
  if((operation==Scaling.Multiply || operation==Scaling.Divide) && value.Type.Width!=integer.Type.Width)throw new ArgumentException("Angle scaling requires matching widths.");
  return new ClassicalRealExpression(NodeKind.Scale,value.Type,integer,value) {ScaleCode=operation};
 }
 public static ClassicalRealExpression Binary(Operator operation,ClassicalRealExpression left,ClassicalRealExpression right) {
  if(left==null || right==null)throw new ArgumentNullException("operand");
  if(!Enum.IsDefined(typeof(Operator),operation))throw new ArgumentException("Unknown real operator.");
  bool angle=Angle(left.Type) || Angle(right.Type);
  if(angle ? !left.Type.Same(right.Type) || (operation!=Operator.Add && operation!=Operator.Subtract && (int)operation<6) : (int)operation>=6)throw new ArgumentException("Unsupported numeric operand types.");
  return new ClassicalRealExpression(NodeKind.Binary,angle ? left.Type : Float(Math.Max(left.Type.Width,right.Type.Width)),null,left,right) {Operation=operation};
 }
 internal void Validate(int bits,IList<ClassicalIntegerType> variables) {
  if(Selection!=null && !Type.Same(Selection.Validate(bits,variables).Numeric))throw new ArgumentException("Array read type differs from declaration.");
  if(bits<0 || bits>64 || (bits<64 && References>>bits!=0))throw new ArgumentException("Numeric expression reads outside the classical register.");
  if(Kind==NodeKind.Variable) {
   var declarations=variables as RuntimeDeclarations;
   if(declarations==null || Slot>=declarations.Numeric.Count || !Type.Same(declarations.Numeric[Slot]))throw new ArgumentException("Numeric variable slot/type does not match its declaration.");
  }
  if(Integer!=null)Integer.Validate(bits,variables);if(BitOperand!=null)BitOperand.ValidateVariables(bits,variables);
  if(Left!=null)Left.Validate(bits,variables);if(Right!=null)Right.Validate(bits,variables);
 }
 internal void WriteNode(Action<ulong> number) {
  number((ulong)Kind);
  if(Selection!=null){Type.Write(number);Selection.Write(number);return;}
  if(Kind==NodeKind.Constant)number(Raw);
  else if(Kind==NodeKind.TypedConstant){Type.Write(number);number(Raw);}
  else if(Kind==NodeKind.Variable){Type.Write(number);number((ulong)Slot);}
  else if(Kind==NodeKind.Cast){Type.Write(number);Left.WriteNode(number);}
  else if(Kind==NodeKind.Function){number((ulong)FunctionCode);Left.WriteNode(number);}
  else if(Kind==NodeKind.Scale){number((ulong)ScaleCode);Left.WriteNode(number);Integer.WriteNode(number);}
  else if(Kind==NodeKind.Bits){number((ulong)Type.Width);BitOperand.WriteNode(number);}
  else if(Kind==NodeKind.TypedInteger){number((ulong)Type.Width);Integer.WriteNode(number);}
  else if(Kind==NodeKind.Integer)Integer.WriteNode(number);
  else {number((ulong)Operation);Left.WriteNode(number);Right.WriteNode(number);}
 }
}
sealed class ClassicalIntegerExpression {
 public enum NodeKind { Constant=0, Read=1, Cast=2, Binary=3, Variable=4, BitExpression=5, NumericCast=6, AngleRatio=7, AngleBits=8, NumericCompare=9, ArrayElement=10, ArrayExtent=11 }
 public enum Operator { Add=0, Subtract=1, Multiply=2, Divide=3, Remainder=4, Power=5 }
 public ClassicalArraySelection Selection {get;private set;}
 public NodeKind Kind {get;private set;}public Operator Operation {get;private set;}
 public int Slot {get;private set;}
 public ClassicalIntegerType Type {get;private set;}public ulong Value {get;private set;}
 public ClassicalIntegerExpression Left {get;private set;}public ClassicalIntegerExpression Right {get;private set;}
 public ClassicalRealExpression NumericLeft {get;private set;}public ClassicalRealExpression NumericRight {get;private set;}
 public bool UsesNumericProtocol {get{return NumericLeft!=null || (Left!=null && Left.UsesNumericProtocol) || (Right!=null && Right.UsesNumericProtocol) || (BitOperand!=null && BitOperand.UsesNumericProtocol);}}
 public ClassicalExpression BitOperand {get;private set;}
 public bool UsesBitExpressionProtocol {get;private set;}
 internal int Depth {get;private set;}internal int Count {get;private set;}internal ulong References {get;private set;}
 readonly int[] indices;public int[] Indices {get{return indices==null ? null : (int[])indices.Clone();}}
 ClassicalIntegerExpression(NodeKind kind,ClassicalIntegerType type,ulong value,int[] bits,Operator operation,ClassicalIntegerExpression left,ClassicalIntegerExpression right,ClassicalExpression bitOperand=null) {
  if(type==null)throw new ArgumentNullException("type");
  Kind=kind;Type=type;Value=value;Operation=operation;Left=left;Right=right;
  BitOperand=bitOperand;UsesBitExpressionProtocol=bitOperand!=null || (left!=null && left.UsesBitExpressionProtocol)||(right!=null && right.UsesBitExpressionProtocol);
  Depth=1+Math.Max(bitOperand==null ? 0 : bitOperand.Depth,Math.Max(left==null ? 0 : left.Depth,right==null ? 0 : right.Depth));
  Count=1+(left==null ? 0 : left.Count)+(right==null ? 0 : right.Count)+(bitOperand==null ? 0 : bitOperand.Count);
  if(Depth>32 || Count>512)throw new ArgumentException("Integer expressions allow 32 levels and 512 nodes.");
  References=(left==null ? 0 : left.References)|(right==null ? 0 : right.References)|(bitOperand==null ? 0 : bitOperand.References);
  if(bits!=null) {indices=(int[])bits.Clone();foreach(int bit in indices){if(bit<0 || bit>=64)throw new ArgumentException("Integer indices must be 0–63.");References|=1UL<<bit;}}
 }
 static ClassicalIntegerExpression Numeric(NodeKind kind,ClassicalIntegerType type,ClassicalRealExpression left,ClassicalRealExpression right=null) {
  if(left==null)throw new ArgumentNullException("operand");
  var result=new ClassicalIntegerExpression(kind,type,0,null,0,null,null) {NumericLeft=left,NumericRight=right};
  result.Depth=1+Math.Max(left.Depth,right==null ? 0 : right.Depth);result.Count=1+left.Count+(right==null ? 0 : right.Count);
  result.References=left.References|(right==null ? 0 : right.References);
  if(result.Depth>32 || result.Count>512)throw new ArgumentException("Integer expressions allow 32 levels and 512 nodes.");
  return result;
 }
 public static ClassicalIntegerExpression FromNumeric(ClassicalIntegerType type,ClassicalRealExpression operand) {
  if(operand==null || operand.Type.Kind!=ClassicalNumericType.NumericKind.Float)throw new ArgumentException("Integer casts require floats.");
  return Numeric(NodeKind.NumericCast,type,operand);
 }
 public static ClassicalIntegerExpression AngleBits(ClassicalRealExpression operand) {
  if(operand==null || operand.Type.Kind!=ClassicalNumericType.NumericKind.Angle)throw new ArgumentException("Angle bit conversion requires an angle.");
  return Numeric(NodeKind.AngleBits,ClassicalIntegerType.Create(ClassicalIntegerType.Sign.Unsigned,operand.Type.Width),operand);
 }
 public static ClassicalIntegerExpression AngleRatio(ClassicalRealExpression left,ClassicalRealExpression right) {
  if(left==null || right==null || left.Type.Kind!=ClassicalNumericType.NumericKind.Angle || !left.Type.Same(right.Type))throw new ArgumentException("Angle ratios require equal widths.");
  return Numeric(NodeKind.AngleRatio,ClassicalIntegerType.Create(ClassicalIntegerType.Sign.Unsigned,left.Type.Width),left,right);
 }
 public static ClassicalIntegerExpression NumericCompare(ClassicalRealExpression left,ClassicalRealExpression right) {
  if(left==null || right==null || ((left.Type.Kind==ClassicalNumericType.NumericKind.Angle || right.Type.Kind==ClassicalNumericType.NumericKind.Angle) && !left.Type.Same(right.Type)))throw new ArgumentException("Incompatible numeric comparison.");
  return Numeric(NodeKind.NumericCompare,ClassicalIntegerType.Create(ClassicalIntegerType.Sign.Signed),left,right);
 }
 public static ClassicalIntegerExpression Constant(ClassicalIntegerType type,ulong value) {
  if(type==null)throw new ArgumentNullException("type");
  if(type.Width<64 && value>>type.Width!=0)throw new ArgumentException("Integer constant must fit its type.");
  return new ClassicalIntegerExpression(NodeKind.Constant,type,value,null,0,null,null);
 }
 public static ClassicalIntegerExpression Read(ClassicalIntegerType type,params int[] bits) {
  if(type==null || bits==null)throw new ArgumentNullException("type or indices");
  if(bits.Length!=type.Width)throw new ArgumentException("Integer read width must match its type.");
  return new ClassicalIntegerExpression(NodeKind.Read,type,0,bits,0,null,null);
 }
 public static ClassicalIntegerExpression ArrayExtent(ClassicalArraySelection selection) {
  var result=ArrayElement(ClassicalIntegerType.Create(ClassicalIntegerType.Sign.Signed,0),selection);result.Kind=NodeKind.ArrayExtent;return result;
 }
 public static ClassicalIntegerExpression ArrayElement(ClassicalIntegerType type,ClassicalArraySelection selection) {
  if(type==null || selection==null)throw new ArgumentNullException("array type or selection");
  var result=new ClassicalIntegerExpression(NodeKind.ArrayElement,type,0,null,0,null,null);result.Selection=selection;result.Depth=1+selection.Depth;result.Count=1+selection.Count;result.References=selection.References;
  if(result.Depth>32 || result.Count>512)throw new ArgumentException("Array expression exceeds its bounds.");return result;
 }
 public static ClassicalIntegerExpression Variable(ClassicalIntegerType type,int slot) {
  if(slot<0 || slot>=4096)throw new ArgumentException("Variable slots must be 0-4095.");
  return new ClassicalIntegerExpression(NodeKind.Variable,type,0,null,0,null,null) {Slot=slot};
 }
 public static ClassicalIntegerExpression FromBits(ClassicalIntegerType type,ClassicalExpression operand) {
  if(type==null || operand==null)throw new ArgumentNullException("type or operand");
  if(type.Width!=operand.Width)throw new ArgumentException("Bit expression width must match its integer type.");
  return new ClassicalIntegerExpression(NodeKind.BitExpression,type,0,null,0,null,null,operand);
 }
 internal void Validate(int bits,IList<ClassicalIntegerType> variables) {
  if(Selection!=null && Kind==NodeKind.ArrayExtent)Selection.Validate(bits,variables,true);
  if(Selection!=null && Kind!=NodeKind.ArrayExtent && !Type.Same(Selection.Validate(bits,variables).Integer))throw new ArgumentException("Array read type differs from declaration.");
  if(bits<0 || bits>64 || (bits<64 && (References>>bits)!=0))throw new ArgumentException("Integer expression reads outside the classical register.");
  if(Kind==NodeKind.Variable) {
   if(variables==null || Slot>=variables.Count || variables[Slot]==null || variables[Slot].Signedness!=Type.Signedness || variables[Slot].DeclaredWidth!=Type.DeclaredWidth)
    throw new ArgumentException("Variable slot or declared type does not match the circuit.");
  }
  if(Left!=null)Left.Validate(bits,variables);if(Right!=null)Right.Validate(bits,variables);
  if(BitOperand!=null)BitOperand.ValidateVariables(bits,variables);
  if(NumericLeft!=null)NumericLeft.Validate(bits,variables);if(NumericRight!=null)NumericRight.Validate(bits,variables);
 }
 public static ClassicalIntegerExpression Cast(ClassicalIntegerType type,ClassicalIntegerExpression operand) {
  if(operand==null)throw new ArgumentNullException("operand");
  return new ClassicalIntegerExpression(NodeKind.Cast,type,0,null,0,operand,null);
 }
 public static ClassicalIntegerExpression Binary(Operator operation,ClassicalIntegerExpression left,ClassicalIntegerExpression right) {
  if(left==null || right==null)throw new ArgumentNullException("operand");
  if(!Enum.IsDefined(typeof(Operator),operation))throw new ArgumentException("Unknown integer operator.");
  return new ClassicalIntegerExpression(NodeKind.Binary,ClassicalIntegerType.Common(left.Type,right.Type),0,null,operation,left,right);
 }
 internal void WriteNode(Action<ulong> number) {
  number((ulong)Kind);
  if(Selection!=null){if(Kind!=NodeKind.ArrayExtent)Type.Write(number);Selection.Write(number);return;}
  if(NumericLeft!=null){if(Kind==NodeKind.NumericCast)Type.Write(number);NumericLeft.WriteNode(number);if(NumericRight!=null)NumericRight.WriteNode(number);return;}
  if(Kind==NodeKind.Binary){number((ulong)Operation);Left.WriteNode(number);Right.WriteNode(number);return;}
  Type.Write(number);
  if(Kind==NodeKind.Constant)number(Value);
  else if(Kind==NodeKind.Read){foreach(int bit in indices)number((ulong)bit);}
  else if(Kind==NodeKind.Variable)number((ulong)Slot);
  else if(Kind==NodeKind.BitExpression)BitOperand.WriteNode(number);
  else Left.WriteNode(number);
 }
}
