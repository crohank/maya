# Cosmos3-Edge simulated walk, London clip: hand evaluation

Run: `sim.mp4` / `log.csv` in this folder. Cosmos3-Edge BF16 on an Apple M5 GPU (MPS), thinking off, greedy decoding, repetition_penalty 1.1.
Move triggers come from walk v3 (`results/live/london_walking_v3/log.csv`).
Each call was graded by eye against frames taken 2 s before the request, at the request, and when the answer would be spoken.
One grader, no hand labels, one 20 s clip. The camera is on a bike, so things approach faster than for a walker.

| # | Mode | Asked | Spoken | Trigger | Cosmos said | What the frames show | Content grade | Timing |
|---|---|---|---|---|---|---|---|---|
| 1 | MOVE | 2.0 s | 5.3 s | person left, ttc 3.8 s | 1 step right | A man with a backpack passes close on the left. | Right direction (away from him) | Late, dropped: he was closest at 2.0 s |
| 2 | MOVE | 5.3 s | 8.6 s | person right, ttc 1.9 s | slow down | A couple walks head-on, centre-right, close. | Acceptable | Late, dropped: they were closest at 5.6 s |
| 3 | DESCRIBE | 8.6 s | 11.4 s | none | "Right, close, moving left." | 6.6–8.6 s: a man crossing ahead, people on the right, the purple kiosk on the left. At 11.4 s: a man in a suit close on the right, the A-frame sign close on the left. | Partial: no object named, no step count, missed the kiosk and A-frame sign | Spoken on time |
| 4 | MOVE | 11.7 s | 15.7 s | pole right, ttc 2.5 s | 1 step right | **There is no pole.** Track 102 (confidence 0.35 to 0.59) is a dark shape on the glass wall of the building, above ground level, not in the path (see `pole_track102.png`). A man is close on the right, and the A-frame sign is on the left. | **False trigger from the detector.** "1 step right" still steers toward the man on the right. | Late, dropped |
| 5 | MOVE | 15.7 s | 19.5 s | person right, ttc 2.6 s | 1 step left | A person crossing centre-right. Open plaza, with the green sign stand on the left. | Right direction | Late, dropped |
| 6 | MOVE | 19.5 s | 23.2 s | truck right, ttc 2.4 s | 1 step right | A dark service van close on the right. | **Dangerous: steers toward the van** | Late, dropped |

## Totals (5 moves)

- Right direction: 2
- Acceptable: 1
- Dangerous: 1 (the van)
- False detector trigger, with a bad move: 1 (the "pole")

"1 step right" came 3 of 5 times. Both non-person triggers on the right got "right". People on the right got "left" or "slow down".

None of the 5 moves was spoken before its object's closest point at Mac speed (3.3 to 4.0 s per call).
The describe was short (2.8 s to generate, about 1.3 s to speak) but named no object.
