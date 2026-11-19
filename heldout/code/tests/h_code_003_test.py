def check(candidate):

    # Check some simple cases
    assert candidate([]) == [], "Error"
    assert candidate([[1, 3], [4, 6], [8, 9]]) == [[1, 6], [8, 9]], "Error"
    assert candidate([[5, 7], [1, 2]]) == [[1, 2], [5, 7]], "Error"
    assert candidate([[1, 10], [2, 3]]) == [[1, 10]], "Error"
    assert candidate([[3, 3], [1, 1], [2, 2]]) == [[1, 3]], "Error"
    assert candidate([[-5, -1], [0, 2], [10, 12], [11, 11]]) == [[-5, 2], [10, 12]], "Error"
    assert candidate([[1, 2], [4, 5]]) == [[1, 2], [4, 5]], "Error"


check(merge_ranges)
