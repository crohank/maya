def check(candidate):

    # Check some simple cases
    assert candidate([1, 7, 3, 6, 5, 6]) == 3, "Error"
    assert candidate([1, 2, 3]) == -1, "Error"
    assert candidate([]) == -1, "Error"
    assert candidate([5]) == 0, "Error"
    assert candidate([0, 0, 0]) == 0, "Error"
    assert candidate([2, 1, -1]) == 0, "Error"
    assert candidate([1, -1, 5]) == 2, "Error"
    assert candidate([-1, -1, -1, 0, 1, 1]) == 0, "Error"


check(balance_index)
