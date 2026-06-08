#!/bin/bash

echo "=== Fern-OS Git Push Script (SSH Mode) ==="

# Ask for commit message
read -p "Enter commit message: " commit_msg

echo "=== Ensuring SSH agent is running ==="
eval "$(ssh-agent -s)"

echo "=== Adding SSH key ==="
ssh-add ~/.ssh/id_ed25519

echo "=== Testing SSH connection to GitHub ==="
ssh -T git@github.com

echo "=== Forcing remote to use SSH ==="
git remote set-url origin git@github.com:notinvisible-dev/Fern-OS.git

echo "=== Adding .gitkeep to empty directories ==="
find . -type d -empty -exec touch {}/.gitkeep \;

echo "=== Staging all changes ==="
git add .

echo "=== Committing ==="
git commit -m "$commit_msg"

echo "=== Pushing to GitHub over SSH ==="
git push -u origin main

echo "=== Done. ==="
