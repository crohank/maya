import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.safety import SAFE_SUFFIX, safety_filter  # noqa: E402

UNSAFE = [
    "It is safe to cross.",
    "You can cross now.",
    "Go ahead.",
    "Keep straight, path ahead is clear of people.",
    "The road is clear.",
]

HARMLESS = [
    "Bus passing on your right.",
    "Person walking toward you, slightly left.",
    "The sign says M15 Select Bus, South Ferry.",
]


def test_unsafe_rewritten():
    for s in UNSAFE:
        out, flagged = safety_filter(s)
        assert flagged, s
        assert out == SAFE_SUFFIX, (s, out)


def test_unsafe_sentence_dropped_rest_kept():
    out, flagged = safety_filter("Car parked on your left. The road is clear.")
    assert flagged
    assert out == "Car parked on your left. " + SAFE_SUFFIX


def test_harmless_unchanged():
    for s in HARMLESS:
        out, flagged = safety_filter(s)
        assert not flagged, s
        assert out == s


if __name__ == "__main__":
    test_unsafe_rewritten()
    test_unsafe_sentence_dropped_rest_kept()
    test_harmless_unchanged()
    print("ok")


def test_advice_cut_description_kept():
    from app.safety import advice_filter
    cases = {
        "Yes, there's a construction zone ahead with orange and white barricades. Be cautious and follow the crosswalk.":
            "Yes, there's a construction zone ahead with orange and white barricades.",
        "The street is busy with traffic and pedestrians, so be cautious and watch for vehicles and people around you.":
            "The street is busy with traffic and pedestrians.",
        "Yes, there's a pedestrian zone ahead with specific rules and signs. Stay aware of your surroundings and follow the posted guidelines.":
            "Yes, there's a pedestrian zone ahead with specific rules and signs.",
    }
    for src, want in cases.items():
        out, flagged = advice_filter(src)
        assert flagged and out == want, (src, out)


def test_advice_leaves_descriptions():
    from app.safety import advice_filter
    for s in HARMLESS + ["A woman in a white top is walking toward you.", "The sign reads 42nd Street Passage."]:
        assert advice_filter(s) == (s, False), s
