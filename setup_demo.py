"""Connect services and seed labeled presentation data. Fake patients lang ang demo."""

import csv
import json
import re
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import psycopg
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent
CONFIG = dotenv_values(ROOT / '.env')
REF = 'mymjrohklofgwdfhxcru'
MANILA = ZoneInfo('Asia/Manila')
PATIENTS = [('mia.santos', '[DEMO] Mia Santos'), ('leo.reyes', '[DEMO] Leo Reyes'), ('ana.cruz', '[DEMO] Ana Cruz')]
SERVICES = [('checkup', 'Checkup & consultation', 30), ('cleaning', 'Teeth cleaning', 30), ('filling', 'Dental fillings', 60), ('extraction', 'Tooth extraction', 60), ('followup', 'Follow-up care', 30)]


def save_setting(name, value):
    # Keep secrets in one ignored file. Walang secret na pini-print sa terminal.
    path = ROOT / '.env'
    content = path.read_text(encoding='utf-8')
    line = name + '=' + str(value)
    content = re.sub(r'^' + re.escape(name) + r'=.*$', lambda match: line, content, flags=re.M) if re.search(r'^' + re.escape(name) + '=', content, re.M) else content.rstrip() + '\n' + line + '\n'
    path.write_text(content, encoding='utf-8')
    CONFIG[name] = str(value)


def database():
    # The pooler supports our IPv4 connection. Password stays in .env, hindi sa URL.
    if CONFIG.get('SUPABASE_URL') != 'https://' + REF + '.supabase.co':
        raise RuntimeError('Wrong Supabase project; stopped before writing.')
    return psycopg.connect(host='aws-0-ap-southeast-1.pooler.supabase.com', port=5432, dbname='postgres', user='postgres.' + REF, password=CONFIG['SUPABASE_POSTRES'], sslmode='require', connect_timeout=15)


def cal(client, method, path, version='2024-06-14', **options):
    # Do not retry booking writes automatically. Baka madoble ang reservation.
    response = client.request(method, 'https://api.cal.com/v2/' + path, headers={'Authorization': 'Bearer ' + CONFIG['CAL_API_KEY'], 'cal-api-version': version}, **options)
    if response.status_code >= 400:
        # Provider errors may contain patient details. Status lang ang ipapakita.
        if path == 'event-types':
            message = response.json().get('error', {}).get('message', '')
            raise RuntimeError(f'Cal.com event configuration: {message}')
        raise RuntimeError(f'Cal.com {path.split("/")[0]} returned HTTP {response.status_code}')
    return response.json()['data']


def setup_cal(client):
    owner = cal(client, 'GET', 'me')
    if owner.get('email') != CONFIG.get('PROJECT_CAL_ACCOUNT_EMAIL'):
        raise RuntimeError('Wrong Cal.com account; stopped before writing.')
    schedules = cal(client, 'GET', 'schedules')
    schedule = next(item for item in schedules if item.get('isDefault'))
    if schedule.get('timeZone') != 'Asia/Manila':
        raise RuntimeError('Please confirm the Cal.com timezone before setup.')
    events = cal(client, 'GET', 'event-types', params={'take': 100})
    by_slug = {item['slug']: item for item in events}
    for service, title, minutes in SERVICES:
        slug = 'bright-smile-' + service
        event = by_slug.get(slug)
        if not event:
            event = cal(client, 'POST', 'event-types', json={'title': title, 'slug': slug, 'lengthInMinutes': minutes, 'scheduleId': schedule['id'], 'hidden': True, 'locations': [{'type': 'address', 'address': CONFIG['CLINIC_ADDRESS'], 'public': True}]})
        if event.get('lengthInMinutes') != minutes:
            raise RuntimeError('A clinic event has an unexpected duration.')
        save_setting('CAL_EVENT_' + service.upper(), event['id'])
    # A separate hidden event keeps sample names together. Demo lang ito, hindi clinic treatment.
    demo = by_slug.get('bright-smile-demo')
    if not demo:
        demo = cal(client, 'POST', 'event-types', json={'title': '[DEMO] Bright Smile presentation visit', 'slug': 'bright-smile-demo', 'lengthInMinutes': 15, 'scheduleId': schedule['id'], 'hidden': True, 'minimumBookingNotice': 0, 'locations': [{'type': 'address', 'address': 'DEMO ONLY - no clinic visit', 'public': True}]})
    save_setting('CAL_EVENT_DEMO', demo['id'])
    for service, title, minutes in SERVICES:
        slug = 'bright-smile-demo-' + service
        event = by_slug.get(slug)
        if not event:
            event = cal(client, 'POST', 'event-types', json={'title': '[DEMO] ' + title, 'slug': slug, 'lengthInMinutes': minutes, 'scheduleId': schedule['id'], 'hidden': True, 'locations': [{'type': 'address', 'address': 'DEMO ONLY - no clinic visit', 'public': True}]})
        save_setting('CAL_DEMO_EVENT_' + service.upper(), event['id'])
    print('Cal.com: dental services and separate demo events are ready.')


