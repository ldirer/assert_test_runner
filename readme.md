
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




## Notes

This happens constantly:

    --> 150     compiled = compile(module, filename='<ast>', mode='exec')
    151     exec(compiled)

TypeError: required field "lineno" missing from expr

BEWARE: there's an error somewhere, but it's not necessarily about the lineno...



**Issue**: I try to print the exception I get but the ast-munging seems to have broken the traceback.

traceback.print_exception(a.__class__, a, a.__traceback__)






**Navigating tracebacks**

Use `tb_next` to go to the next level in the stack trace ('up').

Using e.__traceback__.tb_frame.f_back does not do the same thing.
I think it's because it's the frame BEFORE the code that caused the exception. So we are going up but we're already 'above' the exception.

So the variables we are interested in are in:

    e.__traceback__.tb_next.tb_frame.f_locals

Warning though: there could be more levels in the traceback (pbbly).


A convenient way using the `traceback` module from the standard lib:

    stack_summary = traceback.StackSummary.extract(traceback.walk_tb(e.__traceback__), capture_locals=True)


