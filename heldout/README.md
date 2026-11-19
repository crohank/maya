# Held-out set (Maya)

A local test set to catch overfitting to the practice pack. Judges use new items of the
same kinds plus surprise items, so nothing here copies a pack item's parameters, colors,
words, documents or code problems. Same layout and schema as `Kaggle Data/`.

**Do not tune on this set.** Look at the score, not at individual items, or it stops being held out.

Everything is rebuilt from `scripts/make_heldout.py` (CPU, no network, seeded, about 50 s):

```bash
MSYS_NO_PATHCONV=1 docker run --rm --network none -v "$(pwd -W):/app" -w /app -e PYTHONPATH=/app \
  maya-engine python scripts/make_heldout.py
```

Run it through the engine and score it with the existing script (it already has `--pack`
and loads `heldout/keys.json` in place of `scripts/pack_keys.json`):

```bash
bash scripts/gpu_job.sh heldout python scripts/eval_pack.py --pack heldout --run heldout_v1
```

## Contents

68 items: 12 image, 6 audio, 18 text (3 documents), 24 video, 8 code.

```
heldout/
  items.json  answers.json  keys.json  README.md
  image/  h_img_001.jpg ... h_img_012.jpg
  audio/  h_aud_001.wav ... (2 are .webm)
  text/   h_txt_doc_01.txt and .pdf ... h_txt_doc_03
  video/  h_vid_001.mp4 ... (3 are .webm)
  code/tests/  h_code_001_test.py ... h_code_008_test.py
```

## How the answers were made

- Video, image, text, code: known by construction. The generator draws each clip or
  picture from explicit parameters (stored in `answers.json` under `params` / `transform`),
  the documents and questions were written by hand, and each code reference solution is
  run against its test file during generation (all 8 pass).
- Audio: transforms of practice-pack clips, so the labels are the pack's labels. These
  items test robustness to speed, noise, channel and container, not new content.
- `keys.json` is in the `scripts/pack_keys.json` format. Each reference answer scores as a
  pass against its own key (checked with `eval_pack.score`). Keys are lenient on wording
  (direction synonyms, "2 remain" as well as a leading 2) and strict on facts.

## Format robustness (containers)

The live app receives browser MediaRecorder output, so a few items use that container.
The WebM files are written with the muxer in live mode, which leaves out the duration and
cues the same way MediaRecorder does: `ffprobe` reports `Duration: N/A` and OpenCV's
`CAP_PROP_FRAME_COUNT` returns a garbage negative number, while decoding frame by frame works.

| Item | Container | Codec |
|---|---|---|
| h_vid_005, h_vid_014, h_vid_020 | .webm | VP8, 640x480, 24 fps, no audio, no duration in header |
| h_aud_002, h_aud_005 | .webm | Opus 32 kbps, 48 kHz mono, no duration in header |
| other 21 videos | .mp4 | H.264 yuv420p, 640x480, 24 fps, no audio (like the pack) |
| other 4 audio | .wav | 16 kHz mono 16-bit PCM (like the pack) |
| images | .jpg | quality 90, long side at most 1100 px |
| documents | .txt + .pdf | PDF from matplotlib's PDF backend with embedded TrueType text; `pypdf` extracts every word of the .txt |

## Video (24, synthetic)

Same ten families as the pack, with new shapes (triangle, star, hexagon, diamond),
new colors (orange, purple, pink, cyan, brown, black, white), dark and colored
backgrounds, new sizes and speeds, and some reworded questions. Exact parameters are
in `answers.json`.

