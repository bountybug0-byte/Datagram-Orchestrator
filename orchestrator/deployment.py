# orchestrator/deployment.py

import json
import time
import tempfile
from pathlib import Path

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
    CONFIG_FILE,
    TOKEN_CACHE_FILE,
    FORKED_REPOS_FILE,
    WORKFLOWS_ENABLED_FILE
)

def enable_actions_on_repo(repo_path: str, token: str) -> bool:
    """Mengaktifkan GitHub Actions pada repositori."""
    print_info("🔧 Enabling GitHub Actions on repository...")
    
    # Set Actions permissions ke 'all'
    result = run_gh_api(
        f"api -X PUT repos/{repo_path}/actions/permissions -f enabled=true -f allowed_actions=all",
        token,
        timeout=30
    )
    
    if result["success"]:
        print_success("✅ Actions enabled on repository")
        time.sleep(2)
        return True
    else:
        print_warning(f"⚠️ Failed to enable Actions: {result.get('error')}")
        return False

def enable_workflow_with_retry(repo_path: str, token: str, workflow_file: str) -> bool:
    """Mencoba mengaktifkan workflow dengan beberapa kali percobaan."""
    max_retries = 5
    delay = 10
    
    for attempt in range(max_retries):
        print_info(f"Attempt {attempt + 1}/{max_retries}: Checking workflows...")
        time.sleep(delay * (attempt + 1))
        
        check_result = run_gh_api(f"api repos/{repo_path}/actions/workflows", token, timeout=60)
        if not check_result["success"]:
            print_warning(f"Failed to list workflows: {check_result['error']}")
            continue
        
        try:
            workflows = json.loads(check_result["output"]).get("workflows", [])
            workflow_id = next((wf.get("id") for wf in workflows if workflow_file in wf.get("path", "")), None)

            if workflow_id:
                enable_result = run_gh_api(
                    f"api -X PUT repos/{repo_path}/actions/workflows/{workflow_id}/enable", token, timeout=30
                )
                if enable_result["success"] or "already enabled" in enable_result.get("error", "").lower():
                    print_success(f"✅ Workflow enabled (ID: {workflow_id})")
                    return True
                print_warning(f"Enable failed: {enable_result.get('error')}")
            else:
                print_warning(f"Workflow '{workflow_file}' not found.")
        except json.JSONDecodeError as e:
            print_error(f"JSON decode error: {e}")

    print_error(f"❌ Failed to enable workflow after {max_retries} attempts")
    return False

def deploy_to_github():
    """Men-deploy file workflow ke repositori target."""
    print_header("10. DEPLOY TO GITHUB")
    config = load_json_file(CONFIG_FILE)
    token_cache = load_json_file(TOKEN_CACHE_FILE)
    forked_users = read_file_lines(FORKED_REPOS_FILE)
    if not config or not token_cache:
        print_error("Konfigurasi atau cache token tidak lengkap.")
        return

    workflow_file = "datagram-runner.yml"
    workflow_source = Path(__file__).parent.parent / ".github" / "workflows" / workflow_file
    if not workflow_source.exists():
        print_error(f"File workflow tidak ditemukan: {workflow_source}")
        return

    print("Pilih target deployment:\n 1. Main repo saja\n 2. Semua forked repos\n 3. Main + semua forks")
    choice = input("\nPilihan (1/2/3): ").strip()

    targets = []
    if choice in ['1', '3']:
        targets.append({'repo': f"{config['main_account_username']}/{config['main_repo_name']}", 'token': config['main_token'], 'username': config['main_account_username']})
    if choice in ['2', '3']:
        targets.extend([
            {'repo': f"{u}/{config['main_repo_name']}", 'token': t, 'username': u}
            for t, u in token_cache.items() if u in forked_users
        ])

    if not targets or input(f"\n🎯 Akan deploy ke {len(targets)} repo. Lanjutkan? (y/n): ").lower() != 'y':
        print_warning("Operasi dibatalkan.")
        return

    workflow_content = workflow_source.read_text(encoding='utf-8')
    workflows_enabled = read_file_lines(WORKFLOWS_ENABLED_FILE)
    success_count = 0

    for i, target in enumerate(targets, 1):
        repo_path, token, username = target['repo'], target['token'], target['username']
        print(f"\n{'='*47}\n[{i}/{len(targets)}] Deploying to: {repo_path}\n{'='*47}")

        # Aktifkan GitHub Actions di level repository
        enable_actions_on_repo(repo_path, token)

        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            try:
                print_info("📥 Cloning repository...")
                clone_cmd = f"git clone https://{token}@github.com/{repo_path}.git ."
                clone_result = run_command(clone_cmd, cwd=temp_dir, timeout=120)
                if clone_result.returncode != 0:
                    print_error(f"❌ Clone failed: {clone_result.stderr}")
                    continue

                workflow_dir = temp_dir / ".github" / "workflows"
                workflow_dir.mkdir(parents=True, exist_ok=True)
                (workflow_dir / workflow_file).write_text(workflow_content, encoding='utf-8')
                print_success(f"✅ Workflow file written.")

                print_info("📤 Committing and pushing...")
                run_command("git config user.name 'Datagram Bot'", cwd=temp_dir)
                run_command("git config user.email 'bot@datagram.local'", cwd=temp_dir)
                run_command("git add .", cwd=temp_dir)
                commit_result = run_command('git commit -m "Deploy Datagram workflow"', cwd=temp_dir)
                
                if "nothing to commit" in commit_result.stdout.lower():
                    print_info("ℹ️ No changes to commit.")
                    if repo_path not in workflows_enabled:
                         if enable_workflow_with_retry(repo_path, token, workflow_file):
                            append_to_file(WORKFLOWS_ENABLED_FILE, repo_path)
                    success_count += 1
                    continue

                push_result = run_command(f"git push", cwd=temp_dir, timeout=120)
                if push_result.returncode == 0:
                    print_success("✅ Push successful")
                    if repo_path not in workflows_enabled:
                        print_info("🔄 Enabling workflow...")
                        if enable_workflow_with_retry(repo_path, token, workflow_file):
                            append_to_file(WORKFLOWS_ENABLED_FILE, repo_path)
                    success_count += 1
                else:
                    print_error(f"❌ Push failed: {push_result.stderr}")

            except Exception as e:
                print_error(f"❌ Error during deployment: {str(e)}")
            time.sleep(2)

    print_success(f"\n{'='*47}\n✅ Deployment completed! Success: {success_count}/{len(targets)}\n{'='*47}")


