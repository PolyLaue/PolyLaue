# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

import numpy as np

from reflections_table_editor import ReflectionsTableEditor

# Output will be written to 'predictions.h5'
editor = ReflectionsTableEditor('predictions.h5')

# Pick the scan number and scan position
scan_num = 1
scan_pos_x = 1
scan_pos_y = 1

# Each NPZ file is for a separate crystal ID
npz_files = [
    'predicted_list.npz',
    # Add more, one for each crystal
]

# NOTE: at this point, you need to call `editor.set_crystals_table()`
# with the crystals in the same order as the order of the NPZ files above.

# editor.set_crystals_table(crystals_table)

for crystal_id, filename in enumerate(npz_files):
    f = np.load(filename)
    pred_list1 = f['ipred_list1']
    pred_list2 = f['ipred_list2']

    # Stack the predictions together in the way we expect for the HDF5 file
    table = np.hstack(
        (
            # x, y
            pred_list2[:, 0:2],
            # h, k, l
            pred_list1[:, 0:3],
            # energy
            pred_list2[:, 2:3],
            # First order, last order
            pred_list1[:, 3:5],
            # d-spacing
            pred_list2[:, 3:4],
        )
    )

    # Add the crystal ID into the 9th column
    table = np.insert(table, 9, crystal_id, axis=1)

    # Now write this to the HDF5 file
    editor.set_reflections_table(
        table,
        scan_num,
        scan_pos_x,
        scan_pos_y,
    )
