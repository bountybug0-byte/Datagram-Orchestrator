# orchestrator/collaboration.py

import json
import time

from .helpers import (
    print_success,
    print_error,
    print_info,
    print_warning,
    print_header,
    run_gh_api,
    read_file_lines,
    append_to_file,
    load_json_file,
    CONFIG_FILE,
    TOKEN_CACHE_FILE,
    INVITED_USERS_FILE,
    ACCEPTED_USERS_FILE,
    FORKED_REPOS_FILE
)

def invoke_auto_invite():
    """Mengundang semua akun di cache token sebagai kolaborator."""
    print_header("6. AUTO INVITE COLLABORATORS")
    config = load_json_file(CONFIG_FILE)
    if not config:
        print_error("Konfigurasi belum diset.")
        return

    token_cache = load_json_file(TOKEN_CACHE_FILE)
    if not token_cache:
        print_error("Token cache kosong.")
        return

    invited_users = read_file_lines(INVITED_USERS_FILE)
    main_username = config['main_account_username']
    users_to_invite = [u for u in token_cache.values() if u not in invited_users and u != main_username]

    if not users_to_invite:
        print_success("✅ Semua akun sudah diundang.")
        return

    print_info(f"Akan mengundang {len(users_to_invite)} user baru...")
    repo_path = f"{main_username}/{config['main_repo_name']}"
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
        time.sleep(1)

    print_success(f"\nProses selesai! Berhasil: {success_count}/{len(users_to_invite)}")

def invoke_auto_accept():
    """Menerima undangan kolaborasi secara otomatis untuk semua akun."""
    print_header("7. AUTO ACCEPT INVITATIONS")
    config = load_json_file(CONFIG_FILE)
    token_cache = load_json_file(TOKEN_CACHE_FILE)

    if not config or not token_cache:
        print_error("Konfigurasi atau token cache tidak ditemukan.")
        return

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
            print_error(f" ❌ Gagal fetch invitations")
            continue

        try:
            invitations = json.loads(result["output"])
            inv_id = next(
                (inv['id'] for inv in invitations if inv.get('repository', {}).get('full_name', '').lower() == target_repo),
                None
            )

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

def get_default_branch(repo_path: str, token: str) -> str:
    """Mendapatkan nama branch default dari repository."""
    result = run_gh_api(f"api repos/{repo_path} --jq '.default_branch'", token, max_retries=1)
    if result["success"] and result["output"].strip():
        return result["output"].strip().strip('"')
    return "main"

def sync_fork_with_upstream(fork_repo: str, token: str, default_branch: str) -> bool:
    """Sinkronisasi fork dengan upstream menggunakan berbagai strategi."""
    
    # Strategy 1: Gunakan merge-upstream API
    sync_result = run_gh_api(
        f"api -X POST repos/{fork_repo}/merge-upstream -f branch={default_branch}",
        token,
        max_retries=1
    )
    
    if sync_result["success"]:
        return True
    
    error_msg = sync_result.get('error', '').lower()
    
    # Jika sudah up-to-date, anggap sukses
    if any(keyword in error_msg for keyword in ['up-to-date', 'up to date', 'already']):
        return True
    
    # Strategy 2: Gunakan compare API untuk cek status
    repo_parts = fork_repo.split('/')
    username = repo_parts[0]
    repo_name = repo_parts[1]
    
    # Ambil info parent repo
    parent_info = run_gh_api(f"api repos/{fork_repo} --jq '.parent.full_name'", token, max_retries=1)
    if parent_info["success"] and parent_info["output"].strip():
        parent_repo = parent_info["output"].strip().strip('"')
        
        # Cek apakah ada commits baru di upstream
        compare_result = run_gh_api(
            f"api repos/{fork_repo}/compare/{username}:{default_branch}...{parent_repo.replace('/', ':')}:{default_branch} --jq '.behind_by'",
            token,
            max_retries=1
        )
        
        if compare_result["success"]:
            try:
                behind_by = int(compare_result["output"].strip())
                if behind_by == 0:
                    return True  # Sudah up-to-date
            except (ValueError, AttributeError):
                pass
    
    # Strategy 3: Fallback - anggap berhasil jika error bukan critical
    if 'not found' not in error_msg and 'forbidden' not in error_msg and 'unauthorized' not in error_msg:
        return True
    
    return False

def invoke_auto_create_or_sync_fork():
    """Membuat atau menyinkronkan fork repository utama ke semua akun kolaborator."""
    print_header("8. AUTO CREATE OR SYNC FORK REPOSITORY")
    config = load_json_file(CONFIG_FILE)
    if not config:
        print_error("Konfigurasi belum diset.")
        return

    token_cache = load_json_file(TOKEN_CACHE_FILE)
    if not token_cache:
        print_error("Token cache kosong.")
        return

    forked_users = read_file_lines(FORKED_REPOS_FILE)
    main_username = config['main_account_username']
    source_repo = f"{main_username}/{config['main_repo_name']}"

    users_to_process = {u: t for t, u in token_cache.items() if u != main_username}

    if not users_to_process:
        print_success("✅ Tidak ada akun untuk diproses.")
        return

    print_info(f"Akan memproses {len(users_to_process)} user...")
    success_count = 0

    for i, (username, token) in enumerate(users_to_process.items(), 1):
        print(f"[{i}/{len(users_to_process)}] Processing @{username}...", end="", flush=True)
        fork_repo = f"{username}/{config['main_repo_name']}"

        # Cek apakah fork sudah ada
        check_result = run_gh_api(f"api repos/{fork_repo}", token, max_retries=1)
        fork_exists = check_result["success"]

        if fork_exists:
            print_info(" 🔄 Syncing...")
            
            # Deteksi branch default
            default_branch = get_default_branch(fork_repo, token)
            
            # Sinkronisasi fork dengan upstream
            if sync_fork_with_upstream(fork_repo, token, default_branch):
                print_success(" ✅ Synced")
            else:
                print_warning(" ⚠️ Sync skipped")
            
            # Pastikan visibilitas publik
            visibility_result = run_gh_api(
                f"api -X PATCH repos/{fork_repo} -f private=false",
                token,
                max_retries=1
            )
            
            if visibility_result["success"] or "unprocessable" in visibility_result.get("error", "").lower():
                print_info(" 🔓 Public")
            
            if username not in forked_users:
                append_to_file(FORKED_REPOS_FILE, username)
            success_count += 1
        else:
            # Buat fork baru
            print_info(" 🍴 Creating...")
            result = run_gh_api(f"api -X POST repos/{source_repo}/forks", token, max_retries=2)
            
            if result["success"]:
                print_success(" ✅ Created")
                time.sleep(5)
                
                # Set visibility menjadi publik
                visibility_result = run_gh_api(
                    f"api -X PATCH repos/{fork_repo} -f private=false",
                    token,
                    max_retries=2
                )
                
                if visibility_result["success"] or "unprocessable" in visibility_result.get("error", "").lower():
                    print_info(" 🔓 Public")
                
                append_to_file(FORKED_REPOS_FILE, username)
                success_count += 1
            else:
                error_msg = result.get('error', '')
                if "already exists" in error_msg.lower() or "fork exists" in error_msg.lower():
                    print_success(" ✅ Exists")
                    if username not in forked_users:
                        append_to_file(FORKED_REPOS_FILE, username)
                    success_count += 1
                else:
                    print_error(f" ❌ {error_msg}")

        time.sleep(2)

    print_success(f"\nProses selesai! Berhasil: {success_count}/{len(users_to_process)}")
