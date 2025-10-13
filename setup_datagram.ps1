# =============================================
# DATAGRAM ORCHESTRATOR - PowerShell Edition
# Inspired by setup.py architecture
# =============================================

# Color Functions
function Write-Success { param($msg) Write-Host "✅ $msg" -ForegroundColor Green }
function Write-Error { param($msg) Write-Host "❌ $msg" -ForegroundColor Red }
function Write-Info { param($msg) Write-Host "ℹ️  $msg" -ForegroundColor Cyan }
function Write-Warning { param($msg) Write-Host "⚠️  $msg" -ForegroundColor Yellow }
function Write-Header { 
    param($msg) 
    Write-Host "`n═══════════════════════════════════════" -ForegroundColor Magenta
    Write-Host "  $msg" -ForegroundColor Magenta
    Write-Host "═══════════════════════════════════════`n" -ForegroundColor Magenta
}

# Configuration Files
$CONFIG_DIR = "config"
$LOGS_DIR = "logs"
$API_KEYS_FILE = "$CONFIG_DIR/api_keys.txt"
$TOKENS_FILE = "$CONFIG_DIR/tokens.txt"
$CONFIG_FILE = "$CONFIG_DIR/config.json"
$TOKEN_CACHE_FILE = "$CONFIG_DIR/token_cache.json"
$INVITED_USERS_FILE = "$CONFIG_DIR/invited_users.txt"
$ACCEPTED_USERS_FILE = "$CONFIG_DIR/accepted_users.txt"
$SECRETS_SET_FILE = "$CONFIG_DIR/secrets_set.txt"
$LOG_FILE = "$LOGS_DIR/setup.log"

# =============================================
# HELPER FUNCTIONS
# =============================================

function Initialize-Directories {
    @($CONFIG_DIR, $LOGS_DIR) | ForEach-Object {
        if (-not (Test-Path $_)) {
            New-Item -ItemType Directory -Path $_ -Force | Out-Null
            Write-Info "Created directory: $_"
        }
    }
}

function Write-Log {
    param($message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $message" | Out-File -FilePath $LOG_FILE -Append -Encoding UTF8
}

function Test-GitHubCLI {
    try {
        $null = gh --version
        return $true
    } catch {
        Write-Error "GitHub CLI (gh) tidak terinstal!"
        Write-Info "Install dari: https://cli.github.com/"
        return $false
    }
}

function Read-FileLines {
    param($filePath)
    if (Test-Path $filePath) {
        return Get-Content $filePath | Where-Object { $_.Trim() -ne "" }
    }
    return @()
}

function Add-ToFile {
    param($filePath, $content)
    $content | Out-File -FilePath $filePath -Append -Encoding UTF8
}

function Load-JsonFile {
    param($filePath)
    if (Test-Path $filePath) {
        try {
            return Get-Content $filePath -Raw | ConvertFrom-Json
        } catch {
            return @{}
        }
    }
    return @{}
}

function Save-JsonFile {
    param($filePath, $data)
    $data | ConvertTo-Json -Depth 10 | Out-File -FilePath $filePath -Encoding UTF8
}

function Invoke-GitHubAPI {
    param(
        [string]$Command,
        [string]$Token,
        [int]$MaxRetries = 3,
        [int]$RetryDelay = 5
    )
    
    $env:GH_TOKEN = $Token
    $attempt = 0
    
    while ($attempt -lt $MaxRetries) {
        try {
            $result = Invoke-Expression "gh $Command 2>&1"
            if ($LASTEXITCODE -eq 0) {
                return @{ Success = $true; Output = $result }
            } else {
                $errorMsg = $result -join "`n"
                if ($errorMsg -match "api.github.com|timeout|connection") {
                    $attempt++
                    if ($attempt -lt $MaxRetries) {
                        Write-Warning "Connection failed. Retry $attempt/$MaxRetries in ${RetryDelay}s..."
                        Start-Sleep -Seconds $RetryDelay
                        continue
                    }
                }
                return @{ Success = $false; Output = $errorMsg }
            }
        } catch {
            return @{ Success = $false; Output = $_.Exception.Message }
        }
    }
    
    return @{ Success = $false; Output = "Max retries exceeded" }
}

# =============================================
# FEATURE 1: SETUP CONFIGURATION
# =============================================

function Initialize-Configuration {
    Write-Header "SETUP KONFIGURASI"
    
    $config = @{}
    
    # Main Account
    Write-Host "📝 Konfigurasi Akun Utama" -ForegroundColor Yellow
    $config.main_account_username = Read-Host "Username GitHub utama"
    $config.main_repo_name = Read-Host "Nama repository (misal: datagram-runner)"
    $config.main_token = Read-Host "GitHub Personal Access Token (main account)" -AsSecureString
    $config.main_token = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($config.main_token)
    )
    
    Save-JsonFile -filePath $CONFIG_FILE -data $config
    Write-Success "Konfigurasi disimpan ke $CONFIG_FILE"
    Write-Log "Configuration initialized"
}

