#!/bin/bash
set -e

echo "Installing Foxyz..."

# 1. Check Python 3
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null && python --version 2>&1 | grep -q "^Python 3"; then
    PYTHON=python
else
    echo "Python 3 not found. Installing via Homebrew..."
    if ! command -v brew &>/dev/null; then
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        if [ -f /opt/homebrew/bin/brew ]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        elif [ -f /usr/local/bin/brew ]; then
            eval "$(/usr/local/bin/brew shellenv)"
        fi
    fi
    brew install python3
    PYTHON=python3
fi

echo "Using: $($PYTHON --version)"

# 2. Create venv at ~/.foxyz-env
VENV_DIR="$HOME/.foxyz-env"
echo "Setting up virtual environment..."
rm -rf "$VENV_DIR"
$PYTHON -m venv "$VENV_DIR"

# 3. Install foxyz using venv's own pip — isolated from system, no PEP 668 conflict
echo "Installing foxyz..."
"$VENV_DIR/bin/pip" install foxyz

# 4. Download browser binary
echo "Downloading browser..."
"$VENV_DIR/bin/foxyz" fetch

# 5. Remove macOS quarantine
FOXYZ_CACHE="$HOME/Library/Caches/foxyz"
if [ -d "$FOXYZ_CACHE" ]; then
    echo "Removing macOS quarantine..."
    xattr -dr com.apple.quarantine "$FOXYZ_CACHE" 2>/dev/null || true
fi

# 6. Add to PATH in shell profile
SHELL_PROFILE=""
if [ -f "$HOME/.zshrc" ]; then
    SHELL_PROFILE="$HOME/.zshrc"
elif [ -f "$HOME/.bash_profile" ]; then
    SHELL_PROFILE="$HOME/.bash_profile"
elif [ -f "$HOME/.bashrc" ]; then
    SHELL_PROFILE="$HOME/.bashrc"
fi

if [ -n "$SHELL_PROFILE" ]; then
    if ! grep -q "foxyz-env/bin" "$SHELL_PROFILE" 2>/dev/null; then
        echo "" >> "$SHELL_PROFILE"
        echo "# Foxyz" >> "$SHELL_PROFILE"
        echo 'export PATH="$HOME/.foxyz-env/bin:$PATH"' >> "$SHELL_PROFILE"
    fi
fi

echo ""
echo "Done! Foxyz is ready to use."
if [ -n "$SHELL_PROFILE" ]; then
    echo ""
    echo "Apply PATH changes:"
    echo "  source $SHELL_PROFILE"
fi
