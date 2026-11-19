"""Score live-harness walk runs against hand labels.

Usage (inside the maya-cosmos-tf container, standard library only):
  python scripts/score_walk.py --labels test_videos/labels/<stem>.json \
      --log results/live/<run_dir>/log.csv [--log ...] --out results/walk_scores.md

--labels may be repeated. Each log is paired with the labels file whose stem is
the longest prefix of the log's run directory name; with one labels file every
log uses it. Writes the .md given by --out and a .csv next to it.

Rules:
- Only log rows with status == spoken count; those are what the user heard.
  Logs without a status column (older harness versions) are skipped.
- An utterance matches an event when audio_start is in
  [t_start, t_close + 1.0] and the answer mentions the event's class
  (CLASS_WORDS below, whole words, optional plural) or one of the event's
  optional "keywords" (extra words the annotator accepts, used mainly for
  cls "other").
- Hit: an event with at least one matching utterance. One utterance may hit
  several events whose windows overlap (no one-to-one assignment).
- Lead time = t_close - audio_start of the first matching utterance.
  Positive means the warning came before the event was nearest.
- Side is correct when the first matching utterance contains the label's side
  word: left, right, or for "ahead" any of ahead/front/center/straight.
- False alarm: a spoken utterance that matches no event.
- Utterances per minute = spoken rows / clip length, where clip length is the
  largest win_end in the log.
"""
import argparse
import csv
import json
import re
import statistics
import sys
from pathlib import Path

WINDOW_AFTER_CLOSE = 1.0

# Deviations from the plain word list in the task spec, both to stop distance
# phrases from matching: "step" is singular only, because the prompt phrases
# distance as "two steps ahead"; "can" counts only as "trash/garbage/waste can".
CLASS_WORDS = {
    "person": ["person", "persons", "pedestrian", "man", "men", "woman", "women",
               "people", "someone"],
    "car": ["car", "vehicle", "suv", "taxi", "taxis", "jeep"],
    "truck": ["truck", "pickup"],
    "bus": ["bus", "buses"],
    "pole": ["pole", "post", "lamp", "lamppost"],
    "trash_can": ["trash", "bin", "trash can", "garbage can", "waste can"],
    "sign": ["sign", "board"],
    "curb": ["curb", "kerb", "edge", "step"],
    "crosswalk": ["crosswalk", "crossing"],
    "bicycle": ["bike", "bicycle", "cyclist"],
    "stroller": ["stroller", "pram", "buggy"],
    "other": [],
}
NO_PLURAL = {"step", "people", "men", "women", "persons", "buses", "taxis"}
SIDE_WORDS = {"left": ["left"], "right": ["right"],
              "ahead": ["ahead", "front", "center", "centre", "straight"]}


def word_re(words):
    parts = []
    for w in words:
        w = re.escape(w.lower()).replace(r"\ ", r"\s+")
        parts.append(w if w in NO_PLURAL else w + "(?:s|es)?")
    return re.compile(r"\b(?:" + "|".join(parts) + r")\b") if parts else None


def mentions(answer, words):
    r = word_re(words)
    return bool(r and r.search(answer.lower()))


def load_labels(path):
    events = json.loads(Path(path).read_text(encoding="utf-8"))
    for e in events:
        e["words"] = CLASS_WORDS[e["cls"]] + list(e.get("keywords", []))
    return events


