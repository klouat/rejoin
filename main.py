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

# Import smart tap helper
try:
    import tap_helper as _tap_helper
    _SMART_TAP = True
except ImportError:
    _SMART_TAP = False

def _tap_helper_fallback(pkg, x1, y1, x2, y2):
    """Fallback tap tanpa tap_helper."""
    cx = (x1 + x2) // 2
    run_root(f"am start -a android.intent.action.MAIN -n {pkg}/com.roblox.client.ActivityProtocolLaunch 2>/dev/null; true")
    time.sleep(0.2)
    for ty in [(y1+y2)//2, y1+int((y2-y1)*0.70), y1+int((y2-y1)*0.85)]:
        run_root(f"input tap {cx} {ty}")
        time.sleep(0.08)

# --- ARGS --------------------------------------------------
parser = argparse.ArgumentParser()
parser.add_argument("--auto",      action="store_true")
parser.add_argument("--preventif", action="store_true")
parser.add_argument("--low",       action="store_true")
parser.add_argument("--packages",  help="Filter: package1,package2,...")
ARGS = parser.parse_args()

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_FILE    = os.path.join(BASE_DIR, "activity.log")
STATUS_FILE = os.path.join(BASE_DIR, "status.json")
CMD_FILE    = os.path.join(BASE_DIR, ".bot_cmd")   # File perintah dari bot

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
    """Simpler and more stable clear for Termux."""
    sys.stdout.write("\033[H\033[2J")
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
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{time.strftime('%d/%m %H:%M:%S')}][{lvl}] {msg}\n")
    except:
        pass

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
            p = r.json()['userPresences'][0]
            # Type 2 = In-Game, Type 1 = Online (Lobby/Menu)
            # 0=Offline, 1=Online, 2=InGame, 3=Studio, 4=Basic
            st_type  = p.get('userPresenceType', 0)
            place_id = p.get('placeId')
            game_id  = p.get('gameId') # Job ID Instance
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
    """Cek network via simple shell command."""
    ok, out = run_root(f"cat /proc/net/tcp 2>/dev/null | grep -i {pkg} || true")
    return ok and pkg in out
    return connected

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
    clear()
    mem, mpct = get_memory()

    try:
        import shutil
        W = shutil.get_terminal_size().columns
    except:
        W = int(os.environ.get("COLUMNS", 44))
    W = max(28, W - 1)
    sep  = "=" * W
    sep2 = "-" * W

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

    # Header
    sys.stdout.write(f"{CY}{sep}{R}\n")
    sys.stdout.write(f"{MG} YURXZ Rejoin v9  |  by YURXZ{R}\n")
    sys.stdout.write(f"{CY}{sep2}{R}\n")
    sys.stdout.write(f"{YE} {trunc(st_txt, W-2)}{R}\n")
    sys.stdout.write(f"{GY} RAM: {mem} ({mpct}%){R}\n")
    if mode:
        sys.stdout.write(f"{GY} Mode: {' | '.join(mode)}{R}\n")
    sys.stdout.write(f"{CY}{sep2}{R}\n")

    # Package list — portrait: tiap package 2 baris
    for a in accounts:
        st  = a.get("status", "?")
        mtd = a.get("method", "auto")
        lbl = mtd_labels.get(mtd, "[?]")
        col = GR
        if any(x in st for x in ["Restart","Launch","Wait","Cache","Stop","Loading","Cek","Detect","Tap","Inject"]):
            col = YE
        elif any(x in st for x in ["Error","Failed","Crash","Freeze","mati","putus","Offline"]):
            col = RE
        elif any(x in st for x in ["Idle","Pending"]):
            col = GY
        pkg     = a.get('pkg', '?').replace('com.roblox.', 'rb.')
        uname   = a.get('username', 'Unknown')
        rejoin  = a.get('rejoin_count', 0)
        sys.stdout.write(f"{CY} {lbl}{R} {WH}{pkg} {GY}({uname}){R}\n")
        sys.stdout.write(f"    {col}{trunc(st, W-5)}{R} {GY}({rejoin}x){R}\n")
        sys.stdout.write(f"{GY} {sep2}{R}\n")

    sys.stdout.write(f"{CY}{sep}{R}\n")
    sys.stdout.write(f"{GY} [q]=stop{R}\n")
    sys.stdout.flush()

