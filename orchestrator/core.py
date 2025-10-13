# File: orchestrator/core.py
import json
import getpass
import time
import os
import tempfile
from pathlib import Path

# Impor helper dan path dari file helpers.py
from .helpers import (
    print_success, print_error, print_info, print_warning, print_header,
    write_log, run_gh_api, read_file_lines, append_to_file,
    load_json_file, save_json_file, run_command,
    validate_github_username, validate_repo_name, validate_github_token, validate_api_key,
    API_KEYS_FILE, TOKENS_FILE, CONFIG_FILE, TOKEN_CACHE_FILE,
    INVITED_USERS_FILE, ACCEPTED_USERS_FILE, SECRETS_SET_FILE, LOG_FILE
)

# =============================================
# SEMUA FUNGSI LAINNYA (1-7) TETAP SAMA
# ... (kode dari Menu 1 hingga 7 tidak perlu diubah) ...
# =============================================

# =============================================
# FEATURE 1: SETUP KONFIGURASI (WITH VALIDATION)
# =============================================
def initialize_configuration():
    print_header("1. INITIALIZE CONFIGURATION")
    config = {}
    
    # Validate username
    while True:
        username = input("Username GitHub utama: ").strip()
        valid, msg = validate_github_username(username)
        if valid:
            config['main_account_username'] = username
            break
        print_error(msg)
    
    # Validate repo name
    while True:
        repo_name = input("Nama repository (e.g., datagram-runner): ").strip()
        valid, msg = validate_repo_name(repo_name)
        if valid:
            config['main_repo_name'] = repo_name
            break
        print_error(msg)
    
    # Validate token
    while True:
        token = getpass.getpass("GitHub Personal Access Token (input tersembunyi): ").strip()
        valid, msg = validate_github_token(token)
        if valid:
            config['main_token'] = token
            break
        print_error(msg)
    
    try:
        save_json_file(CONFIG_FILE, config)
        print_success(f"Konfigurasi berhasil disimpan ke: {CONFIG_FILE}")
        write_log("Configuration initialized successfully")
    except Exception as e:
        print_error(f"Gagal menyimpan konfigurasi: {str(e)}")
        write_log(f"Configuration save failed: {str(e)}")

# =============================================
# FEATURE 2 & 3: MANAJEMEN API KEYS (WITH VALIDATION)
# =============================================
def import_api_keys():
    print_header("2. IMPORT API KEYS")
    print("Pilih metode import:\n  1. Input manual\n  2. Import dari file .txt")
    choice = input("\nPilihan (1/2): ").strip()
    
    if choice == '1':
        keys = []
        print_info("Masukkan API keys satu per satu. Kosongkan untuk selesai.")
        while True:
            key = input(f"API Key #{len(keys) + 1}: ").strip()
            if not key: 
                break
            
            valid, msg = validate_api_key(key)
            if not valid:
                print_error(msg)
                continue
            
            keys.append(key)
            print_success(f"Key #{len(keys)} added")
        
        if keys:
            try:
                API_KEYS_FILE.write_text("\n".join(keys), encoding="utf-8")
                print_success(f"Berhasil menyimpan {len(keys)} API key(s).")
                write_log(f"Imported {len(keys)} API keys manually")
            except Exception as e:
                print_error(f"Gagal menyimpan: {str(e)}")
        else:
            print_warning("Tidak ada key yang dimasukkan.")
    
    elif choice == '2':
        source_file = input("Masukkan path ke file .txt: ").strip()
        source_path = Path(source_file)
        
        if not source_path.is_file():
            print_error("File tidak ditemukan.")
            return
        
        try:
            content = source_path.read_text(encoding="utf-8")
            keys = [line.strip() for line in content.splitlines() if line.strip()]
            
            valid_keys = []
            invalid_count = 0
            for key in keys:
                valid, msg = validate_api_key(key)
                if valid:
                    valid_keys.append(key)
                else:
                    invalid_count += 1
                    print_warning(f"Skipped invalid key: {key[:15]}... ({msg})")
            
            if valid_keys:
                API_KEYS_FILE.write_text("\n".join(valid_keys), encoding="utf-8")
                print_success(f"Berhasil mengimpor {len(valid_keys)} API key(s).")
                if invalid_count > 0:
                    print_warning(f"Skipped {invalid_count} invalid key(s).")
                write_log(f"Imported {len(valid_keys)} API keys from file")
            else:
                print_error("Tidak ada key valid yang ditemukan.")
        except Exception as e:
            print_error(f"Gagal membaca file: {str(e)}")
    else:
        print_warning("Pilihan tidak valid.")

