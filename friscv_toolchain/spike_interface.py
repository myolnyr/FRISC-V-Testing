# Launch Spike
# Load program
# Step execution
# Extract state (PC, registers, memory)
import os
import shutil
import subprocess


def get_spike_installed(custom_path: str | None = None) -> bool:
    """
    Check if Spike is installed and accessible.

    Args:
        custom_path: Optional custom path to Spike installation

    Returns:
        True if Spike is installed and working, False otherwise
    """
    if custom_path:
        possible_cmd_path = os.path.join(custom_path, 'spike')
        if os.path.exists(possible_cmd_path) and os.access(possible_cmd_path, os.X_OK):
            spike_cmd = possible_cmd_path
        else:
            possible_cmd_path = os.path.join(custom_path, 'bin', 'spike')
            if os.path.exists(possible_cmd_path) and os.access(possible_cmd_path, os.X_OK):
                spike_cmd = possible_cmd_path
            else:
                print(f"Warning: Custom Spike path {custom_path} is invalid.")
                return False
    else:
        spike_cmd = shutil.which('spike')

    if not spike_cmd:
        return False

    try:
        _ = subprocess.run([spike_cmd, '--help'], capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f'Error executing Spike: {e}')
        return False
    except FileNotFoundError:
        print(f'Error: Spike executable not found at {spike_cmd if spike_cmd else 'PATH'}')
        return False
