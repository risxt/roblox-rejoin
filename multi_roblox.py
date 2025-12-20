#!/usr/bin/env python3
"""
Roblox Multi-Instance Tool v1.0
Launch multiple Roblox accounts and auto-rejoin

Features:
- Load cookies from file (1 per line)
- Launch multiple instances
- Monitor all instances
- Auto-rejoin when DC

USAGE:
    pip install requests psutil
    python multi_roblox.py
"""

import json
import time
import sys
import os
import subprocess
import threading
import requests
from datetime import datetime

try:
    import psutil
except ImportError:
    print("[!] Installing psutil...")
    os.system("pip install psutil")
    import psutil

# ============ COLORS ============
class C:
    R = '\033[91m'
    G = '\033[92m'
    Y = '\033[93m'
    B = '\033[94m'
    C = '\033[96m'
    X = '\033[0m'

if os.name == 'nt':
    os.system('color')

# ============ CONFIG ============
DEFAULT_CONFIG = {
    "place_id": 121864768012064,
    "job_id": "",
    "check_interval": 60,
    "launch_delay": 5,
    "rejoin_delay": 10,
    "cookies_file": "cookies.txt"
}

# ============ GLOBAL STATE ============
class Instance:
    def __init__(self, cookie, index):
        self.cookie = cookie
        self.index = index
        self.pid = None
        self.running = False
        self.rejoins = 0
        self.last_check = None
        self.username = f"Account_{index}"

instances = []
running = True

# ============ ROBLOX API ============
def get_auth_ticket(cookie):
    """Get authentication ticket using cookie"""
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", cookie, domain=".roblox.com")
    
    # Get CSRF token
    try:
        r = session.post("https://auth.roblox.com/v2/logout")
        csrf = r.headers.get("x-csrf-token", "")
    except:
        csrf = ""
    
    headers = {
        "x-csrf-token": csrf,
        "Referer": "https://www.roblox.com/"
    }
    
    try:
        r = session.post(
            "https://auth.roblox.com/v1/authentication-ticket/",
            headers=headers
        )
        
        if r.status_code == 403:
            csrf = r.headers.get("x-csrf-token", "")
            headers["x-csrf-token"] = csrf
            r = session.post(
                "https://auth.roblox.com/v1/authentication-ticket/",
                headers=headers
            )
        
        ticket = r.headers.get("rbx-authentication-ticket")
        return ticket
    except Exception as e:
        print(f"{C.R}[!] Auth error: {e}{C.X}")
        return None

def get_username(cookie):
    """Get username from cookie"""
    try:
        session = requests.Session()
        session.cookies.set(".ROBLOSECURITY", cookie, domain=".roblox.com")
        r = session.get("https://users.roblox.com/v1/users/authenticated")
        if r.status_code == 200:
            return r.json().get("name", "Unknown")
    except:
        pass
    return "Unknown"

# ============ LAUNCHER ============
def launch_roblox(place_id, job_id="", auth_ticket=None):
    """Launch Roblox with auth ticket"""
    
    # Build URL based on job_id type
    if job_id and ("roblox.com/share" in job_id or "ro.blox.com" in job_id):
        url = job_id
    elif job_id:
        url = f"roblox://placeId={place_id}&gameInstanceId={job_id}"
    else:
        url = f"roblox://placeId={place_id}"
    
    # Add auth ticket if available
    if auth_ticket:
        if "?" in url:
            url += f"&ticket={auth_ticket}"
        else:
            url += f"?ticket={auth_ticket}"
    
    try:
        # Launch via start command
        subprocess.Popen(f'start "" "{url}"', shell=True)
        return True
    except:
        return False

def get_roblox_pids():
    """Get all Roblox process IDs"""
    pids = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if 'roblox' in proc.info['name'].lower():
                pids.append(proc.info['pid'])
        except:
            continue
    return pids

def count_roblox_instances():
    """Count running Roblox instances"""
    return len(get_roblox_pids())

# ============ COOKIE MANAGER ============
def load_cookies(filepath):
    """Load cookies from file"""
    cookies = []
    if not os.path.exists(filepath):
        # Create sample file
        with open(filepath, 'w') as f:
            f.write("# Paste your cookies here, one per line\n")
            f.write("# Lines starting with # are comments\n")
            f.write("# Example:\n")
            f.write("# _|WARNING:-DO-NOT-SHARE-THIS...\n")
        return []
    
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                cookies.append(line)
    
    return cookies

# ============ MAIN LOGIC ============
def banner():
    print(f"""
{C.C}╔═══════════════════════════════════════════╗
║   ROBLOX MULTI-INSTANCE TOOL v1.0         ║
╠═══════════════════════════════════════════╣
║   Launch multiple accounts + Auto-Rejoin  ║
╚═══════════════════════════════════════════╝{C.X}
    """)

