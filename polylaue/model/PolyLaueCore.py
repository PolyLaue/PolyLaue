# -*- coding: utf-8 -*-
"""
Created on Fri Aug  9 21:28:33 2024

@author: dpopov
"""

# Copyright © 2024, UChicago Argonne, LLC
# All Rights Reserved
# Software Name: Extended version of software PolyLaue
# By: Argonne National Laboratory, KITWARE, INC.
# BSD OPEN SOURCE LICENSE
# The full text of the license is available in file LICENSE

import numpy as np

ImageSizeX=2048 # X-ray image size along X, pixels
ImageSizeY=2048 # X-ray image size along Y, pixels

WhiteBeamShift=0.01 # Shift of white beam from mono beam
# at the sample position along HPCAT Y+, mm

EnergyHighest=70 # Highest limit of X-ray energy, keV
EnergyLowest=5 # Lowest limit of X-ray energy, keV

#StructureType='hcp' # Defines reflection conditions, if any
StructureType='' # Defines reflection conditions, if any
#StructureType='Diamond' # Defines reflection conditions, if any



def save_shift(n):
    a=np.loadtxt('abc', dtype=np.float64)
    ar=np.load('abc_matrix.npy')
    sh_tab=np.load('ang_shifts.npy')
    a1=ar[6:9]/np.sqrt(np.sum(np.square(ar[6:9])))
    a2=np.cross(ar[3:6], ar[6:9])
    a2=a2/np.sqrt(np.sum(np.square(a2)))
    a3=np.cross(a1, a2)
    unmov=np.vstack((a1,a2,a3))
    a1=a[6:9]/np.sqrt(np.sum(np.square(a[6:9])))
    a2=np.cross(a[3:6], a[6:9])
    a2=a2/np.sqrt(np.sum(np.square(a2)))
    a3=np.cross(a1, a2)
    mov=np.hstack((np.expand_dims(a1, axis=1), np.expand_dims(a2, axis=1), np.expand_dims(a3, axis=1)))
    ten=mov @ unmov
    sh_tab[(n-2),0:9]=np.reshape(ten, 9)
    sh_tab[(n-2),9]=np.float64(0)
    np.save('ang_shifts.npy', sh_tab)
    print(sh_tab)



def shifts_table(n):
    sh_tab=np.zeros(((n-1),10), dtype=np.float64)
    sh_tab[:,9]=np.float64(100)
    print(sh_tab)
    np.save('ang_shifts.npy', sh_tab)


