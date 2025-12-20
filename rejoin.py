#!/usr/bin/env python3
"""
Roblox Auto-Rejoin Tool v2.1
With Discord Webhook Notifications

INSTALL:
    pkg update -y && pkg install python -y && pip install requests
    curl -o rejoin.py https://raw.githubusercontent.com/risxt/roblox-rejoin/main/rejoin.py
    python rejoin.py
"""

import json
import time
import sys
import os
import subprocess
import requests
from datetime import datetime

# ============ CONFIGURATION ============
DEFAULT_CONFIG = {
    "place_id": 121864768012064,
    "job_id": "",
    "package_name": "com.roblox.client",
    "activity_name": ".startup.ActivitySplash",
    "check_interval": 300,
    "rejoin_delay": 5,
    "discord_webhook": ""
}

# ============ GLOBAL STATE ============
class State:
    running = True
    rejoins = 0
    start_time = None
    last_check = None
    roblox_running = False

state = State()

# ============ COLORS ============
class C:
    R = '\033[91m'
    G = '\033[92m'
    Y = '\033[93m'
    B = '\033[94m'
    C = '\033[96m'
    X = '\033[0m'

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
        "footer": {"text": "Roblox Auto-Rejoin v2.1"}
    }
    
    data = {"embeds": [embed]}
    
    try:
        r = requests.post(webhook_url, json=data, timeout=10)
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
        "Roblox Auto-Rejoin tool successfully connected to Discord!",
        color=0x00ff00
    )
    
    if success:
        print(f"{C.G}[✓] Webhook test successful!{C.X}")
    else:
        print(f"{C.R}[✗] Webhook test failed! Check your URL.{C.X}")
    
    return success

# ============ LAUNCHER ============
def launch_game(package, activity, place_id, job_id=""):
    if job_id and ("roblox.com/share" in job_id or "ro.blox.com" in job_id):
        url = job_id
    elif job_id:
        url = f"roblox://placeId={place_id}&gameInstanceId={job_id}"
    else:
        url = f"roblox://placeId={place_id}"
    
    cmd = f'am start -a android.intent.action.VIEW -d "{url}"'
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if r.returncode == 0:
            return True
    except:
        pass
    
    cmd2 = f'am start -a android.intent.action.VIEW -d "{url}" -p {package}'
    try:
        r = subprocess.run(cmd2, shell=True, capture_output=True, text=True)
        return r.returncode == 0
    except:
        pass
    
    cmd3 = f'am start -n {package}/{activity}'
    try:
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
║     ROBLOX AUTO-REJOIN TOOL v2.1      ║
╠═══════════════════════════════════════╣
║  With Discord Webhook Notifications   ║
╚═══════════════════════════════════════╝{C.X}
    """)

def load_config():
    if os.path.exists("config.json"):
        try:
            with open("config.json") as f:
                config = json.load(f)
                if "discord_webhook" not in config:
                    config["discord_webhook"] = ""
                return config
        except:
            pass
    
    with open("config.json", "w") as f:
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
    
    inp = input(f"JobId/PrivateServer [{config.get('job_id', '')}]: ").strip()
    config['job_id'] = inp
    
    inp = input(f"Package [{config['package_name']}]: ").strip()
    if inp:
        config['package_name'] = inp
    
    inp = input(f"Check Interval (seconds) [{config['check_interval']}]: ").strip()
    if inp:
        config['check_interval'] = int(inp)
    
    # Discord webhook
    print(f"\n{C.C}=== Discord Webhook ==={C.X}")
    print("Get webhook: Server Settings > Integrations > Webhooks > New Webhook > Copy URL")
    inp = input(f"Webhook URL (kosong = skip): ").strip()
    if inp:
        config['discord_webhook'] = inp
        # Test webhook
        test_webhook(inp)
    
    save_config(config)
    print(f"{C.G}\nConfig saved!{C.X}")
    return config

def main():
    banner()
    
    config = load_config()
    
    print(f"{C.B}[*] Current Config:{C.X}")
    print(f"    PlaceId:  {config['place_id']}")
    print(f"    JobId:    {config.get('job_id', '') or '(random)'}")
    print(f"    Package:  {config['package_name']}")
    print(f"    Interval: {config['check_interval']}s")
    print(f"    Webhook:  {'Set' if config.get('discord_webhook') else 'Not set'}")
    
    inp = input(f"\n{C.Y}Edit config? (y/n): {C.X}").strip().lower()
    if inp == 'y':
        config = setup_interactive(config)
    
    package = config['package_name']
    activity = config.get('activity_name', '.startup.ActivitySplash')
    place_id = config['place_id']
    job_id = config.get('job_id', '')
    interval = config.get('check_interval', 300)
    delay = config.get('rejoin_delay', 5)
    webhook = config.get('discord_webhook', '')
    
    state.start_time = datetime.now()
    
    print(f"\n{C.G}[*] Starting monitor...{C.X}")
    print(f"{C.Y}[!] Make sure you're logged in to Roblox!{C.X}")
    print(f"{C.Y}[!] Press Ctrl+C to stop{C.X}\n")
    
    # Send startup notification
    if webhook:
        send_webhook(webhook, "🚀 Monitor Started!", 
            f"**PlaceId:** {place_id}\n**Package:** {package}\n**Interval:** {interval}s",
            color=0x00ff00)
    
    # Initial launch
    print(f"{C.B}[*] Launching game...{C.X}")
    launch_game(package, activity, place_id, job_id)
    time.sleep(10)
    
    try:
        while state.running:
            state.last_check = datetime.now().strftime("%H:%M:%S")
            state.roblox_running = is_running(package)
            
            if state.roblox_running:
                print(f"{C.G}[✓] Roblox running. Next check in {interval}s{C.X}")
            else:
                state.rejoins += 1
                print(f"{C.R}[!] DC detected! Rejoining... (#{state.rejoins}){C.X}")
                
                # Send DC notification
                if webhook:
                    send_webhook(webhook, "🔴 Disconnect Detected!",
                        f"Attempting rejoin #{state.rejoins}...",
                        color=0xff0000)
                
                time.sleep(delay)
                launch_game(package, activity, place_id, job_id)
                time.sleep(10)
                
                # Send rejoin success
                if webhook and is_running(package):
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
