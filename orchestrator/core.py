# File: orchestrator/core.py
import json
import getpass
import time
import base64
from pathlib import Path
from typing import Dict, List, Optional

from .helpers import (
    print_success, print_error, print_info, print_warning, print_header,
    write_log, run_gh_api, read_file_lines, append_to_file,
    load_json_file, save_json_file, run_command, validate_api_key_format,
    API_KEYS_FILE, TOKENS_FILE, CONFIG_FILE, TOKEN_CACHE_FILE,
    INVITED_USERS_FILE, ACCEPTED_USERS_FILE, SECRETS_SET_FILE
)

def initialize_configuration():
    print_header("1. INITIALIZE CONFIGURATION")
    config = {}
    config['main_account_username'] = input("Username GitHub utama: ").strip()
    config['main_repo_name'] = input("Nama repository (e.g., datagram-runner): ").strip()
    print_warning("\n⚠️  Token akan disembunyikan saat diketik")
    config['main_token'] = getpass.getpass("GitHub Personal Access Token: ").strip()

    if not config['main_account_username'] or not config['main_repo_name'] or not config['main_token']:
        print_error("Semua field harus diisi!")
        return

    print_info("Memvalidasi token...")
    result = run_gh_api("api user --jq .login", config['main_token'], max_retries=2)

    if not result["success"]:
        print_error(f"Token tidak valid: {result['error']}")
        return

    username = result["output"]
    if username != config['main_account_username']:
        print_warning(f"Username token ({username}) tidak sama dengan yang diinput ({config['main_account_username']})")
        if input("Lanjutkan? (y/n): ").lower() != 'y':
            return

    save_json_file(CONFIG_FILE, config)
    print_success(f"✅ Konfigurasi berhasil disimpan!")
    print_info(f"📁 Lokasi: {CONFIG_FILE}")
    write_log(f"Configuration initialized for @{config['main_account_username']}")

def import_api_keys():
    print_header("2. IMPORT API KEYS")
    print("Pilih metode import:")
    print("  1. Input manual (satu per satu)")
    print("  2. Import dari file .txt")
    choice = input("\nPilihan (1/2): ").strip()

    if choice == '1':
        keys = []
        print_info("Masukkan API key (kosongkan untuk selesai)")
        while True:
            key = input(f"API Key #{len(keys) + 1}: ").strip()
            if not key:
                break
            if not validate_api_key_format(key):
                print_warning("⚠️  Format API key tidak valid, skip...")
                continue
            keys.append(key)

        if keys:
            API_KEYS_FILE.write_text("\n".join(keys), encoding="utf-8")
            print_success(f"✅ Berhasil menyimpan {len(keys)} API key(s)")
            write_log(f"Imported {len(keys)} API keys manually")
        else:
            print_warning("Tidak ada API key yang diinput.")

    elif choice == '2':
        source_file = input("Masukkan path ke file .txt: ").strip()
        source_path = Path(source_file)
        if not source_path.is_file():
            print_error(f"File tidak ditemukan: {source_file}")
            return
        try:
            content = source_path.read_text(encoding="utf-8")
            keys = [line.strip() for line in content.splitlines() if line.strip()]
            valid_keys = [k for k in keys if validate_api_key_format(k)]
            invalid_count = len(keys) - len(valid_keys)
            if valid_keys:
                API_KEYS_FILE.write_text("\n".join(valid_keys), encoding="utf-8")
                print_success(f"✅ Berhasil mengimpor {len(valid_keys)} API key(s)")
                if invalid_count > 0:
                    print_warning(f"⚠️  {invalid_count} key tidak valid (diabaikan)")
                write_log(f"Imported {len(valid_keys)} API keys from file")
            else:
                print_error("Tidak ada API key valid yang ditemukan.")
        except Exception as e:
            print_error(f"Error membaca file: {str(e)}")
    else:
        print_warning("Pilihan tidak valid.")

