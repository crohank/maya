# 01. Perception stack for walk mode (detector, depth, tracker, warning policy)

Research for Prompt 1 in `docs/research_prompts.md`, written 2026-11-18. Every model ID
and license below was read from the model card, README or LICENSE page listed in
Sources. Anything not confirmed from a primary source is marked **UNVERIFIED**.
Speed numbers on our RTX 5060 Laptop are not measured yet; all published speeds are on
other GPUs (T4 with TensorRT, A100), so they are upper bounds on what eager PyTorch on
our card will do.

## 1. Recommendation (ranked)

| Rank | Role | Model | Exact ID | License (source) | Published speed | Why |
|---|---|---|---|---|---|---|
| 1 | Detector (main) | D-FINE-S, Objects365 head | `ustc-community/dfine-small-obj365` | Apache-2.0 on the HF card. D-FINE README warns `*_obj365` weights "should not be assumed to be commercially cleared" (Objects365 terms). Fine for a hackathon, name it as a limit. | D-FINE-S: 3.49 ms on T4, TensorRT 10.4 FP16, batch 1 (README, COCO variant; same architecture) | 366 labels include the sidewalk things COCO lacks: `Street Lights`, `Trash bin Can`, `Traffic cone`, `Traffic Sign`, `Crosswalk Sign`, `Stroller`, `Scooter`, `Bench`, `Fire Hydrant`, plus `Person`, `Bicycle`, `Car`, `Bus`, `Truck`. Loads with `DFineForObjectDetection` in transformers. 10.4M params. |
| 1b | Detector (fallback) | D-FINE-S, COCO | `ustc-community/dfine-small-coco` | Apache-2.0 (HF card, README) | 48.5 COCO AP, 3.49 ms T4 TRT FP16 | Clean license, but COCO has no pole, trash can, curb, stairs or A-frame sign. Use if the obj365 head is noisy. `ustc-community/dfine-medium-coco` (19.6M params, 52.3 AP, 5.62 ms T4) is the step up. |
| 2 | Depth (relative) | Depth Anything V2 Small | `depth-anything/Depth-Anything-V2-Small-hf` | Apache-2.0 (HF card; repo LICENSE section says only Small is Apache-2.0) | None published. **UNVERIFIED** estimate 10 to 25 ms at 518 px FP16 eager on our GPU; measure first. | 24.8M params. Gives near/far ordering inside a frame, which is what "nearest obstacle" needs. |
| 2b | Depth (metres) | Depth Anything V2 Metric, outdoor, Small | `depth-anything/Depth-Anything-V2-Metric-Outdoor-Small-hf` (transformers) or original `depth-anything/Depth-Anything-V2-Metric-VKITTI-Small` | Original VKITTI Small card: Apache-2.0. The `-hf` card states no license (**UNVERIFIED**, assume it follows the original). | Same backbone as row 2 | Max depth 80 m. Trained on synthetic Virtual KITTI 2 (car-mounted camera), so absolute metres from a chest-height phone are **UNVERIFIED**; use it for distance bands (under 2 m, 2 to 5 m, over 5 m), not exact steps. Pick one of 2 or 2b, not both, to save VRAM. |
| 3 | Tracker | BoT-SORT (or ByteTrack) from Roboflow `trackers` | pip `trackers`, GitHub `roboflow/trackers` | Apache-2.0 (README) | Association is CPU, negligible next to the detector (OC-SORT README: about 700 FPS association alone on a 3.0 GHz i9) | Same `update(detections, frame=None)` API for SORT, ByteTrack, OC-SORT, BoT-SORT. BoT-SORT adds camera motion compensation, which a walking camera needs. `ByteTrackTracker` class name is confirmed; the BoT-SORT class name is **UNVERIFIED**, read it from the package. |
| 4 | Open-vocabulary (curb, pole, A-frame sign, stairs) | OmDet-Turbo Swin-T | `omlab/omdet-turbo-swin-tiny-hf` | Apache-2.0 (HF card) | Paper: 100.2 FPS for OmDet-Turbo-Base with TensorRT and language cache (GPU not named in abstract). Our speed **UNVERIFIED**. | Text prompts like "pole", "sandwich board sign", "curb", "stairs", "bollard". Run at 1 to 2 Hz or on tap, not every frame. Accuracy on curbs and stairs is **UNVERIFIED** (curbs are long thin edges, a weak case for box detectors). |
| 4b | Open-vocabulary (slower backup) | Grounding DINO Tiny | `IDEA-Research/grounding-dino-tiny` | Apache-2.0 (HF card) | None published on the card; 0.2B params | 52.5 AP COCO zero-shot (card). Use only if OmDet-Turbo misses poles. |

