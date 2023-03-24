import os
import string
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import time

# specify the directory path where you want to create files
dir_path = "E:\\"

# specify the number of files you want to create per batch
num_files_per_batch = 10000

# specify the number of batches to create
num_batches = 100

# specify the length of the random text for file names
name_length = 100

# specify the length of the random text for file content
text_length = 1000000

# set the characters to be used for random text
charset = string.ascii_letters + string.digits

# define a function to generate a single random file with a random extension
def generate_file(_):
    random_name = ''.join(np.random.choice(list(charset), size=name_length))
    extension = ''.join(np.random.choice(list(charset), size=4))
    file_path = os.path.join(dir_path, f"{random_name}.{extension}")
    random_text = ''.join(np.random.choice(list(charset), size=text_length))
    with open(file_path, 'w') as f:
        f.write(random_text)
    time.sleep(0.002)  # introduce a 10-millisecond delay between writes

# define a function to generate multiple random files with random extensions in parallel
def generate_files(num_files):
    bytes_per_second = 50 * 1024 * 1024  # 50 MB/s
    bytes_per_thread = bytes_per_second // text_length
    max_workers = max(1, int(bytes_per_thread))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(generate_file, range(num_files))

# generate the random files in batches
for batch in range(num_batches):
    print(f"Generating batch {batch+1} of {num_batches}...")
    generate_files(num_files_per_batch)

print(f"{num_files_per_batch * num_batches} files created in {dir_path}")

