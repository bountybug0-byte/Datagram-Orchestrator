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

# =============================================
# FEATURE 1: SETUP KONFIGURASI
# =============================================
def initialize_configuration():
    """Inisialisasi konfigurasi dasar."""
    print_header("1. INITIALIZE CONFIGURATION")
    
    config = {}
    config['main_account_username'] = input("Username GitHub utama: ").strip()
    config['main_repo_name'] = input("Nama repository (e.g., datagram-runner): ").strip()
    
    print_warning("\n⚠️  Token akan disembunyikan saat diketik")
    config['main_token'] = getpass.getpass("GitHub Personal Access Token: ").strip()
    
    if not config['main_account_username'] or not config['main_repo_name'] or not config['main_token']:
        print_error("Semua field harus diisi!")
        return
    
    # Validasi token
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

# =============================================
# FEATURE 2 & 3: MANAJEMEN API KEYS
# =============================================
def import_api_keys():
    """Import API keys dari input manual atau file."""
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
            
            # Validasi keys
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
    """Menampilkan status API keys yang tersimpan."""
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

# =============================================
# FEATURE 4 & 5: MANAJEMEN GITHUB TOKEN
# =============================================
def import_github_tokens():
    """Import GitHub tokens dari file."""
    print_header("4. IMPORT GITHUB TOKENS")
    
    source_file = input("Masukkan path ke file .txt berisi token: ").strip()
    source_path = Path(source_file)
    
    if not source_path.is_file():
        print_error(f"File tidak ditemukan: {source_file}")
        return
    
    try:
        content = source_path.read_text(encoding="utf-8")
        all_lines = [line.strip() for line in content.splitlines() if line.strip()]
        
        # Filter hanya token yang valid (dimulai dengan ghp_ atau github_pat_)
        tokens = [
            line for line in all_lines 
            if line.startswith("ghp_") or line.startswith("github_pat_")
        ]
        
        if tokens:
            TOKENS_FILE.write_text("\n".join(tokens), encoding="utf-8")
            print_success(f"✅ Berhasil mengimpor {len(tokens)} token")
            write_log(f"Imported {len(tokens)} GitHub tokens")
        else:
            print_error("Tidak ada token valid (ghp_* atau github_pat_*) ditemukan.")
    
    except Exception as e:
        print_error(f"Error membaca file: {str(e)}")

def validate_github_tokens():
    """Validasi semua GitHub tokens dan cache username."""
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
        
        # Cek cache dulu
        if token in token_cache:
            print_success(f" ✅ @{token_cache[token]} (cached)")
            valid_count += 1
            continue
        
        # Validasi via API
        result = run_gh_api("api user --jq .login", token, max_retries=2)
        
        if result["success"]:
            username = result["output"]
            print_success(f" ✅ @{username}")
            token_cache[token] = username
            valid_count += 1
        else:
            print_error(f" ❌ Invalid")
            invalid_tokens.append(token)
        
        time.sleep(0.5)  # Rate limiting
    
    # Simpan cache
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

# =============================================
# FEATURE 6, 7, 8: LOGIKA KOLABORASI
# =============================================
def invoke_auto_invite():
    """Mengundang semua akun dari token_cache sebagai collaborator."""
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
    
    # Filter user yang belum diundang
    users_to_invite = [
        username for username in token_cache.values()
        if username not in invited_users and username != main_username
    ]
    
    if not users_to_invite:
        print_success("✅ Semua akun sudah diundang sebagai collaborator.")
        return
    
    print_info(f"Akan mengundang {len(users_to_invite)} user baru...")
    repo_path = f"{config['main_account_username']}/{config['main_repo_name']}"
    success_count = 0
    
    for i, username in enumerate(users_to_invite, 1):
        print(f"[{i}/{len(users_to_invite)}] Mengundang @{username}...", end="", flush=True)
        
        result = run_gh_api(
            f"api --silent -X PUT repos/{repo_path}/collaborators/{username} -f permission=push",
            config['main_token']
        )
        
        if result["success"]:
            print_success(" ✅")
            append_to_file(INVITED_USERS_FILE, username)
            success_count += 1
        else:
            print_error(f" ❌ {result['error']}")
        
        time.sleep(1)  # Rate limiting
    
    print("\n" + "═" * 47)
    print_success(f"Proses selesai! Berhasil: {success_count}/{len(users_to_invite)}")
    write_log(f"Auto invite completed: {success_count} successful")

