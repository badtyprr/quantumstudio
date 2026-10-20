// GPL-2.0-or-later; see COPYING.
using System;
using System.Globalization;
using System.Text.RegularExpressions;
using R=ClassicalCircuit.RealNode;

// Editor arithmetic is real. float(integer-expression) explicitly preserves
// an imported integer calculation before its conversion to binary64.
static class ClassicalRealExpressionText {
 static R Constant(double value) {
  if(Double.IsNaN(value) || Double.IsInfinity(value))throw new ArgumentException("Angles require finite real values.");
  return new R{Kind="Constant",ValueBits=unchecked((ulong)BitConverter.DoubleToInt64Bits(value)).ToString(CultureInfo.InvariantCulture)};
 }
 static void Validate(R value,ClassicalCircuit.Document context) {
  ClassicalCircuit.From(new ClassicalCircuit.Document{Version=11,Qubits=1,
   Registers=context.Registers,Variables=context.Variables??new ClassicalCircuit.Variable[0],
   OutputBits=new int[0],LoopConditionBudget=1000000,
   Steps=new[]{new ClassicalCircuit.Step{Kind="Rotation",Axis="Y",Angle=value,Wires=new[]{0}}}});
 }
 public static R Parse(string text,ClassicalCircuit.Document context) {
  if(context==null)throw new ArgumentNullException("context");
  var parser=new Parser(text,context);var result=parser.Expression(0,0);parser.End();Validate(result,context);return result;
 }
 public static string Format(R value,ClassicalCircuit.Document context) {
  if(context==null)throw new ArgumentNullException("context");Validate(value,context);return FormatNode(value,context);
 }
 static string FormatNode(R value,ClassicalCircuit.Document context) {
  if(value.Kind=="Integer")return "float("+ClassicalExpressionText.Format(value.IntegerValue,context)+")";
  if(value.Kind=="Constant") {
   long bits=unchecked((long)UInt64.Parse(value.ValueBits,CultureInfo.InvariantCulture));
   double number=BitConverter.Int64BitsToDouble(bits);
   if(number==0 && bits<0)return "-0.0";
   return number.ToString("R",CultureInfo.InvariantCulture);
  }
  string op=value.Operator=="Add" ? "+" : value.Operator=="Subtract" ? "-" : value.Operator=="Multiply" ? "*" : "/";
  return "("+FormatNode(value.Left,context)+" "+op+" "+FormatNode(value.Right,context)+")";
 }
 sealed class Parser {
  readonly string text;readonly ClassicalCircuit.Document context;int position,nodes;
  public Parser(string source,ClassicalCircuit.Document document) {
   if(String.IsNullOrWhiteSpace(source) || source.Length>65536)throw new ArgumentException("Enter an angle of at most 65536 characters.");
   text=source;context=document;
  }
  void Space(){while(position<text.Length && Char.IsWhiteSpace(text[position]))position++;}
  bool Take(char c){Space();if(position==text.Length || text[position]!=c)return false;position++;return true;}
  R Node(R value){if(++nodes>512)throw new ArgumentException("Angles allow at most 512 nodes.");return value;}
  public void End(){Space();if(position!=text.Length)throw new ArgumentException("Unexpected angle text at column "+(position+1)+".");}
  public R Expression(int minimum,int depth) {
   if(depth>=128)throw new ArgumentException("Angle nesting is too deep.");
   R left=Atom(depth+1);
   while(true) {
    Space();if(position==text.Length)break;
    char op=text[position];int precedence=op=='+' || op=='-' ? 1 : op=='*' || op=='/' ? 2 : -1;
    if(precedence<minimum)break;position++;
    left=Node(new R{Kind="Binary",Operator=op=='+' ? "Add" : op=='-' ? "Subtract" : op=='*' ? "Multiply" : "Divide",Left=left,Right=Expression(precedence+1,depth+1)});
   }
   return left;
  }
  string Parenthesized() {
   if(!Take('('))throw new ArgumentException("Expected an integer expression in parentheses.");
   int start=position,depth=1;
   while(position<text.Length) {
    char c=text[position++];if(c=='(' && ++depth>32)throw new ArgumentException("Angle nesting is too deep.");
    if(c==')' && --depth==0)return text.Substring(start,position-start-1);
   }
   throw new ArgumentException("Missing closing parenthesis.");
  }
  R Integer(string source){return Node(new R{Kind="Integer",IntegerValue=ClassicalExpressionText.ParseInteger(source,context)});}
  R Atom(int depth) {
   if(depth>=128)throw new ArgumentException("Angle nesting is too deep.");
   if(Take('+'))return Atom(depth+1);
   if(Take('-')) {
    R value=Atom(depth+1);
    if(value.Kind=="Constant")return Constant(-BitConverter.Int64BitsToDouble(unchecked((long)UInt64.Parse(value.ValueBits,CultureInfo.InvariantCulture))));
    return Node(new R{Kind="Binary",Operator="Multiply",Left=Node(Constant(-1)),Right=value});
   }
   if(Take('(')){R value=Expression(0,depth+1);if(!Take(')'))throw new ArgumentException("Missing closing parenthesis.");return value;}
   Space();var match=Regex.Match(text.Substring(position),@"\A(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?");
   if(match.Success){position+=match.Length;return Node(Constant(Double.Parse(match.Value,NumberStyles.Float,CultureInfo.InvariantCulture)));}
   int start=position;while(position<text.Length && (Char.IsLetterOrDigit(text[position]) || text[position]=='_'))position++;
   string name=text.Substring(start,position-start);if(name.Length==0)throw new ArgumentException("Expected an angle, variable or float(integer expression).");
   if(name=="float")return Integer(Parenthesized());
   foreach(var variable in context.Variables??new ClassicalCircuit.Variable[0])if(variable.Name==name)return Integer(name);
   if(name=="pi" || name=="π")return Node(Constant(Math.PI));
   if(name=="int" || name=="uint") {
    if(Take('[')){while(position<text.Length && Char.IsDigit(text[position]))position++;if(!Take(']'))throw new ArgumentException("Invalid integer width.");}
    string cast=text.Substring(start,position-start);return Integer(cast+"("+Parenthesized()+")");
   }
   throw new ArgumentException("Unknown angle variable: "+name+". Cast bits with uint[width](...).");
  }
 }
}
