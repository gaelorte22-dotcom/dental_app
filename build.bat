@echo off
title DentalApp — Compilador
color 0A
echo.
echo  ==========================================
echo   🦷  DentalApp — Generador de Ejecutable
echo  ==========================================
echo.

:: Verificar que PyInstaller esté instalado
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] PyInstaller no encontrado. Instalando...
    pip install pyinstaller
)

:: Verificar que reportlab esté instalado
pip show reportlab >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] ReportLab no encontrado. Instalando...
    pip install reportlab
)

:: Verificar que plyer esté instalado
pip show plyer >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] Plyer no encontrado. Instalando...
    pip install plyer
)

echo.
echo  [*] Limpiando compilaciones anteriores...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
if exist "DentalApp.spec" del /q DentalApp.spec

echo  [*] Compilando DentalApp...
echo.

pyinstaller ^
    --onefile ^
    --windowed ^
    --name="DentalApp" ^
    --icon="diente.ico" ^
    --add-data="database;database" ^
    --add-data="modules;modules" ^
    --add-data="theme.py;." ^
    --add-data="notificaciones.py;." ^
    --add-data="license_manager.py;." ^
    --add-data="activation_screen.py;." ^
    --add-data="generate_license.py;." ^
    --add-data="diente.ico;." ^
    --hidden-import="reportlab" ^
    --hidden-import="reportlab.lib" ^
    --hidden-import="reportlab.lib.pagesizes" ^
    --hidden-import="reportlab.platypus" ^
    --hidden-import="reportlab.lib.styles" ^
    --hidden-import="reportlab.lib.units" ^
    --hidden-import="reportlab.lib.colors" ^
    --hidden-import="plyer" ^
    --hidden-import="plyer.platforms.win.notification" ^
    --hidden-import="sqlite3" ^
    main.py

echo.
if exist "dist\DentalApp.exe" (
    echo  ==========================================
    echo   ✅  Compilacion exitosa!
    echo   📁  Archivo: dist\DentalApp.exe
    echo  ==========================================
    echo.
    echo  [*] Copiando archivos necesarios a dist\...
    
    :: Crear carpeta de distribución completa
    mkdir "dist\DentalApp_Release" 2>nul
    copy "dist\DentalApp.exe" "dist\DentalApp_Release\DentalApp.exe"
    copy "diente.ico" "dist\DentalApp_Release\diente.ico" 2>nul
    
    echo.
    echo  ✅  Todo listo en dist\DentalApp_Release\
    echo.
    echo  Ahora puedes:
    echo   1. Usar DentalApp.exe directamente, o
    echo   2. Abrir installer.iss con Inno Setup para crear el instalador
    echo.
) else (
    echo  ==========================================
    echo   ❌  Error en la compilacion
    echo   Revisa los mensajes de error arriba
    echo  ==========================================
)

pause
