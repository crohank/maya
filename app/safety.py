"""Go/cross/clear filter, copied from scripts/live_harness.py (keep the two in sync)."""
import re

UNSAFE = re.compile(
    r"\b(safe to (cross|go|walk)|you can (cross|go)|go ahead|it'?s (clear|safe)|"
    r"cross now|start crossing|(path|way|road|street|coast)( ahead)? is clear)\b",
    re.I,
)
SAFE_SUFFIX = "I can describe what I see, but I can't tell you when it's safe."


# Soft advice Qwen3-VL added to "anything I should know ahead?" on real street video
# (2026-11-19): "Be cautious and follow the crosswalk.", "so be cautious and watch for
# vehicles", "follow the posted guidelines". Not a go/cross decision, so no disclaimer;
# the advice is cut and the description kept.
ADVICE = re.compile(
    r"\b(be (cautious|careful|aware|mindful|alert|safe)|stay (aware|alert|safe|cautious|careful|vigilant)|"
    r"watch (out|for)|look (out|both ways)|keep an eye|follow the|make sure|proceed with|you should|"
    r"you (may|might) want to|it'?s (best|advisable|important|wise) to|exercise caution|take care)\b",
    re.I,
)
ADVICE_JOIN = re.compile(r",?\s+(so|and|but|which means)\s+$|[,;:]\s*$", re.I)


def advice_filter(text):
    """Cut advice clauses from a description. Returns (text, flagged)."""
    if not ADVICE.search(text):
        return text, False
    kept = []
    for s in re.split(r"(?<=[.!?])\s+", text):
        m = ADVICE.search(s)
        if not m:
            kept.append(s)
            continue
        head = s[:m.start()]
        j = ADVICE_JOIN.search(head)
        if j and head[:j.start()].strip():
            kept.append(head[:j.start()].rstrip(" ,;:") + ".")
    return " ".join(kept).strip(), True


def safety_filter(text):
    """Drop sentences that imply a go/cross decision; append the fixed disclaimer.

    Returns (text, flagged).
    """
    if not UNSAFE.search(text):
        return text, False
    kept = [s for s in re.split(r"(?<=[.!?])\s+", text) if not UNSAFE.search(s)]
    return " ".join(kept + [SAFE_SUFFIX]).strip(), True
