# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

from __future__ import annotations
import logging
from pathlib import Path
import re
from typing import TYPE_CHECKING

import numpy as np

from polylaue.model.editable import Editable, ParameterDescription
from polylaue.model.io import get_file_creation_time
from polylaue.model.scan import Scan
from polylaue.model.serializable import ValidationError
from polylaue.typing import PathLike

if TYPE_CHECKING:
    from polylaue.model.section import Section


logger = logging.getLogger(__name__)

# The image file regular expression
# Put the number in its own group.
IMAGE_FILE_SUFFIX_REGEX = r'_(\d+)\.(tiff?|cbf)$'


class Series(Editable):
    """The Series class is used to keep track of files within a series

    Several arguments are provided, including the directory path,
    scan range (end-inclusive), scan shape, and a number of frames
    to skip.

    The Series will automatically identify the series files within
    the directory, validate that the file indices and number of files
    match what is expected (based upon the number of scans, scan shape,
    and number of frames to skip), and provide a way to obtain a
    numpy array from a particular scan number, row, and column.
    """

    def __init__(
        self,
        parent: Section,
        name='Series',
        description='Description',
        dirpath: PathLike = '.',
        scans: list[Scan] | None = None,
        scan_start_number: int | None = None,
        scan_shape: tuple[int, int] | None = None,
        skip_frames: int | None = None,
        background_image_path: PathLike | None = None,
        file_prefix: str | None = None,
    ):
        super().__init__()

        if scans is None:
            # Use the same number of scans as the last series, if possible.
            if parent.series:
                scans = [
                    Scan(self) for _ in range(parent.series[-1].num_scans)
                ]
            else:
                # Default to 1 scan
                scans = [Scan(self)]

        if scan_start_number is None:
            # Try to default to the next valid scan number in this section.
            # Otherwise, default to 1.
            if parent.series:
                scan_start_number = parent.series[-1].scan_range_tuple[1] + 1
            else:
                scan_start_number = 1

        if scan_shape is None:
            # Copy the scan shape from the most recent scan, if one is
            # available. Otherwise, default to (21, 21).
            if parent.series:
                scan_shape = parent.series[-1].scan_shape
            else:
                scan_shape = (21, 21)

        if skip_frames is None:
            # Copy from the most recent scan, if one is available.
            if parent.series:
                skip_frames = parent.series[-1].skip_frames
            else:
                skip_frames = 10

        self.name = name
        self.description = description
        self.dirpath = dirpath
        self.scans = scans
        self.scan_start_number = scan_start_number
        self.scan_shape = scan_shape
        self.skip_frames = skip_frames
        self.background_image_path = background_image_path
        self.has_final_dark_file = False
        self.file_prefix = file_prefix
        self.file_list = []
        self.parent = parent

    @property
    def path_from_root(self) -> list[int]:
        index = self.parent.series.index(self)
        return self.parent.path_from_root + [index]

    def filepath(self, row: int, column: int, scan_number: int = 1) -> Path:
        """Get the filepath for a specified, row, column, and scan_number"""
        if row >= self.scan_shape[0]:
            msg = f'Row "{row}" is out of bounds'
            raise ValidationError(msg)

        if column >= self.scan_shape[1]:
            msg = f'Column "{column}" is out of bounds'
            raise ValidationError(msg)

        if scan_number not in self.scan_range:
            msg = (
                f'Scan number "{scan_number}" is not in this '
                f'series\' scan range: "{self.scan_range_tuple}"'
            )
            raise ValidationError(msg)

        scan_number_idx = self.scan_range.index(scan_number)
        scan_start = scan_number_idx * np.prod(self.scan_shape)
        idx = scan_start + row * self.scan_shape[1] + column
        filename = self.file_list[idx]

        return self.dirpath / filename

    def scan_number(self, scan: Scan) -> int:
        # Get the number of the provided scan
        if scan not in self.scans:
            return -1

        return self.scan_start_number + self.scans.index(scan)

    @property
    def scan_range(self) -> range:
        """Return a Python range representing the scan range"""
        start, stop = self.scan_range_tuple
        return range(start, stop + 1)

    @property
    def scan_range_tuple(self) -> tuple[int, int]:
        """Returns [start, stop] (both inclusive)"""
        if not self.scans:
            raise Exception('No scans')

        return (
            self.scan_start_number,
            self.scan_start_number + self.num_scans - 1,
        )

    @scan_range_tuple.setter
    def scan_range_tuple(self, v: tuple[int, int]):
        # Update the scan start number and the scans list
        # to reflect the scan range tuple provided.
        self.scan_start_number = v[0]
        num_scans = v[1] - v[0] + 1

        while self.num_scans < num_scans:
            self.scans.append(Scan(self))

        while self.num_scans > num_scans:
            self.scans.pop()

    @property
    def scan_range_formatted(self):
        return ' - '.join(map(str, self.scan_range_tuple))

    @property
    def num_scans(self):
        return len(self.scans)

    @property
    def scan_shape_reversed(self) -> tuple[int, int]:
        """Get the scan shape in the user-facing, HPCAT convention"""
        return self.scan_shape[::-1]

    @scan_shape_reversed.setter
    def scan_shape_reversed(self, v: tuple[int, int]):
        """Set the scan shape in the user-facing, HPCAT convention"""
        self.scan_shape = v[::-1]

    @staticmethod
    def identify_file_prefix(dirpath: Path):
        """Inspect the tif files and identify the file template"""

        regex = re.compile(IMAGE_FILE_SUFFIX_REGEX, re.IGNORECASE)

        # Find all prefixes that match the regex.
        # We will choose the prefix with the most files.
        # The key is the prefix, the value is the number of files that match.
        prefix_counts = {}
        for path in dirpath.iterdir():
            if not path.is_file():
                continue

            name = path.name
            if result := re.search(regex, name):
                prefix = name[: result.start()]
                prefix_counts.setdefault(prefix, 0)
                prefix_counts[prefix] += 1

        if not prefix_counts:
            msg = (
                f'In series dirpath "{dirpath}", failed to find image '
                f'file matching regular expression: "{regex}"'
            )
            raise ValidationError(msg)

        # Select the prefix with the most counts
        prefixes = list(prefix_counts)
        counts = list(prefix_counts.values())
        selected_prefix = prefixes[np.argmax(counts)]

        logger.debug(
            f'For series with dirpath "{dirpath}", file prefix was '
            f'identified to be {selected_prefix}'
        )
        return selected_prefix

    @staticmethod
    def generate_file_list(dirpath: Path, skip_frames: int):
        """Generate a list of files ordered by their index

        We will index into this file list to obtain the file
        name for that index.
        """
        file_prefix = Series.identify_file_prefix(dirpath)

        file_dict = {}

        # Identify all files that match the full regex
        full_regex = re.compile(
            file_prefix + IMAGE_FILE_SUFFIX_REGEX, re.IGNORECASE
        )

        # Start after the number of frames to skip
        start_idx = skip_frames + 1

        for path in dirpath.iterdir():
            if not path.is_file():
                continue

            name = path.name
            if result := re.search(full_regex, name):
                idx = int(result.groups()[0])
                if idx < start_idx:
                    # Ignore skip frames.
                    continue

                file_dict[idx] = name

        indices = sorted(list(file_dict))

        # The indices should be continuous from the start to the max.
        # Verify this.
        verify_indices = np.arange(start_idx, indices[-1] + 1)
        if not np.array_equal(indices, verify_indices):
            missing = set(verify_indices) - set(indices)
            extra = set(indices) - set(verify_indices)
            msg = (
                f'Files with prefix "{file_prefix}" are not continuous '
                f'from "{start_idx}" to "{indices[-1]}"'
            )
            if missing:
                msg += f'\nMissing indices: {list(missing)}'

            if extra:
                msg += f'\nExtra indices: {list(extra)}'

            raise ValidationError(msg)

        file_list = [file_dict[i] for i in indices]

        logger.debug(
            f'For series with dirpath "{dirpath}", found '
            f'{len(file_list)} files'
        )

        return file_prefix, file_list

    @property
    def has_enough_data_for_new_scan(self) -> bool:
        # Check if there are enough data files present for a new scan.
        # This needs to be fast because we will check it multiple times each
        # second during acquisition.
        prefix = self.file_prefix
        if not prefix or not self.file_list:
            return False

        # Assume that we will use the same file extension as the other files
        last_file = self.file_list[-1]
        suffix = Path(last_file).suffix

        # We make assumptions here about the file name pattern that we don't
        # exactly make elsewhere. We assume it has enough leading zeroes to
        # always contain at least 3 digits, which is true for the data we
        # are currently looking at, but might not always be true.
        final_file_idx = self.skip_frames + (self.num_scans + 1) * np.prod(
            self.scan_shape
        )

        filename = f'{prefix}_{final_file_idx:03d}{suffix}'
        return (self.dirpath / filename).exists()

    def invalidate(self):
        self.file_prefix = None
        self.file_list.clear()
        self.has_final_dark_file = False

    def validate_files(
        self,
        dirpath_str,
        skip_frames,
        scan_shape,
        scan_range_tuple,
        dry=False,
        check_dark_file=True,
    ):
        dirpath = Path(dirpath_str)
        file_prefix, file_list = self.generate_file_list(dirpath, skip_frames)
        num_files = len(file_list)

        num_scans = scan_range_tuple[1] - scan_range_tuple[0] + 1
        num_frames = num_scans * np.prod(scan_shape)

        expected_num_files = num_frames

        has_final_dark_file = False

        # The number of files should be equal to
        if check_dark_file and num_files == expected_num_files + 1:
            # Assume the extra file is the final dark file
            has_final_dark_file = True
            logger.debug(
                f'For series at "{dirpath}", assuming final file is a '
                'dark file'
            )
        elif num_files < expected_num_files:
            msg = (
                f'For series at "{dirpath}", number of unskipped files '
                f'"{num_files}" does not match the '
                f'expected number of files "{expected_num_files}", '
                'which was computed based upon the number of scans '
                f'({num_scans}) and the scan shape ({scan_shape}).'
            )
            raise ValidationError(msg)

        if not dry:
            self.file_prefix = file_prefix
            self.file_list = file_list
            self.has_final_dark_file = has_final_dark_file

    def self_validate(self, check_dark_file=True):
        self.validate_files(
            self.dirpath_str,
            self.skip_frames,
            self.scan_shape,
            self.scan_range_tuple,
            dry=False,  # Apply internal attributes
            check_dark_file=check_dark_file,
        )

    def validate_parameters(self, params):
        # Superficial validation of the parameters
        # (they exists, they are tuples, etc)
        super().validate_parameters(params)

        # Make sure the parameters are self-consistent
        self.validate_files(
            params['dirpath_str'],
            params['skip_frames'],
            params['scan_shape_reversed'],
            params['scan_range_tuple'],
            dry=True,  # Don't change any attributes on self
        )

    def set_parameters(self, params: dict, validate: bool = True):
        super().set_parameters(params, validate)

        if self.name == 'Series':
            # If the series name is the default of 'Series', update the name to
            # the name of the directory.
            self.name = self.dirpath.name

        # Parameters have been already validated and assigned as attribute to
        # self. Assign derived attributes
        self.self_validate()

    @property
    def dirpath(self) -> Path:
        return self._dirpath

    @dirpath.setter
    def dirpath(self, v: PathLike):
        self._dirpath = Path(v).resolve()

    @property
    def dirpath_str(self) -> str:
        return str(self.dirpath)

    @dirpath_str.setter
    def dirpath_str(self, v: str):
        self.dirpath = v

    @property
    def background_image_path(self) -> Path | None:
        return self._background_image_path

    @background_image_path.setter
    def background_image_path(self, v: PathLike | None):
        if v is not None:
            v = Path(v).resolve()

        self._background_image_path = v

    @property
    def background_image_path_str(self) -> str | None:
        p = self.background_image_path
        return str(p) if p is not None else None

    @background_image_path_str.setter
    def background_image_path_str(self, v: str | None):
        if v is not None and v.strip() == '':
            v = None

        self.background_image_path = v

    # Serialization code
    _attrs_to_serialize = [
        'name',
        'description',
        'dirpath_str',
        'scan_start_number',
        'scan_shape',
        'scans_serialized',
        'skip_frames',
        'file_prefix',
        'background_image_path_str',
    ]

    @property
    def scans_serialized(self) -> list[dict]:
        return [x.serialize() for x in self.scans]

    @scans_serialized.setter
    def scans_serialized(self, v: list[dict]):
        self.scans = [Scan.from_serialized(x, parent=self) for x in v]

    def deserialize(self, d: dict):
        self.invalidate()
        super().deserialize(d)

    def relative_file_creation_time(
        self, row: int, column: int, scan_number: int
    ) -> float:
        # Get the file creation time relative to the creation time
        # of the very first file in the first series of this section.
        # The number returned is in fractional seconds.
        first_series = self.parent.series[0]
        if not first_series.file_list:
            # File list must be generated
            first_series.self_validate()

        first_path = first_series.dirpath / first_series.file_list[0]
        t1 = get_file_creation_time(first_path)

        this_path = self.filepath(row, column, scan_number)
        t2 = get_file_creation_time(this_path)

        return t2 - t1

    # Editable fields
    @classmethod
    def get_parameters_description(cls) -> dict[str, ParameterDescription]:
        return {
            'name': {
                'type': 'string',
                'label': 'Name',
                'min': 1,
                'tooltip': 'The name of the series (must be unique)',
            },
            'description': {
                'type': 'string',
                'label': 'Description',
                'required': False,
                'tooltip': 'A description for personal records',
            },
            'dirpath_str': {
                'type': 'folder',
                'label': 'Directory',
                'tooltip': (
                    'Directory containing the images within this series.\n\n'
                    'The contents of the directory will be validated, '
                    'including verifying the expected number of images,\n'
                    'which is computed via the other settings in this dialog.'
                ),
            },
            'scan_shape_reversed': {
                'type': 'tuple',
                'subtype': 'integer',
                'label': 'Scan shape',
                'tooltip': 'Shape of the scans within this series',
                'min': 0,
                'max': 10000000,
            },
            'scan_range_tuple': {
                'type': 'tuple',
                'subtype': 'integer',
                'label': 'Scan range',
                'tooltip': 'Range of scan numbers in this series (inclusive)',
                'min': 0,
                'max': 10000000,
            },
            'skip_frames': {
                'type': 'integer',
                'label': 'Skip frames',
                'tooltip': (
                    'How many frames to skip from the beginning of the '
                    'series (usually invalid or background frames).'
                ),
                'min': 0,
                'max': 10000000,
            },
            'background_image_path_str': {
                'type': 'file',
                'label': 'Background image',
                'required': False,
                'tooltip': (
                    'Image file for performing background subtraction.\n\n'
                    'This may be selected automatically by right-clicking '
                    'an image in the application and selecting '
                    '"set as background".'
                ),
            },
        }
