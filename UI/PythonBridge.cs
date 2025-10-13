using System.Diagnostics;
using System.Text;
using CliWrap;
using CliWrap.Buffered;
using Spectre.Console;

namespace DatagramOrchestrator.UI;

public class PythonBridge
{
    private readonly string _pythonExecutable;
    private readonly string _baseDirectory;
    
    public PythonBridge()
    {
        _baseDirectory = Directory.GetCurrentDirectory();
        _pythonExecutable = FindPythonExecutable();
    }
    
    private string FindPythonExecutable()
    {
        // Try python3 first (Unix), then python (Windows)
        var candidates = new[] { "python3", "python", "py" };
        
        foreach (var candidate in candidates)
        {
            try
            {
                var process = Process.Start(new ProcessStartInfo
                {
                    FileName = candidate,
                    Arguments = "--version",
                    RedirectStandardOutput = true,
                    UseShellExecute = false,
                    CreateNoWindow = true
                });
                
                if (process != null)
                {
                    process.WaitForExit();
                    if (process.ExitCode == 0)
                        return candidate;
                }
            }
            catch { }
        }
        
        return "python"; // Fallback
    }
    
    public static async Task<bool> CheckPythonInstallation()
    {
        try
        {
            var result = await Cli.Wrap("python")
                .WithArguments("--version")
                .WithValidation(CommandResultValidation.None)
                .ExecuteBufferedAsync();
            
            if (result.ExitCode == 0)
            {
                var version = result.StandardOutput.Trim();
                AnsiConsole.MarkupLine($"[green]✅ {version} detected[/]");
                return true;
            }
        }
        catch { }
        
        // Try python3
        try
        {
            var result = await Cli.Wrap("python3")
                .WithArguments("--version")
                .WithValidation(CommandResultValidation.None)
                .ExecuteBufferedAsync();
            
            if (result.ExitCode == 0)
            {
                var version = result.StandardOutput.Trim();
                AnsiConsole.MarkupLine($"[green]✅ {version} detected[/]");
                return true;
            }
        }
        catch { }
        
        return false;
    }
    
    public static async Task<bool> CheckDependencies()
    {
        try
        {
            var result = await Cli.Wrap("pip")
                .WithArguments("show PyNaCl")
                .WithValidation(CommandResultValidation.None)
                .ExecuteBufferedAsync();
            
            return result.ExitCode == 0;
        }
        catch
        {
            return false;
        }
    }
    
    public static async Task InitializeDirectories()
    {
        var dirs = new[] { "config", "config/.cache", "logs" };
        foreach (var dir in dirs)
        {
            Directory.CreateDirectory(dir);
        }
    }
    
    // ========================================
    // SETUP & KONFIGURASI METHODS
    // ========================================
    
    public async Task InitializeConfiguration()
    {
        AnsiConsole.Clear();
        var panel = new Panel("[cyan bold]1. INITIALIZE CONFIGURATION[/]")
        {
            Border = BoxBorder.Rounded,
            BorderStyle = new Style(Color.Cyan1)
        };
        AnsiConsole.Write(panel);
        
        var username = AnsiConsole.Ask<string>("\n[cyan]Username GitHub utama:[/]");
        var repoName = AnsiConsole.Ask<string>("[cyan]Nama repository:[/]");
        var token = AnsiConsole.Prompt(
            new TextPrompt<string>("[cyan]GitHub Personal Access Token:[/]")
                .Secret()
        );
        
        var script = $@"
import sys
sys.path.insert(0, '.')
from orchestrator.core import initialize_configuration
from orchestrator.helpers import save_json_file, CONFIG_FILE

config = {{
    'main_account_username': '{username}',
    'main_repo_name': '{repoName}',
    'main_token': '{token}'
}}
save_json_file(CONFIG_FILE, config)
print('SUCCESS: Configuration saved')
";
        
        await ExecutePythonScript(script);
    }
    
    public async Task ImportApiKeys()
    {
        AnsiConsole.Clear();
        var panel = new Panel("[cyan bold]2. IMPORT API KEYS[/]")
        {
            Border = BoxBorder.Rounded,
            BorderStyle = new Style(Color.Cyan1)
        };
        AnsiConsole.Write(panel);
        
        var choice = AnsiConsole.Prompt(
            new SelectionPrompt<string>()
                .Title("[cyan]Pilih metode import:[/]")
                .AddChoices(new[] { "1. Input manual", "2. Import dari file .txt" })
        );
        
        if (choice.Contains("1."))
        {
            await ImportApiKeysManual();
        }
        else
        {
            var filePath = AnsiConsole.Ask<string>("[cyan]Path ke file .txt:[/]");
            await ImportApiKeysFromFile(filePath);
        }
    }
    
