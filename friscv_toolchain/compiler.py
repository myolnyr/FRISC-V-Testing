import os
from pathlib import Path

from .utils import run_bash_script


def compile_riscv_tests(
    bash_script_path: Path,
    test_src_dir: Path,
    output_base_dir: Path,
    riscv_tools_path: Path | str | None = None
) -> bool:
    """
    Compiles RISC-V tests using the provided bash script.
    Args:
        bash_script_path: Path to the build-tests.sh script.
        test_src_dir: Directory containing the C test files.
        output_base_dir: Directory where the bash script will store compiled outputs (bin, hex, disasm).
        riscv_tools_path: Optional path to the RISC-V toolchain.
    Returns:
        True if the compilation script ran successfully (exit code 0), False otherwise.
    """
    print(f"\n--- Starting RISC-V Test Compilation ---")
    print(f"Source Test Directory: {test_src_dir.resolve()}")
    print(f"Output Base Directory: {output_base_dir.resolve()}")

    script_env_overrides = {}
    if riscv_tools_path:
        resolved_riscv_path = str(Path(riscv_tools_path).resolve())
        script_env_overrides["RISCV_PATH"] = resolved_riscv_path
        print(f"Setting RISCV_PATH for script: {resolved_riscv_path}")
    else:
        if "RISCV_PATH" in os.environ:
            print(f"Using existing RISCV_PATH from environment: {os.environ['RISCV_PATH']}")
        else:
            print("RISCV_PATH not provided and not in environment. Bash script will use its default ($HOME/riscv32).")

    success, _, _ = run_bash_script(
        bash_script_path,
        str(test_src_dir.resolve()),
        str(output_base_dir.resolve()),
        env=script_env_overrides
    )

    if success:
        print("RISC-V test compilation script executed successfully.")
    else:
        print("RISC-V test compilation script failed.")
    print(f"--- Finished RISC-V Test Compilation ---\n")
    return success
