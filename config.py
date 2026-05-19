"""
BullyDetector Configuration — edit this file to tune behaviour.
"""

import os

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR      = os.path.join(BASE_DIR, "models")
DB_DIR         = os.path.join(BASE_DIR, "db")
DB_PATH        = os.path.join(DB_DIR,   "bully.db")
BERT_PATH      = os.path.join(MODEL_DIR, "toxic-bert.onnx")
VOCAB_PATH     = os.path.join(MODEL_DIR, "vocab.txt")

# ── Whisper ───────────────────────────────────────────────────────────────────
# "tiny"   = fastest (~1s/clip),  least accurate
# "base"   = fast   (~2s/clip),  decent English
# "small"  = medium (~3s/clip),  good multilingual ← recommended
# "medium" = slow   (~6s/clip),  best multilingual
WHISPER_MODEL = "base"    # base = fast, already downloaded, no crashes

# ── Continuous Recording ──────────────────────────────────────────────────────
# Records non-stop in fixed chunks — no silence detection, always listening
CHUNK_SECONDS = 30   # process every N seconds (15=faster, 30=more context, 60=max)

# ── Detection ─────────────────────────────────────────────────────────────────
BERT_THRESHOLD = 0.3       # BERT confidence threshold (0.0–1.0)

# ── Recordings ────────────────────────────────────────────────────────────────
SAVE_RECORDINGS = True     # Save audio files when bullying detected
SAVE_ALL        = False    # True = save all clips, False = YES only
RECORDINGS_DIR  = os.path.join(BASE_DIR, "recordings")

# ── Telegram ──────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN   = "YOUR_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID_HERE"

# ── UI ────────────────────────────────────────────────────────────────────────
WINDOW_TITLE  = "BullyDetector — Speech Detection System"
WINDOW_WIDTH  = 1300
WINDOW_HEIGHT = 860