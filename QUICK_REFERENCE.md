# 📋 Quick Reference Guide

Panduan cepat untuk Datagram Orchestrator.

---

## 🚀 Installation One-Liner

### Windows
```powershell
# Install dependencies
winget install GitHub.cli Git.Git Python.Python.3.11; pip install pynacl

# Run orchestrator
.\setup_datagram.ps1
```

### Linux/macOS
```bash
# Install dependencies  
sudo apt install gh git jq python3-pip && pip3 install pynacl

# Run orchestrator
chmod +x setup_datagram.sh && ./setup_datagram.sh
```

---

## 📂 File Structure

```
datagram-orchestrator/
├── .github/workflows/
│   └── datagram-runner.yml          ← GitHub Actions workflow
├── config/
│   ├── api_keys.txt                 ← Your Datagram API keys
│   ├── tokens.txt                   ← GitHub PATs
│   ├── config.json                  ← Main configuration
│   ├── token_cache.json             ← Username cache
│   ├── invited_users.txt            ← Invite tracking
│   ├── accepted_users.txt           ← Accept tracking
│   └── secrets_set.txt              ← Secrets tracking
├── logs/
│   └── setup.log                    ← Execution logs
├── setup_datagram.ps1               ← Windows orchestrator
└── setup_datagram.sh                ← Linux/Mac orchestrator
```

---

## ⚡ Common Commands

### GitHub CLI

```bash
# Authenticate
gh auth login

# Check authentication
gh auth status

# Repository operations
gh repo create my-repo --private
gh repo view owner/repo

# Workflow operations
gh workflow list
gh workflow run workflow-name.yml
gh workflow view workflow-name.yml

# Run operations
gh run list --limit 10
gh run view <run-id>
gh run view <run-id> --log
gh run watch <run-id>

# Secret operations
gh secret list
gh secret set SECRET_NAME < file.txt
gh secret delete SECRET_NAME
```

### Git Operations

```bash
# Initialize
git init
git branch -M main

# Commit
git add .
git commit -m "message"

# Remote & Push
git remote add origin https://github.com/user/repo.git
git push -u origin main --force

# Status
git status
git log --oneline -5
```

---

## 🔑 GitHub Token Scopes

### Required Permissions

```
✅ repo                  Full control of private repositories
✅ workflow              Update GitHub Action workflows  
✅ admin:org             Full control of orgs and teams
✅ codespace             Full control of codespaces

Optional (recommended):
✅ read:user            Read user profile data
✅ user:email           Access user email addresses
```

### Generate Token

```
1. Go to: https://github.com/settings/tokens
2. Click: "Generate new token" → "Generate new token (classic)"
3. Select scopes: repo, workflow, admin:org, codespace
4. Click: "Generate token"
5. Copy token immediately (won't show again!)
```

---

## 📝 Configuration Templates

### config/config.json
```json
{
  "main_account_username": "your_github_username",
  "main_repo_name": "datagram-runner",
  "main_token": "ghp_xxxxxxxxxxxxxxxxxxxx"
}
```

### config/api_keys.txt
```
key_abc123xyz456def789
key_ghi012jkl345mno678
key_pqr901stu234vwx567
```

### config/tokens.txt
```
ghp_1234567890abcdefghij
ghp_abcdefghijklmnopqrst
ghp_uvwxyz0123456789abcd
```

---

## 🎯 Workflow Execution Flow

```
┌─────────────────────────────────────┐
│ 1. Parse API Keys from Secret      │
│    Input: DATAGRAM_API_KEYS         │
│    Output: JSON matrix              │
└──────────┬──────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│ 2. Spawn Parallel Nodes             │
│    Strategy: matrix                 │
│    Max Parallel: 50                 │
└──────────┬──────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│ 3. Each Node Executes:              │
│    a. Download Datagram CLI         │
│    b. Start infinite loop           │
│    c. Run: datagram-cli -key X      │
│    d. Timeout: 5 hours              │
│    e. Cooldown: 10 seconds          │
│    f. Repeat until max iterations   │
└──────────┬──────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│ 4. Monitor & Report                 │
│    - Health check                   │
│    - Upload logs on failure         │
└──────────┬──────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│ 5. Cron Trigger (Every 5 hours)     │
│    Schedule: 0 */5 * * *            │
│    Action: Restart entire workflow  │
└─────────────────────────────────────┘
```

