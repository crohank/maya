"""Fetch a few SANPO-Real chest-camera segments and turn them into walk test clips.

SANPO (Google Research, CC BY 4.0): https://github.com/google-research-datasets/sanpo_dataset
Public bucket gs://gresearch/sanpo_dataset/v0, read over plain HTTPS (no gcloud, no auth).

Steps (run in maya-engine with network on, no GPU):
  python -I scripts/sanpo_fetch.py index            # data/sanpo/index.json
  python -I scripts/sanpo_fetch.py masks --top 30   # masks of the best sessions, scores windows
  python -I scripts/sanpo_fetch.py clips --n 11 --seconds 30 --step 2
      # left RGB -> data/sanpo/clips/sanpo_<sid8>_<start>.mp4 (15 fps / step, 1280x720),
      # CREStereo depth downsampled to 320x180 -> data/sanpo/seg/<stem>/depth.npz,
      # masks kept as PNG under data/sanpo/seg/<stem>/masks/.
  python -I scripts/sanpo_fetch.py poses            # camera positions, for walker speed
Raw PNG frames are deleted after encoding; only the MP4 stays.

Bucket layout (checked 2026-11-18):
  sanpo-real/<sid>/description.json
  sanpo-real/<sid>/camera_chest/left/video_frames/NNNNNN.png     2208x1242 RGB, 3.0 to 3.6 MB
  .../left/segmentation_masks/NNNNNN.png   R = semantic id (labelmap.json), B = instance id
  .../left/depth_maps/NNNNNN.float16.gz    CREStereo metres, 2 header halfs (h, w) then 720x1280
  .../left/zed_depth_maps/...              ZED sparse depth, full res, not used
  .../left/frame_segmentation_annotation_type.json   {frame: HUMAN_ANNOTATED|MACHINE_ANNOTATED}
"""
import argparse
import concurrent.futures as cf
import gzip
import io
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

API = "https://storage.googleapis.com/storage/v1/b/gresearch/o"
GET = "https://storage.googleapis.com/gresearch/"
ROOT = "sanpo_dataset/v0/sanpo-real/"
DATA = Path("data/sanpo")
FPS = 15.0
PERSON, RIDER, VEHICLE = 12, 13, 21
DEPTH_DS = 4  # 1280x720 -> 320x180