def load_config():
    if os.path.exists("config.json"):
        try:
            with open("config.json") as f:
                config = json.load(f)
                for key in DEFAULT_CONFIG:
                    if key not in config:
                        config[key] = DEFAULT_CONFIG[key]
                return config
        except:
            pass
    
    with open("config.json", "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    
    return DEFAULT_CONFIG

def save_config(config):
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)

def setup_interactive(config):
    print(f"\n{C.C}=== Setup ==={C.X}\n")
    
    inp = input(f"PlaceId [{config['place_id']}]: ").strip()
    if inp:
        config['place_id'] = int(inp)
    
    inp = input(f"JobId/PrivateServer URL [{config.get('job_id', '')}]: ").strip()
    config['job_id'] = inp
    
    inp = input(f"Check Interval seconds [{config['check_interval']}]: ").strip()
    if inp:
        config['check_interval'] = int(inp)
    
    inp = input(f"Delay between launches [{config['launch_delay']}]: ").strip()
    if inp:
        config['launch_delay'] = int(inp)
    
    inp = input(f"Cookies file [{config['cookies_file']}]: ").strip()
    if inp:
        config['cookies_file'] = inp
    
    save_config(config)
    print(f"{C.G}\nConfig saved!{C.X}")
    return config

def launch_all(config, cookies):
    """Launch all accounts"""
    global instances
    
    place_id = config['place_id']
    job_id = config.get('job_id', '')
    delay = config.get('launch_delay', 5)
    
    print(f"\n{C.B}[*] Launching {len(cookies)} accounts...{C.X}")
    
    for i, cookie in enumerate(cookies):
        inst = Instance(cookie, i + 1)
        
        # Get username
        username = get_username(cookie)
        inst.username = username
        
        print(f"{C.Y}[{i+1}/{len(cookies)}] Launching {username}...{C.X}")
        
        # Get auth ticket
        ticket = get_auth_ticket(cookie)
        
        if ticket:
            launch_roblox(place_id, job_id, ticket)
            inst.running = True
            print(f"{C.G}    ✓ Launched!{C.X}")
        else:
            print(f"{C.R}    ✗ Failed to get auth ticket{C.X}")
            # Try launching without ticket (will prompt login)
            launch_roblox(place_id, job_id)
        
        instances.append(inst)
        
        if i < len(cookies) - 1:
            print(f"{C.B}    Waiting {delay}s...{C.X}")
            time.sleep(delay)
    
    print(f"\n{C.G}[✓] All accounts launched!{C.X}")

def monitor_loop(config):
    """Monitor and auto-rejoin"""
    global running, instances
    
    place_id = config['place_id']
    job_id = config.get('job_id', '')
    interval = config.get('check_interval', 60)
    rejoin_delay = config.get('rejoin_delay', 10)
    expected = len(instances)
    
    print(f"\n{C.G}[*] Monitoring {expected} instances...{C.X}")
    print(f"{C.Y}[!] Press Ctrl+C to stop{C.X}\n")
    
    total_rejoins = 0
    
    try:
        while running:
            current = count_roblox_instances()
            now = datetime.now().strftime("%H:%M:%S")
            
            if current >= expected:
                print(f"{C.G}[✓] [{now}] All {current} instances running. Next check in {interval}s{C.X}")
            else:
                missing = expected - current
                total_rejoins += missing
                print(f"{C.R}[!] [{now}] {missing} instance(s) DC'd! Rejoining...{C.X}")
                
                time.sleep(rejoin_delay)
                
                # Rejoin missing instances
                for i in range(missing):
                    if i < len(instances):
                        inst = instances[i]
                        inst.rejoins += 1
                        print(f"{C.Y}    Rejoining {inst.username}...{C.X}")
                        ticket = get_auth_ticket(inst.cookie)
                        launch_roblox(place_id, job_id, ticket)
                        time.sleep(3)
                
                print(f"{C.G}    Done! Total rejoins: {total_rejoins}{C.X}")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        running = False
        print(f"\n\n{C.Y}[*] Stopped. Total rejoins: {total_rejoins}{C.X}")

def main():
    global running
    
    banner()
    
    config = load_config()
    
    # Load cookies
    cookies = load_cookies(config['cookies_file'])
    
    print(f"{C.B}[*] Current Config:{C.X}")
    print(f"    PlaceId:  {config['place_id']}")
    print(f"    JobId:    {config.get('job_id', '') or '(random)'}")
    print(f"    Interval: {config['check_interval']}s")
    print(f"    Cookies:  {len(cookies)} loaded from {config['cookies_file']}")
    
    if len(cookies) == 0:
        print(f"\n{C.R}[!] No cookies found!{C.X}")
        print(f"    Edit {config['cookies_file']} and add your cookies (1 per line)")
        print(f"    Then run this script again.")
        return
    
    inp = input(f"\n{C.Y}Edit config? (y/n): {C.X}").strip().lower()
    if inp == 'y':
        config = setup_interactive(config)
    
    # Launch all
    launch_all(config, cookies)
    
    # Start monitoring
    time.sleep(10)  # Wait for games to load
    monitor_loop(config)

if __name__ == "__main__":
    main()
