# Para o Python antigo e sobe o Flask deste projeto (pasta do script).
$ErrorActionPreference = 'SilentlyContinue'
Get-Process python* | Stop-Process -Force
Start-Sleep -Seconds 2
$backend = Join-Path $PSScriptRoot 'backend'
Write-Host "A iniciar Flask em: $backend" -ForegroundColor Cyan
Set-Location $backend
python app.py
