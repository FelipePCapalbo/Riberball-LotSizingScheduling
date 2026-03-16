@echo off
setlocal EnableDelayedExpansion
chcp 65001 > nul
title Riberball - Build do Executavel

set APP_NAME=RiverballLotSizing
set DIST_DIR=dist\%APP_NAME%
set RELEASE_DIR=release\%APP_NAME%

echo ============================================================
echo   Riberball Lot Sizing - Build do Executavel (.exe)
echo ============================================================
echo.

REM ── 1. Verifica Python ──────────────────────────────────────
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado no PATH.
    echo        Instale em https://www.python.org e marque "Add to PATH".
    pause & exit /b 1
)
echo [OK] Python encontrado.

REM ── 2. Instala dependências ──────────────────────────────────
echo.
echo [1/5] Instalando dependencias do projeto...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar requirements.txt
    pause & exit /b 1
)

echo [2/5] Instalando PyInstaller...
pip install pyinstaller --quiet
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar PyInstaller
    pause & exit /b 1
)
echo [OK] Dependencias prontas.

REM ── 3. Limpa builds anteriores ──────────────────────────────
echo.
echo [3/5] Limpando builds anteriores...
if exist build          rmdir /s /q build
if exist dist           rmdir /s /q dist
if exist release        rmdir /s /q release
echo [OK] Pastas limpas.

REM ── 4. Compila o executável ──────────────────────────────────
echo.
echo [4/5] Compilando o executavel com PyInstaller...
echo       (Isso pode levar alguns minutos...)
echo.
pyinstaller riberball.spec
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Falha na compilacao. Leia o log acima para detalhes.
    pause & exit /b 1
)
echo [OK] Executavel compilado em %DIST_DIR%\

REM ── 5. Monta a pasta de distribuição limpa (release/) ────────
echo.
echo [5/5] Montando pasta de distribuicao limpa em release\%APP_NAME%\...

REM Cria a pasta de release
mkdir "%RELEASE_DIR%"

REM Copia o executável principal
copy /Y "%DIST_DIR%\%APP_NAME%.exe"  "%RELEASE_DIR%\%APP_NAME%.exe" >nul

REM Copia as DLLs e arquivos de runtime gerados pelo PyInstaller
REM (todos exceto o .exe, pois já foi copiado acima)
for /f "delims=" %%f in ('dir /b "%DIST_DIR%\*" ^| findstr /v /i "%APP_NAME%.exe"') do (
    if exist "%DIST_DIR%\%%f\" (
        xcopy /E /I /Q /Y "%DIST_DIR%\%%f" "%RELEASE_DIR%\%%f" >nul
    ) else (
        copy /Y "%DIST_DIR%\%%f" "%RELEASE_DIR%\%%f" >nul
    )
)

REM Copia os módulos Python da aplicação (necessários em runtime)
xcopy /E /I /Q /Y "app"  "%RELEASE_DIR%\app"  >nul

REM Copia os dados de entrada
xcopy /E /I /Q /Y "data" "%RELEASE_DIR%\data" >nul

echo [OK] Pasta de distribuicao pronta.

REM ── Resultado final ───────────────────────────────────────────
echo.
echo ============================================================
echo   BUILD CONCLUIDO COM SUCESSO!
echo ============================================================
echo.
echo   Executavel: %RELEASE_DIR%\%APP_NAME%.exe
echo.
echo   Para distribuir, copie a pasta inteira:
echo     %RELEASE_DIR%\
echo.
echo   Conteudo da pasta de distribuicao:
echo     %APP_NAME%.exe   <- executavel principal
echo     app\             <- modulos Python (obrigatorio)
echo     data\            <- arquivos de dados (obrigatorio)
echo     *.dll / *.pyd    <- runtime Python empacotado
echo ============================================================
echo.
pause
