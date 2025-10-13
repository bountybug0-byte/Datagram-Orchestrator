# 🚀 Datagram 24/7 Multi-Node Orchestrator

Enterprise-grade automation system untuk menjalankan multiple Datagram nodes secara **parallel** dan **non-stop** menggunakan GitHub Actions dengan dukungan full orchestration dari local terminal.

[![GitHub Actions](https://img.shields.io/badge/GitHub-Actions-2088FF?logo=github-actions&logoColor=white)](https://github.com/features/actions)
[![PowerShell](https://img.shields.io/badge/PowerShell-5.1%2B-5391FE?logo=powershell&logoColor=white)](https://docs.microsoft.com/en-us/powershell/)
[![Bash](https://img.shields.io/badge/Bash-4.0%2B-4EAA25?logo=gnu-bash&logoColor=white)](https://www.gnu.org/software/bash/)

---

## 📋 Table of Contents

- [✨ Features](#-features)
- [🏗️ Architecture](#️-architecture)
- [📦 Prerequisites](#-prerequisites)
- [🚀 Quick Start](#-quick-start)
- [📖 Detailed Setup Guide](#-detailed-setup-guide)
- [⚙️ Configuration](#️-configuration)
- [🎯 Usage Examples](#-usage-examples)
- [🔧 Troubleshooting](#-troubleshooting)
- [📊 Monitoring](#-monitoring)
- [🤝 Contributing](#-contributing)

---

## ✨ Features

### 🎯 Core Features

- ✅ **True Parallel Execution** - Semua node berjalan bersamaan, tidak sequential
- ✅ **24/7 Auto-Restart** - Triple-layer restart mechanism (loop + timeout + cron)
- ✅ **Multi-Account Support** - Unlimited API keys dalam satu secret
- ✅ **Zero Configuration** - Setup sekali, run forever
- ✅ **Health Monitoring** - Real-time status tracking per node
- ✅ **Graceful Shutdown** - Proper cleanup saat restart

### 🤖 Orchestration Features

- ✅ **Auto Invite Collaborators** - Bulk invitation management
- ✅ **Auto Accept Invitations** - Automated invitation acceptance
- ✅ **Auto Set Secrets** - Encrypted secret distribution via Codespaces API
- ✅ **Token Validation** - Smart caching untuk performance
- ✅ **Retry Mechanism** - Connection failure handling
- ✅ **Progress Tracking** - File-based state management

### 🛠️ Technical Features

- ✅ **Cross-Platform** - Windows (PowerShell) & Linux/Mac (Bash)
- ✅ **GitHub CLI Integration** - Native gh command usage
- ✅ **Sodium Encryption** - Secure secret storage dengan PyNaCl
- ✅ **JSON Configuration** - Clean, readable config files
- ✅ **Logging System** - Detailed operation logs
- ✅ **Error Recovery** - Intelligent retry dengan exponential backoff

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   LOCAL ORCHESTRATOR                         │
│  ┌────────────────────────────────────────────────────┐     │
│  │  setup_datagram.ps1 / setup_datagram.sh            │     │
│  │  ┌──────────────────────────────────────────────┐  │     │
│  │  │  1. Initialize Configuration                 │  │     │
│  │  │  2. Import API Keys & GitHub Tokens         │  │     │
│  │  │  3. Validate & Cache Tokens                 │  │     │
│  │  │  4. Auto Invite Collaborators               │  │     │
│  │  │  5. Auto Accept Invitations                 │  │     │
│  │  │  6. Auto Set Secrets (Encrypted)            │  │     │
│  │  │  7. Deploy Workflow to GitHub               │  │     │
│  │  │  8. Trigger & Monitor                       │  │     │
│  │  └──────────────────────────────────────────────┘  │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
                             ↓
                    Push & Auto-Trigger
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                  GITHUB ACTIONS RUNNER                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Job: setup-matrix                                   │   │
│  │  → Parse DATAGRAM_API_KEYS secret                    │   │
│  │  → Generate dynamic matrix                           │   │
│  └──────────────────────────────────────────────────────┘   │
│                             ↓                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Job: run-nodes (Parallel Matrix Strategy)          │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐      │   │
│  │  │  Node #1   │ │  Node #2   │ │  Node #N   │      │   │
│  │  │ ─────────  │ │ ─────────  │ │ ─────────  │      │   │
│  │  │ API_KEY_1  │ │ API_KEY_2  │ │ API_KEY_N  │      │   │
│  │  │            │ │            │ │            │      │   │
│  │  │ [Running]  │ │ [Running]  │ │ [Running]  │      │   │
│  │  │ 24/7 Loop  │ │ 24/7 Loop  │ │ 24/7 Loop  │      │   │
│  │  │            │ │            │ │            │      │   │
│  │  │ Timeout:   │ │ Timeout:   │ │ Timeout:   │      │   │
│  │  │ 5h 50m     │ │ 5h 50m     │ │ 5h 50m     │      │   │
│  │  └────────────┘ └────────────┘ └────────────┘      │   │
│  └──────────────────────────────────────────────────────┘   │
│                             ↓                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Job: monitor                                        │   │
│  │  → Health check all nodes                            │   │
│  │  → Generate report                                   │   │
│  │  → Upload logs (on failure)                          │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                             ↓
                   Auto-Restart via Cron
                   (Every 5 hours: 0 */5 * * *)
```

---

## 📦 Prerequisites

### Required Tools

#### Windows (PowerShell)

```powershell
# 1. PowerShell 5.1+ (sudah built-in di Windows 10+)
$PSVersionTable.PSVersion

# 2. GitHub CLI
winget install --id GitHub.cli

# 3. Git
winget install --id Git.Git

# 4. Python 3.8+ (untuk encryption)
winget install --id Python.Python.3.11

# 5. PyNaCl (untuk secret encryption)
pip install pynacl
```

#### Linux/macOS (Bash)

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y gh git jq python3 python3-pip
pip3 install pynacl

# macOS (Homebrew)
brew install gh git jq python3
pip3 install pynacl

# Verify installations
gh --version
git --version
jq --version
python3 --version
python3 -c "import nacl; print('PyNaCl OK')"
```

### GitHub Requirements

1. **Personal Access Token (PAT)** dengan scopes:
   - ✅ `repo` (full control)
   - ✅ `workflow` (manage workflows)
   - ✅ `admin:org` (manage collaborators)
   - ✅ `codespace` (untuk set secrets via Codespaces API)

2. **Repository**:
   - Private/Public repository
   - Actions enabled
   - Collaborator access untuk multi-account

---

## 🚀 Quick Start

### Method 1: Automated Setup (Recommended)

#### Windows PowerShell

```powershell
# 1. Clone or create project directory
mkdir datagram-orchestrator
cd datagram-orchestrator

# 2. Download scripts
# (Copy script content dari artifacts ke setup_datagram.ps1)

# 3. Run orchestrator
.\setup_datagram.ps1

# 4. Follow interactive menu:
#    1 → Initialize Configuration
#    2 → Import API Keys
#    4 → Import GitHub Tokens
#    5 → Validate Tokens
#    6 → Auto Invite Collaborators
#    7 → Auto Accept Invitations
#    8 → Auto Set Secrets
#    9 → Deploy to GitHub
#    10 → Trigger Workflow
```

#### Linux/macOS Bash

```bash
# 1. Clone or create project directory
mkdir datagram-orchestrator
cd datagram-orchestrator

# 2. Download script
# (Copy script content ke setup_datagram.sh)
chmod +x setup_datagram.sh

# 3. Run orchestrator
./setup_datagram.sh

# Follow same steps as Windows
```

### Method 2: Manual Setup

```bash
# 1. Create directory structure
mkdir -p .github/workflows config logs

# 2. Create api_keys.txt
cat > config/api_keys.txt <<EOF
your_api_key_1
your_api_key_2
your_api_key_3
EOF

# 3. Create workflow file
# Copy content dari datagram-runner.yml artifact

# 4. Set GitHub Secret
gh secret set DATAGRAM_API_KEYS < config/api_keys.txt

# 5. Push to GitHub
git init
git add .
git commit -m "Initial setup"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main

# 6. Trigger workflow
gh workflow run datagram-runner.yml
```

---

## 📖 Detailed Setup Guide

### Step 1: Configuration Initialization

```powershell
# Run orchestrator
.\setup_datagram.ps1

# Menu 1: Initialize Configuration
# Input:
#   - Main GitHub username: your_username
#   - Repository name: datagram-runner
#   - Personal Access Token: ghp_xxxxxxxxxxxxx

# Output: config/config.json
{
  "main_account_username": "your_username",
  "main_repo_name": "datagram-runner",
  "main_token": "ghp_xxxxxxxxxxxxx"
}
```

### Step 2: API Keys Import

**Format 1: Manual Input**
```
Menu 2 → Option 1
API Key #1: key_abc123xyz
API Key #2: key_def456uvw
(Enter kosong untuk selesai)
```

**Format 2: From File**
```
Menu 2 → Option 2
Path file: D:\keys\datagram_keys.txt

# File content:
key_abc123xyz
key_def456uvw
key_ghi789rst
```

### Step 3: GitHub Tokens Import

```
Menu 4: Import GitHub Tokens
Path file: D:\tokens\github_tokens.txt

# File content (PAT format):
ghp_1234567890abcdefghijklmnopqrst1
ghp_abcdefghijklmnopqrstuvwxyz1234
ghp_zyxwvutsrqponmlkjihgfedcba9876
```

### Step 4: Token Validation & Caching

```
Menu 5: Validate GitHub Tokens

Output:
[1/3] Validating... ✅ @account1
[2/3] Validating... ✅ @account2 (cached)
[3/3] Validating... ❌ Invalid token

Valid Tokens: 2/3

# Creates: config/token_cache.json
{
  "ghp_123...": "account1",
  "ghp_abc...": "account2"
}
```

### Step 5: Auto Invite Collaborators

```
Menu 6: Auto Invite Collaborators

Process:
1. Load valid tokens from cache
2. Filter: exclude main account & already invited
3. Check existing collaborator status
4. Send invitations

Output:
[1/5] @account1... ✅ Invited
[2/5] @account2... ℹ️  Already collaborator
[3/5] @account3... ✅ Invited
...

Berhasil: 5/5

# Creates: config/invited_users.txt
account1
account2
account3
```

### Step 6: Auto Accept Invitations

```
Menu 7: Auto Accept Invitations

Process:
1. Iterate through all tokens
2. Check invitation list via API
3. Accept matching repository invitation

Output:
[1/5] @account1... ✅ Accepted
[2/5] @account2... ℹ️  No invitation
[3/5] @account3... ✅ Already collaborator
...

Summary:
  ✅ Accepted       : 3
  👥 Already member : 1
  ℹ️  No invitation  : 1

# Creates: config/accepted_users.txt
```

### Step 7: Auto Set Secrets (Encrypted)

```
Menu 8: Auto Set Secrets

Process:
1. Load API keys from config/api_keys.txt
2. For each token:
   a. Get repository ID
   b. Get public encryption key
   c. Encrypt API keys using PyNaCl
   d. Set via Codespaces Secrets API

Output:
[1/5] @account1
   🔍 Get repo ID... ✅ 123456789
   🔑 Get public key... ✅
   🔐 Set DATAGRAM_API_KEYS... ✅
   📊 Berhasil: 1/1

[2/5] @account2
   🔍 Get repo ID... ✅ 123456789
   🔑 Get public key... ✅
   🔐 Set DATAGRAM_API_KEYS... ✅
   📊 Berhasil: 1/1

Summary:
  ✅ Success : 5
  ⏭️  Skipped : 0

# Creates: config/secrets_set.txt
```

**Important Notes:**
- Secret name: `DATAGRAM_API_KEYS`
- Encryption: Sodium sealed box (libsodium)
- Scope: User-level Codespaces secret
- Repository access: Auto-configured per account

### Step 8: Deploy to GitHub

```
Menu 9: Deploy to GitHub

Process:
1. Check if repository exists
2. Create if needed
3. Initialize git (if .git not exists)
4. Add workflow file check
5. Commit & push

Output:
🔍 Checking repository... ✅ Found
📦 Initializing git repository...
📝 Checking workflow file...
🚀 Deploying to GitHub...

✅ Deployment successful!
Repository: https://github.com/your_username/datagram-runner
Actions: https://github.com/your_username/datagram-runner/actions
```

### Step 9: Trigger & Monitor

```
Menu 10: Trigger Workflow

✅ Workflow triggered successfully!
View at: https://github.com/.../actions

🔍 Fetching latest run...
   Run ID: 123456789
   Status: in_progress
   URL: https://github.com/.../runs/123456789

---

Menu 11: Show Workflow Status

Recent Workflow Runs:
═══════════════════════════════════════

✅ Run #123456789
   Workflow: Datagram 24/7 Multi-Node Runner
   Status: completed (success)
   Created: 2024-01-15T10:30:00Z

🔄 Run #123456788
   Workflow: Datagram 24/7 Multi-Node Runner
   Status: in_progress
   Created: 2024-01-15T05:30:00Z
```

---

## ⚙️ Configuration

### config/config.json

```json
{
  "main_account_username": "your_github_username",
  "main_repo_name": "datagram-runner",
  "main_token": "ghp_your_personal_access_token"
}
```

### config/api_keys.txt

```
key_abc123xyz456def789ghi012jkl345mno
key_pqr678stu901vwx234yza567bcd890efg
key_hij123klm456nop789qrs012tuv345wxy
```

**Supported Formats:**
- One key per line (recommended)
- Comma-separated (for GitHub Secret)
- JSON array (for programmatic usage)

### config/tokens.txt

```
ghp_1234567890abcdefghijklmnopqrst123456789
ghp_abcdefghijklmnopqrstuvwxyz0123456789abc
ghp_zyxwvutsrqponmlkjihgfedcba9876543210zy
```

**Requirements:**
- Must start with `ghp_`
- Valid GitHub Personal Access Token
- Required scopes: repo, workflow, admin:org, codespace

---

## 🎯 Usage Examples

### Example 1: Setup dari Zero

```powershell
# 1. Buat project baru
mkdir my-datagram-nodes
cd my-datagram-nodes

# 2. Siapkan files
# - Copy setup_datagram.ps1
# - Copy datagram-runner.yml ke .github/workflows/

# 3. Siapkan data
# Buat file api_keys.txt dan tokens.txt

# 4. Run orchestrator
.\setup_datagram.ps1

# 5. Execute secara berurutan:
1 → Init config
2 → Import API keys
4 → Import tokens
5 → Validate tokens
6 → Invite collaborators
7 → Accept invitations
8 → Set secrets
9 → Deploy
10 → Trigger
```

### Example 2: Update API Keys

```powershell
# Jika ingin menambah/update API keys:

# 1. Edit file
notepad config/api_keys.txt

# 2. Run orchestrator
.\setup_datagram.ps1

# 3. Reset secrets_set tracking
13 → Clean Cache

# 4. Re-set secrets
8 → Auto Set Secrets

# 5. Restart workflow
10 → Trigger Workflow
```

### Example 3: Add New Accounts

```powershell
# 1. Add tokens ke file
echo "ghp_new_token_here" >> config/tokens.txt

# 2. Run orchestrator
.\setup_datagram.ps1

# 3. Validate new token
5 → Validate Tokens

# 4. Invite
6 → Auto Invite

# 5. Accept (dari akun baru)
7 → Auto Accept

# 6. Set secrets (dari akun baru)
8 → Auto Set Secrets
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. "GitHub CLI not found"

**Solution:**
```bash
# Windows
winget install GitHub.cli

# Linux
sudo apt install gh

# macOS
brew install gh

# Authenticate
gh auth login
```

#### 2. "PyNaCl import error"

**Solution:**
```bash
pip install pynacl

# If multiple Python versions:
pip3 install pynacl
python3 -m pip install pynacl
```

#### 3. "API rate limit exceeded"

**Solution:**
- Wait 1 hour for rate limit reset
- Use authenticated requests (set GH_TOKEN)
- Reduce concurrent operations

#### 4. "Secret encryption failed"

**Solution:**
```bash
# Verify PyNaCl installation
python3 -c "from nacl import public; print('OK')"

# Re-install if needed
pip3 uninstall pynacl
pip3 install pynacl
```

#### 5. "Workflow not triggered"

**Solution:**
```bash
# Check workflow file exists
ls .github/workflows/datagram-runner.yml

# Check Actions enabled in repo settings
# Repository → Settings → Actions → Allow all actions

# Manual trigger
gh workflow run datagram-runner.yml
```

### Debug Mode

```bash
# Enable verbose output
export GH_DEBUG=1

# Check logs
cat logs/setup.log

# GitHub Actions logs
gh run list
gh run view <run_id> --log
```

---

## 📊 Monitoring

### Real-time Monitoring

```bash
# Via GitHub CLI
gh run list --limit 5
gh run view <run_id> --log-failed

# Via Web
https://github.com/YOUR_USERNAME/YOUR_REPO/actions
```

### Workflow Status

- ✅ **Success**: All nodes running normally
- 🔄 **In Progress**: Nodes currently executing
- ⏳ **Queued**: Waiting for runner availability
- ❌ **Failed**: Check logs for errors

### Performance Metrics

```
Per Node:
- Uptime: ~5 hours per iteration
- Restart Interval: ~10 seconds cooldown
- Max Iterations: 100 (configurable)
- Total Runtime: ~500 hours max

Overall System:
- Parallel Nodes: Unlimited (GitHub limit: 20-180)
- Auto-Restart: Every 5 hours via cron
- Zero Downtime: <1 minute gap during restart
```

---

## 🤝 Contributing

### Development Setup

```bash
git clone https://github.com/YOUR_USERNAME/datagram-orchestrator
cd datagram-orchestrator

# Test PowerShell script
pwsh -File setup_datagram.ps1

# Test Bash script
bash -x setup_datagram.sh
```

### Code Style

- **PowerShell**: PascalCase functions, descriptive names
- **Bash**: snake_case functions, POSIX-compliant
- **Comments**: Explain "why", not "what"
- **Error Handling**: Always handle edge cases

---

## 📄 License

MIT License - Feel free to use and modify

---

## 🙏 Acknowledgments

- Datagram Network Team
- GitHub Actions Community
- PyNaCl Developers

---

## 📞 Support

- **Issues**: Create GitHub issue dengan detail log
- **Discussions**: GitHub Discussions untuk Q&A
- **Documentation**: Update README jika ada improvement

---

**Built with ❤️ by Code-Architect**

*"Kode bukan hanya tentang membuat sesuatu berfungsi, tapi membuat sesuatu yang bertahan."*
