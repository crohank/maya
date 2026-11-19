"""Walk mode v5: v3 with the side held back until it is knowable.

results/walk_v4_summary.md: the labelled person's own box gives the right side 19 to
24 of 29 times 1.5 s before contact but only 12 to 16 of 26 at 2.5 s, and v3 cues
fire 2 to 3 s out. v5 changes only when a side is given:
- Tones are centred (side "none", "something is coming") until the track's urgency
  is under commit_ttc. The first tone for a track is always centred.
- The first frame a track is under commit_ttc plays a panned tone at once (the
  "commit tone"); later repeats are panned on v3's schedule.
- Words name the side, so a word v3 would queue before commit is deferred until the
  track is under commit_ttc (still once per track, same conditions as v3).
- Crossing tracks carry the fixed v3 urgency (2.0 s) and are already close and in
  the corridor, so they commit at once.

Run inside maya-engine from the repo root (CPU, no network):
  python -I -B scripts/walk_v5.py internet   # thresholds on the 4 hand-labelled clips
  python -I -B scripts/walk_v5.py eval       # writes results/walk_v5.md
"""
import collections
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fused_harness as fh  # noqa: E402
import score_walk as sw  # noqa: E402
import score_walk_id as sid  # noqa: E402
import walk_v3 as w3  # noqa: E402
import walk_v4 as v4  # noqa: E402

# Internet clips (results/walk_v5.md): cues side right 2, 3, 4 of 29 at 1.0, 1.5, 2.0 s
# (v3 BASE 10), so 2.0 s, the least late, was picked before SANPO was scored.
COMMIT_TTC = 2.0
V5 = dict(w3.BASE, commit_ttc=COMMIT_TTC, first_centred=1)


def simulate(frames, cfg, voice):
    """walk_v3.simulate with the commit rule; returns (words, tones) as v3 does."""
    hist = collections.defaultdict(lambda: collections.deque(maxlen=cfg["window"]))
    worded, kind_last, last_tone = {}, {}, {}
    toned, committed = set(), set()
    pending, words, tones = [], [], []
    st = dict(voice_free=0.0, tone_free=0.0, last_text="", last_text_t=-99.0)

    def play_tone(t, c, kind, side):
        start = max(t, st["tone_free"])
        if cfg["single_channel"] and start < st["voice_free"]:
            start = st["voice_free"]
        e = dict(source="tone", ready=t, kind=kind, track=c["track"], cls=c["cls"], side=side,
                 urgency=c["urgency"], band=w3.band(c["urgency"], cfg), win_start=c["win_start"],
                 win_end=c["win_end"], X=c["X"])
        if start - t > cfg["tone_stale"]:
            e["status"] = "stale"
        else:
            e.update(status="tone", audio_start=start, audio_dur=cfg["tone_s"])
            st["tone_free"] = start + cfg["tone_s"] + cfg["tone_gap"]
            last_tone[c["track"]] = start
            toned.add(c["track"])
        tones.append(e)

    def drop(p, status):
        p["status"] = status
        words.append(p)
        if worded.get(p["track"]) == p["ready"]:
            worded.pop(p["track"])
        if kind_last.get(p["name"]) == p["ready"]:
            kind_last[p["name"]] = p["prev_kind"]

    def flush(now):
        while pending:
            T = max(st["voice_free"], min(p["ready"] for p in pending))
            if T > now:
                break
            fresh = []
            for p in [p for p in pending if p["ready"] <= T]:
                pending.remove(p)
                (drop(p, "stale") if T - p["ready"] > cfg["word_stale"] else fresh.append(p))
            if not fresh:
                continue
            pick = min(fresh, key=lambda p: p["urgency"])
            for p in fresh:
                if p is not pick:
                    drop(p, "stale")
            if pick["answer"].lower() == st["last_text"] and T - st["last_text_t"] < w3.SAME_TEXT_S:
                pick["status"] = "repeat"
                words.append(pick)
                if cfg["tones"]:
                    play_tone(T, pick, "repeat", pick["side"])
                continue
            (dur, syn, path), _ = voice.get(pick["answer"])
            start = T + syn
            if cfg["single_channel"]:
                start = max(start, st["tone_free"] - cfg["tone_gap"])
            pick.update(status="spoken", audio_start=start, audio_dur=dur, wav=str(path),
                        tts_s=syn, lag=start - pick["win_end"])
            words.append(pick)
            st["voice_free"] = start + dur
            st["last_text"], st["last_text_t"] = pick["answer"].lower(), pick["ready"]
            last_tone[pick["track"]] = start + dur

    for fr in frames:
        t = fr["t"]
        now = t + sum(fr.get("timing", {}).values()) / 1000.0
        flush(now)
        seen, cands = set(), []
        for tr in fr["tracks"]:
            u, horizon = w3.urgency(tr, cfg)
            hist[tr["id"]].append(u)
            seen.add(tr["id"])
            if u is not None and sum(k is not None for k in hist[tr["id"]]) >= cfg["confirm"]:
                cands.append((u, horizon, tr))
        for tid in list(hist):
            if tid not in seen:
                hist[tid].append(None)
        if not cands:
            continue
        u, horizon, tr = min(cands, key=lambda c: c[0])
        tid, name = tr["id"], fh.NAMES[tr["cls"]]
        crossing = tr["motion"].startswith("crossing")
        side = w3.side_of(tr, horizon, cfg)
        commit = crossing or u < cfg["commit_ttc"]
        newly = commit and tid not in committed
        if commit:
            committed.add(tid)
        verb = " crossing" if crossing else ""
        c = dict(source="fast", track=tid, cls=tr["cls"], name=name, side=side, urgency=u,
                 ready=now, win_start=max(0.0, t - cfg["window"] / 8), win_end=t,
                 answer=f"{name}{verb} {side}.", X=w3.predict(tr, horizon)[1],
                 raw=json.dumps({k: v for k, v in tr.items() if not k.startswith("_")}))
        veh = tr["cls"] in fh.VEHICLES
        want = commit and tid not in worded and (veh or now - kind_last.get(name, -99) > cfg["new_kind_s"]
                                                 or u < cfg["word_ttc"])
        if want:
            c["prev_kind"] = kind_last.get(name, -99)
            worded[tid] = now
            kind_last[name] = now
            pending.append(c)
            busy = st["voice_free"] > now + 0.05 or len(pending) > 1
            if cfg["tones"] and (cfg["lead_tone"] == "always" or (cfg["lead_tone"] == "busy" and busy)):
                first = cfg["first_centred"] and tid not in toned
                play_tone(now, c, "lead", "none" if first else side)
        elif cfg["tones"] and not any(p["track"] == tid for p in pending):
            first = cfg["first_centred"] and tid not in toned
            pan = commit and not first
            if (newly and not first) or now - last_tone.get(tid, -99) >= cfg["tone_repeat"][w3.band(u, cfg)]:
                play_tone(now, c, "commit" if newly and pan else "repeat" if tid in last_tone else "new",
                          side if pan else "none")
    flush(float("inf"))
    words.sort(key=lambda e: e["ready"])
    return words, tones


