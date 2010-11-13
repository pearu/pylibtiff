""" Encoder and decoder of Lempel-Ziv-Welch algorithm for TIFF.

This module is obsolete, use tif_lzw extension module instead.
"""
# Author: Pearu Peterson
# Created: May 2010
from __future__ import division
import numpy

default_backend='bittools'
#default_backend='bittools'

if default_backend=='bitarray':
    from bitarray import bitarray
if default_backend=='bittools':
    from bittools import setword, getword

CODECLEAR = 256
CODEEOI = 257
CODESTART = 258

def encode_bitarray(seq, max_bits=12):
    """ Compress sequence using Lempel-Ziv-Welch algorithm for TIFF.

    Parameters
    ----------
    seq : {str, numpy.ndarray}
    max_bits : int
      Specify maximum bits for encoding table.

    Returns
    -------
    bseq : bitarray

    See also
    --------
    decode_bitarray
    """
    if isinstance (seq, numpy.ndarray):
        seq = seq.tostring()
    r = bitarray(0, endian='little')
    write = r.fromword

    init_table = [(chr(code),code) for code in range (256)]

    table = {}
    table_get = table.get
    table_clear = table.clear
    table_update = table.update

    sup_code2 = (1<<max_bits) - 2
    next_code = CODESTART
    bits = 9
    max_code = (1<<bits)
    s = ''

    table_update(init_table)

    index = 0
    write(CODECLEAR, bits)
    for c in seq:
        s1 = s + c
        if s1 in table:
            s = s1
        else:
            write(table_get(s), bits)
            table[s1] = next_code
            next_code += 1
            s = c
            if next_code==sup_code2:
                write(table_get(s), bits)
                write(CODECLEAR, bits)
                s = ''
                table_clear()
                table_update(init_table)
                next_code = CODESTART
                bits = 9
                max_code = (1<<bits)
            elif next_code==max_code:
                bits += 1
                max_code = (1<<bits)
    if s:
        write(table_get(s), bits)
    write(CODEEOI, bits)
    return r

def encode_bittools(seq, max_bits=12):
    """ Compress sequence using Lempel-Ziv-Welch algorithm for TIFF.

    Parameters
    ----------
    seq : {str, numpy.ndarray}
    max_bits : int
      Specify maximum bits for encoding table.

    Returns
    -------
    bseq : numpy.ndarray

    See also
    --------
    decode_bittools
    """
    if isinstance (seq, numpy.ndarray):
        nbytes = seq.nbytes*2
        seq = seq.tostring()
    else:
        nbytes = len(seq)*2
    r = numpy.zeros((nbytes,), dtype=numpy.ubyte)

    init_table = [(chr(code),code) for code in range (256)]

    table = {}
    table_get = table.get
    table_clear = table.clear
    table_update = table.update

    sup_code2 = (1<<max_bits) - 2
    next_code = CODESTART
    bits = 9
    max_code = (1<<bits)
    s = ''

    table_update(init_table)

    index = setword(r, 0, bits, CODECLEAR, 1)
    for c in seq:
        s1 = s + c
        if s1 in table:
            s = s1
        else:
            index = setword(r, index, bits, table_get(s), 1)
            table[s1] = next_code
            next_code += 1
            s = c
            if next_code==sup_code2:
                index = setword(r, index, bits, table_get(s), 1)
                index = setword(r, index, bits, CODECLEAR, 1)
                s = ''
                table_clear()
                table_update(init_table)
                next_code = CODESTART
                bits = 9
                max_code = (1<<bits)
            elif next_code==max_code:
                bits += 1
                max_code = (1<<bits)
    if s:
        index = setword(r, index, bits, table_get(s), 1)
    index = setword(r, index, bits, CODEEOI)
    bytes = index//8
    if 8*bytes < index:
        bytes += 1
    return r[:bytes]

