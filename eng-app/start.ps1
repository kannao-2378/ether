$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (!(Get-Command node -ErrorAction SilentlyContinue)) { $env:Path = 'C:\Program Files\nodejs;' + $env:Path }
if (!(Test-Path '.venv\Scripts\python.exe')) { throw '请先按 README.md 安装 Python 环境和依赖。' }
$backendPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
Start-Process -FilePath $backendPython -ArgumentList '-m','uvicorn','app:app','--host','127.0.0.1','--port','8000' -WorkingDirectory (Join-Path $PSScriptRoot 'backend') -WindowStyle Hidden
Set-Location -LiteralPath (Join-Path $PSScriptRoot 'frontend')
npm.cmd run dev
