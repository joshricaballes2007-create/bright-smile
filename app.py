"""Bright Smile uses plain HTML pages. Python ang bahala sa private services."""

import hmac
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
load_dotenv(ROOT / '.env')
MANILA = ZoneInfo('Asia/Manila')
app = FastAPI(title='Bright Smile', docs_url=None, redoc_url=None, openapi_url=None)
templates = Jinja2Templates(directory=str(ROOT / 'templates'))
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


def setting(name):
    """Get one setting safely. Blank lang kapag wala pang key."""
    return os.getenv(name, '').strip()


def auth_ready():
    return bool(setting('SUPABASE_URL') and setting('SUPABASE_PUBLISHABLE_KEY'))


def live_booking():
    # Both the switch and ALL event types must be ready. Hindi puwedeng kalahati ang live setup.
    return setting('LIVE_BOOKING_ENABLED').lower() == 'true' and bool(setting('CAL_API_KEY')) and all(event_id(s['id']) for s in SERVICES)


def event_id(service):
    raw = setting('CAL_EVENT_' + service.upper())
    return int(raw) if raw.isdigit() and int(raw) > 0 else None


def clinic():
    return {'address': setting('CLINIC_ADDRESS') or 'Rizal Street, San Isidro', 'dentist': setting('CLINIC_DENTIST') or 'Dr. A. Reyes', 'phone': setting('CLINIC_PHONE'), 'email': setting('CLINIC_EMAIL')}


@app.middleware('http')
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


def page(request, template, title, **extra):
    # Templates turn data into ordinary HTML. Automatic escaping ang bantay laban sa unsafe text.
    csrf = request.cookies.get('bs_csrf') or secrets.token_urlsafe(32)
    response = templates.TemplateResponse(request=request, name=template, context={'title': title, 'path': request.url.path, 'clinic': clinic(), 'services': SERVICES, 'faqs': FAQS, 'year': datetime.now(MANILA).year, 'csrf': csrf, 'auth_ready': auth_ready(), 'live': live_booking(), **extra})
    response.set_cookie('bs_csrf', csrf, httponly=True, secure=request.url.scheme == 'https', samesite='lax', max_age=86400)
    return response


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


def text_field(data, key, minimum=1, maximum=100):
    value = str(data.get(key, '')).strip()
    if len(value) < minimum or len(value) > maximum:
        raise HTTPException(422, f'Please check your {key.replace("_", " ")}.')
    return value


def email_field(data):
    value = text_field(data, 'email', 3, 254)
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
        raise HTTPException(422, 'Please enter a valid email address.')
    return value


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


