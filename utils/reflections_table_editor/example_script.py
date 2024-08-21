# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

import numpy as np

from reflections_table_editor import ReflectionsTableEditor

# File is created automatically if it does not exist
editor = ReflectionsTableEditor('predictions.h5')

# The editor includes the following functions for writing/reading tables:
# editor.set_crystals_table()
# editor.crystals_table()
# editor.set_reflections_table()
# editor.reflections_table()

# First, create a crystals table. This must have 9 columns
# NOTE: crystal id uses zero indexing, so 0 is the first crystal
crystals_table = np.array(
    [
        # Each row of the crystal table is just the 9 parameters
        [1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 2, 3, 4, 5, 6, 7, 8, 9],
    ]
)

# Set the crystals table with the editor
editor.set_crystals_table(crystals_table)

# We can also read the crystals table with the editor, modify it, and
# set it again.
# Read the table from the file
table_from_file = editor.crystals_table()
print('Crystals table from file is:\n', table_from_file)
# Modify the table
table_from_file[0, 0] = 0
# Set it back on the file
editor.set_crystals_table(table_from_file)

# Now you can see file has the edited version
table_from_file = editor.crystals_table()
print('After modifying, crystals table from file is now:\n', table_from_file)


# Now, create a reflections table. This must have 10 columns.
table_of_reflections = np.array(
    [
        # Columns are (in order):
        # x (predicted),y (predicted),h,k,l,Energy (keV),First Order,Last Order,d (Å),  Crystal ID
        [1328.67, 809.85, 1, 0, 0, 6.73, 1, 5, 4.3164, 0],
        [1839.69, 1975.93, 1, 2, 1, 17.77, 1, 1, 1.4444, 0],
        [1537.13, 1769.52, 2, 2, 1, 21.4, 1, 1, 1.1565, 1],
    ]
)


# Choose the scan number and scan position
scan_num = 22
scan_pos_x = 1
scan_pos_y = 1

# Write this table to the file
editor.set_reflections_table(
    table_of_reflections,
    scan_num,
    scan_pos_x,
    scan_pos_y,
)

# Now read this table from the file
table_from_file = editor.reflections_table(
    scan_num,
    scan_pos_x,
    scan_pos_y,
)
print('Reflections table from file is:\n', table_from_file)

# Modify the table (change the crystal ID for the second reflection)
table_from_file[1, 9] = 1

# Set the modified table back on the file
editor.set_reflections_table(
    table_from_file,
    scan_num,
    scan_pos_x,
    scan_pos_y,
)

# Now read it again from the file, and show it was modified
table_from_file = editor.reflections_table(
    scan_num,
    scan_pos_x,
    scan_pos_y,
)

print('After modifying, reflections table from file is now:\n', table_from_file)
