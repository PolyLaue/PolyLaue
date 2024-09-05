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
# The key is the crystal ID. The value is the file name.
npz_files = {
    0: 'predicted_list.npz',
    # 1: 'predicted_list0.npz',
    # Add more, one for each crystal
}

# NOTE: if the crystals_table doesn't already exist on the HDF5 file,
# you will need to also set it, something simlar to the following:

crystals_table = np.array(
    [
        # Each row of the crystal table is just the 9 parameters
        [1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 2, 3, 4, 5, 6, 7, 8, 9],
    ]
)

editor.set_crystals_table(crystals_table)

# Stack all tables together in one list
all_tables = []
for crystal_id, filename in npz_files.items():
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

    all_tables.append(table)

reflections = np.vstack(all_tables)

# Pull the existing reflections table out of the file, remove any
# reflections that match the crystal IDs we will insert, and stack
# this with the new reflections.
existing_reflections = editor.reflections_table(
    scan_num,
    scan_pos_x,
    scan_pos_y,
)
if existing_reflections is not None:
    # Delete any existing reflections that match any crystal IDs
    # that we are inserting.
    for crystal_id in npz_files:
        existing_reflections = np.delete(
            existing_reflections,
            np.where(existing_reflections[:, 9].astype(int) == crystal_id)[0],
            axis=0,
        )

    # Stack together with the new reflections
    reflections = np.vstack(
        (
            reflections,
            existing_reflections,
        )
    )

    # Sort by crystal ID
    reflections = reflections[reflections[:, 9].argsort()]

# Now write all tables to the HDF5 file
editor.set_reflections_table(
    reflections,
    scan_num,
    scan_pos_x,
    scan_pos_y,
)
