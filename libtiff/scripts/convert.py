#!/usr/bin/env python
# -*- python -*-
# Author: Pearu Peterson
# Created: May 2010
# flake8: noqa

import os

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


def runner(parser, options, args):

    if not hasattr(parser, 'runner'):
        options.output_path = None

    assert not args, repr(args)

    if options.input_path is None:
        parser.error('Expected --input-path but got nothing')

    input_path = options.input_path
    output_path = options.output_path

    if output_path is None:
        b, e = os.path.splitext(input_path)
        b = os.path.basename(b)
        output_path = b + '_%(channel_name)s_%(slice)s.tif'

    from libtiff.tiff import TIFFfile, TIFFimage
    tiff = TIFFfile(input_path)
    samples, sample_names = tiff.get_samples()

    description = []
    for ifd in tiff.IFD:
        s = ifd.get('ImageDescription')
        if s is not None:
            description.append(s.value.tostring())
    init_description = '\n'.join(description)
    samples_list, names_list = tiff.get_samples()
    while samples_list:
        samples = samples_list.pop()
        if options.slice is not None:
            exec('samples = samples[%s]' % (options.slice))
        name = names_list.pop()
        if tiff.is_lsm:
            voxel_sizes = [tiff.lsmentry[
                'VoxelSize' + x][0] for x in 'XYZ']  # m
            # us, integration is >=70% of # the pixel time
            pixel_time = tiff.lsminfo.get(
                'track pixel time')[0]
            rotation = tiff.lsminfo.get('recording rotation')[0]  # deg
            objective = tiff.lsminfo.get(
                'recording objective')[0]  # objective description
            excitation_wavelength = tiff.lsminfo.get(
                'illumination channel wavelength')[0]  # nm
            description = description_template % (dict(
                    DimensionX=samples.shape[2],
                    DimensionY=samples.shape[1],
                    DimensionZ=samples.shape[0],
                    VoxelSizeX=voxel_sizes[0],
                    VoxelSizeY=voxel_sizes[1],
                    VoxelSizeZ=voxel_sizes[2],
                    RotationAngle=rotation,
                    PixelTime=pixel_time,
                    Objective=objective,
                    MicroscopeType='confocal',
                    OriginalFile=os.path.abspath(input_path),
                    ExcitationWavelength=excitation_wavelength,
                    ChannelName=name,
                    )) + init_description
            description += '\n'+tiff.lsminfo.tostr(short=True)
        else:
            description = init_description
        tif = TIFFimage(samples, description=description)
        fn = output_path % dict(channel_name=name, slice=options.slice)
        tif.write_file(fn, compression=getattr(options, 'compression', 'none'))
    return


def main():
    from optparse import OptionParser
    from libtiff.script_options import set_convert_options
    parser = OptionParser()

    set_convert_options(parser)
    if hasattr(parser, 'runner'):
        parser.runner = runner
    options, args = parser.parse_args()
    runner(parser, options, args)
    return


if __name__ == '__main__':
    main()
