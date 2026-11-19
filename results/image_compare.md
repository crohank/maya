# Image reading: Cosmos3-Edge vs Qwen3-VL

Rule: pass when every required key string appears in the answer (case-insensitive, alternatives separated by |). 10 items: 3 real frames from test_videos/, 7 synthetic with known text.

| Model | Passed | Mean key recall | Median latency | p90 latency | Peak VRAM | Load time |
|---|---|---|---|---|---|---|
| cosmos3-edge-nf4 | 5/10 | 0.71 | 1.05s | 2.33s | 2.44 GiB | 8.8s |
| qwen3vl-4b | 6/10 | 0.81 | 1.98s | 2.72s | 3.61 GiB | 5.3s |

| Model | Image | Pass | Answer |
|---|---|---|---|
| cosmos3-edge-nf4 | real_kiosk_sign.png | no | The purple signs in the image say "Kiosk Opens Today At 2:58". There's also a number visible in the bottom left corner of the image, which is 1269047642. |
| cosmos3-edge-nf4 | real_parking_sign.png | no | 303 PARKING 303 PARKING Wegman's Wegman's BARRI EXIT ONLY PARKING EXIT ONLY PARKING EXIT ONLY PARKING PARKING |
| cosmos3-edge-nf4 | real_lunch_sign.png | no | The white sign on the right says "RIDE". |
| cosmos3-edge-nf4 | real_parking_sign.png | yes | Yes, there is a black pickup truck visible on the road. It's driving towards the camera in the left lane, positioned in front of a white building with a green awning. |
| cosmos3-edge-nf4 | syn_bus_sign.png | yes | The bus shown is M15 heading to South Ferry. |
| cosmos3-edge-nf4 | syn_slide.png | yes | The slide shows Quarterly Results with three bullet points stating that revenue is up 12%, churn is down to 3.1%, and they are hiring 4 engineers. |
| cosmos3-edge-nf4 | syn_whiteboard.png | yes | Exam: Dec 3, Room 214 Covers Ch. 5-7 Bring a calculator |
| cosmos3-edge-nf4 | syn_medicine.png | no | The dose is 1 tablet every 4 to 6 hours, and the daily limit is 6 tablets. |
| cosmos3-edge-nf4 | syn_bar_chart.png | yes | Bar B is tallest with a value of 7 thousand units. |
| cosmos3-edge-nf4 | syn_small_text.png | no | December 12, 14 |
| qwen3vl-4b | real_kiosk_sign.png | no | The purple signs say "LOCO OPENS TODAY AT 2:58" and "FOR ONE MINUTE ONLY". |
| qwen3vl-4b | real_parking_sign.png | yes | The signs read "303 PARKING Wegmans" and "EXIT ONLY" with an arrow pointing down. |
| qwen3vl-4b | real_lunch_sign.png | no | The white sign on the right says "FAR CORP." |
| qwen3vl-4b | real_parking_sign.png | yes | Yes, there is a black pickup truck on the road, driving toward the center of the image. It’s positioned between the yellow lane lines, slightly to the left of the road’s center. |
| qwen3vl-4b | syn_bus_sign.png | yes | Bus M15 to South Ferry. |
| qwen3vl-4b | syn_slide.png | no | Revenue increased by 12%, churn dropped to 3.1%, and 4 engineers were hired. |
| qwen3vl-4b | syn_whiteboard.png | yes | The whiteboard says: "Exam: Dec 3, Room 214; Covers Ch. 5-7; Bring a calculator." |
| qwen3vl-4b | syn_medicine.png | no | Take 1 tablet every 4 to 6 hours, not exceeding 6 tablets in 24 hours. |
| qwen3vl-4b | syn_bar_chart.png | yes | Bar B is tallest, with a value of 7 thousand units sold. |
| qwen3vl-4b | syn_small_text.png | yes | The best-before date is 2026-12-14. |
