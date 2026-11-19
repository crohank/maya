"""Walk mode v4: v3 with a side rule chosen under identity-matched scoring.

Imports, never edits, scripts/fused_harness.py (v2), scripts/walk_v3.py (v3),
scripts/score_walk.py (class scorer) and scripts/score_walk_id.py (identity scorer).
Every utterance and tone carries the id of the track that triggered it: v3 logs it
already; for v2 it is read from the candidate's raw track json.

Run inside the maya-engine image from the repo root (CPU, no network):
  python -I -B scripts/walk_v4.py internet   # side rules on the 4 hand-labelled clips
  python -I -B scripts/walk_v4.py eval       # everything; writes results/walk_v4.md,
                                             # results/sanpo/walk_v4_events.md
"""
import collections
import glob
import json
import math
import random
import statistics
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fused_harness as fh  # noqa: E402
import score_walk as sw  # noqa: E402
import score_walk_id as sid  # noqa: E402
import walk_v3 as w3  # noqa: E402

V3_SIDE_OF = w3.side_of
SANPO_ASPECT = 1280 / 720

# Picked on the internet clips (a tie there) and by reasoning before SANPO was scored
# with it. On SANPO it lost to the v3 rule (9 vs 11 of 33 first-cue side right,
# results/walk_v4.md), so RECOMMENDED keeps v3's side rule.
V4 = dict(side="pred_full", side_cap=4.0)
RECOMMENDED = dict(w3.BASE)


def annotate_drift(frames, cfg):
    """Raw image drift of the box centre (_vraw, width fraction per s, expansion kept,
    camera yaw removed). Approaching at a fixed lateral offset moves a box outward,
    toward the side it passes on, so the expansion term is signal here, unlike in
    walk_v3.annotate."""
    hist = collections.defaultdict(collections.deque)
    for fr in frames:
        t = fr["t"]
        de = []
        for tr in fr["tracks"]:
            x1, y1, x2, y2 = tr["box"]
            cx = (x1 + x2) / 2
            q = hist[tr["id"]]
            q.append((t, cx, math.log(max(1e-6, ((x2 - x1) * (y2 - y1)) ** 0.5))))
            while q and t - q[0][0] > cfg["lat_window"] + 1e-6:
                q.popleft()
            tr["_vraw"] = None
            if len(q) >= 3 and q[-1][0] - q[0][0] >= 0.25:
                ts = [p[0] for p in q]
                v = w3.slope(ts, [p[1] for p in q])
                tr["_vraw"] = v
                if y2 - y1 >= 0.05:
                    de.append(v - (cx - 0.5) * w3.slope(ts, [p[2] for p in q]))
        yaw = statistics.median(de) if cfg["yaw_comp"] and len(de) >= 3 else 0.0
        for tr in fr["tracks"]:
            if tr["_vraw"] is not None:
                tr["_vraw"] -= yaw


def side_band(cx, band):
    return "left" if cx < band[0] else "right" if cx > band[1] else "ahead"


def side_of_v4(tr, horizon, cfg):
    s = cfg["side"]
    if s in ("v2", "pred"):
        return V3_SIDE_OF(tr, horizon, cfg)
    cx = (tr["box"][0] + tr["box"][2]) / 2
    band = cfg.get("side_band", fh.V2_CENTRE)
    if s == "pos":
        return side_band(cx, band)
    if s == "pred_full":
        cap = tr["_hcap"]
        tr["_hcap"] = cfg["side_cap"]
        try:
            return V3_SIDE_OF(tr, horizon, dict(cfg, side="pred"))
        finally:
            tr["_hcap"] = cap
    if s == "img_pred":
        return side_band(cx + (tr["_vraw"] or 0.0) * min(horizon, cfg["side_cap"]), band)
    if s in ("drift", "drift_world"):
        v = tr["_vraw"] if s == "drift" else tr["_lat"]
        if v is not None and abs(v) >= cfg["drift_min"]:
            return "left" if v < 0 else "right"
        return side_band(cx, band)
    raise ValueError(s)


w3.side_of = side_of_v4


def load_sanpo():
    clips = []
    for lp in sorted(glob.glob("data/sanpo/labels/sanpo_*.json")):
        if lp.endswith("_tracks.json"):
            continue
        stem = Path(lp).stem
        frames = [json.loads(line) for line in open(f"results/sanpo/perception/{stem}.jsonl")]
        clips.append(dict(stem=stem, frames=frames, events=sw.load_labels(lp), aspect=SANPO_ASPECT,
                          minutes=frames[-1]["t"] / 60, dur=frames[-1]["t"],
                          clip=sid.Clip(stem, frames)))
    return clips


