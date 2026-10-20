// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Web.Script.Serialization;
using E=ClassicalExpression;

static class ClassicalQasmStorageTests {
 static readonly List<object> cases=new List<object>();
 static int rejected;
 static void Reject(Action action) {
  try {action();}
  catch(ArgumentException){rejected++;return;}
  catch(InvalidDataException){rejected++;return;}
  throw new Exception("Invalid storage accepted.");
 }
 static void Case(string name,int bits,int[] outputs,ulong initial,int[] reads,int[] targets,string expected) {
  var storage=new ClassicalQasmStorage(bits,outputs);
  var source=new StringBuilder("OPENQASM 3; include \"stdgates.inc\"; qubit q; reset q;\n");
  source.Append(storage.Declarations());
  for(int i=0;i<bits;i++)source.Append(storage.Bit(i)+" = "+((initial>>i)&1)+";\n");
  if(reads!=null)source.Append(storage.Assign(targets,E.Read(reads)));
  cases.Add(new {name=name,source=source.ToString(),expected=expected});
 }
 static void Main(string[] args) {
  if(args.Length!=1 || File.Exists(args[0]))throw new ArgumentException("Pass a fresh case path.");
  Reject(()=>new ClassicalQasmStorage(-1,new int[0]));
  Reject(()=>new ClassicalQasmStorage(65,new int[0]));
  Reject(()=>new ClassicalQasmStorage(1,null));
  Reject(()=>new ClassicalQasmStorage(1,new int[0]));
  Reject(()=>new ClassicalQasmStorage(2,new[]{0,0}));
  Reject(()=>new ClassicalQasmStorage(2,new[]{2}));
  var s=new ClassicalQasmStorage(4,new[]{0,3});
  Reject(()=>s.Bit(4));
  Reject(()=>s.Read(new int[0]));
  Reject(()=>s.Read(new[]{-1}));
  Reject(()=>s.Assign(new[]{0,0},E.Read(0,1)));
  Reject(()=>s.Assign(new[]{0},E.Read(0,1)));
  Reject(()=>new ClassicalExpressionQasm(3,null,s));
  var variables=new List<ClassicalIntegerType>();
  for(int i=0;i<4096;i++)variables.Add(ClassicalIntegerType.Create(ClassicalIntegerType.Sign.Unsigned,1));
  Reject(()=>s.Assign(new[]{0},E.Read(0),variables));
  if(new ClassicalQasmStorage(0,new int[0]).Declarations()!="")throw new Exception("Empty storage declares bits.");
  var outputs=new[]{0,3};var copied=new ClassicalQasmStorage(4,outputs);outputs[0]=2;
  if(copied.Bit(0)!="result[1]" || copied.Bit(3)!="result[0]")throw new Exception("Output ordering or ownership changed.");
  Case("overlapping-permutation",4,new[]{0,3},5,new[]{3,0,2},new[]{0,1,3},"01");
  Case("repeated-read",4,new[]{0,3},5,new[]{0,0,3},new[]{0,1,3},"10");
  Case("output-order",4,new[]{0,3,1},9,null,null,"110");
  Case("all-output",4,new[]{0,1,2,3},5,new[]{3,2,1,0},new[]{0,1,2,3},"0101");
  Case("single-bit",1,new[]{0},1,new[]{0},new[]{0},"1");
  int[] odd=new int[32],reverse=new int[64],all=new int[64];
  for(int i=0;i<32;i++)odd[i]=63-2*i;
  for(int i=0;i<64;i++){reverse[i]=63-i;all[i]=i;}
  Case("full-storage-boundary",64,odd,0xCCCCCCCCCCCCCCCCUL,reverse,all,"01010101010101010101010101010101");
  File.WriteAllText(args[0],new JavaScriptSerializer().Serialize(cases));
  Console.WriteLine("PASS: "+cases.Count+" storage cases; "+rejected+" invalid contexts rejected.");
 }
}