def load_log(path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        fields = rows[0].keys() if rows else []
    if "status" not in fields:
        return None, None
    clip_len = max(float(r["win_end"]) for r in rows)
    spoken = [r for r in rows if r["status"] == "spoken" and r.get("audio_start")]
    for r in spoken:
        r["t"] = float(r["audio_start"])
    return spoken, clip_len


def score(events, spoken):
    matches = {e["id"]: [] for e in events}
    fa = 0
    fa_no_class = 0
    all_words = [w for ws in CLASS_WORDS.values() for w in ws]
    for r in spoken:
        hit = False
        for e in events:
            if e["t_start"] <= r["t"] <= e["t_close"] + WINDOW_AFTER_CLOSE \
                    and mentions(r["answer"], e["words"]):
                matches[e["id"]].append(r)
                hit = True
        if not hit:
            fa += 1
            if not mentions(r["answer"], all_words):
                fa_no_class += 1
    per_event = []
    for e in events:
        m = sorted(matches[e["id"]], key=lambda r: r["t"])
        if m:
            first = m[0]
            lead = e["t_close"] - first["t"]
            side_ok = mentions(first["answer"], SIDE_WORDS[e["side"]])
        else:
            first, lead, side_ok = None, None, None
        per_event.append({"event": e, "first": first, "lead": lead, "side_ok": side_ok})
    return per_event, fa, fa_no_class


def summarize(per_event, n_spoken, fa, fa_no_class, minutes):
    mw = [p for p in per_event if p["event"]["must_warn"]]
    mw_hits = [p for p in mw if p["first"]]
    hits = [p for p in per_event if p["first"]]
    mw_leads = [p["lead"] for p in mw_hits]
    all_leads = [p["lead"] for p in hits]
    return {
        "events": len(per_event), "hits": len(hits),
        "must_warn": len(mw), "must_warn_hits": len(mw_hits),
        "lead_mw_median": statistics.median(mw_leads) if mw_leads else None,
        "lead_mw_min": min(mw_leads) if mw_leads else None,
        "lead_all_median": statistics.median(all_leads) if all_leads else None,
        "side_ok": sum(1 for p in hits if p["side_ok"]), "side_n": len(hits),
        "spoken": n_spoken, "false_alarms": fa, "fa_no_class": fa_no_class,
        "minutes": minutes,
        "utt_per_min": n_spoken / minutes if minutes else None,
    }


def frac(a, b):
    return f"{a}/{b} ({100 * a / b:.0f}%)" if b else "n/a (0 events)"


def num(x, fmt="{:+.1f}"):
    return "n/a" if x is None else fmt.format(x)


def pick_labels(run_name, label_paths):
    if len(label_paths) == 1:
        return label_paths[0]
    best = None
    for p in label_paths:
        stem = Path(p).stem
        if run_name.startswith(stem) and (best is None or len(stem) > len(Path(best).stem)):
            best = p
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", action="append", required=True)
    ap.add_argument("--log", action="append", required=True)
    ap.add_argument("--out", default="results/walk_scores.md")
    args = ap.parse_args()

    results, skipped = [], []
    for log in args.log:
        run_dir = Path(log).parent.name
        lp = pick_labels(run_dir, args.labels)
        if lp is None:
            skipped.append((log, "no labels file matches the run directory"))
            continue
        spoken, clip_len = load_log(log)
        if spoken is None:
            skipped.append((log, "no status column (older harness)"))
            continue
        clip = Path(lp).stem
        mode = run_dir[len(clip):].lstrip("_") or run_dir
        sources = sorted({r.get("source", "") for r in spoken} - {""})
        per_event, fa, fa_nc = score(load_labels(lp), spoken)
        s = summarize(per_event, len(spoken), fa, fa_nc, clip_len / 60.0)
        results.append({"run": run_dir, "mode": mode, "clip": clip, "s": s,
                        "per_event": per_event, "fa_nc": fa_nc,
                        "sources": {src: sum(1 for r in spoken if r.get("source") == src)
                                    for src in sources}})

    totals = {}
    for r in results:
        t = totals.setdefault(r["mode"], {"per_event": [], "spoken": 0, "fa": 0,
                                          "fa_nc": 0, "minutes": 0.0, "clips": 0})
        t["per_event"] += r["per_event"]
        t["spoken"] += r["s"]["spoken"]
        t["fa"] += r["s"]["false_alarms"]
        t["fa_nc"] += r["s"]["fa_no_class"]
        t["minutes"] += r["s"]["minutes"]
        t["clips"] += 1
    total_rows = [{"run": f"TOTAL {m} ({t['clips']} clips)", "mode": m, "clip": "all",
                   "s": summarize(t["per_event"], t["spoken"], t["fa"], t["fa_nc"], t["minutes"])}
                  for m, t in sorted(totals.items())]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    head = ["run", "clip", "spoken", "utt/min", "must_warn hits", "all-event hits",
            "lead median (must_warn)", "lead min (must_warn)", "lead median (all hits)",
            "side correct (hits)", "false alarms (no class word)"]
    lines = ["# Walk scores", "",
             "Hand labels from one annotator (test_videos/labels/README.md). "
             "Lead time in seconds, t_close minus first matching speech start; "
             "positive means warned before the event was nearest.", "",
             "Rules:", "",
             "- Only rows with status == spoken count.",
             f"- Match: audio_start in [t_start, t_close + {WINDOW_AFTER_CLOSE}] and the "
             "answer names the event's class (synonym table in scripts/score_walk.py) "
             "or one of its keywords. One utterance can hit several overlapping events.",
             "- Side: the first matching utterance contains the label side word "
             "(left, right, ahead/front/center/straight).",
             "- False alarm: spoken utterance matching no event. The bracketed count "
             "is how many of those name no labelled class at all (for example "
             "\"No obstacles in my path\").",
             "- utt/min uses the largest win_end in the log as clip length.", "",
             "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    csv_rows = []
    for r in results + total_rows:
        s = r["s"]
        lines.append("| " + " | ".join([
            r["run"], r["clip"], str(s["spoken"]), num(s["utt_per_min"], "{:.1f}"),
            frac(s["must_warn_hits"], s["must_warn"]), frac(s["hits"], s["events"]),
            num(s["lead_mw_median"]), num(s["lead_mw_min"]), num(s["lead_all_median"]),
            frac(s["side_ok"], s["side_n"]) if s["side_n"] else "n/a (no hits)",
            f"{s['false_alarms']} ({s['fa_no_class']})"]) + " |")
        csv_rows.append({"run": r["run"], "mode": r["mode"], "clip": r["clip"],
                         **{k: ("" if v is None else (round(v, 3) if isinstance(v, float) else v))
                            for k, v in s.items()},
                         "spoken_by_source": json.dumps(r.get("sources", {}))})

    lines += ["", "## Per-event detail", ""]
    for r in results:
        lines.append(f"### {r['run']}")
        lines.append("")
        lines.append("| id | cls | side | must_warn | t_start | t_close | first match | lead | side ok | answer |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for p in r["per_event"]:
            e, f = p["event"], p["first"]
            lines.append("| " + " | ".join([
                e["id"], e["cls"], e["side"], "yes" if e["must_warn"] else "no",
                f"{e['t_start']:.1f}", f"{e['t_close']:.1f}",
                f"{f['t']:.2f}" if f else "miss", num(p["lead"]),
                ("yes" if p["side_ok"] else "no") if f else "",
                f["answer"].replace("|", "/") if f else ""]) + " |")
        lines.append("")
    if skipped:
        lines += ["## Skipped logs", ""] + [f"- {p}: {why}" for p, why in skipped] + [""]

    out.write_text("\n".join(lines), encoding="utf-8")
    with open(out.with_suffix(".csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()) if csv_rows else ["run"])
        w.writeheader()
        w.writerows(csv_rows)
    for p, why in skipped:
        print(f"skipped {p}: {why}", file=sys.stderr)
    print(f"wrote {out} and {out.with_suffix('.csv')} ({len(results)} runs)")


if __name__ == "__main__":
    main()
