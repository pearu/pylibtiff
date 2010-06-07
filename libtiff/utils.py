
# Author: Pearu Peterson
# Created: June 2010

from __future__ import division
__all__ = ['bytes2str']

VERBOSE = False

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
