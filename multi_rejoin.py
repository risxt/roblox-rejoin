#!/usr/bin/env python3
"""
Multi-Instance Roblox Auto-Rejoin Tool v1.1
For Redfinger Cloud Phone with Freeform Window Support

Features:
- Auto-detect modded Roblox packages (com.roblox.clien1, clien2, etc.)
- Real-time TUI dashboard with username mapping
- Monitor all instances for crashes/disconnects
- Auto-rejoin disconnected instances

INSTALL:
    pkg update -y && pkg install python -y && pip install requests
    python multi_rejoin.py
"""

import json
import time
import subprocess
import requests
import re
import os
import sys
from datetime import datetime
from urllib.parse import quote, urlparse, parse_qs

# ============ CONFIGURATION ============
CONFIG_FILE = "multi_config.json"
DEFAULT_CONFIG = {
    "private_server_url": "",
    "check_interval": 60,
    "rejoin_delay": 5,
    "discord_webhook": "",
    "package_prefix": "com.roblox.clien",
    "activity_name": ".startup.ActivitySplash",
    "accounts": {}  # {"com.roblox.clien1": "Username1", ...}
}

# ============ COLORS ============
class C:
    R = '\033[91m'   # Red
    G = '\033[92m'   # Green
    Y = '\033[93m'   # Yellow
    B = '\033[94m'   # Blue
    M = '\033[95m'   # Magenta
    C = '\033[96m'   # Cyan
    W = '\033[97m'   # White
    X = '\033[0m'    # Reset
    BOLD = '\033[1m'
    DIM = '\033[2m'

# ============ GLOBAL STATE ============
class State:
    running = True
    instances = {}  # {package: {"running": bool, "rejoins": int, "username": str}}
    start_time = None
    total_rejoins = 0

state = State()

# ============ TERMINAL UTILITIES ============
def clear_screen():
    """Clear terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')

def move_cursor(row, col):
    """Move cursor to position"""
    print(f"\033[{row};{col}H", end="")

def clear_line():
    """Clear current line"""
    print("\033[2K", end="")

def get_ram_info():
    """Get free RAM in MB"""
    try:
        result = subprocess.run(
            "cat /proc/meminfo | grep MemAvailable",
            shell=True, capture_output=True, text=True
        )
        if result.stdout:
            # Parse "MemAvailable:    1234567 kB"
            match = re.search(r'(\d+)', result.stdout)
            if match:
                kb = int(match.group(1))
                return f"{kb // 1024}MB"
    except:
        pass
    return "N/A"

def format_uptime(start_time):
    """Format uptime as HH:MM:SS"""
    if not start_time:
        return "00:00:00"
    delta = datetime.now() - start_time
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

# ============ DISCORD WEBHOOK ============
def send_webhook(webhook_url, title, description, color=0x00ff00):
    """Send embed message to Discord webhook"""
    if not webhook_url:
        return False
    
    embed = {
        "title": title,
        "description": description,
        "color": color,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {"text": "Multi-Instance Rejoin v1.1"}
    }
    
    try:
        r = requests.post(webhook_url, json={"embeds": [embed]}, timeout=10)
        return r.status_code in [200, 204]
    except:
        return False

# ============ PACKAGE DETECTION ============
def detect_packages(prefix="com.roblox.clien"):
    """Auto-detect installed Roblox packages"""
    packages = []
    
    try:
        result = subprocess.run(
            f"pm list packages | grep {prefix}",
            shell=True, capture_output=True, text=True
        )
        
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line.startswith('package:'):
                    pkg = line.replace('package:', '').strip()
                    if pkg.startswith(prefix):
                        packages.append(pkg)
        
        def get_num(pkg):
            match = re.search(r'(\d+)$', pkg)
            return int(match.group(1)) if match else 0
        
        packages.sort(key=get_num)
        
    except Exception as e:
        pass
    
    return packages

# ============ URL PARSING ============
def parse_private_server_url(url):
    """Parse Roblox private server URL"""
    try:
        parsed = urlparse(url)
        path_parts = parsed.path.split('/')
        place_id = None
        for part in path_parts:
            if part.isdigit():
                place_id = part
                break
        
        params = parse_qs(parsed.query)
        link_code = params.get('privateServerLinkCode', [''])[0]
        
        return place_id, link_code
    except:
        return None, None

def build_deep_link(place_id, link_code):
    """Build Roblox deep link URL"""
    if link_code:
        launch_data = quote(f"privateServerLinkCode={link_code}")
        return f"roblox://experiences/start?placeId={place_id}&launchData={launch_data}"
    else:
        return f"roblox://placeId={place_id}"

# ============ LAUNCHER ============
def launch_game(package, deep_link, activity=".startup.ActivitySplash"):
    """Launch Roblox with deep link"""
    try:
        cmd = f'am start -a android.intent.action.VIEW -d "{deep_link}" -p {package}'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def force_stop(package):
    """Force stop a package"""
    try:
        subprocess.run(f"am force-stop {package}", shell=True, capture_output=True)
    except:
        pass

# ============ MONITOR ============
def is_running(package):
    """Check if a Roblox package is running using /proc/*/cmdline (only method that works on cloud phone)"""
    try:
        # This is the ONLY method that works on Redfinger cloud phone
        result = subprocess.run(
            f"cat /proc/*/cmdline 2>/dev/null | tr '\\0' '\\n' | grep -q {package} && echo FOUND",
            shell=True,
            capture_output=True,
            text=True
        )
        return "FOUND" in result.stdout
        
    except Exception as e:
        return False

