# orchestrator/collaboration.py

import json
import time
import re
from typing import List, Set, Tuple

from .helpers import (
    Style,
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
    FORKED_REPOS_FILE,
    write_log
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


def get_user_repos_matching_pattern(token: str, repo_name: str) -> List[str]:
    """Mendapatkan semua repo yang match pattern repo_name atau repo_name-N."""
    result = run_gh_api("api user/repos --paginate --jq '.[].name'", token, max_retries=2, timeout=60)
    
    if not result["success"] or not result["output"].strip():
        return []
    
    matching_repos_set: Set[str] = set()
    pattern = re.compile(rf'^{re.escape(repo_name)}(-\d+)?$', re.IGNORECASE)
    
    for line in result["output"].strip().split('\n'):
        if line.strip():
            repo = line.strip().strip('"').strip("'")
            if pattern.match(repo):
                matching_repos_set.add(repo)
    
    return sorted(matching_repos_set)


def check_if_correct_fork(repo_path: str, token: str, expected_parent: str) -> bool:
    """Cek apakah repo adalah fork valid dari expected parent."""
    result = run_gh_api(f"api repos/{repo_path} --jq '.parent.full_name'", token, max_retries=1)
    if not result["success"]:
        return False
    
    parent = result["output"].strip().strip('"')
    return parent == expected_parent


def get_default_branch(repo_path: str, token: str) -> str:
    """Mendapatkan nama branch default."""
    result = run_gh_api(f"api repos/{repo_path} --jq '.default_branch'", token, max_retries=1)
    if result["success"] and result["output"].strip():
        return result["output"].strip().strip('"')
    return "main"


def delete_repository(repo_path: str, token: str) -> bool:
    """Menghapus repository."""
    result = run_gh_api(f"api -X DELETE repos/{repo_path}", token, max_retries=2, timeout=30)
    if not result["success"]:
        write_log(f"Failed to delete {repo_path}: {result.get('error')}")
    return result["success"]


def sync_fork_with_upstream(fork_repo: str, token: str) -> bool:
    """Sinkronisasi fork dengan upstream."""
    default_branch = get_default_branch(fork_repo, token)
    sync_result = run_gh_api(f"api -X POST repos/{fork_repo}/merge-upstream -f branch={default_branch}", token, max_retries=2)
    
    if sync_result["success"]:
        return True
    
    error_msg = sync_result.get('error', '').lower()
    if any(keyword in error_msg for keyword in ['up-to-date', 'up to date', 'already']):
        return True
    
    return False


def set_repo_public(repo_path: str, token: str) -> bool:
    """Set repository visibility menjadi public."""
    result = run_gh_api(f"api -X PATCH repos/{repo_path} -f private=false", token, max_retries=1)
    return result["success"] or "unprocessable" in result.get("error", "").lower()


def cleanup_invalid_repos(username: str, token: str, matching_repos: List[str], source_repo: str) -> Tuple[int, List[str]]:
    """Delete repo yang bukan fork valid."""
    if not matching_repos:
        return 0, []
    
    deleted_count = 0
    kept_repos: List[str] = []
    
    for repo in matching_repos:
        repo_path = f"{username}/{repo}"
        
        if check_if_correct_fork(repo_path, token, source_repo):
            print_success(f"    ✅ Keeping valid fork: {repo}")
            kept_repos.append(repo)
            continue
        
        print_warning(f"    🗑️  Deleting: {repo}")
        if delete_repository(repo_path, token):
            print_success(f"    ✅ Deleted: {repo}")
            deleted_count += 1
            time.sleep(2)
        else:
            print_error(f"    ❌ Failed to delete: {repo}")
    
    return deleted_count, kept_repos


def prompt_user_cleanup(username: str, matching_repos: List[str]) -> bool:
    """Prompt user untuk konfirmasi cleanup. Return True jika y, False jika n."""
    print_warning(f"\n    ⚠️  @{username} memiliki {len(matching_repos)} repo:")
    for repo in matching_repos:
        print_warning(f"       • {repo}")
    
    print_info("\n    Delete semua dan buat fork baru?")
    
    while True:
        choice = input(f"    {Style.BOLD}[y/n]:{Style.ENDC} ").strip().lower()
        if choice == 'y':
            return True
        elif choice == 'n':
            return False
        else:
            print_warning("    Invalid input. Masukkan 'y' atau 'n'")


def create_new_fork(username: str, token: str, source_repo: str, fork_repo: str) -> bool:
    """Create fork baru."""
    result = run_gh_api(f"api -X POST repos/{source_repo}/forks", token, max_retries=2)
    
    if result["success"]:
        print_success("    ✅ Fork created")
        time.sleep(5)
        
        if set_repo_public(fork_repo, token):
            print_info("    🔓 Set public")
        
        append_to_file(FORKED_REPOS_FILE, username)
        return True
    else:
        print_error(f"    ❌ Failed: {result.get('error')}")
        write_log(f"Fork failed for @{username}: {result.get('error')}")
        return False


def invoke_auto_create_or_sync_fork():
    """Membuat atau sync fork untuk semua akun kolaborator."""
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
    repo_name = config['main_repo_name']

    users_to_process = {u: t for t, u in token_cache.items() if u != main_username}

    if not users_to_process:
        print_success("✅ Tidak ada akun untuk diproses.")
        return

    print_info(f"Source: {source_repo}")
    print_info(f"Processing {len(users_to_process)} users...\n")
    
    success_count = 0
    sync_count = 0
    create_count = 0
    skip_count = 0

    for i, (username, token) in enumerate(users_to_process.items(), 1):
        print(f"\n[{i}/{len(users_to_process)}] @{username}")
        print('-'*50)
        
        fork_repo = f"{username}/{repo_name}"
        is_valid_fork = check_if_correct_fork(fork_repo, token, source_repo)

        if is_valid_fork:
            # Valid fork - sync
            print_success("✅ Valid fork detected")
            print_info("🔄 Syncing...")
            
            if sync_fork_with_upstream(fork_repo, token):
                print_success("✅ Synced")
                sync_count += 1
            else:
                print_warning("⚠️  Sync failed")
            
            set_repo_public(fork_repo, token)
            
            if username not in forked_users:
                append_to_file(FORKED_REPOS_FILE, username)
            
            success_count += 1
            
        else:
            # No valid fork
            print_warning("⚠️  No valid fork")
            matching_repos = get_user_repos_matching_pattern(token, repo_name)
            
            # ALWAYS prompt user untuk delete/create decision
            if matching_repos:
                # Ada repo matching - show list
                proceed = prompt_user_cleanup(username, matching_repos)
            else:
                # Ga ada repo - confirm create
                print_info("\n    Tidak ada repo ditemukan.")
                print_info("    Buat fork baru?")
                while True:
                    choice = input(f"    {Style.BOLD}[y/n]:{Style.ENDC} ").strip().lower()
                    if choice == 'y':
                        proceed = True
                        break
                    elif choice == 'n':
                        proceed = False
                        break
                    else:
                        print_warning("    Invalid input. Masukkan 'y' atau 'n'")
            
            if proceed:
                # User pilih y
                if matching_repos:
                    # Cleanup dulu kalau ada
                    deleted, _ = cleanup_invalid_repos(username, token, matching_repos, source_repo)
                    if deleted > 0:
                        print_success(f"\n    ✅ Cleaned {deleted} repo(s)")
                        time.sleep(3)
                
                # Create fork baru
                print_info("\n    🍴 Creating fork...")
                if create_new_fork(username, token, source_repo, fork_repo):
                    create_count += 1
                    success_count += 1
            else:
                # User pilih n
                print_info("\n    ⏭️  Skipped")
                if matching_repos:
                    # Coba sync repo pertama
                    first_repo = f"{username}/{matching_repos[0]}"
                    if sync_fork_with_upstream(first_repo, token):
                        print_success(f"    ✅ Synced: {matching_repos[0]}")
                        sync_count += 1
                        success_count += 1
                    else:
                        print_warning("    ⚠️  Sync failed")
                        skip_count += 1
                else:
                    # Ga ada repo, skip count
                    skip_count += 1

        time.sleep(2)

    # Summary
    print(f"\n{'='*50}")
    print_success("✅ COMPLETE")
    print('='*50)
    print_info(f"Total: {len(users_to_process)}")
    print_success(f"Success: {success_count}")
    print_info(f"  Synced: {sync_count} | Created: {create_count}")
    if skip_count > 0:
        print_warning(f"Skipped: {skip_count}")
    print('='*50)