def load_internet():
    clips = w3.load_clips()
    for c in clips:
        c["dur"] = c["frames"][-1]["t"]
    return clips


def side_word(answer):
    a = answer.lower()
    return next((s for s in ("left", "right", "ahead") if s in a), "none")


def run_sim(c, cfg, voice):
    """(words, tones) as spoken / played, each with kind, t, t_end, track, side."""
    frames = json.loads(json.dumps(c["frames"]))
    w3.annotate(frames, c["aspect"], cfg)
    annotate_drift(frames, cfg)
    words, tones = w3.simulate(frames, cfg, voice)
    ws = [dict(kind="word", t=w["audio_start"], t_end=w["audio_start"] + w["audio_dur"], track=w["track"],
               side=w["side"], answer=w["answer"], t_trig=w["win_end"], status="spoken",
               audio_start=w["audio_start"], audio_dur=w["audio_dur"])
          for w in words if w["status"] == "spoken"]
    ts = [dict(kind="tone", t=x["audio_start"], t_end=x["audio_start"] + x["audio_dur"], track=x["track"],
               side=x["side"], cls=x["cls"], answer=w3.tone_name(x), t_trig=x["win_end"], status="tone",
               audio_start=x["audio_start"], audio_dur=x["audio_dur"], band=x["band"])
          for x in tones if x["status"] == "tone"]
    return ws, ts


def run_v2(c, voice):
    cands = fh.speak(fh.fast_candidates_v2(c["frames"]), voice, Path(tempfile.mkdtemp()),
                     fh.V2_FAST_STALE_S)
    return [dict(kind="word", t=e["audio_start"], t_end=e["audio_start"] + e["audio_dur"],
                 track=json.loads(e["raw"])["id"], side=side_word(e["answer"]), answer=e["answer"],
                 t_trig=e["win_end"], status="spoken", audio_start=e["audio_start"],
                 audio_dur=e["audio_dur"])
            for e in cands if e["status"] == "spoken"], []


def shifted(ws, shift, dur):
    out = []
    for w in ws:
        t = (w["t"] + shift) % dur
        out.append(dict(w, t=t, t_end=t + w["t_end"] - w["t"], audio_start=t, t_trig=(w["t_trig"] + shift) % dur))
    return out


def other_track(ws, frames, rng):
    """Same times and sides, track swapped for another track of the same class that
    is in the trigger frame (box height >= 0.15). No other track: no credit."""
    by_t = {round(fr["t"], 3): fr for fr in frames}
    out = []
    for w in ws:
        fr = by_t.get(round(w["t_trig"], 3), {"tracks": []})
        me = next((tr for tr in fr["tracks"] if tr["id"] == w["track"]), None)
        cls = me["cls"] if me else "person"
        pool = [tr["id"] for tr in fr["tracks"] if tr["id"] != w["track"] and tr["cls"] == cls
                and tr["box"][3] - tr["box"][1] >= 0.15]
        out.append(dict(w, track=rng.choice(pool) if pool else -1))
    return out


def id_score(c, ws, ts):
    words = [dict(w) for w in ws]
    cues = [dict(w) for w in ws + ts]
    return dict(w=sid.score_clip(c["clip"], c["events"], words),
                c=sid.score_clip(c["clip"], c["events"], cues),
                n_words=len(ws), n_tones=len(ts), minutes=c["minutes"])


def class_score(c, ws, ts):
    return w3.score_run(c["events"], ws, ts, c["minutes"])


def id_total(rows):
    out = {}
    for key in ("w", "c"):
        pe = [p for r in rows for p in r[key]["per_event"]]
        hits = [p for p in pe if p["first"]]
        spare = [p["spare"] for p in hits]
        out[key] = dict(mw=len(pe), on=len(hits), side_first=sum(p["side_first"] for p in hits),
                        side_any=sum(p["side_any"] for p in pe),
                        side_last=sum(p["side_last"] for p in hits),
                        by_tone=sum(1 for p in hits if p["first"]["kind"] == "tone"),
                        spare=statistics.median(spare) if spare else None,
                        rel=sum(r[key]["rel"] for r in rows), must=sum(r[key]["must"] for r in rows),
                        n=sum(r[key]["n"] for r in rows),
                        reasons=sum((r[key]["reasons"] for r in rows), collections.Counter()))
    mins = sum(r["minutes"] for r in rows)
    out["utt_min"] = sum(r["n_words"] for r in rows) / mins
    out["tone_min"] = sum(r["n_tones"] for r in rows) / mins
    return out


