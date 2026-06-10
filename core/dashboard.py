#!/usr/bin/env python3
import os
import sys
import time
import curses
from core.manager import GeminiManager, TOKENS_DIR
from core.branding import init_colors, draw_header, draw_footer, get_text

def run_dashboard(stdscr):
    os.environ.setdefault('ESCDELAY', '25')
    init_colors()
    curses.curs_set(0)
    stdscr.keypad(True)
    stdscr.timeout(1000)
    
    mgr = GeminiManager()
    
    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        
        try: stdscr.box()
        except: pass
        
        y = draw_header(stdscr, y_start=2)
        
        title = " ◈ GEMINI ECOSYSTEM DASHBOARD ◈ "
        stdscr.addstr(y, (w - len(title)) // 2, title, curses.color_pair(1) | curses.A_BOLD)
        y += 2
        
        # Stats
        tokens = [f for f in os.listdir(TOKENS_DIR) if f.endswith(".json")]
        model = mgr.get_active_model()
        active_email = mgr.get_active_email_from_sync_file() or mgr.load_json(os.path.join(os.path.expanduser("~/.ecosystem"), "google_accounts.json")).get("active", "None")
        
        info_lines = [
            f"Active Model:   {model.upper()}",
            f"Active Account: {active_email}",
            f"Identities:     {len(tokens)}",
            f"Environment:    TERMUX/ANDROID",
            f"Status:         SURGICAL LINK ESTABLISHED"
        ]
        
        for line in info_lines:
            if y >= h - 3: break
            stdscr.addstr(y, 6, "• " + line, curses.A_BOLD if "Active" in line else 0)
            y += 1
            
        y += 1
        stdscr.addstr(y, 6, "Available Uplinks:", curses.color_pair(10))
        y += 1
        stdscr.addstr(y, 8, "- auth:  GMN Switcher Interface", curses.A_DIM)
        y += 1
        stdscr.addstr(y, 8, "- agy3:  agy-3-proxy Interface", curses.A_DIM)
        
        draw_footer(stdscr, f" [ESC] Exit | {time.strftime('%H:%M:%S')} ")
        
        stdscr.refresh()
        key = stdscr.getch()
        if key == 27: break
        
def main():
    try:
        curses.wrapper(run_dashboard)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