def show_api_keys_status():
    print_header("3. SHOW API KEYS STATUS")
    try:
        keys = read_file_lines(API_KEYS_FILE)
        print_info(f"Total API Keys ditemukan: {len(keys)}")
        if keys:
            print_info("\nPreview (3 kunci pertama):")
            for i, key in enumerate(keys[:3], 1):
                print(f"  {i}. 🔑 {key[:10]}...{key[-5:]}")
    except Exception as e:
        print_error(f"Gagal membaca API keys: {str(e)}")

# =============================================
# FEATURE 4 & 5: MANAJEMEN GITHUB TOKEN (WITH VALIDATION)
# =============================================
def import_github_tokens():
    print_header("4. IMPORT GITHUB TOKENS")
    source_file = input("Masukkan path ke file .txt berisi token: ").strip()
    source_path = Path(source_file)
    
    if not source_path.is_file():
        print_error("File tidak ditemukan.")
        return
    
    try:
        tokens = [line.strip() for line in read_file_lines(source_path) if line.strip().startswith("ghp_")]
        
        valid_tokens = []
        invalid_count = 0
        for token in tokens:
            valid, msg = validate_github_token(token)
            if valid:
                valid_tokens.append(token)
            else:
                invalid_count += 1
                print_warning(f"Skipped invalid token: {token[:12]}... ({msg})")
        
        if valid_tokens:
            TOKENS_FILE.write_text("\n".join(valid_tokens), encoding="utf-8")
            print_success(f"Berhasil mengimpor {len(valid_tokens)} token.")
            if invalid_count > 0:
                print_warning(f"Skipped {invalid_count} invalid token(s).")
            write_log(f"Imported {len(valid_tokens)} tokens from file")
        else:
            print_error("Tidak ada token valid (ghp_) ditemukan.")
    except Exception as e:
        print_error(f"Gagal membaca file: {str(e)}")

def validate_github_tokens():
    print_header("5. VALIDATE GITHUB TOKENS")
    try:
        tokens = read_file_lines(TOKENS_FILE)
        if not tokens: 
            return print_error("File tokens.txt kosong.")
        
        token_cache = load_json_file(TOKEN_CACHE_FILE)
        valid_count = 0
        invalid_tokens = []
        
        for i, token in enumerate(tokens):
            print(f"[{i+1}/{len(tokens)}] Validating...", end="", flush=True)
            
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
                print_error(f" ❌ Invalid ({result.get('error_type', 'unknown')})")
                invalid_tokens.append(token)
            
            time.sleep(0.5)
        
        save_json_file(TOKEN_CACHE_FILE, token_cache)
        
        print_success(f"\nValidasi selesai. Token valid: {valid_count}/{len(tokens)}")
        
        if invalid_tokens:
            print_warning(f"\n{len(invalid_tokens)} token invalid. Hapus dari tokens.txt? (y/n): ", end="")
            if input().lower() == 'y':
                valid_tokens = [t for t in tokens if t not in invalid_tokens]
                TOKENS_FILE.write_text("\n".join(valid_tokens), encoding="utf-8")
                print_success("Token invalid telah dihapus.")
        
        write_log(f"Token validation: {valid_count}/{len(tokens)} valid")
    except Exception as e:
        print_error(f"Error during validation: {str(e)}")
        write_log(f"Token validation error: {str(e)}")

# =============================================
# FEATURE 6, 7: LOGIKA KOLABORASI (ENHANCED)
# =============================================
def invoke_auto_invite():
    print_header("6. AUTO INVITE COLLABORATORS")
    try:
        config = load_json_file(CONFIG_FILE)
        if not config: 
            return print_error("Konfigurasi belum diset. Jalankan Menu 1.")
        
        token_cache = load_json_file(TOKEN_CACHE_FILE)
        if not token_cache:
            return print_error("Token cache kosong. Jalankan Menu 5 untuk validasi token.")
        
        invited_users = read_file_lines(INVITED_USERS_FILE)
        users_to_invite = [
            u for u in token_cache.values() 
            if u not in invited_users and u != config['main_account_username']
        ]
        
        if not users_to_invite: 
            return print_success("Semua akun sudah diundang.")
        
        print_info(f"Akan mengundang {len(users_to_invite)} user baru...")
        
        success_count = 0
        repo_path = f"{config['main_account_username']}/{config['main_repo_name']}"
        
        for i, username in enumerate(users_to_invite):
            print(f"[{i+1}/{len(users_to_invite)}] Mengundang @{username}...", end="", flush=True)
            
            res = run_gh_api(
                f"api --silent -X PUT repos/{repo_path}/collaborators/{username} -f permission=push", 
                config['main_token']
            )
            
            if res["success"]:
                print_success(" ✅ Invited")
                append_to_file(INVITED_USERS_FILE, username)
                success_count += 1
            else:
                print_error(f" ❌ Failed: {res.get('error_type', 'unknown')}")
            
            time.sleep(1.5)
        
        print_success(f"\nProses selesai. Undangan berhasil: {success_count}/{len(users_to_invite)}")
        write_log(f"Invited {success_count}/{len(users_to_invite)} collaborators")

    except Exception as e:
        print_error(f"Error: {str(e)}")
        write_log(f"Invite error: {str(e)}")

