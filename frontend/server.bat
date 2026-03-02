@echo off
echo ========================================
echo Servidor Pastelaria Delicia
echo ========================================
echo.

REM Verificar se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado!
    echo.
    echo Por favor, instale o Python 3:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo Iniciando servidor...
echo.
python server.py

pause
