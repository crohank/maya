import json, glob, sys
from pathlib import Path
import numpy as np
from PIL import Image
D = Path("data/sanpo")
idx = {r["sid"]: r for r in json.load(open(D / "index.json"))}
for seg in sorted(glob.glob(str(D / "seg" / "*"))):
    seg = Path(seg)
    if not (seg / "depth.npz").exists():
        continue
    meta = json.load(open(seg / "meta.json"))
    d = idx[meta["sid"]]["desc"]
    p = d["session_camera_details"][d["session_camera_location"].index("camera_chest")]["left_camera_params"]
    s = 320 / p["image_width"]; fx, cx, cy = p["fx"] * s, p["cx"] * s, p["cy"] * s
    z = np.load(seg / "depth.npz"); dep, fr = z["depth"].astype(np.float32), list(z["frame"])
    hs, pitches = [], []
    for i in range(0, len(fr), max(1, len(fr) // 12)):
        mp = seg / "masks" / f"{fr[i]:06d}.png"
        if not mp.exists():
            continue
        a = np.array(Image.open(mp).convert("RGB"))
        rows = ((np.arange(180) + .5) * a.shape[0] / 180).astype(int); cols = ((np.arange(320) + .5) * a.shape[1] / 320).astype(int)
        sem = a[rows][:, cols, 0]
        g = np.isin(sem, [1, 3, 5, 6, 17]) & (dep[i] > 0.5) & (dep[i] < 8)
        if g.sum() < 200:
            continue
        v, u = np.nonzero(g); Z = dep[i][g]
        P = np.stack([(u - cx) / fx * Z, (v - cy) / fx * Z, Z], 1)
        best = None
        rng = np.random.default_rng(0)
        for _ in range(200):
            q = P[rng.choice(len(P), 3, replace=False)]
            n = np.cross(q[1] - q[0], q[2] - q[0]); nn = np.linalg.norm(n)
            if nn < 1e-6: continue
            n /= nn; dd = -n @ q[0]
            inl = np.abs(P @ n + dd) < 0.05
            if best is None or inl.sum() > best[0]: best = (inl.sum(), n, dd)
        _, n, dd = best
        if n[1] < 0: n, dd = -n, -dd
        hs.append(abs(dd)); pitches.append(np.degrees(np.arcsin(np.clip(n[2], -1, 1))))
    print(seg.name, p["h_fov"], "height m", np.round(np.median(hs), 2) if hs else None,
          "pitch down deg", np.round(np.median(pitches), 1) if pitches else None, len(hs))
