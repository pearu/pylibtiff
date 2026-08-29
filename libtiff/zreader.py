"""Reads zstacks off of disk and stores them in an np.memmap array."""
import numpy as np
import os
import tempfile


def roundup(num, multiple):
    """Rounds a number to the nearest larger multiple. Returns an int."""
    if int(num / multiple) == num / multiple:
        return num
    else:
        return int((num + multiple) / multiple) * multiple

def rounddown(num, multiple):
    """Rounds a number to the nearest lower multiple. Returns an int."""
    return int(num / multiple) * multiple

def get_tiled_bbox(x, y, roi_width, roi_height, tile_width, tile_height):
    """Returns the top left corner of the (x,y) pixels enclosing tile, and the enclosing width, height."""
    x1 = rounddown(x, tile_width)
    y1 = roundup(y, tile_height)
    roi_width1 = roi_width + (x-x1)
    roi_height1 = roi_height + (y-y1)

    return x1, y1, roi_width1, roi_height1


class ZReader():
    """Extracts TIFF images which contain a depth dimensions. 

    Currently this class assumes the data is stored in YCRCB format. Data stored in this format has subtly different
    dimensions than the declared dimensions in the TIFF tags. 

    YCRCB contains 3 channels, cR, Cb, and luminance. However the cR and cB channels are downsampled by a factor of 2.
    The luminance channel is not downsampled. This results in an image with a stored shape of (X/2, Y/2, 6), where each
    stored pixel represents a 2x2 region in the image and contains (cR, cB, l1, l2, l3, 4)."""
    def __init__(self, tiff):
        self.tiff = tiff

    def read_roi(self, region, X, Y, r_width, r_height):
        """Reads regions into memory with shape (Depth, Height, Width, Channels).
        region: np array to hold returned image, shape: (depths, x, y, 6). Accepts memmapped arrays."""
        # Remap coords for YCRCB space
        # RGB:YCRCB = (x,y,3):(x/2,y/2,6)
        X = int(X/2)
        Y = int(Y/2)
        num_depths = self.tiff.GetField("ImageDepth")
        num_icols = int(r_width / 2)
        num_irows = int(r_height / 2)
        num_tcols = int(self.tiff.GetField("TileWidth") / 2)
        num_trows = int(self.tiff.GetField("TileLength") / 2)
        samples_pp = self.tiff.GetField('SamplesPerPixel') * 2
        # we only have a single image plane, so that's easy at least.
        plane_index = 0

        tmp_tile = np.zeros((num_trows, num_tcols, samples_pp), dtype=region.dtype, order='C')

        for depth_index in range(num_depths):
            for x in range(X, X + num_icols, num_tcols):
                for y in range(Y, Y + num_irows, num_trows):
                    # We need to use RGB coords to index tiles with libtiff, even though it returns YCRCB formatted data.
                    r = self.tiff.ReadTile(tmp_tile.ctypes.data, x*2, y*2, depth_index, plane_index)

                    if not r:
                        raise ValueError(
                            "Could not read tile x:%d,y:%d,z:%d,sample:%d from file" %
                            (x, y, plane_index, depth_index))

                    # tile_width = num_tcols
                    # tile_height = num_trows

                    region[depth_index, y-Y: y-Y + num_trows, x-X: x-X + num_tcols] = \
                        tmp_tile[:num_trows, :num_tcols]

        return region

    def read_all_z_tiles(self, dtype=np.uint8):
        """Reads 4 dimensional images into memory with shape (Depth, Height, Width, Channels)."""
        num_tcols = int(self.tiff.GetField("TileWidth") / 2)
        num_trows = int(self.tiff.GetField("TileLength") / 2)
        num_icols = int(self.tiff.GetField("ImageWidth") / 2)
        num_irows = int(self.tiff.GetField("ImageLength") / 2)
        num_depths = self.tiff.GetField("ImageDepth")
        # this number includes extra samples [edit: huh?]
        samples_pp = self.tiff.GetField('SamplesPerPixel') * 2

        def read_plane(plane, plane_index=0, depth_index=0):
            for x in range(0, num_icols, num_tcols):
                for y in range(0, num_irows, num_trows):
                    # input data is 2x as many dims per pixel as parameters state.
                    tmp_tile = np.empty((num_trows, num_tcols, samples_pp), dtype=dtype, order='C')
                    r = self.tiff.ReadTile(tmp_tile.ctypes.data, x * 2, y * 2, depth_index, plane_index)
                    if not r:
                        raise ValueError(
                            "Could not read tile x:%d,y:%d,z:%d,sample:%d from file" %
                            (x, y, plane_index, depth_index))

                    # if the tile is on the edge, it is smaller
                    tile_width = min(num_tcols, num_icols - x)
                    tile_height = min(num_trows, num_irows - y)

                    plane[y:y + tile_height, x:x + tile_width] = \
                        tmp_tile[:tile_height, :tile_width]

        tmpfile = os.path.join(tempfile.mkdtemp(prefix=os.path.expanduser("~/data/tmp/zstack/")), "tmparr.dat")
        full_image = np.memmap(tmpfile, shape=(num_depths, num_irows, num_icols, samples_pp),
                               dtype=dtype, order='C', mode="w+")

        for depth_index in range(num_depths):
                read_plane(plane=full_image[depth_index], depth_index=depth_index)

        return full_image
