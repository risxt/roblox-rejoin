#!/usr/bin/env python3
"""
Debug script v2 - Auto-run with delay, shows what is being matched

Usage:
    python debug_detect.py                    # 5 second delay
    python debug_detect.py 10                 # 10 second delay
    python debug_detect.py 10 com.roblox.clien1  # Custom delay and package
"""
import subprocess
import sys
import time

# Parse arguments
delay = 5
package = "com.roblox.clien1"

if len(sys.argv) >= 2:
    if sys.argv[1].isdigit():
        delay = int(sys.argv[1])
        if len(sys.argv) >= 3:
            package = sys.argv[2]
    else:
        package = sys.argv[1]

print(f"""
╔════════════════════════════════════════════════════╗
║   PROCESS DETECTION DEBUG v2 (AUTO-RUN)           ║
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

def test_with_output(name, cmd):
    """Test a method and show WHAT was matched"""
    print(f"{'─'*50}")
    print(f"[{name}]")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        
        if result.stdout.strip():
            # Show what was found
            lines = result.stdout.strip().split('\n')
            print(f"  ✅ DETECTED - Found {len(lines)} match(es):")
            for line in lines[:5]:  # Show max 5 lines
                print(f"     → {line[:60]}")
            if len(lines) > 5:
                print(f"     ... and {len(lines)-5} more")
            return True
        else:
            print(f"  ❌ Not detected")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"  ⏰ TIMEOUT")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

results = {}

# Test 1: /proc/*/cmdline - show matched lines
print("\n=== TESTING DETECTION METHODS ===\n")

results['proc_cmdline'] = test_with_output(
    "/proc/*/cmdline",
    f"cat /proc/*/cmdline 2>/dev/null | tr '\\0' '\\n' | grep '{package}'"
)

# Test 2: pgrep -f - show PIDs
results['pgrep'] = test_with_output(
    "pgrep -f",
    f"pgrep -f '{package}' 2>/dev/null"
)

# Test 3: What processes contain our package name?
print(f"\n{'─'*50}")
print("[DEBUG] All processes containing package name:")
try:
    result = subprocess.run(
        f"cat /proc/*/cmdline 2>/dev/null | tr '\\0' '\\n' | sort -u | grep -i 'roblox'",
        shell=True, capture_output=True, text=True, timeout=10
    )
    if result.stdout.strip():
        for line in result.stdout.strip().split('\n')[:10]:
            print(f"  • {line[:60]}")
    else:
        print("  (none)")
except:
    print("  (error)")

# Test 4: Check if specific process exists
print(f"\n{'─'*50}")
print(f"[DEBUG] PIDs for {package}:")
try:
    result = subprocess.run(
        f"pgrep -f '{package}' 2>/dev/null",
        shell=True, capture_output=True, text=True, timeout=10
    )
    if result.stdout.strip():
        pids = result.stdout.strip().split('\n')
        for pid in pids[:5]:
            # Get process name for this PID
            name_result = subprocess.run(
                f"cat /proc/{pid}/cmdline 2>/dev/null | tr '\\0' ' '",
                shell=True, capture_output=True, text=True, timeout=5
            )
            name = name_result.stdout.strip()[:50] if name_result.stdout else "(unknown)"
            print(f"  PID {pid}: {name}")
    else:
        print("  (no PIDs found)")
except:
    print("  (error)")

# Summary
print(f"""

{'═'*50}
  RESULT SUMMARY
{'═'*50}

  /proc/*/cmdline: {"✅ DETECTED" if results.get('proc_cmdline') else "❌ NOT DETECTED"}
  pgrep -f:        {"✅ DETECTED" if results.get('pgrep') else "❌ NOT DETECTED"}

  Overall: {"🟢 RUNNING" if any(results.values()) else "🔴 CRASHED/STOPPED"}

{'═'*50}
""")
