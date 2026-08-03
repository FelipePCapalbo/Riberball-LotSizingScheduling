@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv" (
    echo Criando ambiente virtual em .venv ...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Instalando dependencias ...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

where cloudflared >nul 2>nul
if errorlevel 1 (
    echo cloudflared nao encontrado no PATH.
    echo Instale antes de continuar: choco install cloudflared ou veja
    echo https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
    exit /b 1
)

if not exist "backend\.env" (
    echo backend\.env nao encontrado - copiando de backend\.env.example.
    copy backend\.env.example backend\.env >nul
    echo Edite backend\.env e preencha SHARED_SECRET ^(mesmo valor configurado no Worker^) antes de rodar novamente.
    exit /b 1
)

echo Iniciando backend FastAPI ^(conectando ao frontend em riberball-lotsizingscheduling.felipecapalbo.workers.dev^) ...
python backend\app.py
