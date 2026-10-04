"""Bright Smile uses plain HTML pages. Python ang bahala sa private services."""

# PROJECT FLOW: HTML shows the page, CSS styles it, and JavaScript handles clicks.
# Python checks form details before asking Supabase to save them or Cal.com to book a time.
# Parang school office: the browser submits a form, then Python checks where it should go.
# Supabase handles accounts and records; Cal.com keeps the actual appointment schedule.
import hmac
import logging
import json
import os
import re
import secrets
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Read private settings from .env. Hindi naka-print o kasama sa HTML ang secret keys.
ROOT = Path(__file__).resolve().parent
# Local settings win over another terminal's keys. Dito lang ang account na gagamitin.
load_dotenv(ROOT / '.env', override=True)
MANILA = ZoneInfo('Asia/Manila')
app = FastAPI(title='Bright Smile', docs_url=None, redoc_url=None, openapi_url=None)
templates = Jinja2Templates(directory=str(ROOT / 'templates'))
# This shared list supplies service names, descriptions, and planned visit lengths.
# A short ID, like "checkup", connects a page choice to its database record and Cal.com event.
# Isang listahan lang ang gamit para pareho ang service details sa lahat ng pages.
SERVICES = [
    {'id': 'checkup', 'name': 'Checkup & consultation', 'minutes': 30, 'description': 'A conversation, a closer look, and a clear next step. A good place to start if you are new to the clinic or unsure what you need.'},
    {'id': 'cleaning', 'name': 'Teeth cleaning', 'minutes': 30, 'description': 'Give your smile a fresh start with oral prophylaxis. Your dentist will check what kind of cleaning is right for you.'},
    {'id': 'filling', 'name': 'Dental fillings', 'minutes': 60, 'description': 'Care for a tooth that needs a little repair. We will explain the treatment options and help you understand the plan.'},
    {'id': 'extraction', 'name': 'Tooth extraction', 'minutes': 60, 'description': 'Start with a careful assessment and a conversation about your comfort, your options, and your aftercare.'},
    {'id': 'followup', 'name': 'Follow-up care', 'minutes': 30, 'description': 'Check how you are doing after treatment, ask questions, and talk about keeping your smile healthy.'},
]
SERVICE_MAP = {item['id']: item for item in SERVICES}
FAQS = [
    ('Do I need an account to book?', 'No account is needed to try the booking preview. When scheduling goes live, your name and email will be used for your appointment details. A patient account is optional.'),
    ('What should I bring to my first visit?', 'Bring your questions and any information your dentist may need about past dental care. The clinic can let you know if anything else is needed before your appointment.'),
    ('Can I walk in?', 'Walk-ins are welcome during clinic hours, subject to dentist availability. Booking ahead helps you plan your day.'),
    ('Is online booking available yet?', 'The booking calendar is currently a preview. Sample times let you try the experience, but do not reserve a real appointment. Live booking will start once scheduling is connected.'),
]


# Environment settings are values kept outside the main code, such as private API keys.
# Read one value and remove extra spaces so pasted settings are easier to use.
# Kapag wala pa ang value, empty text ang ibabalik instead of crashing the page.
def setting(name):
    """Get one setting safely. Blank lang kapag wala pang key."""
    return os.getenv(name, '').strip()


# The URL identifies the Supabase project; the publishable key identifies requests to it.
# This checks whether both settings exist, not whether the provider is online right now.
# Para alam ng page kung may login setup na bago ipakita ang normal form.
def auth_ready():
    return bool(setting('SUPABASE_URL') and setting('SUPABASE_PUBLISHABLE_KEY'))


# The live switch is a deliberate on/off choice, separate from having an API key.
# Every service needs its own Cal.com event ID so bookings use the correct appointment type.
# Kapag kulang ang setup, preview mode muna at walang totoong reservation.
def live_booking():
    # Both the switch and ALL event types must be ready. Hindi puwedeng kalahati ang live setup.
    return setting('LIVE_BOOKING_ENABLED').lower() == 'true' and bool(setting('CAL_API_KEY')) and all(event_id(s['id']) for s in SERVICES)


