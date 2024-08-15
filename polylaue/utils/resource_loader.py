# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from contextlib import contextmanager
from importlib.resources import (  # noqa
    as_file,
    files,
    read_binary,  # these may be imported elsewhere
    read_text,  # these may be imported elsewhere
)
from pathlib import Path
from types import ModuleType
from typing import ContextManager


@contextmanager
def filepath(module: ModuleType, name: str) -> ContextManager[Path]:
    """Provide a filepath for reading the resource

    The filepath will be temporary if the resource was extracted from
    a zip file (but I am not sure if we would ever do this).
    """
    with as_file(files(module).joinpath(name)) as path:
        yield path
