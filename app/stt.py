"""Speech in: faster-whisper on CPU int8, so the GPU stays with the vision models."""


class Stt:
    def __init__(self, size, device, compute_type, cpu_threads, language):
        from faster_whisper import WhisperModel
        self.model = WhisperModel(size, device=device, compute_type=compute_type, cpu_threads=cpu_threads)
        self.language = language

    def transcribe(self, path):
        segments, _ = self.model.transcribe(path, language=self.language, beam_size=1)
        return " ".join(s.text.strip() for s in segments).strip()
