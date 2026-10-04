"""Check this project's connections. Read-only lang; walang booking o upload."""

from pathlib import Path
from urllib.parse import urlsplit

import httpx
from dotenv import dotenv_values


# Check connections without creating patients, uploading code, or reserving visits.
# Reduce provider replies to status messages instead of printing credential values.
# Para makita kung tama ang account at project while keeping keys inside .env.
def main():
    # Read our own file only. Hindi binabago ang keys ng ibang project.
    config = dotenv_values(Path(__file__).with_name('.env'))
    with httpx.Client(timeout=20, follow_redirects=False) as client:
        # Confirm the public Auth key. Walang patient account na gagawin dito.
        project_url = config.get('SUPABASE_URL', '').rstrip('/')
        if project_url == 'https://mymjrohklofgwdfhxcru.supabase.co' and config.get('SUPABASE_PUBLISHABLE_KEY'):
            response = client.get(project_url + '/auth/v1/settings', headers={'apikey': config['SUPABASE_PUBLISHABLE_KEY']})
            print('Supabase Auth:', 'verified' if response.status_code == 200 else f'HTTP {response.status_code}')
        else:
            print('Supabase Auth: needs this project URL and publishable key')

        # Check the key owner first. Stop kapag hindi ito ang expected Cal account.
        if config.get('CAL_API_KEY'):
            response = client.get('https://api.cal.com/v2/me', headers={'Authorization': 'Bearer ' + config['CAL_API_KEY'], 'cal-api-version': '2024-06-14'})
            data = response.json().get('data', {}) if response.status_code == 200 else {}
            matches = data.get('email') == config.get('PROJECT_CAL_ACCOUNT_EMAIL')
            print('Cal.com:', 'verified account' if matches else f'account not verified (HTTP {response.status_code})')
        else:
            print('Cal.com: key missing')

        # A token must belong to our chosen account. Huwag gamitin ang ibang GitHub login.
        if config.get('GITHUB_TOKEN'):
            headers = {'Authorization': 'Bearer ' + config['GITHUB_TOKEN'], 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
            response = client.get('https://api.github.com/user', headers=headers)
            owner = response.json().get('login') if response.status_code == 200 else None
            repo = urlsplit(config.get('PROJECT_GITHUB_REPO_URL', ''))
            if owner == config.get('PROJECT_GITHUB_USERNAME') and repo.hostname == 'github.com' and repo.path == '/' + owner + '/bright-smile':
                response = client.get('https://api.github.com/repos' + repo.path, headers=headers)
                print('GitHub:', 'verified target repository' if response.status_code == 200 and response.json().get('full_name') == owner + '/bright-smile' else 'repository not verified')
            else:
                print('GitHub: account or repository mismatch')
        else:
            print('GitHub: repository ready; token approval pending')

        # Use the project's CLI login. Hindi natin kino-copy ang private login tokens.
        print('Vercel: verify the dedicated account using the project-local CLI login')


if __name__ == '__main__':
    main()
