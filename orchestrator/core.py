# File: orchestrator/core.py

import json
import getpass
import time
from pathlib import Path
from typing import Dict, List, Any
from .helpers import (
    print_success,
    print_error,
    print_info,
    print_warning,
    print_header,
    write_log,
    run_gh_api,
    read_file_lines,
    append_to_file,
    load_json_file,
    save_json_file,
    run_command,
    validate_api_key_format,
    API_KEYS_FILE,
    TOKENS_FILE,
    CONFIG_FILE,
    TOKEN_CACHE_FILE,
    INVITED_USERS_FILE,
    ACCEPTED_USERS_FILE,
    FORKED_REPOS_FILE,
    SECRETS_SET_FILE,
    CACHE_DIR,
    LOGS_DIR
)

def initialize_configuration():
    print_header("1. INITIALIZE CONFIGURATION")
    config = {}
    config['main_account_username'] = input("Username GitHub utama: ").strip()
    config['main_repo_name'] = input("Nama repository: ").strip()
    print_warning("\n⚠️ Token akan disembunyikan saat diketik")
    config['main_token'] = getpass.getpass("GitHub Personal Access Token: ").strip()
    if not all(config.values()):
        print_error("Semua field harus diisi!"); return
    print_info("Memvalidasi token...")
    result = run_gh_api("api user", config['main_token'], max_retries=2)
    if not result["success"]:
        print_error(f"Token tidak valid: {result['error']}"); return
    save_json_file(CONFIG_FILE, config)
    print_success(f"✅ Konfigurasi berhasil disimpan di {CONFIG_FILE}")

def import_api_keys():
    print_header("2. IMPORT API KEYS")
    print("Pilih metode:\n 1. Input manual\n 2. Import dari file .txt")
    choice = input("\nPilihan (1/2): ").strip()
    keys = []
    if choice == '1':
        print_info("Masukkan API key (kosongkan untuk selesai)")
        while True:
            key = input(f"API Key #{len(keys) + 1}: ").strip()
            if not key:
                break
            if not validate_api_key_format(key):
                print_warning("⚠️ Format API key tidak valid, skip...")
                continue
            keys.append(key)
    elif choice == '2':
        source_file = input("Masukkan path ke file .txt: ").strip()
        if not Path(source_file).is_file():
            print_error(f"File tidak ditemukan: {source_file}"); return
        keys = read_file_lines(Path(source_file))
    else:
        print_warning("Pilihan tidak valid."); return
    valid_keys = [k for k in keys if k and len(k) > 10]
    if valid_keys:
        API_KEYS_FILE.write_text("\n".join(valid_keys), encoding="utf-8")
        print_success(f"✅ Berhasil menyimpan {len(valid_keys)} API key(s)")
    else:
        print_warning("Tidak ada API key valid yang diinput.")

def show_api_keys_status():
    print_header("3. SHOW API KEYS STATUS")
    if not API_KEYS_FILE.exists():
        print_warning("File API keys belum ada."); return
    keys = read_file_lines(API_KEYS_FILE)
    print_success(f"Total API Keys: {len(keys)}")
    if keys:
        print_info("\nPreview (3 key pertama):")
        for i, key in enumerate(keys[:3], 1):
            print(f" {i}. {key[:8]}...{key[-6:]}")

def import_github_tokens():
    print_header("4. IMPORT GITHUB TOKENS")
    source_file = input("Masukkan path ke file .txt berisi token: ").strip()
    if not Path(source_file).is_file():
        print_error(f"File tidak ditemukan: {source_file}"); return
    tokens = [line for line in read_file_lines(Path(source_file)) if line.startswith(("ghp_", "github_pat_"))]
    if tokens:
        TOKENS_FILE.write_text("\n".join(tokens), encoding="utf-8")
        print_success(f"✅ Berhasil mengimpor {len(tokens)} token")
    else:
        print_error("Tidak ada token valid ditemukan.")

