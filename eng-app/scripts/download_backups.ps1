param(
    [string]$Destination = (Join-Path (Split-Path $PSScriptRoot -Parent) '学习数据备份'),
    [string]$Identity = "$env:USERPROFILE\.ssh\english_backup"
)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $Destination | Out-Null
$logFile = Join-Path $Destination 'download.log'
$stateFile = Join-Path $Destination 'last-sync.txt'
if (Test-Path -LiteralPath $stateFile) {
    $last = [datetimeoffset]::Parse((Get-Content -LiteralPath $stateFile -Raw).Trim())
    if (([datetimeoffset]::Now - $last).TotalDays -lt 7) { exit 0 }
}
function Write-BackupLog([string]$Message) {
    Add-Content -LiteralPath $logFile -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' ' + $Message) -Encoding UTF8
}
try {
    if (-not (Test-Path -LiteralPath $Identity)) { throw 'Backup SSH key not found.' }
    $ssh = Join-Path $env:WINDIR 'System32\OpenSSH\ssh.exe'
    $scp = Join-Path $env:WINDIR 'System32\OpenSSH\scp.exe'
    $options = @('-i', $Identity, '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=20', '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=3')
    $manifest = & $ssh @options 'admin@120.55.186.234' 'sha256sum /var/backups/pels/learning-*.zip'
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read server backup checksums.' }
    $entries = @($manifest | ForEach-Object {
        if ($_ -notmatch '^([a-fA-F0-9]{64})\s+/var/backups/pels/(learning-\d{8}-\d{6}\.zip)$') { throw 'Unexpected backup manifest entry.' }
        [pscustomobject]@{Hash=$Matches[1];Name=$Matches[2]}
    } | Sort-Object Name -Descending | Select-Object -First 2)
    if (-not $entries.Count) { throw 'No server backup files found.' }
    $newest = [datetimeoffset]::ParseExact(($entries[0].Name.Substring(9,15) + '+08:00'), 'yyyyMMdd-HHmmsszzz', [cultureinfo]::InvariantCulture)
    if (([datetimeoffset]::Now - $newest).TotalHours -lt 12) {
        Write-BackupLog 'DEFER newest server backup is less than 12 hours old'
        exit 0
    }
    $downloaded = 0; $skipped = 0
    foreach ($entry in $entries) {
        $expected = $entry.Hash; $name = $entry.Name
        $target = Join-Path $Destination $name
        if ((Test-Path -LiteralPath $target) -and ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -eq $expected)) { $skipped++; continue }
        $partial = Join-Path $Destination ($name + '.part')
        & $scp @options ("admin@120.55.186.234:/var/backups/pels/" + $name) $partial
        if ($LASTEXITCODE -ne 0) { throw "Download failed: $name" }
        if ((Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash -ne $expected) { throw "Checksum mismatch: $name" }
        Move-Item -LiteralPath $partial -Destination $target -Force
        $downloaded++
    }
    if (($downloaded + $skipped) -eq 0) { throw 'No server backup files found.' }
    # Delete only recognized backups in the explicitly selected destination,
    # and only after both selected server files are SHA256-verified.
    $keep = @($entries | ForEach-Object { $_.Name })
    Get-ChildItem -LiteralPath $Destination -File | Where-Object {
        $_.Name -match '^learning-\d{8}-\d{6}\.zip$' -and $_.Name -notin $keep
    } | ForEach-Object { Remove-Item -LiteralPath $_.FullName }
    [datetimeoffset]::Now.ToString('o') | Set-Content -LiteralPath $stateFile -Encoding ASCII
    Write-BackupLog "OK downloaded=$downloaded verified_existing=$skipped retained=$($keep.Count)"
    exit 0
} catch {
    Write-BackupLog ('ERROR ' + $_.Exception.Message)
    Write-Error $_.Exception.Message
    exit 1
}
