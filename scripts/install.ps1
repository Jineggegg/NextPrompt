[CmdletBinding()]
param(
    [switch]$Probe
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$minimumPython = [version]"3.10"
$pythonPackage = "Python.Python.3.12"
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

function Update-ProcessPath {
    $currentPath = $env:Path
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $pathParts = @($userPath, $machinePath, $currentPath) |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    $env:Path = $pathParts -join [IO.Path]::PathSeparator
}

function Get-CompatiblePython {
    $command = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $command) {
        return $null
    }

    $versionText = & $command.Source -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($versionText)) {
        return $null
    }

    try {
        $version = [version]($versionText | Select-Object -Last 1)
    }
    catch {
        return $null
    }

    if ($version -lt $minimumPython) {
        return $null
    }

    return [PSCustomObject]@{
        Command = $command.Source
        Version = $version
    }
}

function Install-UserPython {
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($null -eq $winget) {
        throw "Python 3.10+ is required and winget is unavailable. Install Python from python.org, then rerun this script."
    }

    Write-Host "Python 3.10+ was not found. Installing Python 3.12 for the current user through winget..."
    $wingetArgs = @(
        "install",
        "--id", $pythonPackage,
        "--exact",
        "--source", "winget",
        "--scope", "user",
        "--silent",
        "--disable-interactivity",
        "--accept-package-agreements",
        "--accept-source-agreements"
    )
    & $winget.Source @wingetArgs
    if ($LASTEXITCODE -ne 0) {
        throw "winget could not install Python (exit code $LASTEXITCODE)."
    }

    Update-ProcessPath
}

Update-ProcessPath
$python = Get-CompatiblePython
if ($null -eq $python) {
    Install-UserPython
    $python = Get-CompatiblePython
}
if ($null -eq $python) {
    throw "Python was installed but the 'python' command is still unavailable. Restart PowerShell and rerun this script."
}

$codex = Get-Command codex -ErrorAction SilentlyContinue
if ($null -eq $codex) {
    throw "Codex CLI is required. Install or repair Codex, then rerun this script."
}

Write-Host "Python $($python.Version) ready."
& $codex.Source plugin marketplace add $repoRoot
if ($LASTEXITCODE -ne 0) {
    throw "Could not register the local codex-prompty marketplace."
}

& $codex.Source plugin add "nextprompt@codex-prompty"
if ($LASTEXITCODE -ne 0) {
    throw "Could not install nextprompt@codex-prompty."
}

$doctorArgs = @((Join-Path $repoRoot "scripts\doctor.py"))
if ($Probe) {
    $doctorArgs += "--probe"
}
& $python.Command @doctorArgs
if ($LASTEXITCODE -ne 0) {
    throw "NextPrompt Doctor reported a required check failure."
}

Write-Host "NextPrompt installed successfully. Restart Codex, review the hook in /hooks, then run `$nextprompt-setup."
