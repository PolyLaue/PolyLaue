# Copyright © 2025, UChicago Argonne, LLC. See "LICENSE" for full details.

from reflections_table_editor import ReflectionsTableEditor

# Read a crystal from the 'predictions.h5' file and write to txt
editor = ReflectionsTableEditor('predictions.h5')
crystal_id = 0

table = editor.crystals_table()

# Read this crystal. This is an array of length 9.
crystal = table[crystal_id]

# Modify it however you want
crystal[1] = 5

# Set it back on the table
table[crystal_id] = crystal

# Write the table back to the HDF5 file
editor.set_crystals_table(table)
