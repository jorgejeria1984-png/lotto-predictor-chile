@echo off
cd /d "%~dp0"
title Lotto Predictor Chile 3.1 - LSTM
where py >nul 2>nul
if not errorlevel 1 (
  py -c "import torch; print('PyTorch CPU:', torch.__version__); print(torch.zeros(1))"
  py chile\launcher.py
  goto :done
)
where python >nul 2>nul
if not errorlevel 1 (
  python -c "import torch; print('PyTorch CPU:', torch.__version__); print(torch.zeros(1))"
  python chile\launcher.py
  goto :done
)
echo Python no encontrado. Instale Python 3.10 o superior.
:done
pause
