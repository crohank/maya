import sys, time, torch
sys.path.insert(0, "/Users/zyrus/Documents/Projects/maya-main")
from maya import video as mv
from transformers import AutoModelForImageTextToText, AutoProcessor

SYSTEM = ("I am blind and I am walking. The video comes from a phone camera on my chest, facing where I walk. "
          "The last frame is now. Please be my eyes. Tell me only about people, vehicles and obstacles near me, "
          "within about 5 steps. Ignore buildings, the sky and anything far away. Describe what you see; do not "
          "tell me what to do.")
USER = ("I need your help. What is on my left, what is ahead of me, and what is on my right? For each one, say "
        "what it is, about how many steps away, and whether it is coming toward me, moving away, crossing, or not "
        "moving. If a side has nothing near, say \"nothing\".\nAnswer in this format:\nLeft: ...\nAhead: ...\nRight: ...")

mid = "nvidia/Cosmos3-Edge"
proc = AutoProcessor.from_pretrained(mid)
model = AutoModelForImageTextToText.from_pretrained(mid, dtype=torch.bfloat16).to("mps").eval()
for clip, span in [("walk_w1.mp4", "2 to 4 s"), ("walk_w2.mp4", "8 to 10 s"), ("walk_w3.mp4", "15 to 17 s")]:
    frames, times = mv.decode(clip)
    idx = mv.pick(times, 4.0, 32)
    ims = [mv.to_pil(frames[i], 448) for i in idx]
    pk = {"do_sample_frames": False, "video_metadata": [{"fps": (len(times) - 1) / (times[-1] - times[0]),
          "frames_indices": idx, "total_num_frames": len(times), "duration": times[-1] - times[0]}]}
    msgs = [{"role": "system", "content": [{"type": "text", "text": SYSTEM}]},
            {"role": "user", "content": [{"type": "video", "video": ims}, {"type": "text", "text": USER}]}]
    x = proc.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True, return_dict=True,
                                 return_tensors="pt", enable_thinking=False, processor_kwargs=pk).to("mps")
    t = time.perf_counter()
    with torch.inference_mode():
        out = model.generate(**x, max_new_tokens=96, do_sample=False, repetition_penalty=1.1)
    text = proc.decode(out[0][x["input_ids"].shape[-1]:], skip_special_tokens=True).split("</think>")[-1].strip()
    print(f"=== {clip} (video {span}), {time.perf_counter() - t:.1f} s\n{text}\n", flush=True)
