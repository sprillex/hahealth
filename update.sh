#!/bin/bash
# Exit immediately if a command exits with a non-zero status
set -e

echo "🚀 Starting hahealth update..."

# 1. Navigate to directory
cd /home/dietpi/hahealth

# 2. Fetch latest data
echo "📡 Fetching latest branch info from remote..."
git fetch --all --prune

# 3. List branches and let user select
echo "------------------------------------------------"
echo "🔍 Available Branches (Sorted by last update):"
echo "------------------------------------------------"

branches=()
display_lines=()

# Parse git output
while IFS='|' read -r rel_date refname; do
    # Strip "refs/remotes/" to get "origin/branchname"
    short_name=${refname#refs/remotes/}
    
    branches+=("$short_name")
    display_lines+=("$short_name -- (Updated: $rel_date)")
done < <(git for-each-ref --sort=-committerdate --format='%(committerdate:relative)|%(refname)' refs/remotes)

# Check if we found remote branches; if not, check local
if [ ${#branches[@]} -eq 0 ]; then
    echo "⚠️  No remote branches found! Checking local branches instead..."
    while IFS='|' read -r rel_date refname; do
        short_name=${refname#refs/heads/}
        branches+=("$short_name")
        display_lines+=("$short_name -- (Updated: $rel_date)")
    done < <(git for-each-ref --sort=-committerdate --format='%(committerdate:relative)|%(refname)' refs/heads)
fi

# Print the menu
count=0
for line in "${display_lines[@]}"; do
    echo "  [$count] $line"
    # FIXED: Use standard math to avoid 'set -e' killing the script on 0
    count=$((count+1))
done
echo "------------------------------------------------"

if [ $count -eq 0 ]; then
    echo "❌ No branches found at all. Please check your git configuration."
    exit 1
fi

# --- NEW AUTO-SELECT LOGIC START ---
if [ $count -eq 1 ]; then
    echo "ℹ️  Only one branch found. Automatically selecting it..."
    choice=0
else
    # Read user input if there is more than one option
    read -p "Select the branch number to install: " choice
fi
# --- NEW AUTO-SELECT LOGIC END ---

# Validate input
if ! [[ "$choice" =~ ^[0-9]+$ ]] || [ -z "${branches[$choice]}" ]; then
    echo "❌ Invalid selection. Exiting."
    exit 1
fi

SELECTED_BRANCH="${branches[$choice]}"
# Strip the remote name (e.g., origin/) for the local branch name
LOCAL_BRANCH_NAME=${SELECTED_BRANCH#*/}

echo "✅ You selected: $SELECTED_BRANCH (Local target: $LOCAL_BRANCH_NAME)"

# 4. Checkout and Pull
echo "twisted checking out $LOCAL_BRANCH_NAME..."

# Check if local branch already exists
if git show-ref --verify --quiet "refs/heads/$LOCAL_BRANCH_NAME"; then
    git checkout "$LOCAL_BRANCH_NAME"
else
    # Create new local branch tracking the remote
    git checkout -b "$LOCAL_BRANCH_NAME" --track "$SELECTED_BRANCH"
fi

echo "📥 Pulling latest changes..."
# We explicitly pull the selected branch to ensure we get the right updates
git pull origin "$LOCAL_BRANCH_NAME"

# 5. Update dependencies
echo "📦 Updating python dependencies..."
./venv/bin/pip install -r requirements.txt

# 6. Run Database Migrations
echo "🗄️ Running database migrations..."
./venv/bin/python3 scripts/migrate_all.py

# 7. Restart the systemd service
echo "🔄 Restarting hahealth service..."
sudo systemctl restart hahealth

echo "✅ Update complete! Checking service status..."
sudo systemctl status hahealth --no-pager
