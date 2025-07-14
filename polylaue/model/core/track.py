# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

import numpy as np


def track(
    obs_xy: np.ndarray,
    abc: np.ndarray,
    energy_highest: float,
    det_org: np.ndarray,
    beam_dir: np.ndarray,
    pix_dist: np.ndarray,
    ang_tol: float = 0.07,
    ang_lim: float = 29,
    res_lim: float = 0.3,
    ref_thr: float = 3,
) -> np.ndarray | None:

    abc_dir = np.reshape(abc, (3, -1))
    abc_vol = np.cross(abc_dir[2, :], abc_dir[0, :]) @ abc_dir[1, :]
    abc_rec = (
        np.vstack(
            (
                np.cross(abc_dir[1, :], abc_dir[2, :]),
                np.cross(abc_dir[2, :], abc_dir[0, :]),
                np.cross(abc_dir[0, :], abc_dir[1, :]),
            )
        )
        / abc_vol
    )
    abc_len = np.sqrt(np.sum(np.square(abc_dir), axis=1))
    print('a=, b=, c=:', abc_len)
    abc_nor = abc_dir / np.expand_dims(abc_len, axis=1)
    abc_ang = np.array([0, 0, 0], dtype=np.float64)
    abc_ang[0] = abc_nor[1] @ abc_nor[2]
    abc_ang[1] = abc_nor[2] @ abc_nor[0]
    abc_ang[2] = abc_nor[0] @ abc_nor[1]
    abc_ang = np.degrees(np.arccos(abc_ang))
    print('alpha=, beta=, gamma=:', abc_ang)
    print('Unit cell volume, Angstroms**3:', round(float(abc_vol), 2))
    d_min = (
        0.4246
        * 29.2
        / (2.0 * float(energy_highest) * np.sin(float(pix_dist[2])))
    )
    print(' ')
    print(
        '... Detector opening resolution limit d/n >',
        round(d_min, 4),
        'Angstroms',
    )
    if d_min < float(res_lim):
        d_min = float(res_lim)
        print(' ')
        print(
            '... Sample resolution limit d/n >', round(d_min, 4), 'Angstroms'
        )
    print(' ')
    hkl_max_flo = np.sqrt(np.sum(np.square(abc_dir), axis=1)) / np.float64(
        d_min
    )
    hkl_max = hkl_max_flo.astype(np.int64) + np.int64(1)
    print('h,k,l maximal:', hkl_max)
    max_h = hkl_max[0]
    max_k = hkl_max[1]
    max_l = hkl_max[2]
    h1 = np.expand_dims(np.arange(-max_h, (max_h + 1), dtype=np.int64), axis=1)
    k1 = np.expand_dims(np.arange(-max_k, (max_k + 1), dtype=np.int64), axis=1)
    l1 = np.expand_dims(np.arange(-max_l, (max_l + 1), dtype=np.int64), axis=1)
    h0 = np.expand_dims(
        np.zeros((max_h * np.int64(2) + np.int64(1)), dtype=np.int64), axis=1
    )
    k0 = np.expand_dims(
        np.zeros((max_k * np.int64(2) + np.int64(1)), dtype=np.int64), axis=1
    )
    l0 = np.expand_dims(
        np.zeros((max_l * np.int64(2) + np.int64(1)), dtype=np.int64), axis=1
    )
    h = np.hstack((h1, h0, h0))
    k = np.hstack((k0, k1, k0))
    l = np.hstack((l0, l0, l1))  # noqa
    hkl = np.expand_dims((np.expand_dims(h, axis=1) + k), axis=2) + l
    hkl = np.reshape(
        hkl,
        (
            (
                (max_h * np.int64(2) + np.int64(1))
                * (max_k * np.int64(2) + np.int64(1))
                * (max_l * np.int64(2) + np.int64(1))
            ),
            3,
        ),
    )
    vec_sel = np.sum(np.absolute(hkl), axis=1) != 0
    hkl = hkl[vec_sel, :]
    print('Total number of indices:', np.shape(hkl)[0])
    ind_tot = float(np.shape(hkl)[0])
    vec_sel = np.gcd.reduce(hkl, axis=1) == 1
    hkl = hkl[vec_sel, :]
    ind_rpi = float(np.shape(hkl)[0])
    print(
        'Relatively prime integers:',
        np.shape(hkl)[0],
        '(',
        round((ind_rpi * 100.0 / ind_tot), 2),
        '% )',
    )
    hkl_vec = hkl.astype(np.float64)
    hkl_vec = hkl_vec @ abc_rec
    hkl_dis = np.float64(1) / np.sqrt(np.sum(np.square(hkl_vec), axis=1))
    vec_sel = np.nonzero(hkl_dis > np.float64(d_min))
    hkl_vec = hkl_vec[vec_sel[0], :]
    hkl_dis = hkl_dis[vec_sel[0]]
    hkl_vec = hkl_vec * np.expand_dims(hkl_dis, axis=1)
    hkl = hkl[vec_sel[0], :]
    print(' ')
    print('... n=1')
    print(
        'Sets of crystallographic planes with d >',
        round(d_min, 4),
        'Angstroms:',
        np.shape(hkl)[0],
    )
    dt = []
    for i in obs_xy:
        dt.append(float(pix_dist[1]))
    obs_vec = np.hstack(
        (
            ((obs_xy - det_org) * pix_dist[0]),
            np.expand_dims(np.array(dt, dtype=np.float64), axis=1),
        )
    )
    obs_vec = obs_vec / np.expand_dims(
        np.sqrt(np.sum(np.square(obs_vec), axis=1)), axis=1
    )
    obs_vec = obs_vec - beam_dir
    obs_vec = obs_vec / np.expand_dims(
        np.sqrt(np.sum(np.square(obs_vec), axis=1)), axis=1
    )
    print(' ')
    print('... Observed reflections:', np.shape(obs_vec)[0])
    s1 = np.shape(hkl)[0]
    s2 = np.shape(obs_vec)[0]
    t1 = np.zeros((s1, 3), dtype=np.float64)
    t2 = np.zeros((s2, 3), dtype=np.float64)
    obs_vec = np.expand_dims(obs_vec, axis=1) + t1
    obs_vec = np.reshape(obs_vec, ((s1 * s2), 3))
    hkl_vec = np.expand_dims(t2, axis=1) + hkl_vec
    hkl_vec = np.reshape(hkl_vec, ((s1 * s2), 3))
    vec_sel = np.nonzero(
        np.sum((obs_vec * hkl_vec), axis=1)
        > np.cos(np.radians(np.float64(ang_lim)))
    )
    hkl_vec = hkl_vec[vec_sel[0], :]
    obs_vec = obs_vec[vec_sel[0], :]
    print('Possible indices in total:', np.shape(hkl_vec)[0])
    mm = np.int64(10)
    sh1 = np.expand_dims(np.arange(-mm, (mm + 1), dtype=np.int64), axis=1)
    sk1 = np.expand_dims(np.arange(-mm, (mm + 1), dtype=np.int64), axis=1)
    sl1 = np.expand_dims(np.arange(-mm, (mm + 1), dtype=np.int64), axis=1)
    sh0 = np.expand_dims(
        np.zeros((mm * np.int64(2) + np.int64(1)), dtype=np.int64), axis=1
    )
    sk0 = np.expand_dims(
        np.zeros((mm * np.int64(2) + np.int64(1)), dtype=np.int64), axis=1
    )
    sl0 = np.expand_dims(
        np.zeros((mm * np.int64(2) + np.int64(1)), dtype=np.int64), axis=1
    )
    sh = np.hstack((sh1, sh0, sh0))
    sk = np.hstack((sk0, sk1, sk0))
    sl = np.hstack((sl0, sl0, sl1))
    shkl = np.expand_dims((np.expand_dims(sh, axis=1) + sk), axis=2) + sl
    shkl = np.reshape(
        shkl,
        (
            (
                (mm * np.int64(2) + np.int64(1))
                * (mm * np.int64(2) + np.int64(1))
                * (mm * np.int64(2) + np.int64(1))
            ),
            3,
        ),
    )
    vec_sel = np.sum(np.absolute(shkl), axis=1) != 0
    shkl = shkl[vec_sel, :]
    s1 = np.shape(hkl_vec)[0]
    t1 = np.zeros((s1, 3), dtype=np.float64)
    obs_pri = np.expand_dims(obs_vec, axis=1) + t1
    obs_pri = np.reshape(obs_pri, ((s1 * s1), 3))
    obs_sec = np.expand_dims(t1, axis=1) + obs_vec
    obs_sec = np.reshape(obs_sec, ((s1 * s1), 3))
    hkl_pri = np.expand_dims(hkl_vec, axis=1) + t1
    hkl_pri = np.reshape(hkl_pri, ((s1 * s1), 3))
    hkl_sec = np.expand_dims(t1, axis=1) + hkl_vec
    hkl_sec = np.reshape(hkl_sec, ((s1 * s1), 3))
    t1 = np.zeros((s1, 1), dtype=np.int64)
    nnn = np.expand_dims(np.arange(s1, dtype=np.int64), axis=1)
    nnn_pri = np.expand_dims(nnn, axis=1) + t1
    nnn_pri = np.reshape(nnn_pri, (s1 * s1))
    nnn_sec = np.expand_dims(t1, axis=1) + nnn
    nnn_sec = np.reshape(nnn_sec, (s1 * s1))
    vec_sel = np.nonzero((nnn_sec - nnn_pri) > np.int64(0))
    obs_pri = obs_pri[vec_sel[0], :]
    obs_sec = obs_sec[vec_sel[0], :]
    hkl_pri = hkl_pri[vec_sel[0], :]
    hkl_sec = hkl_sec[vec_sel[0], :]
    t1 = np.sum((hkl_pri * hkl_sec), axis=1)
    vec_sel = np.nonzero(np.absolute(t1) < np.cos(np.radians(np.float64(20))))
    obs_pri = obs_pri[vec_sel[0], :]
    obs_sec = obs_sec[vec_sel[0], :]
    hkl_pri = hkl_pri[vec_sel[0], :]
    hkl_sec = hkl_sec[vec_sel[0], :]
    t2 = np.sum((obs_pri * obs_sec), axis=1)
    vec_sel = np.nonzero(np.absolute(t2) < np.cos(np.radians(np.float64(20))))
    obs_pri = obs_pri[vec_sel[0], :]
    obs_sec = obs_sec[vec_sel[0], :]
    hkl_pri = hkl_pri[vec_sel[0], :]
    hkl_sec = hkl_sec[vec_sel[0], :]
    t1 = np.sum((hkl_pri * hkl_sec), axis=1)
    t2 = np.sum((obs_pri * obs_sec), axis=1)
    t1 = np.degrees(np.arccos(t1))
    t2 = np.degrees(np.arccos(t2))
    vec_sel = np.nonzero(np.absolute(t1 - t2) < np.float64(ang_tol))
    obs_pri = obs_pri[vec_sel[0], :]
    obs_sec = obs_sec[vec_sel[0], :]
    hkl_pri = hkl_pri[vec_sel[0], :]
    hkl_sec = hkl_sec[vec_sel[0], :]
    print(
        'Combinations of primary and secondary vectors:', np.shape(hkl_sec)[0]
    )
    print('J. Appl. Phys., Vol. 86, No. 9, 1 November 1999, 5249-5255')
    hkl_axi1 = hkl_pri
    obs_axi1 = obs_pri
    hkl_axi2 = np.cross(hkl_axi1, hkl_sec)
    hkl_axi2 = hkl_axi2 / np.expand_dims(
        np.sqrt(np.sum(np.square(hkl_axi2), axis=1)), axis=1
    )
    obs_axi2 = np.cross(obs_axi1, obs_sec)
    obs_axi2 = obs_axi2 / np.expand_dims(
        np.sqrt(np.sum(np.square(obs_axi2), axis=1)), axis=1
    )
    hkl_axi3 = np.cross(hkl_axi1, hkl_axi2)
    obs_axi3 = np.cross(obs_axi1, obs_axi2)
    hkl_x = np.sum((np.expand_dims(hkl_axi1, axis=1) * hkl_vec), axis=2)
    hkl_y = np.sum((np.expand_dims(hkl_axi2, axis=1) * hkl_vec), axis=2)
    hkl_z = np.sum((np.expand_dims(hkl_axi3, axis=1) * hkl_vec), axis=2)
    obs_x = np.sum((np.expand_dims(obs_axi1, axis=1) * obs_vec), axis=2)
    obs_y = np.sum((np.expand_dims(obs_axi2, axis=1) * obs_vec), axis=2)
    obs_z = np.sum((np.expand_dims(obs_axi3, axis=1) * obs_vec), axis=2)
    vec_sel = (hkl_x * obs_x + hkl_y * obs_y + hkl_z * obs_z) > np.cos(
        np.radians(np.float64(ang_tol))
    )
    com_sel = np.zeros(np.shape(obs_z), dtype=np.int64)
    com_sel[vec_sel] = np.int64(1)
    com_sel = np.sum(com_sel, axis=1)
    if int(np.max(com_sel)) > int(ref_thr):
        vec_sel = np.nonzero(com_sel > np.int64(ref_thr))
        com_sel = com_sel[vec_sel[0]]
        hkl_axi1 = hkl_axi1[vec_sel[0], :]
        hkl_axi2 = hkl_axi2[vec_sel[0], :]
        hkl_axi3 = hkl_axi3[vec_sel[0], :]
        obs_axi1 = obs_axi1[vec_sel[0], :]
        obs_axi2 = obs_axi2[vec_sel[0], :]
        obs_axi3 = obs_axi3[vec_sel[0], :]
        n_foun = 0
        s1 = int(np.shape(obs_axi1)[0])
        for i in range(s1):
            if n_foun < int(com_sel[np.int64(i)]):
                hkl_axs1 = hkl_axi1[np.int64(i), :]
                hkl_axs2 = hkl_axi2[np.int64(i), :]
                hkl_axs3 = hkl_axi3[np.int64(i), :]
                obs_axs1 = obs_axi1[np.int64(i), :]
                obs_axs2 = obs_axi2[np.int64(i), :]
                obs_axs3 = obs_axi3[np.int64(i), :]
                hkl_mat = np.hstack(
                    (
                        np.expand_dims(hkl_axs1, axis=1),
                        np.expand_dims(hkl_axs2, axis=1),
                        np.expand_dims(hkl_axs3, axis=1),
                    )
                )
                obs_mat = np.hstack(
                    (
                        np.expand_dims(obs_axs1, axis=1),
                        np.expand_dims(obs_axs2, axis=1),
                        np.expand_dims(obs_axs3, axis=1),
                    )
                )
                abc_dir_m = abc_dir @ hkl_mat
                abc_dir_m = abc_dir_m @ obs_mat.T
                shkl_vec1 = shkl.astype(np.float64)
                shkl_vec1 = shkl_vec1 @ abc_dir
                shkl_vec1 = shkl_vec1 / np.expand_dims(
                    np.sqrt(np.sum(np.square(shkl_vec1), axis=1)), axis=1
                )
                shkl_vec2 = shkl.astype(np.float64)
                shkl_vec2 = shkl_vec2 @ abc_dir_m
                shkl_vec2 = shkl_vec2 / np.expand_dims(
                    np.sqrt(np.sum(np.square(shkl_vec2), axis=1)), axis=1
                )
                ang = float(np.min(np.sum((shkl_vec1 * shkl_vec2), axis=1)))
                ang = np.acos(ang) * 180.0 / np.pi
                if ang < float(ang_lim):
                    nang = ang
                    abc_dir_n = abc_dir_m
                    n_foun = int(com_sel[np.int64(i)])
        print(' ')
        print('Indexed reflections:', n_foun)
        print('Angular shift, deg.:', round(nang, 2))
        abc_dir_n = np.reshape(abc_dir_n, 9)
        return abc_dir_n


