
from .tiff_base import TiffBase


class TiffChannelsAndFiles(TiffBase):
    """Represent a collection of TIFF files as a single TIFF source
    object.

    See also
    --------
    TiffFile, TiffFiles

    """

    def __init__(self, channels_files_map):
        """Parameters
        ----------
        channels_files_map : dict
          A dictionary of channel names and TIFF files (``TiffFiles``
          instances)
        """
        self.channels_files_map = channels_files_map

    def get_tiff_array(self, channel, sample_index=0,
                       subfile_type=0, assume_one_image_per_file=False):
        """ Return an array of images for given channel.

        Parameters
        ----------
        channel : str
          The name of a channel.
        sample_index : int
          Specify sample within a pixel.
        subfile_type : int
          Specify TIFF NewSubfileType used for collecting sample images.
        assume_one_image_per_file : bool
          When True then it is assumed that each TIFF file contains
          exactly one image and all images have the same parameters.
          This knowledge speeds up tiff_array construction as only the
          first TIFF file is opened for reading image parameters. The
          other TIFF files are opened only when particular images are
          accessed.

        Returns
        -------
        tiff_array : TiffArray
          Array of sample images. The array has rank equal to 3.
        """
        return self.channels_files_map[channel].get_tiff_array(
            sample_index=sample_index,
            subfile_type=subfile_type,
            assume_one_image_per_file=assume_one_image_per_file)

    def get_info(self):
        lst = []
        for channel, tiff in list(self.channels_files_map.items()):
            lst.append('Channel %s:' % (channel))
            lst.append('-' * len(lst[-1]))
            lst.append(tiff.get_info())
        return '\n'.join(lst)

    def close(self):
        for tiff in self.channels_files_map.values():
            tiff.close()
