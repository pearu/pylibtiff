
import os
import sys
import numpy

class TIFFView:


    def __init__(self, filename):
        self.data = numpy.memmap(filename, dtype=numpy.byte, mode='r')
        self.check()

    def check (self):
        byteorder = self.get_int16(0)
        if byteorder==0x4949:
            self.endian = 'little'
        elif byteorder==0x4d4d:
            self.endian = 'big'
        else:
            raise ValueError('unrecognized byteorder: %s' % (hex(byteorder)))
        magic = self.get_int16(2)
        if magic!=42:
            raise ValueError('wrong magic number for TIFF file: %s' % (magic))
        self.IFD0 = self.get_int32(4)

    def get_int16(self, offset):
        return self.data[offset:offset+2].view(dtype=numpy.int16)[0]
    def get_int32(self, offset):
        return self.data[offset:offset+4].view(dtype=numpy.int32)[0]

    def iter_IFD(self):
        IFD0 = self.IFD0
        n = self.get_int16(IFD0)
        for i in range(n):
            yield IFDEntry(self, IFD0 + 2 + i*12)

class IFDEntry:

    def __init__(self, tiff, offset):
        self.tag = tiff.get_int16(offset)
        self.type = tiff.get_int16(offset+2)
        self.count = tiff.get_int32(offset+4)
        self.offset = tiff.get_int32(offset+8)

    def __str__(self):
        return 'IFD (tag=%(tag)s, type=%(type)s, count=%(count)s, offset=%(offset)s)' % (self.__dict__)

def main ():
    filename = sys.argv[1]
    if not os.path.isfile(filename):
        raise ValueError('File %r does not exists' % (filename))

    t = TIFFView(filename)

    for IFD in t.iter_IFD():
        print 'IFD:', IFD

if __name__ == '__main__':
    main()

