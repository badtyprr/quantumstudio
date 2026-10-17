// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using N=ClassicalCircuit.ExpressionNode;

// Text syntax is independent of WPF and resolves to the validated file model.
static class ClassicalExpressionText {
 static readonly string[] Symbols={"||","&&","|","^","&","==","!=","<",">","<=",">=","<<",">>"};
 static readonly string[] Names={"LogicalOr","LogicalAnd","Or","Xor","And","Equal","NotEqual","Less","Greater","LessEqual","GreaterEqual","ShiftLeft","ShiftRight"};
 static readonly int[] Priority={1,2,3,4,5,6,6,7,7,7,7,8,8};
 static bool Comparison(string op){return op=="Equal" || op=="NotEqual" || op=="Less" || op=="Greater" || op=="LessEqual" || op=="GreaterEqual";}
 static int Minimum(ulong value){int width=1;while((value>>=1)!=0)width++;return width;}
 public static N Parse(string text,ClassicalCircuit.Document context,int width) {
  if(context==null || width<1 || width>64)throw new ArgumentException("Use a valid circuit and 1–64 result bits.");
  var parser=new Parser(text,context.Registers);var value=parser.Expression(1,0);parser.End();
  if(Resolve(value,width,0)!=width)throw new ArgumentException("Expression width must match the assignment or one-bit condition.");
  var step=width==1 ? new ClassicalCircuit.Step{Kind="ExpressionBranch",ClassicalValue=value,WhenTrue=new ClassicalCircuit.Step[0],WhenFalse=new ClassicalCircuit.Step[0]} :
   new ClassicalCircuit.Step{Kind="Assign",ClassicalValue=value,Wires=Enumerable.Range(0,width).ToArray()};
  ClassicalCircuit.From(new ClassicalCircuit.Document{Version=3,Qubits=0,Registers=context.Registers,OutputBits=new int[0],Steps=new[]{step}});
  return value;
 }
 static int? Known(N n) {
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
  if(logical)n.Operator=n.Operator=="LogicalAnd" ? "And" : "Or";
  return compare ? 1 : left;
 }
 public static string Format(N value){return FormatNode(value,0);}
 static string FormatNode(N n,int depth) {
  if(n==null || depth>=32)throw new ArgumentException("Invalid expression tree.");
  if(n.Kind=="Constant") {
   ulong value=UInt64.Parse(n.Value,CultureInfo.InvariantCulture);int width=n.Width.Value;var bits=new char[width];
   for(int i=0;i<width;i++)bits[width-i-1]=((value>>i)&1)==0 ? '0' : '1';
   return "\""+new string(bits)+"\"";
  }
  if(n.Kind=="Read")return "read("+String.Join(",",n.Bits)+")";
  if(n.Kind=="Complement")return "~("+FormatNode(n.Left,depth+1)+")";
  if(n.Kind=="PopulationCount")return "popcount("+FormatNode(n.Left,depth+1)+")";
  if(n.Kind=="Rotate") {
   string distance=n.DistanceInterpretation=="Signed" && n.Right.Kind=="Constant" && n.Right.Width==64 ? unchecked((long)UInt64.Parse(n.Right.Value,CultureInfo.InvariantCulture)).ToString(CultureInfo.InvariantCulture) : FormatNode(n.Right,depth+1);
   return (n.RotationDirection=="Left" ? "rotl" : "rotr")+(n.DistanceInterpretation=="Signed" ? "_signed" : "")+"("+FormatNode(n.Left,depth+1)+", "+distance+")";
  }
  int op=Array.IndexOf(Names,n.Operator);if(op<0)throw new ArgumentException("Unknown expression operator.");
  bool sharedWidth=n.Operator!="ShiftLeft" && n.Operator!="ShiftRight";
  string left=sharedWidth && n.Right.Kind=="PopulationCount" && n.Left.Kind=="Constant" && n.Left.Width==64 ? n.Left.Value : FormatNode(n.Left,depth+1);
  string right=sharedWidth && n.Left.Kind=="PopulationCount" && n.Right.Kind=="Constant" && n.Right.Width==64 ? n.Right.Value : FormatNode(n.Right,depth+1);
  return "("+left+" "+Symbols[op]+" "+right+")";
 }
 sealed class Parser {
  readonly string text;int position,nodes;readonly Dictionary<string,int[]> registers=new Dictionary<string,int[]>(StringComparer.Ordinal);
  public Parser(string value,ClassicalCircuit.Register[] declared) {
   if(value==null || value.Length>65536 || declared==null)throw new ArgumentException("Enter an expression of at most 65536 characters.");
   text=value;int offset=0;foreach(var r in declared){registers.Add(r.Name,Enumerable.Range(offset,r.Size).ToArray());offset+=r.Size;}
  }
  void Space(){while(position<text.Length && Char.IsWhiteSpace(text[position]))position++;}
  bool Take(string token){Space();if(position+token.Length>text.Length || String.CompareOrdinal(text,position,token,0,token.Length)!=0)return false;position+=token.Length;return true;}
  void Need(string token){if(!Take(token))throw new ArgumentException("Expected '"+token+"' at position "+(position+1)+".");}
  N Node(N node){if(++nodes>512)throw new ArgumentException("Expressions allow at most 512 nodes.");return node;}
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
    position+=Symbols[op].Length;var right=Expression(Priority[op]+1,depth+1);left=Node(new N{Kind="Binary",Operator=Names[op],Left=left,Right=right});
   }
   return left;
  }
  N Atom(int depth) {
   if(depth>=128)throw new ArgumentException("Expression nesting is too deep.");
   if(Take("~"))return Node(new N{Kind="Complement",Left=Atom(depth+1)});
   if(Take("!"))return Node(new N{Kind="LogicalNot",Left=Atom(depth+1)});
   if(Take("(")){var value=Expression(1,depth+1);Need(")");return value;}
   if(Take("\"")) {
    ulong value=0;int width=0;
    while(position<text.Length && (text[position]=='0' || text[position]=='1')){if(++width>64)throw new ArgumentException("Bit strings allow 1–64 bits.");value=(value<<1)+(ulong)(text[position++]-'0');}
    if(position>=text.Length || text[position]!='"')throw new ArgumentException("A bit string may contain only 0 and 1.");position++;
    if(width==0)throw new ArgumentException("A bit string cannot be empty.");return Node(new N{Kind="Constant",Width=width,Value=value.ToString(CultureInfo.InvariantCulture)});
   }
   Space();if(position<text.Length && Char.IsDigit(text[position]))return Node(new N{Kind="Constant",Value=Number().ToString(CultureInfo.InvariantCulture)});
   int start=position;while(position<text.Length && (Char.IsLetterOrDigit(text[position]) || text[position]=='_'))position++;
   string name=text.Substring(start,position-start);if(name.Length==0)throw new ArgumentException("Expected a register, bit string or integer.");
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