def run_sim(c, cfg, voice):
    sim = w3.simulate
    if "commit_ttc" in cfg:
        w3.simulate = simulate
    try:
        return v4.run_sim(c, cfg, voice)
    finally:
        w3.simulate = sim


def id_total(rows):
    s = v4.id_total(rows)
    pe = [p for r in rows for p in r["c"]["per_event"] if p["first"]]
    s["c"]["side_bearing"] = sum(p["side_bearing"] for p in pe)
    s["c"]["centred"] = sum(1 for p in pe if p["first"]["side"] == "none")
    return s


HEAD = ("| run | words on time | words side right | cues on time | first cue centred | "
        "side right, first side-bearing cue | side right, last cue | side right, first cue | "
        "cue spare median (s) | precision (within 5 m) | utt/min | tones/min |\n" + "|---" * 12 + "|")


def row(name, s):
    w, c = s["w"], s["c"]
    f = lambda a: f"{a}/{c['mw']}"
    return (f"| {name} | {f(w['on'])} | {f(w['side_first'])} | {f(c['on'])} | {c['centred']} | "
            f"{f(c['side_bearing'])} | {f(c['side_last'])} | {f(c['side_first'])} | {sw.num(c['spare'])} | "
            f"{v4.pct(c['rel'], c['n'])} | {s['utt_min']:.1f} | {s['tone_min']:.1f} |")


VARIANTS = [
    ("v3 BASE", dict(w3.BASE)),
    ("v5 commit 1.0 s", dict(V5, commit_ttc=1.0)),
    ("v5 commit 1.5 s", dict(V5, commit_ttc=1.5)),
    ("v5 commit 2.0 s", dict(V5, commit_ttc=2.0)),
    ("v5 commit 2.0 s, first tone panned when already under 2.0 s", dict(V5, first_centred=0)),
]


def cmd_internet():
    clips = v4.load_internet()
    voice = w3.Voice(fh.V2_LENGTH_SCALE)
    lines = [v4.CLS_HEAD]
    for name, cfg in VARIANTS:
        lines.append(v4.cls_row(name, w3.total([v4.class_score(c, *run_sim(c, cfg, voice)) for c in clips])))
        print(lines[-1], flush=True)
    return lines


def cmd_eval():
    voice = w3.Voice(fh.V2_LENGTH_SCALE)
    out = ["# Walk mode v5: side held back until close", "",
           "Generated by `python -I -B scripts/walk_v5.py eval` (maya-engine, CPU). Rules in the "
           "scripts/walk_v5.py docstring, scorer in scripts/score_walk_id.py. Centred tones carry "
           "side \"none\": they count as wrong for first-cue and last-cue side, and are skipped by "
           "the first side-bearing cue.", "",
           f"Commit threshold {COMMIT_TTC} s picked on the internet clips (best of the three, all below v3) before "
           "SANPO was scored.", "",
           "## Internet clips, class scorer (29 must_warn)", ""] + cmd_internet()
    sanpo = v4.load_sanpo()
    out += ["", "## SANPO, identity scorer (33 must_warn)", "", HEAD]
    for name, cfg in VARIANTS:
        runs = [run_sim(c, cfg, voice) for c in sanpo]
        out.append(row(name, id_total([v4.id_score(c, *r) for c, r in zip(sanpo, runs)])))
        print(out[-1], flush=True)
        if name in ("v3 BASE", "v5 commit 2.0 s"):
            rs = [(v4.shifted(ws, 7.0, c["dur"]), v4.shifted(ts, 7.0, c["dur"])) for c, (ws, ts) in zip(sanpo, runs)]
            out.append(row(f"{name}, shifted 7 s", id_total([v4.id_score(c, *r) for c, r in zip(sanpo, rs)])))
    Path("results/walk_v5.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("wrote results/walk_v5.md")


if __name__ == "__main__":
    {"internet": cmd_internet, "eval": cmd_eval}[sys.argv[1] if len(sys.argv) > 1 else "eval"]()
