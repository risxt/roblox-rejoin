#!/usr/bin/env python3
"""
Roblox Auto-Rejoin Tool v2.1 - Windows Edition
Monitor and auto-rejoin Roblox games on Windows

INSTALL:
    pip install requests psutil
    python rejoin_windows.py
"""

import json
import time
import sys
import os
import subprocess
import webbrowser
from datetime import datetime

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("[!] psutil not installed. Install with: pip install psutil")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# ============ CONFIGURATION ============
DEFAULT_CONFIG = {
    "place_id": 121864768012064,
    "job_id": "",
    "check_interval": 300,
    "rejoin_delay": 5,
    "discord_webhook": "",
    "roblox_process": "RobloxPlayerBeta.exe"
}

# ============ GLOBAL STATE ============
class State:
    running = True
    rejoins = 0
    start_time = None
    last_check = None
    roblox_running = False

state = State()

# ============ COLORS (Windows Console) ============
class C:
    R = '\033[91m'
    G = '\033[92m'
    Y = '\033[93m'
    B = '\033[94m'
    C = '\033[96m'
    X = '\033[0m'

# Enable ANSI colors on Windows
if os.name == 'nt':
    os.system('color')

# ============ DISCORD WEBHOOK ============
def send_webhook(webhook_url, title, description, color=0x00ff00):
    """Send embed message to Discord webhook"""
    if not webhook_url or not REQUESTS_AVAILABLE:
        return False
    
    embed = {
        "title": title,
        "description": description,
        "color": color,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {"text": "Roblox Auto-Rejoin Windows v2.1"}
    }
    
    try:
        r = requests.post(webhook_url, json={"embeds": [embed]}, timeout=10)
        return r.status_code in [200, 204]
    except:
        return False

def test_webhook(webhook_url):
    """Test webhook connection"""
    if not webhook_url:
        return False
    
    print(f"{C.Y}[*] Testing webhook...{C.X}")
    success = send_webhook(
        webhook_url,
        "✅ Webhook Connected!",
        "Windows Roblox Auto-Rejoin connected!",
        color=0x00ff00
    )
    
    if success:
        print(f"{C.G}[✓] Webhook test successful!{C.X}")
    else:
        print(f"{C.R}[✗] Webhook test failed!{C.X}")
    
    return success

# ============ PROCESS MONITOR ============
def is_roblox_running(process_name="RobloxPlayerBeta.exe"):
    """Check if Roblox is running"""
    if not PSUTIL_AVAILABLE:
        # Fallback: use tasklist
        try:
            output = subprocess.check_output(
                f'tasklist /FI "IMAGENAME eq {process_name}"',
                shell=True, text=True
            )
            return process_name.lower() in output.lower()
        except:
            return False
    
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] and process_name.lower() in proc.info['name'].lower():
                return True
        except:
            continue
    return False

def kill_roblox(process_name="RobloxPlayerBeta.exe"):
    """Kill Roblox process"""
    try:
        subprocess.run(f'taskkill /F /IM "{process_name}"', shell=True, 
                      capture_output=True)
        return True
    except:
        return False

# ============ LAUNCHER ============
def launch_roblox(place_id, job_id=""):
    """Launch Roblox using protocol URL"""
    # Build URL
    if job_id and ("roblox.com/share" in job_id or "ro.blox.com" in job_id):
        # Private server link
        url = job_id
    elif job_id:
        url = f"roblox://placeId={place_id}&gameInstanceId={job_id}"
    else:
        url = f"roblox://placeId={place_id}"
    
    print(f"{C.B}[*] Launching: {url[:60]}...{C.X}")
    
    try:
        # Method 1: webbrowser module
        webbrowser.open(url)
        return True
    except:
        pass
    
    try:
        # Method 2: start command
        os.system(f'start "" "{url}"')
        return True
    except:
        return False

# ============ MAIN ============
def banner():
    print(f"""
{C.C}╔═══════════════════════════════════════════╗
║   ROBLOX AUTO-REJOIN TOOL v2.1 - WINDOWS  ║
╠═══════════════════════════════════════════╣
║   Monitor & Auto-Rejoin for Windows PC    ║
╚═══════════════════════════════════════════╝{C.X}
    """)

