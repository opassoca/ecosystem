#!/usr/bin/env python3
__version__ = "0.0.1"
import os
import sys
import json
import socket
import subprocess
import time
import shutil
import argparse
import signal
import curses

# Add system brain to path
BRAIN_PATH = os.path.expanduser("~/projects/ecosystem")
if BRAIN_PATH not in sys.path: sys.path.insert(0, BRAIN_PATH)

try:
    from core.manager import GeminiManager, ECOSYSTEM_DIR, CLAUDE_JSON, ACCOUNTS_FILE, GEMINI_DIR, TOKENS_DIR
    from core.branding import init_colors, draw_header, get_text
except ImportError as e:
    print(f"[!] Critical: Gemini Ecosystem (Brain) error: {e}")
    sys.exit(1)

mgr = GeminiManager()
AGY_LAUNCHER = shutil.which("agy") or "/data/data/com.termux/files/usr/bin/agy"

def sync_before_launch():
    """Syncs everything before launching agy using Brain logic."""
    # Backup configurations
    mgr.backup_config(CLAUDE_JSON)
    settings_path = os.path.join(GEMINI_DIR, "antigravity-cli", "settings.json")
    if os.path.exists(settings_path):
        mgr.backup_config(settings_path)
    
    # Auto-rotate account if quota is low (< 5% left or has error)
    active_model = mgr.get_active_model()
    active_email = mgr.get_active_email_from_sync_file() or mgr.load_json(ACCOUNTS_FILE).get('active')
    
    if active_email:
        cache_path = os.path.join(ECOSYSTEM_DIR, "quota_cache.json")
        quotas = mgr.load_json(cache_path)
        active_quota = quotas.get(active_email, {})
        models = active_quota.get("models", {})
        
        m_key = next((k for k in models if active_model.lower() in k.lower()), None)
        used = models.get(m_key, {}).get("used", 0.0) if m_key else 0.0
        
        if used >= 95.0 or active_quota.get("error"):
            print(f"[!] Active account {active_email} quota is low or exhausted ({used}% used). Rotating...")
            new_email, new_used = mgr.smart_switch_identity()
            if new_email:
                print(f"[✓] Automatically switched to {new_email} ({new_used}% used)")
            else:
                print("[!] No alternative accounts with available quota found.")

