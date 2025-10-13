#!/bin/bash

# =============================================
# DATAGRAM ORCHESTRATOR - Bash Edition
# Compatible with Linux & macOS
# =============================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
CONFIG_DIR="config"
LOGS_DIR="logs"
API_KEYS_FILE="$CONFIG_DIR/api_keys.txt"
TOKENS_FILE="$CONFIG_DIR/tokens.txt"
CONFIG_FILE="$CONFIG_DIR/config.json"
TOKEN_CACHE_FILE="$CONFIG_DIR/token_cache.json"
INVITED_USERS_FILE="$CONFIG_DIR/invited_users.txt"
ACCEPTED_USERS_FILE="$CONFIG_DIR/accepted_users.txt"
SECRETS_SET_FILE="$CONFIG_DIR/secrets_set.txt"
LOG_FILE="$LOGS_DIR/setup.log"

# =============================================
# HELPER FUNCTIONS
# =============================================

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_header() {
    echo -e "\n${MAGENTA}═══════════════════════════════════════${NC}"
    echo -e "${MAGENTA}  $1${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════${NC}\n"
}

init_directories() {
    mkdir -p "$CONFIG_DIR" "$LOGS_DIR"
}

check_dependencies() {
    print_header "CHECKING DEPENDENCIES"
    
    local missing=0
    
    # Check GitHub CLI
    if ! command -v gh &> /dev/null; then
        print_error "GitHub CLI (gh) not found"
        print_info "Install from: https://cli.github.com/"
        missing=1
    else
        print_success "GitHub CLI: $(gh --version | head -1)"
    fi
    
    # Check jq
    if ! command -v jq &> /dev/null; then
        print_error "jq not found"
        print_info "Install with: sudo apt install jq (Ubuntu) or brew install jq (macOS)"
        missing=1
    else
        print_success "jq: $(jq --version)"
    fi
    
    # Check Python (untuk encryption)
    if ! command -v python3 &> /dev/null; then
        print_warning "Python3 not found (needed for secret encryption)"
        print_info "Install from: https://python.org"
    else
        print_success "Python: $(python3 --version)"
        
        # Check PyNaCl
        if python3 -c "import nacl" 2>/dev/null; then
            print_success "PyNaCl: Installed"
        else
            print_warning "PyNaCl not installed (needed for secret encryption)"
            print_info "Install with: pip3 install pynacl"
        fi
    fi
    
    if [ $missing -eq 1 ]; then
        print_error "Missing required dependencies. Please install them first."
        exit 1
    fi
    
    echo ""
    read -p "Press Enter to continue..."
}

run_gh_command() {
    local cmd="$1"
    local token="$2"
    local max_retries="${3:-3}"
    local retry_delay="${4:-5}"
    
    export GH_TOKEN="$token"
    
    local attempt=0
    while [ $attempt -lt $max_retries ]; do
        local output
        if output=$(eval "gh $cmd" 2>&1); then
            echo "$output"
            return 0
        else
            if echo "$output" | grep -iq "api.github.com\|timeout\|connection"; then
                ((attempt++))
                if [ $attempt -lt $max_retries ]; then
                    print_warning "Connection failed. Retry $attempt/$max_retries in ${retry_delay}s..."
                    sleep "$retry_delay"
                    continue
                fi
            fi
            echo "$output" >&2
            return 1
        fi
    done
    
    return 1
}

# =============================================
# FEATURE 1: SETUP CONFIGURATION
# =============================================

init_configuration() {
    print_header "SETUP KONFIGURASI"
    
    echo -n "Username GitHub utama: "
    read main_username
    
    echo -n "Nama repository (misal: datagram-runner): "
    read repo_name
    
    echo -n "GitHub Personal Access Token (main account): "
    read -s main_token
    echo ""
    
    # Create config JSON
    cat > "$CONFIG_FILE" <<EOF
{
  "main_account_username": "$main_username",
  "main_repo_name": "$repo_name",
  "main_token": "$main_token"
}
EOF
    
    print_success "Konfigurasi disimpan ke $CONFIG_FILE"
    log_message "Configuration initialized"
}

# =============================================
# FEATURE 2: API KEYS MANAGEMENT
# =============================================

