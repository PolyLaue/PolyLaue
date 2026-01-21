# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

import numpy as np

BASIC_STRUCTURE_TYPES = [
    '',
    'hcp',
    'Diamond',
    'fcc',
    'bcc',
]

ADVANCED_STRUCTURE_TYPES = [
    'Cmcm',
    'Laves',
]

VALID_STRUCTURE_TYPES = BASIC_STRUCTURE_TYPES + ADVANCED_STRUCTURE_TYPES


def burn(
    energy_highest: float,
    energy_lowest: float,
    structure_type: str,
    image_size_x: int,
    image_size_y: int,
    abc: np.ndarray,
    det_org: np.ndarray,
    beam_dir: np.ndarray,
    pix_dist: np.ndarray,
    res_lim: float = 0,
    nscan: int = -1,
    ang_shifts: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    if nscan > 1:
        if ang_shifts[(nscan - 2), 9] > 50:
            raise RuntimeError('No angular shift available')

        ten = np.reshape(ang_shifts[(nscan - 2), 0:9], (3, -1))

    if structure_type not in VALID_STRUCTURE_TYPES:
        msg = f'Unhandled structure type: {structure_type}'
        raise NotImplementedError(msg)

    abc_dir = np.reshape(abc, (3, -1))
    if nscan > 1:
        abc_dir = abc_dir @ ten
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
    d_min = 0.4246 * 29.2 / (2.0 * float(energy_highest) * np.sin(float(pix_dist[2])))
    print(' ')
    print(
        '... Detector opening resolution limit d/n >',
        round(d_min, 4),
        'Angstroms',
    )
    if d_min < float(res_lim):
        d_min = float(res_lim)
        print(' ')
        print('... Sample resolution limit d/n >', round(d_min, 4), 'Angstroms')
    print(' ')
    hkl_max_flo = np.sqrt(np.sum(np.square(abc_dir), axis=1)) / np.float64(d_min)
    hkl_max = hkl_max_flo.astype(np.int64) + np.int64(1)
    print('h,k,l maximal:', hkl_max)
    max_h = hkl_max[0]
    max_k = hkl_max[1]
    max_l = hkl_max[2]
    h1 = np.expand_dims(np.arange(np.int64(1), (max_h + 1), dtype=np.int64), axis=1)
    k1 = np.expand_dims(np.arange(-max_k, (max_k + 1), dtype=np.int64), axis=1)
    l1 = np.expand_dims(np.arange(-max_l, (max_l + 1), dtype=np.int64), axis=1)
    h0 = np.expand_dims(np.zeros(max_h, dtype=np.int64), axis=1)
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
    hkl1 = np.reshape(
        hkl,
        (
            (
                max_h
                * (max_k * np.int64(2) + np.int64(1))
                * (max_l * np.int64(2) + np.int64(1))
            ),
            3,
        ),
    )
    hkl = (
        np.expand_dims(k[max_k : (np.int64(2) * max_k + np.int64(1)), :], axis=1)
        + l[max_l : (np.int64(2) * max_l + np.int64(1)), :]
    )
    hkl2 = np.reshape(hkl, ((max_k + np.int64(1)) * (max_l + np.int64(1)), 3))
    hkl = (
        np.expand_dims(
            k[(max_k + np.int64(1)) : (np.int64(2) * max_k + np.int64(1)), :],
            axis=1,
        )
        + l[np.int64(0) : max_l, :]
    )
    hkl3 = np.reshape(hkl, ((max_k * max_l), 3))
    hkl = np.vstack((hkl1, hkl2, hkl3))
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
    hkl_tet = hkl_vec @ beam_dir
    vec_sel = np.nonzero(np.fabs(hkl_tet) < np.sin(pix_dist[2]))
    hkl_vec = hkl_vec[vec_sel[0], :]
    hkl_dis = hkl_dis[vec_sel[0]]
    hkl_tet = hkl_tet[vec_sel[0]]
    hkl = hkl[vec_sel[0], :]
    print(
        'Reciprocal vectors with theta <',
        round((float(pix_dist[2]) * 180.0 / np.pi), 2),
        'degrees:',
        np.shape(hkl)[0],
    )
    hkl_enr = 0.4246 * 29.2 / (np.float64(2) * np.fabs(hkl_tet) * hkl_dis)
    vec_sel = np.nonzero(hkl_enr < np.float64(energy_highest))
    hkl_vec = hkl_vec[vec_sel[0], :]
    hkl_dis = hkl_dis[vec_sel[0]]
    hkl_tet = hkl_tet[vec_sel[0]]
    hkl_enr = hkl_enr[vec_sel[0]]
    hkl = hkl[vec_sel[0], :]
    print(
        'Reciprocal vectors with energies <',
        round(float(energy_highest), 2),
        'keV:',
        np.shape(hkl)[0],
    )
    hkl_dif = beam_dir - hkl_vec * np.expand_dims(hkl_tet, axis=1) * np.float64(2)
    vec_sel = np.nonzero(hkl_dif[:, 2] > pix_dist[3])
    hkl_vec = hkl_vec[vec_sel[0], :]
    hkl_dif = hkl_dif[vec_sel[0], :]
    hkl_dis = hkl_dis[vec_sel[0]]
    hkl_tet = hkl_tet[vec_sel[0]]
    hkl_enr = hkl_enr[vec_sel[0]]
    hkl = hkl[vec_sel[0], :]
    print('Reflections towards area detector:', np.shape(hkl)[0])
    hkl_pos = (
        np.expand_dims((pix_dist[1] / hkl_dif[:, 2]), axis=1) * hkl_dif[:, 0:2]
    ) / pix_dist[0] + det_org
    vec_sel = np.nonzero(hkl_pos[:, 0] > np.float64(0))
    hkl_vec = hkl_vec[vec_sel[0], :]
    hkl_dif = hkl_dif[vec_sel[0], :]
    hkl_pos = hkl_pos[vec_sel[0], :]
    hkl_dis = hkl_dis[vec_sel[0]]
    hkl_tet = hkl_tet[vec_sel[0]]
    hkl_enr = hkl_enr[vec_sel[0]]
    hkl = hkl[vec_sel[0], :]
    vec_sel = np.nonzero(hkl_pos[:, 0] < np.float64(image_size_x))
    hkl_vec = hkl_vec[vec_sel[0], :]
    hkl_dif = hkl_dif[vec_sel[0], :]
    hkl_pos = hkl_pos[vec_sel[0], :]
    hkl_dis = hkl_dis[vec_sel[0]]
    hkl_tet = hkl_tet[vec_sel[0]]
    hkl_enr = hkl_enr[vec_sel[0]]
    hkl = hkl[vec_sel[0], :]
    vec_sel = np.nonzero(hkl_pos[:, 1] > np.float64(0))
    hkl_vec = hkl_vec[vec_sel[0], :]
    hkl_dif = hkl_dif[vec_sel[0], :]
    hkl_pos = hkl_pos[vec_sel[0], :]
    hkl_dis = hkl_dis[vec_sel[0]]
    hkl_tet = hkl_tet[vec_sel[0]]
    hkl_enr = hkl_enr[vec_sel[0]]
    hkl = hkl[vec_sel[0], :]
    vec_sel = np.nonzero(hkl_pos[:, 1] < np.float64(image_size_y))
    hkl_vec = hkl_vec[vec_sel[0], :]
    hkl_dif = hkl_dif[vec_sel[0], :]
    hkl_pos = hkl_pos[vec_sel[0], :]
    hkl_dis = hkl_dis[vec_sel[0]]
    hkl_tet = hkl_tet[vec_sel[0]]
    hkl_enr = hkl_enr[vec_sel[0]]
    hkl = hkl[vec_sel[0], :]
    vec_sel = np.nonzero(np.fabs(hkl_tet) > np.float64(15) * pix_dist[0] / pix_dist[1])
    hkl_vec = hkl_vec[vec_sel[0], :]
    hkl_dif = hkl_dif[vec_sel[0], :]
    hkl_pos = hkl_pos[vec_sel[0], :]
    hkl_dis = hkl_dis[vec_sel[0]]
    hkl_tet = hkl_tet[vec_sel[0]]
    hkl_enr = hkl_enr[vec_sel[0]]
    hkl = hkl[vec_sel[0], :]
    print('Reflections hitting area detector:', np.shape(hkl)[0])
    aaa = -np.sign(hkl_tet)
    hkl = hkl * np.expand_dims(aaa.astype(np.int64), axis=1)
    hkl_enr_dis = np.hstack(
        (np.expand_dims(hkl_enr, axis=1), np.expand_dims(hkl_dis, axis=1))
    )
    eded = []
    n1n2 = []
    sta_mul = [0, 0, 0, 0, 0]
    iii = 0
    for aaa in hkl_enr_dis:
        eee = aaa[0]
        ddd = aaa[1]
        nnn = 1
        chch = 1
        while eee < float(energy_highest):
            if eee > float(energy_lowest):
                if ddd > d_min:
                    if chch == 1:
                        nnn1 = nnn
                        chch = 0
                    nnn2 = nnn
                else:
                    break
            nnn = nnn + 1
            eee = aaa[0] * float(nnn)
            ddd = aaa[1] / float(nnn)
        if chch == 0:
            eded.append(iii)
            n1n2_loc = []
            n1n2_loc.append(nnn1)
            n1n2_loc.append(nnn2)
            n1n2.append(n1n2_loc)
            if (nnn2 - nnn1) < 5:
                sta_mul[(nnn2 - nnn1)] = sta_mul[(nnn2 - nnn1)] + 1
        iii = iii + 1
    vec_sel = np.array(eded, dtype=np.int64)
    hkl_nnn = np.array(n1n2, dtype=np.int64)
    hkl_vec = hkl_vec[vec_sel, :]
    hkl_dif = hkl_dif[vec_sel, :]
    hkl_pos = hkl_pos[vec_sel, :]
    hkl_dis = hkl_dis[vec_sel]
    hkl_tet = hkl_tet[vec_sel]
    hkl_enr = hkl_enr[vec_sel]
    hkl = hkl[vec_sel, :]

    if hkl.shape[0] == 0:
        print('No reflections predicted')
        return np.array([], dtype=int), np.array([])

    print(' ')
    print('... Predicted reflections:', np.shape(hkl)[0])
    print('Multiplicity distribution')
    print(
        '(International Tables for Crystallography (2006). '
        'Vol. C, Section 2.2.1, pp. 26–29.)'
    )
    print('n    %')
    sta_pre_tot = float(np.shape(hkl)[0])
    for i in range(5):
        print((i + 1), round((float(sta_mul[i]) * 100.0 / sta_pre_tot), 2), '%')
    if structure_type != '':
        if structure_type == 'Laves':
            ref_cond1 = range(0, (max_l + 1), 2)
            ref_cond2 = range(1, (max_h + max_k + 1), 3)
            ref_cond3 = range(2, (max_h + max_k + 1), 3)
        if structure_type == 'Cmcm':
            ref_cond1 = range(0, (max_h + max_k + 1), 2)
            ref_cond2 = range(0, (max_h + 1), 2)
            ref_cond3 = range(0, (max_l + 1), 2)
        if structure_type == 'bcc':
            ref_cond1 = range(0, (max_h + max_k + max_l + 1), 2)
        if structure_type == 'fcc':
            ref_cond1 = range(0, (max_h + max_k + 1), 2)
            ref_cond2 = range(0, (max_h + max_l + 1), 2)
            ref_cond3 = range(0, (max_l + max_k + 1), 2)
        if structure_type == 'hcp':
            ref_cond1 = range(0, (max_l + 1), 2)
            ref_cond2 = range(1, (max_h + max_k + 1), 3)
            ref_cond3 = range(2, (max_h + max_k + 1), 3)
        if structure_type == 'Diamond':
            ref_cond1 = range(0, (max_h + max_k + 1), 2)
            ref_cond2 = range(0, (max_h + max_k + 1), 4)
            ref_cond3 = range(1, (max_h + 1), 2)
            ref_cond4 = range(0, (max_h + max_k + max_l + 1), 4)
        hkl_ord = np.hstack((hkl, hkl_nnn))
        eded = []
        n1n2 = []
        iii = 0
        for aaa in hkl_ord:
            n1 = int(aaa[3])
            n2 = int(aaa[4])
            ch_ch_ch = 1
            for i in range(n1, (n2 + 1)):
                h = int(aaa[0]) * i
                k = int(aaa[1]) * i
                l = int(aaa[2]) * i  # noqa
                if structure_type == 'Laves':
                    ch_ch = -1
                    if abs(l) in ref_cond1:
                        ch_ch = ch_ch + 1
                    elif abs(h - k) in ref_cond2:
                        ch_ch = ch_ch + 1
                    elif abs(h - k) in ref_cond3:
                        ch_ch = ch_ch + 1
                    if ch_ch == 0:
                        if ch_ch_ch == 1:
                            ch_ch_ch = 0
                            nnn1 = i
                        nnn2 = i
                if structure_type == 'Cmcm':
                    ch_ch = -1
                    if abs(h + k) in ref_cond1:
                        ch_ch = ch_ch + 1
                    if ch_ch == 0:
                        if k == 0:
                            ch_ch = -2
                            if abs(h) in ref_cond2:
                                ch_ch = ch_ch + 1
                            if abs(l) in ref_cond2:
                                ch_ch = ch_ch + 1
                    if ch_ch == 0:
                        if ch_ch_ch == 1:
                            ch_ch_ch = 0
                            nnn1 = i
                        nnn2 = i
                if structure_type == 'bcc':
                    ch_ch = -1
                    if abs(h + k + l) in ref_cond1:
                        ch_ch = ch_ch + 1
                    if ch_ch == 0:
                        if ch_ch_ch == 1:
                            ch_ch_ch = 0
                            nnn1 = i
                        nnn2 = i
                if structure_type == 'fcc':
                    ch_ch = -3
                    if abs(h + k) in ref_cond1:
                        ch_ch = ch_ch + 1
                    if abs(h + l) in ref_cond2:
                        ch_ch = ch_ch + 1
                    if abs(l + k) in ref_cond3:
                        ch_ch = ch_ch + 1
                    if ch_ch == 0:
                        if ch_ch_ch == 1:
                            ch_ch_ch = 0
                            nnn1 = i
                        nnn2 = i
                if structure_type == 'hcp':
                    ch_ch = -1
                    if abs(l) in ref_cond1:
                        ch_ch = ch_ch + 1
                    elif abs(h - k) in ref_cond2:
                        ch_ch = ch_ch + 1
                    elif abs(h - k) in ref_cond3:
                        ch_ch = ch_ch + 1
                    if ch_ch == 0:
                        if ch_ch_ch == 1:
                            ch_ch_ch = 0
                            nnn1 = i
                        nnn2 = i
                if structure_type == 'Diamond':
                    ch_ch = -3
                    if abs(h + k) in ref_cond1:
                        ch_ch = ch_ch + 1
                    if abs(h + l) in ref_cond1:
                        ch_ch = ch_ch + 1
                    if abs(l + k) in ref_cond1:
                        ch_ch = ch_ch + 1
                    if ch_ch == 0:
                        if h == 0:
                            ch_ch = -1
                            if abs(k + l) in ref_cond2:
                                ch_ch = ch_ch + 1
                    if ch_ch == 0:
                        if k == 0:
                            ch_ch = -1
                            if abs(h + l) in ref_cond2:
                                ch_ch = ch_ch + 1
                    if ch_ch == 0:
                        if l == 0:
                            ch_ch = -1
                            if abs(k + h) in ref_cond2:
                                ch_ch = ch_ch + 1
                    if ch_ch == 0:
                        ch_ch = -1
                        if abs(h) in ref_cond3:
                            ch_ch = ch_ch + 1
                        elif abs(h + k + l) in ref_cond4:
                            ch_ch = ch_ch + 1
                    if ch_ch == 0:
                        ch_ch = -1
                        if abs(k) in ref_cond3:
                            ch_ch = ch_ch + 1
                        elif abs(h + k + l) in ref_cond4:
                            ch_ch = ch_ch + 1
                    if ch_ch == 0:
                        ch_ch = -1
                        if abs(l) in ref_cond3:
                            ch_ch = ch_ch + 1
                        elif abs(h + k + l) in ref_cond4:
                            ch_ch = ch_ch + 1
                    if ch_ch == 0:
                        if ch_ch_ch == 1:
                            ch_ch_ch = 0
                            nnn1 = i
                        nnn2 = i
            if ch_ch_ch == 0:
                eded.append(iii)
                n1n2_loc = []
                n1n2_loc.append(nnn1)
                n1n2_loc.append(nnn2)
                n1n2.append(n1n2_loc)
            iii = iii + 1
        vec_sel = np.array(eded, dtype=np.int64)
        hkl_nnn = np.array(n1n2, dtype=np.int64)
        hkl_vec = hkl_vec[vec_sel, :]
        hkl_dif = hkl_dif[vec_sel, :]
        hkl_pos = hkl_pos[vec_sel, :]
        hkl_dis = hkl_dis[vec_sel]
        hkl_tet = hkl_tet[vec_sel]
        hkl_enr = hkl_enr[vec_sel]
        hkl = hkl[vec_sel, :]
        print('')
        print(
            '... Satisfying reflection conditions for',
            structure_type,
            ':',
            np.shape(hkl)[0],
        )
    hkl_n1 = hkl_nnn[:, 0]
    hkl = hkl * np.expand_dims(hkl_n1, axis=1)
    hkl_enr = hkl_enr * hkl_n1.astype(np.float64)
    hkl_dis = hkl_dis / hkl_n1.astype(np.float64)
    pred_list1 = np.hstack((hkl, hkl_nnn))
    pred_list2 = np.hstack(
        (
            hkl_pos,
            np.expand_dims(hkl_enr, axis=1),
            np.expand_dims(hkl_dis, axis=1),
        )
    )
    return pred_list1, pred_list2
