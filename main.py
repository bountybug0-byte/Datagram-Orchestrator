# File: main.py
import os
import sys
import time
from orchestrator.helpers import (
    Style, print_success, print_warning, print_error,
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
    print("║     DATAGRAM ORCHESTRATOR v3.2 (OPTIMIZED)   ║")
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
    print("  8. Auto Set Secrets (Actions + Codespaces)")
    
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
    try:
        initialize_directories()
        check_dependencies()
        
        menu_actions = {
            '1': initialize_configuration,
            '2': import_api_keys,
            '3': show_api_keys_status,
            '4': import_github_tokens,
            '5': validate_github_tokens,
            '6': invoke_auto_invite,
            '7': invoke_auto_accept,
            '8': invoke_auto_set_secrets,
            '9': deploy_to_github,
            '10': invoke_workflow_trigger,
            '11': show_workflow_status,
            '12': view_logs,
            '13': clean_cache,
        }
        
        while True:
            try:
                show_menu()
                choice = input("Pilih menu (0-13): ").strip()
                
                if choice == '0':
                    print_success("Terima kasih telah menggunakan Datagram Orchestrator!")
                    break
                
                action = menu_actions.get(choice)
                if action:
                    try:
                        action()
                    except KeyboardInterrupt:
                        print_warning("\n\nOperasi dibatalkan oleh user.")
                    except Exception as e:
                        print_error(f"Terjadi error: {str(e)}")
                        print_warning("Lihat logs/setup.log untuk detail.")
                    
                    press_enter_to_continue()
                else:
                    print_warning("Pilihan tidak valid. Silakan pilih 0-13.")
                    time.sleep(1)
            
            except KeyboardInterrupt:
                print_warning("\n\nKembali ke menu utama...")
                time.sleep(1)
    
    except KeyboardInterrupt:
        print_warning("\n\nProgram dihentikan oleh user. Sampai jumpa!")
        sys.exit(0)
    except Exception as e:
        print_error(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
