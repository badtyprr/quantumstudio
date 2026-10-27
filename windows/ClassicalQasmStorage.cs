// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;

// Logical circuit bits retain one physical location. Explicit outputs occupy
// result; other bits occupy scratch. No final measurements or copied bit bank.
sealed class ClassicalQasmStorage {
 readonly string[] names;
 readonly int[] offsets;
 readonly int outputCount;
 const string Temporary="assignment_value";
 public int BitCount {get{return names.Length;}}
 static string Number(int value){return value.ToString(CultureInfo.InvariantCulture);}
 public ClassicalQasmStorage(int bits,int[] outputs) {
  if(bits<0 || bits>64 || outputs==null || outputs.Length>bits)throw new ArgumentException("Invalid classical export storage.");
  names=new string[bits];offsets=new int[bits];outputCount=outputs.Length;
  for(int i=0;i<outputs.Length;i++) {
   int bit=outputs[i];
   if(bit<0 || bit>=bits || names[bit]!=null)throw new ArgumentException("Output bits must be distinct and inside the register.");
   names[bit]="result";offsets[bit]=outputs.Length-1-i;
  }
  int next=0;
  for(int bit=0;bit<bits;bit++)if(names[bit]==null){names[bit]="scratch";offsets[bit]=next++;}
 }
 string Declarations() {
  if(BitCount==0)return "";
  var result=new StringBuilder();
  if(outputCount>0)result.Append("output bit["+Number(outputCount)+"] result;\n");
  if(BitCount>outputCount)result.Append("bit["+Number(BitCount-outputCount)+"] scratch;\n");
  result.Append("uint[64] "+Temporary+";\n");
  return result.ToString();
 }
 // Keep storage and operations in the same scope. Without explicit outputs,
 // program-scope bits would otherwise become results on reimport.
 public string ProgramBody(string operations) {
  if(operations==null)throw new ArgumentNullException("operations");
  string body=Declarations()+operations;
  return BitCount>0 && outputCount==0 ? "if (true) {\n"+body+"\n}\n" : body;
 }
 public string Bit(int index) {
  if(index<0 || index>=BitCount)throw new ArgumentException("Classical bit is outside the register.");
  return names[index]+"["+Number(offsets[index])+"]";
 }
 public string Read(int[] indices) {
  if(indices==null || indices.Length<1 || indices.Length>64)throw new ArgumentException("Read 1–64 classical bits.");
  foreach(int index in indices)Bit(index);
  string first=names[indices[0]];
  bool same=true;foreach(int index in indices)if(names[index]!=first)same=false;
  if(same)return first+"[{"+String.Join(",",Array.ConvertAll(indices,i=>Number(offsets[i])))+"}]";
  // A one-element slice keeps register semantics through the integer casts.
  // Balance the OR tree so a 64-bit read stays below the expression depth cap.
  var terms=new List<string>();
  for(int i=0;i<indices.Length;i++) {
   int index=indices[i];string width=Number(indices.Length);
   string value="bit["+width+"](uint["+width+"](uint[1]("+names[index]+"[{"+Number(offsets[index])+"}])))";
   terms.Add(i==0 ? value : "("+value+" << "+Number(i)+")");
  }
  while(terms.Count>1) {
   var next=new List<string>();
   for(int i=0;i<terms.Count;i+=2)next.Add(i+1==terms.Count ? terms[i] : "("+terms[i]+" | "+terms[i+1]+")");
   terms=next;
  }
  return terms[0];
 }
 public string Assign(int[] targets,ClassicalExpression value,IList<ClassicalIntegerType> variables=null) {
  if(value==null || targets==null || targets.Length!=value.Width)throw new ArgumentException("Assignment width must match its targets.");
  var seen=new HashSet<int>();
  foreach(int target in targets){Bit(target);if(!seen.Add(target))throw new ArgumentException("Assignment targets must be distinct.");}
  if(variables!=null && variables.Count+(variables is RuntimeDeclarations ? ((RuntimeDeclarations)variables).Numeric.Count : 0)>=4096)throw new InvalidDataException("Export needs one integer temporary within the 4096-variable limit.");
  string expression=new ClassicalExpressionQasm(BitCount,variables,this).Bits(value);
  // Evaluate before any write, preserving overlapping reads and error behavior.
  var result=new StringBuilder(Temporary+" = uint["+Number(value.Width)+"]("+expression+");\n");
  for(int i=0;i<targets.Length;i++) {
   string divisor=(1UL<<i).ToString(CultureInfo.InvariantCulture);
   result.Append(Bit(targets[i])+" = bit[1](uint[1]("+Temporary+" / uint[64]("+divisor+")));\n");
  }
  return result.ToString();
 }
}
