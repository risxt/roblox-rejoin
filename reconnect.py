#!/usr/bin/env python3
"""
Roblox Auto-Reconnect Tool v2.0
For Cloud Phone (Redfinger, VMOS)

INSTALL:
    pkg update -y && pkg install python -y
    curl -sO https://raw.githubusercontent.com/risxt/roblox-rejoin/main/reconnect.py
    python reconnect.py
"""

import json
import time
import sys
import os
import subprocess
import re
from datetime import datetime

# ============ DEFAULT CONFIG ============
DEFAULT_CONFIG = {
    "place_id": "",
    "link_code": "",
    "packages": ["com.roblox.client"],
    "check_interval": 5,
    "launch_delay": 30
}

# ============ COLORS ============
class C:
    R = '\033[91m'
    G = '\033[92m'
    Y = '\033[93m'
    B = '\033[94m'
    N = '\033[96m'
    X = '\033[0m'
    BOLD = '\033[1m'

# ============ GLOBALS ============
running = True
stats = {}

# ============ HELPER FUNCTIONS ============
def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    colors = {"INFO": C.B, "OK": C.G, "WARN": C.Y, "ERR": C.R, "CRASH": C.R + C.BOLD}
    c = colors.get(level, C.X)
    print(f"{C.N}[{ts}]{C.X} {c}[{level}]{C.X} {msg}")

def run_cmd(cmd):
    """Run shell command with root"""
    try:
        result = subprocess.run(f'su -c "{cmd}"', shell=True, capture_output=True, text=True, timeout=15)
        return result.returncode == 0, result.stdout.strip()
    except:
        return False, ""

def banner():
    print(f"""
{C.N}{C.BOLD}
╔═══════════════════════════════════════╗
║   ROBLOX AUTO-RECONNECT TOOL v2.0     ║
╠═══════════════════════════════════════╣
║  For Cloud Phone (Redfinger/VMOS)     ║
╚═══════════════════════════════════════╝{C.X}
    """)

# ============ URL PARSER ============
def parse_url(url):
    """Extract PlaceID and LinkCode from URL"""
    patterns = [
        r'games/(\d+).*?privateServerLinkCode=([A-Za-z0-9_-]+)',
        r'placeId=(\d+).*?launchData=([A-Za-z0-9_-]+)',
        r'games/(\d+).*?code=([A-Za-z0-9_-]+)',
    ]
    for p in patterns:
        m = re.search(p, url, re.IGNORECASE)
        if m:
            return m.group(1), m.group(2)
    return None, None

# ============ CONFIG ============
def load_config():
    if os.path.exists("config.json"):
        try:
            with open("config.json") as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(config):
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)
    print(f"{C.G}[✓] Config saved to config.json{C.X}")

# ============ PROCESS CHECK ============
def is_running(package):
    """Check if package is running using multiple methods"""
    # Method 1: pgrep
    ok, out = run_cmd(f"pgrep -f {package}")
    if ok and out:
        return True
    
    # Method 2: ps | grep
    ok, out = run_cmd(f"ps -A | grep {package}")
    if ok and out:
        return True
    
    # Method 3: pidof
    ok, out = run_cmd(f"pidof {package}")
    if ok and out:
        return True
    
    return False

# ============ LAUNCHER ============
def launch_game(package, place_id, link_code):
    """Launch Roblox to private server"""
    url = f"roblox://navigation/game?placeId={place_id}&launchData={link_code}"
    
    # Try direct activity launch first (bypass chooser)
    activity = f"{package}/com.roblox.client.startup.ActivitySplash"
    cmd = f'am start -n {activity} -a android.intent.action.VIEW -d "{url}"'
    
    log(f"Launching {package}...")
    ok, out = run_cmd(cmd)
    
    # Fallback to package-based launch
    if not ok or "Error" in out:
        log("Trying fallback launch...", "WARN")
        cmd = f'am start -a android.intent.action.VIEW -d "{url}" -p {package}'
        ok, out = run_cmd(cmd)
    
    if ok and "Error" not in out:
        log(f"✅ Launched {package}", "OK")
        return True
    else:
        log(f"❌ Failed to launch {package}", "ERR")
        return False

