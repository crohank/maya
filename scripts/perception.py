"""Fast perception layer for Maya: detector + metric depth + IoU tracker + motion labels.

Contract (other modules code against it):
    p = Perception(device="cuda")
    tracks = p.update(frame_rgb, t)   # frame_rgb (H,W,3) uint8, t in seconds
    p.last_timing                     # {"detect_ms", "depth_ms", "track_ms"}

Each track: id, cls, conf, box (normalized x1,y1,x2,y2), side, dist_m, dist_bucket,
motion, ttc_s, age_s. See docs/perception.md for models, timing and known errors.

CLI:
    python scripts/perception.py --video test_videos/X.mp4 --fps 8 \
        --out results/perception/X.jsonl
"""

import argparse
import json
import math
import os
import subprocess
import time
from collections import deque

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from scipy.optimize import linear_sum_assignment
from transformers import AutoModelForDepthEstimation, AutoModelForObjectDetection

DETECTOR_ID = "ustc-community/dfine-small-obj365"
DETECTOR_FALLBACK_ID = "ustc-community/dfine-small-coco"
# Same tensors as the Apache-2.0 depth-anything/Depth-Anything-V2-Metric-VKITTI-Small
# .pth (checked tensor by tensor, qkv split included); this -hf copy states no license
# but is the one transformers loads.
DEPTH_ID = "depth-anything/Depth-Anything-V2-Metric-Outdoor-Small-hf"

DET_SIZE = 640
DEPTH_LONG = 518  # long side fed to depth, multiple of 14
DET_THRESH = 0.30

# Detector label -> Maya class. Labels not listed are dropped.
CLASS_MAP = {
    # Objects365 names
    "Person": "person", "Bicycle": "bicycle", "Tricycle": "bicycle",
    "Car": "car", "SUV": "car", "Van": "car", "Sports Car": "car",
    "Motorcycle": "motorcycle", "Scooter": "scooter", "Bus": "bus",
    "Truck": "truck", "Pickup Truck": "truck", "Heavy Truck": "truck",
    "Fire Truck": "truck", "Machinery Vehicle": "truck", "Ambulance": "truck",
    "Traffic Light": "traffic light", "Fire Hydrant": "fire hydrant",
    "Stop Sign": "stop sign", "Bench": "bench", "Street Lights": "pole",
    "Trash bin Can": "trash can", "Traffic cone": "traffic cone",
    "Traffic Sign": "sign", "Speed Limit Sign": "sign", "Crosswalk Sign": "sign",
    "Stroller": "stroller", "Wheelchair": "wheelchair", "Dog": "dog",
    "Chair": "chair", "Stool": "chair", "Potted Plant": "potted plant",
    "Barrel/bucket": "barrel", "Parking meter": "parking meter",
    "Luggage": "luggage", "Trolley": "cart",
    # COCO names (fallback checkpoint)
    "person": "person", "bicycle": "bicycle", "car": "car", "motorcycle": "motorcycle",
    "bus": "bus", "truck": "truck", "traffic light": "traffic light",
    "fire hydrant": "fire hydrant", "stop sign": "stop sign", "bench": "bench",
    "parking meter": "parking meter", "dog": "dog", "chair": "chair",
    "potted plant": "potted plant", "suitcase": "luggage",
}

# The detector often fires car and truck (or SUV and pickup) on one vehicle. These
# classes share NMS and track matching; a track reports its highest summed-score class.
GROUP = {"car": "vehicle", "truck": "vehicle", "bus": "vehicle"}

# Tracker
HIGH_CONF = 0.50
MATCH_IOU = 0.25
MIN_HITS = 2
MAX_LOST_S = 1.0

# Motion. Rates are per second over a window of HIST_S.
HIST_S = 1.0
MIN_HIST_S = 0.5
EMA = 0.5
SCALE_ENTER = 0.15   # box size growth 15 %/s: approaching (receding if negative)
LAT_ENTER = 0.08     # 8 % of frame width per second after camera compensation
STAY = 0.6           # current label holds while its score is >= STAY * enter
SWITCH_FRAMES = 2
# Below this box height (fraction of frame) one pixel of box jitter is over 3 % of the
# size, enough to fake a 15 %/s growth rate; such tracks stay "static".
MIN_MOTION_H = 0.04

