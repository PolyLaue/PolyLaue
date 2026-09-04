# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

from PySide6.QtWidgets import QWidget

from polylaue.model.core.geometry import DEFAULT_DETECTOR_SETUP, DETECTOR_SETUPS
from polylaue.model.editable import Editable, ParameterDescription
from polylaue.model.project import Project
from polylaue.ui.editor import EditorDialog


class PoniGeometry(Editable):
    """The geometry parameters parsed from a PONI file

    These can be edited by the user before the geometry file is written.
    """

    def __init__(
        self,
        pixel_size: float,
        detector_distance: float,
        poni1: float,
        poni2: float,
        rot1: float,
        rot2: float,
        detector_setup: str = DEFAULT_DETECTOR_SETUP,
    ):
        super().__init__()

        self.detector_setup = detector_setup
        self.pixel_size = pixel_size
        self.detector_distance = detector_distance
        self.poni1 = poni1
        self.poni2 = poni2
        self.rot1 = rot1
        self.rot2 = rot2

    @classmethod
    def get_parameters_description(cls) -> dict[str, ParameterDescription]:
        return {
            'detector_setup': {
                'type': 'enum',
                'label': 'Detector Setup',
                'options': list(DETECTOR_SETUPS),
                'tooltip': (
                    'The HPCAT setup that was used to collect the data. '
                    'The setups differ in how the white beam shift is '
                    'applied to the point of normal incidence.'
                ),
            },
            'pixel_size': {
                'type': 'float',
                'label': 'Pixel Size (mm)',
                'min': 1e-16,
                'max': float('inf'),
                'tooltip': 'The size of a detector pixel, in mm',
            },
            'detector_distance': {
                'type': 'float',
                'label': 'Sample-Detector Distance (mm)',
                'min': 1e-16,
                'max': float('inf'),
                'tooltip': 'The sample to detector distance, in mm',
            },
            'poni1': {
                'type': 'float',
                'label': 'Poni1 (m)',
                'min': float('-inf'),
                'max': float('inf'),
                'tooltip': (
                    'The coordinate of the point of normal incidence '
                    'along the detector\'s slow dimension, in meters'
                ),
            },
            'poni2': {
                'type': 'float',
                'label': 'Poni2 (m)',
                'min': float('-inf'),
                'max': float('inf'),
                'tooltip': (
                    'The coordinate of the point of normal incidence '
                    'along the detector\'s fast dimension, in meters'
                ),
            },
            'rot1': {
                'type': 'float',
                'label': 'Rot1 (rad)',
                'min': float('-inf'),
                'max': float('inf'),
                'tooltip': 'The first detector rotation, in radians',
            },
            'rot2': {
                'type': 'float',
                'label': 'Rot2 (rad)',
                'min': float('-inf'),
                'max': float('inf'),
                'tooltip': 'The second detector rotation, in radians',
            },
        }

    def write_geometry_file(self, project: Project):
        """Write the geometry to the project's geometry file location"""
        params = self.get_parameters()
        detector_setup = params.pop('detector_setup')
        project.write_poni_geometry(params, detector_setup)


def review_poni_import(project: Project, parent: QWidget | None = None):
    """Let the user review and edit freshly imported PONI parameters

    If the project does not have freshly imported PONI parameters, this
    does nothing. Otherwise, a dialog with the imported parameters is
    shown. If the user accepts it, the (possibly edited) parameters are
    written to the project's geometry file. If the user cancels it, the
    parameters that were parsed from the PONI file remain in use.
    """
    params = project.last_poni_import_params
    if params is None:
        return

    project.last_poni_import_params = None

    geometry = PoniGeometry(**params)

    dialog = EditorDialog(geometry, parent)
    dialog.setWindowTitle('Imported PONI Geometry')
    if dialog.exec():
        geometry.write_geometry_file(project)
