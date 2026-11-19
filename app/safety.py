"""Go/cross/clear filter, copied from scripts/live_harness.py (keep the two in sync)."""
import re

UNSAFE = re.compile(
    r"\b(safe to (cross|go|walk)|you can (cross|go)|go ahead|it'?s (clear|safe)|"
    r"cross now|start crossing|(path|way|road|street|coast)( ahead)? is clear)\b",
    re.I,
)
SAFE_SUFFIX = "I can describe what I see, but I can't tell you when it's safe."


def safety_filter(text):
    """Drop sentences that imply a go/cross decision; append the fixed disclaimer.

    Returns (text, flagged).
    """
    if not UNSAFE.search(text):
        return text, False
    kept = [s for s in re.split(r"(?<=[.!?])\s+", text) if not UNSAFE.search(s)]
    return " ".join(kept + [SAFE_SUFFIX]).strip(), True