def show_api_keys_status():
    print_header("3. SHOW API KEYS STATUS")
    if not API_KEYS_FILE.exists():
        print_warning("File API keys belum ada.")
        return
    keys = read_file_lines(API_KEYS_FILE)
    if not keys:
        print_warning("File API keys kosong.")
        return
    print_success(f"Total API Keys: {len(keys)}")
    print_info("\nPreview (3 key pertama):")
    for i, key in enumerate(keys[:3], 1):
        masked_key = f"{key[:8]}...{key[-6:]}" if len(key) > 14 else "***"
        print(f"  {i}. 🔑 {masked_key}")
    if len(keys) > 3:
        print_info(f"  ... dan {len(keys) - 3} key lainnya")

def import_github_tokens():
    print_header("4. IMPORT GITHUB TOKENS")
    source_file = input("Masukkan path ke file .txt berisi token: ").strip()
    source_path = Path(source_file)
    if not source_path.is_file():
        print_error(f"File tidak ditemukan: {source_file}")
        return
    try:
        content = source_path.read_text(encoding="utf-8")
        all_lines = [line.strip() for line in content.splitlines() if line.strip()]
        tokens = [line for line in all_lines if line.startswith("ghp_") or line.startswith("github_pat_")]
        if tokens:
            TOKENS_FILE.write_text("\n".join(tokens), encoding="utf-8")
            print_success(f"✅ Berhasil mengimpor {len(tokens)} token")
            write_log(f"Imported {len(tokens)} GitHub tokens")
        else:
            print_error("Tidak ada token valid (ghp_* atau github_pat_*) ditemukan.")
    except Exception as e:
        print_error(f"Error membaca file: {str(e)}")

def validate_github_tokens():
    print_header("5. VALIDATE GITHUB TOKENS")
    if not TOKENS_FILE.exists():
        print_error("File tokens.txt belum ada. Import tokens terlebih dahulu.")
        return
    tokens = read_file_lines(TOKENS_FILE)
    if not tokens:
        print_error("File tokens.txt kosong.")
        return
    print_info(f"Memvalidasi {len(tokens)} token...")
    token_cache = load_json_file(TOKEN_CACHE_FILE)
    valid_count = 0
    invalid_tokens = []

    for i, token in enumerate(tokens, 1):
        print(f"[{i}/{len(tokens)}] Validating token...", end="", flush=True)
        if token in token_cache:
            print_success(f" ✅ @{token_cache[token]} (cached)")
            valid_count += 1
            continue
        result = run_gh_api("api user --jq .login", token, max_retries=2)
        if result["success"]:
            username = result["output"]
            print_success(f" ✅ @{username}")
            token_cache[token] = username
            valid_count += 1
        else:
            print_error(f" ❌ Invalid")
            invalid_tokens.append(token)
        time.sleep(0.5)

    save_json_file(TOKEN_CACHE_FILE, token_cache)
    print("\n" + "═" * 47)
    print_success(f"Validasi selesai! Valid: {valid_count}/{len(tokens)}")
    if invalid_tokens:
        print_warning(f"⚠️  {len(invalid_tokens)} token tidak valid")
        if input("\nHapus token invalid dari file? (y/n): ").lower() == 'y':
            valid_tokens = [t for t in tokens if t not in invalid_tokens]
            TOKENS_FILE.write_text("\n".join(valid_tokens), encoding="utf-8")
            print_success("Token invalid telah dihapus.")
    write_log(f"Token validation completed: {valid_count} valid, {len(invalid_tokens)} invalid")

def invoke_auto_invite():
    print_header("6. AUTO INVITE COLLABORATORS")
    config = load_json_file(CONFIG_FILE)
    if not config:
        print_error("Konfigurasi belum diset. Jalankan menu 1 terlebih dahulu.")
        return
    token_cache = load_json_file(TOKEN_CACHE_FILE)
    if not token_cache:
        print_error("Token cache kosong. Validasi tokens terlebih dahulu (menu 5).")
        return
    invited_users = read_file_lines(INVITED_USERS_FILE)
    main_username = config['main_account_username']
    users_to_invite = [username for username in token_cache.values() if username not in invited_users and username != main_username]
    if not users_to_invite:
        print_success("✅ Semua akun sudah diundang sebagai collaborator.")
        return
    print_info(f"Akan mengundang {len(users_to_invite)} user baru...")
    repo_path = f"{config['main_account_username']}/{config['main_repo_name']}"
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
    print("\n" + "═" * 47)
    print_success(f"Proses selesai! Berhasil: {success_count}/{len(users_to_invite)}")
    write_log(f"Auto invite completed: {success_count} successful")

