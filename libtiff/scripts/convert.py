#!/usr/bin/env python
# -*- python-mode -*-
# Author: Pearu Peterson
# Created: May 2010

from __future__ import division
import os

### START UPDATE SYS.PATH ###
### END UPDATE SYS.PATH ###

import numpy

description_template = '''
DimensionX: %(DimensionX)s
DimensionY: %(DimensionY)s
DimensionZ: %(DimensionZ)s
VoxelSizeX: %(VoxelSizeX)s
VoxelSizeY: %(VoxelSizeY)s
VoxelSizeZ: %(VoxelSizeZ)s
NofStacks: 1
RotationAngle: %(RotationAngle)s
PixelTime: %(PixelTime)s
ENTRY_OBJECTIVE: %(Objective)s
Objective: %(Objective)s
ExcitationWavelength: %(ExcitationWavelength)s
MicroscopeType: %(MicroscopeType)s
ChannelName: %(ChannelName)s
OriginalFile: %(OriginalFile)s
'''


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
    from libtiff.tiff import TIFFfile, TIFFimage
    tiff = TIFFfile (input_path)
    #tiff.show_memory_usage()

    channel_images = []

    description = []

    output_channel_name = options.channel_name

    for i,ifd in enumerate(tiff.IFD):
        assert ifd.get ('Compression').value==1,`ifd.get ('Compression')`
        images = ifd.get_contiguous()
        if isinstance (images, dict):
            if not output_channel_name:
                print 'Channel names:', sorted (images.keys())
                output_channel_name = sorted (images.keys())[0]
            for channel_name, image in images.items():
                if channel_name==output_channel_name:
                    if not image[0].max():
                        break
                    channel_images.append(image)
        else:
            raise NotImplementedError (`type (images)`)
        s = ifd.get('ImageDescription')
        if s:
            description.append(s)

    description = '\n'.join (description)
    if tiff.is_lsm:
        dimensions = [tiff.lsmentry['Dimension'+x][0] for x in 'XYZ'] # px
        voxel_sizes = [tiff.lsmentry['VoxelSize'+x][0] for x in 'XYZ'] # m
        pixel_time = tiff.lsminfo.get('track pixel time')[0] # us, integration is >=70% of the pixel time
        rotation =  tiff.lsminfo.get('recording rotation')[0] # deg
        objective = tiff.lsminfo.get('recording objective')[0] # objective description
        excitation_wavelength = tiff.lsminfo.get ('illumination channel wavelength')[0] # nm
        description = description_template % (dict(
                DimensionX=dimensions[0],
                DimensionY=dimensions[1],
                DimensionZ=len(channel_images),
                VoxelSizeX=voxel_sizes[0], 
                VoxelSizeY=voxel_sizes[1],
                VoxelSizeZ=voxel_sizes[2],
                RotationAngle=rotation,
                PixelTime = pixel_time,
                Objective = objective,
                MicroscopeType = 'confocal',
                OriginalFile = os.path.abspath(input_path),
                ExcitationWavelength = excitation_wavelength,
                ChannelName = output_channel_name,
                )) + description
        description += '\n'+tiff.lsminfo.tostr (short=True)
        #print description
    fn = output_path % dict(channel_name=output_channel_name, index='all')
    sys.stdout.flush ()
    tif = TIFFimage(channel_images, description=description)
    tif.write_file (fn, compression=options.compression)

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
