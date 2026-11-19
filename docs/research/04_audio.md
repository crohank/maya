# 04. Audio: speech, questions about audio, non-speech sounds

Brief: "transcribe speech, answer questions about it, and identify non-speech
sounds (vehicles, sirens, horns, crosswalk signal chirps)". Practice pack has 20
audio items, format unknown.

Constraint from `docs/decisions.md`: the GPU already holds Cosmos3-Edge NF4
(2.4 GiB) and Qwen3-VL-4B NF4 (3.6 GiB peak) for vision. Audio should run on the
CPU (Ryzen 9 8940HX, 16 cores, 31 GB RAM) so it never competes for VRAM.

Nothing in this file was run on this machine. Numbers marked UNVERIFIED are
estimates or from memory and need one timing run before they go in a slide.

## Recommendation (short)

| Job | Model | Exact ID | License | Device | Expected latency | VRAM |
|---|---|---|---|---|---|---|
| Speech to text | Whisper small.en, CTranslate2 | `Systran/faster-whisper-small.en` (load as `"small.en"`) | MIT (conversion), weights from `openai/whisper-small` Apache-2.0 | CPU int8 | about 1.5 s per 10 s of speech (RTF about 0.13, see 1.3) | 0 |
| Accuracy fallback STT | distil-large-v3, CTranslate2 | `Systran/faster-distil-whisper-large-v3` | MIT | CPU int8 | about 3 to 5 s per 10 s (UNVERIFIED) | 0 |
| Sound ID | AST, AudioSet fine-tuned | `MIT/ast-finetuned-audioset-10-10-0.4593` | BSD-3-Clause | CPU fp32 | about 0.3 to 0.8 s per 10.24 s window (UNVERIFIED) | 0 |
| Open-label sound ID | CLAP | `laion/clap-htsat-unfused` | Apache-2.0 | CPU | about 0.2 to 0.5 s per clip (UNVERIFIED) | 0 |
| Crosswalk signal | rule: tick-rate detector on onsets (section 2.4) | none | own code | CPU | under 50 ms | 0 |
| Answering questions | pipeline: transcript + timed sound labels + the LLM already loaded (Qwen3-VL-4B text-only) | none new | | GPU (already resident) | about 1 s (D5 latency class) | 0 extra |

No audio-language model fits the budget with a license and quality worth the
risk one day before the deadline (section 3).

## 1. Speech to text

### 1.1 Candidates (primary sources)

| Model | Params | License | LibriSpeech clean / other WER | Notes |
|---|---|---|---|---|
| `openai/whisper-small` | 244 M | Apache-2.0 | 3.43 / 7.63 (card, self-reported) | `.en` variant exists, also 244 M |
| `openai/whisper-medium` | 769 M | Apache-2.0 | 2.90 / 5.90 (card) | |
| `distil-whisper/distil-large-v3` | 756 M | MIT | short-form 9.7 vs large-v3 8.4, long-form seq 10.8 vs 10.0 (card, mean over OOD sets) | "6.3x faster than large-v3" (card), English only |
| `openai/whisper-large-v3-turbo` | 809 M | MIT | Open ASR leaderboard mean WER 7.83, AMI 16.13, RTFx 200 on GPU (card) | decoder cut from 32 to 4 layers; encoder is full large-v3 |

CTranslate2 builds for faster-whisper: `Systran/faster-whisper-small`,
`Systran/faster-whisper-small.en`, `Systran/faster-whisper-medium`,
`Systran/faster-distil-whisper-large-v3` (all MIT, stored FP16, requantized at
load time via `compute_type`). Turbo: faster-whisper accepts `"large-v3-turbo"`
or `"turbo"` as a size name (UNVERIFIED which HF repo it maps to in the installed
version; check `faster_whisper.utils._MODELS`).

### 1.2 faster-whisper's own benchmark (13 min clip, github.com/SYSTRAN/faster-whisper)

CPU, Whisper small, Intel i7-12700K, 8 threads, beam 5:

| Precision | Time | RAM |
|---|---|---|
| fp32 | 2m37s | 2257 MB |
| int8 | 1m42s | 1477 MB |
| int8, `batch_size=8` | 51s | 3608 MB |