def pct(a, b):
    return f"{a}/{b} ({100 * a / b:.0f}%)" if b else "n/a"


ID_HEAD = ("| run | words on time | words side right | cues on time | cues side right (first cue) | "
           "cues side right (last cue) | cues side right (any cue) | by tone | cue spare median (s) | precision (within 5 m) | "
           "must precision | utt/min | tones/min |\n" + "|---" * 13 + "|")


def id_row(name, s):
    w, c = s["w"], s["c"]
    f = lambda a, b: f"{a}/{b}"
    return (f"| {name} | {f(w['on'], w['mw'])} | {f(w['side_first'], w['mw'])} | {f(c['on'], c['mw'])} | "
            f"{f(c['side_first'], c['mw'])} | {f(c['side_last'], c['mw'])} | {f(c['side_any'], c['mw'])} | "
            f"{c['by_tone']} | "
            f"{sw.num(c['spare'])} | {pct(c['rel'], c['n'])} | {pct(c['must'], c['n'])} | "
            f"{s['utt_min']:.1f} | {s['tone_min']:.1f} |")


CLS_HEAD = ("| run | words on time | words side right | word precision | cues on time, side right | "
            "by word + by tone | tone precision | utt/min | tones/min |\n|---|---|---|---|---|---|---|---|---|")


def cls_row(name, s):
    f = lambda a, b: f"{a}/{b}"
    return (f"| {name} | {f(s['on_time'], s['mw'])} | {f(s['on_time_side'], s['mw'])} | {pct(*s['word_prec'])} | "
            f"{f(s['cued'], s['mw'])} | {s['cued_word']} + {s['cued_tone']} | {pct(*s['tone_prec'])} | "
            f"{s['utt_min']:.1f} | {s['tone_min']:.1f} |")


SIDE_VARIANTS = [
    ("v3 rule: metric X at contact, horizon capped 0.5 s, dead zone 0.25 m (v3 BASE)", {}),
    ("v2 rule: box centre now, ahead in 0.42 to 0.58", dict(side="v2")),
    ("box centre now, no ahead (split at 0.5)", dict(side="pos", side_band=(0.5, 0.5))),
    ("metric X at contact, full TTC horizon (cap 4 s)", dict(side="pred_full", side_cap=4.0)),
    ("metric X at contact, horizon cap 2 s", dict(side="pred_full", side_cap=2.0)),
    ("metric X at contact, full TTC, dead zone 0.4 m", dict(side="pred_full", side_cap=4.0, side_m=0.4)),
    ("metric X at contact, full TTC, no ahead", dict(side="pred_full", side_cap=4.0, side_m=0.0)),
    ("image centre at contact: centre + raw drift x TTC", dict(side="img_pred", side_cap=4.0)),
    ("drift direction (raw image drift >= 0.03 width/s), else box centre", dict(side="drift", drift_min=0.03)),
    ("drift direction >= 0.08 width/s, else box centre", dict(side="drift", drift_min=0.08)),
    ("world drift direction (v3 lateral rate >= 0.03), else box centre", dict(side="drift_world", drift_min=0.03)),
]


LEADS = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0)