**Not recommended**

| Model | ID / source | Reason |
|---|---|---|
| RT-DETRv2-S | `PekingU/rtdetr_v2_r18vd`, Apache-2.0 | Works (48.1 AP, 217 FPS T4 TRT FP16 per `lyuwenyu/RT-DETR`), but D-FINE-S is faster and has an Objects365 head on HF. Keep as a second fallback. |
| Depth Anything V2 Base / Large | `depth-anything/Depth-Anything-V2-Base`, `-Large` | CC-BY-NC-4.0. Your belief is correct: only Small is Apache-2.0. |
| Video Depth Anything | `depth-anything/Video-Depth-Anything-Small` (Apache-2.0); Base/Large CC-BY-NC-4.0; Metric variants license not stated | Small: 7.5 ms FP16 but on A100 with a 32-frame 518x518 window and 6.8 GB VRAM. Too much VRAM for us. Streaming mode is "experimental" and loses accuracy (ScanNet d1 0.926 to 0.836). |
| Depth Pro | `apple/DepthPro-hf` | 1.0B params, 0.3 s per 2.25 MP image on "a standard GPU". License name conflicts on the card (apple-amlr vs Apple-ASCL). Too slow and unclear. |
| UniDepth V1/V2 | `lpiccinelli/unidepth-v2-vits14` etc. | CC-BY-NC-4.0. |
| Metric3D v2 | `YvanYin/Metric3D` | Code BSD-2-Clause, weights license not stated (**UNVERIFIED**). Needs a focal length for good metric output. |
| SegFormer Cityscapes (would give sidewalk, pole, curb-like regions) | `nvidia/segformer-b0-finetuned-cityscapes-1024-1024` | NVIDIA Source Code License: research and non-commercial only. |
| Ultralytics YOLO | | AGPL, excluded by the brief. |

**VRAM budget (UNVERIFIED until measured).** VLM peak 2.37 GiB (D3). D-FINE-S weights about 20 MB in FP16, DA-V2-S about 50 MB; activations at 640 px and 518 px should stay well under 1 GB together. OmDet-Turbo 0.1B params adds roughly 0.2 GB of weights. Expected total under 4 GiB, inside the about 5 GB free. Measure with `torch.cuda.max_memory_allocated` in the same process as the VLM.

**Expected latency per frame (UNVERIFIED).** Detector 8 to 20 ms + depth 10 to 25 ms + tracker under 2 ms, so about 20 to 45 ms in eager FP16, 10 Hz achievable. The 20 ms target is likely only with TensorRT or `torch.compile`; do not spend the build day on that. GPU contention will slow the VLM look (0.5 s today); measure both together.

## 2. How the pieces answer the four failures in D3

| Failure seen | What fixes it |
|---|---|
| Missed pole + trash can ahead, A-frame signs on the left | Objects365 head has `Street Lights` and `Trash bin Can`; OmDet-Turbo prompt "sandwich board sign", "pole". Nearest is chosen by depth, not by the VLM. |
| Crossing people called "walking away", receding bus called "coming toward you" | Track box centre and size over 1 s. Shrinking box = receding, growing = approaching, sideways centre motion with little size change = crossing. |
| "Two steps ahead" for a far truck | Distance band from depth (or from box height, below), not from VLM words. |
| "Move right" 65/85 | No steering. Speak what and where only (D2 rule stands). |

## 3. Motion, distance and time to contact

Notation per track: box height `h(t)` in px, box bottom `y_b`, centre `x_c`, image width `W`,
median depth `Z(t)` inside the box (from depth model, central 50% of the box to avoid
background bleed).

