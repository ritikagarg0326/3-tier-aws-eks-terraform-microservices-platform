# Creates .env from .env.example with freshly generated random secrets (Windows PowerShell 5+/7).
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
if (Test-Path .env) { Write-Host '.env already exists - delete it first to regenerate.'; exit 1 }

function New-Secret([int]$Length = 24) {
  $chars = [char[]]'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  $bytes = New-Object byte[] $Length
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
  -join ($bytes | ForEach-Object { $chars[$_ % $chars.Length] })
}

$lines = Get-Content .env.example
$secrets = @{ MYSQL_ROOT_PASSWORD = 24; AUTH_DB_PASSWORD = 24; USER_DB_PASSWORD = 24; CONTENT_DB_PASSWORD = 24; VIDEO_DB_PASSWORD = 24; WATCHLIST_DB_PASSWORD = 24; HISTORY_DB_PASSWORD = 24; MINIO_ROOT_PASSWORD = 24; JWT_SECRET = 64 }
$out = foreach ($line in $lines) {
  $key = ($line -split '=', 2)[0]
  if ($secrets.ContainsKey($key)) { "$key=$(New-Secret $secrets[$key])" } else { $line }
}
# write UTF-8 without BOM, LF endings (docker compose is picky about BOMs)
[System.IO.File]::WriteAllText((Join-Path (Get-Location) '.env'), (($out -join "`n") + "`n"), (New-Object System.Text.UTF8Encoding($false)))
Write-Host 'Created .env with random secrets. Sample logins: see README (admin@hotstar-demo.com / Admin@12345).'