def side_vs_lead(sanpo):
    """Each side rule applied to the box of the labelled instance itself (the box the
    mask assigns to the event's first member in that frame), tau seconds before its
    t_close, horizon = the track's TTC (tau when it has none). Independent of which
    cue the harness happened to fire."""
    lines = ["| rule | " + " | ".join(f"{l:.1f} s before" for l in LEADS) + " | swaps L/R (all leads) |",
             "|---" * (len(LEADS) + 2) + "|"]
    prepared = []
    for c in sanpo:
        frames = json.loads(json.dumps(c["frames"]))
        w3.annotate(frames, c["aspect"], w3.BASE)
        annotate_drift(frames, w3.BASE)
        boxes = {}
        for fr in frames:
            for tr in fr["tracks"]:
                boxes[round(fr["t"], 3), tr["id"]] = tr
        for e in c["events"]:
            if not e["must_warn"]:
                continue
            sem, inst, tc = sid.members(e)[0]
            seen = [(t, tid) for t, tid in c["clip"].by_inst.get((sem, inst), []) if t <= tc + 1e-6]
            prepared.append((e["side"], tc, seen, boxes))
    for name, over in SIDE_VARIANTS:
        cfg = dict(w3.BASE, **over)
        cells, swaps, n_all = [], 0, 0
        for lead in LEADS:
            ok = n = 0
            for side, tc, seen, boxes in prepared:
                near = [(abs(t - (tc - lead)), t, tid) for t, tid in seen if abs(t - (tc - lead)) <= 0.15]
                if not near:
                    continue
                _, t, tid = min(near)
                tr = boxes[round(t, 3), tid]
                got = side_of_v4(tr, tr["ttc_s"] if tr["ttc_s"] is not None else lead, cfg)
                n += 1
                ok += got == side
                swaps += {got, side} == {"left", "right"}
            n_all += n
            cells.append(f"{ok}/{n}")
        lines.append(f"| {name} | " + " | ".join(cells) + f" | {swaps}/{n_all} |")
    return lines


def cmd_internet(_):
    clips = load_internet()
    voice = w3.Voice(fh.V2_LENGTH_SCALE)
    lines = [CLS_HEAD]
    rows = [class_score(c, *run_v2(c, voice)) for c in clips]
    lines.append(cls_row("v2 (fused_harness, re-simulated)", w3.total(rows)))
    for name, over in SIDE_VARIANTS:
        cfg = dict(w3.BASE, **over)
        rows = [class_score(c, *run_sim(c, cfg, voice)) for c in clips]
        lines.append(cls_row(name, w3.total(rows)))
        print(lines[-1], flush=True)
    return lines


def oracle_side(c, p):
    """Side of the matched track's last box at or before the member's t_close
    (frame thirds, as the label): can the track geometry give the label side at all?"""
    tracks = set(p["matched"])
    last = None
    for fr in c["frames"]:
        if fr["t"] > p["deadline"] + 1e-6:
            break
        for tr in fr["tracks"]:
            if tr["id"] in tracks:
                last = tr
    if not last:
        return None
    return side_band((last["box"][0] + last["box"][2]) / 2, (1 / 3, 2 / 3))


