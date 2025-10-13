# File: orchestrator/core.py
import json
import getpass
import time
import os
from pathlib import Path

# Impor helper dan path dari file helpers.py
from .helpers import (
    print_success, print_error, print_info, print_warning, print_header,
    write_log, run_gh_api, read_file_lines, append_to_file,
    load_json_file, save_json_file,
    API_KEYS_FILE, TOKENS_FILE, CONFIG_FILE, TOKEN_CACHE_FILE,
    INVITED_USERS_FILE, ACCEPTED_USERS_FILE, SECRETS_SET_FILE, LOG_FILE
)

# =============================================
# FEATURE 1: SETUP KONFIGURASI
# =============================================
def initialize_configuration():
    print_header("1. INITIALIZE CONFIGURATION")
    config = {}
    config['main_account_username'] = input("Username GitHub utama: ")
    config['main_repo_name'] = input("Nama repository (e.g., datagram-runner): ")
    config['main_token'] = getpass.getpass("GitHub Personal Access Token (input tersembunyi): ")
    save_json_file(CONFIG_FILE, config)
    print_success(f"Konfigurasi berhasil disimpan ke: {CONFIG_FILE}")
    write_log("Configuration initialized")

# =============================================
# FEATURE 2 & 3: MANAJEMEN API KEYS
# =============================================
def import_api_keys():
    print_header("2. IMPORT API KEYS")
    # (Logika tidak berubah dari implementasi sebelumnya)
    print("Pilih metode import:\n  1. Input manual\n  2. Import dari file .txt")
    choice = input("\nPilihan (1/2): ")
    if choice == '1':
        keys = []
        while True:
            key = input(f"API Key #{len(keys) + 1} (kosongkan untuk selesai): ")
            if not key: break
            keys.append(key)
        if keys:
            API_KEYS_FILE.write_text("\n".join(keys), encoding="utf-8")
            print_success(f"Berhasil menyimpan {len(keys)} API key(s).")
    elif choice == '2':
        source_file = input("Masukkan path ke file .txt: ")
        if Path(source_file).is_file():
            content = Path(source_file).read_text(encoding="utf-8")
            API_KEYS_FILE.write_text(content, encoding="utf-8")
            count = len(read_file_lines(API_KEYS_FILE))
            print_success(f"Berhasil mengimpor {count} API key(s).")
        else:
            print_error("File tidak ditemukan.")

def show_api_keys_status():
    print_header("3. SHOW API KEYS STATUS")
    # (Logika tidak berubah)
    keys = read_file_lines(API_KEYS_FILE)
    print_info(f"Total API Keys ditemukan: {len(keys)}")
    if keys:
        print_info("\nPreview (3 kunci pertama):")
        for key in keys[:3]: print(f"  🔑 {key[:10]}...{key[-5:]}")

# =============================================
# FEATURE 4 & 5: MANAJEMEN GITHUB TOKEN
# =============================================
def import_github_tokens():
    print_header("4. IMPORT GITHUB TOKENS")
    # (Logika tidak berubah)
    source_file = input("Masukkan path ke file .txt berisi token: ")
    if Path(source_file).is_file():
        tokens = [line for line in read_file_lines(Path(source_file)) if line.startswith("ghp_")]
        if tokens:
            TOKENS_FILE.write_text("\n".join(tokens), encoding="utf-8")
            print_success(f"Berhasil mengimpor {len(tokens)} token.")
        else:
            print_error("Tidak ada token valid (ghp_) ditemukan.")
    else:
        print_error("File tidak ditemukan.")

def validate_github_tokens():
    print_header("5. VALIDATE GITHUB TOKENS")
    # (Logika tidak berubah)
    tokens = read_file_lines(TOKENS_FILE)
    if not tokens: return print_error("File tokens.txt kosong.")
    token_cache = load_json_file(TOKEN_CACHE_FILE)
    valid_count = 0
    for i, token in enumerate(tokens):
        print(f"[{i+1}/{len(tokens)}] Validating...", end="", flush=True)
        if token in token_cache:
            print_success(f" ✅ @{token_cache[token]} (from cache)")
            valid_count += 1
            continue
        result = run_gh_api("api user --jq .login", token, max_retries=1)
        if result["success"]:
            username = result["output"]
            print_success(f" ✅ @{username}")
            token_cache[token] = username
            valid_count += 1
        else:
            print_error(" ❌ Invalid token")
        time.sleep(0.5)
    save_json_file(TOKEN_CACHE_FILE, token_cache)
    print_success(f"\nValidasi selesai. Token valid: {valid_count}/{len(tokens)}")