# Create presentation patients through the private Auth API and label them as demo.
# Keep the shared demo password in ignored .env, never in the clinic profile table.
# Check existing accounts first para hindi mapalitan ang unrelated real account.
def setup_auth(client, db):
    password = CONFIG.get('DEMO_PASSWORD') or secrets.token_urlsafe(24)
    save_setting('DEMO_PASSWORD', password)
    headers = {'apikey': CONFIG['SUPABASE_SECRET_KEY'], 'Authorization': 'Bearer ' + CONFIG['SUPABASE_SECRET_KEY']}
    users = []
    for slug, name in PATIENTS:
        email = slug + '@example.com'
        existing = db.execute('select id, raw_app_meta_data from auth.users where email = %s', (email,)).fetchone()
        if existing:
            if not existing[1].get('is_demo'):
                raise RuntimeError('An existing account is not labeled demo; stopped safely.')
            user_id = str(existing[0])
            # Keep the demo login in sync with our private file. Demo accounts lang ang puwedeng baguhin.
            checked = client.post(CONFIG['SUPABASE_URL'] + '/auth/v1/token?grant_type=password', headers={'apikey': CONFIG['SUPABASE_PUBLISHABLE_KEY']}, json={'email': email, 'password': password})
            if checked.status_code == 400:
                updated = client.put(CONFIG['SUPABASE_URL'] + '/auth/v1/admin/users/' + user_id, headers=headers, json={'password': password, 'email_confirm': True})
                if updated.status_code >= 400:
                    raise RuntimeError('Could not repair the labeled demo login.')
            elif checked.status_code >= 400:
                raise RuntimeError('Demo login is temporarily unavailable; no password was changed.')
        else:
            # Admin creation does not send invitations. Walang email sa fake address.
            response = client.post(CONFIG['SUPABASE_URL'] + '/auth/v1/admin/users', headers=headers, json={'email': email, 'password': password, 'email_confirm': True, 'user_metadata': {'full_name': name}, 'app_metadata': {'is_demo': True, 'demo_dataset': 'bright-smile-v1'}})
            if response.status_code >= 400:
                raise RuntimeError(f'Demo Auth user returned HTTP {response.status_code}')
            user_id = response.json()['id']
        db.execute('insert into public.patient_profiles (id,full_name,is_demo) values (%s,%s,true) on conflict (id) do update set full_name=excluded.full_name where patient_profiles.is_demo=true', (user_id, name))
        users.append({'id': user_id, 'name': name, 'email': email})
    db.commit()
    save_setting('DEMO_EMAIL', users[0]['email'])
    print('Supabase Auth: three labeled demo accounts are ready; password stays in .env.')
    return users


# Seeding adds initial sample rows so an empty project is easier to demonstrate.
# These rows use fake patient names and demo labels for presentation reports.
# Fixed keys help avoid adding the same classroom sample again sa repeated setup.
def seed_database(db, users):
    # Fixed IDs prevent extra rows when this script runs again. Hindi nadodoble ang samples.
    today = datetime.now(MANILA).replace(hour=9, minute=0, second=0, microsecond=0)
    for index in range(24):
        patient = users[index % len(users)]
        service = SERVICES[index % len(SERVICES)][0]
        start = today + timedelta(days=index - 18, hours=index % 4)
        while start.weekday() > 4:
            start += timedelta(days=1)
        status = ('completed', 'completed', 'cancelled', 'no_show')[index % 4] if start < today else 'upcoming'
        db.execute('insert into public.appointments (patient_id,cal_booking_uid,service_id,starts_at,status,is_demo,source) values (%s,%s,%s,%s,%s,true,\'demo\') on conflict (cal_booking_uid) do nothing', (patient['id'], f'demo-presentation-v1-{index:02}', service, start, status))
    for index, patient in enumerate(users):
        db.execute('insert into public.contact_messages (id,name,email,message,is_demo) values (%s,%s,%s,%s,true) on conflict (id) do nothing', (f'00000000-0000-4000-8000-{index+1:012}', patient['name'], patient['email'], '[DEMO] I would like to ask about appointment availability for my next dental visit. This is presentation data.'))
    db.commit()
    print('Database: 24 sample visits and three sample contact messages are ready.')


