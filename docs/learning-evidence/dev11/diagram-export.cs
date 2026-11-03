// GPL-2.0-or-later; see COPYING.
// Calls the real shared gate exporter; does not duplicate its decomposition.
using System;
using System.Text;
using System.Web.Script.Serialization;
class DiagramExport {
 public class Step {public string Gate; public string Angle; public int[] Wires;}
 public class Circuit {public int Qubits; public Step[] Steps;}
 static void Main() {
  var c=new JavaScriptSerializer().Deserialize<Circuit>(Console.In.ReadToEnd());
  var output=new StringBuilder("OPENQASM 3.0;\ninclude \"stdgates.inc\";\nqubit["+c.Qubits+"] q;\n");
  int classical=0;
  foreach(var step in c.Steps) QasmGateSerializer.Append(output,step.Gate,step.Angle,step.Wires,ref classical);
  Console.Write(output.ToString());
 }
}
