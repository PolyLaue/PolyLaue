# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

import logging
from pathlib import Path
import re

import numpy as np

from polylaue.model.scan import Scan
from polylaue.model.serializable import Serializable
from polylaue.typing import PathLike

logger = logging.getLogger(__name__)

# The image file regular expression
# Put the number in its own group.
IMAGE_FILE_SUFFIX_REGEX = r'_(\d+)\.(tiff?|cbf)$'


class Series(Serializable):
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
        name='Series',
        description='Description',
        dirpath: PathLike = '.',
        scans: list[Scan] | None = None,
        scan_start_number: int = 1,
        scan_shape: tuple[int, int] = (21, 21),
        skip_frames: int = 10,
        file_prefix: str | None = None,
        parent: Serializable | None = None,
    ):
        if scans is None:
            # Default to 3 scans
            scans = [Scan(parent=self) for _ in range(3)]

        self.name = name
        self.description = description
        self.dirpath = dirpath
        self.scans = scans
        self.scan_start_number = scan_start_number
        self.scan_shape = scan_shape
        self.skip_frames = skip_frames
        self.has_final_dark_file = False
        self.file_prefix = file_prefix
        self.file_list = []
        self.parent = parent

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
            self.scans.append(Scan())

        while self.num_scans > num_scans:
            self.scans.pop()

    @property
    def scan_range_formatted(self):
        return ' - '.join(map(str, self.scan_range_tuple))

    @property
    def num_scans(self):
        return len(self.scans)

    def identify_file_prefix(self):
        """Inspect the tif files and identify the file template"""

        regex = re.compile(IMAGE_FILE_SUFFIX_REGEX, re.IGNORECASE)

        # Find all prefixes that match the regex.
        # We will choose the prefix with the most files.
        # The key is the prefix, the value is the number of files that match.
        prefix_counts = {}
        for path in self.dirpath.iterdir():
            if not path.is_file():
                continue

            name = path.name
            if result := re.search(regex, name):
                prefix = name[: result.start()]
                prefix_counts.setdefault(prefix, 0)
                prefix_counts[prefix] += 1

        if not prefix_counts:
            msg = (
                f'In series dirpath "{self.dirpath}", failed to find image '
                f'file matching regular expression: "{regex}"'
            )
            raise ValidationError(msg)

        # Select the prefix with the most counts
        prefixes = list(prefix_counts)
        counts = list(prefix_counts.values())
        selected_prefix = prefixes[np.argmax(counts)]

        logger.debug(
            f'For series with dirpath "{self.dirpath}", file prefix was '
            f'identified to be {selected_prefix}'
        )
        self.file_prefix = selected_prefix

    def generate_file_list(self):
        """Generate a list of files ordered by their index

        We will index into this file list to obtain the file
        name for that index.
        """
        if self.file_prefix is None:
            # Identify the file prefix automatically, if one was not
            # provided.
            self.identify_file_prefix()

        file_dict = {}

        # Identify all files that match the full regex
        full_regex = re.compile(
            self.file_prefix + IMAGE_FILE_SUFFIX_REGEX, re.IGNORECASE
        )

        # Start after the number of frames to skip
        start_idx = self.skip_frames + 1

        for path in self.dirpath.iterdir():
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
                f'Files with prefix "{self.file_prefix}" are not continuous '
                f'from "{start_idx}" to "{indices[-1]}"'
            )
            if missing:
                msg += f'\nMissing indices: {list(missing)}'

            if extra:
                msg += f'\nExtra indices: {list(extra)}'

            raise ValidationError(msg)

        self.file_list = [file_dict[i] for i in indices]

        logger.debug(
            f'For series with dirpath "{self.dirpath}", found '
            f'{len(self.file_list)} files'
        )

    def invalidate(self):
        self.file_prefix = None
        self.file_list.clear()
        self.has_final_dark_file = False

    def validate(self):
        """Generate the file list if missing, and ensure that the files in the
        directory match the scan info
        """
        if not self.file_list:
            # Generate the file list if there is none
            self.generate_file_list()

        num_files = len(self.file_list)

        num_frames = self.num_scans * np.prod(self.scan_shape)
        expected_num_files = num_frames

        # The number of files should be equal to
        if num_files == expected_num_files + 1:
            # Assume the extra file is the final dark file
            self.has_final_dark_file = True
            logger.debug(
                f'For series at "{self.dirpath}", assuming final file is a '
                'dark file'
            )
        elif num_files != expected_num_files:
            msg = (
                f'For series at "{self.dirpath}", number of files '
                f'"{num_files}" does not match the '
                f'expected number of files "{expected_num_files}", '
                'which was computed based upon the number of scans '
                f'({self.num_scans}) and the scan shape ({self.scan_shape}).'
            )
            raise ValidationError(msg)

        logger.debug(f'Validation for "{self.dirpath}" passed')

    @property
    def dirpath(self):
        return self._dirpath

    @dirpath.setter
    def dirpath(self, v):
        self._dirpath = Path(v).resolve()

    @property
    def dirpath_str(self):
        return str(self.dirpath)

    @dirpath_str.setter
    def dirpath_str(self, v):
        self.dirpath = v

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


class ValidationError(Exception):
    pass
