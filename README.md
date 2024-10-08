# PolyLaue

![image](https://github.com/user-attachments/assets/ad01aa2a-69ee-466e-acba-0079acf86e2b)

PolyLaue is a tool for visualizing and analyzing scans of Laue x-ray diffraction patterns.
It is developed in collaboration with the High-Pressure Collaborative Access Team (HPCAT)
located in the Advanced Photon Source (APS) of Argonne National Laboratory.

## Install (Conda)

First, create and activate a new conda environment for PolyLaue:

```bash
conda create -n polylaue -y
conda activate polylaue
```

Next, install Python3.11 and the latest PolyLaue release into the conda
environment.

```bash
conda install -y -c conda-forge python=3.11 polylaue
```

You should be able to start PolyLaue now by running the `polylaue` command.

When a new terminal is opened, to start PolyLaue, first be sure to
activate the PolyLaue environment by running `conda activate polylaue`,
and then run the `polylaue` command to start the application again.

## Update (conda)

To update PolyLaue to the latest version, first activate the PolyLaue
environment:

```bash
conda activate polylaue
```

And then run the following command:

```bash
conda update -y -c conda-forge polylaue
```

After it completes, PolyLaue will be updated to the latest.