def load_config():
    config_path = "config.json"
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                config = json.load(f)
                for key in DEFAULT_CONFIG:
                    if key not in config:
                        config[key] = DEFAULT_CONFIG[key]
                return config
        except:
            pass
    
    with open(config_path, "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    
    print(f"{C.Y}[!] config.json created!{C.X}")
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
    
    # Discord webhook
    print(f"\n{C.C}=== Discord Webhook (Optional) ==={C.X}")
    inp = input(f"Webhook URL (enter to skip): ").strip()
    if inp:
        config['discord_webhook'] = inp
        test_webhook(inp)
    
    save_config(config)
    print(f"{C.G}\nConfig saved!{C.X}")
    return config

def main():
    banner()
    
    if not PSUTIL_AVAILABLE:
        print(f"{C.Y}[!] Installing psutil...{C.X}")
        os.system("pip install psutil")
        print(f"{C.Y}[!] Please restart the script{C.X}")
        sys.exit(0)
    
    config = load_config()
    
    print(f"{C.B}[*] Current Config:{C.X}")
    print(f"    PlaceId:  {config['place_id']}")
    print(f"    JobId:    {config.get('job_id', '') or '(random server)'}")
    print(f"    Interval: {config['check_interval']}s ({config['check_interval']//60}min)")
    print(f"    Webhook:  {'Set' if config.get('discord_webhook') else 'Not set'}")
    
    inp = input(f"\n{C.Y}Edit config? (y/n): {C.X}").strip().lower()
    if inp == 'y':
        config = setup_interactive(config)
    
    place_id = config['place_id']
    job_id = config.get('job_id', '')
    interval = config.get('check_interval', 300)
    delay = config.get('rejoin_delay', 5)
    webhook = config.get('discord_webhook', '')
    process_name = config.get('roblox_process', 'RobloxPlayerBeta.exe')
    
    state.start_time = datetime.now()
    
    print(f"\n{C.G}[*] Starting monitor...{C.X}")
    print(f"{C.Y}[!] Make sure you're logged in to Roblox!{C.X}")
    print(f"{C.Y}[!] Press Ctrl+C to stop{C.X}\n")
    
    # Send startup notification
    if webhook:
        send_webhook(webhook, "🚀 Windows Monitor Started!",
            f"**PlaceId:** {place_id}\n**Interval:** {interval}s",
            color=0x00ff00)
    
    # Initial launch
    print(f"{C.B}[*] Launching game...{C.X}")
    launch_roblox(place_id, job_id)
    time.sleep(15)  # Windows needs more time
    
    try:
        while state.running:
            state.last_check = datetime.now().strftime("%H:%M:%S")
            state.roblox_running = is_roblox_running(process_name)
            
            if state.roblox_running:
                print(f"{C.G}[✓] [{state.last_check}] Roblox running. Next check in {interval}s{C.X}")
            else:
                state.rejoins += 1
                print(f"{C.R}[!] [{state.last_check}] DC detected! Rejoining... (#{state.rejoins}){C.X}")
                
                if webhook:
                    send_webhook(webhook, "🔴 Disconnect Detected!",
                        f"Attempting rejoin #{state.rejoins}...",
                        color=0xff0000)
                
                time.sleep(delay)
                launch_roblox(place_id, job_id)
                time.sleep(15)
                
                if webhook and is_roblox_running(process_name):
                    send_webhook(webhook, "🟢 Rejoin Successful!",
                        f"Total rejoins: {state.rejoins}",
                        color=0x00ff00)
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        state.running = False
        print(f"\n\n{C.Y}[*] Stopped. Total rejoins: {state.rejoins}{C.X}")
        if webhook:
            uptime = datetime.now() - state.start_time
            send_webhook(webhook, "🛑 Monitor Stopped",
                f"**Uptime:** {str(uptime).split('.')[0]}\n**Total Rejoins:** {state.rejoins}",
                color=0xffaa00)

if __name__ == "__main__":
    main()
