#!/usr/bin/env python3
"""
+==========================================================+
|          YURXZ Rejoin  v9  —  main.py                  |
|          Android Rooted + Termux  |  by YURXZ          |
+==========================================================+
|  Deteksi (tanpa cookie):                               |
|    Level 1 → dumpsys activity  (Activity name)         |
|    Level 2 → network check     (koneksi aktif)         |
|    Level 3 → CPU usage         (app aktif)             |
|    Level 4 → pidof             (fallback universal)    |
+==========================================================+
|  --auto      : langsung mulai tanpa menu               |
|  --preventif : cek tiap 20 detik                       |
|  --low       : hemat RAM/CPU                           |
+==========================================================+
"""

import os, sys, json, subprocess, time, math, re, argparse

# --- PATH DATA -----------------------------------------------
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
LOG_FILE    = os.path.join(BASE_DIR, "activity.log")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
# -------------------------------------------------------------

# Global shared data for Bot (so it doesn't use status.json)
# Using a list of dicts that Bot can read directly if imported.
MONITOR_DATA = []
BOT_COMMAND  = None # To replace .bot_cmd file

# --- BRING TO FOREGROUND ---------------------------------------
def bring_to_foreground(pkg):
    """
    Bawa window Roblox ke foreground secara pasif.
    Cek dulu apa sudah di depan, biar gak ganggu executor.
    """
    try:
        # Cek apakah package target sudah ada di foreground (Resume Activity)
        ok, out = run_root("dumpsys activity top 2>/dev/null | grep mResumedActivity")
        if ok and pkg in out:
            return True # Sudah di depan, jangan am start lagi (cegah crash)
            
        # Jika belum, baru panggil am start
        run_root(f"am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -n {pkg}/com.roblox.client.ActivityProtocolLaunch 2>/dev/null; true")
        time.sleep(0.3)
        return True
    except:
        return False

def smart_tap_burst(pkg, x1, y1, x2, y2):
    """Tap burst 3x di tengah window Roblox. Bawa ke foreground dulu."""
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2

    # bring_to_foreground(pkg)  # TEST: Deactivated to stop crashes on some executors
    time.sleep(0.3) # Tunggu focus mantap

    # Burst tap 3x Center
    for _ in range(3):
        run_root(f"input tap {cx} {cy}")
        time.sleep(0.04)
    return cx, cy, "burst-center"

# --- ARGS --------------------------------------------------
parser = argparse.ArgumentParser()
parser.add_argument("--auto",      action="store_true")
parser.add_argument("--preventif", action="store_true")
parser.add_argument("--low",       action="store_true")
parser.add_argument("--packages",  help="Filter: package1,package2,...")
ARGS = parser.parse_args()

PID_FILE    = os.path.join(BASE_DIR, "rejoin.pid")

# --- WARNA -------------------------------------------------
R  = "\033[0m"
CY = "\033[96m"
GR = "\033[92m"
YE = "\033[93m"
RE = "\033[91m"
MG = "\033[95m"
GY = "\033[90m"
WH = "\033[97m"

# ==========================================================
#  HELPERS
# ==========================================================
def reset_terminal():
    """Reset terminal state supaya tidak rusak setelah keluar submenu."""
    try:
        os.system("stty sane 2>/dev/null")
        os.system("stty cols 80 rows 40 2>/dev/null || true")
    except:
        pass
    # clear whole screen and move to home
    sys.stdout.write("\033[0m\033[?7h\033[r\033[H\033[2J")
    sys.stdout.flush()

def clear():
    """Clear screen total (hanya panggil saat ganti menu)."""
    sys.stdout.write("\033[H\033[2J")
    sys.stdout.flush()

def move_home():
    """Pindah kursor ke (1,1) tanpa hapus layar (cegah flicker)."""
    sys.stdout.write("\033[H")
    sys.stdout.flush()

def run_root(cmd, timeout=15):
    try:
        r = subprocess.run(["su", "-c", cmd],
                           capture_output=True, text=True, timeout=timeout)
        out = (r.stdout or "") + "\n" + (r.stderr or "")
        return r.returncode == 0, out.strip()
    except Exception as e:
        return False, str(e)

def log(msg, lvl="INFO"):
    formatted = f"[{time.strftime('%d/%m %H:%M:%S')}][{lvl}] {msg}"
    try:
        with open(LOG_FILE, "a") as f:
            f.write(formatted + "\n")
    except:
        pass
    # Print to console only if it's a real terminal (Termux) AND not DEBUG
    if sys.stdout.isatty() and lvl != "DEBUG":
        sys.stdout.write(formatted + "\n")
        sys.stdout.flush()

def _open_tty():
    return None

def _read_input(tty_file, max_chars=2, timeout=60):
    return ""

def flush_stdin():
    """Buang sisa input di buffer."""
    try:
        import termios
        termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
    except:
        pass
    time.sleep(0.3)

def wait_enter(msg="  Tekan Enter untuk kembali ke menu"):
    """Tunggu input apapun yang paling stabil di Termux."""
    sys.stdout.write(f"\n{GY}{msg}: {R}")
    sys.stdout.flush()
    try:
        # Pake os.read untuk nangkep apapun yang masuk di FD 0 (stdin)
        # Akan return begitu user pencet tombol apapun.
        os.read(0, 1024)
    except:
        time.sleep(0.5)
    sys.stdout.write(f"  {GR}✓ OK{R}\r\n")
    sys.stdout.flush()

def inp(prompt, max_chars=2, timeout=60):
    """Input menu — flush stdin dulu, lalu baca via input()."""
    flush_stdin()
    try:
        return input(prompt).strip()
    except EOFError:
        return ""
    except KeyboardInterrupt:
        raise

def inp_text(prompt, timeout=120):
    """Input teks panjang."""
    flush_stdin()
    sys.stdout.write(prompt)
    sys.stdout.flush()
    try:
        line = sys.stdin.readline()
        return line.strip() if line else ""
    except EOFError:
        return ""
    except KeyboardInterrupt:
        raise

def pause_auto(detik=5):
    """Auto lanjut setelah beberapa detik."""
    for i in range(detik, 0, -1):
        sys.stdout.write(f"\r  \033[90mLanjut dalam {i}s...\033[0m  ")
        sys.stdout.flush()
        time.sleep(1)
    sys.stdout.write("\r" + " "*40 + "\r\n")
    sys.stdout.flush()



def get_memory():
    try:
        with open("/proc/meminfo") as f:
            c = f.read()
        mt = re.search(r"MemTotal:\s+(\d+)", c)
        ma = re.search(r"MemAvailable:\s+(\d+)", c) or re.search(r"MemFree:\s+(\d+)", c)
        if mt and ma:
            tot, av = int(mt.group(1)), int(ma.group(1))
            return f"{av//1024}MB", int(av/tot*100)
    except:
        pass
    return "N/A", 0

def check_root():
    try:
        r = subprocess.run(["su", "-c", "id"], capture_output=True, timeout=5)
        return r.returncode == 0
    except:
        return False

# ==========================================================
#  CONFIG
# ==========================================================
def load_cfg():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except:
            pass
    return {
        "packages": [],
        "ps_links": {},
        "check_interval": 35,
        "restart_delay": 10,
        "floating_window": True,
        "auto_mute": True,
        "auto_low_graphics": True,
        "auto_tap_splash": True,
        "load_delay": 40,
        "webhook_url": "",
    }

def save_cfg(cfg):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"{RE}Gagal simpan config: {e}{R}")

# ==========================================================
#  ROBLOX PACKAGE DETECTION — PURE DEVICE SCAN
# ==========================================================
def find_installed_pkgs():
    """
    Scan SEMUA package di device secara dinamis.
    Mendukung Roblox clone (clientw, clientx, dll.) dan Executor.
    """
    installed = []
    keywords = ["roblox", "delta", "fluxus", "arceus", "executor", "clien", "com.ro"]
    
    ok, out = run_root("pm list packages")
    if ok and out:
        for line in out.splitlines():
            pkg = line.replace("package:", "").strip()
            if any(k in pkg.lower() for k in keywords) and pkg not in installed:
                installed.append(pkg)

    return installed

def is_running(pkg):
    """
    Cek apakah package Roblox sedang BENAR-BENAR running.
    Delta Lite dan executor lain kadang meninggalkan ghost process
    di dumpsys meski sudah di-force close.
    Prioritaskan pidof + /proc/cmdline sebagai sumber kebenaran.
    """
    # Metode 1: pidof — paling akurat, tidak bisa ditipu ghost
    ok, out = run_root(f"pidof '{pkg}' 2>/dev/null")
    if ok and out.strip():
        # Validasi: pastikan /proc/{pid} benar-benar ada dan punya cmdline
        first_pid = out.strip().split()[0]
        ok2, cmdline = run_root(f"cat /proc/{first_pid}/cmdline 2>/dev/null | tr '\\0' ' '")
        if ok2 and pkg in (cmdline or ""):
            return True
        # pidof ada tapi /proc tidak ada = zombie/ghost, anggap mati
        return False

    # Metode 2: /proc scan — cari cmdline yang mengandung package name
    ok, out = run_root(f"grep -rl '{pkg}' /proc/*/cmdline 2>/dev/null | head -1")
    if ok and out.strip():
        return True

    # Metode 3: ps -ef (fallback)
    ok, out = run_root(f"ps -ef 2>/dev/null | grep '{pkg}' | grep -v grep")
    if ok and pkg in (out or ""):
        return True

    return False

# ==========================================================
#  PREMIUM DETECTION — COOKIE & PRESENCE API (via w.py)
# ==========================================================
def find_cookie_databases(pkg):
    base_path = f"/data/data/{pkg}"
    found_paths = []
    cmds = [
        f'find {base_path} -type f -name "Cookies" 2>/dev/null',
        f'find {base_path} -type f -name "cookies.sqlite" 2>/dev/null',
        f'find {base_path} -type f -name "*cookie*" 2>/dev/null'
    ]
    for cmd in cmds:
        ok, out = run_root(cmd)
        if ok and out.strip():
            for p in out.strip().split('\n'):
                p = p.strip()
                if p and p not in found_paths and not p.endswith('-journal'):
                    found_paths.append(p)
    return found_paths

