# Scene cues: yt_siren1 v2

Settings: `{"confirm": 2, "off_s": 5.0, "traffic": "tracks", "traffic_gap": 8.0, "track_bottom": 0.55, "track_motion": "crossing", "traffic_needs_edge": 1, "stages": 1, "road_confirm": 2, "road_leave": 3, "min_cross_s": 4.0, "obstacles": 1, "obstacle_confirm": 2, "obstacle_gap": 10.0}`

Frames asked: 12, latency median 1.01 s, p90 1.19 s
- per frame `edge`: 10 right yes, 2 wrong yes, 0 missed (precision 0.83, recall 1.00)
- per frame `traffic`: 1 right yes, 2 wrong yes, 3 missed (precision 0.33, recall 0.25)

| Spoken at (s) | Words | Verdict |
|---|---|---|
| 1.9 | Crosswalk ahead. | corner 1, 0.1 s before reaching the edge |
| 4.2 | Cars passing. | traffic there |
| 7.9 | In the crosswalk. | right, +1.4 s from stepping into the street |
| 10.0 | Barrier right. | check by eye |

Corners announced on time: 1/1
