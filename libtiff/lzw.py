
import numpy
from bitarray import bitarray

def code2bits(code, bits=None):
    """Return bitarray of code using bits.

    Maximum number of bits is 16.

    Parameters
    ----------
    code : int
    bits : {None, int}


    """
    assert code is not None
    a = numpy.array([code], dtype=numpy.uint16)
    b = bitarray(a, endian='little')
    if bits is None:
        bits = len(b.to01().rstrip('0'))
    return b[:bits]

def encode(seq):
    s = ''
    r = code2bits(256, 9)
    table = {}
    for b in seq:
        c = chr(b)
        if not table:
            for code in range(256):
                table[chr(code)] = code
            next_code = 258
            bits = 9
        s1 = s + c
        table_code = table.get(s1)
        if table_code is not None:
            s = s1
        else:
            b1 = code2bits(table[s], bits)
            r = r + b1
            table[s1] = next_code
            next_code += 1
            s = c
            if next_code==(1<<bits):
                bits += 1
                if bits==13:
                    r = r + code2bits(table[s], bits)
                    s = ''
                    r = r + code2bits(256, bits)
                    table.clear()
    if s:
        r = r + code2bits(table[s], bits)
    r = r + code2bits(257, bits)
    return r

def decode(bseq):
    bits = 9
    i = 0
    seq = ''
    invtable = {}
    while True:
        code = bseq.toword (index=i, bits=bits)
        i += bits        
        if code==256:
            invtable.clear ()
            for j in range (256):
                invtable[j] = chr(j)
            old_code = None
            next_code = 258
            bits = 9
            continue
        if code==257:
            break
        if old_code is None:
            seq += invtable[code]
            old_code = code
            continue
        s = invtable.get(code)
        if s is not None:
            s1 = invtable[old_code] + s[0]
        else:
            s1 = invtable[old_code]
            s = s1 = s1 + s1[0]
        invtable[next_code] = s1
        next_code += 1
        seq += s
        old_code = code
        if next_code+1==(1<<bits):
            bits += 1
    return seq


def test_encode ():
    for s in ['TOBEORNOTTOBEORTOBEORNOT', '/WED/WE/WEE/WEB/WET']:
        arr = numpy.array([s]).view (dtype=numpy.uint8)
        r = encode (arr)
        a = decode (r)
        assert a==s,`a,s`

    f = open(__file__)
    s = f.read ()
    f.close ()
    arr = numpy.array([s]).view (dtype=numpy.uint8)
    r = encode (arr)
    a = decode (r)
    assert a==s

    print len(r)/8, arr.nbytes

if __name__=='__main__':
    test_encode ()