def decode_bitarray(bseq):
    """ Decompress Lempel-Ziv-Welch encoded sequence.

    Parameters
    ----------
    bseq : {bitarray, numpy.ndarray}

    Returns
    -------
    seq : str

    See also
    --------
    encode_bitarray
    """
    if isinstance(bseq, numpy.ndarray):
        bseq = bitarray(bseq, endian='little')
    assert bseq.endian ()=='little',`bseq.endian()`
    read = bseq.toword

    init_invtable = [(code, chr(code)) for code in range (256)]
    table = [chr(code) for code in range(256)] + ['CODECLEAR', 'CODEEOI']
    table_append = table.append
    table_len = table.__len__

    bits = 9
    max_code2 = (1<<bits) - 2
    i = 0
    seq = []
    seq_append = seq.append

    while True:
        code = read(i, bits)
        i += bits
        if code==CODEEOI:
            break
        elif code==CODECLEAR:
            del table[CODESTART:]
            bits = 9
            max_code2 = (1<<bits) - 2
            code = read(i, bits)
            i += bits
            old_str = table[code]
            seq_append(old_str)
            old_code = code
        else:
            l = table_len()
            if code < l:
                s = table[code]
                table_append(old_str + s[0])
                old_str = s
            else:
                old_str = old_str + old_str[0]
                table_append(old_str)

            seq_append(old_str)
            old_code = code

            if l==max_code2:
                bits += 1
                max_code2 = (1<<bits) - 2
    return ''.join(seq)

def decode_bittools(bseq):
    """ Decompress Lempel-Ziv-Welch encoded sequence.

    Parameters
    ----------
    bseq : numpy.ndarray

    Returns
    -------
    seq : str

    See also
    --------
    encode_bittools
    """
    init_invtable = [(code, chr(code)) for code in range (256)]
    table = [chr(code) for code in range(256)] + ['CODECLEAR', 'CODEEOI']
    table_append = table.append
    table_len = table.__len__

    bits = 9
    max_code2 = (1<<bits) - 2
    i = 0
    seq = []
    seq_append = seq.append

    while True:
        code, i = getword(bseq, i, bits)
        if code==CODEEOI:
            break
        elif code==CODECLEAR:
            del table[CODESTART:]
            bits = 9
            max_code2 = (1<<bits) - 2
            code, i = getword(bseq, i, bits)
            old_str = table[code]
            seq_append(old_str)
            old_code = code
        else:
            l = table_len()
            if code < l:
                s = table[code]
                table_append(old_str + s[0])
                old_str = s
            else:
                old_str = old_str + old_str[0]
                table_append(old_str)

            seq_append(old_str)
            old_code = code

            if l==max_code2:
                bits += 1
                max_code2 = (1<<bits) - 2
    return ''.join(seq)


#print 'backend:', default_backend
if default_backend=='bitarray':
    encode = encode_bitarray
    decode = decode_bitarray
    def encode_array(arr):
        return encode_bitarray(arr).toarray ()
if default_backend=='bittools':
    encode = encode_array = encode_bittools
    decode = decode_bittools


def test_lzw():
    for s in ['TOBEORNOTTOBEORTOBEORNOT', '/WED/WE/WEE/WEB/WET'][:0]:
        r = encode (s)
        a = decode (r)
        assert a==s,`a,s`

    if 1:
        f = open(__file__)
        s = f.read ()
        f.close ()

        r = encode (s)
        a = decode (r)
        assert a==s
    print 'ok'
    import sys
    import os
    import time
    for fn in sys.argv[1:]:
        if not os.path.exists(fn):
            continue
        t0 = time.time()
        f = open(fn, 'rb')
        s = f.read()
        f.close()
        t = time.time()-t0
        print 'Reading %s took %.3f seconds, bytes = %s' % (fn, t, len(s))
        t0 = time.time()
        r = encode(s)
        t = time.time()-t0
        sz = len(r)
        if default_backend=='bitarray':
            sz //= 8
        print 'Encoding took %.3f seconds, compress ratio = %.3f, Kbytes per second = %.3f' % (t, len (s)/sz, len(s)/t/1024)
        t0 = time.time()
        s1 = decode(r)
        t = time.time()-t0
        print 'Decoding took %.3f seconds, Kbytes per second = %.3f' % (t, (sz/t)/1024)
        assert s1==s

if __name__=='__main__':
    test_lzw()