def validate_github_tokens():
    print_header("5. VALIDATE GITHUB TOKENS")
    if not TOKENS_FILE.exists():
        print_error("File tokens.txt belum ada."); return
    tokens = read_file_lines(TOKENS_FILE)
    print_info(f"Memvalidasi {len(tokens)} token...")
    token_cache = load_json_file(TOKEN_CACHE_FILE)
    valid_tokens, invalid_tokens = [], []
    for i, token in enumerate(tokens, 1):
        print(f"[{i}/{len(tokens)}] Validating...", end="", flush=True)
        if token in token_cache:
            print_success(f" ✅ @{token_cache[token]} (cached)"); valid_tokens.append(token); continue
        result = run_gh_api("api user --jq .login", token, max_retries=2)
        if result["success"]:
            username = result["output"]
            print_success(f" ✅ @{username}")
            token_cache[token] = username
            valid_tokens.append(token)
        else:
            print_error(f" ❌ Invalid"); invalid_tokens.append(token)
    save_json_file(TOKEN_CACHE_FILE, token_cache)
    if valid_tokens:
        TOKENS_FILE.write_text("\n".join(valid_tokens), encoding="utf-8")
        print_success(f"\nValidasi selesai! Valid: {len(valid_tokens)}/{len(tokens)}. Token invalid otomatis dihapus.")
    else:
        print_warning("Tidak ada token valid.")

def invoke_auto_invite():
    print_header("6. AUTO INVITE COLLABORATORS")
    config = load_json_file(CONFIG_FILE)
    if not config:
        print_error("Konfigurasi belum diset."); return
    token_cache = load_json_file(TOKEN_CACHE_FILE)
    if not token_cache:
        print_error("Token cache kosong."); return
    invited_users = read_file_lines(INVITED_USERS_FILE)
    main_username = config['main_account_username']
    users_to_invite = [u for u in token_cache.values() if u not in invited_users and u != main_username]
    if not users_to_invite:
        print_success("✅ Semua akun sudah diundang."); return
    print_info(f"Akan mengundang {len(users_to_invite)} user baru...")
    repo_path = f"{main_username}/{config['main_repo_name']}"
    success_count = 0
    for i, username in enumerate(users_to_invite, 1):
        print(f"[{i}/{len(users_to_invite)}] Mengundang @{username}...", end="", flush=True)
        result = run_gh_api(f"api --silent -X PUT repos/{repo_path}/collaborators/{username} -f permission=push", config['main_token'])
        if result["success"]:
            print_success(" ✅")
            append_to_file(INVITED_USERS_FILE, username)
            success_count += 1
        else:
            print_error(f" ❌ {result['error']}")
        time.sleep(1)
    print_success(f"\nProses selesai! Berhasil: {success_count}/{len(users_to_invite)}")

def invoke_auto_accept():
    print_header("7. AUTO ACCEPT INVITATIONS")
    config = load_json_file(CONFIG_FILE)
    token_cache = load_json_file(TOKEN_CACHE_FILE)
    if not config or not token_cache:
        print_error("Konfigurasi atau token cache tidak ditemukan."); return
    target_repo = f"{config['main_account_username']}/{config['main_repo_name']}".lower()
    accepted_users = read_file_lines(ACCEPTED_USERS_FILE)
    print_info(f"Target: {target_repo}\nMengecek {len(token_cache)} akun...")
    accepted_count = 0
    for i, (token, username) in enumerate(token_cache.items(), 1):
        if username in accepted_users:
            print(f"[{i}/{len(token_cache)}] @{username} - ✅ Already accepted")
            continue
        print(f"[{i}/{len(token_cache)}] @{username}...", end="", flush=True)
        result = run_gh_api("api user/repository_invitations", token)
        if not result["success"]:
            print_error(f" ❌ Gagal fetch invitations"); continue
        try:
            invitations = json.loads(result["output"])
            inv_id = next((inv['id'] for inv in invitations if inv.get('repository', {}).get('full_name', '').lower() == target_repo), None)
            if inv_id:
                accept_result = run_gh_api(f"api --method PATCH /user/repository_invitations/{inv_id} --silent", token)
                if accept_result["success"]:
                    print_success(" ✅ Accepted")
                    append_to_file(ACCEPTED_USERS_FILE, username)
                    accepted_count += 1
                else:
                    print_error(f" ❌ Gagal accept: {accept_result['error']}")
            else:
                print_info(" ℹ️ No invitation found")
        except (json.JSONDecodeError, KeyError):
            print_error(f" ❌ Gagal parse JSON")
        time.sleep(1)
    print_success(f"\nProses selesai! Invitation baru diterima: {accepted_count}")