def extract_cookie(db_path):
    temp_db = "/sdcard/temp_cookies_premium.db"
    run_root(f'cp "{db_path}" "{temp_db}" && chmod 666 "{temp_db}"')
    cookie = None
    try:
        import sqlite3
        conn = sqlite3.connect(temp_db)
        # Coba format Chromium (Chrome/Edge/Delta)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM cookies WHERE host_key LIKE '%roblox.com%' AND name = '.ROBLOSECURITY'")
            res = cursor.fetchone()
            if res: cookie = res[0]
            if not cookie:
                cursor.execute("SELECT value FROM cookies WHERE name = '.ROBLOSECURITY'")
                res = cursor.fetchone()
                if res: cookie = res[0]
        except:
            # Coba format Firefox
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM moz_cookies WHERE host LIKE '%roblox.com%' AND name = '.ROBLOSECURITY'")
                res = cursor.fetchone()
                if res: cookie = res[0]
            except: pass
        conn.close()
    except: pass
    run_root(f'rm "{temp_db}"')
    return cookie

def get_user_info(cookie):
    try:
        import requests as req
        r = req.get("https://users.roblox.com/v1/users/authenticated", 
                    cookies={".ROBLOSECURITY": cookie}, timeout=8)
        if r.status_code == 200:
            data = r.json()
            return data.get('id'), data.get('name')
    except: pass
    return None, None

def check_user_presence(uid, cookie):
    try:
        # Pastikan uid dikirim sebagai int
        try: uid = int(uid)
        except: pass
        
        import requests as req
        r = req.post("https://presence.roblox.com/v1/presence/users",
                    json={'userIds': [uid]},
                    cookies={".ROBLOSECURITY": cookie},
                    headers={'User-Agent': 'Mozilla/5.0'}, timeout=8)
        if r.status_code == 200 and r.json().get('userPresences'):
            resp_json = r.json()
            p = resp_json['userPresences'][0]
            st_type  = p.get('userPresenceType', 0)
            place_id = p.get('placeId')
            game_id  = p.get('gameId')
            
            # Detailed Logging: Show full API response as requested by user
            st_labels = {0: "Offline", 1: "Lobby", 2: "InGame", 3: "Studio", 4: "Basic"}
            label = st_labels.get(st_type, "Unknown")
            log(f"Presence API Full Result: {resp_json}", "DEBUG")
            log(f"Presence API: Type={st_type}({label}) Place={place_id} ID={str(game_id)[:8]}...", "DEBUG")
            
            return (st_type == 2), place_id, st_type, game_id
    except: pass
    return False, None, 0, None # Fallback: Assume NOT in-game on API error

def get_pid(pkg):
    ok, out = run_root(f"pidof {pkg}")
    return out.strip() if ok and out.strip() else None

# ==========================================================
#  SISTEM DETEKSI — 4 METODE + FALLBACK OTOMATIS
# ==========================================================
#  NETWORK CHECK (standalone wrapper)
# ==========================================================
def has_active_connection(pkg):
    """Cek network via package UID untuk deteksi ghost session."""
    try:
        # Dapatkan UID package
        ok, out = run_root(f"ls -ld /data/data/{pkg} 2>/dev/null | awk '{{print $3}}'")
        if not ok or not out.strip(): return False
        uid = out.strip()
        
        # Cek koneksi TCP aktif untuk UID tersebut
        ok2, out2 = run_root(f"cat /proc/net/tcp 2>/dev/null | grep -i ' {uid} ' || cat /proc/net/tcp6 2>/dev/null | grep -i ' {uid} '")
        return ok2 and len(out2.strip()) > 0
    except:
        return False

# ==========================================================
#  FREEZE DETECTION via CPU
# ==========================================================
def get_cpu_usage(pkg):
    ok, out = run_root(f"top -bn1 | grep {pkg}", timeout=10)
    if ok and out:
        for line in out.splitlines():
            if pkg in line:
                for part in line.split():
                    try:
                        v = float(part.replace('%', ''))
                        if 0 <= v <= 100:
                            return v
                    except:
                        pass
    return -1.0

def is_frozen(pkg):
    """
    Ambil 3 sample CPU tiap 3 detik.
    Rata-rata < 0.5% padahal app running = freeze.
    """
    samples = []
    for _ in range(3):
        v = get_cpu_usage(pkg)
        if v >= 0:
            samples.append(v)
        time.sleep(3)
    return bool(samples) and (sum(samples) / len(samples)) < 0.5

# ==========================================================
#  ROBLOX ACTIONS
# ==========================================================
def force_stop(pkg):
    run_root(f"am force-stop {pkg}")
    time.sleep(1)

def clear_cache_safe(pkg):
    """Clear cache AMAN — tidak hapus data login."""
    run_root(f"rm -rf /data/data/{pkg}/cache/")
    run_root(f"rm -rf /data/data/{pkg}/code_cache/")
    run_root(f"rm -rf /data/user/0/{pkg}/cache/*")

def protect_app(pkg=None):
    """
    Set oom_score_adj -1000 supaya sistem tidak kill process.
    Jika pkg=None, protect diri sendiri (Termux).
    """
    pids = []
    if pkg:
        ok, out = run_root(f"pidof {pkg}")
        if ok and out.strip():
            pids = out.strip().split()
    else:
        # Protect diri sendiri (Termux/Python)
        pids = [str(os.getpid())]

    for p in pids:
        run_root(f"echo -1000 > /proc/{p}/oom_score_adj")
        run_root(f"renice -n -20 -p {p}")

def mute_roblox(pkg=None):
    """Mute ONLY app-level volume (Roblox settings)."""
    if pkg:
        # Method 1: SharedPrefs XML (Fallback)
        pref = f"/data/data/{pkg}/shared_prefs"
        ok, files = run_root(f"ls {pref} 2>/dev/null")
        if ok:
            for fname in files.split():
                target = f"{pref}/{fname.strip()}"
                if target.endswith(".xml"):
                    run_root(f"sed -i 's/<int name=\"Volume\" value=\"[0-9]*\"/<int name=\"Volume\" value=\"0\"/g' {target}")
        
        # Method 2: Fast Flags (Primary)
        # Using DFIntGameVolume and FIntGameVolumePercent for total mute
        apply_fflags(pkg, {
            "DFIntGameVolume": 0,
            "FIntGameVolumePercent": 0
        })

def set_low_graphics(pkg):
    """
    Force Roblox to Manual Graphics Mode and Lowest Level (1).
    Modifies shared_prefs and uses Fast Flags for extra reliability.
    """
    # Method 1: SharedPrefs XML
    pref = f"/data/data/{pkg}/shared_prefs"
    ok, files = run_root(f"ls {pref} 2>/dev/null")
    if ok:
        for fname in files.split():
            target = f"{pref}/{fname.strip()}"
            if not target.endswith(".xml"):
                continue
            run_root(f"sed -i 's/<int name=\"GraphicsQualityLevel\" value=\"[0-9]*\"/<int name=\"GraphicsQualityLevel\" value=\"1\"/g' {target}")
            run_root(f"sed -i 's/<int name=\"SavedQualityLevel\" value=\"[0-9]*\"/<int name=\"SavedQualityLevel\" value=\"1\"/g' {target}")
            run_root(f"sed -i 's/<boolean name=\"AutoGraphicsQuality\" value=\"true\"/<boolean name=\"AutoGraphicsQuality\" value=\"false\"/g' {target}")
            run_root(f"sed -i 's/<int name=\"InAppGraphicsQuality\" value=\"[0-9]*\"/<int name=\"InAppGraphicsQuality\" value=\"1\"/g' {target}")

    # Method 2: Fast Flags (Primary)
    apply_fflags(pkg, {
        "FFlagAutoGraphicsQuality": "False",
        "FIntDebugForceInitializeGraphicsQualityLevel": 1,
        "FIntSavedGraphicsQualityLevel": 1,
        "FFlagDebugForceFullQuadsInEveryRoom": "False"
    })

def apply_fflags(pkg, new_flags):
    """Helper to merge and apply Fast Flags to ClientAppSettings.json"""
    path = f"/data/data/{pkg}/files/exe/ClientSettings"
    file = f"{path}/ClientAppSettings.json"
    
    # Ensure directory exists
    run_root(f"mkdir -p {path}")
    
    # Read existing flags
    ok, out = run_root(f"cat {file} 2>/dev/null")
    flags = {}
    if ok and out.strip():
        try:
            flags = json.loads(out)
        except:
            pass
            
    # Merge new flags
    flags.update(new_flags)
    
    # Write back to file
    json_str = json.dumps(flags).replace("'", "'\\''")
    run_root(f"echo '{json_str}' > {file}")
    run_root(f"chmod 777 {file}")

def get_resolution():
    ok, out = run_root("dumpsys window displays")
    if ok and out:
        m = re.search(r"cur=(\d+)x(\d+)", out)
        if m:
            return int(m.group(1)), int(m.group(2))
    ok, out = run_root("wm size")
    if ok and out:
        m = re.search(r"(\d+)x(\d+)", out)
        if m:
            return int(m.group(1)), int(m.group(2))
    return 1080, 2400

def grid_bounds(idx, total, sw, sh):
    cols = math.ceil(math.sqrt(total))
    rows = math.ceil(total / cols)
    cw, ch = sw // cols, sh // rows
    r = (idx - 1) // cols
    c = (idx - 1) % cols
    return f"{c*cw},{r*ch},{(c+1)*cw},{(r+1)*ch}"

def parse_launch_link(raw):
    """
    Format link:
    - Jika cuma angka -> jadikan roblox://placeId=...
    - Jika selain itu -> pakai apa adanya.
    """
    if not raw:
        return ""
    val = str(raw).strip()
    if val.isdigit():
        return f"roblox://placeId={val}"
    return val

def launch_game(ps_link, pkg, bounds=None):
    """
    Launch Roblox ke link secara DIRECT tanpa picker.
    Support Multi-Instance Android 12+ (Floating Window).
    """
    link   = parse_launch_link(ps_link)
    # extras: Using NEW_TASK | CLEAR_TOP flags for Android 12+ multi-window stability
    extras = f"-f 0x10008000 --windowingMode 5 --bounds {bounds}" if bounds else ""

    def try_launch(ex=""):
        # We add the -f flag inside the command to ensure separate tasks per package
        c = f'am start {ex} -n {pkg}/com.roblox.client.ActivityProtocolLaunch -a android.intent.action.VIEW -d "{link}"'
        ok, out = run_root(c)
        if ok and "Error:" not in out and "does not exist" not in out: 
            return True
        
        # Fallback to package-only if activity protocol mismatch (needed for some clones)
        c2 = f'am start {ex} -a android.intent.action.VIEW -d "{link}" -p {pkg}'
        ok2, out2 = run_root(c2)
        if ok2 and "Error:" not in out2 and "does not exist" not in out2: 
            return True
        return False

    # Try launching with floating mode + bounds
    if try_launch(extras): return True
    # If floating fails, fallback to standard mode but still unique task
    if try_launch("-f 0x10000000"): return True 
    return False

