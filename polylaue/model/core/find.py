# Copyright © 2025, UChicago Argonne, LLC. See "LICENSE" for full details.

import numpy as np


def find(
    obs_xy: np.ndarray,
    energy_highest: float,
    cell_parameters: list[float],
    det_org: np.ndarray,
    beam_dir: np.ndarray,
    pix_dist: np.ndarray,
    ang_tol: float = 0.07,
    res_lim: float = 0.4,
    ref_thr: float = 3,
) -> np.ndarray | None:

    abc = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    a = float(cell_parameters[0])
    b = float(cell_parameters[1])
    c = float(cell_parameters[2])
    alpha = float(cell_parameters[3])
    betta = float(cell_parameters[4])
    gamma = float(cell_parameters[5])
    bz = b * np.cos(alpha * np.pi / float(180.0))
    by = b * np.sin(alpha * np.pi / float(180.0))
    az = a * np.cos(betta * np.pi / float(180.0))
    ay = (a * b * np.cos(gamma * np.pi / float(180.0)) - az * bz) / by
    abc[0] = np.sqrt(a * a - az * az - ay * ay)
    abc[1] = ay
    abc[2] = az
    abc[3] = float(0.0)
    abc[4] = by
    abc[5] = bz
    abc[6] = float(0.0)
    abc[7] = float(0.0)
    abc[8] = c
    abc_dir = np.reshape(np.array(abc, dtype=np.float64), (3, -1))
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
    num_ore = int(np.shape(obs_vec)[0])
    print(
        '... Observed reflections:',
        num_ore,
        '  !!!Points from MORE than one zone line MUST be included!!!',
    )
    s1 = np.shape(hkl)[0]
    t1 = np.zeros((s1, 3), dtype=np.float64)
    obs_pri = obs_vec[0]
    hkl_prii = np.expand_dims(hkl_vec, axis=1) + t1
    hkl_prii = np.reshape(hkl_prii, ((s1 * s1), 3))
    hkl_seci = np.expand_dims(t1, axis=1) + hkl_vec
    hkl_seci = np.reshape(hkl_seci, ((s1 * s1), 3))
    ct2 = np.sum((hkl_prii * hkl_seci), axis=1)
    vec_sel = np.nonzero(np.absolute(ct2) < np.cos(np.radians(np.float64(10))))
    hkl_prii = hkl_prii[vec_sel[0], :]
    hkl_seci = hkl_seci[vec_sel[0], :]
    ct2 = np.sum((hkl_prii * hkl_seci), axis=1)
    ct2 = np.degrees(np.arccos(ct2))
    for j in range(len(obs_xy)):
        s2 = np.int64(j)
        obs_sec = obs_vec[s2]
        ct1 = np.sum((obs_pri * obs_sec))
        if float(ct1) < float(np.cos(np.radians(np.float64(10)))):
            print(' ')
            print('Secondary reflection:', j + 1)
            print(
                'Primary - secondary angle, deg:',
                round(float(np.degrees(np.arccos(ct1))), 2),
            )
            ct1 = np.degrees(np.arccos(ct1))
            vec_sel = np.nonzero(np.absolute(ct1 - ct2) < np.float64(ang_tol))
            hkl_pri = hkl_prii[vec_sel[0], :]
            hkl_sec = hkl_seci[vec_sel[0], :]
            print(
                'Combinations of primary and secondary vectors:',
                np.shape(hkl_sec)[0],
            )
            print('J. Appl. Phys., Vol. 86, No. 9, 1 November 1999, 5249-5255')
            hkl_axi1 = hkl_pri
            obs_axi1 = obs_pri
            hkl_axi2 = np.cross(hkl_axi1, hkl_sec)
            hkl_axi2 = hkl_axi2 / np.expand_dims(
                np.sqrt(np.sum(np.square(hkl_axi2), axis=1)), axis=1
            )
            obs_axi2 = np.cross(obs_axi1, obs_sec)
            obs_axi2 = obs_axi2 / np.sqrt(np.sum(np.square(obs_axi2)))
            hkl_axi3 = np.cross(hkl_axi1, hkl_axi2)
            obs_axi3 = np.cross(obs_axi1, obs_axi2)
            hkl_x = np.sum(
                (np.expand_dims(hkl_axi1, axis=1) * hkl_vec), axis=2
            )
            hkl_y = np.sum(
                (np.expand_dims(hkl_axi2, axis=1) * hkl_vec), axis=2
            )
            hkl_z = np.sum(
                (np.expand_dims(hkl_axi3, axis=1) * hkl_vec), axis=2
            )
            obs_x = np.sum((obs_axi1 * obs_vec), axis=1)
            obs_y = np.sum((obs_axi2 * obs_vec), axis=1)
            obs_z = np.sum((obs_axi3 * obs_vec), axis=1)
            hkl_x = np.expand_dims(hkl_x, axis=2)
            hkl_y = np.expand_dims(hkl_y, axis=2)
            hkl_z = np.expand_dims(hkl_z, axis=2)
            vec_sel = (hkl_x * obs_x + hkl_y * obs_y + hkl_z * obs_z) > np.cos(
                np.radians(np.float64(ang_tol))
            )
            com_sel = np.zeros(np.shape(vec_sel), dtype=np.int64)
            com_sel[vec_sel] = np.int64(1)
            com_sel = np.sum(com_sel, axis=2)
            com_sel = np.sum(com_sel, axis=1)
            if int(np.max(com_sel)) > int(ref_thr):
                vec_sel = np.nonzero(com_sel > np.int64(ref_thr))
                com_sel = com_sel[vec_sel[0]]
                hkl_axi1 = hkl_axi1[vec_sel[0], :]
                hkl_axi2 = hkl_axi2[vec_sel[0], :]
                hkl_axi3 = hkl_axi3[vec_sel[0], :]
                n_foun = 0
                n_mult = 0
                n_hist = int(np.shape(hkl_axi1)[0])
                for i in range(n_hist):
                    if n_foun < int(com_sel[np.int64(i)]):
                        n_mult = 0
                        hkl_axs1 = hkl_axi1[np.int64(i), :]
                        hkl_axs2 = hkl_axi2[np.int64(i), :]
                        hkl_axs3 = hkl_axi3[np.int64(i), :]
                        obs_axs1 = obs_axi1
                        obs_axs2 = obs_axi2
                        obs_axs3 = obs_axi3
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
                        abc_dir_n = abc_dir @ hkl_mat
                        abc_dir_n = abc_dir_n @ obs_mat.T
                        n_foun = int(com_sel[np.int64(i)])
                    if n_foun == int(com_sel[np.int64(i)]):
                        n_mult = n_mult + 1
                print(' ')
                print('Indexed reflections:', n_foun)
                print(
                    '...This number MUST be substantially higher than the '
                    'random solutions limit of',
                    ref_thr,
                )
                print(' ')
                print('Multiplicity:', n_mult)
                print(' ')
                print('Multiplicity MUST match to one of the following:')
                print('...Cubic: 24')
                print('...Hexagonal/trigonal: 12')
                print('...Rhombohedral: 6')
                print('...Tetragonal: 8')
                print('...Orthorhombic: 4')
                print('...Monoclinic: 2')
                print('...Triclinic: 1')
                print(' ')
                print('Solutions in total:', n_hist)
                print(
                    '...This number MUST be the same as multiplicity. '
                    'Try higher ref_thr otherwise.'
                )
                abc_dir_n = np.reshape(abc_dir_n, 9)
                return abc_dir_n