GPU, large-v2, RTX 3070 Ti 8 GB, beam 5: fp16 1m03s at 4525 MB; int8 59s at
2926 MB; int8 `batch_size=8` 16s at 4500 MB.

### 1.3 What that means on this laptop

- small int8 on CPU: 102 s / 780 s = RTF 0.13 on 8 threads of a 12700K. The
  8940HX (Zen 4, 16 cores) should be similar or a little faster: a 10 s utterance
  in about 1 to 1.5 s with beam 5, under 1 s with `beam_size=1` (UNVERIFIED on
  this CPU).
- medium int8 on CPU: about 3x the compute of small, so RTF about 0.35 to 0.45
  (UNVERIFIED).
- distil-large-v3 and large-v3-turbo on CPU: both keep the full 32-layer large
  encoder, which dominates CPU time on short clips. Expect RTF 0.3 to 0.6
  (UNVERIFIED). Turbo is multilingual; distil-large-v3 is English only.
- On GPU int8: large-v2 int8 used 2.9 GB in the table above; turbo int8 would
  be roughly 1.0 to 1.5 GB, small int8 about 0.5 to 0.8 GB (UNVERIFIED). With
  Cosmos plus Qwen3-VL resident there is no safe room, and it is not needed.

**Pick:** `small.en`, `device="cpu"`, `compute_type="int8"`. Street speech that
matters (APS voice messages, a bus announcement, a person talking) is short and
English; small is 3.43 WER on clean speech. If the practice pack shows word
errors on noisy speech, swap the name to `distil-large-v3` with no other code
change and accept about 3x the CPU time.

### 1.4 Gotchas

- Whisper invents text on non-speech audio (sirens, engines). Use
  `vad_filter=True` (Silero VAD inside faster-whisper) and drop segments with
  `no_speech_prob > 0.6` and `avg_logprob < -1.0` (attribute names are on the
  `Segment` objects; thresholds are the openai/whisper defaults, UNVERIFIED for
  faster-whisper). Also skip STT when AST's "Speech" score is low.
- `segments` is a generator; transcription only runs when iterated.
- `condition_on_previous_text=False` reduces repetition loops on short clips
  (the distil-large-v3 card uses it).

## 2. Sound identification

### 2.1 Candidates

| Model | Source | License | AudioSet mAP | Size | Loader |
|---|---|---|---|---|---|
| AST | `MIT/ast-finetuned-audioset-10-10-0.4593`, github.com/YuanGongND/ast | BSD-3-Clause | 0.459 single model (repo README; the "0.4593" in the ID) | 86.6 M params, about 350 MB fp32 | transformers `AutoModelForAudioClassification` |
| EfficientAT | github.com/fschmid56/EfficientAT | MIT | mn10_as 47.1, dymn10_as 47.7, mn04_as 43.2, mn40_as_ext 48.7 | mn10_as 4.88 M params, 0.54 GMACs | repo code only, no pip package |
| PANNs CNN14 | github.com/qiuqiangkong/audioset_tagging_cnn | MIT | 0.431 (32 kHz), 0.438 (16 kHz variant) | about 81 M params (UNVERIFIED) | `panns_inference` pip package |
| BEATs | github.com/microsoft/unilm/tree/master/beats | repo LICENSE (MIT for unilm, UNVERIFIED for this folder) | about 48 single (UNVERIFIED, only in README images) | about 90 M (UNVERIFIED) | repo code, `torch.load` |
| CLAP | `laion/clap-htsat-unfused` | Apache-2.0 | zero-shot, not an AudioSet tagger | about 150 M (UNVERIFIED) | transformers `zero-shot-audio-classification` pipeline, `candidate_labels=` |

**Pick:** AST. Already in transformers (same stack as the Docker image, no new
repo code), BSD license, 527 AudioSet classes, and its 768-d pooled embedding is
a good base for the small fine-tune in 2.5. EfficientAT mn10_as is 18x smaller
with higher mAP and would be faster on CPU, but needs its repo code vendored;
use it only if AST latency on the CPU turns out too slow.

AST input is fixed at 1024 frames = 10.24 s at 16 kHz (README). Shorter audio is
padded, so a 2 s window costs the same as a 10 s window. Use 10 s windows with
5 s hop for timing ("siren from 3 s to 12 s").

