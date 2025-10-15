import os
import sys
import time
from typing import List, Dict, Any
from orchestrator.helpers import (
    Style, print_success, print_warning, print_error,
    initialize_directories, check_dependencies, press_enter_to_continue
)
from orchestrator.core import (
    initialize_configuration, import_api_keys, show_api_keys_status,
    import_github_tokens, validate_github_tokens, invoke_auto_invite,
    invoke_auto_accept, invoke_auto_fork, invoke_auto_set_secrets,
    deploy_to_github, invoke_workflow_trigger, show_workflow_status,
    view_logs, clean_cache
)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_main_menu():
    clear_screen()
    print(Style.CYAN + Style.BOLD + "╔═══════════════════════════════════════════════╗")
    print("║     DATAGRAM ORCHESTRATOR v3.2 (STABLE)      ║")
    print("╚═══════════════════════════════════════════════╝" + Style.ENDC)
    print(f"\n{Style.HEADER}═══════════════ MAIN MENU ═══════════════{Style.ENDC}\n")
    print(f"{Style.CYAN} 1.{Style.ENDC} Setup & Konfigurasi")
    print(f"{Style.CYAN} 2.{Style.ENDC} Manajemen Kolaborasi")
    print(f"{Style.CYAN} 3.{Style.ENDC} Deployment & Monitoring")
    print(f"{Style.CYAN} 4.{Style.ENDC} Utilities")
    print(f"\n{Style.WARNING} 0.{Style.ENDC} Exit")
    print("\n" + "═" * 47)

def show_submenu(title: str, options: List[str], tip: str = ""):
    clear_screen()
    print(Style.CYAN + f"╔═══════════════════════════════════════════════╗")
    print(f"║ {title.upper():^45} ║")
    print(f"╚═══════════════════════════════════════════════╝" + Style.ENDC)
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")
    if tip:
        print(f"\n{Style.INFO}💡 Tip: {tip}{Style.ENDC}")
    print(f"\n{Style.WARNING} 0.{Style.ENDC} ← Kembali ke Main Menu")
    print("\n" + "═" * 47)

def handle_menu(title: str, actions: List[Any], options: List[str], tip: str = ""):
    action_map = {str(i): action for i, action in enumerate(actions, 1)}
    while True:
        show_submenu(title, options, tip)
        choice = input(f"Pilih menu (0-{len(options)}): ").strip()
        if choice == '0':
            break
        action = action_map.get(choice)
        if action:
            try:
                action()
            except Exception as e:
                print_error(f"Terjadi error tak terduga: {e}")
            press_enter_to_continue()
        else:
            print_warning("Pilihan tidak valid.")
            time.sleep(1)

def main():
    try:
        initialize_directories()
        check_dependencies()
        
        menu_definitions = {
            '1': (
                "📋 Setup & Konfigurasi",
                [
                    initialize_configuration,
                    import_api_keys,
                    show_api_keys_status,
                    import_github_tokens,
                    validate_github_tokens
                ],
                [
                    "Initialize Configuration",
                    "Import API Keys",
                    "Show API Keys Status",
                    "Import GitHub Tokens",
                    "Validate GitHub Tokens"
                ],
                "Jalankan Initialize Configuration terlebih dahulu"
            ),
            '2': (
                "🤝 Manajemen Kolaborasi",
                [
                    invoke_auto_invite,
                    invoke_auto_accept,
                    invoke_auto_fork,
                    invoke_auto_set_secrets
                ],
                [
                    "Auto Invite Collaborators",
                    "Auto Accept Invitations",
                    "Auto Fork Repository",
                    "Auto Set Secrets"
                ],
                "Jalankan secara berurutan dari atas ke bawah"
            ),
            '3': (
                "🚀 Deployment & Monitoring",
                [
                    deploy_to_github,
                    invoke_workflow_trigger,
                    show_workflow_status
                ],
                [
                    "Deploy to GitHub",
                    "Trigger Workflow",
                    "Show Workflow Status"
                ],
                "Deploy workflow sebelum trigger"
            ),
            '4': (
                "🔧 Utilities",
                [
                    view_logs,
                    clean_cache
                ],
                [
                    "View Logs",
                    "Clean Cache"
                ]
            )
        }
        
        while True:
            show_main_menu()
            choice = input("Pilih menu (0-4): ").strip()
            
            if choice == '0':
                print_success("\nTerima kasih! Program berhenti.")
                break
            
            if choice in menu_definitions:
                title, actions, options, *tip = menu_definitions[choice]
                handle_menu(title, actions, options, tip[0] if tip else "")
            else:
                print_warning("Pilihan tidak valid.")
                time.sleep(1)
    
    except KeyboardInterrupt:
        print_warning("\n\nProgram dihentikan oleh user.")
    except Exception as e:
        print_error(f"\n💥 Fatal error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
