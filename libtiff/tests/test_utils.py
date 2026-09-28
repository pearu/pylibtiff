import optparse

import pytest

from libtiff.utils import bytes2str, Options, splitcommandline, splitquote


@pytest.mark.parametrize(
    ("nbytes", "expected"),
    [
        (0, '0 bytes'),
        (1, '1 bytes'),
        (1024, '1Ki bytes'),
        (1025, '1Ki+1 bytes'),
        (3 * 1024 ** 2 + 5, '3Mi+5 bytes'),
        (1024 ** 5 + 3 * 1024 ** 3, '1Pi+3Gi bytes'),
        (2 * 1024 ** 4, '2Ti bytes'),
    ]
)
def test_bytes2str(nbytes, expected):
    assert bytes2str(nbytes) == expected


def test_options():
    options = Options(a='abc', n=4)
    assert options.get(n=5) == 4
    # a missing option is added with the default value
    assert options.get(m=5) == 5
    assert options.m == 5
    # None values are replaced by the default
    options.k = None
    assert options.get(k=6) == 6

    shared = Options(options, x=1)
    assert shared.x == 1
    options.get(y=2)
    assert shared.y == 2

    values = optparse.Values({'a': 1})
    assert Options(values, b=2).__dict__ == {'a': 1, 'b': 2}
    assert Options(None).__dict__ == {}
    with pytest.raises(NotImplementedError):
        Options(1)
    with pytest.raises(NotImplementedError):
        Options(1, 2)


def test_splitcommandline():
    assert splitcommandline('a b "c d" e') == ['a', 'b', 'c d', 'e']
    assert splitcommandline("-i 'file name.tif' -o out.tif") == ['-i', 'file name.tif', '-o', 'out.tif']


def test_splitquote():
    assert splitquote('a "b c" d') == (['a ', '"b c"', ' d'], None)
    assert splitquote('A "B" c', lower=True) == (['a ', '"B"', ' c'], None)
    # an unterminated string returns the pending stop character
    assert splitquote('a "b c') == (['a ', '"b c'], '"')
    # continue a string started on a previous line
    assert splitquote('b" c', stopchar='"') == (['b"', ' c'], None)