# ============ TUI DASHBOARD ============
def draw_dashboard(packages, accounts, log_messages):
    """Draw the TUI dashboard"""
    clear_screen()
    
    # Header
    print(f"{C.C}{C.BOLD}╔══════════════════════════════════════════════════════════════╗")
    print(f"║          MULTI-INSTANCE ROBLOX MONITOR v1.1                  ║")
    print(f"╠══════════════════════════════════════════════════════════════╣{C.X}")
    
    # Table header
    print(f"{C.C}║  # │ {'PACKAGE':<22} │ {'USERNAME':<15} │ STATUS   ║{C.X}")
    print(f"{C.C}╠════╪════════════════════════╪═════════════════╪══════════╣{C.X}")
    
    # Table rows
    online_count = 0
    for i, pkg in enumerate(packages, 1):
        info = state.instances.get(pkg, {})
        running = info.get("running", False)
        username = accounts.get(pkg, f"Account{i}")[:15]
        
        if running:
            status = f"{C.G}● Online {C.X}"
            online_count += 1
        else:
            status = f"{C.R}● Offline{C.X}"
        
        # Truncate package name for display
        pkg_short = pkg[-22:] if len(pkg) > 22 else pkg
        
        print(f"{C.C}║{C.X} {i:2} │ {pkg_short:<22} │ {username:<15} │ {status}{C.C}║{C.X}")
    
    print(f"{C.C}╠══════════════════════════════════════════════════════════════╣{C.X}")
    
    # Stats bar
    ram = get_ram_info()
    uptime = format_uptime(state.start_time)
    print(f"{C.C}║{C.X} RAM: {C.G}{ram:<8}{C.X} │ Uptime: {C.Y}{uptime}{C.X} │ Rejoins: {C.M}{state.total_rejoins:<5}{C.X} {C.C}║{C.X}")
    print(f"{C.C}║{C.X} Status: {C.G}{online_count}/{len(packages)} Online{C.X}                                      {C.C}║{C.X}")
    print(f"{C.C}╠══════════════════════════════════════════════════════════════╣{C.X}")
    
    # Log section
    print(f"{C.C}║{C.X} {C.BOLD}MONITOR LOG:{C.X}                                                  {C.C}║{C.X}")
    print(f"{C.C}╠══════════════════════════════════════════════════════════════╣{C.X}")
    
    # Show last 5 log messages
    for msg in log_messages[-5:]:
        # Truncate message to fit
        msg_display = msg[:60] if len(msg) > 60 else msg
        print(f"{C.C}║{C.X} {msg_display:<60} {C.C}║{C.X}")
    
    # Fill remaining log lines
    for _ in range(5 - len(log_messages[-5:])):
        print(f"{C.C}║{C.X} {'':<60} {C.C}║{C.X}")
    
    print(f"{C.C}╚══════════════════════════════════════════════════════════════╝{C.X}")
    print(f"{C.DIM}Press Ctrl+C to stop{C.X}")