def invoke_auto_accept():
    """Auto-accept invitation untuk semua akun di token_cache."""
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
        
        # Fetch invitations
        result = run_gh_api("api user/repository_invitations", token)
        
        if not result["success"]:
            print_error(f" ❌ Gagal fetch invitations")
            continue
        
        try:
            invitations = json.loads(result["output"])
            
            # Cari invitation untuk target repo
            inv_id = None
            for inv in invitations:
                repo_full_name = inv.get('repository', {}).get('full_name', '').lower()
                if repo_full_name == target_repo:
                    inv_id = inv['id']
                    break
            
            if inv_id:
                # Accept invitation
                accept_result = run_gh_api(
                    f"api --method PATCH /user/repository_invitations/{inv_id} --silent",
                    token
                )
                
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
        
        time.sleep(1)  # Rate limiting
    
    print("\n" + "═" * 47)
    print_success(f"Proses selesai! Invitation baru diterima: {accepted_count}")
    write_log(f"Auto accept completed: {accepted_count} new acceptances")

def invoke_auto_set_secrets():
    """
    Set secrets ke repository (Actions + Codespaces) untuk main repo dan collaborators.
    Support multi-repo secret distribution.
    """
    print_header("8. AUTO SET SECRETS (ACTIONS + CODESPACES)")
    
    config = load_json_file(CONFIG_FILE)
    if not config:
        print_error("Konfigurasi belum diset. Jalankan menu 1 terlebih dahulu.")
        return
    
    if not API_KEYS_FILE.exists() or API_KEYS_FILE.stat().st_size == 0:
        print_error("File API keys kosong. Import API keys terlebih dahulu (menu 2).")
        return
    
    # Baca API keys
    api_keys = read_file_lines(API_KEYS_FILE)
    if not api_keys:
        print_error("Tidak ada API keys yang valid.")
        return
    
    print_info(f"📊 Total API Keys: {len(api_keys)}")
    
    # Format API keys sesuai dengan workflow (plain text multiline)
    api_keys_str = "\n".join(api_keys)
    
    # Tanyakan target repositories
    print("\nPilih target untuk set secrets:")
    print("  1. Main repository saja")
    print("  2. Main repository + semua collaborator repositories")
    
    choice = input("\nPilihan (1/2): ").strip()
    
    target_repos = []
    
    # Main repository
    main_repo = f"{config['main_account_username']}/{config['main_repo_name']}"
    target_repos.append({
        'repo': main_repo,
        'token': config['main_token'],
        'owner': config['main_account_username']
    })
    
    # Jika pilih opsi 2, tambahkan collaborator repos
    if choice == '2':
        token_cache = load_json_file(TOKEN_CACHE_FILE)
        accepted_users = read_file_lines(ACCEPTED_USERS_FILE)
        
        if not token_cache:
            print_warning("Token cache kosong. Hanya akan set secret di main repo.")
        else:
            # Ambil token untuk setiap accepted user
            for token, username in token_cache.items():
                if username in accepted_users and username != config['main_account_username']:
                    # Asumsikan repo name sama untuk semua collaborator
                    collab_repo = f"{username}/{config['main_repo_name']}"
                    target_repos.append({
                        'repo': collab_repo,
                        'token': token,
                        'owner': username
                    })
    
    print_info(f"\n🎯 Target: {len(target_repos)} repository/repositories")
    print_warning("\n⚠️  Proses ini akan:")
    print("  • Set secret 'DATAGRAM_API_KEYS' ke GitHub Actions")
    print("  • Set secret 'DATAGRAM_API_KEYS' ke Codespaces")
    print("  • Secrets akan tersedia untuk workflows dan codespaces")
    
    if input("\nLanjutkan? (y/n): ").lower() != 'y':
        print_warning("Operasi dibatalkan.")
        return
    
    success_count = 0
    failed_repos = []
    
    for i, target in enumerate(target_repos, 1):
        repo_path = target['repo']
        token = target['token']
        owner = target['owner']
        
        print(f"\n[{i}/{len(target_repos)}] Setting secrets untuk: {repo_path}")
        
        # 1. Set Actions Secret
        print("  ├─ Actions Secret...", end="", flush=True)
        actions_result = set_actions_secret(repo_path, token, api_keys_str)
        
        if actions_result["success"]:
            print_success(" ✅")
        else:
            print_error(f" ❌ {actions_result['error']}")
            failed_repos.append({'repo': repo_path, 'type': 'actions', 'error': actions_result['error']})
        
        # 2. Set Codespaces Secret
        print("  └─ Codespaces Secret...", end="", flush=True)
        codespaces_result = set_codespaces_secret(repo_path, token, api_keys_str)
        
        if codespaces_result["success"]:
            print_success(" ✅")
            success_count += 1
        else:
            print_error(f" ❌ {codespaces_result['error']}")
            failed_repos.append({'repo': repo_path, 'type': 'codespaces', 'error': codespaces_result['error']})
        
        time.sleep(1)  # Rate limiting
    
    # Summary
    print("\n" + "═" * 47)
    print_success(f"✅ Berhasil set secrets: {success_count}/{len(target_repos)} repos")
    
    if failed_repos:
        print_warning(f"\n⚠️  {len(failed_repos)} operasi gagal:")
        for fail in failed_repos[:5]:  # Show max 5
            print(f"  • {fail['repo']} ({fail['type']}): {fail['error'][:50]}...")
    
    write_log(f"Auto set secrets completed: {success_count} successful, {len(failed_repos)} failed")
    
    # Save ke cache
    if success_count > 0:
        for target in target_repos:
            append_to_file(SECRETS_SET_FILE, target['owner'])

