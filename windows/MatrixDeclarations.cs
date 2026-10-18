// GPL-2.0-or-later; see COPYING.
using System;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;
using System.Collections.Generic;

public class MatrixDeclaration {
 public string Name {get;set;}
 public string Rows {get;set;}
 public string Columns {get;set;}
}
static class MatrixDeclarations {
 public const int MaximumCount=32;
 static readonly UTF8Encoding Utf8=new UTF8Encoding(false,true);
 static readonly Regex Identifier=new Regex(@"\A[\p{L}_][\p{L}\p{N}_]*\z",RegexOptions.CultureInvariant);
 static readonly Regex Tokens=new Regex(@"[\p{L}_][\p{L}\p{N}_]*",RegexOptions.CultureInvariant);
 static void Dimension(string text,HashSet<string> names) {
  if(String.IsNullOrWhiteSpace(text) || Utf8.GetByteCount(text)>256)throw new InvalidDataException("Dimensions need an expression of at most 256 UTF-8 bytes.");
  int depth=0;
  foreach(char c in text) {
   if(c=='(') {if(++depth>32)throw new InvalidDataException("Dimension expression is too deeply nested.");}
   else if(c==')') {if(--depth<0)throw new InvalidDataException("Unmatched dimension parentheses.");}
   else if(c==',') {if(depth==0)throw new InvalidDataException("Dimension commas belong inside function calls.");}
   else if(!Char.IsLetterOrDigit(c) && c!='_' && c!=' ' && "+-−*/×÷^.".IndexOf(c)<0)
    throw new InvalidDataException("Use arithmetic, symbols, and function calls for dimensions.");
  }
  if(depth!=0)throw new InvalidDataException("Unmatched dimension parentheses.");
  foreach(Match token in Tokens.Matches(text))if(names.Contains(token.Value))throw new InvalidDataException("A matrix name cannot also be a scalar dimension.");
 }
 public static void Validate(MatrixDeclaration[] declarations) {
  if(declarations==null || declarations.Length>MaximumCount)throw new InvalidDataException("Expected at most 32 matrix declarations.");
  var names=new HashSet<string>(StringComparer.Ordinal);
  foreach(var declaration in declarations) {
   if(declaration==null || declaration.Name==null || Utf8.GetByteCount(declaration.Name)>128 || !Identifier.IsMatch(declaration.Name) || !names.Add(declaration.Name))
    throw new InvalidDataException("Matrix names must be unique symbols of at most 128 UTF-8 bytes.");
  }
  foreach(var declaration in declarations) {Dimension(declaration.Rows,names);Dimension(declaration.Columns,names);}
 }
 public static MatrixDeclaration[] Copy(MatrixDeclaration[] declarations) {
  if(declarations==null)return new MatrixDeclaration[0];
  Validate(declarations);var result=new MatrixDeclaration[declarations.Length];
  for(int i=0;i<result.Length;i++)result[i]=new MatrixDeclaration {Name=declarations[i].Name,Rows=declarations[i].Rows,Columns=declarations[i].Columns};
  return result;
 }
 public static string Apply(string expression,MatrixDeclaration[] declarations) {
  Validate(declarations);
  if(String.IsNullOrWhiteSpace(expression) || expression.IndexOf('\0')>=0)throw new InvalidDataException("Enter a calculation expression.");
  string result=expression;
  foreach(var declaration in declarations)
   result="matrixassume(("+result+"),\""+declaration.Name+"\",("+declaration.Rows+"),("+declaration.Columns+"))";
  if(Utf8.GetByteCount(result)>32000)throw new InvalidDataException("Expression and matrix declarations exceed 32 KB.");
  return result;
 }
}
