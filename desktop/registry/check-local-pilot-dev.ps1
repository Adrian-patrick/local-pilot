$keys = @(
    "Software\Classes\*\shell\LocalPilot",
    "Software\Classes\*\shell\LocalPilot\command",
    "Software\Classes\Directory\shell\LocalPilot\command",
    "Software\Classes\Directory\Background\shell\LocalPilot\command"
)

foreach ($keyPath in $keys) {
    $key = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey($keyPath)
    if ($key) {
        Write-Host "$keyPath = $($key.GetValue(''))"
    } else {
        Write-Host "$keyPath = missing"
    }
}

