# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from polylaue.model.project_manager import ProjectManager


def test_deserialize(test_project_manager_serialized):
    serialized = test_project_manager_serialized
    pm = ProjectManager.from_serialized(serialized)

    # Now just check a few things to be sure it happened correctly
    assert len(pm.projects) == len(serialized['projects_serialized'])
    for i, project in enumerate(pm.projects):
        serialized_project = serialized['projects_serialized'][i]
        assert project.name == serialized_project['name']
        assert project.description == serialized_project['description']
        assert len(project.sections) == len(
            serialized_project['sections_serialized']
        )

        for j, section in enumerate(project.sections):
            serialized_section = serialized_project['sections_serialized'][j]
            assert section.name == serialized_section['name']
            assert section.description == serialized_section['description']
            assert len(section.series) == len(
                serialized_section['series_serialized']
            )
            for k, series in enumerate(section.series):
                serialized_series = serialized_section['series_serialized'][k]
                assert series.name == serialized_series['name']


def test_serialize(test_project_manager_serialized):
    ref_serialized = test_project_manager_serialized
    pm = ProjectManager.from_serialized(ref_serialized)

    # Verify that the round trip produces the same result
    serialized = pm.serialize()
    assert ref_serialized == serialized
