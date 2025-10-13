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

def clear_screen():
    """Clear terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def show_main_menu():
    """Menampilkan menu utama program."""
    clear_screen()
    print(Style.CYAN + Style.BOLD + "╔═══════════════════════════════════════════════╗")
    print("║     DATAGRAM ORCHESTRATOR v3.2 (OPTIMIZED)   ║")
    print("╚═══════════════════════════════════════════════╝" + Style.ENDC)
    
    print(f"\n{Style.HEADER}═══════════════ MAIN MENU ═══════════════{Style.ENDC}\n")
    
    print(f"{Style.CYAN}  1.{Style.ENDC} 📋 Setup & Konfigurasi")
    print(f"{Style.CYAN}  2.{Style.ENDC} 🤝 Manajemen Kolaborasi")
    print(f"{Style.CYAN}  3.{Style.ENDC} 🚀 Deployment & Monitoring")
    print(f"{Style.CYAN}  4.{Style.ENDC} 🔧 Utilities")
    
    print(f"\n{Style.WARNING}  0.{Style.ENDC} Exit")
    print("\n" + "═" * 47)

def show_setup_menu():
    """Menampilkan sub-menu Setup & Konfigurasi."""
    clear_screen()
    print(Style.CYAN + "╔═══════════════════════════════════════════════╗")
    print("║         📋 SETUP & KONFIGURASI                ║")
    print("╚═══════════════════════════════════════════════╝" + Style.ENDC)
    
    print(f"\n{Style.WARNING}API Keys Management:{Style.ENDC}")
    print("  1. Initialize Configuration")
    print("  2. Import API Keys")
    print("  3. Show API Keys Status")
    
    print(f"\n{Style.WARNING}GitHub Tokens Management:{Style.ENDC}")
    print("  4. Import GitHub Tokens")
    print("  5. Validate GitHub Tokens")
    
    print(f"\n{Style.WARNING}  0.{Style.ENDC} ← Kembali ke Main Menu")
    print("\n" + "═" * 47)

def show_collaboration_menu():
    """Menampilkan sub-menu Manajemen Kolaborasi."""
    clear_screen()
    print(Style.CYAN + "╔═══════════════════════════════════════════════╗")
    print("║        🤝 MANAJEMEN KOLABORASI                ║")
    print("╚═══════════════════════════════════════════════╝" + Style.ENDC)
    
    print(f"\n{Style.WARNING}Collaboration Workflow:{Style.ENDC}")
    print("  1. Auto Invite Collaborators")
    print("  2. Auto Accept Invitations")
    print("  3. Auto Set Secrets (Actions + Codespaces)")
    
    print(f"\n{Style.INFO}💡 Tip: Jalankan secara berurutan (1 → 2 → 3){Style.ENDC}")
    
    print(f"\n{Style.WARNING}  0.{Style.ENDC} ← Kembali ke Main Menu")
    print("\n" + "═" * 47)

def show_deployment_menu():
    """Menampilkan sub-menu Deployment & Monitoring."""
    clear_screen()
    print(Style.CYAN + "╔═══════════════════════════════════════════════╗")
    print("║       🚀 DEPLOYMENT & MONITORING              ║")
    print("╚═══════════════════════════════════════════════╝" + Style.ENDC)
    
    print(f"\n{Style.WARNING}Deployment:{Style.ENDC}")
    print("  1. Deploy to GitHub")
    
    print(f"\n{Style.WARNING}Workflow Management:{Style.ENDC}")
    print("  2. Trigger Workflow")
    print("  3. Show Workflow Status")
    
    print(f"\n{Style.WARNING}  0.{Style.ENDC} ← Kembali ke Main Menu")
    print("\n" + "═" * 47)

def show_utilities_menu():
    """Menampilkan sub-menu Utilities."""
    clear_screen()
    print(Style.CYAN + "╔═══════════════════════════════════════════════╗")
    print("║              🔧 UTILITIES                     ║")
    print("╚═══════════════════════════════════════════════╝" + Style.ENDC)
    
    print(f"\n{Style.WARNING}Tools:{Style.ENDC}")
    print("  1. View Logs")
    print("  2. Clean Cache")
    
    print(f"\n{Style.WARNING}  0.{Style.ENDC} ← Kembali ke Main Menu")
    print("\n" + "═" * 47)

def handle_setup_menu():
    """Handler untuk sub-menu Setup & Konfigurasi."""
    setup_actions = {
        '1': initialize_configuration,
        '2': import_api_keys,
        '3': show_api_keys_status,
        '4': import_github_tokens,
        '5': validate_github_tokens,
    }
    
    while True:
        try:
            show_setup_menu()
            choice = input("Pilih menu (0-5): ").strip()
            
            if choice == '0':
                break
            
            action = setup_actions.get(choice)
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
                print_warning("Pilihan tidak valid. Silakan pilih 0-5.")
                time.sleep(1)
        
        except KeyboardInterrupt:
            print_warning("\n\nKembali ke menu utama...")
            time.sleep(1)
            break

def handle_collaboration_menu():
    """Handler untuk sub-menu Manajemen Kolaborasi."""
    collab_actions = {
        '1': invoke_auto_invite,
        '2': invoke_auto_accept,
        '3': invoke_auto_set_secrets,
    }
    
    while True:
        try:
            show_collaboration_menu()
            choice = input("Pilih menu (0-3): ").strip()
            
            if choice == '0':
                break
            
            action = collab_actions.get(choice)
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
                print_warning("Pilihan tidak valid. Silakan pilih 0-3.")
                time.sleep(1)
        
        except KeyboardInterrupt:
            print_warning("\n\nKembali ke menu utama...")
            time.sleep(1)
            break

def handle_deployment_menu():
    """Handler untuk sub-menu Deployment & Monitoring."""
    deploy_actions = {
        '1': deploy_to_github,
        '2': invoke_workflow_trigger,
        '3': show_workflow_status,
    }
    
    while True:
        try:
            show_deployment_menu()
            choice = input("Pilih menu (0-3): ").strip()
            
            if choice == '0':
                break
            
            action = deploy_actions.get(choice)
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
                print_warning("Pilihan tidak valid. Silakan pilih 0-3.")
                time.sleep(1)
        
        except KeyboardInterrupt:
            print_warning("\n\nKembali ke menu utama...")
            time.sleep(1)
            break

def handle_utilities_menu():
    """Handler untuk sub-menu Utilities."""
    util_actions = {
        '1': view_logs,
        '2': clean_cache,
    }
    
    while True:
        try:
            show_utilities_menu()
            choice = input("Pilih menu (0-2): ").strip()
            
            if choice == '0':
                break
            
            action = util_actions.get(choice)
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
                print_warning("Pilihan tidak valid. Silakan pilih 0-2.")
                time.sleep(1)
        
        except KeyboardInterrupt:
            print_warning("\n\nKembali ke menu utama...")
            time.sleep(1)
            break

def main():
    """Fungsi utama untuk menjalankan program."""
    try:
        # Initialize directories
        initialize_directories()
        
        # Check dependencies
        check_dependencies()
        
        # Main menu actions
        main_menu_actions = {
            '1': handle_setup_menu,
            '2': handle_collaboration_menu,
            '3': handle_deployment_menu,
            '4': handle_utilities_menu,
        }
        
        while True:
            try:
                show_main_menu()
                choice = input("Pilih menu (0-4): ").strip()
                
                if choice == '0':
                    clear_screen()
                    print(Style.GREEN + "╔═══════════════════════════════════════════════╗")
                    print("║         ✅ Terima Kasih!                      ║")
                    print("║   Datagram Orchestrator v3.2 - Stopped        ║")
                    print("╚═══════════════════════════════════════════════╝" + Style.ENDC)
                    break
                
                handler = main_menu_actions.get(choice)
                if handler:
                    handler()
                else:
                    print_warning("Pilihan tidak valid. Silakan pilih 0-4.")
                    time.sleep(1)
            
            except KeyboardInterrupt:
                print_warning("\n\nKembali ke menu utama...")
                time.sleep(1)
    
    except KeyboardInterrupt:
        clear_screen()
        print(Style.WARNING + "\n╔═══════════════════════════════════════════════╗")
        print("║     ⚠️  Program dihentikan oleh user          ║")
        print("╚═══════════════════════════════════════════════╝" + Style.ENDC)
        sys.exit(0)
    except Exception as e:
        print_error(f"\n💥 Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
