// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using N=ClassicalCircuit.ExpressionNode;
using R=ClassicalCircuit.RealNode;
using System.Text.RegularExpressions;

// Text syntax is independent of WPF and resolves to the validated file model.
static class ClassicalExpressionText {
 static readonly string[] Symbols={"||","&&","|","^","&","==","!=","<",">","<=",">=","<<",">>","+","-","*","/","%","**"};
 static readonly string[] Names={"LogicalOr","LogicalAnd","Or","Xor","And","Equal","NotEqual","Less","Greater","LessEqual","GreaterEqual","ShiftLeft","ShiftRight","Add","Subtract","Multiply","Divide","Remainder","Power"};
 static readonly int[] Priority={1,2,3,4,5,6,6,7,7,7,7,8,8,9,9,10,10,10,12};
 static bool Comparison(string op){return op=="Equal" || op=="NotEqual" || op=="Less" || op=="Greater" || op=="LessEqual" || op=="GreaterEqual";}
 static int Minimum(ulong value){int width=1;while((value>>=1)!=0)width++;return width;}
 public static string FormatArray(ClassicalCircuit.ArraySelectionNode selection,ClassicalCircuit.Document context) {
  return "array("+selection.Array.ToString(CultureInfo.InvariantCulture)+", "+String.Join(", ",Array.ConvertAll(selection.Indices,index=>Format(index,context)))+")";
 }
 public static ClassicalCircuit.ArraySelectionNode ParseArrayTarget(string text,ClassicalCircuit.Document context,bool numeric) {
  ClassicalCircuit.ArraySelectionNode selection;
  if(numeric)selection=ParseNumeric(text,context).Selection;
  else {var node=ParseInteger(text,context);selection=node.Kind=="IntegerArrayElement" ? node.Selection : null;}
  if(selection==null)throw new ArgumentException("An array target must be one indexed element.");return selection;
 }
 public static N Parse(string text,ClassicalCircuit.Document context,int width) {
  if(context==null || width<1 || width>64)throw new ArgumentException("Use a valid circuit and 1–64 result bits.");
  var parser=new Parser(text,context.Registers,context.Variables,context.NumericVariables,context.Arrays);var value=parser.Expression(1,0);parser.End();value=Normalize(value,0);
  if(Numeric(value))throw new ArgumentException("Compare numeric values or cast them to bits.");
  if(IntegerValue(value))throw new ArgumentException("Compare integer values to produce a one-bit condition.");
  if(Resolve(value,width,0)!=width)throw new ArgumentException("Expression width must match the assignment or one-bit condition.");
  var step=width==1 ? new ClassicalCircuit.Step{Kind="ExpressionBranch",ClassicalValue=value,WhenTrue=new ClassicalCircuit.Step[0],WhenFalse=new ClassicalCircuit.Step[0]} :
   new ClassicalCircuit.Step{Kind="Assign",ClassicalValue=value,Wires=Enumerable.Range(0,width).ToArray()};
  ClassicalCircuit.From(new ClassicalCircuit.Document{Version=Math.Max(RequiredVersion(value),context.Version),Qubits=0,LoopConditionBudget=context.LoopConditionBudget??(RequiredVersion(value)>=7 ? (int?)1000000 : null),Arrays=context.Arrays,Registers=context.Registers,NumericVariables=context.NumericVariables??(RequiredVersion(value)>=13 ? new ClassicalCircuit.NumericVariable[0] : null),Variables=context.Variables ?? (RequiredVersion(value)>=5 ? new ClassicalCircuit.Variable[0] : null),OutputBits=new int[0],Steps=new[]{step}});
  return value;
 }
 public static N ParseInteger(string text,ClassicalCircuit.Document context) {
  if(context==null)throw new ArgumentNullException("context");
  var parser=new Parser(text,context.Registers,context.Variables,context.NumericVariables,context.Arrays);var value=parser.Expression(1,0);parser.End();
  value=AsInteger(Normalize(value,0));ResolveInteger(value,0);
  int version=Math.Max(context.Version,RequiredVersion(value));
  ClassicalCircuit.ValidateIntegerExpression(value,new ClassicalCircuit.Document{Version=version,Qubits=0,LoopConditionBudget=context.LoopConditionBudget??(RequiredVersion(value)>=7 ? (int?)1000000 : null),Arrays=context.Arrays,Registers=context.Registers,NumericVariables=context.NumericVariables??(RequiredVersion(value)>=13 ? new ClassicalCircuit.NumericVariable[0] : null),Variables=context.Variables ?? (version>=5 ? new ClassicalCircuit.Variable[0] : null),OutputBits=new int[0],Steps=new ClassicalCircuit.Step[0]});
  return value;
 }
 static bool Numeric(N n){return n!=null && n.Kind=="NumericOperand";}
 static N Numeric(R value,string kind,int width){return new N{Kind="NumericOperand",RealLeft=value,Signedness=kind,Width=width};}
 static N Real(N value,int width=64) {
  if(Numeric(value))return value;
  return Numeric(new R{Kind="TypedInteger",Width=width,IntegerValue=AsInteger(value)},"Float",width);
 }
 static int RealWidth(R value){return value.Width ?? (value.Kind=="Binary" ? Math.Max(RealWidth(value.Left),RealWidth(value.Right)) : value.Kind=="Function" && (value.Function=="Sin" || value.Function=="Cos" || value.Function=="Tan") && RealKind(value.Left)=="Angle" ? 64 : value.Left!=null ? RealWidth(value.Left) : 64);}
 static string RealKind(R value){return value.NumericKind ?? (value.Kind=="Bits" ? "Angle" : value.Kind=="Function" && (value.Function=="Sin" || value.Function=="Cos" || value.Function=="Tan") ? "Float" : value.Left!=null ? RealKind(value.Left) : "Float");}
 static int IntegerWidth(N value){return value.Kind=="AngleBits" || value.Kind=="AngleRatio" ? RealWidth(value.RealLeft) : value.Width ?? 0;}
 static N NumericTruth(N value) {
  if(!Numeric(value))return Normalize(new N{Kind="BooleanCast",Left=value},0);
  return new N{Kind="IntegerCompare",Operator="NotEqual",Left=new N{Kind="NumericCompare",RealLeft=value.RealLeft,RealRight=new R{Kind="TypedConstant",NumericKind=value.Signedness,Width=value.Width,ValueBits="0"}},Right=new N{Kind="IntegerConstant",Signedness="Signed",Width=0,Value="0"}};
 }
 static N NumericBinary(N n) {
  var left=n.Left;var right=n.Right;
  if(n.Operator=="LogicalAnd" || n.Operator=="LogicalOr")return new N{Kind="Logical",Operator=n.Operator=="LogicalAnd" ? "And" : "Or",Left=NumericTruth(left),Right=NumericTruth(right)};
  if(Numeric(left) && left.Signedness=="Angle" && !Numeric(right) && (n.Operator=="Multiply" || n.Operator=="Divide" || n.Operator=="ShiftLeft" || n.Operator=="ShiftRight"))
   return Numeric(new R{Kind="Scale",Scaling=n.Operator,Left=left.RealLeft,IntegerValue=AsInteger(right)},"Angle",left.Width.Value);
  left=Real(left,Numeric(right) && right.Signedness=="Float" ? right.Width.Value : 64);right=Real(right,left.Signedness=="Float" ? left.Width.Value : 64);
  if(Comparison(n.Operator))return new N{Kind="IntegerCompare",Operator=n.Operator,Left=new N{Kind="NumericCompare",RealLeft=left.RealLeft,RealRight=right.RealLeft},Right=new N{Kind="IntegerConstant",Signedness="Signed",Width=0,Value="0"}};
  if(left.Signedness=="Angle" && right.Signedness=="Angle" && n.Operator=="Divide")return new N{Kind="AngleRatio",RealLeft=left.RealLeft,RealRight=right.RealLeft};
  return Numeric(new R{Kind="Binary",Operator=n.Operator,Left=left.RealLeft,Right=right.RealLeft},left.Signedness,Math.Max(left.Width.Value,right.Width.Value));
 }
 public static bool NeedsNumeric(string text,ClassicalCircuit.Document context) {
  if(text==null)return false;
  if(Regex.IsMatch(text,@"\b(?:float|angle)\s*\[|\b(?:sin|cos|tan|arcsin|arccos|arctan|exp|log|sqrt|floor|ceiling|mod|compare|anglebits|numeric|angle)\s*\("))return true;
  return (context.NumericVariables??new ClassicalCircuit.NumericVariable[0]).Any(v=>Regex.IsMatch(text,@"(?<![\w])"+Regex.Escape(v.Name)+@"(?![\w])"));
 }
 public static R ParseNumeric(string text,ClassicalCircuit.Document context,int targetWidth=64) {
  var parser=new Parser(text,context.Registers,context.Variables,context.NumericVariables,context.Arrays);var result=parser.Expression(1,0);parser.End();var numeric=Real(Normalize(result,0),targetWidth).RealLeft;
  ClassicalCircuit.From(new ClassicalCircuit.Document{Version=Math.Max(13,context.Version),Qubits=1,Arrays=context.Arrays,Registers=context.Registers,Variables=context.Variables??new ClassicalCircuit.Variable[0],NumericVariables=context.NumericVariables??new ClassicalCircuit.NumericVariable[0],LoopConditionBudget=1000000,OutputBits=new int[0],Steps=new[]{new ClassicalCircuit.Step{Kind="Rotation",Axis="Y",Angle=numeric,Wires=new[]{0}}}});
  return numeric;
 }
 public static string FormatNumeric(R value,ClassicalCircuit.Document context) {
  if(value.Kind=="ArrayElement")return FormatArray(value.Selection,context);
  if(value.Kind=="Variable") {
   string name=context.NumericVariables[value.Slot.Value].Name;
   var reserved=new[]{"pi","π","float","angle","numeric","sin","cos","tan","arcsin","arccos","arctan","exp","log","sqrt","floor","ceiling","mod","compare","anglebits"};
   if(Regex.IsMatch(name,@"\A[A-Za-z_][A-Za-z0-9_]*\z") && !reserved.Contains(name))return name;
   return "numeric("+value.Slot.Value.ToString(CultureInfo.InvariantCulture)+")";
  }
  if(value.Kind=="Integer" || value.Kind=="TypedInteger")return "float["+(value.Width??64)+"]("+Format(value.IntegerValue,context)+")";
  if(value.Kind=="Constant" || value.Kind=="TypedConstant") {
   ulong bits=UInt64.Parse(value.ValueBits,CultureInfo.InvariantCulture);
   if(value.NumericKind=="Angle") {var chars=new char[value.Width.Value];for(int i=0;i<chars.Length;i++)chars[chars.Length-i-1]=((bits>>i)&1)==0 ? '0' : '1';return "angle["+value.Width+"](\""+new string(chars)+"\")";}
   double number=value.Width==32 ? BitConverter.ToSingle(BitConverter.GetBytes((uint)bits),0) : BitConverter.Int64BitsToDouble(unchecked((long)bits));
   string text=number==0 && ((value.Width==32 ? bits>>31 : bits>>63)!=0) ? "-0.0" : number.ToString("R",CultureInfo.InvariantCulture);
   if(text.IndexOf('.')<0 && text.IndexOf('E')<0 && text.IndexOf('e')<0)text+=".0";
   return (value.Kind=="Constant" || value.Width==64) ? text : "float["+value.Width+"]("+text+")";
  }
  if(value.Kind=="Cast")return value.NumericKind.ToLowerInvariant()+"["+value.Width+"]("+FormatNumeric(value.Left,context)+")";
  if(value.Kind=="Bits")return "angle["+value.Width+"]("+Format(value.BitValue,context)+")";
  if(value.Kind=="Function")return value.Function=="Negate" ? "(-"+FormatNumeric(value.Left,context)+")" : value.Function=="Complement" ? "(~"+FormatNumeric(value.Left,context)+")" : value.Function.ToLowerInvariant()+"("+FormatNumeric(value.Left,context)+")";
  if(value.Kind=="Scale")return "("+FormatNumeric(value.Left,context)+" "+Symbols[Array.IndexOf(Names,value.Scaling)]+" "+Format(value.IntegerValue,context)+")";
  if(value.Operator=="Mod")return "mod("+FormatNumeric(value.Left,context)+", "+FormatNumeric(value.Right,context)+")";
  return "("+FormatNumeric(value.Left,context)+" "+Symbols[Array.IndexOf(Names,value.Operator)]+" "+FormatNumeric(value.Right,context)+")";
 }
 static bool IntegerValue(N n){return n!=null && (n.Kind=="NumericCast" || n.Kind=="NumericCompare" || n.Kind=="AngleRatio" || n.Kind=="AngleBits" || n.Kind.StartsWith("Integer",StringComparison.Ordinal)) && n.Kind!="IntegerCompare" && n.Kind!="IntegerBits";}
 static bool Arithmetic(string op){return op=="Add" || op=="Subtract" || op=="Multiply" || op=="Divide" || op=="Remainder" || op=="Power";}
 static N AsInteger(N n) {
  if(IntegerValue(n))return n;
  if(n.Kind=="Constant" && !n.Width.HasValue) {
   ulong value=UInt64.Parse(n.Value,CultureInfo.InvariantCulture);
   return new N{Kind="IntegerConstant",Signedness=value>Int64.MaxValue ? "Unsigned" : "Signed",Width=0,Value=n.Value};
  }
  throw new ArgumentException("Cast bit values explicitly with int[width](...) or uint[width](...) before integer arithmetic.");
 }
 static N Normalize(N n,int depth) {
  if(depth>=128)throw new ArgumentException("Expression nesting is too deep.");
  if(n.Kind=="IntegerCast" && n.Left.Kind=="UnaryMinus" && n.Left.Left.Kind=="Constant" && !n.Left.Left.Width.HasValue) {
   // A typed negative literal is a constant, just like int[8](127).
   // Keep explicit nested casts as nodes so formatted documents round-trip.
   ulong magnitude=UInt64.Parse(n.Left.Left.Value,CultureInfo.InvariantCulture);
   if(magnitude>(1UL<<63))throw new ArgumentException("Negative literals must fit signed 64 bits.");
   ulong bits=unchecked(0UL-magnitude);int width=n.Width==0 ? 64 : n.Width.Value;
   if(width<64)bits&=(1UL<<width)-1;
   return new N{Kind="IntegerConstant",Signedness=n.Signedness,Width=n.Width,Value=bits.ToString(CultureInfo.InvariantCulture)};
  }
  if(n.Left!=null)n.Left=Normalize(n.Left,depth+1);if(n.Right!=null)n.Right=Normalize(n.Right,depth+1);
  if(n.Kind=="RealCast") {
   if(n.Signedness=="Angle" && (n.Left.Kind=="Read" || n.Left.Kind=="Constant" && n.Left.Width.HasValue || n.Left.Kind=="IntegerBits"))return Numeric(new R{Kind="Bits",Width=n.Width,BitValue=n.Left},"Angle",n.Width.Value);
   if(n.Signedness=="Float" && !Numeric(n.Left))return Real(n.Left,n.Width.Value);
   var value=Real(n.Left,n.Signedness=="Float" ? n.Width.Value : 64);
   if(value.Signedness==n.Signedness && value.Width==n.Width)return value;
   return Numeric(new R{Kind="Cast",NumericKind=n.Signedness,Width=n.Width,Left=value.RealLeft},n.Signedness,n.Width.Value);
  }
  if(n.Kind=="NumericFunction") {
   if(n.Operator=="AngleBits")return new N{Kind="AngleBits",RealLeft=Real(n.Left).RealLeft};
   var left=Real(n.Left);
   if(n.Operator=="Compare")return new N{Kind="NumericCompare",RealLeft=left.RealLeft,RealRight=Real(n.Right).RealLeft};
   if(n.Operator=="Mod"){var right=Real(n.Right);return Numeric(new R{Kind="Binary",Operator="Mod",Left=left.RealLeft,Right=right.RealLeft},"Float",Math.Max(left.Width.Value,right.Width.Value));}
   bool trig=n.Operator=="Sin" || n.Operator=="Cos" || n.Operator=="Tan";
   return Numeric(new R{Kind="Function",Function=n.Operator,Left=left.RealLeft},"Float",trig && left.Signedness=="Angle" ? 64 : left.Width.Value);
  }
  if(Numeric(n.Left)) {
   if(n.Kind=="IntegerCast")return new N{Kind="NumericCast",Signedness=n.Signedness,Width=n.Width,RealLeft=n.Left.RealLeft};
   if(n.Kind=="BooleanCast" || n.Kind=="LogicalNot") {var truth=NumericTruth(n.Left);return n.Kind=="BooleanCast" ? truth : new N{Kind="Complement",Left=truth};}
   if(n.Kind=="BitCast" && n.Left.Signedness=="Angle" && n.Width==n.Left.Width)return new N{Kind="IntegerBits",Left=new N{Kind="AngleBits",RealLeft=n.Left.RealLeft}};
   if(n.Kind=="UnaryMinus" || n.Kind=="Complement")return Numeric(new R{Kind="Function",Function=n.Kind=="UnaryMinus" ? "Negate" : "Complement",Left=n.Left.RealLeft},n.Left.Signedness,n.Left.Width.Value);
  }
  if(n.Kind=="Binary" && (Numeric(n.Left) || Numeric(n.Right)))return NumericBinary(n);
  if(n.Kind=="BooleanCast") {
   bool integer=IntegerValue(n.Left);
   return new N{Kind=integer ? "IntegerCompare" : "Binary",Operator="NotEqual",Left=n.Left,
    Right=integer ? new N{Kind="IntegerConstant",Signedness="Signed",Width=0,Value="0"} : new N{Kind="Constant",Value="0"}};
  }
  if(n.Kind=="BitCast") {
   if(!IntegerValue(n.Left) || IntegerWidth(n.Left)==0 || IntegerWidth(n.Left)!=n.Width)throw new ArgumentException("Bit casts require an explicitly sized integer of the same width.");
   return new N{Kind="IntegerBits",Left=n.Left};
  }
  if(n.Kind=="UnaryMinus") {
   if(n.Left.Kind=="Constant" && !n.Left.Width.HasValue) {
    ulong magnitude=UInt64.Parse(n.Left.Value,CultureInfo.InvariantCulture);
    if(magnitude>(1UL<<63))throw new ArgumentException("Negative literals must fit signed 64 bits.");
    return new N{Kind="IntegerConstant",Signedness="Signed",Width=0,Value=unchecked(0UL-magnitude).ToString(CultureInfo.InvariantCulture)};
   }
   return new N{Kind="IntegerBinary",Operator="Subtract",Left=new N{Kind="IntegerConstant",Signedness="Signed",Width=0,Value="0"},Right=AsInteger(n.Left)};
  }
  if(n.Kind=="IntegerCast") {
   if(IntegerValue(n.Left))return n;
   int width=n.Width==0 ? 64 : n.Width.Value;
   if(n.Left.Kind=="Read") {
    if(n.Left.Bits.Length!=width)throw new ArgumentException("Bit-to-integer casts require matching widths.");
    return new N{Kind="IntegerRead",Signedness=n.Signedness,Width=n.Width,Bits=n.Left.Bits};
   }
   if(n.Left.Kind=="Constant") {
    if(n.Left.Width.HasValue && n.Left.Width.Value!=width)throw new ArgumentException("Bit-to-integer casts require matching widths.");
    ulong value=UInt64.Parse(n.Left.Value,CultureInfo.InvariantCulture);if(width<64)value&=(1UL<<width)-1;
    return new N{Kind="IntegerConstant",Signedness=n.Signedness,Width=n.Width,Value=value.ToString(CultureInfo.InvariantCulture)};
   }
   if(RequiredVersion(n.Left)>=13 && (n.Left.Kind=="IntegerCompare" || n.Left.Kind=="Logical" || n.Left.Kind=="Binary" && Comparison(n.Left.Operator)))
    return new N{Kind="IntegerCast",Signedness=n.Signedness,Width=n.Width,Left=new N{Kind="IntegerFromBits",Signedness="Unsigned",Width=1,Left=n.Left}};
   return new N{Kind="IntegerFromBits",Signedness=n.Signedness,Width=n.Width,Left=n.Left};
  }
  if(n.Kind=="Binary" && (Arithmetic(n.Operator) || IntegerValue(n.Left) || IntegerValue(n.Right))) {
   if(!Arithmetic(n.Operator) && !Comparison(n.Operator))throw new ArgumentException("Use arithmetic or comparison operators with integers.");
   n.Kind=Comparison(n.Operator) ? "IntegerCompare" : "IntegerBinary";n.Left=AsInteger(n.Left);n.Right=AsInteger(n.Right);
  }
  return n;
 }
 public static int RequiredVersion(N value){return RequiredVersion(value,0);}
 static int RequiredVersion(N n,int depth) {
  if(n==null)return 3;if(depth>=32)throw new ArgumentException("Expressions allow at most 32 levels.");
  if(n.Selection!=null)return 15;
  return Math.Max(n.RealLeft!=null || n.RealRight!=null ? 13 : n.Kind=="IntegerFromBits" ? 6 : n.Kind=="IntegerVariable" ? 5 : (n.Kind=="Logical" || n.Kind.StartsWith("Integer",StringComparison.Ordinal)) ? 4 : 3,Math.Max(RequiredVersion(n.Left,depth+1),RequiredVersion(n.Right,depth+1)));
 }
 static void ResolveInteger(N n,int depth) {
  if(depth>=32)throw new ArgumentException("Expressions allow at most 32 levels.");
  if(!IntegerValue(n))throw new ArgumentException("Expected an integer expression.");
  if(n.RealLeft!=null || n.RealRight!=null)return;
  if(n.Kind=="IntegerFromBits") {
   int width=n.Width==0 ? 64 : n.Width.Value;
   if(Resolve(n.Left,width,depth+1)!=width)throw new ArgumentException("Bit-to-integer casts require matching widths.");
   return;
  }
  if(n.Left!=null)ResolveInteger(n.Left,depth+1);if(n.Right!=null)ResolveInteger(n.Right,depth+1);
 }
 static int? Known(N n) {
  if(n.Kind=="IntegerBits")return IntegerWidth(n.Left);
  if(n.Kind=="IntegerCompare")return 1;
  if(n.Kind=="Constant")return n.Width;
  if(n.Kind=="Read")return n.Bits.Length;
  if(n.Kind=="LogicalNot")return 1;
  if(n.Kind=="PopulationCount")return 64;
  if(n.Kind=="Rotate")return Known(n.Left);
  if(n.Kind=="Complement")return Known(n.Left);
  return Comparison(n.Operator) || n.Operator.StartsWith("Logical",StringComparison.Ordinal) ? 1 : Known(n.Left) ?? Known(n.Right);
 }
 static int Natural(N n){return Known(n) ?? (n.Kind=="Constant" ? Minimum(UInt64.Parse(n.Value,CultureInfo.InvariantCulture)) : 1);}
 static int Resolve(N n,int? hint,int depth) {
  if(depth>=32)throw new ArgumentException("Expressions allow at most 32 levels.");
  if(n.Kind=="IntegerBits"){ResolveInteger(n.Left,depth+1);return IntegerWidth(n.Left);}
  if(n.Kind=="IntegerCompare"){ResolveInteger(n.Left,depth+1);ResolveInteger(n.Right,depth+1);return 1;}
  if(IntegerValue(n))throw new ArgumentException("Compare integer values before using bit operators.");
  if(n.Kind=="Constant"){n.Width=n.Width ?? hint ?? Natural(n);return n.Width.Value;}
  if(n.Kind=="Read")return n.Bits.Length;
  if(n.Kind=="PopulationCount"){Resolve(n.Left,null,depth+1);return 64;}
  if(n.Kind=="Rotate") {
   int width=Resolve(n.Left,hint,depth+1);
   Resolve(n.Right,n.DistanceInterpretation=="Signed" ? (int?)64 : null,depth+1);return width;
  }
  if(n.Kind=="Complement" || n.Kind=="LogicalNot") {
   int size=Resolve(n.Left,hint,depth+1);
   if(n.Kind=="LogicalNot" && size!=1)throw new ArgumentException("Logical negation needs one bit.");
   n.Kind="Complement";return size;
  }
  bool compare=Comparison(n.Operator),logical=n.Operator.StartsWith("Logical",StringComparison.Ordinal),shift=n.Operator=="ShiftLeft" || n.Operator=="ShiftRight";
  int? common=logical ? (int?)1 : Known(n.Left) ?? (shift ? null : Known(n.Right)) ?? (compare ? null : hint);
  if(!common.HasValue && !shift)common=Math.Max(Natural(n.Left),Natural(n.Right));
  int left=Resolve(n.Left,common,depth+1),right=Resolve(n.Right,shift ? null : (int?)left,depth+1);
  if((!shift && left!=right) || (logical && left!=1))throw new ArgumentException("Expression operands have incompatible widths.");
  if(logical){n.Kind="Logical";n.Operator=n.Operator=="LogicalAnd" ? "And" : "Or";}
  return compare ? 1 : left;
 }
 public static string Format(N value,ClassicalCircuit.Document context=null){return FormatNode(value,0,context);}
 static string FormatNode(N n,int depth,ClassicalCircuit.Document context) {
  if(n.Kind=="IntegerArrayExtent")return FormatArray(n.Selection,context).Replace("array(","arrayextent(");
  if(n.Kind=="IntegerArrayElement")return FormatArray(n.Selection,context);
  if(n==null || depth>=32)throw new ArgumentException("Invalid expression tree.");
  if(n.Kind=="NumericCast")return (n.Signedness=="Signed" ? "int" : "uint")+(n.Width==0 ? "" : "["+n.Width+"]")+"("+FormatNumeric(n.RealLeft,context)+")";
  if(n.Kind=="NumericCompare")return "compare("+FormatNumeric(n.RealLeft,context)+", "+FormatNumeric(n.RealRight,context)+")";
  if(n.Kind=="AngleRatio")return "("+FormatNumeric(n.RealLeft,context)+" / "+FormatNumeric(n.RealRight,context)+")";
  if(n.Kind=="AngleBits")return "anglebits("+FormatNumeric(n.RealLeft,context)+")";
  // bool(...) parses back to these exact canonical comparisons. Retain other
  // zero types explicitly: changing signedness or width can change promotion.
  // Validated bit comparisons already require equal operand widths.
  if(n.Operator=="NotEqual" && n.Left!=null && n.Right!=null && n.Right.Value=="0" &&
     ((n.Kind=="IntegerCompare" && IntegerValue(n.Left) && n.Right.Kind=="IntegerConstant" && n.Right.Signedness=="Signed" && n.Right.Width==0) ||
      (n.Kind=="Binary" && !IntegerValue(n.Left) && n.Right.Kind=="Constant" && n.Right.Width>=1 && n.Right.Width<=64)))
   return "bool("+FormatNode(n.Left,depth+1,context)+")";
  if(n.Kind=="IntegerVariable") {
   int slot=n.Slot.Value;
   if(context!=null && context.Variables!=null && slot>=0 && slot<context.Variables.Length) {
    string name=context.Variables[slot].Name;
    if(!String.IsNullOrEmpty(name) && (Char.IsLetter(name[0]) || name[0]=='_') && name.All(c=>Char.IsLetterOrDigit(c) || c=='_') && name!="true" && name!="false")return name;
   }
   return "variable("+slot.ToString(CultureInfo.InvariantCulture)+")";
  }
  if(n.Kind=="IntegerBits")return "bit["+IntegerWidth(n.Left).ToString(CultureInfo.InvariantCulture)+"]("+FormatNode(n.Left,depth+1,context)+")";
  if(n.Kind=="IntegerConstant" || n.Kind=="IntegerRead" || n.Kind=="IntegerCast" || n.Kind=="IntegerFromBits") {
   string type=(n.Signedness=="Signed" ? "int" : "uint")+(n.Width==0 ? "" : "["+n.Width.Value.ToString(CultureInfo.InvariantCulture)+"]");
   string operand=n.Kind=="IntegerConstant" ? n.Value : n.Kind=="IntegerRead" ? "read("+String.Join(",",n.Bits)+")" : FormatNode(n.Left,depth+1,context);
   if(n.Kind=="IntegerConstant" && n.Signedness=="Signed") {
    int shift=64-(n.Width==0 ? 64 : n.Width.Value);
    operand=(unchecked((long)(UInt64.Parse(n.Value,CultureInfo.InvariantCulture)<<shift))>>shift).ToString(CultureInfo.InvariantCulture);
   }
   return type+"("+operand+")";
  }
  if(n.Kind=="IntegerBinary") {
   string[] names={"Add","Subtract","Multiply","Divide","Remainder","Power"},symbols={"+","-","*","/","%","**"};
   int code=Array.IndexOf(names,n.Operator);if(code<0)throw new ArgumentException("Unknown integer operator.");
   return "("+FormatNode(n.Left,depth+1,context)+" "+symbols[code]+" "+FormatNode(n.Right,depth+1,context)+")";
  }
  if(n.Kind=="Constant") {
   ulong value=UInt64.Parse(n.Value,CultureInfo.InvariantCulture);int width=n.Width.Value;var bits=new char[width];
   for(int i=0;i<width;i++)bits[width-i-1]=((value>>i)&1)==0 ? '0' : '1';
   return "\""+new string(bits)+"\"";
  }
  if(n.Kind=="Read")return "read("+String.Join(",",n.Bits)+")";
  if(n.Kind=="Complement")return "~("+FormatNode(n.Left,depth+1,context)+")";
  if(n.Kind=="PopulationCount")return "popcount("+FormatNode(n.Left,depth+1,context)+")";
  if(n.Kind=="Rotate") {
   string distance=n.DistanceInterpretation=="Signed" && n.Right.Kind=="Constant" && n.Right.Width==64 ? unchecked((long)UInt64.Parse(n.Right.Value,CultureInfo.InvariantCulture)).ToString(CultureInfo.InvariantCulture) : FormatNode(n.Right,depth+1,context);
   return (n.RotationDirection=="Left" ? "rotl" : "rotr")+(n.DistanceInterpretation=="Signed" ? "_signed" : "")+"("+FormatNode(n.Left,depth+1,context)+", "+distance+")";
  }
  if(n.Kind=="Logical")return "("+FormatNode(n.Left,depth+1,context)+(n.Operator=="And" ? " && " : " || ")+FormatNode(n.Right,depth+1,context)+")";
  int op=Array.IndexOf(Names,n.Operator);if(op<0)throw new ArgumentException("Unknown expression operator.");
  bool sharedWidth=n.Operator!="ShiftLeft" && n.Operator!="ShiftRight";
  string left=sharedWidth && n.Right.Kind=="PopulationCount" && n.Left.Kind=="Constant" && n.Left.Width==64 ? n.Left.Value : FormatNode(n.Left,depth+1,context);
  string right=sharedWidth && n.Left.Kind=="PopulationCount" && n.Right.Kind=="Constant" && n.Right.Width==64 ? n.Right.Value : FormatNode(n.Right,depth+1,context);
  return "("+left+" "+Symbols[op]+" "+right+")";
 }
 sealed class Parser {
  readonly string text;int position,nodes;readonly Dictionary<string,int[]> registers=new Dictionary<string,int[]>(StringComparer.Ordinal);
  readonly ClassicalCircuit.Variable[] variables;readonly ClassicalCircuit.NumericVariable[] numericVariables;readonly ClassicalCircuit.ArrayDeclaration[] arrays;
  public Parser(string value,ClassicalCircuit.Register[] declared,ClassicalCircuit.Variable[] variables,ClassicalCircuit.NumericVariable[] numericVariables=null,ClassicalCircuit.ArrayDeclaration[] arrays=null) {
   this.arrays=arrays??new ClassicalCircuit.ArrayDeclaration[0];
   this.variables=variables ?? new ClassicalCircuit.Variable[0];this.numericVariables=numericVariables??new ClassicalCircuit.NumericVariable[0];
   if(value==null || value.Length>65536 || declared==null)throw new ArgumentException("Enter an expression of at most 65536 characters.");
   text=value;int offset=0;foreach(var r in declared){registers.Add(r.Name,Enumerable.Range(offset,r.Size).ToArray());offset+=r.Size;}
  }
  void Space(){while(position<text.Length && Char.IsWhiteSpace(text[position]))position++;}
  bool Take(string token){Space();if(position+token.Length>text.Length || String.CompareOrdinal(text,position,token,0,token.Length)!=0)return false;position+=token.Length;return true;}
  void Need(string token){if(!Take(token))throw new ArgumentException("Expected '"+token+"' at position "+(position+1)+".");}
  N Node(N node){if(++nodes>1024)throw new ArgumentException("Expression parsing exceeds 1024 temporary nodes.");return node;}
  public void End(){Space();if(position!=text.Length)throw new ArgumentException("Unexpected expression text at position "+(position+1)+".");}
  ulong Number(){Space();int start=position;while(position<text.Length && text[position]>='0' && text[position]<='9')position++;ulong result;if(start==position || !UInt64.TryParse(text.Substring(start,position-start),NumberStyles.None,CultureInfo.InvariantCulture,out result))throw new ArgumentException("Expected an unsigned 64-bit integer.");return result;}
  int Index(){ulong value=Number();if(value>63)throw new ArgumentException("Bit indices must be 0–63.");return (int)value;}
  public N Expression(int minimum,int depth) {
   if(depth>=128)throw new ArgumentException("Expression nesting is too deep.");
   N left=Atom(depth+1);
   while(true) {
    Space();int op=-1;
    for(int i=0;i<Symbols.Length;i++)if(position+Symbols[i].Length<=text.Length && String.CompareOrdinal(text,position,Symbols[i],0,Symbols[i].Length)==0 && (op<0 || Symbols[i].Length>Symbols[op].Length))op=i;
    if(op<0 || Priority[op]<minimum)break;
    position+=Symbols[op].Length;var right=Expression(Priority[op]+(Names[op]=="Power" ? 0 : 1),depth+1);left=Node(new N{Kind="Binary",Operator=Names[op],Left=left,Right=right});
   }
   return left;
  }
  N Variable(int slot){var declaration=variables[slot];return Node(new N{Kind="IntegerVariable",Signedness=declaration.Signedness,Width=declaration.Width,Slot=slot});}
  N Atom(int depth) {
   if(depth>=128)throw new ArgumentException("Expression nesting is too deep.");
   if(Take("-"))return Node(new N{Kind="UnaryMinus",Left=Expression(11,depth+1)});
   if(Take("~"))return Node(new N{Kind="Complement",Left=Expression(11,depth+1)});
   if(Take("!"))return Node(new N{Kind="LogicalNot",Left=Expression(11,depth+1)});
   if(Take("(")){var value=Expression(1,depth+1);Need(")");return value;}
   if(Take("\"")) {
    ulong value=0;int width=0;
    while(position<text.Length && (text[position]=='0' || text[position]=='1')){if(++width>64)throw new ArgumentException("Bit strings allow 1–64 bits.");value=(value<<1)+(ulong)(text[position++]-'0');}
    if(position>=text.Length || text[position]!='"')throw new ArgumentException("A bit string may contain only 0 and 1.");position++;
    if(width==0)throw new ArgumentException("A bit string cannot be empty.");return Node(new N{Kind="Constant",Width=width,Value=value.ToString(CultureInfo.InvariantCulture)});
   }
   Space();var decimalNumber=Regex.Match(text.Substring(position),@"\A(?:[0-9]+\.[0-9]*|\.[0-9]+|[0-9]+[eE][+-]?[0-9]+)(?:[eE][+-]?[0-9]+)?");
   if(decimalNumber.Success) {position+=decimalNumber.Length;double number=Double.Parse(decimalNumber.Value,NumberStyles.Float,CultureInfo.InvariantCulture);return Node(Numeric(new R{Kind="TypedConstant",NumericKind="Float",Width=64,ValueBits=unchecked((ulong)BitConverter.DoubleToInt64Bits(number)).ToString(CultureInfo.InvariantCulture)},"Float",64));}
   Space();if(position<text.Length && Char.IsDigit(text[position]))return Node(new N{Kind="Constant",Value=Number().ToString(CultureInfo.InvariantCulture)});
   int start=position;while(position<text.Length && (Char.IsLetterOrDigit(text[position]) || text[position]=='_'))position++;
   string name=text.Substring(start,position-start);if(name.Length==0)throw new ArgumentException("Expected a register, bit string or integer.");
   if(name=="pi" || name=="π")return Node(Numeric(new R{Kind="TypedConstant",NumericKind="Float",Width=64,ValueBits=unchecked((ulong)BitConverter.DoubleToInt64Bits(Math.PI)).ToString(CultureInfo.InvariantCulture)},"Float",64));
   if(name=="float" || name=="angle") {
    int width=64;if(Take("[")){width=checked((int)Number());Need("]");}Need("(");var operand=Expression(1,depth+1);Need(")");
    return Node(new N{Kind="RealCast",Signedness=name=="float" ? "Float" : "Angle",Width=width,Left=operand});
   }
   if(new[]{"sin","cos","tan","arcsin","arccos","arctan","exp","log","sqrt","floor","ceiling","mod","compare","anglebits"}.Contains(name)) {
    Need("(");var left=Expression(1,depth+1);N right=null;if(name=="mod" || name=="compare"){Need(",");right=Expression(1,depth+1);}Need(")");
    return Node(new N{Kind="NumericFunction",Operator=name=="anglebits" ? "AngleBits" : Char.ToUpperInvariant(name[0])+name.Substring(1),Left=left,Right=right});
   }
   if((name=="array" || name=="arrayextent") && Take("(")) {
    ulong id=Number();if(id>=(ulong)arrays.Length)throw new ArgumentException("Unknown array.");var declaration=arrays[(int)id];var indices=new List<N>();
    while(Take(",")){if(indices.Count>=7)throw new ArgumentException("Array rank exceeds seven.");indices.Add(AsInteger(Normalize(Expression(1,depth+1),depth+1)));}Need(")");
    if(name=="arrayextent" ? indices.Count<1 || indices.Count>declaration.Dimensions.Length : indices.Count!=declaration.Dimensions.Length)throw new ArgumentException("Array index rank differs from its declaration.");
    var selection=new ClassicalCircuit.ArraySelectionNode{Array=(int)id,Indices=indices.ToArray(),Source="editor"};
    if(name=="arrayextent")return Node(new N{Kind="IntegerArrayExtent",Signedness="Signed",Width=0,Selection=selection});
    return declaration.NumericKind==null ? Node(new N{Kind="IntegerArrayElement",Signedness=declaration.Signedness,Width=declaration.Width,Selection=selection}) : Node(Numeric(new R{Kind="ArrayElement",NumericKind=declaration.NumericKind,Width=declaration.Width,Selection=selection},declaration.NumericKind,declaration.Width));
   }
   if(name=="numeric" && Take("(")){ulong slot=Number();Need(")");if(slot>=(ulong)numericVariables.Length)throw new ArgumentException("Unknown numeric slot.");var type=numericVariables[(int)slot];return Node(Numeric(new R{Kind="Variable",NumericKind=type.NumericKind,Width=type.Width,Slot=(int)slot},type.NumericKind,type.Width));}
   for(int slot=0;slot<numericVariables.Length;slot++)if(numericVariables[slot].Name==name){var type=numericVariables[slot];return Node(Numeric(new R{Kind="Variable",NumericKind=type.NumericKind,Width=type.Width,Slot=slot},type.NumericKind,type.Width));}
   if(name=="bool" && Take("(")){var operand=Expression(1,depth+1);Need(")");return Node(new N{Kind="BooleanCast",Left=operand});}
   if(name=="int" || name=="uint" || name=="bit") {
    int saved=position;bool explicitWidth=Take("["),typeShape=true;ulong width=0;
    if(explicitWidth){width=Number();typeShape=Take("]");}
    if(typeShape && Take("(")) {
     if(name=="bit" && !explicitWidth)throw new ArgumentException("Use an explicit width for bit-register casts.");
     if(width>64 || (explicitWidth && width==0))throw new ArgumentException("Integer widths must be 1–64.");
     var operand=Expression(1,depth+1);Need(")");
     if(name=="bit")return Node(new N{Kind="BitCast",Width=(int)width,Left=operand});
     return Node(new N{Kind="IntegerCast",Signedness=name=="int" ? "Signed" : "Unsigned",Width=(int)width,Left=operand});
    }
    position=saved;
   }
   if(name=="variable" && Take("(")){ulong slot=Number();Need(")");if(slot>4095 || slot>=(ulong)variables.Length)throw new ArgumentException("Unknown variable slot.");return Variable((int)slot);}
   if(name=="read" && Take("(")){var indices=new List<int>();do{indices.Add(Index());}while(Take(","));Need(")");return Node(new N{Kind="Read",Bits=indices.ToArray()});}
   if(name=="popcount" && Take("(")){var operand=Expression(1,depth+1);Need(")");return Node(new N{Kind="PopulationCount",Left=operand});}
   if((name=="rotl" || name=="rotr" || name=="rotl_signed" || name=="rotr_signed") && Take("(")) {
    var operand=Expression(1,depth+1);Need(",");bool signed=name.EndsWith("_signed",StringComparison.Ordinal);N distance;
    if(Take("-")) {
     ulong magnitude=Number();if(magnitude>(1UL<<63))throw new ArgumentException("Negative rotation distances must fit signed 64 bits.");
     distance=Node(new N{Kind="Constant",Width=64,Value=unchecked(0UL-magnitude).ToString(CultureInfo.InvariantCulture)});signed=true;
    } else distance=Expression(1,depth+1);
    Need(")");return Node(new N{Kind="Rotate",RotationDirection=name.StartsWith("rotl",StringComparison.Ordinal) ? "Left" : "Right",DistanceInterpretation=signed ? "Signed" : "Unsigned",Left=operand,Right=distance});
   }
   if(name=="true" || name=="false")return Node(new N{Kind="Constant",Width=1,Value=name=="true" ? "1" : "0"});
   for(int slot=0;slot<variables.Length;++slot)if(variables[slot].Name==name)return Variable(slot);
   int[] bits;if(!registers.TryGetValue(name,out bits))throw new ArgumentException("Unknown classical register: "+name);
   if(Take("[")) {
    int first=Index(),last=first;
    if(Take(":"))last=Index();Need("]");
    if(first>last || last>=bits.Length)throw new ArgumentException("Slice indices must be ascending and inside the register; use read(...) for other orders.");
    bits=bits.Skip(first).Take(last-first+1).ToArray();
   }
   return Node(new N{Kind="Read",Bits=(int[])bits.Clone()});
  }
 }
}