def invoke_auto_accept():
    print_header("7. AUTO ACCEPT INVITATIONS")
    try:
        config = load_json_file(CONFIG_FILE)
        token_cache = load_json_file(TOKEN_CACHE_FILE)
        
        if not config or not token_cache: 
            return print_error("Konfigurasi/cache tidak ditemukan. Jalankan Menu 1 dan 5.")
        
        target_repo = f"{config['main_account_username']}/{config['main_repo_name']}".lower()
        accepted_count = 0
        
        print_info(f"Checking invitations untuk {len(token_cache)} akun...")
        
        for i, (token, username) in enumerate(token_cache.items()):
            print(f"[{i+1}/{len(token_cache)}] Akun @{username}...", end="", flush=True)
            
            res = run_gh_api("api user/repository_invitations", token)
            
            if not res["success"]:
                print_error(f" ❌ Gagal fetch invitations")
                time.sleep(1)
                continue
            
            try:
                invitations = json.loads(res["output"])
                inv_id = next((inv['id'] for inv in invitations if inv['repository']['full_name'].lower() == target_repo), None)
                
                if inv_id:
                    accept_res = run_gh_api(f"api --method PATCH /user/repository_invitations/{inv_id} --silent", token)
                    if accept_res["success"]:
                        print_success(" ✅ Accepted")
                        append_to_file(ACCEPTED_USERS_FILE, username)
                        accepted_count += 1
                    else:
                        print_error(f" ❌ Gagal accept: {accept_res.get('error_type', 'unknown')}")
                else:
                    print_info(" ℹ️  No invitation")
                    
            except json.JSONDecodeError as e:
                print_error(" ❌ Gagal parse JSON")
                write_log(f"JSON Parse Error for @{username}: {str(e)}")
            
            time.sleep(1.5)
        
        print_success(f"\nProses selesai. Undangan baru diterima: {accepted_count}")
        write_log(f"Accepted {accepted_count} invitations")
    except Exception as e:
        print_error(f"Error: {str(e)}")
        write_log(f"Accept error: {str(e)}")


# =============================================
# FEATURE 8: AUTO SET SECRETS (REPAIRED)
# =============================================
def invoke_auto_set_secrets():
    print_header("8. AUTO SET SECRETS")
    print_warning("Fitur ini akan membuat/memperbarui 'Actions Secret' di repositori utama.")

    try:
        config = load_json_file(CONFIG_FILE)
        if not config:
            return print_error("Konfigurasi belum diset. Jalankan Menu 1.")

        if not API_KEYS_FILE.exists() or API_KEYS_FILE.stat().st_size == 0:
            return print_error("File API keys kosong. Jalankan Menu 2.")

        api_keys_str = API_KEYS_FILE.read_text(encoding="utf-8").strip()
        repo_path = f"{config['main_account_username']}/{config['main_repo_name']}"
        main_token = config['main_token']

        print_info(f"Menyiapkan secret untuk repositori: {repo_path}")

        # Menggunakan perintah `gh secret set` yang lebih sederhana dan tepat sasaran
        # Perintah ini akan membaca isi file api_keys.txt dan mengirimkannya sebagai secret
        command = f'gh secret set DATAGRAM_API_KEYS --body "{api_keys_str}" -R {repo_path}'
        
        # Jalankan perintah menggunakan token utama
        print_info("Mengirim secret ke GitHub Actions...")
        result = run_command(command, env={"GH_TOKEN": main_token})

        if result.returncode == 0:
            print_success("✅ Secret 'DATAGRAM_API_KEYS' berhasil di-set di Actions!")
            print_info("Sekarang workflow Anda dapat berjalan dengan benar.")
            # Menandai bahwa secret sudah di-set untuk akun utama
            append_to_file(SECRETS_SET_FILE, config['main_account_username'])
            write_log(f"Actions Secret DATAGRAM_API_KEYS set for repo {repo_path}")
        else:
            print_error("❌ Gagal men-set Actions Secret.")
            print_error(f"Detail: {result.stderr}")
            write_log(f"Failed to set Actions Secret: {result.stderr}")

    except Exception as e:
        print_error(f"Terjadi error tak terduga: {str(e)}")
        write_log(f"Set secrets (repaired) error: {str(e)}")


