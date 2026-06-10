import sys
import os
import subprocess

# Add ecosystem to path
sys.path.append(os.path.expanduser("~/projects/ecosystem"))

def check_syntax(path):
    print(f"[*] Checking syntax: {path}")
    res = subprocess.run([sys.executable, "-m", "py_compile", path], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[!] Syntax Error in {path}:\n{res.stderr}")
        return False
    return True

def check_imports():
    print("[*] Checking imports...")
    try:
        from core.manager import GeminiManager
        from core.branding import init_colors, run_menu, get_text
        mgr = GeminiManager()
        print("[✓] Core imports OK")
        return True
    except Exception as e:
        print(f"[!] Import Error: {e}")
        return False

def check_locales():
    loc_dir = os.path.expanduser("~/projects/ecosystem/core/locales")
    langs = ["pt", "en", "es", "fr", "hi", "ja", "ko", "ru", "zh", "de"]
    missing = []
    for l in langs:
        if not os.path.exists(os.path.join(loc_dir, f"{l}.json")):
            missing.append(l)
    if missing:
        print(f"[!] Missing locales: {missing}")
        return False
    print("[✓] All 10 locales present")
    return True

if __name__ == "__main__":
    success = True
    success &= check_syntax(os.path.expanduser("~/projects/ecosystem/core/manager.py"))
    success &= check_syntax(os.path.expanduser("~/projects/ecosystem/core/branding.py"))
    success &= check_syntax(os.path.expanduser("~/projects/ecosystem/core/dashboard.py"))
    success &= check_syntax(os.path.expanduser("~/projects/ecosystem/core/switcher.py"))
    success &= check_syntax(os.path.expanduser("~/projects/ecosystem/core/agy3.py"))
    success &= check_syntax(os.path.expanduser("~/projects/ecosystem/core/oauth.py"))
    
    success &= check_imports()
    success &= check_locales()
    
    if success:
        print("\n✨ SYSTEM AUDIT PASSED: 0 ERRORS FOUND")
    else:
        print("\n[!] AUDIT FAILED: FIX ERRORS ABOVE")
        sys.exit(1)