def invoke_workflow_trigger():
    """Memicu workflow di repositori target."""
    print_header("11. TRIGGER WORKFLOW")
    config = load_json_file(CONFIG_FILE)
    token_cache = load_json_file(TOKEN_CACHE_FILE)
    forked_users = read_file_lines(FORKED_REPOS_FILE)
    if not config or not token_cache:
        print_error("Konfigurasi atau cache token tidak lengkap.")
        return

    print("Pilih target:\n 1. Main repo saja\n 2. Semua forked repos\n 3. Main + semua forks")
    choice = input("\nPilihan (1/2/3): ").strip()
    
    targets = []
    if choice in ['1', '3']:
        targets.append({'repo': f"{config['main_account_username']}/{config['main_repo_name']}", 'token': config['main_token']})
    if choice in ['2', '3']:
        targets.extend([{'repo': f"{u}/{config['main_repo_name']}", 'token': t} for t, u in token_cache.items() if u in forked_users])

    if not targets:
        print_warning("Tidak ada target yang dipilih.")
        return

    workflow_file = "datagram-runner.yml"
    success_count = 0
    print_info(f"\n🚀 Triggering workflow untuk {len(targets)} repos...")

    for i, target in enumerate(targets, 1):
        repo_path, token = target['repo'], target['token']
        print(f"[{i}/{len(targets)}] {repo_path}...", end="", flush=True)
        result = run_gh_api(
            f"api -X POST repos/{repo_path}/actions/workflows/{workflow_file}/dispatches -f ref=main", token, timeout=30
        )
        if result["success"]:
            print_success(" ✅")
            success_count += 1
        else:
            print_error(f" ❌ {result.get('error', 'Unknown error')}")
        time.sleep(1)

    print_success(f"\n✅ Selesai! Berhasil trigger: {success_count}/{len(targets)}")


def show_workflow_status():
    """Menampilkan status 3 workflow run terakhir."""
    print_header("12. SHOW WORKFLOW STATUS")
    config = load_json_file(CONFIG_FILE)
    token_cache = load_json_file(TOKEN_CACHE_FILE)
    forked_users = read_file_lines(FORKED_REPOS_FILE)
    if not config or not token_cache:
        print_error("Konfigurasi atau cache token tidak lengkap.")
        return

    print("Pilih target:\n 1. Main repo saja\n 2. Semua forked repos\n 3. Main + semua forks")
    choice = input("\nPilihan (1/2/3): ").strip()
    
    targets = []
    if choice in ['1', '3']:
        targets.append({'repo': f"{config['main_account_username']}/{config['main_repo_name']}", 'token': config['main_token']})
    if choice in ['2', '3']:
        targets.extend([{'repo': f"{u}/{config['main_repo_name']}", 'token': t} for t, u in token_cache.items() if u in forked_users])

    if not targets:
        print_warning("Tidak ada target yang dipilih.")
        return
    
    print_info(f"\n📊 Checking workflow status untuk {len(targets)} repos...\n")

    for i, target in enumerate(targets, 1):
        repo_path, token = target['repo'], target['token']
        print(f"{'='*47}\n[{i}/{len(targets)}] {repo_path}\n{'='*47}")
        result = run_gh_api(
            f"api repos/{repo_path}/actions/runs --jq '.workflow_runs[:3] | .[] | \"\\(.status) | \\(.conclusion // \"running\") | \\(.created_at)\"'",
            token, timeout=30
        )
        if result["success"] and result["output"]:
            for run in result["output"].strip().split("\n"):
                print(f"  {run}")
        elif not result["output"]:
             print("  ℹ️ No workflow runs found")
        else:
            print_error(f"  ❌ Failed to fetch status: {result.get('error')}")
        print()
        time.sleep(1)
