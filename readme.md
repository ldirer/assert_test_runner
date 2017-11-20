
Objective: Write a simple pytest-like program that can run tests which use `assert` and provide useful information on `assert` failure.


## Why plain assert is bad


Traceback (most recent call last):
  File "tests_assert.py", line 15, in <module>
    test_add()
  File "tests_assert.py", line 11, in test_add
    assert add(a, b) == result
AssertionError

shell returned 1


--> Not the most helpful stacktrace. What is a? What is b? 

## What we want

We just want to have more information in the error message: What's the value of a? b? result?
Maybe even: How where they computed?





