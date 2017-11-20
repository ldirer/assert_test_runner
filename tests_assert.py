
from pprint import pprint
def add(x, y):
    return x + y


def test_add():
    # ok
    assert add(8, 6) == 14
    # nok
    a, b, result = 4, 6, 14
    assert add(a, b) == result


#if __name__ == '__main__':
#    print('__name__', __name__)
#    print('{:-^40}'.format('locals'))
#    pprint(locals())
#    test_add()
