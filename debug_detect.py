#!/usr/bin/env python3
"""
Debug script v3 - Fixed false positive detection

Usage:
    python debug_detect.py                    # 5 second delay, default package
    python debug_detect.py 10                 # 10 second delay
    python debug_detect.py 10 com.roblox.clienv  # Custom delay and package
"""
import subprocess
import sys
import time

# Parse arguments
delay = 5
package = "com.roblox.clienv"  # Changed default to clienv

if len(sys.argv) >= 2:
    if sys.argv[1].isdigit():
        delay = int(sys.argv[1])
        if len(sys.argv) >= 3:
            package = sys.argv[2]
    else:
        package = sys.argv[1]

print(f"""
╔════════════════════════════════════════════════════╗
║   PROCESS DETECTION DEBUG v3 (FIXED)              ║
╠════════════════════════════════════════════════════╣
║   Package: {package:<38} ║
╚════════════════════════════════════════════════════╝
""")

print(f"⏳ Auto-starting in {delay} seconds...")
print(f"   Switch to Roblox window OR close Roblox now!")
print()

# Countdown
for i in range(delay, 0, -1):
    print(f"\r   Starting in {i}s...  ", end="", flush=True)
    time.sleep(1)
print("\r   Starting now!       ")
print()

def test_method(name, cmd, timeout=10):
    """Test a method and show result"""
    print(f"{'─'*50}")
    print(f"[{name}]")
    print(f"  CMD: {cmd[:70]}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        
        if "FOUND" in result.stdout or (result.returncode == 0 and result.stdout.strip()):
            lines = result.stdout.strip().split('\n')
            print(f"  ✅ DETECTED")
            if result.stdout.strip() and result.stdout.strip() != "FOUND":
                for line in lines[:3]:
                    print(f"     → {line[:50]}")
            return True
        else:
            print(f"  ❌ NOT DETECTED")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"  ⏰ TIMEOUT")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

results = {}

print("\n=== TESTING DETECTION METHODS ===\n")

# Method 1: /proc/*/cmdline with proper check (process starts with package name)
results['proc_cmdline_fixed'] = test_method(
    "Method 1: /proc cmdline (FIXED - checks process name)",
    f"for f in /proc/*/cmdline; do "
    f"if cat \"$f\" 2>/dev/null | tr '\\0' ' ' | grep -q '^{package}'; then "
    f"echo FOUND; break; fi; done"
)

# Method 2: ps -A -o NAME
results['ps_name'] = test_method(
    "Method 2: ps -A -o NAME (exact match)",
    f"ps -A -o NAME 2>/dev/null | grep -q '^{package}$' && echo FOUND"
)

# Method 3: dumpsys activity processes
results['dumpsys'] = test_method(
    "Method 3: dumpsys activity processes",
    f"dumpsys activity processes 2>/dev/null | grep -q 'ProcessRecord.*{package}' && echo FOUND"
)

# DEBUG: Show what processes exist with 'roblox' in name
print(f"\n{'─'*50}")
print("[DEBUG] All 'roblox' processes (for reference):")
try:
    result = subprocess.run(
        f"ps -A 2>/dev/null | grep -i roblox | head -5",
        shell=True, capture_output=True, text=True, timeout=10
    )
    if result.stdout.strip():
        for line in result.stdout.strip().split('\n'):
            print(f"  • {line[:60]}")
    else:
        print("  (none found)")
except:
    print("  (error)")

# Summary
any_detected = any(results.values())
print(f"""

{'═'*50}
  RESULT SUMMARY
{'═'*50}

  Method 1 (/proc cmdline): {"✅ DETECTED" if results.get('proc_cmdline_fixed') else "❌ NOT DETECTED"}
  Method 2 (ps -A):         {"✅ DETECTED" if results.get('ps_name') else "❌ NOT DETECTED"}
  Method 3 (dumpsys):       {"✅ DETECTED" if results.get('dumpsys') else "❌ NOT DETECTED"}

  Overall: {"🟢 RUNNING" if any_detected else "🔴 CRASHED/STOPPED"}

{'═'*50}
""")

if not any_detected:
    print("  ✅ This is correct if Roblox is NOT running!")
else:
    print("  ✅ This is correct if Roblox IS running!")
