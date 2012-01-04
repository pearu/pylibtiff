
# Author: Pearu Peterson
# Created: June 2010

from __future__ import division
__all__ = ['bytes2str', 'isindisk']

import os
import optparse

VERBOSE = False

def isindisk(path):
    """ Return True if path is stored in a local disk.
    """
    return os.major(os.stat(path).st_dev) in [3, # HD 
                                              8, # SCSI
                                              ]

def bytes2str(bytes):
    l = []
    Pbytes = bytes//1024**5
    if Pbytes:
        l.append('%sPi' % (Pbytes))
        bytes = bytes - 1024**5 * Pbytes
    Tbytes = bytes//1024**4
    if Tbytes:
        l.append('%sTi' % (Tbytes))
        bytes = bytes - 1024**4 * Tbytes
    Gbytes = bytes//1024**3
    if Gbytes:
        l.append('%sGi' % (Gbytes))
        bytes = bytes - 1024**3 * Gbytes
    Mbytes = bytes//1024**2
    if Mbytes:
        l.append('%sMi' % (Mbytes))
        bytes = bytes - 1024**2 * Mbytes
    kbytes = bytes//1024
    if kbytes:
        l.append('%sKi' % (kbytes))
        bytes = bytes - 1024*kbytes
    if bytes: l.append('%s' % (bytes))
    if not l: return '0 bytes'
    return '+'.join(l) + ' bytes'

class Options(optparse.Values):
    """Holds option keys and values.

    Examples
    --------

      >>> from iocbio.utils import Options
      >>> options = Options(a='abc', n=4)
      >>> print options
      {'a': 'abc', 'n': 4}
      >>> options.get(n=5)
      4
      >>> options.get(m=5)
      5
      >>> print options
      {'a': 'abc', 'm': 5, 'n': 4}
      >>> options2 = Options(options)
      >>> options.get(k = 6)
      >>> print options2 # note that updating options will update also options2
      {'a': 'abc', 'm': 5, 'n': 4, 'k': 6}

    See also
    --------
    __init__
    """
    def __init__(self, *args, **kws):
        """Construct Options instance.

        The following constructions are supported:
        
        + construct Options instance from keyword arguments::

            Options(key1 = value1, key2 = value2, ...)

        + construct Options instance from :pythonlib:`optparse`.Values
          instance and override with keyword arguments::

            Options(<Values instance>, key1 = value1, ...)

        + construct Options instance from Options instance::
        
            Options(<Options instance>, key1 = value1, ...)
        
          Note that both Options instances will share options data.

        See also
        --------
        Options
        """
        if len(args)==0:
            optparse.Values.__init__(self, kws)
        elif len (args)==1:
            arg = args[0]
            if isinstance(arg, Options):
                self.__dict__ = arg.__dict__
                self.__dict__.update(**kws)
            elif isinstance(arg, optparse.Values):
                optparse.Values.__init__(self, arg.__dict__)
                self.__dict__.update(**kws)
            elif isinstance(arg, type (None)):
                optparse.Values.__init__(self, kws)
            else:
                raise NotImplementedError(`arg`)
        else:
            raise NotImplementedError(`args`)
    def get(self, **kws):
        """Return option value.

        For example, ``options.get(key = default_value)`` will return
        the value of an option with ``key``. If such an option does
        not exist then update ``options`` and return
        ``default_value``.

        Parameters
        ----------
        key = default_value
          Specify option key and its default value. 

        Returns
        -------
        value
          Value of the option.

        See also
        --------
        Options
        """
        assert len (kws)==1,`kws`
        key, default = kws.items()[0]
        if key not in self.__dict__:
            if VERBOSE:
                print 'Options.get: adding new option: %s=%r' % (key, default)
            self.__dict__[key] = default
        value = self.__dict__[key]
        if value is None:
            value = self.__dict__[key] = default
        return value

def splitcommandline(line):
    items, stopchar = splitquote (line)
    result = []
    for item in items:
        if item[0]==item[-1] and item[0] in '\'"':
            result.append (item[1:-1])
        else:
            result.extend (item.split())
    return result

def splitquote(line, stopchar=None, lower=False, quotechars = '"\''):
    """
    Fast LineSplitter.

    Copied from The F2Py Project.
    """
    items = []
    i = 0
    while 1:
        try:
            char = line[i]; i += 1
        except IndexError:
            break
        l = []
        l_append = l.append
        nofslashes = 0
        if stopchar is None:
            # search for string start
            while 1:
                if char in quotechars and not nofslashes % 2:
                    stopchar = char
                    i -= 1
                    break
                if char=='\\':
                    nofslashes += 1
                else:
                    nofslashes = 0
                l_append(char)
                try:
                    char = line[i]; i += 1
                except IndexError:
                    break
            if not l: continue
            item = ''.join(l)
            if lower: item = item.lower()
            items.append(item)
            continue
        if char==stopchar:
            # string starts with quotechar
            l_append(char)
            try:
                char = line[i]; i += 1
            except IndexError:
                if l:
                    item = str(''.join(l))
                    items.append(item)
                break
        # else continued string
        while 1:
            if char==stopchar and not nofslashes % 2:
                l_append(char)
                stopchar = None
                break
            if char=='\\':
                nofslashes += 1
            else:
                nofslashes = 0
            l_append(char)
            try:
                char = line[i]; i += 1
            except IndexError:
                break
        if l:
            item = str(''.join(l))
            items.append(item)
    return items, stopchar
