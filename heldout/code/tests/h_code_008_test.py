def check(candidate):

    # Check some simple cases
    assert candidate([1, 2, 2, 3, 4, 1]) == 3, "Error"
    assert candidate([5, 4, 3]) == 1, "Error"
    assert candidate([]) == 0, "Error"
    assert candidate([7]) == 1, "Error"
    assert candidate([1, 2, 3, 4, 5]) == 5, "Error"
    assert candidate([3, 1, 2, 3, 0, 1]) == 3, "Error"
    assert candidate([-2, -1, 0, 0, 1]) == 3, "Error"
    assert candidate([1, 1, 1]) == 1, "Error"


check(longest_increasing_run)
