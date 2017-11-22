
This is an attempt at writing a simple pytest-inspired program that can run tests which use plain `assert` while providing useful information on test failure.

## Why plain assert is bad

Here's the output of a (failing) test with `assert`:

    Traceback (most recent call last):
      File "tests_assert.py", line 15, in <module>
        test_add()
      File "tests_assert.py", line 11, in test_add
        assert add(a, b) == result
    AssertionError

--> Not the most helpful stacktrace. What is a? What is b? Why did our test fail?  

It's really hard to figure what has gone wrong without running the test again (and adding print statements/breakpoints).


## Run it

The only requirements is Python 3.6.

Try it with:

    python runner.py tests_assert.py
    
The output should show failing tests (this is good!) with individual test stacktraces that show us the values of 
our variables:


    Test test_add_and_square failed with the following stacktrace:
      Traceback (most recent call last):
      
        File "tests_assert.py", line 1, in <module>
      
        File "tests_assert.py", line 31, in test_add_and_square
          assert square(add(a, b)) == expected - 1
      
      AssertionError
      
    Where: 
      expected=25
      b=3
      a=2
      square(add(a, b))=25
      add(a, b)=5
      expected - 1=24
      
      
You can also try it with your own file(s) containing `test_*` functions at top-level. 
It will probably break though since I tested it in a limited number of cases ;).
