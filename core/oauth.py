#!/usr/bin/env python3
import json, os, time, base64, shutil, sys, urllib.request, urllib.parse

OAUTH_CREDS   = os.path.expanduser("~/.gemini/oauth_creds.json")
AUTH_DIR      = os.path.expanduser("~/.ecosystem")
TOKENS_DIR    = os.path.join(AUTH_DIR, "id-tokens")
ACCOUNTS_FILE = os.path.join(AUTH_DIR, "google_accounts.json")
QUOTA_CACHE   = os.path.join(AUTH_DIR, "quota_cache.json")
PID_FILE      = os.path.join(AUTH_DIR, "sync-daemon.pid")
ACTIVITY_FILE = os.path.join(AUTH_DIR, "last_activity")
SECRETS_FILE  = os.path.join(AUTH_DIR, "secrets", "google_api.json")

CLIENT_ID     = None
CLIENT_SECRET = None

def load_secrets():
    global CLIENT_ID, CLIENT_SECRET
    CLIENT_ID = os.environ.get("GEMINI_CLIENT_ID") or CLIENT_ID
    CLIENT_SECRET = os.environ.get("GEMINI_CLIENT_SECRET") or CLIENT_SECRET
    if os.path.exists(SECRETS_FILE):
        try:
            with open(SECRETS_FILE) as f:
                d = json.load(f)
                CLIENT_ID = CLIENT_ID or d.get("client_id")
                CLIENT_SECRET = CLIENT_SECRET or d.get("client_secret")
        except: pass

REFRESH_URL   = "https://oauth2.googleapis.com/token"
QUOTA_URL     = "https://cloudcode-pa.googleapis.com/v1internal:retrieveUserQuota"

REFRESH_BEFORE = 600
ACTIVE_WINDOW  = 300 
POLL_INTERVAL  = 10  

LAST_MTAGS = {} # email -> mtime

def check_single_instance():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, 0)
            sys.exit(0)
        except (ProcessLookupError, ValueError, PermissionError):
            pass
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

def decode_email(id_token):
    try:
        payload = id_token.split('.')[1]
        padded  = payload + '=' * (-len(payload) % 4)
        return json.loads(base64.b64decode(padded)).get('email')
    except: return None

