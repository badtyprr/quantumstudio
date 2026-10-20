// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.Globalization;
using E=ClassicalExpression;
using I=ClassicalIntegerExpression;
using T=ClassicalIntegerType;

// Standard OpenQASM expressions over the exporter's canonical c and vN storage.
// Typed nodes carry the semantics; editor display text is deliberately not parsed.
sealed class ClassicalExpressionQasm {
 readonly int bits;
 readonly IList<T> variables;
 public ClassicalExpressionQasm(int registerBits,IList<T> variableTypes=null) {
  if(registerBits<0 || registerBits>64)throw new ArgumentException("Use 0–64 classical bits.");
  if(variableTypes!=null && variableTypes.Count>4096)throw new ArgumentException("Too many integer variables.");
  bits=registerBits;
  variables=variableTypes==null ? new T[0] : new List<T>(variableTypes).ToArray();
 }
 static string Number(int value){return value.ToString(CultureInfo.InvariantCulture);}
 static string TypeName(T type) {
  if(type==null)throw new ArgumentException("An integer expression needs a type.");
  // QuantumStudio defines machine integers as 64 bits; OpenQASM leaves that
  // width target-dependent. Explicit widths preserve our numerical semantics.
  return (type.Signedness==T.Sign.Signed ? "int[" : "uint[")+Number(type.Width)+"]";
 }
 static string BitType(int width){return "bit["+Number(width)+"]";}
 static string IntegerLiteral(I value) {
  if(value.Type.Signedness==T.Sign.Unsigned)return value.Value.ToString(CultureInfo.InvariantCulture);
  ulong pattern=value.Value;
  int width=value.Type.Width;
  if(width<64 && (pattern&(1UL<<(width-1)))!=0)pattern|=~((1UL<<width)-1);
  return unchecked((long)pattern).ToString(CultureInfo.InvariantCulture);
 }
 static string Cast(string type,string value){return type+"("+value+")";}
 static string Literal(int width,ulong value) {
  char[] result=new char[width+2];result[0]=result[width+1]='"';
  for(int i=0;i<width;i++)result[width-i]=(value&(1UL<<i))==0 ? '0' : '1';
  return new string(result);
 }
 static string Read(int[] indices) {
  string[] values=Array.ConvertAll(indices,Number);
  // A discrete selection preserves ordering and repeated indices, including
  // the one-bit register type required by explicit integer casts.
  return "c[{"+String.Join(",",values)+"}]";
 }
 public string Bits(E value) {
  if(value==null)throw new ArgumentNullException("value");
  value.Write(delegate(ulong ignored){},bits,variables);
  return BitNode(value);
 }
 public string Integer(I value) {
  if(value==null)throw new ArgumentNullException("value");
  value.Validate(bits,variables);
  return IntegerNode(value);
 }
 static string BitOperator(E.Operator op) {
  switch(op) {
   case E.Operator.And:return "&";case E.Operator.Or:return "|";case E.Operator.Xor:return "^";
   case E.Operator.ShiftLeft:return "<<";case E.Operator.ShiftRight:return ">>";
   case E.Operator.Equal:return "==";case E.Operator.NotEqual:return "!=";
   case E.Operator.Less:return "<";case E.Operator.LessEqual:return "<=";
   case E.Operator.Greater:return ">";case E.Operator.GreaterEqual:return ">=";
   default:throw new ArgumentException("Unsupported bit operator.");
  }
 }
 static string Binary(string left,string op,string right){return "("+left+" "+op+" "+right+")";}
 static string Compare(E value) {
  T common=T.Common(value.IntegerLeft.Type,value.IntegerRight.Type);
  return Binary(Cast(TypeName(common),IntegerNode(value.IntegerLeft)),BitOperator(value.Operation),
                Cast(TypeName(common),IntegerNode(value.IntegerRight)));
 }
 static string BitNode(E value) {
  switch(value.Kind) {
   case E.NodeKind.Constant:return Literal(value.Width,value.Value);
   case E.NodeKind.Read:return Read(value.Indices);
   case E.NodeKind.Complement:return "(~"+BitNode(value.Left)+")";
   case E.NodeKind.IntegerBits:return Cast(BitType(value.Width),IntegerNode(value.IntegerLeft));
   case E.NodeKind.PopulationCount:
    return Cast("bit[64]",Cast("uint[64]","popcount("+BitNode(value.Left)+")"));
   case E.NodeKind.Rotate:
    return (value.RotationDirection==E.Direction.Left ? "rotl(" : "rotr(")+BitNode(value.Left)+","+
      Cast((value.DistanceInterpretation==E.Distance.Signed ? "int[" : "uint[")+Number(value.Right.Width)+"]",BitNode(value.Right))+")";
   case E.NodeKind.IntegerCompare:return Cast("bit[1]",Compare(value));
   case E.NodeKind.Logical:
    return Cast("bit[1]",Binary(Cast("bool",BitNode(value.Left)),value.Operation==E.Operator.And ? "&&" : "||",Cast("bool",BitNode(value.Right))));
   case E.NodeKind.Binary:
    string right=BitNode(value.Right);
    if(value.Operation==E.Operator.ShiftLeft || value.Operation==E.Operator.ShiftRight)
     right=Cast("uint["+Number(value.Right.Width)+"]",right);
    string result=Binary(BitNode(value.Left),BitOperator(value.Operation),right);
    return (int)value.Operation>=(int)E.Operator.Equal ? Cast("bit[1]",result) : result;
   default:throw new ArgumentException("Unsupported bit expression.");
  }
 }
 static string IntegerNode(I value) {
  switch(value.Kind) {
   case I.NodeKind.Constant:return Cast(TypeName(value.Type),IntegerLiteral(value));
   case I.NodeKind.Read:return Cast(TypeName(value.Type),Read(value.Indices));
   case I.NodeKind.Variable:return "v"+Number(value.Slot);
   case I.NodeKind.Cast:return Cast(TypeName(value.Type),IntegerNode(value.Left));
   case I.NodeKind.BitExpression:return Cast(TypeName(value.Type),BitNode(value.BitOperand));
   case I.NodeKind.Binary:
    string op;
    switch(value.Operation) {
     case I.Operator.Add:op="+";break;case I.Operator.Subtract:op="-";break;
     case I.Operator.Multiply:op="*";break;case I.Operator.Divide:op="/";break;
     case I.Operator.Remainder:op="%";break;case I.Operator.Power:op="**";break;
     default:throw new ArgumentException("Unsupported integer operator.");
    }
    // Arithmetic promotes to the model's common machine type before operating.
    return Binary(Cast(TypeName(value.Type),IntegerNode(value.Left)),op,Cast(TypeName(value.Type),IntegerNode(value.Right)));
   default:throw new ArgumentException("Unsupported integer expression.");
  }
 }
}
