import numpy as np
from PIL import Image

from polylaue.typing import PathLike


def load_image_file(path: PathLike) -> np.ndarray:
    # For now, just assume Pillow can open it
    return np.array(Image.open(path))
