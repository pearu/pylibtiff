"""
Tests for bitarray

Author: Ilan Schnell
"""
import os
import sys
import unittest
import tempfile
import shutil
from random import randint
from io import StringIO


if __name__ == '__main__':
    from __init__ import bitarray, bits2bytes
    repr_type = "<class '__init__.bitarray'>"
else:
    from bitarray import bitarray, bits2bytes
    repr_type = "<class 'bitarray.bitarray'>"


tests = []


class Util(object):

    def randombitarrays(self):
        for n in range(25) + [randint(1000, 2000)]:
            yield bitarray([randint(0, 1) for d in range(n)],
                           endian='big' if randint(0, 1) else 'little')

    def randomlists(self):
        for n in range(25) + [randint(1000, 2000)]:
            yield [bool(randint(0, 1)) for d in range(n)]

    def rndsliceidx(self, length):
        return randint(-2*length, 2*length-1) if randint(0, 1) == 1 else None

    def slicelen(self, r, length):
        return getIndicesEx(r, length)[-1]

    def check_obj(self, a):
        self.assertEqual(repr(type(a)), repr_type)
        unused = 8 * a.buffer_info()[1] - len(a)
        self.assert_(0 <= unused < 8)
        self.assertEqual(unused, a.buffer_info()[3])

    def assertEQUAL(self, a, b):
        self.assertEqual(a, b)
        self.assertEqual(a.endian(), b.endian())
        self.check_obj(a)
        self.check_obj(b)


def getIndicesEx(r, length):
    if not isinstance(r, slice):
        raise TypeError("slice object expected")
    start = r.start
    stop  = r.stop
    step  = r.step
    if r.step is None:
        step = 1
    else:
        if step == 0:
            raise ValueError("slice step cannot be zero")

    defstart = length-1 if step < 0 else 0
    defstop  = -1 if step < 0 else length

    if r.start is None:
        start = defstart
    else:
        if start < 0: start += length
        if start < 0: start = -1 if step < 0 else 0
        if start >= length: start = length-1 if step < 0 else length

    if r.stop is None:
        stop = defstop
    else:
        if stop < 0: stop += length
        if stop < 0: stop = -1
        if stop > length: stop = length

    if (step < 0 and stop >= length) or (step > 0 and start >= stop):
        slicelength = 0
    elif step < 0:
        slicelength = (stop-start+1) / step + 1
    else:
        slicelength = (stop-start-1) / step + 1

    if slicelength < 0:
        slicelength = 0

    return start, stop, step, slicelength

# ---------------------------------------------------------------------------

class TestsModuleFunctions(unittest.TestCase, Util):

    def test_bits2bytes(self):
        for arg in ['foo', [], None, {}]:
            self.assertRaises(TypeError, bits2bytes, arg)

        self.assertRaises(TypeError, bits2bytes)
        self.assertRaises(TypeError, bits2bytes, 1, 2)

        self.assertRaises(ValueError, bits2bytes, -1)
        self.assertRaises(ValueError, bits2bytes, -924)

        for n in range(1000):
            self.assertEqual(bits2bytes(n),
                             0 if n==0 else ((n - 1) / 8 + 1));

        for n, m in [(0, 0), (1, 1), (2, 1), (7, 1), (8, 1), (9, 2),
                     (10, 2), (15, 2), (16, 2), (64, 8), (65, 9),
                     (0, 0), (1, 1), (65, 9), (2**29, 2**26),
                     (2**31, 2**28), (2**32, 2**29), (2**34, 2**31),
                     (2**34+793, 2**31+100), (2**35-8, 2**32-1),
                     (2**62, 2**59), (2**63-8, 2**60-1)]:
            self.assertEqual(bits2bytes(n), m)


tests.append(TestsModuleFunctions)

# ---------------------------------------------------------------------------

class CreateObjectTests(unittest.TestCase, Util):

    def test_noInitializer(self):
        a = bitarray()
        self.assertEqual(len(a), 0)
        self.assertEqual(a.tolist(), [])
        self.check_obj(a)

    def test_endian(self):
        a = bitarray(endian='little')
        a.fromstring('A')
        self.assertEqual(a.endian(), 'little')
        self.check_obj(a)

        b = bitarray(endian='big')
        b.fromstring('A')
        self.assertEqual(b.endian(), 'big')
        self.check_obj(b)

        self.assertEqual(a.tostring(), b.tostring())

        a = bitarray(endian=u'little')
        a.fromstring(' ')
        self.assertEqual(a.endian(), 'little')
        self.check_obj(a)

        b = bitarray(endian=u'big')
        b.fromstring(' ')
        self.assertEqual(b.endian(), 'big')
        self.check_obj(b)

        self.assertEqual(a.tostring(), b.tostring())

        self.assertRaises(TypeError, bitarray.__new__, bitarray, endian=0)
        self.assertRaises(ValueError, bitarray.__new__, bitarray, endian='')

    def test_integers(self):
        for n in range(50):
            a = bitarray(n)
            self.assertEqual(len(a), n)
            self.check_obj(a)

            a = bitarray(int(n))
            self.assertEqual(len(a), n)
            self.check_obj(a)

        self.assertRaises(ValueError, bitarray.__new__, bitarray, -1)
        self.assertRaises(ValueError, bitarray.__new__, bitarray, -924)

    def test_list(self):
        lst = ['foo', None, [1], {}]
        a = bitarray(lst)
        self.assertEqual(a.tolist(), [True, False, True, False])
        self.check_obj(a)

        for n in range(50):
            lst = [bool(randint(0, 1)) for d in range(n)]
            a = bitarray(lst)
            self.assertEqual(a.tolist(), lst)
            self.check_obj(a)

    def test_tuple(self):
        tup = ('', True, [], {1:2})
        a = bitarray(tup)
        self.assertEqual(a.tolist(), [False, True, False, True])
        self.check_obj(a)

        for n in range(50):
            lst = [bool(randint(0, 1)) for d in range(n)]
            a = bitarray(tuple(lst))
            self.assertEqual(a.tolist(), lst)
            self.check_obj(a)

    def test_iter(self):
        for n in range(50):
            lst = [bool(randint(0, 1)) for d in range(n)]
            a = bitarray(iter(lst))
            self.assertEqual(a.tolist(), lst)
            self.check_obj(a)

    def test_iter2(self):
        for lst in self.randomlists():
            def foo():
                for x in lst:
                    yield x
            a = bitarray(foo())
            self.assertEqual(a, bitarray(lst))
            self.check_obj(a)

    def test_01(self):
        a = bitarray('0010111')
        self.assertEqual(a.tolist(), [0, 0, 1, 0, 1, 1, 1])
        self.check_obj(a)

        for n in range(50):
            lst = [bool(randint(0, 1)) for d in range(n)]
            s = ''.join('1' if x else '0' for x in lst)
            a = bitarray(s)
            self.assertEqual(a.tolist(), lst)
            self.check_obj(a)

        self.assertRaises(ValueError, bitarray.__new__, bitarray, '01012100')


    def test_bitarray(self):
        for n in range(50):
            a = bitarray(n)
            b = bitarray(a)
            self.assert_(a is not b)
            self.assertEQUAL(a, b)

        for end in ('little', 'big'):
            a = bitarray(endian=end)
            c = bitarray(a)
            self.assertEqual(c.endian(), end)
            c = bitarray(a, endian='little')
            self.assertEqual(c.endian(), 'little')
            c = bitarray(a, endian='big')
            self.assertEqual(c.endian(), 'big')


    def test_None(self):
        self.assertEQUAL(bitarray(), bitarray(0))
        self.assertEQUAL(bitarray(), bitarray(None))


    def test_WrongArgs(self):
        self.assertRaises(TypeError, bitarray.__new__, bitarray, 'A', 42, 69)

        self.assertRaises(TypeError, bitarray.__new__, bitarray, Ellipsis)
        self.assertRaises(TypeError, bitarray.__new__, bitarray, slice(0))

        self.assertRaises(TypeError, bitarray.__new__, bitarray, 2.345)
        self.assertRaises(TypeError, bitarray.__new__, bitarray, 4+3j)

        self.assertRaises(TypeError, bitarray.__new__, bitarray, '', 0, 42)
        self.assertRaises(ValueError, bitarray.__new__, bitarray, 0, 'foo')