AudioSet is multi-label: apply `sigmoid` to the logits. The transformers
`audio-classification` pipeline applies softmax by default (UNVERIFIED for the
installed version), which squashes co-occurring sounds; call the model directly.

### 2.2 AudioSet classes for the brief (from `class_labels_indices.csv` in the AST repo; index = AST output index)

| Brief term | Index, display name |
|---|---|
| sirens | 396 Siren, 397 Civil defense siren, 322 Emergency vehicle, 323 Police car (siren), 324 Ambulance (siren), 325 Fire engine, fire truck (siren) |
| horns | 308 Vehicle horn, car horn, honking; 318 Air horn, truck horn; 331 Train horn |
| vehicle | 300 Vehicle, 306 Motor vehicle (road), 307 Car, 314 Car passing by, 327 Traffic noise, roadway noise, 343 Engine, 351 Engine starting |
| bus / truck / motorcycle | 321 Bus, 316 Truck, 326 Motorcycle |
| bicycle | 341 Bicycle, 203 Bicycle bell |
| danger cues | 312 Skidding, 313 Tire squeal, 319 Reversing beeps, 310 Car alarm |
| beeps and ticks | 481 Beep, bleep; 503 Chirp tone; 407 Tick; 491 Clicking; 505 Pulse; 398 Buzzer |
| trains | 329 Train, 330 Train whistle, 333 Train wheels squealing |
| speech | 0 Speech, 70 Hubbub, speech noise, speech babble |

There is **no class for accessible pedestrian signals or crosswalk beeping.** No
row contains "crosswalk" or "pedestrian". Note 113 "Chirp, tweet" is the bird
class; a chirping APS will often land there.

### 2.3 APS chirps: what the literature has

- No public APS sound dataset or APS classifier was found. Searches turned up
  ASPED (arXiv 2309.06531, pedestrian presence from audio, ICASSP 2024), ASPED
  v.b (arXiv 2509.19295, 1321 h roadside audio, DCASE 2025), and a 2025 CUNY
  thesis on crosswalk traffic direction from spatial audio for blind and low
  vision users (academicworks.cuny.edu/cc_etds_theses/1273), which notes only
  about 2% of NYC intersections have APS. None label APS tones.
- APS sound design (US MUTCD section 4E, from memory, UNVERIFIED wording): a
  pushbutton locator tone that repeats about once per second, and a walk
  indication that is either a rapid percussive tick (about 8 to 10 per second)
  or a speech message ("Walk sign is on to cross Main"). Older installs use
  cuckoo and chirp tones, often bird-like. Other countries differ (UK
  bleeper, Japan melodies, Australia rapid tick).

Consequences:
1. Speech-message APS: Whisper handles it. Match "walk sign", "wait" in the
   transcript.
2. Tick APS: AST should fire on Tick / Clicking / Beep, bleep (UNVERIFIED, no
   measurement exists). A rule on tick rate is more specific than any label:
   count onsets and read the dominant repeat rate. About 1 Hz means locator
   tone ("crosswalk button nearby"), 6 to 12 Hz sustained for over 2 s means
   walk indication. Use `librosa.onset.onset_detect` or a numpy envelope plus
   autocorrelation; under 50 ms per clip.
3. Chirp APS: CLAP zero-shot with labels such as "crosswalk signal beeping",
   "electronic chirping beeps", "bird chirping", "car horn", "siren", "traffic".
   CLAP is weak on rare, synthetic labels (UNVERIFIED for APS); treat it as a
   tie breaker, never as the only cue.
4. Maya should say "beeping that sounds like a crosswalk signal", never "it is
   safe to cross". Matches D2: describe, never decide.

### 2.4 Small fine-tune on 20 to 50 recorded clips

Realistic in under an hour on CPU if only a linear head is trained:

1. Cut each recording into 2 to 4 s windows, pad each to AST length, take the
   pooled embedding (`model.audio_spectrogram_transformer(...).pooler_output`,
   768-d; attribute path UNVERIFIED, alternatively `output_hidden_states=True`
   and mean-pool the last layer). About 0.5 s per window on CPU (UNVERIFIED), so
   300 windows take a few minutes; cache them to `.npy`.
