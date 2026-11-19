def check(candidate):

    # Check some simple cases
    assert candidate("") == 0, "Error"
    assert candidate("Anna ate a banana") == 3, "Error"
    assert candidate("rhythm") == 0, "Error"
    assert candidate("Olive trees are everywhere") == 3, "Error"
    assert candidate("Echo, I see you!") == 2, "Error"
    assert candidate("UNIQUE idea.") == 2, "Error"
    assert candidate("a e i o u") == 5, "Error"
    assert candidate("   Area   ") == 1, "Error"
    assert candidate("...!") == 0, "Error"


check(count_vowel_words)
