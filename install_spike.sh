#!/bin/bash
set -e

# --- Configuration ---
# Build with a more complete ISA for flexibility
RISCV_ARCH="rv32imac_zicsr_zifencei"
RISCV_ABI="ilp32"
NUM_JOBS=$(nproc)
BUILD_DIR_BASE="/tmp/riscv_build"

print_info()   { echo "INFO:    $1"; }
print_warning(){ echo "WARNING: $1"; }
print_error()  { echo "ERROR:   $1" >&2; }

# --- Sudo Check ---
print_info "Checking for root privileges..."
if [ "$EUID" -ne 0 ]; then
  print_error "Please run this script with sudo: sudo $0"
  exit 1
fi
print_info "Running as root."

# --- Pre-flight check: ensure no existing spike ---
print_info "Checking for existing Spike installation in PATH..."
if command -v spike >/dev/null 2>&1; then
    print_error "Found an existing 'spike' executable at $(command -v spike)."
    print_error "Please remove or rename it before running this installer."
    exit 1
fi


# --- Determine original user & home ---
if [ -n "$SUDO_USER" ]; then
    ORIGINAL_USER="$SUDO_USER"
    USER_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    print_info "Invoked via sudo by $ORIGINAL_USER"
else
    ORIGINAL_USER="root"
    USER_HOME="$HOME"
    print_warning "Running directly as root; installation will go into $USER_HOME/riscv32"
fi

INSTALL_DIR="$USER_HOME/riscv32"
BUILD_DIR="${BUILD_DIR_BASE}_${ORIGINAL_USER}_$$"

# shellcheck disable=SC2317
cleanup(){
    print_info "Cleaning up $BUILD_DIR"
    rm -rf "$BUILD_DIR"
}
trap cleanup EXIT HUP INT TERM

# --- Prerequisites ---
print_info "Installing build dependencies..."
apt-get update
apt-get install -y autoconf automake autotools-dev curl python3 \
                   libmpc-dev libmpfr-dev libgmp-dev gawk \
                   build-essential bison flex texinfo gperf libtool \
                   patchutils bc zlib1g-dev libexpat1-dev git \
                   device-tree-compiler pkg-config

# --- Safety Check ---
print_info "Target install directory: $INSTALL_DIR"
if [ -d "$INSTALL_DIR" ] && [ "$(ls -A "$INSTALL_DIR")" ]; then
    print_error "$INSTALL_DIR exists and is not empty; please remove or choose another."
    exit 1
elif [ -e "$INSTALL_DIR" ] && [ ! -d "$INSTALL_DIR" ]; then
    print_error "$INSTALL_DIR exists but isn't a directory."
    exit 1
fi

# --- Build & Install ---
print_info "Creating build directory $BUILD_DIR"
mkdir -p "$BUILD_DIR" && cd "$BUILD_DIR"

print_info "=== 1) GNU Toolchain ==="
git clone --recursive https://github.com/riscv/riscv-gnu-toolchain riscv-gnu-toolchain-src
cd riscv-gnu-toolchain-src
./configure --prefix="$INSTALL_DIR" \
            --with-arch="$RISCV_ARCH" \
            --with-abi="$RISCV_ABI" \
            --enable-multilib
print_info "Building toolchain…"
make -j"$NUM_JOBS"
print_info "Installing toolchain…"
make install -j"$NUM_JOBS"
cd "$BUILD_DIR"

export PATH="$INSTALL_DIR/bin:$PATH"
export RISCV="$INSTALL_DIR"

print_info "=== 2) Proxy Kernel (PK) ==="
git clone https://github.com/riscv-software-src/riscv-pk riscv-pk-src
cd riscv-pk-src
mkdir -p build && cd build
../configure --prefix="$INSTALL_DIR" \
             --host=riscv32-unknown-elf \
             --with-arch="$RISCV_ARCH" \
             --with-abi="$RISCV_ABI"
make -j"$NUM_JOBS"
make install -j"$NUM_JOBS"
cd "$BUILD_DIR"

print_info "=== 3) Spike Simulator ==="
git clone https://github.com/riscv-software-src/riscv-isa-sim riscv-isa-sim-src
cd riscv-isa-sim-src
mkdir -p build && cd build
../configure --prefix="$INSTALL_DIR"
make -j"$NUM_JOBS"
make install -j"$NUM_JOBS"
cd "$BUILD_DIR"

# Create helper scripts for RV32I testing
print_info "=== 4) Creating helper scripts ==="
mkdir -p "$INSTALL_DIR/bin"

# Script for compiling RV32I-only programs
cat > "$INSTALL_DIR/bin/rv32i-gcc" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
"$SCRIPT_DIR/riscv32-unknown-elf-gcc" -march=rv32i -mabi=ilp32 "$@"
EOF
chmod +x "$INSTALL_DIR/bin/rv32i-gcc"

# Script for running Spike with RV32I-only configuration
cat > "$INSTALL_DIR/bin/rv32i-spike" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
"$SCRIPT_DIR/spike" --isa=rv32i "$@"
EOF
chmod +x "$INSTALL_DIR/bin/rv32i-spike"

# Restore ownership
if [ "$ORIGINAL_USER" != "root" ]; then
    print_info "Chowning $INSTALL_DIR back to $ORIGINAL_USER"
    chown -R "$ORIGINAL_USER:$ORIGINAL_USER" "$INSTALL_DIR"
fi

# --- Automatically add RISCV and PATH exports to user's shell rc ---
print_info "Adding RISCV environment variables to user's shell config..."

# Detect appropriate shell RC file
RC_FILE=""
if [ -n "$SUDO_USER" ]; then
    USER_SHELL=$(getent passwd "$SUDO_USER" | cut -d: -f7)
    case "$USER_SHELL" in
        */zsh) RC_FILE="$USER_HOME/.zshrc" ;;
        *)     RC_FILE="$USER_HOME/.bashrc" ;;
    esac
else
    RC_FILE="$HOME/.bashrc"
fi

# Ensure file exists
touch "$RC_FILE"

# Backup first
BACKUP_FILE="${RC_FILE}.$(date +%Y%m%d%H%M%S).bak"
cp "$RC_FILE" "$BACKUP_FILE"
print_info "Backed up $RC_FILE to $BACKUP_FILE"

# Lines to add
RISCV_EXPORT="export RISCV=\"$INSTALL_DIR\""
PATH_EXPORT="export PATH=\"$RISCV/bin:$PATH\""

# Only add if not already present
grep -Fqx "$RISCV_EXPORT" "$RC_FILE" || echo -e "\n# RISC-V Toolchain\n$RISCV_EXPORT" >> "$RC_FILE"
grep -Fqx "$PATH_EXPORT" "$RC_FILE" || echo "$PATH_EXPORT" >> "$RC_FILE"

print_info "Updated $RC_FILE with RISC-V environment variables."


print_info "------------------------------------------------"
print_info "Installation complete: tools in $INSTALL_DIR"
print_info "------------------------------------------------"

exit 0