# =============================================
# FEATURE 6, 7, 8: LOGIKA KOLABORASI
# =============================================
def invoke_auto_invite():
    print_header("6. AUTO INVITE COLLABORATORS")
    # (Logika tidak berubah)
    config = load_json_file(CONFIG_FILE)
    if not config: return print_error("Konfigurasi belum diset.")
    token_cache = load_json_file(TOKEN_CACHE_FILE)
    invited_users = read_file_lines(INVITED_USERS_FILE)
    users_to_invite = [u for u in token_cache.values() if u not in invited_users and u != config['main_account_username']]
    if not users_to_invite: return print_success("Semua akun sudah diundang.")
    print_info(f"Akan mengundang {len(users_to_invite)} user baru...")
    success_count = 0
    repo_path = f"{config['main_account_username']}/{config['main_repo_name']}"
    for i, username in enumerate(users_to_invite):
        print(f"[{i+1}/{len(users_to_invite)}] Mengundang @{username}...", end="", flush=True)
        res = run_gh_api(f"api --silent -X PUT repos/{repo_path}/collaborators/{username} -f permission=push", config['main_token'])
        if res["success"]:
            print_success(" ✅ Invited"); append_to_file(INVITED_USERS_FILE, username); success_count += 1
        else:
            print_error(f" ❌ Failed")
        time.sleep(1)
    print_success(f"\nProses selesai. Undangan berhasil: {success_count}/{len(users_to_invite)}")

def invoke_auto_accept():
    print_header("7. AUTO ACCEPT INVITATIONS")
    # (Logika tidak berubah)
    config = load_json_file(CONFIG_FILE)
    token_cache = load_json_file(TOKEN_CACHE_FILE)
    if not config or not token_cache: return print_error("Konfigurasi/cache tidak ditemukan.")
    target_repo = f"{config['main_account_username']}/{config['main_repo_name']}".lower()
    accepted_count = 0
    for i, token in enumerate(token_cache.keys()):
        print(f"[{i+1}/{len(token_cache)}] Akun @{token_cache[token]}...", end="", flush=True)
        res = run_gh_api("api user/repository_invitations", token)
        if not res["success"]: print_error(" ❌ Gagal fetch"); continue
        try:
            invitations = json.loads(res["output"])
            inv_id = next((inv['id'] for inv in invitations if inv['repository']['full_name'].lower() == target_repo), None)
            if inv_id:
                accept_res = run_gh_api(f"api --method PATCH /user/repository_invitations/{inv_id} --silent", token)
                if accept_res["success"]: print_success(" ✅ Accepted"); accepted_count += 1
                else: print_error(" ❌ Gagal accept")
            else: print_info(" ℹ️  No invitation")
        except json.JSONDecodeError: print_error(" ❌ Gagal parse")
        time.sleep(1)
    print_success(f"\nProses selesai. Undangan baru diterima: {accepted_count}")

def _encrypt_secret_with_python(public_key, secret_value):
    from nacl import encoding, public; import base64
    pk_obj = public.PublicKey(public_key.encode(), encoding.Base64Encoder())
    sealed_box = public.SealedBox(pk_obj)
    encrypted = sealed_box.encrypt(secret_value.encode())
    return base64.b64encode(encrypted).decode()

