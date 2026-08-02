# Creates the "Builder" desktop shortcut (Phase 3A).
#
# Run once from PowerShell on Windows:
#   powershell -ExecutionPolicy Bypass -File install-shortcut.ps1
#
# The shortcut's target is Builder.cmd in this same folder; its working directory is set to
# this folder too, so it behaves the same regardless of where it's double-clicked from.

$ErrorActionPreference = "Stop"

$scriptDir = $PSScriptRoot
$targetPath = Join-Path $scriptDir "Builder.cmd"

if (-not (Test-Path $targetPath)) {
    Write-Host "ERROR: Builder.cmd not found next to this script ($targetPath)." -ForegroundColor Red
    exit 1
}

$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktopPath "Builder.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $targetPath
$shortcut.WorkingDirectory = $scriptDir
$shortcut.Description = "Start Builder (Phase 3A: task intake, no Agent Zero yet)"
$shortcut.IconLocation = "shell32.dll,220"
$shortcut.Save()

Write-Host "Created desktop shortcut: $shortcutPath"
Write-Host "Double-click it to start Builder."