- **Distance from box height (no depth model needed, rough):** `Z = f_px * H_real / h`, with
  `f_px = (W / 2) / tan(HFOV / 2)`. Typical `H_real`: person 1.7 m, car 1.5 m, bus 3.0 m.
  Phone main camera HFOV about 65 to 70 degrees is **UNVERIFIED**; calibrate once by filming
  a person at a taped 3 m mark. Fails when the box is cut by the frame edge.
- **Time to contact from expansion (tau):** `TTC = h / (dh/dt)` (Lee's tau; valid for an
  object closing at constant speed, independent of its real size). Estimate `dh/dt` by a
  least-squares line fit over the last 0.8 to 1.0 s of `h`, not frame-to-frame differences
  (box jitter is a few px and dominates at 10 Hz). With depth: `TTC = Z / (-dZ/dt)`.
- **Approach / recede / cross classifier (per track, over about 1 s):**
  - `s = (dh/dt) / h` (relative expansion rate, 1/s); `u = (dx_c/dt) / W` (lateral rate).
  - approaching if `s > +0.15`, receding if `s < -0.15`, crossing if `|u| > 0.10` and
    `|s| < 0.15`, else static or unknown. Thresholds are starting points, tune on the four clips.
- **Ego-motion pitfalls (the camera walks at roughly 1.2 to 1.4 m/s, UNVERIFIED typical value):**
  - Static objects ahead also expand, so "approaching" is true relative to the user and is
    the right thing to say for a pole. To tell a moving person from a static one, compare the
    track's closing rate with the closing rate of static background (median of tracks for
    classes that never move: pole, bin, sign, bench). Only call a person "walking toward
    you" if it closes clearly faster than the background.
  - Camera yaw (turning, phone sway) shifts every box sideways at once and fakes "crossing".
    Subtract the global image motion: BoT-SORT camera motion compensation does this, or
    take the median sparse optical flow (OpenCV `calcOpticalFlowPyrLK` on corners outside
    boxes) and subtract it from `dx_c/dt`.
  - Walking bounce moves boxes vertically about 1 to 2 Hz; use height and x only, not `y`.
  - Partial boxes at the image edge change size without real motion; skip expansion
    estimates when the box touches the border.
  - Relative depth (row 2) is affine-invariant per frame and drifts in scale between frames,
    so `dZ/dt` from relative depth is unreliable. Use it for ordering within one frame; use
    box expansion for TTC; use metric depth (row 2b) only for bands.
  - The receding-bus error: a box that shrinks while its depth grows is receding, full stop.
    That single rule fixes the D3 promenade clip.

## 4. From tracks to a spoken warning

**Ahead corridor.** Middle 40% of image width, lower 60% of height (where things at walking
distance appear for a chest-height camera; **UNVERIFIED**, check on clips). Left and right
sectors are the rest. Say "ahead", "ahead left", "ahead right", "left", "right". Clock-face
directions are common in O and M training but whether users prefer them here is
**UNVERIFIED**; keep three to five sectors.

**Trigger rules (start values).**
- Warn when an object in the corridor has distance band "near" (under 2 to 3 m) or TTC under
  3 s, and is confirmed in at least 3 of the last 5 frames (detector score over 0.5 for COCO
  classes, over 0.4 for open-vocab, tune).
- Hysteresis: enter "near" at 2.5 m, leave at 3.5 m; enter TTC alarm at 3.0 s, leave at 4.5 s.
- Per-track cooldown 5 s: do not repeat the same track unless its band gets closer or its
  motion label changes.
- Global rate: at most one warning per 1.5 s, and a warning preempts a VLM description that
  has not started.
- Priority: TTC ascending, then distance, then class weight (vehicle > bicycle/scooter >
  person > static obstacle).
- Wording template, under 6 words: `<class>, <band>, <sector>, <motion>`, for example
  "Person close, ahead left, approaching", "Pole ahead, near", "Bus right, moving away".
  Never "clear", "safe", "go". Keep the D3 safety filter on the output.

**What prior work says users want (only what was verified).**
- WorldScribe (Chang, Liu, Guo; arXiv 2408.06627, ACM DOI 10.1145/3654777.3676375,
  UIST 2024 per arXiv listing): short, quick descriptions in dynamic scenes and longer
  ones in stable scenes; prioritised by user intent; pauses when a conversation starts.
  It pairs a fast detector (word-level labels) with a slower VLM, the same split proposed here.
