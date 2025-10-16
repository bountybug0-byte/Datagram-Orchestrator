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
    disable_workflow,
    enable_workflow,
    CONFIG_FILE,
    TOKEN_CACHE_FILE,
    FORKED_REPOS_FILE,
    WORKFLOWS_ENABLED_FILE
)
from .collaboration import sync_fork_with_upstream
from .utils import check_actions_usage


def enable_actions_on_repo(repo_path: str, token: str) -> bool:
    """Mengaktifkan GitHub Actions pada repositori menggunakan metode file input."""
    print_info("🔧 Enabling GitHub Actions on repository...")
    
    # PERBAIKAN FINAL: Membuat file JSON sementara untuk payload.
    # Ini adalah cara paling robust untuk mengirim data boolean dan
    # menghindari masalah parsing oleh shell.
    payload = {
        "enabled": True,
        "allowed_actions": "all"
    }
    
    temp_file_path = None
    try:
        # Buat file sementara dan tulis payload JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(payload, f)
            temp_file_path = f.name

        # Gunakan flag --input untuk membaca payload dari file
        cmd = f'api -X PUT repos/{repo_path}/actions/permissions --input "{temp_file_path}"'
        result = run_gh_api(cmd, token, timeout=30)
        
    finally:
        # Pastikan file sementara selalu dihapus
        if temp_file_path and Path(temp_file_path).exists():
            Path(temp_file_path).unlink()

    if result["success"]:
        print_success("✅ Actions enabled on repository")
        time.sleep(2)
        return True
    else:
        error_msg = result.get('error', '').lower()
        if "must be an organization" in error_msg:
             print_info("ℹ️  Skipping for personal account (not required)")
             return True
        elif "not available" in error_msg:
             print_info("ℹ️  Actions permissions setting not available for this repository.")
             return True
        print_warning(f"⚠️ Failed to enable Actions: {result.get('error')}")
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

    total_accounts = len(token_cache)
    print_info(f"📊 Memulai proses untuk {total_accounts} akun...")

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
    success_count = 0
    failed_count = 0
    main_username = config['main_account_username']

    for i, target in enumerate(targets, 1):
        repo_path, token, username = target['repo'], target['token'], target['username']
        print(f"\n{'='*47}\n[{i}/{len(targets)}] Deploying to: {repo_path}\n{'='*47}")

        if username != main_username:
            print_info("🔄 Menyinkronkan fork...")
            if sync_fork_with_upstream(repo_path, token):
                print_success("✅ Fork berhasil disinkronkan")
            else:
                print_warning("⚠️ Sinkronisasi fork gagal, melanjutkan deployment...")
            time.sleep(2)

        enable_actions_on_repo(repo_path, token)

        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            try:
                print_info("📥 Cloning repository...")
                clone_cmd = f"git clone --depth 1 https://{token}@github.com/{repo_path}.git ."
                clone_result = run_command(clone_cmd, cwd=temp_dir, timeout=120)
                if clone_result.returncode != 0:
                    print_error(f"❌ Clone failed: {clone_result.stderr}")
                    failed_count += 1
                    continue

                workflow_dir = temp_dir / ".github" / "workflows"
                workflow_dir.mkdir(parents=True, exist_ok=True)
                
                # Cek apakah file workflow sudah ada dan sama
                workflow_target_path = workflow_dir / workflow_file
                if workflow_target_path.exists() and workflow_target_path.read_text(encoding='utf-8') == workflow_content:
                    print_info("ℹ️  Workflow file is already up to date.")
                    success_count += 1
                    # Workflow mungkin dinonaktifkan, jadi kita tetap enable
                    enable_workflow(repo_path, token, workflow_file)
                    continue

                workflow_target_path.write_text(workflow_content, encoding='utf-8')
                print_success(f"✅ Workflow file written.")

                print_info("📤 Committing and pushing...")
                run_command("git config user.name 'Datagram Bot'", cwd=temp_dir)
                run_command("git config user.email 'bot@datagram.local'", cwd=temp_dir)
                run_command(f"git add .github/workflows/{workflow_file}", cwd=temp_dir)
                
                # Hanya commit jika ada perubahan
                commit_result = run_command('git commit -m "Deploy/Update Datagram workflow"', cwd=temp_dir)
                if "nothing to commit" in commit_result.stdout.lower() or "no changes" in commit_result.stdout.lower():
                     print_info("ℹ️ No changes to commit.")
                     success_count += 1
                     enable_workflow(repo_path, token, workflow_file)
                     continue

                print_info("🔒 Disabling workflow before push...")
                disable_workflow(repo_path, token, workflow_file)
                time.sleep(2)

                push_result = run_command(f"git push", cwd=temp_dir, timeout=120)
                if push_result.returncode == 0:
                    print_success("✅ Push successful")
                    success_count += 1
                else:
                    print_error(f"❌ Push failed: {push_result.stderr}")
                    failed_count += 1

            except Exception as e:
                print_error(f"❌ Error during deployment: {str(e)}")
                failed_count += 1
            time.sleep(2)

    print_success(f"\n{'='*47}")
    print_success(f"✅ Deployment selesai!")
    print_info(f"   Berhasil: {success_count}, Gagal: {failed_count}, Total: {len(targets)}")
    print_success(f"{'='*47}")

