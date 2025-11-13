import os
import subprocess
import json
import requests

def get_access_token():
    """Get GitHub access token from Replit connection."""
    hostname = os.environ.get('REPLIT_CONNECTORS_HOSTNAME')
    x_replit_token = None
    
    repl_identity = os.environ.get('REPL_IDENTITY')
    web_repl_renewal = os.environ.get('WEB_REPL_RENEWAL')
    
    if repl_identity:
        x_replit_token = 'repl ' + repl_identity
    elif web_repl_renewal:
        x_replit_token = 'depl ' + web_repl_renewal
    
    if not x_replit_token:
        raise Exception('X_REPLIT_TOKEN not found for repl/depl')
    
    response = requests.get(
        f'https://{hostname}/api/v2/connection?include_secrets=true&connector_names=github',
        headers={
            'Accept': 'application/json',
            'X_REPLIT_TOKEN': x_replit_token
        }
    )
    
    data = response.json()
    connection_settings = data.get('items', [])[0] if data.get('items') else None
    
    if not connection_settings:
        raise Exception('GitHub not connected')
    
    access_token = (connection_settings.get('settings', {}).get('access_token') or 
                   connection_settings.get('settings', {}).get('oauth', {}).get('credentials', {}).get('access_token'))
    
    if not access_token:
        raise Exception('Access token not found')
    
    return access_token

def get_github_user(token):
    """Get GitHub user information."""
    response = requests.get(
        'https://api.github.com/user',
        headers={
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
    )
    return response.json()

def create_github_repo(token, repo_name, description=""):
    """Create a new GitHub repository."""
    response = requests.post(
        'https://api.github.com/user/repos',
        headers={
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        },
        json={
            'name': repo_name,
            'description': description,
            'private': False,
            'auto_init': False
        }
    )
    
    if response.status_code == 201:
        return response.json()
    elif response.status_code == 422:
        # Repository already exists
        user = get_github_user(token)
        username = user.get('login')
        # Get the existing repo
        get_response = requests.get(
            f'https://api.github.com/repos/{username}/{repo_name}',
            headers={
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3+json'
            }
        )
        if get_response.status_code == 200:
            return get_response.json()
    
    raise Exception(f'Failed to create/get repository: {response.status_code} - {response.text}')

def push_to_github(repo_name, description="Wedding Card Generator - AI-powered wedding invitation generator"):
    """Push code to GitHub repository."""
    try:
        # Get access token
        print("Getting GitHub access token...")
        token = get_access_token()
        
        # Get user info
        print("Getting GitHub user info...")
        user = get_github_user(token)
        username = user.get('login')
        print(f"Authenticated as: {username}")
        
        # Create or get repository
        print(f"Creating/getting repository '{repo_name}'...")
        repo = create_github_repo(token, repo_name, description)
        repo_url = repo.get('html_url')
        clone_url = repo.get('clone_url')
        
        print(f"Repository URL: {repo_url}")
        
        # Configure git
        print("Configuring git...")
        subprocess.run(['git', 'config', 'user.name', username], check=True)
        subprocess.run(['git', 'config', 'user.email', f"{username}@users.noreply.github.com"], check=True)
        
        # Add GitHub remote with token
        remote_url = f"https://{username}:{token}@github.com/{username}/{repo_name}.git"
        
        # Remove existing github remote if it exists
        subprocess.run(['git', 'remote', 'remove', 'github'], capture_output=True)
        
        # Add new remote
        print("Adding GitHub remote...")
        subprocess.run(['git', 'remote', 'add', 'github', remote_url], check=True)
        
        # Add all files
        print("Adding files to git...")
        subprocess.run(['git', 'add', '.'], check=True)
        
        # Commit changes
        print("Committing changes...")
        result = subprocess.run(['git', 'commit', '-m', 'Initial commit: Wedding Card Generator'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            if 'nothing to commit' in result.stdout or 'nothing to commit' in result.stderr:
                print("No new changes to commit")
            else:
                print(f"Commit output: {result.stdout}")
                print(f"Commit error: {result.stderr}")
        
        # Push to GitHub
        print("Pushing to GitHub...")
        subprocess.run(['git', 'push', '-u', 'github', 'main'], check=True)
        
        print(f"\n✅ Successfully pushed to GitHub!")
        print(f"Repository URL: {repo_url}")
        
        return repo_url
        
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {e}")
        print(f"Output: {e.output if hasattr(e, 'output') else 'No output'}")
        raise
    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    import sys
    
    repo_name = sys.argv[1] if len(sys.argv) > 1 else "wedding-card-generator"
    description = sys.argv[2] if len(sys.argv) > 2 else "Wedding Card Generator - AI-powered wedding invitation generator"
    
    repo_url = push_to_github(repo_name, description)
    print(f"\n🎉 Done! Your code is now on GitHub: {repo_url}")