---

## 🐛 Debugging Cheat Sheet

### Check Logs

```bash
# Orchestrator logs
cat logs/setup.log
tail -f logs/setup.log

# GitHub Actions logs
gh run list
gh run view <run-id> --log
gh run view <run-id> --log-failed

# System logs (Linux)
journalctl -xe | grep datagram
```

### Common Error Patterns

| Error | Cause | Solution |
|-------|-------|----------|
| `gh: command not found` | GitHub CLI not installed | Install: `winget install GitHub.cli` |
| `jq: command not found` | jq not installed (Linux) | Install: `sudo apt install jq` |
| `ModuleNotFoundError: No module named 'nacl'` | PyNaCl not installed | Install: `pip install pynacl` |
| `API rate limit exceeded` | Too many API calls | Wait 1 hour or use authenticated requests |
| `Resource not accessible by integration` | Missing token permissions | Regenerate token with correct scopes |
| `refusing to allow an OAuth App` | SAML/SSO required | Authorize token for organization |
| `timeout` in logs | Network issues | Retry automatically handled |

### Force Refresh

```bash
# Clear all cache
rm -f config/token_cache.json config/*_users.txt config/secrets_set.txt

# Or via menu
# Windows: .\setup_datagram.ps1 → Menu 13
# Linux: ./setup_datagram.sh → Menu 13

# Re-run setup
# Menu 5 → Validate tokens
# Menu 6 → Invite collaborators
# Menu 7 → Accept invitations
# Menu 8 → Set secrets
```

---

## 🔄 Update Procedures

### Update API Keys

```bash
# Method 1: Edit file directly
nano config/api_keys.txt
# Add/remove keys

# Method 2: Via orchestrator
.\setup_datagram.ps1 → Menu 2

# Apply changes
Menu 13 → Clean cache (reset secrets_set.txt)
Menu 8  → Auto Set Secrets (re-distribute)
Menu 10 → Trigger Workflow (restart nodes)
```

### Add New GitHub Accounts

```bash
# 1. Add new token
echo "ghp_new_token" >> config/tokens.txt

# 2. Validate
Menu 5 → Validate Tokens

# 3. Invite to repo
Menu 6 → Auto Invite Collaborators

# 4. Accept invitation (from new account)
Menu 7 → Auto Accept Invitations

# 5. Set secrets (from new account)
Menu 8 → Auto Set Secrets

# Done! New account will participate in next run
```

### Update Workflow File

```bash
# 1. Edit workflow
nano .github/workflows/datagram-runner.yml

# 2. Commit changes
git add .github/workflows/datagram-runner.yml
git commit -m "Update workflow configuration"

# 3. Push
git push

# 4. Trigger manually if needed
gh workflow run datagram-runner.yml
```

---

## 📊 Monitoring Commands

### Real-time Status

```bash
# Watch workflow runs
gh run list --limit 20

# Watch specific run (auto-refresh)
gh run watch <run-id>

# View logs for specific job
gh run view <run-id> --job <job-id> --log

# Download logs
gh run download <run-id>
```

### Check Node Health

```bash
# List all running jobs
gh run list --workflow=datagram-runner.yml --status=in_progress

# Check conclusions
gh run list --workflow=datagram-runner.yml --json conclusion,status,createdAt

# Example output parsing
gh run list --json status,conclusion | jq '.[] | select(.status=="completed" and .conclusion=="success")'
```

### Performance Metrics

