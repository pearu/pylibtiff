"""
lsm - implements TIFF CZ_LSM support.
"""
# Author: Pearu Peterson
# Created: April 2010

__all__ = ['scaninfo', 'timestamps', 'eventlist','channelcolors',
           'channelwavelength','inputlut','outputlut',
           'vectoroverlay','roi','bleachroi','meanofroisoverlay',
           'topoisolineoverlay','topoprofileoverlay','linescanoverlay',
           'channelfactors', 'channeldatatypes',
           'lsmblock', 'lsminfo'
           ]

import sys
import numpy

CZ_LSMInfo_tag = 0x866C
tiff_module_dict = None
verbose_lsm_memory_usage = False

def IFDEntry_lsm_str_hook(entry):
    l = []
    for name in entry.value.dtype.names:
        func = CZ_LSMOffsetField_readers.get(name)
        if func is not None:
            l.append('\n  %s->%s' % (name, func(entry, debug=False)))
        else:
            v = entry.value[name]
            l.append('\n  %s=%s' % (name, v))
    return 'IFDEntry(tag=%s, value=%s(%s))' % (entry.tag_name, entry.type_name, ', '.join (l))

def IFDEntry_lsm_init_hook(ifdentry):
    """Make tiff.IFDENTRYEntry CZ_LSM aware.
    """
    global tiff_module_dict
    if ifdentry.tag==CZ_LSMInfo_tag:
        # replace type,count=(BYTE,500) with (CZ_LSMInfo, 1)
        reserved_bytes = (ifdentry.count - CZ_LSMInfo_dtype_fields_size)
        CZ_LSMInfo_type = (CZ_LSMInfo_tag, reserved_bytes)
        if CZ_LSMInfo_type not in tiff_module_dict['type2dtype']:
            dtype = numpy.dtype(CZ_LSMInfo_dtype_fields + [('Reserved', numpy.dtype('(%s,)u4' % (reserved_bytes//4)))])
            CZ_LSMInfo_type_name = 'CZ_LSMInfo%s' % (reserved_bytes)
            CZ_LSMInfo_type_size = dtype.itemsize
            tiff_module_dict['type2dtype'][CZ_LSMInfo_type] = dtype
            tiff_module_dict['type2name'][CZ_LSMInfo_type] = CZ_LSMInfo_type_name
            tiff_module_dict['type2bytes'][CZ_LSMInfo_type] = CZ_LSMInfo_type_size
            tiff_module_dict['tag_name2value'][CZ_LSMInfo_type_name] = CZ_LSMInfo_tag
        #assert ifdentry.count==CZ_LSMInfo_type_size,`ifdentry.count,CZ_LSMInfo_type_size`
        ifdentry.type = CZ_LSMInfo_type
        ifdentry.count = 1
        ifdentry.tiff.is_lsm = True
        ifdentry.str_hook = IFDEntry_lsm_str_hook
    else:
        if not hasattr(ifdentry.tiff, 'is_lsm'):
            ifdentry.tiff.is_lsm = False

def IFDEntry_lsm_finalize_hook(ifdentry):
    if ifdentry.tag==CZ_LSMInfo_tag:
        blockstart, blockend = None, None
        for name in ifdentry.value.dtype.names:
            func = CZ_LSMOffsetField_readers.get(name)
            if func is not None:
                s = func(ifdentry, debug=False)
                if s is not None:
                    start = s.offset
                    end = start + s.get_size()
                    if blockstart is None:
                        blockstart, blockend = start, end
                    else:
                        blockstart, blockend = min(blockstart,start), max(blockend,end)
                    if verbose_lsm_memory_usage:
                        ifdentry.memory_usage.append((start, end,
                                                      ifdentry.tag_name+' '+name[6:]))
        if verbose_lsm_memory_usage:
            for offset in ifdentry.value['Reserved'][0]:
                if offset:
                    ifdentry.memory_usage.append((offset, offset, 'start of a unknown reserved field'))
        else:
            ifdentry.memory_usage.append((blockstart, blockend, 'lsmblock'))
        ifdentry.block_range = (blockstart, blockend)
        ifdentry.tiff.lsminfo = scaninfo(ifdentry, debug=False)
        ifdentry.tiff.lsmblock = lsmblock(ifdentry, debug=False)
        ifdentry.tiff.lsmentry = ifdentry.value

def register(tiff_dict):
    """Register CZ_LSM support in tiff module.
    """
    global tiff_module_dict
    tiff_module_dict = tiff_dict
    tiff_dict['IFDEntry_init_hooks'].append(IFDEntry_lsm_init_hook)
    tiff_dict['IFDEntry_finalize_hooks'].append(IFDEntry_lsm_finalize_hook)

def lsminfo(ifdentry, new_lsmblock_start=None):
    if ifdentry.tag!=CZ_LSMInfo_tag:
        return
    target = ifdentry.value.copy()
    old_lsmblock_start = ifdentry.block_range[0]
    if new_lsmblock_start is None:
        new_lsmblock_start = old_lsmblock_start
    offset_diff = new_lsmblock_start - old_lsmblock_start
    i = 0
    for name in ifdentry.value.dtype.names:
        dt = ifdentry.value.dtype[name]
        value_ref = target[name]
        value = value_ref[0]
        if name.startswith('Offset') and value!=0:
            #print 'changing',name,'from',value,'to',
            value_ref += offset_diff
            #print value_ref[0]
        elif name=='Reserved':
            # assuming that unknown values in Reserved field are offsets:
            for i in range(len(value)):
                if value[i]!=0:
                    if value[i]>=ifdentry.block_range[0] and value[i]<=ifdentry.block_range[1]:
                        #print 'chaning Reserved[%s] from %s to' % (i, value[i]),
                        value[i] += offset_diff
                        #print value[i]
                    else:
                        sys.stderr.write('Reserved[%s]=%s is out of block range %s. lsminfo might not be correct.' % (i,value[i], ifdentry.block_range))
        i += dt.itemsize    

    return target

class LSMBlock:
    
    def __init__(self, ifdentry):
        self.ifdentry = ifdentry
        self._offset = None

    @property
    def offset(self):
        if self._offset is None:
            self._offset = self.ifdentry.block_range[0]
        return self._offset

    def get_size(self):
        return self.ifdentry.block_range[1] - self.offset

    def __str__(self):
        return '%s(offset=%s, size=%s, end=%s)' % (self.__class__.__name__, self.offset, self.get_size(), self.offset+self.get_size())

    def get_data(self, new_offset):
        raise NotImplementedError(`new_offset`)

    def toarray(self, target=None, new_offset=None):
        sz = self.get_size()
        if target is None:
            target = numpy.zeros((sz,), dtype = numpy.ubyte)
        if new_offset is None:
            new_offset = self.offset
        offset_diff = new_offset - self.offset
        dtype = target.dtype
        target[:sz] = self.ifdentry.tiff.data[self.offset:self.offset + sz]
        return target


def lsmblock(ifdentry, debug=True):
    if ifdentry.tag!=CZ_LSMInfo_tag:
        return
    r = LSMBlock(ifdentry)
    if debug:
        arr = r.toarray()
        offset = r.offset
        arr2 = ifdentry.tiff.data[offset:offset+arr.nbytes]
        assert (arr==arr2).all()
    return r

class ScanInfoEntry:
    """ Holds scan information entry data structure.
    """
    def __init__(self, entry, type_name, label, data):
        self._offset = None
        self.record = (entry, type_name, label, data)
        self.footer = None
        if type_name == 'ASCII':
            self.type = 2
            self.header = numpy.array([entry, 2, len(data)+1], dtype=numpy.uint32).view(dtype=numpy.ubyte)
        elif type_name == 'LONG':
            self.type = 4
            self.header = numpy.array([entry, 4, 4], dtype=numpy.uint32).view(dtype=numpy.ubyte)
        elif type_name == 'DOUBLE':
            self.type = 5
            self.header = numpy.array([entry, 5, 8], dtype=numpy.uint32).view(dtype=numpy.ubyte)
        elif type_name == 'SUBBLOCK':
            self.type = 0
            self.header = numpy.array([entry, 0, 0], dtype=numpy.uint32).view(dtype=numpy.ubyte)
        else:
            raise NotImplementedError (`self.record`)

    def __repr__ (self):
        return '%s%r' % (self.__class__.__name__, self.record)

    @property
    def is_subblock(self):
        return self.record[1]=='SUBBLOCK'
    @property
    def label(self):
        return self.record[2]
    @property
    def data(self):
        return self.record[3]

    def get(self, label):
        if self.label == label:
            if self.is_subblock:
                return self
            return self.data
        if self.is_subblock and self.data is not None:
            l = []
            for entry in self.data:
                r = entry.get(label)
                if isinstance(r, list):
                    l.extend(r)
                elif r is not None:
                    l.append(r)
            if not l:
                return
            return l
    @property
    def offset(self):
        if self._offset is None:
            self._offset = self.ifdentry.value['OffsetScanInformation'][0]
        return self._offset

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
            target = numpy.zeros((self.get_size(),), dtype=numpy.ubyte)
        dtype = target.dtype
        (entry, type_name, label, data) = self.record
        target[:12] = self.header
        if type_name=='SUBBLOCK':
            if data is not None:
                n = 12
                for item in data:
                    item.toarray(target[n:])
                    n += item.get_size()
        elif type_name == 'ASCII':
            target[12:12+len(data)+1] = numpy.array([data+'\0']).view(dtype=dtype)
        elif type_name == 'LONG':
            target[12:12+4] = numpy.array([data], dtype=numpy.uint32).view(dtype=dtype)
        elif type_name == 'DOUBLE':
            target[12:12+8] = numpy.array([data], dtype=numpy.float64).view(dtype=dtype)
        else:
            raise NotImplementedError (`self.record`)
        return target

    def tostr(self, tab='', short=False):
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
                if not short or item.data:
                    l.append(item.tostr(tab=tab+'  ', short=short))
            return '\n'.join (l)
        if label.startswith(parent_label):
            label = label[len(parent_label):]
        return '%s%s = %r' % (tab, label, data)

    __str__ = tostr

    def append (self, entry):
        assert self.record[1]=='SUBBLOCK',`self.record`
        self.record[3].append(entry)


def scaninfo(ifdentry, debug=True):
    """
    Return LSM scan information.

    Parameters
    ----------
    ifdentry : IFDEntry
    debug: bool
      Enable consistency checks.
    Returns
    -------
    record : ScanInfoEntry
    """
    if ifdentry.tag!=CZ_LSMInfo_tag:
        return
    #assert ifdentry.is_lsm
    n = n1 = ifdentry.value['OffsetScanInformation'][0]
    if not n:
        return
    record = None
    tab = ' '
    while 1:
        entry, type, size = ifdentry.tiff.get_values(n, 'LONG', 3)
        n += 12
        label, type_name = scaninfo_map.get(entry, (None, None))
        if label is None:
            type_name = {0:'SUBBLOCK', 2:'ASCII', 4:'LONG', 5:'DOUBLE'}.get(type)
            if type_name is None:
                raise NotImplementedError(`hex (entry), type, size`)
            label = 'ENTRY%s' % (hex(entry))
            #scaninfo_map[entry] = label, type_name
            if debug:
                sys.stderr.write('lsm.scaninfo: undefined %s entry %s in subblock %r\n'\
                                     % (type_name, hex(entry), record.record[2]))
                pass
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
            value = ifdentry.tiff.get_string (n, size-1)
        elif type_name=='LONG':
            assert type==4,`hex (entry), type, size, scaninfo_map[entry]`
            value = ifdentry.tiff.get_long(n)
        elif type_name=='DOUBLE':
            assert type==5,`hex (entry), type, size`
            value = ifdentry.tiff.get_double(n)
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
        arr2 = ifdentry.tiff.data[n1:n1+size]
        assert (arr==arr2).all()

    record.offset = n1

    return record

class TimeStamps:
    """ Holds LSM time stamps information.
    """
    def __init__(self, ifdentry):
        self.ifdentry = ifdentry
        self._offset = None
        self._header = None
        self._stamps = None

    @property
    def offset(self):
        if self._offset is None:
            self._offset = self.ifdentry.value['OffsetTimeStamps'][0]            
        return self._offset

    @property
    def header(self):
        if self._header is None:
            offset = self.offset
            self._header = self.ifdentry.tiff.get_value(offset, CZ_LSMTimeStamps_header_dtype)            
        return self._header

    @property
    def stamps(self):
        if self._stamps is None:
            n = self.header['NumberTimeStamps']
            self._stamps = self.ifdentry.tiff.get_values(self.offset + self.header.dtype.itemsize, numpy.float64, int(n))
        return self._stamps

    def __str__(self):
        return '%s(stamps=%s)' % (self.__class__.__name__, self.stamps)

    def get_size(self):
        return 8+self.stamps.nbytes

    def toarray(self, target=None):
        sz = self.get_size()
        if target is None:
            target = numpy.zeros((sz,), dtype=numpy.ubyte)
        dtype = target.dtype
        header = numpy.array([sz, self.stamps.size], dtype=numpy.int32).view(dtype=dtype)
        assert header.nbytes==8,`header.nbytes`
        data = self.stamps.view(dtype=dtype)
        target[:header.nbytes] = header
        target[header.nbytes:header.nbytes+data.nbytes] = data
        return target

def timestamps(ifdentry, debug=True):
    """
    Return LSM time stamp information.
    """
    if ifdentry.tag!=CZ_LSMInfo_tag:
        return
    #assert ifdentry.is_lsm
    offset = ifdentry.value['OffsetTimeStamps'][0]
    if not offset:
        return None
    r = TimeStamps(ifdentry)
    if debug:
        arr = r.toarray()
        arr2 = ifdentry.tiff.data[offset:offset+arr.nbytes]
        assert (arr==arr2).all()
    return r

class EventEntry:
    
    def __init__ (self, entry_size, time, event_type, unknown, description):
        self.record = entry_size, time, event_type, unknown, description

    @property
    def time (self): return self.record[1]
    @property
    def type (self): return self.record[2]
    @property
    def type_name (self):
        r = {0:'marker', 1:'timer change', 2:'cleach start',
             3:'bleach stop', 4:'trigger'}.get (self.type)
        if r is None:
            r = 'EventType%s' % (self.type)
        return r
    @property
    def description(self): return self.record[4]

    def __str__(self):
        return 'EventEntry(time=%r, type=%r, description=%r)' % (self.time, self.type_name, self.description)

    def get_size(self):
        return 4+8+4+4+len(self.description)+1

    def toarray (self, target = None):
        sz = self.get_size()
        if target is None:
            target = numpy.zeros((sz,), dtype=numpy.ubyte)
        dtype = target.dtype
        target[:4].view(dtype=numpy.uint32)[0] = sz
        target[4:4+8].view(dtype=numpy.float64)[0] = self.time
        target[12:16].view (dtype=numpy.uint32)[0] = self.type
        target[16:20].view (dtype=numpy.uint32)[0] = self.record[3]
        l = len (self.description)
        target[20:20+l] = numpy.array([self.description]).view(dtype=dtype)
        target[20+l] = 0
        return target

class EventList:
    """ Holds LSM event list information.
    """
    def __init__(self, ifdentry):
        self.ifdentry = ifdentry
        self._offset = None
        self._header = None
        self._events = None

    @property
    def offset(self):
        if self._offset is None:
            self._offset = self.ifdentry.value['OffsetEventList'][0]
        return self._offset

    @property
    def header(self):
        if self._header is None:
            self._header = self.ifdentry.tiff.get_value(self.offset, CZ_LSMEventList_header_dtype)
        return self._header

    @property
    def events(self):
        if self._events is None:
            n = self.header['NumberEvents']
            offset = self.offset + self.header.nbytes
            self._events = []
            for i in range(n):
                entry_size = self.ifdentry.tiff.get_value (offset, numpy.uint32)
                time = self.ifdentry.tiff.get_value(offset+4, numpy.float64)
                event_type = self.ifdentry.tiff.get_value(offset + 4+8, numpy.uint32)
                unknown = self.ifdentry.tiff.get_value(offset + 4+8+4, numpy.uint32)
                descr = self.ifdentry.tiff.get_string(offset + 4+8+4+4)
                self._events.append(EventEntry(entry_size, time, event_type, unknown, descr))
                offset += entry_size
        return self._events

    def __str__ (self):
        return '%s(events=[%s])' % (self.__class__.__name__, ','.join(map(str,self.events)))

    def get_size(self):
        s = self.header.nbytes
        for event in self.events:
            s += event.get_size()
        return s

    def toarray (self, target=None):
        sz = self.get_size()
        if target is None:
            target = numpy.zeros((sz,), dtype=numpy.ubyte)
        dtype = target.dtype     
        header = numpy.array([sz, len (self.events)], dtype=numpy.int32).view(dtype=dtype)
        target[:header.nbytes] = header
        offset = header.nbytes
        for event in self.events:
            event.toarray(target[offset:])
            offset += event.get_size()
        return target

def eventlist(ifdentry, debug=True):
    """
    Return LSM event list information.
    """
    if ifdentry.tag!=CZ_LSMInfo_tag:
        return
    #assert ifdentry.is_lsm
    offset = ifdentry.value['OffsetEventList'][0]
    if not offset:
        return None
    r = EventList(ifdentry)
    if debug:
        arr = r.toarray()
        arr2 = ifdentry.tiff.data[offset:offset+arr.nbytes]
        assert (arr==arr2).all()
    return r

class ChannelWavelength:
    """ Holds LSM channel wavelength information.
    """
    def __init__ (self, ifdentry):
        self.ifdentry = ifdentry
        self._offset = None
        self._ranges = None

    @property
    def offset(self):
        if self._offset is None:
            self._offset = self.ifdentry.value['OffsetChannelWavelength'][0]            
        return self._offset

    @property
    def ranges (self):
        if self._ranges is None:
            self._ranges = []
            offset = self.offset
            n = self.ifdentry.tiff.get_value (offset, numpy.int32)
            for i in range(n):
                start, end = self.ifdentry.tiff.get_values(offset + 4 + i*(8+8), numpy.float64, 2)
                self._ranges.append((start, end))
        return self._ranges

    def __str__ (self):
        return '%s (ranges=%s)' % (self.__class__.__name__, self.ranges)

    def get_size(self):
        return 4 + len(self.ranges)*16

    def toarray (self, target=None):
        sz = self.get_size()
        if target is None:
            target = numpy.zeros((sz,), dtype=numpy.ubyte)
        dtype = target.dtype     
        target[:4].view(dtype=numpy.int32)[0] = len(self.ranges)
        data = numpy.array(self.ranges).ravel()
        target[4:4+data.nbytes] = data.view (dtype=dtype)
        return target

def channelwavelength(ifdentry, debug=True):
    """
    Return LSM wavelength range information.
    """
    if ifdentry.tag!=CZ_LSMInfo_tag:
        return
    #assert ifdentry.is_lsm
    offset = ifdentry.value['OffsetChannelWavelength'][0]
    if not offset:
        return None
    r = ChannelWavelength(ifdentry)
    if debug:
        arr = r.toarray()
        arr2 = ifdentry.tiff.data[offset:offset+arr.nbytes]
        assert (arr==arr2).all()
    return r

class ChannelColors:
    """ Holds LSM channel name and color information.
    """
    def __init__ (self, ifdentry):
        self.ifdentry = ifdentry
        self._offset = None
        self._header = None
        self._names = None
        self._colors = None
        self._mono = None

    @property
    def offset(self):
        if self._offset is None:
            self._offset = self.ifdentry.value['OffsetChannelColors'][0]            
        return self._offset

    @property
    def mono (self):
        if self._mono is None:
            self._mono = not not self.header[5]
        return self._mono

    @property
    def header (self):
        if self._header is None:
            self._header = self.ifdentry.tiff.get_values(self.offset, numpy.int32, 10)
            sz = self._header[0]
        return self._header

    @property
    def names(self):
        if self._names is None:
            header = self.header
            n = header[2]
            offset = self.offset + header[4] + 4
            self._names = []
            for i in range(n):
                name = self.ifdentry.tiff.get_string(offset)
                offset += len(name) + 1 + 4
                self._names.append(name)
        return self._names
    
    @property
    def colors(self):
        if self._colors is None:
            header = self.header
            n = header[1]
            offset = self.offset + header[3]
            self._colors = []
            for i in range(n):
                color = self.ifdentry.tiff.get_values(offset, numpy.uint8, 4)
                offset += color.nbytes
                self._colors.append(tuple(color))
        return self._colors

    def __str__(self):
        return '%s (names=%s, colors=%s)' % (self.__class__.__name__, self.names, self.colors)

    def get_size(self):
        s = 10*4
        for name in self.names:
            s += len(name) + 1 + 4
        for color in self.colors:
            s += len(color)
        return s

    def toarray (self, target=None):
        sz = self.get_size()
        if target is None:
            target = numpy.zeros((sz,), dtype=numpy.ubyte)
        dtype = target.dtype
        header = numpy.array([sz,len (self.colors), len (self.names), 0, 0, self.mono, 0,0,0,0], dtype=numpy.int32)
        names = ''
        for name in self.names:
            names += '\x04\0\0\0' + name + '\x00'
        noffset = sz - len(names)
        names = numpy.array([names]).view (dtype=dtype)
        colors = numpy.array (self.colors, dtype=numpy.uint8).ravel()
        coffset = noffset - colors.nbytes
        header[3] = coffset
        header[4] = noffset

        target[:header.nbytes] = header.view(dtype=dtype)
        target[coffset:coffset + colors.nbytes] = colors
        target[noffset:noffset + names.nbytes] = names
        return target

def channelcolors(ifdentry, debug=True):
    """
    Return LSM channel name and color information.
    """
    if ifdentry.tag!=CZ_LSMInfo_tag:
        return
    #assert ifdentry.is_lsm
    offset = ifdentry.value['OffsetChannelColors'][0]
    if not offset:
        return None
    r = ChannelColors(ifdentry)
    if debug:
        arr = r.toarray()
        arr2 = ifdentry.tiff.data[offset:offset+arr.nbytes]
        assert (arr==arr2).all()
    return r

class ChannelFactors:

    def __init__(self, ifdentry):
        self.ifdentry = ifdentry
        self._offset = None
        self._data = None

    @property
    def offset(self):
        if self._offset is None:
            self._offset = self.ifdentry.value['OffsetChannelFactors'][0]            
        return self._offset

    @property
    def data(self):
        if self._data is None:
            n = self.ifdentry.tiff.get_value(self.offset, numpy.int32)
            sz = 4 + n # n should be equal to 32*nofchannels
            self._data = self.ifdentry.tiff.get_values(self.offset, numpy.ubyte, sz)
        return self._data

    def __str__(self):
        return '%s(size=%r, offset=%r)' % (self.__class__.__name__, self.get_size(), self.offset)

    def get_size(self):
        return self.data.nbytes

    def toarray(self, target=None):
        sz = self.get_size()
        if target is None:
            target = numpy.zeros((sz,), dtype=numpy.ubyte)
        dtype = target.dtype
        target[:self.data.nbytes] = self.data.view(dtype=dtype)
        return target

def channelfactors(ifdentry, debug=True):
    if ifdentry.tag!=CZ_LSMInfo_tag:
        return
    #assert ifdentry.is_lsm
    offset = ifdentry.value['OffsetChannelFactors'][0]
    if not offset:
        return
    r = ChannelFactors(ifdentry)
    if debug:
        arr = r.toarray()
        arr2 = ifdentry.tiff.data[offset:offset+arr.nbytes]
        assert (arr==arr2).all()        
    return r

class ChannelDataTypes:

    def __init__(self, ifdentry):
        self.ifdentry = ifdentry
        self._offset = None
        self._data = None

    @property
    def offset(self):
        if self._offset is None:
            self._offset = self.ifdentry.value['OffsetChannelDataTypes'][0]            
        return self._offset

    @property
    def data(self):
        if self._data is None:
            channels = self.ifdentry.value['DimensionChannels']
            sz = channels * 4
            self._data = self.ifdentry.tiff.get_values(self.offset, numpy.ubyte, sz)
        return self._data

    def __str__(self):
        return '%s(size=%r, offset=%r)' % (self.__class__.__name__, self.get_size(), self.offset)

    def get_size(self):
        return self.data.nbytes

    def toarray(self, target=None):
        sz = self.get_size()
        if target is None:
            target = numpy.zeros((sz,), dtype=numpy.ubyte)
        dtype = target.dtype
        target[:self.data.nbytes] = self.data.view(dtype=dtype)
        return target

def channeldatatypes(ifdentry, debug=True):
    if ifdentry.tag!=CZ_LSMInfo_tag:
        return
    #assert ifdentry.is_lsm
    offset = ifdentry.value['OffsetChannelDataTypes'][0]
    if not offset:
        return
    r = ChannelDataTypes(ifdentry)
    if debug:
        arr = r.toarray()
        arr2 = ifdentry.tiff.data[offset:offset+arr.nbytes]
        assert (arr==arr2).all()        
    return r

class OffsetData:

    def __init__(self, ifdentry, offset_name):
        self.ifdentry = ifdentry
        self.offset_name = offset_name
        self._offset = None
        self._data = None

    @property
    def offset(self):
        if self._offset is None:
            self._offset = self.ifdentry.value[self.offset_name][0]            
        return self._offset

    @property
    def data(self):
        if self._data is None:
            sz = self.ifdentry.tiff.get_value(self.offset, numpy.uint32)
            self._data = self.ifdentry.tiff.get_values(self.offset, numpy.ubyte, sz)
        return self._data

    def __str__(self):
        return '%s(name=%r, size=%r, offset=%r)' % (self.__class__.__name__, self.offset_name, self.get_size(), self.offset)

    def get_size(self):
        return self.data.nbytes

    def toarray(self, target=None):
        sz = self.get_size()
        if target is None:
            target = numpy.zeros((sz,), dtype=numpy.ubyte)
        dtype = target.dtype
        target[:self.data.nbytes] = self.data.view(dtype=dtype)
        return target
        

def offsetdata(ifdentry, offset_name, debug=True):
    if ifdentry.tag!=CZ_LSMInfo_tag:
        return
    #assert ifdentry.is_lsm
    offset = ifdentry.value[offset_name][0]
    if not offset:
        return
    r = OffsetData(ifdentry, offset_name)
    if debug:
        arr = r.toarray()
        arr2 = ifdentry.tiff.data[offset:offset+arr.nbytes]
        assert (arr==arr2).all()        
    return r

class DrawingElement:

    def __init__(self, ifdentry, offset_name):
        self.ifdentry = ifdentry
        self.offset_name = offset_name
        self._offset = None
        self._data = None

    @property
    def offset(self):
        if self._offset is None:
            self._offset = self.ifdentry.value[self.offset_name][0]            
        return self._offset

    @property
    def data(self):
        if self._data is None:
            n = self.ifdentry.tiff.get_value(self.offset, numpy.int32)
            sz = self.ifdentry.tiff.get_value(self.offset+4, numpy.int32)
            self._data = self.ifdentry.tiff.get_values(self.offset, numpy.ubyte, sz)
        return self._data

    def __str__(self):
        return '%s(name=%r, size=%r, offset=%r)' % (self.__class__.__name__, self.offset_name, self.get_size(), self.offset)

    def get_size(self):
        return self.data.nbytes

    def toarray(self, target=None):
        sz = self.get_size()
        if target is None:
            target = numpy.zeros((sz,), dtype=numpy.ubyte)
        dtype = target.dtype
        target[:self.data.nbytes] = self.data.view(dtype=dtype)
        return target

def drawingelement(ifdentry, offset_name, debug=True):
    if ifdentry.tag!=CZ_LSMInfo_tag:
        return
    #assert ifdentry.is_lsm
    offset = ifdentry.value[offset_name][0]
    if not offset:
        return
    r = DrawingElement(ifdentry, offset_name)
    if debug:
        arr = r.toarray()
        arr2 = ifdentry.tiff.data[offset:offset+arr.nbytes]
        assert (arr==arr2).all()        
    return r

class LookupTable:

    def __init__(self, ifdentry, offset_name):
        self.ifdentry = ifdentry
        self.offset_name = offset_name
        self._offset = None
        self._data = None

    @property
    def offset(self):
        if self._offset is None:
            self._offset = self.ifdentry.value[self.offset_name][0]            
        return self._offset

    @property
    def data(self):
        if self._data is None:
            sz = self.ifdentry.tiff.get_value(self.offset, numpy.uint32)
            self._data = self.ifdentry.tiff.get_values(self.offset, numpy.ubyte, sz)
        return self._data

    def __str__(self):
        nsubblocks = self.ifdentry.tiff.get_value(self.offset+4, numpy.uint32)
        nchannels = self.ifdentry.tiff.get_value(self.offset+8, numpy.uint32)
        return '%s(name=%r, size=%r, subblocks=%r, channels=%r, offset=%r)' \
               % (self.__class__.__name__, self.offset_name, self.get_size(),
                  nsubblocks, nchannels, self.offset)

    def get_size(self):
        return self.data.nbytes

    def toarray(self, target=None):
        sz = self.get_size()
        if target is None:
            target = numpy.zeros((sz,), dtype=numpy.ubyte)
        dtype = target.dtype
        target[:self.data.nbytes] = self.data.view(dtype=dtype)
        return target
        

def lookuptable(ifdentry, offset_name, debug=True):
    if ifdentry.tag!=CZ_LSMInfo_tag:
        return
    offset = ifdentry.value[offset_name][0]
    if not offset:
        return
    r = LookupTable(ifdentry, offset_name)
    if debug:
        arr = r.toarray()
        arr2 = ifdentry.tiff.data[offset:offset+arr.nbytes]
        assert (arr==arr2).all()        
    return r

inputlut = lambda ifdentry, debug=True: lookuptable(ifdentry, 'OffsetInputLut', debug=debug)
outputlut = lambda ifdentry, debug=True: lookuptable(ifdentry, 'OffsetOutputLut', debug=debug)
vectoroverlay = lambda ifdentry, debug=True: drawingelement(ifdentry, 'OffsetVectorOverlay', debug=debug)
roi = lambda ifdentry, debug=True: drawingelement(ifdentry, 'OffsetRoi', debug=debug)
bleachroi = lambda ifdentry, debug=True: drawingelement(ifdentry, 'OffsetBleachRoi', debug=debug)
meanofroisoverlay = lambda ifdentry, debug=True: drawingelement(ifdentry, 'OffsetMeanOfRoisOverlay', debug=debug)
topoisolineoverlay = lambda ifdentry, debug=True: drawingelement(ifdentry, 'OffsetTopoIsolineOverlay', debug=debug)
topoprofileoverlay = lambda ifdentry, debug=True: drawingelement(ifdentry, 'OffsetTopoProfileOverlay', debug=debug)
linescanoverlay = lambda ifdentry, debug=True: drawingelement(ifdentry, 'OffsetLinescanOverlay', debug=debug)

CZ_LSMOffsetField_readers = dict(
    OffsetChannelWavelength = channelwavelength,
    OffsetTimeStamps=timestamps,
    OffsetEventList=eventlist,
    OffsetChannelColors = channelcolors,
    OffsetScanInformation = scaninfo,
    OffsetInputLut = inputlut,
    OffsetOutputLut = outputlut,
    OffsetChannelFactors = channelfactors,
    OffsetChannelDataTypes = channeldatatypes,
    OffsetUnmixParameters = lambda ifdentry, debug=True: offsetdata(ifdentry, 'OffsetUnmixParameters', debug=debug),
    OffsetNextRecording = lambda ifdentry, debug=True: offsetdata(ifdentry, 'OffsetNextRecording', debug=debug),
    OffsetKsData = lambda ifdentry, debug=True: offsetdata(ifdentry, 'OffsetKsData', debug=debug),

    OffsetVectorOverlay = vectoroverlay,
    OffsetRoi = roi,
    OffsetBleachRoi = bleachroi,
    OffsetMeanOfRoisOverlay = meanofroisoverlay,
    OffsetTopoIsolineOverlay = topoisolineoverlay,
    OffsetTopoProfileOverlay = topoprofileoverlay,
    OffsetLinescanOverlay = linescanoverlay,
    )

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
    #('Reserved', numpy.dtype('(69,)u4')), # depends on the version of LSM file
    ]

CZ_LSMInfo_dtype_fields_size = 0
for item in CZ_LSMInfo_dtype_fields:
    CZ_LSMInfo_dtype_fields_size += item[1]().itemsize

CZ_LSMTimeStamps_header_dtype = numpy.dtype([
        ('Size', numpy.int32),
        ('NumberTimeStamps', numpy.int32),
        # ('TimeStamp<N>', numpy.float64)
        ])

CZ_LSMEventList_header_dtype = numpy.dtype ([
        ('Size', numpy.int32),
        ('NumberEvents', numpy.int32),
        # ('Event<N>', EventListEntry)
        ])

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
    0x07000000e: ( 'detection channel pinhole name','ASCII'),
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

