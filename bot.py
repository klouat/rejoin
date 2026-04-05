#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║   YURXZ Rejoin Bot  —  bot.py                          ║
║   Discord Bot dengan Button UI                         ║
║   Jalan di Termux bersamaan dengan main.py             ║
╚══════════════════════════════════════════════════════════╝

Setup:
1. Buat bot di https://discord.com/developers/applications
2. Copy TOKEN bot
3. Enable: MESSAGE CONTENT INTENT + SERVER MEMBERS INTENT
4. Invite bot ke server dengan permission: Send Messages,
   Embed Links, Attach Files, Read Message History
5. Isi BOT_TOKEN dan CHANNEL_ID di config.json atau saat setup
"""

import os, sys, json, time, subprocess, threading, re
from pathlib import Path

# Import main.py logic directly (Zero latency)
try:
    import main as rejoin_module
except ImportError:
    # Fallback if main.py is missing (unlikely)
    rejoin_module = None

# ── Path ────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
LOG_FILE    = BASE_DIR / "activity.log"
PID_FILE    = BASE_DIR / "rejoin.pid"
BOT_CFG     = BASE_DIR / "bot_config.json"
BOT_LOG     = BASE_DIR / "bot.log"

def bot_log(msg):
    """Log ke file, tidak tampil di terminal."""
    try:
        with open(str(BOT_LOG), "a") as f:
            f.write(f"[{time.strftime('%d/%m %H:%M:%S')}] {msg}\n")
    except:
        pass

# ── Warna terminal ─────────────────────────────────────
R  = "\033[0m"; CY = "\033[96m"; GR = "\033[92m"
YE = "\033[93m"; RE = "\033[91m"; MG = "\033[95m"
GY = "\033[90m"; WH = "\033[97m"

# ═══════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════
def load_bot_cfg():
    if BOT_CFG.exists():
        try:
            with open(BOT_CFG) as f:
                return json.load(f)
        except:
            pass
    return {"token": "", "channel_id": "", "owner_ids": []}

def save_bot_cfg(cfg):
    with open(BOT_CFG, "w") as f:
        json.dump(cfg, f, indent=2)

def load_main_cfg():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except:
            pass
    return {}

def load_status():
    """Read status directly from memory (Fast). In-process only."""
    # Memory check only (Now strictly no status.json)
    if rejoin_module and rejoin_module.MONITOR_DATA:
        return rejoin_module.MONITOR_DATA
    return []

def find_cookie_for_pkg(pkg):
    """Cari cookie .ROBLOSECURITY untuk package tertentu (via su)."""
    temp_db = "/sdcard/temp_bot_cookies.db"
    cookie = None
    try:
        # Cari file cookie
        r = subprocess.run(["su", "-c", f"find /data/data/{pkg} -type f -name 'Cookies' 2>/dev/null | head -1"], 
                           capture_output=True, text=True, timeout=10)
        db_path = r.stdout.strip()
        if not db_path:
            r = subprocess.run(["su", "-c", f"find /data/data/{pkg} -type f -name 'cookies.sqlite' 2>/dev/null | head -1"], 
                               capture_output=True, text=True, timeout=10)
            db_path = r.stdout.strip()
            
        if db_path:
            subprocess.run(["su", "-c", f"cp '{db_path}' '{temp_db}' && chmod 666 '{temp_db}'"], timeout=10)
            import sqlite3
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            # Chromium
            try:
                cursor.execute("SELECT value FROM cookies WHERE host_key LIKE '%roblox.com%' AND name = '.ROBLOSECURITY'")
                res = cursor.fetchone()
                if res: cookie = res[0]
            except:
                # Firefox
                try:
                    cursor.execute("SELECT value FROM moz_cookies WHERE host LIKE '%roblox.com%' AND name = '.ROBLOSECURITY'")
                    res = cursor.fetchone()
                    if res: cookie = res[0]
                except: pass
            conn.close()
            subprocess.run(["rm", temp_db])
    except: pass
    return cookie

def get_username_from_cookie(cookie):
    try:
        import requests
        r = requests.get("https://users.roblox.com/v1/users/authenticated", 
                         cookies={".ROBLOSECURITY": cookie}, timeout=5)
        if r.status_code == 200:
            return r.json().get("name")
    except: pass
    return "Unknown"

def get_last_log(n=15):
    """Ambil N baris terakhir dari log."""
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE) as f:
                lines = f.readlines()
            return "".join(lines[-n:]).strip() or "(log kosong)"
        except:
            pass
    return "(log tidak ditemukan)"

def take_screenshot():
    """Ambil screenshot via root. Coba beberapa path."""
    local = str(BASE_DIR / "bot_ss.png")
    # Coba beberapa tmp path yang pasti bisa ditulis root
    for tmp in ["/data/local/tmp/yurxz_ss.png", "/sdcard/yurxz_ss.png"]:
        try:
            r = subprocess.run(
                ["su", "-c", f"screencap -p '{tmp}' 2>/dev/null && cp '{tmp}' '{local}' && chmod 666 '{local}'"],
                capture_output=True, timeout=15
            )
            if r.returncode == 0 and os.path.exists(local) and os.path.getsize(local) > 1000:
                return local
        except:
            continue
    return None

# PID file untuk tools (start.sh)
TOOLS_PID_FILE = BASE_DIR / "tools.pid"

# --- Commands -----------------------------------------------

def write_cmd(cmd):
    """Set command directly in main module memory."""
    if rejoin_module:
        rejoin_module.BOT_COMMAND = cmd
        return True
    return False

def run_tools(target_pkgs=None, auto=True):
    """Versi Stabil: Python yang memegang kontrol Background (Bukan Shell)."""
    mode_str = "AUTO" if auto else "MENU"
    print(f"\n{YE}[Bot] Meminta start tools mode: {mode_str}...{R}", flush=True)

    if is_rejoin_running():
        # Cek apakah itu proses kita atau bukan
        print(f"{YE}[Bot] Periksa status... Tools terdeteksi sudah jalan.{R}", flush=True)
        return False, "Tools sudah jalan!"
    
    cfg        = load_main_cfg()
    main_py    = str(BASE_DIR / "main.py")
    python_exe = sys.executable or "python3"
    log_f      = str(BASE_DIR / "tools.log")
    launcher   = str(BASE_DIR / "_launch.sh")

    pkg_arg = f"--packages '{','.join(target_pkgs)}'" if target_pkgs else ""
    prefix  = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
    
    if auto:
        # Mode AUTO: Pakai launcher loop + su -c (Root)
        with open(launcher, "w") as f:
            f.write("#!/bin/sh\n")
            f.write(f"export PATH=$PATH:{prefix}/bin\n")
            f.write(f"cd '{BASE_DIR}'\n")
            f.write("while true; do\n")
            f.write(f"  su -c 'echo -1000 > /proc/$$/oom_score_adj' 2>/dev/null\n")
            f.write(f"  '{python_exe}' '{main_py}' --auto {pkg_arg} >> '{log_f}' 2>&1\n")
            f.write("  echo 'Main script crashed or killed. Restarting in 5s...' >> '" + str(log_f) + "'\n")
            f.write("  sleep 5\n")
            f.write("done\n")
        os.chmod(launcher, 0o755)
        cmd = ["sh", launcher]
    else:
        # Mode MENU: Jalankan sebagai user biasa (seperti 'python main.py')
        # main.py akan handle su -c sendiri untuk aksi yang butuh root.
        cmd = [python_exe, main_py]
        if target_pkgs:
            cmd += ["--packages", ",".join(target_pkgs)]

    print(f"{GY}[Bot] Exec: {' '.join(cmd)}{R}", flush=True)
    
    try:
        subprocess.run(["termux-wake-lock"], capture_output=True)
        if auto:
            # Direct In-Process Monitor (Zero File Intermediaries)
            def run_main_in_thread():
                # Inject ARGS to main.py before running
                if rejoin_module:
                    rejoin_module.ARGS.auto     = True
                    rejoin_module.ARGS.packages = ",".join(target_pkgs) if target_pkgs else None
                    rejoin_module.main() # Start the main loop
            
            t = threading.Thread(target=run_main_in_thread, name="MonitorThread", daemon=True)
            t.start()
            bot_log("Launched in-process monitor thread.")
            return True, "✅ Rejoin dimulai (Internal Thread aktif)!"
        else:
            # Menu mode stays as a separate window for manual interact
            subprocess.Popen(cmd)
    except Exception as e:
        print(f"{RE}[Bot] Launch Error: {e}{R}", flush=True)
        return False, f"❌ Error: {e}"

    # 3. Tunggu monitoring (Hanya butuh bbrp detik kalau lancar)
    print(f"{GY}[Bot] Menunggu monitoring aktif...{R}")
    for _ in range(12):
        time.sleep(1)
        if is_rejoin_running():
            print(f"{GR}[Bot] ✅ Berhasil Jalan! ✓{R}")
            
            # ── LIVE MONITOR (Mimic Manual Main.py UI in Terminal) ──
            def _terminal_monitor():
                print(f"{CY}[Bot] Monitoring Mode: TERMINAL LOG AKTIF{R}")
                time.sleep(2)
                
                while is_rejoin_running():
                    try:
                        # Clear screen and move to home like main.py
                        sys.stdout.write("\033[H\033[2J")
                        sys.stdout.flush()
                        
                        # Load stats derived from status.json (updated by main.py)
                        status_data = load_status()
                        cfg         = load_main_cfg()
                        
                        W = 44
                        try:
                            import shutil
                            W = shutil.get_terminal_size().columns
                        except: pass
                        W = max(30, W - 1)
                        
                        div = f"{CY}{'='*W}{R}"
                        sep = f"{CY}{'-'*W}{R}"
                        
                        # -- Header --
                        print(div)
                        print(f"{MG}YURXZ Rejoin Bot | Monitor Live{R}")
                        print(sep)
                        print(f"{YE}Status: MONITORING ACTIVE{R}")
                        print(f"{GY}Bot is handling Discord commands...{R}")
                        print(sep)
                        
                        # -- Accounts --
                        if not status_data:
                            print(f"{GY}Menunggu data dari session...{R}")
                        else:
                            mtd_labels = {
                                "activity":     "[A]",
                                "network":      "[N]",
                                "cpu":          "[C]",
                                "pidof":        "[P]",
                                "presence-api": "[API]",
                            }
                            
                            for s in status_data:
                                pkg    = s.get("pkg", "?").replace("com.roblox.", "rb.")
                                st     = s.get("status", "?")
                                rj     = s.get("rejoin", 0)
                                uname  = s.get("username", "Unknown")
                                mtd    = s.get("method", "auto")
                                lbl    = mtd_labels.get(mtd, "[-] ")
                                
                                color = GR
                                if any(x in st for x in ["Restart","Launch","Wait","Cache","Stop","Loading"]): color = YE
                                elif any(x in st for x in ["Error","Failed","Crash","Freeze","Offline"]): color = RE
                                
                                # Header (Label + Pkg + User)
                                print(f"{CY}{lbl} {pkg} ({uname}){R}")
                                # Status line
                                print(f"{color}{st[:W-6]:<{W-6}}{R} ({rj}x)")
                                print(sep)
                        
                        # -- Footer --
                        print(div)
                        print(f"{GY}[Bot Hub] Tekan Ctrl+C untuk paksa stop bot{R}")
                        sys.stdout.flush()
                        
                    except Exception as e:
                        bot_log(f"Monitor error: {e}")
                    
                    time.sleep(2) # Refresh rate

                # When finished
                print(f"\n{RE}[Bot] Monitoring berhenti (Tools Mati).{R}")
                time.sleep(1)
                print(f"{CY}[Bot] Kembali ke UI Bot dasar...{R}\n")
            
            if auto: # Only start monitor if in background loop where we don't own the terminal
                threading.Thread(target=_terminal_monitor, daemon=True).start()
            
            # Buat list launching
            if auto:
                all_pkgs = target_pkgs or cfg.get("packages", [])
                launch_txt = "\n".join([f"🚀 Launching `{p}`..." for p in all_pkgs])
                msg = f"▶ ✅ Tools dimulai! Monitoring Aktif.\n\n{launch_txt}"
            else:
                msg = "🛠 ✅ Tools dimulai dalam mode **MENU** di terminal."
            return True, msg
            
    print(f"{RE}[Bot] Timeout Gagal Start. Cek izin Root di HP!{R}")
    return False, "❌ Masih Gagal (Timeout). Cek popup izin Root di HP!"

def start_rejoin():
    """
    Start rejoin:
    - Kalau main.py belum jalan → jalankan via run_tools() dengan --auto
    - Kalau sudah jalan di mode menu → kirim CMD 'start', tunggu konfirmasi
    """
    if not is_rejoin_running():
        return run_tools()

    # Log terminal
    cfg = load_main_cfg()
    pkgs = cfg.get("packages", [])
    print(f"\n{CY}[Bot] Perintah Start Diterima!{R}")
    if pkgs:
        print(f"{GY}[Bot] Meluncurkan package:{R}")
        for p in pkgs:
            print(f"      🚀 {YE}{p}{R}")

    # Sudah jalan → kirim perintah start via CMD_FILE
    if not write_cmd("start"):
        return False, "❌ Gagal kirim perintah."

    # Tunggu main.py masuk mode rejoin (MONITOR_DATA akan berubah)
    last_len = len(load_status())
    
    for i in range(15):
        time.sleep(1)
        if len(load_status()) != last_len or any(x.get('status') != 'Pending' for x in load_status()):
            return True, "✅ Rejoin dimulai (Thread monitor aktif)!"

    # Kalau status belum berubah, cukup assume berhasil kalau masih running
    if is_rejoin_running():
        return True, "✅ Perintah start dikirim!"
    return False, "❌ Gagal start rejoin."

def is_tools_running():
    """Cek apakah main.py jalan."""
    return is_rejoin_running()

def is_rejoin_running():
    """Cek apakah main.py sedang jalan di background."""
    # 1. Cek file PID (paling akurat)
    if PID_FILE.exists():
        try:
            pid = PID_FILE.read_text().strip()
            if pid and os.path.exists(f"/proc/{pid}"):
                return True
        except: pass

    # 2. Cek via pgrep dan ps (fallback)
    try:
        # Pgrep cmdline (lebih pakem di android)
        # Cari proses python yang menjalankan main.py
        r = subprocess.run(["pgrep", "-f", "main.py"], 
                           capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            # Filter pids yang valid / ada di proc
            for pid in r.stdout.strip().split():
                if os.path.exists(f"/proc/{pid}"):
                    return True
        
        # Cek apakah launcher shell-nya masih idup
        r = subprocess.run(["pgrep", "-f", "_launch.sh"], 
                           capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
             return True

        # Last resort: su -c ps (bisa lihat proses root juga)
        r = subprocess.run(["su", "-c", "ps -A | grep 'main.py' | grep -v grep"], 
                           capture_output=True, text=True, timeout=5)
        if "main.py" in r.stdout: return True
    except:
        pass
    return False

def stop_tools():
    """Hentikan semua — termasuk launcher loop agar tidak auto-restart."""
    # 1. Kirim sinyal stop graceful
    write_cmd("stop")
    time.sleep(2)
    
    # 2. Kill Launcher & Python script
    try:
        # Kita kill _launch.sh dulu supaya tidak spawn main.py baru
        subprocess.run(["su", "-c", "pkill -f '_launch.sh' 2>/dev/null; true"], timeout=5)
        
        # Baru kill main.py
        for sig in ["-SIGINT", "-SIGTERM", "-9"]:
            subprocess.run(
                ["su", "-c", f"pkill {sig} -f 'main.py' 2>/dev/null; true"],
                capture_output=True, timeout=5
            )
            time.sleep(1)
            if not is_rejoin_running():
                break
        
        # Matikan wake-lock agar hemat baterai
        subprocess.run(["termux-wake-unlock"], capture_output=True)
        
        return True, "✅ Tools & Launcher dihentikan total!"
    except Exception as e:
        return False, f"❌ Error saat stopping: {e}"

def stop_rejoin():
    """Stop rejoin — sama seperti stop_tools karena main.py = rejoin."""
    if not is_rejoin_running():
        return False, "Tools tidak sedang jalan!"
    return stop_tools()

def run_lua_script(script_text, pkg=None):
    """Inject script Lua ke executor."""
    cfg  = load_main_cfg()
    pkgs = [pkg] if pkg else cfg.get("packages", [])
    if not pkgs:
        return False, "Tidak ada package Roblox!"

    results = []
    for p in pkgs:
        base_data   = f"/data/data/{p}/files"
        base_sdcard = f"/sdcard/Android/data/{p}/files"
        escaped     = script_text.replace("'", "'\\''")

        # Scan folder executor
        injected = 0
        for base in [base_data, base_sdcard]:
            r, out = subprocess.run(
                ["su", "-c", f"ls '{base}' 2>/dev/null"],
                capture_output=True, text=True
            ).returncode, subprocess.run(
                ["su", "-c", f"ls '{base}' 2>/dev/null"],
                capture_output=True, text=True
            ).stdout

            for folder in out.split():
                for subpath in [
                    f"{base}/{folder}/autoexec/autoexec.lua",
                    f"{base}/{folder}/workspace/autoexec.lua",
                ]:
                    folder_path = "/".join(subpath.split("/")[:-1])
                    subprocess.run(
                        ["su", "-c", f"mkdir -p '{folder_path}' && printf '%s' '{escaped}' > '{subpath}' && chmod 666 '{subpath}'"],
                        capture_output=True, timeout=5
                    )
                    injected += 1

        results.append(f"{p}: {injected} path")

    return True, "\n".join(results)

def find_installed_pkgs():
    """Scan SEMUA package di device secara dinamis (seperti main.py)."""
    installed = []
    keywords = ["roblox", "delta", "fluxus", "arceus", "executor", "clien", "com.ro"]
    try:
        r = subprocess.run(["su", "-c", "pm list packages"], 
                           capture_output=True, text=True, timeout=15)
        if r.returncode == 0 and r.stdout:
            for line in r.stdout.splitlines():
                pkg = line.replace("package:", "").strip()
                if any(k in pkg.lower() for k in keywords) and pkg not in installed:
                    installed.append(pkg)
    except: pass
    return installed

# ═══════════════════════════════════════════════════════
#  DISCORD BOT — pakai requests (tanpa library berat)
# ═══════════════════════════════════════════════════════
try:
    import requests
except ImportError:
    print(f"{RE}Install requests dulu: pip install requests{R}")
    sys.exit(1)

DISCORD_API = "https://discord.com/api/v10"

class DiscordBot:
    def __init__(self, token, channel_id, owner_ids=None):
        self.token      = token
        self.channel_id = str(channel_id)
        self.owner_ids  = [str(x) for x in (owner_ids or [])]
        self.headers    = {
            "Authorization": f"Bot {token}",
            "Content-Type":  "application/json",
        }
        self.last_msg_id = None
        self.panel_msg_id = None  # ID pesan panel utama
        self.is_running  = True  # Flag untuk loop utama bot

    def api(self, method, endpoint, **kwargs):
        url = f"{DISCORD_API}{endpoint}"
        try:
            r = getattr(requests, method)(
                url, headers=self.headers, timeout=15, **kwargs
            )
            return r
        except Exception as e:
            print(f"{RE}API error: {e}{R}")
            return None

    def send_message(self, content="", embeds=None, components=None, file_path=None):
        """Kirim pesan ke channel."""
        payload = {}
        if content:    payload["content"]    = content
        if embeds:     payload["embeds"]     = embeds
        if components: payload["components"] = components

        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as f:
                r = requests.post(
                    f"{DISCORD_API}/channels/{self.channel_id}/messages",
                    headers={"Authorization": f"Bot {self.token}"},
                    data={"payload_json": json.dumps(payload)},
                    files={"file": ("screenshot.png", f, "image/png")},
                    timeout=20
                )
        else:
            r = self.api("post", f"/channels/{self.channel_id}/messages",
                        json=payload)
        if r and r.status_code in (200, 201):
            return r.json().get("id")
        return None

    def edit_message(self, msg_id, content="", embeds=None, components=None):
        """Edit pesan yang sudah ada."""
        payload = {}
        if content:    payload["content"]    = content
        if embeds:     payload["embeds"]     = embeds
        if components: payload["components"] = components
        self.api("patch", f"/channels/{self.channel_id}/messages/{msg_id}",
                json=payload)

    def respond_modal(self, interaction_id, interaction_token, custom_id, title, components):
        """Kirim Discord Modal (popup box)."""
        payload = {
            "type": 9,
            "data": {
                "custom_id": custom_id,
                "title":     title,
                "components": components
            }
        }
        url = f"{DISCORD_API}/interactions/{interaction_id}/{interaction_token}/callback"
        try:
            requests.post(url, headers=self.headers, json=payload, timeout=15)
        except Exception as e:
            print(f"{RE}Modal error: {e}{R}")

    def respond_interaction(self, interaction_id, interaction_token,
                            content="", embeds=None, components=None,
                            ephemeral=False, file_path=None):
        """Respond ke button interaction."""
        flags   = 64 if ephemeral else 0
        payload = {
            "type": 4,
            "data": {"flags": flags}
        }
        if content:    payload["data"]["content"]    = content
        if embeds:     payload["data"]["embeds"]     = embeds
        if components: payload["data"]["components"] = components

        url = f"{DISCORD_API}/interactions/{interaction_id}/{interaction_token}/callback"
        try:
            if file_path and os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    requests.post(
                        url,
                        headers={"Authorization": f"Bot {self.token}"},
                        data={"payload_json": json.dumps(payload)},
                        files={"file": ("screenshot.png", f, "image/png")},
                        timeout=20
                    )
            else:
                requests.post(url, headers=self.headers,
                            json=payload, timeout=15)
        except Exception as e:
            print(f"{RE}Interaction respond error: {e}{R}")

    def edit_interaction_response(self, interaction_token, content="", embeds=None, components=None):
        """Edit response interaction yang sudah ada (bisa ephemeral)."""
        payload = {}
        if content:    payload["content"]    = content
        if embeds:     payload["embeds"]     = embeds
        if components: payload["components"] = components
        
        url = f"{DISCORD_API}/webhooks/{self.token.split('.')[0]}/{interaction_token}/messages/@original"
        try:
            requests.patch(url, headers=self.headers, json=payload, timeout=15)
        except Exception as e:
            print(f"{RE}Edit interaction error: {e}{R}")

    def get_gateway(self):
        """Ambil gateway URL."""
        r = self.api("get", "/gateway/bot")
        if r and r.status_code == 200:
            return r.json().get("url")
        return None

    def build_panel_embed(self):
        """Build embed panel utama."""
        cfg    = load_main_cfg()
        status = load_status()
        running = is_rejoin_running()

        # Status tiap package
        pkg_lines = []
        last_names = cfg.get("usernames", {})

        if running and status:
            for s in status:
                icon   = "🟢" if "Running" in s.get("status","") or "In-game" in s.get("status","") else "🔴"
                rejoin = s.get("rejoin", 0)
                uname  = s.get("username", "Unknown")
                
                # Fallback ke last known username jika Unknown
                if uname == "Unknown":
                    uname = last_names.get(s.get("pkg",""), "Unknown")
                
                # Format: ICON [Package] PLAYER -> Status
                pkg_lines.append(f"{icon} `{s.get('pkg','?')}`\n👤 **{uname}** — {s.get('status','?')}")
        else:
            # Jika tidak running, pakai list dari config
            pkgs = cfg.get("packages", [])
            for p in pkgs:
                uname = last_names.get(p, "Unknown")
                pkg_lines.append(f"⚪ `{p}`\n👤 **{uname}** — (Tools belum start)")

        pkg_text = "\n".join(pkg_lines) if pkg_lines else "Tidak ada package terdeteksi."

        color  = 0x2ecc71 if running else 0xe74c3c
        status_text = "🟢 **RUNNING**" if running else "🔴 **STOPPED**"

        embed = {
            "title": "🎮 YURXZ Rejoin v9 — Control Panel",
            "color": color,
            "fields": [
                {"name": "Status", "value": status_text, "inline": True},
                {"name": "PS Link", "value": f"`{cfg.get('global_ps_link','(belum diset)')[:50]}`", "inline": True},
                {"name": "Packages", "value": pkg_text, "inline": False},
            ],
            "footer": {"text": f"YURXZ Bot • {time.strftime('%d/%m/%Y %H:%M:%S')}"},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        return embed

    def build_main_buttons(self):
        """Build button panel utama."""
        running = is_rejoin_running()
        return [
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "label": "⚙️ Edit Config",
                        "style": 2,
                        "custom_id": "btn_edit_config",
                    },
                    {
                        "type": 2,
                        "label": "🔴 Kill Everything",
                        "style": 4,
                        "custom_id": "btn_stop_tools",
                    },
                    {
                        "type": 2,
                        "label": "🚀 Start Rejoin",
                        "style": 3,
                        "custom_id": "btn_start",
                    },
                    {
                        "type": 2,
                        "label": "➕ Add AutoExec",
                        "style": 1,
                        "custom_id": "btn_add_autoexec",
                    },
                    {
                        "type": 2,
                        "label": "⏹ Stop Rejoin",
                        "style": 4,
                        "custom_id": "btn_stop",
                    },
                ]
            },
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "label": "🔍 Detect Pkg",
                        "style": 1,
                        "custom_id": "btn_detect_pkg",
                    },
                    {
                        "type": 2,
                        "label": "📊 Status",
                        "style": 2,
                        "custom_id": "btn_status",
                    },
                    {
                        "type": 2,
                        "label": "⚙️ Config",
                        "style": 2,
                        "custom_id": "btn_config",
                    },
                    {
                        "type": 2,
                        "label": "📸 Screenshot",
                        "style": 2,
                        "custom_id": "btn_ss",
                    },
                    {
                        "type": 2,
                        "label": "📜 Log",
                        "style": 2,
                        "custom_id": "btn_log",
                    },
                ]
            },
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "label": "💉 Run Script",
                        "style": 1,
                        "custom_id": "btn_script",
                    },
                    {
                        "type": 2,
                        "label": "🔗 Set PS Link",
                        "style": 1,
                        "custom_id": "btn_set_ps",
                    },
                    {
                        "type": 2,
                        "label": "🗑 Remove Auto Exec",
                        "style": 4,
                        "custom_id": "btn_remove_ae",
                    },
                    {
                        "type": 2,
                        "label": "🔄 Refresh",
                        "style": 2,
                        "custom_id": "btn_refresh",
                    },
                ]
            }
        ]

    def send_panel(self):
        """Kirim panel kontrol ke channel."""
        embed      = self.build_panel_embed()
        components = self.build_main_buttons()
        msg_id     = self.send_message(embeds=[embed], components=components)
        if msg_id:
            self.panel_msg_id = msg_id
            bot_log("Panel dikirim ke channel")
        return msg_id

    def refresh_panel(self):
        """Update panel yang sudah ada."""
        if not self.panel_msg_id:
            self.send_panel()
            return
        embed      = self.build_panel_embed()
        components = self.build_main_buttons()
        self.edit_message(self.panel_msg_id, embeds=[embed],
                         components=components)

    def cleanup_old_messages(self):
        """Hapus pesan bot biasa, panel utama tidak dihapus."""
        try:
            r = self.api("get", f"/channels/{self.channel_id}/messages?limit=20")
            if not r or r.status_code != 200:
                return
            msgs = r.json()
            bot_id = None
            for m in msgs:
                if m.get("author", {}).get("bot"):
                    bot_id = m["author"]["id"]
                    break
            if not bot_id:
                return
            deleted = 0
            for m in msgs:
                mid = m.get("id")
                if mid == self.panel_msg_id:
                    continue  # Jangan hapus panel utama
                if m.get("author", {}).get("id") == bot_id:
                    # Hanya hapus pesan teks biasa (bukan embed panel)
                    has_embed = bool(m.get("embeds"))
                    has_components = bool(m.get("components"))
                    if not has_components:  # Hapus pesan tanpa tombol
                        self.api("delete", f"/channels/{self.channel_id}/messages/{mid}")
                        deleted += 1
                        time.sleep(0.5)
                        if deleted >= 5:  # Max 5 pesan per cleanup
                            break
        except:
            pass

    def handle_interaction(self, data):
        """Handle button press."""
        interaction_id    = data.get("id")
        interaction_token = data.get("token")
        custom_id         = data.get("data", {}).get("custom_id", "")
        user_id           = data.get("member", {}).get("user", {}).get("id", "")

        # Cek owner
        if self.owner_ids and user_id not in self.owner_ids:
            self.respond_interaction(
                interaction_id, interaction_token,
                content="❌ Kamu tidak punya akses!", ephemeral=True
            )
            return

        bot_log(f"Button: {custom_id} dari user {user_id}")
        print(f"{CY}[Bot] Interaction: {YE}{custom_id}{R} (User: {user_id})", flush=True)

        if custom_id == "btn_edit_config":
            cfg = load_main_cfg()
            # Max 5 components in modal
            # Formatting boolean flags for easier edit
            flags = ",".join([
                "T" if cfg.get("floating_window", True) else "F",
                "T" if cfg.get("auto_mute", True) else "F",
                "T" if cfg.get("auto_low_graphics", True) else "F",
                "T" if cfg.get("auto_tap_splash", True) else "F"
            ])
            
            self.respond_modal(
                interaction_id, interaction_token,
                "modal_edit_config", "Edit Configuration",
                [
                    {"type": 1, "components": [{"type": 4, "custom_id": "check_interval", "label": "Check Interval (s)", "style": 1, "value": str(cfg.get("check_interval", 35)), "required": True}]},
                    {"type": 1, "components": [{"type": 4, "custom_id": "restart_delay", "label": "Restart Delay (s)", "style": 1, "value": str(cfg.get("restart_delay", 10)), "required": True}]},
                    {"type": 1, "components": [{"type": 4, "custom_id": "load_delay", "label": "Load Delay (s)", "style": 1, "value": str(cfg.get("load_delay", 40)), "required": True}]},
                    {"type": 1, "components": [{"type": 4, "custom_id": "packages", "label": "Packages (comma separated)", "style": 2, "value": ",".join(cfg.get("packages", [])), "required": False}]},
                    {"type": 1, "components": [{"type": 4, "custom_id": "flags", "label": "Flags: Float,Mute,LowGfx,Tap (T/F)", "style": 1, "value": flags, "placeholder": "T,T,T,T", "required": True}]}
                ]
            )



        elif custom_id == "btn_stop_tools":
            self.respond_interaction(interaction_id, interaction_token,
                content="🔴 Menghentikan tools...", ephemeral=True)
            def _stop_tools():
                ok, msg = stop_tools()
                self.send_message(content=f"{'🔴' if ok else '❌'} {msg}")
                time.sleep(3); self.refresh_panel()
            threading.Thread(target=_stop_tools, daemon=True).start()

        elif custom_id == "btn_start":
            self.respond_interaction(interaction_id, interaction_token,
                content="▶ Memulai rejoin...", ephemeral=True)
            def _start():
                ok, msg = start_rejoin()
                self.edit_interaction_response(interaction_token, 
                    content=f"{'▶' if ok else '❌'} {msg}")
                time.sleep(2); self.refresh_panel()
            threading.Thread(target=_start, daemon=True).start()

        elif custom_id == "btn_stop":
            # Respond DULU sebelum eksekusi!
            try:
                self.respond_interaction(interaction_id, interaction_token,
                    content="⏹ Menghentikan rejoin...", ephemeral=True)
            except: pass

            def _stop(token):
                ok, msg = stop_rejoin()
                self.edit_interaction_response(token, content=f"{'✅' if ok else '❌'} {msg}")
                time.sleep(3); self.refresh_panel()
            threading.Thread(target=_stop, args=(interaction_token,), daemon=True).start()

        elif custom_id == "btn_detect_pkg":
            # Beri feedback langsung sebelum panggil thread
            try:
                self.respond_interaction(interaction_id, interaction_token,
                    content="🔍 Memindai package Roblox...", ephemeral=True)
            except:
                pass

            def _detect(token):
                cfg = load_main_cfg()
                current_pkgs = cfg.get("packages", [])
                current_ps   = cfg.get("ps_links", {})
                
                new_pkgs = find_installed_pkgs()
                if new_pkgs:
                    cfg["packages"] = new_pkgs
                    if "ps_links" not in cfg: cfg["ps_links"] = {}
                    if "usernames" not in cfg: cfg["usernames"] = {}
                    
                    results = []
                    for p in new_pkgs:
                        # 1. Deteksi Username
                        cookie = find_cookie_for_pkg(p)
                        uname = get_username_from_cookie(cookie) if cookie else "Guest/Lobby"
                        
                        # Simpan ke config untuk fallback
                        cfg["usernames"][p] = uname
                        
                        res_line = f"📦 `{p}`\n👤 **{uname}**"
                        
                        # 2. Cek PS Link (Paling penting: Preserve if exists!)
                        if p in current_ps:
                            res_line += " (✅ PS Link Tersimpan)"
                        else:
                            res_line += " (❌ PS Link Belum Ada)"
                        
                        results.append(res_line)
                    
                    try:
                        with open(str(CONFIG_FILE), "w") as f:
                            json.dump(cfg, f, indent=2)
                        
                        res_text = "\n".join(results)
                        self.edit_interaction_response(token, content=f"🔍 **Pencarian Selesai!**\n\n{res_text}\n\n*Jika PS Link kosong, gunakan !ps atau tombol Set PS Link.*")
                    except Exception as e:
                        self.edit_interaction_response(token, content=f"❌ Gagal simpan config: {e}")
                else:
                    self.edit_interaction_response(token, content="❌ Tidak ditemukan satu pun package Roblox!")
                self.refresh_panel()
            
            # Gunakan threading untuk proses scan yang lama agar tidak timeout
            t = threading.Thread(target=_detect, args=(interaction_token,), daemon=True)
            t.start()

        elif custom_id == "btn_status":
            status = load_status()
            cfg    = load_main_cfg()
            running = is_rejoin_running()

            lines = [f"**Status:** {'🟢 Running' if running else '🔴 Stopped'}"]
            lines.append(f"**PS Link:** `{cfg.get('global_ps_link','(kosong)')[:60]}`")
            lines.append("")
            if status:
                for s in status:
                    icon = "🟢" if "Running" in s.get("status","") or "In-game" in s.get("status","") else "🔴"
                    lines.append(f"{icon} `{s.get('pkg','?')}`")
                    lines.append(f"   Status: {s.get('status','?')}")
                    lines.append(f"   Rejoin: {s.get('rejoin',0)}x")
            else:
                lines.append("Belum ada data status.")

            embed = {
                "title": "📊 Status Sekarang",
                "description": "\n".join(lines),
                "color": 0x3498db,
                "footer": {"text": time.strftime('%d/%m/%Y %H:%M:%S')},
            }
            self.respond_interaction(
                interaction_id, interaction_token,
                embeds=[embed], ephemeral=True
            )

        elif custom_id == "btn_config":
            cfg = load_main_cfg()
            pkgs     = cfg.get("packages", [])
            ps_link  = cfg.get("global_ps_link", "(kosong)")
            interval = cfg.get("check_interval", 35)
            delay    = cfg.get("restart_delay", 10)
            webhook  = cfg.get("webhook_url", "")
            floating = cfg.get("floating_window", True)
            mute     = cfg.get("auto_mute", True)
            lowgfx   = cfg.get("auto_low_graphics", True)
            auto_tap = cfg.get("auto_tap_splash", True)
            ae_delay = cfg.get("autoexec_delay", 30)
            ae_script= cfg.get("autoexec_script", "")

            on  = "✅ ON"
            off = "❌ OFF"

            lines = [
                f"**Packages ({len(pkgs)}):**",
            ]
            for p in pkgs:
                ps = cfg.get("ps_links", {}).get(p, ps_link)
                lines.append(f"  • `{p}`")
                lines.append(f"    PS: `{ps[:50]}`")
            lines += [
                "",
                f"**PS Link Global:** `{ps_link[:60]}`",
                f"**Check Interval:** {interval}s",
                f"**Restart Delay:** {delay}s",
                f"**Load Delay:** {cfg.get('load_delay',40)}s",
                f"**Webhook:** {'Ada ✅' if webhook else 'Kosong ❌'}",
                "",
                f"**Floating Window:** {on if floating else off}",
                f"**Auto Mute:** {on if mute else off}",
                f"**Low Grafik:** {on if lowgfx else off}",
                f"**Auto Tap Splash:** {on if auto_tap else off}",
                "",
                f"**AutoExec Delay:** {ae_delay}s",
                f"**AutoExec Script:** {'Ada ✅' if ae_script else 'Kosong ❌'}",
            ]
            embed = {
                "title": "⚙️ Config Saat Ini",
                "description": "\n".join(lines),
                "color": 0x9b59b6,
                "footer": {"text": time.strftime('%d/%m/%Y %H:%M:%S')},
            }
            self.respond_interaction(
                interaction_id, interaction_token,
                embeds=[embed], ephemeral=True
            )

        elif custom_id == "btn_ss":
            try:
                self.respond_interaction(interaction_id, interaction_token,
                    content="📸 Mengambil screenshot...", ephemeral=True)
            except: pass

            def _ss(token):
                ss_path = take_screenshot()
                if ss_path:
                    # Discord follow-up webhooks support files and stay ephemeral if original was
                    url = f"{DISCORD_API}/webhooks/{self.token.split('.')[0]}/{token}"
                    with open(ss_path, "rb") as f:
                        requests.post(url, 
                                     data={"payload_json": json.dumps({"content": "📸 Screenshot sekarang:", "flags": 64})},
                                     files={"file": ("ss.png", f, "image/png")})
                else:
                    self.edit_interaction_response(token, content="❌ Gagal ambil screenshot (butuh root)")
            threading.Thread(target=_ss, args=(interaction_token,), daemon=True).start()

        elif custom_id == "btn_log":
            log_text = get_last_log(20)
            embed = {
                "title": "📜 Log Aktivitas (20 baris terakhir)",
                "description": f"```\n{log_text[:3900]}\n```",
                "color": 0x95a5a6,
                "footer": {"text": time.strftime('%d/%m/%Y %H:%M:%S')},
            }
            self.respond_interaction(
                interaction_id, interaction_token,
                embeds=[embed], ephemeral=True
            )

        elif custom_id == "btn_set_ps":
            components = [
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 2,
                            "label": "🌏 Set Global PS",
                            "style": 1,
                            "custom_id": "btn_set_global",
                        },
                        {
                            "type": 2,
                            "label": "📦 Set Per Package",
                            "style": 2,
                            "custom_id": "btn_set_per_pkg",
                        },
                    ]
                }
            ]
            self.respond_interaction(
                interaction_id, interaction_token,
                content="Pilih jenis PS Link yang ingin diset:",
                components=components,
                ephemeral=True
            )

        elif custom_id == "btn_set_global":
            self.respond_modal(
                interaction_id, interaction_token,
                "modal_set_global", "Set Global PS Link",
                [
                    {
                        "type": 1,
                        "components": [
                            {
                                "type": 4,
                                "custom_id": "ps_link",
                                "label": "Link atau Place ID",
                                "style": 1,
                                "placeholder": "18970406828",
                                "required": True
                            }
                        ]
                    }
                ]
            )

        elif custom_id == "btn_set_per_pkg":
            cfg = load_main_cfg()
            pkgs = cfg.get("packages", [])
            self.respond_modal(
                interaction_id, interaction_token,
                "modal_set_per_pkg", "Set PS Link per Package",
                [
                    {
                        "type": 1,
                        "components": [
                            {
                                "type": 4,
                                "custom_id": "pkg_name",
                                "label": "Nama Package",
                                "style": 1,
                                "placeholder": "com.roblox.client",
                                "value": pkgs[0] if pkgs else "",
                                "required": True
                            }
                        ]
                    },
                    {
                        "type": 1,
                        "components": [
                            {
                                "type": 4,
                                "custom_id": "ps_link",
                                "label": "Link atau Place ID",
                                "style": 1,
                                "placeholder": "18970406828",
                                "required": True
                            }
                        ]
                    }
                ]
            )

        elif custom_id == "btn_remove_ae":
            import subprocess
            folder = "/storage/emulated/0/Delta/Autoexecute"
            r = subprocess.run(["su", "-c", f"ls -1 {folder}/*.lua 2>/dev/null"], capture_output=True, text=True)
            files = [f.strip().split('/')[-1] for f in r.stdout.splitlines() if f.strip()]
            
            if not files:
                self.respond_interaction(interaction_id, interaction_token,
                    content="❌ **Tidak ada script AutoExecute yang ditemukan.**", ephemeral=True)
                return
                
            options = [{"label": f, "value": f} for f in files[:25]] # Select menu max 25 options
            
            self.respond_interaction(interaction_id, interaction_token,
                content="🗑️ **Pilih script yang ingin dihapus:**",
                components=[
                    {
                        "type": 1,
                        "components": [
                            {
                                "type": 3, # Select Menu
                                "custom_id": "select_delete_ae",
                                "placeholder": "Pilih script untuk dihapus...",
                                "options": options,
                                "min_values": 1,
                                "max_values": 1
                            }
                        ]
                    }
                ],
                ephemeral=True
            )

        elif custom_id == "select_delete_ae":
            # Values are in d["data"]["values"] for component interactions
            selected = data.get("data", {}).get("values", [])
            if not selected:
                # Fallback if structure varies
                selected = data.get("values", [])
                
            if not selected: return
            filename = selected[0]
            
            path = f"/storage/emulated/0/Delta/Autoexecute/{filename}"
            import subprocess
            r = subprocess.run(["su", "-c", f"rm '{path}'"], capture_output=True, text=True)
            
            if r.returncode == 0:
                self.respond_interaction(interaction_id, interaction_token,
                    content=f"✅ **Script `{filename}` telah dihapus!**", ephemeral=True)
            else:
                self.respond_interaction(interaction_id, interaction_token,
                    content=f"❌ **Gagal menghapus script:**\n`{r.stderr or r.stdout}`", ephemeral=True)

        elif custom_id == "btn_script":
            self.respond_modal(
                interaction_id, interaction_token,
                "modal_run_script", "Run Lua Script",
                [
                    {
                        "type": 1,
                        "components": [
                            {
                                "type": 4,
                                "custom_id": "script_code",
                                "label": "Kode Lua",
                                "style": 2, # Text Area
                                "placeholder": "print('hello')",
                                "required": True
                            }
                        ]
                    }
                ]
            )

        elif custom_id == "btn_add_autoexec":
            self.respond_modal(
                interaction_id, interaction_token,
                "modal_add_autoexec", "Add AutoExecute Script",
                [
                    {
                        "type": 1,
                        "components": [
                            {
                                "type": 4,
                                "custom_id": "filename",
                                "label": "Nama File (tanpa .lua)",
                                "style": 1,
                                "placeholder": "myscript",
                                "required": True
                            }
                        ]
                    },
                    {
                        "type": 1,
                        "components": [
                            {
                                "type": 4,
                                "custom_id": "script_content",
                                "label": "Script Content",
                                "style": 2,
                                "placeholder": "print('Hello AutoExecute')",
                                "required": True
                            }
                        ]
                    }
                ]
            )

        elif custom_id == "btn_refresh":
            # Respond dulu dengan update panel langsung (type 7 = update message)
            embed      = self.build_panel_embed()
            components = self.build_main_buttons()
            payload = {
                "type": 7,  # UPDATE_MESSAGE — langsung update panel
                "data": {
                    "embeds":     [embed],
                    "components": components,
                }
            }
            url = f"{DISCORD_API}/interactions/{interaction_id}/{interaction_token}/callback"
            try:
                requests.post(url, headers=self.headers, json=payload, timeout=10)
            except:
                pass

    def handle_modal_submit(self, data):
        """Handle data dari input box (modal)."""
        interaction_id    = data.get("id")
        interaction_token = data.get("token")
        custom_id         = data.get("data", {}).get("custom_id", "")
        components        = data.get("data", {}).get("components", [])
        
        # Extract values
        values = {}
        for row in components:
            for c in row.get("components", []):
                values[c.get("custom_id")] = c.get("value")

        if custom_id == "modal_add_autoexec":
            name = values.get("filename", "").strip()
            content = values.get("script_content", "")
            if name and content:
                if not name.endswith(".lua"):
                    name += ".lua"
                
                # Sesuai path di gambar: /storage/emulated/0/Delta/Autoexecute
                folder_path = "/storage/emulated/0/Delta/Autoexecute"
                path        = f"{folder_path}/{name}"
                escaped     = content.replace("'", "'\\''")
                
                # Buat folder jika belum ada, masukkan content, chmod
                cmd = f"mkdir -p '{folder_path}' && printf '%s' '{escaped}' > '{path}' && chmod 666 '{path}'"
                
                try:
                    import subprocess
                    r = subprocess.run(["su", "-c", cmd], capture_output=True, text=True, timeout=10)
                    if r.returncode == 0:
                        self.respond_interaction(interaction_id, interaction_token,
                            content=f"✅ **AutoExecute saved!**\n📁 Path: `{path}`", ephemeral=True)
                    else:
                        self.respond_interaction(interaction_id, interaction_token,
                            content=f"❌ **Gagal simpan (Root error):**\n`{r.stderr or r.stdout}`", ephemeral=True)
                except Exception as e:
                    self.respond_interaction(interaction_id, interaction_token,
                        content=f"❌ **Error:** {e}", ephemeral=True)
            return

        if custom_id == "modal_set_global":
            link = values.get("ps_link", "").strip()
            if link:
                # Format otomatis jika cuma angka
                if link.isdigit():
                    link = f"roblox://placeId={link}"
                
                cfg = load_main_cfg()
                cfg["global_ps_link"] = link
                try:
                    with open(str(CONFIG_FILE), "w") as f:
                        json.dump(cfg, f, indent=2)
                    self.respond_interaction(interaction_id, interaction_token,
                        content=f"✅ Global PS Link set ke:\n{link}", ephemeral=True)
                    time.sleep(2); self.refresh_panel()
                except Exception as e:
                    self.respond_interaction(interaction_id, interaction_token,
                        content=f"❌ Gagal simpan config: {e}", ephemeral=True)

        elif custom_id == "modal_set_per_pkg":
            pkg  = values.get("pkg_name")
            link = values.get("ps_link", "").strip()
            if pkg and link:
                # Format otomatis jika cuma angka
                if link.isdigit():
                    link = f"roblox://placeId={link}"
                
                cfg = load_main_cfg()
                if "ps_links" not in cfg: cfg["ps_links"] = {}
                cfg["ps_links"][pkg] = link
                try:
                    with open(str(CONFIG_FILE), "w") as f:
                        json.dump(cfg, f, indent=2)
                    self.respond_interaction(interaction_id, interaction_token,
                        content=f"✅ PS Link untuk `{pkg}` set ke:\n{link}", ephemeral=True)
                    time.sleep(2); self.refresh_panel()
                except:
                    pass

        elif custom_id == "modal_edit_config":
            try:
                cfg = load_main_cfg()
                
                # Parse basic numeric fields
                try:
                    cfg["check_interval"] = int(values.get("check_interval", 35))
                    cfg["restart_delay"]  = int(values.get("restart_delay", 10))
                    cfg["load_delay"]     = int(values.get("load_delay", 40))
                except: pass
                
                cfg["webhook_url"] = values.get("webhook_url", "").strip()
                
                # Parse packages
                pkgs_raw = values.get("packages", "")
                cfg["packages"] = [p.strip() for p in pkgs_raw.split(",") if p.strip()]
                
                # Parse flags (T,T,T,T)
                flags_raw = values.get("flags", "T,T,T,T").split(",")
                if len(flags_raw) >= 4:
                    cfg["floating_window"]    = flags_raw[0].strip().upper() == "T"
                    cfg["auto_mute"]          = flags_raw[1].strip().upper() == "T"
                    cfg["auto_low_graphics"]  = flags_raw[2].strip().upper() == "T"
                    cfg["auto_tap_splash"]    = flags_raw[3].strip().upper() == "T"
                
                with open(str(CONFIG_FILE), "w") as f:
                    json.dump(cfg, f, indent=2)
                
                self.respond_interaction(interaction_id, interaction_token,
                    content="✅ Configuration updated successfully!", ephemeral=True)
                time.sleep(1); self.refresh_panel()
            except Exception as e:
                self.respond_interaction(interaction_id, interaction_token,
                    content=f"❌ Error updating config: {e}", ephemeral=True)

        elif custom_id == "modal_run_script":
            script = values.get("script_code")
            if script:
                try:
                    self.respond_interaction(interaction_id, interaction_token,
                        content="💉 Menjalankan script...", ephemeral=True)
                except: pass
                ok, msg = run_lua_script(script)
                self.edit_interaction_response(interaction_token, content=f"💉 {'✅' if ok else '❌'} Inject script:\n```\n{msg}\n```")

    def handle_message(self, data):
        """Handle pesan !script."""
        content   = data.get("content", "")
        author_id = data.get("author", {}).get("id", "")

        if self.owner_ids and author_id not in self.owner_ids:
            return

        if content.startswith("!script "):
            script_text = content[8:].strip()
            if script_text:
                ok, msg = run_lua_script(script_text)
                icon = "✅" if ok else "❌"
                self.send_message(content=f"💉 {icon} Inject script:\n```\n{msg}\n```")

        elif content.startswith("!ps "):
            args = content[4:].strip().split(None, 1)
            cfg  = load_main_cfg()
            
            if len(args) == 2:
                # Per package: !ps com.roblox.client <link>
                pkg, link = args[0], args[1]
                if "ps_links" not in cfg: cfg["ps_links"] = {}
                cfg["ps_links"][pkg] = link
                msg_txt = f"✅ PS Link untuk `{pkg}` set ke:\n`{link}`"
            elif len(args) == 1:
                # Global: !ps <link>
                link = args[0]
                cfg["global_ps_link"] = link
                msg_txt = f"✅ Global PS Link set ke:\n`{link}`"
            else:
                return

            try:
                with open(CONFIG_FILE, "w") as f:
                    json.dump(cfg, f, indent=2)
                self.send_message(content=msg_txt)
                time.sleep(2); self.refresh_panel()
            except Exception as e:
                self.send_message(content=f"❌ Gagal simpan: {e}")

        elif content == "!panel":
            self.send_panel()

        elif content == "!status":
            self.refresh_panel()

    def disconnect(self):
        """Hentikan bot dan loop."""
        self.is_running = False
        bot_log("Bot dimatikan (is_running = False)")

    def run_gateway(self):
        """Jalankan bot via Discord Gateway (WebSocket)."""
        try:
            import websocket
        except ImportError:
            print(f"{RE}Install websocket-client: pip install websocket-client{R}")
            sys.exit(1)

        import websocket as ws_lib

        # ── LOOP UTAMA RECONNECT ────────────────────────────────
        while self.is_running:
            gateway_url = self.get_gateway()
            if not gateway_url:
                print(f"{RE}Gagal ambil gateway URL! Reconnect dalam 10 detik...{R}")
                time.sleep(10)
                continue

            gateway_url += "?v=10&encoding=json"
            heartbeat_interval = None
            sequence           = None
            session_id         = None

            def on_open(ws):
                bot_log("WebSocket terhubung")

            def on_message(ws, message):
                nonlocal heartbeat_interval, sequence, session_id
                try:
                    data = json.loads(message)
                    op   = data.get("op")
                    d    = data.get("d", {})
                    t    = data.get("t")
                    s    = data.get("s")
                    if s:
                        sequence = s

                    # Op 10: Hello → kirim identify + start heartbeat
                    if op == 10:
                        heartbeat_interval = d.get("heartbeat_interval", 41250) / 1000

                        # Identify
                        identify_payload = {
                            "op": 2,
                            "d": {
                                "token":      self.token,
                                "intents":    513,  # GUILDS + GUILD_MESSAGES
                                "properties": {
                                    "os":      "android",
                                    "browser": "yurxz-bot",
                                    "device":  "yurxz-bot",
                                },
                            }
                        }
                        ws.send(json.dumps(identify_payload))

                        # Start heartbeat di thread terpisah
                        def heartbeat_loop():
                            while True:
                                time.sleep(heartbeat_interval)
                                try:
                                    ws.send(json.dumps({"op": 1, "d": sequence}))
                                except:
                                    break
                        threading.Thread(target=heartbeat_loop, daemon=True).start()

                    # Op 0: Event
                    elif op == 0:
                        if t == "READY":
                            session_id = d.get("session_id")
                            user = d.get("user", {})
                            bot_log(f"Login sebagai {user.get('username')}#{user.get('discriminator')}")
                            # Kirim panel HANYA 1x saat pertama connect
                            # Cari panel lama dulu, kalau ada edit, kalau tidak ada baru kirim
                            def _init_panel():
                                try:
                                    r = self.api("get", f"/channels/{self.channel_id}/messages?limit=20")
                                    if r and r.status_code == 200:
                                        for m in r.json():
                                            # Cari pesan panel lama milik bot (punya components)
                                            if (m.get("author", {}).get("bot") and
                                                    m.get("components") and m.get("embeds")):
                                                self.panel_msg_id = m["id"]
                                                self.refresh_panel()
                                                bot_log(f"Panel lama ditemukan, diupdate: {m['id']}")
                                                return
                                except:
                                    pass
                                # Tidak ada panel lama → kirim baru
                                self.send_panel()
                            threading.Thread(target=_init_panel, daemon=True).start()

                        elif t == "INTERACTION_CREATE":
                            itype = d.get("type")
                            if itype == 3:  # Component interaction (button)
                                threading.Thread(
                                    target=self.handle_interaction,
                                    args=(d,), daemon=True
                                ).start()
                            elif itype == 5:  # Modal submit
                                threading.Thread(
                                    target=self.handle_modal_submit,
                                    args=(d,), daemon=True
                                ).start()

                        elif t == "MESSAGE_CREATE":
                            # Hanya proses pesan dari channel yang dikonfigurasi
                            if str(d.get("channel_id")) == self.channel_id:
                                # Abaikan pesan dari bot sendiri
                                if not d.get("author", {}).get("bot"):
                                    threading.Thread(
                                        target=self.handle_message,
                                        args=(d,), daemon=True
                                    ).start()

                    # Op 11: Heartbeat ACK
                    elif op == 11:
                        pass

                except Exception as e:
                    bot_log(f"Error: {e}")

            def on_error(ws, error):
                bot_log(f"WS Error: {error}")

            def on_close(ws, code, msg):
                bot_log(f"WS Closed: {code}")
                if self.is_running:
                    bot_log("Reconnect dalam 10 detik...")
                    # Delay pemindahan ke loop berikutnya ada di main loop
                else:
                    bot_log("Koneksi ditutup secara graceful.")

            ws_app = ws_lib.WebSocketApp(
                gateway_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
            )

            # Panel refresh tiap 5 menit (edit panel yang ada, bukan kirim baru)
            cleanup_counter = 0
            def auto_refresh():
                nonlocal cleanup_counter
                while self.is_running:
                    time.sleep(300)  # 5 menit
                    try:
                        if self.panel_msg_id:
                            self.refresh_panel()  # edit saja, tidak kirim baru
                        cleanup_counter += 1
                        if cleanup_counter >= 3:  # tiap 15 menit cleanup
                            self.cleanup_old_messages()
                            cleanup_counter = 0
                    except:
                        pass
            threading.Thread(target=auto_refresh, daemon=True).start()

            # Jalankan loop websocket secara blocking di main thread
            ws_app.run_forever(ping_interval=30, ping_timeout=10)
            bot_log("Websocket loop berhenti.")
            
            if not self.is_running:
                break
            time.sleep(10)

# ═══════════════════════════════════════════════════════
#  SETUP INTERAKTIF
# ═══════════════════════════════════════════════════════
def setup_bot():
    """Setup bot pertama kali."""
    print(f"\n{CY}+{'='*45}+{R}")
    print(f"{MG}  YURXZ Bot Setup{R}")
    print(f"{CY}+{'='*45}+{R}\n")

    cfg = load_bot_cfg()

    print(f"{YE}Cara buat bot Discord:{R}")
    print(f"  1. Buka https://discord.com/developers/applications")
    print(f"  2. New Application -> beri nama")
    print(f"  3. Bot -> Add Bot -> Copy Token")
    print(f"  4. Bot -> Aktifkan MESSAGE CONTENT INTENT")
    print(f"  5. OAuth2 -> URL Generator -> centang bot")
    print(f"     Permissions: Send Messages, Embed Links, Attach Files")
    print(f"  6. Copy Generated URL -> invite bot ke server\n")

    # Loop untuk Token
    while True:
        token = input(f"{YE}Masukkan Bot Token: {R}").strip()
        if token:
            break
        print(f"{RE}Token tidak boleh kosong! Silakan paste lagi.{R}")

    # Loop untuk Channel ID
    while True:
        channel_id = input(f"{YE}Masukkan Channel ID: {R}").strip()
        if channel_id:
            break
        # Jika paste token tadi mengandung newline, dia akan skip ke sini.
        # Kita beri peringatan dan minta input lagi.
        print(f"{RE}Channel ID tidak boleh kosong!{R}")

    owner_raw = input(f"{YE}Masukkan Owner ID kamu (opsional, pisah koma): {R}").strip()
    owner_ids = [x.strip() for x in owner_raw.split(",") if x.strip()]

    cfg["token"]      = token
    cfg["channel_id"] = channel_id
    cfg["owner_ids"]  = owner_ids
    save_bot_cfg(cfg)

    print(f"\n{GR}✓ Config bot tersimpan!{R}")
    print(f"{CY}Jalankan bot sekarang: python3 bot.py{R}\n")

# ═══════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════
def main():
    print(f"\n{CY}+{'='*45}+{R}")
    print(f"{MG}  YURXZ Rejoin Bot  by YURXZ{R}")
    print(f"{CY}+{'='*45}+{R}\n")

    cfg = load_bot_cfg()

    # Cek apakah perlu setup
    if not cfg.get("token") or not cfg.get("channel_id"):
        print(f"{YE}Bot belum dikonfigurasi. Jalankan setup dulu.{R}")
        setup_bot()
        cfg = load_bot_cfg()
        if not cfg.get("token"):
            return

    print(f"{GY}Token   : {cfg['token'][:20]}...{R}")
    print(f"{GY}Channel : {cfg['channel_id']}{R}")
    print(f"{GY}Owners  : {cfg.get('owner_ids', [])}{R}\n")

    import signal
    def handle_sigint(sig, frame):
        print(f"\n{YE}[Bot] Menutup koneksi...{R}")
        bot.disconnect()
        # Jika ditekan 2x, paksa exit
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_sigint)

    bot = DiscordBot(
        token      = cfg["token"],
        channel_id = cfg["channel_id"],
        owner_ids  = cfg.get("owner_ids", [])
    )

    print(f"{GR}[Bot] Connecting to Discord...{R}\n")
    
    # Initial refresh: ensures panel is up to date on start
    # We no longer auto-run tools on start; wait for Discord command.

    try:
        bot.run_gateway()
    except KeyboardInterrupt:
        pass
    print(f"\n{YE}[Bot] Dihentikan.{R}\n")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        setup_bot()
    else:
        main()
