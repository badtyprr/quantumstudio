// GPL-2.0-or-later; see COPYING.
using System;

// Immutable unsigned expressions shared by exact and sampled request builders.
sealed class ClassicalExpression {
 public enum NodeKind { Constant=0, Read=1, Complement=2, Binary=3 }
 public enum Operator { And=0, Or=1, Xor=2, ShiftLeft=3, ShiftRight=4, Equal=5, NotEqual=6, Less=7, LessEqual=8, Greater=9, GreaterEqual=10 }
 public NodeKind Kind {get;private set;}public Operator Operation {get;private set;}
 public int Width {get;private set;}public ulong Value {get;private set;}
 public ClassicalExpression Left {get;private set;}public ClassicalExpression Right {get;private set;}
 readonly int[] indices;readonly ulong references;readonly int depth,count;
 public int[] Indices {get{return indices==null ? null : (int[])indices.Clone();}}
 ClassicalExpression(NodeKind kind,int width,ulong value,int[] bits,Operator operation,ClassicalExpression left,ClassicalExpression right) {
  if(width<1 || width>64)throw new ArgumentException("Classical expressions need 1–64 bits.");
  Kind=kind;Width=width;Value=value;Operation=operation;Left=left;Right=right;
  depth=1+Math.Max(left==null ? 0 : left.depth,right==null ? 0 : right.depth);
  count=1+(left==null ? 0 : left.count)+(right==null ? 0 : right.count);
  if(depth>32 || count>512)throw new ArgumentException("Classical expressions allow 32 levels and 512 nodes.");
  references=(left==null ? 0 : left.references)|(right==null ? 0 : right.references);
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
 public void Write(Action<ulong> number,int registerBits) {
  if(number==null)throw new ArgumentNullException("number");
  if(registerBits<0 || registerBits>64)throw new ArgumentException("Use 0–64 classical bits.");
  ulong allowed=registerBits==64 ? UInt64.MaxValue : (1UL<<registerBits)-1;
  if((references & ~allowed)!=0)throw new ArgumentException("Expression reads outside the classical register.");
  WriteNode(number);
 }
 void WriteNode(Action<ulong> number) {
  number((ulong)Kind);
  if(Kind==NodeKind.Constant){number((ulong)Width);number(Value);}
  else if(Kind==NodeKind.Read){number((ulong)indices.Length);foreach(int bit in indices)number((ulong)bit);}
  else if(Kind==NodeKind.Complement)Left.WriteNode(number);
  else {number((ulong)Operation);Left.WriteNode(number);Right.WriteNode(number);}
 }
}
