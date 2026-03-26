#!/bin/bash
# YURXZ Rejoin v9 — start.sh

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

RED='\033[0;31m'; YEL='\033[0;33m'; GRE='\033[0;32m'
CYA='\033[0;36m'; RES='\033[0m'; MGA='\033[0;35m'; GRY='\033[0;37m'

W=$(tput cols 2>/dev/null || echo 44)
[ "$W" -lt 30 ] && W=30
SEP=$(printf '=%.0s' $(seq 1 $W))
SEP2=$(printf '-%.0s' $(seq 1 $W))
pr() { printf "${2:-$RES}  %-$((W-2))s${RES}\n" "$1"; }

# ── Mode ──────────────────────────────────────────────
MODE="${1:-menu}"  # menu | auto | bot | all | stop

# ── Stop mode ─────────────────────────────────────────
if [ "$MODE" = "stop" ]; then
    clear
    echo -e "${CYA}${SEP}${RES}"
    pr "YURXZ Rejoin v9 -- Stopper" "$MGA"
    echo -e "${CYA}${SEP}${RES}"; echo ""
    pr "[*] Menghentikan semua proses..." "$YEL"
    pkill -f "main.py" 2>/dev/null
    pkill -f "bot.py"  2>/dev/null
    pkill -f "python3 main" 2>/dev/null
    pkill -f "python3 bot"  2>/dev/null
    rm -f "$DIR/rejoin.pid" "$DIR/bot.pid" 2>/dev/null
    command -v termux-wake-unlock &>/dev/null && termux-wake-unlock
    pr "[v] Semua proses dihentikan." "$GRE"
    echo ""; exit 0
fi

clear
echo -e "${CYA}${SEP}${RES}"
pr "YURXZ Rejoin v9  --  Launcher" "$MGA"
pr "by YURXZ" "$GRY"
echo -e "${CYA}${SEP2}${RES}"; echo ""

# ── Auto install dependencies ─────────────────────────
pr "[*] Cek & install dependencies..." "$YEL"
pkg update -y -q 2>/dev/null

install_if_missing() {
    if ! command -v "$1" &>/dev/null; then
        pr "  -> Install $2..." "$YEL"
        pkg install -y "$2" -q 2>/dev/null
    else
        pr "  v $1 sudah ada" "$GRE"
    fi
}
install_if_missing python3 python
install_if_missing pip3 python-pip
install_if_missing nano nano

for pkg_py in requests websocket-client; do
    if ! python3 -c "import ${pkg_py//-/_}" 2>/dev/null; then
        pr "  -> pip install $pkg_py..." "$YEL"
        pip3 install "$pkg_py" -q
    else
        pr "  v $pkg_py sudah ada" "$GRE"
    fi
done
echo ""; pr "[v] Dependencies OK" "$GRE"; echo ""

# ── Wakelock ──────────────────────────────────────────
pr "[*] Aktifkan wakelock..." "$YEL"
if command -v termux-wake-lock &>/dev/null; then
    termux-wake-lock &
    pr "  v wakelock aktif" "$GRE"
else
    pr "  ! termux-wake-lock tidak ada" "$YEL"
fi

# ── Buat stop.sh ─────────────────────────────────────
cat > "$DIR/stop.sh" << 'STOPEOF'
#!/bin/bash
bash "$(cd "$(dirname "$0")" && pwd)/start.sh" stop
STOPEOF
chmod +x "$DIR/stop.sh"
pr "[v] stop.sh dibuat" "$GRE"; echo ""

renice -5 $$ 2>/dev/null

# ── Cek root ─────────────────────────────────────────
pr "[*] Cek root..." "$YEL"
if su -c "id" &>/dev/null; then
    pr "  v Root tersedia" "$GRE"; echo ""
else
    pr "  x Root TIDAK tersedia!" "$RED"; echo ""; exit 1
fi

export TERM=xterm-256color
stty sane 2>/dev/null || true

# ── Jalankan sesuai mode ──────────────────────────────
echo -e "${CYA}${SEP}${RES}"

if [ "$MODE" = "bot" ]; then
    # Hanya bot
    pr "[*] Menjalankan Bot saja..." "$CYA"
    echo -e "${CYA}${SEP}${RES}"; echo ""
    while true; do
        python3 "$DIR/bot.py"
        EXIT=$?
        [ $EXIT -eq 0 ] || [ $EXIT -eq 130 ] && break
        pr "[!] Bot crash. Restart 10 detik..." "$RED"; sleep 10
    done

elif [ "$MODE" = "all" ] || [ "$MODE" = "auto" ]; then
    # Bot background + Rejoin foreground (menu tetap muncul)
    pr "[*] Menjalankan Bot (background) + Rejoin (foreground)..." "$CYA"
    echo -e "${CYA}${SEP}${RES}"; echo ""

    # Bot jalan di background
    if [ -f "$DIR/bot_config.json" ]; then
        # Matiin bot lama kalau ada
        pkill -f "bot.py" 2>/dev/null
        sleep 1
        pr "[*] Start bot di background..." "$YEL"
        nohup python3 "$DIR/bot.py" > "$DIR/bot.log" 2>&1 &
        echo $! > "$DIR/bot.pid"
        pr "  v Bot jalan di background (PID: $(cat $DIR/bot.pid))" "$GRE"
        pr "  v Log bot: $DIR/bot.log" "$GRY"
    else
        pr "  ! bot_config.json tidak ada" "$YEL"
        pr "    Setup bot: python3 bot.py setup" "$GRY"
    fi
    echo ""
    pr "[*] Menjalankan Rejoin di foreground..." "$CYA"
    echo -e "${CYA}${SEP}${RES}"; echo ""

    # Rejoin jalan foreground dengan menu (bisa dilihat + dikontrol)
    while true; do
        python3 "$DIR/main.py"
        EXIT=$?
        [ $EXIT -eq 0 ] || [ $EXIT -eq 130 ] && break
        pr "[!] Rejoin crash (code $EXIT). Restart 10 detik..." "$RED"; sleep 10
    done

else
    # Mode menu default — bot background, rejoin foreground
    pr "[*] Menjalankan menu..." "$CYA"
    echo -e "${CYA}${SEP}${RES}"; echo ""

    # Bot di background kalau config ada
    if [ -f "$DIR/bot_config.json" ]; then
        pkill -f "bot.py" 2>/dev/null
        sleep 1
        pr "[*] Start bot di background..." "$YEL"
        nohup python3 "$DIR/bot.py" > "$DIR/bot.log" 2>&1 &
        echo $! > "$DIR/bot.pid"
        pr "  v Bot jalan di background (PID: $(cat $DIR/bot.pid))" "$GRE"; echo ""
    fi

    # Rejoin foreground dengan menu
    while true; do
        python3 "$DIR/main.py"
        EXIT=$?
        [ $EXIT -eq 0 ] || [ $EXIT -eq 130 ] && break
        pr "[!] Crash (code $EXIT). Restart 10 detik..." "$RED"; sleep 10
    done
fi

command -v termux-wake-unlock &>/dev/null && termux-wake-unlock 2>/dev/null
