using Spectre.Console;

namespace DatagramOrchestrator.UI;

public class MenuSystem
{
    private readonly PythonBridge _pythonBridge;
    
    public MenuSystem()
    {
        _pythonBridge = new PythonBridge();
    }
    
    public async Task Run()
    {
        while (true)
        {
            Console.Clear();
            
            var choice = ShowMainMenu();
            
            if (choice == "Exit")
                break;
            
            try
            {
                await HandleMainMenuChoice(choice);
            }
            catch (Exception ex)
            {
                AnsiConsole.MarkupLine($"[red]❌ Error: {ex.Message}[/]");
                AnsiConsole.MarkupLine("[yellow]Lihat logs/setup.log untuk detail[/]");
                ConsoleHelper.PressEnterToContinue();
            }
        }
    }
    
    private string ShowMainMenu()
    {
        ConsoleHelper.ShowBanner();
        
        var panel = new Panel(
            new Markup("[cyan]Pilih kategori menu yang ingin dijalankan[/]")
        )
        {
            Border = BoxBorder.Rounded,
            BorderStyle = new Style(Color.Cyan1),
            Padding = new Padding(2, 1)
        };
        AnsiConsole.Write(panel);
        
        var choice = AnsiConsole.Prompt(
            new SelectionPrompt<string>()
                .Title("\n[cyan bold]═══════════════ MAIN MENU ═══════════════[/]")
                .PageSize(10)
                .HighlightStyle(new Style(Color.Cyan1, decoration: Decoration.Bold))
                .AddChoices(new[]
                {
                    "📋 Setup & Konfigurasi",
                    "🤝 Manajemen Kolaborasi",
                    "🚀 Deployment & Monitoring",
                    "🔧 Utilities",
                    "Exit"
                })
        );
        
        return choice;
    }
    
    private async Task HandleMainMenuChoice(string choice)
    {
        switch (choice)
        {
            case "📋 Setup & Konfigurasi":
                await ShowSetupMenu();
                break;
            case "🤝 Manajemen Kolaborasi":
                await ShowCollaborationMenu();
                break;
            case "🚀 Deployment & Monitoring":
                await ShowDeploymentMenu();
                break;
            case "🔧 Utilities":
                await ShowUtilitiesMenu();
                break;
        }
    }
    
    private async Task ShowSetupMenu()
    {
        while (true)
        {
            Console.Clear();
            
            var panel = new Panel("[cyan bold]📋 SETUP & KONFIGURASI[/]")
            {
                Border = BoxBorder.Double,
                BorderStyle = new Style(Color.Cyan1)
            };
            AnsiConsole.Write(panel);
            
            var table = new Table()
                .Border(TableBorder.Rounded)
                .BorderColor(Color.Grey)
                .AddColumn(new TableColumn("[yellow]Kategori[/]").Centered())
                .AddColumn(new TableColumn("[cyan]Menu[/]").LeftAligned());
            
            table.AddRow("[yellow]API Keys[/]", "Initialize Configuration");
            table.AddRow("", "Import API Keys");
            table.AddRow("", "Show API Keys Status");
            table.AddEmptyRow();
            table.AddRow("[yellow]GitHub Tokens[/]", "Import GitHub Tokens");
            table.AddRow("", "Validate GitHub Tokens");
            
            AnsiConsole.Write(table);
            
            var choice = AnsiConsole.Prompt(
                new SelectionPrompt<string>()
                    .Title("\n[cyan]Pilih menu:[/]")
                    .PageSize(10)
                    .HighlightStyle(new Style(Color.Cyan1, decoration: Decoration.Bold))
                    .AddChoices(new[]
                    {
                        "1. Initialize Configuration",
                        "2. Import API Keys",
                        "3. Show API Keys Status",
                        "4. Import GitHub Tokens",
                        "5. Validate GitHub Tokens",
                        "← Kembali ke Main Menu"
                    })
            );
            
            if (choice.Contains("Kembali"))
                break;
            
            await ExecuteSetupChoice(choice);
        }
    }
    
    private async Task ExecuteSetupChoice(string choice)
    {
        await AnsiConsole.Status()
            .Spinner(Spinner.Known.Dots)
            .SpinnerStyle(Style.Parse("cyan bold"))
            .StartAsync("Menjalankan operasi...", async ctx =>
            {
                if (choice.Contains("1."))
                    await _pythonBridge.InitializeConfiguration();
                else if (choice.Contains("2."))
                    await _pythonBridge.ImportApiKeys();
                else if (choice.Contains("3."))
                    await _pythonBridge.ShowApiKeysStatus();
                else if (choice.Contains("4."))
                    await _pythonBridge.ImportGitHubTokens();
                else if (choice.Contains("5."))
                    await _pythonBridge.ValidateGitHubTokens();
            });
        
        ConsoleHelper.PressEnterToContinue();
    }
    
