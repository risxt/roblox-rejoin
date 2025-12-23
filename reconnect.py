#!/usr/bin/env python3
"""
Roblox Auto-Rejoin Tool v2.1
EXACT COPY dari reference script, dengan sedikit modifikasi

INSTALL:
    pkg update -y && pkg install python -y
    curl -o reconnect.py https://raw.githubusercontent.com/risxt/roblox-rejoin/main/reconnect.py
    python reconnect.py
"""

import json
import time
import sys
import os
import subprocess
from datetime import datetime

# ============ CONFIGURATION ============
DEFAULT_CONFIG = {
    "place_id": 121864768012064,
    "job_id": "45107399580631088032082953284064",
    "package_name": "com.roblox.clienv",
    "activity_name": ".startup.ActivitySplash",
    "check_interval": 5,
    "rejoin_delay": 30,
}

# ============ GLOBAL STATE ============
class State:
    running = True
    rejoins = 0
    start_time = None
    last_check = None
    roblox_running = False

state = State()

# ============ COLORS ============
class C:
    R = '\033[91m'
    G = '\033[92m'
    Y = '\033[93m'
    B = '\033[94m'
    C = '\033[96m'
    X = '\033[0m'

# ============ LAUNCHER ============
def launch_game(package, activity, place_id, job_id=""):
    """EXACT COPY from reference script"""
    if job_id and ("roblox.com/share" in job_id or "ro.blox.com" in job_id):
        url = job_id
    elif job_id:
        url = f"roblox://placeId={place_id}&linkCode={job_id}"
    else:
        url = f"roblox://placeId={place_id}"
    
    # Method 1: Direct am start
    cmd = f'am start -a android.intent.action.VIEW -d "{url}"'
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if r.returncode == 0:
            return True
    except:
        pass
    
    # Method 2: With package
    cmd2 = f'am start -a android.intent.action.VIEW -d "{url}" -p {package}'
    try:
        r = subprocess.run(cmd2, shell=True, capture_output=True, text=True)
        return r.returncode == 0
    except:
        pass
    
    # Method 3: Start activity directly
    cmd3 = f'am start -n {package}/{activity}'
    try:
        subprocess.run(cmd3, shell=True)
        return True
    except:
        return False

def stop_app(package):
    try:
        subprocess.run(f"am force-stop {package}", shell=True)
    except:
        pass

# ============ MONITOR ============
def is_running(package):
    """EXACT COPY from reference script"""
    try:
        r = subprocess.run(f"pgrep -f {package}", shell=True, capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return True
        r = subprocess.run(f"ps -A | grep {package}", shell=True, capture_output=True, text=True)
        return bool(r.stdout.strip())
    except:
        return False

# ============ MAIN ============
def banner():
    print(f"""
{C.C}╔═══════════════════════════════════════╗
║   ROBLOX AUTO-REJOIN TOOL v2.1        ║
╠═══════════════════════════════════════╣
║   EXACT COPY dari Reference Script    ║
╚═══════════════════════════════════════╝{C.X}
    """)

def load_config():
    if os.path.exists("config.json"):
        try:
            with open("config.json") as f:
                return json.load(f)
        except:
            pass
    
    with open("config.json", "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    
    print(f"{C.Y}[!] config.json created! Edit with nano config.json{C.X}")
    return DEFAULT_CONFIG

def main():
    banner()
    
    config = load_config()
    
    print(f"{C.B}[*] Current Config:{C.X}")
    print(f"    PlaceId:  {config['place_id']}")
    print(f"    JobId:    {config.get('job_id', '') or '(random)'}")
    print(f"    Package:  {config['package_name']}")
    print(f"    Interval: {config['check_interval']}s")
    
    package = config['package_name']
    activity = config.get('activity_name', '.startup.ActivitySplash')
    place_id = config['place_id']
    job_id = config.get('job_id', '')
    interval = config.get('check_interval', 5)
    delay = config.get('rejoin_delay', 30)
    
    state.start_time = datetime.now()
    
    print(f"\n{C.G}[*] Starting monitor...{C.X}")
    print(f"{C.Y}[!] Press Ctrl+C to stop{C.X}\n")
    
    # Initial launch
    print(f"{C.B}[*] Launching game...{C.X}")
    launch_game(package, activity, place_id, job_id)
    time.sleep(10)
    
    try:
        while state.running:
            state.last_check = datetime.now().strftime("%H:%M:%S")
            state.roblox_running = is_running(package)
            
            if state.roblox_running:
                print(f"{C.G}[{state.last_check}] ✓ Roblox running. Next check in {interval}s{C.X}")
            else:
                state.rejoins += 1
                print(f"{C.R}[{state.last_check}] 💥 DC detected! Rejoining... (#{state.rejoins}){C.X}")
                
                time.sleep(delay)
                launch_game(package, activity, place_id, job_id)
                time.sleep(10)
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        state.running = False
        print(f"\n\n{C.Y}[*] Stopped. Total rejoins: {state.rejoins}{C.X}")

if __name__ == "__main__":
    main()
