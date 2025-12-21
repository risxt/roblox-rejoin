#!/usr/bin/env python3
"""
Debug script to test which process detection method works on Redfinger
Run this while Roblox is RUNNING in floating window, then run again after CLOSING it

Usage:
    python debug_detect.py              # Test with default package
    python debug_detect.py com.roblox.clien1  # Test specific package
"""
import subprocess
import sys

# Default package - change this or pass as argument
PACKAGE = sys.argv[1] if len(sys.argv) > 1 else "com.roblox.clien1"

def test_method(name, cmd):
    """Test a detection method and return result"""
    print(f"\n{'─'*50}")
    print(f"[TEST] {name}")
    print(f"  CMD: {cmd[:80]}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        
        stdout_preview = result.stdout[:150].replace('\n', ' ') if result.stdout else '(empty)'
        stderr_preview = result.stderr[:80].replace('\n', ' ') if result.stderr else '(empty)'
        
        print(f"  Return: {result.returncode}")
        print(f"  Stdout: {stdout_preview}")
        if result.stderr:
            print(f"  Stderr: {stderr_preview}")
        
        # Check if process was found
        detected = False
        if "FOUND" in result.stdout or "echo FOUND" not in cmd:
            if result.returncode == 0 and result.stdout.strip():
                detected = True
        
        if detected:
            print(f"  ✅ DETECTED!")
            return True
        else:
            print(f"  ❌ Not detected")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"  ⏰ TIMEOUT!")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

print(f"""
╔════════════════════════════════════════════════════╗
║   PROCESS DETECTION DEBUG TOOL                     ║
╠════════════════════════════════════════════════════╣
║   Testing package: {PACKAGE:<30} ║
╚════════════════════════════════════════════════════╝
""")

print("Instructions:")
print("  1. Run this while Roblox is RUNNING")
print("  2. Note which methods show ✅")
print("  3. CLOSE Roblox manually")
print("  4. Run this AGAIN")
print("  5. Methods that showed ✅ before and ❌ now = WORKING")
print()
input("Press Enter to start testing... ")

# Test all methods
results = []

# Method 1: dumpsys activity processes
results.append(("dumpsys activity processes", 
    test_method("dumpsys activity processes", 
    f"dumpsys activity processes 2>/dev/null | grep -q '{PACKAGE}' && echo FOUND")))

# Method 2: dumpsys window windows  
results.append(("dumpsys window windows",
    test_method("dumpsys window windows",
    f"dumpsys window windows 2>/dev/null | grep -q '{PACKAGE}' && echo FOUND")))

# Method 3: /proc/*/cmdline
results.append(("/proc/*/cmdline",
    test_method("/proc/*/cmdline", 
    f"cat /proc/*/cmdline 2>/dev/null | tr '\\0' '\\n' | grep -q '{PACKAGE}' && echo FOUND")))

# Method 4: pidof
results.append(("pidof",
    test_method("pidof",
    f"pidof {PACKAGE} 2>/dev/null")))

# Method 5: ps -A | grep
results.append(("ps -A | grep",
    test_method("ps -A | grep",
    f"ps -A 2>/dev/null | grep -v grep | grep -q '{PACKAGE}' && echo FOUND")))

# Method 6: pgrep -f
results.append(("pgrep -f",
    test_method("pgrep -f",
    f"pgrep -f {PACKAGE} 2>/dev/null")))

# Method 7: dumpsys activity activities
results.append(("dumpsys activity activities",
    test_method("dumpsys activity activities",
    f"dumpsys activity activities 2>/dev/null | grep -q '{PACKAGE}' && echo FOUND")))

# Method 8: Check running services
results.append(("dumpsys activity services",
    test_method("dumpsys activity services",
    f"dumpsys activity services 2>/dev/null | grep -q '{PACKAGE}' && echo FOUND")))

# Summary
print(f"""

{'═'*50}
  SUMMARY
{'═'*50}
""")

working = []
not_working = []

for name, worked in results:
    if worked:
        working.append(name)
        print(f"  ✅ {name}")
    else:
        not_working.append(name)
        print(f"  ❌ {name}")

print(f"""
{'─'*50}
  Working methods: {len(working)}/{len(results)}
  
  💡 TIP: Run this again AFTER closing Roblox.
         The methods that change from ✅ to ❌ are 
         the ones that WORK for crash detection!
{'─'*50}
""")
