# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from functools import lru_cache
import logging
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QWidget

import numpy as np

from polylaue.model.io import load_image_file, identify_loader_function, Bounds
from polylaue.model.roi_manager import ROIManager
from polylaue.model.scan import Scan
from polylaue.model.series import Series
from polylaue.model.state import load_project_manager, save_project_manager
from polylaue.typing import PathLike
from polylaue.ui.frame_tracker import FrameTracker
from polylaue.ui.image_view import PolyLaueImageView
from polylaue.ui.reflections_editor import ReflectionsEditor
from polylaue.ui.point_selector import PointSelectorDialog
from polylaue.ui.prediction_matcher import PredictionMatcherDialog
from polylaue.ui.project_navigator.dialog import ProjectNavigatorDialog
from polylaue.ui.region_mapping.dialog import RegionMappingDialog
from polylaue.ui.regions_navigator.dialog import RegionsNavigatorDialog
from polylaue.ui.series_editor import SeriesEditorDialog
from polylaue.ui.utils.ui_loader import UiLoader


logger = logging.getLogger(__name__)


class MainWindow:
    def __init__(self, parent: QWidget | None = None):
        self.ui = UiLoader().load_file('main_window.ui', parent)

        # Keep track of the working directory
        self.working_dir = None
        self.series = None
        self.frame_tracker = FrameTracker()

        # We currently assume all image files in a series will have the
        # same image loader. Cache that image loader so we do not have
        # to identify the image loader every time a new file is opened.
        self.image_loader_func = None

        # Load the project manager
        self.project_manager = load_project_manager()

        self.reset_scan_position()

        # Add the pyqtgraph view to its layout
        self.image_view = PolyLaueImageView(
            self.ui, 'CentralView', frame_tracker=self.frame_tracker
        )
        self.ui.image_view_layout.addWidget(self.image_view)

        self.reflections_editor = ReflectionsEditor(self.ui)

        self.roi_manager = ROIManager()

        self.region_mapping_dialogs = {}
        self.mapping_highlight_area = None
        self.mapping_domain_area = None
        self.show_mapping_highlight_area = False
        self.show_mapping_domain_area = False

        self.setup_connections()

    def setup_connections(self):
        self.ui.action_open_series.triggered.connect(self.on_open_series)
        self.ui.action_open_project_navigator.triggered.connect(
            self.open_project_navigator
        )
        self.ui.action_overlays_reflections.triggered.connect(
            self.open_reflections_editor
        )
        self.ui.action_select_indexing_points.triggered.connect(
            self.begin_select_indexing_points
        )

        self.ui.action_regions_manager.triggered.connect(
            self.open_mapping_regions_manager
        )
        self.ui.action_apply_background_subtraction.toggled.connect(
            self.on_action_apply_background_subtraction_toggled
        )

        self.image_view.shift_scan_number.connect(self.on_shift_scan_number)
        self.image_view.shift_scan_position.connect(
            self.on_shift_scan_position
        )
        self.image_view.mouse_move_message.connect(self.on_mouse_move_message)
        self.image_view.set_image_to_series_background.connect(
            self.set_current_image_to_series_background
        )
        self.image_view.set_image_to_section_background.connect(
            self.set_current_image_to_section_background
        )

        self.reflections_editor.reflections_changed.connect(
            self.on_reflections_changed
        )
        self.reflections_editor.prediction_matcher_triggered.connect(
            self.begin_prediction_matcher
        )
        self.reflections_editor.reflections_style_changed.connect(
            self.on_reflections_style_changed
        )

    @property
    def apply_background_subtraction(self) -> bool:
        return self.ui.action_apply_background_subtraction.isChecked()

    @apply_background_subtraction.setter
    def apply_background_subtraction(self, b: bool):
        return self.ui.action_apply_background_subtraction.setChecked(b)

    @property
    def scan_pos(self) -> np.ndarray:
        return np.asarray(self.frame_tracker.scan_pos)

    @scan_pos.setter
    def scan_pos(self, v: np.ndarray):
        self.frame_tracker.scan_pos = tuple(v)

    @property
    def scan_num(self) -> int:
        return self.frame_tracker.scan_num

    @scan_num.setter
    def scan_num(self, v: int):
        self.frame_tracker.scan_num = v

    def reset_scan_position(self):
        self.scan_pos = np.array([0, 0])

        if self.series:
            # Reset to the first available position on the series
            self.scan_num = self.series.scan_range_tuple[0]
        else:
            self.scan_num = 1

    def on_open_series(self):
        selected_directory = QFileDialog.getExistingDirectory(
            self.ui, 'Open Series Directory', self.working_dir
        )

        if not selected_directory:
            # User canceled
            return

        self.create_and_load_series(selected_directory)

    def create_and_load_series(self, selected_directory: PathLike):
        series = Series(selected_directory)
        editor = SeriesEditorDialog(series, self.ui)
        if not editor.exec():
            # User canceled.
            return

        self.load_series(series)

    def load_series(self, series: Series, reset_settings: bool = True):
        """Load the series located in the directory.

        This will also reset the current image settings and scan position.
        """

        self.series = series

        # Identify the image loader we will use for the series
        self.identify_image_loader()

        if reset_settings:
            # Reset scan position
            self.reset_scan_position()
            self.load_current_image()
            self.reset_image_view_settings()

        self.update_info_label()

        # After the data has been loaded, set the window title to be
        # the name of this series
        self.ui.setWindowTitle(f'PolyLaue - {series.name}')

    def identify_image_loader(self):
        self.image_loader_func = None
        if self.series is None:
            return

        if not self.series.file_list:
            # Might need to validate...
            self.series.validate()

        # Assume that all files in the series use the same image loader.
        # Use that loader for all files, rather than identifying the loader
        # each time an individual file is loaded.
        first_file = self.series.file_list[0]
        logger.debug(f'Identifying loader function for: {first_file}')
        self.image_loader_func = identify_loader_function(first_file)
        logger.debug(f'Identified loader function: {self.image_loader_func}')

    def open_project_navigator(self):
        if not hasattr(self, '_project_navigator_dialog'):
            d = ProjectNavigatorDialog(self.project_manager, self.ui)
            d.model.data_modified.connect(self.save_project_manager)
            d.view.series_modified.connect(
                self.on_project_navigator_series_modified
            )
            d.view.open_scan.connect(self.on_project_navigator_open_scan)
            self._project_navigator_dialog = d

        self._project_navigator_dialog.show()

    def on_project_navigator_series_modified(self, series: Series):
        if series is self.series:
            # Reload the series
            prev_scan_number = self.scan_num
            self.load_series(series)

            # Set the scan number
            self.scan_num = prev_scan_number
            self.on_frame_changed()
            self.set_mapping_dialogs_stale()

    def on_project_navigator_open_scan(self, scan: Scan):
        series = scan.parent
        if series is None:
            raise Exception('Scan does not have a parent')

        # Load the series
        self.load_series(series)

        # Hide the project navigator dialog
        self._project_navigator_dialog.hide()

        # Set the scan number
        self.scan_num = scan.number
        self.on_frame_changed()
        self.set_mapping_dialogs_stale()

    def save_project_manager(self):
        save_project_manager(self.project_manager)

    def reset_image_view_settings(self):
        self.image_view.auto_level_colors()
        self.image_view.auto_level_histogram_range()
        self.image_view.autoRange()

    def on_shift_scan_number(self, i: int):
        """Shift the scan number by `i`"""
        if self.series is None:
            # No series. Skip it.
            return

        new_scan_idx = self.scan_num + i
        if new_scan_idx in self.series.scan_range:
            # Just change the scan number
            self.scan_num = new_scan_idx
            self.on_series_or_scan_changed()
            self.on_frame_changed()
            return

        # See if we have a parent section, and switch to a different
        # series if we can.
        section = self.series.parent
        if section is None:
            # Just return - can't do anything
            return

        new_series = section.series_with_scan_index(new_scan_idx)
        if new_series is None:
            # Just return - can't do anything
            return

        self.scan_num = new_scan_idx

        # Load this series without resetting the settings
        self.load_series(new_series, reset_settings=False)
        self.scan_num = new_scan_idx
        self.on_series_or_scan_changed()
        self.on_frame_changed()

    def on_shift_scan_position(self, i: int, j: int):
        """Shift the scan position by `i` rows and `j` columns"""
        if self.series is None:
            # No series. Skip it.
            return

        # Clip it so we don't go out of bounds
        scan_pos = np.clip(
            self.scan_pos + (i, j),
            a_min=[0, 0],
            a_max=np.asarray(self.series.scan_shape) - 1,
        )

        self.on_change_scan_position(scan_pos[0], scan_pos[1])

    def on_change_scan_position(self, i: int, j: int):
        """Change the current scan position to `i` row and `j` column"""
        self.scan_pos = np.array([i, j])

        for dialog in self.region_mapping_dialogs.values():
            dialog.set_scan_position(self.scan_pos[0], self.scan_pos[1])

        self.on_frame_changed()

    def on_frame_changed(self):
        self.load_current_image()
        self.update_info_label()

        # Update the mouse hover info with the new frame
        self.image_view.on_mouse_move()
        self.image_view.update_reflection_overlays()

    def on_series_or_scan_changed(self):
        for dialog in self.region_mapping_dialogs.values():
            dialog.set_series(self.series)
            dialog.set_scan_number(self.scan_num)

    def set_mapping_dialogs_stale(self):
        for dialog in self.region_mapping_dialogs.values():
            dialog.set_stale(True)

    def load_current_image(self):
        filepath, img = self.open_image(
            self.series, self.scan_num, self.scan_pos
        )
        self.ui.setWindowTitle(filepath.name)
        self.image_view.setImage(
            img, autoRange=False, autoLevels=False, autoHistogramRange=False
        )

    def open_image(
        self,
        series: Series,
        scan_number: int,
        scan_position: np.ndarray,
        bounds: Bounds | None = None,
    ):
        filepath = series.filepath(*scan_position, scan_number)
        img = self.image_loader_func(filepath, bounds)

        if (
            self.apply_background_subtraction
            and series.background_image_path_str is not None
        ):
            # This function will cache the background
            background = _load_background_image(
                series.background_image_path_str
            )

            if bounds is not None:
                background = background[
                    bounds[0] : bounds[1],
                    bounds[2] : bounds[3],
                ]

            # Need to cast up, because sometimes the background can
            # have higher values than the image, which results in
            # negative numbers, and most of the data we work with
            # is unsigned, which results in an underflow.
            # Maybe we should convert to a larger signed integer than
            # a float? I'm not sure. We can revisit in the future.
            img = img - background.astype(np.float64)

        return filepath, img

    def update_info_label(self):
        if self.series is None:
            text = ''
        else:
            # Make sure these are native types, or else on Mac and
            # Windows, they might appear as `np.int64(1)`.
            text = (
                f'Scan {int(self.scan_num)}, '
                # Reverse the position to match HPCAT notation
                f'Position {tuple(map(int, self.scan_pos[::-1] + 1))}'
            )

        self.ui.info_label.setText(text)

    def set_icon(self, icon: QIcon):
        self.ui.setWindowIcon(icon)

    def show(self):
        """Show the window"""
        self.ui.show()

    def on_mouse_move_message(self, message: str):
        self.ui.status_bar.showMessage(message)

    def set_current_image_to_series_background(self):
        filepath = self.series.filepath(*self.scan_pos, self.scan_num)
        self.series.background_image_path = filepath

        # Save the project manager so this change will persist
        self.save_project_manager()

        if self.apply_background_subtraction:
            # Same logic now as toggling background subtraction on/off
            self.on_action_apply_background_subtraction_toggled()

    def set_current_image_to_section_background(self):
        filepath = self.series.filepath(*self.scan_pos, self.scan_num)
        section = self.series.parent
        if section is None:
            # Can't do anything
            return

        for series in section.series:
            series.background_image_path = filepath

        # Save the project manager so this change will persist
        self.save_project_manager()

        if self.apply_background_subtraction:
            # Same logic now as toggling background subtraction on/off
            self.on_action_apply_background_subtraction_toggled()

    def open_reflections_editor(self):
        self.reflections_editor.ui.show()

    def on_reflections_changed(self):
        new_reflections = self.reflections_editor.reflections
        self.image_view.reflections = new_reflections

    def on_action_apply_background_subtraction_toggled(self):
        self.load_current_image()
        # We don't want to call self.image_view.autoRange(),
        # so don't call self.reset_image_view_settings() for this.
        self.image_view.auto_level_colors()
        self.image_view.auto_level_histogram_range()
        self.image_view.on_mouse_move()
        self.set_mapping_dialogs_stale()

    def open_mapping_regions_manager(self):
        if not hasattr(self, '_regions_navigator_dialog'):
            d = RegionsNavigatorDialog(
                self.image_view,
                self.roi_manager,
                parent=self.ui,
            )

            d.sigDisplayRoiClicked.connect(self.on_roi_display_clicked)
            d.sigRemoveRoiClicked.connect(self.on_roi_remove_clicked)
            d.sigRoiModified.connect(self.on_roi_modified)

            self._regions_navigator_dialog = d

        self._regions_navigator_dialog.show()

    def begin_prediction_matcher(self):
        selected_file, selected_filter = QFileDialog.getOpenFileName(
            self.ui,
            'Open Reflections Table for Matching',
            None,
            'CSV files (*.csv)',
        )

        if not selected_file:
            # We cannot continue
            return

        array = np.loadtxt(selected_file, delimiter=',', skiprows=1)

        # Validate that there are 9 columns
        if array.shape[1] != 9:
            msg = (
                'Expected 9 columns in CSV file, but only found '
                f'{array.shape[1]}. Columns are as follows: '
                'x (predicted),y (predicted),h,k,l,Energy (keV),'
                'First Order,Last Order,d (Å)'
            )
            QMessageBox.critical(self.ui, 'Invalid CSV File', msg)
            return

        # Now figure out what crystal ID should be used.
        num_crystals = self.image_view.reflections.num_crystals
        crystal_id, accepted = QInputDialog.getInt(
            self.ui,
            'Select Crystal ID',
            'Select the Crystal ID associated with these reflections',
            value=0,
            minValue=0,
            maxValue=num_crystals - 1,
        )
        if not accepted:
            # User canceled
            return

        if hasattr(self, '_prediction_matcher_dialog'):
            self._prediction_matcher_dialog.disconnect()
            self._prediction_matcher_dialog.hide()
            self._prediction_matcher_dialog = None

        d = PredictionMatcherDialog(
            self.image_view, array, crystal_id, self.ui
        )
        d.run()

        self._prediction_matcher_dialog = d

    def on_reflections_style_changed(self):
        new_style = self.reflections_editor.style
        self.image_view.reflections_style = new_style

    def begin_select_indexing_points(self):
        if self.series is None:
            msg = 'A series must be loaded to select indexing points'
            QMessageBox.warning(self.ui, 'No Series Loaded', msg)
            return

        if hasattr(self, '_point_selector_dialog'):
            self._point_selector_dialog.on_finished()

        d = PointSelectorDialog(
            self.image_view,
            window_title='Select Points',
            parent=self.ui,
        )
        d.show()
        d.accepted.connect(self.select_indexing_points_accepted)

        self._point_selector_dialog = d

    def select_indexing_points_accepted(self):
        # Get the points
        d = self._point_selector_dialog
        if not d.points:
            # No points, just return
            return

        project = self.series.parent.parent
        project_dir = project.directory

        filename = d.filename
        select_file_manually = (
            filename is None
            or not project_dir
            or not Path(project_dir).exists()
        )
        if not select_file_manually:
            path = Path(project_dir) / filename
            if path.exists():
                msg = f'"{path}"\nAlready exists. Overwrite?'
                if (
                    QMessageBox.question(self.ui, 'File exists', msg)
                    == QMessageBox.No
                ):
                    # Force the file to be selected manually.
                    select_file_manually = True

        if select_file_manually:
            if not project_dir or not Path(project_dir).exists():
                msg = (
                    f'Project directory for "{project.name}" does not '
                    'exist. It may be set in the Project Navigator.\n\n'
                    'You must specify the save file path manually.'
                )
                QMessageBox.warning(self.ui, 'No Project Directory', msg)

            # Get the user to specify
            path, _ = QFileDialog.getSaveFileName(
                self.ui,
                'Save Indexing Points',
                str(project_dir),
                'xy files (*.xy)',
            )

            if not path:
                # User canceled
                return

        points = np.asarray(d.points)
        np.savetxt(path, points, fmt='%8.3f')
        if not select_file_manually:
            # Tell the user where it was saved
            msg = f'File saved to:\n{path}'
            QMessageBox.information(self.ui, 'File Saved', msg)

    def on_roi_remove_clicked(self, id: str):
        if id in self.region_mapping_dialogs:
            dialog = self.region_mapping_dialogs[id]
            dialog.setParent(None)
            del self.region_mapping_dialogs[id]

        # Reset mapping highlight and domain regions if the last roi has been removed
        if len(self.region_mapping_dialogs) == 0:
            self.mapping_domain_area = None
            self.mapping_highlight_area = None

    def on_roi_display_clicked(self, id: str):
        # Initialize mapping highlight and domain regions the first time a mapping is shown
        if len(self.region_mapping_dialogs) == 0:
            # # Initial mapping domain target is a 5x5 square in scan position
            # # space centered around the current scan position
            # target_size = 5
            # half_target_size = target_size // 2

            # pos = np.clip(
            #     self.scan_pos - half_target_size,
            #     a_min=[0, 0],
            #     a_max=np.asarray(self.series.scan_shape) - target_size,
            # )

            # size = np.clip(
            #     np.array((target_size, target_size)),
            #     a_min=[0, 0],
            #     a_max=np.asarray(self.series.scan_shape) - pos,
            # )

            # To set the default size to be the scan shape, do this:
            pos = np.array((0, 0))
            size = np.array(self.series.scan_shape)

            self.mapping_domain_area = {"position": pos, "size": size}
            self.mapping_highlight_area = {
                "position": self.scan_pos,
                "size": np.array((1, 1)),
            }

        if id in self.region_mapping_dialogs:
            dialog = self.region_mapping_dialogs[id]
        else:
            dialog = RegionMappingDialog(id, self.roi_manager, self.ui)
            histogram_widget = self.image_view.getHistogramWidget()

            if histogram_widget:
                dialog.link_levels_and_lookuptable(histogram_widget.item)

            dialog.open_image_fn = self.open_image
            dialog.set_series(self.series)
            dialog.set_scan_number(self.scan_num)
            dialog.set_scan_position(self.scan_pos[0], self.scan_pos[1])
            dialog.set_domain_roi(self.mapping_domain_area)
            dialog.set_highlight_roi(self.mapping_highlight_area)
            dialog.set_show_domain(self.show_mapping_domain_area)
            dialog.set_show_highlight(self.show_mapping_highlight_area)
            dialog.set_stale(True)

            dialog.change_scan_position.connect(self.on_change_scan_position)
            dialog.shift_scan_number.connect(self.on_shift_scan_number)
            dialog.shift_scan_position.connect(self.on_shift_scan_position)
            dialog.sigMappingDomainChanged.connect(
                self.on_mapping_domain_changed
            )
            dialog.sigMappingHighlightChanged.connect(
                self.on_mapping_highlight_changed
            )
            dialog.sigShowDomainChanged.connect(self.on_show_domain_changed)
            dialog.sigShowHighlightChanged.connect(
                self.on_show_highlight_changed
            )

            self.region_mapping_dialogs[id] = dialog

        dialog.show()

    def on_roi_modified(self, id: str):
        if id in self.region_mapping_dialogs:
            dialog = self.region_mapping_dialogs[id]
            dialog.set_stale(True)

    def on_mapping_domain_changed(
        self, i: int, j: int, size_i: int, size_j: int
    ):
        self.mapping_domain_area = {
            "position": np.array((i, j)),
            "size": np.array((size_i, size_j)),
        }
        for dialog in self.region_mapping_dialogs.values():
            dialog.set_domain_roi(self.mapping_domain_area)

    def on_mapping_highlight_changed(
        self, i: int, j: int, size_i: int, size_j: int
    ):
        self.mapping_highlight_area = {
            "position": np.array((i, j)),
            "size": np.array((size_i, size_j)),
        }
        for dialog in self.region_mapping_dialogs.values():
            dialog.set_highlight_roi(self.mapping_highlight_area)

    def on_show_domain_changed(self, show: bool):
        self.show_mapping_domain_area = show
        for dialog in self.region_mapping_dialogs.values():
            dialog.set_show_domain(self.show_mapping_domain_area)

    def on_show_highlight_changed(self, show: bool):
        self.show_mapping_highlight_area = show
        for dialog in self.region_mapping_dialogs.values():
            dialog.set_show_highlight(self.show_mapping_highlight_area)


# We probably only need to cache one background image, but since they are
# small, just cache 2...
@lru_cache(maxsize=2)
def _load_background_image(path: str):
    return load_image_file(path)