def invoke_auto_set_secrets():
    print_header("8. AUTO SET SECRETS")
    # (Logika tidak berubah, hanya pemanggilan helper yang disesuaikan)
    config = load_json_file(CONFIG_FILE)
    api_keys_str = API_KEYS_FILE.read_text(encoding="utf-8").strip()
    token_cache = load_json_file(TOKEN_CACHE_FILE)
    if not all([config, api_keys_str, token_cache]): return print_error("Data tidak lengkap.")
    repo_path = f"{config['main_account_username']}/{config['main_repo_name']}"
    repo_id_res = run_gh_api(f"api repos/{repo_path} --jq .id", config['main_token'])
    if not repo_id_res["success"]: return print_error("Gagal mendapatkan ID repo.")
    repo_id = repo_id_res["output"]
    success_count = 0
    for i, (token, username) in enumerate(token_cache.items()):
        print(f"[{i+1}/{len(token_cache)}] @{username}:")
        key_res = run_gh_api("api user/codespaces/secrets/public-key", token)
        if not key_res["success"]: print("   🔑 Gagal dapat public key"); continue
        key_data = json.loads(key_res["output"])
        encrypted_value = _encrypt_secret_with_python(key_data['key'], api_keys_str)
        payload = json.dumps({"encrypted_value": encrypted_value, "key_id": key_data['key_id'], "selected_repository_ids": [str(repo_id)]})
        Path("payload.json").write_text(payload)
        set_res = run_gh_api("api --method PUT /user/codespaces/secrets/DATAGRAM_API_KEYS --input payload.json", token)
        os.remove("payload.json")
        if set_res["success"]:
            print_success("   ✅ Secret set"); append_to_file(SECRETS_SET_FILE, username); success_count += 1
        else:
            print_error(f"   ❌ Gagal set secret")
        time.sleep(1)
    print_success(f"\nProses selesai. Secret di-set untuk {success_count} akun.")

# =============================================
# FEATURE 9, 10, 11: DEPLOYMENT & MONITORING
# =============================================
def deploy_to_github():
    print_header("9. DEPLOY TO GITHUB")
    # (Logika tidak berubah)
    config = load_json_file(CONFIG_FILE)
    if not config: return print_error("Konfigurasi belum diset.")
    repo_path = f"{config['main_account_username']}/{config['main_repo_name']}"
    print_info(f"Mengecek repo {repo_path}...")
    if not run_gh_api(f"api repos/{repo_path}", config['main_token'], 1)["success"]:
        if input("Repo tidak ditemukan. Buat baru? (y/n): ").lower() == 'y':
            run_gh_api(f"repo create {repo_path} --private --confirm", config['main_token'])
        else: return
    print_info("Melakukan commit dan push...")
    os.system('git add . && git commit -m "🚀 Deploy Orchestrator" && git push -u origin main --force')
    print_success(f"\n✅ Deployment berhasil!\nLihat di: https://github.com/{repo_path}/actions")

def invoke_workflow_trigger():
    print_header("10. TRIGGER WORKFLOW")
    # (Logika tidak berubah)
    config = load_json_file(CONFIG_FILE)
    if not config: return print_error("Konfigurasi belum diset.")
    repo_path = f"{config['main_account_username']}/{config['main_repo_name']}"
    res = run_gh_api(f"workflow run datagram-runner.yml -R {repo_path}", config['main_token'])
    if res["success"]: print_success("✅ Workflow berhasil dipicu!")
    else: print_error(f"Gagal memicu workflow: {res['output']}")

def show_workflow_status():
    print_header("11. SHOW WORKFLOW STATUS")
    # (Logika tidak berubah)
    config = load_json_file(CONFIG_FILE)
    if not config: return print_error("Konfigurasi belum diset.")
    repo_path = f"{config['main_account_username']}/{config['main_repo_name']}"
    res = run_gh_api(f"run list -R {repo_path} --limit 5", config['main_token'])
    if res["success"]: print("\n" + res["output"])
    else: print_error("Gagal mendapatkan status.")

# =============================================
# FEATURE 12 & 13: UTILITIES
# =============================================
def view_logs():
    print_header("12. VIEW LOGS")
    if LOG_FILE.exists():
        print(LOG_FILE.read_text(encoding="utf-8"))
    else:
        print_warning("File log belum ada.")

def clean_cache():
    print_header("13. CLEAN CACHE")
    if input("Hapus semua file cache? (y/n): ").lower() == 'y':
        files_to_delete = [TOKEN_CACHE_FILE, INVITED_USERS_FILE, ACCEPTED_USERS_FILE, SECRETS_SET_FILE]
        for f in files_to_delete:
            if f.exists(): f.unlink()
        print_success("Cache dibersihkan.")
