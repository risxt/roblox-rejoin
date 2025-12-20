#!/usr/bin/env python3
"""
Multi-Instance Roblox Auto-Rejoin Tool v1.0
For Redfinger Cloud Phone with Freeform Window Support

Features:
- Auto-detect modded Roblox packages (com.roblox.clien1, clien2, etc.)
- Launch all instances in freeform window mode
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
from datetime import datetime
from urllib.parse import quote, urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor

# ============ CONFIGURATION ============
CONFIG_FILE = "multi_config.json"
DEFAULT_CONFIG = {
    "private_server_url": "",
    "check_interval": 60,
    "rejoin_delay": 5,
    "discord_webhook": "",
    "package_prefix": "com.roblox.clien",
    "activity_name": ".startup.ActivitySplash"
}

# ============ COLORS ============
class C:
    R = '\033[91m'  # Red
    G = '\033[92m'  # Green
    Y = '\033[93m'  # Yellow
    B = '\033[94m'  # Blue
    M = '\033[95m'  # Magenta
    C = '\033[96m'  # Cyan
    W = '\033[97m'  # White
    X = '\033[0m'   # Reset

# ============ GLOBAL STATE ============
class State:
    running = True
    instances = {}  # {package: {"running": bool, "rejoins": int, "last_check": str}}
    start_time = None
    total_rejoins = 0

state = State()

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
        "footer": {"text": "Multi-Instance Rejoin v1.0"}
    }
    
    try:
        r = requests.post(webhook_url, json={"embeds": [embed]}, timeout=10)
        return r.status_code in [200, 204]
    except:
        return False

# ============ PACKAGE DETECTION ============
def detect_packages(prefix="com.roblox.clien"):
    """
    Auto-detect installed Roblox packages with custom prefix
    Returns list of package names: ['com.roblox.clien1', 'com.roblox.clien2', ...]
    """
    packages = []
    
    try:
        # Method 1: pm list packages
        result = subprocess.run(
            f"pm list packages | grep {prefix}",
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line.startswith('package:'):
                    pkg = line.replace('package:', '').strip()
                    if pkg.startswith(prefix):
                        packages.append(pkg)
        
        # Sort by number at end (clien1, clien2, etc.)
        def get_num(pkg):
            match = re.search(r'(\d+)$', pkg)
            return int(match.group(1)) if match else 0
        
        packages.sort(key=get_num)
        
    except Exception as e:
        print(f"{C.R}[!] Error detecting packages: {e}{C.X}")
    
    return packages

# ============ URL PARSING ============
def parse_private_server_url(url):
    """
    Parse Roblox private server URL to extract placeId and linkCode
    Input: https://www.roblox.com/games/121864768012064/Fish-It?privateServerLinkCode=xxx
    Output: (place_id, link_code)
    """
    try:
        parsed = urlparse(url)
        
        # Extract placeId from path
        path_parts = parsed.path.split('/')
        place_id = None
        for part in path_parts:
            if part.isdigit():
                place_id = part
                break
        
        # Extract privateServerLinkCode from query
        params = parse_qs(parsed.query)
        link_code = params.get('privateServerLinkCode', [''])[0]
        
        return place_id, link_code
    except Exception as e:
        print(f"{C.R}[!] Error parsing URL: {e}{C.X}")
        return None, None

def build_deep_link(place_id, link_code):
    """
    Build Roblox deep link URL (no browser redirect)
    Output: roblox://experiences/start?placeId=xxx&launchData=privateServerLinkCode%3Dyyy
    """
    if link_code:
        launch_data = quote(f"privateServerLinkCode={link_code}")
        return f"roblox://experiences/start?placeId={place_id}&launchData={launch_data}"
    else:
        return f"roblox://placeId={place_id}"

# ============ FREEFORM LAUNCHER ============
def launch_freeform(package, deep_link, activity=".startup.ActivitySplash"):
    """
    Launch Roblox in freeform window mode
    Uses --windowingMode 5 for freeform
    """
    try:
        # Build AM command for freeform launch
        cmd = [
            "am", "start",
            "-a", "android.intent.action.VIEW",
            "-d", deep_link,
            "-p", package,
            "--windowingMode", "5",  # Freeform mode
            "--activityType", "1"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"{C.G}[✓] Launched {package} in freeform mode{C.X}")
            return True
        else:
            # Fallback: try without freeform flags
            print(f"{C.Y}[*] Trying fallback launch for {package}...{C.X}")
            return launch_fallback(package, deep_link, activity)
            
    except Exception as e:
        print(f"{C.R}[!] Launch error for {package}: {e}{C.X}")
        return launch_fallback(package, deep_link, activity)

def launch_fallback(package, deep_link, activity):
    """Fallback launch method without freeform flags"""
    try:
        cmd = f'am start -a android.intent.action.VIEW -d "{deep_link}" -p {package}'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"{C.G}[✓] Launched {package} (fallback){C.X}")
            return True
        
        # Last resort: direct activity launch
        cmd2 = f'am start -n {package}/{activity}'
        subprocess.run(cmd2, shell=True)
        return True
        
    except Exception as e:
        print(f"{C.R}[!] Fallback launch failed for {package}: {e}{C.X}")
        return False

def force_stop(package):
    """Force stop a package"""
    try:
        subprocess.run(f"am force-stop {package}", shell=True, capture_output=True)
    except:
        pass

# ============ MONITOR ============
def is_running(package):
    """Check if a Roblox package is running"""
    try:
        # Method 1: pgrep
        result = subprocess.run(
            f"pgrep -f {package}",
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            return True
        
        # Method 2: ps grep
        result = subprocess.run(
            f"ps -A | grep {package}",
            shell=True,
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            return True
        
        # Method 3: dumpsys activity
        result = subprocess.run(
            f"dumpsys activity activities | grep {package}",
            shell=True,
            capture_output=True,
            text=True
        )
        return bool(result.stdout.strip())
        
    except:
        return False

def check_all_instances(packages):
    """Check running status of all instances"""
    status = {}
    for pkg in packages:
        status[pkg] = is_running(pkg)
    return status

# ============ CONFIG ============
def load_config():
    """Load config from file or create default"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                config = json.load(f)
                # Merge with defaults for new keys
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
def setup_interactive(config, packages):
    """Interactive setup wizard"""
    print(f"\n{C.C}{'='*50}")
    print(f"           CONFIGURATION SETUP")
    print(f"{'='*50}{C.X}\n")
    
    # Private Server URL
    print(f"{C.Y}[1] Private Server URL{C.X}")
    print(f"    Current: {config.get('private_server_url', '') or '(not set)'}")
    print(f"    Format: https://www.roblox.com/games/PLACEID/NAME?privateServerLinkCode=CODE")
    inp = input(f"\n    New URL (enter to skip): ").strip()
    if inp:
        config['private_server_url'] = inp
        place_id, link_code = parse_private_server_url(inp)
        if place_id and link_code:
            print(f"{C.G}    ✓ Parsed: PlaceId={place_id}, LinkCode={link_code[:20]}...{C.X}")
        else:
            print(f"{C.R}    ✗ Could not parse URL!{C.X}")
    
    # Check Interval
    print(f"\n{C.Y}[2] Check Interval (seconds){C.X}")
    print(f"    Current: {config.get('check_interval', 60)}s")
    inp = input(f"    New interval (enter to skip): ").strip()
    if inp and inp.isdigit():
        config['check_interval'] = int(inp)
    
    # Rejoin Delay
    print(f"\n{C.Y}[3] Rejoin Delay (seconds){C.X}")
    print(f"    Current: {config.get('rejoin_delay', 5)}s")
    inp = input(f"    New delay (enter to skip): ").strip()
    if inp and inp.isdigit():
        config['rejoin_delay'] = int(inp)
    
    # Discord Webhook
    print(f"\n{C.Y}[4] Discord Webhook (optional){C.X}")
    print(f"    Current: {'Set' if config.get('discord_webhook') else 'Not set'}")
    inp = input(f"    Webhook URL (enter to skip): ").strip()
    if inp:
        config['discord_webhook'] = inp
        # Test webhook
        print(f"{C.Y}    Testing webhook...{C.X}")
        if send_webhook(inp, "✅ Connected!", f"Monitoring {len(packages)} instances"):
            print(f"{C.G}    ✓ Webhook test successful!{C.X}")
        else:
            print(f"{C.R}    ✗ Webhook test failed!{C.X}")
    
    save_config(config)
    print(f"\n{C.G}[✓] Config saved to {CONFIG_FILE}{C.X}")
    return config

