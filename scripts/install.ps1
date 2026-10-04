[CmdletBinding()]
param(
    [switch]$Probe,
    [ValidateSet("on", "off")]
    [string]$AutoCopy,
    # inline: your Codex model ends each reply with the prompt; model: a separate request.
    [ValidateSet("inline", "model")]
    [string]$Source = "inline"
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

    try {
        $versionText = & $command.Source -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>$null
    }
    catch {
        # Windows App Execution Aliases can throw instead of returning a version.
        return $null
    }
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
    throw "Could not register the local nextprompt marketplace."
}

& $codex.Source plugin add "nextprompt@nextprompt"
if ($LASTEXITCODE -ne 0) {
    throw "Could not install nextprompt@nextprompt."
}

$doctorArgs = @((Join-Path $repoRoot "scripts\doctor.py"))
if ($Probe) {
    $doctorArgs += "--probe"
}
& $python.Command @doctorArgs
if ($LASTEXITCODE -ne 0) {
    throw "NextPrompt Doctor reported a required check failure."
}

if ([string]::IsNullOrWhiteSpace($AutoCopy)) {
    Write-Host ""
    Write-Host "NextPrompt clipboard preference"
    Write-Host "Automatically copy suggested next prompts to your clipboard?"
    Write-Host "Y = automatic copy (default); N = display only."
    Write-Host "Other local applications may read clipboard contents."
    try {
        while ([string]::IsNullOrWhiteSpace($AutoCopy)) {
            $answer = (Read-Host "Choose Y or N [Y]").Trim().ToLowerInvariant()
            switch ($answer) {
                { $_ -in @("", "y", "yes") } { $AutoCopy = "on" }
                { $_ -in @("n", "no") } { $AutoCopy = "off" }
                default { Write-Host "Please enter Y or N." }
            }
        }
    }
    catch {
        throw "Clipboard preference was not saved. Rerun interactively, or pass -AutoCopy on|off explicitly."
    }
}

& $python.Command (Join-Path $repoRoot "scripts\nextprompt.py") setup --source $Source --auto-copy $AutoCopy
if ($LASTEXITCODE -ne 0) {
    throw "Could not save the NextPrompt clipboard preference."
}

Write-Host ""
Write-Host "NextPrompt installed successfully."
if ($AutoCopy -eq "on") {
    Write-Host "Automatic clipboard copy: ON. New suggestions will be copied automatically."
    Write-Host "A desktop notification shows each suggestion when it is ready to paste."
}
else {
    Write-Host "Automatic clipboard copy: OFF. Suggestions will be displayed only."
}
if ($Source -eq "inline") {
    Write-Host "Suggestion source: your Codex model ends each reply with a 'Next prompt:' line"
    Write-Host "(labelled in Chinese for Chinese conversations), and exactly that line is copied."
    Write-Host "Pass -Source model for a separate lightweight request instead."
}
else {
    Write-Host "Suggestion source: a separate lightweight model request after each turn."
}
Write-Host "Your clipboard choice has been saved. Other existing settings are preserved."
Write-Host "No additional setup is required."
Write-Host ""
Write-Host "Finish in Codex:"
Write-Host "1. Fully quit and reopen Codex to load the plugin and refreshed PATH."
Write-Host "2. Open /hooks, review each NextPrompt hook (SessionStart, UserPromptSubmit, Stop), and approve/trust it."
Write-Host "   Installation does not grant hook trust or bypass your approval."
Write-Host "3. Complete a normal conversation turn. The reply ends with a line such as:"
Write-Host "   Next prompt: Run the full regression suite and review the final diff."
Write-Host "   (Example only; suggestions depend on the conversation.)"
Write-Host ""
Write-Host "Optional: run `$nextprompt-setup to change clipboard copy or other settings."
Write-Host "Help: run `$nextprompt-status or `$nextprompt-doctor."
Write-Host "If /hooks is unavailable, use a supported Codex client/CLI; automatic suggestions are not verified until the hook loads and is trusted."
