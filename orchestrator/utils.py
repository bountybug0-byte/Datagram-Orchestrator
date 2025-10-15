# orchestrator/utils.py

import json
from .helpers import (
    print_success,
    print_error,
    print_info,
    print_warning,
    print_header,
    run_gh_api,
    LOGS_DIR,
    TOKEN_CACHE_FILE,
    INVITED_USERS_FILE,
    ACCEPTED_USERS_FILE,
    FORKED_REPOS_FILE,
    SECRETS_SET_FILE,
    WORKFLOWS_ENABLED_FILE
)

def check_actions_usage(username: str, token: str) -> int:
    """
    Mengecek penggunaan GitHub Actions (dalam menit) untuk user tertentu.
    
    Args:
        username: GitHub username
        token: GitHub personal access token
        
    Returns:
        Total menit Actions yang telah digunakan
    """
    result = run_gh_api(
        f"api /users/{username}/settings/billing/usage",
        token,
        timeout=30
    )
    
    if not result["success"]:
        print_warning(f"⚠️ Gagal mengambil data billing untuk {username}: {result.get('error')}")
        return 0
    
    try:
        billing_data = json.loads(result["output"])
        total_minutes = 0
        
        # Parse semua item usage
        if "usage" in billing_data:
            for item in billing_data["usage"]:
                if (item.get("product") == "actions" and 
                    item.get("unitType") == "Minutes"):
                    total_minutes += item.get("quantity", 0)
        
        return int(total_minutes)
    
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print_warning(f"⚠️ Error parsing billing data untuk {username}: {str(e)}")
        return 0


def view_logs():
    """Menampilkan 50 baris terakhir dari file log."""
    print_header("VIEW LOGS")
    log_file = LOGS_DIR / "setup.log"

    if not log_file.exists():
        print_warning("Log file tidak ditemukan.")
        return

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            logs = f.readlines()
        if not logs:
            print_info("Log file kosong.")
            return

        print_info(f"Menampilkan {min(len(logs), 50)} baris terakhir:\n")
        for line in logs[-50:]:
            print(line.strip())
    except Exception as e:
        print_error(f"Error membaca log: {str(e)}")


def clean_cache():
    """Menghapus file cache yang dipilih atau semua cache."""
    print_header("CLEAN CACHE")
    print("Pilih cache yang ingin dihapus:")
    print(" 1. Token cache")
    print(" 2. Invited users cache")
    print(" 3. Accepted users cache")
    print(" 4. Forked repos cache")
    print(" 5. Secrets set cache")
    print(" 6. Workflows enabled cache")
    print(" 7. Hapus semua cache")
    print(" 0. Batal")

    choice = input("\nPilihan (0-7): ").strip()

    cache_files = {
        '1': ('Token cache', TOKEN_CACHE_FILE),
        '2': ('Invited users', INVITED_USERS_FILE),
        '3': ('Accepted users', ACCEPTED_USERS_FILE),
        '4': ('Forked repos', FORKED_REPOS_FILE),
        '5': ('Secrets set', SECRETS_SET_FILE),
        '6': ('Workflows enabled', WORKFLOWS_ENABLED_FILE)
    }

    if choice == '0':
        print_warning("Operasi dibatalkan.")
        return
    elif choice == '7':
        if input("⚠️ Hapus SEMUA cache? (y/n): ").lower() != 'y':
            print_warning("Operasi dibatalkan.")
            return
        for name, file_path in cache_files.values():
            if file_path.exists():
                file_path.unlink()
                print_success(f"✅ {name} dihapus")
        print_success("\n✅ Semua cache berhasil dihapus!")
    elif choice in cache_files:
        name, file_path = cache_files[choice]
        if file_path.exists() and input(f"⚠️ Hapus {name}? (y/n): ").lower() == 'y':
            file_path.unlink()
            print_success(f"✅ {name} berhasil dihapus!")
        else:
            print_warning(f"{name} tidak ditemukan atau operasi dibatalkan.")
    else:
        print_warning("Pilihan tidak valid.")
