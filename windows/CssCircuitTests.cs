// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.IO;
using System.Web.Script.Serialization;

static class CssCircuitTests {
 public static void Run(CircuitComposer composer,string path) {
  var cases=new List<Dictionary<string,object>>();int valid=0,rejected=0;
  Action<string,string,string> check=delegate(string hx,string hz,string bits) {
   string before=composer.Expression();bool invalid=false;
   try {composer.CssState(hx,hz,bits);}catch(ArgumentException){invalid=true;}
   var record=new Dictionary<string,object>{{"Hx",hx},{"Hz",hz},{"Bits",bits},{"Rejected",invalid}};
   if(invalid) {
    if(composer.Expression()!=before)throw new Exception("Rejected CSS input changed the circuit.");rejected++;
   } else {
    string expression=composer.Expression();
    if(expression!=before && (!composer.Undo() || composer.Expression()!=before || !composer.Redo() || composer.Expression()!=expression))throw new Exception("CSS undo/redo failed.");
    composer.SaveCircuit(path+".qcircuit");composer.OpenCircuit(path+".qcircuit");
    if(composer.Expression()!=expression)throw new Exception("CSS save/open failed.");
    record["Expression"]=expression;record["Circuit"]=File.ReadAllText(path+".qcircuit");record["Qasm"]=composer.OpenQasm();valid++;
   }
   cases.Add(record);
  };
  for(int x=0;x<8;x++)for(int z=0;z<8;z++)for(int u=0;u<8;u++) {
   string hx="["+((x>>2)&1)+","+((x>>1)&1)+","+(x&1)+"]";
   string hz="["+((z>>2)&1)+","+((z>>1)&1)+","+(z&1)+"]";
   check(hx,hz,Convert.ToString(u,2).PadLeft(3,'0'));
  }
  string h="[1,1,1,1,0,0,0;1,1,0,0,1,1,0;1,0,1,0,1,0,1]";
  check(h,h,"0000000");check(h,h,"0000111");
  check("[1,1;1,1;0,0]","[1,1]","00");check("[]","[1,1,0;0,1,1]","111");
  check("[1,1]","[]","01");check("1","[]","1");
  string wide="[1,0,0,0,1,0,0,0;0,1,0,0,0,1,0,0;0,0,1,0,0,0,1,0;0,0,0,1,0,0,0,1]";
  check(wide,wide,"00000000");check(wide,wide,"11111111");
  check("[1,0,0,0,0,0,0,0;0,1,0,0,0,0,0,0;0,0,1,0,0,0,0,0;0,0,0,1,0,0,0,0;0,0,0,0,1,0,0,0;0,0,0,0,0,1,0,0;0,0,0,0,0,0,1,0;0,0,0,0,0,0,0,1]","[]","10101010");
  check("[]","[0,0,0,0,0,0,0,0]","11111111");
  check("1 1\n1 1","0 0","00");
  var random=new Random(2219);
  for(int sample=0;sample<32;sample++) {
   int n=sample%8+1,rows=1+random.Next(n);string hx="[";
   for(int r=0;r<rows;r++) {if(r>0)hx+=";";for(int c=0;c<n;c++){if(c>0)hx+=",";hx+=random.Next(2);}}
   check(hx+"]","[]",Convert.ToString(random.Next(1<<n),2).PadLeft(n,'0'));
  }
  foreach(string bad in new[]{null,"","[1,0","1,2","1,,0","1,0;0","1,0,0,0,0,0,0,0,0"}) {
   string before=composer.Expression();bool failed=false;try {composer.CssState(bad,"[]","00");}catch(ArgumentException){failed=true;}
   if(!failed || composer.Expression()!=before)throw new Exception("Invalid CSS matrix was accepted or changed the circuit.");
  }
  foreach(string bits in new[]{null,"","0","000","0x","02"}) {
   string before=composer.Expression();bool failed=false;try {composer.CssState("[1,1]","[]",bits);}catch(ArgumentException){failed=true;}
   if(!failed || composer.Expression()!=before)throw new Exception("Invalid CSS representative was accepted or changed the circuit.");
  }
  foreach(string[] input in new[]{new[]{"[]","[]","0"},new[]{"1,1","1","00"},new[]{"1,0","1,0","00"},new[]{"[]","1,1","01"},new[]{String.Join(";",new string('0',33).ToCharArray()),"[]","0"}}) {
   string before=composer.Expression();bool failed=false;try {composer.CssState(input[0],input[1],input[2]);}catch(ArgumentException){failed=true;}
   if(!failed || composer.Expression()!=before)throw new Exception("Invalid CSS constraints changed the circuit.");
  }
  var serializer=new JavaScriptSerializer {MaxJsonLength=8*1024*1024};File.WriteAllText(path+".json",serializer.Serialize(cases));
  composer.CssState(h,h,"0000000");composer.SaveCircuit(path+".steane.qcircuit");
  File.WriteAllText(path+".txt","PASS: "+valid+" circuits, "+rejected+" rejected check/representative combinations, undo/redo, save/open, exports and malformed-input preservation.");
 }
}
