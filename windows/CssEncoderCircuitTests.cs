// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.IO;
using System.Web.Script.Serialization;
static class CssEncoderCircuitTests {
 public static void Run(CircuitComposer composer,string path) {
  var serializer=new JavaScriptSerializer {MaxJsonLength=8*1024*1024};var records=new List<Dictionary<string,object>>();
  Action<string,string,bool,bool> check=delegate(string hx,string hz,bool append,bool mixed) {
   string input=null;
   if(append) {
    int logical=composer.CssEncoder(hx,hz,false);if(logical<1)throw new Exception("Append fixture needs logical qubits.");
    var preparation=new List<CircuitComposer.Step>();
    for(int j=0;j<logical;j++){preparation.Add(new CircuitComposer.Step {Gate="H",Angle="",Wires=new[]{j}});preparation.Add(new CircuitComposer.Step {Gate="S",Angle="",Wires=new[]{j}});}
    if(logical>1)preparation.Add(new CircuitComposer.Step {Gate="CNOT",Angle="",Wires=new[]{0,1}});
    if(mixed)preparation.Add(new CircuitComposer.Step {Gate="AD",Angle="1/3",Wires=new[]{0}});
    composer.LoadCircuit(serializer.Serialize(new CircuitComposer.CircuitFile {Version=1,Qubits=logical,Steps=preparation.ToArray()}));input=composer.Expression();
   }
   string before=composer.Expression();int k=-1;bool rejected=false;
   try {k=composer.CssEncoder(hx,hz,append);}catch(ArgumentException){rejected=true;}
   var record=new Dictionary<string,object>{{"Hx",hx},{"Hz",hz},{"Append",append},{"Mixed",mixed},{"Rejected",rejected},{"LogicalQubits",k},{"Input",input}};
   if(rejected) {if(composer.Expression()!=before)throw new Exception("Rejected encoder changed the circuit.");}
   else {
    string expression=composer.Expression();
    if(before!=expression && (!composer.Undo() || composer.Expression()!=before || !composer.Redo() || composer.Expression()!=expression))throw new Exception("Encoder undo/redo failed.");
    composer.SaveCircuit(path+".qcircuit");composer.OpenCircuit(path+".qcircuit");if(composer.Expression()!=expression)throw new Exception("Encoder save/open failed.");
    record["Expression"]=expression;record["Circuit"]=File.ReadAllText(path+".qcircuit");
    if(mixed) {bool refused=false;try {composer.OpenQasm();}catch(InvalidDataException){refused=true;}if(!refused)throw new Exception("Noise export must be rejected.");record["Qasm"]=null;}
    else record["Qasm"]=composer.OpenQasm();
   }
   records.Add(record);
  };
  for(int x=0;x<8;x++)for(int z=0;z<8;z++)check("["+((x>>2)&1)+","+((x>>1)&1)+","+(x&1)+"]","["+((z>>2)&1)+","+((z>>1)&1)+","+(z&1)+"]",false,false);
  string h="[1,1,1,1,0,0,0;1,1,0,0,1,1,0;1,0,1,0,1,0,1]";
  check(h,h,false,false);check(h,h,true,false);
  check("[]","[1,1,0;0,1,1]",true,true);
  check("[1,1,1,1]","[1,1,1,1]",true,false);
  check("[1,1;1,1;0,0]","[1,1]",false,false);
  var random=new Random(932);
  for(int sample=0;sample<32;sample++) {
   int n=sample%8+1,rows=1+random.Next(n);string x="[";
   for(int r=0;r<rows;r++){if(r>0)x+=";";for(int c=0;c<n;c++){if(c>0)x+=",";x+=random.Next(2);}}
   check(x+"]","[]",false,false);
  }
  foreach(string[] pair in new[]{new[]{"[]","[]"},new[]{"1,1","1"},new[]{"1,2","[]"},new[]{"1,0,0,0,0,0,0,0,0","[]"},new[]{"[1,1","[]"},new[]{String.Join(";",new string('0',33).ToCharArray()),"[]"}}) {
   string before=composer.Expression();bool failed=false;try {composer.CssEncoder(pair[0],pair[1],false);}catch(ArgumentException){failed=true;}
   if(!failed || composer.Expression()!=before)throw new Exception("Invalid encoder changed the circuit.");
  }
  composer.CssState("1,1","1,1","00");string beforeAppend=composer.Expression();
  foreach(string[] pair in new[]{new[]{h,h},new[]{"1,1","1,1"}}) {
   bool failed=false;try {composer.CssEncoder(pair[0],pair[1],true);}catch(ArgumentException){failed=true;}
   if(!failed || composer.Expression()!=beforeAppend)throw new Exception("Invalid append register changed the circuit.");
  }
  var many=new List<CircuitComposer.Step>();for(int j=0;j<64;j++)many.Add(new CircuitComposer.Step {Gate="H",Angle="",Wires=new[]{0}});
  composer.LoadCircuit(serializer.Serialize(new CircuitComposer.CircuitFile {Version=1,Qubits=1,Steps=many.ToArray()}));string beforeLimit=composer.Expression();bool limit=false;
  try {composer.CssEncoder(h,h,true);}catch(ArgumentException){limit=true;}
  if(!limit || composer.Expression()!=beforeLimit)throw new Exception("Encoder step limit failed.");
  File.WriteAllText(path+".json",serializer.Serialize(records));
  composer.LoadCircuit(serializer.Serialize(new CircuitComposer.CircuitFile {Version=1,Qubits=1,Steps=new[]{new CircuitComposer.Step {Gate="H",Angle="",Wires=new[]{0}},new CircuitComposer.Step {Gate="S",Angle="",Wires=new[]{0}}}}));
  composer.CssEncoder(h,h,true);composer.SaveCircuit(path+".steane.qcircuit");
  File.WriteAllText(path+".txt","PASS: "+records.Count+" encoder fixtures, append, undo/redo, save/open, invalid-register and step-limit preservation.");
 }
}
