$Root = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Set-Location $Root

if (!(Test-Path "frontend/dist")) {
  Write-Host "请先在 frontend 目录执行 npm install && npm run build"
  exit 1
}

pyinstaller -F backend/run.py `
  --name support-mail-assistant `
  --add-data "frontend/dist;frontend/dist" `
  --hidden-import uvicorn.logging
