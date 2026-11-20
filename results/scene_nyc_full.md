# Scene cues: nyc_full

Settings: `{"confirm": 2, "off_s": 5.0, "traffic": "tracks", "traffic_gap": 8.0, "track_bottom": 0.55, "track_motion": "crossing", "traffic_needs_edge": 1}`

Frames asked: 388, latency median 0.46 s, p90 0.61 s
- per frame `edge`: 152 right yes, 21 wrong yes, 8 missed (precision 0.88, recall 0.95)
- per frame `traffic`: 1 right yes, 0 wrong yes, 64 missed (precision 1.00, recall 0.02)

| Spoken at (s) | Words | Verdict |
|---|---|---|
| 5.5 | Crosswalk ahead. | corner 1, 0.5 s before reaching the edge |
| 7.9 | Cars passing. | traffic there |
| 16.9 | Cars passing. | traffic there |
| 25.0 | Cars passing. | traffic there |
| 86.4 | Curb ahead. | corner 2, 0.6 s before reaching the edge |
| 89.9 | Cars passing. | no moving traffic in front |
| 99.5 | Cars passing. | traffic there |
| 108.4 | Cars passing. | traffic there |
| 117.9 | Cars passing. | traffic there |
| 173.5 | Curb ahead. | corner 3, 3.5 s before reaching the edge |
| 182.0 | Cars passing. | traffic there |
| 190.5 | Cars passing. | no moving traffic in front |

Corners announced on time: 3/3

## Notes

- Test set: the team's own 3:14 phone recording in Manhattan (`data/user_clips/nyc_full.mp4`, local only), labelled by eye at 1 fps in `test_videos/labels/nyc_full_scene.json`: 3 street corners and about 2 minutes of plain sidewalk.
- Qwen3-VL-4B NF4 answers three yes/no words per frame at 2 fps, 448 px long side, in 0.46 s median. A JSON reply took 1.7 to 2.1 s per frame.
- Curb and crosswalk: no false corner cue on the sidewalk stretches. The rule (2 yes frames in a row, episode ends after 5 s of no) was not tuned.
- Traffic: Qwen3-VL almost never says yes, so "Cars passing." comes from perception tracks (vehicle crossing, box bottom below 55 % of the frame, only while the frame says edge, at most every 8 s). Those settings were picked on this same recording, so 7 of 9 right is optimistic.
- Wording describes only: no "stop", no "safe to cross", and no light colour (Qwen3-VL read yellow NYC signal housings as a yellow light).
- In walk v3: `python scripts/walk_v3.py run --video <clip> --set scene=1` after `walk_scene.py probe`. Default v3 output is unchanged (same log on nyc_crossing12).
- Not measured: running Qwen3-VL and perception at the same time on the GPU. The 0.46 s is Qwen3-VL alone.
