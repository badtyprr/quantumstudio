// GPL-2.0-or-later; see COPYING.
using System;
using System.Reflection;
using System.Windows;
using System.Windows.Markup;
using System.Windows.Media;

// Semantic colors live here once, shared by XAML and programmatic diagrams.
// Frozen brushes also work in non-UI circuit-file tests without an Application.
static class WorkspaceTheme {
 static SolidColorBrush Color(string hex) {var brush=new SolidColorBrush((Color)ColorConverter.ConvertFromString(hex));brush.Freeze();return brush;}
 public static readonly SolidColorBrush Background=Color("#0D1420"), Surface=Color("#151F2E"), Input=Color("#101A29"), Raised=Color("#223149");
 public static readonly SolidColorBrush Text=Color("#EFF4FC"), Muted=Color("#B0BED3"), Border=Color("#3B506D"), Accent=Color("#95B6FF");
 public static readonly SolidColorBrush Primary=Color("#365FC7"), OnPrimary=Color("#FFFFFF"), Selection=Color("#2C4265"), Error=Color("#FFAAAA");
 public static readonly SolidColorBrush Warning=Color("#F4C37C"), WarningSurface=Color("#352B20");
 public static void Install(Application application) {
  foreach(var field in typeof(WorkspaceTheme).GetFields(BindingFlags.Public|BindingFlags.Static))
   application.Resources["Theme."+field.Name]=field.GetValue(null);
  using(var stream=Assembly.GetExecutingAssembly().GetManifestResourceStream("WorkspaceTheme.xaml"))
   application.Resources.MergedDictionaries.Add((ResourceDictionary)XamlReader.Load(stream));
 }
}
