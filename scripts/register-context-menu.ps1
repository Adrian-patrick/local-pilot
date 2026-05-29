# register-context-menu.ps1
# Registers "Ask Local Pilot" in the Windows Explorer right-click context menu
# Updated for the Python-native application (no more Tauri)

$WorkspaceRoot = Resolve-Path "$PSScriptRoot\.."

# Find pythonw.exe (windowless Python) — prefer the project venv, else system
$VenvPythonW = Join-Path $WorkspaceRoot ".venv\Scripts\pythonw.exe"
$VenvPython = Join-Path $WorkspaceRoot ".venv\Scripts\python.exe"

if (Test-Path $VenvPythonW) {
    $PythonExe = $VenvPythonW
} elseif (Test-Path $VenvPython) {
    $PythonExe = $VenvPython
} else {
    # Fall back to system pythonw
    $PythonExe = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
    if (-not $PythonExe) {
        $PythonExe = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
    }
}

if (-not $PythonExe) {
    Write-Host -ForegroundColor Red "ERROR: Python not found. Please install Python 3.11+ first."
    exit 1
}

$MainScript = Join-Path $WorkspaceRoot "main.py"

if (-not (Test-Path $MainScript)) {
    Write-Host -ForegroundColor Red "ERROR: main.py not found at $MainScript"
    exit 1
}

# Build the command: pythonw.exe "path\to\main.py" "%1"
$Command = "`"$PythonExe`" `"$MainScript`" `"%1`""

Write-Host "Registering Context Menu..."
Write-Host "Python:  $PythonExe"
Write-Host "Script:  $MainScript"
Write-Host "Command: $Command"

# File Context Menu Registry Paths
$RegistryPath = "HKCU:\Software\Classes\*\shell\AskLocalPilot"
$CommandPath = "$RegistryPath\command"

# Create registry keys for files
if (-not (Test-Path $RegistryPath)) {
    New-Item -Path $RegistryPath -Force | Out-Null
}
Set-ItemProperty -Path $RegistryPath -Name "(Default)" -Value "Ask Local Pilot"
Set-ItemProperty -Path $RegistryPath -Name "Icon" -Value "$PythonExe,0"

if (-not (Test-Path $CommandPath)) {
    New-Item -Path $CommandPath -Force | Out-Null
}
Set-ItemProperty -Path $CommandPath -Name "(Default)" -Value $Command

# Folder Context Menu Registry Paths
$FolderRegistryPath = "HKCU:\Software\Classes\Directory\shell\AskLocalPilot"
$FolderCommandPath = "$FolderRegistryPath\command"

if (-not (Test-Path $FolderRegistryPath)) {
    New-Item -Path $FolderRegistryPath -Force | Out-Null
}
Set-ItemProperty -Path $FolderRegistryPath -Name "(Default)" -Value "Ask Local Pilot"
Set-ItemProperty -Path $FolderRegistryPath -Name "Icon" -Value "$PythonExe,0"

if (-not (Test-Path $FolderCommandPath)) {
    New-Item -Path $FolderCommandPath -Force | Out-Null
}
Set-ItemProperty -Path $FolderCommandPath -Name "(Default)" -Value $Command

Write-Host -ForegroundColor Green "`nSUCCESS: 'Ask Local Pilot' has been registered in your right-click context menu!"
Write-Host -ForegroundColor Cyan "You can now right-click any file or folder in Windows Explorer and select 'Ask Local Pilot'."