import_api_keys() {
    print_header "IMPORT API KEYS"
    
    print_info "Pilih metode import:"
    echo "1. Input manual (satu per satu)"
    echo "2. Import dari file .txt"
    echo ""
    
    read -p "Pilihan (1/2): " choice
    
    case $choice in
        1)
            echo "" > "$API_KEYS_FILE"
            print_info "Masukkan API keys (Enter kosong untuk selesai):"
            
            local count=0
            while true; do
                ((count++))
                read -p "API Key #$count: " key
                [ -z "$key" ] && break
                echo "$key" >> "$API_KEYS_FILE"
            done
            
            ((count--))
            [ $count -gt 0 ] && print_success "Berhasil menyimpan $count API keys"
            ;;
            
        2)
            read -p "Path file .txt: " source_file
            if [ -f "$source_file" ]; then
                cp "$source_file" "$API_KEYS_FILE"
                local count=$(wc -l < "$API_KEYS_FILE")
                print_success "Berhasil import $count API keys"
            else
                print_error "File tidak ditemukan"
            fi
            ;;
            
        *)
            print_error "Pilihan tidak valid"
            ;;
    esac
    
    log_message "API keys imported"
}

show_api_keys_status() {
    print_header "STATUS API KEYS"
    
    if [ ! -f "$API_KEYS_FILE" ]; then
        print_warning "File API keys belum ada"
        return
    fi
    
    local count=$(grep -c . "$API_KEYS_FILE" 2>/dev/null || echo 0)
    print_info "Total API Keys: $count"
    
    if [ $count -gt 0 ]; then
        echo -e "\n${CYAN}Preview (first 3):${NC}"
        head -n 3 "$API_KEYS_FILE" | while read -r key; do
            local preview="${key:0:10}...${key: -5}"
            echo "  🔑 $preview"
        done
        
        echo -e "\n${YELLOW}📋 Format untuk GitHub Secret:${NC}"
        echo "Secret Name: DATAGRAM_API_KEYS"
        echo -e "\nSecret Value (newline separated):"
        echo "────────────────────────────────"
        head -n 2 "$API_KEYS_FILE"
        echo "..."
        echo "────────────────────────────────"
    fi
}

# =============================================
# FEATURE 3: GITHUB TOKENS MANAGEMENT
# =============================================

import_github_tokens() {
    print_header "IMPORT GITHUB TOKENS"
    
    print_info "Import GitHub Personal Access Tokens"
    print_warning "Token harus memiliki scope: repo, workflow, admin:org"
    
    read -p "Path file tokens.txt: " source_file
    
    if [ -f "$source_file" ]; then
        grep "^ghp_" "$source_file" > "$TOKENS_FILE" || true
        local count=$(wc -l < "$TOKENS_FILE")
        
        if [ $count -eq 0 ]; then
            print_error "Tidak ada token valid (harus dimulai dengan ghp_)"
            return
        fi
        
        print_success "Berhasil import $count tokens"
        log_message "GitHub tokens imported: $count"
    else
        print_error "File tidak ditemukan"
    fi
}

