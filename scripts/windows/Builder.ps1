# Builder launcher (Phase 3A) — Windows-side entrypoint invoked by the "Builder" desktop shortcut.
#
# This script's only job is to get into WSL2 and hand off to the real launcher
# (scripts/start_all.py), which does all the actual dependency checking, service startup,
# health polling, and browser opening on the Linux side. Everything this script checks here is
# specifically the Windows-side prerequisite (WSL2 itself, the configured distribution) --
# repository path, Python/uv, Node/npm, and port availability are re-checked by start_all.py
# once we're already inside WSL, so that logic is never duplicated across the two sides.
#
# Reads config/builder.yaml (the single central configuration source used everywhere else in
# Phase 3A) for the WSL distribution name and the repository path, via a small, deliberately
# minimal regex extraction -- not a full YAML parser -- since this file's structure is simple
# and controlled. Comment-only lines are stripped first so a "key:\n  value" match can't
# accidentally skip past the real value to a later section's same-named key (verified against
# a real config/builder.yaml containing inline comments -- an earlier, comment-unaware version
# of this regex matched the wrong "path:" entirely). If config/builder.yaml's structure changes
# beyond simple "key:\n  value" pairs, update the two regexes below.

$ErrorActionPreference = "Stop"

$repoRootWindows = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$configPath = Join-Path $repoRootWindows "config\builder.yaml"

function Write-BuilderError {
    param([string]$Message)
    Write-Host ""
    Write-Host "Builder could not start:" -ForegroundColor Red
    Write-Host "  $Message" -ForegroundColor Red
    Write-Host ""
}

if (-not (Test-Path $configPath)) {
    Write-BuilderError "Configuration file not found: $configPath"
    exit 1
}

$configText = Get-Content -Raw -Path $configPath
# Strip comment-only lines before matching, so a "key:\n  value" pattern can't skip past a
# comment line and accidentally land on a different section's same-named key.
$configTextNoComments = [regex]::Replace($configText, '(?m)^\s*#.*$\r?\n?', '')

$distroMatch = [regex]::Match($configTextNoComments, '(?ms)^wsl:\s*\r?\n\s*distribution:\s*(\S+)')
$pathMatch = [regex]::Match($configTextNoComments, '(?ms)^repository:\s*\r?\n\s*path:\s*(\S+)')

if (-not $distroMatch.Success -or -not $pathMatch.Success) {
    Write-BuilderError "Could not read wsl.distribution / repository.path from $configPath"
    exit 1
}

$wslDistro = $distroMatch.Groups[1].Value
$repoPathLinux = $pathMatch.Groups[1].Value

# 1. WSL2 itself.
$wslCommand = Get-Command wsl -ErrorAction SilentlyContinue
if (-not $wslCommand) {
    Write-BuilderError "WSL was not found on this machine. Install it first: wsl --install"
    exit 1
}

# 2. The configured distribution.
$installedDistros = (wsl -l -q) -replace "`0", ""
$distroFound = $installedDistros -split "`r?`n" | Where-Object { $_.Trim() -eq $wslDistro }
if (-not $distroFound) {
    Write-BuilderError (
        "WSL distribution '$wslDistro' was not found. Installed distributions:`n" +
        (($installedDistros -split "`r?`n" | Where-Object { $_.Trim() -ne "" }) -join "`n")
    )
    exit 1
}

Write-Host "[Builder] Starting via WSL distribution '$wslDistro'..."

# Everything else (repo path, Python/uv, Node/npm, ports, database setup, service health,
# opening the dashboard) is handled inside WSL by scripts/start_all.py.
& wsl -d $wslDistro -- bash -lc "cd '$repoPathLinux' && uv run python scripts/start_all.py"
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-BuilderError "Builder exited with an error (see the messages above)."
    exit $exitCode
}
