def check(candidate):

    # Check some simple cases
    assert candidate([4, 1, 4, 3]) == 3, "Error"
    assert candidate([2, 2]) is None, "Error"
    assert candidate([]) is None, "Error"
    assert candidate([5]) is None, "Error"
    assert candidate([-1, -3, -2]) == -2, "Error"
    assert candidate([10, 9, 10, 9, 8]) == 9, "Error"
    assert candidate([0, 100]) == 0, "Error"
    assert candidate([1.5, 2.5, 2.5]) == 1.5, "Error"


check(second_largest_unique)