tests.append(CreateObjectTests)

# ---------------------------------------------------------------------------

class MetaDataTests(unittest.TestCase):

    def test_buffer_info(self):
        a = bitarray('0000111100001', endian='little')
        self.assertEqual(a.buffer_info()[1:4], (2, 'little', 3))

        a = bitarray()
        self.assertRaises(TypeError, a.buffer_info, 42)

        bi = a.buffer_info()
        self.assert_(isinstance(bi, tuple))
        self.assertEqual(len(bi), 5)

        self.assert_(isinstance(bi[0], int))
        self.assert_(isinstance(bi[1], int))
        self.assert_(isinstance(bi[2], str))
        self.assert_(isinstance(bi[3], int))
        self.assert_(isinstance(bi[4], int))

        for n in range(50):
            bi = bitarray(n).buffer_info()
            self.assertEqual(bi[1], bits2bytes(n))
            self.assertEqual(bi[3] + n, 8 * bi[1])
            self.assert_(bi[4] >= bi[1])

        a = bitarray(endian='little')
        self.assertEqual(a.buffer_info()[2], 'little')

        a = bitarray(endian='big')
        self.assertEqual(a.buffer_info()[2], 'big')


    def test_endian(self):
        a = bitarray(endian='little')
        self.assertEqual(a.endian(), 'little')

        a = bitarray(endian='big')
        self.assertEqual(a.endian(), 'big')


    def test_length(self):
        for n in range(1000):
            a = bitarray(n)
            self.assertEqual(len(a), n)
            self.assertEqual(a.length(), n)


tests.append(MetaDataTests)

# ---------------------------------------------------------------------------

class SliceTests(unittest.TestCase, Util):

    def test_getitem(self):
        a = bitarray()
        self.assertRaises(IndexError, a.__getitem__,  0)
        a.append(True)
        self.assertEqual(a[0], True)
        self.assertRaises(IndexError, a.__getitem__,  1)
        self.assertRaises(IndexError, a.__getitem__, -2)

        a.append(False)
        self.assertEqual(a[1], False)
        self.assertRaises(IndexError, a.__getitem__,  2)
        self.assertRaises(IndexError, a.__getitem__, -3)

        a = bitarray('1100010')
        for i, b in enumerate([True, True, False, False, False, True, False]):
            self.assertEqual(a[i], b)
            self.assertEqual(a[i-7], b)
        self.assertRaises(IndexError, a.__getitem__,  7)
        self.assertRaises(IndexError, a.__getitem__, -8)

        a = bitarray('0100000100001')
        self.assertEQUAL(a[:], a)
        self.assert_(a[:] is not a)
        aa = a.tolist()
        self.assertEQUAL(a[11:2:-3], bitarray(aa[11:2:-3]))
        self.check_obj(a[:])

        self.assertRaises(ValueError, a.__getitem__, slice(None, None, 0))
        self.assertRaises(TypeError, a.__getitem__, (1, 2))

        for a in self.randombitarrays():
            aa = a.tolist()
            la = len(a)
            if la == 0: continue
            for dum in range(10):
                step = self.rndsliceidx(la)
                if step == 0: step = None
                s = slice(self.rndsliceidx(la),
                          self.rndsliceidx(la), step)
                self.assertEQUAL(a[s], bitarray(aa[s], endian=a.endian()))

    def test_setitem(self):
        a = bitarray([False])
        a[0] = 1
        self.assertEqual(a.tolist(), [True])

        a = bitarray(2)
        a[0] = 0
        a[1] = 1
        self.assertEqual(a.tolist(), [False, True])
        a[-1] = 0
        a[-2] = 1
        self.assertEqual(a.tolist(), [True, False])

        self.assertRaises(IndexError, a.__setitem__,  2, True)
        self.assertRaises(IndexError, a.__setitem__, -3, False)

        for a in self.randombitarrays():
            la = len(a)
            if la == 0:
                continue
            i = randint(0, la-1)
            aa = a.tolist()
            ida = id(a)
            val = bool(randint(0, 1))
            a[i] = val
            aa[i] = val
            self.assertEqual(a.tolist(), aa)
            self.assertEqual(id(a), ida)
            self.check_obj(a)

            b = bitarray(la)
            b[0:la] = bitarray(a)
            self.assertEqual(a, b)
            self.assertNotEqual(id(a), id(b))

            b = bitarray(la)
            b[:] = bitarray(a)
            self.assertEqual(a, b)
            self.assertNotEqual(id(a), id(b))

            b = bitarray(la)
            b[::-1] = bitarray(a)
            self.assertEqual(a.tolist()[::-1], b.tolist())

        a = bitarray(5*[False])
        a[0] = 1
        a[-2] = 1
        self.assertEqual(a, bitarray('10010'))
        self.assertRaises(IndexError, a.__setitem__,  5, 'foo')
        self.assertRaises(IndexError, a.__setitem__, -6, 'bar')

        for a in self.randombitarrays():
            la = len(a)
            if la == 0: continue
            for dum in range(3):
                step = self.rndsliceidx(la)
                if step == 0: step = None
                s = slice(self.rndsliceidx(la),
                          self.rndsliceidx(la), step)
                for b in self.randombitarrays():
                    if len(b) == self.slicelen(s, len(a)) or step is None:
                        c = bitarray(a)
                        d = c
                        c[s] = b
                        self.assert_(c is d)
                        self.check_obj(c)
                        cc = a.tolist()
                        cc[s] = b.tolist()
                        self.assertEqual(c, bitarray(cc))


    def test_setslice_to_bool(self):
        a = bitarray('11111111')
        a[::2] = False
        self.assertEqual(a, bitarray('01010101'))
        a[4::] = True
        self.assertEqual(a, bitarray('01011111'))
        a[-2:] = False
        self.assertEqual(a, bitarray('01011100'))
        a[:2:] = True
        self.assertEqual(a, bitarray('11011100'))
        a[:] = True
        self.assertEqual(a, bitarray('11111111'))


    def test_delitem(self):
        a = bitarray('100110')
        del a[1]
        self.assertEqual(len(a), 5)
        del a[3]
        del a[-2]
        self.assertEqual(a, bitarray('100'))
        self.assertRaises(IndexError, a.__delitem__,  3)
        self.assertRaises(IndexError, a.__delitem__, -4)

        for a in self.randombitarrays():
            la = len(a)
            if la == 0: continue
            for dum in range(10):
                step = self.rndsliceidx(la)
                if step == 0: step = None
                s = slice(self.rndsliceidx(la),
                          self.rndsliceidx(la), step)
                c = bitarray(a)
                d = c
                del c[s]
                self.assert_(c is d)
                self.check_obj(c)
                cc = a.tolist()
                del cc[s]
                self.assertEQUAL(c, bitarray(cc, endian=c.endian()))