# Cal.com gives each appointment type a number, called an event ID.
# Match the service name to its .env setting and accept only a positive whole number.
# Halimbawa, the checkup ID is different from the cleaning ID kahit same clinic.
def event_id(service):
    raw = setting('CAL_EVENT_' + service.upper())
    return int(raw) if raw.isdigit() and int(raw) > 0 else None


# app_metadata is set through the private admin service, unlike editable profile details.
# Read the demo label only after Supabase has verified the signed-in account.
# Hindi sapat na mag-type ng DEMO sa name para makakuha ng demo account access.
def demo_user(user):
    # Only admin-set metadata can mark demo accounts. Hindi puwedeng baguhin ng ordinary user.
    return bool(user and user.get('app_metadata', {}).get('is_demo') is True)


# Real patients and presentation patients use separate Cal.com appointment types.
# A missing demo ID stops the request instead of silently choosing a real appointment.
# Para hindi mapaghalo ang practice bookings at real dental visits.
def booking_event_id(service, demo=False):
    if not demo:
        return event_id(service)
    raw = setting('CAL_DEMO_EVENT_' + service.upper())
    if not raw.isdigit() or int(raw) <= 0:
        raise HTTPException(503, 'Demo scheduling is awaiting setup. No real visit will be reserved.')
    return int(raw)


# These details are reused by the footer, contact page, and booking page.
# Values come from .env, with fallback text for optional settings that are still blank.
# Isang setting lang ang papalitan kapag nagbago ang clinic address or office hours.
def clinic():
    return {'address': setting('CLINIC_ADDRESS') or 'Rizal Street, San Isidro', 'dentist': setting('CLINIC_DENTIST') or 'Dr. A. Reyes', 'phone': setting('CLINIC_PHONE'), 'email': setting('CLINIC_EMAIL'), 'hours': setting('CLINIC_HOURS') or 'Monday–Saturday · 9 AM–5 PM'}


@app.middleware('http')
# Middleware runs around every request, like a shared checkpoint for all pages.
# Get the page response first, then add rules about caching and allowed page resources.
# Para hindi maiwan ang private account page sa shared cache ng ibang visitor.
async def safe_headers(request, call_next):
    response = await call_next(request)
    # These rules keep personal pages out of shared caches. Para hindi makita ng ibang tao.
    if not request.url.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; font-src 'self'; connect-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
    return response


# Join an HTML template with Python data such as clinic details and patient visits.
# Extra values let each page receive its own data while reusing the basic layout.
# May CSRF token din: a random check value connecting a submitted form to this browser.
def page(request, template, title, **extra):
    # Templates turn data into ordinary HTML. Automatic escaping ang bantay laban sa unsafe text.
    csrf = request.cookies.get('bs_csrf') or secrets.token_urlsafe(32)
    faqs = list(FAQS)
    if live_booking():
        # Live pages should give current answers. Hindi na preview ang calendar kapag connected na.
        faqs[0] = ('Do I need an account to book?', 'An account is optional. Sign in before booking if you want your visits to appear in your patient history.')
        faqs[-1] = ('Is online booking available yet?', 'Yes. Choose your service, select an available time, and complete your details. You will receive your appointment reference after booking.')
    response = templates.TemplateResponse(request=request, name=template, context={'title': title, 'path': request.url.path, 'clinic': clinic(), 'services': SERVICES, 'faqs': faqs, 'year': datetime.now(MANILA).year, 'csrf': csrf, 'auth_ready': auth_ready(), 'live': live_booking(), **extra})
    response.set_cookie('bs_csrf', csrf, httponly=True, secure=request.url.scheme == 'https', samesite='lax', max_age=86400)
    return response