def invoke_auto_fork():
    print_header("8. AUTO FORK REPOSITORY")
    config = load_json_file(CONFIG_FILE)
    if not config:
        print_error("Konfigurasi belum diset."); return
    token_cache = load_json_file(TOKEN_CACHE_FILE)
    if not token_cache:
        print_error("Token cache kosong."); return
    forked_users = read_file_lines(FORKED_REPOS_FILE)
    main_username = config['main_account_username']
    source_repo = f"{main_username}/{config['main_repo_name']}"
    users_to_fork = {u: t for t, u in token_cache.items() if u not in forked_users and u != main_username}
    if not users_to_fork:
        print_success("✅ Semua akun sudah melakukan fork."); return
    print_info(f"Akan melakukan fork untuk {len(users_to_fork)} user baru...")
    success_count = 0
    for i, (username, token) in enumerate(users_to_fork.items(), 1):
        print(f"[{i}/{len(users_to_fork)}] Forking untuk @{username}...", end="", flush=True)
        result = run_gh_api(f"api -X POST repos/{source_repo}/forks", token)
        if result["success"] or "fork exists" in result.get("error", ""):
            print_success(" ✅")
            if username not in forked_users:
                append_to_file(FORKED_REPOS_FILE, username)
            success_count += 1
        else:
            print_error(f" ❌ {result.get('error', 'Unknown')}")
        time.sleep(2)
    print_success(f"\nProses fork selesai! Berhasil: {success_count}/{len(users_to_fork)}")

def enable_actions(repo_path: str, token: str) -> bool:
    max_retries = 3
    for attempt in range(max_retries):
        result = run_gh_api(f"api -X PUT repos/{repo_path}/actions/permissions -f enabled=true -f allowed_actions=all", token)
        if result["success"]:
            return True
        print_warning(f"Attempt {attempt + 1}/{max_retries} failed: {result['error']}")
        time.sleep(5)
    return False

def enable_workflow_with_retry(repo_path: str, token: str, workflow_file: str) -> bool:
    max_retries = 8
    base_delay = 15
    for attempt in range(max_retries):
        delay = base_delay * (2 ** attempt)
        print_info(f"Attempt {attempt + 1}/{max_retries}: Waiting {delay}s for workflow sync...")
        time.sleep(delay)
        check_result = run_gh_api(f"api repos/{repo_path}/actions/workflows", token, timeout=60)
        if not check_result["success"]:
            print_warning(f"Failed to list workflows: {check_result['error']}")
            continue
        try:
            workflows_data = json.loads(check_result["output"])
            workflows = workflows_data.get("workflows", [])
            workflow_id = None
            for wf in workflows:
                if wf.get("path") == f".github/workflows/{workflow_file}" or wf.get("name") == workflow_file.replace(".yml", "").replace(".yaml", ""):
                    workflow_id = wf.get("id")
                    break
            if workflow_id:
                enable_result = run_gh_api(f"api -X PUT repos/{repo_path}/actions/workflows/{workflow_id}/enable", token, timeout=30)
                if enable_result["success"]:
                    print_success(f"✅ Workflow enabled successfully")
                    return True
                error_msg = enable_result.get("error", "")
                if "already enabled" in error_msg.lower():
                    print_success(f"✅ Workflow already enabled")
                    return True
                print_warning(f"Enable failed: {error_msg}")
            else:
                print_warning(f"Workflow '{workflow_file}' not found in {len(workflows)} available workflows")
                if attempt == max_retries - 1 and workflows:
                    print_info("Available workflows:")
                    for wf in workflows[:5]:
                        print(f" - {wf.get('name')} ({wf.get('path')})")
        except json.JSONDecodeError as e:
            print_error(f"JSON decode error: {e}")
        except Exception as e:
            print_error(f"Unexpected error: {e}")
    print_error(f"❌ Failed to enable workflow after {max_retries} attempts")
    return False

def set_secret(repo_path: str, token: str, name: str, value: str, app: str = "") -> bool:
    app_flag = f"--app {app}" if app else ""
    command = f"echo '{value}' | gh secret set {name} --repo \"{repo_path}\" {app_flag} --body -"
    result = run_command(command, env={"GH_TOKEN": token})
    return result.returncode == 0

