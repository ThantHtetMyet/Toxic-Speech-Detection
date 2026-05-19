"""
Simple continuous recorder - records fixed chunks, puts in queue.
"""
import os, wave, tempfile, threading, queue, time
import re
from math import gcd
import numpy as np
import sounddevice as sd
from scipy.signal import resample_poly

TARGET_RATE = 16000
DTYPE = "float32"


def _normalize_device_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"\s+", " ", name)
    noise_tokens = [
        "microsoft sound mapper - input",
        "primary sound capture driver",
        "directsound",
        "mme",
        "wasapi",
        "wdm-ks",
        "windows ",
        "(r)",
        "(tm)",
        "sst",
        "()",
    ]
    for token in noise_tokens:
        name = name.replace(token, " ")
    name = re.sub(r"[^a-z0-9 ]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _device_priority(name: str, is_default: bool, hostapi_name: str) -> tuple:
    lowered = name.lower()
    score = 0
    if is_default:
        score += 100
    if "wasapi" in hostapi_name.lower():
        score += 30
    elif "wdm-ks" in hostapi_name.lower():
        score += 20
    elif "directsound" in hostapi_name.lower():
        score += 10

    preferred_tokens = [
        "microphone",
        "mic",
        "array",
        "headset",
        "headphone",
        "earphone",
        "webcam",
        "usb",
        "input",
    ]
    if any(token in lowered for token in preferred_tokens):
        score += 25

    unwanted_tokens = [
        "stereo mix",
        "speaker",
        "output",
        "loopback",
        "mapper",
        "capture driver",
    ]
    if any(token in lowered for token in unwanted_tokens):
        score -= 40

    return score, -len(lowered)


def _group_key(normalized: str) -> str:
    if "microphone array" in normalized:
        normalized = re.sub(r"\s+\d+$", "", normalized)
    return normalized


def _candidate_rates(default_rate: int) -> list[int]:
    rates = []
    for rate in [default_rate, 48000, 44100, 16000]:
        if rate and rate > 0 and rate not in rates:
            rates.append(int(rate))
    return rates


def _can_open_stream(device_id: int, rate: int, channels: int) -> bool:
    try:
        stream = sd.InputStream(
            device=device_id,
            samplerate=rate,
            channels=channels,
            dtype=DTYPE,
            blocksize=max(256, int(rate * 0.05)),
            callback=lambda indata, frames, t, status: None,
        )
        stream.start()
        stream.stop()
        stream.close()
        return True
    except Exception:
        return False


def _pick_openable_rate(device_id: int, max_input_channels: int, default_rate: int) -> int | None:
    channels = 1
    for rate in _candidate_rates(default_rate):
        try:
            sd.check_input_settings(
                device=device_id,
                samplerate=rate,
                channels=channels,
                dtype=DTYPE,
            )
            if _can_open_stream(device_id, rate, channels):
                return rate
        except Exception:
            continue
    return None


def get_devices():
    all_devs = sd.query_devices()
    hostapis = sd.query_hostapis()
    default_input = None
    try:
        default_input = sd.default.device[0]
    except Exception:
        default_input = None

    grouped = {}
    for i, d in enumerate(all_devs):
        if d["max_input_channels"] <= 0:
            continue

        hostapi_idx = d["hostapi"]
        hostapi_name = hostapis[hostapi_idx]["name"] if 0 <= hostapi_idx < len(hostapis) else ""
        name = d["name"]
        normalized = _normalize_device_name(name)
        if not normalized:
            continue
        usable_rate = _pick_openable_rate(i, int(d["max_input_channels"]), int(d["default_samplerate"]))
        if usable_rate is None:
            continue

        is_default = i == default_input
        priority = _device_priority(name, is_default, hostapi_name)
        device_info = {
            "id": i,
            "name": name,
            "channels": d["max_input_channels"],
            "rate": usable_rate,
            "hostapi": d["hostapi"],
            "_normalized": _group_key(normalized),
            "_priority": priority,
            "_is_default": is_default,
        }

        group_key = device_info["_normalized"]
        existing = grouped.get(group_key)
        if existing is None or priority > existing["_priority"]:
            grouped[group_key] = device_info

    filtered = list(grouped.values())

    visible = []
    for dev in filtered:
        lowered = dev["name"].lower()
        if any(token in lowered for token in ["stereo mix", "speaker", "output", "loopback"]):
            if not dev["_is_default"]:
                continue
        visible.append(dev)

    visible.sort(key=lambda d: (not d["_is_default"], -d["_priority"][0], d["name"].lower()))
    return [
        {
            "id": d["id"],
            "name": d["name"],
            "channels": d["channels"],
            "rate": d["rate"],
            "hostapi": d["hostapi"],
        }
        for d in visible
    ]


def open_stream(device_id, callback):
    """Open only the selected device and try safe sample-rate fallbacks."""
    try:
        dev = sd.query_devices(device_id)
    except Exception as e:
        print(f"[Recorder] Device {device_id} is not available: {e}")
        return None, TARGET_RATE

    if int(dev.get("max_input_channels", 0)) < 1:
        print(f"[Recorder] Device {device_id} has no input channels")
        return None, TARGET_RATE

    rate = int(dev["default_samplerate"])
    ch_d = 1
    candidates = [(device_id, r) for r in _candidate_rates(rate)]

    seen = set()
    for dev_id, r in candidates:
        key = (dev_id, r)
        if key in seen:
            continue
        seen.add(key)
        try:
            sd.check_input_settings(
                device=dev_id,
                samplerate=r,
                channels=ch_d,
                dtype=DTYPE,
            )
            d = sd.query_devices(dev_id)
            s    = sd.InputStream(device=dev_id, samplerate=r,
                                  channels=ch_d, dtype=DTYPE,
                                  blocksize=int(r*0.1), callback=callback)
            s.start()
            print(f"[Recorder] Opened device {dev_id} '{d['name']}' @ {r}Hz")
            return s, r
        except Exception as e:
            print(f"[Recorder] device {dev_id} @ {r}Hz failed: {e}")
            continue

    return None, rate


class LevelPreview:
    def __init__(self, device_id, on_level):
        self.device_id = device_id
        self.on_level = on_level
        self.stop_event = threading.Event()
        self._thread = None
        self.running = False

    def start(self):
        if self.running:
            return
        self.running = True
        self.stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop_now(self):
        self.stop_event.set()
        self.running = False

    def is_alive(self):
        return self._thread is not None and self._thread.is_alive()

    def _run(self):
        last_emit = 0.0

        def cb(indata, frames, t, status):
            del frames, t, status
            nonlocal last_emit
            chunk = indata[:, 0].copy() if indata.ndim > 1 else indata.flatten().copy()
            now = time.time()
            if now - last_emit < 0.05:
                return
            last_emit = now
            level = float(np.abs(chunk).mean()) if len(chunk) else 0.0
            try:
                self.on_level(level)
            except Exception:
                pass

        stream, _ = open_stream(self.device_id, cb)
        if stream is None:
            try:
                self.on_level(0.0)
            except Exception:
                pass
            self.running = False
            return

        with stream:
            while not self.stop_event.wait(0.1):
                pass

        try:
            self.on_level(0.0)
        except Exception:
            pass
        self.running = False


class ContinuousRecorder:
    def __init__(self, device_id, stop_event, result_queue,
                 on_level=None, chunk_seconds=15):
        self.device_id     = device_id
        self.stop_event    = stop_event
        self.result_queue  = result_queue
        self.on_level      = on_level
        self.chunk_seconds = chunk_seconds
        self._buf          = []
        self._lock         = threading.Lock()
        self._rate         = TARGET_RATE

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        def cb(indata, frames, t, status):
            chunk = indata[:,0].copy() if indata.ndim>1 else indata.flatten().copy()
            with self._lock:
                self._buf.append(chunk)
            if self.on_level:
                try: self.on_level(float(np.abs(chunk).mean()))
                except: pass

        stream, native_rate = open_stream(self.device_id, cb)
        if stream is None:
            print(f"[Recorder] Could not open any stream for device {self.device_id}")
            self.result_queue.put(None)
            return

        self._rate = native_rate
        chunk_num  = 0

        with stream:
            print(f"[Recorder] Recording — chunk every {self.chunk_seconds}s")
            while not self.stop_event.is_set():
                # Simple sleep-based chunking
                elapsed = 0.0
                interval = 0.5
                while elapsed < self.chunk_seconds:
                    if self.stop_event.is_set():
                        break
                    self.stop_event.wait(interval)
                    elapsed += interval

                if self.stop_event.is_set():
                    break

                with self._lock:
                    frames = self._buf.copy()
                    self._buf.clear()

                if not frames:
                    continue

                path = self._save(frames)
                if path:
                    chunk_num += 1
                    print(f"[Recorder] Chunk #{chunk_num} ready")
                    self.result_queue.put(path)

        # Save remainder
        with self._lock:
            frames = self._buf.copy()
        if frames:
            path = self._save(frames)
            if path:
                self.result_queue.put(path)

        self.result_queue.put(None)
        print(f"[Recorder] Stopped after {chunk_num} chunks")

    def _save(self, frames):
        try:
            audio = np.concatenate(frames)
            if len(audio) < self._rate:
                return None
            if self._rate != TARGET_RATE:
                g = gcd(TARGET_RATE, self._rate)
                audio = resample_poly(audio, TARGET_RATE//g, self._rate//g)
            peak = np.abs(audio).max()
            if peak > 0:
                audio = audio / peak * 0.95
            i16 = (audio * 32767).astype(np.int16)
            fd, path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            with wave.open(path, "wb") as wf:
                wf.setnchannels(1); wf.setsampwidth(2)
                wf.setframerate(TARGET_RATE)
                wf.writeframes(i16.tobytes())
            print(f"[Recorder] Saved {len(i16)/TARGET_RATE:.1f}s")
            return path
        except Exception as e:
            print(f"[Recorder] Save error: {e}")
            return None


def record_vad(device_id, stop_event, on_level=None):
    q = queue.Queue()
    r = ContinuousRecorder(device_id, stop_event, q, on_level, 15)
    r.start()
    return q.get()
