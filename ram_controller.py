#!/usr/bin/env python3
"""
RAM Auto-Rejoin Controller v1.0
Control Roblox Account Manager via Web Server API

Features:
- Uses RAM's built-in Web Server
- Select accounts from RAM
- Launch to game/private server
- Monitor and auto-rejoin

REQUIREMENTS:
- Roblox Account Manager installed
- Web Server enabled in RAM settings
- Accounts already saved in RAM

USAGE:
    pip install requests psutil
    python ram_controller.py
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
    "ram_path": r"C:\Users\faris\Downloads\Compressed\Roblox.Account.Manager.3.7.2_2",
    "ram_exe": "Roblox Account Manager.backup.exe",
    "webserver_port": 7963,
    "place_id": 121864768012064,
    "job_id": "",
    "check_interval": 60,
    "accounts_to_launch": []  # Empty = launch all, or specify usernames
}

# ============ RAM WEB SERVER API ============
class RAMController:
    def __init__(self, port=7963):
        self.port = port
        self.base_url = f"http://localhost:{port}"
    
    def is_online(self):
        """Check if RAM Web Server is online"""
        try:
            r = requests.get(f"{self.base_url}/GetAccounts", timeout=5)
            return r.status_code == 200
        except:
            return False
    
    def get_accounts(self):
        """Get list of accounts from RAM"""
        try:
            r = requests.get(f"{self.base_url}/GetAccounts", timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get("Success"):
                    return data.get("Accounts", [])
            return []
        except Exception as e:
            print(f"{C.R}[!] Error getting accounts: {e}{C.X}")
            return []
    
    def launch_account(self, username, place_id, job_id=""):
        """Launch an account to a game"""
        try:
            url = f"{self.base_url}/LaunchAccount"
            params = {
                "Account": username,
                "PlaceId": place_id
            }
            if job_id:
                params["JobId"] = job_id
            
            r = requests.get(url, params=params, timeout=30)
            
            if r.status_code == 200:
                data = r.json()
                return data.get("Success", False), data.get("Message", "")
            else:
                return False, f"HTTP {r.status_code}"
                
        except Exception as e:
            return False, str(e)

# ============ RAM SETTINGS MANAGER ============
def enable_ram_webserver(ram_path):
    """Enable Web Server in RAM settings"""
    settings_path = os.path.join(ram_path, "RAMSettings.ini")
    
    if not os.path.exists(settings_path):
        print(f"{C.R}[!] RAMSettings.ini not found at {settings_path}{C.X}")
        return False
    
    try:
        with open(settings_path, 'r') as f:
            content = f.read()
        
        # Enable required settings
        changes = [
            ("EnableWebServer=false", "EnableWebServer=true"),
            ("AllowGetAccounts=false", "AllowGetAccounts=true"),
            ("AllowLaunchAccount=false", "AllowLaunchAccount=true"),
        ]
        
        modified = False
        for old, new in changes:
            if old in content:
                content = content.replace(old, new)
                modified = True
        
        if modified:
            with open(settings_path, 'w') as f:
                f.write(content)
            print(f"{C.G}[✓] RAM Web Server settings enabled{C.X}")
        else:
            print(f"{C.B}[*] RAM Web Server already enabled{C.X}")
        
        return True
        
    except Exception as e:
        print(f"{C.R}[!] Error modifying settings: {e}{C.X}")
        return False

def start_ram(ram_path, exe_name):
    """Start RAM application"""
    exe_path = os.path.join(ram_path, exe_name)
    
    if not os.path.exists(exe_path):
        # Try alternative name
        exe_path = os.path.join(ram_path, "Roblox Account Manager.exe")
    
    if not os.path.exists(exe_path):
        print(f"{C.R}[!] RAM executable not found{C.X}")
        return False
    
    try:
        subprocess.Popen(f'"{exe_path}"', cwd=ram_path, shell=True)
        print(f"{C.G}[✓] RAM started{C.X}")
        return True
    except Exception as e:
        print(f"{C.R}[!] Error starting RAM: {e}{C.X}")
        return False

def is_ram_running():
    """Check if RAM is running"""
    for proc in psutil.process_iter(['name']):
        try:
            name = proc.info['name']
            if name and 'roblox account manager' in name.lower():
                return True
        except:
            continue
    return False

# ============ PROCESS MONITOR ============
def get_roblox_player_count():
    """Count RobloxPlayerBeta.exe processes"""
    count = 0
    for proc in psutil.process_iter(['name']):
        try:
            name = proc.info['name']
            if name and name.lower() == 'robloxplayerbeta.exe':
                count += 1
        except:
            continue
    return count

# ============ MAIN LOGIC ============
def banner():
    print(f"""
{C.C}╔════════════════════════════════════════════╗
║   RAM AUTO-REJOIN CONTROLLER v1.0          ║
╠════════════════════════════════════════════╣
║   Control RAM via Web Server API           ║
║   No modifications to RAM required         ║
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
    
    inp = input(f"RAM Path [{config['ram_path']}]: ").strip()
    if inp:
        config['ram_path'] = inp
    
    inp = input(f"PlaceId [{config['place_id']}]: ").strip()
    if inp:
        config['place_id'] = int(inp)
    
    inp = input(f"JobId/PrivateServer link [{config.get('job_id', '')}]: ").strip()
    config['job_id'] = inp
    
    inp = input(f"Check Interval seconds [{config['check_interval']}]: ").strip()
    if inp:
        config['check_interval'] = int(inp)
    
    save_config(config)
    print(f"{C.G}\nConfig saved!{C.X}")
    return config