- WalkVLM (ICCV 2025, arXiv 2412.20903): about 12,000 video-annotation pairs for walking;
  concise reminders and a "temporal-aware adaptive prediction" step to reduce repeated
  reminders. Confirms that repetition control is a core design problem, not a detail.
- Mobilio (Liu and Slade, Nature Biomedical Engineering 2026, DOI 10.1038/s41551-026-01772-x,
  per Harvard SEAS): continuous directional beeps with a chest-worn phone, 9 blind + 5
  visually impaired participants; 72% fewer verbal corrections than Google Maps + cane.
  Suggests a non-speech earcon (left/right pan) for "something close ahead" could beat words
  for the fastest alerts. Paper itself not read (**UNVERIFIED** beyond press release).
- "Just Let the Cane Hit It" (ASSETS 2014, only a secondary summary read, **UNVERIFIED**):
  sighted guides gave vague, badly timed, left/right-confused directions; do not treat every
  object as a hazard, walls and edges are useful cues. Argues against alarming on everything.
- OKO by AYES (App Store, developer pages): on-device pedestrian-signal detection with beeps
  and haptics, phone held at the chest, no network needed. Shows the chest-mount framing and
  non-speech cues are an accepted pattern. Seeing AI, Lookout, Envision, Be My Eyes, NaviLens
  were not researched in this pass (**UNVERIFIED** claims about them omitted).

## 5. Fusing tracker state into the VLM prompt

- Never feed the VLM its own earlier sentences (D4 showed it copies them).
- Feed only current structured state, regenerated each look, 3 objects max:
  `Detected now: 1 person, 2.0 m, ahead left, approaching; 2 pole, 3.5 m, ahead; 3 bus, far, right, moving away.`
- Ask only for what the tracker cannot know: "Using the image, add one short fact not in
  the list: a sign's text, a curb, steps, crosswalk, or path surface. If nothing new, say
  NONE." Post-filter: drop the VLM sentence if it names a class already listed or contains
  a steering verb.
- Optional Set-of-Mark style overlay (Yang et al., arXiv 2310.11441): draw the track IDs
  and boxes on the frame so the VLM can refer to "object 2". Proven for GPT-4V grounding;
  whether a 4B model benefits is **UNVERIFIED**, test on one clip.
- Speech is assembled by code: tracker warning first (deterministic), VLM fact second and
  only if not NONE and not a repeat. No "structured state + small VLM for blind navigation"
  paper beyond WorldScribe and WalkVLM was found and verified in this pass.

## 6. One-day build plan

All inside the existing `docker/cosmos-tf` image (transformers already present; `trackers`
and `opencv-python-headless` need adding to the Dockerfile, not the host).

| Hours | Step | Done when |
|---|---|---|
| 0 to 1 | `scripts/perceive.py`: load `ustc-community/dfine-small-obj365` and `depth-anything/Depth-Anything-V2-Small-hf` in FP16, run on the four clips at 10 Hz, save per-frame JSON (boxes, labels, scores, median box depth) and timing. | Median ms per stage and peak VRAM printed with the VLM also loaded. |
| 1 to 2 | Label whitelist and class remap (`Street Lights` to "pole", `Trash bin Can` to "trash can", vehicles grouped). Dump contact sheets with boxes at 45 s Fifth Ave (pole + bin), London 8 to 11 s (A-frames), 4K clip 22 to 24 s (curb). | Visually confirm what the detector sees and misses. |
| 2 to 3 | Add `trackers` BoT-SORT (fall back to ByteTrack if CMC fails), per-track history, expansion-rate fit, global-motion subtraction, motion label, TTC, distance band. | Bus on promenade clip labelled "moving away" after 11.6 s; London crossers labelled "crossing". |
| 3 to 4 | Warning policy (section 4) and phrase templates; reuse Piper and the stale-drop speaker from `live_harness.py`. | Spoken log per clip with timestamps. |
| 4 to 5 | If pole/A-frame/curb are missed: OmDet-Turbo at 2 Hz on the corridor crop with 6 prompts; merge into tracker as extra detections. | Hits on the three missed events or a named limit. |
| 5 to 6 | VLM fusion (section 5), NONE filter, run all four clips. | VLM adds sign text / crosswalk without repeating tracker objects. |
| 6 to 8 | Eval protocol (section 7) on the four clips, write results into `decisions.md` as D5. | Table of hit rate, lead time, false alarms per minute, direction accuracy. |