| id | family | what is new | question | answer |
|---|---|---|---|---|
| h_vid_001 | appear one at a time | 6 triangles, 6 colors, navy background, 0.8 s apart | How many shapes appear in this video? | 6 |
| h_vid_002 | appear one at a time | 3 large stars, gray background, reworded | How many shapes show up, one after another? | 3 |
| h_vid_003 | direction | purple hexagon on beige | Which direction does the hexagon move? | left |
| h_vid_004 | direction | fast (3.5 s), dark background, reworded | Which way is the triangle moving? | down |
| h_vid_005 | direction (WebM) | diagonal | In which direction does the diamond move? | up and to the right |
| h_vid_006 | color order | 4 colors, shapes stay on screen at random positions (screen order is not time order) | What color appears first, and what color appears last? | purple first, cyan last |
| h_vid_007 | color order | brown, pink, black stars replacing each other in the center, reworded | Which color shows up first and which shows up last? | brown first, black last |
| h_vid_008 | sign text | green sign, white bold sans | What does the sign say at the start and at the end? | ENTER, then EXIT |
| h_vid_009 | sign text | yellow sign, serif, two-word text, reworded | What word is on the sign at the beginning, and what does it change to? | SALE, then SOLD OUT |
| h_vid_010 | bar | shrinks (pack only grows), navy background | Does the bar get taller or shorter? | shorter |
| h_vid_011 | bar | grows slowly, off-center, reworded | Is the bar growing or shrinking? | growing |
| h_vid_012 | two shapes | move apart (pack only meets) | What happens to the two shapes? | they move apart |
| h_vid_013 | two shapes | vertical approach, reworded | Do the two shapes move toward each other or away from each other? | toward each other |
| h_vid_014 | numbers (WebM) | counts up 1 to 6, serif, gradient background | What number is shown last? | 6 |
| h_vid_015 | numbers | countdown that stops at 3, not 1, reworded | What is the final number displayed? | 3 |
| h_vid_016 | appear then vanish | 6 appear, 4 vanish, reworded | Some shapes appear and then a few vanish. How many remain at the end? | 2 |
| h_vid_017 | appear then vanish | 7 stars appear, 3 vanish | Several shapes appear and then some disappear. How many shapes are left at the end? | 4 |
| h_vid_018 | bounce | 1 bounce with decaying height, ball drifts sideways | How many times does the ball bounce? | 1 |
| h_vid_019 | bounce | 5 fast bounces (0.9 s per arc), small ball, reworded | How many bounces does the ball make? | 5 |
| h_vid_020 | background (WebM) | green, purple, orange with a white circle on top | What color is the background at the end? | orange |
| h_vid_021 | background | asks for the start color | What color is the background at the beginning of the video? | pink |
| h_vid_022 | appear one at a time, **hard** | Gaussian noise (sigma 28, new every frame), small circles (radius 13 px) | How many shapes appear in this video? | 5 |
| h_vid_023 | bounce, **hard** | vertical sky-to-green gradient background, small ball (radius 12 px) | How many times does the ball bounce? | 2 |
| h_vid_024 | direction, **hard** | tiny dot (radius 6 px), mild noise (sigma 12), diagonal | Which direction does the dot move? | down and to the left |

A bounce means one floor contact. As in the pack, each clip ends with the ball in the air
after its last contact.

## Text (3 documents, 18 questions)

Written for this set (no SQuAD text). Each document has 4 answerable questions and 2
unanswerable ones that reuse an answerable question's wording with one detail changed
(reference "The document does not say.", `"answerable": false`, key `REFUSE`).

| Document | Topic | Pages (PDF) | Unanswerable variants |
|---|---|---|---|
| h_txt_doc_01 | Lab safety notice, Room 214 | 2 | "radioactive waste" (only solvent waste is covered); "lab manager for Room 305" (notice covers Room 214 only) |
| h_txt_doc_02 | Bus Route 12 weekday timetable guide | 1 | "fare on Route 14"; "first bus from Lighthouse Point" (only Eastgate departures are given) |
| h_txt_doc_03 | Coffee maker manual, cleaning and descaling | 1 | "error code E3" (only E1, E2, E4 listed); "citric acid to water ratio" (only vinegar is given) |

## Image (12, synthetic)

