[CmdletBinding()]
param(
    [switch]$Probe,
    [ValidateSet("on", "off")]
    [string]$AutoCopy
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$minimumPython = [version]"3.9"
$pythonPackage = "Python.Python.3.12"
$pythonOrgVersion = "3.12.10"
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
    # Same order as the hook command: python, python3, then the py launcher.
    $candidates = @(
        @{ Name = "python"; Arguments = @() },
        @{ Name = "python3"; Arguments = @() },
        @{ Name = "py"; Arguments = @("-3") }
    )
    foreach ($candidate in $candidates) {
        $command = Get-Command $candidate.Name -ErrorAction SilentlyContinue
        if ($null -eq $command) {
            continue
        }

        $pythonArgs = $candidate.Arguments
        try {
            $versionText = & $command.Source @pythonArgs -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>$null
        }
        catch {
            # Windows App Execution Aliases can throw instead of returning a version.
            continue
        }
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($versionText)) {
            continue
        }

        try {
            $version = [version]($versionText | Select-Object -Last 1)
        }
        catch {
            continue
        }

        if ($version -ge $minimumPython) {
            return [PSCustomObject]@{
                Command = $command.Source
                Arguments = $pythonArgs
                Version = $version
            }
        }
    }

    return $null
}

function Install-PythonFromPythonOrg {
    # Used only when winget is unavailable: the official installer, accepted only
    # when its Authenticode signature is valid and belongs to the Python Software Foundation.
    $suffix = if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") { "-arm64" } elseif ([Environment]::Is64BitOperatingSystem) { "-amd64" } else { "" }
    $fileName = "python-$pythonOrgVersion$suffix.exe"
    $url = "https://www.python.org/ftp/python/$pythonOrgVersion/$fileName"
    $installer = Join-Path ([IO.Path]::GetTempPath()) $fileName

    Write-Host "未找到 winget，正在从 python.org 下载官方 Python $pythonOrgVersion 安装包…"
    Write-Host "winget is unavailable. Downloading the official Python $pythonOrgVersion installer from python.org..."
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing
    }
    catch {
        throw "Could not download Python from python.org. Install Python 3.9+ yourself, then rerun this script."
    }

    $signature = Get-AuthenticodeSignature -FilePath $installer
    if ($signature.Status -ne "Valid" -or $null -eq $signature.SignerCertificate -or
        $signature.SignerCertificate.Subject -notmatch "Python Software Foundation") {
        Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue
        throw "The downloaded Python installer is not signed by the Python Software Foundation; it was deleted and not run."
    }

    $process = Start-Process -FilePath $installer -Wait -PassThru -ArgumentList @(
        "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_launcher=1", "Include_test=0"
    )
    Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue
    if ($process.ExitCode -ne 0) {
        throw "The Python installer failed (exit code $($process.ExitCode))."
    }
}

function Install-UserPython {
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($null -eq $winget) {
        Install-PythonFromPythonOrg
        Update-ProcessPath
        return
    }

    Write-Host "未找到 Python 3.9+，正在通过 winget 为当前用户安装 Python 3.12…"
    Write-Host "Python 3.9+ was not found. Installing Python 3.12 for the current user through winget..."
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
    throw "Python 3.12 was installed, but no python, python3 or py command with Python 3.9+ is visible yet. Close and reopen PowerShell, then rerun this script."
}

$codex = Get-Command codex -ErrorAction SilentlyContinue
if ($null -eq $codex) {
    throw "Codex CLI is required. Install or repair Codex, then rerun this script."
}

$pythonArgs = @($python.Arguments)
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
& $python.Command @pythonArgs @doctorArgs
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

& $python.Command @pythonArgs (Join-Path $repoRoot "scripts\nextprompt.py") setup --auto-copy $AutoCopy
if ($LASTEXITCODE -ne 0) {
    throw "Could not save the NextPrompt clipboard preference."
}

Write-Host ""
Write-Host "NextPrompt 安装完成 / NextPrompt installed successfully."
if ($AutoCopy -eq "on") {
    Write-Host "自动复制：开，新建议会自动复制到剪贴板。 / Automatic clipboard copy: ON. New suggestions will be copied automatically."
}
else {
    Write-Host "自动复制：关，建议只显示不复制。 / Automatic clipboard copy: OFF. Suggestions will be displayed only."
}
Write-Host "桌面通知：默认开，可以单独关闭。 / Desktop notifications: ON by default; you can turn them off without disabling suggestions."
Write-Host "剪贴板选择已保存，其他已有设置保持不变。 / Your clipboard choice has been saved. Other existing settings are preserved."
Write-Host "不需要再运行 setup。 / No additional setup is required."
Write-Host ""
Write-Host "接下来在 Codex 里 / Finish in Codex:"
Write-Host "1. 完全退出并重新打开 Codex。 / Fully quit and reopen Codex to load the plugin and refreshed PATH."
Write-Host "2. 打开 /hooks，检查并信任 NextPrompt 的 SessionStart、UserPromptSubmit 和 Stop Hook。"
Write-Host "   / Open /hooks, review the NextPrompt SessionStart, UserPromptSubmit and Stop hooks, and trust them."
Write-Host "   安装不会替你信任 Hook。 / Installation does not grant hook trust or bypass your approval."
Write-Host "3. 正常聊一轮。每条回复末尾会有一行下一步建议，例如："
Write-Host "   / Complete a normal conversation turn. A useful suggestion appears as:"
Write-Host "   Next prompt: Run the full regression suite and review the final diff."
Write-Host "   （仅为示例 / Example only; suggestions depend on the conversation.）"
Write-Host "   建议不会自动发送，请检查后自己粘贴发送。 / It is never sent automatically; review, paste and send it yourself."
Write-Host ""
Write-Host "修改设置或关闭通知：`$nextprompt-setup / Optional: run `$nextprompt-setup to change clipboard copy or turn off notifications."
Write-Host "暂停或恢复建议：`$nextprompt-disable、`$nextprompt-enable / Pause or resume suggestions: `$nextprompt-disable or `$nextprompt-enable."
Write-Host "查看状态或排查：`$nextprompt-status、`$nextprompt-doctor / Help: run `$nextprompt-status or `$nextprompt-doctor."
Write-Host "If /hooks is unavailable, use a supported Codex client/CLI; automatic suggestions are not verified until the hook loads and is trusted."