def invoke_auto_accept():
    print_header("7. AUTO ACCEPT INVITATIONS")
    config = load_json_file(CONFIG_FILE)
    token_cache = load_json_file(TOKEN_CACHE_FILE)
    if not config or not token_cache:
        print_error("Konfigurasi atau token cache tidak ditemukan.")
        return
    target_repo = f"{config['main_account_username']}/{config['main_repo_name']}".lower()
    accepted_users = read_file_lines(ACCEPTED_USERS_FILE)
    print_info(f"Target repository: {target_repo}")
    print_info(f"Mengecek {len(token_cache)} akun...\n")
    accepted_count = 0
    for i, (token, username) in enumerate(token_cache.items(), 1):
        if username in accepted_users:
            print(f"[{i}/{len(token_cache)}] @{username} - ✅ Already accepted")
            continue
        print(f"[{i}/{len(token_cache)}] @{username}...", end="", flush=True)
        result = run_gh_api("api user/repository_invitations", token)
        if not result["success"]:
            print_error(f" ❌ Gagal fetch invitations")
            continue
        try:
            invitations = json.loads(result["output"])
            inv_id = None
            for inv in invitations:
                repo_full_name = inv.get('repository', {}).get('full_name', '').lower()
                if repo_full_name == target_repo:
                    inv_id = inv['id']
                    break
            if inv_id:
                accept_result = run_gh_api(f"api --method PATCH /user/repository_invitations/{inv_id} --silent", token)
                if accept_result["success"]:
                    print_success(" ✅ Accepted")
                    append_to_file(ACCEPTED_USERS_FILE, username)
                    accepted_count += 1
                else:
                    print_error(f" ❌ Gagal accept: {accept_result['error']}")
            else:
                print_info(" ℹ️  No invitation found")
        except json.JSONDecodeError as e:
            print_error(f" ❌ Gagal parse JSON")
            write_log(f"JSON Parse Error for @{username}: {str(e)}")
        time.sleep(1)
    print("\n" + "═" * 47)
    print_success(f"Proses selesai! Invitation baru diterima: {accepted_count}")
    write_log(f"Auto accept completed: {accepted_count} new acceptances")

def validate_repo_access(repo_path: str, token: str) -> Dict:
    """Check if repo exists and has required permissions"""
    result = run_gh_api(f"api repos/{repo_path} --jq '.permissions.admin,.permissions.push'", token, max_retries=1)
    if result["success"]:
        try:
            permissions = result["output"].strip().split('\n')
            has_admin = permissions[0].lower() == "true" if len(permissions) > 0 else False
            has_push = permissions[1].lower() == "true" if len(permissions) > 1 else False
            return {"success": True, "has_admin": has_admin, "has_push": has_push}
        except:
            return {"success": False, "error": "Invalid response"}
    return {"success": False, "error": result["error"]}

def enable_actions(repo_path: str, token: str) -> Dict:
    """Enable GitHub Actions for repository"""
    try:
        command = f"gh api -X PUT repos/{repo_path}/actions/permissions -f enabled=true"
        result = run_command(command, env={"GH_TOKEN": token}, timeout=15)
        if result.returncode == 0:
            return {"success": True, "error": None}
        else:
            error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
            return {"success": False, "error": error_msg}
    except Exception as e:
        return {"success": False, "error": str(e)}

def set_actions_secret(repo_path: str, token: str, secret_value: str) -> Dict:
    """
    Set repository-scoped Actions secret using GitHub CLI.
    Target: https://github.com/{owner}/{repo}/settings/secrets/actions/new
    """
    try:
        escaped_value = secret_value.replace("'", "'\\''")
        command = f"echo '{escaped_value}' | gh secret set DATAGRAM_API_KEYS --repo {repo_path} --body -"
        result = run_command(command, env={"GH_TOKEN": token}, timeout=30)
        
        if result.returncode == 0:
            return {"success": True, "error": None}
        else:
            error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
            return {"success": False, "error": error_msg}
    except Exception as e:
        return {"success": False, "error": f"Exception: {str(e)}"}

