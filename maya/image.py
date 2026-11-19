import re

from PIL import Image

SYSTEM = ("You answer questions about a photo for a person who cannot see it. "
          "Start with the answer itself, then at most one short sentence. "
          "For 'how many' questions, start with the number. Read text exactly as written.")
LIST_PROMPT = ("{q}\nFirst list each one you can see, one per line, with where it is in the photo "
               "(include people or animals that are partly hidden, small or at the edges). "
               "Then write the final line as: Answer: <number>")
LONG_SIDE = 1280
COUNT_Q = re.compile(r"\bhow many (\w+)", re.I)


def load(path, long_side=LONG_SIDE, upscale_to=0):
    im = Image.open(path).convert("RGB")
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


def answer(eng, path, question):
    im = load(path, upscale_to=int(eng.opts.get("upscale", 0)))
    mode = eng.opts.get("count", "plain")
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
    if m and mode in ("list", "both"):
        text, i2 = eng.vlm.chat([{"type": "image", "image": im},
                                 {"type": "text", "text": LIST_PROMPT.format(q=q)}], SYSTEM, 400)
        final = re.findall(r"answer:\s*(\d+)", text, re.I)
        info.update(i2, scratch=text[-300:])
        if final:
            noun = m.group(1)
            return f"{final[-1]} {noun}.", info
        return text.strip().splitlines()[-1], info
    text, i2 = eng.vlm.chat([{"type": "image", "image": im}, {"type": "text", "text": q}], SYSTEM, 64)
    return text, {**info, **i2}
