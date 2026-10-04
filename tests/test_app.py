"""Check important rules with fake provider replies. Walang real account o booking na ginagawa."""
import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient

import app as clinic


# Use a pretend browser and fake provider replies to check important app behavior.
# setUp blanks live settings so these ordinary checks do not create actual appointments.
# Fake responses let us check access rules and errors nang walang real patient changes.
class ClinicTests(unittest.TestCase):
    def setUp(self):
        # Empty settings force preview mode. Para safe kahit may real keys sa developer machine.
        self.env = patch.dict(os.environ, {'LIVE_BOOKING_ENABLED':'false', 'CONTACT_ENABLED':'false', 'SUPABASE_URL':'', 'SUPABASE_PUBLISHABLE_KEY':'', 'CAL_API_KEY':''})
        self.env.start()
        self.client = TestClient(clinic.app)
        self.client.get('/book')
        self.headers = {'X-CSRF-Token':self.client.cookies['bs_csrf']}
        selected = datetime.now(clinic.MANILA).date() + timedelta(days=1)
        while selected.weekday() == 6:
            selected += timedelta(days=1)
        self.day = selected.isoformat()

    def tearDown(self):
        self.client.close()
        self.env.stop()

    def test_admin_blocks_patient_before_reading_private_tables(self):
        user = {'id': 'patient', 'app_metadata': {}, 'user_metadata': {'role': 'admin'}}
        with patch.object(clinic, 'current_user', AsyncMock(return_value=user)), patch.object(clinic, 'supabase_request', AsyncMock()) as database:
            self.assertEqual(self.client.get('/admin').status_code, 403)
            database.assert_not_called()

    def test_admin_login_page_has_no_private_records(self):
        result = self.client.get('/admin')
        self.assertEqual(result.status_code, 200)
        self.assertIn('Admin sign in', result.text)
        self.assertNotIn('Contact messages', result.text)

    def test_admin_reads_both_tables_and_escapes_messages(self):
        user = {'email': 'admin@example.com', 'app_metadata': {'role': 'admin'}}
        booking = {'patient_name': 'Patient', 'patient_email': 'patient@example.com', 'service_id': 'checkup', 'starts_at': '2026-10-05T01:00:00Z', 'status': 'accepted', 'cal_booking_uid': 'sample', 'is_demo': True}
        message = {'name': 'Patient', 'email': 'patient@example.com', 'message': '<script>unsafe</script>', 'created_at': '2026-10-04T01:00:00Z', 'is_demo': True}
        replies = [httpx.Response(200, json=[booking]), httpx.Response(200, json=[message])]
        with patch.object(clinic, 'current_user', AsyncMock(return_value=user)), patch.object(clinic, 'supabase_request', AsyncMock(side_effect=replies)) as database:
            result = self.client.get('/admin')
            self.assertEqual(result.status_code, 200)
            self.assertIn('patient@example.com', result.text)
            self.assertNotIn('&lt;script&gt;unsafe', result.text)
            self.assertIn('tab=bookings', result.text)
            result = self.client.get('/admin?tab=messages')
            self.assertEqual(result.status_code, 200)
            self.assertIn('&lt;script&gt;unsafe', result.text)
            self.assertNotIn('<script>unsafe', result.text)
            self.assertNotIn('Visit time (PHT)', result.text)
            self.assertEqual(database.await_count, 2)
            self.assertTrue(all(call.kwargs['secret'] for call in database.await_args_list))

    def booking(self):
        slots = self.client.get('/api/slots', params={'service':'checkup','day':self.day}).json()['slots']
        start = next(slot['start'] for slot in slots if slot['available'])
        return {'service':'checkup', 'day':self.day, 'start':start, 'name':'Sample Patient', 'email':'sample@example.com', 'phone':'09171234567', 'consent':True}

    def test_public_pages_are_real_html(self):
        for route in ['/', '/about', '/services', '/contact', '/book', '/account', '/account?mode=signup', '/privacy']:
            with self.subTest(route=route):
                result = self.client.get(route)
                self.assertEqual(result.status_code, 200)
                self.assertIn('<h1', result.text)
                self.assertNotIn('react', result.text.lower())

    def test_legacy_url_redirects(self):
        result = self.client.get('/index-2.html', follow_redirects=False)
        self.assertEqual(result.status_code, 307)
        self.assertEqual(result.headers['location'], '/')

    def test_missing_page_is_a_real_404(self):
        self.assertEqual(self.client.get('/does-not-exist').status_code, 404)

    def test_preview_result_is_truthful(self):
        result = self.client.post('/api/bookings', json=self.booking(), headers=self.headers)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['mode'], 'preview')
        self.assertIn('No appointment', result.json()['message'])
        self.assertNotIn('email', result.json())

    def test_missing_csrf_is_rejected(self):
        result = self.client.post('/api/bookings', json=self.booking())
        self.assertEqual(result.status_code, 403)

    def test_other_origin_is_rejected(self):
        result = self.client.post('/api/bookings', json=self.booking(), headers={**self.headers,'Origin':'https://different.example'})
        self.assertEqual(result.status_code, 403)

    def test_invalid_email_is_rejected(self):
        details = self.booking(); details['email'] = 'invalid'
        self.assertEqual(self.client.post('/api/bookings', json=details, headers=self.headers).status_code, 422)

    def test_consent_is_required(self):
        details = self.booking(); details['consent'] = False
        self.assertEqual(self.client.post('/api/bookings', json=details, headers=self.headers).status_code, 422)

    def test_fake_slot_is_rejected(self):
        details = self.booking(); details['start'] = self.day + 'T23:00:00Z'
        self.assertEqual(self.client.post('/api/bookings', json=details, headers=self.headers).status_code, 409)

    def test_unknown_service_and_past_date_are_rejected(self):
        for service, day in [('fake',self.day),('checkup','2000-01-01'),('checkup','not-a-date')]:
            self.assertEqual(self.client.get('/api/slots',params={'service':service,'day':day}).status_code, 422)

    def test_sunday_has_no_slots(self):
        day = datetime.now(clinic.MANILA).date() + timedelta(days=1)
        while day.weekday() != 6:
            day += timedelta(days=1)
        result = self.client.get('/api/slots',params={'service':'checkup','day':day.isoformat()})
        self.assertEqual(result.json()['slots'], [])

    def test_hour_long_service_fits_hours_and_lunch(self):
        result = self.client.get('/api/slots',params={'service':'filling','day':self.day}).json()
        times = [datetime.fromisoformat(slot['start'].replace('Z','+00:00')).astimezone(clinic.MANILA) for slot in result['slots']]
        self.assertTrue(times)
        for start in times:
            end = start + timedelta(minutes=60)
            self.assertLessEqual(end.hour, 17)
            self.assertFalse(start.hour == 12 or start.hour < 12 and (end.hour > 12 or end.hour == 12 and end.minute > 0))

    def test_unconnected_contact_does_not_claim_delivery(self):
        result = self.client.post('/api/contact',json={'name':'Sample User','email':'sample@example.com','message':'I have a general question.','consent':True},headers=self.headers)
        self.assertEqual(result.status_code,503)
        self.assertIn('not been sent or saved',result.json()['detail'])

    def test_unconnected_auth_shows_html_feedback(self):
        result = self.client.post('/auth/login', data={'email':'sample@example.com','password':'test-password','csrf':self.headers['X-CSRF-Token']})
        self.assertEqual(result.status_code,200)
        self.assertIn('awaiting setup',result.text)
        self.assertNotIn('bs_access',result.cookies)

    def test_account_feedback_is_escaped(self):
        result = self.client.get('/account',params={'message':'<script>alert(1)</script>'})
        self.assertNotIn('<script>alert(1)</script>',result.text)
        self.assertIn('&lt;script&gt;',result.text)

    def test_private_pages_disable_shared_cache(self):
        result = self.client.get('/account')
        self.assertEqual(result.headers['cache-control'],'no-store')
        self.assertIn('HttpOnly',result.headers['set-cookie'])
        self.assertIn("script-src 'self'",result.headers['content-security-policy'])

    def test_live_switch_requires_all_event_types(self):
        with patch.dict(os.environ, {'LIVE_BOOKING_ENABLED':'true','CAL_API_KEY':'test-key','CAL_EVENT_CHECKUP':'123','CAL_EVENT_CLEANING':'','CAL_EVENT_FILLING':'','CAL_EVENT_EXTRACTION':'','CAL_EVENT_FOLLOWUP':''}):
            self.assertFalse(clinic.live_booking())

    def test_live_booking_uses_current_contract_without_bypasses(self):
        details = self.booking()
        fake = AsyncMock(return_value={'uid':'sample_uid','status':'accepted','start':details['start']})
        choices = AsyncMock(return_value=[{'start':details['start'],'available':True}])
        with patch.object(clinic,'live_booking',return_value=True), patch.object(clinic,'available_slots',choices), patch.object(clinic,'cal_request',fake), patch.object(clinic,'event_id',return_value=123):
            result = self.client.post('/api/bookings',json=details,headers=self.headers)
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json()['mode'],'live')
        self.assertEqual(fake.call_args.args,('POST','bookings','2026-02-25'))
        payload = fake.call_args.kwargs['json']
        self.assertEqual(payload['attendee']['phoneNumber'],'+639171234567')
        self.assertNotIn('allowConflicts',payload)

    def test_supabase_login_keeps_tokens_in_private_cookies(self):
        reply = httpx.Response(200,json={'access_token':'fake-access','refresh_token':'fake-refresh','expires_in':3600})
        with patch.object(clinic,'auth_ready',return_value=True), patch.object(clinic,'supabase_request',AsyncMock(return_value=reply)):
            result = self.client.post('/auth/login',data={'email':'sample@example.com','password':'test-password','csrf':self.headers['X-CSRF-Token']},follow_redirects=False)
        self.assertEqual(result.status_code,303)
        self.assertEqual(result.cookies['bs_access'],'fake-access')
        self.assertIn('HttpOnly',result.headers['set-cookie'])
        self.assertNotIn('fake-access',result.text)

    def test_demo_booking_uses_separate_event_and_verified_fake_identity(self):
        details = self.booking()
        details['email'] = 'different@example.org'
        user = {'id': 'demo-id', 'email': 'mia.santos@example.com', 'app_metadata': {'is_demo': True}, 'user_metadata': {'full_name': '[DEMO] Mia Santos'}}
        provider = AsyncMock(return_value={'uid': 'demo-uid', 'status': 'accepted', 'start': details['start']})
        choices = AsyncMock(return_value=[{'start': details['start'], 'available': True}])
        with patch.object(clinic, 'current_user', AsyncMock(return_value=user)), patch.object(clinic, 'live_booking', return_value=True), patch.object(clinic, 'available_slots', choices), patch.object(clinic, 'cal_request', provider), patch.dict(os.environ, {'CAL_DEMO_EVENT_CHECKUP': '987'}):
            response = self.client.post('/api/bookings', json=details, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        payload = provider.call_args.kwargs['json']
        self.assertEqual(payload['eventTypeId'], 987)
        self.assertEqual(payload['attendee']['email'], user['email'])
        self.assertNotIn('phoneNumber', payload['attendee'])
        self.assertTrue(response.json()['demo'])

    def test_missing_demo_event_never_falls_back_to_a_real_visit(self):
        with patch.dict(os.environ, {'CAL_DEMO_EVENT_CHECKUP': ''}):
            with self.assertRaises(clinic.HTTPException) as error:
                clinic.booking_event_id('checkup', demo=True)
        self.assertEqual(error.exception.status_code, 503)

    def test_database_copy_failure_does_not_repeat_a_confirmed_booking(self):
        details = self.booking()
        provider = AsyncMock(return_value={'uid': 'confirmed-uid', 'status': 'accepted', 'start': details['start']})
        choices = AsyncMock(return_value=[{'start': details['start'], 'available': True}])
        with patch.object(clinic, 'live_booking', return_value=True), patch.object(clinic, 'available_slots', choices), patch.object(clinic, 'cal_request', provider), patch.object(clinic, 'event_id', return_value=123), patch.object(clinic, 'supabase_request', AsyncMock(return_value=httpx.Response(503))), patch.dict(os.environ, {'SUPABASE_URL': 'https://example.test', 'SUPABASE_SECRET_KEY': 'fake-secret'}):
            response = self.client.post('/api/bookings', json=details, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['uid'], 'confirmed-uid')
        self.assertFalse(response.json()['history_saved'])
        provider.assert_awaited_once()


if __name__ == '__main__':
    unittest.main()