# Reserve sample times only in the separate demo appointment type.
# Save provider references locally and in the database so a rerun can recognize them.
# Hindi automatic retry ang booking POST; baka may reservation na kahit nawala ang reply.
def seed_cal_bookings(client, db, users):
    # Reserve only the special demo event. Hindi nagbo-book ng real dental treatment.
    for index in range(2):
        marker = f'cal-demo-presentation-v1-{index}'
        if db.execute('select 1 from public.appointments where demo_seed_key = %s', (marker,)).fetchone():
            continue
        # A local journal protects against duplicates after a network interruption. Check muna bago retry.
        journal = ROOT / '.local-state' / (marker + '.json')
        journal.parent.mkdir(parents=True, exist_ok=True)
        if journal.exists():
            result = json.loads(journal.read_text())
            if 'uid' not in result:
                raise RuntimeError('A demo booking needs manual verification before retry.')
        else:
            start = datetime.now(timezone.utc) + timedelta(days=8 + index * 2)
            slots = cal(client, 'GET', 'slots', '2024-09-04', params={'eventTypeId': int(CONFIG['CAL_EVENT_DEMO']), 'start': start.isoformat(), 'end': (start + timedelta(days=5)).isoformat(), 'timeZone': 'Asia/Manila'})
            first = next((slot['start'] for group in slots.values() for slot in group), None)
            if not first:
                raise RuntimeError('No demo booking slots are available.')
            journal.write_text(json.dumps({'pending': True}))
            result = cal(client, 'POST', 'bookings', '2026-02-25', json={'eventTypeId': int(CONFIG['CAL_EVENT_DEMO']), 'start': first, 'attendee': {'name': users[index]['name'], 'email': users[index]['email'], 'timeZone': 'Asia/Manila', 'language': 'en'}, 'metadata': {'demo_dataset': 'bright-smile-v1', 'is_demo': 'true'}})
            journal.write_text(json.dumps({'uid': result['uid'], 'start': result['start'], 'status': result['status']}))
        # The provider UID is real, but the person is fake. Label both the source and demo flag.
        db.execute('insert into public.appointments (patient_id,cal_booking_uid,service_id,starts_at,status,is_demo,source,demo_seed_key) values (%s,%s,\'checkup\',%s,%s,true,\'cal.com\',%s) on conflict (cal_booking_uid) do nothing', (users[index]['id'], result['uid'], result['start'], result['status'], marker))
        db.commit()
    print('Cal.com: two real API reservations for fake demo patients are saved.')


# This is a local setup tool, not a route that website visitors can call.
# Prepare labeled accounts and sample records so students have data to present.
# Existing demo IDs and saved references help avoid duplicate samples sa next run.
def main():
    if not CONFIG.get('SUPABASE_SECRET_KEY'):
        raise RuntimeError('Please fill SUPABASE_SECRET_KEY in .env first.')
    with httpx.Client(timeout=30) as client, database() as db:
        # Apply the small schema before adding data. May RLS locks agad ang bawat table.
        db.execute((ROOT / 'supabase-setup.sql').read_text())
        db.commit()
        setup_cal(client)
        users = setup_auth(client, db)
        seed_database(db, users)
        seed_cal_bookings(client, db, users)
        rows = db.execute('select service_id,status,source,count(*) from public.appointments where is_demo=true group by service_id,status,source order by service_id,status').fetchall()
        with (ROOT / 'demo-report.csv').open('w', newline='', encoding='utf-8') as output:
            writer = csv.writer(output)
            writer.writerow(['service', 'status', 'source', 'demo_appointments'])
            writer.writerows(rows)
        print('Presentation report saved to demo-report.csv.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, httpx.HTTPError, psycopg.Error) as error:
        # Only our safe messages reach the console. Walang passwords o provider payloads.
        print(str(error) if isinstance(error, RuntimeError) else 'Setup stopped: ' + type(error).__name__)
        sys.exit(1)
