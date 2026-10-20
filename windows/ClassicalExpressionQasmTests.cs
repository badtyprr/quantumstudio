// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.IO;
using System.Globalization;
using System.Web.Script.Serialization;
using E=ClassicalExpression;
using I=ClassicalIntegerExpression;
using T=ClassicalIntegerType;

static class ClassicalExpressionQasmTests {
 static readonly List<object> cases=new List<object>();
 static readonly T signed8=T.Create(T.Sign.Signed,8);
 static readonly T unsigned8=T.Create(T.Sign.Unsigned,8);
 static readonly ClassicalExpressionQasm serializer=new ClassicalExpressionQasm(8,new[]{signed8});
 static string Binary(ulong value,int width) {
  char[] s=new char[width];
  for(int i=0;i<width;i++)s[width-i-1]=(value&(1UL<<i))==0 ? '0' : '1';
  return new string(s);
 }
 static string Prefix(int width,ulong initial) {
  return "OPENQASM 3; include \"stdgates.inc\"; qubit q; reset q; x q; bit["+width+"] c=\""+
   Binary(initial,width)+"\"; c[0]=measure q; ";
 }
 static void Bit(string name,E value,ulong expected) {
  cases.Add(new {name=name,source=Prefix(8,129)+"int[8] v0=int[8](c); bit["+value.Width+"] out; out="+serializer.Bits(value)+";",
    expected=Binary(expected,value.Width)+Binary(129,8)});
 }
 static void Integer(string name,I value,ulong expected) {
  string expression=serializer.Integer(value);
  string type=value.Type.Signedness==T.Sign.Signed ? "int[64]" : "uint[64]";
  string literal=value.Type.Signedness==T.Sign.Signed ? unchecked((long)expected).ToString(CultureInfo.InvariantCulture) : expected.ToString(CultureInfo.InvariantCulture);
  // Test both equality and inequality against independently calculated values.
  cases.Add(new {name=name,source=Prefix(8,129)+"int[8] v0=int[8](c); bit[2] out; out[0]=bit[1](("+expression+")=="+
    type+"("+literal+")); out[1]=bit[1](("+expression+")!="+type+"("+literal+"));",
    expected="01"+Binary(129,8)});
 }
 static void Reject(Action action) {
  try{action();}catch(ArgumentException){return;}
  throw new Exception("Invalid expression context accepted.");
 }
 static void Main(string[] args) {
  if(args.Length!=1)throw new ArgumentException("Pass a fresh JSON case file.");
  if(File.Exists(args[0]))throw new ArgumentException("Preserve previous cases.");
  Reject(()=>new ClassicalExpressionQasm(65));
  Reject(()=>serializer.Bits(E.Read(8)));
  Reject(()=>serializer.Integer(I.Variable(unsigned8,0)));
  Reject(()=>serializer.Bits(null));
  E c=E.Read(0,1,2,3,4,5,6,7);
  Bit("constant",E.Constant(8,7),7);
  Bit("read",c,129);
  Bit("repeated-selection",E.Read(0,0,7),7);
  Bit("complement",E.Complement(c),126);
  Bit("and",E.Binary(E.Operator.And,c,E.Constant(8,15)),1);
  Bit("or",E.Binary(E.Operator.Or,c,E.Constant(8,14)),143);
  Bit("xor",E.Binary(E.Operator.Xor,c,E.Constant(8,255)),126);
  Bit("shift-left",E.Binary(E.Operator.ShiftLeft,c,E.Constant(8,1)),2);
  Bit("shift-right",E.Binary(E.Operator.ShiftRight,c,E.Constant(8,1)),64);
  Bit("shift-out",E.Binary(E.Operator.ShiftLeft,c,E.Constant(64,UInt64.MaxValue)),0);
  Bit("equal",E.Binary(E.Operator.Equal,c,E.Constant(8,129)),1);
  Bit("not-equal",E.Binary(E.Operator.NotEqual,c,E.Constant(8,129)),0);
  Bit("less",E.Binary(E.Operator.Less,c,E.Constant(8,130)),1);
  Bit("less-equal",E.Binary(E.Operator.LessEqual,c,E.Constant(8,128)),0);
  Bit("greater",E.Binary(E.Operator.Greater,c,E.Constant(8,128)),1);
  Bit("greater-equal",E.Binary(E.Operator.GreaterEqual,c,E.Constant(8,130)),0);
  E yes=E.Binary(E.Operator.Equal,c,E.Constant(8,129)),no=E.Binary(E.Operator.Equal,c,E.Constant(8,0));
  Bit("logical-and",E.Logical(E.Operator.And,yes,no),0);
  Bit("logical-or",E.Logical(E.Operator.Or,yes,no),1);
  Bit("signed-rotation",E.Rotate(E.Direction.Left,c,c,E.Distance.Signed),3);
  Bit("unsigned-rotation",E.Rotate(E.Direction.Right,c,c,E.Distance.Unsigned),192);
  I read=I.Read(signed8,0,1,2,3,4,5,6,7),minusOne=I.Constant(signed8,255);
  Bit("integer-less",E.IntegerCompare(E.Operator.Less,read,minusOne),1);
  Bit("integer-greater",E.IntegerCompare(E.Operator.Greater,read,minusOne),0);
  Bit("integer-bits",E.FromInteger(read),129);
  Integer("integer-constant",minusOne,UInt64.MaxValue);
  Integer("signed-one-bit",I.Constant(T.Create(T.Sign.Signed,1),1),UInt64.MaxValue);
  Integer("signed-63-minimum",I.Constant(T.Create(T.Sign.Signed,63),1UL<<62),unchecked((ulong)-(1L<<62)));
  Integer("signed-64-minimum",I.Constant(T.Create(T.Sign.Signed,64),1UL<<63),1UL<<63);
  Integer("unsigned-64-maximum",I.Constant(T.Create(T.Sign.Unsigned,64),UInt64.MaxValue),UInt64.MaxValue);
  Integer("integer-read",read,unchecked((ulong)-127L));
  Integer("integer-variable",I.Variable(signed8,0),unchecked((ulong)-127L));
  Integer("integer-cast",I.Cast(unsigned8,read),129);
  Integer("integer-from-bits",I.FromBits(unsigned8,c),129);
  Integer("add",I.Binary(I.Operator.Add,read,I.Constant(signed8,127)),0);
  Integer("subtract",I.Binary(I.Operator.Subtract,read,I.Constant(signed8,1)),unchecked((ulong)-128L));
  Integer("multiply",I.Binary(I.Operator.Multiply,read,minusOne),127);
  Integer("divide",I.Binary(I.Operator.Divide,read,I.Constant(signed8,2)),unchecked((ulong)-63L));
  Integer("remainder",I.Binary(I.Operator.Remainder,read,I.Constant(signed8,2)),UInt64.MaxValue);
  Integer("power",I.Binary(I.Operator.Power,read,I.Constant(signed8,2)),16129);
  int[] all=new int[64];for(int i=0;i<64;i++)all[i]=i;
  string population=new ClassicalExpressionQasm(64).Bits(E.PopulationCount(E.Read(all)));
  cases.Add(new {name="population-count",source=Prefix(64,(1UL<<63)|1)+"c="+population+";",expected=Binary(2,64)});
  File.WriteAllText(args[0],new JavaScriptSerializer().Serialize(cases));
  Console.WriteLine("PASS: four invalid-context checks; "+cases.Count+" OpenQASM semantic cases generated.");
 }
}