Cut order if behind: OmDet-Turbo (hour 4 to 5), then VLM fusion. Detector + tracker +
templates alone already fix the direction and distance errors.

## 7. Evaluation protocol (a few hours)

**Ground truth, hand labelled (about 1 hour for the 4 clips, about 117 s total).** CSV per clip:
`event_id, t_onset, t_pass, class, sector, motion, must_warn`. `t_onset` = first time the
object is within about 3 m in the corridor or would reach it within 3 s; `t_pass` = when it
is beside or past the walker. `must_warn` = 1 for obstacles in path and approaching
vehicles/people; 0 for far or off-path things (these define false alarms). Already known
events from D2/D3: pole + trash can at 45 s Fifth Ave, crosswalk at 45 s, woman crossing,
bus enters right 3 s and drives away, black car left 13 to 15 s, pickup crossing far at
17 to 20 s, curb + crosswalk 22 to 24 s on the 4K clip, purple A-frames left 8 to 11 s London,
sideways crossers in London.

**Metrics.**
- Hit rate: a `must_warn` event is hit if a warning with the same class group and sector is
  spoken in `[t_onset - 3 s, t_pass]`.
- Lead time: `t_pass - t_speech_start` for each hit (median and min). Target at least 2 s.
- False alarms per minute: warnings matching no `must_warn` event.
- Direction accuracy: for labelled moving objects, motion label at speech time vs truth
  (approaching / receding / crossing). Compare with the VLM baseline from D3 (bus, London).
- Distance band accuracy: band at speech time vs a hand estimate (near / mid / far).
- Report latency and peak VRAM with the VLM running.
- Run three configs: VLM only (D3 baseline), tracker only, tracker + VLM.

**Public data for a larger or quantitative check.**

| Dataset | What | License | Download | Fit |
|---|---|---|---|---|
| SANPO (Google Research) | Egocentric outdoor walking video, 701 real sessions (blog), panoptic labels incl. sidewalk, curb, poles per blog, depth in metres (ZED + CREStereo) | CC BY 4.0 ("Creative Commons V4.0", README) | `gs://gresearch/sanpo_dataset/v0`, about 6 TB total, partial via `gcloud storage rsync` with excludes | Best for checking metric depth error at 1 to 10 m and curb visibility. Pull 2 or 3 sessions only (per-session size **UNVERIFIED**). |
| PEDESTRIAN (CYENS, arXiv 2512.19190) | 340 phone videos, 82,120 frames, 29 sidewalk obstacle types incl. Bin, Advert Sign, Bench, Traffic Cone, Fence, Hole/Pot-Hole, Scaffolding, Narrow/No Pavement | Dataset license not stated in paper; Zenodo page did not load (**UNVERIFIED**) | Zenodo DOI 10.5281/zenodo.10907945, code `github.com/CYENS/PEDESTRIAN` | Image-level labels only (no boxes), so use for detector recall per class (did it fire on a "Bin" frame), not for localisation. |
| GuideDog (ACL 2026, arXiv 2503.12844) | 2,106 human-verified guidance examples; `depth` (383) and `object` (435) multiple-choice subsets with boxes and depth | CC BY-NC 4.0, gated (auto-approve, academic use, no redistribution) | `huggingface.co/datasets/kjunh/GuideDog`, 5.11 GB | The `depth` subset ("which is closer") tests depth ordering from DA-V2 directly. |
| WalkVLM WAD | About 12,000 walking video-annotation pairs | Not stated (**UNVERIFIED**) | `walkvlm2024.github.io` | Possible later; not checked. |

## 8. Unverified items to measure or check first

1. Actual ms per frame for D-FINE-S and DA-V2-S on the RTX 5060 Laptop, and VLM slowdown when they share the GPU.
2. Whether `dfine-small-obj365` fires on poles (via `Street Lights`), bins and A-frame signs in our clips; Objects365 AP for the S variant was not read.
3. License of `Depth-Anything-V2-Metric-Outdoor-Small-hf` (card silent; original VKITTI Small is Apache-2.0).
4. Absolute accuracy of the VKITTI-trained metric model from a chest-height phone.
5. BoT-SORT class name in the `trackers` package.
6. OmDet-Turbo speed on our GPU and recall for curb and stairs prompts.
7. Phone HFOV for the box-height distance formula.
8. PEDESTRIAN dataset license; SANPO per-session size.

