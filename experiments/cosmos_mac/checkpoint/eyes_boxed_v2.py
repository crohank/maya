import time, torch
from transformers import AutoModelForImageTextToText, AutoProcessor

PROMPT = """I am blind and I am walking. The video comes from a phone camera on my chest, facing where I walk. The last frame is now. Please be my eyes.

I've marked things near me with coloured boxes for your convenience:
- ORANGE box = on my LEFT
- RED box = AHEAD of me
- BLUE box = on my RIGHT
Things without a box can still matter (a sign, bin, pole, step or curb close to me): tell me about those too, with their side.

Ignore buildings, the sky and anything far away. Describe what you see; do not tell me what to do.

What is on my left, what is ahead of me, and what is on my right? For each one, say what it is, about how many steps away, and whether it is coming toward me, moving away, crossing, or not moving. If a side has nothing near, say "nothing".
Answer in this format:
Left: ...
Ahead: ...
Right: ..."""

mid = "nvidia/Cosmos3-Edge"
proc = AutoProcessor.from_pretrained(mid)
model = AutoModelForImageTextToText.from_pretrained(mid, dtype=torch.bfloat16).to("mps").eval()
for n, span in [("w1", "2 to 4 s"), ("w2", "8 to 10 s"), ("w3", "15 to 17 s")]:
    clip = f"walk_{n}_boxed.mp4"
    msgs = [{"role": "user", "content": [{"type": "video", "path": clip}, {"type": "text", "text": PROMPT}]}]
    x = proc.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True, return_dict=True,
                                 return_tensors="pt", processor_kwargs={"fps": 4}).to("mps")
    torch.manual_seed(0)
    t = time.perf_counter()
    with torch.inference_mode():
        out = model.generate(**x, max_new_tokens=4096, do_sample=True)
    new = out[0][x["input_ids"].shape[-1]:]
    raw = proc.decode(new, skip_special_tokens=True)
    think, sep, answer = raw.rpartition("</think>")
    if not sep:
        answer = raw
    print(f"=== {clip} (video {span}) grid={x['video_grid_thw'].tolist()} {time.perf_counter() - t:.1f} s, {len(new)} tokens, think_tag={bool(sep)}")
    print("ANSWER:", answer.strip()[-1200:], "\n", flush=True)
