import subprocess
import os

def run_cmd(cmd, shell=True):
    return subprocess.run(cmd, shell=shell, capture_output=True, text=True)

def sync_project(path, repo_name):
    print(f"[*] Syncing {repo_name}...")
    os.chdir(path)
    
    # Get token
    res = run_cmd("gh auth token")
    token = res.stdout.strip()
    if not token:
        print(f"[!] Error: Could not get GH token for {repo_name}")
        return False

    # Init git if needed
    if not os.path.exists(".git"):
        run_cmd("git init && git branch -M main")

    # Set remote with token
    remote_url = f"https://opassoca:{token}@github.com/opassoca/{repo_name}.git"
    run_cmd(f"git remote remove origin")
    run_cmd(f"git remote add origin {remote_url}")

    # Commit
    run_cmd("git add .")
    run_cmd('git commit -m "feat: Extreme Orchestration v2.0-stable"')

    # Push
    res = run_cmd("git push -u origin main --force")
    if res.returncode == 0:
        print(f"[✓] {repo_name} synced successfully.")
        return True
    else:
        print(f"[!] Push failed for {repo_name}: {res.stderr}")
        return False

if __name__ == "__main__":
    home = os.path.expanduser("~")
    projects = {
        os.path.join(home, "projects/ecosystem"): "ecosystem",
        os.path.join(home, "projects/gmn-switcher"): "gmn-switcher",
        os.path.join(home, "projects/agy-3-proxy"): "agy-3-proxy"
    }
    
    for path, name in projects.items():
        if os.path.exists(path):
            sync_project(path, name)
        else:
            print(f"[!] Path not found: {path}")
