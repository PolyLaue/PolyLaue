# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

import numpy as np
import pytest

from polylaue.model.core.geometry import (
    geo_from_dioptas,
    parse_poni,
    write_geometry_file,
)
from polylaue.model.editable import ValidationError
from polylaue.model.project import Project
from polylaue.model.project_manager import ProjectManager

# A classic PONI file
PONI_V1 = """\
# Nota: C-Order, 1 refers to the Y axis, 2 to the X axis
PixelSize1: 7.9e-05
PixelSize2: 7.9e-05
Distance: 0.19
Poni1: 0.041
Poni2: 0.0405
Rot1: 0.002
Rot2: -0.003
Wavelength: 3e-11
"""

# A PONI file where the pixel size is in the detector config
PONI_V2 = """\
poni_version: 2.1
Detector: Detector
Detector_config: {"pixel1": 7.9e-05, "pixel2": 7.9e-05, "max_shape": [1043, 981]}
Distance: 0.19
Poni1: 0.041
Poni2: 0.0405
Rot1: 0.002
Rot2: -0.003
"""

EXPECTED_PARAMS = {
    'pixel_size': 0.079,
    'detector_distance': 190.0,
    'poni1': 0.041,
    'poni2': 0.0405,
    'rot1': 0.002,
    'rot2': -0.003,
}


@pytest.mark.parametrize('content', [PONI_V1, PONI_V2])
def test_parse_poni(content, tmp_path):
    poni_path = tmp_path / 'test.poni'
    poni_path.write_text(content)

    params = parse_poni(poni_path)
    assert params.keys() == EXPECTED_PARAMS.keys()
    for k, v in EXPECTED_PARAMS.items():
        assert np.isclose(params[k], v)


def test_parse_poni_unknown_format(tmp_path):
    poni_path = tmp_path / 'test.poni'
    poni_path.write_text('Distance: 0.19\nPoni1: 0.041\n')

    with pytest.raises(ValueError, match='Unknown PONI format'):
        parse_poni(poni_path)

    # The old-style conversion function reports this as a string
    output_path = tmp_path / 'geometry.npz'
    result = geo_from_dioptas(poni_path, output_path, 981, 1043, 0.01)
    assert result == '...Error! Unknown format'
    assert not output_path.exists()


def test_write_geometry_file(tmp_path):
    output_path = tmp_path / 'geometry.npz'
    image_size_x = 981
    image_size_y = 1043
    white_beam_shift = 0.01

    write_geometry_file(
        output_path,
        image_size_x=image_size_x,
        image_size_y=image_size_y,
        white_beam_shift=white_beam_shift,
        **EXPECTED_PARAMS,
    )

    npz = np.load(output_path)
    assert set(npz.keys()) == {'iitt1', 'iitt2', 'iitt3'}

    det_org = npz['iitt1']
    beam_dir = npz['iitt2']
    pix_dist = npz['iitt3']

    pix = EXPECTED_PARAMS['pixel_size']
    expected_det_org = [
        EXPECTED_PARAMS['poni2'] * 1000.0 / pix,
        image_size_y - EXPECTED_PARAMS['poni1'] * 1000.0 / pix + white_beam_shift / pix,
    ]
    assert np.allclose(det_org, expected_det_org)

    # The beam direction is a unit vector, mostly along z
    assert np.isclose(np.linalg.norm(beam_dir), 1.0)
    assert beam_dir[2] > 0.99

    assert np.isclose(pix_dist[0], pix)
    assert np.isclose(pix_dist[1], EXPECTED_PARAMS['detector_distance'])
    # The largest two-theta and the smallest z of the frame corner
    # directions are both angles-related quantities in sane ranges
    assert 0 < pix_dist[2] < np.pi / 2
    assert 0 < pix_dist[3] < 1


def test_project_poni_import(tmp_path):
    poni_path = tmp_path / 'test.poni'
    poni_path.write_text(PONI_V1)

    project_dir = tmp_path / 'project'
    project_dir.mkdir()

    pm = ProjectManager()
    project = Project(
        parent=pm,
        name='P',
        directory=project_dir,
        frame_shape=(981, 1043),
    )
    pm.projects.append(project)

    # Setting the geometry path to a PONI file converts it in place
    project.geometry_path_str = str(poni_path)
    assert project.geometry_path == project_dir / 'geometry.npz'

    data = project.geometry_data
    assert set(data.keys()) == {'det_org', 'beam_dir', 'pix_dist'}
    assert np.isclose(data['pix_dist'][0], EXPECTED_PARAMS['pixel_size'])

    # The parsed parameters are recorded so the UI can offer a review
    params = project.last_poni_import_params
    assert params is not None
    for k, v in EXPECTED_PARAMS.items():
        assert np.isclose(params[k], v)

    # Setting an NPZ geometry clears the record
    npz_path = tmp_path / 'other.npz'
    npz_path.write_bytes(project.expected_geometry_file_path.read_bytes())
    project.geometry_path_str = str(npz_path)
    assert project.last_poni_import_params is None


def test_project_poni_validation(tmp_path):
    pm = ProjectManager()
    project = Project(parent=pm, name='P', directory=tmp_path)
    pm.projects.append(project)

    params = project.get_parameters()

    # A malformed PONI file fails validation with a friendly error,
    # instead of raising while the parameters are applied
    bad_poni = tmp_path / 'bad.poni'
    bad_poni.write_text('Distance: 0.19\n')
    params['geometry_path_str'] = str(bad_poni)
    with pytest.raises(ValidationError, match='Unknown PONI format'):
        project.validate_parameters(params)

    # A valid PONI file passes
    good_poni = tmp_path / 'good.poni'
    good_poni.write_text(PONI_V1)
    params['geometry_path_str'] = str(good_poni)
    project.validate_parameters(params)


def test_geo_from_dioptas_roundtrip(tmp_path):
    poni_path = tmp_path / 'test.poni'
    poni_path.write_text(PONI_V1)
    output_path = tmp_path / 'geometry.npz'

    geo_from_dioptas(poni_path, output_path, 981, 1043, 0.01)

    npz = np.load(output_path)
    assert set(npz.keys()) == {'iitt1', 'iitt2', 'iitt3'}