def track1(ang_tol=0.15, ang_lim=29, res_lim=0.5, ref_thr=5):
    import math
    global EnergyHighest, EnergyLowest, StructureType, ImageSizeX, ImageSizeY
    with np.load('geosetup.npz') as geo_arr:
        det_org=geo_arr['iitt1']
        beam_dir=geo_arr['iitt2']
        pix_dist=geo_arr['iitt3']
    a=np.loadtxt('abc', dtype=np.float64)
    np.save('abc_matrix.npy', a)
    abc=np.load('abc_matrix.npy')
    abc_dir=np.reshape(abc, (3,-1))
    abc_vol=np.cross(abc_dir[2,:], abc_dir[0,:]) @ abc_dir[1,:]
    abc_rec=np.vstack((np.cross(abc_dir[1,:], abc_dir[2,:]), np.cross(abc_dir[2,:], abc_dir[0,:]), np.cross(abc_dir[0,:], abc_dir[1,:])))/abc_vol
    abc_len=np.sqrt(np.sum(np.square(abc_dir), axis=1))
    print('a=, b=, c=:', abc_len)
    abc_nor=abc_dir/np.expand_dims(abc_len, axis=1)
    abc_ang=np.array([0,0,0], dtype=np.float64)
    abc_ang[0]=abc_nor[1] @ abc_nor[2]
    abc_ang[1]=abc_nor[2] @ abc_nor[0]
    abc_ang[2]=abc_nor[0] @ abc_nor[1]
    abc_ang=np.degrees(np.arccos(abc_ang))
    print('alpha=, beta=, gamma=:', abc_ang)
    print('Unit cell volume, Angstroms**3:', round(float(abc_vol), 2))
    d_min=0.4246*29.2/(2.0*float(EnergyHighest)*math.sin(float(pix_dist[2])))
    print(' ')
    print('... Detector opening resolution limit d/n >', round(d_min, 4), 'Angstroms')
    if d_min < float(res_lim):
        d_min=float(res_lim)
        print(' ')
        print('... Sample resolution limit d/n >', round(d_min, 4), 'Angstroms')
    print(' ')
    hkl_max_flo=np.sqrt(np.sum(np.square(abc_dir), axis=1))/np.float64(d_min)
    hkl_max=hkl_max_flo.astype(np.int64)+np.int64(1)
    print('h,k,l maximal:', hkl_max)
    max_h=hkl_max[0]
    max_k=hkl_max[1]
    max_l=hkl_max[2]
    h1=np.expand_dims(np.arange(-max_h, (max_h+1), dtype=np.int64), axis=1)
    k1=np.expand_dims(np.arange(-max_k, (max_k+1), dtype=np.int64), axis=1)
    l1=np.expand_dims(np.arange(-max_l, (max_l+1), dtype=np.int64), axis=1)
    h0=np.expand_dims(np.zeros((max_h*np.int64(2)+np.int64(1)), dtype=np.int64), axis=1)
    k0=np.expand_dims(np.zeros((max_k*np.int64(2)+np.int64(1)), dtype=np.int64), axis=1)
    l0=np.expand_dims(np.zeros((max_l*np.int64(2)+np.int64(1)), dtype=np.int64), axis=1)
    h=np.hstack((h1,h0,h0))
    k=np.hstack((k0,k1,k0))
    l=np.hstack((l0,l0,l1))
    hkl=np.expand_dims((np.expand_dims(h, axis=1)+k), axis=2)+l
    hkl=np.reshape(hkl, (((max_h*np.int64(2)+np.int64(1))*(max_k*np.int64(2)+np.int64(1))*(max_l*np.int64(2)+np.int64(1))), 3))
    vec_sel=np.sum(np.absolute(hkl), axis=1) != 0
    hkl=hkl[vec_sel,:]
    print('Total number of indices:', np.shape(hkl)[0])
    ind_tot=float(np.shape(hkl)[0])
    vec_sel=(np.gcd.reduce(hkl, axis=1)==1)
    hkl=hkl[vec_sel,:]
    ind_rpi=float(np.shape(hkl)[0])
    print('Relatively prime integers:', np.shape(hkl)[0], '(', round((ind_rpi*100.0/ind_tot),2), '% )')
    hkl_vec=hkl.astype(np.float64)
    hkl_vec=hkl_vec @ abc_rec
    hkl_dis=np.float64(1)/np.sqrt(np.sum(np.square(hkl_vec), axis=1))
    vec_sel=np.nonzero(hkl_dis > np.float64(d_min))
    hkl_vec=hkl_vec[vec_sel[0],:]
    hkl_dis=hkl_dis[vec_sel[0]]
    hkl_vec=hkl_vec*np.expand_dims(hkl_dis, axis=1)
    hkl=hkl[vec_sel[0],:]
    print(' ')
    print('... n=1')
    print('Sets of crystallographic planes with d >', round(d_min, 4), 'Angstroms:', np.shape(hkl)[0])
    obs_xy=np.loadtxt('refinement.xy', dtype=np.float64)
    dt=[]
    for i in obs_xy:
        dt.append(float(pix_dist[1]))
    obs_vec=np.hstack((((obs_xy-det_org)*pix_dist[0]), np.expand_dims(np.array(dt, dtype=np.float64), axis=1)))
    obs_vec=obs_vec/np.expand_dims(np.sqrt(np.sum(np.square(obs_vec), axis=1)), axis=1)
    obs_vec=obs_vec-beam_dir
    obs_vec=obs_vec/np.expand_dims(np.sqrt(np.sum(np.square(obs_vec), axis=1)), axis=1)
    print(' ')
    print('... Observed reflections:', np.shape(obs_vec)[0])
    s1=np.shape(hkl)[0]
    s2=np.shape(obs_vec)[0]
    t1=np.zeros((s1, 3), dtype=np.float64)
    t2=np.zeros((s2, 3), dtype=np.float64)
    obs_vec=np.expand_dims(obs_vec, axis=1)+t1
    obs_vec=np.reshape(obs_vec, ((s1*s2), 3))
    hkl_vec=np.expand_dims(t2, axis=1)+hkl_vec
    hkl_vec=np.reshape(hkl_vec, ((s1*s2), 3))
    vec_sel=np.nonzero(np.sum((obs_vec*hkl_vec), axis=1) > np.cos(np.radians(np.float64(ang_lim))))
    hkl_vec=hkl_vec[vec_sel[0],:]
    obs_vec=obs_vec[vec_sel[0],:]
    print('Possible indices in total:', np.shape(hkl_vec)[0])
    mm=np.int64(10)
    sh1=np.expand_dims(np.arange(-mm, (mm+1), dtype=np.int64), axis=1)
    sk1=np.expand_dims(np.arange(-mm, (mm+1), dtype=np.int64), axis=1)
    sl1=np.expand_dims(np.arange(-mm, (mm+1), dtype=np.int64), axis=1)
    sh0=np.expand_dims(np.zeros((mm*np.int64(2)+np.int64(1)), dtype=np.int64), axis=1)
    sk0=np.expand_dims(np.zeros((mm*np.int64(2)+np.int64(1)), dtype=np.int64), axis=1)
    sl0=np.expand_dims(np.zeros((mm*np.int64(2)+np.int64(1)), dtype=np.int64), axis=1)
    sh=np.hstack((sh1,sh0,sh0))
    sk=np.hstack((sk0,sk1,sk0))
    sl=np.hstack((sl0,sl0,sl1))
    shkl=np.expand_dims((np.expand_dims(sh, axis=1)+sk), axis=2)+sl
    shkl=np.reshape(shkl, (((mm*np.int64(2)+np.int64(1))*(mm*np.int64(2)+np.int64(1))*(mm*np.int64(2)+np.int64(1))), 3))
    vec_sel=np.sum(np.absolute(shkl), axis=1) != 0
    shkl=shkl[vec_sel,:]
    s1=np.shape(hkl_vec)[0]
    t1=np.zeros((s1, 3), dtype=np.float64)
    obs_pri=np.expand_dims(obs_vec, axis=1)+t1
    obs_pri=np.reshape(obs_pri, ((s1*s1), 3))
    obs_sec=np.expand_dims(t1, axis=1)+obs_vec
    obs_sec=np.reshape(obs_sec, ((s1*s1), 3))
    hkl_pri=np.expand_dims(hkl_vec, axis=1)+t1
    hkl_pri=np.reshape(hkl_pri, ((s1*s1), 3))
    hkl_sec=np.expand_dims(t1, axis=1)+hkl_vec
    hkl_sec=np.reshape(hkl_sec, ((s1*s1), 3))
    t1=np.zeros((s1, 1), dtype=np.int64)
    nnn=np.expand_dims(np.arange(s1, dtype=np.int64), axis=1)
    nnn_pri=np.expand_dims(nnn, axis=1)+t1
    nnn_pri=np.reshape(nnn_pri, (s1*s1))
    nnn_sec=np.expand_dims(t1, axis=1)+nnn
    nnn_sec=np.reshape(nnn_sec, (s1*s1))
    vec_sel=np.nonzero((nnn_sec-nnn_pri) > np.int64(0))
    obs_pri=obs_pri[vec_sel[0],:]
    obs_sec=obs_sec[vec_sel[0],:]
    hkl_pri=hkl_pri[vec_sel[0],:]
    hkl_sec=hkl_sec[vec_sel[0],:]
    t1=np.sum((hkl_pri*hkl_sec), axis=1)
    vec_sel=np.nonzero(np.absolute(t1) < np.cos(np.radians(np.float64(20))))
    obs_pri=obs_pri[vec_sel[0],:]
    obs_sec=obs_sec[vec_sel[0],:]
    hkl_pri=hkl_pri[vec_sel[0],:]
    hkl_sec=hkl_sec[vec_sel[0],:]
    t2=np.sum((obs_pri*obs_sec), axis=1)
    vec_sel=np.nonzero(np.absolute(t2) < np.cos(np.radians(np.float64(20))))
    obs_pri=obs_pri[vec_sel[0],:]
    obs_sec=obs_sec[vec_sel[0],:]
    hkl_pri=hkl_pri[vec_sel[0],:]
    hkl_sec=hkl_sec[vec_sel[0],:]
    t1=np.sum((hkl_pri*hkl_sec), axis=1)
    t2=np.sum((obs_pri*obs_sec), axis=1)
    t1=np.degrees(np.arccos(t1))
    t2=np.degrees(np.arccos(t2))
    vec_sel=np.nonzero(np.absolute(t1-t2) < np.float64(1))
    obs_pri=obs_pri[vec_sel[0],:]
    obs_sec=obs_sec[vec_sel[0],:]
    hkl_pri=hkl_pri[vec_sel[0],:]
    hkl_sec=hkl_sec[vec_sel[0],:]
    print('Combinations of primary and secondary vectors:', np.shape(hkl_sec)[0])
    hkl_axi1=hkl_pri
    obs_axi1=obs_pri
    hkl_axi2=np.cross(hkl_axi1, hkl_sec)
    hkl_axi2=hkl_axi2/np.expand_dims(np.sqrt(np.sum(np.square(hkl_axi2), axis=1)), axis=1)
    obs_axi2=np.cross(obs_axi1, obs_sec)
    obs_axi2=obs_axi2/np.expand_dims(np.sqrt(np.sum(np.square(obs_axi2), axis=1)), axis=1)
    hkl_axi3=np.cross(hkl_axi1, hkl_axi2)
    obs_axi3=np.cross(obs_axi1, obs_axi2)
    hkl_x=np.sum((np.expand_dims(hkl_axi1, axis=1)*hkl_vec), axis=2)
    hkl_y=np.sum((np.expand_dims(hkl_axi2, axis=1)*hkl_vec), axis=2)
    hkl_z=np.sum((np.expand_dims(hkl_axi3, axis=1)*hkl_vec), axis=2)
    obs_x=np.sum((np.expand_dims(obs_axi1, axis=1)*obs_vec), axis=2)
    obs_y=np.sum((np.expand_dims(obs_axi2, axis=1)*obs_vec), axis=2)
    obs_z=np.sum((np.expand_dims(obs_axi3, axis=1)*obs_vec), axis=2)
    vec_sel=((hkl_x*obs_x+hkl_y*obs_y+hkl_z*obs_z) > np.cos(np.radians(np.float64(ang_tol))))
    com_sel=np.zeros(np.shape(obs_z), dtype=np.int64)
    com_sel[vec_sel]=np.int64(1)
    com_sel=np.sum(com_sel, axis=1)
    vec_sel=np.nonzero(com_sel > np.int64(ref_thr))
    com_sel=com_sel[vec_sel[0]]
    hkl_axi1=hkl_axi1[vec_sel[0],:]
    hkl_axi2=hkl_axi2[vec_sel[0],:]
    hkl_axi3=hkl_axi3[vec_sel[0],:]
    obs_axi1=obs_axi1[vec_sel[0],:]
    obs_axi2=obs_axi2[vec_sel[0],:]
    obs_axi3=obs_axi3[vec_sel[0],:]
    n_foun=0
    s1=int(np.shape(obs_axi1)[0])
    for i in range(s1):
        if n_foun < int(com_sel[np.int64(i)]):
            hkl_axs1=hkl_axi1[np.int64(i),:]
            hkl_axs2=hkl_axi2[np.int64(i),:]
            hkl_axs3=hkl_axi3[np.int64(i),:]
            obs_axs1=obs_axi1[np.int64(i),:]
            obs_axs2=obs_axi2[np.int64(i),:]
            obs_axs3=obs_axi3[np.int64(i),:]
            hkl_mat=np.hstack((np.expand_dims(hkl_axs1, axis=1), np.expand_dims(hkl_axs2, axis=1), np.expand_dims(hkl_axs3, axis=1)))
            obs_mat=np.hstack((np.expand_dims(obs_axs1, axis=1), np.expand_dims(obs_axs2, axis=1), np.expand_dims(obs_axs3, axis=1)))
            abc_dir_m=abc_dir @ hkl_mat
            abc_dir_m=abc_dir_m @ obs_mat.T
            shkl_vec1=shkl.astype(np.float64)
            shkl_vec1=shkl_vec1 @ abc_dir
            shkl_vec1=shkl_vec1/np.expand_dims(np.sqrt(np.sum(np.square(shkl_vec1), axis=1)), axis=1)
            shkl_vec2=shkl.astype(np.float64)
            shkl_vec2=shkl_vec2 @ abc_dir_m
            shkl_vec2=shkl_vec2/np.expand_dims(np.sqrt(np.sum(np.square(shkl_vec2), axis=1)), axis=1)
            ang=float(np.min(np.sum((shkl_vec1*shkl_vec2), axis=1)))
            ang=math.acos(ang)*180.0/math.pi
            if ang < float(ang_lim):
                nang=ang
                abc_dir_n=abc_dir_m
                n_foun=int(com_sel[np.int64(i)])
    print('Indexed reflections:', n_foun)
    print('Angular shift, deg.:', round(nang,2))
    abc_dir_n=np.reshape(abc_dir_n, 9)
    np.save('abc_matrix.npy', abc_dir_n)


