$ErrorActionPreference = "Stop"

$repoRoot = "C:\Users\Hitan\Documents\Codex\2026-05-23\file-edit-view-window-help-identify\local-pilot"
$backend = Join-Path $repoRoot "backend"
$python = "C:\Users\Hitan\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if (-not (Test-Path -LiteralPath $backend)) {
    throw "Backend folder not found: $backend"
}

if (-not (Test-Path -LiteralPath $python)) {
    throw "Python runtime not found: $python"
}

function Remove-MenuKey {
    param([string] $SubKey)

    [Microsoft.Win32.Registry]::CurrentUser.DeleteSubKeyTree($SubKey, $false)
}

function Set-MenuKey {
    param(
        [string] $SubKey,
        [string] $SelectedPathToken
    )

    $commandText = "powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -Command `"Set-Location -LiteralPath '$backend'; & '$python' .\local_pilot_popup.py '$SelectedPathToken'`""

    $menuKey = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey($SubKey)
    $menuKey.SetValue("", "Local Pilot")

    $commandKey = $menuKey.CreateSubKey("command")
    $commandKey.SetValue("", $commandText)
}

Remove-MenuKey "Software\Classes\*\shell\AskLocalPilot"
Remove-MenuKey "Software\Classes\Directory\shell\AskLocalPilot"
Remove-MenuKey "Software\Classes\Directory\Background\shell\AskLocalPilot"

Set-MenuKey "Software\Classes\*\shell\LocalPilot" "%1"
Set-MenuKey "Software\Classes\Directory\shell\LocalPilot" "%1"
Set-MenuKey "Software\Classes\Directory\Background\shell\LocalPilot" "%V"

Write-Host "Local Pilot context menu installed for this user."
Write-Host "Right click a file or folder, then click Local Pilot."
