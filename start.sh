#!/bin/bash
# File: start.sh
# Launcher untuk Datagram Orchestrator di Linux/macOS

# Pindah ke direktori skrip agar path relatif berfungsi
cd "$(dirname "$0")"

# Cek apakah Python terinstal
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 tidak ditemukan. Mohon install terlebih dahulu."
    exit 1
fi

# Cek apakah dependensi terinstal
python3 -c "import nacl" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Dependensi Python belum terinstal. Menjalankan instalasi..."
    python3 -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Gagal menginstal dependensi. Mohon install manual: pip install -r requirements.txt"
        exit 1
    fi
fi

# Jalankan skrip utama
echo "🚀 Memulai Datagram Orchestrator..."
python3 main.py