def set_actions_secret(repo_path: str, token: str, secret_value: str) -> Dict:
    """
    Set Actions secret menggunakan gh CLI.
    """
    try:
        # Escape secret value untuk shell
        escaped_value = secret_value.replace('"', '\\"').replace(', '\\)
        
        command = f'gh secret set DATAGRAM_API_KEYS --body "{escaped_value}" -R {repo_path}'
        result = run_command(command, env={"GH_TOKEN": token}, timeout=30)
        
        if result.returncode == 0:
            return {"success": True, "error": None}
        else:
            return {"success": False, "error": result.stderr.strip() or "Unknown error"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

def set_codespaces_secret(repo_path: str, token: str, secret_value: str) -> Dict:
    """
    Set Codespaces secret di repository level menggunakan GitHub API.
    """
    try:
        # Import PyNaCl untuk enkripsi
        from nacl import encoding, public
        
        # 1. Get repository public key
        owner, repo = repo_path.split('/')
        
        pubkey_result = run_gh_api(
            f"api repos/{owner}/{repo}/codespaces/secrets/public-key",
            token
        )
        
        if not pubkey_result["success"]:
            return {"success": False, "error": f"Failed to get public key: {pubkey_result['error']}"}
        
        try:
            pubkey_data = json.loads(pubkey_result["output"])
            key_id = pubkey_data['key_id']
            public_key = pubkey_data['key']
        except (json.JSONDecodeError, KeyError) as e:
            return {"success": False, "error": f"Invalid public key response: {str(e)}"}
        
        # 2. Encrypt secret value
        public_key_obj = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
        sealed_box = public.SealedBox(public_key_obj)
        encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
        encrypted_value = base64.b64encode(encrypted).decode("utf-8")
        
        # 3. Set secret via API
        payload = json.dumps({
            "encrypted_value": encrypted_value,
            "key_id": key_id
        })
        
        set_result = run_gh_api(
            f"api -X PUT repos/{owner}/{repo}/codespaces/secrets/DATAGRAM_API_KEYS --input -",
            token
        )
        
        # Inject payload via stdin simulation (workaround)
        command = f'echo \'{payload}\' | gh api -X PUT repos/{owner}/{repo}/codespaces/secrets/DATAGRAM_API_KEYS --input -'
        result = run_command(command, env={"GH_TOKEN": token}, timeout=30)
        
        if result.returncode == 0 or result.returncode == 201:
            return {"success": True, "error": None}
        else:
            return {"success": False, "error": result.stderr.strip() or "Failed to set secret"}
    
    except ImportError:
        return {"success": False, "error": "PyNaCl not installed"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# =============================================
# FEATURE 9, 10, 11: DEPLOYMENT & MONITORING
# =============================================
def deploy_to_github():
    """Deploy workflow ke GitHub repository."""
    print_header("9. DEPLOY TO GITHUB")
    
    config = load_json_file(CONFIG_FILE)
    if not config:
        print_error("Konfigurasi belum diset. Jalankan menu 1 terlebih dahulu.")
        return
    
    repo_path = f"{config['main_account_username']}/{config['main_repo_name']}"
    
    print_info(f"Target repository: {repo_path}")
    print_info("Mengecek repository...")
    
    # Cek apakah repo exists
    check_result = run_gh_api(f"api repos/{repo_path}", config['main_token'], max_retries=1)
    
    if not check_result["success"]:
        print_warning("⚠️  Repository tidak ditemukan.")
        
        if input("Buat repository baru? (y/n): ").lower() == 'y':
            create_result = run_gh_api(
                f"repo create {repo_path} --private --confirm",
                config['main_token']
            )
            
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
    
    # Git operations
    print_info("\n📦 Melakukan git operations...")
    
    # Initialize git if needed
    if not Path(".git").exists():
        print_info("Initializing git...")
        run_command("git init")
        run_command(f"git remote add origin https://github.com/{repo_path}.git")
    
    # Add all files
    print_info("Adding files...")
    run_command("git add .")
    
    # Commit
    print_info("Committing...")
    commit_result = run_command('git commit -m "🚀 Deploy Datagram Orchestrator v3.2"')
    
    if commit_result.returncode != 0 and "nothing to commit" not in commit_result.stdout:
        print_warning("⚠️  Commit warning (mungkin tidak ada perubahan)")
    
    # Push
    print_info("Pushing to GitHub...")
    push_result = run_command(
        f"git push -u origin main --force",
        env={"GH_TOKEN": config['main_token']},
        timeout=60
    )
    
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
    """Trigger workflow di GitHub Actions."""
    print_header("10. TRIGGER WORKFLOW")
    
    config = load_json_file(CONFIG_FILE)
    if not config:
        print_error("Konfigurasi belum diset.")
        return
    
    repo_path = f"{config['main_account_username']}/{config['main_repo_name']}"
    
    print_info(f"Target: {repo_path}")
    print_info("Memicu workflow 'datagram-runner.yml'...")
    
    result = run_gh_api(
        f"workflow run datagram-runner.yml -R {repo_path}",
        config['main_token']
    )
    
    if result["success"]:
        print_success("\n✅ Workflow berhasil dipicu!")
        print_info(f"🔗 Monitor di: https://github.com/{repo_path}/actions")
        write_log(f"Workflow triggered for {repo_path}")
    else:
        print_error(f"\n❌ Gagal memicu workflow:")
        print_error(result["error"])

def show_workflow_status():
    """Menampilkan status workflow runs."""
    print_header("11. SHOW WORKFLOW STATUS")
    
    config = load_json_file(CONFIG_FILE)
    if not config:
        print_error("Konfigurasi belum diset.")
        return
    
    repo_path = f"{config['main_account_username']}/{config['main_repo_name']}"
    
    print_info(f"Repository: {repo_path}")
    print_info("Fetching workflow runs...\n")
    
    result = run_gh_api(
        f"run list -R {repo_path} --limit 10",
        config['main_token']
    )
    
    if result["success"]:
        print(result["output"])
        print("\n" + "═" * 47)
        print_info(f"🔗 Detail: https://github.com/{repo_path}/actions")
    else:
        print_error(f"Gagal mendapatkan status: {result['error']}")

# =============================================
# FEATURE 12 & 13: UTILITIES
# =============================================
def view_logs():
    """Menampilkan isi log file."""
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
        
        # Show last 50 lines
        print("═" * 47)
        for line in lines[-50:]:
            print(line)
        print("═" * 47)
        
        if len(lines) > 50:
            print_info(f"\nShowing last 50 of {len(lines)} lines")
    
    except Exception as e:
        print_error(f"Error membaca log: {str(e)}")

def clean_cache():
    """Membersihkan semua file cache."""
    print_header("13. CLEAN CACHE")
    
    from .helpers import (
        TOKEN_CACHE_FILE, INVITED_USERS_FILE, 
        ACCEPTED_USERS_FILE, SECRETS_SET_FILE
    )
    
    cache_files = [
        TOKEN_CACHE_FILE,
        INVITED_USERS_FILE,
        ACCEPTED_USERS_FILE,
        SECRETS_SET_FILE
    ]
    
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
