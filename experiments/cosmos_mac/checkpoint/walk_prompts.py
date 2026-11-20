"""Compare Cosmos3-Edge prompt variants for Maya's moving-user question on 2 s walk windows.

Input per window matches the live app path: last 2 s, 4 fps, 448 px frame list with
real timestamps (maya/video.py style). Variants:
  A_current   maya/video.py SYSTEM + "What is in front of me?", thinking off
  B_ego       chest-camera walking framing, thinking off
  C_ego_think same as B, thinking on
  D_tracks    B framing + detector tracks as grounding + JSON output, thinking on
"""
import json
import sys
import time

import torch

sys.path.insert(0, "/Users/zyrus/Documents/Projects/maya-main")
from maya import video as mv  # noqa: E402
from transformers import AutoModelForImageTextToText, AutoProcessor  # noqa: E402

REPO = "/Users/zyrus/Documents/Projects/maya-main"
WINDOWS = [("walk_w1.mp4", 4.0), ("walk_w2.mp4", 10.0), ("walk_w3.mp4", 17.0)]

EGO = ("The video comes from a phone camera on the chest of a blind person who is walking "
       "forward. The last frame is now. Describe only what matters for their next few steps: "
       "people, vehicles or obstacles within about 5 metres or in their walking path. For each, "
       "say where it is (left, ahead or right), about how many steps away, and whether it is "
       "coming toward them, moving away, crossing, or still. Ignore buildings and anything far "
       "away. Never tell them what to do and never say it is safe.")
Q_SHORT = "What is in front of me? Answer in one short sentence, nearest thing first."
Q_TRACKS = ("A detector tracked these objects in the last frame (it can be wrong): {tracks}.\n"
            "Using the video, reply with JSON only: a list of up to 3 things that matter for my "
            "next few steps, nearest first, each as {{\"object\": str, \"side\": \"left|ahead|right\", "
            "\"steps_away\": number, \"motion\": \"toward|away|crossing left|crossing right|still\"}}. "
            "Include obstacles in my path that the list misses, such as a sign, bin, pole or curb. "
            "Reply [] if nothing is near.")

VARIANTS = [
    ("A_current", mv.SYSTEM, "What is in front of me?", False, 64),
    ("B_ego", EGO, Q_SHORT, False, 64),
    ("C_ego_think", EGO, Q_SHORT, True, 1024),
    ("D_tracks", EGO, Q_TRACKS, True, 1024),
]


def tracks_at(t):
    rows = [json.loads(l) for l in open(f"{REPO}/results/perception/london_walking.jsonl")]
    r = min(rows, key=lambda r: abs(r["t"] - t))
    items = sorted(r["tracks"], key=lambda tr: -(tr["box"][3] - tr["box"][1]))[:4]
    out = []
    for tr in items:
        h = tr["box"][3] - tr["box"][1]
        ttc = f", time to contact {tr['ttc_s']:.1f} s" if tr.get("ttc_s") else ""
        out.append(f"#{tr['id']} {tr['cls']} {tr['side']}, {tr['motion']}{ttc}, box height {h:.2f} of frame")
    return "; ".join(out) or "none"


def main():
    mid = "nvidia/Cosmos3-Edge"
    proc = AutoProcessor.from_pretrained(mid)
    model = AutoModelForImageTextToText.from_pretrained(mid, dtype=torch.bfloat16).to("mps").eval()
    results = []
    for clip, t_end in WINDOWS:
        frames, times = mv.decode(clip)
        idx = mv.pick(times, 4.0, 32)
        ims = [mv.to_pil(frames[i], 448) for i in idx]
        dec_fps = (len(times) - 1) / (times[-1] - times[0])
        pk = {"do_sample_frames": False,
              "video_metadata": [{"fps": dec_fps, "frames_indices": idx, "total_num_frames": len(times),
                                  "duration": times[-1] - times[0]}]}
        tracks = tracks_at(t_end)
        print(f"\n=== {clip} (video {t_end - 2:.0f} to {t_end:.0f} s, {len(ims)} frames)\ntracks: {tracks}", flush=True)
        for name, system, q, think, max_new in VARIANTS:
            text_q = q.format(tracks=tracks) if "{tracks}" in q else q
            msgs = [{"role": "system", "content": [{"type": "text", "text": system}]},
                    {"role": "user", "content": [{"type": "video", "video": ims}, {"type": "text", "text": text_q}]}]
            x = proc.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True, return_dict=True,
                                         return_tensors="pt", enable_thinking=think,
                                         processor_kwargs=pk).to("mps")
            t = time.perf_counter()
            with torch.inference_mode():
                out = model.generate(**x, max_new_tokens=max_new, do_sample=False)
            dt = time.perf_counter() - t
            raw = proc.decode(out[0][x["input_ids"].shape[-1]:], skip_special_tokens=True).strip()
            final = raw.split("</think>")[-1].strip()
            reasoning = raw.split("</think>")[0].replace("<think>", "").strip() if "</think>" in raw else ""
            print(f"[{name}] {dt:.1f}s, {out.shape[-1] - x['input_ids'].shape[-1]} new tokens\n  ANSWER: {final}", flush=True)
            if reasoning:
                print(f"  REASONING: {reasoning[:700]}", flush=True)
            results.append(dict(clip=clip, variant=name, seconds=round(dt, 1), answer=final, reasoning=reasoning))
    with open("walk_prompts.jsonl", "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")


if __name__ == "__main__":
    main()
