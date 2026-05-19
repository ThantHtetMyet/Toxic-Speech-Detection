@echo off
echo ============================================
echo  BullyDetector - Fresh Setup Script
echo ============================================
echo.

echo [1/5] Checking Python...
python --version
if errorlevel 1 (
    echo ERROR: Python not found. Install from https://www.python.org
    pause
    exit /b 1
)

echo.
echo [2/5] Upgrading pip...
python -m pip install --upgrade pip

echo.
echo [3/5] Installing PyTorch CPU only...
python -m pip install torch==2.2.2 torchvision==0.17.2 torchaudio==2.2.2 --index-url https://download.pytorch.org/whl/cpu

echo.
echo [4/5] Installing all other packages...
python -m pip install -r requirements.txt

echo.
echo [5/5] Verifying installation...
python -c "import tkinter, whisper, sounddevice, onnxruntime, numpy, scipy, requests, tiktoken; print('ALL OK - Ready to run!')"

echo.
echo ============================================
echo  Setup complete! Run: python main.py
echo ============================================
pause