# ============ MAIN ============
def banner():
    print(f"""
{C.C}╔══════════════════════════════════════════════════╗
║   MULTI-INSTANCE ROBLOX AUTO-REJOIN TOOL v1.0    ║
╠══════════════════════════════════════════════════╣
║   Freeform Window Support for Redfinger          ║
╚══════════════════════════════════════════════════╝{C.X}
    """)

def main():
    banner()
    
    # Load config
    config = load_config()
    
    # Detect installed packages
    prefix = config.get('package_prefix', 'com.roblox.clien')
    print(f"{C.B}[*] Scanning for packages with prefix: {prefix}*{C.X}")
    packages = detect_packages(prefix)
    
    if not packages:
        print(f"{C.R}[!] No packages found with prefix '{prefix}'!{C.X}")
        print(f"{C.Y}[*] Make sure you have installed modded Roblox APKs.{C.X}")
        print(f"{C.Y}[*] Expected: {prefix}1, {prefix}2, etc.{C.X}")
        return
    
    print(f"{C.G}[✓] Found {len(packages)} packages:{C.X}")
    for i, pkg in enumerate(packages, 1):
        print(f"    {i}. {pkg}")
    
    # Initialize state for each package
    for pkg in packages:
        state.instances[pkg] = {"running": False, "rejoins": 0, "last_check": ""}
    
    # Show current config
    print(f"\n{C.B}[*] Current Configuration:{C.X}")
    print(f"    URL:      {config.get('private_server_url', '') or '(not set)'}")
    print(f"    Interval: {config.get('check_interval', 60)}s")
    print(f"    Delay:    {config.get('rejoin_delay', 5)}s")
    print(f"    Webhook:  {'Set' if config.get('discord_webhook') else 'Not set'}")
    
    # Setup?
    inp = input(f"\n{C.Y}Edit config? (y/n): {C.X}").strip().lower()
    if inp == 'y':
        config = setup_interactive(config, packages)
    
    # Validate URL
    if not config.get('private_server_url'):
        print(f"{C.R}[!] Private server URL is required!{C.X}")
        return
    
    place_id, link_code = parse_private_server_url(config['private_server_url'])
    if not place_id:
        print(f"{C.R}[!] Could not parse place ID from URL!{C.X}")
        return
    
    deep_link = build_deep_link(place_id, link_code)
    print(f"\n{C.B}[*] Deep Link: {deep_link[:60]}...{C.X}")
    
    # Get config values
    interval = config.get('check_interval', 60)
    delay = config.get('rejoin_delay', 5)
    webhook = config.get('discord_webhook', '')
    activity = config.get('activity_name', '.startup.ActivitySplash')
    
    state.start_time = datetime.now()
    
    print(f"\n{C.G}[*] Starting multi-instance monitor...{C.X}")
    print(f"{C.Y}[!] Make sure all accounts are logged in!{C.X}")
    print(f"{C.Y}[!] Press Ctrl+C to stop{C.X}\n")
    
    # Send startup webhook
    if webhook:
        pkg_list = '\n'.join([f"• {p}" for p in packages])
        send_webhook(webhook, "🚀 Multi-Instance Monitor Started!",
            f"**Packages:** {len(packages)}\n{pkg_list}\n\n**Interval:** {interval}s",
            color=0x00ff00)
    
    # Initial launch of all instances
    print(f"{C.B}[*] Launching all instances...{C.X}\n")
    for i, pkg in enumerate(packages):
        print(f"{C.M}[{i+1}/{len(packages)}] Launching {pkg}...{C.X}")
        launch_freeform(pkg, deep_link, activity)
        time.sleep(2)  # Small delay between launches
    
    print(f"\n{C.G}[✓] All instances launched! Waiting for games to load...{C.X}")
    time.sleep(15)  # Wait for games to load
    
    # Main monitoring loop
    try:
        while state.running:
            now = datetime.now().strftime("%H:%M:%S")
            print(f"\n{C.B}[{now}] Checking all instances...{C.X}")
            
            # Check each package
            for pkg in packages:
                running = is_running(pkg)
                state.instances[pkg]["running"] = running
                state.instances[pkg]["last_check"] = now
                
                if running:
                    print(f"  {C.G}✓ {pkg} - Running{C.X}")
                else:
                    state.instances[pkg]["rejoins"] += 1
                    state.total_rejoins += 1
                    rejoin_count = state.instances[pkg]["rejoins"]
                    
                    print(f"  {C.R}✗ {pkg} - CRASHED! Rejoining... (#{rejoin_count}){C.X}")
                    
                    # Send webhook
                    if webhook:
                        send_webhook(webhook, f"🔴 {pkg} Crashed!",
                            f"Attempting rejoin #{rejoin_count}...",
                            color=0xff0000)
                    
                    # Rejoin
                    time.sleep(delay)
                    force_stop(pkg)
                    time.sleep(1)
                    launch_freeform(pkg, deep_link, activity)
                    time.sleep(5)
                    
                    # Check if rejoin successful
                    if is_running(pkg) and webhook:
                        send_webhook(webhook, f"🟢 {pkg} Rejoined!",
                            f"Total rejoins for this instance: {rejoin_count}",
                            color=0x00ff00)
            
            # Summary
            running_count = sum(1 for p in packages if state.instances[p]["running"])
            print(f"\n{C.C}[Summary] {running_count}/{len(packages)} running | Total rejoins: {state.total_rejoins}{C.X}")
            print(f"{C.Y}[*] Next check in {interval}s...{C.X}")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        state.running = False
        uptime = datetime.now() - state.start_time
        
        print(f"\n\n{C.Y}{'='*50}")
        print(f"           MONITOR STOPPED")
        print(f"{'='*50}{C.X}")
        print(f"  Uptime: {str(uptime).split('.')[0]}")
        print(f"  Total Rejoins: {state.total_rejoins}")
        print()
        for pkg in packages:
            rejoins = state.instances[pkg]["rejoins"]
            print(f"  • {pkg}: {rejoins} rejoins")
        
        if webhook:
            pkg_summary = '\n'.join([f"• {p}: {state.instances[p]['rejoins']} rejoins" for p in packages])
            send_webhook(webhook, "🛑 Monitor Stopped",
                f"**Uptime:** {str(uptime).split('.')[0]}\n**Total Rejoins:** {state.total_rejoins}\n\n{pkg_summary}",
                color=0xffaa00)

if __name__ == "__main__":
    main()
