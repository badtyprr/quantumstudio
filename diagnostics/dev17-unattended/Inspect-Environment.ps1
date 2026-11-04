# Feasibility only. Does not read or write Clipboard contents or change configuration.
param([Parameter(Mandatory=$true)][string]$Evidence)
$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath $Evidence) { throw 'Use a fresh evidence directory.' }
New-Item -ItemType Directory -Path $Evidence | Out-Null
$Evidence = (Resolve-Path -LiteralPath $Evidence).Path
function Observe([scriptblock]$Query) {
    try { @{ status='observed'; value=@(& $Query) } }
    catch { @{ status='unavailable'; error=$_.Exception.Message } }
}
Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class GuiEnvironmentIdentity {
 [DllImport("user32.dll")] public static extern IntPtr GetProcessWindowStation();
 [DllImport("user32.dll")] public static extern IntPtr GetThreadDesktop(uint id);
 [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
 [DllImport("user32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
 static extern bool GetUserObjectInformation(IntPtr h, int index, StringBuilder text, int bytes, out int needed);
 [DllImport("user32.dll", SetLastError=true)] public static extern bool OpenClipboard(IntPtr window);
 [DllImport("user32.dll")] public static extern bool CloseClipboard();
 public static string Name(IntPtr h) {
  var text=new StringBuilder(512); int needed;
  if(!GetUserObjectInformation(h,2,text,1024,out needed)) throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
  return text.ToString();
 }
}
'@
$opened = [GuiEnvironmentIdentity]::OpenClipboard([IntPtr]::Zero)
$clipboardError = if ($opened) { 0 } else { [Runtime.InteropServices.Marshal]::GetLastWin32Error() }
$closed = if ($opened) { [GuiEnvironmentIdentity]::CloseClipboard() } else { $null }
$vmrun = 'C:/Program Files (x86)/VMware/VMware Workstation/vmrun.exe'
$report = [ordered]@{
    utc = [DateTime]::UtcNow.ToString('o')
    machine = $env:COMPUTERNAME
    process_id = $PID
    session_id = (Get-Process -Id $PID).SessionId
    identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    station = [GuiEnvironmentIdentity]::Name([GuiEnvironmentIdentity]::GetProcessWindowStation())
    desktop = [GuiEnvironmentIdentity]::Name([GuiEnvironmentIdentity]::GetThreadDesktop([GuiEnvironmentIdentity]::GetCurrentThreadId()))
    clipboard_open = $opened
    clipboard_win32_error = $clipboardError
    clipboard_handle_closed = $closed
    clipboard_acceptance = 'NOT TESTED: no Copy action or Clipboard text read'
    os = Observe { Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber }
    computer = Observe { Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer,Model,HypervisorPresent,TotalPhysicalMemory }
    cpu = Observe { Get-CimInstance Win32_Processor | Select-Object Name,VirtualizationFirmwareEnabled,SecondLevelAddressTranslationExtensions }
    hyperv_vms = Observe { Get-CimInstance -Namespace root/virtualization/v2 -ClassName Msvm_ComputerSystem | Select-Object ElementName,EnabledState }
    tools = Observe { Get-Command Get-VM,VBoxManage,vmrun,az,pwsh -ErrorAction SilentlyContinue | Select-Object Name,Source }
    services = Observe { Get-Service vmms,vmcompute,TermService -ErrorAction SilentlyContinue | Select-Object Name,@{n='Status';e={$_.Status.ToString()}} }
    sessions = Observe { & quser; if($LASTEXITCODE -ne 0){throw "quser exit $LASTEXITCODE"} }
    vmware_running = Observe { if(Test-Path -LiteralPath $vmrun){ & $vmrun list; if($LASTEXITCODE -ne 0){throw "vmrun exit $LASTEXITCODE"} } else { throw 'VMware vmrun absent at inspected path' } }
    vmware_inventory = Observe { Get-Content -LiteralPath (Join-Path $env:APPDATA 'VMware/inventory.vmls') }
    disks = Observe { Get-PSDrive -PSProvider FileSystem | Select-Object Name,Free,Used }
    cleanup = 'No processes launched persistently; native Clipboard handle closed if acquired; no policy, account, VM, ACL, service or task changes.'
}
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $Evidence 'environment.json')
Get-FileHash -LiteralPath $PSCommandPath | Select-Object Path,Hash | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Evidence 'inspector-hash.json')
$report | ConvertTo-Json -Depth 8