# ==========================================================
#  BANNER MENU
# ==========================================================
MENU_ITEMS = [
    ( "1",  "Start Auto Rejoin"),
    ( "2",  "Detect Packages Roblox"),
    ( "3",  "Set PS Link (Semua)"),
    ( "4",  "Set PS Link per Package"),
    ( "5",  "Clear Config"),
    ( "6",  "List Config"),
    ( "7",  "Setup Webhook"),
    ( "8",  "Set Interval"),
    ( "9",  "Toggle Floating Window"),
    ("10",  "Toggle Auto Mute"),
    ("11",  "Toggle Low Grafik"),
    ("12",  "Toggle Auto Tap Splash"),
    ("13",  "Set AutoExec Script"),
    ("14",  "Diagnostic"),
    ("15",  "Lihat Log"),
    ("16",  "Exit"),
]

def get_term_width():
    """Auto detect lebar terminal."""
    try:
        import shutil
        return shutil.get_terminal_size().columns
    except:
        pass
    try:
        cols = int(os.environ.get("COLUMNS", 0))
        if cols > 0:
            return cols
    except:
        pass
    return 44

def print_banner():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()
    mem, mpct = get_memory()
    cfg  = load_cfg()
    pkgs = cfg.get("packages", [])

    W  = max(30, get_term_width() - 1)
    c1 = int(W * 0.18)
    c2 = W - c1 - 3

    def sep(ch='-'):
        sys.stdout.write(f"{CY}+{ch*(c1+1)}+{ch*(c2+1)}+{R}\n")

    def row(t1, t2, c1v=None, c2v=None):
        _c1 = c1v or R
        _c2 = c2v or R
        sys.stdout.write(
            f"{CY}|{_c1} {str(t1):<{c1}} "
            f"{CY}|{_c2} {str(t2):<{c2}}{R} {CY}|{R}\n"
        )

    sys.stdout.write(f"\n{MG}  YURXZ Rejoin v9  |  No Cookie  |  by YURXZ{R}\n")
    sys.stdout.write(f"{GY}  RAM: {mem} ({mpct}%) | Packages: {len(pkgs)}{R}\n\n")

    sep('=')
    row("No", "Menu", YE, WH)
    sep('-')
    for num, label in MENU_ITEMS:
        row(num, label, YE, WH)
    sep('=')
    print()

# ==========================================================
#  DRAW UI MONITORING
# ==========================================================
def draw_ui(accounts, sys_status, prog="", nxt_wh=""):
    if not sys.stdout.isatty():
        return # Skip UI drawing if stdout is not a terminal

    # Gunakan move_home() biar dia overwrite Buffer lama, bukan clear -> write (flicker)
    move_home()
    
    # Map NL→CR+NL agar bare \n rapi di Termux
    try: os.system("stty onlcr 2>/dev/null")
    except: pass

    # Hitung RAM di tengah biar dapet stats fresh
    mem, mpct = get_memory()

    try:
        import shutil
        W = shutil.get_terminal_size().columns
    except:
        W = int(os.environ.get("COLUMNS", 44))
    W = max(28, W - 1)

    NL  = "\r\n"
    div = f"{CY}{'='*W}{R}"
    sep = f"{CY}{'-'*W}{R}"

    def trunc(s, n):
        s = str(s).replace('\n','').replace('\r','')
        s = s.encode('ascii', errors='replace').decode('ascii')
        return s[:n-1] + "." if len(s) > n else s

    st_txt = (prog + " " if prog else "") + (sys_status or "Idle")
    if nxt_wh: st_txt += f" | {nxt_wh}"

    mode = []
    if ARGS.preventif: mode.append("PREV")
    if ARGS.low:       mode.append("LOW")

    mtd_labels = {
        "activity":     "[A]",
        "network":      "[N]",
        "cpu":          "[C]",
        "pidof":        "[P]",
        "presence-api": "[API]",
    }

    # ── Header ────────────────────────────────────────────
    out  = div + NL
    out += trunc(f"{MG}YURXZ Rejoin v9  |  by YURXZ{R}", W) + NL
    out += sep + NL
    out += f"{YE}{trunc(st_txt, W)}{R}" + NL
    out += f"{GY}RAM: {mem} ({mpct}%){R}" + NL
    if mode:
        out += f"{GY}Mode: {' | '.join(mode)}{R}" + NL
    out += sep + NL

    # ── Package rows ──────────────────────────────────────
    for a in accounts:
        st  = a.get("status", "?")
        mtd = a.get("method", "auto")
        lbl = mtd_labels.get(mtd, "[?]")
        col = GR
        if any(x in st for x in ["Restart","Launch","Wait","Cache","Stop","Loading",
                                  "Cek","Detect","Tap","Inject","Click","Burst"]):
            col = YE
        elif any(x in st for x in ["Error","Failed","Crash","Freeze","mati","putus","Offline"]):
            col = RE
        elif any(x in st for x in ["Idle","Pending"]):
            col = GY

        pkg    = a.get('pkg', '?').replace('com.roblox.', 'rb.')
        uname  = a.get('username', 'Unknown')
        rejoin = a.get('rejoin_count', 0)

        header      = f"{lbl} {pkg} ({uname})"
        status_line = f"{trunc(st, W-6)} ({rejoin}x)"
        out += f"{CY}{trunc(header, W)}{R}" + NL
        out += f"{col}{status_line}{R}" + NL
        out += sep + NL

    # ── Footer ────────────────────────────────────────────
    out += div + NL
    out += f"{GY}[q]=stop{R}" + NL

    # Gunakan satu kali write buffer + flush
    sys.stdout.write(out + "\033[J") # [J untuk hapus sisa line lama
    sys.stdout.flush()

    # --- Update global MONITOR_DATA for direct Bot access (No status.json needed) ---
    try:
        global MONITOR_DATA
        MONITOR_DATA = [
            {
                "pkg":      a.get("pkg", "?"),
                "status":   a.get("status", "?"),
                "username": a.get("username", "Unknown"),
                "rejoin":   a.get("rejoin_count", 0),
                "method":   a.get("method", "auto")
            } for a in accounts
        ]
    except:
        pass



# ==========================================================
#  DETECTION HELPERS (FEATHERWEIGHT — No Libs)
# ==========================================================
def get_current_activity(pkg=None):
    """Ambil nama activity yang sedang fokus/top."""
    # Cara 1: ResumedActivity (Android 10+)
    cmd = "dumpsys activity top 2>/dev/null | grep mResumedActivity | head -1"
    ok, out = run_root(cmd)
    if ok and out:
        # Format: mResumedActivity: ActivityRecord{... pkg/activity t123}
        m = re.search(r'[\s/]([\w.]+)\b', out)
        if m: return m.group(1)

    # Cara 2: mCurrentFocus (Android 8-9)
    cmd = "dumpsys window windows 2>/dev/null | grep mCurrentFocus"
    ok, out = run_root(cmd)
    if ok and out:
        m = re.search(r'[\s/]([\w.]+)\b', out)
        if m: return m.group(1)

    return None

def is_in_game(pkg, cookie_info=None):
    """
    Improved detection: Cross-verify API with actual Window status.
    Return (bool, activity_name, method)
    """
    # 1. Cek Activity (Standard check)
    act = get_current_activity(pkg)
    if act:
        # Jika Activity adalah RobloxActivity/GameActivity, kita lanjut check
        if "RobloxActivity" in act or "GameActivity" in act:
            pass
        else:
            return False, act, "wrong-activity"

    # 2. Check Presence API (Metode Verification)
    if cookie_info:
        uid, cookie = cookie_info
        ingame, place, st_type, job = check_user_presence(uid, cookie)
        if ingame:
            # Re-verify one last time in case of invisible window names
            if st_type == 2:
                return True, f"Game({place})", "presence-api"
        
        if st_type in [0, 1]:
            return False, "Offline/Lobby", "presence-api"

    # 3. Check Network (Fallback)
    if has_active_connection(pkg):
        return True, "Network Active", "network"

    return False, act or "Unknown", "none"

# ==========================================================
#  MENU 1 — START AUTO REJOIN (tanpa cookie)
# ==========================================================
# --- REUSABLE HELPERS ---------------------------------------
def get_win_bounds(pkg, do_float, tot, sw, sh, index):
    """
    Deteksi bounds window Roblox aktual via dumpsys.
    Return (x1, y1, x2, y2) atau fallback ke grid/fullscreen.
    """
    ok, out = run_root(
        f"dumpsys window windows 2>/dev/null | grep -A10 '{pkg}' | grep 'Frame:'"
    )
    if ok and out.strip():
        m = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', out)
        if m:
            x1, y1 = int(m.group(1)), int(m.group(2))
            x2, y2 = int(m.group(3)), int(m.group(4))
            if x2 > x1 and y2 > y1:
                return x1, y1, x2, y2
    # Fallback ke grid
    if do_float and tot > 1:
        bounds_str = grid_bounds(index, tot, sw, sh)
        try:
            x1, y1, x2, y2 = map(int, bounds_str.split(","))
            return x1, y1, x2, y2
        except:
            pass
    return 0, 0, sw, sh

def do_smart_tap_wrapper(pkg, do_float, tot, sw, sh, index, label=""):
    """Tap tengah window Roblox. Bawa ke foreground dulu."""
    x1, y1, x2, y2 = get_win_bounds(pkg, do_float, tot, sw, sh, index)
    smart_tap_burst(pkg, x1, y1, x2, y2)
    return (x1+x2)//2, (y1+y2)//2, "burst-center"

def watch_package(a, cfg, accounts, sw, sh, tot, wh_url,
                  do_float, do_mute, do_lowgfx, interval, stop_event):
    """
    Worker thread — monitor satu package secara independen.
    """
    try: # Ensure thread-level safety
        _watch_package_logic(a, cfg, accounts, sw, sh, tot, wh_url,
                           do_float, do_mute, do_lowgfx, interval, stop_event)
    except Exception as e:
        log(f"CRITICAL: Watcher thread for {a.get('pkg')} DEAD: {e}", "ERROR")
        a["status"] = f"Thread Error ❌"