# Metric scale. Depth-Anything-V2 VKITTI was trained on a car roof camera; on these
# handheld clips it reads 2 to 3 times too far (docs/perception.md). Each frame, standing
# people give a second estimate, d = PERSON_H * f / box_height_px, with f from an assumed
# FOV over the long image side, and the depth map is rescaled by the EMA of their ratio.
PERSON_H = 1.7
LONG_FOV_DEG = 78.0  # wider than a 26 mm phone lens (68 deg) on purpose, see docs/perception.md
SCALE_PRIOR = 0.5    # used until people are seen; final values on 3 clips with people: 0.28, 0.52, 0.62
SCALE_EMA = 0.15


def _iou(a, b):
    """a (N,4), b (M,4) -> (N,M)."""
    x1 = np.maximum(a[:, None, 0], b[None, :, 0])
    y1 = np.maximum(a[:, None, 1], b[None, :, 1])
    x2 = np.minimum(a[:, None, 2], b[None, :, 2])
    y2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    area_a = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1])
    area_b = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / (area_a[:, None] + area_b[None, :] - inter + 1e-9)


def _nms(boxes, scores, classes, thr=0.6):
    """Per-class NMS: Car/SUV/Van map to one class and can stack on the same object."""
    keep = []
    groups = [GROUP.get(c, c) for c in classes]
    for g in set(groups):
        idx = [i for i in range(len(groups)) if groups[i] == g]
        idx.sort(key=lambda i: -scores[i])
        while idx:
            i = idx.pop(0)
            keep.append(i)
            if idx:
                ious = _iou(boxes[[i]], boxes[idx])[0]
                idx = [j for j, v in zip(idx, ious) if v < thr]
    return sorted(keep)


def _slope(ts, vs):
    ts = np.asarray(ts, dtype=np.float64)
    vs = np.asarray(vs, dtype=np.float64)
    tm = ts - ts.mean()
    den = (tm * tm).sum()
    return float((tm * (vs - vs.mean())).sum() / den) if den > 0 else 0.0


class _Track:
    def __init__(self, tid, box, cls, conf, t):
        self.id = tid
        self.box = box
        self.cls = cls
        self.cls_score = {cls: conf}
        self.conf = conf
        self.t0 = t
        self.t_seen = t
        self.hits = 1
        self.vel = np.zeros(4)  # box velocity, normalized units per second
        self.hist = deque()     # (t, box, dist_m, cam_x)
        self.rates = None       # EMA of (scale_rate, lat_rate, depth_rate)
        self.motion = "static"
        self.pending = None
        self.pending_n = 0
        self.dist = None

    def predict(self, t):
        return self.box + self.vel * min(t - self.t_seen, 0.5)

    def update(self, box, conf, t, cls):
        self.cls_score[cls] = self.cls_score.get(cls, 0.0) + conf
        self.cls = max(self.cls_score, key=self.cls_score.get)
        dt = t - self.t_seen
        if dt > 0:
            self.vel = 0.5 * self.vel + 0.5 * (box - self.box) / dt
        self.box = box
        self.conf = conf
        self.t_seen = t
        self.hits += 1


