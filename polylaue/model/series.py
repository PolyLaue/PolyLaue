import logging
from pathlib import Path
import re

import numpy as np

from polylaue.typing import PathLike

logger = logging.getLogger(__name__)

# The image file regular expression
# Put the number in its own group.
IMAGE_FILE_SUFFIX_REGEX = r'_(\d+)\.(tiff?|cbf)$'


class Series:
    """The Series class is used to keep track of files within a series

    Several arguments are provided, including the directory path,
    number of scans, scan shape, and number of background frames.

    The Series will automatically identify the series files within
    the directory, validate that the file indices and number of files
    match what is expected (based upon the number of scans, scan shape,
    and number of background frames), and provide a way to obtain a
    numpy array from a particular scan number, row, and column.
    """

    def __init__(
        self,
        dirpath: PathLike,
        num_scans: int = 3,
        scan_shape: tuple[int, int] = (21, 21),
        num_background_frames: int = 10,
    ):
        self.dirpath = Path(dirpath).resolve()
        self.num_scans = num_scans
        self.scan_shape = scan_shape
        self.num_background_frames = num_background_frames
        self.has_final_dark_file = False

        self.identify_file_prefix()
        self.generate_file_list()

        self.validate()

    def filepath(self, row: int, column: int, scan_number: int = 0) -> Path:
        """Get the filepath for a specified, row, column, and scan_number"""
        if row >= self.scan_shape[0]:
            msg = f'Row "{row}" is out of bounds'
            raise ValidationError(msg)

        if column >= self.scan_shape[1]:
            msg = f'Column "{column}" is out of bounds'
            raise ValidationError(msg)

        if scan_number >= self.num_scans:
            msg = f'Scan number "{scan_number}" is out of bounds'
            raise ValidationError(msg)

        num_background = self.num_background_frames
        scan_start = num_background + scan_number * np.prod(self.scan_shape)
        idx = scan_start + row * self.scan_shape[1] + column
        filename = self.file_list[idx]

        return self.dirpath / filename

    def identify_file_prefix(self):
        """Inspect the tif files and identify the file template"""

        regex = re.compile(IMAGE_FILE_SUFFIX_REGEX, re.IGNORECASE)

        # Find the first file that matches the regular expression
        prefix = None
        for path in self.dirpath.iterdir():
            if not path.is_file():
                continue

            name = path.name
            if result := re.search(regex, name):
                prefix = name[: result.start()]
                break

        if prefix is None:
            msg = (
                f'In series dirpath "{self.dirpath}", failed to find image '
                f'file matching regular expression: "{regex}"'
            )
            raise ValidationError(msg)

        logger.debug(
            f'For series with dirpath "{self.dirpath}", file prefix was '
            f'identified to be {prefix}'
        )
        self.file_prefix = prefix

    def generate_file_list(self):
        """Generate a list of files ordered by their index

        We will index into this file list to obtain the file
        name for that index.
        """
        file_dict = {}

        # Identify all files that match the full regex
        full_regex = re.compile(
            self.file_prefix + IMAGE_FILE_SUFFIX_REGEX, re.IGNORECASE
        )

        for path in self.dirpath.iterdir():
            if not path.is_file():
                continue

            name = path.name
            if result := re.search(full_regex, name):
                idx = int(result.groups()[0])
                file_dict[idx] = name

        indices = sorted(list(file_dict))

        # The indices should be continuous from 1 to the max. Verify this.
        verify_indices = np.arange(1, indices[-1] + 1)
        if not np.array_equal(indices, verify_indices):
            missing = set(verify_indices) - set(indices)
            extra = set(indices) - set(verify_indices)
            msg = (
                f'Files with prefix "{self.file_prefix}" are not continuous '
                f'from 1 to the max value "{indices[-1]}"'
            )
            if missing:
                msg += f'\nMissing indices: {list(missing)}'

            if extra:
                msg += f'\nExtra indices: {list(extra)}'

            raise ValidationError(msg)

        self.file_list = [file_dict[i + 1] for i in range(len(indices))]

        logger.debug(
            f'For series with dirpath "{self.dirpath}", found '
            f'{len(self.file_list)} files'
        )

    def validate(self):
        """Ensure that the files in the directory match the scan info"""
        num_files = len(self.file_list)

        num_frames = self.num_scans * np.prod(self.scan_shape)
        expected_num_files = self.num_background_frames + num_frames

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
                f'({self.num_scans}), the shape ({self.scan_shape}), and '
                'the number of background frames '
                f'({self.num_background_frames}.'
            )
            raise ValidationError(msg)

        logger.debug(f'Validation for "{self.dirpath}" passed')


class ValidationError(Exception):
    pass