# Forms arrive as JSON from JavaScript or as ordinary fields from an HTML form.
# Read either kind, reject oversized input, and compare the form's CSRF token with the cookie.
# Para hindi basta makapag-submit ang ibang website gamit ang signed-in patient browser.
async def body_data(request):
    # Small forms only. Kapag sobrang laki ang request, stop muna tayo.
    body = await request.body()
    if len(body) > 16000:
        raise HTTPException(413, 'This form is too large. Please shorten your message.')
    try:
        if request.headers.get('content-type', '').startswith('application/json'):
            data = json.loads(body)
            if not isinstance(data, dict):
                raise ValueError()
        else:
            data = {key: values[0] for key, values in parse_qs(body.decode()).items()}
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(400, 'Please check the form and try again.')
    token = request.headers.get('x-csrf-token') or str(data.get('csrf', ''))
    expected = request.cookies.get('bs_csrf', '')
    if not expected or not hmac.compare_digest(token, expected):
        raise HTTPException(403, 'Please refresh the page before sending this form.')
    origin = request.headers.get('origin')
    if origin and urlsplit(origin).netloc != request.url.netloc:
        raise HTTPException(403, 'Please send the form from this website.')
    return data


# Browser limits help visitors, but someone can also submit a request outside the form.
# Python trims spaces and checks the length again before accepting the saved value.
# Halimbawa, a name that is too short gets an error before reaching the database.
def text_field(data, key, minimum=1, maximum=100):
    value = str(data.get(key, '')).strip()
    if len(value) < minimum or len(value) > maximum:
        raise HTTPException(422, f'Please check your {key.replace("_", " ")}.')
    return value


# Check the text length first, then check for a basic email shape with an @ and domain.
# This catches simple typing mistakes; it does not prove the visitor owns the email address.
# Email confirmation ang separate step para sa new Supabase patient account.
def email_field(data):
    value = text_field(data, 'email', 3, 254)
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
        raise HTTPException(422, 'Please enter a valid email address.')
    return value


# Accept only a known service and a calendar date inside the allowed booking range.
# Convert date text into a Python date so comparisons use actual dates rather than guesses.
# Manila time ang basis ng today para pareho ang appointment day sa clinic.
def service_and_date(service, day):
    if service not in SERVICE_MAP:
        raise HTTPException(422, 'Please choose one of our services.')
    try:
        selected = date.fromisoformat(day)
    except ValueError:
        raise HTTPException(422, 'Please choose a valid date.')
    today = datetime.now(MANILA).date()
    if not today <= selected <= today + timedelta(days=90):
        raise HTTPException(422, 'Please choose a day within the next 90 days.')
    return SERVICE_MAP[service], selected