tests.append(SliceTests)

# ---------------------------------------------------------------------------

class MiscTests(unittest.TestCase, Util):

    def test_booleanness(self):
        self.assertEqual(bool(bitarray('')), False)
        self.assertEqual(bool(bitarray('0')), True)
        self.assertEqual(bool(bitarray('1')), True)

    def test_iterate(self):
        for lst in self.randomlists():
            acc = []
            for b in bitarray(lst):
                acc.append(b)
            self.assertEqual(acc, lst)

    def test_iterable(self):
        a = iter(bitarray('011'))
        self.assertEqual(a.next(), False)
        self.assertEqual(a.next(), True)
        self.assertEqual(a.next(), True)
        self.assertRaises(StopIteration, a.next)

    def test_assignment(self):
        a = bitarray('00110111001')
        a[1:3] = a[7:9]
        a[-1:] = a[:1]
        b = bitarray('01010111000')
        self.assertEqual(a, b)

    def test_compare(self):
        for a in self.randombitarrays():
            aa = a.tolist()

            for b in self.randombitarrays():
                bb = b.tolist()
                self.assertEqual(a == b, aa == bb)
                self.assertEqual(a != b, aa != bb)
                self.assertEqual(a <= b, aa <= bb)
                self.assertEqual(a <  b, aa <  bb)
                self.assertEqual(a >= b, aa >= bb)
                self.assertEqual(a >  b, aa >  bb)

    def test_subclassing(self):
        class ExaggeratingBitarray(bitarray):

            def __new__(cls, data, offset):
                return bitarray.__new__(cls, data)

            def __init__(self, data, offset):
                self.offset = offset

            def __getitem__(self, i):
                return bitarray.__getitem__(self, i - self.offset)

        for a in self.randombitarrays():
            if len(a) == 0:
                continue
            b = ExaggeratingBitarray(a, 1234)
            for i in range(len(a)):
                self.assertEqual(a[i], b[i+1234])

    def test_endianness(self):
        a = bitarray(endian='little')
        a.fromstring('\x01')
        self.assertEqual(a.to01(), '10000000')

        b = bitarray(endian='little')
        b.fromstring('\x80')
        self.assertEqual(b.to01(), '00000001')

        c = bitarray(endian='big')
        c.fromstring('\x80')
        self.assertEqual(c.to01(), '10000000')

        d = bitarray(endian='big')
        d.fromstring('\x01')
        self.assertEqual(d.to01(), '00000001')

        self.assertEqual(a, c)
        self.assertEqual(b, d)

        a = bitarray(8, endian='little')
        a.setall(False)
        a[0] = True
        self.assertEqual(a.tostring(), '\x01')
        a[1] = True
        self.assertEqual(a.tostring(), '\x03')
        a.fromstring(' ')
        self.assertEqual(a.tostring(), '\x03 ')
        self.assertEqual(a.to01(), '1100000000000100')

        a = bitarray(8, endian='big')
        a.setall(False)
        a[7] = True
        self.assertEqual(a.tostring(), '\x01')
        a[6] = True
        self.assertEqual(a.tostring(), '\x03')
        a.fromstring(' ')
        self.assertEqual(a.tostring(), '\x03 ')
        self.assertEqual(a.to01(), '0000001100100000')

        a = bitarray('00100000', endian='big')
        self.assertEqual(a.tostring(), ' ')

        b = bitarray('00000100', endian='little')
        self.assertEqual(b.tostring(), ' ')

        self.assertNotEqual(a, b)

        a = bitarray('11100000', endian='little')
        b = bitarray(a, endian='big')
        self.assertNotEqual(a, b)
        self.assertEqual(a.tostring(), b.tostring())

    def test_pickle(self):
        from pickle import loads, dumps
        for a in self.randombitarrays():
            b = loads(dumps(a))
            self.assert_(b is not a)
            self.assertEQUAL(a, b)

    def test_cPickle(self):
        from pickle import loads, dumps
        for a in self.randombitarrays():
            b = loads(dumps(a))
            self.assert_(b is not a)
            self.assertEQUAL(a, b)

    def test_overflow(self):
        from platform import architecture

        if architecture()[0] == '64bit':
            return

        self.assertRaises(OverflowError, bitarray.__new__,
                          bitarray, 2**34 + 1)

        a = bitarray(10**6)
        self.assertRaises(OverflowError, a.__imul__, 17180)


tests.append(MiscTests)

# ---------------------------------------------------------------------------

class SpecialMethodTests(unittest.TestCase, Util):

    def test_all(self):
        a = bitarray()
        self.assertTrue(a.all())

        for a in self.randombitarrays():
            self.assertEqual(all(a),          a.all())
            self.assertEqual(all(a.tolist()), a.all())


    def test_any(self):
        a = bitarray()
        self.assertFalse(a.any())

        for a in self.randombitarrays():
            self.assertEqual(any(a),          a.any())
            self.assertEqual(any(a.tolist()), a.any())


    def test_repr(self):
        a = bitarray()
        self.assertEqual(repr(a), "bitarray()")

        a = bitarray('10111')
        self.assertEqual(repr(a), "bitarray('10111')")

        for a in self.randombitarrays():
            b = eval(repr(a))
            self.assert_(b is not a)
            self.assertEqual(a, b)
            self.check_obj(b)


    def test_copy(self):
        import copy
        for a in self.randombitarrays():
            b = a.copy()
            self.assert_(b is not a)
            self.assertEQUAL(a, b)

            b = copy.copy(a)
            self.assert_(b is not a)
            self.assertEQUAL(a, b)

            b = copy.deepcopy(a)
            self.assert_(b is not a)
            self.assertEQUAL(a, b)


tests.append(SpecialMethodTests)

# ---------------------------------------------------------------------------

