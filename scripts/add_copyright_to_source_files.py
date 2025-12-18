# Copyright © 2025, UChicago Argonne, LLC. See "LICENSE" for full details.

"""Utility script to add copyright notice to all source files.

This project has a requirement to include the copyright comment at the top
of every source file. This utility script helps apply that automatically.

This script is intended to be ran from the root level of the repository.
"""

from pathlib import Path

old_copyright_text = '# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.\n'
copyright_text = '# Copyright © 2025, UChicago Argonne, LLC. See "LICENSE" for full details.\n'  # noqa

num_files_edited = 0
for filename in Path('.').rglob('*.py'):
    with open(filename, 'r') as rf:
        first_line = rf.readline()

    if first_line != copyright_text:
        print('Adding copyright text to:', filename)
        with open(filename, 'r') as rf:
            contents = rf.read()

        if first_line == old_copyright_text:
            # Replace the old copyright text with the new one
            contents = contents[len(old_copyright_text):]
            if contents and contents.startswith('\n'):
                contents = contents[len('\n'):]

        # Only include the carriage return if there are file contents
        endline = '\n' if contents else ''
        contents = copyright_text + endline + contents

        with open(filename, 'w') as wf:
            wf.write(contents)

        num_files_edited += 1

print('Number of files edited:', num_files_edited)
