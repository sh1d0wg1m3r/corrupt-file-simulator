# Random File Generator Script

## Description
This script is designed to create a specified number of random text files in batches. Each file has a unique name and contains random alphanumeric characters. It's useful for testing and benchmarking file system performance, data processing applications, and more.

## Requirements
- Python 3.x
- NumPy library
- A modern operating system capable of handling concurrent operations effectively.

## Installation
Ensure Python 3.x is installed on your system. You can download Python from https://www.python.org/downloads/.

Install NumPy using pip:
```
pip install numpy
```

## Usage
1. Modify the `dir_path` variable to specify the directory where you want the files to be created.
2. Adjust `num_files_per_batch`, `num_batches`, `name_length`, and `text_length` variables to fit your requirements.
3. Optionally, modify `charset` if you want to use a different set of characters in your file names and contents.
4. Run the script using Python:
```
python random_file_generator.py
```

## Configuration Options
- `dir_path`: Target directory for created files.
- `num_files_per_batch`: Number of files to create per batch.
- `num_batches`: Total number of batches.
- `name_length`: Length of the random file names.
- `text_length`: Length of the random text within each file.
- `charset`: Characters used for generating random text.

## Advanced Settings
- Throttle write speed by adjusting the `bytes_per_second` value to simulate different write speeds.
- Change `max_workers` in `generate_files` function to control the level of concurrency based on your system's capabilities.

## Caution
Running this script can quickly consume disk space and system resources. Use it judiciously, especially on systems with limited storage.

## License
This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program.  If not, see <https://www.gnu.org/licenses/>.