def set_codespaces_secret(repo_path: str, token: str, secret_value: str) -> Dict:
    """
    Set repository-scoped Codespaces secret using GitHub CLI with --app codespaces flag.
    Target: https://github.com/{owner}/{repo}/settings/secrets/codespaces/new
    
    Requires GitHub CLI v2.40.0+
    """
    try:
        escaped_value = secret_value.replace("'", "'\\''")
        command = f"echo '{escaped_value}' | gh secret set DATAGRAM_API_KEYS --app codespaces --repo {repo_path} --body -"
        result = run_command(command, env={"GH_TOKEN": token}, timeout=30)
        
        if result.returncode == 0:
            return {"success": True, "error": None}
        else:
            error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
            if "404" in error_msg or "Not Found" in error_msg:
                return {"success": False, "error": "Repository not found or no access"}
            elif "403" in error_msg or "Forbidden" in error_msg:
                return {"success": False, "error": "Permission denied (need admin access)"}
            else:
                return {"success": False, "error": error_msg}
    except Exception as e:
        return {"success": False, "error": f"Exception: {str(e)}"}

def invoke_auto_set_secrets():
    print_header("8. AUTO SET SECRETS (ACTIONS + CODESPACES)")
    config = load_json_file(CONFIG_FILE)
    if not config:
        print_error("Konfigurasi belum diset. Jalankan menu 1 terlebih dahulu.")
        return
    if not API_KEYS_FILE.exists() or API_KEYS_FILE.stat().st_size == 0:
        print_error("File API keys kosong. Import API keys terlebih dahulu (menu 2).")
        return

    api_keys = read_file_lines(API_KEYS_FILE)
    if not api_keys:
        print_error("Tidak ada API keys yang valid.")
        return

    print_info(f"📊 Total API Keys: {len(api_keys)}")
    api_keys_json = json.dumps(api_keys)

    print("\nPilih target untuk set secrets:")
    print("  1. Main repository saja")
    print("  2. Main repository + semua collaborator repositories")
    choice = input("\nPilihan (1/2): ").strip()

    target_repos = []
    main_repo = f"{config['main_account_username']}/{config['main_repo_name']}"
    target_repos.append({'repo': main_repo, 'token': config['main_token'], 'owner': config['main_account_username']})

    if choice == '2':
        token_cache = load_json_file(TOKEN_CACHE_FILE)
        accepted_users = read_file_lines(ACCEPTED_USERS_FILE)
        if not token_cache:
            print_warning("Token cache kosong. Hanya akan set secret di main repo.")
        else:
            for token, username in token_cache.items():
                if username in accepted_users and username != config['main_account_username']:
                    collab_repo = f"{username}/{config['main_repo_name']}"
                    target_repos.append({'repo': collab_repo, 'token': token, 'owner': username})

    print_info(f"\n🎯 Target: {len(target_repos)} repository/repositories")
    print_warning("\n⚠️  Proses ini akan:")
    print("  • Validate repository access")
    print("  • Enable GitHub Actions (jika belum aktif)")
    print("  • Set secret 'DATAGRAM_API_KEYS' ke GitHub Actions")
    print("  • Set secret 'DATAGRAM_API_KEYS' ke Codespaces")
    print("  • Format: JSON array untuk multi-node support")

    if input("\nLanjutkan? (y/n): ").lower() != 'y':
        print_warning("Operasi dibatalkan.")
        return

    # Pre-validation: filter repos dengan akses valid
    print_info("\n📋 Validating repository access...")
    validated_repos = []
    for target in target_repos:
        repo_path = target['repo']
        token = target['token']
        print(f"  Checking {repo_path}...", end="", flush=True)
        access = validate_repo_access(repo_path, token)
        if access["success"]:
            if access["has_admin"] or access["has_push"]:
                print_success(" ✅")
                validated_repos.append(target)
            else:
                print_warning(" ⚠️  No push access")
        else:
            print_error(f" ❌ {access['error']}")
        time.sleep(0.3)

    if not validated_repos:
        print_error("\n❌ Tidak ada repository yang dapat diakses.")
        return

    print_info(f"\n✅ {len(validated_repos)}/{len(target_repos)} repositories valid")
    
    success_count = 0
    failed_repos = []

    for i, target in enumerate(validated_repos, 1):
        repo_path = target['repo']
        token = target['token']
        owner = target['owner']
        print(f"\n[{i}/{len(validated_repos)}] Processing: {repo_path}")
        
        # Enable Actions
        print("  ├─ Enabling Actions...", end="", flush=True)
        enable_result = enable_actions(repo_path, token)
        if enable_result["success"]:
            print_success(" ✅")
        else:
            print_warning(f" ⚠️  {enable_result['error'][:40]}...")
        
        # Set Actions Secret
        print("  ├─ Actions Secret...", end="", flush=True)
        actions_result = set_actions_secret(repo_path, token, api_keys_json)
        if actions_result["success"]:
            print_success(" ✅")
        else:
            print_error(f" ❌ {actions_result['error'][:40]}...")
            failed_repos.append({'repo': repo_path, 'type': 'actions', 'error': actions_result['error']})
        
        # Set Codespaces Secret
        print("  └─ Codespaces Secret...", end="", flush=True)
        codespaces_result = set_codespaces_secret(repo_path, token, api_keys_json)
        if codespaces_result["success"]:
            print_success(" ✅")
            if actions_result["success"]:
                success_count += 1
        else:
            print_error(f" ❌ {codespaces_result['error'][:40]}...")
            failed_repos.append({'repo': repo_path, 'type': 'codespaces', 'error': codespaces_result['error']})
        
        time.sleep(1)

    print("\n" + "═" * 47)
    print_success(f"✅ Berhasil set secrets: {success_count}/{len(validated_repos)} repos")
    if failed_repos:
        print_warning(f"\n⚠️  {len(failed_repos)} operasi gagal:")
        for fail in failed_repos[:5]:
            print(f"  • {fail['repo']} ({fail['type']}): {fail['error'][:50]}...")
    write_log(f"Auto set secrets completed: {success_count} successful, {len(failed_repos)} failed")
    if success_count > 0:
        for target in validated_repos:
            append_to_file(SECRETS_SET_FILE, target['owner'])