def track_py(
    obs_xy: np.ndarray,
    abc: np.ndarray,
    energy_highest: float,
    det_org: np.ndarray,
    beam_dir: np.ndarray,
    pix_dist: np.ndarray,
    ang_tol: float = 0.07,
    ang_lim: float = 29,
    res_lim: float = 0.3,
    ref_thr: float = 3,
) -> np.ndarray | None:
    """This version of track() takes up substantially less RAM, but
    may run slower"""

    abc_dir = np.reshape(abc, (3, -1))
    abc_vol = np.cross(abc_dir[2, :], abc_dir[0, :]) @ abc_dir[1, :]
    abc_rec = (
        np.vstack(
            (
                np.cross(abc_dir[1, :], abc_dir[2, :]),
                np.cross(abc_dir[2, :], abc_dir[0, :]),
                np.cross(abc_dir[0, :], abc_dir[1, :]),
            )
        )
        / abc_vol
    )
    abc_len = np.sqrt(np.sum(np.square(abc_dir), axis=1))
    print('a=, b=, c=:', abc_len)
    abc_nor = abc_dir / np.expand_dims(abc_len, axis=1)
    abc_ang = np.array([0, 0, 0], dtype=np.float64)
    abc_ang[0] = abc_nor[1] @ abc_nor[2]
    abc_ang[1] = abc_nor[2] @ abc_nor[0]
    abc_ang[2] = abc_nor[0] @ abc_nor[1]
    abc_ang = np.degrees(np.arccos(abc_ang))
    print('alpha=, beta=, gamma=:', abc_ang)
    print('Unit cell volume, Angstroms**3:', round(float(abc_vol), 2))
    d_min = (
        0.4246
        * 29.2
        / (2.0 * float(energy_highest) * np.sin(float(pix_dist[2])))
    )
    print(' ')
    print(
        '... Detector opening resolution limit d/n >',
        round(d_min, 4),
        'Angstroms',
    )
    if d_min < float(res_lim):
        d_min = float(res_lim)
        print(' ')
        print(
            '... Sample resolution limit d/n >', round(d_min, 4), 'Angstroms'
        )
    print(' ')
    hkl_max_flo = np.sqrt(np.sum(np.square(abc_dir), axis=1)) / np.float64(
        d_min
    )
    hkl_max = hkl_max_flo.astype(np.int64) + np.int64(1)
    print('h,k,l maximal:', hkl_max)
    max_h = hkl_max[0]
    max_k = hkl_max[1]
    max_l = hkl_max[2]
    h1 = np.expand_dims(np.arange(-max_h, (max_h + 1), dtype=np.int64), axis=1)
    k1 = np.expand_dims(np.arange(-max_k, (max_k + 1), dtype=np.int64), axis=1)
    l1 = np.expand_dims(np.arange(-max_l, (max_l + 1), dtype=np.int64), axis=1)
    h0 = np.expand_dims(
        np.zeros((max_h * np.int64(2) + np.int64(1)), dtype=np.int64), axis=1
    )
    k0 = np.expand_dims(
        np.zeros((max_k * np.int64(2) + np.int64(1)), dtype=np.int64), axis=1
    )
    l0 = np.expand_dims(
        np.zeros((max_l * np.int64(2) + np.int64(1)), dtype=np.int64), axis=1
    )
    h = np.hstack((h1, h0, h0))
    k = np.hstack((k0, k1, k0))
    l = np.hstack((l0, l0, l1))  # noqa
    hkl = np.expand_dims((np.expand_dims(h, axis=1) + k), axis=2) + l
    hkl = np.reshape(
        hkl,
        (
            (
                (max_h * np.int64(2) + np.int64(1))
                * (max_k * np.int64(2) + np.int64(1))
                * (max_l * np.int64(2) + np.int64(1))
            ),
            3,
        ),
    )
    vec_sel = np.sum(np.absolute(hkl), axis=1) != 0
    hkl = hkl[vec_sel, :]
    print('Total number of indices:', np.shape(hkl)[0])
    ind_tot = float(np.shape(hkl)[0])
    vec_sel = np.gcd.reduce(hkl, axis=1) == 1
    hkl = hkl[vec_sel, :]
    ind_rpi = float(np.shape(hkl)[0])
    print(
        'Relatively prime integers:',
        np.shape(hkl)[0],
        '(',
        round((ind_rpi * 100.0 / ind_tot), 2),
        '% )',
    )
    hkl_vec = hkl.astype(np.float64)
    hkl_vec = hkl_vec @ abc_rec
    hkl_dis = np.float64(1) / np.sqrt(np.sum(np.square(hkl_vec), axis=1))
    vec_sel = np.nonzero(hkl_dis > np.float64(d_min))
    hkl_vec = hkl_vec[vec_sel[0], :]
    hkl_dis = hkl_dis[vec_sel[0]]
    hkl_vec = hkl_vec * np.expand_dims(hkl_dis, axis=1)
    hkl = hkl[vec_sel[0], :]
    print(' ')
    print('... n=1')
    print(
        'Sets of crystallographic planes with d >',
        round(d_min, 4),
        'Angstroms:',
        np.shape(hkl)[0],
    )
    dt = []
    for i in obs_xy:
        dt.append(float(pix_dist[1]))
    obs_vec = np.hstack(
        (
            ((obs_xy - det_org) * pix_dist[0]),
            np.expand_dims(np.array(dt, dtype=np.float64), axis=1),
        )
    )
    obs_vec = obs_vec / np.expand_dims(
        np.sqrt(np.sum(np.square(obs_vec), axis=1)), axis=1
    )
    obs_vec = obs_vec - beam_dir
    obs_vec = obs_vec / np.expand_dims(
        np.sqrt(np.sum(np.square(obs_vec), axis=1)), axis=1
    )
    print(' ')
    print('... Observed reflections:', np.shape(obs_vec)[0])
    s1 = np.shape(hkl)[0]
    s2 = np.shape(obs_vec)[0]
    t1 = np.zeros((s1, 3), dtype=np.float64)
    t2 = np.zeros((s2, 3), dtype=np.float64)
    obs_vec = np.expand_dims(obs_vec, axis=1) + t1
    obs_vec = np.reshape(obs_vec, ((s1 * s2), 3))
    hkl_vec = np.expand_dims(t2, axis=1) + hkl_vec
    hkl_vec = np.reshape(hkl_vec, ((s1 * s2), 3))
    vec_sel = np.nonzero(
        np.sum((obs_vec * hkl_vec), axis=1)
        > np.cos(np.radians(np.float64(ang_lim)))
    )
    hkl_vec = hkl_vec[vec_sel[0], :]
    obs_vec = obs_vec[vec_sel[0], :]
    print('Possible indices in total:', np.shape(hkl_vec)[0])
    mm = np.int64(10)
    sh1 = np.expand_dims(np.arange(-mm, (mm + 1), dtype=np.int64), axis=1)
    sk1 = np.expand_dims(np.arange(-mm, (mm + 1), dtype=np.int64), axis=1)
    sl1 = np.expand_dims(np.arange(-mm, (mm + 1), dtype=np.int64), axis=1)
    sh0 = np.expand_dims(
        np.zeros((mm * np.int64(2) + np.int64(1)), dtype=np.int64), axis=1
    )
    sk0 = np.expand_dims(
        np.zeros((mm * np.int64(2) + np.int64(1)), dtype=np.int64), axis=1
    )
    sl0 = np.expand_dims(
        np.zeros((mm * np.int64(2) + np.int64(1)), dtype=np.int64), axis=1
    )
    sh = np.hstack((sh1, sh0, sh0))
    sk = np.hstack((sk0, sk1, sk0))
    sl = np.hstack((sl0, sl0, sl1))
    shkl = np.expand_dims((np.expand_dims(sh, axis=1) + sk), axis=2) + sl
    shkl = np.reshape(
        shkl,
        (
            (
                (mm * np.int64(2) + np.int64(1))
                * (mm * np.int64(2) + np.int64(1))
                * (mm * np.int64(2) + np.int64(1))
            ),
            3,
        ),
    )
    vec_sel = np.sum(np.absolute(shkl), axis=1) != 0
    shkl = shkl[vec_sel, :]
    n_foun = 0
    n_psc = 0
    s1 = int(np.shape(hkl_vec)[0])
    for i in range(s1):
        for j in range((i + 1), s1):
            hkl_pri = hkl_vec[np.int64(i), :]
            hkl_sec = hkl_vec[np.int64(j), :]
            obs_pri = obs_vec[np.int64(i), :]
            obs_sec = obs_vec[np.int64(j), :]
            t1 = np.sum(hkl_pri * hkl_sec)
            t2 = np.sum(obs_pri * obs_sec)
            if float(np.absolute(t1)) < np.cos(
                float(20.0) * np.pi / float(180.0)
            ):
                if float(np.absolute(t2)) < np.cos(
                    float(20.0) * np.pi / float(180.0)
                ):
                    t1 = np.degrees(np.arccos(t1))
                    t2 = np.degrees(np.arccos(t2))
                    if float(np.absolute(t1 - t2)) < float(ang_tol):
                        n_psc = n_psc + 1
                        hkl_axi1 = hkl_pri
                        obs_axi1 = obs_pri
                        hkl_axi2 = np.cross(hkl_axi1, hkl_sec)
                        hkl_axi2 = hkl_axi2 / np.sqrt(
                            np.sum(np.square(hkl_axi2))
                        )
                        obs_axi2 = np.cross(obs_axi1, obs_sec)
                        obs_axi2 = obs_axi2 / np.sqrt(
                            np.sum(np.square(obs_axi2))
                        )
                        hkl_axi3 = np.cross(hkl_axi1, hkl_axi2)
                        obs_axi3 = np.cross(obs_axi1, obs_axi2)
                        hkl_mat = np.hstack(
                            (
                                np.expand_dims(hkl_axi1, axis=1),
                                np.expand_dims(hkl_axi2, axis=1),
                                np.expand_dims(hkl_axi3, axis=1),
                            )
                        )
                        obs_mat = np.hstack(
                            (
                                np.expand_dims(obs_axi1, axis=1),
                                np.expand_dims(obs_axi2, axis=1),
                                np.expand_dims(obs_axi3, axis=1),
                            )
                        )
                        hkl_com = hkl_vec @ hkl_mat
                        obs_com = obs_vec @ obs_mat
                        vec_sel = np.sum((hkl_com * obs_com), axis=1) > np.cos(
                            np.radians(np.float64(ang_tol))
                        )
                        obs_fou = obs_vec[vec_sel, :]
                        if n_foun < int(np.shape(obs_fou)[0]):
                            abc_dir_m = abc_dir @ hkl_mat
                            abc_dir_m = abc_dir_m @ obs_mat.T
                            shkl_vec1 = shkl.astype(np.float64)
                            shkl_vec1 = shkl_vec1 @ abc_dir
                            shkl_vec1 = shkl_vec1 / np.expand_dims(
                                np.sqrt(np.sum(np.square(shkl_vec1), axis=1)),
                                axis=1,
                            )
                            shkl_vec2 = shkl.astype(np.float64)
                            shkl_vec2 = shkl_vec2 @ abc_dir_m
                            shkl_vec2 = shkl_vec2 / np.expand_dims(
                                np.sqrt(np.sum(np.square(shkl_vec2), axis=1)),
                                axis=1,
                            )
                            ang = float(
                                np.min(np.sum((shkl_vec1 * shkl_vec2), axis=1))
                            )
                            ang = np.acos(ang) * 180.0 / np.pi
                            if ang < float(ang_lim):
                                n_foun = int(np.shape(obs_fou)[0])
                                nang = ang
                                abc_dir_n = abc_dir_m
    if n_foun > 0:
        print('Combinations of primary and secondary vectors:', n_psc)
        print('J. Appl. Phys., Vol. 86, No. 9, 1 November 1999, 5249-5255')
        print(' ')
        print('Indexed reflections:', n_foun)
        print('Angular shift, deg.:', round(nang, 2))
        abc_dir_n = np.reshape(abc_dir_n, 9)
        return abc_dir_n
