import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import os
import sys
import shutil
import tempfile
import platform
import string

# Add project root to sys.path to allow importing generate_files
# Assuming test_generate_files.py is in the same directory as generate_files.py or a subdirectory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

try:
    from generate_files import (
        is_path_valid,
        generate_file,
        generate_files, # The parallel one
        main as generate_files_main, # Alias to avoid conflict with unittest.main
        DEFAULT_EXTENSIONS,
        RANDOM_CHOICE_EXTENSIONS,
        console
    )
    # Ensure rich components are available for mocking if not fully tested
    from rich.prompt import Prompt, Confirm
    from rich.progress import Progress
except ImportError as e:
    # Fallback for environments where generate_files might not be directly in PYTHONPATH
    try:
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from generate_files import (
            is_path_valid, generate_file, generate_files, 
            main as generate_files_main, DEFAULT_EXTENSIONS, RANDOM_CHOICE_EXTENSIONS, console,
            Prompt, Confirm, Progress
        )
    except ImportError:
        # Print detailed error for debugging in CI or other environments
        print(f"PYTHONPATH: {sys.path}")
        print(f"CWD: {os.getcwd()}")
        print(f"Failed to import from generate_files: {e}")
        raise e # Re-raise if still not found


class TestPathValidation(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir_path = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch('generate_files.console.print') # Suppress console output during tests
    def test_valid_existing_writable_dir(self, mock_print):
        self.assertTrue(is_path_valid(self.test_dir_path))

    @patch('generate_files.console.print')
    def test_valid_non_existing_writable_parent(self, mock_print):
        new_dir = os.path.join(self.test_dir_path, "new_subdir")
        self.assertTrue(is_path_valid(new_dir))

    @patch('generate_files.console.print')
    def test_valid_current_directory(self, mock_print):
        self.assertTrue(is_path_valid("."))

    @patch('generate_files.console.print')
    def test_invalid_non_existing_parent_does_not_exist(self, mock_print):
        invalid_path = os.path.join(self.test_dir_path, "non_existent_parent", "target_dir")
        self.assertFalse(is_path_valid(invalid_path))
        mock_print.assert_any_call(f"[bold red]Error: Parent directory '{os.path.join(self.test_dir_path, 'non_existent_parent')}' for '{invalid_path}' does not exist.[/bold red]")

    @patch('generate_files.console.print')
    def test_invalid_path_is_a_file(self, mock_print):
        file_path = os.path.join(self.test_dir_path, "test_file.txt")
        with open(file_path, "w") as f:
            f.write("hello")
        self.assertFalse(is_path_valid(file_path))
        mock_print.assert_any_call(f"[bold red]Error: Path '{file_path}' exists but is not a directory.[/bold red]")

    @patch('os.access')
    @patch('os.path.isdir', return_value=True)
    @patch('os.path.exists', return_value=True)
    @patch('generate_files.console.print')
    def test_invalid_existing_non_writable_dir(self, mock_print, mock_exists, mock_isdir, mock_access):
        # Deny W_OK for the specific path, allow for others (like parent checks if any)
        mock_access.side_effect = lambda path, mode: False if path == self.test_dir_path and mode == os.W_OK else True
        self.assertFalse(is_path_valid(self.test_dir_path))
        mock_print.assert_any_call(f"[bold red]Error: Directory '{self.test_dir_path}' is not writable.[/bold red]")
        mock_access.assert_any_call(self.test_dir_path, os.W_OK)


    @patch('os.path.expanduser')
    @patch('generate_files.console.print')
    def test_valid_user_expanded_path_non_existing(self, mock_print, mock_expanduser):
        user_path_base = os.path.join(self.test_dir_path, "user_home")
        os.makedirs(user_path_base, exist_ok=True) 
        
        # This is the path that expanduser will return
        expanded_documents_path = os.path.join(user_path_base, "Documents")
        mock_expanduser.return_value = expanded_documents_path
        
        # is_path_valid will check:
        # 1. os.path.exists(expanded_documents_path) -> False (it doesn't exist yet)
        # 2. parent_dir = os.path.dirname(expanded_documents_path) -> user_path_base
        # 3. os.path.exists(user_path_base) -> True (we created it)
        # 4. os.path.isdir(user_path_base) -> True (we created it as a dir)
        # 5. os.access(user_path_base, os.W_OK) -> True (temp dir is writable)
        self.assertTrue(is_path_valid("~/Documents"))
        mock_expanduser.assert_called_with("~/Documents")

    @patch('generate_files.console.print')
    def test_invalid_non_writable_parent_for_new_dir(self, mock_print):
        parent_dir = os.path.join(self.test_dir_path, "read_only_parent")
        os.makedirs(parent_dir)
        
        original_mode = os.stat(parent_dir).st_mode
        read_only_mode = original_mode & ~0o222 # Remove write for owner, group, others
        os.chmod(parent_dir, read_only_mode)
        
        self.addCleanup(os.chmod, parent_dir, original_mode) # Ensure cleanup

        target_dir = os.path.join(parent_dir, "new_dir")

        # If tests run as root, os.access might still return True despite chmod.
        # So, we patch os.access to ensure it reflects the intended non-writable state for the test.
        def access_side_effect(path, mode):
            if path == parent_dir and mode == os.W_OK:
                return False # Simulate parent_dir not being writable
            return os.access(path, mode) # Default behavior for other calls

        # If the chmod was effective (not running as root), os.access(parent_dir, os.W_OK) would be false.
        if os.access(parent_dir, os.W_OK) and os.geteuid() == 0: # Likely running as root and chmod wasn't enough
             with patch('os.access', side_effect=access_side_effect):
                self.assertFalse(is_path_valid(target_dir))
        else: # chmod was effective or not root
            self.assertFalse(is_path_valid(target_dir))
        
        mock_print.assert_any_call(f"[bold red]Error: Parent directory '{parent_dir}' for '{target_dir}' is not writable.[/bold red]")


class TestGenerateFileFunction(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir_path = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    def _assert_file_properties(self, file_path, expected_text_len, expected_ext=None, is_4_char_ext=False):
        self.assertTrue(os.path.exists(file_path))
        self.assertTrue(os.path.isfile(file_path))
        
        name, ext = os.path.splitext(os.path.basename(file_path))
        ext = ext[1:] 

        if expected_ext:
            self.assertIn(ext, expected_ext if isinstance(expected_ext, list) else [expected_ext])
        if is_4_char_ext:
            self.assertEqual(len(ext), 4)
            self.assertTrue(all(c in (string.ascii_letters + string.digits) for c in ext))
        
        with open(file_path, 'r') as f:
            content = f.read()
        self.assertEqual(len(content), expected_text_len)
        self.assertTrue(all(c in (string.ascii_letters + string.digits) for c in content))

    @patch('generate_files.console.print') 
    def test_specific_extensions_list(self, mock_cprint):
        name_len, text_len = 10, 20
        extensions_to_test = ["myext", "yourext"]
        for _ in range(5):
            generate_file(0, self.test_dir_path, name_len, text_len, extensions_list=extensions_to_test, use_random_4_char_ext=False)
            files = os.listdir(self.test_dir_path)
            self.assertEqual(len(files), 1)
            file_name = files[0]
            self._assert_file_properties(os.path.join(self.test_dir_path, file_name), text_len, expected_ext=extensions_to_test)
            os.remove(os.path.join(self.test_dir_path, file_name)) 

    @patch('generate_files.console.print')
    def test_use_random_4_char_ext_true(self, mock_cprint):
        name_len, text_len = 10, 20
        generate_file(0, self.test_dir_path, name_len, text_len, extensions_list=None, use_random_4_char_ext=True)
        files = os.listdir(self.test_dir_path)
        self.assertEqual(len(files), 1)
        self._assert_file_properties(os.path.join(self.test_dir_path, files[0]), text_len, is_4_char_ext=True)

    @patch('generate_files.console.print')
    def test_default_to_4_char_random_if_no_preference(self, mock_cprint):
        name_len, text_len = 10, 20
        generate_file(0, self.test_dir_path, name_len, text_len, extensions_list=None, use_random_4_char_ext=False)
        files = os.listdir(self.test_dir_path)
        self.assertEqual(len(files), 1)
        self._assert_file_properties(os.path.join(self.test_dir_path, files[0]), text_len, is_4_char_ext=True)
        # Check if the specific warning for this fallback was printed (it's commented out in source, so this would fail)
        # mock_cprint.assert_any_call("[yellow]Warning: No valid extension generation mode specified. Defaulting to random 4-char extension.[/yellow]")

class TestCommandLineAndTUI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir_path = self.temp_dir.name
        # Mock to prevent actual file generation during these higher-level tests
        self.generate_files_patcher = patch('generate_files.generate_files') 
        self.mock_generate_files_func = self.generate_files_patcher.start()
        self.addCleanup(self.generate_files_patcher.stop)

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch('generate_files.is_path_valid', return_value=True) # Assume path is always valid for these tests
    @patch('sys.argv')
    def test_cli_extensions_flag(self, mock_argv, mock_is_path_valid):
        custom_exts = ['test', 'log']
        mock_argv.return_value = ['generate_files.py', '-d', self.test_dir_path, '-e'] + custom_exts
        
        generate_files_main() # Run the script's entry point (__main__)
        
        self.mock_generate_files_func.assert_called_once()
        args, kwargs = self.mock_generate_files_func.call_args
        self.assertEqual(kwargs.get('extensions_list'), custom_exts)
        self.assertFalse(kwargs.get('use_random_4_char_ext'))
        self.assertFalse(kwargs.get('use_tui')) # Should be CLI mode

    @patch('generate_files.is_path_valid', return_value=True)
    @patch('sys.argv')
    def test_cli_random_extensions_flag(self, mock_argv, mock_is_path_valid):
        mock_argv.return_value = ['generate_files.py', '-d', self.test_dir_path, '--random-extensions']
        generate_files_main()
        self.mock_generate_files_func.assert_called_once()
        args, kwargs = self.mock_generate_files_func.call_args
        self.assertEqual(kwargs.get('extensions_list'), RANDOM_CHOICE_EXTENSIONS)
        self.assertFalse(kwargs.get('use_random_4_char_ext'))
        self.assertFalse(kwargs.get('use_tui'))

    @patch('generate_files.is_path_valid', return_value=True)
    @patch('sys.argv')
    def test_cli_default_to_4_char_random_ext(self, mock_argv, mock_is_path_valid):
        mock_argv.return_value = ['generate_files.py', '-d', self.test_dir_path] # No extension flags
        generate_files_main()
        self.mock_generate_files_func.assert_called_once()
        args, kwargs = self.mock_generate_files_func.call_args
        self.assertIsNone(kwargs.get('extensions_list')) # Or it could be an empty list depending on implementation
        self.assertTrue(kwargs.get('use_random_4_char_ext_flag')) # This is the flag passed to main()
        self.assertFalse(kwargs.get('use_tui'))

    @patch('generate_files.Prompt.ask')
    @patch('generate_files.is_path_valid', return_value=True) # TUI path selection valid
    @patch('sys.argv')
    def test_tui_mode_trigger_and_specific_extensions(self, mock_argv, mock_is_path_valid, mock_prompt_ask):
        mock_argv.return_value = ['generate_files.py'] # No CLI args should trigger TUI
        
        # Simulate TUI prompts:
        # 1. Path choice (number or custom path) -> "1" (first suggested, e.g. /tmp)
        #    Then is_path_valid is called for it.
        # 2. Num files per batch -> "10"
        # 3. Num batches -> "1"
        # 4. Name length -> "10"
        # 5. Text length -> "10"
        # 6. Extension mode choice -> "1" (Specific extensions)
        # 7. Specific extensions string -> "custom log"
        # 8. Workers -> "" (default)
        # 9. Delay -> "" (default)
        mock_prompt_ask.side_effect = [
            self.test_dir_path, # Path selected (assuming custom or it resolves to this)
            "10", "1", "10", "10", # File params
            "1",                # Extension mode: Specific
            "custom log",       # Specific extensions
            "", ""              # Workers, Delay
        ]
        # Mock platform.system for predictable suggested paths if needed for path prompt part
        with patch('platform.system', return_value='Linux'): # or Windows
             generate_files_main()

        self.mock_generate_files_func.assert_called_once()
        args, kwargs = self.mock_generate_files_func.call_args
        self.assertTrue(kwargs.get('use_tui'))
        self.assertEqual(kwargs.get('extensions_list'), ["custom", "log"])
        self.assertFalse(kwargs.get('use_random_4_char_ext_flag'))

    @patch('generate_files.Prompt.ask')
    @patch('generate_files.Confirm.ask', return_value=False) # For "customize random list?" -> no
    @patch('generate_files.is_path_valid', return_value=True)
    @patch('sys.argv')
    def test_tui_mode_random_from_default_list(self, mock_argv, mock_is_path_valid, mock_confirm_ask, mock_prompt_ask):
        mock_argv.return_value = ['generate_files.py']
        mock_prompt_ask.side_effect = [
            self.test_dir_path, # Path
            "10", "1", "10", "10", # File params
            "2",                # Extension mode: Random from default
            "", ""              # Workers, Delay
        ]
        with patch('platform.system', return_value='Linux'):
            generate_files_main()
        
        self.mock_generate_files_func.assert_called_once()
        args, kwargs = self.mock_generate_files_func.call_args
        self.assertTrue(kwargs.get('use_tui'))
        self.assertEqual(kwargs.get('extensions_list'), RANDOM_CHOICE_EXTENSIONS)
        self.assertFalse(kwargs.get('use_random_4_char_ext_flag'))

    @patch('generate_files.Prompt.ask')
    @patch('generate_files.is_path_valid', return_value=True)
    @patch('sys.argv')
    def test_tui_mode_random_4_char(self, mock_argv, mock_is_path_valid, mock_prompt_ask):
        mock_argv.return_value = ['generate_files.py']
        mock_prompt_ask.side_effect = [
            self.test_dir_path, # Path
            "10", "1", "10", "10", # File params
            "3",                # Extension mode: Random 4-char
            "", ""              # Workers, Delay
        ]
        with patch('platform.system', return_value='Linux'):
            generate_files_main()

        self.mock_generate_files_func.assert_called_once()
        args, kwargs = self.mock_generate_files_func.call_args
        self.assertTrue(kwargs.get('use_tui'))
        self.assertIsNone(kwargs.get('extensions_list')) # Or empty list
        self.assertTrue(kwargs.get('use_random_4_char_ext_flag'))

    @patch('platform.system')
    @patch('os.path.exists') # To control drive letter checks on "Windows"
    @patch('generate_files.Prompt.ask')
    @patch('generate_files.is_path_valid', return_value=True) # Assume chosen path is fine
    @patch('sys.argv', ['generate_files.py']) # Trigger TUI
    def test_tui_path_suggestions_linux(self, mock_is_path_valid, mock_prompt_ask, mock_os_exists, mock_platform_system):
        mock_platform_system.return_value = "Linux"
        # Path selection, then defaults for other prompts until ext choice (then defaults again)
        mock_prompt_ask.side_effect = [
            self.test_dir_path, # User types a custom path after seeing suggestions
            "10", "1", "10", "10", "3", "", "" 
        ]
        
        # We need to capture the print calls that display the suggestions
        with patch('generate_files.console.print') as mock_console_print:
            generate_files_main()

        linux_suggestions = ["/tmp", os.path.expanduser("~/Downloads"), ".", "Custom path"]
        # Check that the path selection prompt was displayed with these options
        # This is a bit fragile as it depends on exact print format.
        # A more robust way would be to have the suggestion list returned by a function and mock that.
        # For now, check if the key paths were mentioned.
        printed_text = "\n".join([str(c[0][0]) if c[0] else "" for c in mock_console_print.call_args_list])
        
        self.assertIn("/tmp", printed_text)
        self.assertIn(os.path.expanduser("~/Downloads"), printed_text)
        self.assertIn(".", printed_text)
        self.assertIn("Custom path", printed_text)


    @patch('platform.system', return_value="Windows")
    @patch('os.path.exists') # To control drive letter checks on "Windows"
    @patch('generate_files.Prompt.ask')
    @patch('generate_files.is_path_valid', return_value=True) # Assume chosen path is fine
    @patch('sys.argv', ['generate_files.py']) # Trigger TUI
    def test_tui_path_suggestions_windows(self, mock_is_path_valid, mock_prompt_ask, mock_os_exists, mock_platform_system):
        # Simulate C and D drives exist, others don't
        mock_os_exists.side_effect = lambda path: path in ["C:\\", "D:\\"]
        
        mock_prompt_ask.side_effect = [
            self.test_dir_path, # User types custom path
            "10", "1", "10", "10", "3", "", ""
        ]

        with patch('generate_files.console.print') as mock_console_print:
            generate_files_main()

        windows_suggestions = ["C:\\", "D:\\", ".", "Custom path"]
        printed_text = "\n".join([str(c[0][0]) if c[0] else "" for c in mock_console_print.call_args_list])

        self.assertIn("C:\\", printed_text)
        self.assertIn("D:\\", printed_text)
        self.assertNotIn("E:\\", printed_text) # Assuming E doesn't exist based on mock_os_exists
        self.assertIn(".", printed_text)
        self.assertIn("Custom path", printed_text)
        
        # Verify os.path.exists was called for drive letters
        drive_calls = [call(f"{chr(ord('A') + i)}:\\") for i in range(26)]
        mock_os_exists.assert_has_calls(drive_calls, any_order=True)

class TestProgressBarIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir_path = self.temp_dir.name
        # We don't want actual file generation here, just to check progress bar calls
        self.generate_file_patcher = patch('generate_files.generate_file')
        self.mock_generate_file = self.generate_file_patcher.start()
        self.addCleanup(self.generate_file_patcher.stop)

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch('rich.progress.Progress') # Mock the Progress class itself
    @patch('generate_files.is_path_valid', return_value=True)
    @patch('generate_files.Prompt.ask') # For TUI mode
    @patch('sys.argv', ['generate_files.py']) # Trigger TUI for progress bar
    def test_progress_bar_calls_in_tui_mode(self, mock_sys_argv, mock_prompt_ask, mock_is_path_valid, MockRichProgress):
        # Simulate TUI inputs to get to file generation part
        mock_prompt_ask.side_effect = [
            self.test_dir_path, # Path
            "5", "2", # 5 files, 2 batches
            "10", "10", # name_len, text_len
            "3", # Extension mode: random 4-char
            "", "" # workers, delay
        ]
        
        # Get the instance of Progress that will be created in main()
        mock_progress_instance = MockRichProgress.return_value.__enter__.return_value

        num_files_pb = 5
        num_batches = 2
        
        with patch('platform.system', return_value='Linux'): # To satisfy path suggestions part
            generate_files_main() 

        # Check add_task calls
        expected_add_task_calls = [
            call(f"Generating batch 1/{num_batches}", total=num_files_pb),
            call(f"Generating batch 2/{num_batches}", total=num_files_pb)
        ]
        mock_progress_instance.add_task.assert_has_calls(expected_add_task_calls)
        self.assertEqual(mock_progress_instance.add_task.call_count, num_batches)

        # Check update calls
        # mock_generate_file is called num_files_pb * num_batches times
        # Each call to the wrapper generate_file_and_update_progress should call progress.update
        # The task_id for update comes from add_task. We can assume add_task returns distinct ids.
        # Let's assume add_task returns 0, 1, ...
        
        # The actual `generate_file` (mocked here) is called inside generate_files -> generate_file_and_update_progress
        # The `update` call is in `generate_file_and_update_progress`
        # So, we need to check that `update` was called for each file.
        # The mock_generate_file doesn't include the wrapper, so we check its call count to infer updates.
        self.assertEqual(self.mock_generate_file.call_count, num_files_pb * num_batches)
        
        # To directly check `update` calls, we'd need to ensure `task_id` is passed correctly.
        # The progress_bar.update is called from generate_file_and_update_progress.
        # Since generate_files (the parallel one) is complex to mock perfectly for this,
        # verifying add_task and the number of times the core generate_file is hit gives good confidence.
        # A more direct test of `update` would be to test `generate_files` (parallel) function itself.
        # However, given the structure, if add_task is called correctly per batch, and generate_file (core)
        # is called for every file, the update mechanism inside the wrapper is implicitly tested.
        
        # Let's check how many times update was called on the progress instance.
        # This requires task_id to be handled. Let's assume add_task returns something simple.
        mock_progress_instance.add_task.side_effect = range(num_batches) # task_id 0, then 1
        
        # Re-run with this side effect for add_task to test update calls more precisely
        self.mock_generate_file.reset_mock()
        mock_progress_instance.reset_mock() # Reset all calls to the progress instance
        MockRichProgress.return_value.__enter__.return_value = mock_progress_instance # Re-assign mock instance

        # Reset Prompt.ask mocks as side_effect is consumed
        mock_prompt_ask.side_effect = [
            self.test_dir_path, "5", "2", "10", "10", "3", "", ""
        ]
        
        with patch('platform.system', return_value='Linux'):
             generate_files_main()

        expected_update_calls = []
        for i in range(num_batches): # For each batch / task_id
            for _ in range(num_files_pb): # For each file in that batch
                expected_update_calls.append(call(i, advance=1)) # task_id is i
        
        # This check is too strict if the order of execution between threads is not guaranteed for updates
        # mock_progress_instance.update.assert_has_calls(expected_update_calls)
        self.assertEqual(mock_progress_instance.update.call_count, num_files_pb * num_batches)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
