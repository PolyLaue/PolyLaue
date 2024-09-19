# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

import numpy as np

from reflections_table_editor import ReflectionsTableEditor

editor = ReflectionsTableEditor('predictions.h5')

# Pick the scan number, scan position, and crystal ID for the
# reflections to be removed. If the crystal_id is `None`, then
# reflections for every crystal ID will be removed from that table.
scan_num = 1
scan_pos_y = 1
scan_pos_z = 1
crystal_id = 0

# Pull the existing reflections table out of the file, remove any
# reflections that match the crystal IDs we will insert, and stack
# this with the new reflections.
reflections = editor.reflections_table(
    scan_num,
    scan_pos_y,
    scan_pos_z,
)
delete_all = False
if crystal_id is None:
    delete_all = True
else:
    # Delete any matching crystal IDs
    reflections = np.delete(
        reflections,
        np.where(reflections[:, 9].astype(int) == crystal_id)[0],
        axis=0,
    )
    if len(reflections) != 0:
        editor.set_reflections_table(
            reflections,
            scan_num,
            scan_pos_y,
            scan_pos_z,
        )
    else:
        delete_all = True


if delete_all:
    # Just delete the whole table
    editor.delete_reflections_table(scan_num, scan_pos_y, scan_pos_z)
