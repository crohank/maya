"""One entry point for every item kind: Engine().answer(modality, path, question).

Each modality lives in its own module so it can be improved and scored on its
own (scripts/eval_pack.py). Options arrive as strings from --opt key=value.

The GPU holds one large model at a time (8 GB card, about 2 GB taken by the
display). `eng.vlm` loads Qwen3-VL on first use; a handler that needs a
different model calls `eng.gpu_model(name, loader)`, which frees whatever else
is loaded first.
"""
import gc

from . import audio, code, docqa, image, video

HANDLERS = {"image": image.answer, "video": video.answer, "text": docqa.answer,
            "code": code.answer, "audio": audio.answer}


class Engine:
    def __init__(self, **opts):
        self.opts = opts
        self.cache = {}          # CPU-side models and per-file results
        self._gpu = {}           # name -> loaded GPU model (at most one)

    def gpu_model(self, name, loader):
        if name not in self._gpu:
            self._gpu.clear()
            gc.collect()
            import torch
            torch.cuda.empty_cache()
            self._gpu[name] = loader()
        return self._gpu[name]

    @property
    def vlm(self):
        from .vlm import Vlm
        return self.gpu_model("vlm", Vlm)

    def warm(self):
        """Load and run every model once so the first live item is not the slow one.

        Measured cold first items: audio about 8 s extra (AST 4.2 s, whisper 2.5 s
        loads), image 4.8 s vs 0.6 s warm. Returns seconds per part.
        """
        import time

        import numpy as np
        from PIL import Image
        out = {}
        t = time.perf_counter()
        self.vlm.chat([{"type": "image", "image": Image.new("RGB", (64, 64))},
                       {"type": "text", "text": "Hi"}], max_new_tokens=2)
        out["vlm"] = round(time.perf_counter() - t, 2)
        t = time.perf_counter()
        from . import sound
        silence = np.zeros(16000, dtype=np.float32)
        audio.whisper(self).transcribe(silence, language="en", beam_size=1)
        sound.ast_model(self)
        if self.opts.get("sound", "clap") == "clap":
            sound.clap_model(self)
        out["audio"] = round(time.perf_counter() - t, 2)
        return out

    def answer(self, modality, path, question):
        return HANDLERS[modality](self, path, question or "")