# Preview mode builds sample time buttons without creating a Cal.com reservation.
# Some sample times are unavailable so students can see different calendar states.
# Practice display lang ito, hindi proof na free talaga ang clinic sa oras na iyon.
def preview_slots(service, selected):
    # These are practice times only. Walang totoong patient o reservation sa preview.
    if selected.weekday() == 6:
        return []
    now = datetime.now(MANILA)
    result = []
    for minute in range(9 * 60, 17 * 60, 30):
        end = minute + service['minutes']
        if 12 * 60 <= minute < 13 * 60 or end > 17 * 60 or minute < 12 * 60 < end:
            continue
        start = datetime.combine(selected, time(minute // 60, minute % 60), MANILA)
        if start <= now:
            continue
        # A few unavailable times help show the calendar states. Sample lang ang mga ito.
        available = (minute // 30 + selected.day) % 5 != 0
        result.append({'start': start.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z'), 'label': start.strftime('%I:%M %p').lstrip('0'), 'available': available})
    return result


# Send Cal.com requests from Python so the private key stays off the browser page.
# The API version selects the response format expected by the calling function.
# Kapag taken na ang slot or offline ang provider, return a useful error without showing keys.
async def cal_request(method, endpoint, version, **options):
    # Cal.com's key lives here, like a private key to a room. Hindi ito pinapadala sa browser.
    headers = {'Authorization': 'Bearer ' + setting('CAL_API_KEY'), 'cal-api-version': version}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.request(method, 'https://api.cal.com/v2/' + endpoint, headers=headers, **options)
        if response.status_code == 409:
            raise HTTPException(409, 'That time was just taken. Please choose another time.')
        if response.status_code >= 400:
            raise HTTPException(502, 'Scheduling is temporarily unavailable. Please try again later.')
        return response.json()['data']
    except (httpx.HTTPError, ValueError, KeyError):
        raise HTTPException(502, 'Scheduling is temporarily unavailable. Please try again later.')


# Decide whether to show practice times or ask Cal.com for current availability.
# Live mode converts the selected Manila day to UTC and reads the returned start times.
# Ibinabalik lang ang slots ng napiling araw para hindi mapunta sa katabing date.
async def available_slots(service, selected, demo=False):
    if not live_booking():
        return preview_slots(service, selected)
    start = datetime.combine(selected, time.min, MANILA)
    end = start + timedelta(days=1, microseconds=-1)
    # Cal.com needs UTC time. Kino-convert natin ang Manila date para tama ang araw.
    data = await cal_request('GET', 'slots', '2024-09-04', params={'eventTypeId': booking_event_id(service['id'], demo), 'start': start.astimezone(timezone.utc).isoformat(), 'end': end.astimezone(timezone.utc).isoformat(), 'timeZone': 'Asia/Manila'})
    slots = []
    for group in data.values():
        for item in group:
            start_time = datetime.fromisoformat(item['start'].replace('Z', '+00:00'))
            if start_time.astimezone(MANILA).date() == selected:
                slots.append({'start': start_time.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z'), 'label': start_time.astimezone(MANILA).strftime('%I:%M %p').lstrip('0'), 'available': True})
    return slots


@app.get('/api/health')
# This endpoint reports which features have their required settings.
# It returns no passwords, API keys, patient names, or saved messages.
# Setup status lang ito; it does not check every outside service on each call.
async def health():
    return {'ok': True, 'booking': 'live' if live_booking() else 'preview', 'auth': 'configured' if auth_ready() else 'awaiting_setup'}


@app.get('/api/slots')
# The calendar calls this endpoint whenever a service or day is selected.
# Verify the account so demo patients receive slots from demo appointment types.
# Python ang nagde-decide ng schedule source, hindi ang editable browser input.
async def slots(request: Request, service: str, day: str):
    selected_service, selected_day = service_and_date(service, day)
    demo = demo_user(await current_user(request))
    return {'mode': 'live' if live_booking() else 'preview', 'slots': await available_slots(selected_service, selected_day, demo)}


@app.post('/api/bookings')
# Booking has three steps: check the form, reserve with Cal.com, then copy a history row.
# Recheck the chosen time because someone may have taken it after the calendar loaded.
# Kapag may reservation na, a database copy failure must not create a second booking.
async def book(request: Request):
    data = await body_data(request)
    service, selected = service_and_date(str(data.get('service', '')), str(data.get('day', '')))
    name = text_field(data, 'name', 2)
    email = email_field(data)
    phone = text_field(data, 'phone', 0, 25)
    if phone and not re.fullmatch(r'(?:\+63|0)9\d{9}', re.sub(r'[\s()\-]', '', phone)):
        raise HTTPException(422, 'Please enter a Philippine mobile number, or leave it blank.')
    start = str(data.get('start', ''))
    user = await current_user(request)
    demo = demo_user(user)
    choices = await available_slots(service, selected, demo)
    if not any(item['start'] == start and item['available'] for item in choices):
        raise HTTPException(409, 'That time is no longer available. Please choose another time.')
    if data.get('consent') is not True:
        raise HTTPException(422, 'Please confirm that we may use your details for this appointment.')
    if not live_booking():
        # No database write in preview. Hindi natin iniipon ang practice patient details.
        return {'mode': 'preview', 'message': 'Your visit preview is ready. No appointment has been reserved.', 'service': service['name'], 'start': start}
    attendee = {'name': name, 'email': email, 'timeZone': 'Asia/Manila', 'language': 'en'}
    if phone:
        digits = re.sub(r'[\s()\-]', '', phone)
        attendee['phoneNumber'] = '+63' + digits[1:] if digits.startswith('0') else digits
    if demo:
        # Demo accounts use fake addresses and visibly labeled Cal.com events. Walang real treatment.
        attendee['name'] = user.get('user_metadata', {}).get('full_name', '[DEMO] Patient')
        attendee['email'] = user['email']
        attendee.pop('phoneNumber', None)
    result = await cal_request('POST', 'bookings', '2026-02-25', json={'start': start, 'eventTypeId': booking_event_id(service['id'], demo), 'attendee': attendee})
    # Copy only the booking details needed for history. Cal.com ang source ng reservation.
    synced = False
    if setting('SUPABASE_URL') and setting('SUPABASE_SECRET_KEY'):
        try:
            saved = await supabase_request('POST', '/rest/v1/appointments', secret=True, params={'on_conflict': 'cal_booking_uid'}, headers={'Prefer': 'resolution=merge-duplicates'}, json={'cal_booking_uid': result['uid'], 'patient_id': user['id'] if user else None, 'patient_name': attendee['name'], 'patient_email': attendee['email'], 'service_id': service['id'], 'starts_at': result['start'], 'status': result['status'], 'is_demo': demo, 'source': 'cal.com'})
            synced = saved.status_code < 400
        except HTTPException:
            pass
        if not synced:
            # The reservation still exists if the copy fails. Huwag ipa-book ulit ang patient.
            logging.warning('A Cal.com booking needs database reconciliation; no patient details logged.')
    # Cal.com is the booking record. Huwag automatic retry para maiwasan ang duplicate booking.
    return {'mode': 'live', 'demo': demo, 'uid': result['uid'], 'status': result['status'], 'service': service['name'], 'start': result['start'], 'history_saved': synced}


# One helper keeps Supabase keys, headers, and timeout rules in a common place.
# A patient token follows ownership rules; the secret key is for trusted server actions.
# Kaya kailangan munang i-check ang admin role bago gamitin ang secret key para sa admin tables.
async def supabase_request(method, endpoint, *, token=None, secret=False, **options):
    key = setting('SUPABASE_SECRET_KEY') if secret else setting('SUPABASE_PUBLISHABLE_KEY')
    if not setting('SUPABASE_URL') or not key:
        raise HTTPException(503, 'This service is awaiting setup. Your details have not been saved.')
    headers = {'apikey': key, 'Content-Type': 'application/json'}
    headers.update(options.pop('headers', {}))
    if token:
        headers['Authorization'] = 'Bearer ' + token
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            return await client.request(method, setting('SUPABASE_URL').rstrip('/') + endpoint, headers=headers, **options)
    except httpx.HTTPError:
        raise HTTPException(502, 'The account service is unavailable. Please try again later.')


@app.post('/api/contact')
# Save the sender's name, email, and message in the contact_messages table.
# Check consent and field lengths before saving; this does not start an email delivery system.
# Pag demo account ang sender, label the row as demo para malinaw sa presentation.
async def contact(request: Request):
    data = await body_data(request)
    name, email = text_field(data, 'name', 2), email_field(data)
    message = text_field(data, 'message', 10, 2000)
    if data.get('consent') not in (True, 'on'):
        raise HTTPException(422, 'Please allow the clinic to reply to your question.')
    if setting('CONTACT_ENABLED').lower() != 'true':
        raise HTTPException(503, 'The clinic inbox is not connected yet. Your message has not been sent or saved.')
    # Only Python writes messages. Walang public key na puwedeng magbasa ng lahat ng messages.
    user = await current_user(request)
    demo = demo_user(user)
    if demo:
        # Demo notes stay clearly labeled. Fake account details lang ang gamit natin.
        name, email = user.get('user_metadata', {}).get('full_name', '[DEMO] Patient'), user['email']
    result = await supabase_request('POST', '/rest/v1/contact_messages', secret=True, json={'name': name, 'email': email, 'message': message, 'is_demo': demo})
    if result.status_code >= 400:
        raise HTTPException(502, 'Your message could not be saved. Please try again later.')
    return {'message': 'Your message has been received. The clinic will follow up.'}


# Supabase returns an access token for login and a refresh token for renewing that login.
# Store them in HttpOnly cookies so ordinary page JavaScript cannot read these values.
# Sa HTTPS, secure cookies travel over HTTPS only; sign-out removes them from this browser.
def session_cookies(response, request, result):
    # HttpOnly means JavaScript cannot read the login keys. Para mas safe ang account.
    options = {'httponly': True, 'secure': request.url.scheme == 'https', 'samesite': 'lax', 'path': '/'}
    response.set_cookie('bs_access', result['access_token'], max_age=int(result.get('expires_in', 3600)), **options)
    response.set_cookie('bs_refresh', result['refresh_token'], max_age=30 * 86400, **options)


# A cookie alone is not proof of identity because requests can contain made-up values.
# Ask Supabase to validate the access token and return the verified account details.
# Kapag invalid or expired ang token, no signed-in user ang ibabalik.
async def current_user(request):
    token = request.cookies.get('bs_access')
    if not token or not auth_ready():
        return None
    # Ask Supabase to verify the user. Hindi sapat na basta may cookie lang.
    response = await supabase_request('GET', '/auth/v1/user', token=token)
    return response.json() if response.status_code == 200 else None


# Admin permission must be in verified app_metadata, not the editable profile.
# This check runs before reading private records for the clinic admin tables.
# Ordinary signup cannot grant this role kahit lagyan ng admin ang display name.
def admin_user(user):
    # Supabase verifies this admin label. Hindi puwedeng gawing admin ang sarili gamit signup.
    return bool(user and user.get('app_metadata', {}).get('role') == 'admin')


@app.get('/admin')
# Show one selected table: bookings or contact messages, after verifying admin access.
# Read 51 rows so the page can show 50 and know whether a Next link is needed.
# Hindi sabay niloload ang buong database; page links let the admin browse more records.
async def admin_page(request: Request, tab: str = 'bookings', bookings_page: int = 1, messages_page: int = 1):
    user = await current_user(request)
    if not user:
        return page(request, 'admin.html', 'Admin sign in', user=None)
    if not admin_user(user):
        raise HTTPException(403, 'Admin access is required.')
    if tab not in ('bookings', 'messages'):
        raise HTTPException(422, 'Please choose a valid tab.')
    if not 1 <= bookings_page <= 100000 or not 1 <= messages_page <= 100000:
        raise HTTPException(422, 'Please choose a valid page.')
    # offset skips earlier pages; limit keeps each response small.
    # Sorting by date and ID gives rows a stable order even when dates match.
    # The private key stays here in Python; walang secret key sa rendered table.
    rows = {}
    # Load only the chosen table. Parang dalawang folders, isa lang ang bukas bawat click.
    selected_table = ('appointments', bookings_page) if tab == 'bookings' else ('contact_messages', messages_page)
    for table, number in [selected_table]:
        # Check admin access BEFORE using the private key. Bawal ito sa ordinary patient account.
        result = await supabase_request('GET', '/rest/v1/' + table, secret=True, params={'select': '*', 'order': 'created_at.desc,id.desc', 'offset': (number - 1) * 50, 'limit': 51})
        if result.status_code >= 400:
            raise HTTPException(502, 'Admin records are temporarily unavailable.')
        records = result.json()
        rows[table] = records[:50]
        rows[table + '_more'] = len(records) > 50
        for record in rows[table]:
            # Show Philippine time in both tables. Para madaling basahin ang dates.
            value = record['starts_at'] if table == 'appointments' else record['created_at']
            record['when'] = datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(MANILA).strftime('%b %d, %Y %I:%M %p')
            if table == 'appointments':
                record['service'] = SERVICE_MAP.get(record['service_id'], {}).get('name', record['service_id'])
    return page(request, 'admin.html', 'Clinic admin', user=user, tab=tab, bookings_page=bookings_page, messages_page=messages_page, **rows)


@app.get('/account')
# Verify login and renew an expired session when a valid refresh cookie is available.
# Fetch visit history with the patient's own token so Supabase checks ownership.
# Sariling visits lang ang makikita kahit may bookings ang ibang patient sa same table.
async def account(request: Request):
    try:
        user = await current_user(request)
    except HTTPException:
        user = None
    # Refresh an expired login using the private refresh cookie. Hindi kailangan mag-login bawat oras.
    refreshed = None
    if not user and auth_ready() and request.cookies.get('bs_refresh'):
        response = await supabase_request('POST', '/auth/v1/token?grant_type=refresh_token', json={'refresh_token': request.cookies['bs_refresh']})
        if response.status_code == 200:
            refreshed = response.json()
            user = refreshed.get('user')
    history, history_unavailable = [], False
    if user:
        token = refreshed['access_token'] if refreshed else request.cookies.get('bs_access')
        # The user's token obeys RLS. Sariling appointments lang ang mababasa dito.
        try:
            records = await supabase_request('GET', '/rest/v1/appointments', token=token, params={'select': 'service_id,starts_at,status,is_demo', 'order': 'starts_at.desc', 'limit': 30})
            history_unavailable = records.status_code >= 400
            if not history_unavailable:
                for record in records.json():
                    start = datetime.fromisoformat(record['starts_at'].replace('Z', '+00:00')).astimezone(MANILA)
                    history.append({**record, 'service': SERVICE_MAP.get(record['service_id'], {}).get('name', 'Clinic visit'), 'when': start.strftime('%b %d, %Y · %I:%M %p')})
        except (HTTPException, ValueError, KeyError):
            history_unavailable = True
    response = page(request, 'account.html', 'Patient account', user=user, appointments=history, history_unavailable=history_unavailable, demo=demo_user(user), message=request.query_params.get('message', ''), signup=request.query_params.get('mode') == 'signup')
    if refreshed:
        session_cookies(response, request, refreshed)
    return response


@app.post('/auth/{action}')
# This route handles signup, login, and logout, with separate checks for each action.
# Supabase manages passwords; the clinic profile table stores the patient's name only.
# After login, admins go to /admin and patients go to /account para tama ang landing page.
async def auth_action(action: str, request: Request):
    data = await body_data(request)
    if action == 'logout':
        token = request.cookies.get('bs_access')
        if token and auth_ready():
            try:
                await supabase_request('POST', '/auth/v1/logout', token=token)
            except HTTPException:
                # Still clear this browser's session if the service is offline. Makaka-sign out pa rin dito.
                pass
        response = RedirectResponse('/account', status_code=303)
        response.delete_cookie('bs_access'); response.delete_cookie('bs_refresh')
        return response
    if action not in ('login', 'signup'):
        raise HTTPException(404, 'Page not found.')
    try:
        if not auth_ready():
            raise HTTPException(503, 'Patient accounts are awaiting setup. No account has been created.')
        email, password = email_field(data), str(data.get('password', ''))
        if len(password) < 8 or len(password) > 128:
            raise HTTPException(422, 'Please use a password with 8 to 128 characters.')
        if action == 'signup':
            if data.get('consent') != 'on':
                raise HTTPException(422, 'Please review the privacy notice before creating an account.')
            name = text_field(data, 'name', 2)
            response = await supabase_request('POST', '/auth/v1/signup', params={'redirect_to': (setting('SITE_URL') or str(request.base_url)).rstrip('/') + '/account'}, json={'email': email, 'password': password, 'data': {'full_name': name}})
        else:
            response = await supabase_request('POST', '/auth/v1/token?grant_type=password', json={'email': email, 'password': password})
        if response.status_code >= 400:
            raise HTTPException(400, 'Please check your details and try again. If you just signed up, confirm your email first.')
        result = response.json()
        # A signup can need email confirmation. Walang fake login habang pending pa.
        if not result.get('access_token'):
            return page(request, 'account.html', 'Patient account', user=None, signup=False, message='Please check your email to confirm your account, then sign in here.')
        signed_user = result.get('user')
        if signed_user:
            # Make a name card with the user's own token. Supabase RLS pa rin ang bantay.
            full_name = str(signed_user.get('user_metadata', {}).get('full_name') or email.split('@')[0])[:100]
            full_name = full_name if len(full_name) >= 2 else 'Patient'
            try:
                profile = await supabase_request('POST', '/rest/v1/patient_profiles', token=result['access_token'], params={'on_conflict': 'id'}, headers={'Prefer': 'resolution=ignore-duplicates'}, json={'id': signed_user['id'], 'full_name': full_name, 'is_demo': demo_user(signed_user)})
                if profile.status_code >= 400:
                    logging.warning('Profile creation needs review; no patient details logged.')
            except HTTPException:
                logging.warning('Profile service unavailable; sign-in still works.')
        redirect = RedirectResponse('/admin' if admin_user(signed_user) else '/account', status_code=303)
        session_cookies(redirect, request, result)
        return redirect
    except HTTPException as error:
        return page(request, 'account.html', 'Patient account', user=None, signup=action == 'signup', message=error.detail)


# Each route shows one HTML file. Parang pagpili ng tamang page sa isang book.
@app.get('/')
async def home(request: Request):
    return page(request, 'home.html', 'A little care. A brighter smile.')


@app.get('/about')
async def about(request: Request):
    return page(request, 'about.html', 'About us')


@app.get('/services')
async def services_page(request: Request):
    return page(request, 'services.html', 'Our services')


@app.get('/contact')
async def contact_page(request: Request):
    return page(request, 'contact.html', 'Contact us', contact_ready=setting('CONTACT_ENABLED').lower() == 'true' and bool(setting('SUPABASE_SECRET_KEY')))


@app.get('/book')
async def book_page(request: Request):
    return page(request, 'book.html', 'Book an appointment', demo=demo_user(await current_user(request)), selected=request.query_params.get('service', 'checkup'), today=datetime.now(MANILA).date().isoformat())


@app.get('/privacy')
async def privacy(request: Request):
    return page(request, 'privacy.html', 'Privacy notice')


@app.get('/index-2.html')
# Old bookmarks may still point to the original prototype filename.
# Redirect them to the current homepage instead of keeping two different homepages.
# Para gumana pa rin ang lumang link habang iisang website lang ang mina-maintain.
async def old_link():
    return RedirectResponse('/', status_code=307)


# CSS, photos, fonts, and small scripts live in one folder. Madaling hanapin ang design files.
app.mount('/static', StaticFiles(directory=str(ROOT / 'static')), name='static')


@app.exception_handler(404)
# Unknown addresses show our own HTML error page with a real 404 status.
# A 404 tells browsers that the requested page does not exist, even with a normal site layout.
# May link pauwi ang visitor instead of a blank screen or confusing server message.
async def not_found(request, error):
    response = page(request, 'not-found.html', 'Page not found')
    response.status_code = 404
    return response
