import h5py
import numpy as np


table_of_reflections = np.array(
    [
        # Columns are (in order):
        # x (predicted),y (predicted),h,k,l,Energy (keV),First Order,Last Order,d (Å),	Crystal ID
        [1328.67, 809.85, 1, 0, 0, 6.73, 1, 5, 4.3164, 0],
        [1839.69, 1975.93, 1, 2, 1, 17.77, 1, 1, 1.4444, 0],
        [1537.13, 1769.52, 2, 2, 1, 21.4, 1, 1, 1.1565, 1],
    ]
)

# NOTE: crystal id uses zero indexing, so 0 is the first crystal
crystals_table = np.array(
    [
        # Each row of the crystal table is just the 9 parameters
        [1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 2, 3, 4, 5, 6, 7, 8, 9],
    ]
)


# Now write it to a file

with h5py.File('reflections.h5', 'a') as wf:
    # Write the crystals table
    if 'crystals' in wf:
        # We must delete it if it already exists
        del wf['crystals']

    wf['crystals'] = crystals_table

    # For every table of reflections, you must specify the scan number,
    # scan position (x), and scan position (y).
    scan_number = 24
    scan_pos_x = 1
    scan_pos_y = 1

    path = f'/predictions/{scan_number}/{scan_pos_x}/{scan_pos_y}'
    if path in wf:
        # We must delete it if it already exists
        del wf[path]

    wf[path] = table_of_reflections

# Now, if you open up the file in PolyLaue, you will see these predictions
# if you navigate to scan 1 at scan position (1, 1).
