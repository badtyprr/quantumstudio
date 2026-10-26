// GPL-2.0-or-later; see COPYING.
using System;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;
using System.Collections.Generic;

public class BasisDeclaration {
 public string Name {get;set;}
 public string Kind {get;set;}
 public string Labels {get;set;}
 public string Family {get;set;}
 public string Dimension {get;set;}
}
static class BasisDeclarations {
 public const int MaximumCount=32;
 public static readonly string[] Kinds={"Named labels","Indexed family"};
 static readonly UTF8Encoding Utf8=new UTF8Encoding(false,true);
 static readonly Regex Identifier=new Regex(@"\A[\p{L}_][\p{L}\p{N}_]*\z",RegexOptions.CultureInvariant);
 static void Symbol(string text) {
  if(text==null || Utf8.GetByteCount(text)>128 || !Identifier.IsMatch(text))throw new InvalidDataException("Basis, family, and label names must be symbols of at most 128 UTF-8 bytes.");
 }
 public static string[] LabelsOf(BasisDeclaration declaration) {
  if(declaration.Labels==null || Utf8.GetByteCount(declaration.Labels)>16000)throw new InvalidDataException("Enter comma-separated labels, at most 16 KB.");
  var labels=declaration.Labels.Split(',');for(int i=0;i<labels.Length;i++)labels[i]=labels[i].Trim();return labels;
 }
 public static void Validate(BasisDeclaration[] declarations) {
  if(declarations==null || declarations.Length>MaximumCount)throw new InvalidDataException("Expected at most 32 basis declarations.");
  var names=new HashSet<string>(StringComparer.Ordinal);var labels=new HashSet<string>(StringComparer.Ordinal);var families=new HashSet<string>(StringComparer.Ordinal);
  foreach(var declaration in declarations) {
   if(declaration==null)throw new InvalidDataException("Invalid basis declaration.");
   Symbol(declaration.Name);if(!names.Add(declaration.Name))throw new InvalidDataException("Basis names must be unique.");
   if(declaration.Kind==Kinds[0]) {
    if(!String.IsNullOrEmpty(declaration.Family) || !String.IsNullOrEmpty(declaration.Dimension))throw new InvalidDataException("Named bases use their label count as dimension; clear family and dimension.");
    var items=LabelsOf(declaration);if(items.Length>1024)throw new InvalidDataException("A named basis supports at most 1024 labels.");
    foreach(string label in items) {Symbol(label);if(!labels.Add(label))throw new InvalidDataException("Each label must belong to just one workspace basis.");}
   } else if(declaration.Kind==Kinds[1]) {
    if(!String.IsNullOrEmpty(declaration.Labels))throw new InvalidDataException("Indexed families use a dimension; clear named labels.");
    Symbol(declaration.Family);if(!families.Add(declaration.Family))throw new InvalidDataException("Each family must belong to just one workspace basis.");
    MatrixDeclarations.ValidateDimension(declaration.Dimension);
    decimal number;if(Decimal.TryParse(declaration.Dimension,System.Globalization.NumberStyles.Number,System.Globalization.CultureInfo.InvariantCulture,out number) && (number<=0 || Decimal.Truncate(number)!=number))throw new InvalidDataException("Basis dimensions must be positive integers.");
   } else throw new InvalidDataException("Choose Named labels or Indexed family.");
  }
  foreach(string label in labels)foreach(string family in families)if(label.StartsWith(family+"_",StringComparison.Ordinal))throw new InvalidDataException("A named label cannot overlap an indexed family.");
 }
 public static BasisDeclaration[] Copy(BasisDeclaration[] declarations) {
  if(declarations==null)return new BasisDeclaration[0];Validate(declarations);
  var result=new BasisDeclaration[declarations.Length];
  for(int i=0;i<result.Length;i++) {var d=declarations[i];result[i]=new BasisDeclaration {Name=d.Name,Kind=d.Kind,Labels=d.Labels,Family=d.Family,Dimension=d.Dimension};}
  return result;
 }
 public static string Apply(string expression,BasisDeclaration[] declarations) {
  Validate(declarations);
  if(String.IsNullOrWhiteSpace(expression) || expression.IndexOf('\0')>=0)throw new InvalidDataException("Enter a calculation expression.");
  string result=expression;
  foreach(var d in declarations) {
   if(d.Kind==Kinds[1])result="orthofamily(("+result+"),\""+d.Name+"\",\""+d.Family+"\",("+d.Dimension+"))";
   else {var kets=new List<string>();foreach(string label in LabelsOf(d))kets.Add("|"+label+">");result="orthobasis(("+result+"),\""+d.Name+"\",["+String.Join(",",kets.ToArray())+"])";}
  }
  if(Utf8.GetByteCount(result)>32000)throw new InvalidDataException("Expression and basis declarations exceed 32 KB.");return result;
 }
}
