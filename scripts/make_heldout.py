"""Build the held-out evaluation set in heldout/ (CPU only, no network).

  MSYS_NO_PATHCONV=1 docker run --rm --network none -v "$(pwd -W):/app" -w /app \
    -e PYTHONPATH=/app maya-engine python scripts/make_heldout.py

Writes heldout/{items,answers,keys}.json plus media in the practice-pack layout,
so `scripts/eval_pack.py --pack heldout` runs it. Answers are known by
construction (video parameters, rendered text, documents written here, reference
solutions). Audio items are transforms of practice-pack clips and reuse their
labels. Output is deterministic: every random draw comes from a seeded rng.
"""
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import cv2
import matplotlib
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

matplotlib.use("pdf")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402

OUT = Path("heldout")
PACK = Path("Kaggle Data")
W, H, FPS = 640, 480, 24
SYN = {"license": "CC BY 4.0", "attribution": "Maya team, synthetic held-out set (not part of the practice pack)"}
items, answers, keys = [], [], {}


def add(iid, modality, file, question, ref, key=None, **meta):
    items.append({"id": iid, "modality": modality, "file": file, "question": question})
    answers.append({"id": iid, "modality": modality, "reference_answer": ref, **meta})
    if key is not None:
        keys[iid] = key


DEJAVU = "/usr/share/fonts/truetype/dejavu"
MPL_TTF = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
FONTS = {
    "sans": f"{DEJAVU}/DejaVuSans.ttf", "sans_bold": f"{DEJAVU}/DejaVuSans-Bold.ttf",
    "serif": f"{DEJAVU}/DejaVuSerif.ttf", "serif_bold": f"{DEJAVU}/DejaVuSerif-Bold.ttf",
    "mono_bold": f"{DEJAVU}/DejaVuSansMono-Bold.ttf",
    "sans_oblique": f"{MPL_TTF}/DejaVuSans-Oblique.ttf",
    "stix": f"{MPL_TTF}/STIXGeneral.ttf", "stix_bold": f"{MPL_TTF}/STIXGeneralBol.ttf",
    "stix_italic": f"{MPL_TTF}/STIXGeneralItalic.ttf", "cmss": f"{MPL_TTF}/cmss10.ttf",
}


def font(name, size):
    return ImageFont.truetype(FONTS[name], size)


# RGB. Colors are chosen away from the pack's flat red/blue/green/yellow on white.
C = {
    "red": (215, 40, 40), "orange": (245, 130, 20), "yellow": (240, 205, 25), "green": (30, 150, 60),
    "blue": (35, 85, 220), "purple": (150, 70, 210), "pink": (245, 110, 185), "cyan": (20, 200, 215),
    "brown": (125, 75, 35), "black": (20, 20, 20), "white": (250, 250, 250), "gray": (120, 120, 120),
    "navy": (22, 30, 72), "beige": (238, 228, 205), "lightgray": (212, 212, 212), "darkgray": (52, 52, 58),
    "skyblue": (150, 200, 240),
}
COLOR_KEYS = {"cyan": ["cyan", "turquoise", "teal", "aqua", "light blue"], "purple": ["purple", "violet"],
              "pink": ["pink", "magenta"]}


def ck(name):
    return COLOR_KEYS.get(name, [name])


# Video

def shape_points(kind, cx, cy, r):
    spec = {"square": (4, math.pi / 4, r * math.sqrt(2)), "diamond": (4, 0, r * 1.3),
            "triangle": (3, -math.pi / 2, r * 1.25), "pentagon": (5, -math.pi / 2, r * 1.1),
            "hexagon": (6, 0, r * 1.1)}
    if kind == "star":
        pts = [(cx + (r * 1.35 if i % 2 == 0 else r * 0.55) * math.cos(-math.pi / 2 + i * math.pi / 5),
                cy + (r * 1.35 if i % 2 == 0 else r * 0.55) * math.sin(-math.pi / 2 + i * math.pi / 5))
               for i in range(10)]
    else:
        n, a0, rr = spec[kind]
        pts = [(cx + rr * math.cos(a0 + 2 * math.pi * i / n), cy + rr * math.sin(a0 + 2 * math.pi * i / n))
               for i in range(n)]
    return np.array(pts)


def draw_shape(img, kind, cx, cy, r, color):
    if kind == "circle":
        cv2.circle(img, (int(round(cx * 16)), int(round(cy * 16))), int(round(r * 16)), color, -1,
                   cv2.LINE_AA, shift=4)
    else:
        pts = np.round(shape_points(kind, cx, cy, r) * 16).astype(np.int32)
        cv2.fillPoly(img, [pts], color, cv2.LINE_AA, shift=4)


def solid(name):
    return np.full((H, W, 3), C[name], np.uint8)


def gradient(c1, c2):
    a = np.linspace(0, 1, H)[:, None, None]
    return (np.array(c1) * (1 - a) + np.array(c2) * a).repeat(W, 1).astype(np.uint8)


def put_text(img, text, xy, fnt, fill, anchor="mm"):
    im = Image.fromarray(img)
    ImageDraw.Draw(im).text(xy, text, font=fnt, fill=fill, anchor=anchor)
    return np.array(im)


def scatter(rng, n, r, margin=40, box=(0, 0, W, H)):
    x0, y0, x1, y1 = box
    pts = []
    while len(pts) < n:
        p = (rng.uniform(x0 + margin + r, x1 - margin - r), rng.uniform(y0 + margin + r, y1 - margin - r))
        if all(math.dist(p, q) > 3.0 * r for q in pts):
            pts.append(p)
    return pts


def noise_post(sigma, seed):
    rng = np.random.default_rng(seed)

    def post(f, i):
        return np.clip(f.astype(np.int16) + rng.normal(0, sigma, f.shape).astype(np.int16), 0, 255).astype(np.uint8)
    return post


