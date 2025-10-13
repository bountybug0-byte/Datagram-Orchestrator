# File: orchestrator/helpers.py
import os
import sys
import json
import subprocess
import time
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional

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

GH_EXECUTABLE = shutil.which("gh")

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
    BOLD = '\033[1m'
    INFO = '\033[94m'  # Blue untuk info

def print_success(msg: str):
    print(f"{Style.GREEN}✅ {msg}{Style.ENDC}")

def print_error(msg: str):
    print(f"{Style.FAIL}❌ {msg}{Style.ENDC}")

def print_info(msg: str):
    print(f"{Style.CYAN}ℹ️  {msg}{Style.ENDC}")

def print_warning(msg: str):
    print(f"{Style.WARNING}⚠️  {msg}{Style.ENDC}")

def print_header(msg: str):
    print(f"\n{Style.HEADER}{'═' * 47}{Style.ENDC}")
    print(f"{Style.HEADER}  {msg}{Style.ENDC}")
    print(f"{Style.HEADER}{'═' * 47}{Style.ENDC}\n")

def initialize_directories():
    """Membuat direktori yang diperlukan jika belum ada."""
    for dir_path in [CONFIG_DIR, CACHE_DIR, LOGS_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)

def write_log(message: str):
    """Menulis log dengan timestamp."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass

def press_enter_to_continue():
    """Tunggu user menekan Enter."""
    input("\nTekan Enter untuk melanjutkan...")

# =============================================
# HELPER: FUNGSI SISTEM
# =============================================
def check_dependencies():
    """Validasi dependensi yang diperlukan."""
    print_header("CHECKING DEPENDENCIES")
    missing = False
    
    if not GH_EXECUTABLE:
        print_error("GitHub CLI (gh) tidak ditemukan di PATH sistem.")
        print_warning("Install dari: https://cli.github.com/")
        missing = True
    else:
        try:
            result = subprocess.run(
                [GH_EXECUTABLE, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip().split('\n')[0]
                print_success(f"GitHub CLI: {version}")
            else:
                print_error("GitHub CLI ditemukan tapi gagal dieksekusi.")
                missing = True
        except Exception as e:
            print_error(f"Error mengecek GitHub CLI: {str(e)}")
            missing = True
    
    try:
        import nacl
        print_success("PyNaCl: Installed")
    except ImportError:
        print_error("PyNaCl tidak ditemukan.")
        print_warning("Install dengan: pip install PyNaCl")
        missing = True
    
    if missing:
        print_error("\n❌ Ada dependensi yang tidak terpenuhi. Install terlebih dahulu.")
        sys.exit(1)
    
    print_success("\n✅ Semua dependensi terpenuhi!\n")

def run_command(command: str, env: Optional[Dict[str, str]] = None, timeout: int = 30) -> subprocess.CompletedProcess:
    """
    Menjalankan command dengan error handling yang robust.
    
    Args:
        command: Command yang akan dijalankan
        env: Environment variables tambahan
        timeout: Timeout dalam detik
    
    Returns:
        subprocess.CompletedProcess object
    """
    if command.strip().startswith("gh "):
        if not GH_EXECUTABLE:
            raise FileNotFoundError("GitHub CLI (gh) tidak ditemukan di PATH sistem.")
        command = command.replace("gh ", f'"{GH_EXECUTABLE}" ', 1)
    
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            env=full_env,
            timeout=timeout
        )
        return result
    except subprocess.TimeoutExpired:
        write_log(f"Command timeout: {command}")
        raise TimeoutError(f"Command timeout setelah {timeout}s")
    except Exception as e:
        write_log(f"Command error: {command} - {str(e)}")
        raise

def run_gh_api(command: str, token: str, max_retries: int = 3, timeout: int = 30) -> Dict[str, Any]:
    """
    Menjalankan GitHub CLI API command dengan retry mechanism.
    
    Args:
        command: GitHub CLI command (tanpa 'gh' prefix)
        token: GitHub Personal Access Token
        max_retries: Maksimal percobaan retry
        timeout: Timeout per percobaan
    
    Returns:
        Dict dengan keys: success (bool), output (str), error (str)
    """
    full_command = f"gh {command}"
    
    for attempt in range(max_retries):
        try:
            result = run_command(
                full_command,
                env={"GH_TOKEN": token},
                timeout=timeout
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "output": result.stdout.strip(),
                    "error": None
                }
            
            stderr = result.stderr.lower()
            
            # Retry untuk network errors
            if any(keyword in stderr for keyword in ["timeout", "connection", "network"]):
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print_warning(f"Network error. Retry dalam {wait_time}s...")
                    time.sleep(wait_time)
                    continue
            
            # Rate limit handling
            if "rate limit" in stderr or "403" in stderr:
                if attempt < max_retries - 1:
                    wait_time = 60
                    print_warning(f"Rate limit detected. Menunggu {wait_time}s...")
                    time.sleep(wait_time)
                    continue
            
            return {
                "success": False,
                "output": None,
                "error": result.stderr.strip()
            }
        
        except TimeoutError as e:
            if attempt < max_retries - 1:
                print_warning(f"Timeout. Retry {attempt + 1}/{max_retries}...")
                time.sleep(5)
                continue
            return {
                "success": False,
                "output": None,
                "error": str(e)
            }
        except Exception as e:
            write_log(f"GH API Error: {command} - {str(e)}")
            return {
                "success": False,
                "output": None,
                "error": str(e)
            }
    
    return {
        "success": False,
        "output": None,
        "error": f"Max retries ({max_retries}) exceeded"
    }

# =============================================
# HELPER: MANAJEMEN FILE
# =============================================
def read_file_lines(file_path: Path) -> List[str]:
    """Membaca file dan return list of lines (stripped)."""
    if not file_path.exists():
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        write_log(f"Error reading {file_path}: {str(e)}")
        return []

def append_to_file(file_path: Path, content: str):
    """Append content ke file secara atomic."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(content + "\n")
    except Exception as e:
        write_log(f"Error appending to {file_path}: {str(e)}")
        raise

def load_json_file(file_path: Path, default: Optional[Dict] = None) -> Dict:
    """Load JSON file dengan fallback ke default value."""
    if default is None:
        default = {}
    
    if not file_path.exists():
        return default
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        write_log(f"Error loading JSON {file_path}: {str(e)}")
        return default

def save_json_file(file_path: Path, data: Dict):
    """Save JSON file secara atomic menggunakan temp file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    temp_path = file_path.with_suffix('.tmp')
    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Atomic replace
        temp_path.replace(file_path)
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        write_log(f"Error saving JSON {file_path}: {str(e)}")
        raise

def validate_api_key_format(key: str) -> bool:
    """Validasi format API key (basic check)."""
    if not key or len(key) < 10:
        return False
    if key.isspace():
        return False
    return True

def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split list menjadi chunks."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]
