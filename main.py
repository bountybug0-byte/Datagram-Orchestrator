# File: main.py
import os
import sys
import time
from orchestrator.helpers import (
    Style, print_success, print_warning,
    initialize_directories, check_dependencies, press_enter_to_continue
)
from orchestrator.core import (
    initialize_configuration, import_api_keys, show_api_keys_status,
    import_github_tokens, validate_github_tokens, invoke_auto_invite,
    invoke_auto_accept, invoke_auto_set_secrets, deploy_to_github,
    invoke_workflow_trigger, show_workflow_status, view_logs, clean_cache
)

def show_menu():
    """Menampilkan menu utama program."""
    os.system('cls' if os.name == 'nt' else 'clear')
    print(Style.CYAN + "╔═══════════════════════════════════════════════╗")
    print("║     DATAGRAM ORCHESTRATOR v3.0 (Refactored)   ║")
    print("╚═══════════════════════════════════════════════╝" + Style.ENDC)
    
    print(f"\n{Style.WARNING}📋 SETUP & KONFIGURASI{Style.ENDC}")
    print("  1. Initialize Configuration")
    print("  2. Import API Keys")
    print("  3. Show API Keys Status")
    print("  4. Import GitHub Tokens")
    print("  5. Validate GitHub Tokens")
    
    print(f"\n{Style.WARNING}🤝 MANAJEMEN KOLABORASI{Style.ENDC}")
    print("  6. Auto Invite Collaborators")
    print("  7. Auto Accept Invitations")
    print("  8. Auto Set Secrets")
    
    print(f"\n{Style.WARNING}🚀 DEPLOYMENT & MONITORING{Style.ENDC}")
    print("  9. Deploy to GitHub")
    print(" 10. Trigger Workflow")
    print(" 11. Show Workflow Status")
    
    print(f"\n{Style.WARNING}🔧 UTILITIES{Style.ENDC}")
    print(" 12. View Logs")
    print(" 13. Clean Cache")
    
    print("\n  0. Exit")
    print("═══════════════════════════════════════════════")

def main():
    """Fungsi utama untuk menjalankan program."""
    initialize_directories()
    check_dependencies()
    
    menu_actions = {
        '1': initialize_configuration, '2': import_api_keys,
        '3': show_api_keys_status,     '4': import_github_tokens,
        '5': validate_github_tokens,   '6': invoke_auto_invite,
        '7': invoke_auto_accept,       '8': invoke_auto_set_secrets,
        '9': deploy_to_github,         '10': invoke_workflow_trigger,
        '11': show_workflow_status,    '12': view_logs,
        '13': clean_cache,
    }
    
    while True:
        show_menu()
        choice = input("Pilih menu (0-13): ")
        
        if choice == '0':
            print_success("Terima kasih!")
            break
        
        action = menu_actions.get(choice)
        if action:
            action()
            press_enter_to_continue()
        else:
            print_warning("Pilihan tidak valid.")
            time.sleep(1)

if __name__ == "__main__":
    main()
