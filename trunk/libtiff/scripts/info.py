#!/usr/bin/env python
# -*- python-mode -*-
# Author: Pearu Peterson
# Created: May 2010

from __future__ import division
import os

### START UPDATE SYS.PATH ###
### END UPDATE SYS.PATH ###

import numpy

def runner (parser, options, args):
    
    if not hasattr(parser, 'runner'):
        options.output_path = None

    assert not args,`args`

    if options.input_path is None:
        parser.error('Expected --input-path but got nothing')

    input_path = options.input_path


    import libtiff
    from libtiff import TIFF
    from libtiff.tiff import TIFFfile, TIFFimage
    from libtiff.utils import bytes2str
    tiff = libtiff.tiff.TIFFfile (input_path)

    if options.memory_usage:
        print 'Memory usage:'
        print '-------------'
        tiff.check_memory_usage()

    human = options.get(human=False)
    print human

    ifd0 = tiff.IFD[0]
    if options.ifd:
        for i,ifd in enumerate(tiff.IFD):
            print 'IFD%s:' % (i)
            print '------'
            if human:
                print ifd.human()
            else:
                print ifd
    else:
        if human:
            print ifd0.human()
        else:
            print ifd0
        if len (tiff.IFD)>1:
            print 'Use --ifd to see the rest of %s IFD entries' % (len (tiff.IFD)-1)

    print 'data is contiguous:', tiff.is_contiguous ()
    if tiff.check_memory_usage(verbose=False):
        print 'memory usage is ok'
    else:
        print 'memory usage has inconsistencies:'
        print '-----'
        tiff.check_memory_usage(verbose=True)
        print '-----'

    print 'reading samples...'
    r = tiff.get_samples(0, verbose=True)
    print 'samples:'
    for arr, name in zip(*r):
        print '  %s: class=%s, dtype=%s, shape=%s, size=%s' \
              % (name, type(arr).__name__, arr.dtype, arr.shape, bytes2str(arr.size))
    if tiff.is_lsm:
        for arr, name in zip(*tiff.get_samples(1)):
            print '  %s: class=%s, dtype=%s, shape=%s, size=%s' \
                  % (name, type(arr).__name__, arr.dtype, arr.shape, bytes2str(arr.size))


def main ():
    try:
        from libtiff.optparse_gui import OptionParser
    except ImportError:
        from optparse import OptionParser
        raise
    from libtiff.script_options import set_info_options
    from libtiff.utils import Options
    parser = OptionParser()

    set_info_options (parser)
    if hasattr(parser, 'runner'):
        parser.runner = runner
    options, args = parser.parse_args()
    runner(parser, Options(options), args)
    return

if __name__ == '__main__':
    main()