# =============================================
# FEATURE 2: API KEYS MANAGEMENT
# =============================================

function Import-ApiKeys {
    Write-Header "IMPORT API KEYS"
    
    Write-Info "Pilih metode import:"
    Write-Host "1. Input manual (satu per satu)"
    Write-Host "2. Import dari file .txt"
    Write-Host "3. Convert CSV/Excel ke format txt"
    
    $choice = Read-Host "`nPilihan (1/2/3)"
    
    switch ($choice) {
        "1" {
            $keys = @()
            Write-Info "Masukkan API keys (Enter kosong untuk selesai):"
            
            do {
                $key = Read-Host "API Key #$($keys.Count + 1)"
                if ($key) { $keys += $key }
            } while ($key)
            
            if ($keys.Count -gt 0) {
                $keys | Out-File -FilePath $API_KEYS_FILE -Encoding UTF8
                Write-Success "Berhasil menyimpan $($keys.Count) API keys"
            }
        }
        
        "2" {
            $sourceFile = Read-Host "Path file .txt"
            if (Test-Path $sourceFile) {
                Copy-Item $sourceFile $API_KEYS_FILE -Force
                $count = (Get-Content $API_KEYS_FILE).Count
                Write-Success "Berhasil import $count API keys"
            } else {
                Write-Error "File tidak ditemukan"
            }
        }
        
        "3" {
            Write-Warning "Fitur ini memerlukan module ImportExcel"
            Write-Info "Install dengan: Install-Module ImportExcel -Scope CurrentUser"
        }
    }
    
    Write-Log "API keys imported"
}

function Show-ApiKeysStatus {
    Write-Header "STATUS API KEYS"
    
    if (-not (Test-Path $API_KEYS_FILE)) {
        Write-Warning "File API keys belum ada. Jalankan Import API Keys terlebih dahulu."
        return
    }
    
    $keys = Read-FileLines $API_KEYS_FILE
    $keysCount = $keys.Count
    
    Write-Info "Total API Keys: $keysCount"
    
    if ($keysCount -gt 0) {
        Write-Host "`nPreview (first 3):" -ForegroundColor Cyan
        $keys | Select-Object -First 3 | ForEach-Object {
            $preview = $_.Substring(0, [Math]::Min(10, $_.Length)) + "..." + 
                       $_.Substring([Math]::Max(0, $_.Length - 5))
            Write-Host "  🔑 $preview"
        }
    }
    
    # Check secret format
    Write-Host "`n📋 Format untuk GitHub Secret:" -ForegroundColor Yellow
    Write-Host "Secret Name: DATAGRAM_API_KEYS"
    Write-Host "Secret Value (pilih salah satu):`n"
    
    Write-Host "Format 1 - Newline separated (Recommended):"
    $keys | Select-Object -First 2 | ForEach-Object { Write-Host $_ }
    Write-Host "..."
    
    Write-Host "`nFormat 2 - Comma separated:"
    Write-Host ($keys -join ",").Substring(0, [Math]::Min(80, ($keys -join ",").Length)) + "..."
}

# =============================================
# FEATURE 3: GITHUB TOKENS MANAGEMENT
# =============================================

function Import-GitHubTokens {
    Write-Header "IMPORT GITHUB TOKENS"
    
    Write-Info "Import GitHub Personal Access Tokens untuk multi-account"
    Write-Warning "Token harus memiliki scope: repo, workflow, admin:org"
    
    $sourceFile = Read-Host "Path file tokens.txt"
    
    if (Test-Path $sourceFile) {
        $tokens = Get-Content $sourceFile | Where-Object { $_ -match "^ghp_" }
        
        if ($tokens.Count -eq 0) {
            Write-Error "Tidak ada token valid yang ditemukan (harus dimulai dengan ghp_)"
            return
        }
        
        $tokens | Out-File -FilePath $TOKENS_FILE -Encoding UTF8
        Write-Success "Berhasil import $($tokens.Count) tokens"
        Write-Log "GitHub tokens imported: $($tokens.Count)"
    } else {
        Write-Error "File tidak ditemukan"
    }
}

