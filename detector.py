"""
detector.py — uses openai-whisper only (stable, no crashes).
faster-whisper removed — it crashes on some Windows setups.
"""

import os
import re
import threading
import numpy as np

from config import (
    BERT_PATH, VOCAB_PATH,
    WHISPER_MODEL, BERT_THRESHOLD,
    BASE_DIR,
)

LABELS = ["toxic", "severe_toxic", "obscene", "threat", "insult", "identity_hate"]

BULLY_WORDS = {
    "kill","murder","hurt","beat","punch","hit","attack","destroy","threaten",
    "stab","shoot","die","death","bomb","harm","idiot","stupid","dumb","moron",
    "loser","ugly","fat","freak","worthless","useless","pathetic","disgusting",
    "trash","garbage","retard","coward","lame","filthy","nasty","bitch",
    "bastard","asshole","fuck","shit","crap","damn","whore","slut","pig",
    "rat","scum","jerk","cunt",
}
BULLY_PHRASES = [
    "shut up","go away","nobody likes","everyone hates","you suck",
    "kill yourself","no one cares","i hate you","get lost",
    "you're worthless","you're nothing","go die",
]

_whisper_model = None
_onnx_session  = None
_vocab         = None
_model_lock    = threading.Lock()
_whisper_lock  = threading.Lock()   # one transcription at a time
_whisper_load_error = None


def preload_models():
    """Call once at startup in a background thread."""
    _ensure_ffmpeg()
    _load_whisper()
    _load_bert()
    print("[Models] All models ready")


def transcribe(audio_path: str) -> str:
    _ensure_ffmpeg()
    if not _validate_audio(audio_path):
        return ""
    model = _load_whisper()
    if model is None:
        return ""
    with _whisper_lock:
        try:
            result = model.transcribe(audio_path, fp16=False, task="transcribe")
            text   = result.get("text", "").strip()
            print(f"[Whisper] OK: '{text[:80]}'")
            return text
        except Exception as e:
            print(f"[Whisper] Error: {e}")
            return ""


def _validate_audio(path):
    if not os.path.exists(path):
        return False
    try:
        import wave as _wave
        with _wave.open(path, "rb") as wf:
            frames = wf.getnframes()
            rate   = wf.getframerate()
            dur    = frames / rate if rate > 0 else 0
        if dur < 0.5:
            print(f"[Whisper] Too short ({dur:.1f}s) — skip")
            return False
        print(f"[Whisper] Audio {dur:.1f}s OK")
        return True
    except Exception as e:
        print(f"[Whisper] Validate error: {e}")
        return False


def _load_whisper():
    global _whisper_model, _whisper_load_error
    if _whisper_model is not None:
        return _whisper_model
    if _whisper_load_error is not None:
        return None
    with _model_lock:
        if _whisper_model is None:
            try:
                import whisper
                print(f"[Whisper] Loading '{WHISPER_MODEL}' model...")
                _whisper_model = whisper.load_model(WHISPER_MODEL)
                print(f"[Whisper] Ready")
            except Exception as e:
                message = str(e)
                if "No module named 'tiktoken'" in message:
                    message = (
                        "Missing Whisper dependency 'tiktoken'. Install it in the app environment, "
                        "for example: pip install tiktoken==0.7.0"
                    )
                if "Numpy is not available" in message or "Failed to initialize NumPy" in message:
                    message = (
                        "NumPy is not available. Install a NumPy 1.x build for the app environment, "
                        "for example: pip install numpy==1.26.4"
                    )
                _whisper_load_error = message
                print(f"[Whisper] Load failed: {_whisper_load_error}")
    return _whisper_model


def _ensure_ffmpeg():
    import shutil
    if shutil.which("ffmpeg"):
        return
    for p in [r"C:\Users\anaconda3\Library\bin",
               os.path.join(BASE_DIR), r"C:\ffmpeg\bin"]:
        if os.path.isdir(p) and p not in os.environ.get("PATH",""):
            os.environ["PATH"] = p + ";" + os.environ.get("PATH","")
            return


def is_toxic(text: str) -> tuple[bool, dict]:
    scores   = {l: 0.0 for l in LABELS}
    kw_hit   = _keyword_check(text)
    bert_hit = False
    if os.path.exists(BERT_PATH) and os.path.exists(VOCAB_PATH):
        bert_hit, scores = _bert_check(text)
    detected = bert_hit or kw_hit
    print(f"[Detection] BERT={bert_hit} KW={kw_hit} -> {'YES' if detected else 'NO'}")
    return detected, scores


def _keyword_check(text: str) -> bool:
    lower = text.lower()
    if any(p in lower for p in BULLY_PHRASES):
        return True
    return bool(set(re.split(r"\W+", lower)) & BULLY_WORDS)


def _bert_check(text: str) -> tuple[bool, dict]:
    scores = {l: 0.0 for l in LABELS}
    session, vocab = _load_bert()
    if session is None:
        return False, scores
    try:
        ids, mask, tids = _tokenize(text, vocab)
        logits = session.run(None, {
            "input_ids": ids, "attention_mask": mask,
            "token_type_ids": tids})[0][0]
        probs  = 1.0 / (1.0 + np.exp(-logits))
        scores = {l: round(float(p), 4) for l,p in zip(LABELS, probs)}
        print(f"[BERT] {scores}")
        return any(p > BERT_THRESHOLD for p in probs), scores
    except Exception as e:
        print(f"[BERT] Error: {e}")
        return False, scores


def _load_bert():
    global _onnx_session, _vocab
    if _onnx_session is not None:
        return _onnx_session, _vocab
    with _model_lock:
        if _onnx_session is None:
            try:
                from onnxruntime import InferenceSession
                print("[BERT] Loading...")
                _onnx_session = InferenceSession(BERT_PATH)
                _vocab = {}
                with open(VOCAB_PATH, encoding="utf-8") as f:
                    for i, line in enumerate(f):
                        _vocab[line.strip()] = i
                print("[BERT] Ready")
            except Exception as e:
                print(f"[BERT] Load error: {e}")
                return None, None
    return _onnx_session, _vocab


def _tokenize(text, vocab, max_len=128):
    CLS, SEP, UNK, PAD = 101, 102, 100, 0
    tokens = []
    for word in re.split(r"(\s+|(?<=[^\w'])|(?=[^\w']))", text.lower()):
        word = word.strip()
        if not word: continue
        if word in vocab:
            tokens.append(vocab[word]); continue
        start = 0; sub = []
        while start < len(word):
            end = len(word); found = None
            while start < end:
                s = ("" if start==0 else "##") + word[start:end]
                if s in vocab: found = vocab[s]; break
                end -= 1
            if found is None: sub = [UNK]; break
            sub.append(found); start = end
        tokens.extend(sub)
    tokens = tokens[:max_len-2]
    ids  = [PAD]*max_len; mask = [0]*max_len; tids = [0]*max_len
    ids[0] = CLS; mask[0] = 1
    for i,t in enumerate(tokens,1): ids[i]=t; mask[i]=1
    sep = len(tokens)+1
    if sep < max_len: ids[sep]=SEP; mask[sep]=1
    return (np.array([ids], dtype=np.int64),
            np.array([mask], dtype=np.int64),
            np.array([tids], dtype=np.int64))
