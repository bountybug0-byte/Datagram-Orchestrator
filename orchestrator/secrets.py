# orchestrator/secrets.py

import json
import base64
import time
import tempfile
from pathlib import Path
from typing import Dict

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
    run_command,
    API_KEYS_FILE,
    CONFIG_FILE,
    TOKEN_CACHE_FILE,
    FORKED_REPOS_FILE,
    SECRETS_SET_FILE
)

def get_repo_public_key(repo_path: str, token: str) -> Dict[str, str]:
    """Mengambil public key dari repositori untuk enkripsi secrets."""
    result = run_gh_api(f"api repos/{repo_path}/actions/secrets/public-key", token, timeout=30)
    if result["success"]:
        try:
            data = json.loads(result["output"])
            return {"key": data.get("key"), "key_id": data.get("key_id")}
        except json.JSONDecodeError:
            return {}
    return {}

def encrypt_secret(public_key: str, secret_value: str) -> str:
    """Mengenkripsi nilai secret menggunakan PyNaCl."""
    try:
        from nacl import encoding, public
        public_key_obj = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
        sealed_box = public.SealedBox(public_key_obj)
        encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
        return base64.b64encode(encrypted).decode("utf-8")
    except ImportError:
        raise ImportError("PyNaCl library is required. Install with: pip install PyNaCl")

def set_secret_via_api(repo_path: str, token: str, name: str, value: str) -> bool:
    """Mengatur secret di repositori GitHub menggunakan API dengan enkripsi."""
    try:
        key_info = get_repo_public_key(repo_path, token)
        if not key_info or not key_info.get("key") or not key_info.get("key_id"):
            print_error("Failed to get repository public key")
            return False

        encrypted_value = encrypt_secret(key_info["key"], value)

        payload = {
            "encrypted_value": encrypted_value,
            "key_id": key_info["key_id"]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(payload, f)
            temp_file_path = f.name

        cmd = f'gh api -X PUT repos/{repo_path}/actions/secrets/{name} --input "{temp_file_path}"'
        proc = run_command(cmd, env={"GH_TOKEN": token}, timeout=30)
        
        Path(temp_file_path).unlink()

        if proc.returncode in [0, 201, 204]:
            time.sleep(3)
            verify_result = run_gh_api(f"api repos/{repo_path}/actions/secrets/{name}", token, max_retries=1)
            return verify_result["success"]
        
        print_warning(f"Set secret failed with code {proc.returncode}: {proc.stderr[:100]}")
        return False
    except Exception as e:
        print_error(f"Error setting secret: {str(e)}")
        return False

def invoke_auto_set_secrets():
    """Mengatur secret DATAGRAM_API_KEYS di semua repositori target."""
    print_header("9. AUTO SET SECRETS")
    config = load_json_file(CONFIG_FILE)
    if not config:
        print_error("Konfigurasi belum diset.")
        return

    api_keys = read_file_lines(API_KEYS_FILE)
    if not api_keys:
        print_error("File API keys kosong.")
        return

    api_keys_json = json.dumps(api_keys)

    print("Pilih target:\n 1. Main repo saja\n 2. Main repo + semua forked repos")
    choice = input("\nPilihan (1/2): ").strip()

    targets = [{
        'repo': f"{config['main_account_username']}/{config['main_repo_name']}",
        'token': config['main_token']
    }]

    if choice == '2':
        token_cache = load_json_file(TOKEN_CACHE_FILE)
        forked_users = read_file_lines(FORKED_REPOS_FILE)
        targets.extend([
            {'repo': f"{u}/{config['main_repo_name']}", 'token': t}
            for t, u in token_cache.items() if u in forked_users
        ])

    if input(f"\n🎯 Target: {len(targets)} repos. Lanjutkan? (y/n): ").lower() != 'y':
        print_warning("Operasi dibatalkan.")
        return

    secrets_set_log = read_file_lines(SECRETS_SET_FILE)
    success_count = 0
    failed_repos = []

    for i, target in enumerate(targets, 1):
        repo_path = target['repo']
        token = target['token']

        print(f"\n[{i}/{len(targets)}] Processing: {repo_path}")

        if repo_path in secrets_set_log:
            print_info(" ℹ️ Already set (skipped)")
            continue
        
        print_info(f" 🔑 Setting secret DATAGRAM_API_KEYS...")
        if set_secret_via_api(repo_path, token, "DATAGRAM_API_KEYS", api_keys_json):
            print_success(" ✅ Secret set and verified")
            append_to_file(SECRETS_SET_FILE, repo_path)
            success_count += 1
        else:
            print_error(" ❌ Failed to set secret")
            failed_repos.append(repo_path)

        time.sleep(2)

    print_success(f"\n{'='*47}")
    print_success(f"✅ Selesai! Berhasil: {success_count}/{len(targets)}")

    if failed_repos:
        print_warning(f"\n⚠️ Failed repos ({len(failed_repos)}):")
        for repo in failed_repos:
            print_warning(f"  - {repo}")

    print_success(f"{'='*47}")