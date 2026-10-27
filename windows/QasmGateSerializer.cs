// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

// Shared OpenQASM gate decomposition. Callers supply validated gate names and
// wire lists; classical measurement names are allocated across the whole output.
static class QasmGateSerializer {
 public static bool ControlledAngle(string name) {return name=="CP" || name=="CRx" || name=="CRy" || name=="CRz";}
 public static bool ParityRotation(string name) {return name=="XXPlusYY" || name=="XXMinusYY";}
 public static bool Interaction(string name) {return name=="Rxx" || name=="Ryy" || name=="Rzz" || name=="Rzx";}
 public static bool Noise(string name) {return name=="AD" || name=="GAD" || name=="PD" || name=="PAD" || name=="Depol" || name=="Thermal";}
 public static bool NeedsAngle(string name) {return name=="GPhase" || ParityRotation(name) || Noise(name) || Interaction(name) || name=="R" || name=="U3" || name=="fSim" || ControlledAngle(name) || name=="Rx" || name=="Ry" || name=="Rz" || name=="P";}
 public static string[] GateAngles(string name,string value) {
  var parts=new List<string>(); int depth=0, start=0;
  for(int j=0;j<value.Length;j++) {
   if(value[j]=='(')depth++; else if(value[j]==')')depth--;
   if(depth<0)throw new InvalidDataException("Unbalanced angle parentheses.");
   if(value[j]==',' && depth==0){parts.Add(value.Substring(start,j-start).Trim());start=j+1;}
  }
  parts.Add(value.Substring(start).Trim());
  int count=name=="Thermal" ? 4 : name=="U3" || name=="PAD" ? 3 : ParityRotation(name) || name=="R" || name=="fSim" || name=="GAD" ? 2 : 1;
  if(depth!=0 || parts.Count!=count || parts.Exists(String.IsNullOrWhiteSpace))throw new InvalidDataException(name+" needs "+count+" parameter expressions, separated by commas, with balanced parentheses.");
  return parts.ToArray();
 }
 public static bool Feedback(string name) {return name!=null && (name=="M0-X" || name=="M1-X" || name=="M0-Z" || name=="M1-Z" || name=="M00-X" || name=="M01-X" || name=="M10-X" || name=="M11-X" || name=="M00-Z" || name=="M01-Z" || name=="M10-Z" || name=="M11-Z");}
 public static string FeedbackBits(string name) {return name.Substring(1,name.IndexOf('-')-1);}
 public static char FeedbackGate(string name) {return name[name.Length-1];}
 public static int WireCount(string name) {return Feedback(name) ? FeedbackBits(name).Length+1 : name=="CCX" || name=="CCZ" || name=="CSWAP" ? 3 : ParityRotation(name) || Interaction(name) || name=="ECR" || name=="FSWAP" || name=="fSim" || ControlledAngle(name) || name=="CNOT" || name=="CZ" || name=="CY" || name=="CH" || name=="SWAP" || name=="iSWAP" ? 2 : 1;}
 static void PauliRotation(StringBuilder result,string axes,string theta,string[] wires) {
  string a=wires[0], b=wires[1];
  for(int k=0;k<2;k++) {
   string wire=k==0 ? a : b;
   if(axes[k]=='x')result.Append("h "+wire+";\n");
   if(axes[k]=='y')result.Append("rx(pi/2.0) "+wire+";\n");
  }
  result.Append("cx "+a+", "+b+";\nrz("+theta+") "+b+";\ncx "+a+", "+b+";\n");
  for(int k=0;k<2;k++) {
   string wire=k==0 ? a : b;
   if(axes[k]=='x')result.Append("h "+wire+";\n");
   if(axes[k]=='y')result.Append("rx(-pi/2.0) "+wire+";\n");
  }
 }

