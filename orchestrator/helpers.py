import os
import sys
import json
import subprocess
import time
import shutil
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
CACHE_DIR = CONFIG_DIR / ".cache"
LOGS_DIR = BASE_DIR / "logs"

API_KEYS_FILE = CONFIG_DIR / "api_keys.txt"
TOKENS_FILE = CONFIG_DIR / "tokens.txt"
CONFIG_FILE = CONFIG_DIR / "config.json"
TOKEN_CACHE_FILE = CACHE_DIR / "token_cache.json"
INVITED_USERS_FILE = CACHE_DIR / "invited_users.txt"
ACCEPTED_USERS_FILE = CACHE_DIR / "accepted_users.txt"
FORKED_REPOS_FILE = CACHE_DIR / "forked_repos.txt"
SECRETS_SET_FILE = CACHE_DIR / "secrets_set.txt"
WORKFLOWS_ENABLED_FILE = CACHE_DIR / "workflows_enabled.txt"

def find_gh_executable():
    """Find gh executable with better Windows support"""
    gh_path = shutil.which("gh")
    if not gh_path:
        # Try common Windows installation paths
        common_paths = [
            r"C:\Program Files\GitHub CLI\gh.exe",
            r"C:\Program Files (x86)\GitHub CLI\gh.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\GitHub CLI\gh.exe"),
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path
    return gh_path

GH_EXECUTABLE = find_gh_executable()

class Style:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    INFO = '\033[94m'

def print_success(msg: str):
    print(f"{Style.GREEN}{msg}{Style.ENDC}")

def print_error(msg: str):
    print(f"{Style.FAIL}{msg}{Style.ENDC}")

def print_info(msg: str):
    print(f"{Style.CYAN}{msg}{Style.ENDC}")

def print_warning(msg: str):
    print(f"{Style.WARNING}{msg}{Style.ENDC}")

def print_header(msg: str):
    print(f"\n{Style.HEADER}{'═' * 47}{Style.ENDC}")
    print(f"{Style.HEADER} {msg}{Style.ENDC}")
    print(f"{Style.HEADER}{'═' * 47}{Style.ENDC}\n")

def initialize_directories():
    for dir_path in [CONFIG_DIR, CACHE_DIR, LOGS_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)

def write_log(message: str):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOGS_DIR / "setup.log", "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        print_error(f"Error writing log: {str(e)}")

def press_enter_to_continue():
    input("\nTekan Enter untuk melanjutkan...")

def check_dependencies():
    print_header("CHECKING DEPENDENCIES")
    missing = False
    if not GH_EXECUTABLE:
        print_error("❌ GitHub CLI (gh) tidak ditemukan di PATH sistem.")
        print_warning("Install dari: https://cli.github.com/")
        missing = True
    else:
        try:
            result = subprocess.run([GH_EXECUTABLE, "--version"], capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                print_success(f"✅ GitHub CLI: {result.stdout.strip().splitlines()[0]}")
            else:
                print_error("❌ GitHub CLI ditemukan tapi gagal dieksekusi.")
                missing = True
        except Exception as e:
            print_error(f"❌ Error mengecek GitHub CLI: {str(e)}")
            missing = True
    
    git_executable = shutil.which("git")
    if not git_executable:
        print_error("❌ Git tidak ditemukan di PATH sistem.")
        print_warning("Install dari: https://git-scm.com/downloads")
        missing = True
    else:
        try:
            result = subprocess.run([git_executable, "--version"], capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                print_success(f"✅ Git: {result.stdout.strip()}")
            else:
                print_error("❌ Git ditemukan tapi gagal dieksekusi.")
                missing = True
        except Exception as e:
            print_error(f"❌ Error mengecek Git: {str(e)}")
            missing = True
    
    if missing:
        print_error("\n❌ Ada dependensi yang tidak terpenuhi. Install terlebih dahulu.")
        sys.exit(1)
    print_success("\n✅ Semua dependensi terpenuhi!\n")

def run_command(command: str, env: Optional[Dict[str, str]] = None, timeout: int = 30, cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    # Replace gh with full path if needed
    if command.strip().startswith("gh "):
        if not GH_EXECUTABLE:
            raise FileNotFoundError("GitHub CLI (gh) tidak ditemukan di PATH sistem atau lokasi standar.")
        command = command.replace("gh ", f'"{GH_EXECUTABLE}" ', 1)
    
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    
    try:
        return subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            encoding='utf-8', 
            env=full_env, 
            timeout=timeout,
            cwd=str(cwd) if cwd else None
        )
    except subprocess.TimeoutExpired:
        write_log(f"Command timeout: {command}")
        raise TimeoutError(f"Command timeout setelah {timeout}s")
    except Exception as e:
        write_log(f"Command error: {command} - {str(e)}")
        raise

def run_gh_api(command: str, token: str, max_retries: int = 3, timeout: int = 30) -> Dict[str, Any]:
    full_command = f"gh {command}"
    for attempt in range(max_retries):
        try:
            result = run_command(full_command, env={"GH_TOKEN": token}, timeout=timeout)
            if result.returncode == 0:
                return {"success": True, "output": result.stdout.strip(), "error": None}
            
            stderr = result.stderr.lower()
            if any(k in stderr for k in ["timeout", "connection", "network"]) and attempt < max_retries - 1:
                time.sleep((attempt + 1) * 2)
                continue
            
            if ("rate limit" in stderr or "403" in stderr) and attempt < max_retries - 1:
                time.sleep(60)
                continue
            
            return {"success": False, "output": None, "error": result.stderr.strip()}
        except TimeoutError as e:
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
            return {"success": False, "output": None, "error": str(e)}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}
    
    return {"success": False, "output": None, "error": f"Max retries ({max_retries}) exceeded"}

def read_file_lines(file_path: Path) -> List[str]:
    if not file_path.exists():
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        write_log(f"Error reading {file_path}: {str(e)}")
        return []

def append_to_file(file_path: Path, content: str):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(content + "\n")
    except Exception as e:
        write_log(f"Error appending to {file_path}: {str(e)}")
        raise

def load_json_file(file_path: Path, default: Optional[Dict] = None) -> Dict:
    if default is None:
        default = {}
    if not file_path.exists():
        return default
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default

def save_json_file(file_path: Path, data: Dict):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = file_path.with_suffix('.tmp')
    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp_path.replace(file_path)
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        write_log(f"Error saving JSON {file_path}: {str(e)}")
        raise

def validate_api_key_format(key: str) -> bool:
    return bool(key and len(key) > 10 and not key.isspace())

def remove_line_from_file(file_path: Path, line_to_remove: str):
    """Remove specific line from file"""
    if not file_path.exists():
        return
    try:
        lines = read_file_lines(file_path)
        filtered_lines = [line for line in lines if line != line_to_remove]
        file_path.write_text("\n".join(filtered_lines) + "\n" if filtered_lines else "", encoding="utf-8")
    except Exception as e:
        write_log(f"Error removing line from {file_path}: {str(e)}")
        raise