def deploy_to_github():
    print_header("9. DEPLOY TO GITHUB")
    config = load_json_file(CONFIG_FILE)
    if not config:
        print_error("Konfigurasi belum diset. Jalankan menu 1 terlebih dahulu.")
        return
    repo_path = f"{config['main_account_username']}/{config['main_repo_name']}"
    print_info(f"Target repository: {repo_path}")
    print_info("Mengecek repository...")
    check_result = run_gh_api(f"api repos/{repo_path}", config['main_token'], max_retries=1)
    if not check_result["success"]:
        print_warning("⚠️  Repository tidak ditemukan.")
        if input("Buat repository baru? (y/n): ").lower() == 'y':
            create_result = run_gh_api(f"repo create {repo_path} --private --confirm", config['main_token'])
            if not create_result["success"]:
                print_error(f"Gagal membuat repository: {create_result['error']}")
                return
            print_success("✅ Repository berhasil dibuat!")
            time.sleep(2)
        else:
            print_warning("Operasi dibatalkan.")
            return
    else:
        print_success("✅ Repository ditemukan!")
    print_info("\n📦 Melakukan git operations...")
    if not Path(".git").exists():
        print_info("Initializing git...")
        run_command("git init")
        run_command(f"git remote add origin https://github.com/{repo_path}.git")
    print_info("Adding files...")
    run_command("git add .")
    print_info("Committing...")
    commit_result = run_command('git commit -m "🚀 Deploy Datagram Orchestrator v3.2"')
    if commit_result.returncode != 0 and "nothing to commit" not in commit_result.stdout:
        print_warning("⚠️  Commit warning (mungkin tidak ada perubahan)")
    print_info("Pushing to GitHub...")
    push_result = run_command(f"git push -u origin main --force", env={"GH_TOKEN": config['main_token']}, timeout=60)
    if push_result.returncode == 0:
        print_success("\n✅ Deployment berhasil!")
        print_info(f"🔗 Repository: https://github.com/{repo_path}")
        print_info(f"🔗 Actions: https://github.com/{repo_path}/actions")
        write_log(f"Deployment successful to {repo_path}")
    else:
        print_error(f"\n❌ Gagal melakukan push:")
        print_error(push_result.stderr)
        write_log(f"Deployment failed: {push_result.stderr}")