function Validate-GitHubTokens {
    Write-Header "VALIDASI GITHUB TOKENS"
    
    if (-not (Test-Path $TOKENS_FILE)) {
        Write-Error "File tokens belum ada"
        return
    }
    
    $tokens = Read-FileLines $TOKENS_FILE
    $tokenCache = Load-JsonFile $TOKEN_CACHE_FILE
    $validTokens = @()
    
    Write-Info "Memvalidasi $($tokens.Count) tokens...`n"
    
    $i = 0
    foreach ($token in $tokens) {
        $i++
        Write-Host "[$i/$($tokens.Count)] Validating..." -NoNewline
        
        if ($tokenCache.$token) {
            $username = $tokenCache.$token
            Write-Host " ✅ @$username (cached)" -ForegroundColor Green
            $validTokens += $username
            continue
        }
        
        $result = Invoke-GitHubAPI -Command "api user --jq .login" -Token $token
        
        if ($result.Success) {
            $username = $result.Output.Trim()
            $tokenCache.$token = $username
            $validTokens += $username
            Write-Host " ✅ @$username" -ForegroundColor Green
        } else {
            Write-Host " ❌ Invalid token" -ForegroundColor Red
        }
        
        Start-Sleep -Milliseconds 500
    }
    
    Save-JsonFile -filePath $TOKEN_CACHE_FILE -data $tokenCache
    
    Write-Host "`n═══════════════════════════════════════"
    Write-Success "Valid Tokens: $($validTokens.Count)/$($tokens.Count)"
    Write-Host "═══════════════════════════════════════"
    
    Write-Log "Token validation completed: $($validTokens.Count) valid"
}

# =============================================
# FEATURE 4: AUTO INVITE COLLABORATORS
# =============================================

function Invoke-AutoInvite {
    Write-Header "AUTO INVITE COLLABORATORS"
    
    if (-not (Test-Path $CONFIG_FILE)) {
        Write-Error "Konfigurasi belum ada. Jalankan Setup Configuration dulu."
        return
    }
    
    if (-not (Test-Path $TOKENS_FILE)) {
        Write-Error "File tokens belum ada. Import GitHub Tokens dulu."
        return
    }
    
    $config = Load-JsonFile $CONFIG_FILE
    $tokens = Read-FileLines $TOKENS_FILE
    $tokenCache = Load-JsonFile $TOKEN_CACHE_FILE
    $invitedUsers = Read-FileLines $INVITED_USERS_FILE
    
    # Get usernames to invite
    $usersToInvite = @()
    
    foreach ($token in $tokens) {
        $username = $tokenCache.$token
        
        if (-not $username) { continue }
        if ($invitedUsers -contains $username) { continue }
        if ($username -eq $config.main_account_username) { continue }
        
        $usersToInvite += $username
    }
    
    if ($usersToInvite.Count -eq 0) {
        Write-Success "Tidak ada user baru untuk diundang"
        return
    }
    
    Write-Info "Akan mengundang $($usersToInvite.Count) user baru ke repo: $($config.main_repo_name)`n"
    
    $mainToken = $config.main_token
    $mainUser = $config.main_account_username
    $repoName = $config.main_repo_name
    $successCount = 0
    
    $i = 0
    foreach ($username in $usersToInvite) {
        $i++
        Write-Host "[$i/$($usersToInvite.Count)] @$username..." -NoNewline
        
        # Check if already collaborator
        $checkCmd = "api repos/$mainUser/$repoName/collaborators/$username"
        $checkResult = Invoke-GitHubAPI -Command $checkCmd -Token $mainToken -MaxRetries 1
        
        if ($checkResult.Success) {
            Write-Host " ℹ️  Already collaborator" -ForegroundColor Cyan
            Add-ToFile -filePath $INVITED_USERS_FILE -content $username
            $successCount++
            Start-Sleep -Milliseconds 500
            continue
        }
        
        # Send invitation
        $inviteCmd = "api --silent -X PUT repos/$mainUser/$repoName/collaborators/$username -f permission=push"
        $inviteResult = Invoke-GitHubAPI -Command $inviteCmd -Token $mainToken
        
        if ($inviteResult.Success -or $inviteResult.Output -match "already a collaborator") {
            Write-Host " ✅ Invited" -ForegroundColor Green
            Add-ToFile -filePath $INVITED_USERS_FILE -content $username
            $successCount++
        } else {
            Write-Host " ❌ Failed: $($inviteResult.Output.Substring(0, [Math]::Min(40, $inviteResult.Output.Length)))" -ForegroundColor Red
        }
        
        Start-Sleep -Seconds 1
    }
    
    Write-Host "`n═══════════════════════════════════════"
    Write-Success "Berhasil: $successCount/$($usersToInvite.Count)"
    Write-Host "═══════════════════════════════════════"
    Write-Log "Auto invite completed: $successCount users"
}

