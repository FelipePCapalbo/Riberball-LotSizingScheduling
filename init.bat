@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONSTARTUP="
set "PYTHONNOUSERSITE=1"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "PIP_REQUIRE_VIRTUALENV=1"

set "WORKER_URL=https://riberball-lotsizingscheduling.felipecapalbo.workers.dev"
set "CLOUDFLARED_URL=https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
set "VENV_PYTHON=%CD%\.venv\Scripts\python.exe"
set "BASE_PYTHON="

echo.
echo Riberball - planejamento semanal e programacao por turno
echo.

if /i not "%PROCESSOR_ARCHITECTURE%"=="AMD64" (
    if /i not "%PROCESSOR_ARCHITEW6432%"=="AMD64" (
        echo Esta maquina nao e x64 ^(%PROCESSOR_ARCHITECTURE%^).
        echo O sistema so foi validado em Windows 64 bits.
        echo.
        pause
        exit /b 1
    )
)

echo [1/5] Procurando um Python compativel ...

call :probe_python "py -3.12"
call :probe_python "py -3.13"
call :probe_python "py -3.11"
call :probe_python "py -3.10"
call :probe_python "py -3"
call :probe_python "python"

if not defined BASE_PYTHON (
    echo.
    echo Nenhum Python compativel foi encontrado nesta maquina.
    echo.
    echo Instale o Python 3.12 de 64 bits em
    echo     https://www.python.org/downloads/windows/
    echo aceitando as opcoes padrao do instalador, e execute este arquivo de novo.
    echo.
    echo Requisitos: versao 3.10 a 3.13, 64 bits.
    echo.
    pause
    exit /b 1
)

echo       Python base: !BASE_PYTHON!

echo [2/5] Preparando o ambiente isolado em .venv ...

set "VENV_OK=0"
if exist "%VENV_PYTHON%" (
    "%VENV_PYTHON%" -E -s -c "import sys, pip" >nul 2>nul
    if not errorlevel 1 set "VENV_OK=1"
)

if "!VENV_OK!"=="0" (
    if exist ".venv" (
        echo       ambiente anterior invalido ^(o Python base mudou^) - recriando
        rmdir /s /q ".venv"
    )
    !BASE_PYTHON! -E -s -m venv ".venv"
)

if not exist "%VENV_PYTHON%" (
    echo.
    echo Falha ao criar o ambiente virtual em .venv.
    echo.
    pause
    exit /b 1
)

echo [3/5] Conferindo as dependencias ...

set "NEED_INSTALL=1"
if exist ".venv\requirements.stamp" (
    fc /b "requirements.txt" ".venv\requirements.stamp" >nul 2>nul
    if not errorlevel 1 set "NEED_INSTALL=0"
)

if "!NEED_INSTALL!"=="0" (
    echo       ja instaladas
) else (
    if exist "wheels" (
        echo       instalando a partir de wheels\ ^(offline^)
        "%VENV_PYTHON%" -E -s -m pip install --quiet --no-index --find-links "wheels" -r "requirements.txt"
    ) else (
        echo       baixando do PyPI ^(so na primeira execucao^)
        "%VENV_PYTHON%" -E -s -m pip install --quiet -r "requirements.txt"
    )
    if errorlevel 1 (
        echo.
        echo Falha ao instalar as dependencias.
        echo.
        pause
        exit /b 1
    )
    copy /y "requirements.txt" ".venv\requirements.stamp" >nul
)

echo [4/5] Conferindo o cloudflared ...

if exist "cloudflared.exe" (
    echo       ja presente nesta pasta
) else (
    echo       baixando cloudflared.exe para esta pasta
    curl -fL --progress-bar -o "cloudflared.exe" "%CLOUDFLARED_URL%"
    if errorlevel 1 (
        if exist "cloudflared.exe" del /q "cloudflared.exe"
        echo.
        echo Nao foi possivel baixar o cloudflared.
        echo Baixe manualmente cloudflared-windows-amd64.exe em
        echo     https://github.com/cloudflare/cloudflared/releases/latest
        echo renomeie para cloudflared.exe e coloque nesta mesma pasta.
        echo.
        pause
        exit /b 1
    )
)

if not exist "backend\.env" (
    echo.
    echo backend\.env nao encontrado.
    echo Copie para backend\.env o arquivo de configuracao enviado junto com o sistema.
    echo.
    pause
    exit /b 1
)

echo [5/5] Iniciando o backend e abrindo a interface ...
echo.
echo       Interface: %WORKER_URL%
echo       Feche esta janela para encerrar o sistema.
echo.

start "" "%WORKER_URL%"
"%VENV_PYTHON%" -E -s -X utf8 "backend\app.py"

echo.
echo Backend encerrado.
pause
exit /b 0

:probe_python
if defined BASE_PYTHON goto :eof
%~1 -E -s -c "import sys, venv, ensurepip; assert sys.version_info[:2] in ((3,10),(3,11),(3,12),(3,13)); assert sys.maxsize.bit_length() == 63" >nul 2>nul
if errorlevel 1 goto :eof
set "BASE_PYTHON=%~1"
goto :eof