class NumberTests(unittest.TestCase, Util):

    def test_add(self):
        c = bitarray('001') + bitarray('110')
        self.assertEQUAL(c, bitarray('001110'))

        for a in self.randombitarrays():
            aa = a.copy()
            for b in self.randombitarrays():
                bb = b.copy()
                c = a + b
                self.assertEqual(c, bitarray(a.tolist() + b.tolist()))
                self.assertEqual(c.endian(), a.endian())
                self.check_obj(c)

                self.assertEQUAL(a, aa)
                self.assertEQUAL(b, bb)

        a = bitarray()
        self.assertRaises(TypeError, a.__add__, 42)


    def test_iadd(self):
        c = bitarray('001')
        c += bitarray('110')
        self.assertEQUAL(c, bitarray('001110'))

        for a in self.randombitarrays():
            for b in self.randombitarrays():
                c = bitarray(a)
                d = c
                d += b
                self.assertEqual(d, a + b)
                self.assert_(c is d)
                self.assertEQUAL(c, d)
                self.assertEqual(d.endian(), a.endian())
                self.check_obj(d)

        a = bitarray()
        self.assertRaises(TypeError, a.__iadd__, 42)


    def test_mul(self):
        c = 0 * bitarray('1001111')
        self.assertEQUAL(c, bitarray())

        c = 3 * bitarray('001')
        self.assertEQUAL(c, bitarray('001001001'))

        c = bitarray('110') * 3
        self.assertEQUAL(c, bitarray('110110110'))

        for a in self.randombitarrays():
            b = a.copy()
            for n in range(-10, 20):
                c = a * n
                self.assertEQUAL(c, bitarray(n * a.tolist(),
                                             endian=a.endian()))
                c = n * a
                self.assertEqual(c, bitarray(n * a.tolist(),
                                             endian=a.endian()))

                self.assertEQUAL(a, b)


        a = bitarray()
        self.assertRaises(TypeError, a.__mul__, None)


    def test_imul(self):
        c = bitarray('1101110011')
        idc = id(c)
        c *= 0
        self.assertEQUAL(c, bitarray())
        self.assertEqual(idc, id(c))

        c = bitarray('110')
        c *= 3
        self.assertEQUAL(c, bitarray('110110110'))

        for a in self.randombitarrays():
            for n in range(-10, 10):
                b = a.copy()
                idb = id(b)
                b *= n
                self.assertEQUAL(b, bitarray(n * a.tolist(),
                                             endian=a.endian()))
                self.assertEqual(idb, id(b))

        a = bitarray()
        self.assertRaises(TypeError, a.__imul__, None)


tests.append(NumberTests)

# ---------------------------------------------------------------------------

class BitwiseTests(unittest.TestCase, Util):

    def test_misc(self):
        for a in self.randombitarrays():
            b = ~a
            c = a & b
            self.assertEqual(c.any(), False)
            self.assertEqual(a, a ^ c)
            d = a ^ b
            self.assertEqual(d.all(), True)
            b &= d
            self.assertEqual(~b, a)

    def test_and(self):
        a = bitarray('11001')
        b = bitarray('10011')
        self.assertEQUAL(a & b, bitarray('10001'))

        b = bitarray('1001')
        self.assertRaises(ValueError, a.__and__, b) # not same length

        self.assertRaises(TypeError, a.__and__, 42)


    def test_iand(self):
        a =  bitarray('110010110')
        ida = id(a)
        a &= bitarray('100110011')
        self.assertEQUAL(a, bitarray('100010010'))
        self.assertEqual(ida, id(a))

    def test_or(self):
        a = bitarray('11001')
        b = bitarray('10011')
        self.assertEQUAL(a | b, bitarray('11011'))

    def test_iand(self):
        a =  bitarray('110010110')
        a |= bitarray('100110011')
        self.assertEQUAL(a, bitarray('110110111'))

    def test_xor(self):
        a = bitarray('11001')
        b = bitarray('10011')
        self.assertEQUAL(a ^ b, bitarray('01010'))

    def test_ixor(self):
        a =  bitarray('110010110')
        a ^= bitarray('100110011')
        self.assertEQUAL(a, bitarray('010100101'))

    def test_invert(self):
        a = bitarray()
        a.invert()
        self.assertEQUAL(a, bitarray())

        a = bitarray('11011')
        a.invert()
        self.assertEQUAL(a, bitarray('00100'))

        a = bitarray('11011')
        b = ~a
        self.assertEQUAL(b, bitarray('00100'))
        self.assertEQUAL(a, bitarray('11011'))
        self.assert_(a is not b)

        for a in self.randombitarrays():
            aa = a.tolist()
            b = bitarray(a)
            b.invert()
            for i in range(len(a)):
                self.assertEqual(b[i], not aa[i])
            self.check_obj(b)

            c = ~a
            self.assert_(c is not a)
            self.assertEQUAL(a, bitarray(aa, endian=a.endian()))

            for i in range(len(a)):
                self.assertEqual(c[i], not aa[i])

            self.check_obj(b)


tests.append(BitwiseTests)

# ---------------------------------------------------------------------------

class SequenceTests(unittest.TestCase, Util):

    def test_contains(self):
        a = bitarray()
        self.assert_(False not in a)
        self.assert_(True not in a)
        a.append(True)
        self.assert_(True in a)
        self.assert_(False not in a)
        a = bitarray([False])
        self.assert_(False in a)
        self.assert_(True not in a)
        a.append(True)
        self.assert_(0 in a)
        self.assert_(1 in a)
        for n in range(2, 100):
            a = bitarray(n)
            a.setall(0)
            self.assert_(False in a)
            self.assert_(True not in a)
            a[randint(0, n-1)] = 1
            self.assert_(True in a)
            self.assert_(False in a)
            a.setall(1)
            self.assert_(True in a)
            self.assert_(False not in a)
            a[randint(0, n-1)] = 0
            self.assert_(True in a)
            self.assert_(False in a)

        a = bitarray('011010000001')
        self.assert_('1' in a)
        self.assert_('11' in a)
        self.assert_('111' not in a)
        self.assert_(bitarray('00') in a)
        self.assert_([0, 0, 0, 1] in a)
        self.assert_((0, 0, 0, 1, 1) not in a)
        self.assert_((0, 0, 0, 0, 2) in a)


tests.append(SequenceTests)

# ---------------------------------------------------------------------------