# ... (sisa fungsi di deployment.py tetap sama) ...
def wait_for_workflow_completion(repo_path: str, token: str, run_id: int, timeout: int = 21600) -> bool:
    """
    Menunggu hingga workflow run selesai (completed).
    """
    start_time = time.time()
    poll_interval = 30
    
    print_info(f"⏳ Menunggu workflow run #{run_id} selesai...")
    
    while (time.time() - start_time) < timeout:
        result = run_gh_api(
            f"api repos/{repo_path}/actions/runs/{run_id}",
            token,
            timeout=30
        )
        
        if not result["success"]:
            print_warning(f"⚠️ Gagal mengecek status: {result.get('error')}")
            time.sleep(poll_interval)
            continue
        
        try:
            run_data = json.loads(result["output"])
            status = run_data.get("status", "")
            conclusion = run_data.get("conclusion", "")
            
            if status == "completed":
                if conclusion == "success":
                    print_success(f"✅ Workflow selesai dengan status: {conclusion}")
                else:
                    print_warning(f"⚠️ Workflow selesai dengan status: {conclusion}")
                return True
            
            elapsed = int(time.time() - start_time)
            print_info(f"   Status: {status} | Elapsed: {elapsed//60}m {elapsed%60}s")
            
        except (json.JSONDecodeError, KeyError) as e:
            print_warning(f"⚠️ Error parsing workflow status: {str(e)}")
        
        time.sleep(poll_interval)
    
    print_error(f"❌ Timeout: Workflow tidak selesai dalam {timeout//60} menit")
    return False


def invoke_workflow_trigger():
    """Memicu workflow di repositori target secara berurutan per akun."""
    print_header("11. TRIGGER WORKFLOW (SEQUENTIAL)")
    config = load_json_file(CONFIG_FILE)
    token_cache = load_json_file(TOKEN_CACHE_FILE)
    forked_users = read_file_lines(FORKED_REPOS_FILE)
    
    if not config or not token_cache:
        print_error("Konfigurasi atau cache token tidak lengkap.")
        return

    total_accounts = len(token_cache)
    print_info(f"📊 Memulai proses untuk {total_accounts} akun...")

    print("Pilih target:\n 1. Main repo saja\n 2. Semua forked repos\n 3. Main + semua forks")
    choice = input("\nPilihan (1/2/3): ").strip()
    
    targets = []
    if choice in ['1', '3']:
        targets.append({
            'repo': f"{config['main_account_username']}/{config['main_repo_name']}", 
            'token': config['main_token'],
            'username': config['main_account_username']
        })
    if choice in ['2', '3']:
        targets.extend([
            {
                'repo': f"{u}/{config['main_repo_name']}", 
                'token': t,
                'username': u
            }
            for t, u in token_cache.items() if u in forked_users
        ])

    if not targets:
        print_warning("Tidak ada target yang dipilih.")
        return

    workflow_file = "datagram-runner.yml"
    billing_threshold = 1800
    success_count = 0
    failed_count = 0
    
    print_info(f"\n🚀 Akan memicu workflow untuk {len(targets)} akun secara BERURUTAN")
    print_warning(f"⚠️ Ambang batas billing: {billing_threshold} menit")
    
    if input("\nLanjutkan? (y/n): ").lower() != 'y':
        print_warning("Operasi dibatalkan.")
        return

    for i, target in enumerate(targets, 1):
        repo_path = target['repo']
        token = target['token']
        username = target['username']
        
        print(f"\n{'='*50}")
        print(f"[{i}/{len(targets)}] Processing: {username}")
        print('='*50)
        
        print_info("📊 Mengecek penggunaan Actions...")
        usage_minutes = check_actions_usage(username, token)
        print_info(f"   Total menit terpakai: {usage_minutes}/{billing_threshold}")
        
        if usage_minutes >= billing_threshold:
            print_warning(f"⚠️ PERINGATAN: Penggunaan Actions ({usage_minutes} menit) melebihi threshold!")
            if input(f"   Tetap lanjutkan untuk {username}? (y/n): ").lower() != 'y':
                print_warning(f"⏭️ Melewati {username}")
                failed_count += 1
                continue
        
        print_info("🔓 Enabling workflow...")
        if not enable_workflow(repo_path, token, workflow_file):
            print_error("❌ Gagal enable workflow")
            failed_count += 1
            continue
        
        time.sleep(3)
        
        print_info(f"🚀 Memicu workflow untuk {repo_path}...")
        trigger_result = run_gh_api(
            f"api -X POST repos/{repo_path}/actions/workflows/{workflow_file}/dispatches -f ref=main",
            token,
            timeout=30
        )
        
        if not trigger_result["success"]:
            print_error(f"❌ Gagal memicu workflow: {trigger_result.get('error')}")
            failed_count += 1
            continue
        
        print_success("✅ Workflow berhasil dipicu")
        
        time.sleep(10)
        
        print_info("🔍 Mencari workflow run yang baru saja dipicu...")
        runs_result = run_gh_api(
            f"api repos/{repo_path}/actions/runs?per_page=1",
            token,
            timeout=30
        )
        
        if not runs_result["success"]:
            print_error(f"❌ Gagal mengambil workflow runs: {runs_result.get('error')}")
            failed_count += 1
            continue
        
        try:
            runs_data = json.loads(runs_result["output"])
            workflow_runs = runs_data.get("workflow_runs", [])
            
            if not workflow_runs:
                print_error("❌ Tidak ada workflow run ditemukan")
                failed_count += 1
                continue
            
            run_id = workflow_runs[0].get("id")
            if not run_id:
                print_error("❌ Run ID tidak valid")
                failed_count += 1
                continue
            
            print_info(f"🎯 Monitoring workflow run ID: {run_id}")
            
            if wait_for_workflow_completion(repo_path, token, run_id):
                print_info("🔒 Disabling workflow after completion...")
                disable_workflow(repo_path, token, workflow_file)
                
                success_count += 1
                print_success(f"✅ Akun {username} selesai\n")
            else:
                print_error(f"❌ Akun {username} gagal atau timeout\n")
                failed_count += 1
            
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            print_error(f"❌ Error parsing workflow runs: {str(e)}")
            failed_count += 1
            continue
        
        if i < len(targets):
            print_info("⏸️ Delay 5 detik sebelum akun berikutnya...")
            time.sleep(5)

    print_success(f"\n{'='*50}")
    print_success(f"✅ Proses selesai!")
    print_info(f"   Berhasil: {success_count}, Gagal/Dilewati: {failed_count}, Total: {len(targets)}")
    print_success('='*50)


