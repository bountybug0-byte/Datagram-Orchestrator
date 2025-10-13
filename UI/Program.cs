using Spectre.Console;
using DatagramOrchestrator.UI;

namespace DatagramOrchestrator;

class Program
{
    static async Task Main(string[] args)
    {
        try
        {
            // Display banner
            ConsoleHelper.ShowBanner();
            
            // Check Python availability
            if (!await PythonBridge.CheckPythonInstallation())
            {
                AnsiConsole.MarkupLine("[red]❌ Python 3.8+ tidak ditemukan![/]");
                AnsiConsole.MarkupLine("[yellow]Install Python dari: https://python.org[/]");
                return;
            }
            
            // Check dependencies
            if (!await PythonBridge.CheckDependencies())
            {
                AnsiConsole.MarkupLine("[yellow]⚠️  Install dependencies: pip install -r requirements.txt[/]");
                if (!AnsiConsole.Confirm("Lanjutkan tanpa validasi dependencies?"))
                    return;
            }
            
            // Initialize directories
            await PythonBridge.InitializeDirectories();
            
            // Start menu system
            var menuSystem = new MenuSystem();
            await menuSystem.Run();
            
            // Exit message
            ConsoleHelper.ShowExitMessage();
        }
        catch (Exception ex)
        {
            AnsiConsole.WriteException(ex);
            AnsiConsole.MarkupLine($"\n[red]💥 Fatal Error: {ex.Message}[/]");
        }
    }
}