# ==========================================================
#  DETECTION HELPERS
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
    Ensure we aren't stuck on a 'Welcome' / 'Key' screen even if API says we are in-game.
    Return (bool, activity_name, method)
    """
    # 1. ALWAYS check for Executor Popups/Splash first
    # This catches Delta's 'Welcome Back' window and the 'Taking Too Long' loading screen.
    ok, out = run_root(f"dumpsys window windows 2>/dev/null | grep -iE 'Delta|Welcome|Key|Fisch|Taking' | head -5")
    if ok and out.strip():
        return False, "Executor-Popup", "manual-window-check"

    # 2. Cek Activity (Standard check)
    act = get_current_activity(pkg)
    loading_keywords = ["Taking", "Welcome", "Key", "Delta"]
    if act and any(k.lower() in act.lower() for k in loading_keywords):
        return False, act, "loading-activity"

    if act:
        # Jika Activity adalah RobloxActivity, kita check lagi via backup/API
        if "RobloxActivity" in act or "GameActivity" in act:
            pass # OK, proceed to API/Network check
        else:
            return False, act, "wrong-activity"

    # 3. Check Presence API (Metode Verification)
    if cookie_info:
        uid, cookie = cookie_info
        ingame, place, st_type, job = check_user_presence(uid, cookie)
        if ingame:
            # Re-verify one last time in case of invisible window names
            if st_type == 2:
                return True, f"Game({place})", "presence-api"
        
        if st_type in [0, 1]:
            return False, "Offline/Lobby", "presence-api"

    # 4. Check Network (Fallback)
    if has_active_connection(pkg):
        return True, "Network Active", "network"

    return False, act or "Unknown", "none"

# ==========================================================
#  MENU 1 — START AUTO REJOIN (tanpa cookie)
# ==========================================================
def watch_package(a, cfg, accounts, sw, sh, tot, wh_url,
                  do_float, do_mute, do_lowgfx, interval, stop_event):
    """
    Worker thread — monitor satu package secara independen.
    Tiap package punya thread sendiri, jadi rejoin/tap paralel.
    """
    import threading

    pkg          = a["pkg"]
    link         = a["ps_link"]
    ae_script    = cfg.get("autoexec_script", "")
    ae_delay     = cfg.get("autoexec_delay", 30)
    auto_tap     = cfg.get("auto_tap_splash", True)
    tap_interval = cfg.get("tap_interval", 3)

    # Hitung posisi tap sesuai grid bounds package ini
    def get_win_bounds():
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
            bounds_str = grid_bounds(a["index"], tot, sw, sh)
            try:
                x1, y1, x2, y2 = map(int, bounds_str.split(","))
                return x1, y1, x2, y2
            except:
                pass
        return 0, 0, sw, sh

    def do_smart_tap(label=""):
        """Tap tengah window Roblox. Bawa ke foreground dulu."""
        x1, y1, x2, y2 = get_win_bounds()
        if _SMART_TAP:
            tx, ty, reason = _tap_helper.smart_tap(pkg, x1, y1, x2, y2)
        else:
            _tap_helper_fallback(pkg, x1, y1, x2, y2)
            tx, ty, reason = (x1+x2)//2, (y1+y2)//2, "manual"
        a["status"] = f"Tap[{reason}] ({label})"
        return tx, ty, reason

    def is_splash_screen():
        """
        ULTRA-ACCURATE SPLASH DETECTION
        Targets: Roblox Splash, Delta Executor Popups, and Launcher Fragments.
        """
        # 1. Search Activity Stack AND Window Stack
        # Use window dump to find titles like "NO MERCY DELTA LITE"
        ok, out = run_root(
            f"dumpsys window windows 2>/dev/null | grep -iE 'mCurrentFocus|mFocusedApp|{pkg}|Delta' | head -30"
        )
        if not ok or not out:
            # Fallback to activity top if window dump fails
            ok, out = run_root(f"dumpsys activity top 2>/dev/null | grep -iE '{pkg}' | head -15")
        
        if not out: return None

        # Primary Activity Targets
        splash_activities = [
            ".ActivityProtocolLaunch", # Official Roblox Splash
            "Delta",                   # Delta Executor
            "Fluxus",                  # Fluxus Executor
            "SplashActivity",          # Generic Executor Splash
            "KeySystem"                # Key system prompts
        ]
        
        # Keywords seen in screenshots (e.g., 'Taking Too Long', 'Welcome Back', 'Fisch')
        splash_keywords = [
            "Welcome", "Protocol", "Fisch", "Delta",
            "Launch", "Loading", "Too", "Long", "Taking",
            "Key", "Press", "Continue"
        ]
        
        out_lower = out.lower()

        # Step 1: Check for known Splash/Executor activities
        for act in splash_activities:
            if act.lower() in out_lower:
                return f"Splash_Act({act})"
        
        # Step 2: Check for text fragments in the window dump
        for kw in splash_keywords:
            if kw.lower() in out_lower:
                return f"Keyword({kw})"

        # Step 3: Package logic fallback
        # If we see the package name but NOT the main GameActivity, we are loading.
        if pkg.lower() in out_lower:
            if "robloxactivity" not in out_lower and "gameactivity" not in out_lower:
                return "LauncherStatus"

        return None

    def tap_burst(detected_as, count=3):
        """Tap tengah window sebanyak `count` kali dengan jeda singkat."""
        x1, y1, x2, y2 = get_win_bounds()
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        log(f"{pkg}: Splash detected [{detected_as}] → burst tap {count}x at ({cx},{cy})", "INFO")
        a["status"] = f"Splash tap x{count} [{detected_as}]"
        for _ in range(count):
            run_root(f"input tap {cx} {cy} 2>/dev/null || true")
            time.sleep(0.15)

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
        time.sleep(5)

        if do_mute:   mute_roblox(pkg)
        if do_lowgfx: set_low_graphics(pkg)
        protect_app(pkg)

        # Auto tap + inject autoexec sampai in-game
        injected_ae  = False
        game_entered = False
        total_wait   = max(ae_delay + 10, 40)

        for t in range(total_wait, 0, -1):
            if stop_event.is_set():
                return

            # Cek via is_in_game (Activity + Network + API)
            ingame_now, activity, _ = is_in_game(pkg, a.get("cookie_info"))

            if ingame_now and not game_entered:
                game_entered = True
                a["status"]  = f"In-game! {activity}"
                log(f"{pkg}: Game loaded, activity={activity}", "INFO")
                if ae_script and not injected_ae:
                    a["status"] = "Inject autoexec..."
                    inject_autoexec(pkg, ae_script)
                    injected_ae = True
                break

            # Auto tap: disabled per user request
            # if auto_tap and not game_entered:
            #     splash_kw = is_splash_screen()
            #     if splash_kw:
            #         tap_burst(splash_kw, count=3)
            #     else:
            #         act_str = activity or "loading"
            #         do_smart_tap(f"{act_str} {t}s")

            if not injected_ae and t <= ae_delay and ae_script:
                a["status"] = "Inject autoexec..."
                inject_autoexec(pkg, ae_script)
                injected_ae = True

            time.sleep(1)

        a["status"] = f"Running ✅ (rejoin #{a['rejoin_count']})"
        if wh_url:
            _send_webhook_nocookie(wh_url, accounts,
                                   f"✅ Rejoin OK: {pkg}", 3066993)

    # ── Main monitoring loop untuk package ini ─────────────
    while not stop_event.is_set():
        try:
            # Cek 1: app running?
            if not is_running(pkg):
                do_rejoin("App mati / crash")
                continue

            # Cek 2: Presence API (Mandatory)
            if a.get("cookie_info"):
                uid, cookie = a["cookie_info"]
                api_ingame, api_place, p_type, api_job = check_user_presence(uid, cookie)
                
                # Ekstrak target placeId dan deteksi PS link
                target_place = None; is_ps = False
                ps_lnk_str = str(a.get("ps_link", ""))
                if "placeId=" in ps_lnk_str:
                    try: target_place = int(ps_lnk_str.split("placeId=")[1].split("&")[0])
                    except: pass
                if "roblox.com/share" in ps_lnk_str or "privateServerLinkCode" in ps_lnk_str:
                    is_ps = True
                
                # VALIDASI: In-Game?
                ingame = api_ingame

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
                    # REJOIN SEGERA TANPA LOADING COUNT JIKA API BILANG OFFLINE/LOBBY
                    reason = "Offline/Lobby"
                    if p_type == 1: reason = "Lobby/Menu"
                    if p_type == 0: reason = "Offline"
                    if a.get("status"): reason = a["status"]
                    
                    do_rejoin(reason)
                    a["last_job_id"] = None
                    continue
                else:
                    # Stabil in-game
                    a["loading_count"] = 0
                    protect_app(pkg)
                    a["status"] = "In-game ✅ API"
            else:
                a["status"] = "No Cookie - Presence Fail"
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
                
                log(f"[{pkg}] {a.get('username','?')}: {new_st} (Presence: {p_str})", "INFO")
                a["last_log_status"] = new_st
                a["last_log_time"]   = now

        except Exception as e:
            log(f"{pkg}: Error di watch_thread: {e}", "WARN")

        time.sleep(interval)

def menu_start_rejoin():
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
    restart_delay = cfg.get("restart_delay", 10)
    do_float      = cfg.get("floating_window", True)
    do_mute       = cfg.get("auto_mute", True)
    do_lowgfx     = cfg.get("auto_low_graphics", True)
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
            "username":      username
        })

    run_root("setenforce 0")

    # -- Launch awal semua package -------------------------
    for i, a in enumerate(accounts):
        pkg  = a["pkg"]
        link = a["ps_link"]

        a["status"] = "Force stop..."
        draw_ui(accounts, "Launching", f"[{i+1}/{tot}]")
        force_stop(pkg)

        a["status"] = "Clear cache..."
        draw_ui(accounts, "Launching", f"[{i+1}/{tot}]")
        clear_cache_safe(pkg)

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
            for t in range(restart_delay, 0, -1):
                draw_ui(accounts, "Launching", f"Next in {t}s")
                time.sleep(1)

    # Tunggu game load
    for t in range(20, 0, -1):
        draw_ui(accounts, "Initializing", f"Wait {t}s")
        time.sleep(1)

    for a in accounts:
        a["status"] = "Running ✅" if is_running(a["pkg"]) else "Not Running ⚠️"

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

            # --- Update status.json untuk bot.py ---
            try:
                data = [{"pkg": x["pkg"], "status": x["status"], "username": x["username"]} for x in accounts]
                with open("status.json", "w") as f_st:
                    json.dump(data, f_st)
            except: pass
            try:
                if os.path.exists(CMD_FILE):
                    with open(CMD_FILE) as f:
                        cmd = f.read().strip()
                    os.remove(CMD_FILE)
                    if cmd == "stop":
                        raise KeyboardInterrupt
                    elif cmd == "start":
                        pass  # sudah jalan, ignore
            except KeyboardInterrupt:
                raise
            except:
                pass

            # Simpan status
            try:
                with open(STATUS_FILE, "w") as f:
                    json.dump([{"pkg": x["pkg"], "status": x["status"],
                                "rejoin": x.get("rejoin_count", 0)} for x in accounts], f)
            except:
                pass

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

    except KeyboardInterrupt:
        stop_event.set()
        # Hapus cmd file kalau ada
        try:
            if os.path.exists(CMD_FILE): os.remove(CMD_FILE)
            if os.path.exists(STATUS_FILE): os.remove(STATUS_FILE)
            if os.path.exists("status.json"): os.remove("status.json")
        except: pass
        print(f"\n{YE}[!] Menghentikan semua thread...{R}")
        for t in threads:
            t.join(timeout=3)
        print(f"{YE}[!] Dihentikan.{R}\n")

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

def main():
    if ARGS.auto:
        if not check_root():
            print(f"{RE}Root required!{R}"); sys.exit(1)
            
        # ───── PROTEKSI TERMUX ─────
        # 1. Wake Lock Termux
        run_root("termux-wake-lock")
        # 2. Set Highest OOM Priority untuk diri sendiri
        protect_app(None)
        
        # Write PID file (agar bot.py bisa deteksi)
        try:
            with open("rejoin.pid", "w") as f:
                f.write(str(os.getpid()))
        except: pass
        
        log("Start dengan --auto","INFO")
        try:
            menu_start_rejoin()
        finally:
            # Hapus PID file saat exit
            if os.path.exists("rejoin.pid"):
                os.remove("rejoin.pid")
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

    import threading as _threading

    # Flag komunikasi antara watcher thread dan main loop
    _bot_cmd_flag = {"cmd": None}
    _exit_flag    = {"exit": False}

    def _cmd_watcher():
        """Thread background: poll CMD_FILE tiap 0.5 detik.
        Tidak terblokir oleh inp() di main loop."""
        while not _exit_flag["exit"]:
            try:
                if os.path.exists(CMD_FILE):
                    with open(CMD_FILE) as f:
                        cmd = f.read().strip()
                    os.remove(CMD_FILE)
                    if cmd in ("start", "stop"):
                        _bot_cmd_flag["cmd"] = cmd
                        log(f"Bot CMD diterima: {cmd}", "INFO")
                        # Interrupt inp() dengan mengirim newline ke stdin
                        try:
                            import subprocess as _sp
                            _sp.run(["su", "-c",
                                     f"echo '' >> /proc/{os.getpid()}/fd/0 2>/dev/null; true"],
                                    capture_output=True, timeout=2)
                        except:
                            pass
            except:
                pass
            time.sleep(0.5)

    watcher_t = _threading.Thread(target=_cmd_watcher, daemon=True)
    watcher_t.start()

    import signal
    def handle_sig_exit(s, f):
        _exit_flag["exit"] = True
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_sig_exit)
    signal.signal(signal.SIGTERM, handle_sig_exit)

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
                clear(); fn()

if __name__ == '__main__':
    main()