validate_github_tokens() {
    print_header "VALIDASI GITHUB TOKENS"
    
    if [ ! -f "$TOKENS_FILE" ]; then
        print_error "File tokens belum ada"
        return
    fi
    
    local tokens=()
    while IFS= read -r token; do
        tokens+=("$token")
    done < "$TOKENS_FILE"
    
    local total=${#tokens[@]}
    [ ! -f "$TOKEN_CACHE_FILE" ] && echo "{}" > "$TOKEN_CACHE_FILE"
    
    print_info "Memvalidasi $total tokens...\n"
    
    local valid_count=0
    local i=0
    
    for token in "${tokens[@]}"; do
        ((i++))
        echo -n "[$i/$total] Validating..."
        
        # Check cache
        local cached_user=$(jq -r --arg token "$token" '.[$token] // empty' "$TOKEN_CACHE_FILE")
        
        if [ -n "$cached_user" ]; then
            echo -e " ${GREEN}✅ @$cached_user (cached)${NC}"
            ((valid_count++))
            continue
        fi
        
        # Validate via API
        local username
        if username=$(run_gh_command "api user --jq .login" "$token" 1 2); then
            echo -e " ${GREEN}✅ @$username${NC}"
            
            # Update cache
            local temp_cache=$(mktemp)
            jq --arg token "$token" --arg user "$username" '.[$token] = $user' "$TOKEN_CACHE_FILE" > "$temp_cache"
            mv "$temp_cache" "$TOKEN_CACHE_FILE"
            
            ((valid_count++))
        else
            echo -e " ${RED}❌ Invalid token${NC}"
        fi
        
        sleep 0.5
    done
    
    echo -e "\n═══════════════════════════════════════"
    print_success "Valid Tokens: $valid_count/$total"
    echo "═══════════════════════════════════════"
    
    log_message "Token validation: $valid_count valid"
}

# =============================================
# FEATURE 4: AUTO INVITE COLLABORATORS
# =============================================

auto_invite_collaborators() {
    print_header "AUTO INVITE COLLABORATORS"
    
    [ ! -f "$CONFIG_FILE" ] && { print_error "Konfigurasi belum ada"; return; }
    [ ! -f "$TOKENS_FILE" ] && { print_error "File tokens belum ada"; return; }
    
    local main_user=$(jq -r '.main_account_username' "$CONFIG_FILE")
    local repo_name=$(jq -r '.main_repo_name' "$CONFIG_FILE")
    local main_token=$(jq -r '.main_token' "$CONFIG_FILE")
    
    [ ! -f "$TOKEN_CACHE_FILE" ] && { print_error "Jalankan validasi token dulu"; return; }
    
    # Get users to invite
    local users_to_invite=()
    local invited_users=()
    
    [ -f "$INVITED_USERS_FILE" ] && readarray -t invited_users < "$INVITED_USERS_FILE"
    
    while IFS= read -r token; do
        local username=$(jq -r --arg token "$token" '.[$token] // empty' "$TOKEN_CACHE_FILE")
        
        [ -z "$username" ] && continue
        [ "$username" = "$main_user" ] && continue
        
        # Check if already invited
        local already_invited=false
        for invited in "${invited_users[@]}"; do
            if [ "${invited,,}" = "${username,,}" ]; then
                already_invited=true
                break
            fi
        done
        
        [ "$already_invited" = false ] && users_to_invite+=("$username")
    done < "$TOKENS_FILE"
    
    if [ ${#users_to_invite[@]} -eq 0 ]; then
        print_success "Tidak ada user baru untuk diundang"
        return
    fi
    
    print_info "Akan mengundang ${#users_to_invite[@]} user ke repo: $repo_name\n"
    
    local success_count=0
    local i=0
    
    for username in "${users_to_invite[@]}"; do
        ((i++))
        echo -n "[$i/${#users_to_invite[@]}] @$username..."
        
        # Check if already collaborator
        if run_gh_command "api repos/$main_user/$repo_name/collaborators/$username" "$main_token" 1 >/dev/null 2>&1; then
            echo -e " ${CYAN}ℹ️  Already collaborator${NC}"
            echo "$username" >> "$INVITED_USERS_FILE"
            ((success_count++))
            sleep 0.5
            continue
        fi
        
        # Send invitation
        if run_gh_command "api --silent -X PUT repos/$main_user/$repo_name/collaborators/$username -f permission=push" "$main_token" >/dev/null 2>&1; then
            echo -e " ${GREEN}✅ Invited${NC}"
            echo "$username" >> "$INVITED_USERS_FILE"
            ((success_count++))
        else
            echo -e " ${RED}❌ Failed${NC}"
        fi
        
        sleep 1
    done
    
    echo -e "\n═══════════════════════════════════════"
    print_success "Berhasil: $success_count/${#users_to_invite[@]}"
    echo "═══════════════════════════════════════"
    
    log_message "Auto invite: $success_count users"
}

# =============================================
# FEATURE 5: AUTO ACCEPT INVITATIONS
# =============================================

auto_accept_invitations() {
    print_header "AUTO ACCEPT INVITATIONS"
    
    [ ! -f "$CONFIG_FILE" ] && { print_error "Konfigurasi belum ada"; return; }
    [ ! -f "$TOKENS_FILE" ] && { print_error "File tokens belum ada"; return; }
    
    local main_user=$(jq -r '.main_account_username' "$CONFIG_FILE")
    local repo_name=$(jq -r '.main_repo_name' "$CONFIG_FILE")
    local target_repo="${main_user}/${repo_name}"
    target_repo="${target_repo,,}"
    
    local accepted_users=()
    [ -f "$ACCEPTED_USERS_FILE" ] && readarray -t accepted_users < "$ACCEPTED_USERS_FILE"
    
    print_info "Target Repo: $target_repo"
    print_info "Processed: ${#accepted_users[@]} users\n"
    
    local accepted_count=0
    local already_member=0
    local no_invitation=0
    local skipped_count=0
    
    local tokens=()
    while IFS= read -r token; do
        tokens+=("$token")
    done < "$TOKENS_FILE"
    
    local i=0
    for token in "${tokens[@]}"; do
        ((i++))
        local username=$(jq -r --arg token "$token" '.[$token] // empty' "$TOKEN_CACHE_FILE")
        
        [ -z "$username" ] && continue
        
        # Check if already processed
        local already_accepted=false
        for accepted in "${accepted_users[@]}"; do
            if [ "${accepted,,}" = "${username,,}" ]; then
                already_accepted=true
                break
            fi
        done
        
        if [ "$already_accepted" = true ]; then
            echo "[$i/${#tokens[@]}] @$username - ⏭️  Skip"
            ((skipped_count++))
            sleep 0.3
            continue
        fi
        
        echo -n "[$i/${#tokens[@]}] @$username..."
        
        # Check if already collaborator
        if run_gh_command "api repos/$main_user/$repo_name/collaborators/$username" "$token" 1 >/dev/null 2>&1; then
            echo -e " ${GREEN}✅ Already collaborator${NC}"
            echo "$username" >> "$ACCEPTED_USERS_FILE"
            ((already_member++))
            sleep 0.5
            continue
        fi
        
        # Get invitations
        local invitations
        if ! invitations=$(run_gh_command "api /user/repository_invitations" "$token" 1 2>/dev/null); then
            echo -e " ${RED}❌ Failed to get invitations${NC}"
            continue
        fi
        
        # Find matching invitation
        local found_inv=false
        local inv_count=$(echo "$invitations" | jq 'length')
        
        for ((j=0; j<inv_count; j++)); do
            local inv_repo=$(echo "$invitations" | jq -r ".[$j].repository.full_name" | tr '[:upper:]' '[:lower:]')
            
            if [ "$inv_repo" = "$target_repo" ]; then
                found_inv=true
                local inv_id=$(echo "$invitations" | jq -r ".[$j].id")
                
                # Accept invitation
                if run_gh_command "api --method PATCH /user/repository_invitations/$inv_id --silent" "$token" >/dev/null 2>&1; then
                    echo -e " ${GREEN}✅ Accepted${NC}"
                    echo "$username" >> "$ACCEPTED_USERS_FILE"
                    ((accepted_count++))
                else
                    echo -e " ${RED}❌ Failed to accept${NC}"
                fi
                break
            fi
        done
        
        if [ "$found_inv" = false ]; then
            echo -e " ${CYAN}ℹ️  No invitation${NC}"
            ((no_invitation++))
        fi
        
        sleep 1
    done
    
    echo -e "\n═══════════════════════════════════════"
    echo -e "${YELLOW}📊 Summary:${NC}"
    echo "   ✅ Accepted       : $accepted_count"
    echo "   👥 Already member : $already_member"
    echo "   ⏭️  Skipped        : $skipped_count"
    echo "   ℹ️  No invitation  : $no_invitation"
    echo "═══════════════════════════════════════"
    
    log_message "Auto accept: $accepted_count accepted"
}

# =============================================
# FEATURE 6: AUTO SET SECRETS
# =============================================

auto_set_secrets() {
    print_header "AUTO SET SECRETS"
    
    print_warning "IMPORTANT: Memerlukan Python3 dan PyNaCl!\n"
    
    # Check Python & PyNaCl
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 tidak ditemukan"
        return
    fi
    
    if ! python3 -c "import nacl" 2>/dev/null; then
        print_error "PyNaCl tidak terinstal"
        print_info "Install dengan: pip3 install pynacl"
        return
    fi
    
    [ ! -f "$CONFIG_FILE" ] && { print_error "Konfigurasi belum ada"; return; }
    [ ! -f "$API_KEYS_FILE" ] && { print_error "File API keys belum ada"; return; }
    [ ! -f "$TOKENS_FILE" ] && { print_error "File tokens belum ada"; return; }
    
    local main_user=$(jq -r '.main_account_username' "$CONFIG_FILE")
    local repo_name=$(jq -r '.main_repo_name' "$CONFIG_FILE")
    
    # Read API keys
    local api_keys_value
    api_keys_value=$(cat "$API_KEYS_FILE")
    
    local api_keys_count=$(echo "$api_keys_value" | wc -l)
    
    print_info "Target Repo: $main_user/$repo_name"
    print_info "API Keys: $api_keys_count keys\n"
    
    # Create Python encryption script
    local py_script="/tmp/encrypt_secret_$.py"
    cat > "$py_script" <<'PYTHON'
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
PYTHON
    
    local secrets_set_users=()
    [ -f "$SECRETS_SET_FILE" ] && readarray -t secrets_set_users < "$SECRETS_SET_FILE"
    
    local tokens=()
    while IFS= read -r token; do
        tokens+=("$token")
    done < "$TOKENS_FILE"
    
    local success_count=0
    local skipped_count=0
    local i=0
    
    for token in "${tokens[@]}"; do
        ((i++))
        local username=$(jq -r --arg token "$token" '.[$token] // empty' "$TOKEN_CACHE_FILE")
        
        [ -z "$username" ] && continue
        
        # Check if already processed
        local already_set=false
        for user in "${secrets_set_users[@]}"; do
            if [ "${user,,}" = "${username,,}" ]; then
                already_set=true
                break
            fi
        done
        
        if [ "$already_set" = true ]; then
            echo "[$i/${#tokens[@]}] @$username - ⏭️  Skip"
            ((skipped_count++))
            sleep 0.3
            continue
        fi
        
        echo "[$i/${#tokens[@]}] @$username"
        
        # Get repo ID
        echo -n "   🔍 Get repo ID..."
        local repo_id
        if ! repo_id=$(run_gh_command "api repos/$main_user/$repo_name --jq .id" "$token" 1 2>/dev/null); then
            echo -e " ${RED}❌ Failed${NC}"
            continue
        fi
        echo -e " ${GREEN}✅ $repo_id${NC}"
        
        # Get public key
        echo -n "   🔑 Get public key..."
        local pubkey_json
        if ! pubkey_json=$(run_gh_command "api /user/codespaces/secrets/public-key" "$token" 1 2>/dev/null); then
            echo -e " ${RED}❌ Failed${NC}"
            continue
        fi
        
        local public_key
        local key_id
        public_key=$(echo "$pubkey_json" | jq -r '.key')
        key_id=$(echo "$pubkey_json" | jq -r '.key_id')
        echo -e " ${GREEN}✅${NC}"
        
        # Encrypt secret
        echo -n "   🔐 Set DATAGRAM_API_KEYS..."
        
        local encrypted_value
        if ! encrypted_value=$(python3 "$py_script" "$public_key" "$api_keys_value" 2>/dev/null); then
            echo -e " ${RED}❌ Encryption failed${NC}"
            continue
        fi
        
        # Prepare payload
        local payload=$(jq -n \
            --arg enc "$encrypted_value" \
            --arg kid "$key_id" \
            --argjson repo "$repo_id" \
            '{encrypted_value: $enc, key_id: $kid, selected_repository_ids: [$repo | tonumber]}')
        
        # Set secret
        local temp_payload="/tmp/payload_$.json"
        echo "$payload" > "$temp_payload"
        
        if run_gh_command "api --method PUT /user/codespaces/secrets/DATAGRAM_API_KEYS --input $temp_payload" "$token" 1 >/dev/null 2>&1; then
            echo -e " ${GREEN}✅${NC}"
            echo "$username" >> "$SECRETS_SET_FILE"
            ((success_count++))
        else
            echo -e " ${RED}❌ Failed${NC}"
        fi
        
        rm -f "$temp_payload"
        echo ""
        sleep 1
    done
    
    # Cleanup
    rm -f "$py_script"
    
    echo "═══════════════════════════════════════"
    echo -e "${YELLOW}📊 Summary:${NC}"
    echo "   ✅ Success : $success_count"
    echo "   ⏭️  Skipped : $skipped_count"
    echo "═══════════════════════════════════════"
    
    log_message "Auto set secrets: $success_count users"
}

# =============================================
# FEATURE 7: DEPLOY TO GITHUB
# =============================================

deploy_to_github() {
    print_header "DEPLOY TO GITHUB"
    
    [ ! -f "$CONFIG_FILE" ] && { print_error "Konfigurasi belum ada"; return; }
    
    local main_user=$(jq -r '.main_account_username' "$CONFIG_FILE")
    local repo_name=$(jq -r '.main_repo_name' "$CONFIG_FILE")
    local main_token=$(jq -r '.main_token' "$CONFIG_FILE")
    
    print_info "Target: $main_user/$repo_name\n"
    
    # Check if repo exists
    echo -n "🔍 Checking repository..."
    if run_gh_command "api repos/$main_user/$repo_name" "$main_token" 1 >/dev/null 2>&1; then
        echo -e " ${GREEN}✅ Found${NC}"
    else
        echo -e " ${YELLOW}⚠️  Not found${NC}"
        
        read -p "Create new repository? (y/n): " create
        if [ "$create" = "y" ]; then
            echo -n "Creating repository..."
            if run_gh_command "repo create $repo_name --private --confirm" "$main_token" >/dev/null 2>&1; then
                echo -e " ${GREEN}✅${NC}"
            else
                echo -e " ${RED}❌ Failed${NC}"
                return
            fi
        else
            return
        fi
    fi
    
    # Initialize git
    if [ ! -d ".git" ]; then
        echo -e "\n📦 Initializing git repository..."
        git init
        git branch -M main
    fi
    
    # Create workflow directory
    echo "📝 Checking workflow file..."
    mkdir -p .github/workflows
    
    local workflow_file=".github/workflows/datagram-runner.yml"
    if [ ! -f "$workflow_file" ]; then
        print_warning "Workflow file not found"
        print_info "Please create $workflow_file manually"
        print_info "Template tersedia di artifacts sebelumnya"
    fi
    
    # Commit and push
    echo -e "\n🚀 Deploying to GitHub..."
    
    git add .
    git commit -m "🚀 Deploy Datagram Runner" -m "- Multi-account support" -m "- Auto-restart mechanism" -m "- Parallel execution" || true
    
    git remote remove origin 2>/dev/null || true
    git remote add origin "https://github.com/$main_user/$repo_name.git"
    
    export GH_TOKEN="$main_token"
    if git push -u origin main --force; then
        echo ""
        print_success "✅ Deployment successful!"
        print_info "Repository: https://github.com/$main_user/$repo_name"
        print_info "Actions: https://github.com/$main_user/$repo_name/actions"
    else
        print_error "Deployment failed"
    fi
    
    log_message "Deployed to: $main_user/$repo_name"
}

# =============================================
# FEATURE 8: TRIGGER WORKFLOW
# =============================================

trigger_workflow() {
    print_header "TRIGGER WORKFLOW"
    
    [ ! -f "$CONFIG_FILE" ] && { print_error "Konfigurasi belum ada"; return; }
    
    local main_user=$(jq -r '.main_account_username' "$CONFIG_FILE")
    local repo_name=$(jq -r '.main_repo_name' "$CONFIG_FILE")
    local main_token=$(jq -r '.main_token' "$CONFIG_FILE")
    
    print_info "Triggering: $main_user/$repo_name\n"
    
    if run_gh_command "workflow run datagram-runner.yml -R $main_user/$repo_name" "$main_token"; then
        print_success "✅ Workflow triggered!"
        print_info "View at: https://github.com/$main_user/$repo_name/actions"
        
        sleep 3
        
        echo -e "\n🔍 Fetching latest run..."
        local run_info
        if run_info=$(run_gh_command "run list -R $main_user/$repo_name --limit 1 --json databaseId,status,url" "$main_token" 1 2>/dev/null); then
            local run_id=$(echo "$run_info" | jq -r '.[0].databaseId')
            local run_status=$(echo "$run_info" | jq -r '.[0].status')
            local run_url=$(echo "$run_info" | jq -r '.[0].url')
            
            echo "   Run ID: $run_id"
            echo "   Status: $run_status"
            echo "   URL: $run_url"
        fi
    else
        print_error "Failed to trigger workflow"
    fi
    
    log_message "Workflow triggered"
}

# =============================================
# FEATURE 9: SHOW WORKFLOW STATUS
# =============================================

show_workflow_status() {
    print_header "WORKFLOW STATUS"
    
    [ ! -f "$CONFIG_FILE" ] && { print_error "Konfigurasi belum ada"; return; }
    
    local main_user=$(jq -r '.main_account_username' "$CONFIG_FILE")
    local repo_name=$(jq -r '.main_repo_name' "$CONFIG_FILE")
    local main_token=$(jq -r '.main_token' "$CONFIG_FILE")
    
    print_info "Repository: $main_user/$repo_name\n"
    
    local runs
    if ! runs=$(run_gh_command "run list -R $main_user/$repo_name --limit 5 --json databaseId,status,conclusion,createdAt,workflowName" "$main_token" 1 2>/dev/null); then
        print_error "Failed to fetch workflow status"
        return
    fi
    
    local run_count=$(echo "$runs" | jq 'length')
    
    if [ "$run_count" -eq 0 ]; then
        print_warning "No workflow runs found"
        return
    fi
    
    echo -e "${YELLOW}Recent Workflow Runs:${NC}"
    echo "═══════════════════════════════════════"
    echo ""
    
    for ((i=0; i<run_count; i++)); do
        local run=$(echo "$runs" | jq ".[$i]")
        local run_id=$(echo "$run" | jq -r '.databaseId')
        local status=$(echo "$run" | jq -r '.status')
        local conclusion=$(echo "$run" | jq -r '.conclusion')
        local created=$(echo "$run" | jq -r '.createdAt')
        local workflow=$(echo "$run" | jq -r '.workflowName')
        
        local icon="❓"
        local color="$NC"
        
        if [ "$status" = "completed" ]; then
            if [ "$conclusion" = "success" ]; then
                icon="✅"
                color="$GREEN"
            else
                icon="❌"
                color="$RED"
            fi
        elif [ "$status" = "in_progress" ]; then
            icon="🔄"
            color="$YELLOW"
        elif [ "$status" = "queued" ]; then
            icon="⏳"
            color="$CYAN"
        fi
        
        echo -e "${color}$icon Run #$run_id${NC}"
        echo "   Workflow: $workflow"
        echo "   Status: $status $([ "$conclusion" != "null" ] && echo "($conclusion)")"
        echo "   Created: $created"
        echo ""
    done
}

# =============================================
# MAIN MENU
# =============================================

show_menu() {
    clear
    cat << "EOF"
╔═══════════════════════════════════════════════╗
║                                               ║
║     DATAGRAM ORCHESTRATOR v2.0                ║
║     Bash Edition (Linux/macOS)                ║
║                                               ║
╚═══════════════════════════════════════════════╝
EOF
    
    echo -e "\n${YELLOW}📋 SETUP & CONFIGURATION${NC}"
    echo "  1. Initialize Configuration"
    echo "  2. Import API Keys"
    echo "  3. Show API Keys Status"
    echo "  4. Import GitHub Tokens"
    echo "  5. Validate GitHub Tokens"
    
    echo -e "\n${YELLOW}🤝 COLLABORATION MANAGEMENT${NC}"
    echo "  6. Auto Invite Collaborators"
    echo "  7. Auto Accept Invitations"
    echo "  8. Auto Set Secrets"
    
    echo -e "\n${YELLOW}🚀 DEPLOYMENT & MONITORING${NC}"
    echo "  9. Deploy to GitHub"
    echo " 10. Trigger Workflow"
    echo " 11. Show Workflow Status"
    
    echo -e "\n${YELLOW}🔧 UTILITIES${NC}"
    echo " 12. View Logs"
    echo " 13. Clean Cache"
    echo " 14. Check Dependencies"
    
    echo -e "\n  0. Exit"
    echo -e "\n═══════════════════════════════════════════════"
}

main() {
    init_directories
    check_dependencies
    
    while true; do
        show_menu
        read -p "Pilih menu (0-14): " choice
        
        case $choice in
            1) init_configuration ;;
            2) import_api_keys ;;
            3) show_api_keys_status ;;
            4) import_github_tokens ;;
            5) validate_github_tokens ;;
            6) auto_invite_collaborators ;;
            7) auto_accept_invitations ;;
            8) auto_set_secrets ;;
            9) deploy_to_github ;;
            10) trigger_workflow ;;
            11) show_workflow_status ;;
            12) 
                if [ -f "$LOG_FILE" ]; then
                    tail -n 50 "$LOG_FILE"
                else
                    print_warning "Log file not found"
                fi
                ;;
            13)
                print_warning "Cleaning cache files..."
                rm -f "$TOKEN_CACHE_FILE" "$INVITED_USERS_FILE" "$ACCEPTED_USERS_FILE" "$SECRETS_SET_FILE"
                print_success "Cache cleaned"
                ;;
            14) check_dependencies ;;
            0)
                print_success "Terima kasih telah menggunakan Datagram Orchestrator!"
                exit 0
                ;;
            *)
                print_warning "Pilihan tidak valid"
                ;;
        esac
        
        if [ "$choice" != "0" ]; then
            echo ""
            read -p "Press Enter to continue..."
        fi
    done
}

# Run main
main
