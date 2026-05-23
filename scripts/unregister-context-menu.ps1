# unregister-context-menu.ps1
# Unregisters "Ask Local Pilot" from the Windows Explorer right-click context menu

Write-Host "Unregistering Context Menu..."

# Remove file context menu registry keys
$RegistryPath = "HKCU:\Software\Classes\*\shell\AskLocalPilot"
if (Test-Path $RegistryPath) {
    Remove-Item -Path $RegistryPath -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Removed file context menu entries."
}

# Remove folder context menu registry keys
$FolderRegistryPath = "HKCU:\Software\Classes\Directory\shell\AskLocalPilot"
if (Test-Path $FolderRegistryPath) {
    Remove-Item -Path $FolderRegistryPath -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Removed folder context menu entries."
}

Write-Host -ForegroundColor Green "SUCCESS: 'Ask Local Pilot' context menu has been completely unregistered."