def track(ang_tol=0.15, ang_lim=29, res_lim=0.5):
    import math
    global EnergyHighest, EnergyLowest, StructureType, ImageSizeX, ImageSizeY
    with np.load('geosetup.npz') as geo_arr:
        det_org=geo_arr['iitt1']
        beam_dir=geo_arr['iitt2']
        pix_dist=geo_arr['iitt3']
    a=np.loadtxt('abc', dtype=np.float64)
    np.save('abc_matrix.npy', a)
    abc=np.load('abc_matrix.npy')
    abc_dir=np.reshape(abc, (3,-1))
    abc_vol=np.cross(abc_dir[2,:], abc_dir[0,:]) @ abc_dir[1,:]
    abc_rec=np.vstack((np.cross(abc_dir[1,:], abc_dir[2,:]), np.cross(abc_dir[2,:], abc_dir[0,:]), np.cross(abc_dir[0,:], abc_dir[1,:])))/abc_vol
    abc_len=np.sqrt(np.sum(np.square(abc_dir), axis=1))
    print('a=, b=, c=:', abc_len)
    abc_nor=abc_dir/np.expand_dims(abc_len, axis=1)
    abc_ang=np.array([0,0,0], dtype=np.float64)
    abc_ang[0]=abc_nor[1] @ abc_nor[2]
    abc_ang[1]=abc_nor[2] @ abc_nor[0]
    abc_ang[2]=abc_nor[0] @ abc_nor[1]
    abc_ang=np.degrees(np.arccos(abc_ang))
    print('alpha=, beta=, gamma=:', abc_ang)
    print('Unit cell volume, Angstroms**3:', round(float(abc_vol), 2))
    d_min=0.4246*29.2/(2.0*float(EnergyHighest)*math.sin(float(pix_dist[2])))
    print(' ')
    print('... Detector opening resolution limit d/n >', round(d_min, 4), 'Angstroms')
    if d_min < float(res_lim):
        d_min=float(res_lim)
        print(' ')
        print('... Sample resolution limit d/n >', round(d_min, 4), 'Angstroms')
    print(' ')
    hkl_max_flo=np.sqrt(np.sum(np.square(abc_dir), axis=1))/np.float64(d_min)
    hkl_max=hkl_max_flo.astype(np.int64)+np.int64(1)
    print('h,k,l maximal:', hkl_max)
    max_h=hkl_max[0]
    max_k=hkl_max[1]
    max_l=hkl_max[2]
    h1=np.expand_dims(np.arange(-max_h, (max_h+1), dtype=np.int64), axis=1)
    k1=np.expand_dims(np.arange(-max_k, (max_k+1), dtype=np.int64), axis=1)
    l1=np.expand_dims(np.arange(-max_l, (max_l+1), dtype=np.int64), axis=1)
    h0=np.expand_dims(np.zeros((max_h*np.int64(2)+np.int64(1)), dtype=np.int64), axis=1)
    k0=np.expand_dims(np.zeros((max_k*np.int64(2)+np.int64(1)), dtype=np.int64), axis=1)
    l0=np.expand_dims(np.zeros((max_l*np.int64(2)+np.int64(1)), dtype=np.int64), axis=1)
    h=np.hstack((h1,h0,h0))
    k=np.hstack((k0,k1,k0))
    l=np.hstack((l0,l0,l1))
    hkl=np.expand_dims((np.expand_dims(h, axis=1)+k), axis=2)+l
    hkl=np.reshape(hkl, (((max_h*np.int64(2)+np.int64(1))*(max_k*np.int64(2)+np.int64(1))*(max_l*np.int64(2)+np.int64(1))), 3))
    vec_sel=np.sum(np.absolute(hkl), axis=1) != 0
    hkl=hkl[vec_sel,:]
    print('Total number of indices:', np.shape(hkl)[0])
    ind_tot=float(np.shape(hkl)[0])
    vec_sel=(np.gcd.reduce(hkl, axis=1)==1)
    hkl=hkl[vec_sel,:]
    ind_rpi=float(np.shape(hkl)[0])
    print('Relatively prime integers:', np.shape(hkl)[0], '(', round((ind_rpi*100.0/ind_tot),2), '% )')
    hkl_vec=hkl.astype(np.float64)
    hkl_vec=hkl_vec @ abc_rec
    hkl_dis=np.float64(1)/np.sqrt(np.sum(np.square(hkl_vec), axis=1))
    vec_sel=np.nonzero(hkl_dis > np.float64(d_min))
    hkl_vec=hkl_vec[vec_sel[0],:]
    hkl_dis=hkl_dis[vec_sel[0]]
    hkl_vec=hkl_vec*np.expand_dims(hkl_dis, axis=1)
    hkl=hkl[vec_sel[0],:]
    print(' ')
    print('... n=1')
    print('Sets of crystallographic planes with d >', round(d_min, 4), 'Angstroms:', np.shape(hkl)[0])
    obs_xy=np.loadtxt('refinement.xy', dtype=np.float64)
    dt=[]
    for i in obs_xy:
        dt.append(float(pix_dist[1]))
    obs_vec=np.hstack((((obs_xy-det_org)*pix_dist[0]), np.expand_dims(np.array(dt, dtype=np.float64), axis=1)))
    obs_vec=obs_vec/np.expand_dims(np.sqrt(np.sum(np.square(obs_vec), axis=1)), axis=1)
    obs_vec=obs_vec-beam_dir
    obs_vec=obs_vec/np.expand_dims(np.sqrt(np.sum(np.square(obs_vec), axis=1)), axis=1)
    print(' ')
    print('... Observed reflections:', np.shape(obs_vec)[0])
    s1=np.shape(hkl)[0]
    s2=np.shape(obs_vec)[0]
    t1=np.zeros((s1, 3), dtype=np.float64)
    t2=np.zeros((s2, 3), dtype=np.float64)
    obs_vec=np.expand_dims(obs_vec, axis=1)+t1
    obs_vec=np.reshape(obs_vec, ((s1*s2), 3))
    hkl_vec=np.expand_dims(t2, axis=1)+hkl_vec
    hkl_vec=np.reshape(hkl_vec, ((s1*s2), 3))
    vec_sel=np.nonzero(np.sum((obs_vec*hkl_vec), axis=1) > np.cos(np.radians(np.float64(ang_lim))))
    hkl_vec=hkl_vec[vec_sel[0],:]
    obs_vec=obs_vec[vec_sel[0],:]
    print('Possible indices in total:', np.shape(hkl_vec)[0])
    mm=np.int64(10)
    sh1=np.expand_dims(np.arange(-mm, (mm+1), dtype=np.int64), axis=1)
    sk1=np.expand_dims(np.arange(-mm, (mm+1), dtype=np.int64), axis=1)
    sl1=np.expand_dims(np.arange(-mm, (mm+1), dtype=np.int64), axis=1)
    sh0=np.expand_dims(np.zeros((mm*np.int64(2)+np.int64(1)), dtype=np.int64), axis=1)
    sk0=np.expand_dims(np.zeros((mm*np.int64(2)+np.int64(1)), dtype=np.int64), axis=1)
    sl0=np.expand_dims(np.zeros((mm*np.int64(2)+np.int64(1)), dtype=np.int64), axis=1)
    sh=np.hstack((sh1,sh0,sh0))
    sk=np.hstack((sk0,sk1,sk0))
    sl=np.hstack((sl0,sl0,sl1))
    shkl=np.expand_dims((np.expand_dims(sh, axis=1)+sk), axis=2)+sl
    shkl=np.reshape(shkl, (((mm*np.int64(2)+np.int64(1))*(mm*np.int64(2)+np.int64(1))*(mm*np.int64(2)+np.int64(1))), 3))
    vec_sel=np.sum(np.absolute(shkl), axis=1) != 0
    shkl=shkl[vec_sel,:]
    n_foun=0
    n_psc=0
    s1=int(np.shape(hkl_vec)[0])
    for i in range(s1):
        for j in range((i+1),s1):
            hkl_pri=hkl_vec[np.int64(i),:]
            hkl_sec=hkl_vec[np.int64(j),:]
            obs_pri=obs_vec[np.int64(i),:]
            obs_sec=obs_vec[np.int64(j),:]
            t1=np.sum(hkl_pri*hkl_sec)
            t2=np.sum(obs_pri*obs_sec)
            if float(np.absolute(t1)) < math.cos(float(20.0)*math.pi/float(180.0)):
                if float(np.absolute(t2)) < math.cos(float(20.0)*math.pi/float(180.0)):
                    t1=np.degrees(np.arccos(t1))
                    t2=np.degrees(np.arccos(t2))
                    if float(np.absolute(t1-t2)) < float(1.0):
                        n_psc=n_psc+1
                        hkl_axi1=hkl_pri
                        obs_axi1=obs_pri
                        hkl_axi2=np.cross(hkl_axi1, hkl_sec)
                        hkl_axi2=hkl_axi2/np.sqrt(np.sum(np.square(hkl_axi2)))
                        obs_axi2=np.cross(obs_axi1, obs_sec)
                        obs_axi2=obs_axi2/np.sqrt(np.sum(np.square(obs_axi2)))
                        hkl_axi3=np.cross(hkl_axi1, hkl_axi2)
                        obs_axi3=np.cross(obs_axi1, obs_axi2)
                        hkl_mat=np.hstack((np.expand_dims(hkl_axi1, axis=1), np.expand_dims(hkl_axi2, axis=1), np.expand_dims(hkl_axi3, axis=1)))
                        obs_mat=np.hstack((np.expand_dims(obs_axi1, axis=1), np.expand_dims(obs_axi2, axis=1), np.expand_dims(obs_axi3, axis=1)))
                        hkl_com=hkl_vec @ hkl_mat
                        obs_com=obs_vec @ obs_mat
                        vec_sel=(np.sum((hkl_com*obs_com), axis=1) > np.cos(np.radians(np.float64(ang_tol))))
                        obs_fou=obs_vec[vec_sel,:]
                        if n_foun < int(np.shape(obs_fou)[0]):
                            abc_dir_m=abc_dir @ hkl_mat
                            abc_dir_m=abc_dir_m @ obs_mat.T
                            shkl_vec1=shkl.astype(np.float64)
                            shkl_vec1=shkl_vec1 @ abc_dir
                            shkl_vec1=shkl_vec1/np.expand_dims(np.sqrt(np.sum(np.square(shkl_vec1), axis=1)), axis=1)
                            shkl_vec2=shkl.astype(np.float64)
                            shkl_vec2=shkl_vec2 @ abc_dir_m
                            shkl_vec2=shkl_vec2/np.expand_dims(np.sqrt(np.sum(np.square(shkl_vec2), axis=1)), axis=1)
                            ang=float(np.min(np.sum((shkl_vec1*shkl_vec2), axis=1)))
                            ang=math.acos(ang)*180.0/math.pi
                            if ang < float(ang_lim):
                                n_foun=int(np.shape(obs_fou)[0])
                                nang=ang
                                abc_dir_n=abc_dir_m
    print('Combinations of primary and secondary vectors:', n_psc)
    print('Indexed reflections:', n_foun)
    print('Angular shift, deg.:', round(nang,2))
    abc_dir_n=np.reshape(abc_dir_n, 9)
    np.save('abc_matrix.npy', abc_dir_n)


