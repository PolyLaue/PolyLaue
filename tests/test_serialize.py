# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

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

    # Verify that everything present within the reference matches
    # This won't fail when we add new keys (because only keys
    # that already exist in the reference are checked).
    def recurse_check(d: dict, ref: dict):
        for key, value in ref.items():
            if isinstance(value, dict) and key in d:
                recurse_check(d[key], value)
                continue

            if isinstance(value, (list, tuple)) and key in d:
                assert len(value) == len(d[key])
                for v1, v2 in zip(value, d[key]):
                    if isinstance(v1, dict):
                        recurse_check(v1, v2)
                        continue

                    assert v1 == v2

                continue

            if key in d:
                assert d[key] == value

    serialized = pm.serialize()
    recurse_check(serialized, ref_serialized)