def invoke_workflow_trigger():
    print_header("10. TRIGGER WORKFLOW")
    config = load_json_file(CONFIG_FILE)
    if not config:
        print_error("Konfigurasi belum diset.")
        return
    repo_path = f"{config['main_account_username']}/{config['main_repo_name']}"
    print_info(f"Target: {repo_path}")
    print_info("Memicu workflow 'datagram-runner.yml'...")
    result = run_gh_api(f"workflow run datagram-runner.yml -R {repo_path}", config['main_token'])
    if result["success"]:
        print_success("\n✅ Workflow berhasil dipicu!")
        print_info(f"🔗 Monitor di: https://github.com/{repo_path}/actions")
        write_log(f"Workflow triggered for {repo_path}")
    else:
        print_error(f"\n❌ Gagal memicu workflow:")
        print_error(result["error"])

def show_workflow_status():
    print_header("11. SHOW WORKFLOW STATUS")
    config = load_json_file(CONFIG_FILE)
    if not config:
        print_error("Konfigurasi belum diset.")
        return
    repo_path = f"{config['main_account_username']}/{config['main_repo_name']}"
    print_info(f"Repository: {repo_path}")
    print_info("Fetching workflow runs...\n")
    result = run_gh_api(f"run list -R {repo_path} --limit 10", config['main_token'])
    if result["success"]:
        print(result["output"])
        print("\n" + "═" * 47)
        print_info(f"🔗 Detail: https://github.com/{repo_path}/actions")
    else:
        print_error(f"Gagal mendapatkan status: {result['error']}")

def view_logs():
    print_header("12. VIEW LOGS")
    from .helpers import LOG_FILE
    if not LOG_FILE.exists():
        print_warning("File log belum ada.")
        return
    try:
        log_content = LOG_FILE.read_text(encoding="utf-8")
        if not log_content.strip():
            print_warning("File log kosong.")
            return
        lines = log_content.splitlines()
        print_info(f"Total log entries: {len(lines)}")
        print_info(f"Log file: {LOG_FILE}\n")
        print("═" * 47)
        for line in lines[-50:]:
            print(line)
        print("═" * 47)
        if len(lines) > 50:
            print_info(f"\nShowing last 50 of {len(lines)} lines")
    except Exception as e:
        print_error(f"Error membaca log: {str(e)}")

def clean_cache():
    print_header("13. CLEAN CACHE")
    from .helpers import TOKEN_CACHE_FILE, INVITED_USERS_FILE, ACCEPTED_USERS_FILE, SECRETS_SET_FILE
    cache_files = [TOKEN_CACHE_FILE, INVITED_USERS_FILE, ACCEPTED_USERS_FILE, SECRETS_SET_FILE]
    print_warning("⚠️  Ini akan menghapus semua file cache:")
    for f in cache_files:
        status = "✓ exists" if f.exists() else "✗ not found"
        print(f"  • {f.name} ({status})")
    if input("\nLanjutkan? (y/n): ").lower() != 'y':
        print_warning("Operasi dibatalkan.")
        return
    deleted_count = 0
    for cache_file in cache_files:
        if cache_file.exists():
            try:
                cache_file.unlink()
                deleted_count += 1
                print_success(f"✅ Deleted: {cache_file.name}")
            except Exception as e:
                print_error(f"❌ Failed to delete {cache_file.name}: {str(e)}")
    print("\n" + "═" * 47)
    print_success(f"Cache berhasil dibersihkan! ({deleted_count} file dihapus)")
    write_log("Cache cleaned")
