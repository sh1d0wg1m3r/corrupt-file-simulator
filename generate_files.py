import os
import string
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import time
import functools
import argparse # Added argparse

# Global constants
charset = string.ascii_letters + string.digits
DEFAULT_EXTENSIONS = ['txt', 'log', 'data', 'tmp', 'out']

# define a function to generate a single random file
def generate_file(_, output_dir, name_len, text_len, delay_s=0.0, extensions=None):
    random_name = ''.join(np.random.choice(list(charset), size=name_len))
    
    if extensions and len(extensions) > 0:
        extension = np.random.choice(extensions)
    else:
        # If no extensions list is provided or it's empty, generate a random 4-char extension
        extension = ''.join(np.random.choice(list(charset), size=4))
    
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, f"{random_name}.{extension}")
    
    random_text = ''.join(np.random.choice(list(charset), size=text_len))
    with open(file_path, 'w') as f:
        f.write(random_text)
    
    if delay_s > 0:
        time.sleep(delay_s)

# define a function to generate multiple random files in parallel
def generate_files(num_f, output_dir, name_len, text_len, delay_s=0.0, extensions=None, num_workers=None):
    if num_workers is None:
        actual_num_workers = min(32, (os.cpu_count() or 4) + 4)
    else:
        actual_num_workers = num_workers
    
    generate_file_with_args = functools.partial(
        generate_file,
        output_dir=output_dir,
        name_len=name_len,
        text_len=text_len,
        delay_s=delay_s,
        extensions=extensions
    )
    
    with ThreadPoolExecutor(max_workers=actual_num_workers) as executor:
        executor.map(generate_file_with_args, range(num_f))

def main(output_dir, num_files_pb, num_b, name_l, text_l, file_extensions=None, workers=None, op_delay_s=0.0):
    # Use DEFAULT_EXTENSIONS if file_extensions is None or empty
    current_file_extensions = file_extensions
    if not current_file_extensions: # Catches None or empty list from argparse
        current_file_extensions = DEFAULT_EXTENSIONS

    for batch_num in range(num_b):
        print(f"Generating batch {batch_num + 1} of {num_b}...")
        generate_files(
            num_f=num_files_pb,
            output_dir=output_dir,
            name_len=name_l,
            text_len=text_l,
            delay_s=op_delay_s,
            extensions=current_file_extensions, # Pass the resolved list
            num_workers=workers
        )

    total_files = num_files_pb * num_b
    print(f"{total_files} files created in {output_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a large number of random files in batches.")
    
    parser.add_argument('-d', '--output-dir', type=str, default="./generated_files",
                        help="Directory to save generated files. Default: ./generated_files")
    parser.add_argument('-n', '--num-files', type=int, default=1000,
                        help="Number of files to generate per batch. Default: 1000")
    parser.add_argument('-b', '--num-batches', type=int, default=10,
                        help="Number of batches to generate. Default: 10")
    parser.add_argument('-nl', '--name-length', type=int, default=50,
                        help="Length of random file names. Default: 50")
    parser.add_argument('-tl', '--text-length', type=int, default=10000,
                        help="Length of random text content in files. Default: 10000")
    parser.add_argument('-e', '--extensions', nargs='*', default=None, # Default is None, main will use DEFAULT_EXTENSIONS
                        help="List of file extensions to use (e.g., txt log data). If not provided, uses default list.")
    parser.add_argument('-w', '--workers', type=int, default=None, # Default is None, generate_files will use its default logic
                        help="Number of worker threads. Defaults to a system-dependent value (min(32, os.cpu_count()+4)) if not set.")
    parser.add_argument('-dl', '--delay', type=float, default=0.0,
                        help="Delay in seconds after each file write operation. Default: 0.0")
    
    args = parser.parse_args()

    # Call main with parsed arguments
    main(output_dir=args.output_dir,
         num_files_pb=args.num_files,
         num_b=args.num_batches,
         name_l=args.name_length,
         text_l=args.text_length,
         file_extensions=args.extensions,
         workers=args.workers,
         op_delay_s=args.delay)
