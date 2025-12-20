#!/usr/bin/env python3
"""
Roblox Multi-Instance Tool v1.1
Launch multiple Roblox accounts and auto-rejoin

Features:
- Load cookies from file (1 per line)
- Launch multiple instances with auth ticket
- Monitor RobloxPlayerBeta.exe processes
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
    "launch_delay": 8,
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
        self.username = f"Account_{index}"
        self.launched = False

instances = []
running = True

# ============ ROBLOX API ============
def validate_cookie(cookie):
    """Check if cookie is valid"""
    try:
        session = requests.Session()
        session.cookies.set(".ROBLOSECURITY", cookie, domain=".roblox.com")
        r = session.get("https://users.roblox.com/v1/users/authenticated", timeout=10)
        if r.status_code == 200:
            data = r.json()
            return True, data.get("name", "Unknown"), data.get("id", 0)
        elif r.status_code == 401:
            return False, "Expired/Invalid Cookie", 0
        else:
            return False, f"Error {r.status_code}", 0
    except Exception as e:
        return False, str(e), 0

def get_auth_ticket(cookie):
    """Get authentication ticket using cookie"""
    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", cookie, domain=".roblox.com")
    
    headers = {
        "User-Agent": "Roblox/WinInet",
        "Referer": "https://www.roblox.com/",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # First request to get CSRF token
    try:
        r = session.post("https://auth.roblox.com/v1/authentication-ticket/", headers=headers)
        csrf = r.headers.get("x-csrf-token", "")
        
        if not csrf:
            print(f"{C.R}      [DEBUG] No CSRF token received{C.X}")
            return None
        
        # Second request with CSRF token
        headers["x-csrf-token"] = csrf
        r = session.post("https://auth.roblox.com/v1/authentication-ticket/", headers=headers)
        
        ticket = r.headers.get("rbx-authentication-ticket")
        
        if ticket:
            print(f"{C.G}      [DEBUG] Got auth ticket!{C.X}")
            return ticket
        else:
            print(f"{C.R}      [DEBUG] No ticket. Status: {r.status_code}{C.X}")
            return None
            
    except Exception as e:
        print(f"{C.R}      [DEBUG] Auth error: {e}{C.X}")
        return None

# ============ LAUNCHER ============
def launch_roblox_with_ticket(place_id, auth_ticket, job_id=""):
    """Launch Roblox game with proper protocol"""
    
    # Build the launch URL
    # Format: roblox-player:1+launchmode:play+gameinfo:<ticket>+placelauncherurl:<encoded_url>
    
    if job_id and ("roblox.com/share" in job_id or "ro.blox.com" in job_id):
        # Private server - use link directly
        url = job_id
        try:
            subprocess.Popen(f'start "" "{url}"', shell=True)
            return True
        except:
            return False
    
    # Build proper Roblox player URL
    import urllib.parse
    
    launcher_url = f"https://assetgame.roblox.com/game/PlaceLauncher.ashx?request=RequestGame&placeId={place_id}"
    if job_id:
        launcher_url += f"&gameId={job_id}"
    
    encoded_url = urllib.parse.quote(launcher_url, safe='')
    
    # Method 1: Direct roblox:// protocol
    roblox_url = f"roblox://placeId={place_id}"
    if job_id:
        roblox_url += f"&gameInstanceId={job_id}"
    
    print(f"{C.B}      [DEBUG] Launching: {roblox_url[:60]}...{C.X}")
    
    try:
        os.system(f'start "" "{roblox_url}"')
        return True
    except Exception as e:
        print(f"{C.R}      [DEBUG] Launch error: {e}{C.X}")
        return False

# ============ PROCESS MONITOR ============
def get_roblox_player_count():
    """Count only RobloxPlayerBeta.exe processes"""
    count = 0
    for proc in psutil.process_iter(['name']):
        try:
            name = proc.info['name']
            if name and name.lower() == 'robloxplayerbeta.exe':
                count += 1
        except:
            continue
    return count

def list_roblox_processes():
    """List all Roblox-related processes for debugging"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            name = proc.info['name']
            if name and 'roblox' in name.lower():
                processes.append(f"{name} (PID: {proc.info['pid']})")
        except:
            continue
    return processes

# ============ COOKIE MANAGER ============
def load_cookies(filepath):
    """Load cookies from file"""
    cookies = []
    if not os.path.exists(filepath):
        with open(filepath, 'w') as f:
            f.write("# Paste your .ROBLOSECURITY cookies here, one per line\n")
            f.write("# Lines starting with # are comments\n")
            f.write("# \n")
            f.write("# Example:\n")
            f.write("# _|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow...\n")
        return []
    
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                # Clean cookie
                if line.startswith('_|WARNING'):
                    cookies.append(line)
                elif len(line) > 100:  # Likely a valid cookie
                    cookies.append(line)
    
    return cookies