def cmd_eval(_):
    voice = w3.Voice(fh.V2_LENGTH_SCALE)
    out = ["# Walk mode v4: identity-matched scoring and side rules", "",
           "Generated by `python -I -B scripts/walk_v4.py eval` (maya-engine, CPU). "
           "Scorer rules: scripts/score_walk_id.py docstring.", ""]
    sanpo = load_sanpo()

    out += ["## Box-mask alignment", "",
            "Median best rect IoU per perception box against SANPO instance masks, with the mask "
            "frame offset from round(t x fps). Offset 0 is the best in every clip; mirrored boxes "
            "(x to 1 - x) are the no-alignment reference. Last column: boxes assigned to an instance "
            f"(IoU >= {sid.MIN_IOU}).", ""] + sid.cmd_check() + [""]

    cov = []
    for c in sanpo:
        pe = sid.score_clip(c["clip"], c["events"], [])["per_event"]
        cov += [len(p["matched"]) > 0 for p in pe]
    out += [f"must_warn events with at least one matched track: {sum(cov)}/{len(cov)} "
            "(the identity ceiling for any rule on this tracker).", ""]

    systems = [("v2 (fused_harness defaults)", None),
               ("v3 (walk_v3 BASE)", dict(w3.BASE)),
               (f"v4 pick (v3 BASE + {json.dumps(V4)})", dict(w3.BASE, **V4))]
    sims = {}
    for name, cfg in systems:
        sims[name] = [run_v2(c, voice) if cfg is None else run_sim(c, cfg, voice) for c in sanpo]

    out += ["## Shifted and swapped baselines (SANPO, identity scorer)", "",
            "Same warnings moved in time by 7 s or 13 s (wrapping at clip end), or kept in time with the "
            "track id swapped for a random other person track in the trigger frame (mean of 20 seeds). "
            "If the scorer were fooled by talking often, these would score close to the real run.", "",
            ID_HEAD]
    shift_cls = ["", "Class scorer (score_walk.py strict table, words only) on the same runs, for contrast:", "",
                 "| run | words on time | words side right | word precision |", "|---|---|---|---|"]
    for name, _ in systems:
        runs = sims[name]
        out.append(id_row(f"{name}, real", id_total([id_score(c, *r) for c, r in zip(sanpo, runs)])))
        s = w3.total([class_score(c, *r) for c, r in zip(sanpo, runs)])
        shift_cls.append(f"| {name}, real | {s['on_time']}/{s['mw']} | {s['on_time_side']}/{s['mw']} | "
                         f"{pct(*s['word_prec'])} |")
        for sh in (7.0, 13.0):
            rs = [(shifted(ws, sh, c["dur"]), shifted(ts, sh, c["dur"])) for c, (ws, ts) in zip(sanpo, runs)]
            out.append(id_row(f"{name}, shifted {sh:.0f} s", id_total([id_score(c, *r) for c, r in zip(sanpo, rs)])))
            s = w3.total([class_score(c, *r) for c, r in zip(sanpo, rs)])
            shift_cls.append(f"| {name}, shifted {sh:.0f} s | {s['on_time']}/{s['mw']} | "
                             f"{s['on_time_side']}/{s['mw']} | {pct(*s['word_prec'])} |")
        acc = collections.defaultdict(list)
        for seed in range(20):
            rng = random.Random(seed)
            rs = [(other_track(ws, c["frames"], rng), other_track(ts, c["frames"], rng))
                  for c, (ws, ts) in zip(sanpo, runs)]
            s = id_total([id_score(c, *r) for c, r in zip(sanpo, rs)])
            for k in ("w", "c"):
                for f in ("on", "side_first", "rel", "n"):
                    acc[k, f].append(s[k][f])
        m = {k: statistics.mean(v) for k, v in acc.items()}
        out.append(f"| {name}, other track (20 seeds) | {m['w', 'on']:.1f} | {m['w', 'side_first']:.1f} | "
                   f"{m['c', 'on']:.1f} | {m['c', 'side_first']:.1f} | | | | | "
                   f"{m['c', 'rel']:.1f}/{m['c', 'n']:.0f} | | | |")
    out += shift_cls + [""]

    out += ["## Comparison", "",
            "### SANPO, identity scorer (11 clips, 5.5 min, 33 must_warn, all people)", "", ID_HEAD]
    for name, _ in systems:
        out.append(id_row(name, id_total([id_score(c, *r) for c, r in zip(sanpo, sims[name])])))
    out += ["", "### SANPO, class scorer (for contrast with docs/sanpo_eval.md)", "", CLS_HEAD]
    for name, _ in systems:
        out.append(cls_row(name, w3.total([class_score(c, *r) for c, r in zip(sanpo, sims[name])])))
    internet = load_internet()
    out += ["", "### Internet clips, class scorer (4 clips, 2.0 min, 29 must_warn, hand labels; no masks, so "
            "no identity scoring here)", "", CLS_HEAD]
    for name, cfg in systems:
        rows = [class_score(c, *(run_v2(c, voice) if cfg is None else run_sim(c, cfg, voice))) for c in internet]
        out.append(cls_row(name, w3.total(rows)))

    out += ["", "## Side rules", "",
            "All on v3 BASE, only the side rule changes. Words take the side at the trigger frame; "
            "each tone takes it at its own frame.", "",
            "### Internet clips, class scorer (used to pick the v4 rule)", ""] + cmd_internet(None)
    out += ["", "### SANPO, identity scorer (measured after the pick)", "", ID_HEAD]
    side_rows = {}
    for name, over in SIDE_VARIANTS:
        cfg = dict(w3.BASE, **over)
        rows = [id_score(c, *run_sim(c, cfg, voice)) for c in sanpo]
        side_rows[name] = rows
        out.append(id_row(name, id_total(rows)))
        print(out[-1], flush=True)

    out += ["", "### SANPO, side of the labelled person's own box by time before t_close", "",
            "Correct / events where the instance has a matched box within 0.15 s of that time. "
            "Labels: 23 left, 9 right, 1 ahead.", ""] + side_vs_lead(sanpo)

    split_a = {c["stem"] for i, c in enumerate(sanpo) if i % 2 == 0}
    out += ["", "### SANPO split (clips 1, 3, 5, ... = A; 2, 4, 6, ... = B), cues side right (first cue)", "",
            "A rule picked on A should hold up on B if the difference is real.", "",
            "| rule | A | B |", "|---|---|---|"]
    for name, rows in side_rows.items():
        a = id_total([r for r, c in zip(rows, sanpo) if c["stem"] in split_a])["c"]
        b = id_total([r for r, c in zip(rows, sanpo) if c["stem"] not in split_a])["c"]
        out.append(f"| {name} | {a['side_first']}/{a['mw']} (on time {a['on']}) | "
                   f"{b['side_first']}/{b['mw']} (on time {b['on']}) |")

    out += ["", "## Scorer sensitivity (SANPO, cues)", "",
            "Box-instance IoU threshold and minimum assigned frames. Default 0.25 and 2.", "",
            "| IoU, frames | v2 cues on time | v2 side right (first) | v2 precision | v3 cues on time | "
            "v3 side right (first) | v3 precision | v3 shifted 7 s on time |", "|---" * 8 + "|"]
    saved = sid.MIN_IOU, sid.MIN_FRAMES
    for iou in (0.15, 0.25, 0.35):
        for mf in (1, 2, 3):
            sid.MIN_IOU, sid.MIN_FRAMES = iou, mf
            for c in sanpo:
                c["clip"] = sid.Clip(c["stem"], c["frames"])
            a = id_total([id_score(c, *r) for c, r in zip(sanpo, sims[systems[0][0]])])["c"]
            b = id_total([id_score(c, *r) for c, r in zip(sanpo, sims[systems[1][0]])])["c"]
            sh = [(shifted(ws, 7.0, c["dur"]), shifted(ts, 7.0, c["dur"])) for c, (ws, ts) in zip(sanpo, sims[systems[1][0]])]
            s7 = id_total([id_score(c, *r) for c, r in zip(sanpo, sh)])["c"]
            out.append(f"| {iou}, {mf} | {a['on']} | {a['side_first']} | {pct(a['rel'], a['n'])} | {b['on']} | "
                       f"{b['side_first']} | {pct(b['rel'], b['n'])} | {s7['on']} |")
    sid.MIN_IOU, sid.MIN_FRAMES = saved
    for c in sanpo:
        c["clip"] = sid.Clip(c["stem"], c["frames"])

    # Per-event detail and side confusion for v3 and v4.
    ev = ["# Walk v4: SANPO per-event detail (identity scorer, cues)", ""]
    conf_lines = []
    for name, _ in systems:
        conf = collections.Counter()
        orc = collections.Counter()
        ev += [f"## {name}", "", "| clip | id | side | t_close | matched tracks | first cue | its side | "
               "track side at t_close |", "|---|---|---|---|---|---|---|---|"]
        for c, r in zip(sanpo, sims[name]):
            res = sid.score_clip(c["clip"], c["events"], [dict(w) for w in r[0] + r[1]])
            for p in res["per_event"]:
                e, f = p["event"], p["first"]
                o = oracle_side(c, p) if p["matched"] else None
                if o:
                    orc[e["side"], o] += 1
                if f:
                    conf[e["side"], f["side"]] += 1
                ev.append(f"| {c['stem']} | {e['id']} | {e['side']} | {e['t_close']:.2f} | "
                          f"{','.join(map(str, p['matched'])) or 'none'} | "
                          + (f"{f['kind']} {f['t']:.2f}-{f['t_end']:.2f} #{f['track']} {f['answer']}" if f else "miss")
                          + f" | {f['side'] if f else ''} | {o or ''} |")
        ev.append("")
        conf_lines += [f"{name}: label side -> first credited cue side: "
                       + ", ".join(f"{a}->{b} {n}" for (a, b), n in sorted(conf.items())),
                       f"  label side -> matched track's last box side at or before t_close (frame thirds): "
                       + ", ".join(f"{a}->{b} {n}" for (a, b), n in sorted(orc.items())), ""]
    reasons = id_total([id_score(c, *r) for c, r in zip(sanpo, sims[systems[2][0]])])["c"]["reasons"]
    out += ["", "## Side confusion on SANPO (cues credited by identity)", ""] + conf_lines
    out += ["Why v4 cues are not relevant (precision breakdown): "
            + ", ".join(f"{k} {v}" for k, v in reasons.most_common()), ""]
    Path("results/walk_v4.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    Path("results/sanpo/walk_v4_events.md").write_text("\n".join(ev) + "\n", encoding="utf-8")
    print("wrote results/walk_v4.md, results/sanpo/walk_v4_events.md")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "eval"
    if cmd == "internet":
        print("\n".join(cmd_internet(None)))
    else:
        cmd_eval(None)


if __name__ == "__main__":
    main()
