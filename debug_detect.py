#!/usr/bin/env python3
"""
Debug script v4 - Tests the fixed detection method

Usage:
    python debug_detect.py                    # 5 second delay
    python debug_detect.py 10                 # 10 second delay
    python debug_detect.py 10 com.roblox.clienv  # Custom delay and package
"""
import subprocess
import sys
import time
import os

# Parse arguments
delay = 5
package = "com.roblox.clienv"

if len(sys.argv) >= 2:
    if sys.argv[1].isdigit():
        delay = int(sys.argv[1])
        if len(sys.argv) >= 3:
            package = sys.argv[2]
    else:
        package = sys.argv[1]

print(f"""
╔════════════════════════════════════════════════════╗
║   PROCESS DETECTION DEBUG v4                       ║
╠════════════════════════════════════════════════════╣
║   Package: {package:<38} ║
╚════════════════════════════════════════════════════╝
""")

if delay > 0:
    print(f"⏳ Auto-starting in {delay} seconds...")
    for i in range(delay, 0, -1):
        print(f"\r   Starting in {i}s...  ", end="", flush=True)
        time.sleep(1)
    print("\r   Starting now!       ")
print()

# The actual detection function (same as in multi_rejoin.py)
def is_running_test(package):
    """
    Check if a Roblox package is running
    Uses /proc/cmdline but filters out false positives (grep, python, cat, sh)
    """
    try:
        # Get all PIDs that have the package name in cmdline
        result = subprocess.run(
            f"grep -l '{package}' /proc/*/cmdline 2>/dev/null",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if not result.stdout.strip():
            print(f"  grep found NO files containing '{package}'")
            return False, []
        
        # Check each matched PID
        pid_files = result.stdout.strip().split('\n')
        found_processes = []
        
        print(f"  grep found {len(pid_files)} file(s) containing package name")
        
        for pid_file in pid_files:
            try:
                pid = pid_file.split('/')[2]
                
                with open(f'/proc/{pid}/cmdline', 'r') as f:
                    cmdline = f.read()
                
                cmdline_str = cmdline.replace('\x00', ' ').strip()
                
                # Check for false positives
                false_positives = ['grep', 'python', 'cat', 'sh', 'bash', 'awk', 'sed', 'tr']
                is_false_positive = False
                first_word = cmdline_str.split()[0] if cmdline_str.split() else ""
                
                for fp in false_positives:
                    if first_word.startswith(fp) or first_word.endswith(f'/{fp}'):
                        is_false_positive = True
                        print(f"  PID {pid}: ⚠️ FALSE POSITIVE ({fp})")
                        print(f"           cmd: {cmdline_str[:50]}...")
                        break
                
                if not is_false_positive and package in cmdline_str:
                    print(f"  PID {pid}: ✅ REAL ROBLOX PROCESS")
                    print(f"           cmd: {cmdline_str[:50]}...")
                    found_processes.append(pid)
                    
            except (FileNotFoundError, PermissionError, IndexError) as e:
                print(f"  PID parse error: {e}")
                continue
        
        return len(found_processes) > 0, found_processes
        
    except subprocess.TimeoutExpired:
        return True, ["timeout"]
    except Exception as e:
        print(f"  Exception: {e}")
        return True, ["error"]

print("=== TESTING DETECTION ===\n")
running, processes = is_running_test(package)

print(f"""

{'═'*50}
  RESULT SUMMARY
{'═'*50}

  Package: {package}
  Running: {"✅ YES" if running else "❌ NO"}
  Real Roblox PIDs: {processes if processes else "(none)"}

  Overall: {"🟢 RUNNING" if running else "🔴 CRASHED/STOPPED"}

{'═'*50}
""")
