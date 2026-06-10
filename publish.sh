#!/bin/bash
# Universal Publisher for Gemini Ecosystem
set -e

REPO_NAME=$(basename "$(pwd)")
GITHUB_USER="opassoca"

echo "◈ Publishing $REPO_NAME to GitHub ◈"

if [ ! -d ".git" ]; then
    echo "[*] Initializing Git repository..."
    git init
    git branch -M main
fi

# Check if remote exists
if ! git remote | grep -q "origin"; then
    echo "[*] Creating GitHub repository via 'gh' CLI..."
    gh repo create "$GITHUB_USER/$REPO_NAME" --public --description "Extreme Gemini Ecosystem Module: $REPO_NAME" --source=. --remote=origin || true
fi

echo "[*] Staging files..."
git add .

echo "[*] Committing 'Extreme' Release..."
git commit -m "feat: Extreme Orchestration v2.0-stable" || echo "Nothing to commit"

echo "[*] Pushing to main..."
git push -u origin main

echo ""
echo "✨ $REPO_NAME is now LIVE on GitHub!"
echo "Uplink: https://github.com/$GITHUB_USER/$REPO_NAME"
echo "------------------------------------------------"