## Sources

- D-FINE repo (license, COCO table, T4 latency, Objects365 caveat): https://github.com/Peterande/D-FINE
- D-FINE in transformers (class names, checkpoint IDs): https://huggingface.co/docs/transformers/main/en/model_doc/d_fine
- https://huggingface.co/ustc-community/dfine-small-coco
- https://huggingface.co/ustc-community/dfine-medium-coco
- https://huggingface.co/ustc-community/dfine-small-obj365 and label list https://huggingface.co/ustc-community/dfine-small-obj365/raw/main/config.json
- HF org listing: https://huggingface.co/ustc-community
- RT-DETR / RT-DETRv2 repo (license, AP, T4 FPS): https://github.com/lyuwenyu/RT-DETR
- https://huggingface.co/PekingU/rtdetr_v2_r18vd
- Depth Anything V2 repo (license per size): https://github.com/DepthAnything/Depth-Anything-V2
- https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf
- Metric depth README: https://github.com/DepthAnything/Depth-Anything-V2/tree/main/metric_depth
- https://huggingface.co/depth-anything/Depth-Anything-V2-Metric-VKITTI-Small
- https://huggingface.co/depth-anything/Depth-Anything-V2-Metric-Outdoor-Small-hf
- Video Depth Anything (licenses, A100 latency, streaming): https://github.com/DepthAnything/Video-Depth-Anything
- Depth Pro: https://github.com/apple/ml-depth-pro and https://huggingface.co/apple/DepthPro-hf
- UniDepth: https://github.com/lpiccinelli-eth/UniDepth
- Metric3D: https://github.com/YvanYin/Metric3D
- SegFormer license: https://github.com/NVlabs/SegFormer/blob/master/LICENSE and https://huggingface.co/nvidia/segformer-b0-finetuned-cityscapes-1024-1024
- OmDet-Turbo: https://huggingface.co/omlab/omdet-turbo-swin-tiny-hf and paper https://arxiv.org/abs/2403.06892
- Grounding DINO Tiny: https://huggingface.co/IDEA-Research/grounding-dino-tiny
- ByteTrack: https://github.com/ifzhang/ByteTrack
- OC-SORT: https://github.com/noahcao/OC_SORT
- BoT-SORT: https://github.com/NirAharon/BoT-SORT
- Norfair (BSD-3, camera motion demo; alternative tracker): https://github.com/tryolabs/norfair
- Roboflow trackers (Apache-2.0, ByteTrack/OC-SORT/BoT-SORT): https://github.com/roboflow/trackers
- Supervision (MIT): https://github.com/roboflow/supervision
- SANPO: https://github.com/google-research-datasets/sanpo_dataset and https://research.google/blog/sanpo-a-scene-understanding-accessibility-navigation-pathfinding-obstacle-avoidance-dataset/
- PEDESTRIAN: https://arxiv.org/abs/2512.19190 and https://arxiv.org/html/2512.19190
- GuideDog: https://huggingface.co/datasets/kjunh/GuideDog and https://arxiv.org/abs/2503.12844v1
- WalkVLM: https://arxiv.org/abs/2412.20903 and https://openaccess.thecvf.com/content/ICCV2025/html/Yuan_WalkVLM_Aid_Visually_Impaired_People_Walking_by_Vision_Language_Model_ICCV_2025_paper.html
- WorldScribe: https://arxiv.org/abs/2408.06627
- Set-of-Mark prompting: https://arxiv.org/abs/2310.11441
- Mobilio (press): https://seas.harvard.edu/news/smartphone-navigation-app-people-blindness-and-low-vision
- "Just Let the Cane Hit It" (secondary summary only): https://a11y-paradise.onrender.com/reviews/69cf09008ef79961d3ffb84e
- OKO: https://apps.apple.com/us/app/oko-by-ayes/id1583614988 and https://ioplus.nl/archive/en/free-ticker-app-oko-from-ayes-allows-the-blind-and-visually-impaired-to-cross-roads-safely-again/
