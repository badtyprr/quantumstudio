// GPL-2.0-or-later; see COPYING.
using System;

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
 public bool UsesTypedProtocol {get;private set;}
 readonly int[] indices;readonly ulong references;readonly int depth,count;
 public int[] Indices {get{return indices==null ? null : (int[])indices.Clone();}}
 ClassicalExpression(NodeKind kind,int width,ulong value,int[] bits,Operator operation,ClassicalExpression left,ClassicalExpression right,ClassicalIntegerExpression integerLeft=null,ClassicalIntegerExpression integerRight=null) {
  if(width<1 || width>64)throw new ArgumentException("Classical expressions need 1–64 bits.");
  Kind=kind;Width=width;Value=value;Operation=operation;Left=left;Right=right;
  IntegerLeft=integerLeft;IntegerRight=integerRight;
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
 public void Write(Action<ulong> number,int registerBits) {
  if(number==null)throw new ArgumentNullException("number");
  if(registerBits<0 || registerBits>64)throw new ArgumentException("Use 0–64 classical bits.");
  ulong allowed=registerBits==64 ? UInt64.MaxValue : (1UL<<registerBits)-1;
  if((references & ~allowed)!=0)throw new ArgumentException("Expression reads outside the classical register.");
  WriteNode(number);
 }
 void WriteNode(Action<ulong> number) {
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
sealed class ClassicalIntegerExpression {
 public enum NodeKind { Constant=0, Read=1, Cast=2, Binary=3 }
 public enum Operator { Add=0, Subtract=1, Multiply=2, Divide=3, Remainder=4, Power=5 }
 public NodeKind Kind {get;private set;}public Operator Operation {get;private set;}
 public ClassicalIntegerType Type {get;private set;}public ulong Value {get;private set;}
 public ClassicalIntegerExpression Left {get;private set;}public ClassicalIntegerExpression Right {get;private set;}
 internal int Depth {get;private set;}internal int Count {get;private set;}internal ulong References {get;private set;}
 readonly int[] indices;public int[] Indices {get{return indices==null ? null : (int[])indices.Clone();}}
 ClassicalIntegerExpression(NodeKind kind,ClassicalIntegerType type,ulong value,int[] bits,Operator operation,ClassicalIntegerExpression left,ClassicalIntegerExpression right) {
  if(type==null)throw new ArgumentNullException("type");
  Kind=kind;Type=type;Value=value;Operation=operation;Left=left;Right=right;
  Depth=1+Math.Max(left==null ? 0 : left.Depth,right==null ? 0 : right.Depth);
  Count=1+(left==null ? 0 : left.Count)+(right==null ? 0 : right.Count);
  if(Depth>32 || Count>512)throw new ArgumentException("Integer expressions allow 32 levels and 512 nodes.");
  References=(left==null ? 0 : left.References)|(right==null ? 0 : right.References);
  if(bits!=null) {indices=(int[])bits.Clone();foreach(int bit in indices){if(bit<0 || bit>=64)throw new ArgumentException("Integer indices must be 0–63.");References|=1UL<<bit;}}
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
  if(Kind==NodeKind.Binary){number((ulong)Operation);Left.WriteNode(number);Right.WriteNode(number);return;}
  Type.Write(number);
  if(Kind==NodeKind.Constant)number(Value);
  else if(Kind==NodeKind.Read){foreach(int bit in indices)number((ulong)bit);}
  else Left.WriteNode(number);
 }
}
