@echo off
echo Verificando e Instalando dependencias de sistema (Windows)...

where glpsol >nul 2>nul
if %errorlevel% neq 0 (
    echo AVISO: Solver GLPK nao encontrado no PATH.
    echo Para usar o solver GLPK, instale-o manualmente (ex: Winget ou baixar binarios).
    echo Comando sugerido: winget install GNU.GLPK
)

echo Instalando dependencias Python...
pip install -r requirements.txt

echo Iniciando aplicacao...
set PYTHONPATH=%PYTHONPATH%;%CD%
python app/main.py
pause