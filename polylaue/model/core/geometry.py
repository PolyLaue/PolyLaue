# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

import numpy as np


def geo_from_dioptas(
    poly_poni_path: str,
    output_path: str,
    image_size_x: int,
    image_size_y: int,
    white_beam_shift: float,
):
    imsiy = float(image_size_y)
    wmbs = float(white_beam_shift)
    dt = [1, 1, 1, 1, 1, 1]

    with open(poly_poni_path, 'r') as rf:
        poly_poni = rf.read()

    for w in poly_poni.splitlines():
        ww = w.split()
        if 'PixelSize1:' in ww:
            dt[0] = 0
            pix = float(ww[1]) * 1000.0
            print('Pixel size, mm:', pix)
        if '"pixel2":' in ww:
            dt[0] = 0
            ss = ww[4]
            sss = len(ww[4])
            pix = float(ss[: (sss - 1)]) * 1000.0
            print('Pixel size, mm:', pix)
        if 'Distance:' in ww:
            dt[1] = 0
            sam_det_d = float(ww[1]) * 1000.0
            print('Sample to detector distance, mm:', sam_det_d)
        if 'Poni1:' in ww:
            dt[2] = 0
            PoniY = float(ww[1])
        if 'Poni2:' in ww:
            dt[3] = 0
            PoniX = float(ww[1])
        if 'Rot1:' in ww:
            dt[4] = 0
            rot1 = float(ww[1])
            print('Rot1, rad:', rot1)
        if 'Rot2:' in ww:
            dt[5] = 0
            rot2 = float(ww[1])
            print('Rot2, rad:', rot2)
    if 1 in dt:
        return '...Error! Unknown format'
    PoniX = PoniX * 1000.0 / pix
    PoniY = imsiy - PoniY * 1000.0 / pix + wmbs / pix
    print('PoniX, pix:', PoniX)
    print('PoniY, pix:', PoniY)
    beam_x = np.cos(rot2) * np.cos(np.pi / 2.0 + rot1)
    beam_y = np.cos(np.pi / 2.0 + rot2)
    beam_z = np.cos(rot2) * np.cos(rot1)
    dt = []
    dt.append(PoniX)
    dt.append(PoniY)
    det_org = np.array(dt, dtype=np.float64)
    dt = []
    dt.append(beam_x)
    dt.append(beam_y)
    dt.append(beam_z)
    beam_dir = np.array(dt, dtype=np.float64)
    dt = []
    dtl = []
    dtl.append(0)
    dtl.append(0)
    dt.append(dtl)
    dtl = []
    dtl.append(image_size_x)
    dtl.append(0)
    dt.append(dtl)
    dtl = []
    dtl.append(image_size_x)
    dtl.append(image_size_y)
    dt.append(dtl)
    dtl = []
    dtl.append(0)
    dtl.append(image_size_y)
    dt.append(dtl)
    im_corn = np.array(dt, dtype=np.float64)
    dt = []
    for i in im_corn:
        dt.append(sam_det_d)
    ang_vec1 = np.hstack(
        (
            ((im_corn - det_org) * np.float64(pix)),
            np.expand_dims(np.array(dt, dtype=np.float64), axis=1),
        )
    )
    ang_vec2 = ang_vec1 / np.expand_dims(
        np.sqrt(np.sum(np.square(ang_vec1), axis=1)), axis=1
    )
    ang_tet = np.acos(float(np.min(ang_vec2 @ beam_dir))) / 2.0
    print('Largest teta, deg.:', round((ang_tet * 180.0 / np.pi), 2))
    ang_sol = float(np.min(ang_vec2[:, 2]))
    dt = []
    dt.append(pix)
    dt.append(sam_det_d)
    dt.append(ang_tet)
    dt.append(ang_sol)
    pix_dist = np.array(dt, dtype=np.float64)
    np.savez(output_path, iitt1=det_org, iitt2=beam_dir, iitt3=pix_dist)


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
