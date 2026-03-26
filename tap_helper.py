#!/usr/bin/env python3
"""
tap_helper.py — Smart splash tap via screencap + pixel detection
Pure Python built-in (zlib + struct), tanpa OpenCV.

Yang di-tap: tengah window Roblox (Please wait / loading dino)
Cara bawa foreground: am start via package name langsung
"""

import os, struct, zlib, subprocess, time, re

SS_PATH = "/data/local/tmp/yurxz_tap.png"

def _run(cmd, timeout=8):
    try:
        r = subprocess.run(["su", "-c", cmd],
                           capture_output=True, timeout=timeout)
        return r.returncode == 0, (r.stdout or b"").decode(errors="ignore")
    except:
        return False, ""

def bring_to_foreground(pkg):
    """
    Bawa window Roblox ke foreground.
    Coba beberapa cara dari yang paling reliable.
    """
    # Cara 1: am start dengan action MAIN
    ok, _ = _run(
        f"am start -a android.intent.action.MAIN"
        f" -c android.intent.category.LAUNCHER"
        f" -n {pkg}/com.roblox.client.ActivityProtocolLaunch 2>/dev/null; true"
    )
    time.sleep(0.15)

    # Cara 2: input keyevent HOME lalu buka lagi (kalau cara 1 gagal)
    # Cek apakah window sudah foreground
    ok2, out2 = _run(
        f"dumpsys window windows 2>/dev/null | grep mCurrentFocus | grep '{pkg}'"
    )
    if not ok2 or not out2.strip():
        _run(f"am start -n {pkg}/com.roblox.client.ActivityProtocolLaunch 2>/dev/null; true")
        time.sleep(0.15)

def get_window_bounds(pkg, sw, sh, index, total, do_float):
    """
    Dapatkan bounds window Roblox via dumpsys.
    Fallback ke grid kalau floating, atau fullscreen.
    """
    ok, out = _run(
        f"dumpsys window windows 2>/dev/null | grep -A15 '{pkg}' | grep -m1 'Frame:'"
    )
    if ok and out.strip():
        m = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', out)
        if m:
            x1, y1 = int(m.group(1)), int(m.group(2))
            x2, y2 = int(m.group(3)), int(m.group(4))
            if x2 > x1 + 50 and y2 > y1 + 50:
                return x1, y1, x2, y2

    # Fallback grid
    if do_float and total > 1:
        import math
        cols = math.ceil(math.sqrt(total))
        rows = math.ceil(total / cols)
        cw, ch = sw // cols, sh // rows
        r_idx = (index - 1) // cols
        c_idx = (index - 1) % cols
        return c_idx*cw, r_idx*ch, (c_idx+1)*cw, (r_idx+1)*ch

    return 0, 0, sw, sh

def smart_tap(pkg, win_x1, win_y1, win_x2, win_y2):
    """
    Tap tengah window Roblox.
    Bawa ke foreground dulu sebelum tap.
    Return (tap_x, tap_y, reason)
    """
    cx = (win_x1 + win_x2) // 2
    cy = (win_y1 + win_y2) // 2

    # Bawa ke foreground
    bring_to_foreground(pkg)

    # Tap tengah window
    _run(f"input tap {cx} {cy}")
    time.sleep(0.05)
    # Tap juga 70% dan 85% tinggi window (untuk berbagai posisi tombol/loading)
    _run(f"input tap {cx} {win_y1 + int((win_y2-win_y1)*0.70)}")
    time.sleep(0.05)
    _run(f"input tap {cx} {win_y1 + int((win_y2-win_y1)*0.85)}")

    return cx, cy, "center"


