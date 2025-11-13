import os
import subprocess
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
        raise Exception('X_REPLIT_TOKEN not found')
    
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

def main():
    print("Getting GitHub access token...")
    token = get_access_token()
    
    username = "sabrinakellermann-source"
    repo_name = "wedding-card-generator"
    
    # Create the authenticated URL
    remote_url = f"https://{username}:{token}@github.com/{username}/{repo_name}.git"
    
    print(f"\nRun these commands in the Shell:\n")
    print(f"git remote remove github 2>/dev/null || true")
    print(f"git remote add github {remote_url}")
    print(f"git add .")
    print(f"git commit -m 'Initial commit: Wedding Card Generator' || true")
    print(f"git push -u github main")
    print(f"\n✅ Copy and paste each command above into the Shell")

if __name__ == "__main__":
    main()