# =============================================
# FEATURE 9, 10, 11: DEPLOYMENT & MONITORING
# =============================================
def deploy_to_github():
    print_header("9. DEPLOY TO GITHUB")
    try:
        config = load_json_file(CONFIG_FILE)
        if not config: 
            return print_error("Konfigurasi belum diset. Jalankan Menu 1.")
        
        repo_path = f"{config['main_account_username']}/{config['main_repo_name']}"
        
        print_info(f"Mengecek repo {repo_path}...")
        
        if not run_gh_api(f"api repos/{repo_path}", config['main_token'], 1)["success"]:
            print_warning("Repo tidak ditemukan.")
            create = input("Buat repository baru? (y/n): ").lower()
            if create == 'y':
                print_info("Membuat repository...")
                create_res = run_gh_api(f"repo create {repo_path} --private --confirm", config['main_token'])
                if not create_res["success"]:
                    return print_error(f"Gagal membuat repo: {create_res['output']}")
                print_success("Repository berhasil dibuat!")
            else:
                return print_warning("Deployment dibatalkan.")
        
        print_info("Melakukan commit dan push...")
        run_command('git add .')
        run_command('git commit -m "🚀 Deploy Orchestrator [automated]"')
        
        print_warning("Melakukan push ke GitHub...")
        push_result = run_command('git push -u origin main --force', env={"GH_TOKEN": config['main_token']})
        
        if push_result.returncode == 0:
            print_success(f"\n✅ Deployment berhasil!")
            print_info(f"Lihat di: https://github.com/{repo_path}/actions")
            write_log("Deployment successful")
        else:
            print_error(f"\n❌ Gagal melakukan push:\n{push_result.stderr}")
            write_log(f"Deployment failed: {push_result.stderr}")
    except Exception as e:
        print_error(f"Error during deployment: {str(e)}")
        write_log(f"Deployment error: {str(e)}")

def invoke_workflow_trigger():
    print_header("10. TRIGGER WORKFLOW")
    try:
        config = load_json_file(CONFIG_FILE)
        if not config: 
            return print_error("Konfigurasi belum diset. Jalankan Menu 1.")
        
        repo_path = f"{config['main_account_username']}/{config['main_repo_name']}"
        
        print_info("Memicu workflow...")
        res = run_gh_api(f"workflow run datagram-runner.yml -R {repo_path}", config['main_token'])
        
        if res["success"]:
            print_success("✅ Workflow berhasil dipicu!")
            print_info(f"Monitor di: https://github.com/{repo_path}/actions")
            write_log("Workflow triggered successfully")
        else:
            print_error(f"Gagal memicu workflow: {res['output']}")
            write_log(f"Workflow trigger failed: {res['output']}")
    except Exception as e:
        print_error(f"Error: {str(e)}")
        write_log(f"Workflow trigger error: {str(e)}")

def show_workflow_status():
    print_header("11. SHOW WORKFLOW STATUS")
    try:
        config = load_json_file(CONFIG_FILE)
        if not config: 
            return print_error("Konfigurasi belum diset. Jalankan Menu 1.")
        
        repo_path = f"{config['main_account_username']}/{config['main_repo_name']}"
        
        print_info("Fetching workflow status...")
        res = run_gh_api(f"run list -R {repo_path} --limit 5", config['main_token'])
        
        if res["success"]:
            print("\n" + res["output"])
            write_log("Workflow status retrieved")
        else:
            print_error(f"Gagal mendapatkan status: {res['output']}")
    except Exception as e:
        print_error(f"Error: {str(e)}")
        write_log(f"Workflow status error: {str(e)}")

# =============================================
# FEATURE 12 & 13: UTILITIES
# =============================================
def view_logs():
    print_header("12. VIEW LOGS")
    try:
        if LOG_FILE.exists() and LOG_FILE.stat().st_size > 0:
            content = LOG_FILE.read_text(encoding="utf-8")
            lines = content.splitlines()
            print_info(f"Menampilkan 50 baris terakhir dari {len(lines)} total baris.")
            print("\n" + "\n".join(lines[-50:]))
        else:
            print_warning("File log belum ada atau kosong.")
    except Exception as e:
        print_error(f"Gagal membaca log: {str(e)}")

def clean_cache():
    print_header("13. CLEAN CACHE")
    
    print_warning("\n⚠️  Ini akan menghapus semua file tracking otomatis!")
    
    confirm = input("Ketik 'DELETE' untuk konfirmasi penghapusan: ")
    
    if confirm == 'DELETE':
        cache_files = [TOKEN_CACHE_FILE, INVITED_USERS_FILE, ACCEPTED_USERS_FILE, SECRETS_SET_FILE]
        deleted_count = 0
        for f in cache_files:
            if f.exists():
                f.unlink()
                deleted_count += 1
        print_success(f"\n✅ Cache dibersihkan ({deleted_count} file dihapus).")
        write_log("Cache cleaned")
    else:
        print_warning("Pembersihan dibatalkan.")
