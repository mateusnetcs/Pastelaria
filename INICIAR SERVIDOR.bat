@echo off
chcp 65001 >nul
setlocal
title Pastelao Brothers - Iniciar servidores

rem Sempre a pasta deste .bat (funciona com espacos no caminho)
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

echo ========================================
echo   Pastelao Brothers - Iniciar servidores
echo ========================================
echo   Pasta: %ROOT%
echo.
echo [IMPORTANTE] Vou encerrar TODOS os processos "python.exe" para a
echo              porta 5000 usar o codigo NOVO (senao o QR da 404^).
echo              Se tiver outro projeto em Python, guarde antes.
echo.
pause

echo A encerrar processos Python antigos...
taskkill /F /IM python.exe /T 2>nul
timeout /t 2 /nobreak >nul
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado no PATH.
    echo Instale Python 3 e marque "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

echo [1/2] Backend Flask ^(porta 5000^)
echo       API + ficheiros: http://localhost:5000
echo       Admin:           http://localhost:5000/admin.html
echo.
start "Pastelao - Flask :5000" /D "%ROOT%\backend" cmd /k "python app.py"

timeout /t 2 /nobreak >nul

echo [2/2] Frontend dev ^(porta 8001 - opcional^)
echo       Site: http://localhost:8001  ^(chama API na 5000 via api.js^)
echo.
start "Pastelao - Frontend :8001" /D "%ROOT%\frontend" cmd /k "python server.py"

echo.
echo Concluido. Duas janelas foram abertas.
echo.
echo Teste rapido: quando o Flask mostrar "Running on", abra no browser:
echo   http://localhost:5000/api/diag
echo   (deve aparecer JSON com "waha_qr_blueprint": true^)
echo.
echo Admin: http://localhost:5000/admin.html
echo Para parar: feche cada janela do titulo "Pastelao" ou Ctrl+C.
echo.
start "" "http://localhost:5000/api/diag"
pause
