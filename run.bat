@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

rem --- Python'u bul (once PATH'teki python, yoksa py baslaticisi) ---
set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY (
    where py >nul 2>&1 && set "PY=py -3"
)
if not defined PY (
    echo Python bulunamadı. https://www.python.org/downloads/ adresinden kur
    echo ve kurulumda "Add python.exe to PATH" seçeneğini işaretle.
    pause
    exit /b 1
)

rem --- Eksik paketleri konsolda kur (ilerleme görünsün diye) ---
%PY% -c "from shadowmacro.deps import ensure_requirements; ensure_requirements()"
if errorlevel 1 (
    echo.
    echo Paket kurulumu başarısız oldu.
    pause
    exit /b 1
)

rem --- Uygulamayı konsolsuz başlat (pythonw), yoksa normal python ile ---
for /f "delims=" %%i in ('%PY% -c "import sys, os; print(os.path.join(os.path.dirname(sys.executable), 'pythonw.exe'))"') do set "PYW=%%i"
if exist "%PYW%" (
    start "" "%PYW%" "%~dp0macro.py"
) else (
    %PY% "%~dp0macro.py"
    if errorlevel 1 pause
)
endlocal
