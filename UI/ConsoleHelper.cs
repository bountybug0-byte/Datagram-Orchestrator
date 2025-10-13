using Spectre.Console;

namespace DatagramOrchestrator.UI;

public static class ConsoleHelper
{
    public static void ShowBanner()
    {
        Console.Clear();
        
        var gradient = new FigletText("DATAGRAM")
            .Color(Color.Cyan1);
        
        AnsiConsole.Write(gradient);
        
        var panel = new Panel(
            new Markup("[cyan bold]ORCHESTRATOR v3.2[/]\n" +
                      "[grey]Multi-Account Automation Toolkit[/]\n" +
                      "[dim]Powered by C# UI + Python Backend[/]")
        )
        {
            Border = BoxBorder.Double,
            BorderStyle = new Style(Color.Cyan1),
            Padding = new Padding(2, 1),
            Expand = false
        };
        
        AnsiConsole.Write(
            new Padder(panel)
                .PadLeft(2)
                .PadTop(0)
        );
        
        AnsiConsole.WriteLine();
    }
    
    public static void ShowExitMessage()
    {
        Console.Clear();
        
        var rule = new Rule("[cyan bold]✅ TERIMA KASIH![/]")
        {
            Style = Style.Parse("cyan dim"),
            Alignment = Justify.Center
        };
        AnsiConsole.Write(rule);
        
        var panel = new Panel(
            new Markup("[green]Datagram Orchestrator v3.2 - Stopped[/]\n\n" +
                      "[dim]Semua operasi telah selesai dengan aman.[/]\n" +
                      "[dim]Lihat logs di: logs/setup.log[/]")
        )
        {
            Border = BoxBorder.Rounded,
            BorderStyle = new Style(Color.Green),
            Padding = new Padding(3, 1),
            Expand = false
        };
        
        AnsiConsole.Write(
            new Padder(panel)
                .PadLeft(10)
                .PadTop(2)
        );
        
        AnsiConsole.WriteLine();
    }
    
    public static void PressEnterToContinue()
    {
        AnsiConsole.WriteLine();
        AnsiConsole.Markup("[dim]Tekan [cyan]Enter[/] untuk melanjutkan...[/]");
        Console.ReadLine();
    }
    
    public static void ShowError(string message)
    {
        var panel = new Panel($"[red bold]❌ ERROR[/]\n\n{message}")
        {
            Border = BoxBorder.Heavy,
            BorderStyle = new Style(Color.Red),
            Padding = new Padding(2, 1)
        };
        AnsiConsole.Write(panel);
    }
    
    public static void ShowSuccess(string message)
    {
        var panel = new Panel($"[green bold]✅ SUCCESS[/]\n\n{message}")
        {
            Border = BoxBorder.Rounded,
            BorderStyle = new Style(Color.Green),
            Padding = new Padding(2, 1)
        };
        AnsiConsole.Write(panel);
    }
    
    public static void ShowWarning(string message)
    {
        var panel = new Panel($"[yellow bold]⚠️  WARNING[/]\n\n{message}")
        {
            Border = BoxBorder.Rounded,
            BorderStyle = new Style(Color.Yellow),
            Padding = new Padding(2, 1)
        };
        AnsiConsole.Write(panel);
    }
    
    public static void ShowInfo(string message)
    {
        var panel = new Panel($"[cyan bold]ℹ️  INFO[/]\n\n{message}")
        {
            Border = BoxBorder.Rounded,
            BorderStyle = new Style(Color.Cyan1),
            Padding = new Padding(2, 1)
        };
        AnsiConsole.Write(panel);
    }
    
    public static async Task<string> PromptForFile(string title)
    {
        return await Task.Run(() =>
        {
            return AnsiConsole.Prompt(
                new TextPrompt<string>($"[cyan]{title}:[/]")
                    .Validate(path =>
                    {
                        if (string.IsNullOrWhiteSpace(path))
                            return ValidationResult.Error("[red]Path tidak boleh kosong[/]");
                        
                        if (!File.Exists(path))
                            return ValidationResult.Error("[red]File tidak ditemukan[/]");
                        
                        return ValidationResult.Success();
                    })
            );
        });
    }
    
    public static void DisplayProgressBar(string taskName, int total, Action<ProgressContext> action)
    {
        AnsiConsole.Progress()
            .AutoClear(false)
            .Columns(new ProgressColumn[]
            {
                new TaskDescriptionColumn(),
                new ProgressBarColumn(),
                new PercentageColumn(),
                new RemainingTimeColumn(),
                new SpinnerColumn(),
            })
            .Start(ctx =>
            {
                var task = ctx.AddTask($"[cyan]{taskName}[/]", maxValue: total);
                action(ctx);
            });
    }
    
    public static void DisplayTable(string title, Dictionary<string, string> data)
    {
        var table = new Table()
            .Border(TableBorder.Rounded)
            .BorderColor(Color.Cyan1)
            .Title($"[cyan bold]{title}[/]")
            .AddColumn(new TableColumn("[yellow]Key[/]").LeftAligned())
            .AddColumn(new TableColumn("[cyan]Value[/]").LeftAligned());
        
        foreach (var kvp in data)
        {
            table.AddRow(kvp.Key, kvp.Value);
        }
        
        AnsiConsole.Write(table);
    }
    
    public static void DisplayTree(string rootTitle, Dictionary<string, List<string>> treeData)
    {
        var tree = new Tree($"[cyan bold]{rootTitle}[/]");
        
        foreach (var branch in treeData)
        {
            var node = tree.AddNode($"[yellow]{branch.Key}[/]");
            foreach (var leaf in branch.Value)
            {
                node.AddNode($"[dim]{leaf}[/]");
            }
        }
        
        AnsiConsole.Write(tree);
    }
}
