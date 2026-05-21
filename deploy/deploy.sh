#!/bin/bash
set -e
trap 'echo "❌ ERROR at line $LINENO. Check logs above."' ERR

# ── CONFIG ───────────────────────────────────────────────────────────────────
PROJECT_DIR="/srv/Shelter"
VENV_DIR="$PROJECT_DIR/ENV3"
GIT_BRANCH="master"
LOG_DIR="/home/ubuntu/deploy"

MIGRATION_ARG="${1:-NONE}"

mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/deploy_$(date +%Y%m%d_%H%M%S).log"
ln -sf "$LOG_FILE" "$LOG_DIR/latest_deploy.log"

exec > >(tee -a "$LOG_FILE") 2>&1

# ── LOG CLEANUP (keep only latest 5 logs) ────────────────────────────────────
echo "🧹 Cleaning old logs (keeping latest 5)..."

LOG_FILES=$(ls -t "$LOG_DIR"/deploy_*.log 2>/dev/null || true)

if [ -n "$LOG_FILES" ]; then
    COUNT=$(echo "$LOG_FILES" | wc -l)
    if [ "$COUNT" -gt 5 ]; then
        echo "$LOG_FILES" | tail -n +6 | while read -r file; do
            echo "🗑️ Removing old log: $file"
            rm -f "$file"
        done
    fi
fi

echo "✅ Log cleanup done."

# ── START ────────────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════════"
echo "🚀 Server Deploy Started — $(date)"
echo "════════════════════════════════════════════════════════════"

cd "$PROJECT_DIR"

# ── STEP 1: Fetch latest code ────────────────────────────────────────────────
echo ""
echo "📥 Fetching latest code..."
git fetch origin

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$GIT_BRANCH")

# ── STEP 2: Check if deploy needed ───────────────────────────────────────────
if [ "$LOCAL" = "$REMOTE" ]; then
    echo "⏩ No new changes. Skipping deploy + backup."
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "✅ Deploy skipped — $(date)"
    echo "════════════════════════════════════════════════════════════"
    exit 0
fi

# ── STEP 3: Switch to branch and pull latest master ──────────────────────────
echo ""
echo "🚀 Deploying latest code..."

# Ensure we are on the correct local branch before pulling
git checkout "$GIT_BRANCH"

# --ff-only fast-forwards the local branch pointer AND updates files.
# Unlike reset --hard (which only updates files but leaves the branch
# pointer behind), this keeps local master in sync with origin/master.
git merge --ff-only "origin/$GIT_BRANCH"

echo "✅ Code updated. Now at: $(git rev-parse --short HEAD)"

# ── STEP 4: Backup AFTER update ──────────────────────────────────────────────
echo ""
echo "🛟 Updating backup branch..."

BACKUP_BRANCH="backup"

if git show-ref --verify --quiet "refs/heads/$BACKUP_BRANCH"; then
    echo "🔄 Updating existing backup branch..."
    git branch -f "$BACKUP_BRANCH"
else
    echo "🆕 Creating backup branch..."
    git branch "$BACKUP_BRANCH"
fi

git push origin "$BACKUP_BRANCH" --force
echo "✅ Backup branch updated."

# ── STEP 5: Activate virtual environment ─────────────────────────────────────
echo ""
echo "🐍 Activating virtual environment..."
source "$VENV_DIR/bin/activate"
echo "✅ Virtualenv activated."

# ── STEP 6: Run migrations ───────────────────────────────────────────────────
echo ""
if [ "$MIGRATION_ARG" = "NONE" ]; then
    echo "⏩ Skipping migrations."
else
    IFS=',' read -ra APPS <<< "$MIGRATION_ARG"

    echo "🗃️ Running migrations for: ${APPS[*]}"
    echo ""

    for app in "${APPS[@]}"; do
        echo "──────────────────────────────────────"
        echo "📝 makemigrations: $app"
        python manage.py makemigrations "$app"

        echo "⚙️ migrate: $app"
        python manage.py migrate "$app"

        echo "✅ Done: $app"
        echo ""
    done
fi

# ── STEP 7: Collect static ───────────────────────────────────────────────────
echo ""
echo "🗂️ Collecting static files..."
python manage.py collectstatic --noinput --clear -v 0
echo "✅ Static files collected."

# ── STEP 8: Restart shelter service ──────────────────────────────────────────
echo ""
echo "🔄 Restarting shelter service..."
sudo service shelter restart
echo "✅ Shelter service restarted."

# ── STEP 9: Verify service ───────────────────────────────────────────────────
echo ""
echo "🔍 Checking service status..."
STATUS=$(sudo service shelter status)

echo "$STATUS"

if echo "$STATUS" | grep -q "start/running"; then
    echo "✅ Shelter service is running."
    echo "[ $(date) ] ✅ Shelter restarted successfully" | sudo tee -a /var/log/upstart/shelter.log
else
    echo "❌ Shelter service is NOT running!"
    echo "[ $(date) ] ❌ Shelter restart FAILED" | sudo tee -a /var/log/upstart/shelter.log
    exit 1
fi

# ── DONE ─────────────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ Deploy complete — $(date)"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "📄 Log file: $LOG_FILE"
