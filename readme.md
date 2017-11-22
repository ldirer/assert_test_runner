## Objective

Write a simple pytest-like program that can run tests which use plain `assert` and provide useful information on assertion error.


## Why plain assert is bad

Here's the output of a (failing) test with `assert`:

    Traceback (most recent call last):
      File "tests_assert.py", line 15, in <module>
        test_add()
      File "tests_assert.py", line 11, in test_add
        assert add(a, b) == result
    AssertionError

--> Not the most helpful stacktrace. What is a? What is b? 
It's really hard to figure what has gone wrong without running the test again (and adding print statements/breakpoints).

## What we want

We want tests with plain assert that give more information in the error message: values of a, b, result.


