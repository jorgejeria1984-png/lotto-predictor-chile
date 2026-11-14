@echo off
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 chile\launcher.py
  goto :done
)
where python >nul 2>nul
if not errorlevel 1 (
  python chile\launcher.py
  goto :done
)
echo Python 3.10 o superior no encontrado. Instale Python o use el ZIP Windows compilado.
:done
pause
