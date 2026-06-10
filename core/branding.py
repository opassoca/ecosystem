import glob
import os
import re as _re
import curses
import json

# Localization Manager
LOCALES_DIR = os.path.join(os.path.dirname(__file__), "locales")

def get_text(key, default=""):
    if not hasattr(get_text, "data"):
        try:
            # We use absolute paths to avoid import issues during initialization
            lang_path = os.path.expanduser("~/.ecosystem/config.json")
            if os.path.exists(lang_path):
                with open(lang_path, 'r') as f: lang = json.load(f).get("language", "auto")
            else: lang = "auto"
        except: lang = "auto"
        
        if lang == "auto":
            lang = os.environ.get("LANG", "pt_BR").split(".")[0].split("_")[0]
        
        p = os.path.join(LOCALES_DIR, f"{lang}.json")
        if not os.path.exists(p): p = os.path.join(LOCALES_DIR, "en.json")
        try:
            with open(p, "r", encoding="utf-8") as f: get_text.data = json.load(f)
        except: get_text.data = {}
    return get_text.data.get(key, default)

def hex_to_curses_rgb(h):
    h = h.lstrip('#')
    r,g,b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return int(r/255*1000), int(g/255*1000), int(b/255*1000)

def get_branding():
    bundle_path = "/data/data/com.termux/files/usr/lib/node_modules/@google/gemini-cli/bundle/"
    files = glob.glob(os.path.join(bundle_path, "interactiveCli-*.js"))
    branding = {
        "logo": "", "icon": "",
        "colors": {
            "accent":    "#D7AFFF",
            "secondary": "#87D7D7",
            "blue":      "#87AFFF",
            "gradient":  ["#4796E4", "#847ACE", "#C3677F"]
        }
    }
    chunk_files = glob.glob(os.path.join(bundle_path, "chunk-*.js"))
    chunk = chunk_files[0] if chunk_files else ""
    if os.path.exists(chunk):
        try:
            with open(chunk, "r", encoding="utf-8") as f: content = f.read()
            dm = _re.search(r"var darkTheme\s*=\s*\{([^}]+)\}", content)
            if dm:
                ds = dm.group(1)
                def ec(key):
                    m = _re.search(rf'"{key}\s*:\s*(#[0-9a-fA-F]+)"', ds)
                    return m.group(1) if m else None
                ap=ec("AccentPurple"); ac=ec("AccentCyan"); ab=ec("AccentBlue")
                gm=_re.search(r"GradientColors\s*:\s*\[([^\]]+)\]", ds)
                if ap: branding["colors"]["accent"]    = ap
                if ac: branding["colors"]["secondary"] = ac
                if ab: branding["colors"]["blue"]      = ab
                if gm: branding["colors"]["gradient"]  = _re.findall(r'"(#[0-9a-fA-F]+)"', gm.group(1))
        except: pass
    if not files: return branding
    try:
        with open(files[0], "r", encoding="utf-8") as f: content = f.read()
        logo_match = _re.search(r"var longAsciiLogoCompactText = `(.*?)`;", content, _re.DOTALL)
        icon_match = _re.search(r"var DEFAULT_ICON = `(.*?)`;", content, _re.DOTALL)
        if logo_match: branding["logo"] = logo_match.group(1).strip().encode().decode("unicode_escape")
        if icon_match: branding["icon"] = icon_match.group(1).strip().encode().decode("unicode_escape")
    except: pass
    return branding

def init_colors():
    if not curses.has_colors(): return
    curses.start_color()
    curses.use_default_colors()
    b = get_branding(); c = b["colors"]
    try:
        if curses.can_change_color() and curses.COLORS >= 256:
            curses.init_color(20, *hex_to_curses_rgb(c["secondary"]))
            curses.init_color(21, *hex_to_curses_rgb(c["accent"]))
            curses.init_color(22, *hex_to_curses_rgb(c["blue"]))
            g = c["gradient"]
            curses.init_color(23, *hex_to_curses_rgb(g[0]))
            curses.init_color(24, *hex_to_curses_rgb(g[1]))
            curses.init_color(25, *hex_to_curses_rgb(g[2]))
            curses.init_pair(1,  20, -1)   # Cyan
            curses.init_pair(10, 21, -1)   # Purple
            curses.init_pair(11, 23, -1)   # Grad Blue
            curses.init_pair(12, 24, -1)   # Grad Purple
            curses.init_pair(13, 25, -1)   # Grad Pink
            curses.init_pair(7,  curses.COLOR_BLACK, 20) # Selected
        else:
            curses.init_pair(1,  curses.COLOR_CYAN, -1)
            curses.init_pair(10, curses.COLOR_MAGENTA, -1)
            curses.init_pair(7,  curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(2, curses.COLOR_YELLOW, -1)
        curses.init_pair(3, curses.COLOR_RED, -1)
        curses.init_pair(4, curses.COLOR_GREEN, -1)
    except: pass

def draw_header(stdscr, y_start=1):
    b = get_branding()
    logo_lines = b["logo"].split("\n")
    icon_lines = b["icon"].split("\n")
    h, w = stdscr.getmaxyx()
    full_width = 44
    start_x = (w - full_width) // 2
    for i in range(min(len(logo_lines), 4)):
        y = y_start + i
        if y >= h: break
        icon_part = (icon_lines[i] if i < len(icon_lines) else "").ljust(6)
        logo_part = logo_lines[i]
        try:
            icon_colors = [11, 11, 12, 13]
            icon_pair = curses.color_pair(icon_colors[i]) if i < len(icon_colors) else curses.color_pair(10)
            stdscr.addstr(y, start_x, icon_part, icon_pair)
            stdscr.addstr(y, start_x + 7, logo_part, curses.A_BOLD)
        except: pass
    return y_start + 5

def draw_footer(stdscr, text):
    h, w = stdscr.getmaxyx()
    try:
        stdscr.addstr(h-2, 2, "─" * (w-4), curses.A_DIM)
        stdscr.addstr(h-1, (w - len(text)) // 2, text, curses.A_DIM)
    except: pass

def run_menu(stdscr, title, options, y_start=2):
    init_colors()
    curses.curs_set(0)
    stdscr.keypad(True)
    current_idx = 0
    
    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        try: stdscr.box()
        except: pass
        
        y = draw_header(stdscr, y_start=y_start)
        # title is shown simply, no box
        stdscr.addstr(y, (w - len(title) - 4) // 2, f" ◈ {title.upper()} ◈ ", curses.color_pair(1) | curses.A_BOLD)
        y += 3
        
        if not options:
            stdscr.addstr(y, (w - 20) // 2, get_text("no_options", "(Nenhuma opção disponível)"), curses.color_pair(3))
        else:
            for i, opt in enumerate(options):
                if y >= h - 3: break
                attr = curses.color_pair(7) if i == current_idx else 0
                label = opt.get("label", str(opt))
                stdscr.addstr(y, 6, f"{'>' if i == current_idx else ' '} {label}", attr)
                y += 1
            
        draw_footer(stdscr, " [↑↓] Navigate | [ENTER] Select | [ESC] Cancel ")
        stdscr.refresh()
        
        key = stdscr.getch()
        if not options:
            if key in (27, ord('q'), ord('Q')): return None
            continue

        if key == curses.KEY_UP: current_idx = (current_idx - 1) % len(options)
        elif key == curses.KEY_DOWN: current_idx = (current_idx + 1) % len(options)
        elif key in (10, 13): return options[current_idx]
        elif key == 27: return None
