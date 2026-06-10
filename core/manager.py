import os
import json
import shutil
import base64
import time
import socket
import urllib.request
import urllib.parse
import http.server
import threading

# Common Paths
HOME = os.path.expanduser("~")
GEMINI_DIR = os.path.join(HOME, ".gemini")
CLAUDE_JSON = os.path.join(HOME, ".claude.json")
ECOSYSTEM_DIR = os.path.join(HOME, ".ecosystem")
BACKUP_DIR = os.path.join(ECOSYSTEM_DIR, "backups")
TOKENS_DIR = os.path.join(ECOSYSTEM_DIR, "id-tokens")
SHARED_CONFIG = os.path.join(ECOSYSTEM_DIR, "config.json")
ACCOUNTS_FILE = os.path.join(ECOSYSTEM_DIR, "google_accounts.json")
KEYS_FILE = os.path.join(ECOSYSTEM_DIR, "api_keys.json")
NICKNAMES_FILE = os.path.join(ECOSYSTEM_DIR, "nicknames.json")

# OAuth Constants
SECRETS_FILE = os.path.join(ECOSYSTEM_DIR, "secrets", "google_api.json")
CLIENT_ID = os.environ.get("GEMINI_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GEMINI_CLIENT_SECRET")

if os.path.exists(SECRETS_FILE):
    try:
        with open(SECRETS_FILE) as f:
            sec_data = json.load(f)
            CLIENT_ID = CLIENT_ID or sec_data.get("client_id")
            CLIENT_SECRET = CLIENT_SECRET or sec_data.get("client_secret")
    except:
        pass

SCOPES = "https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/cloud-platform openid"

class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        if "code" in params:
            self.server.auth_code = params["code"][0]
            self.wfile.write("<h1>Success!</h1><p>Return to your terminal.</p>".encode("utf-8"))
        else:
            self.wfile.write("<h1>Error.</h1>".encode("utf-8"))

