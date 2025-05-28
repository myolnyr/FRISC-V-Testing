# Launch Vivado in batch mode
# Load design
# Configure simulation
# Step simulation
# Extract state (PC, registers, memory)
import os
import shutil
import subprocess

from .spike_interface import SpikeInterface


class VivadoInterface:
    def __init__(self, sim_cmd):
        self.sim_cmd = sim_cmd


    def step_cycle(self):
        return {}
    

    def stop(self):
        pass


def get_vivado_version(custom_path: str | None = None) -> str | None:
    """
    Get the Vivado version if installed.

    Args:
        custom_path: Optional custom path to Vivado installation

    Returns:
        Version string or None if Vivado is not found
    """
    if custom_path:
        # Check if the provided custom path is valid
        possible_cmd_path = os.path.join(custom_path, 'bin', 'vivado')
        if os.path.exists(possible_cmd_path) and os.access(possible_cmd_path, os.X_OK):
            vivado_cmd = possible_cmd_path
        else:
            print(f"Warning: Custom Vivado path {custom_path} is invalid.")
            return None
    else:
        # Try to find Vivado in the system PATH
        vivado_cmd = shutil.which('vivado')

    if not vivado_cmd:
        return None

    try:
        result = subprocess.run([vivado_cmd, '-version'], capture_output=True, text=True, check=True)
        return result.stdout.splitlines()[0]
    except subprocess.CalledProcessError as e:
        print(f'Error executing Vivado: {e}')
        return None
    except FileNotFoundError:
        print(f'Error: Vivado command not found.')
        return None
