# Removes the "Builder" desktop shortcut created by install-shortcut.ps1.
#
# Run from PowerShell on Windows:
#   powershell -ExecutionPolicy Bypass -File uninstall-shortcut.ps1

$ErrorActionPreference = "Stop"

$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktopPath "Builder.lnk"

if (Test-Path $shortcutPath) {
    Remove-Item $shortcutPath -Force
    Write-Host "Removed desktop shortcut: $shortcutPath"
} else {
    Write-Host "No shortcut found at $shortcutPath (nothing to remove)."
}
