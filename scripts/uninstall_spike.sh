#!/bin/bash
set -e

# --- Configuration ---
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

# --- Determine original user & home ---
if [ -n "$SUDO_USER" ]; then
    ORIGINAL_USER="$SUDO_USER"
    USER_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    print_info "Invoked via sudo by $ORIGINAL_USER"
else
    ORIGINAL_USER="root"
    USER_HOME="$HOME"
    print_warning "Running directly as root; assuming installation was in $USER_HOME/riscv32"
fi

INSTALL_DIR="$USER_HOME/riscv32"

# --- Check if installation directory exists ---
if [ ! -d "$INSTALL_DIR" ]; then
    print_warning "Installation directory $INSTALL_DIR not found."
    read -rp "Continue anyway? [y/N] " response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        print_info "Uninstallation cancelled."
        exit 0
    fi
fi

# --- Remove symbolic links ---
print_info "Removing symbolic links from /usr/bin..."
if [ -L /usr/bin/spike ]; then
    rm -f /usr/bin/spike
    print_info "Removed /usr/bin/spike symbolic link."
else
    print_warning "Symbolic link /usr/bin/spike not found."
fi

if [ -L /usr/bin/rv32i-spike ]; then
    rm -f /usr/bin/rv32i-spike
    print_info "Removed /usr/bin/rv32i-spike symbolic link."
else
    print_warning "Symbolic link /usr/bin/rv32i-spike not found."
fi

# --- Remove RISC-V installation directory ---
if [ -d "$INSTALL_DIR" ]; then
    print_info "Removing RISC-V installation directory: $INSTALL_DIR"
    rm -rf "$INSTALL_DIR"
    print_info "Successfully removed $INSTALL_DIR"
else
    print_warning "RISC-V installation directory not found at $INSTALL_DIR. Skipping removal."
fi

# --- Remove environment variables from shell configuration ---
print_info "Removing RISCV environment variables from shell configuration..."

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

if [ -f "$RC_FILE" ]; then
    # Backup first
    BACKUP_FILE="${RC_FILE}.uninstall_$(date +%Y%m%d%H%M%S).bak"
    cp "$RC_FILE" "$BACKUP_FILE"
    print_info "Backed up $RC_FILE to $BACKUP_FILE"

    # Remove RISC-V related lines from RC file
    print_info "Removing RISC-V related lines from $RC_FILE"

    sed -i '/# RISC-V Toolchain/d' "$RC_FILE"
    sed -i '/export RISCV=.*riscv32/d' "$RC_FILE"
    sed -i '/export PATH=.*riscv32\/bin/d' "$RC_FILE"

    print_info "Successfully cleaned up $RC_FILE"
else
    print_warning "Shell configuration file $RC_FILE not found. Skipping cleanup."
fi

# --- Offer to remove build directory ---
BUILD_DIR_BASE="/tmp/riscv_build"
print_info "Note: Build directories in ${BUILD_DIR_BASE}_* should have been automatically cleaned up"
print_info "by the original installation script. If any remain, you may want to manually remove them."

echo ""
echo "=================================================="
echo "Uninstallation complete!"
echo ""
echo "The following actions were performed:"
echo "- Removed symbolic links from /usr/bin"
echo "- Removed the RISC-V installation directory: $INSTALL_DIR"
echo "- Removed environment variables from $RC_FILE"
echo ""
echo "To completely remove the changes from your current shell session,"
echo "please run: source $RC_FILE"
echo "or restart your terminal."
echo "=================================================="

exit 0
