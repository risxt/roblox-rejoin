#!/usr/bin/env python3
"""
Roblox Auto-Rejoin Tool v2.0
With Discord Bot Control

INSTALL:
    pkg update -y && pkg install python -y
    pip install requests aiohttp
    curl -o rejoin.py https://raw.githubusercontent.com/risxt/roblox-rejoin/main/rejoin.py
    python rejoin.py
"""

import json
import time
import sys
import os
import subprocess
import threading
import asyncio
from datetime import datetime

# Try to import aiohttp for Discord
try:
    import aiohttp
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    print("[!] aiohttp not installed. Discord features disabled.")
    print("    Install with: pip install aiohttp")

# ============ CONFIGURATION ============
DEFAULT_CONFIG = {
    "place_id": 121864768012064,
    "job_id": "",
    "package_name": "com.roblox.client",
    "activity_name": ".startup.ActivitySplash",
    "check_interval": 300,
    "rejoin_delay": 5,
    "discord": {
        "enabled": False,
        "bot_token": "YOUR_BOT_TOKEN",
        "channel_id": "YOUR_CHANNEL_ID",
        "owner_id": "YOUR_DISCORD_USER_ID"
    }
}

# ============ GLOBAL STATE ============
class State:
    running = True
    rejoins = 0
    start_time = None
    last_check = None
    roblox_running = False
    force_rejoin = False

state = State()

# ============ COLORS ============
class C:
    R = '\033[91m'
    G = '\033[92m'
    Y = '\033[93m'
    B = '\033[94m'
    C = '\033[96m'
    X = '\033[0m'

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

# ============ DISCORD BOT ============
class DiscordBot:
    def __init__(self, token, channel_id, owner_id):
        self.token = token
        self.channel_id = channel_id
        self.owner_id = owner_id
        self.base_url = "https://discord.com/api/v10"
        self.headers = {
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json"
        }
        self.session = None
        self.gateway_url = None
        self.heartbeat_interval = None
        self.sequence = None
    
    async def send_message(self, content, embed=None):
        """Send message to channel"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"{self.base_url}/channels/{self.channel_id}/messages"
        data = {"content": content}
        if embed:
            data["embeds"] = [embed]
        
        try:
            async with self.session.post(url, headers=self.headers, json=data) as resp:
                return resp.status == 200
        except:
            return False
    
    async def send_embed(self, title, description, color=0x00ff00):
        """Send embed message"""
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.utcnow().isoformat()
        }
        return await self.send_message("", embed=embed)
    
    async def notify_dc(self, rejoin_count):
        """Notify about disconnect"""
        await self.send_embed(
            "🔴 Disconnect Detected!",
            f"Roblox disconnected. Attempting rejoin #{rejoin_count}...",
            color=0xff0000
        )
    
    async def notify_rejoin_success(self, rejoin_count):
        """Notify about successful rejoin"""
        await self.send_embed(
            "🟢 Rejoin Successful!",
            f"Successfully rejoined! Total rejoins: {rejoin_count}",
            color=0x00ff00
        )
    
    async def send_status(self):
        """Send current status"""
        uptime = ""
        if state.start_time:
            delta = datetime.now() - state.start_time
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime = f"{hours}h {minutes}m {seconds}s"
        
        status = "🟢 Running" if state.roblox_running else "🔴 Not Running"
        
        await self.send_embed(
            "📊 Status",
            f"**Roblox:** {status}\n"
            f"**Uptime:** {uptime}\n"
            f"**Total Rejoins:** {state.rejoins}\n"
            f"**Last Check:** {state.last_check or 'N/A'}",
            color=0x00ff00 if state.roblox_running else 0xff0000
        )
    
    async def listen_commands(self):
        """Listen for commands via polling"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        last_message_id = None
        
        while state.running:
            try:
                url = f"{self.base_url}/channels/{self.channel_id}/messages?limit=1"
                async with self.session.get(url, headers=self.headers) as resp:
                    if resp.status == 200:
                        messages = await resp.json()
                        if messages:
                            msg = messages[0]
                            msg_id = msg["id"]
                            content = msg.get("content", "").lower().strip()
                            author_id = msg.get("author", {}).get("id")
                            
                            if msg_id != last_message_id and author_id == self.owner_id:
                                last_message_id = msg_id
                                
                                if content == "!status":
                                    await self.send_status()
                                elif content == "!rejoin":
                                    state.force_rejoin = True
                                    await self.send_message("⚡ Force rejoin triggered!")
                                elif content == "!stop":
                                    state.running = False
                                    await self.send_message("🛑 Stopping monitor...")
                                elif content == "!help":
                                    await self.send_embed(
                                        "📚 Commands",
                                        "**!status** - Show current status\n"
                                        "**!rejoin** - Force rejoin now\n"
                                        "**!stop** - Stop the monitor\n"
                                        "**!help** - Show this help",
                                        color=0x0099ff
                                    )
            except:
                pass
            
            await asyncio.sleep(3)
    
    async def close(self):
        if self.session:
            await self.session.close()

