import os
import string
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import time
import functools
import argparse # Added argparse
import sys # Added sys for checking command-line arguments
from rich.prompt import Prompt
from rich.progress import Progress
from rich.console import Console # For rich.print
import platform # To determine OS for path suggestions

# Global constants
charset = string.ascii_letters + string.digits
DEFAULT_EXTENSIONS = ['txt', 'log', 'data', 'tmp', 'out'] # Used if --extensions is passed without values, or as a TUI default for specific.
RANDOM_CHOICE_EXTENSIONS = ['txt', 'log', 'data', 'tmp', 'out', 'bak', 'doc', 'pdf', 'jpg', 'png', 'csv', 'json', 'xml', 'html', 'js', 'css'] # For --random-extensions flag or TUI random choice
console = Console() # For rich printing, especially errors

# define a function to generate a single random file
def generate_file(_, output_dir, name_len, text_len, delay_s=0.0, extensions_list=None, use_random_4_char_ext=False):
    random_name = ''.join(np.random.choice(list(charset), size=name_len))
    
    if use_random_4_char_ext:
        extension = ''.join(np.random.choice(list(charset), size=4))
    elif extensions_list and len(extensions_list) > 0:
        extension = np.random.choice(extensions_list)
    else:
        # Fallback: if not using random 4-char, and no extension list is provided (or empty),
        # and this state wasn't intended by upstream logic (e.g. user explicitly chose 4-char random).
        # This warning is mostly for developer debugging if logic paths are wrong.
        # console.print("[yellow]Warning: No specific extension list provided and not explicitly using random 4-char. Defaulting to random 4-char extension.[/yellow]")
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
def generate_files(num_f, output_dir, name_len, text_len, delay_s=0.0, extensions_list=None, use_random_4_char_ext=False, num_workers=None, progress_bar=None, task_id=None):
    if num_workers is None:
        actual_num_workers = min(32, (os.cpu_count() or 4) + 4)
    else:
        actual_num_workers = num_workers

    # Wrapper function to update progress bar
    def generate_file_and_update_progress(iterator_val): # First arg is placeholder from range()
        generate_file(iterator_val, # Pass the iterator value as the first (placeholder) arg
                      output_dir=output_dir,
                      name_len=name_len,
                      text_len=text_len,
                      delay_s=delay_s,
                      extensions_list=extensions_list,
                      use_random_4_char_ext=use_random_4_char_ext)
        if progress_bar and task_id is not None:
            progress_bar.update(task_id, advance=1)
    
    with ThreadPoolExecutor(max_workers=actual_num_workers) as executor:
        executor.map(generate_file_and_update_progress, range(num_f))

# Function to check if path is accessible and writable
def is_path_valid(path_str):
    # Expand user directory symbol '~'
    expanded_path = os.path.expanduser(path_str)
    
    # Check if the path exists
    if os.path.exists(expanded_path):
        # If it exists, it must be a directory and writable
        if not os.path.isdir(expanded_path):
            console.print(f"[bold red]Error: Path '{expanded_path}' exists but is not a directory.[/bold red]")
            return False
        if not os.access(expanded_path, os.W_OK):
            console.print(f"[bold red]Error: Directory '{expanded_path}' is not writable.[/bold red]")
            return False
    else:
        # If it doesn't exist, try to check if the parent directory is writable
        # so we can create the directory.
        parent_dir = os.path.dirname(expanded_path)
        if not parent_dir: # Handle case for current directory or relative path without parent
            parent_dir = "." # Assume current directory
        
        if not os.path.exists(parent_dir):
             console.print(f"[bold red]Error: Parent directory '{parent_dir}' for '{expanded_path}' does not exist.[/bold red]")
             return False
        if not os.path.isdir(parent_dir):
            console.print(f"[bold red]Error: Parent path '{parent_dir}' for '{expanded_path}' is not a directory.[/bold red]")
            return False
        if not os.access(parent_dir, os.W_OK):
            console.print(f"[bold red]Error: Parent directory '{parent_dir}' for '{expanded_path}' is not writable.[/bold red]")
            return False
    return True

def main(output_dir, num_files_pb, num_b, name_l, text_l, file_extensions=None, workers=None, op_delay_s=0.0, use_tui=False):
    # Path validation is now done before calling main for CLI, or within the TUI prompt logic.
    # However, an additional check here ensures it's always done if somehow missed.
