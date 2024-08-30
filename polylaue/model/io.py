# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from pathlib import Path
import re
from typing import Callable, Optional

import fabio
import numpy as np
from PIL import Image, ImageFile

from polylaue.typing import PathLike

Bounds = tuple[int, int, int, int]
ImageLoader = Callable[[PathLike, Optional[Bounds]], np.ndarray]


def identify_loader_function(
    path: PathLike,
) -> ImageLoader:
    extension = Path(path).suffix[1:]
    for regex, func in CUSTOM_READERS.items():
        if re.match(regex, extension):
            return func

    # Default to fabio load if nothing else works
    return load_file_with_fabio


def load_image_file(
    path: PathLike, bounds: Optional[Bounds] = None
) -> np.ndarray:
    # Automatically identify the file type and load it
    func = identify_loader_function(path)
    return func(path, bounds)


def load_tif_file(
    path: PathLike, bounds: Optional[Bounds] = None
) -> np.ndarray:
    # Open with Pillow
    pil_img = Image.open(path)

    if bounds is not None:
        pil_img = pil_img.crop((bounds[2], bounds[0], bounds[3], bounds[1]))

    asarray = _fast_pil_to_array

    img = asarray(pil_img)

    return img


def load_file_with_fabio(
    path: PathLike, bounds: Optional[Bounds] = None
) -> np.ndarray:
    with fabio.open(path) as img:
        if bounds is not None:
            return img.data[bounds[0] : bounds[1], bounds[2] : bounds[3]]
        else:
            return img.data


# https://uploadcare.com/blog/fast-import-of-pillow-images-to-numpy-opencv-arrays/
def _fast_pil_to_array(im: ImageFile.ImageFile) -> np.ndarray:
    im.load()
    # unpack data
    e = Image._getencoder(im.mode, 'raw', im.mode)
    e.setimage(im.im)

    # NumPy buffer for the result
    shape, typestr = Image._conv_type_shape(im)
    data = np.empty(shape, dtype=np.dtype(typestr))
    mem = data.data.cast('B', (data.data.nbytes,))

    bufsize, s, offset = 65536, 0, 0
    while not s:
        l, s, d = e.encode(bufsize)
        mem[offset : offset + len(d)] = d
        offset += len(d)
    if s < 0:
        raise RuntimeError("encoder error %d in tobytes" % s)

    return data


# The key for these custom readers is the regular expression
# that the extension should match.
CUSTOM_READERS = {
    r'^tiff?$': load_tif_file,
}

# Compile the regular expressions
CUSTOM_READERS = {re.compile(k): v for k, v in CUSTOM_READERS.items()}
