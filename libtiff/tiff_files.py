
__all__ = ['TiffFiles']

import time

from .tiff_file import TiffFile
from .tiff_array import TiffArray
from .tiff_sample_plane import TiffSamplePlane, TiffSamplePlaneLazy
from .tiff_base import TiffBase

class TiffFiles(TiffBase):
    """Represent a collection of TIFF files as a single TIFF source object.

    See also
    --------
    TiffFile, TiffChannelsAndFiles
    """

    def __init__(self, files, time_map = {}, verbose = False):
        """
        Parameters
        ----------
        files : list
          A list of TIFF file names.
        time_map : dict
          A dictionary of TIFF file names and a list of time values
          corresponding to image file directories (IFDs) in the
          corresponding TIFF files.
        verbose : bool
        """
        self.verbose = verbose
        self.files = files
        self.tiff_files = {}
        self.time_map = time_map


    def get_tiff_file(self, filename):
        tiff = self.tiff_files.get(filename)
        if tiff is None:
            tiff = TiffFile(filename, verbose=self.verbose)
            #tiff.set_time(self.time_map.get(filename))
            self.tiff_files[filename] = tiff
        return tiff

    def get_tiff_array(self, sample_index = 0, subfile_type=0, assume_one_image_per_file=False):
        """ Return an array of images.

        Parameters
        ----------
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
        start = time.time ()
        planes = []
        
        if assume_one_image_per_file:
            for index, filename in enumerate (self.files):
                time_lst = self.time_map.get(filename)
                if index==0:
                    tiff = self.get_tiff_file(filename)
                    assert len (tiff.IFD)==1,`len (tiff.IFD)`
                    ifd = tiff.IFD[0]
                    assert ifd.get_value('NewSubfileType', subfile_type)==subfile_type
                    plane = TiffSamplePlane(ifd, sample_index=sample_index)
                else:
                    def tiff_file_getter(parent=self, filename=filename):
                        tiff = parent.get_tiff_file(filename)
                        return tiff
                    plane = TiffSamplePlaneLazy(tiff_file_getter)
                    plane.copy_attrs(planes[0])
                if time_lst is not None:
                    assert len (time_lst)==1,`len(time_lst)`
                    plane.set_time(time_lst[0])
                planes.append(plane)                    
        else:
            for filename in self.files:
                tiff = self.get_tiff_file(filename)
                time_lst = self.time_map.get(filename)
                index = 0
                for ifd in tiff.IFD:
                    if ifd.get_value('NewSubfileType', subfile_type) != subfile_type:
                        continue
                    plane = TiffSamplePlane(ifd, sample_index=sample_index)
                    if time_lst is not None:
                        plane.set_time(time_lst[index])
                    planes.append(plane)
                    index += 1
        tiff_array = TiffArray(planes)
        print '%s.get_tiff_array: took %ss' % (self.__class__.__name__, time.time ()-start)
        return tiff_array

    def close (self):
        for tiff in self.tiff_files.values():
            tiff.close()

    __del__ = close


    def get_info(self):
        filename = self.files[0]
        tiff = self.get_tiff_file(filename)
        return tiff.get_info()
