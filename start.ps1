# File: start.ps1
# Launcher untuk Datagram Orchestrator di Windows

# Pindah ke direktori skrip
Set-Location -Path (Get-Item -Path $MyInvocation.MyCommand.Definition).Directory.FullName

# Cek apakah Python terinstal
try {
    $null = python --version
} catch {
    Write-Host "❌ Python tidak ditemukan. Mohon install terlebih dahulu." -ForegroundColor Red
    Read-Host "Tekan Enter untuk keluar"
    Exit
}

# Cek dependensi dan install jika perlu
$naclCheck = python -c "import nacl" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Dependensi Python belum terinstal. Menjalankan instalasi..." -ForegroundColor Yellow
    python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Gagal menginstal dependensi. Mohon install manual: pip install -r requirements.txt" -ForegroundColor Red
        Read-Host "Tekan Enter untuk keluar"
        Exit
    }
}

# Jalankan skrip utama
Write-Host "🚀 Memulai Datagram Orchestrator..." -ForegroundColor Cyan
python main.py
