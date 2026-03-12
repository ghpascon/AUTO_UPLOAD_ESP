@echo off
:: ===============================
:: Adiciona main.exe ao Startup do Windows
:: ===============================

:: Pega o diretório do BAT
set "SCRIPT_DIR=%~dp0"
set "EXE_PATH=%SCRIPT_DIR%main.exe"

:: Pega a pasta de startup do usuário atual
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

:: Nome do atalho
set "SHORTCUT_NAME=Smartx.lnk"

:: Verifica se main.exe existe
if not exist "%EXE_PATH%" (
    echo main.exe nao encontrado em %EXE_PATH%
    pause
    exit /b
)

:: Cria o atalho usando PowerShell
powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%STARTUP_FOLDER%\%SHORTCUT_NAME%');$s.TargetPath='%EXE_PATH%';$s.WorkingDirectory='%SCRIPT_DIR%';$s.Save()"

echo Atalho criado na pasta Startup:
echo %STARTUP_FOLDER%\%SHORTCUT_NAME%
pause
