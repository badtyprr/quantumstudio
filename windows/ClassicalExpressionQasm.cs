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
 readonly ClassicalQasmStorage storage;
 public ClassicalExpressionQasm(int registerBits,IList<T> variableTypes=null,ClassicalQasmStorage mappedStorage=null) {
  if(registerBits<0 || registerBits>64)throw new ArgumentException("Use 0–64 classical bits.");
  if(variableTypes!=null && variableTypes.Count>4096)throw new ArgumentException("Too many integer variables.");
  bits=registerBits;
  if(mappedStorage!=null && mappedStorage.BitCount!=registerBits)throw new ArgumentException("Export storage must match the expression register.");
  storage=mappedStorage;
  variables=variableTypes is RuntimeDeclarations ? (IList<T>)new RuntimeDeclarations(variableTypes,((RuntimeDeclarations)variableTypes).Numeric,((RuntimeDeclarations)variableTypes).Arrays) : variableTypes==null ? new T[0] : new List<T>(variableTypes).ToArray();
 }
 public string Slot(int slot,bool numeric) {
  var declarations=variables as RuntimeDeclarations;
  if(declarations!=null)for(int k=0;k<declarations.Arrays.Count;++k) {
   var array=declarations.Arrays[k];if((array.Numeric!=null)!=numeric || slot<array.Base || slot>=array.Base+array.Size)continue;
   int offset=slot-array.Base;var indices=new string[array.Dimensions.Count];
   for(int j=indices.Length-1;j>=0;--j){indices[j]=Number(offset%array.Dimensions[j]);offset/=array.Dimensions[j];}
   return "a"+Number(k)+"["+String.Join(",",indices)+"]";
  }
  return (numeric ? "n" : "v")+Number(slot);
 }
 public string ArrayElement(ClassicalArraySelection selection) {
  selection.Validate(bits,variables);var indices=new List<string>();foreach(var index in selection.Indices)indices.Add(Integer(index));
  return "a"+Number(selection.Array)+"["+String.Join(",",indices)+"]";
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
 string Read(int[] indices) {
  if(storage!=null)return storage.Read(indices);
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
 public string Real(ClassicalRealExpression value) {
  if(value==null)throw new ArgumentNullException("value");
  value.Validate(bits,variables);
  return RealNode(value);
 }
 internal static string NumericTypeName(ClassicalNumericType type){return (type.Kind==ClassicalNumericType.NumericKind.Float ? "float[" : "angle[")+Number(type.Width)+"]";}
 static string FloatLiteral(double number) {
  if(number==0 && BitConverter.DoubleToInt64Bits(number)<0)return "(-0.0)";
  string text=number.ToString("R",CultureInfo.InvariantCulture);
  if(text.IndexOf('.')<0 && text.IndexOf('E')<0 && text.IndexOf('e')<0)text+=".0";
  return "("+text+")";
 }
 string RealNode(ClassicalRealExpression value) {
  switch(value.Kind) {
   case ClassicalRealExpression.NodeKind.Variable:return Slot(value.Slot,true);
   case ClassicalRealExpression.NodeKind.ArrayElement:return ArrayElement(value.Selection);
   case ClassicalRealExpression.NodeKind.TypedConstant:
    if(value.Type.Kind==ClassicalNumericType.NumericKind.Angle)return Cast(NumericTypeName(value.Type),Literal(value.Type.Width,value.Raw));
    double number=value.Type.Width==64 ? BitConverter.Int64BitsToDouble(unchecked((long)value.Raw)) : BitConverter.ToSingle(BitConverter.GetBytes((uint)value.Raw),0);
    return Cast(NumericTypeName(value.Type),FloatLiteral(number));
   case ClassicalRealExpression.NodeKind.TypedInteger:return Cast(NumericTypeName(value.Type),IntegerNode(value.Integer));
   case ClassicalRealExpression.NodeKind.Cast:return Cast(NumericTypeName(value.Type),RealNode(value.Left));
   case ClassicalRealExpression.NodeKind.Bits:return Cast(NumericTypeName(value.Type),BitNode(value.BitOperand));
   case ClassicalRealExpression.NodeKind.Function:
    if(value.FunctionCode==ClassicalRealExpression.FunctionKind.Negate)return "(-"+RealNode(value.Left)+")";
    if(value.FunctionCode==ClassicalRealExpression.FunctionKind.Complement)return "(~"+RealNode(value.Left)+")";
    return value.FunctionCode.ToString().ToLowerInvariant()+"("+RealNode(value.Left)+")";
   case ClassicalRealExpression.NodeKind.Scale:
    return Binary(RealNode(value.Left),new[]{"*","/","<<",">>"}[(int)value.ScaleCode],IntegerNode(value.Integer));
  }
  if(value.Kind==ClassicalRealExpression.NodeKind.Integer)
   return Cast("float[64]",IntegerNode(value.Integer));
  if(value.Kind==ClassicalRealExpression.NodeKind.Constant) {
   // Round-trip binary64 values, including signed zero, without turning an
   // integral-valued real into an OpenQASM integer operand.
   if(value.Value==0 && BitConverter.DoubleToInt64Bits(value.Value)<0)return "(-0.0)";
   string text=value.Value.ToString("R",CultureInfo.InvariantCulture);
   if(text.IndexOf('.')<0 && text.IndexOf('E')<0 && text.IndexOf('e')<0)text+=".0";
   return "("+text+")";
  }
  if(value.Operation==ClassicalRealExpression.Operator.Mod)return "mod("+RealNode(value.Left)+", "+RealNode(value.Right)+")";
  string[] operators={"+","-","*","/","**","","&","|","^"};
  return Binary(RealNode(value.Left),operators[(int)value.Operation],RealNode(value.Right));
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
 string Compare(E value) {
  T common=T.Common(value.IntegerLeft.Type,value.IntegerRight.Type);
  return Binary(Cast(TypeName(common),IntegerNode(value.IntegerLeft)),BitOperator(value.Operation),
                Cast(TypeName(common),IntegerNode(value.IntegerRight)));
 }
 string BitNode(E value) {
  switch(value.Kind) {
   case E.NodeKind.Constant:return Literal(value.Width,value.Value);
   case E.NodeKind.Read:return Read(value.Indices);
   case E.NodeKind.Complement:return "(~"+BitNode(value.Left)+")";
   // Unrolling can replace a typed iterator with an untyped literal. Retain
   // its declared width at the integer-to-register boundary.
   case E.NodeKind.IntegerBits:return Cast(BitType(value.Width),Cast(TypeName(value.IntegerLeft.Type),IntegerNode(value.IntegerLeft)));
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
 string IntegerNode(I value) {
  switch(value.Kind) {
   case I.NodeKind.NumericCast:return Cast(TypeName(value.Type),RealNode(value.NumericLeft));
   case I.NodeKind.AngleRatio:return Binary(RealNode(value.NumericLeft),"/",RealNode(value.NumericRight));
   case I.NodeKind.AngleBits:return Cast(TypeName(value.Type),Cast(BitType(value.Type.Width),RealNode(value.NumericLeft)));
   case I.NodeKind.NumericCompare:
    return Binary(Cast("int[64]",Binary(RealNode(value.NumericLeft),">",RealNode(value.NumericRight))),"-",Cast("int[64]",Binary(RealNode(value.NumericLeft),"<",RealNode(value.NumericRight))));
   case I.NodeKind.Constant:return Cast(TypeName(value.Type),IntegerLiteral(value));
   case I.NodeKind.Read:return Cast(TypeName(value.Type),Read(value.Indices));
   case I.NodeKind.Variable:return Slot(value.Slot,false);
   case I.NodeKind.ArrayElement:return ArrayElement(value.Selection);
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