    private async Task ImportApiKeysManual()
    {
        var keys = new List<string>();
        
        while (true)
        {
            var key = AnsiConsole.Ask<string>($"[cyan]API Key #{keys.Count + 1} (kosongkan untuk selesai):[/]");
            if (string.IsNullOrWhiteSpace(key))
                break;
            keys.Add(key);
        }
        
        if (keys.Count > 0)
        {
            var script = $@"
import sys
sys.path.insert(0, '.')
from orchestrator.helpers import API_KEYS_FILE
from pathlib import Path

keys = {string.Join(",", keys.Select(k => $"'{k}'"))}
API_KEYS_FILE.write_text('\n'.join([{string.Join(",", keys.Select(k => $"'{k}'"))}]), encoding='utf-8')
print(f'SUCCESS: Saved {{len([{string.Join(",", keys.Select(k => $"'{k}'"))}])}} API keys')
";
            await ExecutePythonScript(script);
        }
    }
    
    private async Task ImportApiKeysFromFile(string filePath)
    {
        var script = $@"
import sys
sys.path.insert(0, '.')
from orchestrator.core import import_api_keys
from orchestrator.helpers import API_KEYS_FILE
from pathlib import Path

source = Path('{filePath.Replace("\\", "\\\\")}')
if source.is_file():
    content = source.read_text(encoding='utf-8')
    API_KEYS_FILE.write_text(content, encoding='utf-8')
    count = len([l for l in content.splitlines() if l.strip()])
    print(f'SUCCESS: Imported {{count}} API keys')
else:
    print('ERROR: File not found')
";
        await ExecutePythonScript(script);
    }
    
    public async Task ShowApiKeysStatus()
    {
        var script = @"
import sys
sys.path.insert(0, '.')
from orchestrator.helpers import API_KEYS_FILE, read_file_lines

keys = read_file_lines(API_KEYS_FILE)
print(f'TOTAL: {len(keys)}')
for i, key in enumerate(keys[:3], 1):
    masked = f'{key[:8]}...{key[-6:]}' if len(key) > 14 else '***'
    print(f'KEY{i}: {masked}')
";
        var output = await ExecutePythonScript(script);
        DisplayApiKeysStatus(output);
    }
    
    private void DisplayApiKeysStatus(string output)
    {
        AnsiConsole.Clear();
        var panel = new Panel("[cyan bold]3. API KEYS STATUS[/]")
        {
            Border = BoxBorder.Rounded,
            BorderStyle = new Style(Color.Cyan1)
        };
        AnsiConsole.Write(panel);
        
        var lines = output.Split('\n', StringSplitOptions.RemoveEmptyEntries);
        var total = lines.FirstOrDefault(l => l.StartsWith("TOTAL:"))?.Split(':')[1].Trim() ?? "0";
        
        var table = new Table()
            .Border(TableBorder.Rounded)
            .AddColumn("[yellow]#[/]")
            .AddColumn("[cyan]API Key (Masked)[/]");
        
        foreach (var line in lines.Where(l => l.StartsWith("KEY")))
        {
            var parts = line.Split(':');
            table.AddRow(parts[0].Replace("KEY", ""), parts[1].Trim());
        }
        
        AnsiConsole.MarkupLine($"\n[green]Total API Keys:[/] [cyan bold]{total}[/]\n");
        AnsiConsole.Write(table);
    }
    
    public async Task ImportGitHubTokens()
    {
        AnsiConsole.Clear();
        var filePath = AnsiConsole.Ask<string>("[cyan]Path ke file .txt berisi tokens:[/]");
        
        var script = $@"
import sys
sys.path.insert(0, '.')
from orchestrator.core import import_github_tokens
from orchestrator.helpers import TOKENS_FILE
from pathlib import Path

source = Path('{filePath.Replace("\\", "\\\\")}')
if source.is_file():
    content = source.read_text(encoding='utf-8')
    tokens = [l.strip() for l in content.splitlines() if l.strip().startswith(('ghp_', 'github_pat_'))]
    if tokens:
        TOKENS_FILE.write_text('\n'.join(tokens), encoding='utf-8')
        print(f'SUCCESS: Imported {{len(tokens)}} tokens')
    else:
        print('ERROR: No valid tokens found')
else:
    print('ERROR: File not found')
";
        await ExecutePythonScript(script);
    }
    
    public async Task ValidateGitHubTokens()
    {
        var script = @"
import sys
sys.path.insert(0, '.')
from orchestrator.core import validate_github_tokens
validate_github_tokens()
";
        await ExecutePythonScriptWithLiveOutput(script);
    }
    
    // ========================================
    // MANAJEMEN KOLABORASI METHODS
    // ========================================
    
    public async Task AutoInviteCollaborators()
    {
        var script = @"
import sys
sys.path.insert(0, '.')
from orchestrator.core import invoke_auto_invite
invoke_auto_invite()
";
        await ExecutePythonScriptWithLiveOutput(script);
    }
    
