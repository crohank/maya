# Overnight report, 2026-11-18 23:15 to 2026-11-19 06:00

## The big finding

`Kaggle Data/README.md`: judges pick random items of the practice pack's five kinds
(image, audio, document, video, code, plus surprise items) and ask them live on our
laptop with Wi-Fi off. Walk mode is not one of them. So the night went on answering
those items well, plus a better walk test set.

## Scores (all local, Qwen3-VL-4B NF4 as the main model)

| Set | Items | Start of night | Now |
|---|---|---|---|
| Practice pack | 100 | 74 | **96** |
| Held-out set made tonight (new synthetic videos, docs, images, code; WebM inputs) | 68 | | 64 |
| SQuAD 2.0 extra (15 docs, 15 of 60 unanswerable) | 60 | 47 (plain prompt) | 46 |
| VizWiz extra (real photos from blind users) | 80 | | 72 |
| LibriSpeech extra (transcribe and questions) | 40 | | 34 |
| ESC-50 extra (all 50 sound classes, 40 never in the pack) | 100 | 73 (AST) | 84 |
| HumanEval extra, sample | 40 | 36 (no self-check) | 37 |

Practice pack by kind:

| Kind | Start | Now | Median s per item |
|---|---|---|---|
| Image | 23/25 | 23/25 | 0.3 |
| Audio | 8/20 | 19/20 | 1.7 |
| Document | 17/20 | 19/20 | 2.5 |
| Video | 8/15 | 15/15 | 1.4 |
| Code | 18/20 | 20/20 | 6.7 |

The practice pack was the tuning set, so its 96 is optimistic. The held-out and extra
sets were not tuned on (two documented exceptions in the doc QA and video notes below).

## What changed, by kind

- **Video** (`maya/video.py`, `maya/video_cv.py`):
  - Root cause of most misses: the processor resampled our frame list as if it were 24 fps footage, so the model saw about 4 frames per clip. Fixed by passing the real timestamps.
  - On synthetic-looking clips only, measured facts are added to the prompt: object counts over time, colors in order, direction, bounces, size trend, background color.
  - Cosmos3-Edge was tried again: 2 to 4 of 15, plus about 11 s per swap. Not used.
- **Audio** (`maya/audio.py`, `maya/sound.py`):
  - Speech or sound is decided from the audio itself, not the question wording.
  - Transcription: faster-whisper small.en on CPU.
  - Sound ID: CLAP zero-shot over a general list of 122 everyday and street sounds, plus a tick-rate rule for crosswalk signals.
  - Questions about speech are answered from the transcript.
- **Documents** (`maya/docqa.py`):
  - The model quotes a sentence from the document plus a short answer. Code then checks that the quote is really there and that the question's numbers and names appear in it. If either fails, it says "The document does not say."
  - Pages with no text layer are read by the VLM.
  - Costs about 3 s per question, against 0.6 s for the plain prompt.
- **Code** (`maya/code.py`, `maya/sandbox.py`):
  - The prompt's own examples run in a sandbox, with up to 2 retries.
  - If the main model still fails its own checks, it falls back to Qwen2.5-Coder-3B.
  - The sandbox: resource limits, runs as an unprivileged user, no network, an audit hook.
- **App** (`app/main.py`, `app/router.py`):
  - `/ask` now answers all five kinds through one engine, and `/document/ask` and `/code/run` are real.
  - Phone WebM is converted first.
  - Startup warms every model, so the first item is not 5 to 8 s slower.
- **Walk mode** (`scripts/walk_v3.py` to `walk_v5.py`):
  - New test set: 11 SANPO chest-camera clips (Google Research, CC BY 4.0) with labels made automatically from depth and instance masks.
  - New scorer: a warning only counts if it was about the right tracked person. A time-shifted baseline scores 0 to 1 of 33, so talking often no longer scores.

  | Walk version (SANPO, 33 events) | On time | Right side | Words/min |
  |---|---|---|---|
  | v2 (words) | 15 | 4 | 30 |
  | v3 (panned tones, one word per person) | **24** | 11 to 15 | 17 |

  - v5 (hold the side until close) was worse.
  - Side accuracy is limited by timing: 2 to 3 s out, which side someone passes on is close to a coin flip.

## Open issues (worth knowing before the demo)

- **Car horns:** CLAP called a horn a doorbell, and both models missed the ESC-50 horn. The fallback is `sound: ast` in `app/config.yaml` engine opts. Test a real horn recording.
- **Code sandbox:**
  - Generated code can still write into the repo through the Docker Windows file mount. The audit hook blocks the known ways, but it is not a hard boundary.
  - The real fix is to run the app with `/app` read-only and a separate results volume, or run code in a sidecar container.
- **Unanswerable traps that change a relation** ("rise" for "drop") still get answered: about 8 of 15 on the SQuAD extra set.
- **Rotated phone MP4s:**
  - The app re-encodes them now.
  - The rotation check is not verified on a real phone clip, because this image's ffmpeg cannot write a rotation tag.
- **The phone page** has no document button and no text-only code input. Those kinds work through the API only. (UI work was out of scope tonight.)
- **Scorer keys are mine.** The practice pack keys were hand-written from `answers.json`, lenient on wording and strict on facts. One fair-looking miss is p_txt_005 ("the architect or engineer" against "the project coordinator").

## Process notes

- **GPU:** max 70 C, mean 62 C over the night. One job at a time, through a lock. The watchdog never had to pause anything (log: `results/gpu_temps.csv`, local only).
- **Disk:** C: free went from 41 GB to a low of 21 GB, then back to 76 GB once temporary files were freed.
- **Downloads**, all official sources:
  - Hugging Face models: AST, CLAP, faster-whisper small.en and distil-large-v3, Qwen2.5-Coder-3B
  - Hugging Face datasets: SQuAD 2.0, HumanEval, MBPP, VizWiz-VQA, LibriSpeech
  - ESC-50 from its authors' GitHub
  - SANPO from Google's public bucket
- **Kept local:** all data stays local and gitignored. Nothing was pushed or uploaded.
- **Microsoft Store pop-up:** several agents ran `python` on the Windows host early in the night, before I added a rule against it. That is what opened the Store page.
- **Duplicate pack:** a second copy of the practice pack sits at the repo root (`items.json`, `audio/`, ...), byte-identical to `Kaggle Data/` and dated 23:14. I left it in place and gitignored it.
- **My breakage:** my own typo broke `scripts/eval_pack.py` for about 15 minutes. Affected runs were redone.
- **Commits:** local only, on `main`.
