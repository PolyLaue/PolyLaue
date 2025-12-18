# Copyright © 2025, UChicago Argonne, LLC. See "LICENSE" for full details.

# This is available from Python 3.8
from importlib.metadata import version, PackageNotFoundError


def get_version(package_name: str) -> str | None:
    try:
        return version(package_name)
    except PackageNotFoundError:
        # package is not installed
        return None
