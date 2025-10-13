# File: orchestrator/helpers.py
import os
import sys
import json
import subprocess
import time
import random
from pathlib import Path
import tempfile
import shutil

# Coba impor fcntl, jika gagal, abaikan karena ini untuk Unix
try:
    import fcntl  # Unix file locking
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

# =============================================
# KONFIGURASI PATH
# =============================================
BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
CACHE_DIR = CONFIG_DIR / ".cache"
LOGS_DIR = BASE_DIR / "logs"

# File Konfigurasi & Cache
API_KEYS_FILE = CONFIG_DIR / "api_keys.txt"
TOKENS_FILE = CONFIG_DIR / "tokens.txt"
CONFIG_FILE = CONFIG_DIR / "config.json"
TOKEN_CACHE_FILE = CACHE_DIR / "token_cache.json"
INVITED_USERS_FILE = CACHE_DIR / "invited_users.txt"
ACCEPTED_USERS_FILE = CACHE_DIR / "accepted_users.txt"
SECRETS_SET_FILE = CACHE_DIR / "secrets_set.txt"
LOG_FILE = LOGS_DIR / "setup.log"

# --- PERBAIKAN: Cari path 'gh' secara otomatis ---
GH_EXECUTABLE = shutil.which("gh")
# ------------------------------------------------

# =============================================
# HELPER: TAMPILAN & LOGGING
# =============================================
class Style:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

def print_success(msg): print(f"{Style.GREEN}✅ {msg}{Style.ENDC}")
def print_error(msg): print(f"{Style.FAIL}❌ {msg}{Style.ENDC}")
def print_info(msg): print(f"{Style.CYAN}ℹ️  {msg}{Style.ENDC}")
def print_warning(msg): print(f"{Style.WARNING}⚠️  {msg}{Style.ENDC}")

def print_header(msg):
    print(f"\n{Style.HEADER}═══════════════════════════════════════{Style.ENDC}")
    print(f"{Style.HEADER}  {msg}{Style.ENDC}")
    print(f"{Style.HEADER}═══════════════════════════════════════{Style.ENDC}\n")

def initialize_directories():
    for dir_path in [CONFIG_DIR, CACHE_DIR, LOGS_DIR]:
        dir_path.mkdir(exist_ok=True)

def write_log(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} - {message}\n")

def press_enter_to_continue():
    input("\nTekan Enter untuk melanjutkan...")

# =============================================
# HELPER: FUNGSI SISTEM
# =============================================
def check_dependencies():
    print_header("CHECKING DEPENDENCIES")
    missing = False
    
    # --- PERBAIKAN: Cek GH_EXECUTABLE ---
    if not GH_EXECUTABLE:
        print_error("GitHub CLI (gh) not found in system PATH.")
        missing = True
    else:
        try:
            ver = subprocess.check_output(f'"{GH_EXECUTABLE}" --version', shell=True, stderr=subprocess.STDOUT).decode('utf-8').splitlines()[0]
            print_success(f"GitHub CLI: {ver}")
        except Exception:
            print_error("GitHub CLI (gh) found but failed to execute.")
            missing = True
    # -------------------------------------
            
    try:
        import nacl
        print_success("PyNaCl: Installed")
    except ImportError:
        print_error("PyNaCl not found. Run: pip install -r requirements.txt")
        missing = True
        
    if missing:
        print_error("\nBeberapa dependensi tidak ditemukan. Mohon install terlebih dahulu.")
        sys.exit(1)

def run_command(command, env=None, check=False):
    # --- PERBAIKAN: Gunakan path 'gh' yang eksplisit ---
    if command.strip().startswith("gh "):
        if not GH_EXECUTABLE:
            raise FileNotFoundError("GitHub CLI (gh) not found.")
        # Ganti 'gh' dengan path lengkapnya
        command = command.replace("gh ", f'"{GH_EXECUTABLE}" ', 1)
    # -------------------------------------------------
        
    try:
        return subprocess.run(
            command, shell=True, capture_output=True, text=True,
            encoding='utf-8', env=env, check=check
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return e

def run_gh_api(command, token, max_retries=3):
    # Tidak perlu diubah, karena sudah memanggil run_command yang diperbaiki
    full_command = f"gh {command}"
    current_env = os.environ.copy()
    current_env["GH_TOKEN"] = token
    
    for attempt in range(max_retries):
        result = run_command(full_command, env=current_env)
        
        if result and hasattr(result, 'returncode') and result.returncode == 0:
            return {"success": True, "output": result.stdout.strip()}
        
        stderr = result.stderr.lower() if result and hasattr(result, 'stderr') and result.stderr else ""
        
        if "timeout" in stderr or "connection" in stderr:
            if attempt < max_retries - 1:
                print_warning(f"Connection failed. Retrying...")
                time.sleep(5)
                continue
        
        error_output = result.stderr.strip() if result and hasattr(result, 'stderr') else "Unknown error"
        return {"success": False, "output": error_output}
        
    return {"success": False, "output": "Max retries exceeded"}

# =============================================
# HELPER: MANAJEMEN FILE (ATOMIC)
# =============================================
def read_file_lines(file_path):
    if not file_path.exists(): 
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def append_to_file(file_path, content):
    file_path.parent.mkdir(exist_ok=True)
    with open(file_path, "a", encoding="utf-8") as f:
        if HAS_FCNTL:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.write(content + "\n")
        if HAS_FCNTL:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

def load_json_file(file_path, default=None):
    if default is None:
        default = {}
    if not file_path.exists(): 
        return default
    try:
        with open(file_path, "r", encoding="utf-8") as f: 
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default

def save_json_file(file_path, data):
    file_path.parent.mkdir(exist_ok=True)
    temp_fd, temp_path = tempfile.mkstemp(dir=file_path.parent)
    try:
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        os.replace(temp_path, file_path)
    except Exception as e:
        os.unlink(temp_path)
        raise e
