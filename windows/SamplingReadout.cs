// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using System.Web.Script.Serialization;
using System.Windows;
using System.Windows.Controls;

sealed class SamplingReadout : Expander {
 readonly CheckBox enabled=new CheckBox {Content="Apply to final measurement records",Margin=new Thickness(0,0,0,8)};
 readonly TextBox bits=new TextBox {Text="0",MaxLength=80};
 readonly TextBox matrix=new TextBox {Text="[0.98,0.02;0.03,0.97]",MaxLength=4096};
 public SamplingReadout() {
  Header="Readout error (optional)";Margin=new Thickness(0,0,0,12);
  var panel=new StackPanel {Margin=new Thickness(0,8,0,0)};Content=panel;panel.Children.Add(enabled);
  panel.Children.Add(new TextBlock {Text="Recorded bits · comma-separated, up to 8"});panel.Children.Add(bits);
  panel.Children.Add(new TextBlock {Text="Assignment matrix · rows are true results, columns are recorded results",TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,8,0,0)});panel.Children.Add(matrix);
  panel.Children.Add(new TextBlock {Text="The first listed bit is most significant. Each row sums to 1. This affects final records only, after circuit feedback has finished.",TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,8,0,0)});
  System.Windows.Automation.AutomationProperties.SetName(bits,"Readout target bits");
  System.Windows.Automation.AutomationProperties.SetName(matrix,"Readout assignment matrix");
  enabled.Checked+=delegate {bits.IsEnabled=matrix.IsEnabled=true;};
  enabled.Unchecked+=delegate {bits.IsEnabled=matrix.IsEnabled=false;};
  bits.IsEnabled=matrix.IsEnabled=false;
 }
 public void SetAssignment(string targetBits,string expression) {bits.Text=targetBits;matrix.Text=expression;enabled.IsChecked=true;IsExpanded=true;}
 public NumericalSampling.Readout[] Capture(int qubits) {
  if(enabled.IsChecked!=true)return new NumericalSampling.Readout[0];
  string[] fields=bits.Text.Split(',');var targets=new List<int>();
  if(fields.Length>8)throw new ArgumentException("Readout assignment supports at most eight bits.");
  foreach(string field in fields) {
   int bit;if(!Int32.TryParse(field.Trim(),NumberStyles.None,CultureInfo.InvariantCulture,out bit) || bit<0 || bit>=qubits || targets.Contains(bit))
    throw new ArgumentException("Enter distinct readout bits inside the circuit, such as 0 or 0,1.");
   targets.Add(bit);
  }
  string expression=matrix.Text.Trim();
  if(String.IsNullOrWhiteSpace(expression) || expression.IndexOf('\0')>=0 || Encoding.UTF8.GetByteCount(expression)>4096)
   throw new ArgumentException("Enter a readout matrix of at most 4096 UTF-8 bytes.");
  return new[]{new NumericalSampling.Readout {Bits=targets.ToArray(),Expression=expression}};
 }
}

static class SamplingExport {
 static object[] Models(IList<NumericalSampling.Readout> readout) {
  return readout.Select(item=>(object)new {bits=(int[])item.Bits.Clone(),matrix=item.Expression}).ToArray();
 }
 public static string Json(NumericalSampling.Result result,IList<NumericalSampling.Readout> readout) {
  return new JavaScriptSerializer {MaxJsonLength=16000000}.Serialize(new {schema="QuantumStudio.sampling.v1",result=result,final_readout=Models(readout),assignment_orientation="row=true, column=recorded; first target bit most significant"});
 }
 public static string Csv(NumericalSampling.Result result,IList<NumericalSampling.Readout> readout) {
  string model=new JavaScriptSerializer {MaxJsonLength=1000000}.Serialize(Models(readout));
  // Store run metadata once, in the first data row: repeating a 4 KiB model
  // for 100,000 outcomes would unnecessarily allocate hundreds of MiB.
  // JSON begins with [, and CSV quoting keeps expressions inside one cell.
  string quoted="\""+model.Replace("\"","\"\"")+"\"";
  var text=new StringBuilder("bits,count,frequency,shots,seed,run_final_readout\r\n");bool first=true;
  foreach(var item in result.counts.OrderBy(pair=>pair.Key,StringComparer.Ordinal)) {
   text.Append(item.Key).Append(',').Append(item.Value.ToString(CultureInfo.InvariantCulture)).Append(',').Append(((double)item.Value/result.shots).ToString("R",CultureInfo.InvariantCulture)).Append(',').Append(result.shots.ToString(CultureInfo.InvariantCulture)).Append(',').Append(result.seed).Append(',').Append(first ? quoted : "").Append("\r\n");first=false;
  }
  return text.ToString();
 }
}
