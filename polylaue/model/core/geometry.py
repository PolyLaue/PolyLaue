# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

import numpy as np

from polylaue.typing import PathLike

# The HPCAT setups that have been used to collect Laue data, mapped to
# the direction (x, y) in which the white beam shift is applied to the
# point of normal incidence, in pixels.
DETECTOR_SETUPS = {
    '16BMD': (0, -1),
    '16BMB (2016-2023)': (0, 1),
    '16BMB (before 2016)': (-1, 0),
}
DEFAULT_DETECTOR_SETUP = '16BMD'

# The parameters that must be present in a PONI file
PONI_PARAMETERS = (
    'pixel_size',
    'detector_distance',
    'poni1',
    'poni2',
    'rot1',
    'rot2',
)


def parse_poni(poly_poni_path: PathLike) -> dict:
    """Parse geometry parameters from a PONI file

    Multiple versions of the PONI format are supported (including ones
    where the pixel size is stored in a "Detector_config" JSON entry).

    The returned dict contains 'pixel_size' (mm), 'detector_distance'
    (mm), 'poni1' (m), 'poni2' (m), 'rot1' (rad), and 'rot2' (rad).

    Raises a ValueError if any of these parameters cannot be found.
    """
    params = {}

    with open(poly_poni_path, 'r') as rf:
        poly_poni = rf.read()

    for w in poly_poni.splitlines():
        ww = w.split()
        if 'PixelSize1:' in ww:
            params['pixel_size'] = float(ww[1]) * 1000.0
        if '"pixel2":' in ww:
            # The value ends with a trailing comma or brace
            ss = ww[4]
            params['pixel_size'] = float(ss[:-1]) * 1000.0
        if 'Distance:' in ww:
            params['detector_distance'] = float(ww[1]) * 1000.0
        if 'Poni1:' in ww:
            params['poni1'] = float(ww[1])
        if 'Poni2:' in ww:
            params['poni2'] = float(ww[1])
        if 'Rot1:' in ww:
            params['rot1'] = float(ww[1])
        if 'Rot2:' in ww:
            params['rot2'] = float(ww[1])

    missing = [k for k in PONI_PARAMETERS if k not in params]
    if missing:
        raise ValueError(
            'Unknown PONI format. Could not find the following '
            f'parameters: {", ".join(missing)}'
        )

    return params


def write_geometry_file(
    output_path: str,
    pixel_size: float,
    detector_distance: float,
    poni1: float,
    poni2: float,
    rot1: float,
    rot2: float,
    image_size_x: int,
    image_size_y: int,
    white_beam_shift: float,
    detector_setup: str = DEFAULT_DETECTOR_SETUP,
):
    """Compute the PolyLaue geometry and save it as an NPZ file

    The pixel size and detector distance are in mm, poni1 and poni2 are
    in meters, and the rotations are in radians (all matching the output
    of parse_poni()). The detector setup must be a key of
    DETECTOR_SETUPS.
    """
    pix = pixel_size
    sam_det_d = detector_distance
    imsiy = float(image_size_y)
    wmbs = float(white_beam_shift)
    shift_x, shift_y = DETECTOR_SETUPS[detector_setup]

    PoniX = poni2 * 1000.0 / pix + shift_x * wmbs / pix
    PoniY = imsiy - poni1 * 1000.0 / pix + shift_y * wmbs / pix
    beam_x = np.cos(rot2) * np.cos(np.pi / 2.0 + rot1)
    beam_y = np.cos(np.pi / 2.0 + rot2)
    beam_z = np.cos(rot2) * np.cos(rot1)
    det_org = np.array([PoniX, PoniY], dtype=np.float64)
    beam_dir = np.array([beam_x, beam_y, beam_z], dtype=np.float64)
    im_corn = np.array(
        [
            [0, 0],
            [image_size_x, 0],
            [image_size_x, image_size_y],
            [0, image_size_y],
        ],
        dtype=np.float64,
    )
    ang_vec1 = np.hstack(
        (
            ((im_corn - det_org) * np.float64(pix)),
            np.full((len(im_corn), 1), sam_det_d, dtype=np.float64),
        )
    )
    ang_vec2 = ang_vec1 / np.expand_dims(
        np.sqrt(np.sum(np.square(ang_vec1), axis=1)), axis=1
    )
    ang_tet = np.acos(float(np.min(ang_vec2 @ beam_dir))) / 2.0
    ang_sol = float(np.min(ang_vec2[:, 2]))
    pix_dist = np.array([pix, sam_det_d, ang_tet, ang_sol], dtype=np.float64)
    np.savez(output_path, iitt1=det_org, iitt2=beam_dir, iitt3=pix_dist)


def geo_from_dioptas(
    poly_poni_path: str,
    output_path: str,
    image_size_x: int,
    image_size_y: int,
    white_beam_shift: float,
):
    try:
        params = parse_poni(poly_poni_path)
    except ValueError:
        return '...Error! Unknown format'

    print('Pixel size, mm:', params['pixel_size'])
    print('Sample to detector distance, mm:', params['detector_distance'])
    print('Rot1, rad:', params['rot1'])
    print('Rot2, rad:', params['rot2'])

    write_geometry_file(
        output_path,
        image_size_x=image_size_x,
        image_size_y=image_size_y,
        white_beam_shift=white_beam_shift,
        **params,
    )


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 3:
        sys.exit('Usage: <script> <input.poni> <output.npz>')

    image_size_x = 2048
    image_size_y = 2048
    white_beam_shift = 0.01

    geo_from_dioptas(
        sys.argv[1], sys.argv[2], image_size_x, image_size_y, white_beam_shift
    )
