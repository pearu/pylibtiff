from __future__ import division
__all__ = ['bytes2str']

def bytes2str(bytes):
    if bytes < 1024:
        return '%s bytes' % (bytes)
    if bytes < 1024**2:
        return '%.3f Kbytes' % (bytes/1024)
    if bytes < 1024**3:
        return '%.3f Mbytes' % (bytes/1024**2)
    if bytes < 1024**4:
        return '%.3f Gbytes' % (bytes/1024**3)
    if bytes < 1024**5:
        return '%.3f Tbytes' % (bytes/1024**4)
    return '%s bytes' % (bytes)
