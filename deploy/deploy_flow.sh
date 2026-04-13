#!/bin/bash

MODE="${1:-auto}"

CURRENT_BRANCH=$(git symbolic-ref --short HEAD)

# ── AUTO MODE ───────────────────────────────────────────────────

if [ "$MODE" = "auto" ]; then
if [ "$CURRENT_BRANCH" != "live" ]; then
exit 0
fi
echo "🔁 Post-merge detected on live branch"
fi

# ── MANUAL MODE ─────────────────────────────────────────────────

if [ "$MODE" = "manual" ]; then
echo "🚀 Manual deploy triggered"

if [ "$CURRENT_BRANCH" != "live" ]; then
echo "❌ Switch to live branch and run again"
exit 1
fi
fi

echo ""
echo "🚀 Deploy Flow: fork/live → org/master (PR based)"
echo ""

# ── SSH CONFIG ──────────────────────────────────────────────────

SSH_KEY="$HOME/Desktop/server_credentials/ShelterAppsSecurity.pem"
SERVER_USER="ubuntu"
SERVER_HOST="3.90.10.80"
DEPLOY_SCRIPT="/home/ubuntu/deploy/deploy.sh"

SSH_OPTS=(
-i "$SSH_KEY"
-o IdentitiesOnly=yes
-o StrictHostKeyChecking=no
-o PubkeyAcceptedKeyTypes=+ssh-rsa
)

# ── Helper: get PR ──────────────────────────────────────────────

get_pr_number() {
gh pr list --repo ShelterAssociates/Shelter --state open --limit 20 --json number,headRefName,headRepositoryOwner -q '.[] | select(.headRepositoryOwner.login == "vsonje2102" and .headRefName == "live") | .number' 2>/dev/null
}

# ── STEP 1: Push to origin/live ─────────────────────────────────

echo "📦 Pushing to origin/live..."
git push origin live || { echo "❌ Push failed"; exit 1; }

# ── STEP 2: Create or reuse PR ──────────────────────────────────

echo "📨 Checking PR..."

PR_NUMBER=$(get_pr_number)

if [ -z "$PR_NUMBER" ]; then
echo "📨 Creating PR..."
gh pr create --repo ShelterAssociates/Shelter --base master --head vsonje2102:live --title "Deploy: $(git log -1 --pretty=%s)" --body "Auto deploy PR"
fi

sleep 3
PR_NUMBER=$(get_pr_number)

if [ -z "$PR_NUMBER" ]; then
echo "❌ Could not find PR"
exit 1
fi

PR_URL=$(gh pr view "$PR_NUMBER" --repo ShelterAssociates/Shelter --json url -q '.url')

echo "🔗 PR: $PR_URL"

# ── STEP 3: Wait OR skip if already merged ──────────────────────

STATE=$(gh pr view "$PR_NUMBER" --repo ShelterAssociates/Shelter --json state -q '.state')

if [ "$STATE" = "MERGED" ]; then
echo "✅ PR already merged — deploying..."
else
echo "⏳ Waiting for merge..."

while true; do
STATE=$(gh pr view "$PR_NUMBER" --repo ShelterAssociates/Shelter --json state -q '.state')

```
if [ "$STATE" = "MERGED" ]; then
  echo "✅ PR merged!"
  break
elif [ "$STATE" = "CLOSED" ]; then
  echo "❌ PR closed"
  exit 1
fi

sleep 10
```

done
fi

# ── STEP 4: Trigger server deploy ───────────────────────────────

echo ""
echo "🔌 Deploying to server..."

ssh -tt "${SSH_OPTS[@]}" "$SERVER_USER@$SERVER_HOST" 
"bash -x $DEPLOY_SCRIPT 'NONE'"

DEPLOY_STATUS=$?

# ── STEP 5: Fetch logs via rsync ────────────────────────────────

echo ""
echo "📥 Fetching deploy logs from server..."

REMOTE_LOG="/home/ubuntu/deploy/latest_deploy.log"
LOCAL_LOG="/tmp/deploy_latest.log"

rsync -avz -e "ssh ${SSH_OPTS[*]}" 
"$SERVER_USER@$SERVER_HOST:$REMOTE_LOG" 
"$LOCAL_LOG"

if [ -f "$LOCAL_LOG" ]; then
echo ""
echo "════════════════════════════════════════════════════════════"
echo "📄 DEPLOY LOG"
echo "════════════════════════════════════════════════════════════"
cat "$LOCAL_LOG"
echo "════════════════════════════════════════════════════════════"

rm -f "$LOCAL_LOG"
echo "🧹 Local log deleted"
else
echo "❌ Failed to fetch log file"
fi

# ── FINAL STATUS ────────────────────────────────────────────────

echo ""
if [ $DEPLOY_STATUS -eq 0 ]; then
echo "════════════════════════════════════════════════════════════"
echo "✅ Deployment successful!"
echo "════════════════════════════════════════════════════════════"
else
echo "════════════════════════════════════════════════════════════"
echo "❌ Deployment FAILED!"
echo "════════════════════════════════════════════════════════════"
exit 1
fi

echo ""
echo "🎉 Deploy flow complete!"
echo ""
