"""Piper TTS (en_US-lessac-medium) on CPU, returning WAV bytes."""
import io
import wave

from huggingface_hub import hf_hub_download


class Tts:
    def __init__(self, repo, voice):
        from piper import PiperVoice
        path = hf_hub_download(repo, voice)
        hf_hub_download(repo, voice + ".json")
        self.voice = PiperVoice.load(path)

    def wav_bytes(self, text):
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            self.voice.synthesize_wav(text, w)
        return buf.getvalue()