class Perception:
    def __init__(self, device="cuda", detector_id=DETECTOR_ID, depth_id=DEPTH_ID):
        self.device = device
        self.dtype = torch.float16 if device.startswith("cuda") else torch.float32
        try:
            self.det = AutoModelForObjectDetection.from_pretrained(detector_id)
        except Exception as e:  # noqa: BLE001
            print(f"[perception] {detector_id} failed ({e}); using {DETECTOR_FALLBACK_ID}")
            self.det = AutoModelForObjectDetection.from_pretrained(DETECTOR_FALLBACK_ID)
        self.det = self.det.to(device, self.dtype).eval()
        id2label = self.det.config.id2label
        n = max(int(k) for k in id2label) + 1
        self.label_map = [CLASS_MAP.get(id2label.get(i, id2label.get(str(i), "")))
                          for i in range(n)]
        self.depth = AutoModelForDepthEstimation.from_pretrained(depth_id).to(
            device, self.dtype).eval()
        self.mean = torch.tensor([0.485, 0.456, 0.406], device=device).view(1, 3, 1, 1)
        self.std = torch.tensor([0.229, 0.224, 0.225], device=device).view(1, 3, 1, 1)

        self.keep_idx = torch.tensor([i for i, n in enumerate(self.label_map) if n],
                                     device=device)
        self.keep_names = [self.label_map[i] for i in self.keep_idx.tolist()]
        if device.startswith("cuda"):
            torch.backends.cudnn.benchmark = True

        self.tracks = []
        self.next_id = 1
        self.log_scale = math.log(SCALE_PRIOR)
        self.scale_samples = 0
        self.prev_gray = None
        self.cam_x = 0.0  # accumulated horizontal camera shift, frame widths
        self.last_timing = {"detect_ms": 0.0, "depth_ms": 0.0, "track_ms": 0.0}

    def _sync(self):
        if self.device.startswith("cuda"):
            torch.cuda.synchronize()

    @torch.inference_mode()
    def _detect(self, img):
        x = F.interpolate(img, size=(DET_SIZE, DET_SIZE), mode="bilinear",
                          align_corners=False, antialias=True)
        out = self.det(pixel_values=x.to(self.dtype))
        scores = out.logits[0, :, self.keep_idx].float().sigmoid()
        boxes = out.pred_boxes[0].float()  # cx, cy, w, h normalized
        # D-FINE uses sigmoid focal scores; top-k over (query, class) like its postprocessor.
        top, idx = scores.flatten().topk(min(100, scores.numel()))
        m = top > DET_THRESH
        q = (idx // scores.shape[1])[m]
        c = (idx % scores.shape[1])[m]
        b = boxes[q]
        b = torch.stack([b[:, 0] - b[:, 2] / 2, b[:, 1] - b[:, 3] / 2,
                         b[:, 0] + b[:, 2] / 2, b[:, 1] + b[:, 3] / 2], 1).clamp(0, 1)
        xyxy, top, c = b.cpu().numpy(), top[m].cpu().numpy(), c.cpu().numpy()
        keep_b, keep_s, keep_c = [], [], []
        for bb, sc, ci in zip(xyxy, top, c):
            if bb[2] - bb[0] < 1e-3 or bb[3] - bb[1] < 1e-3:
                continue
            keep_b.append(bb)
            keep_s.append(float(sc))
            keep_c.append(self.keep_names[ci])
        if not keep_b:
            return np.zeros((0, 4)), [], []
        keep_b = np.array(keep_b)
        k = _nms(keep_b, keep_s, keep_c)
        return keep_b[k], [keep_s[i] for i in k], [keep_c[i] for i in k]

    @torch.inference_mode()
    def _depth(self, img):
        h, w = img.shape[2:]
        s = DEPTH_LONG / max(h, w)
        dh = max(14, int(round(h * s / 14)) * 14)
        dw = max(14, int(round(w * s / 14)) * 14)
        x = F.interpolate(img, size=(dh, dw), mode="bicubic", align_corners=False,
                          antialias=True)
        x = (x - self.mean) / self.std
        d = self.depth(pixel_values=x.to(self.dtype)).predicted_depth
        return d[0].float()  # (dh, dw) metres

    def _box_dist(self, depth, box):
        # Lower-centre of the box: legs of a person, base of a pole. The top of a box
        # often holds background (sky, far facade) and pulls the median far.
        dh, dw = depth.shape
        x1, y1, x2, y2 = box
        bw, bh = x2 - x1, y2 - y1
        xa, xb = x1 + 0.3 * bw, x2 - 0.3 * bw
        ya, yb = y1 + 0.55 * bh, y1 + 0.9 * bh
        xa, xb = int(xa * dw), max(int(xa * dw) + 1, int(math.ceil(xb * dw)))
        ya, yb = int(ya * dh), max(int(ya * dh) + 1, int(math.ceil(yb * dh)))
        patch = depth[min(ya, dh - 1):min(yb, dh), min(xa, dw - 1):min(xb, dw)]
        if patch.numel() == 0:
            return None
        return float(patch.median())

    @staticmethod
    def _person_dist(b, H, W):
        # Standing, uncut people only: a box touching the frame edge or a seated
        # person underestimates height and overestimates distance.
        bh, bw = (b[3] - b[1]) * H, (b[2] - b[0]) * W
        if b[1] < 0.01 or b[3] > 0.99 or bh < 0.05 * H or not 1.8 < bh / max(bw, 1) < 5.0:
            return None
        f = (max(H, W) / 2) / math.tan(math.radians(LONG_FOV_DEG / 2))
        return float(PERSON_H * f / bh)

    def _update_scale(self, depth, boxes, scores, classes, H, W):
        logs = []
        for b, sc, c in zip(boxes, scores, classes):
            if c != "person" or sc < 0.6:
                continue
            pd = self._person_dist(b, H, W)
            raw = self._box_dist(depth, b) if pd else None
            if raw and raw > 0.3:
                logs.append(math.log(pd / raw))
        if logs:
            a = SCALE_EMA if self.scale_samples else 0.5
            self.log_scale = (1 - a) * self.log_scale + a * float(np.median(logs))
            self.log_scale = min(max(self.log_scale, math.log(0.1)), math.log(2.0))
            self.scale_samples += len(logs)

    @property
    def scale(self):
        return math.exp(self.log_scale)

    def _camera_shift(self, frame_rgb):
        # Global horizontal shift from phase correlation on a 192 px wide gray frame.
        # Removes head turns and camera pans from lateral (crossing) velocity.
        g = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)
        sw = 192
        g = cv2.resize(g, (sw, max(8, int(g.shape[0] * sw / g.shape[1]))),
                       interpolation=cv2.INTER_AREA).astype(np.float32)
        if self.prev_gray is not None and self.prev_gray.shape == g.shape:
            (dx, _dy), resp = cv2.phaseCorrelate(self.prev_gray, g)
            if resp > 0.05:
                self.cam_x += dx / sw
        self.prev_gray = g

    def _motion(self, tr, t):
        hist = [h for h in tr.hist if t - h[0] <= HIST_S + 1e-6]
        if len(hist) < 3 or hist[-1][0] - hist[0][0] < MIN_HIST_S:
            return
        ts = [h[0] for h in hist]
        size = [math.log(max(1e-6, math.sqrt((h[1][2] - h[1][0]) * (h[1][3] - h[1][1]))))
                for h in hist]
        cx = [(h[1][0] + h[1][2]) / 2 - h[3] for h in hist]
        scale_rate = _slope(ts, size)
        lat = _slope(ts, cx)
        # Walking forward makes static things drift outward from the image centre at
        # (cx - 0.5) * scale_rate; take that out so a pole beside the path is not "crossing".
        cx_now = (tr.box[0] + tr.box[2]) / 2
        lat -= (cx_now - 0.5) * scale_rate
        dd = [h[2] for h in hist if h[2] is not None]
        dts = [h[0] for h in hist if h[2] is not None]
        drate = _slope(dts, dd) if len(dd) >= 3 else 0.0
        new = np.array([scale_rate, lat, drate])
        tr.rates = new if tr.rates is None else EMA * new + (1 - EMA) * tr.rates

        s, l, d = tr.rates
        if tr.box[3] - tr.box[1] < MIN_MOTION_H:
            tr.motion, tr.pending, tr.pending_n = "static", None, 0
            return
        # A shrinking box with depth not growing (or the reverse) is ambiguous; scale
        # leads because box size is measured directly and depth is noisier.
        scores = {
            "approaching": s / SCALE_ENTER + (0.3 if d < -0.5 else 0.0),
            "receding": -s / SCALE_ENTER + (0.3 if d > 0.5 else 0.0),
            "crossing_right": l / LAT_ENTER,
            "crossing_left": -l / LAT_ENTER,
        }
        best = max(scores, key=scores.get)
        cand = best if scores[best] >= 1.0 else "static"
        cur = tr.motion
        if cur != "static" and scores.get(cur, 0) >= STAY and cand in ("static", cur):
            cand = cur
        if cand == cur:
            tr.pending, tr.pending_n = None, 0
            return
        if cand == tr.pending:
            tr.pending_n += 1
        else:
            tr.pending, tr.pending_n = cand, 1
        if tr.pending_n >= SWITCH_FRAMES:
            tr.motion = cand
            tr.pending, tr.pending_n = None, 0

    def _associate(self, boxes, scores, classes, t):
        unmatched_dets = list(range(len(boxes)))
        unmatched_trs = list(range(len(self.tracks)))
        matches = []
        # ByteTrack order: confident detections first, then low-score ones only for
        # tracks that are still unmatched (keeps tracks alive through partial occlusion).
        for stage in (0, 1):
            dets = [i for i in unmatched_dets if (scores[i] >= HIGH_CONF) == (stage == 0)]
            if not dets or not unmatched_trs:
                continue
            pb = np.array([self.tracks[j].predict(t) for j in unmatched_trs])
            iou = _iou(boxes[dets], pb)
            for a, i in enumerate(dets):
                for b, j in enumerate(unmatched_trs):
                    if GROUP.get(classes[i], classes[i]) != GROUP.get(self.tracks[j].cls,
                                                                      self.tracks[j].cls):
                        iou[a, b] = 0.0
            ri, ci = linear_sum_assignment(-iou)
            used_d, used_t = set(), set()
            for a, b in zip(ri, ci):
                if iou[a, b] >= MATCH_IOU:
                    matches.append((dets[a], unmatched_trs[b]))
                    used_d.add(dets[a])
                    used_t.add(unmatched_trs[b])
            unmatched_dets = [i for i in unmatched_dets if i not in used_d]
            unmatched_trs = [j for j in unmatched_trs if j not in used_t]
        return matches, unmatched_dets

    def update(self, frame_rgb, t):
        t = float(t)
        H, W = frame_rgb.shape[:2]
        t0 = time.perf_counter()
        img = torch.from_numpy(np.ascontiguousarray(frame_rgb)).to(self.device)
        img = img.permute(2, 0, 1).unsqueeze(0).float().div_(255.0)
        boxes, scores, classes = self._detect(img)
        self._sync()
        t1 = time.perf_counter()
        depth = self._depth(img)
        self._sync()
        t2 = time.perf_counter()

        self._camera_shift(frame_rgb)
        self._update_scale(depth, boxes, scores, classes, H, W)
        matches, new_dets = self._associate(boxes, scores, classes, t)
        matched = set()
        for i, j in matches:
            tr = self.tracks[j]
            tr.update(boxes[i], scores[i], t, classes[i])
            matched.add(tr.id)
        for i in new_dets:
            if scores[i] >= HIGH_CONF:
                tr = _Track(self.next_id, boxes[i], classes[i], scores[i], t)
                self.next_id += 1
                self.tracks.append(tr)
                matched.add(tr.id)
        self.tracks = [tr for tr in self.tracks if t - tr.t_seen <= MAX_LOST_S]

        out = []
        for tr in self.tracks:
            if tr.id not in matched:
                continue
            # People: height-based distance when the box is whole (it does not depend on
            # the depth scale); everything else: rescaled metric depth. EMA over frames.
            d = self._person_dist(tr.box, H, W) if tr.cls == "person" else None
            if d is None:
                raw = self._box_dist(depth, tr.box)
                d = None if raw is None else raw * self.scale
            if d is not None and tr.dist is not None:
                d = 0.5 * d + 0.5 * tr.dist
            tr.dist = d if d is not None else tr.dist
            tr.hist.append((t, tr.box.copy(), tr.dist, self.cam_x))
            while tr.hist and t - tr.hist[0][0] > HIST_S + 0.3:
                tr.hist.popleft()
            self._motion(tr, t)
            if tr.hits < MIN_HITS:
                continue
            x1, y1, x2, y2 = [float(v) for v in tr.box]
            cx = (x1 + x2) / 2
            side = "left" if cx < 0.35 else "right" if cx > 0.65 else "ahead"
            dist = tr.dist
            bucket = None if dist is None else "near" if dist < 2 else "mid" if dist <= 5 else "far"
            ttc = None
            if tr.motion == "approaching" and tr.rates is not None and tr.rates[0] > 1e-3:
                # dist / closing speed, written as 1 / (relative size growth rate): for a
                # rigid object d/(-dd/dt) == s/(ds/dt), and the size form does not inherit
                # the metric depth scale error.
                ttc = round(1.0 / float(tr.rates[0]), 2)
            out.append({
                "id": tr.id, "cls": tr.cls, "conf": round(float(tr.conf), 3),
                "box": [round(x1, 4), round(y1, 4), round(x2, 4), round(y2, 4)],
                "side": side,
                "dist_m": None if dist is None else round(dist, 2),
                "dist_bucket": bucket or "far",
                "motion": tr.motion, "ttc_s": ttc,
                "age_s": round(t - tr.t0, 2),
            })
        t3 = time.perf_counter()
        self.last_timing = {
            "detect_ms": round((t1 - t0) * 1000, 2),
            "depth_ms": round((t2 - t1) * 1000, 2),
            "track_ms": round((t3 - t2) * 1000, 2),
        }
        return out


