#!/usr/bin/env python3
__version__ = "0.0.1"
import os
import sys
import json
import curses
import argparse

# Add system brain to path
BRAIN_PATH = os.path.expanduser("~/projects/ecosystem")
if BRAIN_PATH not in sys.path: sys.path.insert(0, BRAIN_PATH)

try:
    from core.manager import GeminiManager, ACCOUNTS_FILE, KEYS_FILE, TOKENS_DIR
    from core.branding import init_colors, run_menu, get_text
except ImportError as e:
    print(f"[!] Critical: Ecosystem 'Brain' error: {e}")
    sys.exit(1)

mgr = GeminiManager()

def identity_menu(stdscr):
    acc = mgr.load_json(ACCOUNTS_FILE)
    keys = mgr.load_json(KEYS_FILE)
    active_email = mgr.get_active_email_from_sync_file() or acc.get('active')
    
    tokens_emails = [f.replace('.json', '') for f in os.listdir(TOKENS_DIR) if f.endswith('.json')]
    all_emails = sorted(list(set(([active_email] if active_email else []) + acc.get('old', []) + list(keys.keys()) + tokens_emails)))
    
    options = []
    for email in all_emails:
        label = f"[*] {email}" if email == active_email else f"[ ] {email}"
        options.append({"label": label, "value": email})
    
    sel = run_menu(stdscr, "GMN Switcher", options)
    if sel:
        email = sel["value"]
        token_path = os.path.join(TOKENS_DIR, f"{email}.json")
        if os.path.exists(token_path):
            creds = mgr.load_json(token_path)
            mgr.sync_to_gemini_cli(email, creds)
            try:
                acc["active"] = email
                mgr.save_json(ACCOUNTS_FILE, acc)
            except:
                pass
            return f"Activated {email}"
    return None

def main():
    parser = argparse.ArgumentParser(description="GMN Switcher - Professional Account Manager")
    parser.add_argument("--list", action="store_true", help="List identities")
    args = parser.parse_args()

    if args.list:
        acc = mgr.load_json(ACCOUNTS_FILE)
        print(f"◈ Active: {acc.get('active', 'None')}")
        sys.exit(0)

    original_stdout_fd = os.dup(1)
    os.dup2(2, 1)
    try: result = curses.wrapper(identity_menu)
    finally:
        os.dup2(original_stdout_fd, 1)
        os.close(original_stdout_fd)
        if result: print(f"[✓] {result}")

if __name__ == "__main__":
    main()
