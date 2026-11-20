# Cosmos3-Edge simulated walk, London clip: only triggers with confidence ≥ 0.7

Same setup as `../london_cosmos_sim_short2/`, except that a walk v3 trigger is used only when the detector's confidence at the trigger time is 0.7 or higher.
Graded by eye against frames, as before. One grader, one 20 s bike clip.

**Triggers skipped:**

| Track | Object | Confidence | Was it real? |
|---|---|---|---|
| 102 | "pole" | 0.47 | No: a shape on the building wall (see `../london_cosmos_sim_short2/pole_track102.png`) |
| 163 | person | 0.67 | Not checked |
| 178 | "pole" | 0.66 | Not checked |
| 173 | "truck" | 0.57 | **Yes:** the dark service van close on the right. Dropping it is a miss. |

| # | Mode | Asked | Spoken | Trigger | Cosmos said | What the frames show | Content grade | Timing |
|---|---|---|---|---|---|---|---|---|
| 1 | MOVE | 2.0 s | 5.3 s | person left, ttc 3.8 s | 1 step right | A man with a backpack passes close on the left. | Right direction | Late, dropped |
| 2 | MOVE | 5.3 s | 8.5 s | person right, ttc 1.9 s | 1 step left | A couple walks head-on, centre-right. | Right direction | Late, dropped |
| 3 | DESCRIBE | 8.5 s | 11.4 s | none | "Person crossing, right, ahead, 3 steps." | A man crosses centre-right, close. The purple kiosk and A-frame sign are on the left. | Mostly right. The side is vague ("right, ahead") and it missed the kiosk and sign. | On time, still true at 11.4 s |
| 4 | MOVE | 13.2 s | 16.4 s | person right, ttc 2.6 s | 1 step left | A person crosses centre-right. | Right direction | Late, dropped |
| 5 | DESCRIBE | 16.4 s | 19.5 s | none | "A man in black suit, right, 3 steps away, moving away." | A man walks away on the right. The green sign stand is close on the left. | Partial. The man is right, but it missed the close sign stand. | On time |
| 6 | MOVE | 19.5 s | 22.8 s | person right, ttc 2.6 s | 1 step left | A person ahead, centre. People on the right, a lamp post and planters on the left. | Acceptable | Late, dropped |

## Totals

- **Moves (4):** 3 in the right direction, 1 acceptable, **0 dangerous**.
- **Describes (2):** both name a real nearby person with side and steps. Both miss a close sign on the left.
- Speaking time per describe is 2 to 4 s.
- All moves are still too late at Mac speed (3.2 to 3.3 s per call).
- Cost: the real van was below 0.7 and was skipped.
