#!/bin/bash

# Usage: ./git-auto-push.sh "Your commit message here"

# Exit on any error
set -e

# Default commit message if none is provided

# Display current branch
#
#
BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "📦 Pushing to branch: $BRANCH"

$BRANCH = 'raspberrypi'



# Add all changes
git add .

# Commit with message
git commit -m "$COMMIT_MESSAGE"

# Pull latest to avoid conflicts
git pull origin "$BRANCH" --rebase

# Push to remote
git push origin "$BRANCH"

echo "✅ Git push completed: $COMMIT_MESSAGE"
