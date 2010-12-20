
from .tiff_file import TiffFile
from .tiff_array import TiffArray, TiffSamplePlane
from .tiff_base import TiffBase

class TiffFiles(TiffBase):

    def __init__(self, files, time_map = {}, verbose = False):
        self.verbose = verbose
        self.files = files
        self.tiff_files = {}
        self.time_map = time_map


    def get_tiff_file(self, filename):
        tiff = self.tiff_files.get(filename)
        if tiff is None:
            tiff = TiffFile(filename, verbose=self.verbose)
            tiff.set_time(self.time_map.get(filename))
            self.tiff_files[filename] = tiff
        return tiff

    def get_tiff_array(self, sample_index = 0, subfile_type=0):
        planes = []
        for index,filename in enumerate(self.files):
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
        return TiffArray(planes)

    def close (self):
        for tiff in self.tiff_files.values():
            tiff.close()

    __del__ = close


    def get_info(self):
        filename = self.files[0]
        tiff = self.get_tiff_file(filename)
        return tiff.get_info()
