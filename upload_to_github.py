import os
import subprocess

def run_cmd(cmd, check=True):
    """Run a shell command and print it if fails"""
    try:
        subprocess.run(cmd, check=check)
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {' '.join(cmd)}")
        raise e

def setup_github_credentials(username, token):
    """Save GitHub credentials"""
    run_cmd(["git", "config", "--global", "user.name", username])
    run_cmd(["git", "config", "--global", "user.email", f"{username}@users.noreply.github.com"])
    run_cmd(["git", "config", "--global", "credential.helper", "store"])

    credentials = f"https://{username}:{token}@github.com\n"
    cred_file = os.path.expanduser("~/.git-credentials")
    with open(cred_file, "w") as f:
        f.write(credentials)
    print("✅ GitHub token saved successfully!")

def upload_project(repo_url, branch="main"):
    """Upload project to GitHub (supports new and existing repos)"""
    # init repo if not initialized
    if not os.path.exists(".git"):
        run_cmd(["git", "init"])
    
    run_cmd(["git", "add", "."])
    
    try:
        run_cmd(["git", "commit", "-m", "Update project"], check=False)
    except Exception:
        print("⚠️ No changes to commit.")
    
    run_cmd(["git", "branch", "-M", branch])
    
    # Check if remote exists
    try:
        run_cmd(["git", "remote", "get-url", "origin"])
        print("🔄 Remote already exists, running git pull...")
        try:
            run_cmd(["git", "pull", "origin", branch, "--rebase"], check=False)
        except Exception:
            print("⚠️ Could not pull, maybe repo is empty.")
    except subprocess.CalledProcessError:
        run_cmd(["git", "remote", "add", "origin", repo_url])
    
    run_cmd(["git", "push", "-u", "origin", branch])
    print("🚀 Project uploaded successfully!")

if __name__ == "__main__":
    username = input("Enter your GitHub username: ").strip()
    token = input("Enter your GitHub Personal Access Token: ").strip()
    repo_url = input("Enter your GitHub repository URL (e.g., https://github.com/USERNAME/REPO.git): ").strip()

    setup_github_credentials(username, token)
    upload_project(repo_url)
