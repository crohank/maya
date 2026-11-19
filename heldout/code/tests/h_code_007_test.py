def check(candidate):

    # Check some simple cases
    assert candidate("") == 0, "Error"
    assert candidate("1h30m15s") == 5415, "Error"
    assert candidate("45s") == 45, "Error"
    assert candidate("2h") == 7200, "Error"
    assert candidate("90m") == 5400, "Error"
    assert candidate("1h5s") == 3605, "Error"
    assert candidate("10h0m1s") == 36001, "Error"
    assert candidate("0s") == 0, "Error"
    assert candidate("100m") == 6000, "Error"


check(parse_duration)