class ExtendTests(unittest.TestCase, Util):

    def test_wrongArgs(self):
        a = bitarray()
        self.assertRaises(TypeError, a.extend)
        self.assertRaises(TypeError, a.extend, None)
        self.assertRaises(TypeError, a.extend, True)
        self.assertRaises(TypeError, a.extend, 24)
        self.assertRaises(ValueError, a.extend, '0011201')

    def test_bitarray(self):
        a = bitarray()
        a.extend(bitarray())
        self.assertEqual(a, bitarray())
        a.extend(bitarray('110'))
        self.assertEqual(a, bitarray('110'))
        a.extend(bitarray('1110'))
        self.assertEqual(a, bitarray('1101110'))

        a = bitarray('00001111', endian='little')
        a.extend(bitarray('00111100', endian='big'))
        self.assertEqual(a, bitarray('0000111100111100'))

        for a in self.randombitarrays():
            for b in self.randombitarrays():
                c = bitarray(a)
                idc = id(c)
                c.extend(b)
                self.assertEqual(id(c), idc)
                self.assertEqual(c, a + b)

    def test_list(self):
        a = bitarray()
        a.extend([0, 1, 3, None, {}])
        self.assertEqual(a, bitarray('01100'))
        a.extend([True, False])
        self.assertEqual(a, bitarray('0110010'))

        for a in self.randomlists():
            for b in self.randomlists():
                c = bitarray(a)
                idc = id(c)
                c.extend(b)
                self.assertEqual(id(c), idc)
                self.assertEqual(c.tolist(), a + b)
                self.check_obj(c)

    def test_iterable(self):
        def bar():
            for x in ('', '1', None, True, []):
                yield x
        a = bitarray()
        a.extend(bar())
        self.assertEqual(a, bitarray('01010'))

        for a in self.randomlists():
            for b in self.randomlists():
                def foo():
                    for e in b:
                        yield e
                c = bitarray(a)
                idc = id(c)
                c.extend(foo())
                self.assertEqual(id(c), idc)
                self.assertEqual(c.tolist(), a + b)
                self.check_obj(c)

    def test_tuple(self):
        a = bitarray()
        a.extend((0, 1, 2, 0, 3))
        self.assertEqual(a, bitarray('01101'))

        for a in self.randomlists():
            for b in self.randomlists():
                c = bitarray(a)
                idc = id(c)
                c.extend(tuple(b))
                self.assertEqual(id(c), idc)
                self.assertEqual(c.tolist(), a + b)
                self.check_obj(c)

    def test_iter(self):
        a = bitarray()
        a.extend(iter([3, 9, 0, 1, -2]))
        self.assertEqual(a, bitarray('11011'))

        for a in self.randomlists():
            for b in self.randomlists():
                c = bitarray(a)
                idc = id(c)
                c.extend(iter(b))
                self.assertEqual(id(c), idc)
                self.assertEqual(c.tolist(), a + b)
                self.check_obj(c)

    def test_string01(self):
        a = bitarray()
        a.extend('0110111')
        self.assertEqual(a, bitarray('0110111'))

        for a in self.randomlists():
            for b in self.randomlists():
                c = bitarray(a)
                idc = id(c)
                c.extend(''.join(('1' if x else '0') for x in b))
                self.assertEqual(id(c), idc)
                self.assertEqual(c.tolist(), a + b)
                self.check_obj(c)


tests.append(ExtendTests)

# ---------------------------------------------------------------------------

class MethodTests(unittest.TestCase, Util):

    def test_append(self):
        a = bitarray()
        a.append(True)
        a.append(False)
        a.append(False)
        self.assertEQUAL(a, bitarray('100'))

        for a in self.randombitarrays():
            aa = a.tolist()
            b = a
            b.append(1)
            self.assert_(a is b)
            self.check_obj(b)
            self.assertEQUAL(b, bitarray(aa+[1], endian=a.endian()))
            b.append('')
            self.assertEQUAL(b, bitarray(aa+[1, 0], endian=a.endian()))


    def test_insert(self):
        a = bitarray()
        b = a
        a.insert(0, True)
        self.assert_(a is b)
        self.assertEqual(a, bitarray('1'))
        self.assertRaises(TypeError, a.insert)
        self.assertRaises(TypeError, a.insert, None)

        for a in self.randombitarrays():
            aa = a.tolist()
            item = bool(randint(0, 1))
            pos = randint(-len(a), len(a))
            a.insert(pos, item)
            aa.insert(pos, item)
            self.assertEqual(a.tolist(), aa)
            self.check_obj(a)


    def test_index(self):
        a = bitarray()
        for i in (True, False, 1, 0):
            self.assertRaises(ValueError, a.index, i)

        a = bitarray(100*[False])
        self.assertRaises(ValueError, a.index, True)
        a[20] = a[27] = 54
        self.assertEqual(a.index(42), 20)
        self.assertEqual(a.index(0), 0)

        a = bitarray(200*[True])
        self.assertRaises(ValueError, a.index, False)
        a[173] = a[187] = 0
        self.assertEqual(a.index(False), 173)
        self.assertEqual(a.index(True), 0)

        for n in range(50):
            for m in range(n):
                a = bitarray(n)
                a.setall(0)
                self.assertRaises(ValueError, a.index, 1)
                a[m] = 1
                self.assertEqual(a.index(1), m)

                a.setall(1)
                self.assertRaises(ValueError, a.index, 0)
                a[m] = 0
                self.assertEqual(a.index(0), m)


    def test_count(self):
        a = bitarray('10011')
        self.assertEqual(a.count(), 3)
        self.assertEqual(a.count(True), 3)
        self.assertEqual(a.count(False), 2)
        self.assertEqual(a.count(1), 3)
        self.assertEqual(a.count(0), 2)
        self.assertRaises(TypeError, a.count, 'A')

        for a in self.randombitarrays():
            self.assertEqual(a.count(), a.count(1))
            self.assertEqual(a.count(1), a.to01().count('1'))
            self.assertEqual(a.count(0), a.to01().count('0'))


    def test_search(self):
        a = bitarray('')
        self.assertEqual(a.search(bitarray('0')), [])
        self.assertEqual(a.search(bitarray('1')), [])

        a = bitarray('1')
        self.assertEqual(a.search(bitarray('0')), [])
        self.assertEqual(a.search(bitarray('1')), [0])
        self.assertEqual(a.search(bitarray('11')), [])

        a = bitarray(100*'1')
        self.assertEqual(a.search(bitarray('0')), [])
        self.assertEqual(a.search(bitarray('1')), range(100))

        a = bitarray('10011')
        for s, res in [('0',     [1, 2]),  ('1', [0, 3, 4]),
                       ('01',    [2]),     ('11', [3]),
                       ('000',   []),      ('1001', [0]),
                       ('011',   [2]),     ('0011', [1]),
                       ('10011', [0]),     ('100111', [])]:
            self.assertEqual(a.search(s), res)
            b = bitarray(s)
            self.assertEqual(a.search(b), res)
            self.assertEqual(a.search(list(b)), res)
            self.assertEqual(a.search(tuple(b)), res)

        a = bitarray('10010101110011111001011')
        for limit in range(10):
            self.assertEqual(a.search('011', limit),
                             [6, 11, 20][:limit])


    def test_fill(self):
        a = bitarray('')
        self.assertEqual(a.fill(), 0)
        self.assertEqual(len(a), 0)

        a = bitarray('101')
        self.assertEqual(a.fill(), 5)
        self.assertEQUAL(a, bitarray('10100000'))
        self.assertEqual(a.fill(), 0)
        self.assertEQUAL(a, bitarray('10100000'))

        for a in self.randombitarrays():
            aa = a.tolist()
            la = len(a)
            b = a
            self.assert_(0 <= b.fill() < 8)
            self.assertEqual(b.endian(), a.endian())
            bb = b.tolist()
            lb = len(b)
            self.assert_(a is b)
            self.check_obj(b)
            if la % 8 == 0:
                self.assertEqual(bb, aa)
                self.assertEqual(lb, la)
            else:
                self.assert_(lb % 8 == 0)
                self.assertNotEqual(bb, aa)
                self.assertEqual(bb[:la], aa)
                self.assertEqual(b[la:], (lb-la)*bitarray('0'))
                self.assert_(0 < lb-la < 8)


    def test_sort(self):
        a = bitarray('1101000')
        a.sort()
        self.assertEqual(a, bitarray('0000111'))

        a = bitarray('1101000')
        a.sort(reverse=True)
        self.assertEqual(a, bitarray('1110000'))

        a = bitarray('1101000')
        a.sort(True)
        self.assertEqual(a, bitarray('1110000'))

        self.assertRaises(TypeError, a.sort, 'A')

        for a in self.randombitarrays():
            ida = id(a)
            rev = randint(0, 1)
            a.sort(rev)
            self.assertEqual(a, bitarray(sorted(a.tolist(), reverse=rev)))
            self.assertEqual(id(a), ida)


    def test_reverse(self):
        self.assertRaises(TypeError, bitarray().reverse, 42)

        a = bitarray()
        a.reverse()
        self.assertEQUAL(a, bitarray())

        a = bitarray('1001111')
        a.reverse()
        self.assertEQUAL(a, bitarray('1111001'))

        a = bitarray('11111000011')
        a.reverse()
        self.assertEQUAL(a, bitarray('11000011111'))

        for a in self.randombitarrays():
            aa = a.tolist()
            ida = id(a)
            a.reverse()
            self.assertEqual(ida, id(a))
            self.assertEQUAL(a, bitarray(aa[::-1], endian=a.endian()))


    def test_tolist(self):
        a = bitarray()
        self.assertEqual(a.tolist(), [])

        a = bitarray('110')
        self.assertEqual(a.tolist(), [True, True, False])

        for lst in self.randomlists():
            a = bitarray(lst)
            self.assertEqual(a.tolist(), lst)


    def test_remove(self):
        a = bitarray()
        for i in (True, False, 1, 0):
            self.assertRaises(ValueError, a.remove, i)

        a = bitarray(21)
        a.setall(0)
        self.assertRaises(ValueError, a.remove, 1)
        a.setall(1)
        self.assertRaises(ValueError, a.remove, 0)

        a = bitarray('1010110')
        a.remove(False);        self.assertEqual(a, bitarray('110110'))
        a.remove(True);         self.assertEqual(a, bitarray('10110'))
        a.remove(1);            self.assertEqual(a, bitarray('0110'))
        a.remove(0);            self.assertEqual(a, bitarray('110'))

        a = bitarray('0010011')
        b = a
        b.remove('1')
        self.assert_(b is a)
        self.assertEQUAL(b, bitarray('000011'))


    def test_pop(self):
        a = bitarray()
        self.assertRaises(IndexError, a.pop)

        for a in self.randombitarrays():
            self.assertRaises(IndexError, a.pop, len(a))
            self.assertRaises(IndexError, a.pop, -len(a)-1)
            if len(a) == 0:
                continue
            aa = a.tolist()
            enda = a.endian()
            self.assertEqual(a.pop(), aa[-1])
            self.check_obj(a)
            self.assertEqual(a.endian(), enda)

        for a in self.randombitarrays():
            if len(a) == 0:
                continue
            n = randint(-len(a), len(a)-1)
            aa = a.tolist()
            self.assertEqual(a.pop(n), aa[n])
            self.check_obj(a)


    def test_setall(self):
        a = bitarray(5)
        a.setall(True)
        self.assertEQUAL(a, bitarray('11111'))

        for a in self.randombitarrays():
            val = randint(0, 1)
            b = a
            b.setall(val)
            self.assertEqual(b, bitarray(len(b)*[val]))
            self.assert_(a is b)
            self.check_obj(b)


    def test_bytereverse(self):
        a = bitarray()
        a.bytereverse()
        self.assertEqual(a, bitarray())

        a = bitarray('1011')
        a.bytereverse()
        self.assertEqual(a, bitarray('0000'))

        a = bitarray('111011')
        a.bytereverse()
        self.assertEqual(a, bitarray('001101'))

        a = bitarray('11101101')
        a.bytereverse()
        self.assertEqual(a, bitarray('10110111'))

        for i in range(256):
            a = bitarray()
            a.fromstring(chr(i))
            aa = a.tolist()
            b = a
            b.bytereverse()
            self.assertEqual(b, bitarray(aa[::-1]))
            self.assert_(a is b)
            self.check_obj(b)

    def test_fromtoword(self):
        for bits in range (17):
            for word in range(5,(1<<bits)):
                init = '1'
                r = bitarray(init, endian='little')
                r.fromword (word, bits=bits)
                self.assertEqual(len(r), len(init)+bits)
                self.assertEqual(len(r.to01()), len(init)+bits)
                word2 = r.toword(len(init), bits=bits)
                self.assertEqual (word, word2)

