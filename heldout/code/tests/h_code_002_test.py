def check(candidate):

    # Check some simple cases
    assert candidate(12345, 2) == 45123, "Error"
    assert candidate(1200, 1) == 120, "Error"
    assert candidate(12345, 5) == 12345, "Error"
    assert candidate(12345, 7) == 45123, "Error"
    assert candidate(7, 3) == 7, "Error"
    assert candidate(0, 4) == 0, "Error"
    assert candidate(90, 1) == 9, "Error"
    assert candidate(123, 0) == 123, "Error"
    assert candidate(1000, 3) == 1, "Error"


check(rotate_digits)