def burn(res_lim=0, nscan=-1):
    import math
    global EnergyHighest, EnergyLowest, StructureType, ImageSizeX, ImageSizeY
    with np.load('geosetup.npz') as geo_arr:
        det_org=geo_arr['iitt1']
        beam_dir=geo_arr['iitt2']
        pix_dist=geo_arr['iitt3']
    if nscan > 1:
        a=np.loadtxt('abc', dtype=np.float64)
        # np.save('abc_matrix.npy', a)
        sh_tab=np.load('ang_shifts.npy')
        if sh_tab[(nscan-2),9] > np.float64(50):
            print('...No angular shift available')
            return
        ten=np.reshape(sh_tab[(nscan-2),0:9], (3,-1))
    elif nscan==1:
        a=np.loadtxt('abc', dtype=np.float64)
        # np.save('abc_matrix.npy', a)
    abc=np.load('abc_matrix.npy')
    abc_dir=np.reshape(abc, (3,-1))
    if nscan > 1:
        abc_dir=abc_dir @ ten
    abc_vol=np.cross(abc_dir[2,:], abc_dir[0,:]) @ abc_dir[1,:]
    abc_rec=np.vstack((np.cross(abc_dir[1,:], abc_dir[2,:]), np.cross(abc_dir[2,:], abc_dir[0,:]), np.cross(abc_dir[0,:], abc_dir[1,:])))/abc_vol
    abc_len=np.sqrt(np.sum(np.square(abc_dir), axis=1))
    print('a=, b=, c=:', abc_len)
    abc_nor=abc_dir/np.expand_dims(abc_len, axis=1)
    abc_ang=np.array([0,0,0], dtype=np.float64)
    abc_ang[0]=abc_nor[1] @ abc_nor[2]
    abc_ang[1]=abc_nor[2] @ abc_nor[0]
    abc_ang[2]=abc_nor[0] @ abc_nor[1]
    abc_ang=np.degrees(np.arccos(abc_ang))
    print('alpha=, beta=, gamma=:', abc_ang)
    print('Unit cell volume, Angstroms**3:', round(float(abc_vol), 2))
    d_min=0.4246*29.2/(2.0*float(EnergyHighest)*math.sin(float(pix_dist[2])))
    print(' ')
    print('... Detector opening resolution limit d/n >', round(d_min, 4), 'Angstroms')
    if d_min < float(res_lim):
        d_min=float(res_lim)
        print(' ')
        print('... Sample resolution limit d/n >', round(d_min, 4), 'Angstroms')
    print(' ')
    hkl_max_flo=np.sqrt(np.sum(np.square(abc_dir), axis=1))/np.float64(d_min)
    hkl_max=hkl_max_flo.astype(np.int64)+np.int64(1)
    print('h,k,l maximal:', hkl_max)
    max_h=hkl_max[0]
    max_k=hkl_max[1]
    max_l=hkl_max[2]
    h1=np.expand_dims(np.arange(np.int64(1), (max_h+1), dtype=np.int64), axis=1)
    k1=np.expand_dims(np.arange(-max_k, (max_k+1), dtype=np.int64), axis=1)
    l1=np.expand_dims(np.arange(-max_l, (max_l+1), dtype=np.int64), axis=1)
    h0=np.expand_dims(np.zeros(max_h, dtype=np.int64), axis=1)
    k0=np.expand_dims(np.zeros((max_k*np.int64(2)+np.int64(1)), dtype=np.int64), axis=1)
    l0=np.expand_dims(np.zeros((max_l*np.int64(2)+np.int64(1)), dtype=np.int64), axis=1)
    h=np.hstack((h1,h0,h0))
    k=np.hstack((k0,k1,k0))
    l=np.hstack((l0,l0,l1))
    hkl=np.expand_dims((np.expand_dims(h, axis=1)+k), axis=2)+l
    hkl1=np.reshape(hkl, ((max_h*(max_k*np.int64(2)+np.int64(1))*(max_l*np.int64(2)+np.int64(1))), 3))
    hkl=np.expand_dims(k[max_k:(np.int64(2)*max_k+np.int64(1)),:], axis=1)+l[max_l:(np.int64(2)*max_l+np.int64(1)),:]
    hkl2=np.reshape(hkl, ((max_k+np.int64(1))*(max_l+np.int64(1)), 3))
    hkl=np.expand_dims(k[(max_k+np.int64(1)):(np.int64(2)*max_k+np.int64(1)),:], axis=1)+l[np.int64(0):max_l,:]
    hkl3=np.reshape(hkl, ((max_k*max_l), 3))
    hkl=np.vstack((hkl1,hkl2,hkl3))
    vec_sel=np.sum(np.absolute(hkl), axis=1) != 0
    hkl=hkl[vec_sel,:]
    print('Total number of indices:', np.shape(hkl)[0])
    ind_tot=float(np.shape(hkl)[0])
    vec_sel=(np.gcd.reduce(hkl, axis=1)==1)
    hkl=hkl[vec_sel,:]
    ind_rpi=float(np.shape(hkl)[0])
    print('Relatively prime integers:', np.shape(hkl)[0], '(', round((ind_rpi*100.0/ind_tot),2), '% )')
    hkl_vec=hkl.astype(np.float64)
    hkl_vec=hkl_vec @ abc_rec
    hkl_dis=np.float64(1)/np.sqrt(np.sum(np.square(hkl_vec), axis=1))
    vec_sel=np.nonzero(hkl_dis > np.float64(d_min))
    hkl_vec=hkl_vec[vec_sel[0],:]
    hkl_dis=hkl_dis[vec_sel[0]]
    hkl_vec=hkl_vec*np.expand_dims(hkl_dis, axis=1)
    hkl=hkl[vec_sel[0],:]
    print(' ')
    print('... n=1')
    print('Sets of crystallographic planes with d >', round(d_min, 4), 'Angstroms:', np.shape(hkl)[0])
    hkl_tet=hkl_vec @ beam_dir
    vec_sel=np.nonzero(np.fabs(hkl_tet) < np.sin(pix_dist[2]))
    hkl_vec=hkl_vec[vec_sel[0],:]
    hkl_dis=hkl_dis[vec_sel[0]]
    hkl_tet=hkl_tet[vec_sel[0]]
    hkl=hkl[vec_sel[0],:]
    print('Reciprocal vectors with theta <', round((float(pix_dist[2])*180.0/math.pi), 2), 'degrees:', np.shape(hkl)[0])
    hkl_enr=0.4246*29.2/(np.float64(2)*np.fabs(hkl_tet)*hkl_dis)
    vec_sel=np.nonzero(hkl_enr < np.float64(EnergyHighest))
    hkl_vec=hkl_vec[vec_sel[0],:]
    hkl_dis=hkl_dis[vec_sel[0]]
    hkl_tet=hkl_tet[vec_sel[0]]
    hkl_enr=hkl_enr[vec_sel[0]]
    hkl=hkl[vec_sel[0],:]
    print('Reciprocal vectors with energies <', round(float(EnergyHighest), 2), 'keV:', np.shape(hkl)[0])
    hkl_dif=beam_dir-hkl_vec*np.expand_dims(hkl_tet, axis=1)*np.float64(2)
    vec_sel=np.nonzero(hkl_dif[:,2] > pix_dist[3])
    hkl_vec=hkl_vec[vec_sel[0],:]
    hkl_dif=hkl_dif[vec_sel[0],:]
    hkl_dis=hkl_dis[vec_sel[0]]
    hkl_tet=hkl_tet[vec_sel[0]]
    hkl_enr=hkl_enr[vec_sel[0]]
    hkl=hkl[vec_sel[0],:]
    print('Reflections towards area detector:', np.shape(hkl)[0])
    hkl_pos=(np.expand_dims((pix_dist[1]/hkl_dif[:,2]), axis=1)*hkl_dif[:,0:2])/pix_dist[0]+det_org
    vec_sel=np.nonzero(hkl_pos[:,0] > np.float64(0))
    hkl_vec=hkl_vec[vec_sel[0],:]
    hkl_dif=hkl_dif[vec_sel[0],:]
    hkl_pos=hkl_pos[vec_sel[0],:]
    hkl_dis=hkl_dis[vec_sel[0]]
    hkl_tet=hkl_tet[vec_sel[0]]
    hkl_enr=hkl_enr[vec_sel[0]]
    hkl=hkl[vec_sel[0],:]
    vec_sel=np.nonzero(hkl_pos[:,0] < np.float64(ImageSizeX))
    hkl_vec=hkl_vec[vec_sel[0],:]
    hkl_dif=hkl_dif[vec_sel[0],:]
    hkl_pos=hkl_pos[vec_sel[0],:]
    hkl_dis=hkl_dis[vec_sel[0]]
    hkl_tet=hkl_tet[vec_sel[0]]
    hkl_enr=hkl_enr[vec_sel[0]]
    hkl=hkl[vec_sel[0],:]
    vec_sel=np.nonzero(hkl_pos[:,1] > np.float64(0))
    hkl_vec=hkl_vec[vec_sel[0],:]
    hkl_dif=hkl_dif[vec_sel[0],:]
    hkl_pos=hkl_pos[vec_sel[0],:]
    hkl_dis=hkl_dis[vec_sel[0]]
    hkl_tet=hkl_tet[vec_sel[0]]
    hkl_enr=hkl_enr[vec_sel[0]]
    hkl=hkl[vec_sel[0],:]
    vec_sel=np.nonzero(hkl_pos[:,1] < np.float64(ImageSizeY))
    hkl_vec=hkl_vec[vec_sel[0],:]
    hkl_dif=hkl_dif[vec_sel[0],:]
    hkl_pos=hkl_pos[vec_sel[0],:]
    hkl_dis=hkl_dis[vec_sel[0]]
    hkl_tet=hkl_tet[vec_sel[0]]
    hkl_enr=hkl_enr[vec_sel[0]]
    hkl=hkl[vec_sel[0],:]
    vec_sel=np.nonzero(np.fabs(hkl_tet) > np.float64(15)*pix_dist[0]/pix_dist[1])
    hkl_vec=hkl_vec[vec_sel[0],:]
    hkl_dif=hkl_dif[vec_sel[0],:]
    hkl_pos=hkl_pos[vec_sel[0],:]
    hkl_dis=hkl_dis[vec_sel[0]]
    hkl_tet=hkl_tet[vec_sel[0]]
    hkl_enr=hkl_enr[vec_sel[0]]
    hkl=hkl[vec_sel[0],:]
    print('Reflections hitting area detector:', np.shape(hkl)[0])
    aaa=-np.sign(hkl_tet)
    hkl=hkl*np.expand_dims(aaa.astype(np.int64), axis=1)
    hkl_enr_dis=np.hstack((np.expand_dims(hkl_enr, axis=1), np.expand_dims(hkl_dis, axis=1)))
    eded=[]
    n1n2=[]
    sta_mul=[0,0,0,0,0]
    iii=0
    for aaa in hkl_enr_dis:
        eee=aaa[0]
        ddd=aaa[1]
        nnn=1
        chch=1
        while eee < float(EnergyHighest):
            if eee > float(EnergyLowest):
                if ddd > d_min:
                    if chch==1:
                        nnn1=nnn
                        chch=0
                    nnn2=nnn
                else:
                    break
            nnn=nnn+1
            eee=aaa[0]*float(nnn)
            ddd=aaa[1]/float(nnn)
        if chch==0:
            eded.append(iii)
            n1n2_loc=[]
            n1n2_loc.append(nnn1)
            n1n2_loc.append(nnn2)
            n1n2.append(n1n2_loc)
            if (nnn2-nnn1) < 5:
                sta_mul[(nnn2-nnn1)]=sta_mul[(nnn2-nnn1)]+1
        iii=iii+1
    vec_sel=np.array(eded, dtype=np.int64)
    hkl_nnn=np.array(n1n2, dtype=np.int64)
    hkl_vec=hkl_vec[vec_sel,:]
    hkl_dif=hkl_dif[vec_sel,:]
    hkl_pos=hkl_pos[vec_sel,:]
    hkl_dis=hkl_dis[vec_sel]
    hkl_tet=hkl_tet[vec_sel]
    hkl_enr=hkl_enr[vec_sel]
    hkl=hkl[vec_sel,:]
    print(' ')
    print('... Predicted reflections:', np.shape(hkl)[0])
    print('Multiplicity distribution')
    print('(International Tables for Crystallography (2006). Vol. C, Section 2.2.1, pp. 26–29.)')
    print('n    %')
    sta_pre_tot=float(np.shape(hkl)[0])
    for i in range(5):
        print((i+1), round((float(sta_mul[i])*100.0/sta_pre_tot),2),'%')
    if StructureType != '':
        if StructureType == 'hcp':
            ref_cond1=range(0,(max_l+1),2)
            ref_cond2=range(1,(max_h+max_k+1),3)
            ref_cond3=range(2,(max_h+max_k+1),3)
        if StructureType == 'Diamond':
            ref_cond1=range(0,(max_h+max_k+1),2)
            ref_cond2=range(0,(max_h+max_k+1),4)
            ref_cond3=range(1,(max_h+1),2)
            ref_cond4=range(0,(max_h+max_k+max_l+1),4)
        hkl_ord=np.hstack((hkl, hkl_nnn))
        eded=[]
        n1n2=[]
        iii=0
        for aaa in hkl_ord:
            n1=int(aaa[3])
            n2=int(aaa[4])
            ch_ch_ch=1
            for i in range(n1,(n2+1)):
                h=int(aaa[0])*i
                k=int(aaa[1])*i
                l=int(aaa[2])*i
                if StructureType == 'hcp':
                    ch_ch=-1
                    if abs(l) in ref_cond1:
                        ch_ch=ch_ch+1
                    elif abs(h-k) in ref_cond2:
                        ch_ch=ch_ch+1
                    elif abs(h-k) in ref_cond3:
                        ch_ch=ch_ch+1
                    if ch_ch == 0:
                        if ch_ch_ch == 1:
                            ch_ch_ch=0
                            nnn1=i
                        nnn2=i
                if StructureType == 'Diamond':
                    ch_ch=-3
                    if abs(h+k) in ref_cond1:
                        ch_ch=ch_ch+1
                    if abs(h+l) in ref_cond1:
                        ch_ch=ch_ch+1
                    if abs(l+k) in ref_cond1:
                        ch_ch=ch_ch+1
                    if ch_ch == 0:
                        if h == 0:
                            ch_ch=-1
                            if abs(k+l) in ref_cond2:
                                ch_ch=ch_ch+1
                    if ch_ch == 0:
                        if k == 0:
                            ch_ch=-1
                            if abs(h+l) in ref_cond2:
                                ch_ch=ch_ch+1
                    if ch_ch == 0:
                        if l == 0:
                            ch_ch=-1
                            if abs(k+h) in ref_cond2:
                                ch_ch=ch_ch+1
                    if ch_ch == 0:
                        ch_ch=-1
                        if abs(h) in ref_cond3:
                            ch_ch=ch_ch+1
                        elif abs(h+k+l) in ref_cond4:
                            ch_ch=ch_ch+1
                    if ch_ch == 0:
                        ch_ch=-1
                        if abs(k) in ref_cond3:
                            ch_ch=ch_ch+1
                        elif abs(h+k+l) in ref_cond4:
                            ch_ch=ch_ch+1
                    if ch_ch == 0:
                        ch_ch=-1
                        if abs(l) in ref_cond3:
                            ch_ch=ch_ch+1
                        elif abs(h+k+l) in ref_cond4:
                            ch_ch=ch_ch+1
                    if ch_ch == 0:
                        if ch_ch_ch == 1:
                            ch_ch_ch=0
                            nnn1=i
                        nnn2=i
            if ch_ch_ch == 0:
                eded.append(iii)
                n1n2_loc=[]
                n1n2_loc.append(nnn1)
                n1n2_loc.append(nnn2)
                n1n2.append(n1n2_loc)
            iii=iii+1
        vec_sel=np.array(eded, dtype=np.int64)
        hkl_nnn=np.array(n1n2, dtype=np.int64)
        hkl_vec=hkl_vec[vec_sel,:]
        hkl_dif=hkl_dif[vec_sel,:]
        hkl_pos=hkl_pos[vec_sel,:]
        hkl_dis=hkl_dis[vec_sel]
        hkl_tet=hkl_tet[vec_sel]
        hkl_enr=hkl_enr[vec_sel]
        hkl=hkl[vec_sel,:]
        print('')
        print('... Satisfying reflection conditions for', StructureType, ':', np.shape(hkl)[0])
    hkl_n1=hkl_nnn[:,0]
    hkl=hkl*np.expand_dims(hkl_n1, axis=1)
    hkl_enr=hkl_enr*hkl_n1.astype(np.float64)
    hkl_dis=hkl_dis/hkl_n1.astype(np.float64)
    pred_list1=np.hstack((hkl,hkl_nnn))
    pred_list2=np.hstack((hkl_pos,np.expand_dims(hkl_enr, axis=1),np.expand_dims(hkl_dis, axis=1)))
    np.savez('predicted_list.npz', ipred_list1=pred_list1, ipred_list2=pred_list2)



