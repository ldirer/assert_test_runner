
def add(x, y):
    return x + y


def square(a):
    return a ** 2


def test_plain_add():
    a, b = 4, 4
    # Ideally we want to see that a + b = 8 in the failure report!
    assert 9 == a + b


def test_add():
    # ok
    assert add(8, 6) == 14
    # nok
    a, b, result = 4, 6, 14
    assert add(a, b) == result


def test_square():
    assert square(10) == 100


def test_add_and_square():
    a, b = 2, 3
    expected = 25
    assert square(add(a, b)) == expected - 1


def test_nested_function():

    def test_this():
        a, b = 2, 2
        expected = 16
        assert square(add(a, b)) == expected - 1

    test_this()