# =============================================
# FEATURE 5: AUTO ACCEPT INVITATIONS
# =============================================

function Invoke-AutoAccept {
    Write-Header "AUTO ACCEPT INVITATIONS"
    
    if (-not (Test-Path $CONFIG_FILE)) {
        Write-Error "Konfigurasi belum ada"
        return
    }
    
    if (-not (Test-Path $TOKENS_FILE)) {
        Write-Error "File tokens belum ada"
        return
    }
    
    $config = Load-JsonFile $CONFIG_FILE
    $tokens = Read-FileLines $TOKENS_FILE
    $tokenCache = Load-JsonFile $TOKEN_CACHE_FILE
    $acceptedUsers = Read-FileLines $ACCEPTED_USERS_FILE
    
    $targetRepo = "$($config.main_account_username)/$($config.main_repo_name)".ToLower()
    
    Write-Info "Target Repo: $targetRepo"
    Write-Info "Processed: $($acceptedUsers.Count) users`n"
    
    $acceptedCount = 0
    $alreadyMember = 0
    $noInvitation = 0
    $skippedCount = 0
    
    $i = 0
    foreach ($token in $tokens) {
        $i++
        $username = $tokenCache.$token
        
        if (-not $username) { continue }
        
        if ($acceptedUsers -contains $username) {
            Write-Host "[$i/$($tokens.Count)] @$username - ⏭️  Skip (already processed)"
            $skippedCount++
            Start-Sleep -Milliseconds 300
            continue
        }
        
        Write-Host "[$i/$($tokens.Count)] @$username..." -NoNewline
        
        # Check if already collaborator
        $checkCmd = "api repos/$($config.main_account_username)/$($config.main_repo_name)/collaborators/$username"
        $checkResult = Invoke-GitHubAPI -Command $checkCmd -Token $token -MaxRetries 1
        
        if ($checkResult.Success) {
            Write-Host " ✅ Already collaborator" -ForegroundColor Green
            Add-ToFile -filePath $ACCEPTED_USERS_FILE -content $username
            $alreadyMember++
            Start-Sleep -Milliseconds 500
            continue
        }
        
        # Get invitations
        $invCmd = "api /user/repository_invitations"
        $invResult = Invoke-GitHubAPI -Command $invCmd -Token $token
        
        if (-not $invResult.Success) {
            Write-Host " ❌ Failed to get invitations" -ForegroundColor Red
            continue
        }
        
        try {
            $invitations = $invResult.Output | ConvertFrom-Json
            $foundInvitation = $false
            
            foreach ($inv in $invitations) {
                if ($inv.repository.full_name.ToLower() -eq $targetRepo) {
                    $foundInvitation = $true
                    $invitationId = $inv.id
                    
                    # Accept invitation
                    $acceptCmd = "api --method PATCH /user/repository_invitations/$invitationId --silent"
                    $acceptResult = Invoke-GitHubAPI -Command $acceptCmd -Token $token
                    
                    if ($acceptResult.Success -or $acceptResult.Output -eq "") {
                        Write-Host " ✅ Accepted" -ForegroundColor Green
                        Add-ToFile -filePath $ACCEPTED_USERS_FILE -content $username
                        $acceptedCount++
                    } else {
                        Write-Host " ❌ Failed to accept" -ForegroundColor Red
                    }
                    break
                }
            }
            
            if (-not $foundInvitation) {
                Write-Host " ℹ️  No invitation" -ForegroundColor Cyan
                $noInvitation++
            }
            
        } catch {
            Write-Host " ❌ Parse error" -ForegroundColor Red
        }
        
        Start-Sleep -Seconds 1
    }
    
    Write-Host "`n═══════════════════════════════════════"
    Write-Host "📊 Summary:" -ForegroundColor Yellow
    Write-Host "   ✅ Accepted       : $acceptedCount"
    Write-Host "   👥 Already member : $alreadyMember"
    Write-Host "   ⏭️  Skipped        : $skippedCount"
    Write-Host "   ℹ️  No invitation  : $noInvitation"
    Write-Host "═══════════════════════════════════════"
    Write-Log "Auto accept completed: $acceptedCount accepted"
}

