#!/usr/bin/env python3
"""
Roblox Auto-Rejoin Tool v1.1
No login - just launch & monitor

INSTALL:
    pkg update -y && pkg install python -y
    curl -o rejoin.py https://raw.githubusercontent.com/risxt/roblox-rejoin/main/rejoin.py
    python rejoin.py
"""

import json
import time
import sys
import os
import subprocess

# ============ CONFIGURATION ============
DEFAULT_CONFIG = {
    "place_id": 121864768012064,
    "job_id": "",
    "package_name": "com.roblox.client",
    "activity_name": ".startup.ActivitySplash",
    "check_interval": 300,  # 5 minutes
    "rejoin_delay": 5
}

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
    # If job_id is a share link, use it directly
    if job_id and ("roblox.com/share" in job_id or "ro.blox.com" in job_id):
        # Private server link - launch with the link directly
        url = job_id
        print(f"[*] Launching with Private Server link...")
    elif job_id:
        # Regular job ID
        url = f"roblox://placeId={place_id}&gameInstanceId={job_id}"
    else:
        # Just place ID
        url = f"roblox://placeId={place_id}"
    
    # Method 1: am start with VIEW intent
    cmd = f'am start -a android.intent.action.VIEW -d "{url}"'
    
    try:
        print(f"[DEBUG] Running: {cmd}")
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if r.returncode == 0:
            print(f"[DEBUG] Success!")
            return True
        else:
            print(f"[DEBUG] Failed: {r.stderr}")
    except Exception as e:
        print(f"[DEBUG] Error: {e}")
    
    # Method 2: Try with package specified
    cmd2 = f'am start -a android.intent.action.VIEW -d "{url}" -p {package}'
    try:
        print(f"[DEBUG] Trying method 2: {cmd2}")
        r = subprocess.run(cmd2, shell=True, capture_output=True, text=True)
        return r.returncode == 0
    except:
        pass
    
    # Method 3: Just launch the app
    cmd3 = f'am start -n {package}/{activity}'
    try:
        print(f"[DEBUG] Trying method 3: {cmd3}")
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
║     ROBLOX AUTO-REJOIN TOOL v1.1      ║
╠═══════════════════════════════════════╣
║  Launch & Monitor - No Login Needed   ║
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
    
    print(f"{C.Y}[!] config.json created!{C.X}")
    print(f"{C.Y}    Edit place_id and package_name:{C.X}")
    print(f"{C.C}    nano config.json{C.X}")
    return DEFAULT_CONFIG

def setup_interactive(config):
    print(f"\n{C.C}=== Setup ==={C.X}\n")
    
    # Place ID
    inp = input(f"PlaceId [{config['place_id']}]: ").strip()
    if inp:
        config['place_id'] = int(inp)
    
    # Job ID
    inp = input(f"JobId (kosong = random) [{config['job_id']}]: ").strip()
    config['job_id'] = inp
    
    # Package
    inp = input(f"Package [{config['package_name']}]: ").strip()
    if inp:
        config['package_name'] = inp
    
    # Save
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"{C.G}Config saved!{C.X}")
    return config

def main():
    banner()
    
    config = load_config()
    
    # Show current config
    print(f"{C.B}[*] Current Config:{C.X}")
    print(f"    PlaceId:  {config['place_id']}")
    print(f"    JobId:    {config.get('job_id', '') or '(random)'}")
    print(f"    Package:  {config['package_name']}")
    print(f"    Interval: {config['check_interval']}s")
    
    # Ask to edit
    inp = input(f"\n{C.Y}Edit config? (y/n): {C.X}").strip().lower()
    if inp == 'y':
        config = setup_interactive(config)
    
    package = config['package_name']
    activity = config.get('activity_name', '.startup.ActivitySplash')
    place_id = config['place_id']
    job_id = config.get('job_id', '')
    interval = config.get('check_interval', 300)
    delay = config.get('rejoin_delay', 5)
    
    print(f"\n{C.G}[*] Starting...{C.X}")
    print(f"{C.Y}[!] Make sure you're already logged in to Roblox!{C.X}")
    print(f"{C.Y}[!] Press Ctrl+C to stop{C.X}\n")
    
    # Initial launch
    print(f"{C.B}[*] Launching game...{C.X}")
    launch_game(package, activity, place_id, job_id)
    time.sleep(10)
    
    rejoins = 0
    
    try:
        while True:
            if is_running(package):
                print(f"{C.G}[✓] Roblox running. Next check in {interval}s{C.X}")
            else:
                rejoins += 1
                print(f"{C.R}[!] DC detected! Rejoining... (#{rejoins}){C.X}")
                time.sleep(delay)
                launch_game(package, activity, place_id, job_id)
                time.sleep(10)
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print(f"\n\n{C.Y}[*] Stopped. Total rejoins: {rejoins}{C.X}")

if __name__ == "__main__":
    main()
