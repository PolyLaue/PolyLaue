# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from pathlib import Path
import re
from typing import Callable

import fabio
import numpy as np
from PIL import Image

from polylaue.typing import PathLike


def identify_loader_function(
    path: PathLike,
) -> Callable[[PathLike], np.ndarray]:
    extension = Path(path).suffix[1:]
    for regex, func in CUSTOM_READERS.items():
        if re.match(regex, extension):
            return func

    # Default to fabio load if nothing else works
    return load_file_with_fabio


def load_image_file(path: PathLike) -> np.ndarray:
    # Automatically identify the file type and load it
    func = identify_loader_function(path)
    return func(path)


def load_tif_file(path: PathLike) -> np.ndarray:
    # Open with Pillow
    return np.array(Image.open(path))


def load_file_with_fabio(path: PathLike) -> np.ndarray:
    with fabio.open(path) as img:
        return img.data


# The key for these custom readers is the regular expression
# that the extension should match.
CUSTOM_READERS = {
    r'^tiff?$': load_tif_file,
}

# Compile the regular expressions
CUSTOM_READERS = {re.compile(k): v for k, v in CUSTOM_READERS.items()}
