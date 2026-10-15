// GPL-2.0-or-later; see COPYING.
using System;
using System.IO;

// A deliberately explicit, expression-only OpenQASM angle translator.
// Floating literals preserve calculator division semantics (1/2 is not integer division).
class QasmAngle {
 readonly string text; int pos;
 QasmAngle(string value) {text=value.Replace("π","pi").Replace("−","-");}
 void Space(){while(pos<text.Length && Char.IsWhiteSpace(text[pos]))pos++;}
 bool Take(char value){Space();if(pos<text.Length && text[pos]==value){pos++;return true;}return false;}
 Exception Error(){return new InvalidDataException("QASM export accepts numeric literals, pi, + - * / and parentheses. Use explicit multiplication in angles.");}
 string Atom(){
  if(Take('(')){string value=Sum();if(!Take(')'))throw Error();return "("+value+")";}
  Space(); int start=pos;
  if(pos<text.Length && Char.IsLetter(text[pos])){while(pos<text.Length && Char.IsLetterOrDigit(text[pos]))pos++;if(text.Substring(start,pos-start)!="pi")throw Error();return "pi";}
  int digits=0;while(pos<text.Length && text[pos]>='0' && text[pos]<='9'){pos++;digits++;}
  bool dot=pos<text.Length && text[pos]=='.';if(dot){pos++;while(pos<text.Length && text[pos]>='0' && text[pos]<='9'){pos++;digits++;}}
  if(digits==0)throw Error();
  string number=text.Substring(start,pos-start);if(!dot)number+=".0";if(number.StartsWith("."))number="0"+number;if(number.EndsWith("."))number+="0";
  if(pos<text.Length && (text[pos]=='e' || text[pos]=='E')){int exponent=pos++;if(pos<text.Length && (text[pos]=='+' || text[pos]=='-'))pos++;int first=pos;while(pos<text.Length && text[pos]>='0' && text[pos]<='9')pos++;if(first==pos)throw Error();number+=text.Substring(exponent,pos-exponent).ToLowerInvariant();}
  return number;
 }
 string Unary(){if(Take('+'))return "(+"+Unary()+")";if(Take('-'))return "(-"+Unary()+")";return Atom();}
 string Product(){string value=Unary();while(true){if(Take('*'))value="("+value+"*"+Unary()+")";else if(Take('/'))value="("+value+"/"+Unary()+")";else return value;}}
 string Sum(){string value=Product();while(true){if(Take('+'))value="("+value+"+"+Product()+")";else if(Take('-'))value="("+value+"-"+Product()+")";else return value;}}
 public static string Translate(string value){if(String.IsNullOrWhiteSpace(value) || value.Length>200)throw new InvalidDataException("Invalid angle length.");var parser=new QasmAngle(value);string result=parser.Sum();parser.Space();if(parser.pos!=parser.text.Length)throw parser.Error();return result;}
}
