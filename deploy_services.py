"""Apply private settings to the chosen Vercel project. Dito lang ang deployment setup."""

import json
import os
import subprocess
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent
PROJECT = 'prj_LlfCX6fNWVfC1P1wTRzM3Q9EUe5E'
TEAM = 'team_9y5dAdr3262ZFDEIkDdI5Aq4'
DOMAIN = 'bsmile.vercel.app'


def cli_environment():
    # Use the local CLI login, even if another terminal exported a token.
    # Hindi puwedeng palitan ng ibang project's variables ang chosen account.
    environment = {key: value for key, value in os.environ.items()
                   if key not in {'VERCEL_TOKEN', 'VERCEL_ORG_ID', 'VERCEL_PROJECT_ID'}}
    environment['VERCEL_TELEMETRY_DISABLED'] = '1'
    return environment


def api(path, payload=None):
    # Use the official CLI's local login. Hindi binabasa ang ibang account's global login.
    command = ['npx.cmd', '--yes', 'vercel@62.2.0', 'api', path, '--scope', 'joshua-400f', '--global-config', str(ROOT / '.vercel' / 'cli'), '--raw']
    if payload is not None:
        command += ['--method', 'POST', '--input', '-']
    result = subprocess.run(command, input=json.dumps(payload) if payload is not None else None, capture_output=True, text=True, encoding='utf-8', cwd=ROOT, env=cli_environment())
    if result.returncode:
        # Redact known values before showing a CLI error. Walang key na dapat makita dito.
        error = result.stderr
        for value in dotenv_values(ROOT / '.env').values():
            if value and len(value) > 7:
                error = error.replace(value, '[private value]')
        safe_lines = [line for line in error.splitlines() if 'error' in line.lower()]
        raise RuntimeError('Vercel request failed: ' + ' '.join(safe_lines)[:400])
    return json.loads(result.stdout)


# Copy only required runtime settings to this website's Vercel project.
# Check the account, domain, and project link before uploading any value.
# GitHub tokens, database passwords, and local login reference passwords stay dito sa computer.
def main():
    config = dotenv_values(ROOT / '.env')
    user = api('/v2/user')['user']
    if user.get('email') != 'joshricaballes2007@gmail.com':
        raise RuntimeError('Wrong Vercel account; stopped before changing settings.')
    project = api(f'/v9/projects/{PROJECT}')
    if project.get('accountId') != TEAM:
        raise RuntimeError('Wrong Vercel team; stopped before changing settings.')
    domains = api(f'/v9/projects/{PROJECT}/domains')['domains']
    if DOMAIN not in [item['name'] for item in domains]:
        raise RuntimeError('Wrong Vercel project; stopped before changing settings.')
    link = json.loads((ROOT / '.vercel' / 'project.json').read_text())
    if link.get('projectId') != PROJECT or link.get('orgId') != TEAM:
        raise RuntimeError('Local Vercel link does not match this website.')
    # Upload runtime settings only. GitHub tokens and database passwords stay on this computer.
    allowed = {'SUPABASE_URL', 'SUPABASE_PUBLISHABLE_KEY', 'SUPABASE_SECRET_KEY', 'CAL_API_KEY', 'LIVE_BOOKING_ENABLED', 'CONTACT_ENABLED', 'SITE_URL', 'CLINIC_ADDRESS', 'CLINIC_DENTIST', 'CLINIC_PHONE', 'CLINIC_EMAIL', 'CLINIC_HOURS'}
    values = [{'key': key, 'value': value, 'type': 'encrypted', 'target': ['production']} for key, value in config.items() if value and (key in allowed or key.startswith('CAL_EVENT_') or key.startswith('CAL_DEMO_EVENT_'))]
    for item in values:
        # The current CLI stores project Secrets through its supported endpoint. Private stdin lang.
        command = ['npx.cmd', '--yes', 'vercel@62.2.0', 'env', 'add', item['key'], 'production', '--force', '--yes', '--sensitive', '--project', PROJECT, '--scope', 'joshua-400f', '--global-config', str(ROOT / '.vercel' / 'cli')]
        result = subprocess.run(command, input=item['value'], capture_output=True, text=True, encoding='utf-8', cwd=ROOT, env=cli_environment(), timeout=90)
        if result.returncode:
            raise RuntimeError('Vercel rejected ' + item['key'] + '; private output withheld.')
        print('Production setting saved: ' + item['key'], flush=True)
    print(f'Updated {len(values)} private production settings for brightsmile.')


if __name__ == '__main__':
    main()