def find_py(
    obs_xy: np.ndarray,
    energy_highest: float,
    cell_parameters: list[float],
    det_org: np.ndarray,
    beam_dir: np.ndarray,
    pix_dist: np.ndarray,
    ang_tol: float = 0.07,
    res_lim: float = 0.4,
    ref_thr: float = 3,
) -> np.ndarray | None:
    """This version of find() takes up substantially less RAM, but
    may run slower"""

    abc = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    a = float(cell_parameters[0])
    b = float(cell_parameters[1])
    c = float(cell_parameters[2])
    alpha = float(cell_parameters[3])
    betta = float(cell_parameters[4])
    gamma = float(cell_parameters[5])
    bz = b * np.cos(alpha * np.pi / float(180.0))
    by = b * np.sin(alpha * np.pi / float(180.0))
    az = a * np.cos(betta * np.pi / float(180.0))
    ay = (a * b * np.cos(gamma * np.pi / float(180.0)) - az * bz) / by
    abc[0] = np.sqrt(a * a - az * az - ay * ay)
    abc[1] = ay
    abc[2] = az
    abc[3] = float(0.0)
    abc[4] = by
    abc[5] = bz
    abc[6] = float(0.0)
    abc[7] = float(0.0)
    abc[8] = c
    abc_dir = np.reshape(np.array(abc, dtype=np.float64), (3, -1))
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
    num_ore = int(np.shape(obs_vec)[0])
    print(
        '... Observed reflections:',
        num_ore,
        '  !!!Points from MORE than one zone line MUST be included!!!',
    )
    print(' ')
    s1 = int(np.shape(hkl)[0])
    for k in range(len(obs_xy)):
        n_mult = 0
        n_hist = 0
        n_foun = 0
        n_psc = 0
        s2 = k
        obs_pri = obs_vec[np.int64(0), :]
        obs_sec = obs_vec[np.int64(s2), :]
        t2 = np.sum(obs_pri * obs_sec)
        if float(np.absolute(t2)) < np.cos(float(10.0) * np.pi / float(180.0)):
            t2 = np.degrees(np.arccos(t2))
            print(' ')
            print('Secondary reflection:', k + 1)
            print('Primary - secondary angle, deg:', round(float(t2), 2))
            for i in range(s1):
                for j in range(s1):
                    hkl_pri = hkl_vec[np.int64(i), :]
                    hkl_sec = hkl_vec[np.int64(j), :]
                    t1 = np.sum(hkl_pri * hkl_sec)
                    if float(np.absolute(t1)) < np.cos(
                        float(10.0) * np.pi / float(180.0)
                    ):
                        t1 = np.degrees(np.arccos(t1))
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
                            vec_sel = np.sum(
                                (np.expand_dims(obs_com, axis=1) * hkl_com),
                                axis=2,
                            ) > np.cos(np.radians(np.float64(ang_tol)))
                            com_sel = np.zeros(
                                np.shape(vec_sel), dtype=np.int64
                            )
                            com_sel[vec_sel] = np.int64(1)
                            obs_fou = int(np.sum(com_sel))
                            if ref_thr < obs_fou:
                                n_hist = n_hist + 1
                            if n_foun < obs_fou:
                                n_mult = 0
                                abc_dir_n = abc_dir @ hkl_mat
                                abc_dir_n = abc_dir_n @ obs_mat.T
                                n_foun = obs_fou
                            if n_foun == obs_fou:
                                n_mult = n_mult + 1
            if n_foun > ref_thr:
                print('Combinations of primary and secondary vectors:', n_psc)
                print(
                    'J. Appl. Phys., Vol. 86, No. 9, '
                    '1 November 1999, 5249-5255'
                )
                print(' ')
                print('Indexed reflections:', n_foun)
                print(
                    '...This number MUST be substantially higher than the '
                    'random solutions limit of',
                    ref_thr,
                )
                print(' ')
                print('Multiplicity:', n_mult)
                print(' ')
                print('Multiplicity MUST match to one of the following:')
                print('...Cubic: 24')
                print('...Hexagonal/trigonal: 12')
                print('...Rhombohedral: 6')
                print('...Tetragonal: 8')
                print('...Orthorhombic: 4')
                print('...Monoclinic: 2')
                print('...Triclinic: 1')
                print(' ')
                print('Solutions in total:', n_hist)
                print(
                    '...This number MUST be the same as multiplicity. '
                    'Try higher ref_thr otherwise.'
                )
                abc_dir_n = np.reshape(abc_dir_n, 9)
                return abc_dir_n
