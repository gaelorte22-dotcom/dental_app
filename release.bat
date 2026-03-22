@echo off
title DentalApp — Release Manager
color 0A
echo.
echo  ==========================================
echo   DentalApp — Generar Nueva Version
echo  ==========================================
echo.

:: Pedir la nueva version
set /p VERSION="Ingresa la nueva version (ej: 1.2.0): "
if "%VERSION%"=="" (
    echo [!] Version no puede estar vacia.
    pause
    exit /b
)

echo.
:: Pedir descripcion de novedades
echo  Escribe las novedades de esta version:
echo  (Ejemplo: Fix de periodontograma, mejoras en scrollbars)
echo.
set /p NOVEDADES="Novedades: "
if "%NOVEDADES%"=="" set NOVEDADES=Mejoras y correcciones generales.

echo.
echo  [*] Actualizando version a v%VERSION%...

:: Actualizar version en updater.py
powershell -Command "(Get-Content updater.py) -replace 'VERSION_ACTUAL = \".*\"', 'VERSION_ACTUAL = \"%VERSION%\"' | Set-Content updater.py"

:: Actualizar version en main.py
powershell -Command "(Get-Content main.py) -replace 'QLabel\(\"v[0-9]+\.[0-9]+\.[0-9]+\"\)', 'QLabel(\"v%VERSION%\")' | Set-Content main.py"
powershell -Command "(Get-Content main.py) -replace 'DentalApp v[0-9]+\.[0-9]+\.[0-9]+', 'DentalApp v%VERSION%' | Set-Content main.py"

:: Actualizar version en installer.iss
powershell -Command "(Get-Content installer.iss) -replace '#define AppVersion\s+"".*""', '#define AppVersion   ""%VERSION%""' | Set-Content installer.iss"

:: Guardar novedades en archivo temporal para el release
echo %NOVEDADES% > RELEASE_NOTES.txt

echo  [OK] Archivos actualizados.
echo.

:: Git commit y push
echo  [*] Subiendo cambios a GitHub...
git add updater.py main.py installer.iss RELEASE_NOTES.txt
git commit -m "Release v%VERSION% - %NOVEDADES%"
git push origin main

:: Crear tag con mensaje de novedades
echo  [*] Creando tag v%VERSION%...
git tag -a v%VERSION% -m "%NOVEDADES%"
git push origin v%VERSION%

echo.
echo  ==========================================
echo   OK  Release v%VERSION% en proceso!
echo   Novedades: %NOVEDADES%
echo.
echo   GitHub Actions compilara Windows + Mac
echo   en ~2 minutos.
echo.
echo   Cuando termine descarga de:
echo   github.com/gaelorte22-dotcom/dental_app/releases
echo  ==========================================
echo.
pause
