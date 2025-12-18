# Copyright © 2025, UChicago Argonne, LLC. See "LICENSE" for full details.

import numpy as np

from reflections_table_editor import ReflectionsTableEditor

# Output will be written to 'predictions.h5'
editor = ReflectionsTableEditor('predictions.h5')

crystals_table = np.array(
    [
        # Each row of the crystal table is just the 9 parameters
        [1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 2, 3, 4, 5, 6, 7, 8, 9],
    ]
)

editor.set_crystals_table(crystals_table)
