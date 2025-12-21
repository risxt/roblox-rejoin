#!/usr/bin/env python3
"""
Debug script v5 - Tests the fixed detection method
Now searches for 'roblox' and skips /proc/self and false positives

Usage:
    python debug_detect.py                    # 5 second delay
    python debug_detect.py 0                  # No delay
"""
import subprocess
import sys
import time

delay = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 5

print(f"""
╔════════════════════════════════════════════════════╗
║   PROCESS DETECTION DEBUG v5 (FINAL)              ║
╚════════════════════════════════════════════════════╝
""")

if delay > 0:
    print(f"⏳ Starting in {delay} seconds...")
    for i in range(delay, 0, -1):
        print(f"\r   {i}s...  ", end="", flush=True)
        time.sleep(1)
    print("\r   Go!    ")

print("\n=== TESTING DETECTION ===\n")

def is_running_test():
    """Test the actual detection logic"""
    try:
        # Get all PIDs that have 'roblox' in cmdline
        result = subprocess.run(
            "grep -il 'roblox' /proc/[0-9]*/cmdline 2>/dev/null",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        print(f"[1] grep output: {result.stdout.strip() or '(empty)'}")
        
        if not result.stdout.strip():
            print("    → No files found containing 'roblox'")
            return False
        
        pid_files = result.stdout.strip().split('\n')
        print(f"    → Found {len(pid_files)} file(s)")
        
        for pid_file in pid_files:
            try:
                # Skip /proc/self and /proc/thread-self
                if '/proc/self/' in pid_file or '/proc/thread-self/' in pid_file:
                    print(f"\n[SKIP] {pid_file} (symlink to current process)")
                    continue
                
                pid = pid_file.split('/')[2]
                
                with open(f'/proc/{pid}/cmdline', 'r') as f:
                    cmdline = f.read()
                
                cmdline_str = cmdline.replace('\x00', ' ').strip().lower()
                
                print(f"\n[CHECK] PID {pid}")
                print(f"        cmdline: {cmdline_str[:50]}...")
                
                # Check for false positives
                false_positives = ['grep', 'python', 'cat', 'sh', 'bash', 'awk', 'sed', 'tr']
                is_false_positive = False
                
                first_word = cmdline_str.split()[0] if cmdline_str.split() else ""
                for fp in false_positives:
                    if fp in first_word:
                        is_false_positive = True
                        print(f"        ⚠️ FALSE POSITIVE: {fp} in command")
                        break
                
                if not is_false_positive and 'roblox' in cmdline_str:
                    print(f"        ✅ REAL ROBLOX PROCESS!")
                    return True
                    
            except (FileNotFoundError, PermissionError, IndexError, ValueError) as e:
                print(f"        ⚠️ Error: {e}")
                continue
        
        return False
        
    except Exception as e:
        print(f"Exception: {e}")
        return True

running = is_running_test()

print(f"""

{'═'*50}
  RESULT: {"🟢 RUNNING" if running else "🔴 CRASHED/STOPPED"}
{'═'*50}
""")