def geo_from_Dioptas():
    import math
    global ImageSizeX, ImageSizeY, WhiteBeamShift
    imsiy=float(ImageSizeY)
    wmbs=float(WhiteBeamShift)
    with open('poly.poni') as f:
        poly_poni=f.read()
    dt=[1,1,1,1,1,1]
    for w in poly_poni.splitlines():
        ww=w.split()
        if 'PixelSize1:' in ww:
            dt[0]=0
            pix=float(ww[1])*1000.0
            print('Pixel size, mm:', pix)
        if '"pixel2":' in ww:
            dt[0]=0
            ss=ww[4]
            sss=len(ww[4])
            pix=float(ss[:(sss-1)])*1000.0
            print('Pixel size, mm:', pix)
        if 'Distance:' in ww:
            dt[1]=0
            sam_det_d=float(ww[1])*1000.0
            print('Sample to detector distance, mm:', sam_det_d)
        if 'Poni1:' in ww:
            dt[2]=0
            PoniY=float(ww[1])
        if 'Poni2:' in ww:
            dt[3]=0
            PoniX=float(ww[1])
        if 'Rot1:' in ww:
            dt[4]=0
            rot1=float(ww[1])
            print('Rot1, rad:', rot1)
        if 'Rot2:' in ww:
            dt[5]=0
            rot2=float(ww[1])
            print('Rot2, rad:', rot2)
    if 1 in dt:
        return '...Error! Unknown format'
    PoniX=PoniX*1000.0/pix
    PoniY=imsiy-PoniY*1000.0/pix+wmbs/pix
    print('PoniX, pix:', PoniX)
    print('PoniY, pix:', PoniY)
    beam_x=math.cos(rot2)*math.cos(math.pi/2.0+rot1)
    beam_y=math.cos(math.pi/2.0+rot2)
    beam_z=math.cos(rot2)*math.cos(rot1)
    dt=[]
    dt.append(PoniX)
    dt.append(PoniY)
    det_org=np.array(dt, dtype=np.float64)
    dt=[]
    dt.append(beam_x)
    dt.append(beam_y)
    dt.append(beam_z)
    beam_dir=np.array(dt, dtype=np.float64)
    dt=[]
    dtl=[]
    dtl.append(0)
    dtl.append(0)
    dt.append(dtl)
    dtl=[]
    dtl.append(ImageSizeX)
    dtl.append(0)
    dt.append(dtl)
    dtl=[]
    dtl.append(ImageSizeX)
    dtl.append(ImageSizeY)
    dt.append(dtl)
    dtl=[]
    dtl.append(0)
    dtl.append(ImageSizeY)
    dt.append(dtl)
    im_corn=np.array(dt, dtype=np.float64)
    dt=[]
    for i in im_corn:
        dt.append(sam_det_d)
    ang_vec1=np.hstack((((im_corn-det_org)*np.float64(pix)), np.expand_dims(np.array(dt, dtype=np.float64), axis=1)))
    ang_vec2=ang_vec1/np.expand_dims(np.sqrt(np.sum(np.square(ang_vec1), axis=1)), axis=1)
    ang_tet=math.acos(float(np.min(ang_vec2 @ beam_dir)))/2.0
    print('Largest teta, deg.:', round((ang_tet*180.0/math.pi), 2))
    ang_sol=float(np.min(ang_vec2[:,2]))
    dt=[]
    dt.append(pix)
    dt.append(sam_det_d)
    dt.append(ang_tet)
    dt.append(ang_sol)
    pix_dist=np.array(dt, dtype=np.float64)
    np.savez('geosetup.npz', iitt1=det_org, iitt2=beam_dir, iitt3=pix_dist)