async def available_slots(service, selected):
    if not live_booking():
        return preview_slots(service, selected)
    start = datetime.combine(selected, time.min, MANILA)
    end = start + timedelta(days=1, microseconds=-1)
    # Cal.com needs UTC time. Kino-convert natin ang Manila date para tama ang araw.
    data = await cal_request('GET', 'slots', '2024-09-04', params={'eventTypeId': event_id(service['id']), 'start': start.astimezone(timezone.utc).isoformat(), 'end': end.astimezone(timezone.utc).isoformat(), 'timeZone': 'Asia/Manila'})
    slots = []
    for group in data.values():
        for item in group:
            start_time = datetime.fromisoformat(item['start'].replace('Z', '+00:00'))
            if start_time.astimezone(MANILA).date() == selected:
                slots.append({'start': start_time.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z'), 'label': start_time.astimezone(MANILA).strftime('%I:%M %p').lstrip('0'), 'available': True})
    return slots


@app.get('/api/health')
async def health():
    return {'ok': True, 'booking': 'live' if live_booking() else 'preview', 'auth': 'configured' if auth_ready() else 'awaiting_setup'}


@app.get('/api/slots')
async def slots(service: str, day: str):
    selected_service, selected_day = service_and_date(service, day)
    return {'mode': 'live' if live_booking() else 'preview', 'slots': await available_slots(selected_service, selected_day)}


@app.post('/api/bookings')
async def book(request: Request):
    data = await body_data(request)
    service, selected = service_and_date(str(data.get('service', '')), str(data.get('day', '')))
    name = text_field(data, 'name', 2)
    email = email_field(data)
    phone = text_field(data, 'phone', 0, 25)
    if phone and not re.fullmatch(r'(?:\+63|0)9\d{9}', re.sub(r'[\s()\-]', '', phone)):
        raise HTTPException(422, 'Please enter a Philippine mobile number, or leave it blank.')
    start = str(data.get('start', ''))
    choices = await available_slots(service, selected)
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
    result = await cal_request('POST', 'bookings', '2026-02-25', json={'start': start, 'eventTypeId': event_id(service['id']), 'attendee': attendee})
    # Cal.com is the booking record. Huwag automatic retry para maiwasan ang duplicate booking.
    return {'mode': 'live', 'uid': result['uid'], 'status': result['status'], 'service': service['name'], 'start': result['start']}


async def supabase_request(method, endpoint, *, token=None, secret=False, **options):
    key = setting('SUPABASE_SECRET_KEY') if secret else setting('SUPABASE_PUBLISHABLE_KEY')
    if not setting('SUPABASE_URL') or not key:
        raise HTTPException(503, 'This service is awaiting setup. Your details have not been saved.')
    headers = {'apikey': key, 'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            return await client.request(method, setting('SUPABASE_URL').rstrip('/') + endpoint, headers=headers, **options)
    except httpx.HTTPError:
        raise HTTPException(502, 'The account service is unavailable. Please try again later.')


@app.post('/api/contact')
async def contact(request: Request):
    data = await body_data(request)
    name, email = text_field(data, 'name', 2), email_field(data)
    message = text_field(data, 'message', 10, 2000)
    if data.get('consent') not in (True, 'on'):
        raise HTTPException(422, 'Please allow the clinic to reply to your question.')
    if setting('CONTACT_ENABLED').lower() != 'true':
        raise HTTPException(503, 'The clinic inbox is not connected yet. Your message has not been sent or saved.')
    # Only Python writes messages. Walang public key na puwedeng magbasa ng lahat ng messages.
    result = await supabase_request('POST', '/rest/v1/contact_messages', secret=True, json={'name': name, 'email': email, 'message': message})
    if result.status_code >= 400:
        raise HTTPException(502, 'Your message could not be saved. Please try again later.')
    return {'message': 'Your message has been received. The clinic will follow up.'}


def session_cookies(response, request, result):
    # HttpOnly means JavaScript cannot read the login keys. Para mas safe ang account.
    options = {'httponly': True, 'secure': request.url.scheme == 'https', 'samesite': 'lax', 'path': '/'}
    response.set_cookie('bs_access', result['access_token'], max_age=int(result.get('expires_in', 3600)), **options)
    response.set_cookie('bs_refresh', result['refresh_token'], max_age=30 * 86400, **options)


async def current_user(request):
    token = request.cookies.get('bs_access')
    if not token or not auth_ready():
        return None
    # Ask Supabase to verify the user. Hindi sapat na basta may cookie lang.
    response = await supabase_request('GET', '/auth/v1/user', token=token)
    return response.json() if response.status_code == 200 else None


@app.get('/account')
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
    response = page(request, 'account.html', 'Patient account', user=user, message=request.query_params.get('message', ''), signup=request.query_params.get('mode') == 'signup')
    if refreshed:
        session_cookies(response, request, refreshed)
    return response


@app.post('/auth/{action}')
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
        redirect = RedirectResponse('/account', status_code=303)
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
    return page(request, 'book.html', 'Book an appointment', selected=request.query_params.get('service', 'checkup'), today=datetime.now(MANILA).date().isoformat())


@app.get('/privacy')
async def privacy(request: Request):
    return page(request, 'privacy.html', 'Privacy notice')


@app.get('/index-2.html')
async def old_link():
    return RedirectResponse('/', status_code=307)


# CSS, photos, fonts, and small scripts live in one folder. Madaling hanapin ang design files.
app.mount('/static', StaticFiles(directory=str(ROOT / 'static')), name='static')


@app.exception_handler(404)
async def not_found(request, error):
    response = page(request, 'not-found.html', 'Page not found')
    response.status_code = 404
    return response