```bash
# Total runs today
gh run list --created=$(date +%Y-%m-%d) | wc -l

# Success rate
gh run list --limit 100 --json conclusion | jq '[.[] | select(.conclusion=="success")] | length'

# Average duration (requires log analysis)
gh run list --limit 10 --json durationMs | jq '[.[].durationMs] | add/length/1000/60'
```

---

## 🎨 Customization Options

### Adjust Auto-Restart Timing

**In workflow file (.github/workflows/datagram-runner.yml):**

```yaml
# Change cron schedule (default: every 5 hours)
schedule:
  - cron: '0 */3 * * *'  # Every 3 hours
  - cron: '0 */6 * * *'  # Every 6 hours
  - cron: '0 0 * * *'    # Once daily at midnight

# Change job timeout (default: 350 minutes)
timeout-minutes: 330  # 5h 30m
timeout-minutes: 280  # 4h 40m
```

### Adjust Parallel Execution

```yaml
strategy:
  max-parallel: 20   # Run max 20 nodes simultaneously
  max-parallel: 50   # Run max 50 nodes (default)
  max-parallel: 100  # Run max 100 nodes (requires paid plan)
```

### Adjust Restart Behavior

```yaml
env:
  MAX_RETRIES: 50    # Reduce iterations per job
  RESTART_DELAY: 30  # Increase cooldown to 30 seconds
```

---

## 🔐 Security Best Practices

### Token Management

```bash
# ✅ DO: Store in secure location
# Windows: Use Windows Credential Manager
# Linux: Use keyring or pass

# ✅ DO: Use environment variables
export GH_TOKEN="ghp_xxxx"

# ❌ DON'T: Commit tokens to git
echo "config/tokens.txt" >> .gitignore
echo "config/config.json" >> .gitignore

# ❌ DON'T: Share tokens publicly
# Revoke immediately if exposed
```

### Secret Rotation

```bash
# 1. Generate new tokens
# GitHub Settings → Developer settings → Personal access tokens

# 2. Update files
nano config/tokens.txt
nano config/config.json

# 3. Clean cache
Menu 13 → Clean Cache

# 4. Re-validate and re-setup
Menu 5 → Validate Tokens
Menu 8 → Auto Set Secrets

# 5. Revoke old tokens
# GitHub Settings → Revoke old tokens
```

---

## 🎓 Advanced Tips

### Batch Operations

```bash
# Bulk invite from CSV
cat users.csv | cut -d',' -f1 | while read user; do
  gh api --method PUT /repos/OWNER/REPO/collaborators/$user -f permission=push
done

# Bulk set secrets across repos
for repo in repo1 repo2 repo3; do
  gh secret set DATAGRAM_API_KEYS -R owner/$repo < config/api_keys.txt
done
```

### Conditional Execution

**Only run on specific days:**
```yaml
# In workflow file
on:
  schedule:
    - cron: '0 */5 * * 1-5'  # Monday to Friday only
    - cron: '0 0 * * 6,0'    # Weekends at midnight only
```

**Skip specific nodes:**
```yaml
# Add condition to job
run-nodes:
  if: matrix.index != 3  # Skip node #3
```

### Performance Optimization

```bash
# Use self-hosted runners for unlimited execution
# .github/workflows/datagram-runner.yml
jobs:
  run-nodes:
    runs-on: self-hosted  # Instead of ubuntu-latest
    timeout-minutes: 0    # No timeout on self-hosted
```

---

## 📱 GitHub Actions Limits

### Free Tier (Public Repos)

| Resource | Limit |
|----------|-------|
| Concurrent jobs | 20 |
| Job execution time | 6 hours |
| Workflow run time | 35 days |
| API requests | 1000/hour |
| Storage | 500 MB |
| Minutes | Unlimited (free) |

### Free Tier (Private Repos)