# ============ CONFIG ============
def load_config():
    """Load config from file"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                config = json.load(f)
                for key, val in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = val
                return config
        except:
            pass
    
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG.copy()

def save_config(config):
    """Save config to file"""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

# ============ INTERACTIVE SETUP ============
def setup_accounts(config, packages):
    """Setup username mapping for accounts"""
    print(f"\n{C.C}{'='*50}")
    print(f"         ACCOUNT USERNAME SETUP")
    print(f"{'='*50}{C.X}\n")
    
    accounts = config.get('accounts', {})
    
    for pkg in packages:
        current = accounts.get(pkg, '')
        prompt = f"Username for {pkg}"
        if current:
            prompt += f" [{current}]"
        prompt += ": "
        
        inp = input(prompt).strip()
        if inp:
            accounts[pkg] = inp
        elif not current:
            # Auto-generate based on package number
            match = re.search(r'(\d+)$', pkg)
            num = match.group(1) if match else '?'
            accounts[pkg] = f"Account{num}"
    
    config['accounts'] = accounts
    save_config(config)
    print(f"\n{C.G}[✓] Accounts saved!{C.X}")
    return config

def setup_interactive(config, packages):
    """Interactive setup wizard"""
    print(f"\n{C.C}{'='*50}")
    print(f"           CONFIGURATION SETUP")
    print(f"{'='*50}{C.X}\n")
    
    # Private Server URL
    print(f"{C.Y}[1] Private Server URL{C.X}")
    print(f"    Current: {config.get('private_server_url', '') or '(not set)'}")
    inp = input(f"    New URL (enter to skip): ").strip()
    if inp:
        config['private_server_url'] = inp
    
    # Check Interval
    print(f"\n{C.Y}[2] Check Interval (seconds){C.X}")
    print(f"    Current: {config.get('check_interval', 60)}s")
    inp = input(f"    New interval (enter to skip): ").strip()
    if inp and inp.isdigit():
        config['check_interval'] = int(inp)
    
    # Discord Webhook
    print(f"\n{C.Y}[3] Discord Webhook (optional){C.X}")
    print(f"    Current: {'Set' if config.get('discord_webhook') else 'Not set'}")
    inp = input(f"    Webhook URL (enter to skip): ").strip()
    if inp:
        config['discord_webhook'] = inp
    
    # Setup accounts
    print(f"\n{C.Y}[4] Setup Account Usernames?{C.X}")
    inp = input(f"    Setup now? (y/n): ").strip().lower()
    if inp == 'y':
        config = setup_accounts(config, packages)
    
    save_config(config)
    print(f"\n{C.G}[✓] Config saved!{C.X}")
    return config

# ============ MAIN ============
def banner():
    print(f"""
{C.C}╔══════════════════════════════════════════════════╗
║   MULTI-INSTANCE ROBLOX AUTO-REJOIN TOOL v1.1    ║
╠══════════════════════════════════════════════════╣
║   With TUI Dashboard & Username Mapping          ║
╚══════════════════════════════════════════════════╝{C.X}
    """)

def main():
    banner()
    
    config = load_config()
    prefix = config.get('package_prefix', 'com.roblox.clien')
    
    print(f"{C.B}[*] Scanning for packages with prefix: {prefix}*{C.X}")
    packages = detect_packages(prefix)
    
    if not packages:
        print(f"{C.R}[!] No packages found with prefix '{prefix}'!{C.X}")
        return
    
    print(f"{C.G}[✓] Found {len(packages)} packages{C.X}")
    
    # Initialize state
    accounts = config.get('accounts', {})
    for pkg in packages:
        state.instances[pkg] = {
            "running": False, 
            "rejoins": 0,
            "username": accounts.get(pkg, f"Account{packages.index(pkg)+1}")
        }
    
    # Setup?
    inp = input(f"\n{C.Y}Edit config/accounts? (y/n): {C.X}").strip().lower()
    if inp == 'y':
        config = setup_interactive(config, packages)
        accounts = config.get('accounts', {})
    
    # Validate URL
    if not config.get('private_server_url'):
        print(f"{C.R}[!] Private server URL is required!{C.X}")
        return
    
    place_id, link_code = parse_private_server_url(config['private_server_url'])
    if not place_id:
        print(f"{C.R}[!] Could not parse place ID!{C.X}")
        return
    
    deep_link = build_deep_link(place_id, link_code)
    interval = config.get('check_interval', 60)
    delay = config.get('rejoin_delay', 5)
    webhook = config.get('discord_webhook', '')
    activity = config.get('activity_name', '.startup.ActivitySplash')
    
    state.start_time = datetime.now()
    log_messages = []
    
    # Initial launch
    print(f"\n{C.B}[*] Launching all instances...{C.X}")
    for pkg in packages:
        launch_game(pkg, deep_link, activity)
        log_messages.append(f"[{datetime.now().strftime('%H:%M:%S')}] Launched {pkg[-15:]}")
        time.sleep(2)
    
    print(f"{C.G}[✓] All launched! Starting monitor in 15s...{C.X}")
    time.sleep(15)
    
    # Webhook
    if webhook:
        send_webhook(webhook, "🚀 Monitor Started!", f"Monitoring {len(packages)} instances", 0x00ff00)
    
    # Main loop with TUI
    try:
        while state.running:
            # Check each package
            for pkg in packages:
                running = is_running(pkg)
                state.instances[pkg]["running"] = running
                
                if not running:
                    state.instances[pkg]["rejoins"] += 1
                    state.total_rejoins += 1
                    username = accounts.get(pkg, pkg[-10:])
                    
                    log_messages.append(f"[{datetime.now().strftime('%H:%M:%S')}] {C.R}CRASH:{C.X} {username}")
                    
                    if webhook:
                        send_webhook(webhook, f"🔴 {username} Crashed!", "Attempting rejoin...", 0xff0000)
                    
                    time.sleep(delay)
                    force_stop(pkg)
                    time.sleep(1)
                    launch_game(pkg, deep_link, activity)
                    
                    log_messages.append(f"[{datetime.now().strftime('%H:%M:%S')}] Relaunched {username}")
                    time.sleep(5)
            
            # Draw dashboard
            draw_dashboard(packages, accounts, log_messages)
            
            # Wait for next check
            for i in range(interval):
                time.sleep(1)
                # Could add countdown here if needed
                
    except KeyboardInterrupt:
        state.running = False
        clear_screen()
        uptime = format_uptime(state.start_time)
        
        print(f"\n{C.Y}{'='*50}")
        print(f"           MONITOR STOPPED")
        print(f"{'='*50}{C.X}")
        print(f"  Uptime: {uptime}")
        print(f"  Total Rejoins: {state.total_rejoins}\n")
        
        for pkg in packages:
            info = state.instances.get(pkg, {})
            username = accounts.get(pkg, pkg[-15:])
            rejoins = info.get("rejoins", 0)
            print(f"  • {username}: {rejoins} rejoins")
        
        if webhook:
            send_webhook(webhook, "🛑 Monitor Stopped", f"Uptime: {uptime}\nRejoins: {state.total_rejoins}", 0xffaa00)

if __name__ == "__main__":
    main()
