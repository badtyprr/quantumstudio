// GPL-2.0-or-later; see COPYING.
using System;
using System.IO;
using System.Text;
using System.Web.Script.Serialization;
using System.Collections.Generic;

public class StateDefinition {
 public string Name {get;set;}
 public string Expression {get;set;}
}

public class SessionEntry {
 public string Expression {get;set;}
 public string Result {get;set;}
 public int Mode {get;set;}
 public int Evaluation {get;set;}
 public StateDefinition[] States {get;set;}
}
public class CalculationSession {
 public int Version {get;set;}
 public string Expression {get;set;}
 public int Mode {get;set;}
 public int Evaluation {get;set;}
 public SessionEntry[] History {get;set;}
 public StateDefinition[] States {get;set;}
}
static class SessionStore {
 public const int MaximumStates=32;
 const int MaximumBytes=8*1024*1024;
 static readonly UTF8Encoding StrictUtf8=new UTF8Encoding(false,true);
 static JavaScriptSerializer Serializer() {return new JavaScriptSerializer {MaxJsonLength=MaximumBytes,RecursionLimit=16};}
 public static void ValidateStates(StateDefinition[] states) {
  if(states==null || states.Length>MaximumStates)throw new InvalidDataException("Expected at most "+MaximumStates+" state definitions.");
  var names=new HashSet<string>(StringComparer.Ordinal);
  foreach(var state in states) {
   if(state==null || String.IsNullOrWhiteSpace(state.Name) || state.Name!=state.Name.Trim() || state.Name.IndexOfAny(new[]{'\r','\n','\t','\0'})>=0 || StrictUtf8.GetByteCount(state.Name)>128 || !names.Add(state.Name))
    throw new InvalidDataException("State names must be unique, nonempty, and at most 128 UTF-8 bytes.");
   if(String.IsNullOrWhiteSpace(state.Expression) || state.Expression.IndexOf('\0')>=0 || StrictUtf8.GetByteCount(state.Expression)>32768)
    throw new InvalidDataException("State expressions must contain 1 to 32768 UTF-8 bytes without NUL.");
  }
 }
 public static StateDefinition[] CopyStates(StateDefinition[] states) {
  if(states==null)return new StateDefinition[0]; // Version 1 sessions have no definitions.
  ValidateStates(states);
  var copy=new StateDefinition[states.Length];
  for(int i=0;i<states.Length;i++)copy[i]=new StateDefinition {Name=states[i].Name,Expression=states[i].Expression};
  return copy;
 }
 public static byte[] StateRequest(StateDefinition[] states,string expression) {
  ValidateStates(states);
  if(String.IsNullOrWhiteSpace(expression) || expression.IndexOf('\0')>=0 || StrictUtf8.GetByteCount(expression)>32768)throw new InvalidDataException("Invalid calculation expression.");
  var request=new StringBuilder("QSTATES1\n");
  request.Append(states.Length.ToString(System.Globalization.CultureInfo.InvariantCulture)).Append('\n');
  foreach(var state in states) {
   request.Append(StrictUtf8.GetByteCount(state.Name).ToString(System.Globalization.CultureInfo.InvariantCulture)).Append('\n');
   request.Append(StrictUtf8.GetByteCount(state.Expression).ToString(System.Globalization.CultureInfo.InvariantCulture)).Append('\n');
   request.Append(state.Name).Append(state.Expression);
  }
  request.Append(expression);return StrictUtf8.GetBytes(request.ToString());
 }
 static void ValidateSessionStates(StateDefinition[] states,int version) {
  if(version==1) {
   if(states!=null && states.Length!=0)throw new InvalidDataException("Version 1 sessions cannot contain state definitions.");
  } else ValidateStates(states);
 }
 static void ValidateExpression(string expression,int mode,int evaluation) {
  if(expression==null || StrictUtf8.GetByteCount(expression)>32000 || mode<0 || mode>1 || evaluation<0 || evaluation>1)
   throw new InvalidDataException("Session expressions must be at most 32 KB and use valid notation and evaluation modes.");
 }
 public static void Validate(CalculationSession session) {
  if(session==null || (session.Version!=1 && session.Version!=2) || session.History==null || session.History.Length>50)
   throw new InvalidDataException("Expected a version 1 or 2 calculation session with at most 50 history entries.");
  ValidateSessionStates(session.States,session.Version);
  ValidateExpression(session.Expression,session.Mode,session.Evaluation);
  foreach(var entry in session.History) {
   if(entry==null || entry.Result==null || entry.Result.Length>32768)throw new InvalidDataException("Invalid saved history result.");
   StrictUtf8.GetByteCount(entry.Result);
   ValidateSessionStates(entry.States,session.Version);
   ValidateExpression(entry.Expression,entry.Mode,entry.Evaluation);
   if(String.IsNullOrWhiteSpace(entry.Expression))throw new InvalidDataException("History expressions cannot be empty.");
  }
 }
 public static CalculationSession Load(string path) {
  string text;
  using(var file=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read))
  using(var bytes=new MemoryStream()) {
   if(file.Length>MaximumBytes)throw new InvalidDataException("Session files must be at most 8 MB.");
   byte[] buffer=new byte[8192];int count;
   while((count=file.Read(buffer,0,Math.Min(buffer.Length,MaximumBytes+1-(int)bytes.Length)))>0) {
    bytes.Write(buffer,0,count);
    if(bytes.Length>MaximumBytes)throw new InvalidDataException("Session files must be at most 8 MB.");
   }
   text=StrictUtf8.GetString(bytes.ToArray());
  }
  if(text.Length>0 && text[0]=='\uFEFF')text=text.Substring(1);
  var session=Serializer().Deserialize<CalculationSession>(text);Validate(session);return session;
 }
 public static void Save(string path,CalculationSession session) {
  Validate(session);string text=Serializer().Serialize(session);
  if(Encoding.UTF8.GetByteCount(text)>MaximumBytes)throw new InvalidDataException("Session files must be at most 8 MB.");
  string temporary=path+"."+Guid.NewGuid().ToString("N")+".tmp";
  try {
   File.WriteAllText(temporary,text,new UTF8Encoding(false));
   for(int attempt=0;;attempt++) {
    try {if(File.Exists(path))File.Replace(temporary,path,null);else File.Move(temporary,path);break;}
    catch(IOException ex) {
     int code=ex.HResult & 0xffff;
     if((code!=32 && code!=33 && code!=1175) || attempt>=5)throw;
     System.Threading.Thread.Sleep(200);
    }
   }
  } finally {if(File.Exists(temporary))File.Delete(temporary);}
 }
}