tests.append(MethodTests)

# ---------------------------------------------------------------------------

class StringTests(unittest.TestCase, Util):

    def randomstrings(self):
        for n in range(1, 20):
            yield ''.join(chr(randint(0, 255)) for x in range(n))


    def test_fromstring(self):
        a = bitarray(endian='big')
        a.fromstring('A')
        self.assertEqual(a, bitarray('01000001'))

        b = a
        b.fromstring('BC')
        self.assertEQUAL(b, bitarray('01000001' '01000010' '01000011'))
        self.assert_(b is a)

        for b in self.randombitarrays():
            c = b.__copy__()
            b.fromstring('')
            self.assertEQUAL(b, c)

        for b in self.randombitarrays():
            for s in self.randomstrings():
                a = bitarray(endian=b.endian())
                a.fromstring(s)
                c = b.__copy__()
                b.fromstring(s)
                self.assertEQUAL(b[-len(a):], a)
                self.assertEQUAL(b[:-len(a)], c)
                self.assertEQUAL(c + a, b)


    def test_tostring(self):
        a = bitarray()
        self.assertEqual(a.tostring(), '')

        for end in ('big', 'little'):
            a = bitarray(endian=end)
            a.fromstring('foo')
            self.assertEqual(a.tostring(), "foo")

            for s in self.randomstrings():
                a = bitarray(endian=end)
                a.fromstring(s)
                self.assertEqual(a.tostring(), s)

        for n, s in [(1, '\x01'), (2, '\x03'), (3, '\x07'), (4, '\x0f'),
                     (5, '\x1f'), (6, '\x3f'), (7, '\x7f'), (8, '\xff'),
                     (12, '\xff\x0f'), (15, '\xff\x7f'), (16, '\xff\xff'),
                     (17, '\xff\xff\x01'), (24, '\xff\xff\xff')]:
            a = bitarray(n, endian='little')
            a.setall(1)
            self.assertEqual(a.tostring(), s)


    def test_unpack(self):
        a = bitarray('01')
        self.assertEqual(a.unpack(), '\x00\xff')
        self.assertEqual(a.unpack('A'), 'A\xff')
        self.assertEqual(a.unpack('0', '1'), '01')
        self.assertEqual(a.unpack(one='\x01'), '\x00\x01')
        self.assertEqual(a.unpack(zero='A'), 'A\xff')
        self.assertEqual(a.unpack(one='t', zero='f'), 'ft')
        self.assertEqual(a.unpack('a', one='b'), 'ab')

        self.assertRaises(TypeError, a.unpack, 'a', zero='b')
        self.assertRaises(TypeError, a.unpack, foo='b')
        self.assertRaises(TypeError, a.unpack, 'a', 'b', 'c')

        for a in self.randombitarrays():
            self.assertEqual(a.unpack('0', '1'), a.to01())

            b = bitarray()
            b.pack(a.unpack())
            self.assertEqual(b, a)

            b = bitarray()
            b.pack(a.unpack('\x01', '\x00'))
            b.invert()
            self.assertEqual(b, a)


    def test_pack(self):
        a = bitarray()
        a.pack('\x00')
        self.assertEqual(a, bitarray('0'))
        a.pack('\xff')
        self.assertEqual(a, bitarray('01'))
        a.pack('\x01\x00\x7a')
        self.assertEqual(a, bitarray('01101'))

        a = bitarray()
        for n in range(256):
            a.pack(chr(n))
        self.assertEqual(a, bitarray('0' + 255 * '1'))

        self.assertRaises(TypeError, a.pack, 0)
        self.assertRaises(TypeError, a.pack, u'1')
        self.assertRaises(TypeError, a.pack, [1, 3])
        self.assertRaises(TypeError, a.pack, bitarray())


