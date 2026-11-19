def check(candidate):

    # Check some simple cases
    assert candidate([38, 11, 9, 5]) == [38, 11, 5, 9], "Error"
    assert candidate([-19, 4, 0]) == [0, -19, 4], "Error"
    assert candidate([]) == [], "Error"
    assert candidate([99, 18, 9]) == [99, 18, 9], "Error"
    assert candidate([123, 321, 12]) == [12, 123, 321], "Error"
    assert candidate([10, 100, 1000, 2]) == [10, 100, 1000, 2], "Error"
    assert candidate([7, -7, 16]) == [7, -7, 16], "Error"


check(sort_by_digital_root)
