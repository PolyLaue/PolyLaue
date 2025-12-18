# Copyright © 2025, UChicago Argonne, LLC. See "LICENSE" for full details.

import numpy as np

from reflections_table_editor import ReflectionsTableEditor

# Read a crystal from the 'predictions.h5' file and write to txt
editor = ReflectionsTableEditor('predictions.h5')

crystal_id = 0
output_filename = 'crystal.txt'

table = editor.crystals_table()
np.savetxt(output_filename, table[crystal_id], delimiter='\n')