tests.append(StringTests)

# ---------------------------------------------------------------------------

class FileTests(unittest.TestCase, Util):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tmpfname = os.path.join(self.tmpdir, 'testfile')

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


    def test_cPickle(self):
        from pickle import load, dump

        for a in self.randombitarrays():
            fo = open(self.tmpfname, 'wb')
            dump(a, fo)
            fo.close()

            b = load(open(self.tmpfname, 'rb'))

            self.assert_(b is not a)
            self.assertEQUAL(a, b)


    def test_shelve(self):
        import shelve, hashlib

        d = shelve.open(self.tmpfname)
        stored = []
        for a in self.randombitarrays():
            key = hashlib.md5(repr(a) + a.endian()).hexdigest()
            d[key] = a
            stored.append((key, a))
        d.close()
        del d

        d = shelve.open(self.tmpfname)
        for k, v in stored:
            self.assertEQUAL(d[k], v)
        d.close()


    def test_fromfile_wrong_args(self):
        b = bitarray()
        self.assertRaises(TypeError, b.fromfile)
        self.assertRaises(TypeError, b.fromfile, StringIO()) # file not open
        self.assertRaises(TypeError, b.fromfile, 42)
        self.assertRaises(TypeError, b.fromfile, 'bar')


    def test_from_empty_file(self):
        fo = open(self.tmpfname, 'wb')
        fo.close()

        a = bitarray()
        a.fromfile(open(self.tmpfname, 'rb'))
        self.assertEqual(a, bitarray())


    def test_from_large_file(self):
        N = 100000

        fo = open(self.tmpfname, 'wb')
        fo.write(N * 'X')
        fo.close()

        a = bitarray()
        a.fromfile(open(self.tmpfname, 'rb'))
        self.assertEqual(len(a), 8 * N)
        self.assertEqual(a.buffer_info()[1], N)
        # make sure there is no over-allocation
        self.assertEqual(a.buffer_info()[4], N)


    def test_fromfile_Foo(self):
        fo = open(self.tmpfname, 'wb')
        fo.write('Foo\n')
        fo.close()

        a = bitarray(endian='big')
        a.fromfile(open(self.tmpfname, 'rb'))
        self.assertEqual(a, bitarray('01000110011011110110111100001010'))

        a = bitarray(endian='little')
        a.fromfile(open(self.tmpfname, 'rb'))
        self.assertEqual(a, bitarray('01100010111101101111011001010000'))

        a = bitarray('1', endian='little')
        a.fromfile(open(self.tmpfname, 'rb'))
        self.assertEqual(a, bitarray('101100010111101101111011001010000'))

        for n in range(20):
            a = bitarray(n, endian='little')
            a.setall(1)
            a.fromfile(open(self.tmpfname, 'rb'))
            self.assertEqual(a,
                             n*bitarray('1') +
                             bitarray('01100010111101101111011001010000'))


    def test_fromfile_n(self):
        a = bitarray()
        a.fromstring('ABCDEFGHIJ')
        fo = open(self.tmpfname, 'wb')
        a.tofile(fo)
        fo.close()

        b = bitarray()
        f = open(self.tmpfname, 'rb')
        b.fromfile(f, 1);     self.assertEqual(b.tostring(), 'A')
        f.read(1)
        b = bitarray()
        b.fromfile(f, 2);     self.assertEqual(b.tostring(), 'CD')
        b.fromfile(f, 1);     self.assertEqual(b.tostring(), 'CDE')
        b.fromfile(f, 0);     self.assertEqual(b.tostring(), 'CDE')
        b.fromfile(f);        self.assertEqual(b.tostring(), 'CDEFGHIJ')
        b.fromfile(f);        self.assertEqual(b.tostring(), 'CDEFGHIJ')
        f.close()

        b = bitarray()
        f = open(self.tmpfname, 'rb')
        f.read(1);
        self.assertRaises(EOFError, b.fromfile, f, 10)
        f.close()
        self.assertEqual(b.tostring(), 'BCDEFGHIJ')

        b = bitarray()
        f = open(self.tmpfname, 'rb')
        b.fromfile(f);
        self.assertEqual(b.tostring(), 'ABCDEFGHIJ')
        self.assertRaises(EOFError, b.fromfile, f, 1)
        f.close()


    def test_tofile(self):
        a = bitarray()
        f = open(self.tmpfname, 'wb')
        a.tofile(f)
        f.close()

        fi = open(self.tmpfname, 'rb')
        self.assertEqual(fi.read(), '')
        fi.close()

        a = bitarray('01000110011011110110111100001010', endian='big')
        f = open(self.tmpfname, 'wb')
        a.tofile(f)
        f.close()

        fi = open(self.tmpfname, 'rb')
        self.assertEqual(fi.read(), 'Foo\n')
        fi.close()

        for a in self.randombitarrays():
            b = bitarray(a, endian='big')
            fo = open(self.tmpfname, 'wb')
            b.tofile(fo)
            fo.close()

            s = open(self.tmpfname, 'rb').read()
            self.assertEqual(len(s), a.buffer_info()[1])

        for n in range(3):
            a.fromstring(n * 'A')
            self.assertRaises(TypeError, a.tofile)
            self.assertRaises(TypeError, a.tofile, StringIO())

            f = open(self.tmpfname, 'wb')
            a.tofile(f)
            f.close()
            self.assertRaises(TypeError, a.tofile, f)

        for n in range(20):
            a = n * bitarray('1', endian='little')
            fo = open(self.tmpfname, 'wb')
            a.tofile(fo)
            fo.close()

            s = open(self.tmpfname, 'rb').read()
            self.assertEqual(len(s), a.buffer_info()[1])

            b = a.__copy__()
            b.fill()

            c = bitarray(endian='little')
            c.fromstring(s)
            self.assertEqual(c, b)


tests.append(FileTests)

# ---------------------------------------------------------------------------

