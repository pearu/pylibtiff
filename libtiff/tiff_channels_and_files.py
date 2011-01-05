
from .tiff_base import TiffBase

class TiffChannelsAndFiles (TiffBase):

    def __init__(self, channels_files_map):
        self.channels_files_map = channels_files_map
    
    def get_tiff_array (self, channel, sample_index=0, subfile_type=0, assume_one_image_per_file=False):
        return self.channels_files_map[channel].get_tiff_array(sample_index=sample_index,
                                                               subfile_type=subfile_type,
                                                               assume_one_image_per_file=assume_one_image_per_file)

    def get_info(self):
        l = []
        for channel, tiff in self.channels_files_map.items ():
            l.append ('Channel %s:' % (channel))
            l.append ('-'*len(l[-1]))
            l.append (tiff.get_info())
        return '\n'.join(l)
