#!/usr/bin/env python3
"""
Debug script to test which process detection method works on your device
Run this while Roblox is running in floating window
"""
import subprocess

# Change this to your actual package name
PACKAGE = "com.roblox.clienv"

def test_method(name, cmd, shell=True):
    print(f"\n[TEST] {name}")
    print(f"  CMD: {cmd}")
    try:
        if shell:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True)
        
        print(f"  Return code: {result.returncode}")
        print(f"  Stdout: {result.stdout[:200] if result.stdout else '(empty)'}")
        print(f"  Stderr: {result.stderr[:100] if result.stderr else '(empty)'}")
        
        if result.returncode == 0 and result.stdout.strip():
            print(f"  ✅ DETECTED!")
            return True
        else:
            print(f"  ❌ Not detected")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

print(f"Testing package: {PACKAGE}")
print("=" * 50)

# Test all methods
results = []

results.append(("pgrep -f", test_method("pgrep -f", f"pgrep -f {PACKAGE}")))
results.append(("pgrep array", test_method("pgrep (array)", ["pgrep", "-f", PACKAGE], shell=False)))
results.append(("pidof", test_method("pidof", f"pidof {PACKAGE}")))
results.append(("pidof -s", test_method("pidof -s", f"pidof -s {PACKAGE}")))
results.append(("ps -A grep", test_method("ps -A | grep", f"ps -A | grep {PACKAGE}")))
results.append(("ps -e grep", test_method("ps -e | grep", f"ps -e | grep {PACKAGE}")))
results.append(("ps aux grep", test_method("ps aux | grep", f"ps aux 2>/dev/null | grep -v grep | grep {PACKAGE}")))
results.append(("dumpsys window", test_method("dumpsys window", f"dumpsys window windows | grep -i {PACKAGE}")))
results.append(("dumpsys activity", test_method("dumpsys activity", f"dumpsys activity activities | grep {PACKAGE}")))
results.append(("dumpsys processes", test_method("dumpsys processes", f"dumpsys activity processes | grep {PACKAGE}")))
results.append(("proc cmdline", test_method("/proc/*/cmdline", f"cat /proc/*/cmdline 2>/dev/null | tr '\\0' '\\n' | grep {PACKAGE}")))
results.append(("am stack", test_method("am stack list", f"am stack list 2>/dev/null")))

print("\n" + "=" * 50)
print("SUMMARY - Methods that work:")
for name, worked in results:
    status = "✅" if worked else "❌"
    print(f"  {status} {name}")