    private async Task ShowCollaborationMenu()
    {
        while (true)
        {
            Console.Clear();
            
            var panel = new Panel(
                new Markup("[cyan bold]🤝 MANAJEMEN KOLABORASI[/]\n\n" +
                          "[grey]💡 Tip: Jalankan secara berurutan (1 → 2 → 3)[/]")
            )
            {
                Border = BoxBorder.Double,
                BorderStyle = new Style(Color.Green)
            };
            AnsiConsole.Write(panel);
            
            var choice = AnsiConsole.Prompt(
                new SelectionPrompt<string>()
                    .Title("\n[green]Pilih menu:[/]")
                    .PageSize(10)
                    .HighlightStyle(new Style(Color.Green, decoration: Decoration.Bold))
                    .AddChoices(new[]
                    {
                        "1. Auto Invite Collaborators",
                        "2. Auto Accept Invitations",
                        "3. Auto Set Secrets (Actions + Codespaces)",
                        "← Kembali ke Main Menu"
                    })
            );
            
            if (choice.Contains("Kembali"))
                break;
            
            await ExecuteCollaborationChoice(choice);
        }
    }
    
    private async Task ExecuteCollaborationChoice(string choice)
    {
        await AnsiConsole.Status()
            .Spinner(Spinner.Known.Star)
            .SpinnerStyle(Style.Parse("green bold"))
            .StartAsync("Memproses...", async ctx =>
            {
                if (choice.Contains("1."))
                    await _pythonBridge.AutoInviteCollaborators();
                else if (choice.Contains("2."))
                    await _pythonBridge.AutoAcceptInvitations();
                else if (choice.Contains("3."))
                    await _pythonBridge.AutoSetSecrets();
            });
        
        ConsoleHelper.PressEnterToContinue();
    }
    
    private async Task ShowDeploymentMenu()
    {
        while (true)
        {
            Console.Clear();
            
            var panel = new Panel("[yellow bold]🚀 DEPLOYMENT & MONITORING[/]")
            {
                Border = BoxBorder.Double,
                BorderStyle = new Style(Color.Yellow)
            };
            AnsiConsole.Write(panel);
            
            var choice = AnsiConsole.Prompt(
                new SelectionPrompt<string>()
                    .Title("\n[yellow]Pilih menu:[/]")
                    .PageSize(10)
                    .HighlightStyle(new Style(Color.Yellow, decoration: Decoration.Bold))
                    .AddChoices(new[]
                    {
                        "1. Deploy to GitHub",
                        "2. Trigger Workflow",
                        "3. Show Workflow Status",
                        "← Kembali ke Main Menu"
                    })
            );
            
            if (choice.Contains("Kembali"))
                break;
            
            await ExecuteDeploymentChoice(choice);
        }
    }
    
    private async Task ExecuteDeploymentChoice(string choice)
    {
        await AnsiConsole.Status()
            .Spinner(Spinner.Known.Dots2)
            .SpinnerStyle(Style.Parse("yellow bold"))
            .StartAsync("Executing...", async ctx =>
            {
                if (choice.Contains("1."))
                    await _pythonBridge.DeployToGitHub();
                else if (choice.Contains("2."))
                    await _pythonBridge.TriggerWorkflow();
                else if (choice.Contains("3."))
                    await _pythonBridge.ShowWorkflowStatus();
            });
        
        ConsoleHelper.PressEnterToContinue();
    }
    
    private async Task ShowUtilitiesMenu()
    {
        while (true)
        {
            Console.Clear();
            
            var panel = new Panel("[blue bold]🔧 UTILITIES[/]")
            {
                Border = BoxBorder.Double,
                BorderStyle = new Style(Color.Blue)
            };
            AnsiConsole.Write(panel);
            
            var choice = AnsiConsole.Prompt(
                new SelectionPrompt<string>()
                    .Title("\n[blue]Pilih menu:[/]")
                    .PageSize(10)
                    .HighlightStyle(new Style(Color.Blue, decoration: Decoration.Bold))
                    .AddChoices(new[]
                    {
                        "1. View Logs",
                        "2. Clean Cache",
                        "← Kembali ke Main Menu"
                    })
            );
            
            if (choice.Contains("Kembali"))
                break;
            
            await ExecuteUtilityChoice(choice);
        }
    }
    
    private async Task ExecuteUtilityChoice(string choice)
    {
        if (choice.Contains("1."))
            await _pythonBridge.ViewLogs();
        else if (choice.Contains("2."))
            await _pythonBridge.CleanCache();
        
        ConsoleHelper.PressEnterToContinue();
    }
}
