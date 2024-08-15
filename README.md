# PolyLaue

![image](https://github.com/user-attachments/assets/ad01aa2a-69ee-466e-acba-0079acf86e2b)

PolyLaue is a tool for visualizing and analyzing scans of Laue x-ray diffraction patterns.
It is developed in collaboration with the High-Pressure Collaborative Access Team (HPCAT)
located in the Advanced Photon Source (APS) of Argonne National Laboratory.

## Conda Development Environment

First, create and activate a new conda environment for PolyLaue:

```bash
conda create -n polylaue -y
conda activate polylaue
```

Next, install dependencies into the conda environment, including Python3.11:

```bash
conda install -y -c conda-forge python=3.11 fabio h5py numba numpy platformdirs pyside6 pyqtgraph pillow scipy
```

Now, enter into the `polylaue` source code directory and run the following command:

```bash
pip install --no-build-isolation --no-deps -U -e .
```

You should be able to start PolyLaue now by running the `polylaue` command.