def refresh_token(creds):
    rt = creds.get('refresh_token')
    if not rt: return None
    try:
        data = urllib.parse.urlencode({
            'grant_type': 'refresh_token',
            'refresh_token': rt,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
        }).encode()
        req = urllib.request.Request(REFRESH_URL, data=data,
              headers={'Content-Type': 'application/x-www-form-urlencoded'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            new = json.load(resp)
        if 'access_token' not in new: return None
        creds['access_token'] = new['access_token']
        creds['expiry_date'] = int(time.time() * 1000) + new.get('expires_in', 3600) * 1000
        if 'id_token' in new: creds['id_token'] = new['id_token']
        return creds
    except: return None

def fetch_all_quotas(access_token):
    try:
        req_data = json.dumps({"project": "cloudshell-gca"}).encode()
        req = urllib.request.Request(QUOTA_URL, data=req_data,
              headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
        models_quota = {}
        for b in data.get("buckets", []):
            mid = b.get("modelId")
            if mid:
                rf = b.get("remainingFraction")
                used_val = round((1.0 - float(rf)) * 100.0, 1) if rf is not None else 0.0
                models_quota[mid] = {"used": used_val, "reset": b.get("resetTime")}
        return models_quota
    except Exception as e:
        if "429" in str(e): return "EXHAUSTED"
    return None

def auto_switch_logic(exhausted_email, cache):
    """Extreme Mode: Automatically switch to the account with most remaining quota."""
    try:
        if not os.path.exists(ACCOUNTS_FILE): return
        with open(ACCOUNTS_FILE) as f: acc_data = json.load(f)
        
        # Determine current active email from sync file first
        active_email = None
        native_token_path = os.path.expanduser("~/.gemini/antigravity-cli/antigravity-oauth-token")
        if os.path.exists(native_token_path):
            try:
                with open(native_token_path) as f: data = json.load(f)
                token_info = data.get("token", {})
                rt = token_info.get("refresh_token")
                at = token_info.get("access_token")
                if rt:
                    for fname in os.listdir(TOKENS_DIR):
                        if fname.endswith('.json'):
                            with open(os.path.join(TOKENS_DIR, fname)) as tf:
                                if json.load(tf).get("refresh_token") == rt:
                                    active_email = fname.replace(".json", "")
                                    break
                if not active_email and at:
                    for fname in os.listdir(TOKENS_DIR):
                        if fname.endswith('.json'):
                            with open(os.path.join(TOKENS_DIR, fname)) as tf:
                                if json.load(tf).get("access_token") == at:
                                    active_email = fname.replace(".json", "")
                                    break
            except: pass
            
        if not active_email:
            active_email = acc_data.get("active")
            
        if active_email != exhausted_email: return
        
        candidates = []
        for email, data in cache.items():
            if email == exhausted_email: continue
            models = data.get("models", {})
            if isinstance(models, dict) and models:
                max_used = max([m.get("used", 0) for m in models.values()])
                candidates.append((email, max_used))
        
        if candidates:
            candidates.sort(key=lambda x: x[1])
            new_active = candidates[0][0]
            
            acc_data["active"] = new_active
            with open(ACCOUNTS_FILE, 'w') as f: json.dump(acc_data, f, indent=2)
            with open(ACTIVITY_FILE, 'w') as f: pass 
    except: pass

def capture():
    global LAST_MTAGS
    load_secrets()
    cache = {}
    if os.path.exists(QUOTA_CACHE):
        try:
            with open(QUOTA_CACHE) as f: cache = json.load(f)
        except: pass

    is_active = False
    if os.path.exists(ACTIVITY_FILE):
        mtime = os.path.getmtime(ACTIVITY_FILE)
        if time.time() - mtime < ACTIVE_WINDOW:
            is_active = True

    os.makedirs(TOKENS_DIR, exist_ok=True)
    cache_changed = False
    
    # 1. Verificação de Tokens e Cotas
    for fname in os.listdir(TOKENS_DIR):
        if not fname.endswith('.json'): continue
        fpath = os.path.join(TOKENS_DIR, fname)
        email = fname.replace('.json', '')
        
        mtime = os.path.getmtime(fpath)
        last_m = LAST_MTAGS.get(email, 0)
        
        try:
            with open(fpath) as f: creds = json.load(f)
            exp_ms = creds.get('expiry_date', 0)
            is_expiring = (exp_ms / 1000) - time.time() < REFRESH_BEFORE
            
            if mtime > last_m or is_expiring or is_active:
                if is_expiring:
                    updated = refresh_token(creds)
                    if updated:
                        with open(fpath, 'w') as f: json.dump(updated, f, indent=2)
                        creds = updated
                
                if is_active:
                    qinfo = cache.get(email, {})
                    if time.time() - qinfo.get("last_update", 0) > POLL_INTERVAL:
                        quotas = fetch_all_quotas(creds.get("access_token"))
                        if quotas:
                            cache[email] = {"models": quotas, "last_update": time.time()}
                            cache_changed = True
                            if quotas == "EXHAUSTED":
                                auto_switch_logic(email, cache)
                
                LAST_MTAGS[email] = os.path.getmtime(fpath)
        except: pass

    if cache_changed:
        with open(QUOTA_CACHE, 'w') as f: json.dump(cache, f, indent=2)

    # 2. Captura de Novo Login (OAuth Flow Externo / Antigravity OAuth Token)
    # Scan native antigravity-oauth-token
    native_token_path = os.path.expanduser("~/.gemini/antigravity-cli/antigravity-oauth-token")
    native_accounts_path = os.path.expanduser("~/.gemini/google_accounts.json")
    
    if os.path.exists(native_token_path):
        try:
            mtime_native = os.path.getmtime(native_token_path)
            if mtime_native > LAST_MTAGS.get("__native_token__", 0):
                with open(native_token_path) as f: data = json.load(f)
                token_info = data.get("token", {})
                access_token = token_info.get("access_token")
                refresh_token = token_info.get("refresh_token")
                expiry = token_info.get("expiry")
                
                email = None
                if token_info.get("id_token"):
                    email = decode_email(token_info.get("id_token"))
                
                if not email and access_token:
                    req = urllib.request.Request("https://www.googleapis.com/oauth2/v2/userinfo", 
                                                 headers={"Authorization": f"Bearer {access_token}"})
                    with urllib.request.urlopen(req, timeout=5) as res:
                        userinfo = json.load(res)
                        email = userinfo.get("email")
                
                if email:
                    import datetime
                    try:
                        dt = datetime.datetime.fromisoformat(expiry.replace('Z', '+00:00'))
                        expiry_date = int(dt.timestamp() * 1000)
                    except:
                        expiry_date = int((time.time() + 3600) * 1000)
                        
                    creds = {
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                        "expiry_date": expiry_date,
                        "id_token": token_info.get("id_token")
                    }
                    
                    dest = os.path.join(TOKENS_DIR, f"{email}.json")
                    with open(dest, 'w') as f: json.dump(creds, f, indent=2)
                    
                    # Update active account list
                    if os.path.exists(ACCOUNTS_FILE):
                        with open(ACCOUNTS_FILE, 'r') as f: acc_data = json.load(f)
                        acc_data["active"] = email
                        if "old" not in acc_data: acc_data["old"] = []
                        if email in acc_data["old"]: acc_data["old"].remove(email)
                        acc_data["old"].insert(0, email)
                        with open(ACCOUNTS_FILE, 'w') as f: json.dump(acc_data, f, indent=2)
                        
                LAST_MTAGS["__native_token__"] = os.path.getmtime(native_token_path)
        except: pass

    # Backwards compatibility legacy oauth_creds.json
    if os.path.exists(OAUTH_CREDS):
        try:
            mtime_oauth = os.path.getmtime(OAUTH_CREDS)
            if mtime_oauth > LAST_MTAGS.get("__oauth_creds__", 0):
                with open(OAUTH_CREDS) as f: creds = json.load(f)
                email = decode_email(creds.get('id_token', ''))
                if email:
                    dest = os.path.join(TOKENS_DIR, f"{email}.json")
                    if not os.path.exists(dest) or mtime_oauth > os.path.getmtime(dest):
                        shutil.copy2(OAUTH_CREDS, dest)
                        if os.path.exists(ACCOUNTS_FILE):
                            with open(ACCOUNTS_FILE, 'r') as f: acc_data = json.load(f)
                            acc_data["active"] = email
                            if "old" not in acc_data: acc_data["old"] = []
                            if email in acc_data["old"]: acc_data["old"].remove(email)
                            acc_data["old"].insert(0, email)
                            with open(ACCOUNTS_FILE, 'w') as f: json.dump(acc_data, f, indent=2)
                LAST_MTAGS["__oauth_creds__"] = mtime_oauth
        except: pass

    # 3. Synchronize active account (Ecosystem -> Gemini CLI)
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, 'r') as f: acc_data = json.load(f)
            ecosystem_active = acc_data.get("active")
            
            current_native_active = None
            if os.path.exists(native_accounts_path):
                try:
                    with open(native_accounts_path, 'r') as f:
                        current_native_active = json.load(f).get("active")
                except: pass
                
            if ecosystem_active and ecosystem_active != current_native_active:
                token_src = os.path.join(TOKENS_DIR, f"{ecosystem_active}.json")
                if os.path.exists(token_src):
                    with open(token_src, 'r') as f: creds = json.load(f)
                    
                    # Ensure token is valid/refreshed
                    exp_ms = creds.get('expiry_date', 0)
                    if (exp_ms / 1000) - time.time() < REFRESH_BEFORE:
                        updated = refresh_token(creds)
                        if updated:
                            with open(token_src, 'w') as f: json.dump(updated, f, indent=2)
                            creds = updated
                            
                    # Write to ~/.gemini/google_accounts.json
                    os.makedirs(os.path.dirname(native_accounts_path), exist_ok=True)
                    old_acc = []
                    if os.path.exists(native_accounts_path):
                        try:
                            with open(native_accounts_path, "r") as f:
                                old_acc = json.load(f).get("old", [])
                        except: pass
                    if ecosystem_active in old_acc: old_acc.remove(ecosystem_active)
                    with open(native_accounts_path, "w") as f:
                        json.dump({"active": ecosystem_active, "old": old_acc}, f, indent=2)
                        
                    # Write to ~/.gemini/oauth_creds.json (legacy)
                    oauth_creds_path = os.path.expanduser("~/.gemini/oauth_creds.json")
                    with open(oauth_creds_path, "w") as f:
                        json.dump(creds, f, indent=2)
                        
                    # Write to ~/.gemini/antigravity-cli/antigravity-oauth-token (modern separate token file)
                    os.makedirs(os.path.dirname(native_token_path), exist_ok=True)
                    import datetime
                    expiry_seconds = creds.get("expiry_date", 0) / 1000.0
                    expiry_iso = datetime.datetime.fromtimestamp(expiry_seconds, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                    token_data = {
                        "token": {
                            "access_token": creds.get("access_token"),
                            "token_type": creds.get("token_type", "Bearer"),
                            "refresh_token": creds.get("refresh_token"),
                            "expiry": expiry_iso
                        },
                        "auth_method": "consumer"
                    }
                    with open(native_token_path, "w") as f:
                        json.dump(token_data, f, indent=2)
                    
                    # Update settings activeProject
                    settings_path = os.path.expanduser("~/.gemini/antigravity-cli/settings.json")
                    if os.path.exists(settings_path):
                        try:
                            with open(settings_path, 'r') as f: s = json.load(f)
                            s["activeProject"] = ecosystem_active
                            s.setdefault("security", {}).setdefault("auth", {})["selectedType"] = "oauth-personal"
                            with open(settings_path, 'w') as f: json.dump(s, f, indent=2)
                        except: pass
                        
                    # Update LAST_MTAGS to avoid loop
                    LAST_MTAGS["__native_token__"] = os.path.getmtime(native_token_path)
        except Exception as e:
            pass

if __name__ == "__main__":
    check_single_instance()
    try:
        while True:
            capture()
            time.sleep(10)
    finally:
        if os.path.exists(PID_FILE): os.remove(PID_FILE)