def show_workflow_status():
    """Menampilkan status 3 workflow run terakhir."""
    print_header("12. SHOW WORKFLOW STATUS")
    config = load_json_file(CONFIG_FILE)
    token_cache = load_json_file(TOKEN_CACHE_FILE)
    forked_users = read_file_lines(FORKED_REPOS_FILE)
    
    if not config or not token_cache:
        print_error("Konfigurasi atau cache token tidak lengkap.")
        return

    total_accounts = len(token_cache)
    print_info(f"📊 Memulai proses untuk {total_accounts} akun...")

    print("Pilih target:\n 1. Main repo saja\n 2. Semua forked repos\n 3. Main + semua forks")
    choice = input("\nPilihan (1/2/3): ").strip()
    
    targets = []
    if choice in ['1', '3']:
        targets.append({
            'repo': f"{config['main_account_username']}/{config['main_repo_name']}", 
            'token': config['main_token']
        })
    if choice in ['2', '3']:
        targets.extend([
            {'repo': f"{u}/{config['main_repo_name']}", 'token': t} 
            for t, u in token_cache.items() if u in forked_users
        ])

    if not targets:
        print_warning("Tidak ada target yang dipilih.")
        return
    
    print_info(f"\n📊 Checking workflow status untuk {len(targets)} repos...\n")

    success_count = 0
    failed_count = 0

    for i, target in enumerate(targets, 1):
        repo_path = target['repo']
        token = target['token']
        
        print(f"{'='*47}\n[{i}/{len(targets)}] {repo_path}\n{'='*47}")
        result = run_gh_api(
            f"api repos/{repo_path}/actions/runs --jq '.workflow_runs[:3] | .[] | \"\\(.status) | \\(.conclusion // \"running\") | \\(.created_at)\"'",
            token, 
            timeout=30
        )
        
        if result["success"] and result["output"]:
            for run in result["output"].strip().split("\n"):
                print(f"  {run}")
            success_count += 1
        elif not result["output"]:
             print("  ℹ️ No workflow runs found")
             success_count += 1
        else:
            print_error(f"  ❌ Failed to fetch status: {result.get('error')}")
            failed_count += 1
        print()
        time.sleep(1)

    print_success(f"\n{'='*47}")
    print_success(f"✅ Proses selesai!")
    print_info(f"   Berhasil: {success_count}, Gagal: {failed_count}, Total: {len(targets)}")
    print_success(f"{'='*47}")