| Resource | Limit |
|----------|-------|
| Concurrent jobs | 20 |
| Job execution time | 6 hours |
| Workflow run time | 35 days |
| API requests | 1000/hour |
| Storage | 500 MB |
| Minutes | 2000/month |

### Paid Plans

- **Team**: 3,000 minutes/month, 60 concurrent jobs
- **Enterprise**: 50,000 minutes/month, 180 concurrent jobs
- **Self-hosted**: Unlimited (use your own infrastructure)

---

## 🆘 Emergency Procedures

### Stop All Workflows

```bash
# Cancel all running workflows
gh run list --status=in_progress --json databaseId --jq '.[].databaseId' | \
  xargs -I {} gh run cancel {}

# Or via UI
# Actions → Select workflow → Cancel workflow
```

### Rollback Deployment

```bash
# 1. Revert to previous commit
git log --oneline -5
git revert <commit-hash>
git push

# 2. Or force push old version
git reset --hard <old-commit>
git push --force

# 3. Re-trigger workflow
gh workflow run datagram-runner.yml
```

### Reset Everything

```bash
# ⚠️  WARNING: This deletes all tracking data!

# 1. Stop all workflows
gh run list --status=in_progress --json databaseId --jq '.[].databaseId' | xargs -I {} gh run cancel {}

# 2. Delete cache files
rm -rf config/token_cache.json config/*_users.txt config/secrets_set.txt

# 3. Delete secrets
gh secret delete DATAGRAM_API_KEYS

# 4. Start fresh setup
.\setup_datagram.ps1
# Menu 1 → 2 → 4 → 5 → 6 → 7 → 8 → 9 → 10
```

---

## 📞 Quick Help

### Command Not Found?

```bash
# Windows: Add to PATH
# Git Bash / PowerShell might need restart

# Linux: Install missing tools
sudo apt update
sudo apt install gh git jq python3-pip

# macOS: Use Homebrew
brew install gh git jq python3
```

### Permission Denied?

```bash
# Linux: Make script executable
chmod +x setup_datagram.sh

# Windows: Run PowerShell as Administrator
# Or: Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Rate Limited?

```bash
# Check rate limit status
gh api rate_limit

# Wait for reset or use authenticated requests
# Authenticated: 5000 requests/hour
# Unauthenticated: 60 requests/hour
```

---

## 🔗 Useful Links

- **GitHub CLI Docs**: https://cli.github.com/manual/
- **GitHub Actions Docs**: https://docs.github.com/en/actions
- **Datagram Docs**: https://docs.datagram.network/
- **PyNaCl Docs**: https://pynacl.readthedocs.io/
- **Cron Expression**: https://crontab.guru/

---

## 📚 Quick Recipes

### Recipe 1: Fresh Setup (5 minutes)

```bash
# 1. Install tools (one-time)
winget install GitHub.cli Git.Git Python.Python.3.11
pip install pynacl

# 2. Prepare files
mkdir datagram-orchestrator && cd datagram-orchestrator
# Copy scripts

# 3. Setup
.\setup_datagram.ps1
1 → 2 → 4 → 5 → 6 → 7 → 8 → 9 → 10
```

### Recipe 2: Add 10 New Accounts (2 minutes)

```bash
# 1. Add tokens
cat new_tokens.txt >> config/tokens.txt

# 2. Run
.\setup_datagram.ps1
5 → 6 → 7 → 8
```

### Recipe 3: Update All API Keys (1 minute)

```bash
# 1. Edit keys
notepad config/api_keys.txt

# 2. Redistribute
.\setup_datagram.ps1
13 → 8 → 10
```

---

**🎯 Pro Tip**: Bookmark this file for instant reference during operations!

**💡 Remember**: 
- Always validate tokens after importing (Menu 5)
- Clean cache when you want fresh state (Menu 13)
- Check logs when debugging (Menu 12 or logs/setup.log)

---

**Last Updated**: 2024
**Maintained By**: Code-Architect