class PrefixCodeTests(unittest.TestCase):

    def test_encode_check_codedict(self):
        a = bitarray()
        self.assertRaises(TypeError, a.encode, 0, '')
        self.assertRaises(ValueError, a.encode, {}, '')
        self.assertRaises(TypeError, a.encode, {'a':42}, '')
        self.assertRaises(ValueError, a.encode, {'a':bitarray()}, '')
        # 42 not iterable
        self.assertRaises(TypeError, a.encode, {'a':bitarray('0')}, 42)
        self.assertEqual(len(a), 0)

    def test_encode_string(self):
        a = bitarray()
        d = {'a':bitarray('0')}
        a.encode(d, '')
        self.assertEqual(a, bitarray())
        a.encode(d, 'a')
        self.assertEqual(a, bitarray('0'))
        self.assertEqual(d, {'a':bitarray('0')})

    def test_encode_list(self):
        a = bitarray()
        d = {'a':bitarray('0')}
        a.encode(d, [])
        self.assertEqual(a, bitarray())
        a.encode(d, ['a'])
        self.assertEqual(a, bitarray('0'))
        self.assertEqual(d, {'a':bitarray('0')})

    def test_encode_iter(self):
        a = bitarray()
        d = {'a':bitarray('0'), 'b':bitarray('1')}
        a.encode(d, iter('abba'))
        self.assertEqual(a, bitarray('0110'))

        def foo():
            for c in 'bbaabb':
                yield c

        a.encode(d, foo())
        self.assertEqual(a, bitarray('0110110011'))
        self.assertEqual(d, {'a':bitarray('0'), 'b':bitarray('1')})

    def test_encode(self):
        d = {'I':bitarray('1'),
             'l':bitarray('01'),
             'a':bitarray('001'),
             'n':bitarray('000')}
        a = bitarray()
        a.encode(d, 'Ilan')
        self.assertEqual(a, bitarray('101001000'))
        a.encode(d, 'a')
        self.assertEqual(a, bitarray('101001000001'))
        self.assertEqual(d, {'I':bitarray('1'), 'l':bitarray('01'),
                             'a':bitarray('001'), 'n':bitarray('000')})
        self.assertRaises(ValueError, a.encode, d, 'arvin')


    def test_decode_check_codedict(self):
        a = bitarray()
        self.assertRaises(TypeError, a.decode, 0)
        self.assertRaises(ValueError, a.decode, {})
        # 42 not iterable
        self.assertRaises(TypeError, a.decode, {'a':42})
        self.assertRaises(ValueError, a.decode, {'a':bitarray()})

    def test_decode_simple(self):
        d = {'I':bitarray('1'),
             'l':bitarray('01'),
             'a':bitarray('001'),
             'n':bitarray('000')}
        a = bitarray('101001000')
        self.assertEqual(a.decode(d), ['I', 'l', 'a', 'n'])
        self.assertEqual(d, {'I':bitarray('1'), 'l':bitarray('01'),
                             'a':bitarray('001'), 'n':bitarray('000')})
        self.assertEqual(a, bitarray('101001000'))

    def test_decode_empty(self):
        d = {'a':bitarray('1')}
        a = bitarray()
        self.assertEqual(a.decode(d), [])
        self.assertEqual(d, {'a':bitarray('1')})

    def test_decode_buggybitarray(self):
        d = {'a':bitarray('0')}
        a = bitarray('1')
        self.assertRaises(ValueError, a.decode, d)
        self.assertEqual(a, bitarray('1'))
        self.assertEqual(d, {'a':bitarray('0')})

    def test_decode_buggybitarray2(self):
        d = {'a':bitarray('00'), 'b':bitarray('01')}
        a = bitarray('1')
        self.assertRaises(ValueError, a.decode, d)
        self.assertEqual(a, bitarray('1'))

    def test_decode_ambiguous_code(self):
        d = {'a':bitarray('0'), 'b':bitarray('0'), 'c':bitarray('1')}
        a = bitarray()
        self.assertRaises(ValueError, a.decode, d)

    def test_decode_ambiguous2(self):
        d = {'a':bitarray('01'), 'b':bitarray('01'), 'c':bitarray('1')}
        a = bitarray()
        self.assertRaises(ValueError, a.decode, d)


    def test_miscitems(self):
        d = {None :bitarray('00'),
             0    :bitarray('110'),
             1    :bitarray('111'),
             ''   :bitarray('010'),
             2    :bitarray('011')}
        a = bitarray()
        a.encode(d, [None, 0, 1, '', 2])
        self.assertEqual(a, bitarray('00110111010011'))
        self.assertEqual(a.decode(d), [None, 0, 1, '', 2])

    def test_real_example(self):
        code = {' '  : bitarray('001'),
                '.'  : bitarray('0101010'),
                'a'  : bitarray('0110'),
                'b'  : bitarray('0001100'),
                'c'  : bitarray('000011'),
                'd'  : bitarray('01011'),
                'e'  : bitarray('111'),
                'f'  : bitarray('010100'),
                'g'  : bitarray('101000'),
                'h'  : bitarray('00000'),
                'i'  : bitarray('1011'),
                'j'  : bitarray('0111101111'),
                'k'  : bitarray('00011010'),
                'l'  : bitarray('01110'),
                'm'  : bitarray('000111'),
                'n'  : bitarray('1001'),
                'o'  : bitarray('1000'),
                'p'  : bitarray('101001'),
                'q'  : bitarray('00001001101'),
                'r'  : bitarray('1101'),
                's'  : bitarray('1100'),
                't'  : bitarray('0100'),
                'u'  : bitarray('000100'),
                'v'  : bitarray('0111100'),
                'w'  : bitarray('011111'),
                'x'  : bitarray('0000100011'),
                'y'  : bitarray('101010'),
                'z'  : bitarray('00011011110')}
        a = bitarray()
        a.encode(code, 'the quick brown fox jumps over the lazy dog.')
        self.assertEqual(a, bitarray('01000000011100100001001101000100101100'
          '00110001101000100011001101100001111110010010101001000000010001100'
          '10111101111000100000111101001110000110000111100111110100101000000'
          '0111001011100110000110111101010100010101110001010000101010'))
        self.assertEqual(''.join(a.decode(code)),
                         'the quick brown fox jumps over the lazy dog.')

tests.append(PrefixCodeTests)

# ---------------------------------------------------------------------------

def pages():
    if sys.platform != 'linux2':
        return 0

    dat = open('/proc/%i/statm' % os.getpid()).read()
    return int(dat.split()[0])


def check_memory_leaks(verbosity):
    suite = unittest.TestSuite()
    for cls in tests:
        suite.addTest(unittest.makeSuite(cls))

    logfile = 'pages.log'
    if os.path.isfile(logfile):
        os.unlink(logfile)

    i = 0
    runner = unittest.TextTestRunner(verbosity=verbosity)
    while True:
        print('Run', i)
        r = runner.run(suite)
        if i % 1 == 0:
            fo = open(logfile, 'a')
            fo.write('%10i %r %10i\n' % (i, r.wasSuccessful(), pages()))
            fo.close()
        i += 1


def run(verbosity, chk_mem_leaks=False):
    suite = unittest.TestSuite()
    for cls in tests:
        suite.addTest(unittest.makeSuite(cls))

    runner = unittest.TextTestRunner(verbosity=verbosity)

    return runner.run(suite)


if __name__ == '__main__':
    verbosity = 2 if 'v' in sys.argv else 1
    if 'm' in sys.argv:
        check_memory_leaks(verbosity)
    else:
        run(verbosity)

else:
    from bitarray import __version__

    print('bitarray is installed in:', os.path.dirname(__file__))
    print('bitarray version:', __version__)
    print(sys.version)
