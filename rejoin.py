#!/usr/bin/env python3
"""
Roblox Auto-Rejoin Tool v1.0
Single-file version for easy curl install

INSTALL:
    pkg update -y && pkg install python -y && pip install requests
    curl -o rejoin.py https://your-url/rejoin.py
    python rejoin.py

USAGE:
    python rejoin.py
"""

import json
import time
import sys
import os
import subprocess

# ============ CONFIGURATION ============
# Edit these values or create config.json

DEFAULT_CONFIG = {
    "accounts": [
        {"username": "YOUR_USERNAME", "password": "YOUR_PASSWORD"}
    ],
    "place_id": 121864768012064,
    "job_id": "",
    "package_name": "com.roblox.client",
    "activity_name": ".startup.ActivitySplash",
    "check_interval": 300,  # 5 minutes
    "rejoin_delay": 5
}

# ============ COLORS ============
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def cprint(text, color=Colors.RESET):
    print(f"{color}{text}{Colors.RESET}")

# ============ ROBLOX AUTH ============
import requests

class RobloxAuth:
    BASE_URL = "https://auth.roblox.com"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Roblox/Android",
            "Content-Type": "application/json"
        })
        self.cookie = None
        self.user_id = None
    
    def _get_csrf(self):
        try:
            r = self.session.post(f"{self.BASE_URL}/v2/login")
            if "x-csrf-token" in r.headers:
                self.session.headers["x-csrf-token"] = r.headers["x-csrf-token"]
        except:
            pass
    
    def login(self, username, password):
        self._get_csrf()
        
        try:
            r = self.session.post(
                f"{self.BASE_URL}/v2/login",
                json={"ctype": "Username", "cvalue": username, "password": password}
            )
            
            if r.status_code == 200:
                data = r.json()
                self.user_id = data.get("user", {}).get("id")
                for c in self.session.cookies:
                    if c.name == ".ROBLOSECURITY":
                        self.cookie = c.value
                return True, f"Login OK! UserID: {self.user_id}"
            
            elif r.status_code == 403:
                if "x-csrf-token" in r.headers:
                    self.session.headers["x-csrf-token"] = r.headers["x-csrf-token"]
                    return self.login(username, password)
            
            data = r.json()
            if "errors" in data:
                return False, data["errors"][0].get("message", "Unknown error")
            
            return False, f"Failed: {r.status_code}"
            
        except Exception as e:
            return False, str(e)
    
    def get_ticket(self):
        if not self.cookie:
            return False, "Not logged in"
        
        try:
            self._get_csrf()
            r = self.session.post(
                "https://auth.roblox.com/v1/authentication-ticket/",
                headers={"Referer": "https://www.roblox.com/"}
            )
            
            if r.status_code == 403 and "x-csrf-token" in r.headers:
                self.session.headers["x-csrf-token"] = r.headers["x-csrf-token"]
                return self.get_ticket()
            
            ticket = r.headers.get("rbx-authentication-ticket")
            return (True, ticket) if ticket else (False, "No ticket")
            
        except Exception as e:
            return False, str(e)

# ============ LAUNCHER ============
class Launcher:
    def __init__(self, package, activity):
        self.package = package
        self.activity = activity
    
    def launch(self, place_id, job_id=""):
        url = f"roblox://placeId={place_id}"
        if job_id:
            url += f"&gameInstanceId={job_id}"
        
        cmd = f'am start -a android.intent.action.VIEW -d "{url}" -n {self.package}/{self.activity}'
        
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return r.returncode == 0
        except:
            return False
    
    def stop(self):
        try:
            subprocess.run(f"am force-stop {self.package}", shell=True)
        except:
            pass

# ============ MONITOR ============
class Monitor:
    def __init__(self, package):
        self.package = package
    
    def is_running(self):
        try:
            r = subprocess.run(
                f"pgrep -f {self.package}",
                shell=True, capture_output=True, text=True
            )
            if r.returncode == 0 and r.stdout.strip():
                return True
            
            r = subprocess.run(
                f"ps -A | grep {self.package}",
                shell=True, capture_output=True, text=True
            )
            return bool(r.stdout.strip())
        except:
            return False

# ============ MAIN ============
def banner():
    b = """
╔═══════════════════════════════════════╗
║     ROBLOX AUTO-REJOIN TOOL v1.0      ║
╠═══════════════════════════════════════╣
║  Auto-rejoin when disconnected        ║
╚═══════════════════════════════════════╝
    """
    cprint(b, Colors.CYAN)

def load_config():
    if os.path.exists("config.json"):
        try:
            with open("config.json") as f:
                return json.load(f)
        except:
            pass
    
    # Create default config
    with open("config.json", "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    
    cprint("\n[!] config.json created!", Colors.YELLOW)
    cprint("    Edit it with your account details:", Colors.YELLOW)
    cprint("    nano config.json", Colors.CYAN)
    cprint("\n    Then run again: python rejoin.py\n", Colors.GREEN)
    sys.exit(0)

def main():
    banner()
    
    config = load_config()
    
    # Validate config
    acc = config["accounts"][0]
    if acc["username"] == "YOUR_USERNAME":
        cprint("[!] Please edit config.json first!", Colors.RED)
        cprint("    nano config.json", Colors.CYAN)
        sys.exit(1)
    
    # Init
    auth = RobloxAuth()
    launcher = Launcher(config["package_name"], config["activity_name"])
    monitor = Monitor(config["package_name"])
    
    # Login
    cprint(f"\n[*] Logging in as {acc['username']}...", Colors.BLUE)
    ok, msg = auth.login(acc["username"], acc["password"])
    
    if ok:
        cprint(f"[+] {msg}", Colors.GREEN)
    else:
        cprint(f"[-] Login failed: {msg}", Colors.RED)
        sys.exit(1)
    
    # Config
    place_id = config["place_id"]
    job_id = config.get("job_id", "")
    interval = config.get("check_interval", 300)
    delay = config.get("rejoin_delay", 5)
    
    cprint(f"\n[*] PlaceId: {place_id}", Colors.BLUE)
    cprint(f"[*] Package: {config['package_name']}", Colors.BLUE)
    cprint(f"[*] Check every: {interval}s ({interval//60}min)", Colors.BLUE)
    cprint(f"\n[*] Launching game...", Colors.YELLOW)
    
    # Initial launch
    launcher.launch(place_id, job_id)
    time.sleep(10)
    
    rejoins = 0
    cprint("\n[*] Monitoring started. Press Ctrl+C to stop.\n", Colors.GREEN)
    
    try:
        while True:
            if monitor.is_running():
                cprint(f"[✓] Roblox running. Next check in {interval}s", Colors.GREEN)
            else:
                rejoins += 1
                cprint(f"[!] DC detected! Rejoining... (#{rejoins})", Colors.RED)
                time.sleep(delay)
                
                # Get new ticket
                auth.get_ticket()
                
                # Relaunch
                launcher.launch(place_id, job_id)
                time.sleep(10)
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        cprint(f"\n\n[*] Stopped. Total rejoins: {rejoins}", Colors.YELLOW)

if __name__ == "__main__":
    main()