def invoke_auto_set_secrets():
    print_header("9. AUTO SET SECRETS")
    config = load_json_file(CONFIG_FILE)
    if not config:
        print_error("Konfigurasi belum diset."); return
    api_keys = read_file_lines(API_KEYS_FILE)
    if not api_keys:
        print_error("File API keys kosong."); return
    api_keys_json = json.dumps(api_keys).replace("'", "'\\''")
    print("Pilih target:\n 1. Main repo saja\n 2. Main repo + semua forked repos")
    choice = input("\nPilihan (1/2): ").strip()
    targets = [{'repo': f"{config['main_account_username']}/{config['main_repo_name']}", 'token': config['main_token']}]
    if choice == '2':
        token_cache, forked_users = load_json_file(TOKEN_CACHE_FILE), read_file_lines(FORKED_REPOS_FILE)
        targets.extend([{'repo': f"{u}/{config['main_repo_name']}", 'token': t} for t, u in token_cache.items() if u in forked_users])
    if input(f"\n🎯 Target: {len(targets)} repos. Lanjutkan? (y/n): ").lower() != 'y':
        print_warning("Operasi dibatalkan."); return
    secrets_set_log = read_file_lines(SECRETS_SET_FILE)
    success_count = 0
    for i, target in enumerate(targets, 1):
        repo_path, token = target['repo'], target['token']
        print(f"\n[{i}/{len(targets)}] Processing: {repo_path}")
        if repo_path in secrets_set_log:
            print_info(" ℹ️ Already set (skipped)"); continue
        print_info(" 🔓 Enabling GitHub Actions...")
        if not enable_actions(repo_path, token):
            print_error(" ❌ Failed to enable Actions"); continue
        time.sleep(3)
        print_info(f" 🔑 Setting secret DATAGRAM_API_KEYS...")
        if set_secret(repo_path, token, "DATAGRAM_API_KEYS", api_keys_json):
            print_success(" ✅ Secret set successfully")
            append_to_file(SECRETS_SET_FILE, repo_path)
            success_count += 1
        else:
            print_error(" ❌ Failed to set secret")
        time.sleep(2)
    print_success(f"\n✅ Selesai! Berhasil: {success_count}/{len(targets)}")

def deploy_to_github():
    print_header("10. DEPLOY TO GITHUB")
    config = load_json_file(CONFIG_FILE)
    if not config:
        print_error("Konfigurasi belum diset."); return
    token_cache, forked_users = load_json_file(TOKEN_CACHE_FILE), read_file_lines(FORKED_REPOS_FILE)
    if not token_cache:
        print_error("Token cache kosong."); return
    workflow_file = "datagram-runner.yml"
    workflow_source = Path(__file__).parent.parent / ".github" / "workflows" / workflow_file
    if not workflow_source.exists():
        print_error(f"File workflow tidak ditemukan: {workflow_source}"); return
    print("Pilih target deployment:\n 1. Main repo saja\n 2. Semua forked repos\n 3. Main + semua forks")
    choice = input("\nPilihan (1/2/3): ").strip()
    targets = []
    if choice in ['1', '3']:
        targets.append({'repo': f"{config['main_account_username']}/{config['main_repo_name']}", 'token': config['main_token'], 'username': config['main_account_username']})
    if choice in ['2', '3']:
        targets.extend([{'repo': f"{u}/{config['main_repo_name']}", 'token': t, 'username': u} for t, u in token_cache.items() if u in forked_users])
    if not targets:
        print_warning("Tidak ada target yang dipilih."); return
    if input(f"\n🎯 Akan deploy ke {len(targets)} repo. Lanjutkan? (y/n): ").lower() != 'y':
        print_warning("Operasi dibatalkan."); return
    workflow_content = workflow_source.read_text(encoding='utf-8')
    success_count = 0
    for i, target in enumerate(targets, 1):
        repo_path, token, username = target['repo'], target['token'], target['username']
        print(f"\n{'='*47}")
        print(f"[{i}/{len(targets)}] Deploying to: {repo_path}")
        print(f"{'='*47}")
        temp_dir = Path(f"/tmp/deploy_{username}_{int(time.time())}")
        try:
            print_info("📥 Cloning repository...")
            clone_result = run_command(f"git clone https://{token}@github.com/{repo_path}.git {temp_dir}", timeout=120)
            if clone_result.returncode != 0:
                print_error(f"❌ Clone failed: {clone_result.stderr}"); continue
            workflow_dir = temp_dir / ".github" / "