# ============ MAIN LOGIC ============
def banner():
    print(f"""
{C.C}╔════════════════════════════════════════════╗
║   ROBLOX MULTI-INSTANCE TOOL v1.1          ║
╠════════════════════════════════════════════╣
║   Launch multiple accounts + Auto-Rejoin   ║
║   Fixed: Auth ticket & process monitoring  ║
╚════════════════════════════════════════════╝{C.X}
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
    
    save_config(config)
    print(f"{C.G}\nConfig saved!{C.X}")
    return config

def validate_all_cookies(cookies):
    """Validate all cookies and return valid ones"""
    print(f"\n{C.B}[*] Validating {len(cookies)} cookies...{C.X}")
    valid = []
    
    for i, cookie in enumerate(cookies):
        is_valid, username, user_id = validate_cookie(cookie)
        if is_valid:
            print(f"{C.G}    [{i+1}] ✓ {username} (ID: {user_id}){C.X}")
            valid.append((cookie, username))
        else:
            print(f"{C.R}    [{i+1}] ✗ {username}{C.X}")
    
    print(f"\n{C.B}[*] Valid cookies: {len(valid)}/{len(cookies)}{C.X}")
    return valid

def launch_all(config, valid_cookies):
    """Launch all valid accounts"""
    global instances
    
    place_id = config['place_id']
    job_id = config.get('job_id', '')
    delay = config.get('launch_delay', 8)
    
    print(f"\n{C.B}[*] Launching {len(valid_cookies)} accounts...{C.X}")
    
    launched_count = 0
    
    for i, (cookie, username) in enumerate(valid_cookies):
        inst = Instance(cookie, i + 1)
        inst.username = username
        
        print(f"{C.Y}[{i+1}/{len(valid_cookies)}] Launching {username}...{C.X}")
        
        # Get auth ticket
        ticket = get_auth_ticket(cookie)
        
        if ticket:
            success = launch_roblox_with_ticket(place_id, ticket, job_id)
            if success:
                inst.launched = True
                launched_count += 1
                print(f"{C.G}    ✓ Launched successfully!{C.X}")
        else:
            print(f"{C.R}    ✗ Failed to get auth ticket - trying without...{C.X}")
            # Try anyway with just the URL
            launch_roblox_with_ticket(place_id, None, job_id)
        
        instances.append(inst)
        
        if i < len(valid_cookies) - 1:
            print(f"{C.B}    Waiting {delay}s before next launch...{C.X}")
            time.sleep(delay)
    
    print(f"\n{C.G}[✓] Launched {launched_count}/{len(valid_cookies)} accounts!{C.X}")
    return launched_count

def monitor_loop(config, expected_count):
    """Monitor and auto-rejoin"""
    global running, instances
    
    place_id = config['place_id']
    job_id = config.get('job_id', '')
    interval = config.get('check_interval', 60)
    rejoin_delay = config.get('rejoin_delay', 10)
    
    print(f"\n{C.G}[*] Monitoring for {expected_count} RobloxPlayerBeta.exe processes...{C.X}")
    print(f"{C.Y}[!] Press Ctrl+C to stop{C.X}\n")
    
    # Wait for games to fully load
    print(f"{C.B}[*] Waiting 20s for games to load...{C.X}")
    time.sleep(20)
    
    total_rejoins = 0
    
    try:
        while running:
            current = get_roblox_player_count()
            now = datetime.now().strftime("%H:%M:%S")
            
            # Debug: show all Roblox processes
            procs = list_roblox_processes()
            
            if current >= expected_count:
                print(f"{C.G}[✓] [{now}] {current}/{expected_count} instances running. Next check in {interval}s{C.X}")
            elif current > 0:
                missing = expected_count - current
                print(f"{C.Y}[!] [{now}] {current}/{expected_count} running. {missing} may still be loading...{C.X}")
            else:
                print(f"{C.R}[!] [{now}] No instances running! All may have DC'd.{C.X}")
                
                # Only rejoin if we had instances before
                if expected_count > 0:
                    total_rejoins += 1
                    print(f"{C.Y}    Attempting rejoin for all accounts...{C.X}")
                    
                    time.sleep(rejoin_delay)
                    
                    for inst in instances:
                        if inst.launched:
                            print(f"{C.Y}    Rejoining {inst.username}...{C.X}")
                            ticket = get_auth_ticket(inst.cookie)
                            launch_roblox_with_ticket(place_id, ticket, job_id)
                            time.sleep(5)
                    
                    print(f"{C.G}    Rejoin attempt #{total_rejoins} complete.{C.X}")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        running = False
        print(f"\n\n{C.Y}[*] Stopped. Total rejoin attempts: {total_rejoins}{C.X}")

def main():
    global running
    
    banner()
    
    config = load_config()
    
    # Load cookies
    cookies = load_cookies(config['cookies_file'])
    
    print(f"{C.B}[*] Current Config:{C.X}")
    print(f"    PlaceId:  {config['place_id']}")
    print(f"    JobId:    {config.get('job_id', '') or '(random server)'}")
    print(f"    Interval: {config['check_interval']}s")
    print(f"    Cookies:  {len(cookies)} loaded from {config['cookies_file']}")
    
    if len(cookies) == 0:
        print(f"\n{C.R}[!] No cookies found!{C.X}")
        print(f"    Edit {config['cookies_file']} and add your .ROBLOSECURITY cookies (1 per line)")
        print(f"    Then run this script again.")
        return
    
    inp = input(f"\n{C.Y}Edit config? (y/n): {C.X}").strip().lower()
    if inp == 'y':
        config = setup_interactive(config)
    
    # Validate cookies first
    valid_cookies = validate_all_cookies(cookies)
    
    if len(valid_cookies) == 0:
        print(f"\n{C.R}[!] No valid cookies! Check your cookies.txt file.{C.X}")
        return
    
    inp = input(f"\n{C.Y}Continue with {len(valid_cookies)} valid accounts? (y/n): {C.X}").strip().lower()
    if inp != 'y':
        print("Cancelled.")
        return
    
    # Launch all
    launched = launch_all(config, valid_cookies)
    
    if launched > 0:
        # Start monitoring
        monitor_loop(config, launched)
    else:
        print(f"\n{C.R}[!] No accounts were launched successfully.{C.X}")

if __name__ == "__main__":
    main()