def main(output_dir, num_files_pb, num_b, name_l, text_l, file_extensions=None, workers=None, op_delay_s=0.0, use_tui=False, use_random_4_char_ext_flag=False): # Added use_random_4_char_ext_flag
    # Path validation is now done before calling main for CLI, or within the TUI prompt logic.
    
    # The parameter `file_extensions` to this function is the list of extensions to choose from (if not using 4-char random).
    # `use_random_4_char_ext_flag` determines if 4-char random extensions are used.

    if use_tui:
        with Progress() as progress:
            for batch_num in range(num_b):
                task_description = f"Generating batch {batch_num + 1}/{num_b}"
                task_id = progress.add_task(task_description, total=num_files_pb)
                
                generate_files(
                    num_f=num_files_pb,
                    output_dir=os.path.expanduser(output_dir), 
                    name_len=name_l,
                    text_len=text_l,
                    delay_s=op_delay_s,
                    extensions_list=file_extensions, 
                    use_random_4_char_ext=use_random_4_char_ext_flag,
                    num_workers=workers,
                    progress_bar=progress, 
                    task_id=task_id
                )
    else: # CLI mode
        for batch_num in range(num_b):
            console.print(f"Generating batch {batch_num + 1} of {num_b}...")
            generate_files(
                num_f=num_files_pb,
                output_dir=os.path.expanduser(output_dir),
                name_len=name_l,
                text_len=text_l,
                delay_s=op_delay_s,
                extensions_list=file_extensions, 
                use_random_4_char_ext=use_random_4_char_ext_flag,
                num_workers=workers
            )

    total_files = num_files_pb * num_b
    console.print(f"[green]{total_files} files created in {os.path.expanduser(output_dir)}[/green]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a large number of random files in batches.")
    
    parser.add_argument('-d', '--output-dir', type=str, default=None, 
                        help="Directory to save generated files. If not provided and no other CLI flags trigger CLI mode, TUI will ask.")
    parser.add_argument('-n', '--num-files', type=int, default=1000,
                        help="Number of files to generate per batch. Default: 1000")
    parser.add_argument('-b', '--num-batches', type=int, default=10,
                        help="Number of batches to generate. Default: 10")
    parser.add_argument('-nl', '--name-length', type=int, default=50,
                        help="Length of random file names. Default: 50")
    parser.add_argument('-tl', '--text-length', type=int, default=10000,
                        help="Length of random text content in files. Default: 10000")
    parser.add_argument('-e', '--extensions', nargs='*', default=None, 
                        help="List of file extensions to use (e.g., txt log data). Takes precedence over --random-extensions.")
    parser.add_argument('--random-extensions', action='store_true',
                        help=f"Use random extensions from a predefined list ({', '.join(RANDOM_CHOICE_EXTENSIONS[:3])}...). Overridden by --extensions.")
    parser.add_argument('-w', '--workers', type=int, default=None, 
                        help="Number of worker threads. Defaults to a system-dependent value (min(32, os.cpu_count()+4)) if not set.")
    parser.add_argument('-dl', '--delay', type=float, default=0.0,
                        help="Delay in seconds after each file write operation. Default: 0.0")

    args = parser.parse_args()

    # Determine extension strategy and final list for CLI or TUI defaults
    cli_extensions_list = None
    cli_use_random_4_char = False

    if args.extensions is not None: # Highest precedence: --extensions explicitly provided
        if len(args.extensions) == 0: 
            console.print(f"[yellow]Warning: --extensions flag was used without any values. Using default list: {', '.join(DEFAULT_EXTENSIONS)}[/yellow]")
            cli_extensions_list = DEFAULT_EXTENSIONS
        else:
            cli_extensions_list = args.extensions
    elif args.random_extensions: # Next precedence: --random-extensions flag
        cli_extensions_list = RANDOM_CHOICE_EXTENSIONS
    else: # No extension flags used in CLI, so if CLI mode is triggered, it will be 4-char random
        cli_use_random_4_char = True 

    # CLI mode detection: if output_dir is specified OR any extension flag is used
    is_cli_mode = args.output_dir is not None or args.extensions is not None or args.random_extensions

    if is_cli_mode:
        cli_output_dir_val = args.output_dir
        if cli_output_dir_val is None: # CLI mode triggered by extension flags, but no -d
            cli_output_dir_val = "./generated_files_cli_default" 
            console.print(f"[yellow]Output directory not specified in CLI mode. Using default: {cli_output_dir_val}[/yellow]")

        if not is_path_valid(cli_output_dir_val):
            sys.exit(1)
        
        main(output_dir=cli_output_dir_val,
             num_files_pb=args.num_files,
             num_b=args.num_batches,
             name_l=args.name_length,
             text_l=args.text_length,
             file_extensions=cli_extensions_list, 
             workers=args.workers,
             op_delay_s=args.delay,
             use_random_4_char_ext_flag=cli_use_random_4_char, 
             use_tui=False)
    else: # TUI mode
        console.print("[bold cyan]Interactive File Generation Setup[/bold cyan]")
        tui_output_dir = "" # Will be set by path selection logic
        # Platform specific path suggestions
        suggested_paths = []
        os_type = platform.system().lower()
        if os_type == "windows":
            # Suggest drive letters + current dir + custom
            for letter in string.ascii_uppercase:
                path = f"{letter}:\\"
                if os.path.exists(path):
                    suggested_paths.append(path)
            suggested_paths.extend([".", "Custom path"])
        else: # Linux/macOS
            suggested_paths = ["/tmp", os.path.expanduser("~/Downloads"), ".", "Custom path"]

        choices = [os.path.normpath(p) for p in suggested_paths] # Normalize for display
        
        path_selection_made = False
        while not path_selection_made:
            console.print("\n[bold]Select an output directory or enter a custom path:[/bold]")
            for i, p_choice in enumerate(choices):
                console.print(f"{i+1}. {p_choice}")
            
            choice_prompt = Prompt.ask("Enter your choice (number or custom path)", default="1")
            
            try:
                choice_num = int(choice_prompt)
                if 1 <= choice_num <= len(choices):
                    selected_path_option = choices[choice_num-1]
                    if selected_path_option == "Custom path":
                        output_dir = Prompt.ask("Enter the custom output directory")
                    else:
                        output_dir = selected_path_option
                else:
                    # Assume it's a custom path if number is out of range but looks like a path
                    # or just treat as custom path directly if not a valid number
                    output_dir = choice_prompt 
            except ValueError: # Not a number, assume custom path
                output_dir = choice_prompt

            if not is_path_valid(output_dir):
                console.print(f"[yellow]The path '{output_dir}' is not valid. Please try again.[/yellow]")
            else:
                path_selection_made = True
                console.print(f"[green]Output directory set to: {os.path.expanduser(output_dir)}[/green]\n")

        num_files_pb = Prompt.ask("Enter the number of files per batch", default=str(args.num_files), converter=int)
        num_b = Prompt.ask("Enter the number of batches", default=str(args.num_batches), converter=int)
        name_l = Prompt.ask("Enter the length of random file names", default=str(args.name_length), converter=int)
        text_l = Prompt.ask("Enter the length of random text content in files", default=str(args.text_length), converter=int)
        
        # TUI Extension Logic
        tui_extensions_list = None
        tui_use_random_4_char = False
        console.print("\n[bold]File Extension Options:[/bold]")
        console.print("1. Specific extensions (you provide)")
        console.print(f"2. Random from a predefined list ({', '.join(RANDOM_CHOICE_EXTENSIONS[:3])}...)")
        console.print("3. Random 4-character (default)")
        
        ext_choice = Prompt.ask(
            "Choose extension mode",
            choices=["1", "2", "3"],
            default="3"
        )

        if ext_choice == "1": 
            extensions_str = Prompt.ask("Enter space-separated extensions (e.g., txt log data)")
            tui_extensions_list = extensions_str.split()
            if not tui_extensions_list: 
                console.print(f"[yellow]No specific extensions provided. Using default list for this option: {', '.join(DEFAULT_EXTENSIONS)}[/yellow]")
                tui_extensions_list = DEFAULT_EXTENSIONS
        elif ext_choice == "2": 
            tui_extensions_list = RANDOM_CHOICE_EXTENSIONS
            console.print(f"Using random extensions from: {', '.join(RANDOM_CHOICE_EXTENSIONS)}")
            if Prompt.ask("Do you want to customize this list of random extensions?", choices=["yes", "no"], default="no") == "yes":
                 custom_random_list_str = Prompt.ask("Enter your space-separated list of extensions for random selection")
                 custom_random_list = custom_random_list_str.split()
                 if custom_random_list:
                     tui_extensions_list = custom_random_list
                 else:
                     console.print("[yellow]No custom list provided. Sticking to the selected random list.[/yellow]")
        else: # ext_choice == "3" or default
            tui_use_random_4_char = True
            console.print("Using random 4-character extensions.")

        workers_default_display = f"(system default: min(32, cpus+4))"
        workers_str = Prompt.ask(f"Enter the number of worker threads (or press Enter for default {workers_default_display})", default="")
        workers_val = int(workers_str) if workers_str else args.workers
        
        delay_str = Prompt.ask("Enter delay in seconds after each file write (e.g., 0.1, or press Enter for 0.0)", default=str(args.delay))
        op_delay_s_val = float(delay_str) if delay_str else args.delay

        main(output_dir=tui_output_dir, # Path already validated in TUI path selection
             num_files_pb=num_files_pb,
             num_b=num_b,
             name_l=name_l,
             text_l=text_l,
             file_extensions=tui_extensions_list,
             workers=workers_val,
             op_delay_s=op_delay_s_val,
             use_random_4_char_ext_flag=tui_use_random_4_char,
             use_tui=True)