2. Train scikit-learn `LogisticRegression(class_weight="balanced")` on the
   embeddings, classes such as `aps_tick`, `aps_chirp`, `aps_voice`, `other`.
   Training takes seconds. Append its score as one more label next to AST's 527.
3. Split by location, not by window. Windows from the same corner share traffic,
   reverb, and the same APS unit, so a random split leaks and reports near
   perfect accuracy. Use `sklearn.model_selection.GroupKFold` or
   `LeaveOneGroupOut` with `groups = location_id` (or recording session when
   one location was recorded twice). Each location needs both positive and
   negative windows (the same corner before the walk phase is the best negative).
4. With 20 to 50 clips from maybe 5 to 10 locations, report leave-one-location-out
   accuracy honestly and expect it to drop sharply on a new APS model or country.

Full fine-tuning of AST is not realistic in an hour on CPU and would overfit 50
clips.

## 3. Answering questions about audio

### 3.1 Pipeline (chosen)

Build a text summary, then ask the LLM already on the GPU:

```
Transcript: [0.8 to 2.9 s] "Walk sign is on to cross Fifth Avenue."
Sounds (10 s windows): 0 to 10 s: Siren 0.71, Emergency vehicle 0.64, Traffic noise 0.40
Repeating ticks: 9.6 per second from 3.0 to 9.5 s (crosswalk walk-signal pattern)
Question: "Is there an ambulance coming?"
```

This covers what the brief asks for (what was said, what sounds were there,
when). It cannot answer direction ("from my left") or distance; mono AudioSet
taggers carry no spatial information, and neither does any model below. Say so
in the answer instead of guessing. Loudness trend (RMS rising over windows) is a
cheap "getting closer or louder" cue.

### 3.2 Audio-language models checked

| Model | License | Size | Fits about 3 GB at 4-bit? | Verdict |
|---|---|---|---|---|
| `Qwen/Qwen2-Audio-7B-Instruct` | Apache-2.0 | 8.2 B (card says 8B params) | No, about 5 to 6 GB at 4-bit (UNVERIFIED); llama.cpp docs say its GGUF gave "very poor result" | no |
| `Qwen/Qwen2.5-Omni-3B` | qwen-research (non-commercial research) | about 3 B LLM plus audio and vision encoders | Card BF16 minimum 18.4 GB for 15 s video; `ggml-org/Qwen2.5-Omni-3B-GGUF` Q4_K_M is 2.1 GB plus an mmproj file (size UNVERIFIED). `disable_talker()` saves about 2 GB in transformers. MMAU avg 63.3, sound 70.3 | only candidate; CPU via llama.cpp, stretch goal |
| `moonshotai/Kimi-Audio-7B-Instruct` | MIT (Qwen-derived parts Apache-2.0) | 10 B in safetensors | No | no |
| `nvidia/audio-flamingo-3` | NVIDIA OneWay Noncommercial | 7 B-class (Qwen2.5-7B backbone) | No, tested on A100 80 GB | no |
| SALMONN | Apache-2.0 code, Vicuna-based weights (UNVERIFIED) | 7 B / 13 B | No | no |
| `google/gemma-4-E2B-it` | Apache-2.0 | 2.3 B effective, 5.1 B total | Probably at 4-bit (UNVERIFIED); `ggml-org/gemma-4-E2B-it-GGUF` exists. Card lists ASR and speech translation, 30 s audio max, says nothing on non-speech sounds | interesting, untested on sirens |
| `mistralai/Voxtral-Mini-3B-2507` | Apache-2.0 (UNVERIFIED) | 3 B | yes via `ggml-org/Voxtral-Mini-3B-2507-GGUF` | speech-focused, not sound events (UNVERIFIED) |

Why not now: every model that fits is either speech-only or under a
non-commercial license, none has a published number on vehicle sounds or APS
tones, and a new runtime (llama.cpp mtmd) means a new container the day before
the deadline. The pipeline gives timestamped, checkable labels; an omni model
gives a fluent sentence that may be wrong. If time remains after the pipeline
passes the 20 practice items, try `ggml-org/Qwen2.5-Omni-3B-GGUF` Q4_K_M on CPU
with `llama-mtmd-cli` on the same 20 items and compare.

