#Requires -RunAsAdministrator

param(
    [string]$AllowedSid = "S-1-5-32-545"
)

$ErrorActionPreference = "Stop"
$dir = Join-Path $env:ProgramData "RDPControl"
$controlScript = Join-Path $dir "RDP-Control.ps1"
$taskPath = "\ovworksViewer\"

New-Item -ItemType Directory -Path $dir -Force | Out-Null

$script = @'
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Block", "Unblock")]
    [string]$Action
)

$ErrorActionPreference = "Stop"
$rule = "Managed-RDP-3389-Block"

foreach ($protocol in @("TCP", "UDP")) {
    $name = "$rule-$protocol"
    if ($Action -eq "Block") {
        if (-not (Get-NetFirewallRule -Name $name -ErrorAction SilentlyContinue)) {
            New-NetFirewallRule `
                -Name $name `
                -DisplayName $name `
                -Direction Inbound `
                -Protocol $protocol `
                -LocalPort 3389 `
                -Action Block `
                -Profile Any | Out-Null
        } else {
            Enable-NetFirewallRule -Name $name
        }
    } else {
        Disable-NetFirewallRule -Name $name -ErrorAction SilentlyContinue
    }
}
'@

Set-Content -LiteralPath $controlScript -Value $script -Encoding UTF8

# Only SYSTEM and Administrators may modify the directory. Built-in Users get
# read/execute access so Task Scheduler can validate delegated task callers.
& icacls.exe $dir /inheritance:r | Out-Null
& icacls.exe $dir /grant:r `
    "*S-1-5-18:(OI)(CI)F" `
    "*S-1-5-32-544:(OI)(CI)F" `
    "*${AllowedSid}:(OI)(CI)RX" | Out-Null

$powershell = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$taskService = New-Object -ComObject "Schedule.Service"
$taskService.Connect()
$taskRoot = $taskService.GetFolder("\")
try {
    $taskFolder = $taskRoot.GetFolder($taskPath)
} catch {
    $taskFolder = $taskRoot.CreateFolder("ovworksViewer", $null)
}

foreach ($mode in @("Block", "Unblock")) {
    $action = New-ScheduledTaskAction `
        -Execute $powershell `
        -Argument "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$controlScript`" -Action $mode"
    $principal = New-ScheduledTaskPrincipal `
        -UserId "SYSTEM" `
        -LogonType ServiceAccount `
        -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 1)

    Register-ScheduledTask `
        -TaskName "RDP-$mode" `
        -TaskPath $taskPath `
        -Action $action `
        -Principal $principal `
        -Settings $settings `
        -Force | Out-Null
}

# Register-ScheduledTask does not expose a task DACL. Delegate read/execute,
# but not modification, to the configured local group (Built-in Users by
# default). This is what permits a standard-user viewer process to use /run.
$taskFolder = $taskService.GetFolder($taskPath)
$taskSddl = "D:P(A;;GA;;;SY)(A;;GA;;;BA)(A;;GRGX;;;$AllowedSid)"
foreach ($mode in @("Block", "Unblock")) {
    $taskFolder.GetTask("RDP-$mode").SetSecurityDescriptor($taskSddl, 0)
}

Write-Host "Installed SYSTEM RDP control tasks and delegated execution to $AllowedSid."
