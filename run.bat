@echo off
setlocal

cd /d "%~dp0"

echo ============================================
echo   Riberball - Lot Sizing Scheduling
echo ============================================
echo.

echo [1/3] Verificando dependencias de sistema...
where glpsol >nul 2>nul
if %errorlevel% neq 0 (
    echo  AVISO: Solver GLPK nao encontrado no PATH.
    echo  Para instalar: winget install GNU.GLPK
    echo.
)

echo [2/3] Instalando dependencias Python...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo  ERRO: Falha ao instalar dependencias. Verifique se o Python e pip estao no PATH.
    pause
    exit /b 1
)

echo.
echo [3/3] Iniciando aplicacao...
echo  Acesse: http://localhost:5000
echo  Para encerrar: Ctrl+C
echo.

set PYTHONPATH=%CD%
start "" "http://localhost:5000"
python -m app.main
pause