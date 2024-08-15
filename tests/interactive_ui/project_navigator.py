# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

import json
import os
from pathlib import Path
import signal

from PySide6.QtWidgets import QApplication

from polylaue.model.project_manager import ProjectManager
from polylaue.model.series import Series
from polylaue.ui.project_navigator.dialog import ProjectNavigatorDialog

# Kill the program when ctrl-c is used
signal.signal(signal.SIGINT, signal.SIG_DFL)

example_json_path = (
    Path(__file__).parent / '../test_project_manager.json'
).resolve()

with open(example_json_path, 'r') as rf:
    serialized = json.load(rf)

pm = ProjectManager.from_serialized(serialized)

data_path = os.environ.get('POLYLAUE_TEST_DATA_PATH')
if data_path:
    # Replace '/__test_series_path' with this path
    for project in pm.projects:
        for section in project.sections:
            for series in section.series:
                series.dirpath_str = series.dirpath_str.replace(
                    '/__test_series_path', data_path
                )

app = QApplication()

dialog = ProjectNavigatorDialog(pm)
dialog.setWindowTitle('Test Project Navigator')
dialog.show()


def on_data_modified():
    print('Data modified:')
    print(json.dumps(pm.serialize(), indent=4))


def on_open_series(series: Series):
    print('Open series:', series.name)


dialog.view.open_series.connect(on_open_series)
dialog.model.data_modified.connect(on_data_modified)

app.exec()