COLORS = {"approaching": (230, 40, 40), "receding": (60, 160, 255),
          "crossing_left": (255, 200, 0), "crossing_right": (255, 200, 0),
          "static": (200, 200, 200)}


def draw(frame_rgb, tracks, t, timing, width=960):
    h, w = frame_rgb.shape[:2]
    s = width / w
    img = cv2.resize(frame_rgb, (width, int(round(h * s / 2)) * 2), interpolation=cv2.INTER_AREA)
    H, W = img.shape[:2]
    for x in (0.35, 0.65):
        cv2.line(img, (int(x * W), 0), (int(x * W), H), (90, 90, 90), 1)
    for tr in tracks:
        x1, y1, x2, y2 = tr["box"]
        p1, p2 = (int(x1 * W), int(y1 * H)), (int(x2 * W), int(y2 * H))
        col = COLORS[tr["motion"]]
        cv2.rectangle(img, p1, p2, col, 3 if tr["dist_bucket"] == "near" else 2)
        d = "?" if tr["dist_m"] is None else f"{tr['dist_m']:.1f}m"
        ttc = f" ttc{tr['ttc_s']:.1f}" if tr["ttc_s"] is not None else ""
        lines = [f"#{tr['id']} {tr['cls']}", f"{tr['dist_bucket']} {d} {tr['motion']}{ttc}"]
        y = max(14, p1[1] - 20)
        for k, txt in enumerate(lines):
            (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            yy = y + k * 15
            cv2.rectangle(img, (p1[0], yy - th - 2), (p1[0] + tw + 2, yy + 2), (0, 0, 0), -1)
            cv2.putText(img, txt, (p1[0] + 1, yy), cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1,
                        cv2.LINE_AA)
    hud = (f"t={t:5.2f}s det {timing['detect_ms']:.0f}ms depth {timing['depth_ms']:.0f}ms "
           f"trk {timing['track_ms']:.0f}ms")
    cv2.rectangle(img, (0, 0), (W, 20), (0, 0, 0), -1)
    cv2.putText(img, hud, (4, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return img


def iter_frames(path, fps):
    import av
    with av.open(path) as c:
        st = c.streams.video[0]
        next_t = 0.0
        for fr in c.decode(st):
            if fr.pts is None:
                continue
            t = float(fr.pts * st.time_base)
            if t + 1e-6 < next_t:
                continue
            next_t += 1.0 / fps
            while next_t <= t:
                next_t += 1.0 / fps
            yield t, fr.to_ndarray(format="rgb24")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--fps", type=float, default=8.0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--no-video", action="store_true")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    stem = os.path.splitext(args.out)[0]
    if args.device.startswith("cuda"):
        torch.cuda.reset_peak_memory_stats()
    tl = time.perf_counter()
    p = Perception(device=args.device)
    load_s = time.perf_counter() - tl

    writer = None
    timings = []
    n = 0
    with open(args.out, "w") as f:
        for t, frame in iter_frames(args.video, args.fps):
            tracks = p.update(frame, t)
            f.write(json.dumps({"t": round(t, 3), "tracks": tracks, "timing": p.last_timing}) + "\n")
            timings.append(p.last_timing)
            n += 1
            if not args.no_video:
                img = draw(frame, tracks, t, p.last_timing)
                if writer is None:
                    writer = subprocess.Popen(
                        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo",
                         "-pix_fmt", "rgb24", "-s", f"{img.shape[1]}x{img.shape[0]}",
                         "-r", str(args.fps), "-i", "-", "-c:v", "libx264",
                         "-pix_fmt", "yuv420p", "-crf", "23", stem + "_annotated.mp4"],
                        stdin=subprocess.PIPE)
                writer.stdin.write(img.tobytes())
    if writer is not None:
        writer.stdin.close()
        writer.wait()

    steady = timings[3:] if len(timings) > 6 else timings  # first frames include cuDNN autotune
    summary = {"video": args.video, "frames": n, "fps": args.fps, "load_s": round(load_s, 2)}
    for k in ("detect_ms", "depth_ms", "track_ms"):
        v = np.array([x[k] for x in steady])
        summary[k] = {"median": round(float(np.median(v)), 2),
                      "p90": round(float(np.percentile(v, 90)), 2),
                      "max": round(float(v.max()), 2)}
    tot = np.array([sum(x.values()) for x in steady])
    summary["depth_scale_final"] = round(p.scale, 3)
    summary["depth_scale_samples"] = p.scale_samples
    summary["total_ms"] = {"median": round(float(np.median(tot)), 2),
                           "p90": round(float(np.percentile(tot, 90)), 2)}
    if args.device.startswith("cuda"):
        summary["peak_vram_mib"] = round(torch.cuda.max_memory_allocated() / 2**20, 1)
        summary["peak_reserved_mib"] = round(torch.cuda.max_memory_reserved() / 2**20, 1)
    with open(stem + "_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
