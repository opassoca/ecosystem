#!/bin/bash
set -e
echo "◈ Gemini Ecosystem - The Master Brain ◈"

# 1. Directory Setup
ECO_DIR="$HOME/.ecosystem"
BIN_DIR="$HOME/bin"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$ECO_DIR/backups"
mkdir -p "$ECO_DIR/id-tokens"
mkdir -p "$BIN_DIR"

# 2. Global PYTHONPATH injection
# This ensures all projects can 'from core... import' without issues
BASHRC="$HOME/.bashrc"
EXPORT_CMD="export PYTHONPATH=\"\$HOME/projects/ecosystem:\$PYTHONPATH\""

if ! grep -q "projects/ecosystem" "$BASHRC"; then
    echo "[*] Configuring global PYTHONPATH in .bashrc..."
    echo "" >> "$BASHRC"
    echo "# Gemini Ecosystem Core Path" >> "$BASHRC"
    echo "$EXPORT_CMD" >> "$BASHRC"
fi

# 3. Create 'system' Command
echo "[*] Creating system command..."
cat <<EOF > "$BIN_DIR/system"
#!$(which python3)
import os
import sys
# Path is handled by PYTHONPATH in .bashrc, but added here for safety
sys.path.append(os.path.expanduser("~/projects/ecosystem"))
from core.dashboard import run_dashboard
if __name__ == "__main__":
    run_dashboard()
EOF
chmod +x "$BIN_DIR/system"

# 3.2. Create 'auth' Command
echo "[*] Creating auth command..."
cat <<EOF > "$BIN_DIR/auth"
#!$(which python3)
import os
import sys
script_path = os.path.expanduser("~/projects/ecosystem/core/switcher.py")
os.execv(sys.executable, [sys.executable, script_path] + sys.argv[1:])
EOF
chmod +x "$BIN_DIR/auth"

# 3.3. Create 'agy3' Command
echo "[*] Creating agy3 command..."
cat <<EOF > "$BIN_DIR/agy3"
#!$(which python3)
import os
import sys
script_path = os.path.expanduser("~/projects/ecosystem/core/agy3.py")
os.execv(sys.executable, [sys.executable, script_path] + sys.argv[1:])
EOF
chmod +x "$BIN_DIR/agy3"

# 3.4. Create 'oauth' Command
echo "[*] Creating oauth command..."
cat <<EOF > "$BIN_DIR/oauth"
#!$(which python3)
import os
import sys
script_path = os.path.expanduser("~/projects/ecosystem/core/oauth.py")
os.execv(sys.executable, [sys.executable, script_path] + sys.argv[1:])
EOF
chmod +x "$BIN_DIR/oauth"

# Clean up legacy gmn command
rm -f "$BIN_DIR/gmn"

# 4. PATH Configuration
if ! grep -q 'export PATH="$HOME/bin:$PATH"' "$BASHRC"; then
    echo "[*] Adding $BIN_DIR to PATH in .bashrc..."
    echo 'export PATH="$HOME/bin:$PATH"' >> "$BASHRC"
fi

echo ""
echo "✨ Ecosystem Brain Installed Successfully!"
echo "Please run: source ~/.bashrc"
echo "Launch dashboard with: system"
echo "------------------------------------------------"
