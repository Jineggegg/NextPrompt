[CmdletBinding()]
param(
    [switch]$Probe,
    [ValidateSet("on", "off")]
    [string]$AutoCopy,
    [ValidateSet("on", "off")]
    [string]$Notify
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

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

. (Join-Path $PSScriptRoot "python.ps1")

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
    throw "Python 3.12 was installed, but no compatible Python executable is visible yet. Close and reopen PowerShell, then rerun this script."
}

function Find-Codex {
    $command = Get-Command codex -ErrorAction SilentlyContinue
    if ($null -ne $command) {
        return $command
    }
    # The Codex app unpacks its own codex.exe here; outside the app it is not on PATH.
    if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        return $null
    }
    $bundled = Get-ChildItem -Path (Join-Path $env:LOCALAPPDATA "OpenAI\Codex\bin\*\codex.exe") -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($null -eq $bundled) {
        return $null
    }
    return Get-Command $bundled.FullName -ErrorAction SilentlyContinue
}

$codex = Find-Codex
if ($null -eq $codex) {
    throw "Codex was not found. Install and open the Codex app once (or install Codex CLI), then rerun this script."
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

function ConvertFrom-ChoicePair {
    param([string]$Pair)
    # First letter: automatic copy; second letter: desktop notifications.
    if ($Pair -notmatch "^[yn][yn]$") {
        return $null
    }
    return @(
        $(if ($Pair[0] -eq "y") { "on" } else { "off" }),
        $(if ($Pair[1] -eq "y") { "on" } else { "off" })
    )
}

# A flag skips the questions; a setting without a flag keeps the recommended value.
if ([string]::IsNullOrWhiteSpace($AutoCopy) -and [string]::IsNullOrWhiteSpace($Notify)) {
    Write-Host ""
    Write-Host "推荐设置 / Recommended settings:"
    Write-Host "  自动复制到剪贴板：开（推荐） / Automatic clipboard copy: ON (recommended)"
    Write-Host "  桌面通知：开（推荐） / Desktop notifications: ON (recommended)"
    Write-Host "其他本地程序可能读取剪贴板。 / Other local applications may read clipboard contents."
    try {
        $choice = $null
        while ($null -eq $choice) {
            $answer = ((Read-Host "使用推荐设置？ / Keep the recommended settings? [Y/n]") -replace "\s", "").ToLowerInvariant()
            if ($answer -in @("", "y", "yes")) {
                $choice = @("on", "on")
            }
            elseif ($answer -in @("n", "no")) {
                Write-Host "输入两个字母：第 1 个是自动复制，第 2 个是桌面通知（y = 开，n = 关）。"
                Write-Host "Type two letters: 1st = automatic copy, 2nd = desktop notifications (y = on, n = off)."
                Write-Host "  yn = 复制开、通知关 / copy on, notifications off"
                Write-Host "  ny = 复制关、通知开 / copy off, notifications on"
                Write-Host "  nn = 都关 / both off      yy = 都开 / both on"
                while ($null -eq $choice) {
                    $pair = ((Read-Host "yn / ny / nn / yy") -replace "\s", "").ToLowerInvariant()
                    $choice = ConvertFrom-ChoicePair $pair
                    if ($null -eq $choice) {
                        Write-Host "请输入 yn、ny、nn 或 yy。 / Please enter yn, ny, nn or yy."
                    }
                }
            }
            else {
                # Accept a two-letter answer straight away, e.g. yn.
                $choice = ConvertFrom-ChoicePair $answer
                if ($null -eq $choice) {
                    Write-Host "请输入 Y 或 N。 / Please enter Y or N."
                }
            }
        }
        $AutoCopy, $Notify = $choice
    }
    catch {
        throw "Preferences were not saved. Rerun interactively, or pass -AutoCopy on|off and -Notify on|off explicitly."
    }
}
if ([string]::IsNullOrWhiteSpace($AutoCopy)) {
    $AutoCopy = "on"
}
if ([string]::IsNullOrWhiteSpace($Notify)) {
    $Notify = "on"
}

& $python.Command @pythonArgs (Join-Path $repoRoot "scripts\nextprompt.py") setup --auto-copy $AutoCopy --notify $Notify
if ($LASTEXITCODE -ne 0) {
    throw "Could not save the NextPrompt preferences."
}

Write-Host ""
Write-Host "NextPrompt 安装完成 / NextPrompt installed successfully."
if ($AutoCopy -eq "on") {
    Write-Host "自动复制：开，新建议会自动复制到剪贴板。 / Automatic clipboard copy: ON. New suggestions will be copied automatically."
}
else {
    Write-Host "自动复制：关，建议只显示不复制。 / Automatic clipboard copy: OFF. Suggestions will be displayed only."
}
if ($Notify -eq "on") {
    Write-Host "桌面通知：开，建议准备好时弹出系统通知。 / Desktop notifications: ON. A notification appears when a suggestion is ready."
}
else {
    Write-Host "桌面通知：关。 / Desktop notifications: OFF."
}
Write-Host "以上选择已保存，其他已有设置保持不变。 / Your choices have been saved. Other existing settings are preserved."
Write-Host "不需要再运行 setup。 / No additional setup is required."
Write-Host ""
Write-Host "接下来在 Codex 里 / Finish in Codex:"
Write-Host "1. 完全退出并重新打开 Codex。 / Fully quit and reopen Codex to load the plugin and refreshed PATH."
Write-Host "2. 打开 /hooks，检查并信任 NextPrompt 的 SessionStart、UserPromptSubmit 和 Stop Hook。"
Write-Host "   / Open /hooks, review the NextPrompt SessionStart, UserPromptSubmit and Stop hooks, and trust them."
Write-Host "   安装不会替你信任 Hook。 / Installation does not grant hook trust or bypass your approval."
Write-Host "3. 正常聊一轮。有值得做的下一步时，回复末尾会有一行建议，例如："
Write-Host "   / Complete a normal conversation turn. When a next step is worth it, the reply ends with a line such as:"
Write-Host "   → 要不要「接着写第三章」？"
Write-Host "   引号里的指令会复制到剪贴板（中文会加上“做吧”之类的收尾）。 / The quoted prompt is copied to the clipboard."
Write-Host "   （仅为示例 / Example only; suggestions depend on the conversation.）"
Write-Host "   建议不会自动发送，请检查后自己粘贴发送。 / It is never sent automatically; review, paste and send it yourself."
Write-Host ""
Write-Host "以后修改自动复制或通知：`$nextprompt-setup / Optional: run `$nextprompt-setup to change clipboard copy or turn notifications on or off."
Write-Host "暂停或恢复建议：`$nextprompt-disable、`$nextprompt-enable / Pause or resume suggestions: `$nextprompt-disable or `$nextprompt-enable."
Write-Host "查看状态或排查：`$nextprompt-status、`$nextprompt-doctor / Help: run `$nextprompt-status or `$nextprompt-doctor."
Write-Host "If /hooks is unavailable, use a supported Codex client/CLI; automatic suggestions are not verified until the hook loads and is trusted."
