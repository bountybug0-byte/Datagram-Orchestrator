# File: orchestrator/helpers.py
import os
import sys
import json
import subprocess
import time
import random
from pathlib import Path

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

def sanitize_for_log(text):
    """Remove sensitive data from logs"""
    import re
    # Remove tokens (ghp_, gho_, etc)
    text = re.sub(r'gh[pso]_[a-zA-Z0-9]{36,}', 'ghp_***REDACTED***', text)
    # Remove API keys (key_ prefix)
    text = re.sub(r'key_[a-zA-Z0-9]{30,}', 'key_***REDACTED***', text)
    return text

def write_log(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    sanitized = sanitize_for_log(message)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} - {sanitized}\n")

def press_enter_to_continue():
    input("\nTekan Enter untuk melanjutkan...")

# =============================================
# HELPER: FUNGSI SISTEM
# =============================================
def check_dependencies():
    print_header("CHECKING DEPENDENCIES")
    missing = False
    try:
        ver = subprocess.check_output("gh --version", shell=True, stderr=subprocess.STDOUT).decode('utf-8').splitlines()[0]
        print_success(f"GitHub CLI: {ver}")
    except Exception:
        print_error("GitHub CLI (gh) not found."); missing = True
    try:
        import nacl
        print_success("PyNaCl: Installed")
    except ImportError:
        print_error("PyNaCl not found. Run: pip install -r requirements.txt"); missing = True
    if missing:
        print_error("\nBeberapa dependensi tidak ditemukan. Mohon install terlebih dahulu.")
        sys.exit(1)

def run_command(command, env=None, check=False):
    try:
        return subprocess.run(
            command, shell=True, capture_output=True, text=True,
            encoding='utf-8', env=env, check=check
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        return e

def run_gh_api(command, token, max_retries=3):
    """
    Enhanced GitHub CLI API caller with:
    - Exponential backoff with jitter
    - Rate limit handling (HTTP 429)
    - Connection error retry
    - Detailed error reporting
    """
    full_command = f"gh {command}"
    current_env = os.environ.copy()
    current_env["GH_TOKEN"] = token
    
    base_delay = 2
    max_delay = 60
    
    for attempt in range(max_retries):
        result = run_command(full_command, env=current_env)
        
        if result.returncode == 0:
            return {"success": True, "output": result.stdout.strip()}
        
        stderr = result.stderr.lower() if result.stderr else ""
        
        # Check for rate limit (HTTP 429)
        if "rate limit" in stderr or "429" in stderr:
            if attempt < max_retries - 1:
                # Exponential backoff: 2, 4, 8... seconds + random jitter
                delay = min(base_delay * (2 ** attempt), max_delay)
                jitter = random.uniform(0, delay * 0.1)
                total_delay = delay + jitter
                
                print_warning(f"Rate limit hit. Waiting {total_delay:.1f}s...")
                write_log(f"Rate limit: Retry {attempt+1}/{max_retries}, delay={total_delay:.1f}s")
                time.sleep(total_delay)
                continue
            else:
                write_log(f"Rate limit: Max retries exceeded")
                return {"success": False, "output": "Rate limit exceeded after retries", "error_type": "rate_limit"}
        
        # Check for timeout/connection errors
        if "timeout" in stderr or "connection" in stderr or "network" in stderr:
            if attempt < max_retries - 1:
                delay = min(base_delay * (2 ** attempt), max_delay)
                jitter = random.uniform(0, delay * 0.1)
                total_delay = delay + jitter
                
                print_warning(f"Connection failed. Retrying in {total_delay:.1f}s...")
                write_log(f"Connection error: Retry {attempt+1}/{max_retries}")
                time.sleep(total_delay)
                continue
        
        # Other errors - fail immediately
        error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
        write_log(f"API Error: {sanitize_for_log(error_msg)}")
        return {"success": False, "output": error_msg, "error_type": "api_error"}
    
    write_log(f"Max retries ({max_retries}) exceeded")
    return {"success": False, "output": "Max retries exceeded", "error_type": "max_retries"}

# =============================================
# HELPER: MANAJEMEN FILE (ATOMIC)
# =============================================
import fcntl  # Unix file locking
import tempfile

def read_file_lines(file_path):
    if not file_path.exists(): 
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def append_to_file(file_path, content):
    """Atomic append with file locking"""
    file_path.parent.mkdir(exist_ok=True)
    
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            # Try to acquire exclusive lock (Unix/Linux)
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                f.write(content + "\n")
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except (AttributeError, OSError):
                # Windows fallback - no locking
                f.write(content + "\n")
    except Exception as e:
        write_log(f"Failed to append to {file_path}: {str(e)}")
        raise

def load_json_file(file_path, default=None):
    if default is None:
        default = {}
    if not file_path.exists(): 
        return default
    try:
        with open(file_path, "r", encoding="utf-8") as f: 
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        write_log(f"Failed to load JSON from {file_path}: {str(e)}")
        return default

def save_json_file(file_path, data):
    """Atomic JSON save using temp file + rename"""
    file_path.parent.mkdir(exist_ok=True)
    
    try:
        # Write to temp file first
        temp_fd, temp_path = tempfile.mkstemp(
            dir=file_path.parent, 
            prefix='.tmp_', 
            suffix='.json'
        )
        
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        # Atomic rename
        os.replace(temp_path, file_path)
        
    except Exception as e:
        # Cleanup temp file on error
        try:
            os.unlink(temp_path)
        except:
            pass
        write_log(f"Failed to save JSON to {file_path}: {str(e)}")
        raise

# =============================================
# HELPER: INPUT VALIDATION
# =============================================
import re

def validate_github_username(username):
    """Validate GitHub username format"""
    if not username:
        return False, "Username cannot be empty"
    if len(username) > 39:
        return False, "Username too long (max 39 chars)"
    if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', username):
        return False, "Invalid format (alphanumeric and hyphens only)"
    return True, ""

def validate_repo_name(repo_name):
    """Validate repository name format"""
    if not repo_name:
        return False, "Repository name cannot be empty"
    if len(repo_name) > 100:
        return False, "Repository name too long (max 100 chars)"
    if not re.match(r'^[a-zA-Z0-9._-]+$', repo_name):
        return False, "Invalid characters (use alphanumeric, dots, hyphens, underscores)"
    return True, ""

def validate_github_token(token):
    """Validate GitHub token format"""
    if not token:
        return False, "Token cannot be empty"
    if not token.startswith(('ghp_', 'gho_', 'ghs_')):
        return False, "Invalid token prefix (should start with ghp_, gho_, or ghs_)"
    if len(token) < 40:
        return False, "Token too short (minimum 40 chars)"
    return True, ""

def validate_api_key(key):
    """Validate Datagram API key format"""
    if not key:
        return False, "API key cannot be empty"
    if not key.startswith('key_'):
        return False, "Invalid API key format (should start with key_)"
    if len(key) < 35:
        return False, "API key too short"
    return True, ""