def write_video(path, dur, frame_fn, post=None):
    """mp4: H.264 like the pack. webm: VP8 with the muxer in live mode, which leaves
    out the duration and cues the way browser MediaRecorder output does."""
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-an"]
    if path.suffix == ".mp4":
        cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    else:
        cmd += ["-c:v", "libvpx", "-b:v", "1500k", "-pix_fmt", "yuv420p", "-f", "webm", "-live", "1"]
    p = subprocess.Popen(cmd + [str(path)], stdin=subprocess.PIPE)
    for i in range(int(round(dur * FPS))):
        f = frame_fn(i / FPS)
        if post:
            f = post(f, i)
        p.stdin.write(np.ascontiguousarray(f, np.uint8).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError(f"ffmpeg failed for {path}")


def t_appear(bg, shape, colors, count, interval, r, rng, start=0.6, tail=1.6):
    pos = scatter(rng, count, r)

    def f(t):
        img = bg.copy()
        k = 0 if t < start else min(count, int((t - start) // interval) + 1)
        for i in range(k):
            draw_shape(img, shape, *pos[i], r, C[colors[i % len(colors)]])
        return img
    return start + (count - 1) * interval + tail, f


def t_move(bg, shape, color, p0, p1, r, dur, hold=0.4):
    def f(t):
        a = float(np.clip((t - hold) / (dur - 2 * hold), 0, 1))
        img = bg.copy()
        draw_shape(img, shape, p0[0] + (p1[0] - p0[0]) * a, p0[1] + (p1[1] - p0[1]) * a, r, C[color])
        return img
    return dur, f


def t_order(bg, shape, colors, interval, r, rng, cumulative, start=0.5, tail=1.5):
    pos = scatter(rng, len(colors), r, margin=60) if cumulative else [(W / 2, H / 2)] * len(colors)

    def f(t):
        img = bg.copy()
        k = 0 if t < start else min(len(colors), int((t - start) // interval) + 1)
        shown = range(k) if cumulative else ([k - 1] if k else [])
        for i in shown:
            draw_shape(img, shape, *pos[i], r, C[colors[i]])
        return img
    return start + (len(colors) - 1) * interval + tail, f


def t_sign(bg, words, change_at, dur, board, ink, fnt):
    widths = [fnt.getbbox(w)[2] - fnt.getbbox(w)[0] for w in words]
    bw, bh = max(widths) + 70, fnt.size + 60
    x0, y0 = W // 2 - bw // 2, 120

    def f(t):
        img = bg.copy()
        cv2.rectangle(img, (W // 2 - 7, y0 + bh), (W // 2 + 7, H - 40), C["gray"], -1)
        cv2.rectangle(img, (x0, y0), (x0 + bw, y0 + bh), C[board], -1)
        cv2.rectangle(img, (x0 + 8, y0 + 8), (x0 + bw - 8, y0 + bh - 8), C[ink], 3)
        return put_text(img, words[0] if t < change_at else words[1], (W // 2, y0 + bh // 2), fnt, C[ink])
    return dur, f


def t_bar(bg, color, x, width, h0, h1, dur, floor_col, hold=0.5):
    base = H - 60

    def f(t):
        a = float(np.clip((t - hold) / (dur - 2 * hold), 0, 1))
        h = int(h0 + (h1 - h0) * a)
        img = bg.copy()
        cv2.line(img, (60, base), (W - 60, base), C[floor_col], 2)
        cv2.rectangle(img, (x - width // 2, base - h), (x + width // 2, base), C[color], -1)
        return img
    return dur, f


def t_pair(bg, shapes, colors, a0, a1, b0, b1, r, dur, hold=0.5):
    def f(t):
        a = float(np.clip((t - hold) / (dur - 2 * hold - 0.6), 0, 1))
        img = bg.copy()
        for s, c, p0, p1 in ((shapes[0], colors[0], a0, a1), (shapes[1], colors[1], b0, b1)):
            draw_shape(img, s, p0[0] + (p1[0] - p0[0]) * a, p0[1] + (p1[1] - p0[1]) * a, r, C[c])
        return img
    return dur, f


def t_numbers(bg, seq, interval, fnt, ink, start=0.3, tail=1.2):
    def f(t):
        k = min(len(seq) - 1, int(max(0.0, t - start) // interval))
        img = bg.copy()
        return img if t < start else put_text(img, str(seq[k]), (W // 2, H // 2), fnt, C[ink])
    return start + (len(seq) - 1) * interval + tail, f


def t_appear_vanish(bg, shape, colors, n_in, n_out, interval, r, rng, start=0.5, hold=1.2, tail=1.6):
    pos = scatter(rng, n_in, r)
    gone_order = list(rng.permutation(n_in)[:n_out])
    t_out = start + (n_in - 1) * interval + hold

    def f(t):
        img = bg.copy()
        k = 0 if t < start else min(n_in, int((t - start) // interval) + 1)
        g = 0 if t < t_out else min(n_out, int((t - t_out) // interval) + 1)
        gone = set(gone_order[:g])
        for i in range(k):
            if i not in gone:
                draw_shape(img, shape, *pos[i], r, C[colors[i % len(colors)]])
        return img
    return t_out + (n_out - 1) * interval + tail, f


def bounce_height(t, n, h0, decay, t0):
    if t < t0:
        return h0 * (1 - (t / t0) ** 2)
    t -= t0
    for i in range(1, n + 1):
        hi = h0 * decay ** i
        ti = t0 * math.sqrt(hi / h0)
        span = 2 * ti if i < n else ti
        if t < span:
            return hi * (1 - ((t - ti) / ti) ** 2)
        t -= span
    return h0 * decay ** n


def t_bounce(bg, color, n, h0, decay, t0, r, floor_col, x_speed=0.0, lead=0.4):
    floor = H - 50
    total = t0 + sum(2 * t0 * math.sqrt(decay ** i) for i in range(1, n)) + t0 * math.sqrt(decay ** n)

    def f(t):
        img = bg.copy()
        cv2.line(img, (0, floor), (W, floor), C[floor_col], 3)
        tt = max(0.0, t - lead)
        y = floor - r - bounce_height(min(tt, total - 1e-6), n, h0, decay, t0)
        draw_shape(img, "circle", 120 + x_speed * tt, y, r, C[color])
        return img
    return lead + total, f


def t_background(colors, seg, shape=None):
    def f(t):
        img = solid(colors[min(len(colors) - 1, int(t // seg))])
        if shape:
            draw_shape(img, shape[0], W / 2, H / 2, 40, C[shape[1]])
        return img
    return seg * len(colors), f


def make_videos():
    d = OUT / "video"
    d.mkdir(parents=True, exist_ok=True)
    big = font("serif_bold", 190)
    specs = []

    def v(iid, ext, template, built, question, ref, key, params, difficulty, hard=None, post=None):
        specs.append((iid, ext, template, built, question, ref, key, params, difficulty, hard, post))

    rng = np.random.default_rng(101)
    cols = ["orange", "pink", "cyan", "white", "yellow", "green"]
    v("h_vid_001", "mp4", 1, t_appear(solid("navy"), "triangle", cols, 6, 0.8, 28, rng),
      "How many shapes appear in this video?", "6 triangles appear one at a time.", [["#6"]],
      {"count": 6, "shape": "triangle", "colors": cols, "interval": 0.8, "background": "navy", "radius": 28}, "medium")
    rng = np.random.default_rng(102)
    v("h_vid_002", "mp4", 1, t_appear(solid("lightgray"), "star", ["pink", "purple"], 3, 1.4, 45, rng),
      "How many shapes show up, one after another?", "3 stars appear one at a time.", [["#3"]],
      {"count": 3, "shape": "star", "colors": ["pink", "purple"], "interval": 1.4, "background": "lightgray",
       "radius": 45}, "easy")
    v("h_vid_003", "mp4", 2, t_move(solid("beige"), "hexagon", "purple", (540, 240), (100, 240), 38, 5.5),
      "Which direction does the hexagon move?", "The purple hexagon moves to the left.", [["left"]],
      {"shape": "hexagon", "color": "purple", "direction": "left", "background": "beige"}, "easy")
    v("h_vid_004", "mp4", 2, t_move(solid("darkgray"), "triangle", "orange", (320, 70), (320, 410), 30, 3.5),
      "Which way is the triangle moving?", "The orange triangle moves down.", [["down"]],
      {"shape": "triangle", "color": "orange", "direction": "down", "background": "darkgray", "duration": 3.5},
      "easy")
    up_right = ["up and to the right", "upper right", "upper-right", "top right", "top-right", "up-right",
                "up and right", "northeast", "north-east", "right and up", "up to the right", "upward and to the right",
                "upwards and to the right"]
    v("h_vid_005", "webm", 2, t_move(solid("white"), "diamond", "cyan", (90, 400), (550, 80), 30, 5.0),
      "In which direction does the diamond move?",
      "The cyan diamond moves diagonally up and to the right (from the bottom left to the top right).", [up_right],
      {"shape": "diamond", "color": "cyan", "direction": "up-right diagonal", "background": "white"}, "medium")
    rng = np.random.default_rng(106)
    order4 = ["purple", "orange", "white", "cyan"]
    v("h_vid_006", "mp4", 3, t_order(solid("darkgray"), "triangle", order4, 1.1, 40, rng, cumulative=True),
      "What color appears first, and what color appears last?",
      "A purple triangle appears first, then orange, then white, and cyan appears last.",
      [ck("purple"), ck("cyan")],
      {"shape": "triangle", "colors": order4, "interval": 1.1, "layout": "cumulative, random positions",
       "background": "darkgray"}, "hard")
    order3 = ["brown", "pink", "black"]
    v("h_vid_007", "mp4", 3, t_order(solid("beige"), "star", order3, 1.5, 70, None, cumulative=False),
      "Which color shows up first and which shows up last?",
      "A brown star appears first, then pink, and black appears last.", [["brown"], ["black"]],
      {"shape": "star", "colors": order3, "interval": 1.5, "layout": "one at a time in the center",
       "background": "beige"}, "medium")
    v("h_vid_008", "mp4", 4, t_sign(solid("skyblue"), ["ENTER", "EXIT"], 3.0, 6.5, "green", "white",
                                    font("sans_bold", 72)),
      "What does the sign say at the start and at the end?",
      'The sign says "ENTER" at the start and "EXIT" at the end.', [["enter"], ["exit"]],
      {"words": ["ENTER", "EXIT"], "change_at": 3.0, "board": "green", "ink": "white", "font": "DejaVu Sans Bold"},
      "medium")
    v("h_vid_009", "mp4", 4, t_sign(solid("lightgray"), ["SALE", "SOLD OUT"], 4.5, 8.0, "yellow", "black",
                                    font("serif_bold", 64)),
      "What word is on the sign at the beginning, and what does it change to?",
      'The sign says "SALE" at the beginning and changes to "SOLD OUT".', [["sale"], ["sold out"]],
      {"words": ["SALE", "SOLD OUT"], "change_at": 4.5, "board": "yellow", "ink": "black",
       "font": "DejaVu Serif Bold"}, "medium")
    v("h_vid_010", "mp4", 5, t_bar(solid("navy"), "orange", 320, 70, 330, 60, 5.0, "white"),
      "Does the bar get taller or shorter?", "The bar gets shorter.",
      [["shorter", "shrink", "decreas", "smaller", "lower"]],
      {"bar": "shorter", "bar_color": "orange", "background": "navy", "height_px": [330, 60]}, "easy")
    v("h_vid_011", "mp4", 5, t_bar(solid("white"), "purple", 200, 50, 100, 260, 7.0, "black"),
      "Is the bar growing or shrinking?", "The bar is growing (it gets taller).",
      [["taller", "grows", "growing", "increas", "higher", "rising", "rises"]],
      {"bar": "taller", "bar_color": "purple", "background": "white", "height_px": [100, 260], "x": 200}, "easy")
    v("h_vid_012", "mp4", 6, t_pair(solid("white"), ["triangle", "star"], ["orange", "purple"],
                                    (283, 240), (90, 240), (357, 240), (550, 240), 32, 5.5),
      "What happens to the two shapes?",
      "The two shapes start next to each other and move apart, away from each other.",
      [["apart", "away from each other", "separat", "farther", "further from", "move away", "diverg"]],
      {"shapes": ["triangle", "star"], "colors": ["orange", "purple"], "motion": "apart (horizontal)",
       "background": "white"}, "medium")
    v("h_vid_013", "mp4", 6, t_pair(solid("lightgray"), ["hexagon", "circle"], ["cyan", "brown"],
                                    (320, 60), (320, 205), (320, 420), (320, 271), 34, 6.0),
      "Do the two shapes move toward each other or away from each other?",
      "They move toward each other (one from the top, one from the bottom) until they touch.",
      [["toward each other", "towards each other", "meet", "touch", "collide", "closer", "come together",
        "move together"]],
      {"shapes": ["hexagon", "circle"], "colors": ["cyan", "brown"], "motion": "together (vertical)",
       "background": "lightgray"}, "medium")
    v("h_vid_014", "webm", 7, t_numbers(gradient(C["purple"], C["navy"]), list(range(1, 7)), 1.0, big, "white"),
      "What number is shown last?", "It counts up from 1 to 6; the last number shown is 6.",
      [["#6", "is 6", "to 6", "at 6", "on 6", "is six"]],
      {"numbers": list(range(1, 7)), "interval": 1.0, "direction": "count up", "font": "DejaVu Serif Bold",
       "background": "purple to navy gradient"}, "easy")
    v("h_vid_015", "mp4", 7, t_numbers(solid("beige"), list(range(9, 2, -1)), 0.8, font("mono_bold", 200), "red"),
      "What is the final number displayed?", "A countdown from 9 to 3; the final number displayed is 3.",
      [["#3", "is 3", "to 3", "at 3", "on 3", "is three"]],
      {"numbers": list(range(9, 2, -1)), "interval": 0.8, "direction": "count down, stops at 3",
       "font": "DejaVu Sans Mono Bold", "background": "beige"}, "medium")
    rng = np.random.default_rng(116)
    v("h_vid_016", "mp4", 8, t_appear_vanish(solid("darkgray"), "hexagon", ["cyan", "orange"], 6, 4, 0.7, 30, rng),
      "Some shapes appear and then a few vanish. How many remain at the end?",
      "6 hexagons appear, 4 disappear, so 2 are left at the end.",
      [["#2", "2 remain", "2 left", "2 are left", "2 shapes", "2 hexagons", "two remain", "two left",
        "two are left", "two shapes", "two hexagons"]],
      {"shape": "hexagon", "appear": 6, "disappear": 4, "colors": ["cyan", "orange"], "interval": 0.7,
       "background": "darkgray"}, "hard")
    rng = np.random.default_rng(117)
    v("h_vid_017", "mp4", 8, t_appear_vanish(solid("beige"), "star", ["purple", "pink", "orange"], 7, 3, 0.6, 26, rng),
      "Several shapes appear and then some disappear. How many shapes are left at the end?",
      "7 stars appear, 3 disappear, so 4 are left at the end.",
      [["#4", "4 remain", "4 left", "4 are left", "4 shapes", "4 stars", "four remain", "four left",
        "four are left", "four shapes", "four stars"]],
      {"shape": "star", "appear": 7, "disappear": 3, "colors": ["purple", "pink", "orange"], "interval": 0.6,
       "background": "beige"}, "hard")
    v("h_vid_018", "mp4", 9, t_bounce(solid("navy"), "pink", 1, 330, 0.55, 1.1, 26, "white", x_speed=40, lead=1.2),
      "How many times does the ball bounce?", "The ball bounces once (1 time).",
      [["#1", "once", "one time", "1 time"]],
      {"bounces": 1, "color": "pink", "decay": 0.55, "background": "navy", "drift_px_s": 40}, "medium")
    v("h_vid_019", "mp4", 9, t_bounce(solid("white"), "orange", 5, 200, 1.0, 0.45, 18, "black"),
      "How many bounces does the ball make?", "The ball bounces 5 times.", [["#5", "five"]],
      {"bounces": 5, "color": "orange", "decay": 1.0, "fall_s": 0.45, "background": "white", "radius": 18}, "hard")
    v("h_vid_020", "webm", 10, t_background(["green", "purple", "orange"], 2.5, ("circle", "white")),
      "What color is the background at the end?", "The background ends orange.", [["orange"]],
      {"colors": ["green", "purple", "orange"], "segment_s": 2.5, "distractor": "white circle"}, "easy")
    v("h_vid_021", "mp4", 10, t_background(["pink", "cyan", "black"], 2.0, ("square", "yellow")),
      "What color is the background at the beginning of the video?", "The background starts pink.", [ck("pink")],
      {"colors": ["pink", "cyan", "black"], "segment_s": 2.0, "distractor": "yellow square",
       "asked": "start color"}, "medium")
    rng = np.random.default_rng(122)
    v("h_vid_022", "mp4", 1, t_appear(solid("gray"), "circle", ["white", "black"], 5, 1.0, 13, rng),
      "How many shapes appear in this video?", "5 small circles appear one at a time.", [["#5"]],
      {"count": 5, "shape": "circle", "colors": ["white", "black"], "interval": 1.0, "background": "gray",
       "radius": 13}, "hard", hard="gaussian noise sigma 28 per pixel per frame, small objects (radius 13 px)",
      post=noise_post(28, 222))
    v("h_vid_023", "mp4", 9, t_bounce(gradient(C["skyblue"], (20, 80, 30)), "yellow", 2, 280, 0.7, 0.85, 12, "black",
                                      x_speed=55),
      "How many times does the ball bounce?", "The ball bounces 2 times.", [["#2", "twice", "two times"]],
      {"bounces": 2, "color": "yellow", "decay": 0.7, "radius": 12, "background": "sky blue to dark green gradient"},
      "hard", hard="vertical gradient background, small ball (radius 12 px)")
    down_left = ["down and to the left", "lower left", "lower-left", "bottom left", "bottom-left", "down-left",
                 "down and left", "southwest", "south-west", "left and down", "down to the left",
                 "downward and to the left", "downwards and to the left"]
    v("h_vid_024", "mp4", 2, t_move(solid("white"), "circle", "black", (560, 60), (80, 420), 6, 6.0),
      "Which direction does the dot move?",
      "The small black dot moves diagonally down and to the left (from the top right to the bottom left).",
      [down_left],
      {"shape": "circle", "color": "black", "direction": "down-left diagonal", "radius": 6, "background": "white"},
      "hard", hard="tiny object (radius 6 px) plus gaussian noise sigma 12", post=noise_post(12, 224))

    names = {1: "shapes appear one at a time", 2: "shape moves in one direction", 3: "colors in order",
             4: "sign text changes", 5: "bar grows or shrinks", 6: "two shapes move together or apart",
             7: "count up or down", 8: "shapes appear then some disappear", 9: "ball bounces",
             10: "background color changes"}
    for iid, ext, tpl, (dur, fn), q, ref, key, params, diff, hard, post in specs:
        path = d / f"{iid}.{ext}"
        write_video(path, dur, fn, post)
        codec = "H.264 MP4" if ext == "mp4" else "VP8 WebM (live muxer, no duration in header)"
        add(iid, "video", f"video/{iid}.{ext}", q, ref, key, difficulty=diff,
            source=f"synthetic, family T{tpl} ({names[tpl]}), held-out style", **SYN,
            transform=f"synthetic clip {dur:.1f} s, {W}x{H}, {FPS} fps, {codec}, no audio"
                      + (f"; harder: {hard}" if hard else ""),
            source_ids={"dataset": "synthetic-heldout", "templates": [tpl]}, params={"template": [tpl], **params})


# Text documents

DOCS = {
    "h_txt_doc_01": ("Safety Notice: Chemistry Teaching Lab, Room 214", """\
Building C, Chemistry Teaching Lab, Room 214. Effective 3 March 2026. This notice covers Room 214 only. Other rooms in Building C post their own rules.

Personal protective equipment
Everyone who enters the lab while chemicals are out must wear splash goggles, a buttoned lab coat and closed-toe shoes. Contact lenses are allowed only under goggles. Nitrile gloves are provided at the bench. Change gloves every 30 minutes, or straight away if they are torn or splashed. Do not touch door handles, keyboards or phones while wearing gloves.

Food, drink and personal items
No food, drink, gum or cosmetics in the lab. Bags and coats go in the lockers in the corridor, not under the benches. Water bottles must stay in your bag.

Eyewash station and safety shower
The eyewash station is next to the sink by the north door. The safety shower is in the southeast corner. If a chemical gets in your eyes, hold your eyelids open and flush for 15 minutes, then report it to the lab manager. Test the eyewash every Monday and write the date on the tag.

Fire
A carbon dioxide extinguisher hangs beside the west exit. A fire blanket is mounted on the wall near the fume hoods. If the alarm sounds, turn off gas taps if it is safe to do so, leave by the nearest exit and meet at the flagpole in front of Building C.

Spills
For spills under 100 mL, use the yellow spill kit under the main sink and put the used absorbent in a sealed bag. For any spill larger than 100 mL, or any spill of mercury, leave the room, close the door and call campus safety on extension 4477.

Chemical waste
Never pour solvents down the sink. Halogenated solvent waste goes in the green carboy in fume hood 2. Non-halogenated solvent waste goes in the red carboy in fume hood 3. Broken glass goes in the cardboard glass box, never in the regular trash. Label every waste container with the date and your initials.

Gas cylinders
Gas cylinders must be chained to the wall at all times. Close the main valve at the end of each session.

Hours and supervision
The lab is open Monday to Friday, 8 am to 6 pm. Work outside these hours needs written approval from the lab manager, and a second person must be present in the room. Nobody may work alone with chemicals at any time.

Contacts
Lab manager: Dr. Helen Okafor, office C118, extension 4410.
Campus safety (24 hours): extension 4477.
""", [
        ("How long should you flush your eyes at the eyewash station?", "15 minutes.", True,
         [["15 minutes", "fifteen minutes", "15 min"]]),
        ("Which container gets halogenated solvent waste?", "The green carboy in fume hood 2.", True, [["green"]]),
        ("What extension do you call for a spill larger than 100 mL?", "Extension 4477 (campus safety).", True,
         [["4477"]]),
        ("Who is the lab manager?", "Dr. Helen Okafor.", True, [["okafor"]]),
        ("Which container gets radioactive waste?", "The document does not say.", False, ["REFUSE"]),
        ("Who is the lab manager for Room 305?", "The document does not say.", False, ["REFUSE"]),
    ]),
    "h_txt_doc_02": ("Route 12 Harbor Line: How to Read the Weekday Timetable", """\
Route 12, the Harbor Line, runs between Eastgate Terminal and Lighthouse Point. Buses stop at Market Square, Riverside Hospital and College Street on the way. This guide explains the weekday timetable for Route 12 only. Each route has its own guide.

When the buses run
On weekdays the first Route 12 bus leaves Eastgate Terminal at 5:45 am and the last one leaves at 11:10 pm. During the morning peak, from 7 am to 9 am, a bus leaves every 15 minutes. During the evening peak, from 4 pm to 6 pm, a bus leaves every 12 minutes. At all other times buses run every 30 minutes. Departure times from Lighthouse Point are posted on the timetable at that stop.

On Saturdays service starts at 7:00 am and buses run every 40 minutes. There is no Sunday service on Route 12.

How long the trip takes
A full trip from Eastgate Terminal to Lighthouse Point takes 48 minutes. Market Square is about 10 minutes from Eastgate, and Riverside Hospital about 22 minutes. Allow extra time in the evening peak, when traffic on Bridge Road can add up to 10 minutes.

Reading the table
Each column of the printed timetable is one bus. Times in bold are afternoon and evening departures. A small h next to a time means the bus also enters the Riverside Hospital forecourt, which adds about 3 minutes. A small x means the bus does not stop at College Street.

Fares
An adult single fare is $2.25. Seniors and students with a valid card pay $1.10. Children under 6 ride free with a paying adult. A day pass costs $6.00 and is valid on all city routes until 3 am the next morning. Drivers do not give change, so have the exact fare ready or tap a contactless card.

Bikes and accessibility
Every Route 12 bus has a front rack that holds two bikes. All buses have a low floor and a ramp. Ask the driver if you need the ramp deployed.

Temporary detour
From 1 December to 20 December the College Street stop is closed for road works. Use the temporary stop on Elm Road, about 150 metres north, instead.

Lost property
Items left on Route 12 buses are kept at Eastgate Terminal for 30 days. Call 555 0142 between 9 am and 5 pm on weekdays.
""", [
        ("How often does a Route 12 bus leave during the morning peak?", "Every 15 minutes.", True,
         [["15 minutes", "fifteen minutes", "15 min"]]),
        ("How much is an adult single fare?", "$2.25.", True, [["2.25"]]),
        ("How long does a full trip from Eastgate Terminal to Lighthouse Point take?", "48 minutes.", True,
         [["48"]]),
        ("Which temporary stop replaces College Street during the detour?", "The temporary stop on Elm Road.", True,
         [["elm road"]]),
        ("How much is an adult single fare on Route 14?", "The document does not say.", False, ["REFUSE"]),
        ("What time does the first bus leave Lighthouse Point on weekdays?", "The document does not say.", False,
         ["REFUSE"]),
    ]),
    "h_txt_doc_03": ("Brewmaster K7 Coffee Maker, Section 4: Cleaning and Descaling", """\
This section applies to the Brewmaster K7 12-cup drip coffee maker. Read the safety instructions in Section 1 before cleaning the appliance.

4.1 Daily cleaning
Unplug the coffee maker and let it cool for at least 15 minutes. Remove the filter basket and the carafe. The carafe and its lid can go on the top rack of a dishwasher. The filter basket should be washed by hand in warm soapy water. Wipe the warming plate with a damp cloth only. The warming plate and the base are not dishwasher safe and must never be put in water.

4.2 When to descale
Minerals in tap water build up inside the heater over time. Descale the K7 every 40 brew cycles, or sooner if the DESCALE light blinks orange. In hard water areas, descale every 20 brew cycles.

4.3 How to descale
1. Empty the carafe and the filter basket.
2. Mix a descaling solution of 1 part white vinegar to 2 parts water.
3. Pour the solution into the water tank up to the 10-cup line.
4. Place the empty carafe on the warming plate.
5. Press and hold the CLEAN button for 3 seconds until the light turns steady green.
6. The descaling cycle takes about 35 minutes. Do not switch the machine off during the cycle.
7. When the CLEAN light goes out, empty the carafe and run 2 full cycles with fresh water only.

4.4 Auto shut-off
After brewing, the warming plate stays on for 2 hours and then switches off automatically. To keep coffee hot for longer, pour it into an insulated flask.

4.5 Error codes
E1: The water tank is empty. Fill the tank and press START.
E2: The heater is overheating. Unplug the machine and wait 20 minutes before using it again.
E4: A temperature sensor has failed. Stop using the machine and contact customer support.
If any other code appears, unplug the machine for 1 minute and plug it back in.

4.6 Warranty note
The K7 has a 2-year limited warranty. Damage caused by descaling with chemicals other than white vinegar or the Brewmaster descaler is not covered.
""", [
        ("What ratio of white vinegar to water does the manual recommend for descaling?",
         "1 part white vinegar to 2 parts water.", True,
         [["1 part", "one part", "1:2", "1 to 2", "one to two", "2 parts water", "two parts water"]]),
        ("What does error code E2 mean?", "The heater is overheating; unplug and wait 20 minutes.", True,
         [["overheat"]]),
        ("How long does the descaling cycle take?", "About 35 minutes.", True,
         [["35 min", "thirty-five", "thirty five"]]),
        ("After how many hours does the warming plate switch off automatically?", "After 2 hours.", True,
         [["2 hours", "two hours", "#2"]]),
        ("What does error code E3 mean?", "The document does not say.", False, ["REFUSE"]),
        ("What ratio of citric acid to water does the manual recommend for descaling?", "The document does not say.",
         False, ["REFUSE"]),
    ]),
}


def wrap_doc(title, body, width=90):
    lines = [title, ""]
    for para in body.split("\n"):
        lines += textwrap.wrap(para, width) or [""]
    return lines


def write_pdf(path, title, lines, per_page=46):
    """matplotlib's PDF backend with TrueType embedding (fonttype 42) keeps the text extractable."""
    matplotlib.rcParams["pdf.fonttype"] = 42
    pages = [lines[i:i + per_page] for i in range(0, len(lines), per_page)]
    with PdfPages(path, metadata={"Title": title}) as pdf:
        for pi, page in enumerate(pages):
            fig = plt.figure(figsize=(8.5, 11))
            y = 0.93
            for li, line in enumerate(page):
                is_title = pi == 0 and li == 0
                fig.text(0.08, y, line, fontsize=14 if is_title else 10.5, family="DejaVu Sans",
                         weight="bold" if is_title else "normal", parse_math=False)
                y -= 0.028 if is_title else 0.0185
            fig.text(0.5, 0.04, f"Page {pi + 1} of {len(pages)}", fontsize=8, ha="center", family="DejaVu Sans")
            pdf.savefig(fig)
            plt.close(fig)
    return len(pages)


def make_text():
    d = OUT / "text"
    d.mkdir(parents=True, exist_ok=True)
    n = 0
    for doc, (title, body, qs) in DOCS.items():
        (d / f"{doc}.txt").write_text(title + "\n\n" + body, encoding="utf-8")
        pages = write_pdf(d / f"{doc}.pdf", title, wrap_doc(title, body))
        for q, ref, answerable, key in qs:
            n += 1
            iid = f"h_txt_{n:03d}"
            add(iid, "text", f"text/{doc}.txt", q, ref, key, answerable=answerable,
                difficulty="easy" if answerable else "hard", source=f"written for the held-out set, document {doc}",
                **SYN, transform=("original question" if answerable else
                                  "unanswerable: reuses the wording of an answerable question with one detail changed")
                + f"; PDF has {pages} page(s) with embedded text",
                source_ids={"dataset": "heldout-docs", "doc": doc})


# Images

def rotated_layer(layer, angle):
    return layer.rotate(angle, resample=Image.BICUBIC, expand=True)


def paste_center(bg, layer, cx, cy):
    bg.paste(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)), layer)


def textured(size, base, rng, amp=10, blur=2):
    arr = np.clip(np.array(base, float) + rng.normal(0, amp, (size[1], size[0], 1)), 0, 255).astype(np.uint8)
    return Image.fromarray(arr).filter(ImageFilter.GaussianBlur(blur)).convert("RGB")


def sign_layer(lines, fonts, board, ink, pad=40, gap=16, border=None, radius=24):
    sizes = [f.getbbox(t) for t, f in zip(lines, fonts)]
    w = max(b[2] - b[0] for b in sizes) + 2 * pad
    h = sum(b[3] - b[1] for b in sizes) + gap * (len(lines) - 1) + 2 * pad
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.rounded_rectangle((0, 0, w - 1, h - 1), radius, fill=board + (255,))
    if border:
        dr.rounded_rectangle((8, 8, w - 9, h - 9), radius - 6, outline=border + (255,), width=4)
    y = pad
    for (t, f), b in zip(zip(lines, fonts), sizes):
        dr.text((w / 2, y - b[1]), t, font=f, fill=ink + (255,), anchor="ma")
        y += b[3] - b[1] + gap
    return im


def img_counting_apples(rng, n):
    im = textured((960, 720), (150, 100, 60), rng, 18, 1)
    dr = ImageDraw.Draw(im)
    for y in range(0, 720, 60):
        dr.line((0, y + rng.integers(-3, 3), 960, y), fill=(120, 80, 45), width=3)
    for x, y in scatter(rng, n, 55, margin=20, box=(0, 0, 960, 720)):
        r = 55 + rng.integers(-6, 6)
        dr.ellipse((x - r, y - r * 0.92, x + r, y + r * 0.92), fill=(200 + rng.integers(-20, 20), 30, 35))
        dr.ellipse((x - r * 0.55, y - r * 0.6, x - r * 0.15, y - r * 0.2), fill=(235, 110, 110))
        dr.line((x, y - r * 0.9, x + 6, y - r * 1.3), fill=(70, 40, 15), width=6)
        dr.ellipse((x + 8, y - r * 1.35, x + 40, y - r * 1.1), fill=(40, 140, 40))
    return im


def img_balloons(rng, n):
    im = Image.fromarray(gradient((170, 215, 245), (240, 248, 255))).resize((900, 700))
    dr = ImageDraw.Draw(im)
    cols = [(230, 50, 60), (250, 170, 30), (60, 120, 220), (150, 70, 200), (40, 170, 90)]
    for i, (x, y) in enumerate(scatter(rng, n, 70, margin=30, box=(0, 0, 900, 470))):
        dr.line((x, y + 85, x + rng.integers(-40, 40), 690), fill=(90, 90, 90), width=2)
        dr.ellipse((x - 62, y - 80, x + 62, y + 80), fill=cols[i % len(cols)])
        dr.polygon([(x - 8, y + 92), (x + 8, y + 92), (x, y + 78)], fill=cols[i % len(cols)])
        dr.ellipse((x - 35, y - 55, x - 15, y - 20), fill=(255, 255, 255))
    return im


def img_mixed_shapes(rng):
    im = Image.new("RGB", (900, 700), (245, 245, 240))
    dr = ImageDraw.Draw(im)
    kinds = [("square", (40, 80, 210))] * 5 + [("square", (210, 40, 40))] * 3 + [("circle", (40, 80, 210))] * 3
    for (k, c), (x, y) in zip(kinds, scatter(rng, len(kinds), 45, margin=20, box=(0, 0, 900, 700))):
        if k == "square":
            dr.rectangle((x - 40, y - 40, x + 40, y + 40), fill=c)
        else:
            dr.ellipse((x - 42, y - 42, x + 42, y + 42), fill=c)
    return im


def make_images():
    d = OUT / "image"
    d.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(301)
    out = []

    im = textured((960, 720), (225, 218, 200), rng)
    paste_center(im, rotated_layer(sign_layer(["EMERGENCY", "EXIT"], [font("sans_bold", 78)] * 2, (0, 135, 70),
                                              (255, 255, 255), border=(255, 255, 255)), 4), 480, 330)
    out.append((im, "What does this sign say?", "EMERGENCY EXIT", [["emergency exit"]],
                "green exit sign, DejaVu Sans Bold, rotated 4 degrees, textured wall", "easy"))

    im = textured((900, 600), (192, 197, 208), rng, 6, 3)
    paste_center(im, sign_layer(["KEEP", "REFRIGERATED"], [font("stix_bold", 64)] * 2, (196, 201, 212),
                                (165, 170, 182), pad=30), 450, 300)
    out.append((im, "What does the label say?", "KEEP REFRIGERATED", [["keep refrigerated"]],
                "low contrast: gray text on a gray carton (about 30 levels apart), STIX Bold", "hard"))

    im = Image.fromarray(gradient((120, 175, 235), (215, 235, 250))).resize((960, 720))
    dr = ImageDraw.Draw(im)
    for _ in range(14):
        x, y, r = rng.integers(0, 960), rng.integers(450, 720), rng.integers(60, 130)
        dr.ellipse((x - r, y - r, x + r, y + r), fill=(40 + rng.integers(0, 40), 110 + rng.integers(0, 40), 50))
    im = im.filter(ImageFilter.GaussianBlur(4))
    ImageDraw.Draw(im).rectangle((468, 330, 492, 720), fill=(110, 110, 115))
    paste_center(im, rotated_layer(sign_layer(["Maple Avenue"], [font("cmss", 80)], (0, 110, 60), (255, 255, 255),
                                              pad=28, border=(255, 255, 255), radius=10), -7), 480, 290)
    out.append((im, "What is the name of the street on this sign?", "Maple Avenue", [["maple"]],
                "street sign, Computer Modern Sans, rotated -7 degrees, blurred trees", "medium"))

    im = textured((960, 720), (196, 150, 100), rng, 12, 1)
    dr = ImageDraw.Draw(im)
    dr.text((480, 250), "FRAGILE", font=font("sans_bold", 120), fill=(200, 30, 30), anchor="mm")
    dr.text((480, 420), "THIS SIDE UP", font=font("sans", 56), fill=(25, 25, 25), anchor="mm")
    dr.polygon([(480, 480), (440, 540), (520, 540)], fill=(25, 25, 25))
    dr.rectangle((468, 540, 492, 620), fill=(25, 25, 25))
    out.append((im, "What is written on the box?", "FRAGILE, THIS SIDE UP", [["fragile"], ["this side up"]],
                "cardboard texture, two text sizes", "easy"))

    im = textured((900, 700), (30, 90, 45), rng, 15, 2)
    tag = sign_layer(["Organic Apples", "$3.49 / lb"], [font("stix", 54), font("stix_bold", 96)], (252, 252, 245),
                     (20, 20, 20), radius=12)
    ImageDraw.Draw(tag).ellipse((20, 20, 44, 44), fill=(30, 90, 45, 255))
    paste_center(im, rotated_layer(tag, 3), 450, 350)
    out.append((im, "How much do the apples cost?", "$3.49 per pound", [["3.49"]],
                "price tag, STIX, rotated 3 degrees", "easy"))

    im = textured((900, 700), (235, 235, 235), rng, 5, 2)
    tag = sign_layer(["WAS $24.99", "NOW $17.50"], [font("sans", 48), font("sans_bold", 92)], (250, 215, 40),
                     (20, 20, 20), radius=8)
    ImageDraw.Draw(tag).line((30, 68, tag.width - 30, 68), fill=(20, 20, 20, 255), width=4)
    paste_center(im, rotated_layer(tag, -2), 450, 350)
    out.append((im, "What is the sale price?", "$17.50 (it was $24.99)", [["17.5"]],
                "sale tag with a struck-out old price, rotated -2 degrees", "medium"))

    im = textured((960, 720), (230, 230, 225), rng, 6, 2)
    dr = ImageDraw.Draw(im)
    dr.rounded_rectangle((220, 60, 740, 700), 40, fill=(150, 80, 20))
    dr.rectangle((380, 20, 580, 70), fill=(240, 240, 240))
    lab = ["IBUPROFEN TABLETS 200 mg", "", "Directions: adults and children 12 years",
           "and over, take 1 tablet every 4 to 6 hours", "while symptoms persist. If pain does not",
           "respond, 2 tablets may be used.", "", "Do not take more than 6 tablets in 24 hours."]
    dr.rectangle((250, 200, 710, 560), fill=(252, 252, 250))
    y = 222
    for i, t in enumerate(lab):
        dr.text((480, y), t, font=font("sans_bold", 26) if i == 0 else font("sans", 19), fill=(20, 20, 20),
                anchor="ma")
        y += 40 if i == 0 else 30
    out.append((im, "What is the most tablets you can take in 24 hours?", "6 tablets in 24 hours.",
                [["#6", "6 tablet", "six tablet", "6 in 24", "six in 24"]],
                "medicine bottle label, small print (19 px)", "medium"))

    im = textured((960, 720), (225, 232, 240), rng, 6, 2)
    lab = sign_layer(["AMOXICILLIN 500 mg CAPSULES", "Take 1 capsule by mouth 3 times daily",
                      "for 7 days. Finish all of this medicine.", "Rx 0041729   Qty 21   Refills 0"],
                     [font("serif_bold", 34), font("serif", 26), font("serif", 26), font("mono_bold", 22)],
                     (255, 255, 255), (15, 15, 60), pad=30, gap=14, radius=6)
    paste_center(im, rotated_layer(lab, 1.5), 480, 360)
    out.append((im, "How often should this medicine be taken, and for how long?",
                "1 capsule 3 times daily for 7 days.",
                [["3 times", "three times", "every 8 hours"], ["7 days", "seven days"]],
                "pharmacy label, DejaVu Serif, rotated 1.5 degrees", "medium"))

    out.append((img_counting_apples(rng, 7), "How many apples are in this image?", "There are 7 apples.", [["#7"]],
                "drawn apples on a wood-grain table", "easy"))
    out.append((img_balloons(rng, 4), "How many balloons are there?", "There are 4 balloons.", [["#4"]],
                "drawn balloons with strings on a sky gradient", "easy"))
    out.append((img_mixed_shapes(rng), "How many blue squares are in this image?",
                "There are 5 blue squares (plus 3 red squares and 3 blue circles).", [["#5"]],
                "distractors: 3 red squares and 3 blue circles", "hard"))

    im = textured((1100, 800), (120, 95, 70), rng, 14, 1)
    note = Image.new("RGBA", (330, 300), (250, 238, 140, 255))
    nd = ImageDraw.Draw(note)
    for i, t in enumerate(["Meeting moved", "to Room 12B,", "3:30 PM"]):
        nd.text((24, 40 + i * 52), t, font=font("sans_oblique", 34), fill=(165, 160, 120, 255))
    paste_center(im, rotated_layer(note, 9), 760, 520)
    ImageDraw.Draw(im).rectangle((120, 120, 520, 420), fill=(240, 240, 235))
    out.append((im, "Where was the meeting moved to?", "Room 12B (at 3:30 PM).", [["12b", "12 b"]],
                "sticky note: small oblique text, low contrast, rotated 9 degrees, off-center", "hard"))

    for n, (im, q, ref, key, how, diff) in enumerate(out, 1):
        iid = f"h_img_{n:03d}"
        im.convert("RGB").save(d / f"{iid}.jpg", quality=90)
        add(iid, "image", f"image/{iid}.jpg", q, ref, key, difficulty=diff,
            source="synthetic, rendered with PIL (not a photo)", **SYN,
            transform=f"PIL render, {im.width}x{im.height}, JPEG quality 90; {how}",
            source_ids={"dataset": "synthetic-heldout"})


# Code

CODE = [
    ("count_vowel_words", "sentence",
     """Return how many words in sentence start and end with a vowel (a, e, i, o, u),
    ignoring case. Words are separated by whitespace. Ignore the punctuation
    characters . , ! ? ; : at the start or end of a word. A one-letter vowel word counts.

    >>> count_vowel_words("Anna ate a banana")
    3
    >>> count_vowel_words("rhythm")
    0""",
     """    vowels = set("aeiouAEIOU")
    n = 0
    for w in sentence.split():
        w = w.strip(".,!?;:")
        if w and w[0] in vowels and w[-1] in vowels:
            n += 1
    return n
""",
     ['candidate("") == 0', 'candidate("Anna ate a banana") == 3', 'candidate("rhythm") == 0',
      'candidate("Olive trees are everywhere") == 3', 'candidate("Echo, I see you!") == 2',
      'candidate("UNIQUE idea.") == 2', 'candidate("a e i o u") == 5', 'candidate("   Area   ") == 1',
      'candidate("...!") == 0']),
    ("rotate_digits", "n, k",
     """Rotate the decimal digits of the non-negative integer n to the right by k
    positions and return the result as an integer (leading zeros disappear).
    k may be larger than the number of digits.

    >>> rotate_digits(12345, 2)
    45123
    >>> rotate_digits(1200, 1)
    120""",
     """    s = str(n)
    k %= len(s)
    if k == 0:
        return n
    return int(s[-k:] + s[:-k])
""",
     ['candidate(12345, 2) == 45123', 'candidate(1200, 1) == 120', 'candidate(12345, 5) == 12345',
      'candidate(12345, 7) == 45123', 'candidate(7, 3) == 7', 'candidate(0, 4) == 0', 'candidate(90, 1) == 9',
      'candidate(123, 0) == 123', 'candidate(1000, 3) == 1']),
    ("merge_ranges", "ranges",
     """ranges is a list of [start, end] pairs of integers, inclusive at both ends, in
    any order. Merge ranges that overlap or touch (end + 1 == next start) and
    return the merged ranges sorted by start.

    >>> merge_ranges([[1, 3], [4, 6], [8, 9]])
    [[1, 6], [8, 9]]
    >>> merge_ranges([[5, 7], [1, 2]])
    [[1, 2], [5, 7]]""",
     """    out = []
    for s, e in sorted(ranges):
        if out and s <= out[-1][1] + 1:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out
""",
     ['candidate([]) == []', 'candidate([[1, 3], [4, 6], [8, 9]]) == [[1, 6], [8, 9]]',
      'candidate([[5, 7], [1, 2]]) == [[1, 2], [5, 7]]', 'candidate([[1, 10], [2, 3]]) == [[1, 10]]',
      'candidate([[3, 3], [1, 1], [2, 2]]) == [[1, 3]]',
      'candidate([[-5, -1], [0, 2], [10, 12], [11, 11]]) == [[-5, 2], [10, 12]]',
      'candidate([[1, 2], [4, 5]]) == [[1, 2], [4, 5]]']),
    ("second_largest_unique", "nums",
     """Return the second largest distinct value in the list nums, or None if nums
    has fewer than two distinct values.

    >>> second_largest_unique([4, 1, 4, 3])
    3
    >>> second_largest_unique([2, 2]) is None
    True""",
     """    vals = sorted(set(nums), reverse=True)
    return vals[1] if len(vals) > 1 else None
""",
     ['candidate([4, 1, 4, 3]) == 3', 'candidate([2, 2]) is None', 'candidate([]) is None',
      'candidate([5]) is None', 'candidate([-1, -3, -2]) == -2', 'candidate([10, 9, 10, 9, 8]) == 9',
      'candidate([0, 100]) == 0', 'candidate([1.5, 2.5, 2.5]) == 1.5']),
    ("balance_index", "nums",
     """Return the smallest index i such that the sum of the elements before i equals
    the sum of the elements after i (the element at i is in neither sum).
    Return -1 if there is no such index.

    >>> balance_index([1, 7, 3, 6, 5, 6])
    3
    >>> balance_index([1, 2, 3])
    -1""",
     """    total, left = sum(nums), 0
    for i, x in enumerate(nums):
        if left == total - left - x:
            return i
        left += x
    return -1
""",
     ['candidate([1, 7, 3, 6, 5, 6]) == 3', 'candidate([1, 2, 3]) == -1', 'candidate([]) == -1',
      'candidate([5]) == 0', 'candidate([0, 0, 0]) == 0', 'candidate([2, 1, -1]) == 0',
      'candidate([1, -1, 5]) == 2', 'candidate([-1, -1, -1, 0, 1, 1]) == 0']),
    ("sort_by_digital_root", "nums",
     """Return a new list with the integers in nums sorted by their digital root, in
    ascending order. The digital root is found by summing the digits of the
    absolute value repeatedly until one digit is left (the digital root of 0 is 0).
    Numbers with equal digital roots keep their original order.

    >>> sort_by_digital_root([38, 11, 9, 5])
    [38, 11, 5, 9]
    >>> sort_by_digital_root([-19, 4, 0])
    [0, -19, 4]""",
     """    def root(n):
        n = abs(n)
        return 0 if n == 0 else 1 + (n - 1) % 9
    return sorted(nums, key=root)
""",
     ['candidate([38, 11, 9, 5]) == [38, 11, 5, 9]', 'candidate([-19, 4, 0]) == [0, -19, 4]',
      'candidate([]) == []', 'candidate([99, 18, 9]) == [99, 18, 9]', 'candidate([123, 321, 12]) == [12, 123, 321]',
      'candidate([10, 100, 1000, 2]) == [10, 100, 1000, 2]', 'candidate([7, -7, 16]) == [7, -7, 16]']),
    ("parse_duration", "text",
     """text is a duration such as "1h30m15s": hours (h), minutes (m) and seconds (s),
    each part optional but always in that order, each a whole number of any
    length. Return the total number of seconds. An empty string is 0 seconds.

    >>> parse_duration("1h30m15s")
    5415
    >>> parse_duration("45s")
    45""",
     """    import re
    m = re.fullmatch(r"(?:(\\d+)h)?(?:(\\d+)m)?(?:(\\d+)s)?", text)
    h, mi, s = (int(g) if g else 0 for g in m.groups())
    return h * 3600 + mi * 60 + s
""",
     ['candidate("") == 0', 'candidate("1h30m15s") == 5415', 'candidate("45s") == 45', 'candidate("2h") == 7200',
      'candidate("90m") == 5400', 'candidate("1h5s") == 3605', 'candidate("10h0m1s") == 36001',
      'candidate("0s") == 0', 'candidate("100m") == 6000']),
    ("longest_increasing_run", "nums",
     """Return the length of the longest run of consecutive elements in nums that is
    strictly increasing. An empty list has a longest run of 0.

    >>> longest_increasing_run([1, 2, 2, 3, 4, 1])
    3
    >>> longest_increasing_run([5, 4, 3])
    1""",
     """    best = cur = 0
    for i, x in enumerate(nums):
        cur = cur + 1 if i and x > nums[i - 1] else 1
        best = max(best, cur)
    return best
""",
     ['candidate([1, 2, 2, 3, 4, 1]) == 3', 'candidate([5, 4, 3]) == 1', 'candidate([]) == 0',
      'candidate([7]) == 1', 'candidate([1, 2, 3, 4, 5]) == 5', 'candidate([3, 1, 2, 3, 0, 1]) == 3',
      'candidate([-2, -1, 0, 0, 1]) == 3', 'candidate([1, 1, 1]) == 1']),
]


def make_code():
    d = OUT / "code" / "tests"
    d.mkdir(parents=True, exist_ok=True)
    failures = []
    for n, (fn, args, doc, body, asserts) in enumerate(CODE, 1):
        iid = f"h_code_{n:03d}"
        header = f'\ndef {fn}({args}):\n    """{doc}\n    """\n'
        test = ("def check(candidate):\n\n    # Check some simple cases\n"
                + "".join(f'    assert {a}, "Error"\n' for a in asserts) + f"\n\ncheck({fn})\n")
        (d / f"{iid}_test.py").write_text(test, encoding="utf-8")
        ref = header + body
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "t.py"
            f.write_text(ref + "\n\n" + test)
            p = subprocess.run([sys.executable, "-I", str(f)], capture_output=True, text=True, timeout=20, cwd=td)
            if p.returncode:
                failures.append((iid, p.stderr[-300:]))
        add(iid, "code", None, "Complete this Python function:\n\n" + header, ref, entry_point=fn, difficulty="easy",
            source="written for the held-out set (HumanEval-style, not from HumanEval)", **SYN,
            transform="prompt and tests written by hand; reference solution passes the tests",
            source_ids={"dataset": "heldout-code"})
    return failures


# Audio

def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def active_rms(x, sr):
    frames = x[: len(x) // (sr // 50) * (sr // 50)].reshape(-1, sr // 50)
    e = np.sqrt((frames ** 2).mean(1))
    return float(np.sqrt((e[e > 0.1 * e.max()] ** 2).mean()))


def to_container(wav, dest):
    if dest.suffix == ".webm":
        # 48 kHz mono Opus in a live-mode WebM, like Chrome's MediaRecorder default.
        ffmpeg("-i", str(wav), "-c:a", "libopus", "-b:a", "32k", "-ar", "48000", "-ac", "1", "-f", "webm",
               "-live", "1", str(dest))
    else:
        ffmpeg("-i", str(wav), "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(dest))


def make_audio():
    d = OUT / "audio"
    d.mkdir(parents=True, exist_ok=True)
    pack = {a["id"]: a for a in json.loads((PACK / "answers.json").read_text())}
    pack_q = {i["id"]: i["question"] for i in json.loads((PACK / "items.json").read_text())}
    rng = np.random.default_rng(501)
    speech_keys = ["speech", "speak", "talk", "voice", "narrat", "reading", "words", "person"]
    specs = [
        ("h_aud_001", "wav", ["p_aud_002"], "speed", "Transcribe this audio.", None, None,
         "slowed to 0.9x with ffmpeg atempo (pitch kept)"),
        ("h_aud_002", "webm", ["p_aud_005"], "speed", "Which instrument does she play, and whose letter does she read?",
         "She plays the piano and reads Philip's letter.", [["piano"], ["philip"]],
         "sped up to 1.1x with ffmpeg atempo (pitch kept); WebM Opus 32 kbps 48 kHz"),
        ("h_aud_003", "wav", ["p_aud_015"], "noise", "What sound is this?", "Dog barking.", [["dog", "bark"]],
         "white Gaussian noise added at 10 dB SNR (relative to the active-frame RMS)"),
        ("h_aud_004", "wav", ["p_aud_007"], "phone", "According to the speaker, where was his country home?",
         "An old family place in Essex.", [["essex"]],
         "phone quality: 300 to 3400 Hz band-pass, 8 kHz mu-law, back to 16 kHz"),
        ("h_aud_005", "webm", ["p_aud_018", "p_aud_010"], "mix", "What can you hear?",
         "A rooster crowing while a man is speaking.", [["rooster", "cock", "crow", "chicken"], speech_keys + ["man"]],
         "rooster clip looped under a male speech clip at equal active RMS; WebM Opus 32 kbps 48 kHz"),
        ("h_aud_006", "wav", ["p_aud_012", "p_aud_001"], "mix", "What can you hear?",
         "A clock ticking while a woman is speaking.", [["clock", "tick"], speech_keys + ["woman"]],
         "clock ticking clip looped under a female speech clip at 3 dB below the speech active RMS"),
    ]
    for iid, ext, srcs, kind, q, ref, key, how in specs:
        src = [PACK / "audio" / f"{s}.wav" for s in srcs]
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td) / "x.wav"
            if kind == "speed":
                tempo = 0.9 if iid == "h_aud_001" else 1.1
                ffmpeg("-i", str(src[0]), "-af", f"atempo={tempo}", "-ar", "16000", "-ac", "1", str(tmp))
            elif kind == "noise":
                x, sr = sf.read(src[0])
                noise = rng.normal(0, active_rms(x, sr) / 10 ** (10 / 20), len(x))
                y = x + noise
                sf.write(tmp, y / max(1.0, np.abs(y).max() / 0.95), sr, subtype="PCM_16")
            elif kind == "phone":
                mid = Path(td) / "p.wav"
                ffmpeg("-i", str(src[0]), "-af", "highpass=f=300,lowpass=f=3400", "-ar", "8000",
                       "-c:a", "pcm_mulaw", str(mid))
                ffmpeg("-i", str(mid), "-ar", "16000", "-c:a", "pcm_s16le", str(tmp))
            else:
                sound, sr = sf.read(src[0])
                speech, _ = sf.read(src[1])
                rel_db = 0 if iid == "h_aud_005" else -3
                sound = sound * (active_rms(speech, sr) / active_rms(sound, sr)) * 10 ** (rel_db / 20)
                bed = np.tile(sound, int(np.ceil(len(speech) / len(sound))))[: len(speech)]
                y = speech + bed
                sf.write(tmp, y / max(1.0, np.abs(y).max() / 0.95), sr, subtype="PCM_16")
            to_container(tmp, d / f"{iid}.{ext}")
        base = pack[srcs[0]]
        if ref is None:
            ref = base["transcript"]
        meta = {"transcript": base["transcript"]} if kind in ("speed", "phone") and base.get("transcript") else {}
        if kind == "mix":
            meta["transcript"] = pack[srcs[1]]["transcript"]
        add(iid, "audio", f"audio/{iid}.{ext}", q, ref, key, **meta, difficulty="hard" if kind == "mix" else "medium",
            source="transform of practice pack " + " + ".join(srcs) + f" ({'; '.join(pack[s]['source'] for s in srcs)})",
            license=" / ".join(sorted({pack[s]["license"] for s in srcs})),
            attribution=" ; ".join(pack[s]["attribution"] for s in srcs), transform=how,
            source_ids={"dataset": "pack-transform", "pack_ids": srcs, "pack_questions": [pack_q[s] for s in srcs]})


# Checks

def check_outputs():
    report = []
    for it in items:
        if it["file"] and not (OUT / it["file"]).exists():
            report.append(f"MISSING {it['file']}")
    for p in sorted((OUT / "video").iterdir()):
        cap = cv2.VideoCapture(str(p))
        n, fps = cap.get(cv2.CAP_PROP_FRAME_COUNT), cap.get(cv2.CAP_PROP_FPS)
        decoded = 0
        while cap.read()[0]:
            decoded += 1
        report.append(f"{p.name}: cv2 frame_count={n:.0f} fps={fps:.1f} decoded={decoded} ({decoded / FPS:.1f} s)")
    from pypdf import PdfReader
    for doc in DOCS:
        txt = set(re.findall(r"[a-z0-9]+", (OUT / "text" / f"{doc}.txt").read_text().lower()))
        pdf = PdfReader(str(OUT / "text" / f"{doc}.pdf"))
        got = set(re.findall(r"[a-z0-9]+", " ".join(pg.extract_text() for pg in pdf.pages).lower()))
        report.append(f"{doc}.pdf: {len(pdf.pages)} pages, {len(txt & got)}/{len(txt)} txt words extractable")
    return report


def main():
    OUT.mkdir(exist_ok=True)
    make_videos()
    make_text()
    make_images()
    code_fail = make_code()
    make_audio()
    order = {"image": 0, "audio": 1, "text": 2, "video": 3, "code": 4}
    items.sort(key=lambda i: (order[i["modality"]], i["id"]))
    answers.sort(key=lambda a: (order[a["modality"]], a["id"]))
    (OUT / "items.json").write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "answers.json").write_text(json.dumps(answers, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    doc = ("Acceptance keys for heldout/, same format as scripts/pack_keys.json (eval_pack.py --pack heldout "
           "loads this file instead). Items not listed: audio 'Transcribe' uses WER, code runs the test file.")
    (OUT / "keys.json").write_text(json.dumps({"_doc": doc, **keys}, indent=2) + "\n", encoding="utf-8")
    counts = {}
    for i in items:
        counts[i["modality"]] = counts.get(i["modality"], 0) + 1
    print("counts:", counts, "total", len(items))
    print("code reference failures:", code_fail or "none")
    print("\n".join(check_outputs()))


if __name__ == "__main__":
    main()