# ============ SETUP ============
def setup(config):
    print(f"\n{C.N}=== Setup ==={C.X}\n")
    
    # Private Server URL
    print(f"{C.Y}[1] Enter Private Server URL:{C.X}")
    url = input("    > ").strip()
    
    place_id, link_code = parse_url(url)
    if place_id and link_code:
        config["place_id"] = place_id
        config["link_code"] = link_code
        print(f"{C.G}    ✓ PlaceID: {place_id}{C.X}")
        print(f"{C.G}    ✓ LinkCode: {link_code[:15]}...{C.X}")
    else:
        print(f"{C.R}    ✗ Could not parse URL!{C.X}")
        return None
    
    # Packages
    print(f"\n{C.Y}[2] Enter package names (comma separated):{C.X}")
    print(f"    Example: com.roblox.clienv,com.roblox.clientw")
    pkg_input = input("    > ").strip()
    if pkg_input:
        config["packages"] = [p.strip() for p in pkg_input.split(",")]
        print(f"{C.G}    ✓ {len(config['packages'])} package(s) configured{C.X}")
    
    # Interval
    print(f"\n{C.Y}[3] Check interval seconds [{config['check_interval']}]:{C.X}")
    inp = input("    > ").strip()
    if inp.isdigit():
        config["check_interval"] = int(inp)
    
    # Delay
    print(f"\n{C.Y}[4] Launch delay seconds [{config['launch_delay']}]:{C.X}")
    inp = input("    > ").strip()
    if inp.isdigit():
        config["launch_delay"] = int(inp)
    
    # Save
    save_config(config)
    return config

# ============ MONITOR ============
def monitor(config):
    global running, stats
    
    packages = config["packages"]
    place_id = config["place_id"]
    link_code = config["link_code"]
    interval = config["check_interval"]
    delay = config["launch_delay"]
    
    # Init stats
    stats = {pkg: {"crashes": 0} for pkg in packages}
    
    print(f"\n{C.G}{C.BOLD}🚀 Starting monitor...{C.X}")
    print(f"   Monitoring {len(packages)} package(s)")
    print(f"   Interval: {interval}s | Delay: {delay}s")
    print(f"   Press Ctrl+C to stop\n")
    print(f"{C.N}{'='*50}{C.X}\n")
    
    # ===== INITIAL LAUNCH - Launch all apps at startup =====
    log("Launching all apps...", "INFO")
    for pkg in packages:
        launch_game(pkg, place_id, link_code)
        time.sleep(3)  # Small delay between launches
    
    log(f"All apps launched! Waiting {delay}s for load...", "OK")
    time.sleep(delay)
    print(f"{C.N}{'='*50}{C.X}\n")
    
    # ===== MONITOR LOOP =====
    while running:
        for pkg in packages:
            if not running:
                break
            
            if is_running(pkg):
                log(f"✓ {pkg} running", "INFO")
            else:
                stats[pkg]["crashes"] += 1
                log(f"💥 CRASH: {pkg} (#{stats[pkg]['crashes']})", "CRASH")
                
                if launch_game(pkg, place_id, link_code):
                    log(f"⏳ Waiting {delay}s for load...", "INFO")
                    time.sleep(delay)
        
        time.sleep(interval)

# ============ MAIN ============
def main():
    global running
    
    banner()
    
    # Check root
    log("Checking root access...")
    ok, out = run_cmd("id")
    if ok and "uid=0" in out:
        log("Root access confirmed!", "OK")
    else:
        log("Root access not available!", "ERR")
        print(f"{C.R}Please enable root and try again.{C.X}")
        sys.exit(1)
    
    # Android optimization
    log("Applying Android optimizations...")
    run_cmd("device_config set_sync_disabled_for_tests persistent")
    run_cmd("device_config put activity_manager max_phantom_processes 2147483647")
    log("Optimizations applied", "OK")
    
    # Load config - NO PROMPTS, just load!
    if not os.path.exists("config.json"):
        print(f"\n{C.R}[!] config.json not found!{C.X}")
        print(f"{C.Y}    Create config.json with this format:{C.X}")
        print(f'''
{{
  "place_id": "YOUR_PLACE_ID",
  "link_code": "YOUR_PRIVATE_SERVER_CODE",
  "packages": ["com.roblox.client1", "com.roblox.client2"],
  "check_interval": 5,
  "launch_delay": 30
}}
        ''')
        print(f"{C.Y}    Use: nano config.json{C.X}")
        sys.exit(1)
    
    config = load_config()
    
    # Validate config
    if not config.get("place_id") or not config.get("link_code"):
        print(f"{C.R}[!] Invalid config! Edit config.json with nano{C.X}")
        sys.exit(1)
    
    # Show config
    print(f"\n{C.G}[✓] Config loaded:{C.X}")
    print(f"    PlaceID:  {config['place_id']}")
    print(f"    Packages: {', '.join(config['packages'])}")
    print(f"    Interval: {config['check_interval']}s")
    print(f"    Delay:    {config['launch_delay']}s")
    
    # Start monitor directly - NO PROMPTS!
    try:
        monitor(config)
    except KeyboardInterrupt:
        running = False
        print(f"\n\n{C.Y}🛑 Stopped{C.X}")
        print(f"\n{C.N}📊 Stats:{C.X}")
        for pkg, s in stats.items():
            print(f"   {pkg}: {s['crashes']} crash(es)")
        print(f"\n{C.G}Goodbye! 👋{C.X}\n")

if __name__ == "__main__":
    main()
