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
import argparse
from datetime import datetime
from urllib.parse import quote, urlparse, parse_qs

# ============ CONFIGURATION ============
CONFIG_FILE = "multi_config.json"
DEFAULT_CONFIG = {
    "private_server_url": "",
    "check_interval": 60,
    "rejoin_delay": 5,
    "launch_delay": 20,  # Delay between launching each instance (seconds)
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
    """
    Parse Roblox private server URL
    Supports two formats:
    1. ?privateServerLinkCode= (for emulators like LD, MuMu, Redfinger)
    2. share?code= (for web/Bloxstrap - needs conversion)
    """
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        # Check for share?code= format first
        if 'code' in params and '/share' in parsed.path:
            # This is share?code= format - extract the code
            share_code = params.get('code', [''])[0]
            # For share links, we can't easily get place_id, return special marker
            return None, share_code, 'share'
        
        # Standard privateServerLinkCode format
        path_parts = parsed.path.split('/')
        place_id = None
        for part in path_parts:
            if part.isdigit():
                place_id = part
                break
        
        link_code = params.get('privateServerLinkCode', [''])[0]
        
        return place_id, link_code, 'private'
    except:
        return None, None, None

def build_deep_link(place_id, link_code, original_url=None):
    """Build Roblox deep link URL for emulator launching"""
    if original_url:
        # For emulators, the original URL with privateServerLinkCode works best
        return original_url
    
    if link_code:
        # Fallback: construct URL
        return f"https://www.roblox.com/games/start?placeId={place_id}&privateServerLinkCode={link_code}"
    else:
        return f"https://www.roblox.com/games/start?placeId={place_id}"

def build_deep_link_protocol(place_id, link_code):
    """Build Roblox deep link using roblox:// protocol (alternative method)"""
    if link_code:
        # Format: roblox://placeId=X&linkCode=Y
        return f"roblox://placeId={place_id}&linkCode={link_code}"
    else:
        return f"roblox://placeId={place_id}"

# ============ LAUNCHER ============
def launch_game(package, deep_link, activity=".startup.ActivitySplash"):
    """
    Launch Roblox with deep link - tries multiple methods for reliability
    For emulators (Redfinger, LD, MuMu), we try different intent methods
    """
    try:
        # Method 1: Direct VIEW intent with package specified
        # This tells Android to open the URL with the specific Roblox package
        cmd = f'am start -a android.intent.action.VIEW -d "{deep_link}" -p {package}'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0 and "Error" not in result.stderr:
            return True
            
        # Method 2: VIEW intent without package (let system choose default handler)
        cmd2 = f'am start -a android.intent.action.VIEW -d "{deep_link}"'
        result2 = subprocess.run(cmd2, shell=True, capture_output=True, text=True)
        
        if result2.returncode == 0 and "Error" not in result2.stderr:
            return True
        
        # Method 3: Launch app first, then send intent
        # Sometimes the app needs to be running first
        launch_cmd = f'am start -n {package}/{package}.startup.ActivitySplash'
        subprocess.run(launch_cmd, shell=True, capture_output=True, text=True)
        time.sleep(2)
        
        # Now send the deep link
        cmd3 = f'am start -a android.intent.action.VIEW -d "{deep_link}" -p {package}'
        result3 = subprocess.run(cmd3, shell=True, capture_output=True, text=True)
        
        return result3.returncode == 0
    except Exception as e:
        print(f"Launch error: {e}")
        return False

def force_stop(package):
    """Force stop a package"""
    try:
        subprocess.run(f"am force-stop {package}", shell=True, capture_output=True)
    except:
        pass

# ============ MONITOR ============
def is_running(package):
    """
    Check if a Roblox package is running
    Directly iterates /proc to avoid race conditions with grep
    """
    try:
        our_pid = os.getpid()
        
        # Directly iterate /proc entries
        for entry in os.listdir('/proc'):
            # Only check numeric PIDs
            if not entry.isdigit():
                continue
            
            pid = int(entry)
            
            # Skip our own process
            if pid == our_pid:
                continue
            
            cmdline_path = f'/proc/{pid}/cmdline'
            
            try:
                with open(cmdline_path, 'rb') as f:
                    cmdline = f.read()
                
                # Convert to lowercase string
                cmdline_str = cmdline.replace(b'\x00', b' ').decode('utf-8', errors='ignore').lower().strip()
                
                # Check if 'roblox' is in cmdline
                if 'roblox' in cmdline_str:
                    # Check for false positives (scripts/commands that have 'roblox' as argument)
                    first_word = cmdline_str.split()[0] if cmdline_str.split() else ""
                    false_positives = ['grep', 'python', 'cat', 'sh', 'bash', 'awk', 'sed', 'tr', 'perl']
                    
                    is_fp = any(fp in first_word for fp in false_positives)
                    
                    if not is_fp:
                        # Found a real Roblox process!
                        return True
                    
            except (FileNotFoundError, PermissionError, ProcessLookupError):
                continue
        
        # No Roblox process found
        return False
        
    except Exception as e:
        # On error, assume running to avoid false positives
        return True

# ============ TUI DASHBOARD ============
def draw_dashboard(packages, accounts, log_messages):
    """Draw the TUI dashboard with emoji style"""
    clear_screen()
    
    # Header
    print(f"\n  {C.C}{C.BOLD}🎮 ROBLOX MULTI-INSTANCE MONITOR{C.X}")
    print(f"  {C.DIM}{'─'*40}{C.X}\n")
    
    # Instance rows
    online_count = 0
    for i, pkg in enumerate(packages, 1):
        info = state.instances.get(pkg, {})
        running = info.get("running", False)
        username = accounts.get(pkg, f"Account{i}")[:15]
        
        # Truncate package name
        pkg_short = pkg[-18:] if len(pkg) > 18 else pkg
        
        if running:
            status = f"{C.G}🟢 Online{C.X}"
            online_count += 1
        else:
            status = f"{C.R}🔴 Offline{C.X}"
        
        print(f"  📦 {C.W}{pkg_short:<18}{C.X}  👤 {C.C}{username:<15}{C.X}  {status}")
    
    print()
    
    # Stats bar
    ram = get_ram_info()
    uptime = format_uptime(state.start_time)
    print(f"  💾 RAM: {C.G}{ram}{C.X}  ⏱️ {C.Y}{uptime}{C.X}  🔄 {C.M}{state.total_rejoins}{C.X} rejoins  📊 {C.G}{online_count}/{len(packages)}{C.X}")
    
    print(f"\n  {C.DIM}{'─'*40}{C.X}")
    
    # Log section
    print(f"  {C.BOLD}📋 LOG:{C.X}")
    
    # Show last 5 log messages
    for msg in log_messages[-5:]:
        # Clean up message for display
        msg_display = msg[:50] if len(msg) > 50 else msg
        if "CRASH" in msg or "Offline" in msg:
            print(f"  {C.R}❌ {msg_display}{C.X}")
        elif "Launched" in msg or "Relaunched" in msg:
            print(f"  {C.G}✅ {msg_display}{C.X}")
        else:
            print(f"  📝 {msg_display}")
    
    # Fill remaining lines if needed
    if len(log_messages) < 5:
        for _ in range(5 - len(log_messages)):
            print()
    
    print(f"\n  {C.DIM}Press Ctrl+C to stop{C.X}\n")

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
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Multi-Instance Roblox Auto-Rejoin')
    parser.add_argument('--auto', action='store_true', help='Auto mode - skip all prompts (for Termux Boot)')
    args = parser.parse_args()
    
    auto_mode = args.auto
    
    if not auto_mode:
        banner()
    else:
        print(f"{C.G}[AUTO MODE] Starting...{C.X}")
    
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
    
    # Setup? (skip in auto mode)
    if not auto_mode:
        inp = input(f"\n{C.Y}Edit config/accounts? (y/n): {C.X}").strip().lower()
        if inp == 'y':
            config = setup_interactive(config, packages)
            accounts = config.get('accounts', {})
    
    # Validate URL
    if not config.get('private_server_url'):
        print(f"{C.R}[!] Private server URL is required!{C.X}")
        return
    
    original_url = config['private_server_url']
    place_id, link_code, url_type = parse_private_server_url(original_url)
    
    # Handle share?code= format - warn user to convert
    if url_type == 'share':
        print(f"\n{C.Y}[!] WARNING: You're using share?code= format!{C.X}")
        print(f"    This format doesn't work well on emulators.")
        print(f"    Please open the link in browser and copy the redirected URL")
        print(f"    which should have ?privateServerLinkCode= format instead.")
        print(f"\n    Your link: {original_url[:50]}...")
        inp = input(f"\n{C.Y}Continue anyway? (y/n): {C.X}").strip().lower()
        if inp != 'y':
            return
    
    if not place_id and url_type != 'share':
        print(f"{C.R}[!] Could not parse place ID from URL!{C.X}")
        print(f"    URL: {original_url[:60]}...")
        return
    
    # For emulators, use the original URL if it has privateServerLinkCode
    # This is more reliable than constructing a new URL
    deep_link = build_deep_link(place_id, link_code, original_url)
    interval = config.get('check_interval', 60)
    delay = config.get('rejoin_delay', 5)
    webhook = config.get('discord_webhook', '')
    activity = config.get('activity_name', '.startup.ActivitySplash')
    
    state.start_time = datetime.now()
    log_messages = []
    launch_delay = config.get('launch_delay', 20)  # Default 20s delay between launches
    
    # Debug: Show the deep link being used
    print(f"\n{C.B}[DEBUG] Deep link URL:{C.X}")
    print(f"  {C.DIM}{deep_link}{C.X}")
    print(f"  Place ID: {C.G}{place_id}{C.X}")
    print(f"  Link Code: {C.G}{link_code or 'None'}{C.X}\n")
    
    # ============ LAUNCH MENU ============
    selected_packages = []  # Packages to launch and monitor
    
    if not auto_mode:
        print(f"\n{C.C}{'='*50}")
        print(f"           LAUNCH OPTIONS")
        print(f"{'='*50}{C.X}\n")
        print(f"  {C.G}[1]{C.X} Launch Single Instance (pick one)")
        print(f"  {C.G}[2]{C.X} Launch ALL Instances (20s delay)")
        print(f"  {C.G}[3]{C.X} Monitor Only (no launch)")
        print()
        
        choice = input(f"{C.Y}Select option (1/2/3): {C.X}").strip()
        
        if choice == '1':
            # Single instance selection
            print(f"\n{C.C}{'='*50}")
            print(f"      SELECT INSTANCE TO LAUNCH")
            print(f"{'='*50}{C.X}\n")
            
            for i, pkg in enumerate(packages, 1):
                username = accounts.get(pkg, f"Account{i}")
                pkg_short = pkg.split('.')[-1]  # e.g. "clien1"
                print(f"  {C.G}[{i}]{C.X} {pkg_short} - {C.C}{username}{C.X}")
            
            print()
            idx_input = input(f"{C.Y}Enter number (1-{len(packages)}): {C.X}").strip()
            
            if idx_input.isdigit():
                idx = int(idx_input) - 1
                if 0 <= idx < len(packages):
                    selected_pkg = packages[idx]
                    selected_packages = [selected_pkg]
                    
                    print(f"\n{C.B}[*] Launching {accounts.get(selected_pkg, selected_pkg)}...{C.X}")
                    launch_game(selected_pkg, deep_link, activity)
                    log_messages.append(f"[{datetime.now().strftime('%H:%M:%S')}] Launched {selected_pkg[-15:]}")
                    print(f"{C.G}[✓] Launched! Starting monitor in 15s...{C.X}")
                    time.sleep(15)
                else:
                    print(f"{C.R}[!] Invalid selection!{C.X}")
                    return
            else:
                print(f"{C.R}[!] Invalid input!{C.X}")
                return
                
        elif choice == '2':
            # Launch all with delay
            selected_packages = packages.copy()
            print(f"\n{C.B}[*] Launching all {len(packages)} instances (delay: {launch_delay}s each)...{C.X}")
            
            for i, pkg in enumerate(packages):
                username = accounts.get(pkg, f"Account{i+1}")
                print(f"  {C.G}▶{C.X} Launching {username}...")
                launch_game(pkg, deep_link, activity)
                log_messages.append(f"[{datetime.now().strftime('%H:%M:%S')}] Launched {pkg[-15:]}")
                
                if i < len(packages) - 1:  # Don't wait after last one
                    print(f"  {C.Y}  ⏳ Waiting {launch_delay}s before next...{C.X}")
                    # Countdown display
                    for sec in range(launch_delay, 0, -1):
                        print(f"\r  {C.DIM}    {sec}s remaining...{C.X}  ", end="", flush=True)
                        time.sleep(1)
                    print()  # New line after countdown
            
            print(f"\n{C.G}[✓] All instances launched! Starting monitor in 15s...{C.X}")
            time.sleep(15)
            
        elif choice == '3':
            # Monitor only
            selected_packages = packages.copy()
            print(f"\n{C.B}[*] Monitor mode - no launch, checking existing instances...{C.X}")
            time.sleep(2)
            
        else:
            print(f"{C.R}[!] Invalid option! Exiting...{C.X}")
            return
    else:
        # Auto mode: launch all with delay
        selected_packages = packages.copy()
        print(f"\n{C.B}[*] AUTO MODE: Launching all instances (delay: {launch_delay}s each)...{C.X}")
        for i, pkg in enumerate(packages):
            launch_game(pkg, deep_link, activity)
            log_messages.append(f"[{datetime.now().strftime('%H:%M:%S')}] Launched {pkg[-15:]}")
            if i < len(packages) - 1:
                time.sleep(launch_delay)
        time.sleep(15)
    
    # Webhook
    if webhook:
        send_webhook(webhook, "🚀 Monitor Started!", f"Monitoring {len(selected_packages)} instances", 0x00ff00)
    
    # Use selected_packages for monitoring (could be 1 or all)
    monitor_packages = selected_packages if selected_packages else packages
    
    # ============ MANUAL TRIGGER DASHBOARD ============
    # Since auto crash detection doesn't work well on Redfinger,
    # we use manual trigger - user types number to relaunch instance
    
    import select
    import sys
    
    def draw_manual_dashboard(packages, accounts, log_messages):
        """Draw dashboard with manual trigger options"""
        clear_screen()
        
        # Header
        print(f"\n  {C.C}{C.BOLD}🎮 ROBLOX MULTI-INSTANCE MONITOR{C.X}")
        print(f"  {C.DIM}────────────────────────────────────────{C.X}\n")
        
        # Instance rows with numbers for relaunch
        for i, pkg in enumerate(packages, 1):
            username = accounts.get(pkg, f"Account{i}")[:15]
            pkg_short = pkg.split('.')[-1]  # e.g. "clienv"
            
            print(f"  {C.G}[{i}]{C.X} {C.C}{username:<15}{C.X}  📦 {C.DIM}{pkg_short}{C.X}")
        
        print()
        
        # Stats bar
        ram = get_ram_info()
        uptime = format_uptime(state.start_time)
        print(f"  💾 RAM: {C.G}{ram}{C.X}  ⏱️ {C.Y}{uptime}{C.X}  🔄 {C.M}{state.total_rejoins}{C.X} rejoins")
        
        print(f"\n  {C.DIM}────────────────────────────────────────{C.X}")
        
        # Log section
        print(f"  {C.BOLD}📋 LOG:{C.X}")
        for msg in log_messages[-5:]:
            msg_display = msg[:50] if len(msg) > 50 else msg
            if "RELAUNCH" in msg.upper():
                print(f"  {C.G}✅ {msg_display}{C.X}")
            else:
                print(f"  📝 {msg_display}")
        
        # Fill remaining lines
        if len(log_messages) < 5:
            for _ in range(5 - len(log_messages)):
                print()
        
        print(f"\n  {C.DIM}────────────────────────────────────────{C.X}")
        print(f"  {C.Y}Type 1-{len(packages)} to RELAUNCH instance, Q to quit{C.X}")
        print(f"  {C.DIM}(Runs in background - check when you see crash){C.X}\n")
        print(f"  > ", end="", flush=True)
    
    def get_input_nonblocking(timeout=1):
        """Non-blocking input for Android/Linux"""
        try:
            # Check if stdin has data
            rlist, _, _ = select.select([sys.stdin], [], [], timeout)
            if rlist:
                return sys.stdin.readline().strip()
        except:
            pass
        return None
    
    # Main loop with manual trigger
    try:
        while state.running:
            draw_manual_dashboard(packages, accounts, log_messages)
            
            # Wait for input with timeout (allows refresh)
            user_input = get_input_nonblocking(5)  # 5 second timeout, then refresh
            
            if user_input:
                user_input = user_input.lower().strip()
                
                if user_input == 'q':
                    state.running = False
                    break
                
                elif user_input.isdigit():
                    idx = int(user_input) - 1
                    if 0 <= idx < len(packages):
                        pkg = packages[idx]
                        username = accounts.get(pkg, pkg[-15:])
                        
                        print(f"\n  {C.B}⏳ Relaunching {username}...{C.X}")
                        
                        # Force stop first (might not work but try)
                        force_stop(pkg)
                        time.sleep(1)
                        
                        # Relaunch
                        launch_game(pkg, deep_link, activity)
                        state.total_rejoins += 1
                        
                        log_messages.append(f"[{datetime.now().strftime('%H:%M:%S')}] Relaunched {username}")
                        
                        if webhook:
                            send_webhook(webhook, f"🔄 {username} Relaunched", "Manual trigger", 0x00ff00)
                        
                        print(f"  {C.G}✅ Done! Continuing in 3s...{C.X}")
                        time.sleep(3)
                    else:
                        print(f"\n  {C.R}Invalid number!{C.X}")
                        time.sleep(2)
                else:
                    print(f"\n  {C.R}Type a number (1-{len(packages)}) or Q{C.X}")
                    time.sleep(2)
                
    except KeyboardInterrupt:
        state.running = False
    
    # Exit summary
    clear_screen()
    uptime = format_uptime(state.start_time)
    
    print(f"\n{C.Y}{'='*50}")
    print(f"           MONITOR STOPPED")
    print(f"{'='*50}{C.X}")
    print(f"  Uptime: {uptime}")
    print(f"  Total Relaunches: {state.total_rejoins}\n")
    
    for pkg in monitor_packages:
        username = accounts.get(pkg, pkg[-15:])
        print(f"  • {username}")
    
    if webhook:
        send_webhook(webhook, "🛑 Monitor Stopped", f"Uptime: {uptime}\nRelaunches: {state.total_rejoins}", 0xffaa00)

if __name__ == "__main__":
    main()