# =============================================
# FEATURE 6: AUTO SET SECRETS (SODIUM ENCRYPTION)
# =============================================

function Invoke-AutoSetSecrets {
    Write-Header "AUTO SET SECRETS"
    
    Write-Warning "IMPORTANT: Fitur ini memerlukan PyNaCl untuk enkripsi!"
    Write-Info "Install Python dan PyNaCl terlebih dahulu jika belum ada.`n"
    
    # Check if Python available
    try {
        $null = python --version
    } catch {
        Write-Error "Python tidak ditemukan. Install dari: https://python.org"
        return
    }
    
    if (-not (Test-Path $CONFIG_FILE)) {
        Write-Error "Konfigurasi belum ada"
        return
    }
    
    if (-not (Test-Path $API_KEYS_FILE)) {
        Write-Error "File API keys belum ada"
        return
    }
    
    if (-not (Test-Path $TOKENS_FILE)) {
        Write-Error "File tokens belum ada"
        return
    }
    
    $config = Load-JsonFile $CONFIG_FILE
    $apiKeys = (Read-FileLines $API_KEYS_FILE) -join "`n"
    $tokens = Read-FileLines $TOKENS_FILE
    $tokenCache = Load-JsonFile $TOKEN_CACHE_FILE
    $secretsSetUsers = Read-FileLines $SECRETS_SET_FILE
    
    Write-Info "Target Repo: $($config.main_account_username)/$($config.main_repo_name)"
    Write-Info "API Keys: $(($apiKeys -split "`n").Count) keys"
    Write-Info "Processed: $($secretsSetUsers.Count) users`n"
    
    # Create Python helper script for encryption
    $pythonScript = @"
import sys
import json
import base64
from nacl import encoding, public

def encrypt_secret(public_key_b64, secret_value):
    public_key = public.PublicKey(public_key_b64.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")

if __name__ == "__main__":
    public_key = sys.argv[1]
    secret_value = sys.argv[2]
    print(encrypt_secret(public_key, secret_value))
"@
    
    $tempPyScript = "$env:TEMP\encrypt_secret.py"
    $pythonScript | Out-File -FilePath $tempPyScript -Encoding UTF8
    
    $mainOwner = $config.main_account_username
    $mainRepo = $config.main_repo_name
    $skippedCount = 0
    $successCount = 0
    
    $i = 0
    foreach ($token in $tokens) {
        $i++
        $username = $tokenCache.$token
        
        if (-not $username) { continue }
        
        if ($secretsSetUsers -contains $username) {
            Write-Host "[$i/$($tokens.Count)] @$username - ⏭️  Skip"
            $skippedCount++
            Start-Sleep -Milliseconds 300
            continue
        }
        
        Write-Host "[$i/$($tokens.Count)] @$username"
        
        # Get repo ID
        Write-Host "   🔍 Get repo ID..." -NoNewline
        $repoCmd = "api repos/$mainOwner/$mainRepo --jq .id"
        $repoResult = Invoke-GitHubAPI -Command $repoCmd -Token $token -MaxRetries 1
        
        if (-not $repoResult.Success) {
            Write-Host " ❌ Failed" -ForegroundColor Red
            continue
        }
        
        $repoId = $repoResult.Output.Trim()
        Write-Host " ✅ $repoId" -ForegroundColor Green
        
        # Get public key
        Write-Host "   🔑 Get public key..." -NoNewline
        $keyCmd = "api /user/codespaces/secrets/public-key"
        $keyResult = Invoke-GitHubAPI -Command $keyCmd -Token $token -MaxRetries 1
        
        if (-not $keyResult.Success) {
            Write-Host " ❌ Failed" -ForegroundColor Red
            continue
        }
        
        try {
            $keyData = $keyResult.Output | ConvertFrom-Json
            $publicKey = $keyData.key
            $keyId = $keyData.key_id
            Write-Host " ✅" -ForegroundColor Green
        } catch {
            Write-Host " ❌ Parse failed" -ForegroundColor Red
            continue
        }
        
        # Encrypt and set secret
        Write-Host "   🔐 Set DATAGRAM_API_KEYS..." -NoNewline
        
        try {
            # Encrypt using Python
            $encryptedValue = python $tempPyScript $publicKey $apiKeys
            
            if ($LASTEXITCODE -ne 0) {
                Write-Host " ❌ Encryption failed" -ForegroundColor Red
                Write-Warning "Install PyNaCl: pip install pynacl"
                continue
            }
            
            # Prepare payload
            $payload = @{
                encrypted_value = $encryptedValue
                key_id = $keyId
                selected_repository_ids = @([int]$repoId)
            } | ConvertTo-Json -Compress
            
            # Set secret
            $tempPayload = "$env:TEMP\payload.json"
            $payload | Out-File -FilePath $tempPayload -Encoding UTF8 -NoNewline
            
            $setCmd = "api --method PUT /user/codespaces/secrets/DATAGRAM_API_KEYS --input `"$tempPayload`""
            $setResult = Invoke-GitHubAPI -Command $setCmd -Token $token -MaxRetries 1
            
            Remove-Item $tempPayload -Force -ErrorAction SilentlyContinue
            
            if ($setResult.Success -or $setResult.Output -eq "") {
                Write-Host " ✅" -ForegroundColor Green
                Add-ToFile -filePath $SECRETS_SET_FILE -content $username
                $successCount++
            } else {
                Write-Host " ❌ $($setResult.Output.Substring(0, [Math]::Min(30, $setResult.Output.Length)))" -ForegroundColor Red
            }
            
        } catch {
            Write-Host " ❌ $($_.Exception.Message.Substring(0, [Math]::Min(30, $_.Exception.Message.Length)))" -ForegroundColor Red
        }
        
        Start-Sleep -Seconds 1
        Write-Host ""
    }
    
    # Cleanup
    Remove-Item $tempPyScript -Force -ErrorAction SilentlyContinue
    
    Write-Host "═══════════════════════════════════════"
    Write-Host "📊 Summary:" -ForegroundColor Yellow
    Write-Host "   ✅ Success : $successCount"
    Write-Host "   ⏭️  Skipped : $skippedCount"
    Write-Host "═══════════════════════════════════════"
    Write-Log "Auto set secrets completed: $successCount users"
}

# =============================================
# FEATURE 7: DEPLOY TO GITHUB
# =============================================

function Deploy-ToGitHub {
    Write-Header "DEPLOY TO GITHUB"
    
    if (-not (Test-Path $CONFIG_FILE)) {
        Write-Error "Konfigurasi belum ada"
        return
    }
    
    $config = Load-JsonFile $CONFIG_FILE
    $mainToken = $config.main_token
    $mainUser = $config.main_account_username
    $repoName = $config.main_repo_name
    
    Write-Info "Target: $mainUser/$repoName`n"
    
    # Check if repo exists
    Write-Host "🔍 Checking repository..." -NoNewline
    $checkCmd = "api repos/$mainUser/$repoName"
    $checkResult = Invoke-GitHubAPI -Command $checkCmd -Token $mainToken -MaxRetries 1
    
    if (-not $checkResult.Success) {
        Write-Host " ⚠️  Not found" -ForegroundColor Yellow
        
        $create = Read-Host "`nCreate new repository? (y/n)"
        if ($create -eq "y") {
            Write-Host "Creating repository..." -NoNewline
            $createCmd = "repo create $repoName --private --confirm"
            $createResult = Invoke-GitHubAPI -Command $createCmd -Token $mainToken
            
            if ($createResult.Success) {
                Write-Host " ✅" -ForegroundColor Green
            } else {
                Write-Host " ❌ Failed" -ForegroundColor Red
                return
            }
        } else {
            return
        }
    } else {
        Write-Host " ✅ Found" -ForegroundColor Green
    }
    
    # Initialize git if needed
    if (-not (Test-Path ".git")) {
        Write-Host "`n📦 Initializing git repository..."
        git init
        git branch -M main
    }
    
    # Create workflow file
    Write-Host "📝 Creating workflow file..."
    $workflowDir = ".github/workflows"
    if (-not (Test-Path $workflowDir)) {
        New-Item -ItemType Directory -Path $workflowDir -Force | Out-Null
    }
    
    # Copy workflow from artifacts or create new
    $workflowFile = "$workflowDir/datagram-runner.yml"
    
    if (-not (Test-Path $workflowFile)) {
        Write-Warning "Workflow file not found. Please create it manually."
        Write-Info "Template tersedia di artifacts yang sudah saya buatkan sebelumnya."
    }
    
    # Commit and push
    Write-Host "`n🚀 Deploying to GitHub..."
    
    git add .
    git commit -m "🚀 Deploy Datagram Runner with auto-orchestration" -m "- Multi-account support`n- Auto-restart mechanism`n- Parallel execution`n- Health monitoring"
    
    $remoteUrl = "https://github.com/$mainUser/$repoName.git"
    git remote remove origin 2>$null
    git remote add origin $remoteUrl
    
    # Push with token
    $env:GH_TOKEN = $mainToken
    git push -u origin main --force
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "`n✅ Deployment successful!"
        Write-Info "Repository: https://github.com/$mainUser/$repoName"
        Write-Info "Actions: https://github.com/$mainUser/$repoName/actions"
    } else {
        Write-Error "Deployment failed"
    }
    
    Write-Log "Deployed to GitHub: $mainUser/$repoName"
}

# =============================================
# FEATURE 8: TRIGGER WORKFLOW
# =============================================

function Invoke-WorkflowTrigger {
    Write-Header "TRIGGER WORKFLOW"
    
    if (-not (Test-Path $CONFIG_FILE)) {
        Write-Error "Konfigurasi belum ada"
        return
    }
    
    $config = Load-JsonFile $CONFIG_FILE
    $mainToken = $config.main_token
    $mainUser = $config.main_account_username
    $repoName = $config.main_repo_name
    
    Write-Info "Triggering workflow: $mainUser/$repoName`n"
    
    $triggerCmd = "workflow run datagram-runner.yml -R $mainUser/$repoName"
    $result = Invoke-GitHubAPI -Command $triggerCmd -Token $mainToken
    
    if ($result.Success) {
        Write-Success "✅ Workflow triggered successfully!"
        Write-Info "View at: https://github.com/$mainUser/$repoName/actions"
        
        Start-Sleep -Seconds 3
        
        # Get latest run
        Write-Host "`n🔍 Fetching latest run..."
        $runCmd = "run list -R $mainUser/$repoName --limit 1 --json databaseId,status,conclusion,url"
        $runResult = Invoke-GitHubAPI -Command $runCmd -Token $mainToken
        
        if ($runResult.Success) {
            try {
                $run = ($runResult.Output | ConvertFrom-Json)[0]
                Write-Host "   Run ID: $($run.databaseId)"
                Write-Host "   Status: $($run.status)"
                Write-Host "   URL: $($run.url)"
            } catch {
                # Ignore parse errors
            }
        }
    } else {
        Write-Error "Failed to trigger workflow"
        Write-Info $result.Output
    }
    
    Write-Log "Workflow triggered"
}

# =============================================
# FEATURE 9: MONITOR WORKFLOWS
# =============================================

function Show-WorkflowStatus {
    Write-Header "WORKFLOW STATUS"
    
    if (-not (Test-Path $CONFIG_FILE)) {
        Write-Error "Konfigurasi belum ada"
        return
    }
    
    $config = Load-JsonFile $CONFIG_FILE
    $mainToken = $config.main_token
    $mainUser = $config.main_account_username
    $repoName = $config.main_repo_name
    
    Write-Info "Repository: $mainUser/$repoName`n"
    
    $runCmd = "run list -R $mainUser/$repoName --limit 5 --json databaseId,status,conclusion,createdAt,workflowName"
    $result = Invoke-GitHubAPI -Command $runCmd -Token $mainToken
    
    if ($result.Success) {
        try {
            $runs = $result.Output | ConvertFrom-Json
            
            if ($runs.Count -eq 0) {
                Write-Warning "No workflow runs found"
                return
            }
            
            Write-Host "Recent Workflow Runs:" -ForegroundColor Yellow
            Write-Host "═══════════════════════════════════════`n"
            
            foreach ($run in $runs) {
                $statusColor = switch ($run.status) {
                    "completed" { if ($run.conclusion -eq "success") { "Green" } else { "Red" } }
                    "in_progress" { "Yellow" }
                    default { "White" }
                }
                
                $statusIcon = switch ($run.status) {
                    "completed" { if ($run.conclusion -eq "success") { "✅" } else { "❌" } }
                    "in_progress" { "🔄" }
                    "queued" { "⏳" }
                    default { "❓" }
                }
                
                Write-Host "$statusIcon Run #$($run.databaseId)" -ForegroundColor $statusColor
                Write-Host "   Workflow: $($run.workflowName)"
                Write-Host "   Status: $($run.status) $(if ($run.conclusion) { "($($run.conclusion))" })"
                Write-Host "   Created: $($run.createdAt)"
                Write-Host ""
            }
            
        } catch {
            Write-Error "Failed to parse workflow runs"
        }
    } else {
        Write-Error "Failed to fetch workflow status"
    }
}

# =============================================
# MAIN MENU
# =============================================

function Show-Menu {
    Clear-Host
    Write-Host @"
╔═══════════════════════════════════════════════╗
║                                               ║
║     DATAGRAM ORCHESTRATOR v2.0                ║
║     PowerShell Edition                        ║
║                                               ║
╚═══════════════════════════════════════════════╝
"@ -ForegroundColor Cyan

    Write-Host "`n📋 SETUP & CONFIGURATION" -ForegroundColor Yellow
    Write-Host "  1. Initialize Configuration"
    Write-Host "  2. Import API Keys"
    Write-Host "  3. Show API Keys Status"
    Write-Host "  4. Import GitHub Tokens"
    Write-Host "  5. Validate GitHub Tokens"
    
    Write-Host "`n🤝 COLLABORATION MANAGEMENT" -ForegroundColor Yellow
    Write-Host "  6. Auto Invite Collaborators"
    Write-Host "  7. Auto Accept Invitations"
    Write-Host "  8. Auto Set Secrets"
    
    Write-Host "`n🚀 DEPLOYMENT & MONITORING" -ForegroundColor Yellow
    Write-Host "  9. Deploy to GitHub"
    Write-Host " 10. Trigger Workflow"
    Write-Host " 11. Show Workflow Status"
    
    Write-Host "`n🔧 UTILITIES" -ForegroundColor Yellow
    Write-Host " 12. View Logs"
    Write-Host " 13. Clean Cache"
    
    Write-Host "`n  0. Exit" -ForegroundColor Gray
    Write-Host "`n═══════════════════════════════════════════════"
}

function Main {
    # Initialize
    Initialize-Directories
    
    if (-not (Test-GitHubCLI)) {
        return
    }
    
    while ($true) {
        Show-Menu
        $choice = Read-Host "`nPilih menu (0-13)"
        
        switch ($choice) {
            "1"  { Initialize-Configuration }
            "2"  { Import-ApiKeys }
            "3"  { Show-ApiKeysStatus }
            "4"  { Import-GitHubTokens }
            "5"  { Validate-GitHubTokens }
            "6"  { Invoke-AutoInvite }
            "7"  { Invoke-AutoAccept }
            "8"  { Invoke-AutoSetSecrets }
            "9"  { Deploy-ToGitHub }
            "10" { Invoke-WorkflowTrigger }
            "11" { Show-WorkflowStatus }
            "12" { 
                if (Test-Path $LOG_FILE) {
                    Get-Content $LOG_FILE -Tail 50
                } else {
                    Write-Warning "Log file not found"
                }
            }
            "13" { 
                Write-Warning "Cleaning cache files..."
                @($TOKEN_CACHE_FILE, $INVITED_USERS_FILE, $ACCEPTED_USERS_FILE, $SECRETS_SET_FILE) | 
                    ForEach-Object { if (Test-Path $_) { Remove-Item $_ -Force } }
                Write-Success "Cache cleaned"
            }
            "0"  { 
                Write-Success "Terima kasih telah menggunakan Datagram Orchestrator!"
                break 
            }
            default { Write-Warning "Pilihan tidak valid" }
        }
        
        if ($choice -ne "0") {
            Write-Host "`n" -NoNewline
            Read-Host "Press Enter to continue"
        }
    }
}

# Run main
Main
