import json
import os
import subprocess
from pathlib import Path


def read_json(path: str) -> dict:
    """
    Read and parse a JSON configuration file.

    Args:
        path: Path to the JSON file

    Returns:
        Parsed JSON data as a dictionary
    """
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file {path} not found.")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Configuration file {path} is not valid JSON.")
        return {}


def run_bash_script(script_path: Path, *script_args, env: dict | None = None) -> tuple[bool, str, str]:
    """
    Runs a bash script and captures its output.
    Args:
        script_path: Path to the bash script.
        *script_args: Arguments to pass to the bash script.
        env: Optional dictionary of environment variables.
    Returns:
        A tuple (success, stdout, stderr). Success is True if the return code is 0.
    """
    command = [str(script_path)] + [str(arg) for arg in script_args]
    effective_env = os.environ.copy()
    if env:
        effective_env.update(env)

    print(f"Executing: {' '.join(command)}")
    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env=effective_env
        )
        if process.returncode != 0:
            print(f"Error: Script {script_path.name} exited with code {process.returncode}")
            if process.stdout:
                print(f"STDOUT:\n{process.stdout.strip()}")
            if process.stderr:
                print(f"STDERR:\n{process.stderr.strip()}")
            return False, process.stdout, process.stderr
        # Also print stdout/stderr on success if needed for logging or just return
        if process.stdout.strip(): print(f"Script STDOUT:\n{process.stdout.strip()}")
        if process.stderr.strip(): print(f"Script STDERR:\n{process.stderr.strip()}") # Should be empty on success if the script is well-behaved
        return True, process.stdout, process.stderr
    except FileNotFoundError:
        print(f"Error: Bash script {script_path} not found.")
        return False, "", f"Error: Bash script {script_path} not found."
    except Exception as e:
        print(f"An unexpected error occurred while running {script_path}: {e}")
        return False, "", str(e)
