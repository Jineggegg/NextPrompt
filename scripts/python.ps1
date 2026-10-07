function Get-CompatiblePython {
    # App hooks inherit a stale PATH. Prefer real per-user installs over Store aliases.
    $candidates = @()
    if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        foreach ($minor in 15..9) {
            $candidates += @{ Name = (Join-Path $env:LOCALAPPDATA "Programs\Python\Python3$minor\python.exe"); Arguments = @() }
        }
        $candidates += @{ Name = (Join-Path $env:LOCALAPPDATA 'Python\bin\python.exe'); Arguments = @() }
        $candidates += @{ Name = (Join-Path $env:LOCALAPPDATA 'Programs\Python\Launcher\py.exe'); Arguments = @('-3') }
    }
    $candidates += @(
        @{ Name = 'python'; Arguments = @() },
        @{ Name = 'python3'; Arguments = @() },
        @{ Name = 'py'; Arguments = @('-3') }
    )
    foreach ($candidate in $candidates) {
        if ([IO.Path]::IsPathRooted($candidate.Name) -and -not (Test-Path -LiteralPath $candidate.Name)) {
            continue
        }
        $command = Get-Command $candidate.Name -ErrorAction SilentlyContinue
        if ($null -eq $command -or $command.Source -match '\\Microsoft\\WindowsApps\\python3?\.exe$') {
            continue
        }
        $pythonArgs = $candidate.Arguments
        try {
            $versionText = & $command.Source @pythonArgs -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>$null
            if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($versionText)) { continue }
            $version = [version]($versionText | Select-Object -Last 1)
            if ($version -ge [version]'3.9') {
                return [PSCustomObject]@{ Command = $command.Source; Arguments = $pythonArgs; Version = $version }
            }
        } catch {
            continue
        }
    }
    return $null
}
