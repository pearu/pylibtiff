
[![Build Status](https://travis-ci.org/pearu/pylibtiff.svg?branch=master)](https://travis-ci.org/pearu/pylibtiff)

[![Build status](https://ci.appveyor.com/api/projects/status/4u5dr1ccpabwrgd1?svg=true)](https://ci.appveyor.com/project/pearu/pylibtiff)

PyLibTiff is a package that provides:

* a wrapper to the [libtiff](http://www.simplesystems.org/libtiff/)
    library to [Python](http://www.python.org) using
    [ctypes](http://docs.python.org/library/ctypes.html).

* a pure Python module for reading and writing TIFF and LSM files. The
  images are read as `numpy.memmap` objects so that it is possible to
  open images that otherwise would not fit to computers RAM. Both TIFF
  strips and tiles are supported for low-level data storage.

There exists many Python packages such as
[PIL](http://www.pythonware.com/products/pil/),
[FreeImagePy](http://freeimagepy.sourceforge.net/) that support
reading and writing TIFF files. The PyLibTiff project was started to
have an efficient and direct way to read and write TIFF files using
the libtiff library without the need to install any unnecessary
packages or libraries. The pure Python module was created for reading
"broken" TIFF files such as LSM files that in some places use
different interpretation of TIFF tags than what specified in the TIFF
specification document. The libtiff library would just fail reading
such files. In addition, the pure Python module is more memory
efficient as the arrays are returned as memory maps. Support for
compressed files is not implemented yet.

[tifffile.py](http://www.lfd.uci.edu/~gohlke/code/tifffile.py.html) by
Christoph Gohlke is an excellent module for reading TIFF as well as
LSM files, it is as fast as libtiff.py by using numpy.


# Usage example (libtiff wrapper) #

```
>>> from libtiff import TIFF
>>> # to open a tiff file for reading:
>>> tif = TIFF.open('filename.tif', mode='r')
>>> # to read an image in the currect TIFF directory and return it as numpy array:
>>> image = tif.read_image()
>>> # to read all images in a TIFF file:
>>> for image in tif.iter_images(): # do stuff with image
>>> # to open a tiff file for writing:
>>> tif = TIFF.open('filename.tif', mode='w')
>>> # to write a image to tiff file
>>> tif.write_image(image)
```

# Usage example (pure Python module) #

```
>>> from libtiff import TIFFfile, TIFFimage
>>> # to open a tiff file for reading
>>> tif = TIFFfile('filename.tif')
>>> # to return memmaps of images and sample names (eg channel names, SamplesPerPixel>=1)
>>> samples, sample_names = tiff.get_samples()
>>> # to create a tiff structure from image data
>>> tiff = TIFFimage(data, description='')
>>> # to write tiff structure to file
>>> tiff.write_file('filename.tif', compression='none') # or 'lzw'
>>> del tiff # flushes data to disk
```

# Script usage examples #

```
$ libtiff.info -i result_0.tif --no-gui
IFDEntry(tag=ImageWidth, value=512, count=1, offset=None)
IFDEntry(tag=ImageLength, value=512, count=1, offset=None)
IFDEntry(tag=BitsPerSample, value=32, count=1, offset=None)
IFDEntry(tag=Compression, value=1, count=1, offset=None)
IFDEntry(tag=PhotometricInterpretation, value=1, count=1, offset=None)
IFDEntry(tag=StripOffsets, value=8, count=1, offset=None)
IFDEntry(tag=Orientation, value=6, count=1, offset=None)
IFDEntry(tag=StripByteCounts, value=1048576, count=1, offset=None)
IFDEntry(tag=PlanarConfiguration, value=1, count=1, offset=None)
IFDEntry(tag=SampleFormat, value=3, count=1, offset=None)
Use --ifd to see the rest of 31 IFD entries
data is contiguous: False
memory usage is ok: True
sample data shapes and names:

width : 512
length : 512
samples_per_pixel : 1
planar_config : 1
bits_per_sample : 32
strip_length : 1048576

[('memmap', (32, 512, 512), dtype('float32'))] ['sample0']
```

```
$ libtiff.info --no-gui -i psf_1024_z5_airy1_set1.lsm
IFDEntry(tag=NewSubfileType, value=0, count=1, offset=None)
IFDEntry(tag=ImageWidth, value=1024, count=1, offset=None)
IFDEntry(tag=ImageLength, value=1024, count=1, offset=None)
IFDEntry(tag=BitsPerSample, value=8, count=1, offset=None)
IFDEntry(tag=Compression, value=1, count=1, offset=None)
IFDEntry(tag=PhotometricInterpretation, value=1, count=1, offset=None)
IFDEntry(tag=StripOffsets, value=97770, count=1, offset=None)
IFDEntry(tag=SamplesPerPixel, value=1, count=1, offset=None)
IFDEntry(tag=StripByteCounts, value=1048576, count=1, offset=None)
IFDEntry(tag=PlanarConfiguration, value=2, count=1, offset=None)
IFDEntry(tag=CZ_LSMInfo, value=CZ_LSMInfo276(
  MagicNumber=[67127628], 
  StructureSize=[500], 
  DimensionX=[1024], 
  DimensionY=[1024], 
  DimensionZ=[20], 
  DimensionChannels=[1], 
  DimensionTime=[1], 
  SDataType=[1], 
  ThumbnailX=[128], 
  ThumbnailY=[128], 
  VoxelSizeX=[  2.79017865e-08], 
  VoxelSizeY=[  2.79017865e-08], 
  VoxelSizeZ=[  3.60105263e-07], 
  OriginX=[ -2.22222228e-07], 
  OriginY=[  1.90476196e-07], 
  OriginZ=[ 0.], 
  ScanType=[0], 
  SpectralScan=[0], 
  DataType=[0], 
  OffsetVectorOverlay->DrawingElement(name='OffsetVectorOverlay', size=200, offset=6560), 
  OffsetInputLut->LookupTable(name='OffsetInputLut', size=8388, subblocks=6, channels=1, offset=7560), 
  OffsetOutputLut->LookupTable(name='OffsetOutputLut', size=24836, subblocks=3, channels=3, offset=15948), 
  OffsetChannelColors->ChannelColors (names=['Ch3'], colors=[(255, 0, 0, 0)]), 
  TimeInterval=[ 0.], 
  OffsetChannelDataTypes->None, 
  OffsetScanInformation->recording[size=3535]
   name = 'psf_1024_z5_airy1_set1'
   description = ' '
   notes = ' '
   objective = 'C-Apochromat 63x/1.20 W Korr UV-VIS-IR M27'
   special scan mode = 'FocusStep'
   scan type = ''
   scan mode = 'Stack'
   number of stacks = 10
   lines per plane = 1024
   samples per line = 1024
   planes per volume = 20
   images width = 1024
   images height = 1024
   images number planes = 20
   images number stacks = 1
   images number channels = 1
   linescan xy size = 512
   scan direction = 0
   scan directionz = 0
   time series = 0
   original scan data = 1
   zoom x = 5.0000000000000009
   zoom y = 5.0000000000000009
   zoom z = 1.0
   sample 0x = -0.22200000000000006
   sample 0y = 0.19000000000000006
   sample 0z = 6.8420000000000014
   sample spacing = 0.028000000000000008
   line spacing = 0.028000000000000008
   plane spacing = 0.3600000000000001
   rotation = 0.0
   nutation = 0.0
   precession = 0.0
   sample 0time = 39583.598368055624
   start scan trigger in = ''
   start scan trigger out = ''
   start scan event = 0
   start scan time = 0.0
   stop scan trigger in = ''
   stop scan trigger out = ''
   stop scan event = 0
   start scan time = 0.0
   use rois = 0
   use reduced memory rois = 0
   user = 'User Name'
   usebccorrection = 0
   positionbccorrection1 = 0.0
   positionbccorrection2 = 0.0
   interpolationy = 1
   camera binning = 1
   camera supersampling = 0
   camera frame width = 1388
   camera frame height = 1040
   camera offsetx = 0.0
   camera offsety = 0.0
   rt binning = 1
  ENTRY0x10000064L = 1
   rt frame width = 512
   rt frame height = 512
   rt region width = 512
   rt region height = 512
   rt offsetx = 0.0
   rt offsety = 0.0
   rt zoom = 1.0000000000000004
   rt lineperiod = 112.43300000000002
   prescan = 0
  lasers[size=188]
    laser[size=80]
       name = 'HeNe633'
       acquire = 1
       power = 5.0000000000000009
    end laser
    laser[size=84]
       name = 'DPSS 532-75'
       acquire = 1
       power = 75.000000000000014
    end laser
  end lasers
  tracks[size=2071]
    track[size=2047]
       pixel time = 1.5980000000000003
       time between stacks = 1.0
       multiplex type = 1
       multiplex order = 1
       sampling mode = 2
       sampling method = 1
       sampling number = 8
       acquire = 1
       name = 'Track'
       collimator1 position = 16
       collimator1 name = 'IR/Vis'
       collimator2 position = 66
       collimator2 name = 'UV/Vis'
       is bleach track = 0
       is bleach after scan number = 0
       bleach scan number = 0
       trigger in = ''
       trigger out = ''
       is ratio track = 0
       bleach count = 0
       spi center wavelength = 582.53000000000009
       id condensor aperture = 'KAB1'
       condensor aperture = 0.55000000000000016
       id condensor revolver = 'FW2'
       condensor filter = 'HF'
       id tubelens = 'Tubelens'
       id tubelens position = 'Lens LSM'
       transmitted light = 0.0
       reflected light = -1.0000000000000002
      detection channels[size=695]
        detection channel[size=671]
           detector gain first = 700.00000000000011
           detector gain last = 700.00000000000011
           amplifier gain first = 1.0000000000000002
           amplifier gain last = 1.0000000000000002
           amplifier offs first = 0.10000000000000002
           amplifier offs last = 0.10000000000000002
           pinhole diameter = 144.00000000000003
           counting trigger = 5.0
           acquire = 1
           integration mode = 0
           special mode = 0
           detector name = 'Pmt3'
           amplifier name = 'Amplifier1'
           pinhole name = 'PH3'
           filter set name = 'EF3'
           filter name = 'LP 650'
          ENTRY0x70000011L = ''
          ENTRY0x70000012L = ''
           integrator name = 'Integrator3'
           detection channel name = 'Ch3'
           detector gain bc1 = 0.0
           detector gain bc2 = 0.0
           amplifier gain bc1 = 0.0
           amplifier gain bc2 = 0.0
           amplifier offs bc1 = 0.0
           amplifier offs bc2 = 0.0
           spectral scan channels = 32
           spi wavelength start = 415.0
           spi wavelength end = 735.0
          ENTRY0x70000024L = 575.0
          ENTRY0x70000025L = 575.0
           dye name = ''
           dye folder = ''
          ENTRY0x70000028L = 1.0000000000000004
          ENTRY0x70000029L = 0.0
        end detection channel
      end detection channels
      beam splitters[size=330]
        beam splitter[size=82]
           filter set = 'HT'
           filter = 'HFT 405/514/633'
           name = 'HT'
        end beam splitter
        beam splitter[size=75]
           filter set = 'NT1'
           filter = 'Mirror'
           name = 'NT1'
        end beam splitter
        beam splitter[size=76]
           filter set = 'NT2'
           filter = 'NFT 565'
           name = 'NT2'
        end beam splitter
        beam splitter[size=73]
           filter set = 'FW1'
           filter = 'None'
           name = 'FW1'
        end beam splitter
      end beam splitters
      illumination channels[size=160]
        illumination channel[size=136]
           name = '633'
           power = 0.30000000000000004
           wavelength = 633.0
           aquire = 1
           power bc1 = 0.0
           power bc2 = 0.0
        end illumination channel
      end illumination channels
      data channels[size=338]
        data channel[size=314]
           name = 'Ch3'
           acquire = 1
           acquire = 0
           color = 255
           sampletype = 1
           bitspersample = 8
           ratio type = 0
           ratio track1 = 0
           ratio track2 = 0
           ratio channel1 = ''
           ratio channel2 = ''
           ratio const1 = 0.0
           ratio const2 = 0.0
           ratio const3 = 1.0
           ratio const4 = 0.0
           ratio const5 = 0.0
           ratio const6 = 0.0
        end data channel
      end data channels
    end track
  end tracks
  timers[size=24]
  end timers
  markers[size=24]
  end markers
end recording, 
  OffsetKsData->OffsetData(name='OffsetKsData', size=8, offset=48590), 
  OffsetTimeStamps->TimeStamps(stamps=[ 2335.75582836]), 
  OffsetEventList->EventList(events=[]), 
  OffsetRoi->DrawingElement(name='OffsetRoi', size=200, offset=6160), 
  OffsetBleachRoi->DrawingElement(name='OffsetBleachRoi', size=200, offset=6360), 
  OffsetNextRecording->None, 
  DisplayAspectX=[ 1.], 
  DisplayAspectY=[ 1.], 
  DisplayAspectZ=[ 1.], 
  DisplayAspectTime=[ 1.], 
  OffsetMeanOfRoisOverlay->DrawingElement(name='OffsetMeanOfRoisOverlay', size=200, offset=6760), 
  OffsetTopoIsolineOverlay->DrawingElement(name='OffsetTopoIsolineOverlay', size=200, offset=7160), 
  OffsetTopoProfileOverlay->DrawingElement(name='OffsetTopoProfileOverlay', size=200, offset=7360), 
  OffsetLinescanOverlay->DrawingElement(name='OffsetLinescanOverlay', size=200, offset=6960), 
  ToolbarFlags=[0], 
  OffsetChannelWavelength->ChannelWavelength (ranges=[(-1.0, -1.0)]), 
  OffsetChannelFactors->ChannelFactors(size=36, offset=40836), 
  ObjectiveSphereCorrection=[ 0.], 
  OffsetUnmixParameters->OffsetData(name='OffsetUnmixParameters', size=124, offset=48466), 
  Reserved=[[40896 44726     0     0     0     0     0     0     0     0     0     0
      0     0     0     0     0     0     0     0     0     0     0     0
      0     0     0     0     0     0     0     0     0     0     0     0
      0     0     0     0     0     0     0     0     0     0     0     0
      0     0     0     0     0     0     0     0     0     0     0     0
      0     0     0     0     0     0     0     0     0]]))
Use --ifd to see the rest of 39 IFD entries
data is contiguous: False
memory usage is ok: True
sample data shapes and names:

width : 1024
length : 1024
samples_per_pixel : 1
planar_config : 2
bits_per_sample : 8
strip_length : 1048576

[('memmap', (20, 1024, 1024), dtype('uint8'))] ['Ch3']
[((20, 128, 128), dtype('uint8')), ((20, 128, 128), dtype('uint8')), ((20, 128, 128), dtype('uint8'))] ['red', 'green', 'blue']
```