def http(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except Exception as e:  # 404 is final, the rest are retried
            if getattr(e, "code", None) == 404:
                return None
            if k == tries - 1:
                raise
            time.sleep(2 * (k + 1))


def ls(prefix, delimiter="/", fields="prefixes,items(name,size),nextPageToken"):
    prefixes, items, tok = [], [], None
    while True:
        q = {"prefix": prefix, "delimiter": delimiter, "fields": fields, "maxResults": 1000}
        if tok:
            q["pageToken"] = tok
        r = json.loads(http(API + "?" + urllib.parse.urlencode(q)))
        prefixes += r.get("prefixes", [])
        items += r.get("items", [])
        tok = r.get("nextPageToken")
        if not tok:
            return prefixes, items


def probe_session(sid):
    base = ROOT + sid + "/"
    desc = http(GET + base + "description.json")
    rec = {"sid": sid, "desc": json.loads(desc) if desc else None}
    ann = http(GET + base + "camera_chest/left/frame_segmentation_annotation_type.json")
    if ann:
        ann = json.loads(ann)
        rec["n_seg"] = len(ann)
        rec["n_human"] = sum(v == "HUMAN_ANNOTATED" for v in ann.values())
    sub, _ = ls(base + "camera_chest/left/")
    rec["chest_left"] = [p.rstrip("/").rsplit("/", 1)[1] for p in sub]
    return rec


def cmd_index(args):
    sess, _ = ls(ROOT)
    sids = [p[len(ROOT):].rstrip("/") for p in sess if p[len(ROOT):].rstrip("/") not in ("splits",)]
    print(f"{len(sids)} session prefixes")
    with cf.ThreadPoolExecutor(32) as ex:
        recs = list(ex.map(probe_session, sids))
    DATA.mkdir(parents=True, exist_ok=True)
    json.dump(recs, open(DATA / "index.json", "w"), indent=1)
    print(f"wrote {DATA / 'index.json'}")


LEVEL = {"LOW": 1, "MODERATE": 2, "MEDIUM": 2, "HIGH": 3, "HEAVY": 3}


def level(s):
    return LEVEL.get((s or "").rsplit("_", 1)[-1], 0)


def candidates(recs):
    out = []
    for r in recs:
        d = r.get("desc") or {}
        md = d.get("session_video_metadata", {})
        cams = d.get("session_camera_details", [])
        locs = d.get("session_camera_location", [])
        if d.get("session_type") != "real" or "segmentation_masks" not in r.get("chest_left", []):
            continue
        if "depth_maps" not in r["chest_left"] or "video_frames" not in r["chest_left"]:
            continue
        if md.get("ego_motion") != "EGO_MOTION_WALKING":
            continue
        cam = cams[locs.index("camera_chest")] if "camera_chest" in locs and len(cams) == len(locs) else {}
        score = 2 * level(md.get("human_traffic")) + level(md.get("vehicular_traffic"))
        out.append({"sid": r["sid"], "score": score, "n_seg": r.get("n_seg", 0),
                    "human": md.get("human_traffic"), "vehicle": md.get("vehicular_traffic"),
                    "env": md.get("environment_types"), "cam": cam.get("model"),
                    "hfov": cam.get("left_camera_params", {}).get("h_fov")})
    out.sort(key=lambda c: (-c["score"], -c["n_seg"]))
    return out


def read_mask(raw):
    a = np.array(Image.open(io.BytesIO(raw)).convert("RGB"))
    return a[..., 0], a[..., 2]


def window_score(sem, inst):
    """Largest person/rider/vehicle instance area share in the middle half of the frame."""
    h, w = sem.shape
    mid = slice(w // 4, 3 * w // 4)
    best = 0.0
    s, i = sem[:, mid], inst[:, mid]
    for c in (PERSON, RIDER, VEHICLE):
        m = s == c
        if not m.any():
            continue
        ids, n = np.unique(i[m], return_counts=True)
        best = max(best, n.max() / m.size * (3 if c != VEHICLE else 1))
    return best


def cmd_masks(args):
    recs = json.load(open(DATA / "index.json"))
    cands = candidates(recs)[: args.top]
    out = {}

    def one(c):
        sid = c["sid"]
        mdir = DATA / "masks" / sid
        mdir.mkdir(parents=True, exist_ok=True)
        _, items = ls(ROOT + sid + "/camera_chest/left/segmentation_masks/", delimiter="")
        names = sorted(it["name"] for it in items if it["name"].endswith(".png"))

        def get(name):
            p = mdir / name.rsplit("/", 1)[1]
            if not p.exists():
                p.write_bytes(http(GET + name))
            return p

        def score(p):
            sem, inst = read_mask(p.read_bytes())
            return window_score(sem[::4, ::4], inst[::4, ::4])

        with cf.ThreadPoolExecutor(16) as ex:
            paths = list(ex.map(get, names))
            sc = list(ex.map(score, paths))
        c["frames"] = len(paths)
        c["frame_scores"] = [round(float(x), 5) for x in sc]
        out[sid] = c
        print(sid, c["human"], c["vehicle"], len(paths), "max", round(max(sc or [0]), 4), flush=True)

    with cf.ThreadPoolExecutor(6) as ex:
        list(ex.map(one, cands))
    json.dump(out, open(DATA / "mask_scores.json", "w"))


def best_window(scores, n):
    """Start frame of the n-frame window with the most frames where something is big and central."""
    s = np.array(scores)
    hot = (s > 0.01).astype(float) + s * 20
    if len(s) <= n:
        return 0, float(hot.sum())
    cs = np.concatenate([[0], np.cumsum(hot)])
    tot = cs[n:] - cs[:-n]
    k = int(tot.argmax())
    return k, float(tot[k])


def encode(frame_dir, out_mp4, fps):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps),
                    "-i", str(frame_dir / "%06d.png"), "-vf", "scale=1280:720",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", str(out_mp4)], check=True)


def cmd_clips(args):
    ms = json.load(open(DATA / "mask_scores.json"))
    n = int(args.seconds * FPS)
    ranked = []
    for sid, c in ms.items():
        k, v = best_window(c["frame_scores"], n)
        ranked.append((v, sid, k))
    ranked.sort(reverse=True)
    if args.sids:
        ranked = [r for r in ranked if r[1] in args.sids.split(",")]
    clips = DATA / "clips"
    clips.mkdir(parents=True, exist_ok=True)
    made = []
    for v, sid, k in ranked[: args.n]:
        stem = f"sanpo_{sid[:8].replace('-', 'x')}_{k:04d}"
        seg = DATA / "seg" / stem
        if (clips / f"{stem}.mp4").exists() and (seg / "depth.npz").exists():
            made.append(stem)
            continue
        tmp = DATA / "tmp" / stem
        tmp.mkdir(parents=True, exist_ok=True)
        (seg / "masks").mkdir(parents=True, exist_ok=True)
        base = GET + ROOT + sid + "/camera_chest/left/"
        idx = list(range(k, k + n, args.step))

        def frame(j):
            p = tmp / f"{(j - k) // args.step:06d}.png"
            if not p.exists():
                raw = http(base + f"video_frames/{j:06d}.png")
                if raw is None:
                    return None
                p.write_bytes(raw)
            return p

        def depth(j):
            raw = http(base + f"depth_maps/{j:06d}.float16.gz")
            if raw is None:
                return None
            d = np.frombuffer(gzip.decompress(raw), dtype=np.float16)
            h, w = int(d[0]), int(d[1])
            d = d[2:].reshape(h, w).astype(np.float32)
            # Block median keeps object edges from mixing near and far depth.
            d = d[: h // DEPTH_DS * DEPTH_DS, : w // DEPTH_DS * DEPTH_DS]
            d = np.median(d.reshape(h // DEPTH_DS, DEPTH_DS, w // DEPTH_DS, DEPTH_DS).swapaxes(1, 2)
                          .reshape(h // DEPTH_DS, w // DEPTH_DS, -1), axis=2)
            return d.astype(np.float16)

        t0 = time.time()
        with cf.ThreadPoolExecutor(24) as ex:
            got = list(ex.map(frame, idx))
            deps = list(ex.map(depth, idx))
        if any(g is None for g in got):
            last = next(i for i, g in enumerate(got) if g is None)
            idx, got, deps = idx[:last], got[:last], deps[:last]
        mb = sum(p.stat().st_size for p in got) / 1e6
        encode(tmp, clips / f"{stem}.mp4", FPS / args.step)
        for j in idx:
            src = DATA / "masks" / sid / f"{j:06d}.png"
            if src.exists():
                shutil.copy(src, seg / "masks" / f"{(j - k) // args.step:06d}.png")
        have = [i for i, d in enumerate(deps) if d is not None]
        np.savez_compressed(seg / "depth.npz", depth=np.stack([deps[i] for i in have]),
                            frame=np.array(have))
        meta = dict(ms[sid], start_frame=k, n_frames=len(idx), fps=FPS / args.step, step=args.step, source=base,
                    stem=stem, download_mb=round(mb, 1), depth_ds=DEPTH_DS)
        meta.pop("frame_scores", None)
        ann = http(base + "frame_segmentation_annotation_type.json")
        if ann:
            ann = json.loads(ann)
            meta["human_annotated"] = [(j - k) // args.step for j in idx if ann.get(str(j)) == "HUMAN_ANNOTATED"]
        json.dump(meta, open(seg / "meta.json", "w"), indent=1)
        shutil.rmtree(tmp)
        made.append(stem)
        print(f"{stem}: {len(idx)} frames, {mb:.0f} MB fetched in {time.time() - t0:.0f}s", flush=True)
    print("clips:", " ".join(made))


def cmd_poses(args):
    """camera_chest/fixed_camera_poses.csv (one row per frame) for each clip's session."""
    for meta in sorted((DATA / "seg").glob("*/meta.json")):
        m = json.load(open(meta))
        out = meta.parent / "poses.csv"
        if not out.exists():
            raw = http(GET + ROOT + m["sid"] + "/camera_chest/fixed_camera_poses.csv")
            out.write_bytes(raw)
        print(meta.parent.name, len(out.read_text().splitlines()) - 1, "pose rows")


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("index")
    m = sp.add_parser("masks")
    m.add_argument("--top", type=int, default=30)
    c = sp.add_parser("clips")
    c.add_argument("--n", type=int, default=10)
    c.add_argument("--seconds", type=float, default=30)
    c.add_argument("--sids", default="")
    c.add_argument("--step", type=int, default=1, help="keep every step-th frame (2: 7.5 fps)")
    sp.add_parser("list")
    sp.add_parser("poses")
    args = ap.parse_args()
    if args.cmd == "list":
        for c in candidates(json.load(open(DATA / "index.json")))[:60]:
            print(c)
        return
    {"index": cmd_index, "masks": cmd_masks, "clips": cmd_clips, "poses": cmd_poses}[args.cmd](args)


if __name__ == "__main__":
    main()
