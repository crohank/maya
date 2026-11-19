"""Audio items: speech (transcribe or answer about it) and non-speech sounds.

Routing looks at the audio, not the question wording: AST's speech score and
Whisper's own confidence decide whether there is speech. Speech goes to the
transcript (and the VLM for questions about it); everything else goes to
`sound.identify`. All audio models run on the CPU so the GPU stays with the VLM.
"""
import re

import numpy as np

from . import sound

SR = 16000
SYSTEM = ("You answer a question about an audio recording. You get its transcript and the "
          "sounds detected in it. Answer in one short sentence that starts with the answer. "
          "Copy names exactly as they are spelled in the transcript. If the recording does "
          "not contain the answer, say so.")

# AST speech-class max on the practice pack: speech items 0.56 to 0.87, sound items 0.20 at most
# (chainsaw). Whisper mean log prob on speech items: -0.12 to -0.36.
SPEECH_SKIP = 0.05      # below this no Whisper run: without VAD it looped 15 to 19 s on noise clips
SPEECH_AST = 0.5
SPEECH_LOGPROB = -0.6
SPEECH_MIN_WORDS = 3
TRANSCRIBE = re.compile(r"\btranscri|\bverbatim|word for word|exact words|write (down|out) what|"
                        r"what (exactly )?(is|was) (being )?said|what (does|did) (he|she|they|the \w+|it|someone) say|"
                        r"what (is|are|was|were) (he|she|they|the \w+|someone|somebody) saying", re.I)
DESCRIBE = re.compile(r"what (kind of |type of )?(sound|noise)|which (sound|noise)|what('s| is) (that|this) (sound|noise)|"
                      r"(can|do) (you|i) hear( anything| in| on|\s*\?|\s*$)|what you hear|what('s| is| was) (happening|going on)|identify|"
                      r"describe (the|this) (audio|recording|sound|clip)|what (this|that) is\b|"
                      r"what('s| is) (this|that|in this)( audio| recording| clip)?\??$|what('s| is) making", re.I)


def spoken(text):
    # The app font has no dash glyph, and the VLM sometimes writes em dashes.
    text = re.sub(r"(\d)\s*[–—]\s*(\d)", r"\1 to \2", text)
    return re.sub(r"\s*[–—]\s*", ", ", text).strip()


def load(path):
    from faster_whisper import decode_audio
    return decode_audio(path, sampling_rate=SR)


def whisper(eng):
    if "whisper" not in eng.cache:
        from faster_whisper import WhisperModel
        eng.cache["whisper"] = WhisperModel(eng.opts.get("whisper", "small.en"), device="cpu",
                                            compute_type="int8", cpu_threads=int(eng.opts.get("whisper_threads", 8)))
    return eng.cache["whisper"]


def transcribe(eng, wav):
    """Returns (text, confidence stats). Segments Whisper itself marks as non-speech are dropped."""
    segs, info = whisper(eng).transcribe(
        wav, language="en", beam_size=int(eng.opts.get("beam", 5)), vad_filter=eng.opts.get("vad", "1") == "1",
        condition_on_previous_text=False)
    kept = [s for s in segs if not (s.no_speech_prob > 0.6 and s.avg_logprob < -1.0)]
    text = " ".join(s.text.strip() for s in kept).strip()
    return text, {"speech_s": round(sum(s.end - s.start for s in kept), 2),
                  "avg_logprob": round(float(np.mean([s.avg_logprob for s in kept])), 3) if kept else None,
                  "no_speech": round(float(max([s.no_speech_prob for s in kept], default=1.0)), 3)}


def is_speech(ast_speech, text, st):
    words = len(re.findall(r"[a-z']+", text.lower()))
    if not st or words == 0:
        return False
    if ast_speech >= SPEECH_AST:
        return True
    # Whisper alone: VAD-filtered noise still yields "Thank you." or "Oh" at times, hence the word floor.
    return (words >= SPEECH_MIN_WORDS and st["avg_logprob"] is not None
            and st["avg_logprob"] > SPEECH_LOGPROB and st["no_speech"] < 0.5)


def speaker(agg, names):
    m, f = agg[names.index("Male speech, man speaking")], agg[names.index("Female speech, woman speaking")]
    if m > 0.5 and f < 0.2:
        return "A man is speaking"
    if f > 0.5 and m < 0.2:
        return "A woman is speaking"
    return "Someone is speaking"


def answer(eng, path, question):
    wav = load(path)
    q = question.strip()
    names = sound.ast_model(eng)[2]
    speech_idx = [names.index(n) for n in sound.SPEECHY]
    wants_text = bool(TRANSCRIBE.search(q))
    # The first AST window is enough to route speech; the sound route needs every window.
    probs, starts = sound.ast_probs(eng, wav[:sound.AST_WIN])
    full = len(wav) <= sound.AST_WIN
    ast_speech = float(probs[0][speech_idx].max())
    if ast_speech < SPEECH_SKIP and not full:
        probs, starts = sound.ast_probs(eng, wav)
        full = True
        ast_speech = float(probs[:, speech_idx].max())
    text, st = "", None
    if ast_speech >= SPEECH_SKIP or wants_text:
        text, st = transcribe(eng, wav)
    speech = is_speech(ast_speech, text, st)
    info = {"ast_speech": round(ast_speech, 3), "stt": st, "speech": speech}
    agg = probs.max(0)

    if speech:
        if wants_text:
            return text, {**info, "route": "audio_transcribe"}
        bg = sound.background(eng, agg)
        if DESCRIBE.search(q) or not q:
            out = f"{speaker(agg, names)}. They say: \"{text}\""
            if bg:
                out += f" In the background I also hear {bg}."
            return out, {**info, "route": "audio_speech_describe"}
        ctx = f"Transcript: {text}\n"
        if bg:
            ctx += f"Background sounds: {bg}\n"
        out, vinfo = eng.vlm.text(f"{ctx}\nQuestion: {q}", SYSTEM, max_new_tokens=64)
        return spoken(out), {**info, **vinfo, "route": "audio_qa"}

    if not full:
        probs, starts = sound.ast_probs(eng, wav)
    desc, sinfo = sound.identify(eng, wav, probs, starts)
    if wants_text:
        return f"I do not hear any speech in this recording. {desc}", {**info, **sinfo, "route": "audio_transcribe_nospeech"}
    if DESCRIBE.search(q) or not q:
        return desc, {**info, **sinfo, "route": "audio_sound"}
    ctx = f"No speech. Sounds detected (best first): {sinfo['detected']}\nSummary: {desc}\n"
    out, vinfo = eng.vlm.text(f"{ctx}\nQuestion: {q}", SYSTEM, max_new_tokens=64)
    return spoken(out), {**info, **sinfo, **vinfo, "route": "audio_sound_qa"}