    public async Task AutoAcceptInvitations()
    {
        var script = @"
import sys
sys.path.insert(0, '.')
from orchestrator.core import invoke_auto_accept
invoke_auto_accept()
";
        await ExecutePythonScriptWithLiveOutput(script);
    }
    
    public async Task AutoSetSecrets()
    {
        var script = @"
import sys
sys.path.insert(0, '.')
from orchestrator.core import invoke_auto_set_secrets
invoke_auto_set_secrets()
";
        await ExecutePythonScriptWithLiveOutput(script);
    }
    
    // ========================================
    // DEPLOYMENT & MONITORING METHODS
    // ========================================
    
    public async Task DeployToGitHub()
    {
        var script = @"
import sys
sys.path.insert(0, '.')
from orchestrator.core import deploy_to_github
deploy_to_github()
";
        await ExecutePythonScriptWithLiveOutput(script);
    }
    
    public async Task TriggerWorkflow()
    {
        var script = @"
import sys
sys.path.insert(0, '.')
from orchestrator.core import invoke_workflow_trigger
invoke_workflow_trigger()
";
        await ExecutePythonScriptWithLiveOutput(script);
    }
    
    public async Task ShowWorkflowStatus()
    {
        var script = @"
import sys
sys.path.insert(0, '.')
from orchestrator.core import show_workflow_status
show_workflow_status()
";
        await ExecutePythonScriptWithLiveOutput(script);
    }
    
    // ========================================
    // UTILITIES METHODS
    // ========================================
    
    public async Task ViewLogs()
    {
        var script = @"
import sys
sys.path.insert(0, '.')
from orchestrator.core import view_logs
view_logs()
";
        await ExecutePythonScriptWithLiveOutput(script);
    }
    
    public async Task CleanCache()
    {
        var confirmed = AnsiConsole.Confirm("[yellow]Hapus semua file cache?[/]");
        if (!confirmed)
        {
            AnsiConsole.MarkupLine("[yellow]Operasi dibatalkan.[/]");
            return;
        }
        
        var script = @"
import sys
sys.path.insert(0, '.')
from orchestrator.helpers import TOKEN_CACHE_FILE, INVITED_USERS_FILE, ACCEPTED_USERS_FILE, SECRETS_SET_FILE

files = [TOKEN_CACHE_FILE, INVITED_USERS_FILE, ACCEPTED_USERS_FILE, SECRETS_SET_FILE]
count = 0
for f in files:
    if f.exists():
        f.unlink()
        count += 1
        print(f'DELETED: {f.name}')
print(f'SUCCESS: Cleaned {count} cache files')
";
        await ExecutePythonScript(script);
    }
    
    // ========================================
    // HELPER METHODS
    // ========================================
    
    private async Task<string> ExecutePythonScript(string script)
    {
        try
        {
            var result = await Cli.Wrap(_pythonExecutable)
                .WithArguments("-c")
                .WithStandardInputPipe(PipeSource.FromString(script))
                .WithWorkingDirectory(_baseDirectory)
                .WithValidation(CommandResultValidation.None)
                .ExecuteBufferedAsync();
            
            var output = result.StandardOutput + result.StandardError;
            
            if (output.Contains("SUCCESS:"))
            {
                var message = output.Split("SUCCESS:")[1].Trim();
                AnsiConsole.MarkupLine($"[green]✅ {message}[/]");
            }
            else if (output.Contains("ERROR:"))
            {
                var message = output.Split("ERROR:")[1].Trim();
                AnsiConsole.MarkupLine($"[red]❌ {message}[/]");
            }
            
            return output;
        }
        catch (Exception ex)
        {
            AnsiConsole.MarkupLine($"[red]❌ Python execution failed: {ex.Message}[/]");
            return string.Empty;
        }
    }
    
    private async Task ExecutePythonScriptWithLiveOutput(string script)
    {
        try
        {
            await AnsiConsole.Status()
                .Spinner(Spinner.Known.Dots)
                .StartAsync("Processing...", async ctx =>
                {
                    var stdOutBuffer = new StringBuilder();
                    var stdErrBuffer = new StringBuilder();
                    
                    await Cli.Wrap(_pythonExecutable)
                        .WithArguments("-c")
                        .WithStandardInputPipe(PipeSource.FromString(script))
                        .WithWorkingDirectory(_baseDirectory)
                        .WithStandardOutputPipe(PipeTarget.ToDelegate(line =>
                        {
                            stdOutBuffer.AppendLine(line);
                            AnsiConsole.MarkupLine(line);
                        }))
                        .WithStandardErrorPipe(PipeTarget.ToDelegate(line =>
                        {
                            stdErrBuffer.AppendLine(line);
                            AnsiConsole.MarkupLine($"[yellow]{line}[/]");
                        }))
                        .WithValidation(CommandResultValidation.None)
                        .ExecuteAsync();
                });
        }
        catch (Exception ex)
        {
            AnsiConsole.MarkupLine($"[red]❌ Error: {ex.Message}[/]");
        }
    }
}
