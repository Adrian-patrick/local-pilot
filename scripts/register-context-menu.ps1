# register-context-menu.ps1
# Registers "Ask Local Pilot" in the Windows Explorer right-click context menu

$WorkspaceRoot = Resolve-Path "$PSScriptRoot\.."
$ExePath = Join-Path $WorkspaceRoot "src-tauri\target\release\Local Pilot.exe"

# If the release EXE doesn't exist, check the debug EXE as a fallback
if (-not (Test-Path $ExePath)) {
    $ExePath = Join-Path $WorkspaceRoot "src-tauri\target\debug\Local Pilot.exe"
}

if (-not (Test-Path $ExePath)) {
    Write-Host -ForegroundColor Yellow "WARNING: Built executable not found at `n$ExePath"
    Write-Host -ForegroundColor Yellow "Please run 'npm run tauri build' or 'npm run tauri dev' first to compile the app."
    $ExePath = [IO.Path]::Combine($WorkspaceRoot, "src-tauri\target\release\Local Pilot.exe")
}

Write-Host "Registering Context Menu..."
Write-Host "Target Executable: $ExePath"

# File Context Menu Registry Paths
$RegistryPath = "HKCU:\Software\Classes\*\shell\AskLocalPilot"
$CommandPath = "$RegistryPath\command"

# Create registry keys for files
if (-not (Test-Path $RegistryPath)) {
    New-Item -Path $RegistryPath -Force | Out-Null
}
Set-ItemProperty -Path $RegistryPath -Name "(Default)" -Value "Ask Local Pilot"
Set-ItemProperty -Path $RegistryPath -Name "Icon" -Value $ExePath

if (-not (Test-Path $CommandPath)) {
    New-Item -Path $CommandPath -Force | Out-Null
}
# "%1" passes the path of the right-clicked file to the executable
Set-ItemProperty -Path $CommandPath -Name "(Default)" -Value "`"$ExePath`" `"%1`""

# Folder Context Menu Registry Paths (as a premium bonus)
$FolderRegistryPath = "HKCU:\Software\Classes\Directory\shell\AskLocalPilot"
$FolderCommandPath = "$FolderRegistryPath\command"

if (-not (Test-Path $FolderRegistryPath)) {
    New-Item -Path $FolderRegistryPath -Force | Out-Null
}
Set-ItemProperty -Path $FolderRegistryPath -Name "(Default)" -Value "Ask Local Pilot"
Set-ItemProperty -Path $FolderRegistryPath -Name "Icon" -Value $ExePath

if (-not (Test-Path $FolderCommandPath)) {
    New-Item -Path $FolderCommandPath -Force | Out-Null
}
Set-ItemProperty -Path $FolderCommandPath -Name "(Default)" -Value "`"$ExePath`" `"%1`""

Write-Host -ForegroundColor Green "SUCCESS: 'Ask Local Pilot' has been registered in your right-click context menu!"
Write-Host -ForegroundColor Cyan "You can now right-click any file or folder in Windows Explorer and select 'Ask Local Pilot'."
