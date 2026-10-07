param([ValidateSet('context', 'stop')][string]$Hook)

$ErrorActionPreference = 'Stop'
if ($env:NEXTPROMPT_INTERNAL -eq '1') { exit 0 }
$OutputEncoding = [Console]::InputEncoding = [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
try {
    $root = Split-Path -Parent $PSScriptRoot
    . (Join-Path $root 'scripts\python.ps1')
    $python = Get-CompatiblePython
    if ($null -eq $python) {
        [Console]::WriteLine('{"systemMessage":"NextPrompt needs Python 3.9+. Run $nextprompt-onboarding to finish installation, then restart Codex and review /hooks."}')
        exit 0
    }
    # Forward Unicode JSON explicitly; Windows PowerShell defaults pipes to ASCII.
    $payload = [Console]::In.ReadToEnd()
    $pythonArgs = @($python.Arguments)
    $payload | & $python.Command @pythonArgs (Join-Path $root "hooks\$Hook.py")
    if ($LASTEXITCODE -ne 0) { throw 'Hook failed' }
} catch {
    # No raw errors or exit 2: a broken suggestion must never continue a Codex turn.
    [Console]::WriteLine('{"systemMessage":"NextPrompt could not start its hook. Run $nextprompt-doctor; automatic suggestions are not ready."}')
}
exit 0
