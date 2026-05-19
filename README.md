# BullySpeechDetection

Lightweight source repository for the BullyDetector desktop app.

## What's Included

- Python desktop UI built with `tkinter`
- Microphone scan and live preview flow
- Speech-to-text and bully speech detection app code

## What's Not Included In Git

The following large local runtime assets are intentionally excluded from GitHub:

- Whisper model files under `models/`
- `models/toxic-bert.onnx`
- Bundled `ffmpeg` executables in the project root
- Portable SQLite Browser under `SQL/SQLiteDatabaseBrowserPortable/`

Keep those files locally after cloning, or download/setup them again on your machine before running the app.

## Setup

1. Create and activate your Python or Conda environment.
2. Install dependencies with `setup.bat` or `python -m pip install -r requirements.txt`.
3. Restore the required model files and local binaries.
4. Run `python main.py`.

## Dependency Repair

If Whisper fails with `No module named 'tiktoken'` or NumPy/Torch compatibility errors, repair the environment with:

```bash
python -m pip install numpy==1.26.4
python -m pip install torch==2.2.2 torchvision==0.17.2 torchaudio==2.2.2 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
```