 public static void Append(StringBuilder result,string name,string angle,int[] wires,ref int classical) {
  AppendTargets(result,name,angle,Array.ConvertAll(wires,n=>"q["+n+"]"),ref classical);
 }
 internal static void AppendTargets(StringBuilder result,string name,string angle,string[] wires,ref int classical) {
  if(Noise(name))throw new InvalidDataException("OpenQASM export does not support noise channels ("+name+").");

   if(name=="GPhase") {result.Append("gphase("+QasmAngle.Translate(angle)+");\n");return;}
   if(Interaction(name)) {PauliRotation(result,name.Substring(1),QasmAngle.Translate(angle),wires);return;}
   if(name=="U3") {
    string[] angles=Array.ConvertAll(GateAngles(name,angle),QasmAngle.Translate); string wire=wires[0];
    result.Append("p("+angles[2]+") "+wire+";\nry("+angles[0]+") "+wire+";\np("+angles[1]+") "+wire+";\n");return;
   }
   if(name=="R") {
    string[] angles=Array.ConvertAll(GateAngles(name,angle),QasmAngle.Translate);string wire=wires[0];
    result.Append("rz(-("+angles[1]+")) "+wire+";\nrx("+angles[0]+") "+wire+";\nrz("+angles[1]+") "+wire+";\n");return;
   }
   if(ParityRotation(name)) {
    string[] angles=Array.ConvertAll(GateAngles(name,angle),QasmAngle.Translate);
    bool plus=name=="XXPlusYY";string wire=wires[plus ? 0 : 1], beta="("+angles[1]+")", half="("+angles[0]+")/2.0";
    result.Append("rz("+(plus ? beta : "-"+beta)+") "+wire+";\n");
    PauliRotation(result,"xx",half,wires);PauliRotation(result,"yy",plus ? half : "-("+half+")",wires);
    result.Append("rz("+(plus ? "-"+beta : beta)+") "+wire+";\n");return;
   }
   if(name=="fSim") {
    string[] angles=GateAngles(name,angle); string theta=QasmAngle.Translate(angles[0]), phi=QasmAngle.Translate(angles[1]);
    string a=wires[0], b=wires[1];
    // Commuting XX and YY rotations, followed by the negative controlled phase.
    PauliRotation(result,"xx",theta,wires);PauliRotation(result,"yy",theta,wires);
    result.Append("cp(-("+phi+")) "+a+", "+b+";\n"); return;
   }
   if(name=="ECR") {
    string a=wires[0], b=wires[1];
    // Preserve the matrix's global phase, including for future controlled use.
    result.Append("gphase(-pi/4.0);\ns "+a+";\nsx "+b+";\ncx "+a+", "+b+";\nx "+a+";\n");return;
   }
   if(name=="FSWAP") {
    string a=wires[0], b=wires[1];
    result.Append("swap "+a+", "+b+";\ncz "+a+", "+b+";\n");return;
   }
   if(name=="iSWAP") {
    string a=wires[0], b=wires[1];
    result.Append("swap "+a+", "+b+";\ns "+a+";\ns "+b+";\ncz "+a+", "+b+";\n"); return;
   }
   if(Feedback(name)) {
    string bits=FeedbackBits(name);var conditions=new List<string>();
    for(int k=0;k<bits.Length;k++) {
     string bit="m"+(classical++);
     result.Append("bit "+bit+";\n"+bit+" = measure "+wires[k]+";\n");conditions.Add(bit+" == "+bits[k]);
    }
    result.Append("if ("+String.Join(" && ",conditions)+") {\n  "+Char.ToLowerInvariant(FeedbackGate(name))+" "+wires[bits.Length]+";\n}\n");
    return;
   }
   string instruction=name=="CNOT" ? "cx" : name=="CCZ" ? "ctrl(2) @ z" : name=="SXdg" ? "inv @ sx" : name.ToLowerInvariant();
   result.Append(instruction); if(NeedsAngle(name))result.Append("("+QasmAngle.Translate(angle)+")");
   result.Append(" "); result.Append(String.Join(", ",wires)); result.Append(";\n");

 }
}