# ============ MAIN ============
def banner():
    print(f"""
{C.C}╔═══════════════════════════════════════╗
║     ROBLOX AUTO-REJOIN TOOL v2.0      ║
╠═══════════════════════════════════════╣
║  With Discord Bot Control             ║
╚═══════════════════════════════════════╝{C.X}
    """)

def load_config():
    if os.path.exists("config.json"):
        try:
            with open("config.json") as f:
                config = json.load(f)
                # Ensure discord section exists
                if "discord" not in config:
                    config["discord"] = DEFAULT_CONFIG["discord"]
                return config
        except:
            pass
    
    with open("config.json", "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    
    print(f"{C.Y}[!] config.json created!{C.X}")
    print(f"{C.Y}    Edit place_id, package_name, and discord settings{C.X}")
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
    
    # Discord setup
    print(f"\n{C.C}=== Discord Setup ==={C.X}")
    inp = input("Enable Discord? (y/n): ").strip().lower()
    if inp == 'y':
        config['discord']['enabled'] = True
        inp = input(f"Bot Token: ").strip()
        if inp:
            config['discord']['bot_token'] = inp
        inp = input(f"Channel ID: ").strip()
        if inp:
            config['discord']['channel_id'] = inp
        inp = input(f"Your Discord User ID: ").strip()
        if inp:
            config['discord']['owner_id'] = inp
    
    save_config(config)
    print(f"{C.G}Config saved!{C.X}")
    return config

async def run_discord_bot(config):
    """Run Discord bot in background"""
    dc = config.get("discord", {})
    if not dc.get("enabled") or not DISCORD_AVAILABLE:
        return None
    
    bot = DiscordBot(
        dc.get("bot_token", ""),
        dc.get("channel_id", ""),
        dc.get("owner_id", "")
    )
    
    # Send startup message
    await bot.send_embed(
        "🚀 Rejoin Tool Started!",
        f"Monitoring started.\nPlaceId: {config['place_id']}\nPackage: {config['package_name']}",
        color=0x00ff00
    )
    
    return bot

def main():
    banner()
    
    config = load_config()
    
    print(f"{C.B}[*] Current Config:{C.X}")
    print(f"    PlaceId:  {config['place_id']}")
    print(f"    JobId:    {config.get('job_id', '') or '(random)'}")
    print(f"    Package:  {config['package_name']}")
    print(f"    Interval: {config['check_interval']}s")
    print(f"    Discord:  {'Enabled' if config.get('discord', {}).get('enabled') else 'Disabled'}")
    
    inp = input(f"\n{C.Y}Edit config? (y/n): {C.X}").strip().lower()
    if inp == 'y':
        config = setup_interactive(config)
    
    package = config['package_name']
    activity = config.get('activity_name', '.startup.ActivitySplash')
    place_id = config['place_id']
    job_id = config.get('job_id', '')
    interval = config.get('check_interval', 300)
    delay = config.get('rejoin_delay', 5)
    
    state.start_time = datetime.now()
    
    # Start Discord bot if enabled
    bot = None
    discord_task = None
    
    async def discord_loop():
        nonlocal bot
        bot = await run_discord_bot(config)
        if bot:
            print(f"{C.G}[*] Discord bot connected!{C.X}")
            await bot.listen_commands()
    
    if config.get('discord', {}).get('enabled') and DISCORD_AVAILABLE:
        discord_thread = threading.Thread(target=lambda: asyncio.run(discord_loop()), daemon=True)
        discord_thread.start()
    
    print(f"\n{C.G}[*] Starting monitor...{C.X}")
    print(f"{C.Y}[!] Make sure you're logged in to Roblox!{C.X}")
    print(f"{C.Y}[!] Press Ctrl+C to stop{C.X}\n")
    
    # Initial launch
    print(f"{C.B}[*] Launching game...{C.X}")
    launch_game(package, activity, place_id, job_id)
    time.sleep(10)
    
    try:
        while state.running:
            state.last_check = datetime.now().strftime("%H:%M:%S")
            state.roblox_running = is_running(package)
            
            if state.force_rejoin:
                state.force_rejoin = False
                state.rejoins += 1
                print(f"{C.Y}[!] Force rejoin triggered!{C.X}")
                stop_app(package)
                time.sleep(delay)
                launch_game(package, activity, place_id, job_id)
                time.sleep(10)
                if bot:
                    asyncio.run(bot.notify_rejoin_success(state.rejoins))
            
            elif state.roblox_running:
                print(f"{C.G}[✓] Roblox running. Next check in {interval}s{C.X}")
            else:
                state.rejoins += 1
                print(f"{C.R}[!] DC detected! Rejoining... (#{state.rejoins}){C.X}")
                
                if bot:
                    asyncio.run(bot.notify_dc(state.rejoins))
                
                time.sleep(delay)
                launch_game(package, activity, place_id, job_id)
                time.sleep(10)
                
                if bot and is_running(package):
                    asyncio.run(bot.notify_rejoin_success(state.rejoins))
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        state.running = False
        print(f"\n\n{C.Y}[*] Stopped. Total rejoins: {state.rejoins}{C.X}")
        if bot:
            asyncio.run(bot.send_message("🛑 Monitor stopped."))

if __name__ == "__main__":
    main()
