"""Grid sweep of fast-path v2 thresholds against the strict scorer.

No rendering: Piper runs once per distinct phrase and durations are cached.
Same 4 clips and labels the thresholds are judged on, so the best row is tuned
to this set (see docs/decisions.md D9).

Run inside the maya-cosmos-tf container:
  python scripts/sweep_v2.py > results/sweep_v2.md
"""
import glob
import itertools
import json
import tempfile
from pathlib import Path

import fused_harness as fh
import live_harness as lh
import score_walk as sw


class CachedTts:
    def __init__(self, length_scale):
        self.tts = lh.Tts(length_scale)
        self.cache = {}
        self.tmp = tempfile.mkdtemp()

    def say(self, text, _path):
        if text not in self.cache:
            self.cache[text] = self.tts.say(text, f"{self.tmp}/x.wav")
        return self.cache[text]


def run(clips, tts):
    pe_all, relevant, spoken_n, minutes = [], 0, 0, 0.0
    for stem, frames, events, dur in clips:
        cands = fh.speak(fh.fast_candidates_v2(frames), tts, Path(tts.tmp), fh.V2_FAST_STALE_S)
        spoken = [dict(answer=e["answer"], t=e["audio_start"], t_end=e["audio_start"] + e["audio_dur"])
                  for e in cands if e["status"] == "spoken"]
        pe, rel = sw.strict_score(events, spoken)
        pe_all += pe
        relevant += rel
        spoken_n += len(spoken)
        minutes += dur / 60
    st = sw.strict_summary(pe_all, relevant, spoken_n)
    st["utt_min"] = spoken_n / minutes
    return st


def main():
    clips = []
    for lp in sorted(glob.glob("test_videos/labels/*.json")):
        stem = Path(lp).stem
        frames = [json.loads(line) for line in open(f"results/perception/{stem}.jsonl")]
        clips.append((stem, frames, sw.load_labels(lp), frames[-1]["t"]))
    tts = CachedTts(fh.V2_LENGTH_SCALE)
    grid = {
        "V2_TTC_S": [3.0, 4.0, 5.0],
        "V2_MIN_HEIGHT": [0.15, 0.25],
        "V2_GAP_S": [0.0, 1.5, 2.5],
        "V2_CENTRE": [(0.42, 0.58), (0.45, 0.55)],
    }
    print("| " + " | ".join(grid) + " | on time | on time, side | spare med | precision | utt/min |")
    print("|" + "---|" * (len(grid) + 5))
    for combo in itertools.product(*grid.values()):
        for k, v in zip(grid, combo):
            setattr(fh, k, v)
        st = run(clips, tts)
        print("| " + " | ".join(str(v) for v in combo) + f" | {st['on_time']}/{st['mw']} | "
              f"{st['on_time_side']}/{st['mw']} | {sw.num(st['spare_median'])} | "
              f"{st['relevant']}/{st['spoken']} | {st['utt_min']:.1f} |", flush=True)


if __name__ == "__main__":
    main()
