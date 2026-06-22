"""Deploy to GitHub: create repo and push all files."""
import os, sys, base64, json

try:
    import httpx
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.venv', 'Lib', 'site-packages'))
    import httpx

TOKEN = os.environ.get('GH_TOKEN', '')
if not TOKEN:
    TOKEN = input('GitHub Token: ').strip()
if not TOKEN:
    print('Error: No token provided')
    sys.exit(1)

HEADERS = {
    'Authorization': f'token {TOKEN}',
    'Accept': 'application/vnd.github.v3+json',
}
API = 'https://api.github.com'
REPO_NAME = 'loto6-analyzer'

# Step 1: Get authenticated user
r = httpx.get(f'{API}/user', headers=HEADERS, timeout=15)
r.raise_for_status()
username = r.json()['login']
print(f'Authenticated as: {username}')

# Step 2: Create repo (ignore if exists)
r = httpx.post(f'{API}/user/repos', headers=HEADERS, json={
    'name': REPO_NAME,
    'description': 'LOTO6 出現傾向シミュレータ - 統計分析Webアプリ',
    'private': False,
    'auto_init': False,
}, timeout=15)
if r.status_code == 201:
    print(f'Repository created: https://github.com/{username}/{REPO_NAME}')
elif r.status_code == 422:
    print(f'Repository already exists: https://github.com/{username}/{REPO_NAME}')
else:
    print(f'Create repo response: {r.status_code} {r.text}')

# Step 3: Upload files via Contents API
PROJECT_DIR = os.path.dirname(__file__)
SKIP = {'.venv', '__pycache__', '.gh_token', '_auth.ps1', '_verify.py',
        'loto6.db', 'server_out.log', 'server_err.log', 'server.log',
        '_diag.py', '_probe.py', '_apicheck.py', '_smoke.py'}

files_to_upload = []
for root, dirs, files in os.walk(PROJECT_DIR):
    dirs[:] = [d for d in dirs if d not in SKIP]
    for fname in files:
        if fname in SKIP or fname.endswith('.db') or fname.endswith('.pyc'):
            continue
        fpath = os.path.join(root, fname)
        relpath = os.path.relpath(fpath, PROJECT_DIR).replace('\\', '/')
        files_to_upload.append((relpath, fpath))

print(f'\nUploading {len(files_to_upload)} files...')
for relpath, fpath in sorted(files_to_upload):
    with open(fpath, 'rb') as f:
        content = base64.b64encode(f.read()).decode()

    # Check if file exists (to get sha for update)
    r = httpx.get(f'{API}/repos/{username}/{REPO_NAME}/contents/{relpath}',
                  headers=HEADERS, timeout=15)
    payload = {
        'message': f'add {relpath}',
        'content': content,
    }
    if r.status_code == 200:
        payload['sha'] = r.json()['sha']
        payload['message'] = f'update {relpath}'

    r = httpx.put(f'{API}/repos/{username}/{REPO_NAME}/contents/{relpath}',
                  headers=HEADERS, json=payload, timeout=30)
    if r.status_code in (200, 201):
        print(f'  ✓ {relpath}')
    else:
        print(f'  ✗ {relpath} ({r.status_code}: {r.text[:100]})')

print(f'\nDone! https://github.com/{username}/{REPO_NAME}')