## 4. Example code (verified argument names against the faster-whisper README and the AST / CLAP HF cards)

```python
import numpy as np, torch
from faster_whisper import WhisperModel, decode_audio
from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

AST_ID = "MIT/ast-finetuned-audioset-10-10-0.4593"
stt = WhisperModel("small.en", device="cpu", compute_type="int8", cpu_threads=8)
fx = AutoFeatureExtractor.from_pretrained(AST_ID)
ast = AutoModelForAudioClassification.from_pretrained(AST_ID).eval()

def listen(path, win_s=10.0, hop_s=5.0, k=5):
    wav = decode_audio(path, sampling_rate=16000)          # float32 mono, PyAV
    segs, _ = stt.transcribe(wav, beam_size=5, language="en", vad_filter=True,
                             condition_on_previous_text=False)
    speech = [(s.start, s.end, s.text.strip()) for s in segs
              if not (s.no_speech_prob > 0.6 and s.avg_logprob < -1.0)]
    sounds, n, step = [], int(win_s * 16000), int(hop_s * 16000)
    for i in range(0, max(1, len(wav) - n + step), step):
        x = fx(wav[i:i + n], sampling_rate=16000, return_tensors="pt")
        with torch.inference_mode():
            p = torch.sigmoid(ast(**x).logits[0])           # multi-label
        top = torch.topk(p, k)
        sounds.append((i / 16000, [(ast.config.id2label[j.item()], round(v.item(), 2))
                                   for v, j in zip(top.values, top.indices)]))
    return speech, sounds
```

The returned lists are formatted as in 3.1 and passed to the resident LLM. CLAP
zero-shot, when needed:

```python
from transformers import pipeline
clap = pipeline("zero-shot-audio-classification", model="laion/clap-htsat-unfused")
clap(wav, candidate_labels=["crosswalk signal beeping", "bird chirping", "car horn", "siren"])
```

CLAP's feature extractor expects 48 kHz audio (UNVERIFIED for this checkpoint;
check `clap.feature_extractor.sampling_rate` and resample with
`decode_audio(path, sampling_rate=48000)`).

## 5. To measure first (about 15 minutes)

1. Inspect the 20 practice items: format, length, how many have speech, how many
   are pure sound. `decode_audio` reads wav, mp3, m4a, ogg, and video files.
2. Time `listen()` on the 3 longest items: model load, STT, AST per window. Set
   `cpu_threads` to 8 and to 16 and keep the faster.
3. Check that VRAM does not move (`nvidia-smi`) while audio runs.
4. Hand-score AST top-5 on the sound items; note which brief sounds fail.

## Sources

- faster-whisper README and benchmarks: https://github.com/SYSTRAN/faster-whisper
- https://huggingface.co/openai/whisper-small, https://huggingface.co/openai/whisper-medium
- https://huggingface.co/openai/whisper-large-v3-turbo
- https://huggingface.co/distil-whisper/distil-large-v3, https://huggingface.co/Systran/faster-distil-whisper-large-v3
- https://huggingface.co/Systran/faster-whisper-small
- https://huggingface.co/MIT/ast-finetuned-audioset-10-10-0.4593, https://github.com/YuanGongND/ast
- AudioSet labels: https://github.com/YuanGongND/ast/blob/master/egs/audioset/data/class_labels_indices.csv
- https://github.com/fschmid56/EfficientAT
- https://github.com/qiuqiangkong/audioset_tagging_cnn
- https://github.com/microsoft/unilm/tree/master/beats
- https://huggingface.co/laion/clap-htsat-unfused
- https://huggingface.co/Qwen/Qwen2.5-Omni-3B, https://huggingface.co/ggml-org/Qwen2.5-Omni-3B-GGUF
- https://huggingface.co/Qwen/Qwen2-Audio-7B-Instruct
- https://huggingface.co/moonshotai/Kimi-Audio-7B-Instruct
- https://huggingface.co/nvidia/audio-flamingo-3
- https://huggingface.co/google/gemma-4-E2B-it
- llama.cpp audio support: https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md
- ASPED: https://arxiv.org/abs/2309.06531; ASPED v.b: https://arxiv.org/abs/2509.19295
- CUNY thesis: https://academicworks.cuny.edu/cc_etds_theses/1273