**Synthetic renders made with PIL, not photos.** They check text reading and counting
on clean drawings; they do not replace real camera photos (blur, glare, perspective,
clutter). Fonts are the ones in the image: DejaVu Sans/Serif/Mono, STIX and Computer
Modern Sans from matplotlib.

| id | what it is | question | answer |
|---|---|---|---|
| h_img_001 | green exit sign, bold sans, rotated 4 degrees | What does this sign say? | EMERGENCY EXIT |
| h_img_002 | low contrast gray-on-gray carton label, STIX Bold | What does the label say? | KEEP REFRIGERATED |
| h_img_003 | street sign, Computer Modern Sans, rotated -7 degrees, blurred trees | What is the name of the street on this sign? | Maple Avenue |
| h_img_004 | cardboard box, two text sizes and an arrow | What is written on the box? | FRAGILE, THIS SIDE UP |
| h_img_005 | price tag, serif, rotated 3 degrees | How much do the apples cost? | $3.49 per pound |
| h_img_006 | sale tag with struck-out old price | What is the sale price? | $17.50 |
| h_img_007 | ibuprofen bottle label, 19 px print | What is the most tablets you can take in 24 hours? | 6 |
| h_img_008 | amoxicillin pharmacy label, serif | How often should this medicine be taken, and for how long? | 3 times daily for 7 days |
| h_img_009 | 7 drawn apples on a wood table | How many apples are in this image? | 7 |
| h_img_010 | 4 drawn balloons | How many balloons are there? | 4 |
| h_img_011 | 5 blue squares among 3 red squares and 3 blue circles | How many blue squares are in this image? | 5 |
| h_img_012 | small sticky note, oblique low-contrast text, rotated 9 degrees, off-center | Where was the meeting moved to? | Room 12B |

## Code (8)

New HumanEval-style prompts written for this set (not HumanEval problems):
`count_vowel_words`, `rotate_digits`, `merge_ranges`, `second_largest_unique`,
`balance_index`, `sort_by_digital_root`, `parse_duration`, `longest_increasing_run`.
Each prompt is a signature plus a docstring with 2 examples; the question text starts
with "Complete this Python function:" like the pack. Tests are in `code/tests/<id>_test.py`
and end with `check(<entry_point>)`. They include edge cases not shown in the docstring
(empty input, k larger than the length, touching ranges, None returns, stable order).

## Audio (6, transforms of practice-pack clips)

No new recordings could be made offline, so each item transforms pack audio. The source
pack ids, original question and the transform are in `answers.json` (`source`,
`source_ids.pack_ids`, `transform`). Licenses and attributions are carried over.

| id | source | transform | container | question | answer |
|---|---|---|---|---|---|
| h_aud_001 | p_aud_002 speech | 0.9x speed (ffmpeg atempo, pitch kept) | wav | Transcribe this audio. | pack transcript (WER) |
| h_aud_002 | p_aud_005 speech | 1.1x speed (atempo) | webm Opus | Which instrument does she play, and whose letter does she read? | piano, Philip's |
| h_aud_003 | p_aud_015 dog | white noise at 10 dB SNR (vs active-frame RMS) | wav | What sound is this? | dog barking |
| h_aud_004 | p_aud_007 speech | phone line: 300 to 3400 Hz band-pass, 8 kHz mu-law, back to 16 kHz | wav | According to the speaker, where was his country home? | Essex |
| h_aud_005 | p_aud_018 rooster + p_aud_010 male speech | rooster looped under the speech at equal active RMS | webm Opus | What can you hear? | rooster crowing and a man speaking |
| h_aud_006 | p_aud_012 clock + p_aud_001 female speech | clock looped under the speech, 3 dB quieter | wav | What can you hear? | clock ticking and a woman speaking |

The mixed-clip keys need both parts: the sound and some mention of speech or a voice.

## Known limits

- Images are drawings, and audio repeats pack content, so the set is strongest for video,
  documents and code. Real photos and new recordings would need to be collected by hand.
- Keys are substring matches like the pack keys; read failing rows by eye before trusting a drop.
