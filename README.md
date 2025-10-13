# 🚀 Datagram Orchestrator v3.0

Automated GitHub Actions orchestrator for running Datagram nodes across multiple accounts 24/7.

---

## 📋 Prerequisites

### Required Software
- **Python 3.11+** ([Download](https://www.python.org/downloads/))
- **GitHub CLI** ([Download](https://cli.github.com/))
- **Git** ([Download](https://git-scm.com/downloads))

### GitHub Requirements
- GitHub Personal Access Token with permissions:
  - ✅ `repo` (Full control of repositories)
  - ✅ `workflow` (Update workflows)
  - ✅ `admin:org` (Manage organization)
  - ✅ `codespace` (Manage codespace secrets)

Generate token: https://github.com/settings/tokens

---

## ⚡ Quick Start

### 1. Install Dependencies

**Windows:**
```powershell
# Install tools
winget install GitHub.cli Git.Git Python.Python.3.11

# Install Python dependencies
pip install -r requirements.txt
```

**Linux/macOS:**
```bash
# Ubuntu/Debian
sudo apt install gh git python3-pip
pip3 install -r requirements.txt

# macOS
brew install gh git python3
pip3 install -r requirements.txt
```

### 2. Authenticate GitHub CLI
```bash
gh auth login
```

### 3. Run Orchestrator

**Windows:**
```powershell
.\start.ps1
```

**Linux/macOS:**
```bash
chmod +x start.sh
./start.sh
```

---

## 📂 Project Structure

```
datagram-orchestrator/
├── .github/workflows/
│   └── datagram-runner.yml       # GitHub Actions workflow (auto-restart every 5h)
├── config/
│   ├── api_keys.txt              # Your Datagram API keys (one per line)
│   ├── tokens.txt                # GitHub PATs (one per line)
│   ├── config.json               # Main account configuration
│   └── .cache/                   # Auto-generated tracking files
├── logs/
│   └── setup.log                 # Execution logs
├── orchestrator/
│   ├── core.py                   # Main orchestration logic
│   └── helpers.py                # Utility functions
├── main.py                       # Entry point
├── start.ps1                     # Windows launcher
├── start.sh                      # Linux/macOS launcher
└── requirements.txt              # Python dependencies
```

---

## ⚙️ Configuration

### Step 1: Initialize Configuration (Menu 1)
```json
{
  "main_account_username": "your_github_username",
  "main_repo_name": "datagram-runner",
  "main_token": "ghp_your_main_account_token"
}
```

### Step 2: Import API Keys (Menu 2)
**File:** `config/api_keys.txt`
```
key_abc123xyz456def789ghi012jkl345mno
key_pqr678stu901vwx234yza567bcd890efg
key_hij123klm456nop789qrs012tuv345wxy
```

### Step 3: Import GitHub Tokens (Menu 4)
**File:** `config/tokens.txt`
```
ghp_1234567890abcdefghij
ghp_abcdefghijklmnopqrst
ghp_uvwxyz0123456789abcd
```

---

## 🎯 Usage Workflow

### Complete Setup (First Time)
```
1. Menu 1 → Initialize Configuration
2. Menu 2 → Import API Keys
3. Menu 4 → Import GitHub Tokens
4. Menu 5 → Validate GitHub Tokens
5. Menu 6 → Auto Invite Collaborators
6. Menu 7 → Auto Accept Invitations
7. Menu 8 → Auto Set Secrets
8. Menu 9 → Deploy to GitHub
9. Menu 10 → Trigger Workflow
```

### Daily Operations

**Check Status:**
```bash
Menu 11 → Show Workflow Status
```

**View Logs:**
```bash
Menu 12 → View Logs
```

**Update API Keys:**
```bash
1. Edit config/api_keys.txt
2. Menu 13 → Clean Cache
3. Menu 8 → Auto Set Secrets
4. Menu 10 → Trigger Workflow
```

**Add New Accounts:**
```bash
1. Add new tokens to config/tokens.txt
2. Menu 5 → Validate Tokens
3. Menu 6 → Invite Collaborators
4. Menu 7 → Accept Invitations
5. Menu 8 → Set Secrets
```

---

## 🔐 Security Best Practices

### Token Management
- ✅ **DO:** Store tokens in `config/` directory (already gitignored)
- ✅ **DO:** Rotate tokens every 90 days
- ✅ **DO:** Use tokens with minimum required permissions
- ❌ **DON'T:** Share tokens publicly
- ❌ **DON'T:** Commit tokens to git

### API Keys Protection
- API keys are encrypted using PyNaCl before being sent to GitHub
- Keys are stored as GitHub Codespace secrets (not repository secrets)
- Each account only has access to keys assigned to them

### Revoke Compromised Tokens
```bash
# GitHub Settings → Developer settings → Personal access tokens → Revoke
# Then regenerate and re-run Menu 4 → 5 → 8
```

---

## 🔧 Troubleshooting

### Common Errors

| Error | Solution |
|-------|----------|
| `gh: command not found` | Install GitHub CLI: `winget install GitHub.cli` |
| `ModuleNotFoundError: nacl` | Install dependencies: `pip install -r requirements.txt` |
| `API rate limit exceeded` | Wait 1 hour or use fewer accounts |
| `Resource not accessible` | Regenerate token with correct permissions |
| `refusing to allow OAuth` | Authorize token for organization (SSO) |

### Debug Commands

**Check GitHub CLI Auth:**
```bash
gh auth status
```

**View Workflow Logs:**
```bash
gh run list
gh run view <run-id> --log
```

**Check Token Validity:**
```bash
Menu 5 → Validate GitHub Tokens
```

**Reset Everything:**
```bash
Menu 13 → Clean Cache
# Then re-run setup (Menu 5-8)
```

---

## 📊 How It Works

### Execution Flow
```
1. Parse API Keys → Split into JSON matrix
2. Spawn Parallel Nodes → Max 50 concurrent jobs
3. Each Node:
   - Downloads Datagram CLI
   - Runs: datagram-cli -key <KEY>
   - Auto-restart every 5 hours
   - Max 100 iterations per job
4. Monitor & Report → Upload logs on failure
5. Cron Trigger → Restart workflow every 5 hours
```

### GitHub Actions Architecture
```
Main Repo (your account)
└── Workflow: datagram-runner.yml
    ├── Job 1: Setup Matrix (parse API keys)
    ├── Job 2: Run Nodes (parallel execution)
    │   ├── Node #1 (runner: ubuntu-latest)
    │   ├── Node #2 (runner: ubuntu-latest)
    │   └── Node #N (max 50 parallel)
    ├── Job 3: Monitor (health check)
    └── Job 4: Schedule Next Run (cron)
```

### Collaborator Accounts
- Each account accepts invitation to main repo
- Sets DATAGRAM_API_KEYS secret in their Codespace
- Workflow runs under their account (distributes load)
- Secrets are isolated per account

---

## 🎛️ Customization

### Adjust Auto-Restart Timing
**File:** `.github/workflows/datagram-runner.yml`
```yaml
schedule:
  - cron: '0 */3 * * *'  # Every 3 hours
  - cron: '0 */6 * * *'  # Every 6 hours
  - cron: '0 0 * * *'    # Once daily
```

### Change Parallel Execution Limit
```yaml
strategy:
  max-parallel: 20   # Run max 20 nodes simultaneously
  max-parallel: 50   # Default
  max-parallel: 100  # Requires GitHub Team/Enterprise plan
```

### Adjust Node Restart Behavior
```yaml
env:
  MAX_RETRIES: 50      # Reduce iterations
  RESTART_DELAY: 30    # Increase cooldown
```

### Change Job Timeout
```yaml
timeout-minutes: 330  # 5h 30m
timeout-minutes: 280  # 4h 40m
```

---

## 📈 Monitoring

### Real-time Status
```bash
# Via orchestrator
Menu 11 → Show Workflow Status

# Via GitHub CLI
gh run list --limit 10
gh run watch <run-id>

# Via browser
https://github.com/<username>/<repo>/actions
```

### Log Analysis
```bash
# View orchestrator logs
cat logs/setup.log

# View GitHub Actions logs
gh run view <run-id> --log
gh run view <run-id> --log-failed

# Download logs
gh run download <run-id>
```

### Performance Metrics
```bash
# Check success rate
gh run list --limit 100 --json conclusion | \
  jq '[.[] | select(.conclusion=="success")] | length'

# View run durations
gh run list --limit 10 --json durationMs
```

---

## ⚠️ Known Limitations

### GitHub Actions Free Tier Limits
| Resource | Public Repos | Private Repos |
|----------|--------------|---------------|
| Concurrent jobs | 20 | 20 |
| Job execution time | 6 hours | 6 hours |
| Workflow run time | 35 days | 35 days |
| Storage | 500 MB | 500 MB |
| Minutes | Unlimited | 2000/month |

### Current Issues
1. **Secret Management:** Temporary file created during encryption (security risk)
2. **Git Operations:** Force push without safety checks (data loss risk)
3. **Rate Limiting:** Basic retry logic only (needs exponential backoff)
4. **No Rollback:** Failed batch operations cannot be rolled back
5. **Limited Validation:** Minimal input validation for usernames/tokens

### Workarounds
- Use **public repositories** for unlimited minutes
- For private repos, consider **self-hosted runners**
- Rotate accounts to avoid rate limits
- Monitor logs regularly for failures

---

## 🔄 Update & Maintenance

### Update API Keys
```bash
1. Edit config/api_keys.txt
2. Menu 13 → Clean Cache (reset secrets_set.txt)
3. Menu 8 → Auto Set Secrets
4. Menu 10 → Trigger Workflow
```

### Add New Accounts
```bash
1. Add token to config/tokens.txt
2. Menu 5 → Validate Tokens
3. Menu 6 → Invite Collaborators
4. Menu 7 → Accept Invitations
5. Menu 8 → Set Secrets
```

### Update Workflow File
```bash
1. Edit .github/workflows/datagram-runner.yml
2. git add . && git commit -m "Update workflow"
3. git push
4. Menu 10 → Trigger Workflow (test changes)
```

### Rotate GitHub Tokens
```bash
1. Generate new tokens at: https://github.com/settings/tokens
2. Update config/tokens.txt and config/config.json
3. Menu 13 → Clean Cache
4. Menu 5 → Validate Tokens
5. Menu 8 → Auto Set Secrets
6. Revoke old tokens from GitHub Settings
```

---

## 🆘 Emergency Procedures

### Stop All Workflows
```bash
# Via GitHub CLI
gh run list --status=in_progress --json databaseId --jq '.[].databaseId' | \
  xargs -I {} gh run cancel {}

# Via browser
Actions → Select workflow → Cancel workflow
```

### Rollback Deployment
```bash
# Revert to previous commit
git log --oneline -5
git revert <commit-hash>
git push

# Or force rollback
git reset --hard <old-commit>
git push --force
```

### Complete Reset
```bash
# ⚠️ WARNING: Deletes all tracking data
gh run list --status=in_progress --json databaseId --jq '.[].databaseId' | \
  xargs -I {} gh run cancel {}

rm -rf config/.cache/*
gh secret delete DATAGRAM_API_KEYS

# Re-run setup from scratch
Menu 1 → 2 → 4 → 5 → 6 → 7 → 8 → 9 → 10
```

---

## 📚 Additional Resources

- **GitHub CLI Manual:** https://cli.github.com/manual/
- **GitHub Actions Docs:** https://docs.github.com/en/actions
- **Datagram Network:** https://docs.datagram.network/
- **Cron Expression Generator:** https://crontab.guru/
- **Quick Reference Guide:** See `QUICK_REFERENCE.md`

---

## 📄 License

This project is provided as-is for personal use. Modify and distribute freely.

---

## 🤝 Support

- **Issues:** Create issue in GitHub repository
- **Logs:** Check `logs/setup.log` for debugging
- **Status:** Use Menu 11 for workflow status

---

**Last Updated:** 2024  
**Version:** 3.1 (Security Patched)  
**Maintained By:** Code-Architect

---

## 🎯 Quick Commands Cheat Sheet

```bash
# First time setup
1 → 2 → 4 → 5 → 6 → 7 → 8 → 9 → 10

# Update API keys
Edit api_keys.txt → 13 → 8 → 10

# Add new accounts
Edit tokens.txt → 5 → 6 → 7 → 8

# Monitor status
11 (Show Status) | 12 (View Logs)

# Emergency stop
gh run list --status=in_progress | cancel all
```

---

**Pro Tip:** Bookmark this README for quick reference during operations! 🚀
