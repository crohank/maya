# Scene cues: nyc_full v2

Settings: `{"confirm": 2, "off_s": 5.0, "traffic": "tracks", "traffic_gap": 8.0, "track_bottom": 0.55, "track_motion": "crossing", "traffic_needs_edge": 1, "stages": 1, "road_confirm": 2, "road_leave": 3, "min_cross_s": 4.0, "obstacles": 1, "obstacle_confirm": 2, "obstacle_gap": 10.0}`

Frames asked: 194, latency median 1.04 s, p90 1.36 s
- per frame `edge`: 81 right yes, 18 wrong yes, 0 missed (precision 0.82, recall 1.00)
- per frame `traffic`: 17 right yes, 6 wrong yes, 20 missed (precision 0.74, recall 0.46)

| Spoken at (s) | Words | Verdict |
|---|---|---|
| 2.0 | Scaffolding right. | check by eye |
| 3.0 | Curb ahead. | corner 1, 3.0 s before reaching the edge |
| 7.1 | Cars passing. | traffic there |
| 15.0 | In the crosswalk. | wrong time |
| 16.0 | Cars passing. | traffic there |
| 21.0 | On the sidewalk. | wrong time |
| 24.9 | Cars passing. | traffic there |
| 28.2 | In the crosswalk. | wrong time |
| 36.2 | On the sidewalk. | wrong time |
| 84.1 | Curb ahead. | corner 2, 2.9 s before reaching the edge |
| 87.1 | Cars passing. | no moving traffic in front |
| 96.1 | Cars passing. | no moving traffic in front |
| 97.9 | In the crosswalk. | wrong time |
| 105.0 | Curb ahead, step up. | wrong time |
| 109.0 | Cars passing. | traffic there |
| 118.9 | Cars passing. | traffic there |
| 128.1 | On the sidewalk. | wrong time |
| 171.0 | Trash can left. | check by eye |
| 172.1 | Crosswalk ahead. | false alarm on the sidewalk |
| 175.3 | Cars passing. | false alarm on the sidewalk |
| 185.1 | Cars passing. | traffic there |
| 187.0 | In the crosswalk. | right, +2.0 s from stepping into the street |
| 193.0 | Curb ahead, step up. | wrong time |

Corners announced on time: 2/3
