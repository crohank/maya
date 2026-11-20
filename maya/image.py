import re

from PIL import Image

SYSTEM = ("You answer questions about a photo for a person who cannot see it. "
          "Start with the answer itself, then at most one short sentence. "
          "For 'how many' questions, start with the number. Read text exactly as written. "
          "Describe what is there. Never give advice or instructions such as 'be careful'.")
LIST_PROMPT = ("{q}\nFirst list each one you can see, one per line, with where it is in the photo "
               "(include people or animals that are partly hidden, small or at the edges). "
               "Then write the final line as: Answer: <number>")
LONG_SIDE = 1280
COUNT_Q = re.compile(r"\bhow many (\w+(?: \w+){0,2}?)(?= (?:are|is|were|can|do|does|did|appear|in|on|there)\b|\?|$)", re.I)
# 64 new tokens cut a transcribed menu or page short.
READ_Q = re.compile(r"\b(read|says?|written|text|signs?|labels?|menus?|pages?)\b", re.I)


def to_rgb(im):
    """RGB on a white background: convert("RGB") turns transparent pixels black."""
    if im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.getchannel("A"))
        return bg
    return im.convert("RGB")


def load(path, long_side=LONG_SIDE, upscale_to=0):
    im = to_rgb(Image.open(path))
    im.thumbnail((long_side, long_side))
    if upscale_to and max(im.size) < upscale_to:
        s = upscale_to / max(im.size)
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    return im


def _detector(eng):
    if "dfine" not in eng.cache:
        import torch
        from transformers import AutoImageProcessor, AutoModelForObjectDetection
        rid = "ustc-community/dfine-small-obj365"
        eng.cache["dfine"] = (AutoImageProcessor.from_pretrained(rid),
                              AutoModelForObjectDetection.from_pretrained(rid).to("cuda").eval())
    return eng.cache["dfine"]


def _singular(w):
    w = w.lower()
    for a, b in (("people", "person"), ("men", "man"), ("women", "woman"), ("children", "child"),
                 ("mice", "mouse"), ("geese", "goose"), ("sheep", "sheep"), ("fish", "fish")):
        if w == a:
            return b
    return w[:-3] + "y" if w.endswith("ies") else w[:-2] if w.endswith(("ches", "shes", "sses")) \
        else w[:-1] if w.endswith("s") else w


def detector_count(eng, im, noun, thresh=0.5):
    """Boxes of the asked class from D-FINE obj365, or None if the class is not in its 365 labels."""
    import torch
    proc, model = _detector(eng)
    target = _singular(noun.split()[-1])
    if target in ("man", "woman", "child", "kid", "boy", "girl"):
        target = "person"
    ids = [i for i, n in model.config.id2label.items() if _singular(n.split("/")[0].strip()) == target]
    if not ids:
        return None
    with torch.inference_mode():
        out = model(**proc(images=im, return_tensors="pt").to("cuda"))
    res = proc.post_process_object_detection(out, threshold=thresh, target_sizes=[im.size[::-1]])[0]
    return int(sum(int(l) in ids for l in res["labels"]))


def _iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


AUTO_MIN = 4


def ground_count(eng, im, noun, info):
    """Qwen3-VL grounding: one bbox_2d per object (0 to 1000 coordinates), counted in code."""
    prompt = (f"Locate every {noun} in the image, including ones that are small, partly "
              f"hidden or cut off at the edges. Output a JSON list with one entry per {noun}: "
              '[{"bbox_2d": [x1, y1, x2, y2], "label": "' + noun + '"}]')
    text, i2 = eng.vlm.chat([{"type": "image", "image": im}, {"type": "text", "text": prompt}],
                            None, 1024)
    boxes = re.findall(r"\[\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]", text)
    uniq = []
    for b in (tuple(map(int, b)) for b in boxes):
        if all(_iou(b, u) < 0.7 for u in uniq):
            uniq.append(b)
    info.update(i2, boxes=len(boxes), unique=len(uniq))
    return f"{len(uniq)} {noun}.", info


def answer(eng, path, question):
    im = load(path, upscale_to=int(eng.opts.get("upscale", 0)))
    mode = eng.opts.get("count", "auto")
    m = COUNT_Q.search(question)
    info = {"route": "image"}
    q = question
    if m and mode in ("detector", "both"):
        n = detector_count(eng, im, m.group(1))
        info["detector_count"] = n
        if n is not None:
            q = (f"{question}\n(An object detector found {n} {m.group(1)} with high confidence; "
                 "it can miss ones that are small, hidden or cut off, and can double count. "
                 "Check the photo yourself.)")
    if m and mode == "ground":
        return ground_count(eng, im, m.group(1), info)
    if m and mode == "auto":
        # Plain count first (0.3 s); every miss on our sets was a count of 4 or more,
        # so only those are re-counted from boxes (6 to 15 s).
        text, i2 = eng.vlm.chat([{"type": "image", "image": im}, {"type": "text", "text": q}], SYSTEM, 64)
        info.update(i2, plain=text)
        nums = re.findall(r"\d+", text)
        if nums and int(nums[0]) >= AUTO_MIN:
            g, ginfo = ground_count(eng, im, m.group(1), dict(info))
            if ginfo.get("unique"):
                return g, ginfo
        return text, info
    if m and mode in ("list", "both"):
        text, i2 = eng.vlm.chat([{"type": "image", "image": im},
                                 {"type": "text", "text": LIST_PROMPT.format(q=q)}], SYSTEM, 400)
        final = re.findall(r"answer:\s*(\d+)", text, re.I)
        info.update(i2, scratch=text[-300:])
        if final:
            noun = m.group(1)
            return f"{final[-1]} {noun}.", info
        return text.strip().splitlines()[-1], info
    max_new = 256 if READ_Q.search(question) else 64
    text, i2 = eng.vlm.chat([{"type": "image", "image": im}, {"type": "text", "text": q}], SYSTEM, max_new)
    return text, {**info, **i2}