class GeminiManager:
    def __init__(self):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        os.makedirs(TOKENS_DIR, exist_ok=True)
        os.makedirs(ECOSYSTEM_DIR, exist_ok=True)
        self._migrate_old_data()
        self._init_defaults()
        self._capture_current_system_token()

    def _capture_current_system_token(self):
        oauth_path = os.path.join(GEMINI_DIR, "oauth_creds.json")
        if os.path.exists(oauth_path):
            try:
                with open(oauth_path, "r") as f:
                    creds = json.load(f)
                id_token = creds.get("id_token")
                if id_token:
                    payload = id_token.split('.')[1]
                    padded = payload + '=' * (-len(payload) % 4)
                    email = json.loads(base64.b64decode(padded)).get('email')
                    if email:
                        dest = os.path.join(TOKENS_DIR, f"{email}.json")
                        if not os.path.exists(dest):
                            self.save_json(dest, creds)
                            acc = self.load_json(ACCOUNTS_FILE)
                            if "old" not in acc: acc["old"] = []
                            if email not in acc["old"]:
                                acc["old"].append(email)
                            if not acc.get("active"):
                                acc["active"] = email
                            self.save_json(ACCOUNTS_FILE, acc)
            except:
                pass

    def get_active_email_from_sync_file(self):
        token_path = os.path.join(GEMINI_DIR, "antigravity-cli", "antigravity-oauth-token")
        if not os.path.exists(token_path):
            return None
        try:
            with open(token_path, "r") as f:
                data = json.load(f)
            token_info = data.get("token", {})
            rt = token_info.get("refresh_token")
            at = token_info.get("access_token")
            
            # Try to match refresh_token in our local id-tokens
            if rt:
                for fname in os.listdir(TOKENS_DIR):
                    if not fname.endswith('.json'): continue
                    fpath = os.path.join(TOKENS_DIR, fname)
                    try:
                        with open(fpath, "r") as tf:
                            creds = json.load(tf)
                        if creds.get("refresh_token") == rt:
                            return fname.replace(".json", "")
                    except:
                        pass
            
            # If not found via refresh_token, try matching access_token
            if at:
                for fname in os.listdir(TOKENS_DIR):
                    if not fname.endswith('.json'): continue
                    fpath = os.path.join(TOKENS_DIR, fname)
                    try:
                        with open(fpath, "r") as tf:
                            creds = json.load(tf)
                        if creds.get("access_token") == at:
                            return fname.replace(".json", "")
                    except:
                        pass
            
            # If still not found, request from userinfo using access_token
            if at:
                email = self.get_email_from_token(at)
                if email:
                    # Cache it locally in TOKENS_DIR
                    dest = os.path.join(TOKENS_DIR, f"{email}.json")
                    expiry_date = 0
                    expiry = token_info.get("expiry")
                    if expiry:
                        import datetime
                        try:
                            dt = datetime.datetime.fromisoformat(expiry.replace('Z', '+00:00'))
                            expiry_date = int(dt.timestamp() * 1000)
                        except:
                            expiry_date = int((time.time() + 3600) * 1000)
                    creds = {
                        "access_token": at,
                        "refresh_token": rt,
                        "expiry_date": expiry_date
                    }
                    self.save_json(dest, creds)
                    return email
        except Exception as e:
            pass
        return None

    def _migrate_old_data(self):
        """Migrates data from ~/.gemini-auth to ~/.ecosystem."""
        old_dir = os.path.expanduser("~/.gemini-auth")
        if not os.path.exists(old_dir): return
        
        mapping = {
            "google_accounts.json": ACCOUNTS_FILE,
            "api_keys.json": KEYS_FILE,
            "nicknames.json": NICKNAMES_FILE,
            "id-tokens": TOKENS_DIR
        }
        
        for old_name, new_path in mapping.items():
            old_path = os.path.join(old_dir, old_name)
            if not os.path.exists(old_path): continue
            
            if os.path.isdir(old_path):
                # Migrate directory (tokens)
                for item in os.listdir(old_path):
                    src = os.path.join(old_path, item)
                    dst = os.path.join(new_path, item)
                    if not os.path.exists(dst):
                        try: shutil.copy2(src, dst)
                        except: pass
            else:
                # Migrate file (json)
                if not os.path.exists(new_path) or self.load_json(new_path) == {} or self.load_json(new_path) == {"active": None, "old": []}:
                    try: shutil.copy2(old_path, new_path)
                    except: pass

    def _init_defaults(self):
        if not os.path.exists(SHARED_CONFIG):
            self.save_json(SHARED_CONFIG, {"target_model": "gemini-3.1-flash", "language": "auto", "theme": "pastel-hacker"})
        if not os.path.exists(ACCOUNTS_FILE):
            self.save_json(ACCOUNTS_FILE, {"active": None, "old": []})
        if not os.path.exists(KEYS_FILE):
            self.save_json(KEYS_FILE, {})
        if not os.path.exists(NICKNAMES_FILE):
            self.save_json(NICKNAMES_FILE, {})

    def load_json(self, path):
        try:
            with open(path, 'r') as f: return json.load(f)
        except: return {}

    def save_json(self, path, data):
        with open(path, 'w') as f: json.dump(data, f, indent=2)

    def backup_config(self, path):
        if not os.path.exists(path): return False
        fname = os.path.basename(path)
        dest = os.path.join(BACKUP_DIR, f"{fname}.bak")
        try: shutil.copy2(path, dest); return True
        except: return False

    def restore_config(self, path):
        fname = os.path.basename(path)
        src = os.path.join(BACKUP_DIR, f"{fname}.bak")
        if not os.path.exists(src): return False
        try: shutil.copy2(src, path); return True
        except: return False

    def sync_to_gemini_cli(self, email, creds):
        os.makedirs(GEMINI_DIR, exist_ok=True)
        if creds.get("expiry_date", 0) < (time.time() * 1000 + 120000):
            refreshed = self.refresh_token(creds, email)
            if refreshed:
                creds = refreshed
        try:
            with open(os.path.join(GEMINI_DIR, "oauth_creds.json"), "w") as f:
                json.dump(creds, f, indent=2)
            acc_path = os.path.join(GEMINI_DIR, "google_accounts.json")
            old_acc = []
            if os.path.exists(acc_path):
                try:
                    with open(acc_path, "r") as f: old_acc = json.load(f).get("old", [])
                except: pass
            if email in old_acc: old_acc.remove(email)
            with open(acc_path, "w") as f:
                json.dump({"active": email, "old": old_acc}, f, indent=2)
            
            # Sync Settings
            settings_path = os.path.join(GEMINI_DIR, "antigravity-cli", "settings.json")
            if os.path.exists(settings_path):
                try:
                    with open(settings_path, 'r') as f: s = json.load(f)
                    s["activeProject"] = email
                    s.setdefault("security", {}).setdefault("auth", {})["selectedType"] = "oauth-personal"
                    with open(settings_path, 'w') as f: json.dump(s, f, indent=2)
                except: pass

            # Sync antigravity-oauth-token
            token_path = os.path.join(GEMINI_DIR, "antigravity-cli", "antigravity-oauth-token")
            try:
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
                with open(token_path, "w") as f:
                    json.dump(token_data, f, indent=2)
            except: pass

            return True
        except: return False

    def get_email_from_token(self, access_token):
        try:
            data = self._request("https://www.googleapis.com/oauth2/v2/userinfo", 
                                 headers={"Authorization": f"Bearer {access_token}"})
            return data.get("email")
        except:
            return None

    def run_oauth_flow(self):
        # 1. Back up current token
        token_path = os.path.join(GEMINI_DIR, "antigravity-cli", "antigravity-oauth-token")
        backup_path = token_path + ".tmp_backup"
        if os.path.exists(token_path):
            try: shutil.copy2(token_path, backup_path)
            except: pass
            try: os.remove(token_path)
            except: pass
            
        # 2. Run agy command to trigger native login flow
        print("[*] Launching native Gemini CLI login flow...")
        print("[*] Complete the login in the browser window.")
        try:
            import subprocess
            # We run agy using the global command path
            subprocess.run([os.path.expanduser("~/bin/agy"), "-p", "ping"])
        except Exception as e:
            print(f"[!] Error running login: {e}")
            
        # 3. Read the captured token from the native path
        email = None
        if os.path.exists(token_path):
            try:
                with open(token_path, "r") as f:
                    data = json.load(f)
                token_info = data.get("token", {})
                access_token = token_info.get("access_token")
                refresh_token = token_info.get("refresh_token")
                expiry = token_info.get("expiry")
                
                import datetime
                try:
                    dt = datetime.datetime.fromisoformat(expiry.replace('Z', '+00:00'))
                    expiry_date = int(dt.timestamp() * 1000)
                except:
                    expiry_date = int((time.time() + 3600) * 1000)
                
                email = self.get_email_from_token(access_token)
                if not email and token_info.get("id_token"):
                    id_token = token_info.get("id_token")
                    payload = id_token.split('.')[1]
                    padded = payload + '=' * (-len(payload) % 4)
                    email = json.loads(base64.b64decode(padded)).get('email')
                
                if not email:
                    email = "new_account@gmail.com"
                    
                creds = {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "expiry_date": expiry_date,
                    "id_token": token_info.get("id_token")
                }
                
                # Save to ecosystem
                dest = os.path.join(TOKENS_DIR, f"{email}.json")
                self.save_json(dest, creds)
                
                # Update local accounts
                acc = self.load_json(ACCOUNTS_FILE)
                acc["active"] = email
                if "old" not in acc: acc["old"] = []
                if email not in acc["old"]:
                    acc["old"].append(email)
                self.save_json(ACCOUNTS_FILE, acc)
                
                # Sync globally
                self.sync_to_gemini_cli(email, creds)
                
                print(f"[✓] Successfully captured login for {email}")
            except Exception as e:
                print(f"[!] Error processing captured token: {e}")
                
        # 4. Restore original token backup if native login was cancelled or failed
        if not email and os.path.exists(backup_path):
            try: shutil.copy2(backup_path, token_path)
            except: pass
            
        if os.path.exists(backup_path):
            try: os.remove(backup_path)
            except: pass
            
        return email

    def get_shared_config(self):
        return self.load_json(SHARED_CONFIG)

    def set_shared_config(self, key, value):
        data = self.load_json(SHARED_CONFIG)
        data[key] = value
        self.save_json(SHARED_CONFIG, data)

    def refresh_token(self, creds, email=None):
        rt = creds.get("refresh_token")
        if not rt: return None
        
        client_id = CLIENT_ID
        
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": rt,
            "client_id": client_id
        }
        if CLIENT_SECRET:
            payload["client_secret"] = CLIENT_SECRET
            
        token_url = "https://oauth2.googleapis.com/token"
        encoded_data = urllib.parse.urlencode(payload).encode('utf-8')
        req = urllib.request.Request(token_url, data=encoded_data, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                new_data = json.loads(response.read().decode('utf-8'))
                creds["access_token"] = new_data["access_token"]
                creds["expiry_date"] = int(time.time() * 1000) + (new_data.get("expires_in", 3600) * 1000)
                if "id_token" in new_data:
                    creds["id_token"] = new_data["id_token"]
                
                if email:
                    dest = os.path.join(TOKENS_DIR, f"{email}.json")
                    self.save_json(dest, creds)
                return creds
        except Exception as e:
            return None

    def get_valid_token(self, email=None):
        acc = self.load_json(ACCOUNTS_FILE)
        active_email = self.get_active_email_from_sync_file() or acc.get("active")
        target_email = email or active_email
        if not target_email:
            return None
            
        token_path = os.path.join(TOKENS_DIR, f"{target_email}.json")
        if not os.path.exists(token_path):
            return None
            
        creds = self.load_json(token_path)
        # Refresh if token expires in less than 5 minutes
        if creds.get("expiry_date", 0) < (time.time() * 1000 + 300000):
            refreshed = self.refresh_token(creds, target_email)
            if refreshed:
                creds = refreshed
            
        return creds.get("access_token") if creds else None

    def _request(self, url, method="GET", headers=None, body=None):
        data = json.dumps(body).encode('utf-8') if body else None
        req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            return {"error": str(e)}

    def get_project_id(self, token, email):
        cache_path = os.path.join(ECOSYSTEM_DIR, "project_cache.json")
        cache = self.load_json(cache_path)
        if email in cache:
            return cache[email]
            
        url = "https://cloudcode-pa.googleapis.com/v1internal:loadCodeAssist"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        body = {
            "metadata": {
                "ideType": "IDE_UNSPECIFIED",
                "platform": "PLATFORM_UNSPECIFIED",
                "pluginType": "GEMINI"
            }
        }
        
        data = self._request(url, method="POST", headers=headers, body=body)
        project_id = data.get("cloudaicompanionProject")
        
        if not project_id:
            list_url = "https://cloudresourcemanager.googleapis.com/v1/projects"
            headers_v1 = {"Authorization": f"Bearer {token}"}
            list_data = self._request(list_url, headers=headers_v1)
            if isinstance(list_data, dict) and "projects" in list_data and list_data["projects"]:
                project_id = list_data["projects"][0]["projectId"]
                
        if project_id:
            cache[email] = project_id
            self.save_json(cache_path, cache)
            return project_id
            
        return None

    def _ensure_handshake(self, token, project_id):
        url = "https://cloudcode-pa.googleapis.com/v1internal:loadCodeAssist"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "x-goog-user-project": project_id
        }
        body = {
            "cloudaicompanionProject": project_id,
            "metadata": {
                "ideType": "IDE_UNSPECIFIED",
                "platform": "PLATFORM_UNSPECIFIED",
                "pluginType": "GEMINI",
                "duetProject": project_id
            }
        }
        return self._request(url, method="POST", headers=headers, body=body)

    def get_quota_info(self, email=None):
        token = self.get_valid_token(email)
        if not token:
            return {"error": "Authentication token not found."}
            
        acc = self.load_json(ACCOUNTS_FILE)
        active_email = self.get_active_email_from_sync_file() or acc.get("active")
        target_email = email or active_email
        
        project_id = self.get_project_id(token, target_email)
        if not project_id:
            return {"error": "No Google Cloud project found."}
            
        self._ensure_handshake(token, project_id)
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        if not project_id.startswith("organic-lead"):
            headers["x-goog-user-project"] = project_id
            
        url = "https://cloudcode-pa.googleapis.com/v1internal:retrieveUserQuota"
        return self._request(url, method="POST", headers=headers, body={"project": project_id})

    def get_usage_metrics(self, email=None):
        data = self.get_quota_info(email)
        if "error" in data:
            return (0.0, f"Error: {data['error']}")
            
        buckets = data.get("buckets", [])
        if not buckets:
            return (0.0, "Empty Quota")
            
        summary_list = []
        for b in buckets:
            model = b.get("modelId", "Unknown")
            rem_frac = b.get("remainingFraction")
            if rem_frac is None:
                limit = b.get("quotaLimit", 0)
                rem = b.get("remainingAmount", 0)
                rem_frac = rem / limit if limit > 0 else 0.0
            summary_list.append((rem_frac, model))
            
        summary_list.sort()
        worst_frac, worst_model = summary_list[0]
        percentage = worst_frac * 100
        return (percentage, f"{worst_model[:8]}: {percentage:.1f}%")

    def get_all_quotas(self):
        """Fetches fresh quotas for all accounts and saves to quota_cache.json."""
        cache_path = os.path.join(ECOSYSTEM_DIR, "quota_cache.json")
        cache = self.load_json(cache_path)
        
        active_email = self.get_active_email_from_sync_file()
        acc = self.load_json(ACCOUNTS_FILE)
        all_emails = set(([active_email] if active_email else []) + ([acc.get('active')] if acc.get('active') else []) + acc.get('old', []))
        
        updated = False
        for email in all_emails:
            cached_data = cache.get(email, {})
            last_update = cached_data.get("last_update", 0)
            if time.time() - last_update < 60:
                continue
                
            q_info = self.get_quota_info(email)
            if "error" not in q_info:
                models_quota = {}
                for b in q_info.get("buckets", []):
                    mid = b.get("modelId")
                    if mid:
                        rf = b.get("remainingFraction")
                        used_val = round((1.0 - float(rf)) * 100.0, 1) if rf is not None else 0.0
                        models_quota[mid] = {"used": used_val, "reset": b.get("resetTime")}
                cache[email] = {
                    "models": models_quota,
                    "last_update": time.time()
                }
                updated = True
            else:
                cache[email] = {
                    "models": {},
                    "last_update": time.time(),
                    "error": q_info["error"]
                }
                updated = True
                
        if updated:
            self.save_json(cache_path, cache)
            
        return cache

    def smart_switch_identity(self):
        """Extreme Mode: Automatically switches to the identity with the most remaining quota."""
        quotas = self.get_all_quotas()
        best_email = None
        min_used = 101.0
        
        target_model = self.get_active_model()
        
        active_email = self.get_active_email_from_sync_file()
        acc = self.load_json(ACCOUNTS_FILE)
        all_emails = set(([active_email] if active_email else []) + ([acc.get('active')] if acc.get('active') else []) + acc.get('old', []))
        
        for email in all_emails:
            q_data = quotas.get(email, {}).get("models", {})
            # Find matching model key
            m_key = next((k for k in q_data if target_model.lower() in k.lower()), None)
            used = q_data.get(m_key, {}).get("used", 100.0) if m_key else 100.0
            
            if used < min_used:
                min_used = used
                best_email = email
        
        if best_email and min_used < 100.0:
            token_path = os.path.join(TOKENS_DIR, f"{best_email}.json")
            if os.path.exists(token_path):
                creds = self.load_json(token_path)
                self.sync_to_gemini_cli(best_email, creds)
                try:
                    acc["active"] = best_email
                    self.save_json(ACCOUNTS_FILE, acc)
                except:
                    pass
                return best_email, min_used
        return None, None

    def _encrypt_token(self, data):
        """Phase 3: Basic obfuscation for tokens."""
        # Future: Use cryptography library
        return base64.b64encode(data.encode()).decode()

    def _decrypt_token(self, data):
        """Phase 3: Basic de-obfuscation."""
        return base64.b64decode(data.encode()).decode()

    def get_active_model(self):
        return self.get_shared_config().get("target_model", "gemini-3.1-flash")

    def set_active_model(self, model_name):
        self.set_shared_config("target_model", model_name)
        # Also sync to native if exists
        settings_path = os.path.join(GEMINI_DIR, "antigravity-cli", "settings.json")
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r') as f: data = json.load(f)
                data["model"] = model_name
                with open(settings_path, 'w') as f: json.dump(data, f, indent=2)
            except: pass