def main():
    banner()
    
    config = load_config()
    
    print(f"{C.B}[*] Current Config:{C.X}")
    print(f"    RAM Path: {config['ram_path']}")
    print(f"    PlaceId:  {config['place_id']}")
    print(f"    JobId:    {config.get('job_id', '') or '(random server)'}")
    print(f"    Interval: {config['check_interval']}s")
    
    inp = input(f"\n{C.Y}Edit config? (y/n): {C.X}").strip().lower()
    if inp == 'y':
        config = setup_interactive(config)
    
    ram_path = config['ram_path']
    place_id = config['place_id']
    job_id = config.get('job_id', '')
    interval = config.get('check_interval', 60)
    
    # Step 1: Enable Web Server in RAM settings
    print(f"\n{C.B}[1/4] Configuring RAM Web Server...{C.X}")
    enable_ram_webserver(ram_path)
    
    # Step 2: Start RAM if not running
    print(f"\n{C.B}[2/4] Checking RAM status...{C.X}")
    if not is_ram_running():
        print(f"{C.Y}    RAM not running, starting...{C.X}")
        start_ram(ram_path, config.get('ram_exe', 'Roblox Account Manager.backup.exe'))
    else:
        print(f"{C.G}    RAM already running{C.X}")
    
    # Step 3: Wait for Web Server
    print(f"\n{C.B}[3/4] Waiting for Web Server...{C.X}")
    ram = RAMController(config.get('webserver_port', 7963))
    
    max_retries = 30
    for i in range(max_retries):
        if ram.is_online():
            print(f"{C.G}    Web Server online!{C.X}")
            break
        print(f"    Waiting... ({i+1}/{max_retries})")
        time.sleep(2)
    else:
        print(f"{C.R}[!] Web Server not responding!{C.X}")
        print(f"{C.Y}    Make sure to enable Web Server in RAM:{C.X}")
        print(f"    Settings > Web Server tab > Enable Web Server")
        print(f"    Also enable: Allow GetAccounts, Allow LaunchAccount")
        return
    
    # Step 4: Get accounts
    print(f"\n{C.B}[4/4] Getting accounts from RAM...{C.X}")
    accounts = ram.get_accounts()
    
    if not accounts:
        print(f"{C.R}[!] No accounts found in RAM{C.X}")
        return
    
    print(f"{C.G}    Found {len(accounts)} accounts:{C.X}")
    for i, acc in enumerate(accounts):
        username = acc.get('Username', 'Unknown')
        print(f"      {i+1}. {username}")
    
    # Select accounts to launch
    specified = config.get('accounts_to_launch', [])
    if specified:
        accounts_to_launch = [a for a in accounts if a.get('Username') in specified]
    else:
        accounts_to_launch = accounts
    
    print(f"\n{C.Y}Will launch {len(accounts_to_launch)} account(s){C.X}")
    inp = input(f"{C.Y}Continue? (y/n): {C.X}").strip().lower()
    if inp != 'y':
        print("Cancelled.")
        return
    
    # Launch accounts
    print(f"\n{C.B}[*] Launching accounts...{C.X}")
    launched = 0
    
    for acc in accounts_to_launch:
        username = acc.get('Username', 'Unknown')
        print(f"{C.Y}    Launching {username}...{C.X}")
        
        success, msg = ram.launch_account(username, place_id, job_id)
        
        if success:
            print(f"{C.G}      ✓ {msg}{C.X}")
            launched += 1
        else:
            print(f"{C.R}      ✗ {msg}{C.X}")
        
        time.sleep(8)  # Delay between launches
    
    print(f"\n{C.G}[✓] Launched {launched}/{len(accounts_to_launch)} accounts!{C.X}")
    
    if launched == 0:
        print(f"{C.R}[!] No accounts launched successfully{C.X}")
        return
    
    # Monitor loop
    print(f"\n{C.G}[*] Starting monitor...{C.X}")
    print(f"{C.Y}[!] Press Ctrl+C to stop{C.X}\n")
    
    time.sleep(15)  # Wait for games to load
    
    total_rejoins = 0
    
    try:
        while True:
            current = get_roblox_player_count()
            now = datetime.now().strftime("%H:%M:%S")
            
            if current >= launched:
                print(f"{C.G}[✓] [{now}] {current}/{launched} instances running. Next check in {interval}s{C.X}")
            else:
                missing = launched - current
                print(f"{C.R}[!] [{now}] {current}/{launched} running. {missing} DC'd!{C.X}")
                
                if current == 0:
                    total_rejoins += 1
                    print(f"{C.Y}    Rejoining all accounts...{C.X}")
                    
                    for acc in accounts_to_launch:
                        username = acc.get('Username', 'Unknown')
                        print(f"{C.Y}      Rejoining {username}...{C.X}")
                        ram.launch_account(username, place_id, job_id)
                        time.sleep(8)
                    
                    print(f"{C.G}    Rejoin #{total_rejoins} complete{C.X}")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print(f"\n\n{C.Y}[*] Stopped. Total rejoins: {total_rejoins}{C.X}")

if __name__ == "__main__":
    main()
