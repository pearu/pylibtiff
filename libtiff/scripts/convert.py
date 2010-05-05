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
    output_path = options.output_path
    assert output_path is None,`output_path`
    
    if output_path is None:
        b, e = os.path.splitext (input_path)
        b = os.path.basename (b)
        output_path = b + '_%(channel_name)s_%(index)s.tif'

    from libtiff import TIFF
    from libtiff.tiff import TIFFfile
    tiff = TIFFfile (input_path)
    #tiff.show_memory_usage()
    Ch3i = 0
    Ch3_images = []
    for i,ifd in enumerate(tiff.IFD):
        assert ifd.get ('Compression').value==1,`ifd.get ('Compression')`
        images = ifd.get_contiguous()
        if isinstance (images, dict):
            for channel_name, image in images.items():
                if channel_name=='Ch3':
                    if not image[0].max():
                        break
                    Ch3_images.append (image)
                    Ch3i += 1
        else:
            raise NotImplementedError (`type (images)`)

    fn = output_path % dict(channel_name='Ch3', index='all')
    print 'Saving',len (Ch3_images),'slices to',fn,'...',
    sys.stdout.flush ()
    tif = TIFF.open(fn, mode='w')
    tif.write_image(numpy.array(Ch3_images,dtype=numpy.uint8))
    tif.close()
    print 'done'

def main ():
    from libtiff.optparse_gui import OptionParser
    from libtiff.script_options import set_convert_options
    parser = OptionParser()

    set_convert_options (parser)
    if hasattr(parser, 'runner'):
        parser.runner = runner
    options, args = parser.parse_args()
    runner(parser, options, args)
    return

if __name__ == '__main__':
    main()