def main():
    parser = argparse.ArgumentParser(description="agy-3-proxy - Antigravity Wrapper with Brain Integration")
    parser.add_argument("-stats", action="store_true", help="Show usage metrics")
    parser.add_argument("-model", action="store_true", help="Switch active model")
    parser.add_argument("-act", action="store_true", help="Manage accounts (GMN Switcher)")
    parser.add_argument("-auth", action="store_true", help="Brain OAuth login")
    parser.add_argument("-smart", action="store_true", help="Extreme: Auto-switch to identity with quota")
    
    args, unknown = parser.parse_known_args()

    if any([args.stats, args.model, args.act, args.auth, args.smart]):
        if args.smart:
            print("[*] Engaging Brain Smart-Switch...")
            email, used = mgr.smart_switch_identity()
            if email:
                print(f"[✓] Switched to {email} (Usage: {used}%)")
            else:
                print("[!] No identities with available quota found.")
        elif args.stats:
            print(f"[*] {get_text('stats_loading', 'Fetching metrics via Brain...')}")
            try:
                from rich.console import Console
                from rich.table import Table
                console = Console()
                
                active_model = mgr.get_active_model()
                acc = mgr.load_json(ACCOUNTS_FILE)
                active_email = mgr.get_active_email_from_sync_file() or acc.get('active')
                
                # Fetch quotas
                quotas = mgr.get_all_quotas()
                
                console.print(f"\n[bold cyan]◈ AGY3 PROXY METRICS ◈[/]")
                console.print(f"Target Model:  [bold green]{active_model.upper()}[/]")
                console.print(f"Active Account: [bold yellow]{active_email or 'None'}[/]\n")
                
                table = Table(expand=True)
                table.add_column("Account / Identity", style="magenta")
                table.add_column("Model ID", style="cyan")
                table.add_column("Usage", justify="right")
                table.add_column("Status", justify="center")
                
                tokens_emails = [f.replace('.json', '') for f in os.listdir(TOKENS_DIR) if f.endswith('.json')]
                all_emails = sorted(list(set(([active_email] if active_email else []) + acc.get('old', []) + tokens_emails)))
                for email in all_emails:
                    status = "[bold green]ACTIVE[/]" if email == active_email else "[dim]Inactive[/]"
                    q_data = quotas.get(email, {})
                    
                    if not q_data:
                        table.add_row(email, "-", "[yellow]No usage data[/]", status)
                        continue
                    
                    if "error" in q_data:
                        table.add_row(email, "-", f"[red]Error: {q_data['error']}[/]", status)
                        continue
                        
                    models = q_data.get("models", {})
                    if not models:
                        table.add_row(email, "-", "[yellow]No usage data[/]", status)
                        continue
                        
                    curr_email = email
                    curr_status = status
                    for model_id, m_info in models.items():
                        used = m_info.get("used", 100.0)
                        remaining = 100.0 - used
                        p_color = "green" if remaining > 50 else ("yellow" if remaining > 20 else "red")
                        
                        table.add_row(
                            curr_email,
                            model_id,
                            f"[{p_color}]{used:.1f}% used[/]",
                            curr_status
                        )
                        curr_email = ""
                        curr_status = ""
                
                console.print(table)
            except Exception as e:
                print(f"[!] Error displaying stats: {e}")
        elif args.auth:
            email = mgr.run_oauth_flow()
            if email: print(f"[✓] Authenticated as {email}")
        elif args.act:
            # We call the auth command
            subprocess.run([os.path.expanduser("~/bin/auth")])
        elif args.model:
            def model_menu(stdscr):
                models = [
                    {"label": "Gemini 3.1 Flash (Lite)", "value": "gemini-3.1-flash-lite"},
                    {"label": "Gemini 3.1 Pro (Preview)", "value": "gemini-3.1-pro-preview"},
                    {"label": "Gemini 3.0 Flash", "value": "gemini-3.0-flash"},
                    {"label": "Gemini 3.0 Pro", "value": "gemini-3.0-pro"},
                    {"label": "Gemini 2.5 Flash", "value": "gemini-2.5-flash"},
                    {"label": "Gemini 2.5 Pro", "value": "gemini-2.5-pro"}
                ]
                from core.branding import run_menu
                sel = run_menu(stdscr, "Select Model", models)
                if sel:
                    mgr.set_active_model(sel["value"])
                    return f"Selected {sel['label']}"
                return None
            res = curses.wrapper(model_menu)
            if res: print(f"[✓] {res}")
        sys.exit(0)

    sync_before_launch()
    
    try:
        # Prevent proxy duplication and network interference by isolating shell proxy env vars
        custom_env = os.environ.copy()
        custom_env.pop("HTTP_PROXY", None)
        custom_env.pop("HTTPS_PROXY", None)
        custom_env.pop("ALL_PROXY", None)
        custom_env.pop("http_proxy", None)
        custom_env.pop("https_proxy", None)
        custom_env.pop("all_proxy", None)
        custom_env.pop("no_proxy", None)
        custom_env.pop("NO_PROXY", None)
        custom_env.pop("CODE_ASSIST_ENDPOINT", None)
        custom_env.pop("CODE_ASSIST_API_VERSION", None)
        
        subprocess.run([AGY_LAUNCHER] + unknown, env=custom_env)
    except KeyboardInterrupt:
        pass
    finally:
        mgr.restore_config(CLAUDE_JSON)
        settings_path = os.path.join(GEMINI_DIR, "antigravity-cli", "settings.json")
        if os.path.exists(settings_path):
            mgr.restore_config(settings_path)

if __name__ == "__main__":
    main()
