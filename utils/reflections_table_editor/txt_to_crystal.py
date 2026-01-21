# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

import numpy as np

from reflections_table_editor import ReflectionsTableEditor

# Read a crystal from 'crystal.txt' and write it to the table
input_filename = 'crystal.txt'
crystal_id = 0

editor = ReflectionsTableEditor('predictions.h5')

new_crystal = np.loadtxt(input_filename)

table = editor.crystals_table()
table[crystal_id] = new_crystal
editor.set_crystals_table(table)
