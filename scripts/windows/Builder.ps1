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
# Phase 3A) for the WSL distribution name and the repository path, via Get-BuilderConfigValue
# below -- a small, section-aware scalar-value parser, not a full YAML parser, since this file's
# structure is simple and controlled (top-level "key:" sections, one level of indented
# "key: value" pairs, optional comment lines). It is section-scoped (only lines between a
# section's header and the next top-level line are considered) so a same-named key in an
# unrelated section (e.g. "database: path:") is never matched, and it preserves the full scalar
# value -- including spaces -- for both quoted and unquoted forms, unlike an earlier version of
# this file that used a `\S+` regex and silently truncated any value containing a space (e.g. a
# WSL-mounted Windows path such as /mnt/c/Users/John Doe/builder).

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

function Get-BuilderConfigValue {
    <#
    Extracts the scalar value for $Key nested one level under a top-level "$Section:" block in
    $ConfigTextNoComments (comment lines already stripped by the caller). Returns $null if the
    section, the key, or a non-blank value cannot be found -- never throws, so the caller can
    produce one consistent, clear error message regardless of which part of parsing failed.

    Section-aware: only lines between the "$Section:" header and the next top-level
    (non-indented) line are considered, so a same-named key in an unrelated section is never
    matched. Supports single- or double-quoted scalar values (surrounding quotes stripped,
    interior spaces preserved) and bare unquoted values that may themselves contain spaces (a
    repository path under a Windows user directory with a space in the username, or a WSL
    distribution name with a space).
    #>
    param(
        [Parameter(Mandatory)][string]$ConfigTextNoComments,
        [Parameter(Mandatory)][string]$Section,
        [Parameter(Mandatory)][string]$Key
    )

    $lines = $ConfigTextNoComments -split "`r?`n"
    $sectionHeaderPattern = "^$([regex]::Escape($Section)):\s*$"
    $keyLinePattern = "^\s+$([regex]::Escape($Key)):\s*(.*)$"

    $inSection = $false
    $rawValue = $null

    foreach ($line in $lines) {
        if (-not $inSection) {
            if ($line -match $sectionHeaderPattern) {
                $inSection = $true
            }
            continue
        }

        if ($line -match '^\S') {
            # A new top-level (non-indented) line ends this section -- stop before we wander
            # into an unrelated section's same-named key.
            break
        }

        if ($line -match $keyLinePattern) {
            $rawValue = $Matches[1]
            break
        }
    }

    if ($null -eq $rawValue) {
        return $null
    }

    $trimmed = $rawValue.Trim()
    if ($trimmed.Length -ge 2) {
        $firstChar = $trimmed.Substring(0, 1)
        $lastChar = $trimmed.Substring($trimmed.Length - 1, 1)
        $isQuoted = ($firstChar -eq '"' -and $lastChar -eq '"') -or ($firstChar -eq "'" -and $lastChar -eq "'")
        if ($isQuoted) {
            $trimmed = $trimmed.Substring(1, $trimmed.Length - 2).Trim()
        }
    }

    if ($trimmed -eq "") {
        # Missing or blank value -- same "could not read config" outcome as a missing key.
        return $null
    }

    return $trimmed
}

if (-not (Test-Path $configPath)) {
    Write-BuilderError "Configuration file not found: $configPath"
    exit 1
}

$configText = Get-Content -Raw -Path $configPath
# Strip comment-only lines before matching, so a comment between a section header and its first
# key can't shift which line Get-BuilderConfigValue treats as the key line.
$configTextNoComments = [regex]::Replace($configText, '(?m)^\s*#.*$\r?\n?', '')

$wslDistro = Get-BuilderConfigValue -ConfigTextNoComments $configTextNoComments -Section "wsl" -Key "distribution"
$repoPathLinux = Get-BuilderConfigValue -ConfigTextNoComments $configTextNoComments -Section "repository" -Key "path"

if (-not $wslDistro -or -not $repoPathLinux) {
    Write-BuilderError "Could not read wsl.distribution / repository.path from $configPath"
    exit 1
}

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
#
# The repository path is passed via wsl.exe's own `--cd` argument -- never concatenated into a
# bash string -- so it is never re-parsed as shell syntax. An earlier version built this as
# `bash -lc "cd '$repoPathLinux' && ..."`, which let a repository path containing a single quote
# break out of that quoting and inject arbitrary shell commands (confirmed exploitable with a
# path like `/tmp/x'; echo INJECTED #`). $wslDistro and $repoPathLinux are each passed as their
# own command element (not string-interpolated into one combined argument), so PowerShell's own
# native-argument marshaling -- the same CRT-compatible escaping every well-behaved Windows
# process launcher relies on -- carries each value through intact regardless of embedded spaces,
# apostrophes, `$`, `;`, `&`, backticks, parentheses, `#`, or `"`. `uv run python
# scripts/start_all.py` is a fixed, hardcoded command with no configuration-derived content in
# it at all, so it needs no escaping of its own.
& wsl -d "$wslDistro" --cd "$repoPathLinux" -- uv run python scripts/start_all.py
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-BuilderError "Builder exited with an error (see the messages above)."
    exit $exitCode
}
