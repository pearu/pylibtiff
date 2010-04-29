"""
lsm - implements TIFF CZ_LSM support.
"""
# Author: Pearu Peterson
# Created: April 2010

__all__ = ['scaninfo']

import sys
import numpy

CZ_LSMInfo_tag = 0x866C
#CZ_LSMInfo_type_name = 'CZ_LSMInfo'
#CZ_LSMInfo_type_size = 500
#CZ_LSMInfo_type = -CZ_LSMInfo_tag

tiff_module_dict = None
def IFDEntry_hook(ifd):
    """Make tiff.IFDEntry CZ_LSM aware.
    """
    global tiff_module_dict
    if ifd.tag==CZ_LSMInfo_tag:
        # replace type,count=(BYTE,500) with (CZ_LSMInfo, 1)
        reserved_bytes = (ifd.count - CZ_LSMInfo_dtype_fields_size)
        CZ_LSMInfo_type = (CZ_LSMInfo_tag, reserved_bytes)
        if CZ_LSMInfo_type not in tiff_module_dict['type2dtype']:
            dtype = numpy.dtype(CZ_LSMInfo_dtype_fields + [('Reserved', numpy.dtype('(%s,)u4' % (reserved_bytes//4)))])
            CZ_LSMInfo_type_name = 'CZ_LSMInfo%s' % (reserved_bytes)
            CZ_LSMInfo_type_size = dtype.itemsize
            tiff_module_dict['type2dtype'][CZ_LSMInfo_type] = dtype
            tiff_module_dict['type2name'][CZ_LSMInfo_type] = CZ_LSMInfo_type_name
            tiff_module_dict['type2bytes'][CZ_LSMInfo_type] = CZ_LSMInfo_type_size
            tiff_module_dict['tag_name2value'][CZ_LSMInfo_type_name] = CZ_LSMInfo_tag
        #assert ifd.count==CZ_LSMInfo_type_size,`ifd.count,CZ_LSMInfo_type_size`
        ifd.type = CZ_LSMInfo_type
        ifd.count = 1
        ifd.is_lsm = True
    else:
        ifd.is_lsm = False

def register(tiff_dict):
    """Register CZ_LSM support in tiff module.
    """
    global tiff_module_dict
    tiff_module_dict = tiff_dict
    #tiff_dict['type2dtype'][CZ_LSMInfo_type] = CZ_LSMInfo_dtype
    #tiff_dict['type2name'][CZ_LSMInfo_type] = CZ_LSMInfo_type_name
    #tiff_dict['type2bytes'][CZ_LSMInfo_type] = CZ_LSMInfo_type_size
    #tiff_dict['tag_name2value'][CZ_LSMInfo_type_name] = CZ_LSMInfo_tag
    tiff_dict['IFDEntry_hooks'].append(IFDEntry_hook)

class ScanInfoEntry:
    """ Holds scan information entry data structure.
    """
    def __init__(self, entry, type_name, label, data):
        self.record = (entry, type_name, label, data)
        self.footer = None
        if type_name == 'ASCII':
            self.type = 2
            self.header = numpy.array([entry, 2, len(data)+1], dtype=numpy.uint32).view(dtype=numpy.uint8)
        elif type_name == 'LONG':
            self.type = 4
            self.header = numpy.array([entry, 4, 4], dtype=numpy.uint32).view(dtype=numpy.uint8)
        elif type_name == 'DOUBLE':
            self.type = 5
            self.header = numpy.array([entry, 5, 8], dtype=numpy.uint32).view(dtype=numpy.uint8)
        elif type_name == 'SUBBLOCK':
            self.type = 0
            self.header = numpy.array([entry, 0, 0], dtype=numpy.uint32).view(dtype=numpy.uint8)
        else:
            raise NotImplementedError (`self.record`)

    def get_size(self):
        """ Return total memory size in bytes needed to fit the entry to memory.
        """
        (entry, type_name, label, data) = self.record
        if type_name=='SUBBLOCK':
            if data is None:
                return 12
            size = 0
            for item in data:
                size += item.get_size()
            return 12 + size
        if type_name=='LONG':
            return 12 + 4
        if type_name=='DOUBLE':
            return 12 + 8
        if type_name == 'ASCII':
            return 12 + len(data) + 1
        raise NotImplementedError (`self.record`)

    def toarray(self, target = None):
        if target is None:
            target = numpy.zeros((self.get_size(),), dtype=numpy.uint8)
        (entry, type_name, label, data) = self.record
        target[:12] = self.header
        if type_name=='SUBBLOCK':
            if data is not None:
                n = 12
                for item in data:
                    item.toarray(target[n:])
                    n += item.get_size()
        elif type_name == 'ASCII':
            target[12:12+len(data)+1] = numpy.array([data+'\0']).view (dtype=numpy.uint8)
        elif type_name == 'LONG':
            target[12:12+4] = numpy.array([data], dtype=numpy.uint32).view(dtype=numpy.uint8)
        elif type_name == 'DOUBLE':
            target[12:12+8] = numpy.array([data], dtype=numpy.float64).view(dtype=numpy.uint8)
        else:
            raise NotImplementedError (`self.record`)
        return target

    def tostr(self, tab=''):
        (entry, type_name, label, data) = self.record
        if hasattr(self, 'parent') and self.parent is not None:
            parent_label = self.parent.record[2]
        else:
            parent_label = ''
        if type_name=='SUBBLOCK':
            if data is None:
                return '%s%s %s' % (tab[:-2], label, parent_label)
            l = ['%s%s[size=%s]' % (tab, label, self.get_size ())]
            for item in data:
                l.append(item.tostr(tab=tab+'  '))
            return '\n'.join (l)
        if label.startswith(parent_label):
            label = label[len(parent_label):]
        return '%s%s = %r' % (tab, label, data)

    __str__ = tostr

    def append (self, entry):
        assert self.record[1]=='SUBBLOCK',`self.record`
        self.record[3].append(entry)

def scaninfo(lsm, debug=True):
    """
    Return LSM scan information.

    Parameters
    ----------
    lsm : IFDEntry
    debug: bool
      Enable consistency checks.
    Returns
    -------
    record : ScanInfoEntry
    """
    n = n1 = lsm.value['OffsetScanInformation'][0]
    record = None
    tab = ' '
    while 1:
        entry, type, size = lsm.tiff.get_values(n, 'LONG', 3)
        n += 12
        label, type_name = scaninfo_map.get(entry, (None, None))
        if label is None:
            type_name = {0:'SUBBLOCK', 2:'ASCII', 4:'LONG', 5:'DOUBLE'}.get(type)
            if type_name is None:
                raise NotImplementedError(`hex (entry), type, size`)
            label = 'ENTRY%s' % (hex(entry))
            #scaninfo_map[entry] = label, type_name
            if debug:
                sys.stderr.write('scaninfo: undefined %s entry %s in subblock %r\n'\
                                 % (type_name, hex(entry), record.record[2]))
        if type_name=='SUBBLOCK':
            assert type==0,`hex (entry), type, size`
            if label == 'end':
                entry = ScanInfoEntry(entry, type_name, label, None)
                entry.parent = record
                record.append(entry)
                if record.parent is None:
                    break
                record.parent.append(record)
                record = record.parent
            else:
                prev_record = record
                record = ScanInfoEntry(entry, type_name, label, [])
                record.parent = prev_record
            assert size==0,`hex (entry), type, size`
            continue
        if type_name=='ASCII':
            assert type==2,`hex (entry), type, size`
            value = lsm.tiff.get_string (n, size-1)
        elif type_name=='LONG':
            assert type==4,`hex (entry), type, size, scaninfo_map[entry]`
            value = lsm.tiff.get_long(n)
        elif type_name=='DOUBLE':
            assert type==5,`hex (entry), type, size`
            value = lsm.tiff.get_double(n)
        else:
            raise NotImplementedError(`type_name, hex (entry), type, size`)
        entry = ScanInfoEntry(entry, type_name, label, value)
        entry.parent = record
        n += size
        record.append(entry)
    if debug:
        size = n - n1
        record_size = record.get_size()
        assert size==record_size,`size,record_size`
        arr = record.toarray()
        arr2 = lsm.tiff.data[n1:n1+size].view(numpy.uint8)
        assert (arr==arr2).all()

    return record
    
CZ_LSMInfo_dtype_fields = [
    ('MagicNumber',numpy.uint32),
    ('StructureSize',numpy.int32),
    ('DimensionX',numpy.int32),
    ('DimensionY',numpy.int32),
    ('DimensionZ',numpy.int32),
    ('DimensionChannels', numpy.int32),
    ('DimensionTime', numpy.int32),
    ('SDataType', numpy.int32), # 1: uint8, 2: uint12, 5: float32, 0: see OffsetChannelDataTypes
    ('ThumbnailX', numpy.int32),
    ('ThumbnailY', numpy.int32),
    ('VoxelSizeX', numpy.float64),
    ('VoxelSizeY', numpy.float64),
    ('VoxelSizeZ', numpy.float64),
    ('OriginX', numpy.float64),
    ('OriginY', numpy.float64),
    ('OriginZ', numpy.float64),
    ('ScanType', numpy.uint16),
    # 0:xyz-scan, 1:z-scan, 2:line-scan 3:time xy,
    # 4: time xz (ver>=2.0), 5: time mean roi (ver>=2.0),
    # 6: time xyz (ver>=2.3), 7: spline scan (ver>=2.5),
    # 8: spline plane xz (ver>=2.5)
    # 9: time spline plane xz (ver>=2.5)
    # 10: point mode (ver>=3.0)
    ('SpectralScan', numpy.uint16), # 0:off, 1:on (ver>=3.0)
    ('DataType',numpy.uint32), # 0: original, 1: calculated, 2: animation
    ('OffsetVectorOverlay', numpy.uint32),
    ('OffsetInputLut',numpy.uint32),
    ('OffsetOutputLut',numpy.uint32),
    ('OffsetChannelColors',numpy.uint32),
    ('TimeInterval',numpy.float64),
    ('OffsetChannelDataTypes',numpy.uint32),
    ('OffsetScanInformation',numpy.uint32),
    ('OffsetKsData',numpy.uint32),
    ('OffsetTimeStamps',numpy.uint32),
    ('OffsetEventList',numpy.uint32),
    ('OffsetRoi',numpy.uint32),
    ('OffsetBleachRoi',numpy.uint32),
    ('OffsetNextRecording',numpy.uint32),
    ('DisplayAspectX',numpy.float64),
    ('DisplayAspectY',numpy.float64),
    ('DisplayAspectZ',numpy.float64),
    ('DisplayAspectTime',numpy.float64),
    ('OffsetMeanOfRoisOverlay',numpy.uint32),
    ('OffsetTopoIsolineOverlay', numpy.uint32),
    ('OffsetTopoProfileOverlay', numpy.uint32),
    ('OffsetLinescanOverlay', numpy.uint32),
    ('ToolbarFlags', numpy.uint32),
    ('OffsetChannelWavelength', numpy.uint32),
    ('OffsetChannelFactors', numpy.uint32),
    ('ObjectiveSphereCorrection',numpy.float64),
    ('OffsetUnmixParameters',numpy.uint32),
    #('Reserved', numpy.dtype('(69,)u4')),
    ]

CZ_LSMInfo_dtype_fields_size = 0
for item in CZ_LSMInfo_dtype_fields:
    CZ_LSMInfo_dtype_fields_size += item[1]().itemsize

scaninfo_map = {
    0x0ffffffff: ( 'end', 'SUBBLOCK'),
    0x010000000: ( 'recording','SUBBLOCK'),
    0x010000001: ( 'recording name','ASCII'),
    0x010000002: ( 'recording description','ASCII'),
    0x010000003: ( 'recording notes','ASCII'),
    0x010000004: ( 'recording objective','ASCII'),
    0x010000005: ( 'recording processing summary','ASCII'),
    0x010000006: ( 'recording special scan mode','ASCII'),
    0x010000007: ( 'recording scan type','ASCII'),
    0x010000008: ( 'recording scan mode','ASCII'),
    0x010000009: ( 'recording number of stacks','LONG'),
    0x01000000a: ( 'recording lines per plane','LONG'),
    0x01000000b: ( 'recording samples per line','LONG'),
    0x01000000c: ( 'recording planes per volume','LONG'),
    0x01000000d: ( 'recording images width','LONG'),
    0x01000000e: ( 'recording images height','LONG'),
    0x01000000f: ( 'recording images number planes','LONG'),
    0x010000010: ( 'recording images number stacks','LONG'),
    0x010000011: ( 'recording images number channels','LONG'),
    0x010000012: ( 'recording linescan xy size','LONG'),
    0x010000013: ( 'recording scan direction','LONG'),
    0x010000014: ( 'recording time series','LONG'),
    0x010000015: ( 'recording original scan data','LONG'),
    0x010000016: ( 'recording zoom x','DOUBLE'),
    0x010000017: ( 'recording zoom y','DOUBLE'),
    0x010000018: ( 'recording zoom z','DOUBLE'),
    0x010000019: ( 'recording sample 0x','DOUBLE'),
    0x01000001a: ( 'recording sample 0y','DOUBLE'),
    0x01000001b: ( 'recording sample 0z','DOUBLE'),
    0x01000001c: ( 'recording sample spacing','DOUBLE'),
    0x01000001d: ( 'recording line spacing','DOUBLE'),
    0x01000001e: ( 'recording plane spacing','DOUBLE'),
    0x01000001f: ( 'recording plane width','DOUBLE'),
    0x010000020: ( 'recording plane height','DOUBLE'),
    0x010000021: ( 'recording volume depth','DOUBLE'),
    #0x010000022: ( 'recording ',''),
    0x010000023: ( 'recording nutation','DOUBLE'),
    #0x010000024: ( 'recording ',''),
    #0x010000025: ( 'recording ',''),
    #0x010000026: ( 'recording ',''),
    #0x010000027: ( 'recording ',''),
    #0x010000028: ( 'recording ',''),
    #0x010000029: ( 'recording ',''),
    #0x01000002a: ( 'recording ',''),
    #0x01000002b: ( 'recording ',''),
    #0x01000002c: ( 'recording ',''),
    #0x01000002d: ( 'recording ',''),
    #0x01000002e: ( 'recording ',''),
    #0x01000002f: ( 'recording ',''),
    #0x010000030: ( 'recording ',''),
    #0x010000031: ( 'recording ',''),
    #0x010000032: ( 'recording ',''),
    #0x010000033: ( 'recording ',''),
    0x010000034: ( 'recording rotation','DOUBLE'),
    0x010000035: ( 'recording precession','DOUBLE'),
    0x010000036: ( 'recording sample 0time','DOUBLE'),
    0x010000037: ( 'recording start scan trigger in','ASCII'),
    0x010000038: ( 'recording start scan trigger out','ASCII'),
    0x010000039: ( 'recording start scan event','LONG'),
    #0x01000003a: ( 'recording ',''),
    #0x01000003b: ( 'recording ',''),
    #0x01000003c: ( 'recording ',''),
    #0x01000003d: ( 'recording ',''),
    #0x01000003e: ( 'recording ',''),
    #0x01000003f: ( 'recording ',''),
    0x010000040: ( 'recording start scan time','DOUBLE'),
    0x010000041: ( 'recording stop scan trigger in','ASCII'),
    0x010000042: ( 'recording stop scan trigger out','ASCII'),
    0x010000043: ( 'recording stop scan event','LONG'),
    0x010000044: ( 'recording start scan time','DOUBLE'),
    0x010000045: ( 'recording use rois','LONG'),
    0x010000046: ( 'recording use reduced memory rois','LONG'),
    0x010000047: ( 'recording user','ASCII'),
    0x010000048: ( 'recording usebccorrection','LONG'),
    0x010000049: ( 'recording positionbccorrection1','DOUBLE'),
    #0x01000004a: ( 'recording ',''),
    #0x01000004b: ( 'recording ',''),
    #0x01000004c: ( 'recording ',''),
    #0x01000004d: ( 'recording ',''),
    #0x01000004e: ( 'recording ',''),
    #0x01000004f: ( 'recording ',''),
    0x010000050: ( 'recording positionbccorrection2','DOUBLE'),
    0x010000051: ( 'recording interpolationy','LONG'),
    0x010000052: ( 'recording camera binning','LONG'),
    0x010000053: ( 'recording camera supersampling','LONG'),
    0x010000054: ( 'recording camera frame width','LONG'),
    0x010000055: ( 'recording camera frame height','LONG'),
    0x010000056: ( 'recording camera offsetx','DOUBLE'),
    0x010000057: ( 'recording camera offsety','DOUBLE'),
    #0x010000058: ( 'recording ',''),
    0x010000059: ( 'recording rt binning','LONG'),
    0x01000005a: ( 'recording rt frame width','LONG'),
    0x01000005b: ( 'recording rt frame height','LONG'),
    0x01000005c: ( 'recording rt region width','LONG'),
    0x01000005d: ( 'recording rt region height','LONG'),
    0x01000005e: ( 'recording rt offsetx','DOUBLE'),
    0x01000005f: ( 'recording rt offsety','DOUBLE'),
    0x010000060: ( 'recording rt zoom','DOUBLE'),
    0x010000061: ( 'recording rt lineperiod','DOUBLE'),
    0x010000062: ( 'recording prescan','LONG'),
    0x010000063: ( 'recording scan directionz','LONG'),
    #0x010000064: ( 'recording ','LONG'),
    0x030000000: ( 'lasers','SUBBLOCK'), 
    0x050000000: ( 'laser','SUBBLOCK'),
    0x050000001: ( 'laser name','ASCII'),
    0x050000002: ( 'laser acquire','LONG'),
    0x050000003: ( 'laser power','DOUBLE'),
    0x020000000: ( 'tracks','SUBBLOCK'), 
    0x040000000: ( 'track','SUBBLOCK'),
    0x040000001: ( 'track multiplex type','LONG'),
    0x040000002: ( 'track multiplex order','LONG'),
    0x040000003: ( 'track sampling mode','LONG'),
    0x040000004: ( 'track sampling method','LONG'),
    0x040000005: ( 'track sampling number','LONG'),
    0x040000006: ( 'track acquire','LONG'),
    0x040000007: ( 'track sample observation time','DOUBLE'),
    #
    0x04000000b: ( 'track time between stacks','DOUBLE'),
    0x04000000c: ( 'track name','ASCII'),
    0x04000000d: ( 'track collimator1 name','ASCII'),
    0x04000000e: ( 'track collimator1 position','LONG'),
    0x04000000f: ( 'track collimator2 name','ASCII'),
    0x040000010: ( 'track collimator2 position','LONG'),
    0x040000011: ( 'track is bleach track','LONG'),
    0x040000012: ( 'track is bleach after scan number','LONG'),
    0x040000013: ( 'track bleach scan number','LONG'),
    0x040000014: ( 'track trigger in','ASCII'),
    0x040000015: ( 'track trigger out','ASCII'),
    0x040000016: ( 'track is ratio track','LONG'),
    0x040000017: ( 'track bleach count','LONG'),
    0x040000018: ( 'track spi center wavelength','DOUBLE'),
    0x040000019: ( 'track pixel time','DOUBLE'),
    0x040000020: ( 'track id condensor frontlens','ASCII'),
    0x040000021: ( 'track condensor frontlens','LONG'),
    0x040000022: ( 'track id field stop','ASCII'),
    0x040000023: ( 'track field stop value','DOUBLE'),
    0x040000024: ( 'track id condensor aperture','ASCII'),
    0x040000025: ( 'track condensor aperture','DOUBLE'),
    0x040000026: ( 'track id condensor revolver','ASCII'),
    0x040000027: ( 'track condensor filter','ASCII'),
    0x040000028: ( 'track id transmission filter1','ASCII'),
    0x040000029: ( 'track id transmission1','DOUBLE'),
    0x040000030: ( 'track id transmission filter2','ASCII'),
    0x040000031: ( 'track if transmission2','DOUBLE'),
    0x040000032: ( 'track repeat bleach','LONG'),
    0x040000033: ( 'track enable spot bleach pos','LONG'),
    0x040000034: ( 'track spot bleach posx','DOUBLE'),
    0x040000035: ( 'track spot bleach posy','DOUBLE'),
    0x040000036: ( 'track bleach position z','DOUBLE'),
    0x040000037: ( 'track id tubelens','ASCII'),
    0x040000038: ( 'track id tubelens position','ASCII'),
    0x040000039: ( 'track transmitted light','DOUBLE'),
    0x04000003a: ( 'track reflected light','DOUBLE'),
    0x04000003b: ( 'track simultan grab and bleach','LONG'),
    0x04000003c: ( 'track bleach pixel time','DOUBLE'),

    0x060000000: ( 'detection channels','SUBBLOCK'),
    0x070000000: ( 'detection channel','SUBBLOCK'),
    0x070000001: ( 'detection channel integration mode','LONG'),
    0x070000002: ( 'detection channel special mode','LONG'),
    0x070000003: ( 'detection channel detector gain first','DOUBLE'),
    0x070000004: ( 'detection channel detector gain last','DOUBLE'),
    0x070000005: ( 'detection channel amplifier gain first','DOUBLE'),    
    0x070000006: ( 'detection channel amplifier gain last','DOUBLE'),
    0x070000007: ( 'detection channel amplifier offs first','DOUBLE'),
    0x070000008: ( 'detection channel amplifier offs last','DOUBLE'),
    0x070000009: ( 'detection channel pinhole diameter','DOUBLE'),
    0x07000000a: ( 'detection channel counting trigger','DOUBLE'),
    0x07000000b: ( 'detection channel acquire','LONG'),
    0x07000000c: ( 'detection channel detector name','ASCII'),
    0x07000000d: ( 'detection channel amplifier name','ASCII'),
    0x07000000e: ( 'detection channel pinholw name','ASCII'),
    0x07000000f: ( 'detection channel filter set name','ASCII'),
    0x070000010: ( 'detection channel filter name','ASCII'),
    0x070000013: ( 'detection channel integrator name','ASCII'),
    0x070000014: ( 'detection channel detection channel name','ASCII'),
    0x070000015: ( 'detection channel detector gain bc1','DOUBLE'),
    0x070000016: ( 'detection channel detector gain bc2','DOUBLE'),
    0x070000017: ( 'detection channel amplifier gain bc1','DOUBLE'),
    0x070000018: ( 'detection channel amplifier gain bc2','DOUBLE'),
    0x070000019: ( 'detection channel amplifier offs bc1','DOUBLE'),
    0x070000020: ( 'detection channel amplifier offs bc2','DOUBLE'),
    0x070000021: ( 'detection channel spectral scan channels','LONG'),
    0x070000022: ( 'detection channel spi wavelength start','DOUBLE'),
    0x070000023: ( 'detection channel spi wavelength end','DOUBLE'),
    0x070000026: ( 'detection channel dye name','ASCII'),
    0x070000027: ( 'detection channel dye folder','ASCII'),

    0x080000000: ( 'illumination channels','SUBBLOCK'),
    0x090000000: ( 'illumination channel','SUBBLOCK'),
    0x090000001: ( 'illumination channel name','ASCII'),
    0x090000002: ( 'illumination channel power','DOUBLE'),
    0x090000003: ( 'illumination channel wavelength','DOUBLE'),
    0x090000004: ( 'illumination channel aquire','LONG'),
    0x090000005: ( 'illumination channel detection channel name','ASCII'),
    0x090000006: ( 'illumination channel power bc1','DOUBLE'),
    0x090000007: ( 'illumination channel power bc2','DOUBLE'),

    0x0A0000000: ( 'beam splitters','SUBBLOCK'),
    0x0B0000000: ( 'beam splitter','SUBBLOCK'),
    0x0B0000001: ( 'beam splitter filter set','ASCII'),
    0x0B0000002: ( 'beam splitter filter','ASCII'),
    0x0B0000003: ( 'beam splitter name','ASCII'),

    0x0C0000000: ( 'data channels','SUBBLOCK'),
    0x0D0000000: ( 'data channel','SUBBLOCK'),
    0x0D0000001: ( 'data channel name','ASCII'),
    #0x0D0000002: ( 'data channel',''),
    0x0D0000003: ( 'data channel acquire','LONG'),
    0x0D0000004: ( 'data channel color','LONG'),
    0x0D0000005: ( 'data channel sampletype','LONG'),
    0x0D0000006: ( 'data channel bitspersample','LONG'),
    0x0D0000007: ( 'data channel ratio type','LONG'),
    0x0D0000008: ( 'data channel ratio track1','LONG'),
    0x0D0000009: ( 'data channel ratio track2','LONG'),
    0x0D000000a: ( 'data channel ratio channel1','ASCII'),
    0x0D000000b: ( 'data channel ratio channel2','ASCII'),
    0x0D000000c: ( 'data channel ratio const1','DOUBLE'),
    0x0D000000d: ( 'data channel ratio const2','DOUBLE'),
    0x0D000000e: ( 'data channel ratio const3','DOUBLE'),
    0x0D000000f: ( 'data channel ratio const4','DOUBLE'),
    0x0D0000010: ( 'data channel ratio const5','DOUBLE'),
    0x0D0000011: ( 'data channel ratio const6','DOUBLE'),
    0x0D0000012: ( 'data channel ratio first images1','LONG'),
    0x0D0000013: ( 'data channel ratio first images2','LONG'),
    0x0D0000014: ( 'data channel dye name','ASCII'),
    0x0D0000015: ( 'data channel dye folder','ASCII'),
    0x0D0000016: ( 'data channel spectrum','ASCII'),
    0x0D0000017: ( 'data channel acquire','LONG'),

    0x011000000: ( 'timers','SUBBLOCK'),
    0x012000000: ( 'timer','SUBBLOCK'), 
    0x012000001: ( 'timer name','ASCII'), 
    0x012000003: ( 'timer interval','DOUBLE'), 
    0x012000004: ( 'timer trigger in','ASCII'), 
    0x012000005: ( 'timer trigger out','ASCII'),
    0x012000006: ( 'timer activation time','DOUBLE'),
    0x012000007: ( 'timer activation number','LONG'), 

    0x013000000: ( 'markers','SUBBLOCK'), 
    0x014000000: ( 'marker','SUBBLOCK'),
    0x014000001: ( 'marker name','ASCII'),
    0x014000002: ( 'marker description','ASCII'),
    0x014000003: ( 'marker trigger in','ASCII'),
    0x014000004: ( 'marker trigger out','ASCII'),

}