def _watch_package_logic(a, cfg, accounts, sw, sh, tot, wh_url,
                        do_float, do_mute, do_lowgfx, interval, stop_event):
    import threading

    pkg          = a["pkg"]
    link         = a["ps_link"]
    ae_script    = cfg.get("autoexec_script", "")
    ae_delay     = cfg.get("autoexec_delay", 30)
    auto_tap     = cfg.get("auto_tap_splash", True)
    tap_interval = cfg.get("tap_interval", 3)

    def do_smart_tap(label=""):
        tx, ty, reason = do_smart_tap_wrapper(pkg, do_float, tot, sw, sh, a["index"], label)
        a["status"] = f"Tap[{reason}] ({label})"
        return tx, ty, reason

    def do_rejoin(reason):
        """Rejoin package ini."""
        a["rejoin_count"] = a.get("rejoin_count", 0) + 1
        log(f"{pkg}: {reason} → Rejoin #{a['rejoin_count']}", "WARN")
        a["status"] = f"Disconnect: {reason}"

        if wh_url:
            _send_webhook_nocookie(wh_url, accounts,
                                   f"Disconnect: {pkg}", 15158332)

        # Hentikan proses dengan aman: force-stop dulu supaya Roblox bisa
        # flush session/state files ke disk, baru kill -9 sebagai fallback.
        a["status"] = "Stopping..."
        run_root(f"am force-stop {pkg} 2>/dev/null || true")
        time.sleep(1.5)

        # Kill -9 hanya jika proses masih ada (stuck / tidak mau mati)
        ok, pid = run_root(f"pidof '{pkg}' 2>/dev/null")
        if ok and pid.strip():
            log(f"{pkg}: force-stop tidak cukup, kill -9 fallback", "WARN")
            for p in pid.strip().split():
                run_root(f"kill -9 {p} 2>/dev/null")
            time.sleep(1.5)
        else:
            time.sleep(0.5)

        a["status"] = "Clear cache..."
        clear_cache_safe(pkg)
        time.sleep(1)

        a["status"] = "Relaunching..."
        bounds = grid_bounds(a["index"], tot, sw, sh) if do_float else None
        launch_game(link, pkg, bounds)
        a["launch_time"] = time.time()  # Reset grace period setiap rejoin
        time.sleep(5)

        if do_mute:   mute_roblox(pkg)
        if do_lowgfx: set_low_graphics(pkg)
        protect_app(pkg)

        # Auto tap + inject autoexec sampai in-game
        injected_ae  = False
        
        # --- NEW TIMER LOGIC (YURXZ v9.1.5) ---
        # Toggleable via auto_tap_splash (auto_tap variable)
        if auto_tap:
            l_delay = cfg.get("load_delay", 40)
            a["status"] = f"Wait {l_delay}s load..."
            log(f"{pkg}: Starting {l_delay}s load timer...", "INFO")
            
            for t in range(l_delay, 0, -1):
                if stop_event.is_set():
                    return

                a["status"] = f"Wait Load ({t}s)"
                # Log tiap 1 detik supaya kelihatan "tik-tik" di bot
                log(f"{pkg}: Loading... {t}s remaining", "INFO")

                # Tetap injek autoexec di tengah-tengah loading
                if ae_script and not injected_ae and t <= (l_delay // 2):
                    a["status"] = "Inject autoexec..."
                    inject_autoexec(pkg, ae_script)
                    injected_ae = True
                    
                time.sleep(1)

            # Final 3s countdown buat tap burst
            for t in range(3, 0, -1):
                a["status"] = f"Burst TAP in {t}s"
                if t == 3: log(f"{pkg}: Preparing tap burst in 3s...", "INFO")
                time.sleep(1)

            log(f"{pkg}: Tapping Skip Burst (3x Center)...", "INFO")
            do_smart_tap("Wait End")
            time.sleep(2)
        else:
            # Fast track: Inject AE immediately if timer is off
            if ae_script and not injected_ae:
                a["status"] = "Inject autoexec..."
                inject_autoexec(pkg, ae_script)
                injected_ae = True

        a["status"] = f"Running ✅ (rejoin #{a['rejoin_count']})"
        if wh_url:
            _send_webhook_nocookie(wh_url, accounts,
                                   f"✅ Rejoin OK: {pkg}", 3066993)

    # ── Main monitoring loop untuk package ini ─────────────
    while not stop_event.is_set():
        try:
            # ── GRACE PERIOD: Skip API check 120s setelah launch/rejoin ──
            # Presence API bisa sangat lambat (basi) saat baru launch.
            # Kita kasih nafas 120 detik agar API punya waktu update ke In-Game.
            launch_time = a.get("launch_time", 0)
            elapsed     = time.time() - launch_time
            # Only skip for grace period IF it's actually running. 
            # If not running, REJOIN IMMEDIATELY no matter what timer says.
            if elapsed < 30 and is_running(pkg):
                remaining = int(30 - elapsed)
                a["status"] = f"Loading... ({remaining}s)"
                log(f"[{pkg}] Grace period: {remaining}s sisa (skip API)", "INFO")
                # Sleep sebentar saja agar UI update lancar
                time.sleep(min(5, remaining + 1))
                continue

            # ── METODE: PRESENCE API (PRIMARY) ──
            if a.get("cookie_info"):
                uid, cookie = a["cookie_info"]
                api_ingame, api_place, p_type, api_job = check_user_presence(uid, cookie)
                
                a["method"] = "presence-api"
                
                # Validation logic
                target_place = None; is_ps = False
                ps_lnk_str = str(a.get("ps_link", ""))
                if "placeId=" in ps_lnk_str:
                    try: target_place = int(ps_lnk_str.split("placeId=")[1].split("&")[0])
                    except: pass
                if "roblox.com/share" in ps_lnk_str or "privateServerLinkCode" in ps_lnk_str:
                    is_ps = True
                
                ingame = api_ingame

                # ── GHOST DETECTION (DISABLED) ──
                # User requested to skip network check and just use Presence API.
                # if ingame:
                #     if not has_active_connection(pkg):
                #         log(f"[{pkg}] Ghost Session detected (API says InGame but No Network).", "WARN")
                #         ingame = False
                #         a["status"] = "Ghost Session 👻"

                if ingame and target_place and api_place and int(api_place) != target_place:
                    ingame = False
                    a["status"] = f"Wrong Game ({api_place})"
                
                # ── STRICT PRIVATE SERVER MODE ──
                if ingame and is_ps and api_job:
                    last_job = a.get("last_job_id")
                    if not last_job:
                        a["last_job_id"] = api_job
                        log(f"[{pkg}] Recorded PS Job ID: {api_job[:8]}...", "INFO")
                    elif last_job != api_job:
                        ingame = False
                        a["status"] = "Job Migration"
                        log(f"[{pkg}] Job migration: Rejoining PS...", "WARN")
                        a["last_job_id"] = None
                
                if not ingame:
                    reason = "Offline/Lobby"
                    if p_type == 1: reason = "Lobby/Menu"
                    if a.get("status") and any(x in a["status"] for x in ["Wrong", "Job", "Migration", "Ghost"]):
                        reason = a["status"]
                    
                    do_rejoin(reason)
                    a["last_job_id"] = None
                    continue
                else:
                    if not (a.get("status") and any(x in a["status"] for x in ["Wait", "Burst", "Tap"])):
                        a["status"] = "In-game ✅"
                    protect_app(pkg)
            else:
                a["status"] = "No Cookie - Standby"
                time.sleep(5)
                continue

            # ── LOGGING STATUS CHANGE ATAU PERIODIK 30S ──
            new_st = a.get("status", "?")
            last_log = a.get("last_log_time", 0)
            now = time.time()
            
            # Log jika: Status Berubah ATAU Sudah 30 detik (jika pakai API)
            if a.get("last_log_status") != new_st or (now - last_log > 30):
                st_labels = {0: "Offline", 1: "Online", 2: "InGame", 3: "Studio", 4: "Online"}
                p_str = st_labels.get(p_type, "Unknown") if p_type is not None else "N/A"
                
                # Tambah ID dan Nama supaya user bisa verifikasi akun
                u_id = a.get("cookie_info", [0])[0] if a.get("cookie_info") else "N/A"
                log(f"[{pkg}] User:{a.get('username','?')} (ID:{u_id}): {new_st} (API Type:{p_type})", "INFO")
                a["last_log_status"] = new_st
                a["last_log_time"]   = now

        except Exception as e:
            log(f"{pkg}: Error di watch_thread: {e}", "WARN")

        time.sleep(interval)

def menu_start_rejoin():
    global MONITOR_DATA, BOT_COMMAND
    if not check_root():
        print(f"{RE}Root access required!{R}")
        wait_enter(); return

    cfg  = load_cfg()
    pkgs = cfg.get("packages", [])
    
    # --- Filter by ARGS.packages (from Discord Bot Selective Launch) ---
    if ARGS.packages:
        targets = [p.strip() for p in ARGS.packages.split(",")]
        pkgs = [p for p in pkgs if p in targets]
        if not pkgs: pkgs = targets # Fallback use input directly

    # Auto detect kalau belum ada
    if not pkgs:
        print(f"{YE}Package belum diset, auto detecting...{R}")
        pkgs = find_installed_pkgs()
        if not pkgs:
            print(f"{RE}Tidak ada package Roblox ditemukan!{R}")
            wait_enter(); return
        cfg["packages"] = pkgs
        save_cfg(cfg)

    ps_links    = cfg.get("ps_links", {})
    global_link = cfg.get("global_ps_link", "")

    # Pastikan semua package punya PS link
    missing = [p for p in pkgs if not ps_links.get(p) and not global_link]
    if missing:
        print(f"{RE}PS Link belum diset untuk:{R}")
        for m in missing: print(f"  - {m}")
        print(f"{YE}Gunakan Menu 3 atau 4 untuk set PS Link.{R}")
        wait_enter(); return

    interval      = 20 if ARGS.preventif else cfg.get("check_interval", 35)
    restart_delay = 1 # Accelerated from 10
    do_float      = cfg.get("floating_window", True)
    do_mute       = cfg.get("auto_mute", True)
    do_lowgfx     = cfg.get("auto_low_graphics", True)
    do_tap        = cfg.get("auto_tap_splash", True)
    wh_url        = cfg.get("webhook_url", "")

    if ARGS.low:
        interval = max(interval, 50)

    sw, sh = get_resolution()
    tot    = len(pkgs)

    # Build daftar akun monitoring
    accounts = []
    for i, pkg in enumerate(pkgs):
        link = ps_links.get(pkg) or global_link
        
        # --- Auto Cookie Scan (Premium) ---
        cookie_info = None
        username = cfg.get("usernames", {}).get(pkg, "Unknown")
        for db in find_cookie_databases(pkg):
            raw = extract_cookie(db)
            if raw:
                uid, name = get_user_info(raw)
                if uid:
                    cookie_info = (uid, raw)
                    username = name; break
        
        if cookie_info:
            log(f"Detected: {pkg} -> User: {username}", "INFO")
        else:
            log(f"Detected: {pkg} -> User: Guest/Unknown", "INFO")

        accounts.append({
            "index":         i + 1,
            "pkg":           pkg,
            "ps_link":       link,
            "status":        "Pending",
            "freeze_count":  0,
            "rejoin_count":  0,
            "cookie_info":   cookie_info,
            "username":      username,
            "launch_time":   time.time(),  # Grace period tracker
        })

    # --- Initial Push of MONITOR_DATA for Discord Bot visibility ---
    try:
        MONITOR_DATA = [
            {
                "pkg":      x.get("pkg", "?"),
                "status":   "Initializing...",
                "username": x.get("username", "Unknown"),
                "rejoin":   0,
                "method":   "auto"
            } for x in accounts
        ]
    except:
        pass

    # Skip UI-heavy commands if in background to avoid hangs
    if sys.stdout.isatty():
        run_root("setenforce 0")
    else:
        # Background mode: move root check elsewhere or skip invasive commands
        pass

    # -- Launch awal semua package -------------------------
    for i, a in enumerate(accounts):
        pkg  = a["pkg"]
        link = a["ps_link"]

        # --- SMART START: Skip if already good ---
        already_good = False
        if a["cookie_info"]:
            uid, cookie = a["cookie_info"]
            ingame, _, _, _ = check_user_presence(uid, cookie)
            if ingame:
                log(f"{pkg}: Already In-Game (Presence API), skipping initial force-stop.", "INFO")
                already_good = True
        
        if not already_good and is_running(pkg):
            # If no cookie, we can only check if it's running.
            pass

        if already_good:
            a["status"] = "Running ✅ (Skipped Launch)"
            a["launch_time"] = time.time()
            continue

        a["status"] = "Force stop..."
        draw_ui(accounts, "Launching", f"[{i+1}/{tot}]")
        log(f"{pkg}: Force stopping... (Reason: Not detected In-Game)", "INFO")
        try:
            force_stop(pkg)
        except Exception as e:
            log(f"Force stop error {pkg}: {e}", "ERROR")

        a["status"] = "Clear cache..."
        draw_ui(accounts, "Launching", f"[{i+1}/{tot}]")
        log(f"{pkg}: Clearing cache...", "INFO")
        try:
            clear_cache_safe(pkg)
        except Exception as e:
            log(f"Clear cache error {pkg}: {e}", "ERROR")

        a["status"] = "Launching..."
        draw_ui(accounts, "Launching", f"[{i+1}/{tot}]")
        log(f"Launching {pkg}...", "INFO")
        bounds = grid_bounds(a["index"], tot, sw, sh) if do_float else None
        ok = launch_game(link, pkg, bounds)

        if ok:
            a["status"] = "Launched ✓"
            if do_mute:
                a["status"] = "Muting..."
                draw_ui(accounts, "Launching", f"[{i+1}/{tot}]")
                mute_roblox(pkg)
            if do_lowgfx:
                a["status"] = "Set low grafik..."
                draw_ui(accounts, "Launching", f"[{i+1}/{tot}]")
                set_low_graphics(pkg)
            # Inject AutoExec kalau ada script — dengan delay supaya game loading selesai
            ae_script = cfg.get("autoexec_script", "")
            ae_delay  = cfg.get("autoexec_delay", 30)  # default 30 detik
            if ae_script:
                # Inject file dulu sebelum delay (supaya executor baca saat load)
                a["status"] = "Inject autoexec..."
                draw_ui(accounts, "Launching", f"[{i+1}/{tot}]")
                ok_ae, _ = inject_autoexec(pkg, ae_script)
                log(f"AutoExec pre-inject {'OK' if ok_ae else 'GAGAL'} untuk {pkg}", "INFO")
            time.sleep(3)
            protect_app(pkg)
            log(f"Launch awal {pkg} → OK", "INFO")
        else:
            a["status"] = "Launch Failed ✗"
            log(f"Launch awal {pkg} → GAGAL", "WARN")

        if i < tot - 1:
            # Accelerated stagger for "no matter what" launch
            time.sleep(1)

    # Tunggu game load (YURXZ v9.1 — 40s wait + All-click skip)
    # Accelerated initial load wait
    for t in range(25, 0, -1):
        draw_ui(accounts, "Initializing", f"Wait Load {t}s")
        if t % 5 == 0: log(f"Global Wait: {t}s remaining...", "INFO")
        time.sleep(1)

    # Burst tap 1x semua package setelah load selesai (selalu, tanpa kondisi)
    for t in range(3, 0, -1):
        draw_ui(accounts, "Initializing", f"Burst Tap in {t}s")
        log(f"Burst Tap in {t}s...", "INFO")
        time.sleep(1)

    for a in accounts:
        a["status"] = "Click Skip..."
        pkg_short   = a['pkg'].replace('com.roblox.', 'rb.')
        draw_ui(accounts, "Initializing", f"Tap: {pkg_short}")
        log(f"Burst tap: {a['pkg']}", "INFO")
        do_smart_tap_wrapper(a["pkg"], do_float, tot, sw, sh, a["index"], "Initial")
        time.sleep(0.5)


    for a in accounts:
        a["status"]      = "Running ✅" if is_running(a["pkg"]) else "Not Running ⚠️"
        a["launch_time"] = time.time()  # Reset grace period untuk check pertama

    last_wh    = time.time()
    stop_event = __import__('threading').Event()

    # ── Jalankan thread per package ────────────────────────
    import threading
    threads = []
    for i_t, a in enumerate(accounts):
        t = threading.Thread(
            target=watch_package,
            args=(a, cfg, accounts, sw, sh, tot, wh_url,
                  do_float, do_mute, do_lowgfx, interval, stop_event),
            daemon=True
        )
        t.start()
        threads.append(t)
        log(f"Thread dimulai untuk {a['pkg']}", "INFO")
        # Delay antar thread supaya tidak bertabrakan
        if i_t < len(accounts) - 1:
            time.sleep(2)

    # ── Main loop — UI + webhook + baca command dari bot ───
    try:
        while True:
            nxt_wh = ""
            if wh_url:
                diff = int(600 - (time.time() - last_wh))
                if diff <= 0:
                    _send_webhook_nocookie(wh_url, accounts)
                    last_wh = time.time()
                    diff    = 600
                nxt_wh = f"WH {diff//60}m"

            draw_ui(accounts, "Monitoring", f"{tot} pkg aktif", nxt_wh)

            # --- Update global MONITOR_DATA for direct Bot access (Zero file latency) ---
            try:
                MONITOR_DATA = [
                    {
                        "pkg":      x.get("pkg", "?"),
                        "status":   x.get("status", "?"),
                        "username": x.get("username", "Unknown"),
                        "rejoin":   x.get("rejoin_count", 0),
                        "method":   x.get("method", "auto")
                    } for x in accounts
                ]
            except: pass
            # --- Check Bot Commands via Global Flag (Direct Memory) ---
            cmd_now = BOT_COMMAND
            if cmd_now:
                BOT_COMMAND = None
                if cmd_now == "stop":
                    log("Direct CMD: stop received", "INFO")
                    raise KeyboardInterrupt
                elif cmd_now == "start":
                    log("Direct CMD: start received while running, restarting sequence...", "INFO")
                    raise InterruptedError

            # Cek tombol q dengan timeout 1s agar loop tidak tight (mengurangi resiko force close)
            try:
                import select
                ready, _, _ = select.select([sys.stdin], [], [], 1)
                if ready:
                    ch = sys.stdin.readline().strip()
                    if isinstance(ch, bytes):
                        try: ch = ch.decode('utf-8', errors='ignore')
                        except: ch = ''
                    if ch.lower() in ('q', '\x03', '\x1b'):
                        if tty_q:
                            try: tty_q.close()
                            except: pass
                        raise KeyboardInterrupt
                if tty_q:
                    try: tty_q.close()
                    except: pass
            except KeyboardInterrupt:
                raise
            except:
                time.sleep(2)

    except InterruptedError:
        # Signal for restart (from bot start command)
        stop_event.set()
        print(f"\n{YE}[!] Restarting sequence per bot command...{R}")
        for t in threads:
            t.join(timeout=2)
        return "restart"

    except KeyboardInterrupt:
        stop_event.set()
        print(f"\n{YE}[!] Menghentikan semua thread...{R}")
        for t in threads:
            t.join(timeout=3)
        print(f"{YE}[!] Dihentikan.{R}\n")
        return "stop"

def _send_webhook_nocookie(url, accounts, title="📊 Status Update", color=3447003):
    try:
        import requests as req
    except:
        return
    fields = []
    for a in accounts:
        st = a.get("status","?")
        em = "🟢" if "Running" in st else ("🔴" if any(x in st for x in ["Error","Crash","Failed","mati","freeze"]) else "🟡")
        fields.append({
            "name":   f"{em} {a.get('pkg','?')}",
            "value":  f"**Status:** {st} | Rejoin: {a.get('rejoin_count',0)}x",
            "inline": False,
        })
    payload = {"embeds":[{
        "title": title, "color": color, "fields": fields,
        "footer": {"text": f"YURXZ v9 No-Cookie • {time.strftime('%d/%m/%Y %H:%M:%S')}"},
    }]}
    try:
        req.post(url, json=payload, timeout=10)
    except:
        pass

# ==========================================================
#  MENU 2 — DETECT & SET PACKAGES
# ==========================================================
def menu_detect_packages():
    cfg = load_cfg()
    print(f"\n{CY}[ Detect & Set Packages Roblox ]{R}")
    print(f"{YE}Scanning device...{R}\n")
    found = find_installed_pkgs()
    if not found:
        print(f"{RE}Tidak ada package Roblox ditemukan!{R}")
        pause_auto(10); return
    print(f"{GR}Package ditemukan:{R}")
    for p in found:
        ok, out = run_root(f"dumpsys package {p} | grep versionName")
        ver = out.strip().replace("versionName=","").strip() if ok and out.strip() else "?"
        print(f"  {GR}✓{R} {p}  {GY}(v{ver}){R}")
    cfg["packages"] = found
    save_cfg(cfg)
    print(f"\n{GR}✓ {len(found)} package tersimpan ke config!{R}")
    pause_auto(10)

# ==========================================================
#  MENU 3 — SET PS LINK / GAME ID (SEMUA PACKAGE)
# ==========================================================
def input_ps_link(title="Set PS Link / Game ID"):
    """
    Menu pilihan format PS Link — bisa pilih 1 atau lebih format.
    Return link yang sudah siap dipakai.
    """
    while True:
        print(f"\n{CY}[ {title} ]{R}")
        print(f"{GY}{'-'*get_term_width()}{R}")
        print(f"  {YE}1{R}. Game ID          contoh: {GR}995679412{R}")
        print(f"  {YE}2{R}. Roblox URI       contoh: {GR}roblox://placeId=995679412{R}")
        print(f"  {YE}3{R}. Link game Roblox contoh: {GR}https://www.roblox.com/games/995679412{R}")
        print(f"  {YE}4{R}. Private Server   contoh: {GR}https://www.roblox.com/games/...?privateServerLinkCode=xxx{R}")
        print(f"  {YE}5{R}. Batal")
        print(f"{GY}{'-'*get_term_width()}{R}")
        pilih = inp(f"{YE}Pilih format (1-5): {R}")

        if pilih == "5" or not pilih:
            return None

        if pilih == "1":
            val = inp_text(f"{YE}Masukkan Game ID (angka): {R}")
            if val and val.isdigit():
                link = f"roblox://placeId={val}"
                print(f"{GR}✓ Link: {link}{R}")
                return link
            else:
                print(f"{RE}Game ID harus angka!{R}")

        elif pilih == "2":
            val = inp_text(f"{YE}Masukkan Roblox URI (roblox://...): {R}")
            if val and val.startswith("roblox://"):
                print(f"{GR}✓ Link: {val}{R}")
                return val
            else:
                print(f"{RE}Harus diawali roblox://{R}")

        elif pilih == "3":
            val = inp_text(f"{YE}Masukkan link game Roblox: {R}")
            if val and "roblox.com/games" in val:
                link = parse_launch_link(val)
                print(f"{GR}✓ Link: {link}{R}")
                return link
            else:
                print(f"{RE}Link tidak valid!{R}")

        elif pilih == "4":
            val = inp_text(f"{YE}Paste Private Server link: {R}")
            if val and "privateServerLinkCode" in val:
                print(f"{GR}✓ Link: {val[:60]}...{R}")
                return val
            elif val and "roblox.com" in val:
                print(f"{GR}✓ Link: {val[:60]}{R}")
                return val
            else:
                print(f"{RE}Link tidak valid!{R}")
        else:
            print(f"{RE}Pilihan tidak valid!{R}")

        time.sleep(1)

def menu_set_global_ps():
    cfg = load_cfg()
    current = cfg.get("global_ps_link","")
    if current:
        print(f"\n{GY}PS Link saat ini: {current[:60]}{R}")

    link = input_ps_link("Set PS Link / Game ID untuk Semua Package")
    if not link:
        print(f"{YE}Dibatalkan.{R}")
        wait_enter()
        return

    cfg["global_ps_link"] = link
    pkgs     = cfg.get("packages", find_installed_pkgs())
    ps_links = cfg.get("ps_links", {})
    for pkg in pkgs:
        ps_links[pkg] = link
        print(f"  {GR}✓{R} {pkg}")
    cfg["ps_links"] = ps_links
    save_cfg(cfg)
    print(f"\n{GR}✓ Tersimpan untuk semua package!{R}")
    wait_enter()

# ==========================================================
#  MENU 4 — SET PS LINK PER PACKAGE
# ==========================================================
def menu_set_per_pkg_ps():
    cfg  = load_cfg()
    pkgs = cfg.get("packages", find_installed_pkgs())
    print(f"\n{CY}[ Set PS Link / Game ID per Package ]{R}")
    ps_links = cfg.get("ps_links", {})
    for pkg in pkgs:
        current = ps_links.get(pkg,"")
        print(f"\n{CY}>> Package: {pkg}{R}")
        if current:
            print(f"  {GY}Saat ini: {current[:55]}{R}")
        print(f"  {GY}(Enter skip = tidak diganti){R}")
        skip = inp(f"  {YE}Ganti PS Link untuk package ini? (y/n): {R}").lower()
        if skip != "y":
            print(f"  {GY}Dilewati.{R}")
            continue
        link = input_ps_link(f"PS Link untuk {pkg}")
        if link:
            parsed = parse_launch_link(link)
            print(f"  {GR}✓ Disimpan: {parsed[:50]}{R}")
            ps_links[pkg] = link
    cfg["ps_links"] = ps_links
    cfg["packages"] = pkgs
    save_cfg(cfg)
    print(f"\n{GR}✓ PS Link per-package tersimpan!{R}")
    wait_enter()

# ==========================================================
#  MENU 5 — CLEAR CONFIG
# ==========================================================
def menu_clear_config():
    cfg = load_cfg()
    print(f"\n{CY}[ Clear Config ]{R}")
    print("  1. Clear PS Links saja")
    print("  2. Clear Packages saja")
    print("  3. Clear semua (reset total)")
    print("  4. Batal")
    c = inp(f"{YE}Pilih: {R}")
    if c == "1":
        cfg["ps_links"] = {}; cfg["global_ps_link"] = ""
        save_cfg(cfg); print(f"{GR}✓ PS Links dihapus.{R}")
    elif c == "2":
        cfg["packages"] = []
        save_cfg(cfg); print(f"{GR}✓ Packages dihapus.{R}")
    elif c == "3":
        save_cfg({"packages":[],"ps_links":{},"check_interval":35,
                  "restart_delay":10,"floating_window":True,
                  "auto_mute":True,"auto_low_graphics":True,"webhook_url":""})
        print(f"{GR}✓ Config direset total.{R}")
    else:
        print(f"{YE}Dibatalkan.{R}")
    wait_enter()

# ==========================================================
#  MENU 6 — LIST CONFIG
# ==========================================================
def menu_list_config():
    cfg  = load_cfg()
    pkgs = cfg.get("packages", [])
    ae   = cfg.get("autoexec_script", "")
    wh   = cfg.get("webhook_url", "")

    def yn(key, default=True):
        return f"{GR}ON{R}" if cfg.get(key, default) else f"{RE}OFF{R}"

    def trunc(s, n=55):
        s = str(s)
        return s[:n] + "..." if len(s) > n else s

    def p(txt=""):
        sys.stdout.write(str(txt) + "\r\n")

    clear()
    # Ensure CR is mapped to LF (fix staircase on Termux)
    try:
        os.system("stty onlcr 2>/dev/null || true")
    except:
        pass

    W   = min(max(30, get_term_width() - 1), 70)
    div = f"{CY}{'='*W}{R}"
    sep = f"{CY}{'-'*W}{R}"

    p()
    p(f"{CY} LIST CONFIG {GY}|{R} {MG}YURXZ Rejoin v9{R}")
    p(div)

    # ── PACKAGES ──────────────────────────────────────────
    p()
    p(f"{YE} PACKAGES ({len(pkgs)}){R}")
    p(sep)

    if pkgs:
        for pkg in pkgs:
            ps  = cfg.get("ps_links", {}).get(pkg) or cfg.get("global_ps_link", "")
            ps  = trunc(ps) if ps else "(kosong)"
            p2  = pkg.replace("com.roblox.", "rb.")
            st  = f"{GR}Running{R}" if is_running(pkg) else f"{RE}Mati{R}"
            p(f" {GR}>{R} {WH}{p2}{R} [{st}]")
            p(f"   {GY}PS : {ps}{R}")
    else:
        p(f"  {GY}(tidak ada){R}")

    p(sep)

    # ── SETTINGS ──────────────────────────────────────────
    p()
    p(f"{YE} SETTINGS{R}")
    p(sep)

    rows = [
        ("Interval", f"{cfg.get('check_interval', 35)}s"),
        ("Delay",    f"{cfg.get('restart_delay', 10)}s"),
        ("Load Delay", f"{cfg.get('load_delay', 40)}s"),
        ("Floating", yn("floating_window")),
        ("Mute",     yn("auto_mute")),
        ("LowGfx",   yn("auto_low_graphics")),
        ("AutoTap",  yn("auto_tap_splash")),
        ("AE Delay", f"{cfg.get('autoexec_delay', 30)}s"),
        ("AutoExec", f"{GR}Ada{R}" if ae else f"{GY}Kosong{R}"),
        ("Webhook",  f"{GR}Ada{R}" if wh else f"{GY}Kosong{R}"),
    ]

    key_w = max(len(k) for k, _ in rows)
    for key, val in rows:
        p(f"  {YE}{key:<{key_w}}{R} : {val}")

    p(div)
    sys.stdout.flush()
    wait_enter()

# ==========================================================
#  MENU 7 — SETUP WEBHOOK
# ==========================================================
def menu_setup_webhook():
    cfg = load_cfg()
    print(f"\n{CY}[ Setup Webhook Discord ]{R}")
    current = cfg.get("webhook_url","")
    print(f"{GY}Webhook saat ini: {current[:60] or '(kosong)'}{R}")
    url = inp_text(f"{YE}Masukkan Discord Webhook URL (Enter hapus): {R}")
    cfg["webhook_url"] = url
    save_cfg(cfg)
    if url:
        print(f"{GR}✓ Webhook disimpan!{R}")
        test = inp(f"{YE}Kirim test? (y/n): {R}").lower()
        if test == "y":
            _send_webhook_nocookie(url, [], "🔔 YURXZ Test", 3447003)
            print(f"{GR}✓ Test terkirim!{R}")
    else:
        print(f"{YE}Webhook dihapus.{R}")
    wait_enter()

# ==========================================================
#  MENU 8 — SET INTERVAL
# ==========================================================
def menu_set_interval():
    cfg = load_cfg()
    print(f"\n{CY}[ Set Interval Cek ]{R}")
    print(f"{GY}Interval saat ini: {cfg.get('check_interval',35)}s{R}")
    print(f"{GY}Restart delay saat ini: {cfg.get('restart_delay',10)}s{R}")
    val = inp_text(f"{YE}Interval cek (detik) [Enter skip]: {R}")
    if val.isdigit(): cfg["check_interval"] = int(val)
    val2 = inp_text(f"{YE}Restart delay (detik) [Enter skip]: {R}")
    if val2.isdigit(): cfg["restart_delay"] = int(val2)
    val3 = inp_text(f"{YE}Load delay (detik) [Enter skip]: {R}")
    if val3.isdigit(): cfg["load_delay"] = int(val3)
    save_cfg(cfg)
    print(f"{GR}✓ Tersimpan!{R}")
    wait_enter()

# ==========================================================
#  MENU 9, 10, 11 — TOGGLE
# ==========================================================
def menu_toggle(key, label):
    cfg = load_cfg()
    current = cfg.get(key, True)
    status_now = f"{GR}ON{R}" if current else f"{RE}OFF{R}"
    print(f"\n{CY}[ {label} ]{R}")
    print(f"{GY}Status sekarang: {status_now}{R}")
    print(f"\n  1. ON")
    print(f"  2. OFF")
    print(f"  3. Batal")
    c = inp(f"\n{YE}Pilih: {R}")
    if c == "1":
        cfg[key] = True
        save_cfg(cfg)
        print(f"\n{GR}✓ {label}: ON{R}")
    elif c == "2":
        cfg[key] = False
        save_cfg(cfg)
        print(f"\n{RE}✓ {label}: OFF{R}")
    else:
        print(f"\n{YE}Dibatalkan.{R}")
    wait_enter()

# ==========================================================
#  MENU 12 — LIHAT LOG
# ==========================================================
def inject_autoexec(pkg, script):
    """
    Inject script Lua ke semua executor yang ada di device.
    Cara kerja:
    1. Scan semua subfolder di dalam package files
    2. Cari folder yang ada 'autoexec' di dalamnya
    3. Inject ke sana + path generic fallback
    Jadi support semua executor termasuk lite/clone/modded.
    """
    base_data   = f"/data/data/{pkg}/files"
    base_sdcard = f"/sdcard/Android/data/{pkg}/files"
    escaped     = script.replace("'", "'\\''")
    paths       = []
    injected    = []

    # ── STEP 1: Scan dinamis semua subfolder executor ──────
    for base in [base_data, base_sdcard]:
        # List semua subfolder di base
        ok, out = run_root(f"ls '{base}' 2>/dev/null")
        if ok and out.strip():
            for folder_name in out.split():
                folder_name = folder_name.strip()
                if not folder_name:
                    continue
                sub = f"{base}/{folder_name}"
                # Cek apakah ada folder autoexec di dalamnya
                ok2, out2 = run_root(f"ls '{sub}' 2>/dev/null")
                if ok2 and out2:
                    items = out2.split()
                    if "autoexec" in items:
                        # Ada folder autoexec → inject ke sana
                        paths.append(f"{sub}/autoexec/autoexec.lua")
                    if "workspace" in items:
                        # Ada folder workspace → inject ke sana juga
                        paths.append(f"{sub}/workspace/autoexec.lua")
                    # Cek file autoexec.lua langsung di subfolder
                    if "autoexec.lua" in items:
                        paths.append(f"{sub}/autoexec.lua")

    # ── STEP 2: Path generic / fallback ───────────────────
    for base in [base_data, base_sdcard]:
        paths += [
            f"{base}/autoexec.lua",
            f"{base}/autoexec/autoexec.lua",
            f"{base}/workspace/autoexec.lua",
        ]

    # ── STEP 3: Dedupe ────────────────────────────────────
    paths = list(dict.fromkeys(paths))

    # ── STEP 4: Inject ke semua path ──────────────────────
    for path in paths:
        folder = "/".join(path.split("/")[:-1])
        run_root(f"mkdir -p '{folder}' 2>/dev/null")
        ok, _ = run_root(f"printf '%s' '{escaped}' > '{path}' && chmod 666 '{path}'")
        if ok:
            injected.append(path)
            log(f"AutoExec OK: {path}", "INFO")

    log(f"AutoExec inject {len(injected)}/{len(paths)} path berhasil untuk {pkg}", "INFO")
    return len(injected) > 0, injected

def menu_autoexec():
    cfg = load_cfg()
    current   = cfg.get("autoexec_script", "")
    ae_delay  = cfg.get("autoexec_delay", 30)

    print(f"\n{CY}[ Set AutoExec Script ]{R}")
    print(f"{GY}{'-'*get_term_width()}{R}")

    if current:
        preview = current[:80] + "..." if len(current) > 80 else current
        print(f"{GY}Script: {preview}{R}")
    else:
        print(f"{GY}Script: (belum ada){R}")
    print(f"{GY}Delay inject: {ae_delay} detik setelah launch{R}")
    print()

    print(f"  {YE}1{R}. Input script baru")
    print(f"  {YE}2{R}. Load dari file (/sdcard/Download/autoexec.lua)")
    print(f"  {YE}3{R}. Test inject ke package sekarang")
    print(f"  {YE}4{R}. Set delay inject (detik setelah launch)")
    print(f"  {YE}5{R}. Hapus AutoExec")
    print(f"  {YE}6{R}. Lihat script saat ini")
    print(f"  {YE}7{R}. Batal")
    print(f"{GY}{'-'*get_term_width()}{R}")

    c = inp(f"{YE}Pilih: {R}")

    if c == "1":
        print(f"\n{GY}Paste script Lua kamu.")
        print(f"Ketik END di baris baru untuk selesai:{R}")
        lines = []
        while True:
            try:
                line = input()
                if line.strip() == "END":
                    break
                lines.append(line)
            except EOFError:
                break
        script = "\n".join(lines).strip()
        if script:
            cfg["autoexec_script"] = script
            save_cfg(cfg)
            print(f"\n{GR}✓ Script disimpan! ({len(lines)} baris){R}")
        else:
            print(f"{RE}Script kosong!{R}")

    elif c == "2":
        path = "/sdcard/Download/autoexec.lua"
        ok, out = run_root(f"cat {path} 2>/dev/null")
        if ok and out.strip():
            cfg["autoexec_script"] = out.strip()
            save_cfg(cfg)
            lines = out.strip().split('\n')
            print(f"\n{GR}✓ Script dimuat dari {path}! ({len(lines)} baris){R}")
        else:
            print(f"{RE}File tidak ditemukan atau kosong!{R}")
            print(f"{GY}Buat file: /sdcard/Download/autoexec.lua{R}")

    elif c == "3":
        script = cfg.get("autoexec_script", "")
        if not script:
            print(f"{RE}Belum ada script! Set dulu dengan pilihan 1 atau 2.{R}")
        else:
            pkgs = cfg.get("packages", find_installed_pkgs())
            if not pkgs:
                print(f"{RE}Tidak ada package!{R}")
            else:
                print(f"\n{YE}Inject ke:{R}")
                for pkg in pkgs:
                    ok, injected = inject_autoexec(pkg, script)
                    status = f"{GR}✓ {len(injected)} path{R}" if ok else f"{RE}✗ Gagal{R}"
                    print(f"  {pkg}: {status}")
                    if ok and injected:
                        # Tampilkan beberapa path yang berhasil
                        for p in injected[:3]:
                            executor = p.split("/files/")[-1].split("/")[0] if "/files/" in p else "generic"
                            print(f"    {GY}-> {executor}: {p.split('/')[-1]}{R}")
                        if len(injected) > 3:
                            print(f"    {GY}... dan {len(injected)-3} path lainnya{R}")
                print(f"\n{GR}✓ Inject selesai!{R}")

    elif c == "4":
        print(f"\n{GY}Delay inject saat ini: {ae_delay} detik{R}")
        print(f"{GY}Rekomendasi: 20-40 detik (tunggu loading game selesai){R}")
        print(f"{GY}Untuk Fisch/game loading lama: 30-45 detik{R}")
        val = inp_text(f"{YE}Masukkan delay (detik): {R}")
        if val.isdigit():
            cfg["autoexec_delay"] = int(val)
            save_cfg(cfg)
            print(f"\n{GR}✓ Delay diset ke {val} detik{R}")
        else:
            print(f"{RE}Harus angka!{R}")

    elif c == "5":
        cfg["autoexec_script"] = ""
        save_cfg(cfg)
        print(f"\n{YE}AutoExec dihapus.{R}")

    elif c == "6":
        script = cfg.get("autoexec_script", "")
        if script:
            print(f"\n{GY}Script ({len(script.split(chr(10)))} baris):{R}")
            print(f"{WH}{script}{R}")
        else:
            print(f"{YE}Belum ada script.{R}")

    else:
        print(f"{YE}Dibatalkan.{R}")

    wait_enter()

def menu_lihat_log():
    print(f"\n{CY}[ Log Aktivitas (50 baris terakhir) ]{R}\n")
    log_path = LOG_FILE
    ok, out = run_root(f"tail -50 {log_path} 2>/dev/null")
    if ok and out:
        print(out)
    else:
        print(f"{GY}Log kosong atau belum ada.{R}")
    wait_enter()

# ==========================================================
#  MENU 12 — DIAGNOSTIC (TEST DETEKSI HP INI)
# ==========================================================
def menu_diagnostic():
    clear()
    print(f"\n{CY}+{'='*get_term_width()}+{R}")
    print(f"{CY}|{MG}   DIAGNOSTIC — Test Kompatibilitas HP Ini       {CY}|{R}")
    print(f"{CY}+{'='*get_term_width()}+{R}\n")

    def ok_str(v): return f"{GR}✅ WORK{R}" if v else f"{RE}❌ TIDAK WORK{R}"

    # -- Test 1: Root -------------------------------------
    print(f"{YE}[1] Root Access...{R}")
    root_ok = check_root()
    print(f"    {ok_str(root_ok)}")
    if not root_ok:
        print(f"{RE}    Root tidak ada! Semua test dibatalkan.{R}")
        wait_enter(); return

    # -- Test 2: pidof ------------------------------------
    print(f"\n{YE}[2] Command pidof...{R}")
    ok, out = run_root("pidof init 2>/dev/null || pidof systemd 2>/dev/null")
    pidof_ok = ok
    print(f"    {ok_str(pidof_ok)}")

    # -- Test 3: pm list packages -------------------------
    print(f"\n{YE}[3] Package scan (pm list packages)...{R}")
    ok, out = run_root("pm list packages 2>/dev/null | head -3")
    pm_ok = ok and bool(out.strip())
    print(f"    {ok_str(pm_ok)}")
    if pm_ok:
        pkgs = find_installed_pkgs()
        if pkgs:
            print(f"    {GR}Roblox packages ditemukan: {len(pkgs)}{R}")
            for p in pkgs: print(f"      - {p}")
        else:
            print(f"    {YE}⚠️  Tidak ada package Roblox (install dulu){R}")

    # -- Test 4: dumpsys activity -------------------------
    print(f"\n{YE}[4] dumpsys activity (deteksi Activity)...{R}")
    ok, out = run_root("dumpsys activity top 2>/dev/null | grep mResumedActivity | head -1")
    dumpsys_ok = ok and bool(out.strip())
    print(f"    {ok_str(dumpsys_ok)}")
    if dumpsys_ok:
        print(f"    {GY}Activity aktif: {out.strip()[:60]}{R}")
        # Cek kalau Roblox running, tampilkan activity-nya
        pkgs = find_installed_pkgs()
        for p in pkgs:
            if is_running(p):
                act = get_current_activity(p)
                print(f"    {GR}Roblox ({p}) Activity: {act or 'tidak terdeteksi'}{R}")

    # -- Test 5: network check ----------------------------
    print(f"\n{YE}[5] Network check (ss/netstat)...{R}")
    ok_ss, _ = run_root("ss -tp 2>/dev/null | head -2")
    ok_ns, _ = run_root("netstat -tp 2>/dev/null | head -2")
    ok_proc, _ = run_root("cat /proc/1/net/tcp 2>/dev/null | head -2")
    net_ok = ok_ss or ok_ns or ok_proc
    print(f"    {ok_str(net_ok)}")
    print(f"    {GY}ss: {ok_str(ok_ss)} | netstat: {ok_str(ok_ns)} | /proc/net: {ok_str(ok_proc)}{R}")

    # -- Test 6: CPU top ----------------------------------
    print(f"\n{YE}[6] CPU monitoring (top)...{R}")
    ok, out = run_root("top -bn1 2>/dev/null | head -3")
    cpu_ok = ok and bool(out.strip())
    print(f"    {ok_str(cpu_ok)}")

    # -- Test 7: am start ---------------------------------
    print(f"\n{YE}[7] Launch intent (am start)...{R}")
    ok, out = run_root("am start --help 2>/dev/null | head -1")
    am_ok = ok
    print(f"    {ok_str(am_ok)}")

    # -- Kesimpulan ---------------------------------------
    print(f"\n{CY}{'='*get_term_width()}{R}")
    print(f"{CY}  KESIMPULAN — Metode Deteksi yang akan dipakai:{R}")
    print(f"{CY}{'='*get_term_width()}{R}")
    if dumpsys_ok:
        print(f"  {GR}✅ UTAMA  : dumpsys activity (paling akurat){R}")
    else:
        print(f"  {RE}❌ UTAMA  : dumpsys activity (tidak work){R}")

    if net_ok:
        print(f"  {GR}✅ BACKUP1: network check{R}")
    else:
        print(f"  {RE}❌ BACKUP1: network check (tidak work){R}")

    if cpu_ok:
        print(f"  {GR}✅ BACKUP2: CPU monitoring{R}")
    else:
        print(f"  {RE}❌ BACKUP2: CPU monitoring (tidak work){R}")

    if pidof_ok:
        print(f"  {GR}✅ BACKUP3: pidof (selalu jadi fallback){R}")

    # Tentukan metode terbaik
    if dumpsys_ok:
        best = f"{GR}dumpsys activity{R}"
    elif net_ok:
        best = f"{YE}network check{R}"
    elif cpu_ok:
        best = f"{YE}CPU monitoring{R}"
    else:
        best = f"{YE}pidof only (basic){R}"

    print(f"\n  {WH}Script akan pakai: {best}")
    print(f"{CY}{'='*get_term_width()}{R}")

    # Simpan hasil ke config
    cfg = load_cfg()
    cfg["diagnostic"] = {
        "dumpsys": dumpsys_ok,
        "network": net_ok,
        "cpu":     cpu_ok,
        "pidof":   pidof_ok,
    }
    save_cfg(cfg)
    print(f"\n{GR}✓ Hasil diagnostic tersimpan ke config.{R}")
    wait_enter()

# ==========================================================
#  MAIN
# ==========================================================
def countdown_before_menu(label, detik=2):
    """
    Countdown sebelum masuk menu.
    Tekan Enter → langsung masuk.
    Otomatis masuk setelah 2 detik.
    """
    import select
    # Flush sisa input biar gak skip otomatis
    try:
        import termios
        termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
    except: pass
    
    print(f"\n  {GY}>> {WH}{label}{R}")
    print(f"  {GY}[Enter = langsung masuk | tunggu {detik}s otomatis]{R}")
    for i in range(detik, 0, -1):
        sys.stdout.write(f"\r  {GY}Masuk dalam {i}s...{R}   ")
        sys.stdout.flush()
        try:
            ready, _, _ = select.select([sys.stdin], [], [], 1)
            if ready:
                sys.stdin.readline()
                break
        except:
            time.sleep(1)
    sys.stdout.write("\r" + " "*50 + "\r\n")
    sys.stdout.flush()
    return True

# ==========================================================
#  MAIN
# ==========================================================
def parse_sequence(c):
    """
    Parse input bebas jadi sequence angka.
    Contoh: "231" → ["2","3","1"]
    Contoh: "10,11,1" → ["10","11","1"]
    Contoh: "2 3 1" → ["2","3","1"]
    Single digit/number juga tetap work.
    """
    # Kalau ada koma atau spasi → split
    if ',' in c:
        parts = [x.strip() for x in c.split(',')]
    elif ' ' in c:
        parts = [x.strip() for x in c.split()]
    elif len(c) > 2:
        # Angka nempel — parse digit per digit
        # Handle 10-14 (2 digit): kalau ada "1" diikuti 0-4 → 2 digit
        parts = []
        i = 0
        while i < len(c):
            if c[i] == '1' and i+1 < len(c) and c[i+1] in '0123456789':
                two = c[i:i+2]
                if two in ['10','11','12','13','14','15','16']:
                    parts.append(two); i += 2
                    continue
            parts.append(c[i]); i += 1
    else:
        parts = [c]
    return [p for p in parts if p]

# Flag komunikasi antara watcher thread dan main loop
_exit_flag    = {"exit": False}

def _cmd_watcher():
    """Thread background: poll flag BOT_COMMAND.
    Removed CMD_FILE polling as requested by user."""
    global BOT_COMMAND
    while not _exit_flag["exit"]:
        try:
            # Jika BOT_COMMAND flag sudah ada (DARI BOT DIRECT), trigger refresh stdin
            if BOT_COMMAND:
                # Interrupt inp() dengan mengirim newline ke stdin
                try:
                    run_root(f"echo '' >> /proc/{os.getpid()}/fd/0 2>/dev/null; true")
                except: pass
        except:
            pass
        time.sleep(0.5)

def main():
    # Global PID file for bot detection
    try:
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
    except: pass

    # Start watcher thread immediately so --auto mode also listens for bot commands
    import threading as _threading
    watcher_t = _threading.Thread(target=_cmd_watcher, daemon=True)
    watcher_t.start()

    import signal
    def handle_sig_exit(s, f):
        _exit_flag["exit"] = True
        sys.exit(0)
    
    # Signalling only works in the MAIN THREAD. 
    # Since we are now running as a thread inside Bot, we skip this to avoid crash.
    try:
        signal.signal(signal.SIGINT, handle_sig_exit)
        signal.signal(signal.SIGTERM, handle_sig_exit)
    except (ValueError, RuntimeError):
        pass # Not in main thread

    try:
        if ARGS.auto:
            if not check_root():
                print(f"{RE}Root required!{R}"); sys.exit(1)
                
            # ───── PROTEKSI TERMUX ─────
            # 1. Wake Lock Termux
            run_root("termux-wake-lock")
            # 2. Set Highest OOM Priority untuk diri sendiri
            protect_app(None)
            
            while True:
                log("Start dengan --auto","INFO")
                res = menu_start_rejoin()
                if res == "stop": break
                # If "restart", loop will call it again
                time.sleep(1)
            return

        MENU_FN = {
            "1":  menu_start_rejoin,
            "2":  menu_detect_packages,
            "3":  menu_set_global_ps,
            "4":  menu_set_per_pkg_ps,
            "5":  menu_clear_config,
            "6":  menu_list_config,
            "7":  menu_setup_webhook,
            "8":  menu_set_interval,
            "9":  lambda: menu_toggle("floating_window", "Floating Window"),
            "10": lambda: menu_toggle("auto_mute", "Auto Mute"),
            "11": lambda: menu_toggle("auto_low_graphics", "Low Grafik"),
            "12": lambda: menu_toggle("auto_tap_splash", "Auto Tap Splash"),
            "13": menu_autoexec,
            "14": menu_diagnostic,
            "15": menu_lihat_log,
        }

        redraw_needed = True
        while True:
            # Cek flag dari watcher atau signal
            if _exit_flag["exit"]:
                break
                
            cmd_now = _bot_cmd_flag["cmd"]
            if cmd_now:
                _bot_cmd_flag["cmd"] = None
                if cmd_now == "start":
                    log("Bot CMD: start rejoin", "INFO")
                    clear()
                    menu_start_rejoin()
                    redraw_needed = True
                    continue
                elif cmd_now == "stop":
                    log("Bot CMD: stop", "INFO")
                    _exit_flag["exit"] = True
                    break

            if redraw_needed:
                reset_terminal()
                print_banner()
                print(f"{GY}  Tip: 231 = urut Menu2,Menu3,Menu1{R}\n")
                flush_stdin()
                sys.stdout.write(f"  {YE}Enter choice: {R}")
                sys.stdout.flush()
                redraw_needed = False

            # inp() dengan timeout 2 detik supaya watcher flag bisa dicek
            import select as _select
            c = ""
            try:
                ready, _, _ = _select.select([sys.stdin], [], [], 2)
                if ready:
                    c = sys.stdin.readline().strip()
                    redraw_needed = True
                else:
                    # Timeout — loop ulang untuk cek bot cmd
                    continue
            except KeyboardInterrupt:
                _exit_flag["exit"] = True
                break
            except:
                time.sleep(1)
                continue

            if c.strip() == "16":
                _exit_flag["exit"] = True
                clear(); print(f"{CY}Sampai jumpa!{R}\n"); break

            sequence = parse_sequence(c.strip())

            valid   = [s for s in sequence if s in MENU_FN or s == "16"]
            invalid = [s for s in sequence if s not in MENU_FN and s != "16"]

            if not valid:
                if c.strip():
                    print(f"\n  {RE}Tidak valid: {c}{R}")
                    time.sleep(2)
                continue

            if invalid:
                print(f"\n  {YE}Diabaikan: {', '.join(invalid)}{R}")
                time.sleep(1)

            labels    = [next((l for n, l in MENU_ITEMS if n == s), f"Menu {s}") for s in valid]
            label_str = " -> ".join(labels)
            if len(valid) > 1:
                countdown_before_menu(label_str, 2)
            else:
                # Refresh title untuk single command biar cepet
                sys.stdout.write(f"\r  {CY}Entering: {WH}{label_str}{R}   \n")
                sys.stdout.flush()

            for s in valid:
                if s == "16":
                    _exit_flag["exit"] = True
                    clear(); print(f"{CY}Sampai jumpa!{R}\n"); return
                fn = MENU_FN.get(s)
                if fn:
                    clear()
                    res = fn()
                    if res == "stop": 
                        _exit_flag["exit"] = True
                        break
    finally:
        # Hapus PID file saat exit (entah itu auto atau menu)
        pid_file = os.path.join(BASE_DIR, "rejoin.pid")
        if os.path.exists(pid_file):
            try: os.remove(pid_file)
            except: pass

if __name__ == '__main__':
    main()

