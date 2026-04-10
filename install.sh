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

# 2. Install foxyz
$PYTHON -m pip install --upgrade foxyz

# 3. Download browser binary
$PYTHON -m foxyz fetch

# 4. Remove macOS quarantine (bypass "unidentified developer" block)
FOXYZ_CACHE="$HOME/Library/Caches/foxyz"
if [ -d "$FOXYZ_CACHE" ]; then
    echo "Removing macOS quarantine attributes..."
    xattr -dr com.apple.quarantine "$FOXYZ_CACHE" 2>/dev/null || true
fi

echo ""
echo "Done! Foxyz is ready to use."
